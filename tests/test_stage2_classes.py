"""The Stage 2 defect classes over every connected owner core (stage batch brief, "Last step").

Scope: each module of `owner_workflow.OWNER_SPECS` with a registered core (`_CORES`: `STEP_IDS`,
`SCHEMAS`, `submit`). CP-3, CP-4 and CP-5 are live-contract modules (`entry="model_payload"`)
with neither a core nor `SCHEMAS`; their step schemas are in the Q5 set of
`test_defect_classes_shared.py`.

- Round 1 Q5: `assert_hostile_refused` over each core's `SCHEMAS` rows.
- Round 3 item 2 and round 5 item 10: `model_text_failures` over the module's oracle positive
  payload, the literal its `test_connect_<cp>.py` settles. Each case runs on a fresh copy of a real
  `Execution` that the module's own connect test (or run driver) builds, through the core's real
  `submit` with `rules=None`, so no tool-use issue can stand in for a content refusal.
- Each module's verbatim set maps every path pattern to its sink, as `CP0_VERBATIM` does. No sink
  is `Claim.text` (`RunText`): a hostile value built as one raises in `submit`, which fails the case.

A module whose run raises, wedges or accepts a path outside its verbatim set is a finding. Its case
is a strict xfail that names the path, and the path stays out of the verbatim set.

The modules connected before the batch are here. The batch modules (CP-1D, CP-2G, CP-1C, CP-3C,
CP-2H, CP-4C) are in `test_stage2_classes_batch.py`, which imports this file's run and checks that
the two files cover every registered core once, so each file stays under about 60 s.
"""

import itertools
import json
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cp3d_runs
import cp8_runs
import defect_classes as dc
import pytest
import test_connect_cp2a as tc_cp2a
import test_connect_cp2d as tc_cp2d
import test_connect_cp2e as tc_cp2e
import test_connect_cp3d as tc_cp3d
import test_connect_cpdr as tc_cpdr
import test_connect_cpl10 as tc_cpl10
import test_method_cp2e
import test_method_cpdr
from pydantic import ValidationError

from deploy_vii.execution import Execution
from deploy_workflow import owner_workflow as ow

Built = tuple[Path, str]
"""The store directory with the module at its step, and the positive payload."""
RETAINED = "retained submission only (the journaled step payload); no table, claim or limitation"


@dataclass(frozen=True)
class Case:
    """One module: `build(root)` makes its store under `root`; `verbatim` maps each path
    pattern stored as plain text to its sink."""

    build: Callable[[Path], Built]
    verbatim: Mapping[dc.TextPath, str]


class _CoreRun:
    """A `ReviewRun` over a core's real `submit` on a real store. A submit after a finished
    attempt first begins the next one (the repair); the outcome is `valid` only when the attempt
    finished with no issue."""

    def __init__(self, store: Execution, module_id: str) -> None:
        self._store = store
        self._module_id = module_id

    def submit_review(self, payload: str) -> Mapping[str, Any]:
        core = ow._CORES[self._module_id]
        open_tickets = [
            a.ticket_id
            for a in self._store.read().attempts
            if a.module_id == self._module_id and a.status == "pending"
        ]
        ticket = open_tickets[-1] if open_tickets else self._store.begin(self._module_id).ticket_id
        journal = core.submit(self._store, ticket, core.STEP_IDS[0], payload, None).journal
        settled = journal.status == "finished" and not journal.issues
        return {"status": "valid" if settled else "invalid", "issues": list(journal.issues)}


def model_text_case(module_id: str, case: Case, tmp_path: Path) -> list[str]:
    """`model_text_failures` for one module: the store is built once and copied per case."""
    core = ow._CORES[module_id]
    (tmp_path / "template").mkdir()
    template, positive = case.build(tmp_path / "template")
    copies = itertools.count()

    def fresh() -> dc.ReviewRun:
        target = tmp_path / f"run{next(copies)}"
        shutil.copytree(template, target)
        return _CoreRun(Execution(target), module_id)

    schema = core.SCHEMAS[core.STEP_IDS[0]]
    assert dc.free_text_paths(positive, schema), f"{module_id} has free-text fields"
    return dc.model_text_failures(schema, positive, fresh, verbatim=frozenset(case.verbatim))


# --- Round 1 Q5 over every core ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("module_id", "step_id"),
    [(m, s) for m in sorted(ow._CORES) for s in sorted(ow._CORES[m].SCHEMAS)],
)
def test_hostile_stored_text_raises_only_value_errors(module_id: str, step_id: str) -> None:
    assert module_id in ow.OWNER_SPECS
    dc.assert_hostile_refused(ow._CORES[module_id].SCHEMAS[step_id])


# --- the stores and positive payloads, each from the module's own connect test or driver ----------


def _cpdr(root: Path) -> Built:
    """CP-0 settled through `submit_cp0_review`; the `partial` literal (answered and not found)."""
    store = tc_cpdr.settled_cp0(root)
    return store.directory, json.dumps(test_method_cpdr.SUBMISSIONS["cpdr"]["partial"])


def _cp3d(root: Path) -> Built:
    """CP-0 settled through the public workflow (`cp3d_runs.after_cp0`), CP-3D begun."""
    cp3d_runs.after_cp0("positive", root)
    return root / "store", json.dumps(tc_cp3d.POSITIVE)


