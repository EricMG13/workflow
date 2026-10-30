"""Reviewer perturbations the preparer did not try, against the preparer's comparators.
argv[1] = preparer probe dir. Exit = number of perturbations wrongly ACCEPTED."""
import copy, importlib, sys
K = sys.argv[1]
def load(name, marker="\nfails = 0"):
    src = open(f"{K}/{name}").read().split(marker)[0]
    ns = {"__name__": "x"}; exec(compile(src, name, "exec"), ns); return ns
bad = 0
def expect_fail(label, fn, *a, **kw):
    global bad
    try: fn(*a, **kw)
    except (AssertionError, KeyError, ValueError, StopIteration, IndexError) as e: print("  fails:", label, type(e).__name__)
    else: print("  ACCEPTED (bad):", label); bad += 1
def expect_pass(label, fn, *a, **kw):
    try: fn(*a, **kw); print("  passes (vacuous):", label)
    except Exception as e: print("  fails:", label, type(e).__name__)

# ---- cp3d
P1 = load("probe1_cp3d_tables_exit0.py", "\nfor case in ("); C = P1["C"]
blk = lambda p, bid: next(b for b in p["report"]["blocks"] if b["block_id"] == bid)
for case in ("positive", "gap_no_market"):
    pay = C.payload_of(C.view_with(P1["base"]._pack(case).run, [P1["base"]._module(case)]))
    print("cp3d", case)
    p = copy.deepcopy(pay); blk(p, "market-against-fundamentals")["tabs"][0]["label"] += "x"; expect_fail("tab label", P1["check"], p, case)
    p = copy.deepcopy(pay); m = C.module_payload(p, "CP-3D"); r = next(r for t in m["tables"] for r in t["rows"] if len(r["fact_ids"]) > 1); r["fact_ids"].reverse(); expect_fail("layout fact_ids reversed", P1["check"], p, case)
    p = copy.deepcopy(pay); c = next(c for r in blk(p, "market-against-fundamentals")["rows"] for c in r["cells"] if c["state"] == "known"); c["state"] = "gap"; expect_fail("known state->gap", P1["check"], p, case)
    # vacuity: fact absent from the index while the oracle cell has cites []
    p = copy.deepcopy(pay)
    tabs = {t["table_id"]: t for t in P1["E"]["cases"][case]["tables"]}
    empty = [f["fact_id"] for t in tabs.values() for r in t["rows"] for f in r["facts"] if f["cites"] == []]
    n0 = len(p["report"]["index"]["facts"])
    p["report"]["index"]["facts"] = [e for e in p["report"]["index"]["facts"] if not (e["coord"]["module_id"] == "CP-3D" and e["coord"]["fact_id"] in empty)]
    print("  facts with cites []:", len(empty), "index entries removed:", n0 - len(p["report"]["index"]["facts"]))
    expect_pass("index entries of cites-[] facts removed", P1["check"], p, case)
    # cites order
    p = copy.deepcopy(pay); e = next((e for e in p["report"]["index"]["facts"] if e["coord"]["module_id"] == "CP-3D" and len({r for r in e["ref_ids"] if r[0] in "CS"}) >= 2), None)
    if e: e["ref_ids"].reverse(); expect_fail("index ref order reversed", P1["check"], p, case)
    else: print("  no multi-ref fact")

# ---- cp4
P2 = load("probe2_cp4_pointers_exit0.py"); C = P2["C"]
for case in ("gap_false_same_definition",):
    key = "gap"; view = P2["cp4"]._expected_view(key)
    lit = P2["E"][key]["CP-4"]["inherited_limitations"]["literal_head_from_CP-0"]
    settled = tuple(dict.fromkeys([*P2["E"][key]["CP-4"]["settled_limitations"], *lit]))
    view = view.model_copy(update={"modules": tuple(x.model_copy(update={"limitations": settled}) if x.module_id == "CP-4" else x for x in view.modules)})
    pay = C.payload_of(view); wl = P2["expected_limitations"](pay, key)
    print("cp4", case, "rows in headroom:", len(blk(pay, "covenant-tests-headroom")["rows"]))
    for ri, row in enumerate(blk(pay, "covenant-tests-headroom")["rows"]):
        for ci, cell in enumerate(row["cells"]):
            if cell["state"] != "known":
                p = copy.deepcopy(pay); blk(p, "covenant-tests-headroom")["rows"][ri]["cells"][ci].update(text="75.0%", state="known")
                expect_fail(f"headroom r{ri}c{ci} gap->75.0%", P2["check"], p, case, limitations=wl)
    p = copy.deepcopy(pay); c = next(c for b in p["report"]["blocks"] if b["block_id"] in P2["E"]["render"]["sections"] for r in b["rows"] for c in r["cells"] if c["state"] == "gap"); c.update(state="not_meaningful", text=c["text"] + " n.m.")
    expect_fail("gap -> not_meaningful n.m.", P2["check"], p, case, limitations=wl)
    p = copy.deepcopy(pay); C.module_payload(p, "CP-4")["limitations"].reverse(); expect_fail("limitations order reversed", P2["check"], p, case, limitations=wl)

# ---- cp8
P3 = load("probe3_cp8_lines_exit0.py"); C = P3["C"]
for case in ("positive",):
    out = P3["m8"].report_of(case)
    lo = P3["cp8"].LedgerOutput(run=P3["c8"]._run(case), submission_sha256="a" * 64, facts=out.facts, tables=out.tables, claims=out.claims, limitations=out.limitations)
    mod = P3["cp8"].cp8_module(report=lo, inputs=P3["c8"]._attempt().inputs, attempt=0).model_copy(update={"status": "restricted"})
    pay = C.payload_of(C.view_with(lo.run, [mod])); L = lambda p: blk(p, "what-changed")["lines"]
    print("cp8", case)
    p = copy.deepcopy(pay); L(p)[1], L(p)[2] = L(p)[2], L(p)[1]; expect_fail("lines 1,2 swapped", P3["check"], p, case)
    p = copy.deepcopy(pay); ch = L(p)[1]["runs"][-1]; s = next(x for x in p["report"]["passports"] if x["ref_id"][0] == "S"); ch.update(ref_id=s["ref_id"], text=s["ref_id"]); expect_fail("K chip -> S chip", P3["check"], p, case)
    p = copy.deepcopy(pay); ln = next(l for l in L(p) if l["runs"][-1]["kind"] == "fig" and l["runs"][-1]["ref_id"][0] in "CS"); s = ln["runs"][-1]
    pp = next(x for x in p["report"]["passports"] if x["ref_id"] == s["ref_id"]); next(f for f in pp["fields"] if f["name"] == "Source").update(value="other")
    expect_pass("cited line's passport Source changed (no _page_cites in probe3)", P3["check"], p, case)
sys.exit(bad)
