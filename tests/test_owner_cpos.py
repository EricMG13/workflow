"""CP-OS (report navigation proof) acceptance A1-A8 from `docs/CPOS-OWNER-LEASE.md`.

Every expected value is read from `cases/cpos-owner/expected.json` (the oracle) and the refusal
recipes from `cases/cpos-owner/submissions.json`; nothing is derived from the code under test.
The receipts are genuine closed S1a runs built through `tests/s1a_runs.py` (slow: three CP-1
promotions of 11-26 minutes each). Tampering recipes work on copies; no run is edited in place.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import s1a_runs as runs

from deploy_vii.execution import Execution
from deploy_workflow import owners
from deploy_workflow.owner_workflow import (
    OwnerRunReceipt,
    OwnerWorkflow,
    verify_owner_run_receipt,
)
from deploy_workflow.owners import cpos
from deploy_workflow.owners.cpos import NavigationProof, navigation, verify_navigation
from deploy_workflow.workflow import WorkflowError

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "cases/cpos-owner"
EXPECTED = json.loads((ORACLE / "expected.json").read_text())
SUBMISSIONS = json.loads((ORACLE / "submissions.json").read_text())
CASES = EXPECTED["cases"]
CASE_IDS = ["s1a_positive", "s1a_gap", "s1a_blocked_cp1a", "s1a_refused_cp1a"]
FIXED_ROUTES = {"front", "analysis", "FIT", "evidence", "limitations"}
BLOCKED_PAGE3 = [("business", "page:3")]
SCRIPT = re.compile(
    r'(<script id="report-data" type="application/json">)(.*?)(</script>)', re.DOTALL
)
assert owners.__name__ and cpos.__name__


@dataclass(frozen=True)
class Closed:
    key: str
    root: Path

    @property
    def store(self) -> Execution:
        return Execution(self.root / "store")

    @property
    def publication(self) -> Path:
        return self.root / "model"

    @property
    def receipt(self) -> OwnerRunReceipt:
        return OwnerRunReceipt.model_validate_json((self.root / "owner-receipt.json").read_bytes())


# --- genuine closed S1a runs (slow, built once per module) ------------------------------------


@pytest.fixture(scope="module")
def positive_template(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[OwnerWorkflow, Any, Path]:
    root = tmp_path_factory.mktemp("cpos-promoted-positive")
    workflow, pack = runs.promoted("positive", root)
    return workflow, pack, root


@pytest.fixture(scope="module")
def run_positive(
    positive_template: tuple[OwnerWorkflow, Any, Path], tmp_path_factory: pytest.TempPathFactory
) -> Closed:
    template, pack, _ = positive_template
    root = tmp_path_factory.mktemp("cpos-closed-positive")
    workflow = runs.clone_workflow(template, root)
    runs.close(workflow, pack, "positive", root / "owner-receipt.json")
    return Closed("s1a_positive", root)


@pytest.fixture(scope="module")
def run_gap(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    root = tmp_path_factory.mktemp("cpos-closed-gap")
    workflow, pack = runs.promoted("gap", root)
    runs.close(workflow, pack, "gap", root / "owner-receipt.json")
    return Closed("s1a_gap", root)


@pytest.fixture(scope="module")
def run_blocked(
    positive_template: tuple[OwnerWorkflow, Any, Path], tmp_path_factory: pytest.TempPathFactory
) -> Closed:
    """A3b: CP-1A invalid twice (a cited page unread) so blocked; CP-2 begins over the blocked
    CP-1A (restricted edge) and settles; CP-MODEL publishes."""
    template, pack, _ = positive_template
    root = tmp_path_factory.mktemp("cpos-closed-blocked")
    workflow = runs.clone_workflow(template, root)
    for _ in range(2):
        outcome = runs.drive_cp1a(workflow, pack, "positive", skip_reads=BLOCKED_PAGE3)
        assert outcome["status"] == "invalid"
    body = runs.read_cp2(workflow)
    outcome = runs.drive_cp2(workflow, "positive", body, text=runs.blocked_cp2_text())
    assert outcome["status"] == "valid", outcome["issues"]
    runs.finish(workflow, root / "owner-receipt.json")
    return Closed("s1a_blocked_cp1a", root)


@pytest.fixture(scope="module")
def run_refused(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    """A3c: CP-0 does not command CP-1A, so it is refused at begin and the walk stops; CP-MODEL
    publishes."""
    root = tmp_path_factory.mktemp("cpos-closed-refused")
    text = runs.cp0_cp1a_conditional("positive", runs.make_pack("positive"))
    workflow, _ = runs.promoted("positive", root, cp0_text=text)
    runs.finish(workflow, root / "owner-receipt.json")
    return Closed("s1a_refused_cp1a", root)


@pytest.fixture
def closed(request: pytest.FixtureRequest) -> Closed:
    result: Closed = request.getfixturevalue(request.param)
    return result


BY_CASE = {
    "s1a_positive": "run_positive",
    "s1a_gap": "run_gap",
    "s1a_blocked_cp1a": "run_blocked",
    "s1a_refused_cp1a": "run_refused",
}
ALL_CASES = pytest.mark.parametrize(
    "closed", [BY_CASE[k] for k in CASE_IDS], ids=CASE_IDS, indirect=True
)

_NAV: dict[str, tuple[bytes, NavigationProof]] = {}


def nav_of(run: Closed) -> tuple[bytes, NavigationProof]:
    if run.key not in _NAV:
        _NAV[run.key] = navigation(run.store, run.receipt, run.publication)
    return _NAV[run.key]


def check(run: Closed, page: bytes, proof: NavigationProof) -> None:
    verify_navigation(run.store, run.receipt, run.publication, page, proof)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def report_data(page: bytes) -> dict[str, Any]:
    match = SCRIPT.search(page.decode())
    assert match is not None
    data: dict[str, Any] = json.loads(match[2])
    return data


def edit_data(page: bytes, edit: Callable[[dict[str, Any]], None]) -> bytes:
    """The page with its report-data edited and re-serialised the way render.py does."""
    text = page.decode()
    match = SCRIPT.search(text)
    assert match is not None
    data = json.loads(match[2])
    edit(data)
    blob = json.dumps(data, ensure_ascii=True, allow_nan=False, separators=(",", ":")).replace(
        "<", "\\u003c"
    )
    return (text[: match.start(2)] + blob + text[match.end(2) :]).encode()


def refuses(run: Closed, page: bytes, proof: NavigationProof, prefix: str) -> None:
    with pytest.raises(ValueError) as caught:
        check(run, page, proof)
    assert str(caught.value).startswith(prefix), str(caught.value)


def rewritten(proof: NavigationProof, page: bytes) -> NavigationProof:
    return proof.model_copy(update={"page_sha256": sha(page)})


def tree(*paths: Path) -> dict[str, bytes]:
    return {
        str(p): p.read_bytes() for root in paths for p in sorted(root.rglob("*")) if p.is_file()
    }


# --- A1-A4: rows, tally, destinations, links, search --------------------------------------------


def tally_of(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The navigator's tally rules (app.js renderNavigation) over the proof rows, restated."""
    numbered = [r for r in rows if r["group"] == "numbered"]
    footer = [r for r in rows if r["group"] == "footer"]
    chips = ["All"]
    for glyph in ("lim", "pass", "blocked"):
        count = sum(r["glyph"] == glyph for r in numbered)
        if count or glyph != "blocked":
            chips.append(f"{count} {glyph}")
    unrun = sum(r["glyph"] == "unrun" for r in numbered)
    groups: dict[str, list[str]] = {}
    for row in footer:
        groups.setdefault(row["word"], []).append(row["module_id"])
    return {
        "label": f"Analysis · {len(numbered)}",
        "chips": chips,
        "numbered": len(numbered),
        "footer": len(footer),
        "unrun_line": f"Not run · {unrun}" if unrun else None,
        "footer_groups": [
            {"summary": f"{w} · {len(ids)}", "word": w, "module_ids": ids}
            for w, ids in groups.items()
        ],
    }


