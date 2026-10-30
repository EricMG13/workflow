from common import *
from rb import parse
import os
D = os.path.join(os.path.dirname(__file__), "dumps")

def stage():
    rows = parse(os.path.join(D, "narrative.txt"))
    src = {r["source_id"]: r["evidence_id"] for r in rows if r["kind"] == "source"}
    ev = {r["event_id"]: r["evidence_id"] for r in rows if r["kind"] == "subsequent_event"}
    ent = next(r["evidence_id"] for r in rows if r["kind"] == "entity")
    bs = [r for r in rows if r["kind"] == "statement_BS" and r["line_id"]]
    fin = [r for r in bs if r["line_id"] == "bs-long-term-financing-obligations"]
    assert len(fin) == 3
    P = lambda t: {"kind": "prose", "text": t}
    E = lambda i: {"kind": "evidence", "evidence_id": i}
    I = {"kind": "issuer"}
    findings = [
        {"finding_id": "f-interim-unaudited", "dimension": "data_quality",
         "title": "Interim and release figures are unaudited",
         "evidence": [P("The quarterly report"), E(src[Q]), P("and the earnings release"), E(src[R]), P("carry unaudited statements, while the annual report"), E(src[K]), P("carries an audit opinion.")],
         "risk_mechanic": [I, P("relies on unaudited interim amounts for the current period, so a later restatement or auditor adjustment would move them.")],
         "credit_implication": [P("Current-period credit conclusions for"), I, P("stay provisional until the next audited annual statements.")]},
        {"finding_id": "f-pending-merger", "dimension": "key_gaps",
         "title": "The pending Merger is an unresolved event after the audited year",
         "evidence": [P("The pack records the Merger agreement of May 27, 2026 as an announced event"), E(ev["merger-agreement"]), P("that follows the fiscal year in the annual report and that has not closed.")],
         "risk_mechanic": [P("If the Merger closes, ownership, financing and the capital structure of"), I, P("can change in ways the filed statements do not show.")],
         "credit_implication": [P("All figures for"), I, P("are pre-closing and cannot be read as the post-closing credit profile.")]},
        {"finding_id": "f-alberta-launch", "dimension": "data_quality",
         "title": "A launch after the quarter end is outside the reported period",
         "evidence": [P("The quarterly report discloses a launch of mobile sports betting and iGaming in Alberta, Canada on July 13, 2026"), E(ev["alberta-launch"]), P("after the quarter end.")],
         "risk_mechanic": [P("The launch is an operating event after the reporting period, so it does not enter the reported amounts for"), I, P("and cannot be assumed in them.")],
         "credit_implication": [P("Any effect of the launch on the results of"), I, P("must come from later periods, not from this pack.")]},
        {"finding_id": "f-financing-obligations", "dimension": "key_gaps",
         "title": "Long-term financing obligations sit outside reported debt",
         "evidence": [P("The balance sheets show long-term financing obligations at June 30, 2026"), E(next(r["evidence_id"] for r in fin if r["period_id"] == "bs-2026-06-30")),
                      P("at December 31, 2025"), E(next(r["evidence_id"] for r in fin if r["period_id"] == "bs-2025-12-31")),
                      P("and at December 31, 2024"), E(next(r["evidence_id"] for r in fin if r["period_id"] == "bs-2024-12-31")), P("as a separate line from long-term debt.")],
         "risk_mechanic": [I, P("carries large fixed financing obligations on its leases that sit beside, not inside, its borrowed debt, so debt measures alone understate fixed claims.")],
         "credit_implication": [P("Credit review of"), I, P("must read these obligations with the debt note and cannot rely on debt totals alone.")]},
        {"finding_id": "f-nongaap-definition", "dimension": "definition_risks",
         "title": "Adjusted EBITDA and net debt are issuer-defined non-GAAP measures",
         "evidence": [P("The earnings release presents Adjusted EBITDA and net debt as non-GAAP measures"), E(src[R]), P("defined by the issuer, and no covenant definition is in the pack.")],
         "risk_mechanic": [I, P("defines Adjusted EBITDA by its own add-backs and lease treatment, which can differ from any credit agreement definition.")],
         "credit_implication": [P("Leverage built on the issuer measure for"), I, P("cannot be assumed to match covenant leverage.")]},
    ]
    dims = {
        "leverage": ("unassessed", [], "No leverage metric is available because the calculation gate is blocked, so this dimension is not assessed."),
        "coverage": ("unassessed", [], "No coverage metric is available because the calculation gate is blocked, so this dimension is not assessed."),
        "cash_flow_quality": ("unassessed", [], "No cash flow metric is available because the calculation gate is blocked, so this dimension is not assessed."),
        "liquidity": ("unassessed", [], "No liquidity metric is available because the calculation gate is blocked, so this dimension is not assessed."),
        "data_quality": ("addressed", ["f-interim-unaudited", "f-alberta-launch"], "Source quality and the timing of disclosed events are addressed."),
        "definition_risks": ("addressed", ["f-nongaap-definition"], "The issuer definition of Adjusted EBITDA is addressed."),
        "key_gaps": ("addressed", ["f-pending-merger", "f-financing-obligations"], "The pending Merger and the financing obligations are addressed."),
    }
    coverage = [{"dimension": d, "status": s, "finding_ids": f, "rationale": [P(t)]} for d, (s, f, t) in dims.items()]
    stories = [
        {"evidence_id": ev["merger-agreement"], "finding_ids": ["f-pending-merger"]},
        {"evidence_id": ev["alberta-launch"], "finding_ids": ["f-alberta-launch"]},
        *({"evidence_id": r["evidence_id"], "finding_ids": ["f-financing-obligations"]} for r in fin),
    ]
    sub = {
        "findings": findings, "coverage": coverage, "stories": stories,
        "funding": {"status": "material_items", "reviewed_statement_ids": [r["evidence_id"] for r in bs],
                    "material_statement_ids": [r["evidence_id"] for r in fin],
                    "rationale": [P("Every located balance-sheet row was reviewed. Only long-term financing obligations are a named liability outside debt that is large enough to matter to funding; the other lines are standard operating balances.")]},
        "limitations": ["The narrative covers data quality, definitions and gaps only, because no KPI is available."],
    }
    return {"step": "narrative", "calls": [{"tool": "read_inputs"}], "submission": sub}
