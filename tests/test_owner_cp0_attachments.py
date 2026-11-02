"""Phase 5 Task 3: the CP-0 attachments precheck, a submit and replay gate (`_PRECHECKS["CP-0"]`).

Every expectation comes from the frozen oracle `cases/context-attachments-owner/` (expected.json,
submissions.json, manifest.json and the context files), never from the code under test. The 15
oracle cases are checked on the gate itself (`precheck`); the four that the oracle sends through
`submit_review` (abs-refused, abs-gap-ok, legal-exec-missing, mismatch) are also driven through the
real `OwnerWorkflow`, whose refusal writes no journal step and consumes no attempt. The verifier
recomputes the gate: with the gate switched off while a run is built, or while it is verified, the
receipt fails (plan RED L3).
"""

import hashlib
import importlib
import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from deploy_vii.contracts import Run, Source, Span
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow import owner_workflow as owner
from deploy_workflow.owners import cp0_attachments
from deploy_workflow.workflow import WorkflowError

s1a: Any = importlib.import_module("s1a_runs")

ROOT = Path(__file__).parents[1]
CASE = ROOT / "cases" / "context-attachments-owner"
MANIFEST = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
SUBMISSIONS = json.loads((CASE / "submissions.json").read_text(encoding="utf-8"))
EXPECTED = json.loads((CASE / "expected.json").read_text(encoding="utf-8"))
FINANCIAL = json.loads((ROOT / "cases/financial/manifest.json").read_text(encoding="utf-8"))
LEGAL = json.loads((ROOT / "cases/legal/manifest.json").read_text(encoding="utf-8"))
PLACEHOLDER = SUBMISSIONS["run_time_bindings"]["pack_sha256"]
CASE_IDS = tuple(EXPECTED["cases"])
TEXTS = EXPECTED["texts"]


# --- the oracle packs and reviews ---------------------------------------------------------------


def _frozen_pages() -> dict[str, list[dict[str, str]]]:
    found = [*FINANCIAL["sources"], *(c["legal_source"] for c in LEGAL["cases"])]
    return {source["sha256"]: source["pages"] for source in found}


FROZEN_PAGES = _frozen_pages()
DRAFT_PAGES = (CASE / "legal-draft.txt").read_text(encoding="utf-8").split("\f")


def _source(item: dict[str, Any]) -> Source:
    """One manifest `pack_sources` entry as the pack holds it (manifest pack_rule)."""
    source_id = item["source_id"]
    if source_id == "context":
        request = SourceRequest(source_id="context", path=item["path"], media_type="text/plain")
        return prepare_source(request, (ROOT / item["path"]).read_bytes())
    if source_id == "bridge":
        request = SourceRequest(
            source_id="bridge", path=f"{CASE.relative_to(ROOT)}/bridge.txt", media_type="text/plain"
        )
        ready = item["status"] == "ready"
        return prepare_source(request, (CASE / "bridge.txt").read_bytes() if ready else None)
    if source_id == "legal-draft":
        spans = tuple(Span(locator=f"page:{n}", text=t) for n, t in enumerate(DRAFT_PAGES, 1))
    else:
        spans = tuple(
            Span(locator=p["locator"], text=p["text"]) for p in FROZEN_PAGES[item["sha256"]]
        )
    return Source(
        source_id=source_id,
        name=item["name"],
        status=item["status"],
        sha256=item["sha256"],
        spans=spans,
        extraction_status="complete",
        limitation=item["limitation"],
    )


def _pack(case_id: str) -> PreparedPack:
    entry = next(c for c in MANIFEST["cases"] if c["case_id"] == case_id)
    return PreparedPack(
        run=Run.model_validate_json(json.dumps(entry["run"])),
        sources=tuple(_source(item) for item in entry["pack_sources"]),
    )


def _review(case_id: str, pack: PreparedPack) -> str:
    text = json.dumps(SUBMISSIONS["cases"][case_id]["cp0_review"], ensure_ascii=False)
    return text.replace(PLACEHOLDER, pack.content_hash())


def _gate(pack: PreparedPack, stored: str) -> tuple[str, ...]:
    """The gate over a frozen pack; the gate reads the store only through `pack()`."""
    store = cast(Execution, SimpleNamespace(pack=lambda: pack))
    return cp0_attachments.precheck(store, None, stored)


