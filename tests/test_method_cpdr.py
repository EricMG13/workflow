"""O7b-1c S5: the CP-DR method text, the binding labels and the D12 reuse records.

Every expected value is read from the frozen key cases/cpdr-research-owner/expected.json (version,
R7 table titles, the methodology.json chain) or recomputed from the file under test (sha256), or
read from git at the S5 base commit (the shipped slots).
"""

import hashlib
import importlib.util
import itertools
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from deploy_vii import registry
from deploy_vii.bindings import Binding
from deploy_vii.bindings.cpdr import CPDR
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.execution import CONTEXT_PRODUCERS
from deploy_workflow.research.contracts import METHOD_VERSION_CPDR
from deploy_workflow.research.steps import DEFAULT_QUESTIONS, QUESTION_ID_MAX

ROOT = Path(__file__).resolve().parents[1]
KEY: dict[str, Any] = json.loads(
    (ROOT / "cases" / "cpdr-research-owner" / "expected.json").read_text(encoding="utf-8")
)
PEERS: dict[str, Any] = json.loads(
    (ROOT / "cases" / "cpdr-peers-owner" / "expected.json").read_text(encoding="utf-8")
)
SIX = ("TDR.1", "TDR.2", "TDR.3", "TDR.4", "TDR.5", "TDR.6")
METHOD_MD = ROOT / "src" / "deploy_vii" / "methods" / "cpdr.md"
BINDINGS_PY = ROOT / "src" / "deploy_vii" / "bindings" / "cpdr.py"
METHODOLOGY = ROOT / "src" / "deploy_vii" / "methodology.json"
EXECUTION_PY = ROOT / "src" / "deploy_vii" / "execution.py"
MANIFEST = ROOT / "docs" / "reuse" / "manifest.json"
BASE = "312b2351"  # HEAD when S5 was dispatched: the vii files as S5 found them
S5_COMMIT = "14fb0c328e028b30eb3ad330a2659ca933f6eb84"  # the S5 feat commit
REVIEW = ".superpowers/sdd/2026-10-31-part-b-o7/task-O7b-1c-S5-review.md"
VERSION_SHAPE = re.compile(r"cp-dr/\d{4}-\d{2}-\d{2}")
TEXT = METHOD_MD.read_text(encoding="utf-8")
LINES = TEXT.splitlines()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lines_with(*needles: str) -> list[str]:
    return [line for line in LINES if all(needle in line for needle in needles)]


def _one_version(text: str, where: str) -> str:
    found = VERSION_SHAPE.findall(text)
    assert len(set(found)) == 1, f"{where} must name exactly one method version, found {found}"
    return str(found[0])


def test_version_is_read_identically() -> None:
    literal = KEY["registry_after_o7b1"]["version_literal_form"]
    assert KEY["registry_after_o7b1"]["version_read_from"] == [
        "the registry purpose",
        "methods/cpdr.md first line",
        "METHOD_VERSION_CPDR",
    ]
    purpose = next(r for r in registry.modules() if r.module_id == "CP-DR").purpose
    read = (
        _one_version(purpose, "the registry purpose"),
        _one_version(LINES[0], "methods/cpdr.md first line"),
        METHOD_VERSION_CPDR,
    )
    assert read == (literal, literal, literal)


def test_md_names_max_bytes_for_both_caps() -> None:
    per_item = _lines_with("MAX_BYTES", "per-item")
    converted = _lines_with("MAX_BYTES", "converted text")
    assert per_item and converted, "both caps must name MAX_BYTES"


def test_md_names_the_five_refused_locator_characters() -> None:
    refused = [line for line in _lines_with("locator") if "`?`" in line]
    assert refused, "the locator rule must list the refused characters"
    for char in "?=&%#":
        assert f"`{char}`" in refused[0], f"the locator rule must name {char}"


def test_md_question_id_bound_is_the_code_bound() -> None:
    bound = _lines_with("QUESTION_ID_MAX")
    assert bound, "the method must cite QUESTION_ID_MAX"
    found = re.findall(r"at most (\d+) characters", bound[0])
    assert found == [str(QUESTION_ID_MAX)]


