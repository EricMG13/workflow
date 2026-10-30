"""cp4: sections/<id>/tables + #/<c>/CP-4/tables, displayed_literals/<positive|gap> (gap for
gap_false_same_definition), evidence/limitations rail tables, module limitations, on the real
fast pages (test_connect_cp4._expected_view); one-field perturbations fail."""
import copy
import importlib
import re
import sys

sys.path.insert(0, sys.argv[1])
import common as C  # noqa: E402

from deploy_vii.bindings.shipped import SHIPPED_MAPS  # noqa: E402

cp4 = importlib.import_module("test_connect_cp4")
E = C.oracle("cp4-owner")
LITERAL_CASE = {"positive": "positive", "gap": "gap", "gap_false_same_definition": "gap"}
GAP_PROSE = {"gap spelling, a G# gap id (never 0)", "gap spelling (G#)"}
DEFINITION_PROSE = "names the missing incorporated Schedule A"
NEVER = E["gap_false_same_definition"]["CP-4"]["semantic_acceptance"][
    "values_the_documented_rules_would_compose_from_these_inputs_and_that_must_not_qualify"]


def cell_at(block, table_ids, table_id, row_index, col_index):
    regs = C.registers(block) if block["tab_label"] is not None else [
        {"label": None, "columns": block["columns"], "row_header": block["row_header"], "rows": block["rows"]}]
    return regs[table_ids.index(table_id)]["rows"][row_index]["cells"][col_index]


def check(payload, case, *, limitations=None):
    key = LITERAL_CASE[case]
    tables = {t["table_id"]: t for t in E[key]["CP-4"]["tables"]}
    mod = C.module_payload(payload, "CP-4")
    facts = {f["fact_id"]: f for f in mod["facts"]}
    layouts = {t["table_id"]: t for t in mod["tables"]}
    blocks = {b["block_id"]: b for b in payload["report"]["blocks"]}
    for sid, sec in E["render"]["sections"].items():
        block = blocks[sid]
        assert (block["owner"], block["kind"]) == (sec["owner"], sec["kind"]), sid
        regs = C.registers(block) if block["tab_label"] is not None else [
            {"label": None, "columns": block["columns"], "row_header": block["row_header"], "rows": block["rows"]}]
        assert len(regs) == len(sec["tables"]), sid
        for reg, tid in zip(regs, sec["tables"], strict=True):
            want = tables[tid]
            assert reg["row_header"] == want["row_header"], tid
            assert reg["columns"] == [c["label"] for c in want["columns"]], tid
            assert [(r["row_id"], r["label"]) for r in reg["rows"]] == [(r["row_id"], r["label"]) for r in want["rows"]], tid
            for got_row, lay_row, want_row in zip(reg["rows"], layouts[tid]["rows"], want["rows"], strict=True):
                assert lay_row["fact_ids"] == [f["fact_id"] for f in want_row["facts"]], tid
                for cell, wf in zip(got_row["cells"], want_row["facts"], strict=True):
                    assert facts[wf["fact_id"]]["field"] == wf["fact_id"].rsplit(".", 1)[1]
                    assert cell["state"] == C._STATE[wf["status"]], wf["fact_id"]
                    if wf["status"] != "known":
                        assert re.fullmatch(C.gap_pattern(wf["status"]), cell["text"]), wf["fact_id"]
                    elif wf.get("text") is not None:  # cell_notation: text is the exact displayed text
                        assert cell["text"] == wf["text"], wf["fact_id"]
    # displayed literals (numeric cells have no text in the oracle tables)
    for tid, fields in E["render"]["displayed_literals"][key].items():
        (sid,) = [s for s, sec in E["render"]["sections"].items() if tid in sec["tables"]]
        want = tables[tid]
        for field, literal in fields.items():
            col = [c["field"] for c in want["columns"]].index(field)
            for ri, row in enumerate(want["rows"]):
                cell = cell_at(blocks[sid], E["render"]["sections"][sid]["tables"], tid, ri, col)
                if literal in GAP_PROSE:
                    assert cell["state"] == "gap" and re.fullmatch(r"∅ G\d+", cell["text"]), (tid, field)
                elif literal == DEFINITION_PROSE:
                    assert cell["text"] == row["facts"][col]["text"] and "Schedule A" in cell["text"], (tid, field)
                else:
                    assert cell["text"] == literal, (tid, field, cell["text"], literal)
    if case == "gap_false_same_definition":  # the refused values never show
        cells = [c["text"] for c in blocks["covenant-tests-headroom"]["rows"][0]["cells"]]
        assert "3.00x" not in cells and "75.0%" not in cells and NEVER["verdict"] not in cells
    # rails: every oracle rail table is on the module payload
    for name in ("evidence_rail_tables", "limitations_rail_tables"):
        assert set(E["render"][name]) <= set(layouts), name
    if limitations is not None:
        assert mod["limitations"] == limitations


