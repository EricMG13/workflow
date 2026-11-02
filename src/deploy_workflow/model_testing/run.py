"""Run driver (Task 11): plans the (case, pathway, config) runs of a stage, drives O2
``run_pathway`` for each, scores the run directories with ``score_run`` and writes the report.

The framework never writes or edits ``run.json`` (C4): ``run_pathway`` creates it. Offline is the
default (``recorded_adapter``); a live run passes the ruling to ``live_adapter``, which owns the
R2 gate. The driver's own check of the ruling path is a pre-check for a clear message only.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import re
import sys
from collections.abc import Iterator, Sequence
from collections.abc import Mapping as MappingABC
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, ROUND_UP, Context, Decimal, localcontext
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from pydantic import ValidationError

from deploy_vii.contracts import PATHWAY_MODULES, Contract, PathwayId
from deploy_workflow.context import ContextRefused
from deploy_workflow.html_text import UndecodableHtml
from deploy_workflow.model import adapter as adapter_module
from deploy_workflow.model.adapter import (
    LivePauseInForce,
    ModelAdapter,
    RecordingError,
    live_adapter,
    recorded_adapter,
)
from deploy_workflow.model.record import CallRecord
from deploy_workflow.model.redact import KEY_PATTERN
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.model_testing.budget import (
    AccountExhausted,
    BudgetError,
    Settlement,
    account_spend,
    load_settlements,
    require_budget,
)
from deploy_workflow.model_testing.cases import CaseError, GoldenCase, load_case
from deploy_workflow.model_testing.configs import (
    ACCOUNTS,
    CASES,
    CONFIGS,
    OPUS_PATHWAYS,
    PILOT_PATHWAY,
)
from deploy_workflow.model_testing.faults import read_faults
from deploy_workflow.model_testing.mapping import Mapping, MappingError, load_mapping
from deploy_workflow.model_testing.pathway import PathwayScore, receipt_refusals, score_run
from deploy_workflow.model_testing.records import JournalError, RunMeta, read_run
from deploy_workflow.model_testing.report import render_report
from deploy_workflow.run_inputs import HTML_MEDIA, CaseSource, RunInputError, RunOutcome
from deploy_workflow.run_pathway import run_pathway

Stage = Literal["pilot", "repair", "comparison"]
PlannedRun = tuple[str, PathwayId, str]

SETTLEMENTS_FILE = "settlements.json"
SCORES_FILE = "scores.json"
REPORT_FILE = "report.md"
FAULTS_FILE = "faults.jsonl"
EXHAUSTED_FILE = "exhausted.json"
DEFAULT_RUNS_ROOT = Path("artifacts/model-testing")
LOCK_FILE = ".driver.lock"

# Per-run amount a live run must be able to cover before any run has been measured. Basis: spec
# 7.2 (docs/superpowers/specs/2026-10-31-model-testing-design.md, section 7.2 "Budget"), each
# total divided by its run count and rounded up to the cent:
#   sol-medium   67.68 for about two rounds of six pathways (12 runs)     -> 5.64
#   sol-high     48.88 for six pathways                                    -> 8.1467 -> 8.15
#   opus-medium  125.72 for the five Opus pathways                         -> 25.144 -> 25.15
#   deepseek-max 9.97 for one round of six, the DeepSeek line of the budget plan the user
#                adopted ("Adopt it", 2026-10-31; work/model-testing/HANDOFF.md) -> 1.6617 -> 1.67
# Once a settled live run of the configuration exists, its measured cost replaces the estimate.
RUN_ESTIMATE_USD: MappingABC[str, Decimal] = MappingProxyType(
    {
        "sol-medium": Decimal("5.64"),
        "sol-high": Decimal("8.15"),
        "opus-medium": Decimal("25.15"),
        "deepseek-max": Decimal("1.67"),
    }
)
# Spec 7.2: all six Opus pathways are estimated at 154.65 and the five at 125.72, so
# distressed_restructuring is 28.93; it runs only if the measured Opus spend leaves room.
OPUS_FIVE_ESTIMATE_USD = Decimal("125.72")
DISTRESSED_OPUS_ESTIMATE_USD = Decimal("28.93")
DISTRESSED_PATHWAY: PathwayId = "distressed_restructuring"
OPUS_CONFIG = "opus-medium"

_WIDE = Context(prec=120, rounding=ROUND_HALF_UP)


class DriverError(ValueError):
    """A refused argument or input of the driver; the message names it."""


def plan_runs(stage: Stage) -> tuple[PlannedRun, ...]:
    """The (case_id, pathway, config_id) runs of a stage, one configuration at a time so a
    configuration that runs out of credit loses only its own tail."""
    if stage == "pilot":
        return tuple((CASES[PILOT_PATHWAY], PILOT_PATHWAY, config) for config in CONFIGS)
    if stage == "repair":
        repair = [c.config_id for c in CONFIGS.values() if "repair" in c.roles]
        return tuple(
            (case, pathway, config) for config in repair for pathway, case in CASES.items()
        )
    high = tuple((case, pathway, "sol-high") for pathway, case in CASES.items())
    opus = tuple((CASES[pathway], pathway, OPUS_CONFIG) for pathway in OPUS_PATHWAYS)
    return high + opus  # comparison


@dataclass(frozen=True)
class Settings:
    out: Path
    cases: Path
    corpus: Path
    recordings: Path | None = None
    live: bool = False
    ruling: Path | None = None
    runs_root: Path = DEFAULT_RUNS_ROOT


@dataclass(frozen=True)
class CaseInputs:
    case: GoldenCase
    mapping: Mapping
    sources: tuple[CaseSource, ...]


@dataclass(frozen=True)
class StageResult:
    outcomes: tuple[RunOutcome, ...]
    stopped: MappingABC[str, str]  # config (or config and pathway) -> why its runs stopped


# ------------------------------------------------------------------ arguments and inputs


def _precheck_ruling(ruling: Path) -> None:
    """A clear message for a ruling that is missing or outside docs/rulings. Not the gate:
    ``live_adapter`` runs the R2 gate on every construction."""
    root = adapter_module.LIVE_RULINGS_ROOT.resolve()
    try:
        resolved = ruling.resolve(strict=True)
    except OSError:
        raise DriverError(f"ruling {ruling} does not exist") from None
    if not resolved.is_file() or not resolved.is_relative_to(root):
        raise DriverError(f"ruling {ruling} must be a file under docs/rulings/")


def check_settings(settings: Settings) -> None:
    if settings.live and not settings.runs_root.is_absolute():
        raise DriverError(
            "--live needs an explicit absolute --runs-root: the default is relative, so each "
            "worktree would keep its own ledger and miss spend recorded elsewhere"
        )
    if not settings.out.resolve().is_relative_to(settings.runs_root.resolve()):
        raise DriverError(
            f"--out {settings.out} is outside --runs-root {settings.runs_root}: spend stored "
            "outside the runs root is not counted against the account caps"
        )
    if settings.live:
        if settings.ruling is None:
            raise DriverError("--live needs --ruling docs/rulings/<file>.md")
        if settings.recordings is not None:
            raise DriverError("--recordings is for offline runs; it cannot be combined with --live")
        _precheck_ruling(settings.ruling)
    else:
        if settings.ruling is not None:
            raise DriverError("--ruling is for --live runs only")
        if settings.recordings is None:
            raise DriverError(
                "offline runs need --recordings DIR (each configuration reads DIR/<config_id>/)"
            )


def _media_type(source_id: str, path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".htm", ".html"):
        return HTML_MEDIA
    raise DriverError(f"source {source_id}: unsupported file type {suffix!r}")


def _golden_sources(case_id: str, golden: object, corpus: Path) -> tuple[CaseSource, ...]:
    if not isinstance(golden, dict) or not isinstance(golden.get("sources"), list):
        raise DriverError(f"{case_id}: module_golden.json has no sources list")
    root = corpus.resolve()
    sources: list[CaseSource] = []
    for item in golden["sources"]:
        try:
            source_id, relative, expected = item["source_id"], item["file"], item["sha256"]
        except (KeyError, TypeError):
            raise DriverError(f"{case_id}: a source lacks source_id, file or sha256") from None
        path = (root / relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(root):
            raise DriverError(f"{case_id}: source {source_id}: file must lie inside the corpus")
        if not path.is_file():
            raise DriverError(f"{case_id}: source {source_id}: file is missing from the corpus")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise DriverError(f"{case_id}: source {source_id}: sha256 differs from the golden's")
        sources.append(CaseSource(source_id, path, _media_type(source_id, path)))
    return tuple(sources)


def load_inputs(case_id: str, cases: Path, corpus: Path) -> CaseInputs:
    """The case, its mapping and its corpus sources, every source checked against the golden's
    sha256 before anything runs. The context is the one the golden names."""
    case_dir = cases / case_id
    golden_path = case_dir / "module_golden.json"
    if not golden_path.is_file():
        raise DriverError(f"{case_id}: no module_golden.json under {cases}")
    try:
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
    except ValueError:
        raise DriverError(f"{case_id}: module_golden.json is not valid JSON") from None
    sources = _golden_sources(case_id, golden, corpus)
    case = load_case(case_dir, corpus)
    return CaseInputs(case, load_mapping(case_dir / "mapping.json", case), sources)


# ------------------------------------------------------------------ run folders and budget


def _run_dirs(root: Path) -> list[Path]:
    """Every run directory under ``root``: one that holds ``sources/`` (``run_pathway`` stages
    it first) or ``run.json``. A run directory is not searched further."""
    found: list[Path] = []
    pending = [root] if root.is_dir() else []
    while pending:
        for child in sorted(
            p
            for p in pending.pop().iterdir()
            if p.is_dir() or (p.is_symlink() and not p.exists())  # a dangling link is refused
        ):
            if child.is_symlink():
                raise DriverError(
                    f"{child} is a symbolic link: its runs would go uncounted; "
                    "move the folder in or remove the link"
                )
            if (child / "run.json").is_file() or (child / "sources").is_dir():
                found.append(child)
            else:
                pending.append(child)
    return sorted(found)


def _read_all(root: Path) -> list[tuple[Path, RunMeta, tuple[CallRecord, ...]]]:
    """Every run directory under ``root``. One with ``sources/`` but no ``run.json`` is a crashed
    run whose spend cannot be counted (ledger ruling 2026-11-01): the command stops."""
    found: list[tuple[Path, RunMeta, tuple[CallRecord, ...]]] = []
    for folder in _run_dirs(root):
        if not (folder / "run.json").is_file():
            raise DriverError(
                f"run folder {folder.name} has no run.json: a crashed run, its spend cannot be "
                "counted; resume it or move it away"
            )
        meta, records = read_run(folder)
        found.append((folder, meta, records))
    return found


def load_runs(root: Path) -> list[tuple[RunMeta, tuple[CallRecord, ...]]]:
    return [(meta, records) for _, meta, records in _read_all(root)]


def load_all_settlements(root: Path, out: Path) -> tuple[Settlement, ...]:
    """The settlements file of ``out`` and of every folder holding a run under ``root``."""
    folders = {out.resolve()} | {d.parent.resolve() for d in _run_dirs(root)}
    found: list[Settlement] = []
    for folder in sorted(folders):
        found += load_settlements(folder / SETTLEMENTS_FILE)
    return tuple(found)


def _next_number(root: Path, prefix: str) -> int:
    """The next free integer for run ids ``<prefix>-<n>`` across every run directory."""
    used = [
        int(m.group(1))
        for folder in _run_dirs(root)
        if (m := re.fullmatch(re.escape(prefix) + r"-(\d+)", folder.name))
    ]
    return max(used, default=0) + 1


def _run_spend(
    meta: RunMeta, records: tuple[CallRecord, ...], settlements: Sequence[Settlement]
) -> Decimal:
    mine = [s for s in settlements if s.run_id == meta.run_id]
    return account_spend([(meta, records)], CONFIGS[meta.config_id].provider, mine)


def needed_usd(
    config_id: str,
    runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]],
    settlements: Sequence[Settlement] = (),
) -> Decimal:
    """What one more run of the configuration needs: the highest measured spend of its settled
    live runs, or the spec 7.2 estimate before there is one."""
    measured = [
        _run_spend(meta, records, settlements)
        for meta, records in runs
        if meta.config_id == config_id and meta.mode == "live" and meta.outcome == "settled"
    ]
    return max(measured) if measured else RUN_ESTIMATE_USD[config_id]


def _opus_five(runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]]) -> list[RunMeta]:
    done = [
        meta
        for meta, _ in runs
        if meta.config_id == OPUS_CONFIG
        and meta.outcome == "settled"
        and meta.pathway in OPUS_PATHWAYS
    ]
    return done if {m.pathway for m in done} == set(OPUS_PATHWAYS) else []


def distressed_opus_estimate(
    runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]],
    settlements: Sequence[Settlement] = (),
) -> Decimal | None:
    """The spec 7.2 estimate of distressed_restructuring on Opus, scaled by how the five Opus
    pathways measured against their 125.72 estimate; ``None`` until all five have settled."""
    five = {m.run_id for m in _opus_five(runs)}
    if not five:
        return None
    with localcontext(_WIDE):
        spent = sum(
            (_run_spend(m, r, settlements) for m, r in runs if m.run_id in five), Decimal(0)
        )
        scaled = DISTRESSED_OPUS_ESTIMATE_USD * spent / OPUS_FIVE_ESTIMATE_USD
        return scaled.quantize(Decimal("0.01"), rounding=ROUND_UP)


# ------------------------------------------------------------------ driving


class _Exhausted(Contract):
    schema_version: Literal["driver-exhausted/1"]
    stopped: dict[str, str]


def _invalid(name: str, error: ValidationError) -> DriverError:
    shown = "; ".join(
        f"{'.'.join(str(p) for p in e['loc']) or '<root>'}: {e['msg']}"
        for e in error.errors(include_input=False, include_url=False, include_context=False)[:5]
    )
    return DriverError(f"{name}: invalid: {shown}")


def _read_exhausted(out: Path) -> dict[str, str]:
    path = out / EXHAUSTED_FILE
    if not path.is_file():
        return {}
    try:
        return dict(_Exhausted.model_validate_json(path.read_bytes()).stopped)
    except ValidationError as error:
        raise _invalid(EXHAUSTED_FILE, error) from None


def check_budget(
    config_id: str,
    runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]],
    needed: Decimal,
    settlements: Sequence[Settlement],
) -> Decimal:
    """The cap for one more run, or ``AccountExhausted`` (an unknown charge, too little credit,
    none left)."""
    cap = require_budget(config_id, runs, needed, settlements)
    if cap <= 0:
        raise AccountExhausted(f"{config_id}: no usable credit left")
    return cap


def current_stops(
    runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]], settlements: Sequence[Settlement]
) -> dict[str, str]:
    """The configurations that cannot run now, derived from the runs and settlements as they are."""
    stops: dict[str, str] = {}
    for config_id in CONFIGS:
        try:
            check_budget(config_id, runs, Decimal(0), settlements)
        except AccountExhausted as error:
            stops[config_id] = str(error)
    return stops


def _spec(config_id: str) -> ModelSpec:
    config = CONFIGS[config_id]
    return ModelSpec(config.config_id, config.provider, config.model, config.effort)


def _adapter(settings: Settings, spec: ModelSpec) -> ModelAdapter:
    """``check_settings`` guarantees a ruling exactly when the run is live."""
    if settings.ruling is not None:
        return live_adapter(spec, settings.ruling)
    if settings.recordings is not None:
        return recorded_adapter(spec, settings.recordings / spec.config_id)
    raise DriverError("neither a ruling nor recordings were given")


@dataclass
class _Driver:
    stage: Stage
    settings: Settings
    inputs: dict[str, CaseInputs]
    adapters: dict[str, ModelAdapter]
    settlements: tuple[Settlement, ...]
    runs: list[tuple[RunMeta, tuple[CallRecord, ...]]]
    stopped: dict[str, str] = field(default_factory=dict)
    outcomes: list[RunOutcome] = field(default_factory=list)

    def run(
        self,
        case_id: str,
        pathway: PathwayId,
        config_id: str,
        needed: Decimal | None = None,
        stop_key: str | None = None,
    ) -> None:
        key = config_id if stop_key is None else stop_key
        if key in self.stopped:
            return
        if needed is None:
            live = self.settings.live
            needed = needed_usd(config_id, self.runs, self.settlements) if live else Decimal(0)
        try:
            cap = check_budget(config_id, self.runs, needed, self.settlements)
        except AccountExhausted as error:
            self.stopped[key] = str(error)
            return
        root = self.settings.runs_root
        prefix = f"{self.stage}-{config_id}-{pathway}"
        run_id = f"{prefix}-{_next_number(root, prefix)}"
        found = self.inputs[case_id]
        self.settings.out.mkdir(parents=True, exist_ok=True)
        self.outcomes.append(
            run_pathway(
                case_id=case_id,
                sources=found.sources,
                context=found.case.context_path,
                pathway=pathway,
                model=_spec(config_id),
                adapter=self.adapters[config_id],
                cap_usd=cap,
                run_dir=self.settings.out / run_id,
                run_id=run_id,
            )
        )
        self.runs = load_runs(root)

    def distressed_on_opus(self) -> None:
        """After the five Opus pathways: distressed_restructuring only if the account's cap
        covers its measured estimate."""
        key = f"{OPUS_CONFIG} ({DISTRESSED_PATHWAY})"
        estimate = distressed_opus_estimate(self.runs, self.settlements)
        if estimate is None:
            self.stopped[key] = "skipped: the five Opus pathways have not all settled"
        elif OPUS_CONFIG in self.stopped:
            self.stopped[key] = f"skipped: {OPUS_CONFIG} is stopped"
        else:
            self.run(
                CASES[DISTRESSED_PATHWAY],
                DISTRESSED_PATHWAY,
                OPUS_CONFIG,
                needed=estimate,
                stop_key=key,
            )


def _record_stopped(out: Path, stopped: MappingABC[str, str]) -> None:
    """Rewrite ``exhausted.json`` from this command's stops; none removes it."""
    path = out / EXHAUSTED_FILE
    if not stopped:
        path.unlink(missing_ok=True)
        return
    body = _Exhausted(schema_version="driver-exhausted/1", stopped=dict(stopped))
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(body.model_dump_json(indent=2) + "\n", encoding="utf-8")


