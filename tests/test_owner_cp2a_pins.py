"""CP-2A honours the scenario shocks pinned in the context file (Phase 6 Task 3).

Expectations come from `cases/pins-context-owner/{expected,submissions}.json` (the CP-2A entry),
never from the code under test. Each case runs on a real `Execution` seeded as in
`tests/test_connect_cp2a.py`, over the base run's pack with the `prepare`d context source last.
Fast: no store promotion run (`tests/test_owner_cp2a.py` is the slow one and is not used here).
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2a as connect
from test_method_cp2a import (
    EXPECTED as BASE,
)
from test_method_cp2a import (
    MISSING,
    SUBMISSIONS,
    _edit,
    bind,
    bind_payload,
    cp1_facts,
    fig_ids,
    inputs_for,
)

from deploy_vii.contracts import Fact, Source, Span
from deploy_vii.execution import MAX_ISSUE_CHARS, Attempt, Execution, clipped
from deploy_vii.preparation import PreparedPack, prepare
from deploy_workflow.context import (
    CONTEXT_SOURCE_ID,
    ContextRefused,
    context_facts,
    load_context,
    preparation_request,
)
from deploy_workflow.owners import cp2a, pins
from deploy_workflow.owners.cp3d import PIN_LABEL_FORGED
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
    """The report equals the frozen `cases/cp2a-owner/expected.json` positive case, not a rerun."""
    store, pack, facts, finished = _journal(tmp_path, monkeypatch, case)
    assert finished.status == "finished" and finished.issues == ()
    report = _report(store, pack, facts, case, finished)
    want = BASE["cases"]["positive"]
    ids = fig_ids(facts)
    assert PINNED not in report.limitations
    assert list(report.limitations) == want["own_limitations"]
    assert [(c.claim_id, c.text) for c in report.claims] == [
        (c["claim_id"], bind(c["text"], ids)) for c in want["claims"]
    ]
    own = [f for f in report.facts if f.table_id != "cp1_references"]
    assert [f.fact_id for f in own] == [f["fact_id"] for f in want["facts"]]
    assert [(f.status, f.text) for f in own] == [
        (f["status"], f.get("text")) for f in want["facts"]
    ]
    assert [t.table_id for t in report.tables] == [
        *(t["table_id"] for t in want["tables"]),
        "cp1_references",
    ]
    for table, exp in zip(report.tables, want["tables"], strict=False):
        rows = [
            {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)} for r in table.rows
        ]
        assert rows == exp["rows"], exp["table_id"]


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


# -- the label on the no-ranked path and the refusal form (T3 adversary L1/L2) --------------------


def test_the_label_follows_the_no_first_break_limitation() -> None:
    """M04/M05: with no ranked break the limitations end NO_FIRST_BREAK; pinned, the label comes
    after it. Unpinned they end NO_FIRST_BREAK alone."""
    facts = cp1_facts("gap")
    q3_fcf = BASE["cases"]["gap"]["cp1_inputs"]["fcf"]["label"]
    edited = _edit(facts, q3_fcf, **MISSING, limitation="Fixture: FCF withheld")
    inputs = inputs_for("gap", SUBMISSIONS["gap"]["downside_pathway"], edited)
    assert cp2a.compute(inputs).limitations[-1] == cp2a.NO_FIRST_BREAK
    result = cp2a.compute(replace(inputs, pinned=True))
    assert result.ranking == ()
    assert result.limitations[-2:] == (cp2a.NO_FIRST_BREAK, PINNED)


def _refusing_pack(base: PreparedPack) -> PreparedPack:
    """The base pack with a context source that names three problems (two long, one run field)."""
    doc = json.loads((ORACLE / "context-distressed_restructuring.json").read_text())
    doc["identity"]["issuer_name"] = "X" * 400
    doc["identity"]["issuer_id"] = "someone-else"
    doc["run"]["pathway"] = "credit_snapshot"
    text = json.dumps(doc)
    source = Source(
        source_id=CONTEXT_SOURCE_ID,
        name="context.json",
        status="ready",
        sha256=hashlib.sha256(text.encode()).hexdigest(),
        media_type="text/plain",
        spans=(Span(locator="line:1", text=text),),
    )
    return PreparedPack(run=base.run, sources=(*base.sources, source))


def test_a_multi_problem_refusal_is_one_clipped_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M17/M18: the whole `ContextRefused` message is one `Context refused:` line, clipped."""
    store, _, facts = _seed(tmp_path, monkeypatch, None)
    upstream = cp2a.cp2a_upstream(store, store.begin(cp2a.MODULE_ID))
    pack = _refusing_pack(base_pack())
    got = cp2a.validate_downside(
        pack=pack, submission=_submission("no_context", facts), upstream=upstream
    )
    assert len(got) == 1, got
    assert got[0].startswith("Context refused: identity.issuer_name: ")
    assert "; identity.issuer_id: " in got[0]
    assert len(got[0]) <= MAX_ISSUE_CHARS
    with pytest.raises(ContextRefused) as caught:
        context_facts(pack)
    assert got[0] == clipped(("Context refused: ", str(caught.value)))
    assert len("Context refused: " + str(caught.value)) > MAX_ISSUE_CHARS  # the clip mattered