def test_md_names_the_six_defaults_the_lineage_and_the_ceiling() -> None:
    for question in DEFAULT_QUESTIONS:
        assert f"`{question.question_id}`" in TEXT
    assert KEY["cp_dr_lineage"] == "LOCAL"
    assert _lines_with("Lineage", "LOCAL")
    assert re.search(r"`RESEARCH_READY`", TEXT)
    assert "never above" in TEXT


def _table_keys() -> dict[str, dict[str, Any]]:
    """TDR.1-3 from the research key, TDR.4-6 from the peers key (R7 titles, row headers, columns)."""
    return {
        **{n: KEY["cases"]["positive"]["tables"][n] for n in SIX[:3]},
        **{n: PEERS["tables"][n] for n in SIX[3:]},
    }


def test_md_table_titles_are_the_r7_titles() -> None:
    tables = _table_keys()
    for table_id in SIX:
        row = [line for line in LINES if line.startswith(f"| {table_id} |")]
        assert len(row) == 1, table_id
        cells = [c.strip() for c in row[0].strip("|").split("|")]
        assert cells[1] == tables[table_id]["title"]
        assert cells[2] == f"`{tables[table_id]['row_header']}`"
        for column in tables[table_id]["columns"]:
            assert f"`{column}`" in cells[3]
    for table_id in SIX[3:]:
        line = next(line for line in LINES if line.startswith(f"| {table_id} |"))
        assert line.strip("|").split("|")[-1].strip() == "Evidence"


def test_binding_labels_are_the_r7_titles() -> None:
    tables = _table_keys()
    labels = {b.fact_coord.table_id: b.label for b in CPDR.entries}
    assert labels == {n: tables[n]["title"] for n in SIX}


def test_bindings_cover_every_cpdr_table() -> None:
    """Row 21: every registered CP-DR table has one binding; the evidence/limitations split is
    `cpdr-peers-owner#bindings`; the frozen run's `#evidence_rail` (TDR.1-2) sits inside it."""
    row = next(r for r in registry.modules() if r.module_id == "CP-DR")
    assert {b.fact_coord.table_id for b in CPDR.entries} == set(row.table_ids)
    assert len(CPDR.entries) == len(row.table_ids)
    split = PEERS["bindings"]
    for block, wanted in (("evidence", split["evidence"]), ("limitations", split["limitations"])):
        assert [b.fact_coord.table_id for b in CPDR.entries if b.block_id == block] == wanted
    assert set(KEY["evidence_rail"]) <= set(split["evidence"])
    assert {b.fact_coord.module_id for b in CPDR.entries} == {"CP-DR"}


def _slots(entries: tuple[Binding, ...]) -> list[tuple[Any, ...]]:
    return [
        (b.fact_coord, b.block_id, b.cell_slot, b.unit_class, b.section, b.slot) for b in entries
    ]


