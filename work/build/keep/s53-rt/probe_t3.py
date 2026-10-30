"""T3 differential probe: dump content_issues for a fixed mutation set and seeded combinations,
for every case in cases/cp4c-owner; the caller diffs the incumbent's and the candidate's dumps."""
import copy
import itertools
import json
import random
import sys

import test_connect_cp4c as c
import test_method_cp4c as stage1

from deploy_workflow.owners import cp4c


def m_dup(p):
    p["claims"][1]["class_id"] = p["claims"][0]["class_id"]
def m_two_secured(p):
    p["claims"][1]["kind"] = "secured_debt"
def m_no_secured(p):
    for x in p["claims"]:
        if x["kind"] == "secured_debt":
            x["kind"] = "other_liability"
def m_rank(p):
    for x in p["claims"]:
        x["rank"] = "1"
def m_val_id(p):
    p["valuation"][1]["case_id"] = "v09"
def m_ful_id(p):
    p["fulcrum"][0]["case_id"] = "v03"
def m_plan_id(p):
    p["plan"][2]["case_id"] = "v01"
def m_high(p):
    p["assessment"]["confidence"] = "High"
def m_blank(p):
    p["assessment"]["rationale"] = "  "
def m_name_lines(p):
    p["claims"][0]["name"] = "Senior\nloan"
def m_reserved(p):
    p["claims"][1]["name"] = "Trade {T1.x}"
def m_label_fig(p):
    p["valuation"][0]["label"] = "Base 123"
def m_run_bad(p):
    p["fulcrum"][1]["rationale"] = "{low"
def m_treat(p):
    p["plan"][0]["treatments"][0]["class_id"] = "c99"
def m_treat_fit(p):
    t = p["plan"][0]["treatments"][0]
    t["treatment"] = "No recovery" if t["treatment"] != "No recovery" else "Paid in full"
def m_ful_names(p):
    p["fulcrum"][0]["class_ids"] = []
def m_gap_blank(p):
    p["gaps"][0]["gap"] = " "

MUTS = [v for k, v in sorted(globals().items()) if k.startswith("m_")]


def run(case):
    ctx = stage1._context(case)
    base = c._payload(case)
    out = {}
    rng = random.Random(53)
    sets = [()] + [(m,) for m in MUTS] + list(itertools.combinations(MUTS, 2))
    sets += [tuple(rng.sample(MUTS, rng.randint(3, 8))) for _ in range(60)]
    for s in sets:
        p = copy.deepcopy(base)
        key = "+".join(m.__name__ for m in s) or "base"
        try:
            for m in s:
                m(p)
            out[key] = list(cp4c.content_issues(c._with(ctx, p)))
        except Exception as e:  # recorded verbatim, compared across versions, never hidden
            out[key] = f"RAISED {type(e).__name__}: {e}"
    return out


cases = sys.argv[2:]
json.dump({k: run(k) for k in cases}, open(sys.argv[1], "w"), indent=0, sort_keys=True)
