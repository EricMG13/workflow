"""Acceptance 1 `cites` normaliser on s1a FP01 (company-operating-model, company-profile).
No fast s1a page exists, so the CP-1A module is rebuilt from the snapshot oracle's own CP-1A
tables (`#/<c>/CP-1A/tables`) with one probe-only quote per oracle cite (the oracle stores no
quote), rendered by the real report_view/render. Perturbations of passports and index fail."""
import copy
import json
import re
import sys
from datetime import date

sys.path.insert(0, sys.argv[1])
import common as C  # noqa: E402

from deploy_vii.contracts import Citation, Fact, Module, ReportTable, Run, TableColumn, TableRow  # noqa: E402

E = C.oracle("snapshot")
BLOCKS = ("company-operating-model", "company-profile")


def module_from_oracle(case):
    facts, tables = [], []
    for t in E[case]["CP-1A"]["tables"]:
        rows = []
        for r in t["rows"]:
            ids = []
            for i, f in enumerate(r["facts"]):
                cites = f["cites"] if isinstance(f["cites"], list) else []
                facts.append(Fact(
                    fact_id=f["fact_id"], label=f["column"], table_id=t["table_id"], row_id=r["row_id"],
                    field=f["fact_id"].rsplit(".", 1)[1], text=f["text"], status=f["status"],
                    limitation=f["limitation"] if f["status"] != "known" else None,
                    value_class=f.get("value_class"),
                    citations=tuple(Citation(source_id=s, source_sha256="0" * 64, locator=loc,
                                             quote=f"probe quote {f['fact_id']} {k}")
                                    for k, (s, loc) in enumerate(cites)),
                ))
                ids.append(f["fact_id"])
            rows.append(TableRow(row_id=r["row_id"], label=r["label"], fact_ids=tuple(ids)))
        tables.append(ReportTable(table_id=t["table_id"], title=t["title"], row_header=t["row_header"],
                                  columns=tuple(TableColumn(field=c["field"], label=c["label"]) for c in t["columns"]),
                                  rows=tuple(rows)))
    return Module(run_id="probe", issuer_id="northbridge-synthetic", as_of=date(2025, 12, 31),
                  module_id="CP-1A", status="restricted", facts=tuple(facts), tables=tuple(tables),
                  limitations=("probe",))


def resolve_fact(payload, register, row_index, cell_index):
    """Payload register cell -> (module_id, fact_id): a one-value register's row id is the fact id;
    otherwise the unique module table whose row ids, row labels and column labels are the register's."""
    row = register["rows"][row_index]
    hits = []
    for m in payload["modules"]:
        ids = {f["fact_id"] for f in m["facts"]}
        if register["columns"] == ["Value"] and row["row_id"] in ids:
            hits.append((m["module_id"], row["row_id"]))
            continue
        labels = [(r["row_id"], r["label"]) for r in register["rows"]]
        for t in m["tables"]:
            if [(r["row_id"], r["label"]) for r in t["rows"]] == labels and [c["label"] for c in t["columns"]] == register["columns"]:
                hits.append((m["module_id"], t["rows"][row_index]["fact_ids"][cell_index]))
    assert len(hits) == 1, (register["label"], row["row_id"], hits)
    return hits[0]


def check(payload, case):
    blocks = {b["block_id"]: b for b in payload["report"]["blocks"]}
    n = 0
    for bid in BLOCKS:
        want = E[case]["FP01"][bid]
        wregs = [want["primary"], *want["tabs"]]
        regs = C.registers(blocks[bid])
        assert [r["label"] for r in regs] == [w["tab"] for w in wregs]
        for reg, wreg in zip(regs, wregs, strict=True):
            for ri, wrow in enumerate(wreg["rows"]):
                for ci, wcell in enumerate(wrow["cells"]):
                    if "cites" not in wcell:
                        continue  # gap cells carry no cites (build_s1_oracle.cell_view)
                    module_id, fact_id = resolve_fact(payload, reg, ri, ci)
                    assert C.cites_of(payload, module_id, fact_id, {"status": "known", "cites": wcell["cites"]}) == wcell["cites"], (bid, fact_id)
                    n += 1
    return n


fails = 0
for case in ("positive", "gap_business_without_ownership_transaction"):
    run = Run(run_id="probe", issuer_id="northbridge-synthetic", issuer_name="Northbridge Synthetic Group",
              as_of=date(2025, 12, 31), case_kind="synthetic", pathway="credit_snapshot",
              requested_modules=("CP-1A",))
    payload = C.payload_of(C.view_with(run, [module_from_oracle(case)]))
    n = check(payload, case)
    print(case, "accepts", n, "cells with cites")

    def mutate(fn):
        p = copy.deepcopy(payload); fn(p); return p

    def first_multi(p):  # an index entry with two or more C/S refs
        return next(e for e in p["report"]["index"]["facts"] if e["coord"]["module_id"] == "CP-1A"
                    and e["coord"]["table_id"] in ("operating_model", "company_description", "ownership_register", "revenue_business_mix")
                    and sum(r[0] in "CS" for r in e["ref_ids"]) >= 1)

    def src(p):
        e = first_multi(p); ref = next(r for r in e["ref_ids"] if r[0] in "CS")
        pp = next(x for x in p["report"]["passports"] if x["ref_id"] == ref)
        next(f for f in pp["fields"] if f["name"] == "Source").update(value="other-source")

    def drop(p):
        e = first_multi(p); e["ref_ids"] = [r for r in e["ref_ids"] if r[0] not in "CS"]

    def extra(p):
        e = first_multi(p); e["ref_ids"] = [*e["ref_ids"], next(r for r in e["ref_ids"] if r[0] in "CS")]

    for name, fn in (("passport Source", src), ("index ref dropped", drop), ("index ref duplicated", extra)):
        try:
            check(mutate(fn), case)
        except AssertionError:
            print("  fails:", name)
        else:
            print("  ACCEPTED (bad):", name); fails += 1
sys.exit(1 if fails else 0)
