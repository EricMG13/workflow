"""Shared probe helpers: real fast pages and the candidate comparators (spec draft)."""
import copy
import json
import re
from pathlib import Path
from typing import Any

from deploy_vii.contracts import ModuleView
from deploy_vii.render import empty_view, render

ROOT = Path.cwd()


def oracle(name: str) -> Any:
    return json.loads((ROOT / "cases" / name / "expected.json").read_text(encoding="utf-8"))


def payload_of(view: Any) -> dict[str, Any]:
    html = render(view)
    marker = '<script id="report-data" type="application/json">'
    return json.loads(html.split(marker, 1)[1].split("</script>", 1)[0])


def view_with(run: Any, modules: list[Any]) -> Any:
    view = empty_view(run)
    by_id = {m.module_id: m for m in modules}
    out = []
    for m in view.modules:
        mod = by_id.get(m.module_id)
        if mod is None:
            out.append(m)
            continue
        out.append(
            ModuleView(
                module_id=m.module_id, title=m.title, aliases=m.aliases, status=mod.status,
                artifact_sha256=mod.content_hash(), facts=mod.facts, tables=mod.tables,
                claims=mod.claims,
                limitations=tuple(dict.fromkeys((*mod.limitations, *mod.inherited_limitations))),
            )
        )
    return view.model_copy(update={"modules": tuple(out)})


# ---------------- candidate comparators

def gap_pattern(status: str) -> str:
    return r"∅ G\d+ n\.m\." if status == "not_applicable" else r"∅ G\d+"


def text_ok(got: str, want: str) -> bool:
    parts = (re.escape(p) for p in want.split("∅ G#"))
    return re.fullmatch(r"∅ G\d+".join(parts), got) is not None


_STATE = {"known": "known", "missing": "gap", "not_applicable": "not_meaningful"}


def registers(block: dict[str, Any]) -> list[dict[str, Any]]:
    """[{label, columns, row_header, rows}] primary first, then the further tabs."""
    first = {k: block[k] for k in ("columns", "row_header", "rows")}
    first["label"] = block["tab_label"]
    return [first, *block["tabs"]]


def module_payload(payload: dict[str, Any], module_id: str) -> dict[str, Any]:
    (m,) = [m for m in payload["modules"] if m["module_id"] == module_id]
    return m


def cites_of(payload: dict[str, Any], module_id: str, fact_id: str, want: dict[str, Any]) -> list[list[str]]:
    """Acceptance 1: Source and Locator from the passports of the fact's index refs (C/S only),
    in index order, no de-duplication. No fallback: build_index (report_view.py:772-871) gives a
    fact an entry exactly when it has a ref (a G# for a gap, a C/S per citation, a K# for a
    calculation). The oracle fact says which: an entry is required iff status != known, or
    list cites are non-empty, or calculation_id is set; required -> exactly one entry, else none."""
    entries = [
        e for e in payload["report"]["index"]["facts"]
        if e["coord"]["module_id"] == module_id and e["coord"]["fact_id"] == fact_id
    ]
    required = want["status"] != "known" or bool(want.get("cites")) or bool(want.get("calculation_id"))
    assert len(entries) == (1 if required else 0), (fact_id, len(entries), required)
    if not entries:
        return []
    passports = {p["ref_id"]: p for p in payload["report"]["passports"]}
    out = []
    for ref in entries[0]["ref_ids"]:
        if ref[0] not in "CS":
            continue
        fields = {f["name"]: f["value"] for f in passports[ref]["fields"]}
        out.append([fields["Source"], fields["Locator"]])
    return out


def assert_table_cites(payload: dict[str, Any], module_id: str, tables: list[dict[str, Any]]) -> int:
    """Every oracle fact with list cites, keyed by fact_id (prose run-time cites are skipped).
    Returns the number of non-empty cites checked; the caller asserts it is at least 1."""
    nonempty = 0
    for t in tables:
        for r in t["rows"]:
            for f in r["facts"]:
                cites = f.get("cites")
                if not (isinstance(cites, list) and all(isinstance(c, list) for c in cites)):
                    continue
                assert cites_of(payload, module_id, f["fact_id"], f) == cites, f["fact_id"]
                nonempty += bool(cites)
    return nonempty


def assert_register_equals_table(reg, label, table, module_id, payload, *, cites=True):
    """One page register against one oracle table (`#/cases/<c>/tables` shape)."""
    assert reg["label"] == label, (reg["label"], label)
    assert reg["row_header"] == table["row_header"], table["table_id"]
    assert reg["columns"] == [c["label"] for c in table["columns"]], table["table_id"]
    assert [(r["row_id"], r["label"]) for r in reg["rows"]] == [
        (r["row_id"], r["label"]) for r in table["rows"]
    ], table["table_id"]
    mod = module_payload(payload, module_id)
    (layout,) = [t for t in mod["tables"] if t["table_id"] == table["table_id"]]
    facts = {f["fact_id"]: f for f in mod["facts"]}
    fields = [c["field"] for c in table["columns"]]
    for got_row, lay_row, want_row in zip(reg["rows"], layout["rows"], table["rows"], strict=True):
        assert lay_row["row_id"] == want_row["row_id"]
        assert lay_row["fact_ids"] == [f["fact_id"] for f in want_row["facts"]], want_row["row_id"]
        for cell, fid, want in zip(got_row["cells"], lay_row["fact_ids"], want_row["facts"], strict=True):
            col = [c["label"] for c in table["columns"]].index(want["column"])
            assert facts[fid]["field"] == fields[col], fid
            assert cell["state"] == _STATE[want["status"]], (fid, cell["state"])
            if want["status"] == "known":
                assert text_ok(cell["text"], want["shown"]), (fid, cell["text"], want["shown"])
            else:
                assert re.fullmatch(gap_pattern(want["status"]), cell["text"]), (fid, cell["text"])
            if cites:
                assert cites_of(payload, module_id, fid, want) == want["cites"], (fid,)