@ALL_CASES
def test_rows_destinations_and_tally_match_oracle(closed: Closed) -> None:
    exp = CASES[closed.key]
    page, proof = nav_of(closed)
    assert proof.schema_version == "cpos-navigation/1"
    assert proof.run.run_id == exp["run"]["run_id"]
    assert json.loads(proof.run.model_dump_json()) == json.loads(json.dumps(exp["run"]))
    assert {h.module_id: h.status for h in proof.heads} == exp["heads"]
    rows = [json.loads(r.model_dump_json()) for r in proof.rows]
    want = []
    for row in exp["rows"]:
        flat = {k: v for k, v in row.items() if k != "target"}
        t = row["target"]
        flat.update(
            page_title=t["page_title"],
            has_output=t["has_output"],
            empty_state=t["empty_state"],
            limitations_panel=t["limitations_panel"],
        )
        want.append(flat)
    assert rows == want
    assert [json.loads(d.model_dump_json()) for d in proof.destinations] == [
        {k: v for k, v in d.items() if k != "page_text"} for d in exp["destinations"]
    ]
    assert tally_of(rows) == exp["tally"]
    assert len(rows) == len(EXPECTED["registry"]) - exp["rejected_rows"] == 25
    assert proof.external_links == tuple(exp["external_links"])
    assert proof.page_sha256 == sha(page)
    assert proof.receipt_content_sha256 == closed.receipt.content_hash()
    assert proof.snapshot_sha256 == closed.receipt.snapshot_sha256
    assert proof.pack_sha256 == closed.receipt.pack_sha256
    assert proof.heads == closed.receipt.heads