@contextmanager
def _root_lock(root: Path) -> Iterator[None]:
    """An exclusive lock on the runs root, held from before the first budget and run_id read until
    the last run returns. A second stage command fails at once rather than waiting."""
    # ponytail: one lock per runs-root; per-config locks if parallel stages are ever needed
    try:
        root.mkdir(parents=True, exist_ok=True)
        handle = (root / LOCK_FILE).open("a")
    except OSError as exc:
        raise DriverError(
            f"cannot open the lock file {root / LOCK_FILE}: {exc.strerror or exc}"
        ) from None
    with handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise DriverError(
                f"another stage command holds {root / LOCK_FILE}; wait for it to finish"
            ) from None
        yield


def run_stage(stage: Stage, settings: Settings) -> StageResult:
    """Run every planned run of a stage. Everything that can be refused is refused before the
    first run: the arguments, a crashed run folder, the settlements, the cases and their sources,
    and each configuration's adapter (the live gate included)."""
    check_settings(settings)
    planned = plan_runs(stage)
    case_ids = {case for case, _, _ in planned}
    if stage == "comparison":
        case_ids.add(CASES[DISTRESSED_PATHWAY])
    inputs = {c: load_inputs(c, settings.cases, settings.corpus) for c in sorted(case_ids)}
    adapters: dict[str, ModelAdapter] = {}
    for _, _, config_id in planned:
        if config_id not in adapters:
            adapters[config_id] = _adapter(settings, _spec(config_id))
    with _root_lock(settings.runs_root):
        runs = load_runs(settings.runs_root)
        settlements = load_all_settlements(settings.runs_root, settings.out)
        driver = _Driver(stage, settings, inputs, adapters, settlements, runs)
        for case_id, pathway, config_id in planned:
            driver.run(case_id, pathway, config_id)
        if stage == "comparison":
            driver.distressed_on_opus()
        _record_stopped(settings.out, driver.stopped)
    return StageResult(tuple(driver.outcomes), MappingProxyType(dict(driver.stopped)))


