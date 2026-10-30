"""cp8: what-changed lines against `lines_positive` (positive) and `#/cases/<c>/tables`
cp8.what_changed (every case), on real fast pages from the CP-8 core (decision_ledger); one-field
perturbations fail."""
import copy
import importlib
import re
import sys

sys.path.insert(0, sys.argv[1])
import common as C  # noqa: E402

from deploy_workflow.owners import cp8  # noqa: E402

m8 = importlib.import_module("test_method_cp8")
c8 = importlib.import_module("test_connect_cp8")
E = C.oracle("cp8-owner")
CHIP = re.compile(r"[CKS]\d+")


def visible(runs):
    """app.js lineNodes: runs joined by one space inside a <p>; HTML collapses white space."""
    return re.sub(r"\s+", " ", " ".join(r["text"] for r in runs)).strip()


def check(payload, case):
    (block,) = [b for b in payload["report"]["blocks"] if b["block_id"] == "what-changed"]
    (table,) = [t for t in E["cases"][case]["tables"] if t["table_id"] == "cp8.what_changed"]
    wants = [row["facts"][0] for row in table["rows"]]
    if case == "positive":
        assert [w["shown"] for w in wants] == E["render"]["lines_positive"]
    passports = {p["ref_id"]: {f["name"]: f["value"] for f in p["fields"]} for p in payload["report"]["passports"]}
    assert len(block["lines"]) == len(wants)
    for line, want in zip(block["lines"], wants, strict=True):
        runs = line["runs"]
        if want["status"] != "known":
            assert [r["kind"] for r in runs] == ["text", "gap"], runs
            assert runs[0]["text"] == f"{want['column']}:", runs
            assert re.fullmatch(C.gap_pattern(want["status"]), runs[1]["text"]), runs
            continue
        chip = runs[-1] if runs[-1]["kind"] == "fig" and CHIP.fullmatch(runs[-1]["ref_id"] or "") and runs[-1]["text"] == runs[-1]["ref_id"] else None
        body = runs[:-1] if chip else runs
        assert C.text_ok(visible(body), want["shown"]), (visible(body), want["shown"])
        judged = want["value_class"] == "analyst_judgment"
        assert all(r["kind"] in ({"pen"} if judged else {"text", "gap", "fig"}) for r in body), body
        if want["calculation_id"]:
            assert chip is not None and chip["ref_id"][0] == "K", runs
            assert passports[chip["ref_id"]]["Calculation"] == want["calculation_id"]
        elif want["cites"]:
            assert chip is not None and chip["ref_id"][0] in "CS", runs
        else:
            assert chip is None, runs
    n = C.assert_table_cites(payload, "CP-8", E["cases"][case]["tables"])
    assert n >= 1
    return n


fails = 0
for case in ("positive", "no_outcome"):
    out = m8.report_of(case)
    lo = cp8.LedgerOutput(run=c8._run(case), submission_sha256="a" * 64, facts=out.facts,
                          tables=out.tables, claims=out.claims, limitations=out.limitations)
    mod = cp8.cp8_module(report=lo, inputs=c8._attempt().inputs, attempt=0).model_copy(update={"status": "restricted"})
    payload = C.payload_of(C.view_with(lo.run, [mod]))
    n = check(payload, case)
    print(case, "accepts;", n, "non-empty cites checked over all tables")

    def mutate(fn):
        p = copy.deepcopy(payload); fn(p); return p
    lines = lambda p: next(b for b in p["report"]["blocks"] if b["block_id"] == "what-changed")["lines"]
    perturbs = [
        ("line text", mutate(lambda p: lines(p)[1]["runs"][0].update(text=lines(p)[1]["runs"][0]["text"] + "!"))),
        ("chip dropped", mutate(lambda p: lines(p)[1]["runs"].pop())),
        ("gap label", mutate(lambda p: lines(p)[0]["runs"][0].update(text="Decision:"))),
        ("gap -> 0", mutate(lambda p: lines(p)[0]["runs"][1].update(text="0"))),
        ("pen -> text", mutate(lambda p: lines(p)[-1]["runs"][0].update(kind="text"))),
        ("line dropped", mutate(lambda p: lines(p).pop(2))),
        ("calc passport", mutate(lambda p: next(x for x in p["report"]["passports"] if x["ref_id"] == lines(p)[1]["runs"][-1]["ref_id"])["fields"][0].update(value="calc:other"))),
    ]
    rail = set(E["render"]["rails"]["evidence"]) | set(E["render"]["rails"]["limitations"])
    def rail_entry(p):
        return next(e for e in p["report"]["index"]["facts"] if e["coord"]["module_id"] == "CP-8"
                    and e["coord"]["table_id"] in rail and any(r[0] in "CS" for r in e["ref_ids"]))
    def drop_rail(p):
        p["report"]["index"]["facts"].remove(rail_entry(p))
    def swap_rail_order(p):
        e = next(e for e in p["report"]["index"]["facts"] if e["coord"]["module_id"] == "CP-8"
                 and e["coord"]["table_id"] in rail and sum(r[0] in "CS" for r in e["ref_ids"]) >= 2
                 and len({tuple(sorted((f["name"], f["value"]) for f in x["fields"] if f["name"] in ("Source", "Locator")))
                          for x in p["report"]["passports"] if x["ref_id"] in e["ref_ids"]}) >= 2)
        e["ref_ids"] = list(reversed(e["ref_ids"]))
    def rail_locator(p):
        ref = next(r for r in rail_entry(p)["ref_ids"] if r[0] in "CS")
        pp = next(x for x in p["report"]["passports"] if x["ref_id"] == ref)
        next(f for f in pp["fields"] if f["name"] == "Locator").update(value="page:99")
    perturbs.append(("rail-table cited fact: index entry removed", mutate(drop_rail)))
    perturbs.append(("rail-table cited fact: passport Locator", mutate(rail_locator)))
    try:
        perturbs.append(("rail-table fact: ref order reversed", mutate(swap_rail_order)))
    except StopIteration:
        print("  (no rail fact with two distinct Source/Locator pairs in this case)")
    if case == "no_outcome":
        perturbs.append(("token gap -> text 0", mutate(lambda p: lines(p)[1]["runs"][1].update(text="0", kind="text"))))
    for name, p in perturbs:
        try:
            check(p, case)
        except (AssertionError, KeyError, StopIteration):
            print("  fails:", name)
        else:
            print("  ACCEPTED (bad):", name); fails += 1
sys.exit(1 if fails else 0)