@ALL_CASES
def test_row_link_facts_agree_with_the_real_head_views(closed: Closed) -> None:
    """`has_output` and `limitations_panel` are read from the real view modules, never from status;
    the oracle infers them from status and a disagreement returns to LEAD (lease A1)."""
    exp = CASES[closed.key]
    modules = {m.module_id: m for m in closed.store.view().modules}
    for row in exp["rows"]:
        module = modules[row["module_id"]]
        target = row["target"]
        assert target["has_output"] == bool(module.facts or module.claims or module.tables)
        assert target["limitations_panel"] == bool(module.limitations)


@ALL_CASES
def test_hash_links_are_in_the_oracle_superset_and_all_resolve(closed: Closed) -> None:
    exp = CASES[closed.key]
    page, _ = nav_of(closed)
    data = report_data(page)
    ids = {m["module_id"] for m in data["modules"]}
    routes = ids | {a for m in data["modules"] for a in m["aliases"]} | FIXED_ROUTES
    links = exp["hash_links"]
    assert ["#" + r["module_id"] for r in data["nav"]] == links["navigator_and_footer_rows"]
    drawn = {
        "#" + b["full_analysis_route"]
        for b in data["report"]["blocks"]
        if b.get("full_analysis_route")
    }
    assert drawn <= set(links["front_page_block_links"])
    oracle_routes = {b["block_id"]: b["full_analysis_route"] for b in exp["block_links"]}
    for block in data["report"]["blocks"]:
        if block.get("full_analysis_route"):
            assert block["full_analysis_route"] == oracle_routes[block["block_id"]]
    every = {*links["navigator_and_footer_rows"], *links["rail_destinations"], *drawn}
    every |= {"#" + m["module_id"] for m in data["modules"]}
    assert all(h[1:] in routes for h in every)
    assert links["shell_skip_link"] == ["#workbench"]
    assert b'href="#workbench"' in page


@ALL_CASES
def test_search_probes_match_oracle(closed: Closed) -> None:
    exp = CASES[closed.key]
    _, proof = nav_of(closed)
    for probe in exp["search_probes"]:
        needle = probe["filter"]
        hit = {
            r.module_id: r.group
            for r in proof.rows
            if needle in " ".join([r.module_id, r.title, *r.aliases, r.word]).lower()
        }
        assert [m for m, g in hit.items() if g == "numbered"] == probe["numbered_matches"]
        assert [m for m, g in hit.items() if g == "footer"] == probe["footer_matches"]


