"""CP-2A honours the scenario shocks pinned in the context file (Phase 6 Task 3).

Expectations come from `cases/pins-context-owner/{expected,submissions}.json` (the CP-2A entry),
never from the code under test. Each case runs on a real `Execution` seeded as in
`tests/test_connect_cp2a.py`, over the base run's pack with the `prepare`d context source last.
Fast: no store promotion run (`tests/test_owner_cp2a.py` is the slow one and is not used here).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2a as connect
from test_method_cp2a import bind_payload, fig_ids

from deploy_vii.contracts import Fact
from deploy_vii.execution import Attempt, Execution
from deploy_vii.preparation import PreparedPack, prepare
from deploy_workflow.context import CONTEXT_SOURCE_ID, load_context, preparation_request
from deploy_workflow.owners import cp2a
from deploy_workflow.owners.pins import pinned_line

ORACLE = Path(__file__).resolve().parents[1] / "cases" / "pins-context-owner"
EXPECTED: dict[str, Any] = json.loads((ORACLE / "expected.json").read_text())["modules"]["CP-2A"]
CASES: dict[str, Any] = json.loads((ORACLE / "submissions.json").read_text())["modules"]["CP-2A"][
    "cases"
]
PINNED = pinned_line("CP-2A")
base_pack = connect._pack  # captured before any test patches it
REFUSED = ("differs", "differs_interest", "swapped", "one_scenario", "content_and_pin")


def _pack(tmp_path: Path, context: str | None) -> PreparedPack:
    """The base CP-2A run's pack with the prepared context source appended last."""
    base = base_pack()
    if context is None:
        return base
    raw = (ORACLE / context).read_bytes()
    request = preparation_request(
        load_context(raw), run_id=base.run.run_id, context_path="context.json", sources=()
    )
    (tmp_path / "root").mkdir()
    (tmp_path / "root" / "context.json").write_bytes(raw)
    prepared = prepare(request, tmp_path / "root", tmp_path / "pack")
    found = tuple(s for s in prepared.sources if s.source_id == CONTEXT_SOURCE_ID)
    assert len(found) == 1
    return PreparedPack(run=base.run, sources=(*base.sources, *found))


def _seed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, context: str | None
) -> tuple[Execution, PreparedPack, tuple[Fact, ...]]:
    pack = _pack(tmp_path, context)
    monkeypatch.setattr(connect, "_pack", lambda as_of=None: pack)
    return connect.seed(tmp_path)


def _payload(case: str, facts: tuple[Fact, ...]) -> dict[str, Any]:
    bound: dict[str, Any] = bind_payload(CASES[case]["payload"], fig_ids(facts))
    return bound


def _submission(case: str, facts: tuple[Fact, ...]) -> cp2a.DownsideSubmission:
    return cp2a.DownsideSubmission.model_validate_json(json.dumps(_payload(case, facts)))


def _journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> tuple[Execution, PreparedPack, tuple[Fact, ...], Any]:
    store, pack, facts = _seed(tmp_path, monkeypatch, CASES[case]["context"])
    attempt = store.begin(cp2a.MODULE_ID)
    cp2a.submit(store, attempt.ticket_id, cp2a.STEP_ID, json.dumps(_payload(case, facts)), None)
    finished = next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)
    return store, pack, facts, finished