def _cp2e(root: Path) -> Built:
    store, _ = tc_cp2e._ready_store(root)
    return store.directory, json.dumps(test_method_cp2e.SUBMISSIONS["positive"])


def _cp8(root: Path) -> Built:
    """CP-0 settled through the public workflow (`cp8_runs.start`), CP-8 begun."""
    _, pack = cp8_runs.start("positive", root)
    return root / "store", cp8_runs.literal("positive", "submission", pack)


def _cp2a(root: Path) -> Built:
    store, _, _ = tc_cp2a.seed(root)
    return store.directory, json.dumps(tc_cp2a._positive_payload())


def _cp2d(root: Path) -> Built:
    store, _ = tc_cp2d.make_upstream(root)
    return store.directory, tc_cp2d._literal("positive")


def _cpl10(root: Path) -> Built:
    """The connect test's `settled` store (CP-0 and CP-1 settled), from its own helpers."""
    pack = tc_cpl10._pack()
    store = Execution.create(root / "store", pack)
    commands = [tc_cpl10._t8("CP-1"), tc_cpl10._t8("CP-L10")]
    tc_cpl10._settle(store, "CP-0", commands, tc_cpl10.CP0_LIMIT)
    tc_cpl10._settle(store, "CP-1", tc_cpl10._cp1_with_real_citations(pack), tc_cpl10.CP1_LIMIT)
    return store.directory, tc_cpl10._positive()


# --- the verbatim sets (round 5 item 10), each pattern with its sink ------------------------------

# Every other free-text path of each positive payload journals an issue.
STORE_CASES: Mapping[str, Case] = {
    # `answer` is left out: it is `Claim.text` (the finding below).
    "CP-DR": Case(
        _cpdr,
        {
            ("gaps", "*", "questions", "*", "text"): (
                "TDR.2 question Fact.text; Module.limitations 'Unresolved: <text> <limitation>'"
            ),
            ("gaps", "*", "questions", "*", "limitation"): (
                "TDR.2 answer and evidence Fact.limitation; Module.limitations 'Unresolved: ...'"
            ),
        },
    ),
    # `summary.text` is left out: it is `Claim.text` (the finding below).
    "CP-3D": Case(
        _cp3d,
        {
            ("terms", "reference_rate", "absence", "reason"): "T3E.7 missing-inputs Fact.text",
            ("terms", "reference_rate", "absence", "follow_up"): RETAINED,
            ("recovery", "rationale"): RETAINED,
            ("technicals", "*", "text"): "T3E.6 assessment Fact.text (analyst_judgment)",
            ("technicals", "*", "limitation"): "Module.limitations (own) and T3E.9 Fact.text",
        },
    ),
    "CP-2E": Case(
        _cp2e,
        {
            ("fx", "operating_fx_absence", "reason"): "T2F.7 missing-inputs Fact.text",
            ("fx", "operating_fx_absence", "follow_up"): RETAINED,
            ("hedge_absence", "reason"): "T2F.7 missing-inputs Fact.text",
            ("hedge_absence", "follow_up"): RETAINED,
            ("shock_rationale",): "T2F.6 'Shock basis' Fact.text (analyst_judgment)",
            ("assessments", "*", "text"): "T2F.6 assessment Fact.text (analyst_judgment)",
            ("assessments", "*", "limitation"): RETAINED,
        },
    ),
    "CP-8": Case(_cp8, {}),
    "CP-2A": Case(_cp2a, {}),
    "CP-2D": Case(
        _cp2d,
        {
            ("minimum_cash", "rationale"): RETAINED,
            ("assessments", "*", "text"): RETAINED,
            ("assessments", "*", "credit_implication"): RETAINED,
        },
    ),
    "CP-L10": Case(
        _cpl10,
        {
            ("gaps", "*", "gap"): "Module.limitations 'Gap (<severity>): <gap>'",
            ("gaps", "*", "why_it_matters"): RETAINED,
            ("gaps", "*", "action"): RETAINED,
        },
    ),
}

FINDINGS: Mapping[str, str] = {
    "CP-DR": (
        "Finding: gaps.*.questions.*.answer is built as Claim.text (CPDR-ANS-<question_id>, "
        "RunText) without a RunText check; a hostile value raises pydantic ValidationError in "
        "cpdr.submit after the step is journaled, and the run is wedged (stale_binding)"
    ),
    "CP-3D": (
        "Finding: summary.text is built as Claim.text (CP-3D-VIEW-01, RunText) without a RunText "
        "check; a hostile value raises pydantic ValidationError in cp3d.submit after the step is "
        "journaled, and the run is wedged (stale_binding)"
    ),
}


def params(cases: Mapping[str, Case], findings: Mapping[str, str]) -> list[Any]:
    """One parameter per module; a module with a finding is a strict xfail on that raise."""
    return [
        pytest.param(
            m,
            marks=pytest.mark.xfail(strict=True, raises=ValidationError, reason=findings[m])
            if m in findings
            else (),
            id=m,
        )
        for m in cases
    ]


@pytest.mark.parametrize("module_id", params(STORE_CASES, FINDINGS))
def test_model_text_is_journaled_except_on_the_verbatim_paths(
    module_id: str, tmp_path: Path
) -> None:
    assert model_text_case(module_id, STORE_CASES[module_id], tmp_path) == []
