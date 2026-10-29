"""Data-only checks for the CZR 2026 Q2 public case.

Verifies the owner citation keys and the document-derived value expectations
against the filed document text. No code in src/ is exercised.

Each value record is pinned to a cell of its key line (cell_index, 0 = label),
its period/basis is re-derived from the table header lines it cites, and those
header lines must be the nearest header block above the key line.
"""

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

CASE = Path(__file__).parents[1] / "cases/czr-2026q2-earnings-update"
MANIFEST = json.loads((CASE / "manifest.json").read_text())
QUALIFICATION = json.loads((CASE / "qualification.json").read_text())
EXPECTED = json.loads((CASE / "expected.json").read_text())

DOCS = {d["sha256"]: d for d in MANIFEST["documents"]}
EXPECTS = QUALIFICATION["cases"][0]["expects"]
HEADER_WINDOW = 30
NUMBER = re.compile(r"^\$?\(?\d[\d,]*(\.\d+)?\)?$")

# Vacuous-pass guard: an emptied oracle must fail, not parametrize to nothing.
assert EXPECTS, "qualification expects is empty"
assert EXPECTED["values"], "expected.json values is empty"
assert EXPECTED["prose_keys"], "expected.json prose_keys is empty"
assert EXPECTED["key_lines"], "expected.json key_lines is empty"


def _lines(sha):
    path = CASE / DOCS[sha]["path"]
    return [line.rstrip() for line in path.read_text().splitlines()]


def _iter_keys():
    for n, e in enumerate(EXPECTS):
        yield pytest.param(
            e["module_id"],
            e["document_sha256"],
            e["matched_text"],
            id=f"{n}-{e['module_id']}-primary",
        )
        for m, a in enumerate(e.get("alternatives", [])):
            yield pytest.param(
                e["module_id"],
                a["document_sha256"],
                a["matched_text"],
                id=f"{n}-{e['module_id']}-alt{m}",
            )


KEYS = list(_iter_keys())
PRIMARY = {(e["module_id"], e["document_sha256"], e["matched_text"]) for e in EXPECTS}
PROSE = {(p["module_id"], p["document_sha256"], p["sentence"]) for p in EXPECTED["prose_keys"]}


def _cells(line):
    return [c.strip() for c in line.split("|")]


def _parse(cell):
    """Parse a printed cell: parentheses negative, commas and a leading $ removed."""
    assert NUMBER.match(cell), f"not a numeric cell: {cell!r}"
    negative = "(" in cell
    number = Decimal(cell.replace("$", "").replace("(", "").replace(")", "").replace(",", ""))
    return -number if negative else number


def _numeric_indices(line):
    cells = _cells(line)
    numeric = [i for i in range(1, len(cells)) if NUMBER.match(cells[i])]
    percent = [i for i in range(1, len(cells)) if cells[i].endswith("%")]
    return numeric, percent


