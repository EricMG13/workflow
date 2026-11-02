"""Run driver (Task 11): plans the (case, pathway, config) runs of a stage, drives O2
``run_pathway`` for each, scores the run directories with ``score_run`` and writes the report.

The framework never writes or edits ``run.json`` (C4): ``run_pathway`` creates it. Offline is the
default (``recorded_adapter``); a live run passes the ruling to ``live_adapter``, which owns the
R2 gate. The driver's own check of the ruling path is a pre-check for a clear message only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping as MappingABC
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, ROUND_UP, Context, Decimal, localcontext
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from deploy_vii.contracts import Contract, PathwayId
from deploy_workflow.model import adapter as adapter_module
from deploy_workflow.model.adapter import (
    LivePauseInForce,
    ModelAdapter,
    live_adapter,
    recorded_adapter,
)
from deploy_workflow.model.record import CallRecord
from deploy_workflow.model.redact import KEY_PATTERN
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.model_testing.budget import (
    AccountExhausted,
    Settlement,
    account_spend,
    load_settlements,
    require_budget,
)
from deploy_workflow.model_testing.cases import GoldenCase, load_case
from deploy_workflow.model_testing.configs import (
    ACCOUNTS,
    CASES,
    CONFIGS,
    OPUS_PATHWAYS,
    PILOT_PATHWAY,
)
from deploy_workflow.model_testing.faults import read_faults
from deploy_workflow.model_testing.mapping import Mapping, load_mapping
from deploy_workflow.model_testing.pathway import PathwayScore, receipt_refusals, score_run
from deploy_workflow.model_testing.records import RunMeta, read_run
from deploy_workflow.model_testing.report import render_report
from deploy_workflow.run_inputs import HTML_MEDIA, CaseSource, RunOutcome
from deploy_workflow.run_pathway import run_pathway

Stage = Literal["pilot", "repair", "comparison"]
PlannedRun = tuple[str, PathwayId, str]

SETTLEMENTS_FILE = "settlements.json"
SCORES_FILE = "scores.json"
REPORT_FILE = "report.md"
FAULTS_FILE = "faults.jsonl"
EXHAUSTED_FILE = "exhausted.json"

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
    if stage == "comparison":
        high = tuple((case, pathway, "sol-high") for pathway, case in CASES.items())
        opus = tuple((CASES[pathway], pathway, OPUS_CONFIG) for pathway in OPUS_PATHWAYS)
        return high + opus
    raise DriverError(f"unknown stage {stage!r}")


@dataclass(frozen=True)
class Settings:
    out: Path
    cases: Path
    corpus: Path
    recordings: Path | None = None
    live: bool = False
    ruling: Path | None = None


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
    if suffix == ".pdf":
        return "application/pdf"
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
    sources = _golden_sources(case_id, json.loads(golden_path.read_text(encoding="utf-8")), corpus)
    case = load_case(case_dir, corpus)
    return CaseInputs(case, load_mapping(case_dir / "mapping.json", case), sources)


# ------------------------------------------------------------------ run folders and budget


def _read_all(out: Path) -> list[tuple[Path, RunMeta, tuple[CallRecord, ...]]]:
    """Every run folder under ``out``. A folder without ``run.json`` is a crashed run whose
    spend cannot be counted (ledger ruling 2026-11-01): the command stops."""
    if not out.is_dir():
        return []
    found: list[tuple[Path, RunMeta, tuple[CallRecord, ...]]] = []
    for folder in sorted(p for p in out.iterdir() if p.is_dir()):
        if not (folder / "run.json").is_file():
            raise DriverError(
                f"run folder {folder.name} has no run.json: a crashed run, its spend cannot be "
                "counted; resume it or move it away"
            )
        meta, records = read_run(folder)
        found.append((folder, meta, records))
    return found


def load_runs(out: Path) -> list[tuple[RunMeta, tuple[CallRecord, ...]]]:
    return [(meta, records) for _, meta, records in _read_all(out)]


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


def _read_exhausted(out: Path) -> dict[str, str]:
    path = out / EXHAUSTED_FILE
    if not path.is_file():
        return {}
    return dict(_Exhausted.model_validate_json(path.read_bytes()).stopped)


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
            cap = require_budget(config_id, self.runs, needed, self.settlements)
            if cap <= 0:
                raise AccountExhausted(f"{config_id}: no usable credit left")
        except AccountExhausted as error:
            self.stopped[key] = str(error)
            return
        run_id = f"{self.stage}-{config_id}-{pathway}"
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
        self.runs = load_runs(self.settings.out)

    def distressed_on_opus(self) -> None:
        """After the five Opus pathways: distressed_restructuring only if the account's cap
        covers its measured estimate."""
        estimate = distressed_opus_estimate(self.runs, self.settlements)
        if estimate is None or OPUS_CONFIG in self.stopped:
            return
        self.run(
            CASES[DISTRESSED_PATHWAY],
            DISTRESSED_PATHWAY,
            OPUS_CONFIG,
            needed=estimate,
            stop_key=f"{OPUS_CONFIG} ({DISTRESSED_PATHWAY})",
        )


def _record_stopped(out: Path, stopped: MappingABC[str, str]) -> None:
    if not stopped:
        return
    merged = {**_read_exhausted(out), **stopped}
    body = _Exhausted(schema_version="driver-exhausted/1", stopped=merged)
    (out / EXHAUSTED_FILE).write_text(body.model_dump_json(indent=2) + "\n", encoding="utf-8")


def run_stage(stage: Stage, settings: Settings) -> StageResult:
    """Run every planned run of a stage. Everything that can be refused is refused before the
    first run: the arguments, a crashed run folder, the settlements, the cases and their sources,
    and each configuration's adapter (the live gate included)."""
    check_settings(settings)
    planned = plan_runs(stage)
    runs = load_runs(settings.out)
    settlements = load_settlements(settings.out / SETTLEMENTS_FILE)
    case_ids = {case for case, _, _ in planned}
    if stage == "comparison":
        case_ids.add(CASES[DISTRESSED_PATHWAY])
    inputs = {c: load_inputs(c, settings.cases, settings.corpus) for c in sorted(case_ids)}
    adapters: dict[str, ModelAdapter] = {}
    for _, _, config_id in planned:
        if config_id not in adapters:
            adapters[config_id] = _adapter(settings, _spec(config_id))
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
        scores.append(
            score_run(folder, scored.case, scored.mapping, refusals=receipt_refusals(folder))
        )
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
            "| Run | Call | Settled | By | Date | Source |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for s in sorted(settlements, key=lambda x: (x.run_id, x.call_index)):
            lines.append(
                f"| {_cell(s.run_id)} | {s.call_index} | {_money(s.settled_usd)} | "
                f"{_cell(s.by)} | {s.date} | {_cell(s.source)} |"
            )
        lines += ["", "| Account | Spend after settlements |", "| --- | --- |"]
        lines += [
            f"| {account} | {_money(account_spend(runs, account, settlements))} |"
            for account in ACCOUNTS
        ]
        lines.append("")
    return lines


def report_out(settings: Settings) -> Path:
    """Write ``report.md`` from ``scores.json``, the run folders and ``faults.jsonl``, with the
    stopped configurations and settled charges the driver recorded."""
    scores_path = settings.out / SCORES_FILE
    if not scores_path.is_file():
        raise DriverError(f"no {SCORES_FILE} under {settings.out}: run the score command first")
    scores = _Scores.model_validate_json(scores_path.read_bytes()).scores
    runs = load_runs(settings.out)
    settlements = load_settlements(settings.out / SETTLEMENTS_FILE)
    text = render_report(scores, runs, read_faults(settings.out / FAULTS_FILE))
    notes = _notes(_read_exhausted(settings.out), settlements, runs)
    if notes:
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


def main(argv: Sequence[str] | None = None) -> int:
    """Exit 0 on success, 2 on a refused argument or input (message on stderr, no traceback)."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_:  # argparse: 0 for --help, 2 for a bad command line
        code = exit_.code
        return code if isinstance(code, int) else (0 if code is None else 2)
    try:
        return _dispatch(args)
    except (ValueError, LivePauseInForce) as error:
        print(f"error: {KEY_PATTERN.sub('[redacted]', str(error))}", file=sys.stderr)
        return 2
