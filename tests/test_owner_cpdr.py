"""O7b-1c S2b: the CP-DR LOCAL closed run, through the public `OwnerWorkflow` API.

Answer key: `cases/cpdr-research-owner/expected.json` (frozen; read at test time, never edited).
One genuine run (CP-0 and CP-1 promoted, then the `brief` and `research` steps) is built once; the
tests compare what it left with the key:

- `#cases/positive/{cp_dr_head_status_expected,facts}` and the table order TDR.1-3 (the head);
- `#cases/positive/brief/template_file` and `#brief/{question_ids,kinds,receivers,focus_modules}`
  (`research/brief.json`, a defaults-only brief);
- `#cases/positive/dossier/{template_text,dossier_sha256_rule,head_hash_rule}` (`research/dossier.md`
  and the hashes `run.json` records);
- `#refusals/anchors/blocked_cp0` (a blocked CP-0 head), `#refusals/research/fence_terminator`.

S2c adds the remaining owner-level cases. The first fixture is slow (about two minutes); the tests
that follow it reuse its store.
"""

import ast
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cpdr_runs as runs
import pytest
from cpdr_s1_support import ResearchCase

from deploy_vii.contracts import validate_tables
from deploy_vii.execution import Execution, Head
from deploy_workflow import run_pathway as rp
from deploy_workflow.owner_workflow import OwnerRunReceipt, verify_owner_run_receipt
from deploy_workflow.owners import cpdr
from deploy_workflow.prompts import rules
from deploy_workflow.research import evidence
from deploy_workflow.research.contracts import CpDrNotAnchored
from deploy_workflow.research.intake import RefusedItem, write_rejected
from deploy_workflow.run_inputs import check_arguments
from deploy_workflow.workflow import WorkflowError

ROOT = Path(__file__).resolve().parents[1]
BRIEF_MARKER = "{{BRIEF_SHA256}}"
FACT_FIELDS = (
    "fact_id",
    "table_id",
    "row_id",
    "field",
    "label",
    "text",
    "amount",
    "status",
    "unit",
    "period",
)


@dataclass(frozen=True)
class Closed:
    root: Path
    store: Path
    receipt: Path

    def execution(self) -> Execution:
        return Execution(self.store)

    def head(self, module_id: str) -> Head:
        return next(h for h in self.execution().read().heads if h.module_id == module_id)


@pytest.fixture(scope="module")
def key() -> dict[str, Any]:
    expected: dict[str, Any] = runs.oracle()["expected"]
    return expected