# ------------------------------------------------------------------ scoring and report


class _Scores(Contract):
    schema_version: Literal["model-testing-scores/1"]
    scores: tuple[PathwayScore, ...]


def _check_refusal_names(meta: RunMeta, refusals: MappingABC[str, tuple[str, ...]]) -> None:
    """A refusal naming a module or input outside the pathway preset is refused, by name."""
    preset = set(PATHWAY_MODULES[meta.pathway])
    for module_id, inputs in refusals.items():
        for name in (module_id, *inputs):
            if name not in preset:
                raise DriverError(
                    f"run {meta.run_id}: the receipt's refusal of {module_id} names {name}, "
                    f"outside the {meta.pathway} preset"
                )


def score_out(settings: Settings) -> Path:
    """Score every run folder under ``out`` into ``scores.json`` (reads only the run folders)."""
    found = _read_all(settings.out)
    if not found:
        raise DriverError(f"no run folders under {settings.out}")
    inputs: dict[str, CaseInputs] = {}
    scores: list[PathwayScore] = []
    for folder, meta, _ in found:
        if meta.case_id not in CASES.values():
            raise DriverError(f"run {meta.run_id}: case {meta.case_id} is not one of the goldens")
        if meta.case_id not in inputs:
            inputs[meta.case_id] = load_inputs(meta.case_id, settings.cases, settings.corpus)
        scored = inputs[meta.case_id]
        refusals = receipt_refusals(folder)
        _check_refusal_names(meta, refusals)
        scores.append(score_run(folder, scored.case, scored.mapping, refusals=refusals))
    path = settings.out / SCORES_FILE
    body = _Scores(schema_version="model-testing-scores/1", scores=tuple(scores))
    path.write_text(body.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def _money(value: Decimal) -> str:
    return f"${value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP, context=_WIDE)}"


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def _notes(
    stopped: MappingABC[str, str],
    settlements: Sequence[Settlement],
    runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]],
) -> list[str]:
    lines: list[str] = []
    if stopped:
        lines += ["## Stopped configurations", ""]
        lines += [f"- {key}: {_cell(why)}" for key, why in sorted(stopped.items())]
        lines.append("")
    if settlements:
        lines += [
            "## Settled charges",
            "",
            "| Run | Module | Step | Attempt | Call | Settled | By | Date | Source |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        ordered = sorted(
            settlements, key=lambda x: (x.run_id, x.module_id, x.step_id, x.attempt, x.call_index)
        )
        for s in ordered:
            lines.append(
                f"| {_cell(s.run_id)} | {_cell(s.module_id)} | {_cell(s.step_id)} | {s.attempt} | "
                f"{s.call_index} | {_money(s.settled_usd)} | {_cell(s.by)} | {s.date} | "
                f"{_cell(s.source)} |"
            )
        lines += ["", "| Account | Spend after settlements |", "| --- | --- |"]
        lines += [
            f"| {account} | {_money(account_spend(runs, account, settlements))} |"
            for account in ACCOUNTS
        ]
        lines.append("")
    return lines