# --- the oracle itself --------------------------------------------------------------------------


def test_the_oracle_files_are_the_frozen_bytes() -> None:
    """P5-P13: the context, bridge and draft files are not covered by `pins.py` patterns."""
    for rel, entry in MANIFEST["frozen_inputs"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == entry["sha256"], rel
    for name, digest in MANIFEST["files_sha256"].items():
        assert hashlib.sha256((CASE / name).read_bytes()).hexdigest() == digest, name


def test_the_fixed_ids_the_bound_and_the_texts_are_the_oracle_s() -> None:
    assert cp0_attachments.ATTACHMENT_IDS == EXPECTED["attachment_ids"]
    assert list(cp0_attachments.ATTACHMENT_IDS) == [
        "portfolio_workbook",
        "prior_case",
        "management_bridge",
    ]
    assert cp0_attachments.MAX_ISSUES == EXPECTED["max_issues"]
    for field, source_id in EXPECTED["attachment_ids"].items():
        want = TEXTS["absent_template"].replace("<field>", field).replace("<id>", source_id)
        assert cp0_attachments.absent_issue(field, source_id) == want
    assert cp0_attachments.LEGAL_EXECUTED_MISSING == TEXTS["legal_executed_missing"]
    assert cp0_attachments.LEGAL_DRAFT_MISSING == TEXTS["legal_draft_missing"]
    assert cp0_attachments.CONTEXT_REFUSED == TEXTS["context_refused_prefix"]
    assert cp0_attachments.GAP_MATCH.format(id="<id>") == TEXTS["gap_match_regex"]


# --- the gate against every frozen case ---------------------------------------------------------


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_the_gate_gives_the_frozen_issues_for_every_case(case_id: str) -> None:
    pack = _pack(case_id)
    assert list(_gate(pack, _review(case_id, pack))) == EXPECTED["cases"][case_id]["P"]["issues"]


def test_a_refusal_lists_the_fields_in_the_frozen_order() -> None:
    case = EXPECTED["cases"]["abs-refused"]["P"]
    pack = _pack("abs-refused")
    issues = _gate(pack, _review("abs-refused", pack))
    assert len(issues) == case["count"] == 3
    assert [i.split(":")[0] for i in issues] == [
        "attachments.portfolio_workbook",
        "attachments.prior_case",
        "attachments.management_bridge",
    ]


def test_text_that_is_not_a_review_gets_no_issue_from_this_gate() -> None:
    pack = _pack("abs-refused")
    for stored in ("not json", "[1]", "{}", '{"schema_version": "readiness-review/1"}'):
        assert _gate(pack, stored) == ()


def test_a_gap_must_be_a_source_gap_naming_the_id_as_a_whole_token() -> None:
    pack = _pack("abs-refused")
    base = json.loads(_review("abs-gap-ok", _pack("abs-gap-ok")))
    template = base["gaps"][0]

    def with_gaps(*gaps: tuple[str, str]) -> str:
        review = dict(base, pack_sha256=pack.content_hash())
        review["gaps"] = [
            dict(template, gap_id=f"g-{n}", kind=kind, description=text)
            for n, (kind, text) in enumerate(gaps)
        ]
        return json.dumps(review)

    every = ("source", "portfolio, prior_case and bridge are not supplied")
    assert _gate(pack, with_gaps(every)) == ()
    # a different kind, or the id only inside a longer token, names nothing
    assert len(_gate(pack, with_gaps(("scope", every[1])))) == 3
    longer = ("source", "xportfolio, prior_case_2 and bridge2 are not supplied")
    assert len(_gate(pack, with_gaps(longer))) == 3
    # the match is case-sensitive: upper or title case does not name the id
    cased = ("source", "PORTFOLIO, Prior_Case and BRIDGE are not supplied")
    assert len(_gate(pack, with_gaps(cased))) == 3
    only_one = ("source", "The bridge is not supplied")
    issues = _gate(pack, with_gaps(only_one))
    assert [i.split(":")[0] for i in issues] == [
        "attachments.portfolio_workbook",
        "attachments.prior_case",
    ]


def test_a_gap_naming_an_id_the_pack_holds_is_allowed() -> None:
    pack = _pack("abs-present")
    base = json.loads(_review("abs-present", pack))
    base["gaps"] = json.loads(_review("abs-gap-ok", _pack("abs-gap-ok")))["gaps"]
    assert _gate(pack, json.dumps(base)) == ()


# --- the legal rule, branch by branch (the frozen texts are the answer key) --------------------

LEGAL_EXECUTED = TEXTS["legal_executed_missing"]
LEGAL_DRAFT = TEXTS["legal_draft_missing"]


def _absent(field: str) -> str:
    return str(
        TEXTS["absent_template"]
        .replace("<field>", field)
        .replace("<id>", EXPECTED["attachment_ids"][field])
    )


def _edited(case_id: str, edit: Any) -> tuple[PreparedPack, str]:
    """`case_id`'s oracle pack and review text after `edit(review_dict)`."""
    pack = _pack(case_id)
    review = json.loads(_review(case_id, pack))
    edit(review)
    return pack, json.dumps(review, ensure_ascii=False)


def _assess(review: dict[str, Any], source_id: str, authority: str) -> None:
    for source in review["sources"]:
        if source["source_id"] == source_id:
            source["authority"] = authority


def test_a_filed_source_satisfies_a_declared_executed_rule() -> None:
    def filed_and_ungapped(review: dict[str, Any]) -> None:
        _assess(review, "legal-draft", "filed")
        review["gaps"] = []

    pack, text = _edited("draft-wrong-context", filed_and_ungapped)
    assert _gate(pack, text) == ()


def test_only_a_draft_assessed_does_not_satisfy_a_declared_executed_rule() -> None:
    pack, text = _edited("draft-wrong-context", lambda r: r.update(gaps=[]))
    assert list(_gate(pack, text)) == [LEGAL_EXECUTED]


@pytest.mark.parametrize("authority", ["executed", "filed"])
def test_a_declared_draft_rule_needs_a_draft_assessment(authority: str) -> None:
    pack, text = _edited("draft-ok", lambda r: _assess(r, "legal-draft", authority))
    assert list(_gate(pack, text)) == [LEGAL_DRAFT]


def test_an_executed_assessment_of_a_source_that_is_not_ready_does_not_count() -> None:
    pack = _pack("abs-refused")
    gone = [
        Source(source_id=s.source_id, name=s.name, status="missing", limitation="gone")
        if s.source_id == "legal-covenants"
        else s
        for s in pack.sources
    ]
    unready = PreparedPack(run=pack.run, sources=tuple(gone))
    issues = _gate(unready, _review("abs-refused", unready))
    assert list(issues) == [
        _absent("portfolio_workbook"),
        _absent("prior_case"),
        _absent("management_bridge"),
        LEGAL_EXECUTED,
    ]
    assert len(issues) == cp0_attachments.MAX_ISSUES


def test_a_legal_gap_of_another_kind_does_not_count() -> None:
    def scope_gap(review: dict[str, Any]) -> None:
        gap = json.loads(_review("legal-exec-missing-gap", _pack("legal-exec-missing-gap")))["gaps"]
        review["gaps"] = [{**gap[0], "kind": "scope"}]

    pack, text = _edited("legal-exec-missing", scope_gap)
    assert list(_gate(pack, text)) == [LEGAL_EXECUTED]


# --- a context with several problems refuses with one line per problem -------------------------


def test_a_context_with_several_problems_gives_one_refusal_line_each() -> None:
    pack = _pack("mismatch")
    renamed = pack.run.model_copy(update={"issuer_name": "Other Issuer plc"})
    pack = PreparedPack(run=renamed, sources=pack.sources)
    theirs = json.loads((CASE / "context-mismatch.json").read_text(encoding="utf-8"))
    prefix = TEXTS["context_refused_prefix"]
    want = [
        prefix
        + f"identity.issuer_name: context has {theirs['identity']['issuer_name']!r}"
        + " but the run has 'Other Issuer plc'",
        prefix + "run.as_of: context has '2026-01-11' but the run has '2026-01-10'",
    ]
    assert list(_gate(pack, _review("mismatch", pack))) == want


# --- the property: issues equal declared, absent and ungapped -----------------------------------

FIELDS = tuple(cp0_attachments.ATTACHMENT_IDS)
CONTEXT_ABS = json.loads((CASE / "context-abs.json").read_text(encoding="utf-8"))
ABS_BASE = _pack("abs-refused")
BASE_REVIEW = json.loads(_review("abs-refused", ABS_BASE))


def _context_source(declared: frozenset[str]) -> Source:
    document = json.loads(json.dumps(CONTEXT_ABS))
    for field in FIELDS:
        document["attachments"][field] = field in declared
    document["attachments"]["legal_documents"] = "none"
    raw = (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    return prepare_source(
        SourceRequest(source_id="context", path="c.json", media_type="text/plain"), raw
    )


def _text_source(source_id: str) -> Source:
    request = SourceRequest(source_id=source_id, path=f"{source_id}.txt", media_type="text/plain")
    return prepare_source(request, f"{source_id} attachment text\n".encode())


@settings(max_examples=60, deadline=None)
@given(
    declared=st.sets(st.sampled_from(FIELDS)),
    ready=st.sets(st.sampled_from(FIELDS)),
    gapped=st.sets(st.sampled_from(FIELDS)),
)
def test_issues_equal_declared_and_absent_and_ungapped(
    declared: set[str], ready: set[str], gapped: set[str]
) -> None:
    ids = cp0_attachments.ATTACHMENT_IDS
    frozen = tuple(s for s in ABS_BASE.sources if s.source_id != "context")
    pack = PreparedPack(
        run=ABS_BASE.run,
        sources=(
            *frozen,
            *(_text_source(ids[f]) for f in FIELDS if f in ready),
            _context_source(frozenset(declared)),
        ),
    )
    review = dict(BASE_REVIEW, pack_sha256=pack.content_hash())
    template = json.loads(_review("abs-gap-ok", _pack("abs-gap-ok")))["gaps"][0]
    review["gaps"] = [
        dict(template, gap_id=f"{ids[f]}-gap", description=f"Source '{ids[f]}' is not supplied")
        for f in FIELDS
        if f in gapped
    ]
    want = [f for f in FIELDS if f in declared and f not in ready and f not in gapped]
    issues = _gate(pack, json.dumps(review))
    assert len(issues) == len(want)
    assert [i.split(":")[0] for i in issues] == [f"attachments.{f}" for f in want]
    assert len(issues) <= cp0_attachments.MAX_ISSUES


# --- the gate inside the owner workflow: submit and replay --------------------------------------


@pytest.fixture
def cp0_only(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The plan ends after CP-0, so a run completes (and seals a receipt) without CP-1. The real
    CP-0 owner spec, gate and verifier run; only the plan is shortened."""
    monkeypatch.setattr(owner, "plan", lambda requested: ("CP-0",))
    yield


def _start(case_id: str, root: Path) -> tuple[Any, PreparedPack]:
    pack = _pack(case_id)
    workflow = owner.OwnerWorkflow.create(
        root / "store", pack, specs=owner.OWNER_SPECS, publication_directory=root / "model"
    )
    return workflow, pack


def _steps(workflow: Any) -> int:
    return sum(len(a.steps) + len(a.step_repairs) for a in workflow._store.read().attempts)


def _attempts(workflow: Any) -> list[Any]:
    return list(workflow._store.read().attempts)


def _with_gaps_of(case_id: str, gap_case: str) -> str:
    """`case_id`'s review (same pack) carrying `gap_case`'s gaps: refused-then-edited input."""
    pack = _pack(case_id)
    review = json.loads(_review(case_id, pack))
    review["gaps"] = SUBMISSIONS["cases"][gap_case]["cp0_review"]["gaps"]
    return json.dumps(review)


@pytest.mark.usefixtures("cp0_only")
@pytest.mark.parametrize("case_id", ["abs-refused", "legal-exec-missing", "mismatch"])
def test_submit_review_refuses_without_a_journal_step_or_an_attempt(
    case_id: str, tmp_path: Path
) -> None:
    want = EXPECTED["cases"][case_id]["P"]
    workflow, pack = _start(case_id, tmp_path)
    review = _review(case_id, pack)
    s1a.read_cited(workflow, review)
    before = (_steps(workflow), _attempts(workflow))
    outcome = workflow.submit_review(review)
    assert outcome["status"] == "refused"
    assert outcome["issues"] == want["issues"]
    assert want["journaled_steps"] == 0 and want["attempt_consumed"] is False
    assert (_steps(workflow), _attempts(workflow)) == before
    assert workflow.phase != "complete"


@pytest.mark.usefixtures("cp0_only")
def test_abs_gap_ok_is_accepted_and_the_receipt_verifies(tmp_path: Path) -> None:
    workflow, pack = _start("abs-gap-ok", tmp_path)
    review = _review("abs-gap-ok", pack)
    s1a.read_cited(workflow, review)
    assert workflow.submit_review(review)["status"] == "valid"
    assert EXPECTED["cases"]["abs-gap-ok"]["V"]["issues"] == []
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    owner.verify_owner_run_receipt(workflow._store, receipt)


@pytest.mark.usefixtures("cp0_only")
def test_a_refused_review_edited_to_carry_the_gaps_settles_on_the_same_ticket(
    tmp_path: Path,
) -> None:
    workflow, pack = _start("abs-refused", tmp_path)
    refused = _review("abs-refused", pack)
    s1a.read_cited(workflow, refused)
    assert workflow.submit_review(refused)["status"] == "refused"
    edited = _with_gaps_of("abs-refused", "abs-gap-ok")
    s1a.read_cited(workflow, edited)
    assert workflow.submit_review(edited)["status"] == "valid"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    owner.verify_owner_run_receipt(workflow._store, receipt)


@pytest.mark.usefixtures("cp0_only")
def test_the_verifier_runs_the_gate_on_a_run_built_without_the_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L3: the gate is off while the run is built (the declared-but-absent review settles), then
    on while the receipt is verified. The verifier must refuse the receipt by itself."""
    workflow, pack = _start("abs-refused", tmp_path)
    review = _review("abs-refused", pack)
    s1a.read_cited(workflow, review)
    with monkeypatch.context() as patch:
        patch.setitem(owner._PRECHECKS, "CP-0", lambda store, binding, stored: ())
        assert workflow.submit_review(review)["status"] == "valid"
        receipt = workflow.write_receipt(tmp_path / "receipt.json")
    with pytest.raises(WorkflowError):
        owner.verify_owner_run_receipt(workflow._store, receipt)


@pytest.mark.usefixtures("cp0_only")
def test_open_replays_the_gate_over_a_run_built_without_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replay in `OwnerWorkflow.open` recomputes the gate. With the gate off the run opens (the
    control); with it on, the same stored run is torn."""
    workflow, pack = _start("abs-refused", tmp_path)
    review = _review("abs-refused", pack)
    s1a.read_cited(workflow, review)
    with monkeypatch.context() as patch:
        patch.setitem(owner._PRECHECKS, "CP-0", lambda store, binding, stored: ())
        assert workflow.submit_review(review)["status"] == "valid"
        workflow.write_receipt(tmp_path / "receipt.json")
        owner.OwnerWorkflow.open(tmp_path / "store", publication_directory=tmp_path / "model")
    with pytest.raises(WorkflowError):
        owner.OwnerWorkflow.open(tmp_path / "store", publication_directory=tmp_path / "model")


@pytest.mark.usefixtures("cp0_only")
def test_the_verifier_runs_the_gate_on_a_refused_then_edited_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L3: the run is honest (refused, then edited); with the gate returning nothing at
    verification the refused record no longer reproduces and the receipt fails."""
    workflow, pack = _start("abs-refused", tmp_path)
    refused = _review("abs-refused", pack)
    s1a.read_cited(workflow, refused)
    assert workflow.submit_review(refused)["status"] == "refused"
    edited = _with_gaps_of("abs-refused", "abs-gap-ok")
    s1a.read_cited(workflow, edited)
    assert workflow.submit_review(edited)["status"] == "valid"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    with monkeypatch.context() as patch:
        patch.setitem(owner._PRECHECKS, "CP-0", lambda store, binding, stored: ())
        with pytest.raises(WorkflowError):
            owner.verify_owner_run_receipt(workflow._store, receipt)


def test_the_gate_is_registered_for_cp0_only_through_this_module() -> None:
    assert owner._PRECHECKS["CP-0"] is cp0_attachments.precheck