def test_only_context_refused_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """M14: any other `ValueError` from the reader escapes the validator."""
    store, pack, facts = _seed(tmp_path, monkeypatch, "context-distressed_restructuring.json")
    upstream = cp2a.cp2a_upstream(store, store.begin(cp2a.MODULE_ID))

    def boom(_: object) -> None:
        raise ValueError("reader bug")

    monkeypatch.setattr(pins, "context_facts", boom)
    with pytest.raises(ValueError, match="^reader bug$"):
        cp2a.validate_downside(pack=pack, submission=_submission("match", facts), upstream=upstream)


# --- a model-written copy of the pinned label (Phase 6 phase review M1) ---------------------------
def _forged_gap_payload(facts: tuple[Fact, ...], text: str) -> dict[str, Any]:
    payload = _payload("no_context", facts)
    gap = copy.deepcopy(payload["gaps"][0]) if payload.get("gaps") else {"severity": "high"}
    gap["gap"] = text
    payload["gaps"] = [*payload.get("gaps", []), gap]
    return payload


@pytest.mark.parametrize("variant", ["exact", "shouted", "spaced"])
def test_a_gap_cannot_carry_the_pinned_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    """On a no-pin report a gap spelling Python's pinned line is refused, never settled; since the
    CP-2A head is the only source of CP-4C's inherited limitations, it cannot reach CP-4C either."""
    store, _, facts = _seed(tmp_path, monkeypatch, None)
    line = pinned_line("CP-2A")
    text = {"exact": line, "shouted": line.upper(), "spaced": line.replace(" ", "  ")}[variant]
    payload = _forged_gap_payload(facts, text)
    attempt = store.begin(cp2a.MODULE_ID)
    cp2a.submit(store, attempt.ticket_id, cp2a.STEP_ID, json.dumps(payload), None)
    done = next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)
    index = len(payload["gaps"]) - 1
    assert f"gaps[{index}].gap: {PIN_LABEL_FORGED}" in done.issues
    assert not [h for h in store.read().heads if h.module_id == cp2a.MODULE_ID]


def test_a_gap_that_only_mentions_pins_is_not_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, facts = _seed(tmp_path, monkeypatch, None)
    payload = _forged_gap_payload(facts, "No pin was supplied for the shock sizes.")
    attempt = store.begin(cp2a.MODULE_ID)
    cp2a.submit(store, attempt.ticket_id, cp2a.STEP_ID, json.dumps(payload), None)
    done = next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)
    assert not [i for i in done.issues if PIN_LABEL_FORGED in i]


@pytest.mark.parametrize(
    ("metric", "level"), [("total_leverage", "0.0001"), ("interest_coverage", "999999")]
)
def test_a_threshold_label_cannot_carry_the_pinned_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, metric: str, level: str
) -> None:
    """A threshold label is interpolated into a Python limitation sentence (round 2 M1-b)."""
    store, _, facts = _seed(tmp_path, monkeypatch, None)
    payload = _payload("no_context", facts)
    first = copy.deepcopy(payload["thresholds"][0])
    first.update({"metric": metric, "level": level, "label": pinned_line("CP-2A")})
    payload["thresholds"] = [first, *payload["thresholds"]][:3]
    attempt = store.begin(cp2a.MODULE_ID)
    cp2a.submit(store, attempt.ticket_id, cp2a.STEP_ID, json.dumps(payload), None)
    done = next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)
    assert "thresholds[0].label: " + PIN_LABEL_FORGED in done.issues
    assert not [h for h in store.read().heads if h.module_id == cp2a.MODULE_ID]