_STAGE_RANK = {"pilot": 0, "repair": 1, "comparison": 2}


def _recency(run_id: str) -> tuple[int, int, str]:
    """Later stage, then higher run number, is more recent (run ids are ``<stage>-...-<n>``)."""
    number = re.search(r"-(\d+)$", run_id)
    return (
        _STAGE_RANK.get(run_id.split("-", 1)[0], -1),
        int(number.group(1)) if number else 0,
        run_id,
    )


def _latest(scores: Sequence[PathwayScore]) -> tuple[PathwayScore, ...]:
    """One score per (pathway, configuration): the most recent run, a rerun superseding."""
    best: dict[tuple[str, str], PathwayScore] = {}
    for score in scores:
        key = (score.pathway, score.config_id)
        if key not in best or _recency(score.run_id) > _recency(best[key].run_id):
            best[key] = score
    return tuple(sorted(best.values(), key=lambda x: x.run_id))


def _check_scores_match(
    scores: Sequence[PathwayScore], runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]]
) -> None:
    """Scores written before a run folder changed or went away are stale: name the run."""
    by_run = {meta.run_id: meta for meta, _ in runs}
    for score in scores:
        meta = by_run.get(score.run_id)
        if meta is None or (meta.config_id, meta.pathway, meta.case_id) != (
            score.config_id,
            score.pathway,
            score.case_id,
        ):
            raise DriverError(
                f"{SCORES_FILE} does not match the run folders (run {score.run_id}); "
                "run the score command again"
            )
        if score.pathway not in CASES:
            raise DriverError(f"run {score.run_id}: pathway {score.pathway} is not a golden")