@ALL_CASES
def test_verify_navigation_accepts_the_genuine_page_and_proof(closed: Closed) -> None:
    page, proof = nav_of(closed)
    check(closed, page, proof)


def test_a2_gap_run_is_the_gap_run(run_gap: Closed) -> None:
    _, proof = nav_of(run_gap)
    assert proof.run.run_id == CASES["s1a_gap"]["run"]["run_id"]
    assert proof.run.run_id != CASES["s1a_positive"]["run"]["run_id"]


def test_a3_a4_derived_cp2_states_as_observed(run_blocked: Closed, run_refused: Closed) -> None:
    """The oracle's CP-2 `restricted` (blocked CP-1A) and `unrun` (refused CP-1A) are derived; the
    real receipts confirm them (ruling item 1.1)."""
    blocked = {h.module_id: h.status for h in run_blocked.receipt.heads}
    refused = {h.module_id: h.status for h in run_refused.receipt.heads}
    assert blocked == CASES["s1a_blocked_cp1a"]["heads"]
    assert refused == CASES["s1a_refused_cp1a"]["heads"]
    row = next(r for r in nav_of(run_refused)[1].rows if r.module_id == "CP-2")
    assert (row.glyph, row.word) == ("unrun", "Not run")


# --- A5: the verifier's own refusals ------------------------------------------------------------


def copy_run(run: Closed, destination: Path) -> Closed:
    destination.mkdir()
    for name in ("store", "model"):
        shutil.copytree(run.root / name, destination / name)
    shutil.copy(run.root / "owner-receipt.json", destination / "owner-receipt.json")
    return Closed(run.key, destination)


def seal_edited(receipt: OwnerRunReceipt) -> OwnerRunReceipt:
    return receipt.model_copy(update={"participant": receipt.participant + "-edited"})


def test_a5_seal_edit_refuses_identity_mismatch(run_positive: Closed) -> None:
    assert SUBMISSIONS["verifier_refusals"][0]["id"] == "seal_edit"
    with pytest.raises(WorkflowError) as caught:
        navigation(run_positive.store, seal_edited(run_positive.receipt), run_positive.publication)
    assert caught.value.code == "identity_mismatch"


def test_a5_head_status_forged_refuses_identity_mismatch(
    run_positive: Closed, tmp_path: Path
) -> None:
    copied = copy_run(run_positive, tmp_path / "copy")
    receipt = copied.receipt
    heads = tuple(
        h.model_copy(update={"status": "accepted"}) if h.module_id == "CP-1A" else h
        for h in receipt.heads
    )
    assert heads != receipt.heads
    forged = receipt.model_copy(update={"heads": heads})
    (copied.root / "store/owner-run-audit/receipt.sha256").write_text(forged.content_hash())
    with pytest.raises(WorkflowError) as caught:
        navigation(copied.store, forged, copied.publication)
    assert caught.value.code == "identity_mismatch"


def test_a5_foreign_store_refuses_stale_binding(run_positive: Closed, run_gap: Closed) -> None:
    with pytest.raises(WorkflowError) as caught:
        navigation(run_gap.store, run_positive.receipt, run_gap.publication)
    assert caught.value.code == "stale_binding"


