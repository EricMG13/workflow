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
from deploy_workflow.research.contracts import METHOD_VERSION_CPDR
from deploy_workflow.research.steps import DEFAULT_QUESTIONS, QUESTION_ID_MAX

ROOT = Path(__file__).resolve().parents[1]
KEY: dict[str, Any] = json.loads(
    (ROOT / "cases" / "cpdr-research-owner" / "expected.json").read_text(encoding="utf-8")
)
METHOD_MD = ROOT / "src" / "deploy_vii" / "methods" / "cpdr.md"
BINDINGS_PY = ROOT / "src" / "deploy_vii" / "bindings" / "cpdr.py"
METHODOLOGY = ROOT / "src" / "deploy_vii" / "methodology.json"
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


def test_md_table_titles_are_the_r7_titles() -> None:
    tables = KEY["cases"]["positive"]["tables"]
    for table_id in ("TDR.1", "TDR.2", "TDR.3"):
        row = [line for line in LINES if line.startswith(f"| {table_id} |")]
        assert row, table_id
        cells = [c.strip() for c in row[0].strip("|").split("|")]
        assert cells[1] == tables[table_id]["title"]
        assert cells[2] == f"`{tables[table_id]['row_header']}`"
        for column in tables[table_id]["columns"]:
            assert f"`{column}`" in cells[3]


def test_binding_labels_are_the_r7_titles() -> None:
    tables = KEY["cases"]["positive"]["tables"]
    labels = {b.fact_coord.table_id: b.label for b in CPDR.entries}
    assert labels == {n: tables[n]["title"] for n in ("TDR.1", "TDR.2", "TDR.3")}


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
    shipped = [m for m in SHIPPED_MAPS if m.module_id == "CP-DR"]
    assert len(shipped) == 1
    assert shipped[0] is CPDR
    assert _slots(shipped[0].entries) == _slots(_base_bindings(tmp_path))


def _git_sha(commit: str, destination: str) -> str:
    shown = subprocess.run(
        ["git", "show", f"{commit}:{destination}"], cwd=ROOT, check=True, capture_output=True
    ).stdout
    return hashlib.sha256(shown).hexdigest()


def _commit_exists(commit: str) -> bool:
    found = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    return found.returncode == 0


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
        if _commit_exists(record["project_commit"]):
            assert _git_sha(record["project_commit"], destination) == record["sha256"]


def test_methodology_chain_runs_7d164d11_to_the_current_file() -> None:
    before = KEY["registry_after_o7b1"]["today_before_change"]["methodology_sha256"]
    records = _records("src/deploy_vii/methodology.json")
    p7r4 = [r for r in records if r["project_commit"].startswith("9f32bbd3")]
    assert len(p7r4) == 1
    assert p7r4[0]["sha256"] == before, "the P7-R4 record is history: it keeps 7d164d11"
    last = records[-1]
    assert last["prior_project_sha256"] == before
    assert last["sha256"] == _sha(METHODOLOGY)
    assert last["project_commit"].startswith("8b19c74b")
    assert last["imported_sha256"] == p7r4[0]["imported_sha256"]
    assert last["review"] == ".superpowers/sdd/2026-10-31-part-b-o7/task-O7b-1c-S3-review.md"