@pytest.mark.parametrize("case", REFUSED)
def test_a_differing_pin_is_a_journaled_refusal_with_the_oracle_lines(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, _, finished = _journal(tmp_path, monkeypatch, case)
    assert finished.status == "finished"
    assert list(finished.issues) == EXPECTED["cases"][case]["issues"]
    assert finished.steps[0].status == "invalid"


@pytest.mark.parametrize("case", REFUSED)
def test_the_composer_gate_raises_on_the_same_lines(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, facts = _seed(tmp_path, monkeypatch, CASES[case]["context"])
    upstream = cp2a.cp2a_upstream(store, store.begin(cp2a.MODULE_ID))
    with pytest.raises(ValueError) as caught:
        cp2a.downside_report(pack=pack, submission=_submission(case, facts), upstream=upstream)
    assert str(caught.value) == "; ".join(EXPECTED["cases"][case]["issues"])


def test_the_base_period_issue_alone_still_carries_the_pin_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Decision 1: `validate` returns the base-period issue alone; the pin line follows it."""
    _, _, _, finished = _journal(tmp_path, monkeypatch, "content_and_pin")
    assert [i.split(":")[0] for i in finished.issues] == [
        "base_period",
        "assumptions.cp2a.scenarios[0].ebitda_decline_pct",
    ]


def test_a_stale_line_comes_before_the_pin_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, facts = _seed(tmp_path, monkeypatch, CASES["differs"]["context"])
    bound = store.begin(cp2a.MODULE_ID).inputs
    upstream = cp2a.Upstream(bound=bound, current="Required upstream is unrun", cp1=facts)
    issues = cp2a.validate_downside(
        pack=pack, submission=_submission("differs", facts), upstream=upstream
    )
    assert issues == (
        "Stale inputs: Required upstream is unrun",
        *EXPECTED["cases"]["differs"]["issues"],
    )


def _report(
    store: Execution, pack: PreparedPack, facts: tuple[Fact, ...], case: str, attempt: Attempt
) -> cp2a.DownsideReport:
    upstream = cp2a.cp2a_upstream(store, attempt)
    return cp2a.downside_report(pack=pack, submission=_submission(case, facts), upstream=upstream)


def test_spelling_the_pins_with_trailing_zeros_composes_and_labels_the_shocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, facts, finished = _journal(tmp_path, monkeypatch, "match")
    assert finished.status == "finished" and finished.issues == ()
    head = next(h for h in store.read().heads if h.module_id == cp2a.MODULE_ID)
    report = _report(store, pack, facts, "match", finished)
    own = EXPECTED["cases"]["match"]["own_limitations"]
    assert list(report.limitations) == own
    assert own[-1] == PINNED == EXPECTED["cases"]["match"]["pinned_line"]
    assert PINNED in store.head_module(head).limitations
    base = _report(store, base_pack(), facts, "no_context", finished)
    assert (report.facts, report.tables, report.claims) == (base.facts, base.tables, base.claims)


@pytest.mark.parametrize("case", ("no_pin", "no_context"))
def test_no_context_or_no_pin_equals_the_base_oracle(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, facts, finished = _journal(tmp_path, monkeypatch, case)
    assert finished.status == "finished" and finished.issues == ()
    report = _report(store, pack, facts, case, finished)
    assert PINNED not in report.limitations
    plain = _report(store, base_pack(), facts, "no_context", finished)
    assert (report.facts, report.tables, report.claims, report.limitations) == (
        plain.facts,
        plain.tables,
        plain.claims,
        plain.limitations,
    )


def test_a_context_that_differs_from_the_run_is_one_refusal_line_after_the_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P6-P3: only `ContextRefused` is caught; it becomes `Context refused: <message>`, with no
    pin lines, after the content issues."""
    store, pack, facts = _seed(tmp_path, monkeypatch, "context-credit_snapshot.json")
    upstream = cp2a.cp2a_upstream(store, store.begin(cp2a.MODULE_ID))
    refused = (
        "Context refused: run.pathway: context has 'credit_snapshot' but the run has "
        "'distressed_restructuring'"
    )
    positive = _submission("no_context", facts)
    assert cp2a.validate_downside(pack=pack, submission=positive, upstream=upstream) == (refused,)
    off_period = _submission("content_and_pin", facts)
    issues = cp2a.validate_downside(pack=pack, submission=off_period, upstream=upstream)
    assert issues == (EXPECTED["cases"]["content_and_pin"]["issues"][0], refused)