def report_out(settings: Settings) -> Path:
    """Write ``report.md`` from ``scores.json`` (the latest run per pathway and configuration),
    the run folders and ``faults.jsonl``. The stopped configurations are derived from the runs
    and settlements as they are now; only a skipped distressed run, which cannot be derived, is
    taken from the last stage command."""
    scores_path = settings.out / SCORES_FILE
    if not scores_path.is_file():
        raise DriverError(f"no {SCORES_FILE} under {settings.out}: run the score command first")
    try:
        scores = _Scores.model_validate_json(scores_path.read_bytes()).scores
    except ValidationError as error:
        raise _invalid(SCORES_FILE, error) from None
    runs = load_runs(settings.out)
    everywhere = load_runs(settings.runs_root)
    settlements = load_all_settlements(settings.runs_root, settings.out)
    latest = _latest(scores)
    _check_scores_match(latest, runs)
    try:
        faults = read_faults(settings.out / FAULTS_FILE)
    except ValueError as error:  # the fault journal's one refusal: an unparsable record
        raise DriverError(f"{FAULTS_FILE}: {error}") from None
    text = render_report(latest, runs, faults)
    skipped = {k: v for k, v in _read_exhausted(settings.out).items() if k not in CONFIGS}
    stopped = {**skipped, **current_stops(everywhere, settlements)}
    notes = _notes(stopped, settlements, everywhere)
    notes += ["## Runs root", "", f"Runs root: {settings.runs_root.resolve()}", ""]
    text += "\n" + "\n".join(notes)
    path = settings.out / REPORT_FILE
    path.write_text(text, encoding="utf-8")
    return path