@pytest.fixture(scope="module")
def closed(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    """The positive case, closed: CP-0, CP-1 and CP-DR settled, the receipt sealed."""
    root = tmp_path_factory.mktemp("cpdr-positive")
    store, receipt, _ = runs.cpdr_closed("positive", root)
    return Closed(root, store, receipt)


def sha(data: bytes | str) -> str:
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def brief_file(template: str, cp0: str, cp1: str) -> tuple[str, str]:
    """The key's brief file with the run-time markers substituted, and its brief_sha256, by the
    key's own rule (`brief/brief_sha256_rule`): the body without `brief_sha256`, sorted keys,
    compact separators, UTF-8, after the two result hashes are substituted."""
    text = template.replace("{{CP0_RESULT_SHA256}}", cp0).replace("{{CP1_RESULT_SHA256}}", cp1)
    body = json.loads(text)
    body.pop("brief_sha256")
    digest = sha(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return text.replace(BRIEF_MARKER, digest), digest


# --- the positive closed run --------------------------------------------------------------------


def test_closed_run_positive(closed: Closed, key: dict[str, Any]) -> None:
    """The head settles at the key's status with TDR.1-3 in order, its facts are the key's, the
    tables lay out over them, and the sealed receipt verifies from the store and the record."""
    want = key["cases"]["positive"]
    head = closed.head("CP-DR")
    assert head.status == want["cp_dr_head_status_expected"] == "restricted"
    module = closed.execution().head_module(head)
    assert [table.table_id for table in module.tables] == ["TDR.1", "TDR.2", "TDR.3"]
    validate_tables(module.tables, module.facts)
    by_id = {fact.fact_id: fact for fact in module.facts}
    assert sorted(by_id) == sorted(f["fact_id"] for f in want["facts"])
    for wanted in want["facts"]:
        fact = by_id[wanted["fact_id"]]
        got = {n: None if (v := getattr(fact, n)) is None else str(v) for n in FACT_FIELDS}
        assert got == {n: wanted.get(n) for n in FACT_FIELDS}, fact.fact_id
        assert fact.limitation == wanted.get("limitation"), fact.fact_id
    receipt = OwnerRunReceipt.model_validate_json(closed.receipt.read_bytes())
    verify_owner_run_receipt(closed.execution(), receipt)


def test_the_brief_file_is_the_key_template(closed: Closed, key: dict[str, Any]) -> None:
    template = key["cases"]["positive"]["brief"]["template_file"]
    want, digest = brief_file(
        template, closed.head("CP-0").result_sha256, closed.head("CP-1").result_sha256
    )
    written = (closed.root / "research" / "brief.json").read_bytes()
    assert written == want.encode("utf-8")
    assert json.loads(written)["brief_sha256"] == digest


def test_a_defaults_only_brief_gives_the_keys_eight_questions(
    closed: Closed, key: dict[str, Any]
) -> None:
    brief = json.loads((closed.root / "research" / "brief.json").read_text(encoding="utf-8"))
    questions = brief["questions"]
    wanted = key["brief"]
    assert [q["question_id"] for q in questions] == wanted["question_ids"]
    assert [q["kind"] for q in questions] == wanted["kinds"]
    assert {q["question_id"]: q["receivers"] for q in questions} == wanted["receivers"]
    assert {q["question_id"]: q["focus_module"] for q in questions} == wanted["focus_modules"]


def test_the_dossier_is_the_key_template_and_its_hashes_are_recorded(
    closed: Closed, key: dict[str, Any]
) -> None:
    """`dossier_sha256_rule` and `head_hash_rule`: the file is the template with the brief hash;
    the record holds the file's hash, the brief's hash and the head's own `result_sha256`, which is
    not the dossier's."""
    research = closed.root / "research"
    record = rp.write_dossier(closed.execution(), research)
    dossier = key["cases"]["positive"]["dossier"]
    template = key["cases"]["positive"]["brief"]["template_file"]
    _, digest = brief_file(
        template, closed.head("CP-0").result_sha256, closed.head("CP-1").result_sha256
    )
    text = dossier["template_text"].replace(BRIEF_MARKER, digest)
    written = (research / "dossier.md").read_bytes()
    assert written == text.encode("utf-8")
    assert record.dossier_sha256 == sha(text) == sha(written)
    assert record.brief_sha256 == digest
    assert record.head_sha256 == closed.head("CP-DR").result_sha256
    assert record.head_sha256 != record.dossier_sha256


def test_run_json_takes_the_three_hashes_from_the_record(
    closed: Closed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`run.json`'s `cp_dr_*` keys are the record's (the staged run is S1's case; the record is the
    closed run's)."""
    monkeypatch.setattr(evidence, "research_clock", lambda: datetime(2026, 11, 2, tzinfo=UTC))
    case = ResearchCase(tmp_path)
    checked = check_arguments(**case.arguments(tmp_path))
    record = rp.write_dossier(closed.execution(), closed.root / "research")
    keys = rp._cp_dr_keys(checked, record)
    assert keys["cp_dr_dossier_sha256"] == sha(
        (closed.root / "research" / "dossier.md").read_bytes()
    )
    assert keys["cp_dr_head_sha256"] == closed.head("CP-DR").result_sha256
    assert keys["cp_dr_brief_sha256"] == record.brief_sha256
    assert rp._cp_dr_keys(checked, None)["cp_dr_dossier_sha256"] is None


def test_the_delimiter_label_replaces_a_terminator_reason_in_the_dossier(
    closed: Closed, key: dict[str, Any], tmp_path: Path
) -> None:
    """A dossier over a fence-terminator refusal shows the key's label; `rejected.json` keeps the
    literal reason (`refusals/research/fence_terminator`)."""
    terminator = key["refusals"]["research"]["fence_terminator"]
    item = runs.oracle()["manifest"]["fence_terminator_item"]
    reason = f"evidence item {item['locator']} {terminator['reason_suffix']}"
    research = tmp_path / "research"
    shutil.copytree(closed.root / "research", research)
    refused = (
        *runs.refused_items(),
        RefusedItem(item["locator"], item["family"], None, reason),
    )
    write_rejected(research / evidence.REJECTED_FILE, refused)
    rp.write_dossier(closed.execution(), research)
    shown = (research / "dossier.md").read_text(encoding="utf-8")
    assert terminator["dossier_shown_reason"] in shown and reason not in shown
    assert reason in (research / evidence.REJECTED_FILE).read_text(encoding="utf-8")


def test_the_receipt_needs_the_evidence_record_and_names_it_when_it_is_gone(
    closed: Closed, tmp_path: Path
) -> None:
    """S1 review, item 14: the `ev-*` tool results take their retrieval times from
    `research/evidence.json`, which is outside the sealed store. Verification reads it; without it
    the verifier refuses with the named `identity_mismatch`, never skipping the `ev-*` calls."""
    moved = tmp_path / "run"
    shutil.copytree(closed.root, moved)
    shutil.rmtree(moved / "research")
    receipt = OwnerRunReceipt.model_validate_json((moved / "owner-receipt.json").read_bytes())
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        verify_owner_run_receipt(Execution(moved / "store"), receipt)


# --- anchors at begin (O7-R20) -------------------------------------------------------------------


def test_a_blocked_cp0_head_is_not_anchored_and_nothing_is_written(
    tmp_path: Path, key: dict[str, Any]
) -> None:
    """`refusals/anchors/blocked_cp0`: a CP-0 head blocked by two invalid reviews stops the walk
    before CP-DR is begun, with the key's reason; no `brief.json`, no CP-DR attempt."""
    refusal = key["refusals"]["anchors"]["blocked_cp0"]
    workflow, pack = runs.start("positive", tmp_path)
    review = json.loads(runs.cp0_text(pack, "positive"))
    review["pack_sha256"] = "0" * 64  # a review that does not bind the pack is invalid, twice
    payload = json.dumps(review)
    runs.read_cited(workflow, payload)
    assert workflow.submit_review(payload)["status"] == "invalid"
    runs.read_cited(workflow, payload)
    with pytest.raises(CpDrNotAnchored) as raised:
        workflow.submit_review(payload)
    assert str(raised.value) == refusal["reason"]
    assert refusal["research_brief_json_written"] is False
    assert not (tmp_path / "research" / "brief.json").exists()
    assert all(a.module_id != "CP-DR" for a in Execution(tmp_path / "store").read().attempts)


# --- the entry the prompt rules start from -------------------------------------------------------


def test_each_steps_rule_entry_is_the_validator_the_entry_validator_dispatches_to() -> None:
    """`prompts/rules.py` starts a CP-DR step's rule coverage at that step's validator (one
    `ENTRY_VALIDATOR` serves both steps); this is the guard that the declared entries are what
    `ENTRY_VALIDATOR` calls."""
    tree = ast.parse((ROOT / "src/deploy_workflow/owners/cpdr.py").read_text(encoding="utf-8"))
    entry = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "ENTRY_VALIDATOR"
    )
    called = {n.id for n in ast.walk(entry) if isinstance(n, ast.Name)}
    for step, name in (("brief", "_validate_brief"), ("research", "_validate_research")):
        assert rules.ENTRIES[step] == (rules.OWNERS + f"cpdr:{name}",)
        assert name in called
    assert cpdr.STEP_IDS == ("brief", "research")