def _derive_columns(evidence):
    """Return [(period, basis)] per header data column (None period = percent column)."""
    units = next(e for e in evidence if "in millions" in e.lower())
    group = next(e for e in evidence if e is not units)
    unit_cells = _cells(units)[1:]
    if "Face Value" in unit_cells:
        dates = _cells(group)
        columns, seen, di = [], set(), 0
        for label in unit_cells:
            if label not in ("Face Value", "Book Value"):
                columns.append((None, None))
                continue
            if label in seen:
                di += 1
                seen = set()
            seen.add(label)
            month, day, year = re.match(r"(\w+) (\d+), (\d{4})", dates[di]).groups()
            iso = f"{year}-{ {'June': '06', 'December': '12'}[month] }-{int(day):02d}"
            columns.append((iso, label.split()[0].lower()))
        return columns
    groups = _cells(group)
    years = [c for c in unit_cells if c != "% Change"]
    per_group = len(years) // len(groups)
    columns, k = [], 0
    for cell in unit_cells:
        if cell == "% Change":
            columns.append((None, None))
            continue
        name = groups[k // per_group]
        year = cell
        if name.startswith("Three Months Ended June 30"):
            period = f"Q2 {year}"
        elif name.startswith("Six Months Ended June 30"):
            period = f"6M {year}"
        elif name.startswith("Years Ended December 31"):
            period = f"FY{year}"
        else:
            raise AssertionError(f"unknown period group {name!r}")
        columns.append((period, None))
        k += 1
    return columns


def _value_id(r):
    return f"{r['module_id']}-{r['measure']}-{r['period']}-{r['basis']}-{r['source_id']}"


def _key_line_id(k):
    return f"{k['module_id']}-{k['key_line'][:30]}"


@pytest.mark.parametrize("doc", MANIFEST["documents"], ids=lambda d: d["source_id"])
def test_document_sha256_matches_manifest(doc):
    actual = hashlib.sha256((CASE / doc["path"]).read_bytes()).hexdigest()
    assert actual == doc["sha256"], doc["path"]


def test_qualification_sha256_matches_manifest_origin():
    actual = hashlib.sha256((CASE / "qualification.json").read_bytes()).hexdigest()
    assert actual == MANIFEST["origin"]["qualification_json_sha256"]


@pytest.mark.parametrize(("module_id", "sha", "text"), KEYS)
def test_key_document_is_in_manifest(module_id, sha, text):
    assert sha in DOCS, f"{module_id}: {text!r} names unknown document {sha}"


@pytest.mark.parametrize(("module_id", "sha", "text"), KEYS)
def test_key_line_occurs_exactly_once(module_id, sha, text):
    count = _lines(sha).count(text)
    assert count == 1, f"{module_id}: {text!r} occurs {count} times in {DOCS[sha]['path']}"


def test_every_primary_key_is_figure_or_prose_key():
    figure = {(k["module_id"], k["document_sha256"], k["key_line"]) for k in EXPECTED["key_lines"]}
    assert len(figure) == len(EXPECTED["key_lines"]), "duplicate key_lines entry"
    assert figure | PROSE == PRIMARY
    assert not figure & PROSE


@pytest.mark.parametrize("key", EXPECTED["key_lines"], ids=_key_line_id)
def test_key_line_cells_fully_accounted(key):
    records = [
        r
        for r in EXPECTED["values"]
        if (r["module_id"], r["document_sha256"], r["key_line"])
        == (key["module_id"], key["document_sha256"], key["key_line"])
    ]
    numeric, percent = _numeric_indices(key["key_line"])
    excluded = [x["cell_index"] for x in key["excluded_cells"]]
    assert all(x["reason"] for x in key["excluded_cells"])
    assert sorted(r["cell_index"] for r in records) + sorted(excluded) == sorted(
        [i for i in numeric if i not in percent] + percent
    )
    assert sorted(excluded) == sorted(percent)


@pytest.mark.parametrize("record", EXPECTED["values"], ids=_value_id)
def test_value_key_line_is_primary_key_of_module(record):
    key = (record["module_id"], record["document_sha256"], record["key_line"])
    assert key in PRIMARY


@pytest.mark.parametrize("record", EXPECTED["values"], ids=_value_id)
def test_value_equals_pinned_cell(record):
    cells = _cells(record["key_line"])
    assert 0 < record["cell_index"] < len(cells)
    assert _parse(cells[record["cell_index"]]) == Decimal(record["value"])


@pytest.mark.parametrize("record", EXPECTED["values"], ids=_value_id)
def test_measure_matches_key_line_label(record):
    label = _cells(record["key_line"])[0]
    assert EXPECTED["label_measure"][label] == record["measure"]


@pytest.mark.parametrize("record", EXPECTED["values"], ids=_value_id)
def test_column_evidence_is_nearest_header_above_key_line(record):
    evidence = record["column_evidence"]
    assert len(evidence) == 2, "need a period-group line and a units/column line"
    lines = _lines(record["document_sha256"])
    key_at = lines.index(record["key_line"])
    positions = []
    for e in evidence:
        above = [i for i in range(key_at) if lines[i] == e]
        assert above, f"{e!r} not above key line in {record['source_id']}"
        assert key_at - above[-1] <= HEADER_WINDOW, f"{e!r} too far above key line"
        positions.append(above[-1])
    assert positions == sorted(positions)


@pytest.mark.parametrize("record", EXPECTED["values"], ids=_value_id)
def test_period_and_basis_match_header_column(record):
    columns = _derive_columns(record["column_evidence"])
    cells = _cells(record["key_line"])
    # Data cells align to the rightmost header columns (leading text columns are skipped).
    offset = len(columns) - (len(cells) - 1)
    assert offset >= 0
    period, basis = columns[record["cell_index"] - 1 + offset]
    assert (record["period"], record["basis"]) == (period, basis)


@pytest.mark.parametrize("record", EXPECTED["values"], ids=_value_id)
def test_unit_matches_header(record):
    assert any("in millions" in e.lower() for e in record["column_evidence"])
    assert record["unit"] == "USD millions"


@pytest.mark.parametrize("record", EXPECTED["values"], ids=_value_id)
def test_value_source_matches_manifest(record):
    assert DOCS[record["document_sha256"]]["source_id"] == record["source_id"]


@pytest.mark.parametrize("prose", EXPECTED["prose_keys"], ids=lambda p: p["module_id"])
def test_prose_key_is_primary_key_of_module(prose):
    assert (prose["module_id"], prose["document_sha256"], prose["sentence"]) in PRIMARY


def test_no_unresolved_expectations():
    assert EXPECTED["unresolved"] == []