def _base_bindings(tmp_path: Path) -> tuple[Binding, ...]:
    """The CP-DR entries as the file stood at BASE, imported from git (never restated)."""
    source = subprocess.run(
        ["git", "show", f"{BASE}:src/deploy_vii/bindings/cpdr.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    copy = tmp_path / "cpdr_at_base.py"
    copy.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("cpdr_at_base", copy)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    entries = module.CPDR.entries
    assert isinstance(entries, tuple)
    return entries


def test_shipped_maps_carry_cpdr_with_unchanged_slots(tmp_path: Path) -> None:
    """Six slots now: the three S5 slots equal the BASE file's entries verbatim, then the three
    peer-pack slots `cpdr-tdr-4..6` (O7d D1b)."""
    shipped = [m for m in SHIPPED_MAPS if m.module_id == "CP-DR"]
    assert len(shipped) == 1
    assert shipped[0] is CPDR
    base = _slots(_base_bindings(tmp_path))
    assert len(base) == 3
    slots = _slots(shipped[0].entries)
    assert len(slots) == 6
    assert slots[:3] == base
    assert [b.cell_slot for b in shipped[0].entries[3:]] == [f"cpdr-tdr-{n}" for n in (4, 5, 6)]
    assert [b.fact_coord.table_id for b in shipped[0].entries[3:]] == list(SIX[3:])
    assert len({b.cell_slot for b in shipped[0].entries}) == 6


def _git_sha(commit: str, destination: str) -> str:
    shown = subprocess.run(
        ["git", "show", f"{commit}:{destination}"], cwd=ROOT, check=True, capture_output=True
    ).stdout
    return hashlib.sha256(shown).hexdigest()


def _records(destination: str) -> list[dict[str, Any]]:
    patches = json.loads(MANIFEST.read_text(encoding="utf-8"))["post_import_patches"]
    return [r for r in patches if r["destination"] == destination]


@pytest.mark.parametrize(
    "destination, path",
    [
        ("src/deploy_vii/methods/cpdr.md", METHOD_MD),
        ("src/deploy_vii/bindings/cpdr.py", BINDINGS_PY),
    ],
)
def test_d12_record_carries_the_file_sha256(destination: str, path: Path) -> None:
    records = _records(destination)
    starts = [i for i, r in enumerate(records) if r["project_commit"] == S5_COMMIT]
    assert len(starts) == 1, f"no single S5 D12 record for {destination}"
    first = records[starts[0]]
    assert first["review"] == REVIEW
    assert first["prior_project_sha256"] == _git_sha(BASE, destination)
    chain = records[starts[0] :]
    for before, after in itertools.pairwise(chain):
        assert after["prior_project_sha256"] == before["sha256"], "the chain is broken"
    assert chain[-1]["sha256"] == _sha(path)
    for record in chain:
        assert re.fullmatch(r"[0-9a-f]{40}", record["project_commit"])
        assert record["reason"].strip()
        assert _git_sha(record["project_commit"], destination) == record["sha256"]


def test_d12_record_for_execution_py() -> None:
    """O7c C1 (B31a): the last `execution.py` record is chained after the previous one, names the
    commit that holds the file at its `sha256`, and carries the file's current bytes."""
    records = _records("src/deploy_vii/execution.py")
    previous, last = records[-2], records[-1]
    assert last["prior_project_sha256"] == previous["sha256"]
    assert last["imported_sha256"] == previous["imported_sha256"]
    assert last["sha256"] == _sha(EXECUTION_PY)
    assert re.fullmatch(r"[0-9a-f]{40}", last["project_commit"])
    assert _git_sha(last["project_commit"], "src/deploy_vii/execution.py") == last["sha256"]
    assert "O7c C1" in last["reason"] and "O7-R47" in last["reason"]
    assert last["review"] == "work/context-plan/reviews/o7c-c1-review.md"
    wanted = {k: tuple(v) for k, v in KEY["consumers"]["context_producers"].items()}
    assert {k: v for k, v in CONTEXT_PRODUCERS.items() if k != "CP-1A"} == wanted
    assert CONTEXT_PRODUCERS["CP-1A"] == ("CP-1",)


S3_METHODOLOGY_SHA = "e0255a7b0ecb5993e1ebc4f1aef11c59f2555d983d2c7c18b16d79fcb91d606f"
D0B_COMMIT = "cffca98b7217f006e0ee60fa8213d17dcf98aaee"
D0B_REVIEW = ".superpowers/sdd/2026-10-31-part-b-o7/task-O7d-D0b-review.md"


def test_methodology_chain_runs_7d164d11_to_the_current_file() -> None:
    """7d164d11 -> the 8b19c74b record (e0255a7b) -> the D0b record (O7-R59) -> the current file."""
    before = KEY["registry_after_o7b1"]["today_before_change"]["methodology_sha256"]
    records = _records("src/deploy_vii/methodology.json")
    p7r4 = [r for r in records if r["project_commit"].startswith("9f32bbd3")]
    assert len(p7r4) == 1
    assert p7r4[0]["sha256"] == before, "the P7-R4 record is history: it keeps 7d164d11"
    s3 = [r for r in records if r["project_commit"].startswith("8b19c74b")]
    assert len(s3) == 1
    assert s3[0]["prior_project_sha256"] == before
    assert s3[0]["sha256"] == S3_METHODOLOGY_SHA
    assert s3[0]["imported_sha256"] == p7r4[0]["imported_sha256"]
    assert s3[0]["review"] == ".superpowers/sdd/2026-10-31-part-b-o7/task-O7b-1c-S3-review.md"
    d0b = [r for r in records if r["project_commit"] == D0B_COMMIT]
    assert len(d0b) == 1
    assert records[-1] is d0b[0], "the D0b record is the last methodology record"
    last = d0b[0]
    assert last["prior_project_sha256"] == S3_METHODOLOGY_SHA
    assert last["sha256"] == _sha(METHODOLOGY)
    assert _git_sha(last["project_commit"], "src/deploy_vii/methodology.json") == last["sha256"]
    assert last["imported_sha256"] == p7r4[0]["imported_sha256"]
    assert last["review"] == D0B_REVIEW
    assert "O7d D0b" in last["reason"] and "TDR.4" in last["reason"]
    for before_record, after_record in itertools.pairwise([p7r4[0], s3[0], last]):
        assert after_record["prior_project_sha256"] == before_record["sha256"], "chain broken"


def test_d12_records_for_the_vii_files_are_chained_and_cite_d1b() -> None:
    """O7d D1b (B31a): one new record per vii text file, chained after its previous record."""
    for destination, path in (
        ("src/deploy_vii/bindings/cpdr.py", BINDINGS_PY),
        ("src/deploy_vii/methods/cpdr.md", METHOD_MD),
    ):
        records = _records(destination)
        previous, last = records[-2], records[-1]
        assert last["prior_project_sha256"] == previous["sha256"], destination
        assert last["sha256"] == _sha(path), destination
        assert last["sha256"] != previous["sha256"], destination
        assert "O7d D1b" in last["reason"], destination
        assert last["review"] == D1B_REVIEW, destination


D1B_REVIEW = ".superpowers/sdd/2026-10-31-part-b-o7/task-O7d-D1b-review.md"


def test_method_states_the_peer_pack_rules_and_the_opt_in() -> None:
    """The method names the pack's rules (located figures only, no typed amount, no CP-1C
    ownership field, period end on or before the cutoff) and the Q4 opt-in clause."""
    lowered = TEXT.lower()
    assert "peer pack" in lowered
    for forbidden in PEERS["no_ownership_leak"]["forbidden_fields"]:
        assert f"`{forbidden}`" in TEXT, forbidden
    pack = [line for line in LINES if "peer pack" in line.lower()]
    joined = "\n".join(pack).lower()
    for phrase in (
        "located",
        "no amount typed by the model",
        "on or before the cutoff",
        "cp-1c owns",
    ):
        assert phrase in joined, phrase
    opt_in = [line for line in pack if "cp_dr_public" in line]
    assert opt_in, "the opt-in clause names peer_source cp_dr_public"
    assert "`CP-1C`" in opt_in[0] and "requested" in opt_in[0]
    assert PEERS["opt_in_matrix"]["rule"].split(" (")[0].startswith("peer_pack = cp_dr")
    assert "No module reads CP-DR output until O7d" in TEXT, "kept sentence"


def test_method_states_the_context_cutoff_and_the_web_retrieval_gate() -> None:
    """O7b-2 S5 (B1): the method carries the two frozen sentences and not the lines they replace."""
    key = json.loads(
        (ROOT / "cases" / "cpdr-web-retrieval" / "expected.json").read_text(encoding="utf-8")
    )
    sentences = key["method"]["sentences"]
    assert len(sentences) == 4
    for sentence in sentences:
        assert sentence in TEXT
    assert "The cutoff is the as-of date." not in TEXT
    assert "A URL row is refused while web retrieval is unavailable." not in TEXT
    assert "No web, provider or credential is used" not in TEXT
    assert "Each research item names a file, a family" not in TEXT