def test_a5_refusal_comes_from_the_verifier_before_any_render(
    run_positive: Closed, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[str] = []
    real = verify_owner_run_receipt

    def spy(*args: Any, **kwargs: Any) -> None:
        called.append("verify")
        real(*args, **kwargs)

    def boom(*_: Any, **__: Any) -> str:
        raise AssertionError("rendered before the verifier refused")

    monkeypatch.setattr(cpos, "verify_owner_run_receipt", spy)
    monkeypatch.setattr(cpos, "render", boom)
    with pytest.raises(WorkflowError):
        navigation(run_positive.store, seal_edited(run_positive.receipt), run_positive.publication)
    assert called == ["verify"]


# --- A6: CP-OS refusals, in the stated order ----------------------------------------------------


def test_a6_refusal_ids_and_order_are_the_oracle_recipes() -> None:
    assert [r["id"] for r in SUBMISSIONS["cpos_refusals"]] == [
        "proof_of_other_receipt",
        "dangling_target",
        "forged_row",
        "page_bytes_edited",
        "receipt_hash_only",
        "forged_proof_row",
        "forged_proof_destination",
        "forged_external_link",
        "unverifiable_page_hash",
    ]
    assert SUBMISSIONS["order_of_cpos_checks"] == [
        "cpos_binding",
        "cpos_target_missing",
        "cpos_rows",
        "cpos_page",
        "cpos_proof",
    ]


def test_a6_proof_of_other_receipt(run_positive: Closed, run_gap: Closed) -> None:
    page, proof = nav_of(run_positive)
    nav_of(run_gap)  # the other receipt verifies too
    refuses(run_gap, page, proof, "cpos_binding")


def test_a6_receipt_hash_only(run_positive: Closed) -> None:
    page, proof = nav_of(run_positive)
    other = seal_edited(run_positive.receipt).content_hash()
    assert other != proof.receipt_content_sha256
    refuses(
        run_positive,
        page,
        proof.model_copy(update={"receipt_content_sha256": other}),
        "cpos_binding",
    )


def test_a6_unverifiable_page_hash(run_positive: Closed) -> None:
    page, proof = nav_of(run_positive)
    refuses(run_positive, page, proof.model_copy(update={"page_sha256": "0" * 64}), "cpos_binding")


def test_a6_dangling_target(run_positive: Closed) -> None:
    page, proof = nav_of(run_positive)

    def drop(data: dict[str, Any]) -> None:
        data["modules"] = [m for m in data["modules"] if m["module_id"] != "CP-2"]

    forged = edit_data(page, drop)
    refuses(run_positive, forged, rewritten(proof, forged), "cpos_target_missing")


@pytest.mark.parametrize("damage", ["no_tag", "no_close", "bad_json"])
def test_a6_report_data_that_cannot_be_extracted(run_positive: Closed, damage: str) -> None:
    page, proof = nav_of(run_positive)
    text = page.decode()
    if damage == "no_tag":
        forged = text.replace('id="report-data"', 'id="other-data"', 1)
    elif damage == "no_close":
        start = text.index('<script id="report-data"')
        end = text.index("</script>", start)
        forged = text[:end] + "<!--" + text[end + len("</script>") :]
    else:
        match = SCRIPT.search(text)
        assert match is not None
        forged = text[: match.start(2)] + "{not json" + text[match.end(2) :]
    forged_bytes = forged.encode()
    refuses(run_positive, forged_bytes, rewritten(proof, forged_bytes), "cpos_target_missing")


def test_a6_forged_row(run_positive: Closed) -> None:
    page, proof = nav_of(run_positive)

    def forge(data: dict[str, Any]) -> None:
        row = next(r for r in data["nav"] if r["module_id"] == "CP-1A")
        row["glyph"], row["word"] = "pass", "Pass"

    forged = edit_data(page, forge)
    refuses(run_positive, forged, rewritten(proof, forged), "cpos_rows")


def test_a6_page_bytes_edited(run_positive: Closed) -> None:
    page, proof = nav_of(run_positive)
    forged = page + b"\n"
    refuses(run_positive, forged, rewritten(proof, forged), "cpos_page")


def test_a6_forged_proof_row(run_blocked: Closed) -> None:
    page, proof = nav_of(run_blocked)
    row = next(r for r in proof.rows if r.module_id == "CP-1A")
    assert row.has_output is False
    rows = tuple(r.model_copy(update={"has_output": True}) if r is row else r for r in proof.rows)
    refuses(run_blocked, page, proof.model_copy(update={"rows": rows}), "cpos_rows")


def test_a6_forged_proof_destination(run_positive: Closed) -> None:
    page, proof = nav_of(run_positive)
    destinations = tuple(
        d.model_copy(update={"href": "#CP-MODEL"}) if d.key == "model" else d
        for d in proof.destinations
    )
    assert destinations != proof.destinations
    refuses(
        run_positive, page, proof.model_copy(update={"destinations": destinations}), "cpos_rows"
    )


@pytest.mark.parametrize("links", [("evil.json",), ()])
def test_a6_forged_external_link_is_refused_only_by_full_equality(
    run_positive: Closed, links: tuple[str, ...]
) -> None:
    page, proof = nav_of(run_positive)
    assert proof.external_links == ("calculation.json",)
    refuses(run_positive, page, proof.model_copy(update={"external_links": links}), "cpos_proof")


def test_a6_calculation_json_linked_but_not_in_the_receipt_files(
    run_positive: Closed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the receipt's `model.files` may back the link. The verifier is bypassed here because a
    receipt edited that way would never verify; this isolates CP-OS's own file check."""
    monkeypatch.setattr(cpos, "verify_owner_run_receipt", lambda *a, **k: None)
    receipt = run_positive.receipt
    assert receipt.model is not None and "calculation.json" in receipt.model.files
    forged = receipt.model_copy(update={"model": receipt.model.model_copy(update={"files": {}})})
    with pytest.raises(ValueError) as caught:
        navigation(run_positive.store, forged, run_positive.publication)
    assert str(caught.value).startswith("cpos_target_missing")


# --- A7: CP-OS is not an owner-run step ---------------------------------------------------------


def test_a7_cp_os_requested_refuses_at_create_and_writes_nothing(tmp_path: Path) -> None:
    pack = runs.make_pack("positive")
    requested = (*pack.run.requested_modules, "CP-OS")
    raw = json.loads(pack.model_dump_json())
    raw["run"]["requested_modules"] = list(requested)
    widened = type(pack).model_validate_json(json.dumps(raw))
    assert "CP-OS" in widened.run.requested_modules
    with pytest.raises(WorkflowError) as caught:
        OwnerWorkflow.create(tmp_path / "store", widened, publication_directory=tmp_path / "model")
    assert caught.value.code == "not_permitted"
    assert list(tmp_path.iterdir()) == []


# --- A8: read-only and deterministic ------------------------------------------------------------


def test_a8_navigation_and_a_refused_verify_leave_everything_unchanged(
    run_positive: Closed,
) -> None:
    receipt = run_positive.receipt
    before = (tree(run_positive.root), receipt.model_dump_json())
    page, proof = navigation(run_positive.store, receipt, run_positive.publication)
    with pytest.raises(ValueError):
        check(run_positive, page + b"\n", rewritten(proof, page + b"\n"))
    assert (tree(run_positive.root), receipt.model_dump_json()) == before
    assert (page, proof) == nav_of(run_positive)


def test_a8_other_hash_seed_gives_identical_page_and_proof(run_positive: Closed) -> None:
    page, proof = nav_of(run_positive)
    code = (
        "import sys, hashlib\n"
        "from pathlib import Path\n"
        "from deploy_vii.execution import Execution\n"
        "from deploy_workflow.owner_workflow import OwnerRunReceipt\n"
        "from deploy_workflow.owners.cpos import navigation\n"
        "root = Path(sys.argv[1])\n"
        "receipt = OwnerRunReceipt.model_validate_json((root / 'owner-receipt.json').read_bytes())\n"
        "page, proof = navigation(Execution(root / 'store'), receipt, root / 'model')\n"
        "print(hashlib.sha256(page).hexdigest())\n"
        "print(hashlib.sha256(proof.model_dump_json().encode()).hexdigest())\n"
    )
    env = {**os.environ, "PYTHONHASHSEED": "4242"}
    result = subprocess.run(
        [sys.executable, "-c", code, str(run_positive.root)],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.split() == [sha(page), sha(proof.model_dump_json().encode())]