# ------------------------------------------------------------------ command line


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m deploy_workflow.model_testing",
        description="Plan, run, score and report model-testing runs (offline unless --live).",
    )
    parser.add_argument("command", choices=("pilot", "repair", "comparison", "score", "report"))
    parser.add_argument("--out", type=Path, required=True, help="artifacts/model-testing/<run_id>/")
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=DEFAULT_RUNS_ROOT,
        help="every run directory under it counts toward the account caps; --out lies inside it",
    )
    parser.add_argument("--cases", type=Path, default=Path("cases/goldens"))
    parser.add_argument("--corpus", type=Path, default=Path("artifacts/public-corpus/v1"))
    parser.add_argument("--recordings", type=Path, help="offline: DIR/<config_id>/ per config")
    parser.add_argument("--live", action="store_true", help="paid provider calls; needs --ruling")
    parser.add_argument("--ruling", type=Path, help="docs/rulings/<file>.md lifting the pause")
    return parser


_STAGES: MappingABC[str, Stage] = MappingProxyType(
    {"pilot": "pilot", "repair": "repair", "comparison": "comparison"}
)


def _dispatch(args: argparse.Namespace) -> int:
    settings = Settings(
        out=args.out,
        cases=args.cases,
        corpus=args.corpus,
        recordings=args.recordings,
        live=args.live,
        ruling=args.ruling,
        runs_root=args.runs_root,
    )
    command: str = args.command
    if command in ("score", "report"):
        if settings.live or settings.ruling is not None or settings.recordings is not None:
            raise DriverError(f"{command} takes no --live, --ruling or --recordings")
        if command == "score":
            print(f"scores: {score_out(settings)}")
        else:
            print(f"report: {report_out(settings)}")
        return 0
    result = run_stage(_STAGES[command], settings)
    for outcome in result.outcomes:
        print(f"{outcome.run_id}: {outcome.outcome}")
    for key, why in sorted(result.stopped.items()):
        print(f"stopped {key}: {why}")
    print(f"scores: {score_out(settings)}")
    print(f"report: {report_out(settings)}")
    return 0


_REFUSALS = (
    DriverError,
    BudgetError,
    RunInputError,
    CaseError,
    MappingError,
    JournalError,
    ContextRefused,
    UndecodableHtml,
    RecordingError,
    LivePauseInForce,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Exit 0 on success, 2 on a refusal of the framework (message on stderr, no traceback).
    Any other exception is a defect and propagates."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_:  # argparse: 0 for --help, 2 for a bad command line
        code = exit_.code
        return code if isinstance(code, int) else (0 if code is None else 2)
    try:
        return _dispatch(args)
    except _REFUSALS as error:
        print(f"error: {KEY_PATTERN.sub('[redacted]', str(error))}", file=sys.stderr)
        return 2