def expected_limitations(payload, key):
    """Settled list, then CP-0 literal head, then the CP-1 head's own list (page payload)."""
    cp1 = [m for m in payload["modules"] if m["module_id"] == "CP-1"]
    cp1_limits = cp1[0]["limitations"] if cp1 else []
    inh = E[key]["CP-4"]["inherited_limitations"]["literal_head_from_CP-0"]
    return list(dict.fromkeys([*E[key]["CP-4"]["settled_limitations"], *inh, *cp1_limits]))


# Bindings G2 draws its rails from: the evidence / limitations rail tables of CP-4.
cp4_map = next(m for m in SHIPPED_MAPS if m.module_id == "CP-4")
for dest, name in (("evidence", "evidence_rail_tables"), ("limitations", "limitations_rail_tables")):
    got = [e.fact_coord.table_id for e in cp4_map.entries if e.block_id == dest]
    print(dest, "binding tables == oracle:", got == E["render"][name])

fails = 0
for case in ("positive", "gap", "gap_false_same_definition"):
    key = LITERAL_CASE[case]
    view = cp4._expected_view(key)
    # settled shape of the head (execution.settle adds the synthetic limitation; inherited from CP-0)
    m = next(x for x in view.modules if x.module_id == "CP-4")
    lit = E[key]["CP-4"]["inherited_limitations"]["literal_head_from_CP-0"]
    settled = tuple(dict.fromkeys([*E[key]["CP-4"]["settled_limitations"], *lit]))
    view = view.model_copy(update={"modules": tuple(
        x.model_copy(update={"limitations": settled}) if x.module_id == "CP-4" else x for x in view.modules)})
    payload = C.payload_of(view)
    want_limits = expected_limitations(payload, key)
    check(payload, case, limitations=want_limits)
    print(case, "accepts")
    def mutate(fn):
        p = copy.deepcopy(payload); fn(p); return p
    blk = lambda p, sid: next(b for b in p["report"]["blocks"] if b["block_id"] == sid)
    perturbs = [
        ("threshold literal", mutate(lambda p: blk(p, "covenant-tests-headroom")["rows"][0]["cells"][1].update(text="4.0x"))),
        ("current literal", mutate(lambda p: blk(p, "covenant-tests-headroom")["rows"][0]["cells"][4].update(text="1.0x"))),
        ("capacity gap -> 0", mutate(lambda p: blk(p, "capacity")["rows"][1]["cells"][2].update(text="0"))),
        ("rating text", mutate(lambda p: blk(p, "lender-protection-score")["rows"][0]["cells"][0].update(text="Weak"))),
        ("tab row label", mutate(lambda p: blk(p, "documents-structure")["tabs"][0]["rows"][0].update(label="X"))),
        ("module limitation dropped", mutate(lambda p: C.module_payload(p, "CP-4")["limitations"].pop())),
        ("rail table missing", mutate(lambda p: C.module_payload(p, "CP-4")["tables"].pop(
            next(i for i, t in enumerate(C.module_payload(p, "CP-4")["tables"]) if t["table_id"] == "T4D.5")))),
    ]
    if key == "gap":
        perturbs.append(("refused headroom shows", mutate(lambda p: blk(p, "covenant-tests-headroom")["rows"][0]["cells"][5].update(text="3.00x", state="known"))))
        perturbs.append(("definition text", mutate(lambda p: blk(p, "ebitda-definition")["rows"][0]["cells"][0].update(text="Same definition"))))
    for name, p in perturbs:
        try:
            check(p, case, limitations=want_limits)
        except (AssertionError, ValueError, StopIteration):
            print("  fails:", name)
        else:
            print("  ACCEPTED (bad):", name); fails += 1
sys.exit(1 if fails else 0)
