"""Writes cases/cp4c-owner/{manifest,submissions,expected}.json (stdlib only, imports nothing from src/).

Independent oracle for the CP-4C (Restructuring fulcrum) owner. Every number is derived with
exact rational arithmetic (fractions.Fraction) from the frozen financial and legal source bytes,
the pinned frozen upstream oracles (CP-2A, CP-2G, CP-4) and the literal analyst submissions, and
cross-checked against decimal.Context(prec=38, ROUND_HALF_EVEN). No product module is imported.
Method rules: work/lead/cp4c-owner-preparation/lease-draft.md.

Run: python3 -I cases/cp4c-owner/builder/build.py   (from the repository root)
"""

import hashlib
import json
import re
import sys
from copy import deepcopy
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, DivisionByZero, Inexact, InvalidOperation, Overflow, localcontext
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "cases" / "cp4c-owner"
CTX = Context(prec=38, rounding=ROUND_HALF_EVEN)
CTX_EXACT = Context(prec=38, rounding=ROUND_HALF_EVEN, traps=[Inexact, InvalidOperation, DivisionByZero, Overflow])
D = Decimal

# --- 0. pinned inputs --------------------------------------------------------------------------
PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/legal/manifest.json": "d6a8ec15285dbe16a6e2ff3f167c26a295b675decfb4df7231901b0243305168",
    "cases/cp2a-owner/submissions.json": "191180c2596c38fad13a9b190c6b0fb0103de21ff43b08d175c0f4cf38003a81",
    "cases/cp2a-owner/expected.json": "457508a0643af8ca6e31bfec6103ae2a0ca9f009dfcc3bf57d29b001e88668b5",
    "cases/cp2g-owner/manifest.json": "1c36928c44a0a69ce9da286db4332f2d8aa8e2fca1b1d9504b9191969d105242",
    "cases/cp2g-owner/submissions.json": "aaa8ea0eeb563064cc944c69ec0e7b3dbc54032243fa72d07d6a735be49da86f",
    "cases/cp2g-owner/expected.json": "97328745be246b3bf67fe5840f291afb3da3cbae99b51db1ba7bd24d2eef406c",
    "cases/cp4-owner/submissions.json": "f2ef2e30d3541e3a72a2337ca6cec9c9396a364f61398057cc45172a6fce9461",
    "cases/cp4-owner/expected.json": "154fc2d09a4c8a06232a489e5a047e947ee098507969e5e11cdb1ca7f6f4f6a0",
    "cases/cp3c-owner/manifest.json": "d5ca731c45891613a2982b0e538162127fa8f290017f6da43161c6f4fe616f53",
    "src/deploy_vii/methodology.json": "1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6",
    "src/deploy_vii/business_context.py": "1d8f0cc5aeee7ad79ec314300cebeef772abd83dc65e554cd47d638f3abf41a7",
}


def pinned(rel, load=True):
    data = (ROOT / rel).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == PINS[rel], (rel, digest)
    return json.loads(data) if load else data


FIN = pinned("cases/financial/manifest.json")
LEGAL = pinned("cases/legal/manifest.json")
CP2A_SUB = pinned("cases/cp2a-owner/submissions.json")
CP2A_EXP = pinned("cases/cp2a-owner/expected.json")
CP2G_MAN = pinned("cases/cp2g-owner/manifest.json")
CP2G_SUB = pinned("cases/cp2g-owner/submissions.json")
CP2G_EXP = pinned("cases/cp2g-owner/expected.json")
CP4_SUB = pinned("cases/cp4-owner/submissions.json")
CP4_EXP = pinned("cases/cp4-owner/expected.json")
CP3C_MAN = pinned("cases/cp3c-owner/manifest.json")
METHODOLOGY = pinned("src/deploy_vii/methodology.json")
pinned("src/deploy_vii/business_context.py", load=False)


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


SRC = {s["source_id"]: s for s in FIN["sources"]}
LEG = {c["case_id"]: c["legal_source"] for c in LEGAL["cases"]}
LEGAL_CASE = {"positive": "legal-current-matching-definition", "gap": "legal-current-missing-ebitda-definition"}
for _s in list(SRC.values()) + list(LEG.values()):
    assert page_sha([p["text"] for p in _s["pages"]]) == _s["sha256"]
PAGE = {p["locator"]: p["text"] for p in SRC["financial"]["pages"]}
LEGAL_PAGE = {k: {p["locator"]: p["text"] for p in LEG[v]["pages"]} for k, v in LEGAL_CASE.items()}
for k in LEGAL_PAGE:
    assert LEGAL_PAGE[k]["page:1"].count("Clause 1.3.") == 1

MOD = {m["module_id"]: m for m in METHODOLOGY}
T4E_IDS = [f"T4E.{n}" for n in range(1, 11)]
assert MOD["CP-4C"]["required"] == ["CP-0", "CP-1", "CP-2G", "CP-4", "CP-2A"] and MOD["CP-4C"]["optional"] == ["CP-3C"]
assert "edge_rules" not in MOD["CP-4C"] and sorted(MOD["CP-4C"]["table_ids"]) == sorted(T4E_IDS)
assert not any(t in m["table_ids"] for m in METHODOLOGY if m["module_id"] != "CP-4C" for t in T4E_IDS)

# --- 1. exact arithmetic -----------------------------------------------------------------------


def fr(x):
    return x if isinstance(x, Fraction) else Fraction(x)


def q38(x):
    f = fr(x)
    if f == 0:
        return D(0)
    with localcontext(CTX):
        return D(f.numerator) / D(f.denominator)


def div(a, b):
    with localcontext(CTX):
        v = a / b
    assert v == q38(fr(a) / fr(b)), (a, b)
    return v


def sub38(a, b):
    with localcontext(CTX):
        v = a - b
    assert v == q38(fr(a) - fr(b)), (a, b)
    return v


def sum38(xs):
    with localcontext(CTX):
        v = sum(xs, D(0))
    assert v == q38(sum((fr(x) for x in xs), Fraction(0))), xs
    return v


def ex(fn):
    with localcontext(CTX_EXACT):
        return fn()


def norm(d):
    t = format(d, "f")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return "0" if t in ("", "-0") else t


def show(d, uc, decimals=None):
    places, scale, suffix = {"amount": (0, 1, ""), "multiple": (2, 1, "x"), "percent": (1, 100, "%")}[uc]
    if decimals is not None:
        places = decimals
    r = (d * scale).quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP)
    assert not (r == 0 and d < 0), d
    body = f"{abs(r):,.{places}f}"
    return (f"({body})" if r < 0 else body) + suffix


def pp_diff(a, b):
    """percent minus percent: percentage points, (a - b) in the 38-digit context then .scaleb(2); shown is the exact text + ' pp'."""
    with localcontext(CTX):
        v = a - b
    assert v == q38(fr(a) - fr(b))
    return v.scaleb(2, context=CTX)


UC_UNIT = {"amount": "MILLIONS", "multiple": "MULTIPLE", "percent": "PERCENT"}
TOKEN = {"amount": "US$ m", "multiple": "x", "percent": "%"}

# --- 2. CP-1 operands and source rows ----------------------------------------------------------


def row_cells(page_text, label):
    for line in page_text.split("\n"):
        if line.startswith(label + "  "):
            return re.split(r"  +", line)
    raise AssertionError(label)


BS_HEADER = re.split(r"  +", next(l for l in PAGE["page:4"].split("\n") if l.startswith("Period end  ")))
assert BS_HEADER[5] == "Q4 2025-12-31"


def bs_value(label, column):
    cells = row_cells(PAGE["page:4"], label)
    return D(cells[BS_HEADER.index(column)])


TOTAL_DEBT = bs_value("Total debt", "Q4 2025-12-31")
CASH = bs_value("Cash and cash equivalents", "Q4 2025-12-31")
EBITDA_LTM = sum(D(x) for x in row_cells(PAGE["page:2"], "Reported EBITDA")[1:5])
_o = FIN["q4_ltm_derived_source_units"]
assert TOTAL_DEBT == D(_o["total_debt"]) and EBITDA_LTM == D(_o["ebitda"]) and TOTAL_DEBT - CASH == D(_o["net_debt"])
for _lab in ("Unsecured debt", "Subordinated debt", "Lease obligations", "Pension obligations"):
    assert bs_value(_lab, "Q4 2025-12-31") == 0
LTM_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
LTM_COLUMN = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
BS_PERIOD = "Q4 2025: 2025-12-31"
OBS_CLASS = CP2G_MAN["fact_selection_rule"]["observed_value_class"]
assert OBS_CLASS["total_debt"] == "source" and OBS_CLASS["ebitda"] == "calculated"


def _find(o, key):
    if isinstance(o, dict):
        if key in o:
            return o[key]
        for v in o.values():
            r = _find(v, key)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = _find(v, key)
            if r is not None:
                return r
    return None


T418 = {k: _find(CP3C_MAN, k) for k in ("term-loan.secured_status", "term-loan.seniority", "term-loan.facility_name")}
assert (T418["term-loan.secured_status"]["observed_on_promoted_head"], T418["term-loan.seniority"]["observed_on_promoted_head"],
        T418["term-loan.facility_name"]["observed_on_promoted_head"]) == ("SECURED", "SENIOR", "Northbridge Term Loan")


def cp1_facts(missing=()):
    out = {}
    for metric, amount in (("total_debt", TOTAL_DEBT), ("ebitda", EBITDA_LTM)):
        known = metric not in missing
        out[metric] = {"label": f"{LTM_COLUMN} · {metric}", "period": LTM_PERIOD, "status": "known" if known else "missing",
                       "amount_exact": norm(amount) if known else None, "value_class": OBS_CLASS[metric], "unit_class": "amount",
                       "cell_text": show(amount, "amount", None) if known else None,
                       "limitation": None if known else f"{metric} is not disclosed in the supplied statements."}
    return out


# --- 3. frozen upstream heads ------------------------------------------------------------------
YEARS = ["FY2026", "FY2027", "FY2028"]
CASE_ROW = {"base": "b", "down": "d"}


def fact_map(facts):
    return {f["fact_id"]: f for f in facts}


def cp2g_head(source_case):
    exp = CP2G_EXP["cases"][source_case]
    fm = fact_map(exp["facts"])
    ebitda = {}
    for c in ("base", "down"):
        for t, y in enumerate(YEARS):
            ebitda[(c, y)] = fm[f"T2H.4.{CASE_ROW[c]}{26 + t}.ebitda"]
    first = {c: fm[f"T2H.7.b01.{c}_first"] for c in ("base", "down")}
    return {"source": f"cases/cp2g-owner/expected.json cases.{source_case}", "ebitda": ebitda, "first": first, "facts": fm}


def cp2a_head():
    fm = fact_map(CP2A_EXP["cases"]["positive"]["facts"])
    return {"source": "cases/cp2a-owner/expected.json cases.positive", "facts": fm, "base_period": CP2A_EXP["cases"]["positive"]["base_period"]}


def cp4_head(case):
    cp4 = CP4_EXP[case]["CP-4"]
    fm = {f["fact_id"]: f for t in cp4["tables"] for r in t["rows"] for f in r["facts"]}
    return {"source": f"cases/cp4-owner/expected.json {case}.CP-4", "facts": fm, "status": cp4["status"]}


# --- 4. literal analyst submissions ------------------------------------------------------------
FIGS = {
    "total_debt_ltm": {"source": "cp1", "metric": "total_debt", "unit_token": "US$ m"},
    "ebitda_ltm": {"source": "cp1", "metric": "ebitda", "unit_token": "US$ m"},
    "ebitda_base_fy26": {"source": "cp2g", "fact_id": "T2H.4.b26.ebitda", "unit_token": "US$ m"},
    "ebitda_down_fy26": {"source": "cp2g", "fact_id": "T2H.4.d26.ebitda", "unit_token": "US$ m"},
}


def fig(name):
    return "{{FIG:" + name + "|" + FIGS[name]["unit_token"] + "}}"


QUOTE_TL = {"source_id": "legal-covenants", "locator": "page:1",
            "quote": "Clause 1.3. The agreement governs Northbridge Term Loan, facility_id term-loan, the sole senior secured term loan in the complete facility schedule."}
ROW_TP = "Trade payables  17  17.75  18.50  19.25  20.00  20.00"
ROW_OCL = "Other current liabilities  10  10  10  10  10  10"
assert ROW_TP in PAGE["page:4"] and ROW_OCL in PAGE["page:4"]
PCOL = "Q4 2025-12-31"
AP = "Analyst Interpretation"


def claim_(cid, name, kind, rank, src, rationale, quote=None, support=(), limitation=None, category=AP):
    return {"class_id": cid, "name": name, "kind": kind, "rank": rank, "amount_source": src,
            "amount_quote": ({"source_id": "financial", "locator": "page:4", "quote": quote} if quote else None),
            "period_column": PCOL if quote else None, "support": list(support), "rationale": rationale, "category": category, "limitation": limitation}


C_TL = claim_("c01", "Senior secured term loan", "secured_debt", "1", "cp1_total_debt",
              f"The only borrowed money is the term loan of {fig('total_debt_ltm')}, a secured senior facility, so it ranks first.", support=[QUOTE_TL],
              limitation="Collateral value, guarantees and enforcement terms are not supplied, so the claim is taken against the whole distributable value.")
C_TP = lambda rank: claim_("c02" if rank == "2" else "c03", "Trade payables", "unsecured_trade", rank, "source_row",
                           "Trade creditors are taken as unsecured claims sharing equally with other operating liabilities; no source states their ranking.",
                           quote=ROW_TP, limitation="Ranking is an analyst assumption without a source.")
C_OCL = lambda cid, rank: claim_(cid, "Other current liabilities", "other_liability", rank, "source_row",
                                 "Other current liabilities are taken as unsecured claims of the same rank as trade creditors; their nature is not described in the statements.",
                                 quote=ROW_OCL, limitation="Their nature and ranking are not described in any source.")
C_ADM = claim_("c02", "Administrative and priority claims", "administrative_priority", "2", "not_stated",
               "Restructuring costs and priority claims would rank after the secured term loan, but no supplied source states them.",
               limitation="No supplied source states these claims; they are not zero.")


def val_(cid, label, ecase, mult, rationale, limitation=None):
    return {"case_id": cid, "label": label, "ebitda_case": ecase, "ebitda_year": "FY2026", "multiple": mult, "rationale": rationale,
            "category": AP, "limitation": limitation}


V_BASE = val_("v01", "Base", "base", "4.0", f"Base valuation takes the base-case forecast earnings of {fig('ebitda_base_fy26')} at a mid-cycle multiple.",
              "The multiple is an analyst assumption without a market source.")
V_DOWN = val_("v02", "Downside", "down", "3.0", f"Downside valuation takes the downside forecast earnings of {fig('ebitda_down_fy26')} at a lower multiple for a weaker, higher-rate business.",
              "The multiple is an analyst assumption without a market source.")
V_STRESS = val_("v03", "Stress", "down", "2.0", f"Stress valuation keeps the downside earnings of {fig('ebitda_down_fy26')} and cuts the multiple to a distressed level.",
                "The multiple is an analyst assumption without a market source.")
V_STRESS_NA = dict(V_STRESS, multiple="not assessed", rationale="No multiple is assessed for the stress valuation because no supplied source or comparable supports one.",
                   limitation="Stress enterprise value is not assessed.")


def ful_(cid, ids, rationale):
    return {"case_id": cid, "class_ids": ids, "rationale": rationale, "category": AP, "limitation": "Judgment on analyst-assumed valuation."}


def plan_(cid, treatments, rationale):
    return {"case_id": cid, "treatments": [{"class_id": a, "treatment": b} for a, b in treatments], "rationale": rationale, "category": AP,
            "limitation": "Plan treatment is an analyst judgment, not a plan document."}


ASSESS = {"rationale": f"Against the term loan of {fig('total_debt_ltm')}, the base valuation pays every creditor, while the downside valuation breaks value among the unsecured creditors and the stress valuation breaks it at the term loan.",
          "category": AP, "confidence": "Medium", "limitation": "Multiples, ranks and plan treatment are analyst assumptions without a source citation."}
GAPS_POS = [{"gap": "Security package, guarantees and collateral value are not supplied.", "why_it_matters": "Recovery of the secured class rests on the whole distributable value, not on collateral.",
             "affected_analysis": "Secured class recovery", "severity": "Material", "action": "Obtain the security documents and a collateral valuation, then rerun the waterfall."}]

SUBMISSION = {
    "positive": {
        "claims": [C_TL, C_TP("2"), C_OCL("c03", "2")],
        "valuation": [V_BASE, V_DOWN, V_STRESS],
        "fulcrum": [ful_("v01", ["equity"], "Every creditor class is paid in full, so equity is the first class that does not receive a full claim."),
                    ful_("v02", ["c02", "c03"], "Value runs out among the unsecured operating creditors, who share equally."),
                    ful_("v03", ["c01"], "Value runs out at the secured term loan, so it is the fulcrum class.")],
        "plan": [plan_("v01", [("c01", "Paid in full"), ("c02", "Paid in full"), ("c03", "Paid in full"), ("equity", "Equity retained")], "All creditors are unimpaired and equity keeps the residual."),
                 plan_("v02", [("c01", "Paid in full"), ("c02", "Receives reorganised equity"), ("c03", "Receives reorganised equity"), ("equity", "No recovery")],
                       "The unsecured creditors take the reorganised equity and the old equity is cancelled."),
                 plan_("v03", [("c01", "Receives reorganised equity"), ("c02", "No recovery"), ("c03", "No recovery"), ("equity", "No recovery")],
                       "The term loan lenders take the reorganised equity and all junior classes are cancelled.")],
        "assessment": ASSESS, "gaps": GAPS_POS,
    },
    "gap": {
        "claims": [C_TL, C_ADM, dict(C_TP("3"), class_id="c03"), C_OCL("c04", "3")],
        "valuation": [V_BASE, V_DOWN, V_STRESS_NA],
        "fulcrum": [ful_("v01", [], "The fulcrum cannot be named because the administrative and priority claims are not stated."),
                    ful_("v02", [], "The fulcrum cannot be named because the administrative and priority claims are not stated."),
                    ful_("v03", [], "The fulcrum cannot be named because no stress value is assessed.")],
        "plan": [plan_("v01", [("c01", "Paid in full"), ("c02", "Not determined"), ("c03", "Not determined"), ("c04", "Not determined"), ("equity", "Not determined")], "Only the term loan can be placed."),
                 plan_("v02", [("c01", "Paid in full"), ("c02", "Not determined"), ("c03", "Not determined"), ("c04", "Not determined"), ("equity", "Not determined")], "Only the term loan can be placed."),
                 plan_("v03", [("c01", "Not determined"), ("c02", "Not determined"), ("c03", "Not determined"), ("c04", "Not determined"), ("equity", "Not determined")], "No treatment can be placed without a stress value.")],
        "assessment": dict(ASSESS, rationale=f"Against the term loan of {fig('total_debt_ltm')}, only the secured class can be placed in the base and downside valuations; every junior recovery is blocked by the unstated priority claims and the unassessed stress value.",
                           confidence="Low", limitation="Priority claims and the stress multiple are not available."),
        "gaps": [{"gap": "Administrative and priority claims and the stress multiple are not available.", "why_it_matters": "Without them no junior recovery and no fulcrum can be determined.",
                  "affected_analysis": "Junior recoveries and fulcrum", "severity": "Critical", "action": "Obtain a restructuring cost estimate and a supported stress multiple, then rerun."}],
    },
}
SUBMISSION["gap"]["claims"][2] = dict(C_TP("3"), class_id="c03")
SUBMISSION["gap"]["claims"][3] = C_OCL("c04", "3")
# composer-only variants of the positive submission
FIXTURE_SUB = {
    "fixture_ev_zero": deepcopy(SUBMISSION["positive"]),
    "fixture_ebitda_missing": deepcopy(SUBMISSION["positive"]),
    "fixture_debt_missing": deepcopy(SUBMISSION["positive"]),
}
FIXTURE_SUB["fixture_ev_zero"]["fulcrum"] = [SUBMISSION["positive"]["fulcrum"][0], ful_("v02", ["c01"], "With no earnings, value runs out at the first class."), ful_("v03", ["c01"], "With no earnings, value runs out at the first class.")]
FIXTURE_SUB["fixture_ev_zero"]["plan"] = [SUBMISSION["positive"]["plan"][0],
    plan_("v02", [("c01", "No recovery"), ("c02", "No recovery"), ("c03", "No recovery"), ("equity", "No recovery")], "All value is lost."),
    plan_("v03", [("c01", "No recovery"), ("c02", "No recovery"), ("c03", "No recovery"), ("equity", "No recovery")], "All value is lost.")]
FIXTURE_SUB["fixture_ebitda_missing"]["fulcrum"] = [SUBMISSION["positive"]["fulcrum"][0], ful_("v02", [], "No fulcrum can be named without earnings."), ful_("v03", [], "No fulcrum can be named without earnings.")]
FIXTURE_SUB["fixture_ebitda_missing"]["plan"] = [SUBMISSION["positive"]["plan"][0]] + [
    plan_(c, [(k, "Not determined") for k in ("c01", "c02", "c03", "equity")], "No treatment can be placed without earnings.") for c in ("v02", "v03")]
FIXTURE_SUB["fixture_debt_missing"]["fulcrum"] = [ful_(c, [], "No fulcrum can be named without the secured claim.") for c in ("v01", "v02", "v03")]
FIXTURE_SUB["fixture_debt_missing"]["plan"] = [plan_(c, [(k, "Not determined") for k in ("c01", "c02", "c03", "equity")], "No treatment can be placed without the secured claim.") for c in ("v01", "v02", "v03")]
FIXTURE_SUB["fixture_debt_missing"]["claims"] = [dict(C_TL, rationale="The term loan claim is not available in CP-1, so its size is unknown.")] + SUBMISSION["positive"]["claims"][1:]
_PLAIN = dict(ASSESS, rationale="The waterfall is shown only where its inputs are available; every other figure is blocked by the missing input.", confidence="Low", limitation="An input of the waterfall is missing.")
FIXTURE_SUB["fixture_debt_missing"]["assessment"] = _PLAIN
FIXTURE_SUB["fixture_ebitda_missing"]["assessment"] = _PLAIN
FIXTURE_SUB["fixture_ev_zero"]["assessment"] = dict(_PLAIN, rationale="With no earnings in the downside, enterprise value is nil and every creditor recovers nothing.")
for _k in ("fixture_ebitda_missing", "fixture_ev_zero"):
    FIXTURE_SUB[_k]["valuation"] = [FIXTURE_SUB[_k]["valuation"][0]] + [dict(v, rationale="This valuation keeps the downside forecast earnings.") for v in FIXTURE_SUB[_k]["valuation"][1:]]
FIXTURE_SUB["fixture_debt_missing"]["claims"][0] = dict(FIXTURE_SUB["fixture_debt_missing"]["claims"][0])
PCASE = {  # case -> (submission, cp2g source case, cp4 case, cp1 missing, legal pack, ebitda override)
    "positive": ("positive", "gap", "positive", (), "positive", None),
    "gap": ("gap", "gap", "gap", (), "gap", None),
    "fixture_ev_zero": ("fixture_ev_zero", "fixture_total_loss", "positive", (), "positive", None),
    "fixture_ebitda_missing": ("fixture_ebitda_missing", "gap", "positive", (), "positive", ("down", "FY2026")),
    "fixture_debt_missing": ("fixture_debt_missing", "gap", "positive", ("total_debt",), "positive", None),
}
EXEC = {"positive": "run", "gap": "run"}

# --- 5. the waterfall engine -------------------------------------------------------------------
NC_E = "Not calculable: EBITDA is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
R_EV_NA = "Not calculable: the EV multiple was not assessed"


def waterfall(classes, ev, ev_why):
    """classes: [{id, name, rank:int, claim:Decimal|None, why}]. Absolute priority by rank number (lowest first); classes of one rank share
    pro rata. A missing claim or EV blocks every figure that needs it (never 0). dist = claim x paid / group total (one division of an exact
    product); recovery = paid / group total (one division); both correctly rounded rationals (asserted)."""
    res = {c["id"]: {} for c in classes}
    avail, avail_why = ev, ev_why
    ahead, ahead_why = D(0), None
    brk, brk_why, brk_found, brk_through = None, None, False, None
    for r in sorted({c["rank"] for c in classes}):
        mem = [c for c in classes if c["rank"] == r]
        miss = next((c for c in mem if c["claim"] is None), None)
        tot = None if miss else ex(lambda: sum((c["claim"] for c in mem), D(0)))
        tot_why = miss["why"] if miss else None
        through = None if (tot is None or ahead is None) else ex(lambda: ahead + tot)
        through_why = ahead_why or tot_why
        paid = None
        if avail is not None and tot is not None:
            assert tot > 0
            paid = min(avail, tot)
        for c in mem:
            x = res[c["id"]]
            x.update(ahead=ahead, ahead_why=ahead_why, through=through, through_why=through_why, avail=avail, avail_why=avail_why, group=tot, group_why=tot_why)
            if paid is None:
                x.update(dist=None, rec=None, short=None, why=avail_why if avail is None else tot_why)
            else:
                rec = div(paid, tot)
                dist = div(ex(lambda: c["claim"] * paid), tot)
                x.update(dist=dist, rec=rec, short=sub38(c["claim"], dist), why=None)
        if not brk_found:
            if avail is None or tot is None:
                brk, brk_why, brk_found = None, (avail_why if avail is None else tot_why), True
            elif paid < tot:
                brk, brk_found, brk_through = [c["id"] for c in mem], True, through
        ahead, ahead_why = through, through_why
        if avail is None:
            pass
        elif tot is None:
            avail, avail_why = None, tot_why
        else:
            avail = ex(lambda: avail - paid)
    if not brk_found:
        brk = ["equity"]
    total = None if ahead is None else ahead
    return {"classes": res, "residual": avail, "residual_why": avail_why, "break": brk, "break_why": brk_why, "break_through": brk_through,
            "total_claims": total, "total_why": ahead_why}


# --- 6. composition ----------------------------------------------------------------------------
TABLES = {
    "T4E.1": "Upstream register", "T4E.2": "Claims register", "T4E.3": "Valuation scenarios", "T4E.4": "Waterfall allocation",
    "T4E.5": "Recovery by class", "T4E.6": "Attachment and detachment", "T4E.7": "Fulcrum identification", "T4E.8": "Plan treatment",
    "T4E.9": "Waterfall totals", "T4E.10": "Gaps ledger",
}
BLOCKS = {
    "recovery-by-class": {"title": "Recovery by class", "owner": "CP-4C", "kind": "dense", "producers": ["CP-4C"],
                          "tabs": [["T4E.5", "Recovery"], ["T4E.7", "Fulcrum"], ["T4E.8", "Plan treatment"]]},
    "value-allocation-claims": {"title": "Value allocation and claims", "owner": "CP-4C", "kind": "dense", "producers": ["CP-4C"],
                                "tabs": [["T4E.2", "Claims"], ["T4E.3", "Valuation"], ["T4E.4", "Waterfall"], ["T4E.6", "Attachment"]]},
}
EVIDENCE_TABLES = ["T4E.1", "T4E.9", "cp1_references", "cp2a_references", "cp2g_references", "cp4_references"]
LIMITATION_TABLES = ["T4E.10"]
GAP_SPELLING = {"missing": ("gap", "∅ G#"), "not_applicable": ("not_meaningful", "∅ G# n.m.")}
VAL_LIMIT = "Valuation on analyst-assumed multiples"
SECURITY_TEXT = {"unsecured_trade": "UNSECURED", "other_liability": "UNSECURED", "administrative_priority": "PRIORITY"}


def fp05(facts, tables):
    by_id = {x["fact_id"]: x for x in facts}
    out = {"pathway": "distressed_restructuring", "blocks": {}}

    def cell(fid):
        x = by_id[fid]
        if x["status"] == "known":
            return {"fact_id": fid, "field": x["field"], "shown": x["shown"], "state": "known"}
        st, tx = GAP_SPELLING[x["status"]]
        return {"fact_id": fid, "field": x["field"], "shown": tx, "state": st}

    for bid, b in BLOCKS.items():
        tabs = []
        for tid, label in b["tabs"]:
            t = next(t for t in tables if t["table_id"] == tid)
            tabs.append({"table_id": tid, "label": label, "rows": [{"row_id": r["row_id"], "label": r["label"], "cells": [cell(f) for f in r["fact_ids"]]} for r in t["rows"]]})
        out["blocks"][bid] = {"title": b["title"], "owner": b["owner"], "kind": b["kind"], "state": "populated", "tabs": tabs}
    out["other_blocks"] = "every other distressed_restructuring block keeps its idle wording; CP-4C fills only these two"
    out["evidence_rail_tables"], out["limitations_rail_tables"] = EVIDENCE_TABLES, LIMITATION_TABLES
    return out


def prose_texts(sub):
    for c in sub["claims"]:
        yield c["rationale"]
    for k in ("valuation", "fulcrum", "plan"):
        for x in sub[k]:
            yield x["rationale"]
    yield sub["assessment"]["rationale"]
    for g in sub["gaps"]:
        yield from (g["gap"], g["why_it_matters"], g["affected_analysis"], g["action"])


def spell_figs(text, figs):
    return re.sub(r"\{\{FIG:([a-z_0-9]+)\|[^}]*\}\}", lambda m: figs[m.group(1)]["spelled"], text)


def join_names(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def build_case(name):
    skey, g_case, c4_case, missing, legal_key, ebitda_override = PCASE[name]
    sub = SUBMISSION[skey] if skey in SUBMISSION else FIXTURE_SUB[skey]
    cp1 = cp1_facts(missing)
    g2 = cp2g_head(g_case)
    if ebitda_override:
        f = dict(g2["ebitda"][ebitda_override])
        f.update(status="missing", amount_exact=None, shown=None, limitation="Not calculable: downside FY2026 EBITDA is missing in CP-2G (synthetic upstream fixture)")
        g2["ebitda"] = {**g2["ebitda"], ebitda_override: f}
        g2["facts"] = {**g2["facts"], f["fact_id"]: f}
    c2a = cp2a_head()
    c4 = cp4_head(c4_case)
    claims, vals = sub["claims"], sub["valuation"]
    cname = {c["class_id"]: c["name"] for c in claims}
    facts, rows, claim_list, own_limits = [], {t: [] for t in TABLES}, [], []
    by_id = {}

    figs = {}
    for fname, f in FIGS.items():
        if f["source"] == "cp1":
            s = cp1[f["metric"]]
            figs[fname] = {"unit_token": f["unit_token"], "cp1_metric": f["metric"], "known": s["status"] == "known", "spelled": None if s["status"] != "known" else s["cell_text"] + " US$ m"}
        else:
            s = g2["facts"][f["fact_id"]]
            figs[fname] = {"unit_token": f["unit_token"], "fact_id": f["fact_id"], "known": s["status"] == "known", "spelled": None if s["status"] != "known" else s["shown"] + " US$ m"}

    def fact(table, row, field, label, **kw):
        rec = {"fact_id": f"{table}.{row}.{field}", "table_id": table, "row_id": row, "field": field, "label": label}
        rec.update(kw)
        facts.append(rec)
        by_id[rec["fact_id"]] = rec
        return rec

    def num(table, row, field, label, v, uc, formula, value_class="calculated", period=None, derives=(), unit=None, citations=None, keep_lineage=False):
        dec = 2 if (uc == "amount" and unit is None) else None
        extra = {"currency": "USD", "scale": "1000000"} if (uc == "amount" and unit is None) else {}
        shown = f"{norm(v)} {unit}" if unit else show(v, uc, dec)
        d_ = list(derives) if (value_class == "calculated" or keep_lineage) else []
        for d in d_:
            if d.startswith("cp1:"):
                assert cp1[d[4:]]["status"] == "known"
        rec = fact(table, row, field, label, status="known", unit=unit or UC_UNIT[uc], period=period or LTM_PERIOD, amount_exact=norm(v), shown=shown, **extra,
                   decimals=dec, value_class=value_class, formula=formula, calculation_id=f"calc:{table}.{row}.{field}" if value_class == "calculated" else None, derives_from=d_)
        if citations:
            rec["citations"] = citations
        return rec

    def gap(table, row, field, label, uc, reason, status="missing", period=None, unit=None):
        return fact(table, row, field, label, status=status, unit=unit or UC_UNIT[uc], period=period or LTM_PERIOD, amount_exact=None, shown=None, limitation=reason)

    def text(table, row, field, label, v, value_class=None, derives=(), citations=None):
        rec = fact(table, row, field, label, status="known", text=v, shown=v, value_class=value_class)
        if derives:
            rec["derives_from"] = list(derives)
        if citations:
            rec["citations"] = citations
        return rec

    def gap_text(table, row, field, label, reason, status="missing"):
        return fact(table, row, field, label, status=status, text=None, shown=None, limitation=reason)

    def reg(table, row_id, label, fields):
        rows[table].append({"row_id": row_id, "label": label, "fact_ids": [f"{table}.{row_id}.{f}" for f in fields]})

    def val_or_gap(table, row, field, label, v, why, uc, formula, derives, period=None, unit=None):
        if v is None:
            assert why, (table, row, field)
            gap(table, row, field, label, uc, why, period=period, unit=unit)
        else:
            num(table, row, field, label, v, uc, formula, derives=derives, period=period, unit=unit)

    # ---- claim amounts
    cls, amount_cite = [], {}
    for c in claims:
        if c["amount_source"] == "cp1_total_debt":
            s = cp1["total_debt"]
            amt = D(s["amount_exact"]) if s["status"] == "known" else None
            why = None if amt is not None else "Not calculable: total debt is missing in CP-1 for " + LTM_PERIOD
        elif c["amount_source"] == "source_row":
            cells = row_cells(PAGE["page:4"], c["amount_quote"]["quote"].split("  ")[0])
            assert c["amount_quote"]["quote"] in PAGE["page:4"]
            amt, why = D(cells[BS_HEADER.index(c["period_column"])]), None
            amount_cite[c["class_id"]] = [dict(c["amount_quote"])]
        else:
            amt, why = None, f"Not calculable: no supplied source states the claim of {c['name']}"
        cls.append({"id": c["class_id"], "name": c["name"], "rank": int(c["rank"]), "claim": amt, "why": why})

    # ---- valuation
    ev_in = {}
    for v in vals:
        ef = g2["ebitda"][(v["ebitda_case"], v["ebitda_year"])]
        e = D(ef["amount_exact"]) if ef["status"] == "known" else None
        m = None if v["multiple"] == "not assessed" else D(v["multiple"])
        if e is None:
            ev, why = None, ef["limitation"]
        elif m is None:
            ev, why = None, R_EV_NA
        else:
            ev, why = ex(lambda: e * m), None
        ev_in[v["case_id"]] = {"ebitda": e, "ebitda_why": ef["limitation"] if e is None else None, "mult": m, "ev": ev, "why": why, "ef": ef}
    wf = {v["case_id"]: waterfall(cls, ev_in[v["case_id"]]["ev"], ev_in[v["case_id"]]["why"]) for v in vals}

    pp_ = "pp"
    # ---- T4E.1
    for row, module, status, basis, read, lim in (
        ("u_cp1", "CP-1", "restricted", f"Base period {LTM_PERIOD}", "T4.10 total debt and EBITDA; T4.18 term loan security and seniority", "Inherits CP-1's own limitations."),
        ("u_cp2a", "CP-2A", "restricted", f"Base period {c2a['base_period']}", "T2B.1 name and shock sizes of the downside scenario CP-2G applied", "Shock sizes are analyst assumptions."),
        ("u_cp2g", "CP-2G", "restricted", "Forecast years FY2026 to FY2028 from the CP-1 twelve-month base", "T2H.4 forecast EBITDA and T2H.7 first year the free cash flow test is reached", "Forecast on analyst-assumed drivers."),
        ("u_cp4", "CP-4", c4["status"], "Executed term loan terms, current restatement", "T4C.11 facility map, T4.10 additional-debt consent, T4.13 lender protection rating",
         "Selected executed terms only; security, guarantees, default, cure and voting terms are not supplied."),
        ("u_cp3c", "CP-3C", "not part of this run", "Not applicable", "Nothing read", "CP-3C (refinancing and liability management) is an optional input that this version never reads."),
    ):
        for fld, lab, val in (("module", "Module", module), ("status", "Status", status), ("basis", "Basis", basis), ("read", "Read", read), ("limitation", "Limitation", lim)):
            text("T4E.1", row, fld, lab, val)
        reg("T4E.1", row, module, ["module", "status", "basis", "read", "limitation"])

    # ---- T4E.2 claims register
    facility = c4["facts"]["T4C.11.r01.facility"]
    rating = c4["facts"]["T4.13.rating.rating"]
    addl = c4["facts"]["T4.10.r02.conditions"]
    for c, k in zip(claims, cls):
        r = c["class_id"]
        text("T4E.2", r, "name", "Class", c["name"], "analyst_judgment")
        text("T4E.2", r, "kind", "Kind", c["kind"], "analyst_judgment")
        text("T4E.2", r, "rank", "Rank", c["rank"], "analyst_judgment")
        if c["kind"] == "secured_debt":
            text("T4E.2", r, "security", "Security", T418["term-loan.secured_status"]["observed_on_promoted_head"], derives=["cp1:term-loan.secured_status"], citations=c["support"] or None)
        else:
            text("T4E.2", r, "security", "Security", SECURITY_TEXT[c["kind"]], "analyst_judgment")
        if k["claim"] is None:
            gap("T4E.2", r, "claim", "Claim", "amount", k["why"], period=BS_PERIOD)
        elif c["amount_source"] == "cp1_total_debt":
            num("T4E.2", r, "claim", "Claim", k["claim"], "amount", "CP-1 total debt", derives=["cp1:total_debt"])
        else:
            num("T4E.2", r, "claim", "Claim", k["claim"], "amount", "quoted statement figure", "source", period=BS_PERIOD, citations=amount_cite[r])
        basis = {"cp1_total_debt": f"CP-1 T4.10 total debt · {LTM_PERIOD}", "source_row": f"financial page:4, column {c['period_column']}", "not_stated": "No supplied source states this claim"}[c["amount_source"]]
        text("T4E.2", r, "basis", "Basis", basis)
        if c["kind"] == "secured_debt":
            text("T4E.2", r, "facility", "Facility", facility["text"], derives=["cp4:T4C.11.r01.facility"])
            text("T4E.2", r, "lender_protection", "Lender protection", rating["text"], derives=["cp4:T4.13.rating.rating"])
            text("T4E.2", r, "additional_debt", "Additional debt", addl["text"], derives=["cp4:T4.10.r02.conditions"])
        else:
            for fld, lab in (("facility", "Facility"), ("lender_protection", "Lender protection"), ("additional_debt", "Additional debt")):
                gap_text("T4E.2", r, fld, lab, "The class is not a facility governed by the legal source", "not_applicable")
        reg("T4E.2", r, c["name"], ["name", "kind", "rank", "security", "claim", "basis", "facility", "lender_protection", "additional_debt"])
    text("T4E.2", "eq", "name", "Class", "Equity")
    text("T4E.2", "eq", "kind", "Kind", "equity")
    text("T4E.2", "eq", "rank", "Rank", "Residual")
    text("T4E.2", "eq", "security", "Security", "RESIDUAL")
    gap("T4E.2", "eq", "claim", "Claim", "amount", "Equity is the residual claimant and has no claim amount", status="not_applicable", period=BS_PERIOD)
    text("T4E.2", "eq", "basis", "Basis", "Residual after all claims")
    for fld, lab in (("facility", "Facility"), ("lender_protection", "Lender protection"), ("additional_debt", "Additional debt")):
        gap_text("T4E.2", "eq", fld, lab, "The class is not a facility governed by the legal source", "not_applicable")
    reg("T4E.2", "eq", "Equity", ["name", "kind", "rank", "security", "claim", "basis", "facility", "lender_protection", "additional_debt"])

    # ---- T4E.3 valuation
    down_lineage = next(d for d in g2["facts"]["T2H.4.d26.ebitda"]["derives_from"] if d.startswith("cp2a:T2B.1."))
    scen_row = down_lineage.split(".")[2]
    for v_ in vals:  # every downside EBITDA year used shares one CP-2A scenario lineage
        if v_["ebitda_case"] == "down":
            assert down_lineage in g2["ebitda"][("down", v_["ebitda_year"])]["derives_from"], (name, v_["case_id"])
    sc_name, sc_dec = c2a["facts"][f"T2B.1.{scen_row}.name"], c2a["facts"][f"T2B.1.{scen_row}.ebitda_decline"]
    for v in vals:
        r = v["case_id"]
        e = ev_in[r]
        fy = v["ebitda_year"]
        text("T4E.3", r, "scenario", "Valuation", v["label"], "analyst_judgment")
        text("T4E.3", r, "ebitda_basis", "EBITDA basis", f"CP-2G {'base' if v['ebitda_case'] == 'base' else 'downside'} case {fy}")
        ef = e["ef"]
        assert ef["fact_id"] == f"T2H.4.{CASE_ROW[v['ebitda_case']]}{26 + YEARS.index(fy)}.ebitda" and ef["period"].startswith(fy + ":")
        ef_id = ef["fact_id"]
        val_or_gap("T4E.3", r, "ebitda", "EBITDA", e["ebitda"], e["ebitda_why"], "amount", f"Copy of CP-2G {ef_id}", [f"cp2g:{ef_id}"], period=ef["period"])
        if v["multiple"] == "not assessed":
            gap("T4E.3", r, "multiple", "EV multiple", "multiple", R_EV_NA, period=ef["period"])
        else:
            num("T4E.3", r, "multiple", "EV multiple", e["mult"], "multiple", "analyst input", "analyst_judgment", period=ef["period"])
        ev_why = e["why"]
        val_or_gap("T4E.3", r, "ev", "Enterprise value", e["ev"], ev_why, "amount", "EBITDA x EV multiple", [f"T4E.3.{r}.ebitda", f"T4E.3.{r}.multiple"], period=ef["period"])
        imp = None if e["ev"] is None else div(e["ev"], EBITDA_LTM)
        val_or_gap("T4E.3", r, "implied_ltm_multiple", "Implied multiple of CP-1 EBITDA", imp, ev_why, "multiple", "Enterprise value / CP-1 EBITDA", [f"T4E.3.{r}.ev", "cp1:ebitda"])
        text("T4E.3", r, "first_break", "First year free cash flow at or below zero (CP-2G)", g2["first"][v["ebitda_case"]]["text"], derives=[f"cp2g:T2H.7.b01.{v['ebitda_case']}_first"])
        if v["ebitda_case"] == "down":
            text("T4E.3", r, "cp2a_scenario", "CP-2A scenario", sc_name["text"], derives=[f"cp2a:T2B.1.{scen_row}.name"])
            num("T4E.3", r, "ebitda_decline", "CP-2A EBITDA decline", D(sc_dec["amount_exact"]), "percent", f"Copy of CP-2A T2B.1.{scen_row}.ebitda_decline", sc_dec["value_class"],
                derives=[f"cp2a:T2B.1.{scen_row}.ebitda_decline"], keep_lineage=True)
        else:
            gap_text("T4E.3", r, "cp2a_scenario", "CP-2A scenario", "The base valuation uses no CP-2A scenario", "not_applicable")
            gap("T4E.3", r, "ebitda_decline", "CP-2A EBITDA decline", "percent", "The base valuation uses no CP-2A scenario", status="not_applicable")
        reg("T4E.3", r, v["label"], ["scenario", "ebitda_basis", "ebitda", "multiple", "ev", "implied_ltm_multiple", "first_break", "cp2a_scenario", "ebitda_decline"])

    # ---- T4E.4 / T4E.5 / T4E.6 / T4E.8
    first_case = vals[0]["case_id"]
    treat = {p["case_id"]: {t["class_id"]: t["treatment"] for t in p["treatments"]} for p in sub["plan"]}
    for v in vals:
        r0, w = v["case_id"], wf[v["case_id"]]
        ev_e = ev_in[r0]
        period = ev_in[v["case_id"]]["ef"]["period"]
        for c, k in zip(claims, cls):
            x = w["classes"][k["id"]]
            r = f"{r0}{k['id']}"
            lab = f"{v['label']} · {c['name']}"
            val_or_gap("T4E.4", r, "claim", "Claim", k["claim"], k["why"], "amount", "From T4E.2", [f"T4E.2.{k['id']}.claim"], period=period)
            val_or_gap("T4E.4", r, "value_available", "Value available to the class", x["avail"], x["avail_why"], "amount", "Enterprise value less distributions to better-ranked classes",
                       [f"T4E.3.{r0}.ev"] + ([f"T4E.4.{r0}{o['id']}.distribution" for o in cls if o["rank"] < k["rank"]]), period=period)
            val_or_gap("T4E.4", r, "distribution", "Distribution", x["dist"], x["why"], "amount", "Claim x value paid to the rank / total claims of the rank",
                       [f"T4E.4.{r}.claim", f"T4E.4.{r}.value_available"] + [f"T4E.4.{r0}{o['id']}.claim" for o in cls if o["rank"] == k["rank"]], period=period)
            val_or_gap("T4E.4", r, "shortfall", "Shortfall", x["short"], x["why"], "amount", "Claim - distribution", [f"T4E.4.{r}.claim", f"T4E.4.{r}.distribution"], period=period)
            reg("T4E.4", r, lab, ["claim", "value_available", "distribution", "shortfall"])
            val_or_gap("T4E.5", r, "recovery", "Recovery", x["rec"], x["why"], "percent", "Value paid to the rank / total claims of the rank", [f"T4E.4.{r}.distribution", f"T4E.4.{r}.claim"], period=period)
            base_r = wf[first_case]["classes"][k["id"]]["rec"]
            if r0 == first_case:
                gap("T4E.5", r, "vs_first_pp", "Change from first valuation", "percent", "The first valuation is the comparison base", status="not_applicable", unit=pp_)
            elif x["rec"] is None or base_r is None:
                gap("T4E.5", r, "vs_first_pp", "Change from first valuation", "percent", x["why"] or wf[first_case]["classes"][k["id"]]["why"], unit=pp_)
            else:
                num("T4E.5", r, "vs_first_pp", "Change from first valuation", pp_diff(x["rec"], base_r), "percent", "(recovery - first-valuation recovery) x 100, percentage points",
                    derives=[f"T4E.5.{r}.recovery", f"T4E.5.{first_case}{k['id']}.recovery"], unit=pp_, period=period)
            reg("T4E.5", r, lab, ["recovery", "vs_first_pp"])
            # attachment
            e = ev_e["ebitda"]
            e_why = ev_e["ebitda_why"] or NC_E
            for fld, lab_, val_, why_ in (("claims_ahead", "Claims ahead", x["ahead"], x["ahead_why"]), ("claims_through", "Claims through the class", x["through"], x["through_why"])):
                val_or_gap("T4E.6", r, fld, lab_, val_, why_, "amount", "Claims of better-ranked classes" if fld == "claims_ahead" else "Claims ahead + claims of the rank",
                           [f"T4E.4.{r0}{o['id']}.claim" for o in cls if o["rank"] < k["rank"] or (fld == "claims_through" and o["rank"] == k["rank"])], period=period)
            for fld, lab_, num_, nwhy in (("attach_multiple", "Attachment multiple", x["ahead"], x["ahead_why"]), ("detach_multiple", "Detachment multiple", x["through"], x["through_why"])):
                if num_ is None:
                    gap("T4E.6", r, fld, lab_, "multiple", nwhy, period=period)
                elif e is None:
                    gap("T4E.6", r, fld, lab_, "multiple", e_why, period=period)
                elif e <= 0:
                    gap("T4E.6", r, fld, lab_, "multiple", NC_E, period=period)
                else:
                    num("T4E.6", r, fld, lab_, div(num_, e), "multiple", "Claims ahead / EBITDA" if fld == "attach_multiple" else "Claims through the class / EBITDA",
                        derives=[f"T4E.6.{r}.{'claims_ahead' if fld == 'attach_multiple' else 'claims_through'}", f"T4E.3.{r0}.ebitda"], period=period)
            reg("T4E.6", r, lab, ["claims_ahead", "claims_through", "attach_multiple", "detach_multiple"])
            # plan treatment
            tr = treat[r0][k["id"]]
            text("T4E.8", r, "treatment", "Treatment", tr, "analyst_judgment")
            text("T4E.8", r, "fit", "Fit with the waterfall", "Fits the waterfall" if x["rec"] is not None else "Not determinable", derives=[f"T4E.5.{r}.recovery"] if x["rec"] is not None else [])
            reg("T4E.8", r, lab, ["treatment", "fit"])
        # equity row
        r = f"{r0}eq"
        lab = f"{v['label']} · Equity"
        gap("T4E.4", r, "claim", "Claim", "amount", "Equity has no claim amount", status="not_applicable", period=period)
        val_or_gap("T4E.4", r, "value_available", "Value available to the class", w["residual"], w["residual_why"], "amount", "Enterprise value less all creditor distributions",
                   [f"T4E.3.{r0}.ev"] + [f"T4E.4.{r0}{o['id']}.distribution" for o in cls], period=period)
        val_or_gap("T4E.4", r, "distribution", "Distribution", w["residual"], w["residual_why"], "amount", "Residual value", [f"T4E.4.{r}.value_available"], period=period)
        gap("T4E.4", r, "shortfall", "Shortfall", "amount", "Equity has no claim amount", status="not_applicable", period=period)
        reg("T4E.4", r, lab, ["claim", "value_available", "distribution", "shortfall"])
        for fld, lab_ in (("recovery", "Recovery"), ("vs_first_pp", "Change from first valuation")):
            gap("T4E.5", r, fld, lab_, "percent", "Equity has no claim amount, so no recovery percentage", status="not_applicable", unit=pp_ if fld == "vs_first_pp" else None, period=period)
        reg("T4E.5", r, lab, ["recovery", "vs_first_pp"])
        tr = treat[r0]["equity"]
        text("T4E.8", r, "treatment", "Treatment", tr, "analyst_judgment")
        text("T4E.8", r, "fit", "Fit with the waterfall", "Fits the waterfall" if w["residual"] is not None else "Not determinable", derives=[f"T4E.4.{r}.distribution"] if w["residual"] is not None else [])
        reg("T4E.8", r, lab, ["treatment", "fit"])

    # ---- T4E.7 fulcrum, T4E.9 totals
    fulc = {f["case_id"]: f["class_ids"] for f in sub["fulcrum"]}
    for v in vals:
        r, w = v["case_id"], wf[v["case_id"]]
        period = ev_in[v["case_id"]]["ef"]["period"]
        if w["break"] is None:
            gap_text("T4E.7", r, "value_break", "Where value breaks", w["break_why"])
        elif w["break"] == ["equity"]:
            text("T4E.7", r, "value_break", "Where value breaks", "Equity (every creditor class is paid in full)", derives=[f"T4E.5.{r}{k['id']}.recovery" for k in cls])
        else:
            text("T4E.7", r, "value_break", "Where value breaks", join_names([cname[i] for i in w["break"]]), derives=[f"T4E.5.{r}{i}.recovery" for i in w["break"]])
        named = fulc[r]
        text("T4E.7", r, "analyst_fulcrum", "Fulcrum named by the analyst", join_names([("Equity" if i == "equity" else cname[i]) for i in named]) if named else "None named", "analyst_judgment")
        text("T4E.7", r, "agreement", "Agreement", "Agrees with the waterfall" if (w["break"] is not None and sorted(named) == sorted(w["break"])) else "Value break not determinable",
             derives=[f"T4E.7.{r}.value_break", f"T4E.7.{r}.analyst_fulcrum"] if w["break"] is not None else [])
        tot, tw = w["total_claims"], w["total_why"]
        evv, evw = ev_in[r]["ev"], ev_in[r]["why"]
        cover = None if (tot is None or evv is None) else div(evv, tot)
        val_or_gap("T4E.7", r, "ev_cover", "Enterprise value / total claims", cover, evw or tw, "multiple", "Enterprise value / total claims", [f"T4E.3.{r}.ev", f"T4E.9.{r}.total_claims"], period=period)
        if w["break"] == ["equity"]:
            gap("T4E.7", r, "break_multiple", "EBITDA multiple needed to cover the fulcrum class", "multiple", "No creditor class is impaired", status="not_applicable", period=period)
        elif w["break"] is None:
            gap("T4E.7", r, "break_multiple", "EBITDA multiple needed to cover the fulcrum class", "multiple", w["break_why"], period=period)
        else:
            e = ev_in[r]["ebitda"]
            if e is None or e <= 0:
                gap("T4E.7", r, "break_multiple", "EBITDA multiple needed to cover the fulcrum class", "multiple", ev_in[r]["ebitda_why"] or NC_E, period=period)
            else:
                num("T4E.7", r, "break_multiple", "EBITDA multiple needed to cover the fulcrum class", div(w["break_through"], e), "multiple", "Claims through the fulcrum rank / EBITDA",
                    derives=[f"T4E.6.{r}{w['break'][0]}.detach_multiple"], period=period)
        reg("T4E.7", r, v["label"], ["value_break", "analyst_fulcrum", "agreement", "ev_cover", "break_multiple"])
        # totals
        distsum = None if any(x["dist"] is None for x in w["classes"].values()) else sum38([x["dist"] for x in w["classes"].values()])
        val_or_gap("T4E.9", r, "ev", "Enterprise value", evv, evw, "amount", "From T4E.3", [f"T4E.3.{r}.ev"], period=period)
        val_or_gap("T4E.9", r, "total_claims", "Total creditor claims", tot, tw, "amount", "Sum of the claims of the creditor classes", [f"T4E.2.{k['id']}.claim" for k in cls], period=period)
        val_or_gap("T4E.9", r, "creditor_distributions", "Distributions to creditors", distsum, next((x["why"] for x in w["classes"].values() if x["dist"] is None), None), "amount",
                   "Sum of creditor distributions", [f"T4E.4.{r}{k['id']}.distribution" for k in cls], period=period)
        val_or_gap("T4E.9", r, "equity_residual", "Residual to equity", w["residual"], w["residual_why"], "amount", "From T4E.4", [f"T4E.4.{r}eq.distribution"], period=period)
        bal = None if (evv is None or distsum is None or w["residual"] is None) else sub38(sub38(evv, distsum), w["residual"])
        if bal is not None:
            assert bal == 0
        val_or_gap("T4E.9", r, "balance", "Balance", bal, evw or (w["residual_why"]), "amount", "Enterprise value - creditor distributions - residual", [f"T4E.9.{r}.ev", f"T4E.9.{r}.creditor_distributions", f"T4E.9.{r}.equity_residual"], period=period)
        reg("T4E.9", r, v["label"], ["ev", "total_claims", "creditor_distributions", "equity_residual", "balance"])

    for n, g in enumerate(sub["gaps"], 1):
        r = f"g{n:02d}"
        text("T4E.10", r, "id", "Gap id", f"CP-4C-GAP-{n:03d}")
        for fld, lab in (("gap", "Gap"), ("why_it_matters", "Why it matters"), ("affected_analysis", "Affected analysis")):
            text("T4E.10", r, fld, lab, g[fld], "analyst_judgment")
        text("T4E.10", r, "severity", "Severity", g["severity"])
        text("T4E.10", r, "action", "Action", g["action"], "analyst_judgment")
        reg("T4E.10", r, f"Gap {n}", ["id", "gap", "why_it_matters", "affected_analysis", "severity", "action"])

    # ---- references: upstream facts copied verbatim
    named = []
    for t_ in prose_texts(sub):
        named += re.findall(r"FIG:([a-z_0-9]+)", t_)
    named = list(dict.fromkeys(named))
    for n_ in named:
        assert figs[n_]["known"], (name, n_)

    def up_row(n, f, figure=None):
        return {"row_id": f"ref{n:02d}", "figure": figure, "fact_id": f["fact_id"], "label": f.get("label") or f.get("column"), "period": f.get("period"), "status": f["status"],
                "unit": f.get("unit"), "shown": f.get("shown") or f.get("text"), "text": f.get("text"), "value_class": f.get("value_class"), "amount_exact": f.get("amount_exact"),
                "limitation": f.get("limitation")}

    cp1_rows = []
    for n, metric in enumerate(("total_debt", "ebitda"), 1):
        s_ = cp1[metric]
        fn = next((k for k in named if FIGS[k].get("metric") == metric), None)
        cp1_rows.append({"row_id": f"ref{n:02d}", "figure": fn, "label": f"{s_['label']} · {s_['period']}", "cp1_label": s_["label"], "period": s_["period"], "status": s_["status"],
                         "unit": "US$ m", "shown": None if s_["status"] != "known" else s_["cell_text"] + " US$ m", "cell_text": s_["cell_text"], "value_class": s_["value_class"],
                         "amount_exact": s_["amount_exact"], "limitation": s_["limitation"],
                         "fact_id": "bound at run time: the unique T4.10 fact with label cp1_label (manifest.json fact_selection_rule); the module carries the CP-1 fact verbatim under this fact_id"})
    for fld, metric in (("secured_status", "term-loan.secured_status"), ("seniority", "term-loan.seniority")):
        obs = T418[metric]["observed_on_promoted_head"]
        cp1_rows.append({"row_id": f"ref{len(cp1_rows) + 1:02d}", "figure": None, "label": f"T4.18 · term-loan · {fld} · q4-2025", "cp1_label": None, "period": "q4-2025", "status": "known",
                         "unit": None, "shown": obs, "cell_text": obs, "text": obs, "value_class": "source", "amount_exact": None, "limitation": None,
                         "fact_id": f"bound at run time: the unique T4.18 fact with facility_id term-loan and field {fld} at the quarter period q4-2025 (manifest.json fact_selection_rule.cp1_t418); the module carries the CP-1 fact verbatim under this fact_id"})
    cp1_refs = {"table_id": "cp1_references", "title": "CP-1 facts referenced in CP-4C text and copied into T4E.2 and T4E.3", "row_header": "CP-1 fact", "rows": cp1_rows}
    g_rows, n, seen_ef = [], 0, set()
    for v in vals:
        ef_ = ev_in[v["case_id"]]["ef"]
        if ef_["fact_id"] in seen_ef:  # one reference row per distinct fact id (contracts.py:252 "Duplicate fact identity")
            continue
        seen_ef.add(ef_["fact_id"])
        n += 1
        g_rows.append(up_row(n, ef_, next((k for k in named if FIGS[k].get("fact_id") == ef_["fact_id"]), None)))
    for c_ in ("base", "down"):
        n += 1
        g_rows.append(up_row(n, g2["first"][c_]))
    cp2g_refs = {"table_id": "cp2g_references", "title": "CP-2G facts read by CP-4C (T2H.4 EBITDA, T2H.7 first year of the free cash flow test)", "row_header": "CP-2G fact", "rows": g_rows}
    cp2a_refs = {"table_id": "cp2a_references", "title": "CP-2A facts read by CP-4C (T2B.1 scenario applied by CP-2G)", "row_header": "CP-2A fact",
                 "rows": [up_row(i + 1, c2a["facts"][f"T2B.1.{scen_row}.{fld}"]) for i, fld in enumerate(("name", "ebitda_decline", "interest_increase"))]}
    cp4_refs = {"table_id": "cp4_references", "title": "CP-4 facts read by CP-4C (T4C.11, T4.10, T4.13)", "row_header": "CP-4 fact",
                "rows": [up_row(i + 1, c4["facts"][fid]) for i, fid in enumerate(("T4C.11.r01.facility_id", "T4C.11.r01.facility", "T4.10.r02.permits", "T4.10.r02.conditions", "T4.13.rating.rating"))]}

    for x in facts:
        for d_ in x.get("derives_from", []):
            if x["status"] == "known" and not d_.startswith(("cp1:", "cp2a:", "cp2g:", "cp4:")):
                assert by_id[d_]["status"] == "known", (name, x["fact_id"], d_)

    # ---- claims
    def ref(fid, token):
        return "{" + fid + "|" + token + "}" if by_id[fid]["status"] == "known" else "[" + fid + "]"

    def rendered(t_):
        t_ = re.sub(r"\{([A-Za-z0-9_.:-]+)\|([^}]*)\}", lambda m: by_id[m.group(1)]["shown"] + (" US$ m" if m.group(2) == "US$ m" else ""), t_)
        return t_

    def claim(cid, text_, limitation, refs=(), python=False):
        if python:
            assert limitation is None
            limitation = VAL_LIMIT
        e = {"claim_id": cid, "text": text_, "limitation": limitation, "citations": [], "cp1_references": list(refs)}
        if refs:
            e["text_rendered"] = spell_figs(text_, figs)
        claim_list.append(e)

    for c in claims:
        claim(f"T4E.2.{c['class_id']}.rationale", c["rationale"], c["limitation"], re.findall(r"FIG:([a-z_0-9]+)", c["rationale"]))
    for v in vals:
        claim(f"T4E.3.{v['case_id']}.rationale", v["rationale"], v["limitation"], re.findall(r"FIG:([a-z_0-9]+)", v["rationale"]))
    for v in vals:
        r = v["case_id"]
        claim(f"T4E.3.{r}.ev", f"In the {v['label'].lower()} valuation, enterprise value is {ref(f'T4E.3.{r}.ev', 'US$ m')} on EBITDA of {ref(f'T4E.3.{r}.ebitda', 'US$ m')}.", None, python=True)
    for v in vals:
        r = v["case_id"]
        parts = "; ".join(f"{c['name']} {ref(f'T4E.5.{r}{c['class_id']}.recovery', '%')}" for c in claims)
        claim(f"T4E.5.{r}", f"In the {v['label'].lower()} valuation the classes recover as follows: {parts}.", None, python=True)
    for f_ in sub["fulcrum"]:
        claim(f"T4E.7.{f_['case_id']}.rationale", f_["rationale"], f_["limitation"], [])
    for v in vals:
        r, w = v["case_id"], wf[v["case_id"]]
        lab = v["label"].lower()
        if w["break"] is None:
            t_ = f"In the {lab} valuation the fulcrum cannot be determined: [T4E.7.{r}.value_break]."
        elif w["break"] == ["equity"]:
            t_ = f"In the {lab} valuation every creditor class is paid in full and equity is the residual claimant."
        else:
            nm = join_names([cname[i] for i in w["break"]])
            t_ = (f"In the {lab} valuation value breaks at {nm}, which {'is' if len(w['break']) == 1 else 'are'} the fulcrum; "
                  f"{'it is' if len(w['break']) == 1 else 'they are'} covered in full only at an EBITDA multiple of {ref(f'T4E.7.{r}.break_multiple', 'x')}.")
        claim(f"T4E.7.{r}.fulcrum", t_, None, python=True)
    for p_ in sub["plan"]:
        claim(f"T4E.8.{p_['case_id']}.rationale", p_["rationale"], p_["limitation"], [])
    a = sub["assessment"]
    claim("T4E.3.assessment", a["rationale"], a["limitation"], re.findall(r"FIG:([a-z_0-9]+)", a["rationale"]))
    for c in claim_list:
        if "text_rendered" not in c:
            c["text_rendered"] = rendered(c["text"])

    # ---- own limitations
    L = own_limits.append
    L("Multiples, claim ranks and plan treatment are analyst assumptions without a source citation; no market or restructuring-plan source is an input.")
    L("Value available to claims is the enterprise value only: balance-sheet cash is not added and restructuring, administrative and financing costs are not deducted unless a claim class states them.")
    L("The waterfall applies strict priority by the analyst's rank number; classes of one rank share pro rata. Collateral value, guarantees, structural subordination and intercreditor terms are not modelled.")
    L("Claims are the 31 December 2025 balances: accrued interest, fees, make-whole amounts, lease and pension claims, contingent and rejection-damage claims are not stated in any source and are not modelled; they are not zero.")
    L("New-money or priming debt is not modelled: the legal source requires the consent of every lender for additional debt, so no debt-in-possession financing is assumed.")
    L("Enterprise value is the analyst's multiple applied to a CP-2G forecast EBITDA that rests on analyst-assumed drivers; it is not a market or court valuation.")
    L("The fulcrum is the first rank whose recovery is below its claim; the analyst's named fulcrum is checked against it. Plan treatment is checked for fit with the recovery, not for legal feasibility.")
    L("Recoveries are not probability-weighted and the valuations are not scenarios of equal likelihood.")
    L("CP-3C (refinancing and liability management) is an optional input that this version never reads.")
    L("The lender protection rating is read from CP-4 and stays Insufficient Information: security, guarantee, default, cure and voting terms are not supplied.")
    for k in cls:
        if k["claim"] is None:
            L(f"The claim of {k['name']} is not available: {k['why'].replace('Not calculable: ', '')}; every recovery at or below its rank is Not calculable.")
    for v in vals:
        e = ev_in[v["case_id"]]
        if e["ev"] is None:
            L(f"The enterprise value of the {v['label'].lower()} valuation is not available: {(e['why'] or '').replace('Not calculable: ', '')}; every recovery in it is Not calculable.")
    for v in vals:
        if wf[v["case_id"]]["break"] is None and ev_in[v["case_id"]]["ev"] is not None:
            L(f"The fulcrum of the {v['label'].lower()} valuation cannot be determined, so the analyst names none.")
    for g in sub["gaps"]:
        L(f"Gap ({g['severity']}): {g['gap']}")

    tables = [{"table_id": t, "title": title, "rows": rows[t]} for t, title in TABLES.items()]
    summary = {}
    for v in vals:
        w = wf[v["case_id"]]
        summary[v["case_id"]] = {"ev": None if ev_in[v["case_id"]]["ev"] is None else norm(ev_in[v["case_id"]]["ev"]), "break": w["break"],
                                 "residual": None if w["residual"] is None else norm(w["residual"]),
                                 "recovery": {i: (None if x["rec"] is None else norm(x["rec"])) for i, x in w["classes"].items()},
                                 "distribution": {i: (None if x["dist"] is None else norm(x["dist"])) for i, x in w["classes"].items()}}
    return {
        "legal_pack": f"cases/legal/manifest.json cases[{LEGAL_CASE[legal_key]}]", "cp1_inputs": cp1, "cp2g_head": {"source": g2["source"], "ebitda_override": bool(ebitda_override)},
        "cp2a_head": {"source": c2a["source"], "scenario": scen_row, "scenario_name": sc_name["text"]}, "cp4_head": {"source": c4["source"], "status": c4["status"]},
        "figures": {k: {kk: vv for kk, vv in v.items() if kk != "known"} for k, v in figs.items()},
        "cp1_references": cp1_refs, "cp2g_references": cp2g_refs, "cp2a_references": cp2a_refs, "cp4_references": cp4_refs,
        "waterfall": summary, "facts": facts, "tables": tables, "claims": claim_list, "own_limitations": own_limits,
        "module_status": "restricted" if name in EXEC else "composer_only", "FP05": fp05(facts, tables),
    }


# --- 7. the phrase guard (CP-4C owns fulcrum and recovery conclusions) -------------------------
# Transcription of business_context.PROHIBITED / NEAR_INSTRUMENT for the two kinds CP-4C keeps; the 'recovery conclusion' kind is NOT checked
# (CP-4C is the module that states recoveries and the fulcrum). 'instrument action' (ACTIONS) is not a CP-1A kind and is not checked.
PEER = ("peer ranking", "ranks above", "ranks below", "ranks among", "ranked first", "ranked last", "top quartile", "best-in-class", "best in class",
        "outperforms peers", "underperforms peers", "versus peers", "relative to peers", "compared with peers", "against its peers")
INSTR = ("we recommend", "recommend buying", "recommend selling", "buy recommendation", "sell recommendation", "should buy", "should sell", "overweight",
         "underweight", "preferred instrument", "instrument recommendation")
NEAR_INSTR = ("prefer the", "recommend", "recommendation")
NOUN = r"(?:creditors?|lenders?|noteholders?|bondholders?|holders?|investors|claims?|bonds?|notes?|loans?|instruments?|debts?|tranches?|securities|facility|revolver|lien)"


def _word(p):
    return re.compile(rf"(?<![A-Za-z]){re.escape(p)}(?![A-Za-z])", re.IGNORECASE)


def _near(p):
    b = rf"(?<![A-Za-z])(?:{p})(?![A-Za-z])"
    gap_ = r"(?:\W+\w+){0,4}?\W+"
    return re.compile(rf"{b}{gap_}{NOUN}\b|\b{NOUN}{gap_}{b}", re.IGNORECASE)


OUTCOME_CERTAINTY = ("recovery is guaranteed", "recovery is assured", "recovery is certain", "guaranteed recovery", "assured recovery", "plan will be confirmed",
                     "confirmation is assured", "confirmation is certain")
PROB_WEIGHT = ("probability-weighted", "probability weighted", "probability of", "weighted by probability", "expected value", "likelihood-weighted")
GUARD = ([("peer ranking", p, _word(p)) for p in PEER] + [("instrument recommendation", p, _word(p)) for p in INSTR]
         + [("instrument recommendation", p, _near(p)) for p in NEAR_INSTR]
         + [("outcome certainty", p, _word(p)) for p in OUTCOME_CERTAINTY] + [("probability weighting", p, _word(p)) for p in PROB_WEIGHT])


def guard_issues(path, t):
    return [f'{path}: prohibited conclusion ({k}): "{p}"' for k, p, pat in GUARD if pat.search(t)]


GUARD_PROBE = [  # (sentence, class)
    ("The senior secured term loan is the fulcrum security.", "allowed"),
    ("Value breaks at the trade creditors, so they hold the fulcrum.", "allowed"),
    ("The expected recovery of the term loan is full.", "allowed"),
    ("The notes would recover in full.", "allowed"),
    ("Recovery of the unsecured class is partial.", "allowed"),
    ("The term loan ranks above peers' loans.", "caught"),
    ("We recommend the term loan.", "caught"),
    ("Recovery is guaranteed.", "caught"),
    ("The plan will be confirmed.", "caught"),
    ("The recoveries are probability-weighted.", "caught"),
    ("Holders should avoid this credit.", "guard_limit"),
    ("Lenders should extend the maturity.", "guard_limit"),
    ("The term loan is certain to be repaid.", "guard_limit"),
    ("The fulcrum is the trade creditors.", "guard_limit"),
    ("Senior lenders will get everything back.", "guard_limit"),
]
for _s, _k in GUARD_PROBE:
    _hit = guard_issues("p", _s)
    assert (_k == "caught") == bool(_hit), (_s, _hit)

# --- 8. reference validator (oracle's own; derives every expected refusal issue) ---------------
HIGH_ISSUE = "assessment.confidence: High is not allowed: multiples, ranks and plan treatment are uncited analyst assumptions"
SCOPE = ("financial", "legal-covenants")


def split_text_fields(sub):
    out = []
    for i, c in enumerate(sub["claims"]):
        out += [(f"claims[{i}].rationale", c["rationale"], True), (f"claims[{i}].limitation", c["limitation"], False)]
    for key in ("valuation", "fulcrum", "plan"):
        for i, x in enumerate(sub[key]):
            out += [(f"{key}[{i}].rationale", x["rationale"], True), (f"{key}[{i}].limitation", x["limitation"], False)]
    out += [("assessment.rationale", sub["assessment"]["rationale"], True), ("assessment.limitation", sub["assessment"]["limitation"], False)]
    for i, g in enumerate(sub["gaps"]):
        out += [(f"gaps[{i}].{k}", g[k], False) for k in ("gap", "why_it_matters", "affected_analysis", "action")]
    return out


def prose_oracle(path, t, bound):
    if not t.strip():
        return [f"{path}: empty text"]
    if "{{FIG" in t and not bound:
        return [f"{path}: Malformed run text: unbalanced or empty reference"]
    out = []
    for m in re.finditer(r"\{\{FIG:([a-z_0-9]+)\|([^}]*)\}\}", t):
        want = FIGS[m.group(1)]["unit_token"]
        if m.group(2) != want:
            out.append(f"{path}: Unit {m.group(2)} differs from the fact's unit {want}: {{{{FACT_ID:{m.group(1)}}}}}")
    for m in re.finditer(r"\{([A-Za-z0-9_.:-]+)\|[^}]*\}", re.sub(r"\{\{FIG:[a-z_0-9]+\|[^}]*\}\}", "", t)):
        out.append(f"{path}: Unresolved reference: {m.group(1)}")
    rest = re.sub(r"CP-[0-9]{1,2}[A-Z]?", "", re.sub(r"\{\{FIG:[a-z_0-9]+\|[^}]*\}\}|\{[^}]*\}", "", t))
    out += [f"{path}: Bare figure: {tok}" for tok in dict.fromkeys(re.findall(r"[0-9][0-9.,]*[0-9]|[0-9]", rest))]
    return out


def content_issues(sub, summary, pack_pages, bind=True):
    """summary: the case waterfall summary (break, recovery) the fulcrum and plan checks read; pack_pages: {(source, locator): text}."""
    out = []
    ids, struct = [], True
    for i, c in enumerate(sub["claims"]):
        n0 = len(out)
        if c["class_id"] in ids:
            out.append(f"claims[{i}].class_id: duplicate class {c['class_id']}")
        ids.append(c["class_id"])
        mismatch = (c["kind"] == "secured_debt") != (c["amount_source"] == "cp1_total_debt")
        if mismatch:
            out.append(f"claims[{i}].amount_source: cp1_total_debt is the secured_debt class's source and no other class's")
        elif c["amount_source"] == "source_row":
            aq = c["amount_quote"]
            if aq is None:
                out.append(f"claims[{i}].amount_quote: a source_row class cites the row it reads")
            else:
                found = aq["source_id"] == "financial" and aq["quote"] in pack_pages.get(("financial", aq["locator"]), "")
                if not found:
                    out.append(f"claims[{i}].amount_quote: quote not found under {aq['source_id']} {aq['locator']}")
                elif c["period_column"] not in BS_HEADER[1:]:
                    out.append(f"claims[{i}].period_column: not a column of the quoted statement: {c['period_column']}")
        else:
            if c["amount_quote"] is not None:
                out.append(f"claims[{i}].amount_quote: only a source_row class cites an amount row")
            if c["period_column"] is not None:
                out.append(f"claims[{i}].period_column: only a source_row class names a column")
        for j, q in enumerate(c["support"]):
            if q["source_id"] not in SCOPE:
                out.append(f"claims[{i}].support[{j}].source_id: not in this step's source scope: {q['source_id']}")
            elif q["quote"] not in pack_pages.get((q["source_id"], q["locator"]), ""):
                out.append(f"claims[{i}].support[{j}]: quote not found under {q['source_id']} {q['locator']}")
        struct = struct and len(out) == n0
    sec = [i for i, c in enumerate(sub["claims"]) if c["kind"] == "secured_debt"]
    if len(sec) != 1:
        out.append("claims: exactly one secured_debt class is required")
        struct = False
    else:
        k = sec[0]
        if any(int(c["rank"]) <= int(sub["claims"][k]["rank"]) for j, c in enumerate(sub["claims"]) if j != k):
            out.append(f"claims[{k}].rank: the secured_debt class ranks first, ahead of every other class")
            struct = False
    for i, v in enumerate(sub["valuation"]):
        if v["case_id"] != f"v{i + 1:02d}":
            out.append(f"valuation[{i}].case_id: expected v{i + 1:02d}")
            struct = False
    known = set(ids) | {"equity"}
    for key in ("fulcrum", "plan"):
        for i, x in enumerate(sub[key]):
            if x["case_id"] != f"v{i + 1:02d}":
                out.append(f"{key}[{i}].case_id: expected v{i + 1:02d}")
    if struct:
        for i, f in enumerate(sub["fulcrum"]):
            bad = False
            for cid in f["class_ids"]:
                if cid not in known:
                    out.append(f"fulcrum[{i}].class_ids: not a claim class: {cid}")
                    bad = True
            if len(set(f["class_ids"])) != len(f["class_ids"]):
                out.append(f"fulcrum[{i}].class_ids: duplicate class")
                bad = True
            if not bad and f["case_id"] == f"v{i + 1:02d}":
                brk = summary[f["case_id"]]["break"]
                if brk is None:
                    if f["class_ids"]:
                        out.append(f"fulcrum[{i}].class_ids: the value break is not determinable in {f['case_id']}, so no class can be named")
                elif sorted(f["class_ids"]) != sorted(brk):
                    out.append(f"fulcrum[{i}].class_ids: value breaks at {', '.join(brk)} in {f['case_id']}; the judgment names {', '.join(f['class_ids']) or 'no class'}")
        for i, p in enumerate(sub["plan"]):
            bad = False
            seen = []
            for j, t in enumerate(p["treatments"]):
                if t["class_id"] not in known:
                    out.append(f"plan[{i}].treatments[{j}].class_id: not a claim class: {t['class_id']}")
                    bad = True
                elif t["class_id"] in seen:
                    out.append(f"plan[{i}].treatments[{j}].class_id: duplicate class {t['class_id']}")
                    bad = True
                seen.append(t["class_id"])
            for cid in ids + ["equity"]:
                if cid not in seen:
                    out.append(f"plan[{i}].treatments: no treatment for {cid}")
                    bad = True
            if not bad and p["case_id"] == f"v{i + 1:02d}":
                S = summary[p["case_id"]]
                for j, t in enumerate(p["treatments"]):
                    if t["class_id"] == "equity":
                        r = S["residual"]
                        ok = (r is None and t["treatment"] == "Not determined") or (r is not None and ((D(r) > 0 and t["treatment"] == "Equity retained") or (D(r) == 0 and t["treatment"] == "No recovery")))
                    else:
                        r = S["recovery"][t["class_id"]]
                        ok = (r is None and t["treatment"] == "Not determined") or (r is not None and ((D(r) == 1 and t["treatment"] == "Paid in full") or (0 < D(r) < 1 and t["treatment"] == "Receives reorganised equity") or (D(r) == 0 and t["treatment"] == "No recovery")))
                    if not ok:
                        out.append(f"plan[{i}].treatments[{j}]: {t['treatment']} does not fit the waterfall result of {t['class_id']} in {p['case_id']}")
    if sub["assessment"]["confidence"] == "High":
        out.append(HIGH_ISSUE)
    for path, t, is_run in split_text_fields(sub):
        if t is None:
            continue
        if is_run:
            out += prose_oracle(path, t, bind)
        out += guard_issues(path, t)
    return out


def pages_of(legal_key):
    pg = {("financial", k): v for k, v in PAGE.items()}
    pg.update({("legal-covenants", k): v for k, v in LEGAL_PAGE[legal_key].items()})
    return pg


PATTERN = {"mult": "String should match pattern '^([0-9]{1,2}(\\.[0-9]{1,2})?|not assessed)$'", "rank": "String should match pattern '^[1-9]$'",
           "cid": "String should match pattern '^c[0-9]{2}$'", "fid": "String should match pattern '^(c[0-9]{2}|equity)$'"}


def refusals(built):
    pos = SUBMISSION["positive"]
    S = built["positive"]["waterfall"]
    P = pages_of("positive")
    out = []

    def mut(fn, base=None):
        d = deepcopy(base or pos)
        fn(d)
        return d

    def add_shape(rid, klass, mutation, payload, issues):
        out.append({"id": rid, "class": klass, "mutation": mutation, "issue_kind": "shape", "expected_issues": issues, "payload": payload})

    add_shape("r01", "multiple not a decimal", "valuation[1].multiple = 'three'", mut(lambda d: d["valuation"][1].update(multiple="three")), [f"valuation.1.multiple: {PATTERN['mult']}"])
    add_shape("r02", "rank outside 1 to 9", "claims[1].rank = '10'", mut(lambda d: d["claims"][1].update(rank="10")), [f"claims.1.rank: {PATTERN['rank']}"])
    add_shape("r03", "class id malformed", "claims[1].class_id = 'claim2'", mut(lambda d: d["claims"][1].update(class_id="claim2")), [f"claims.1.class_id: {PATTERN['cid']}"])
    add_shape("r04", "unknown claim kind", "claims[1].kind = 'mezzanine'", mut(lambda d: d["claims"][1].update(kind="mezzanine")),
              ["claims.1.kind: Input should be 'secured_debt', 'unsecured_trade', 'other_liability' or 'administrative_priority'"])
    add_shape("r05", "unknown amount source", "claims[1].amount_source = 'guess'", mut(lambda d: d["claims"][1].update(amount_source="guess")),
              ["claims.1.amount_source: Input should be 'cp1_total_debt', 'source_row' or 'not_stated'"])
    add_shape("r06", "EBITDA year outside the forecast", "valuation[0].ebitda_year = 'FY2029'", mut(lambda d: d["valuation"][0].update(ebitda_year="FY2029")),
              ["valuation.0.ebitda_year: Input should be 'FY2026', 'FY2027' or 'FY2028'"])
    add_shape("r07", "two valuations instead of three", "valuation loses its last element", mut(lambda d: d["valuation"].pop()),
              ["valuation: Tuple should have at least 3 items after validation, not 2"])
    add_shape("r08", "treatment outside the enumeration", "plan[0].treatments[0].treatment = 'Cancelled'", mut(lambda d: d["plan"][0]["treatments"][0].update(treatment="Cancelled")),
              ["plan.0.treatments.0.treatment: Input should be 'Paid in full', 'Receives reorganised equity', 'Equity retained', 'No recovery' or 'Not determined'"])
    add_shape("r09", "confidence outside the enumeration", "assessment.confidence = 'Very High'", mut(lambda d: d["assessment"].update(confidence="Very High")),
              ["assessment.confidence: Input should be 'High', 'Medium', 'Low' or 'Insufficient Information'"])
    add_shape("r10", "required field absent", "assessment.limitation removed", mut(lambda d: d["assessment"].pop("limitation")), ["assessment.limitation: Field required"])
    add_shape("r11", "unknown field", "top-level key 'extra' added", mut(lambda d: d.update(extra=1)), ["extra: Extra inputs are not permitted"])
    out.append({"id": "r12", "class": "not JSON", "mutation": "payload text '{not json'", "issue_kind": "shape", "expected_issues": ["(root): Invalid JSON: key must be a string at line 1 column 2"],
                "payload": None, "payload_text": "{not json"})
    add_shape("r13", "fulcrum class id malformed", "fulcrum[0].class_ids[0] = 'c1'", mut(lambda d: d["fulcrum"][0].update(class_ids=["c1"])), [f"fulcrum.0.class_ids.0: {PATTERN['fid']}"])

    def add(rid, klass, mutation, payload, against="positive", bind=True, **extra):
        summ = built[against]["waterfall"]
        issues = content_issues(payload, summ, pages_of(against), bind)
        assert issues, rid
        e = {"id": rid, "class": klass, "mutation": mutation, "issue_kind": "content", "expected_issues": issues, "payload": payload}
        if against != "positive":
            e["against"] = against
        if not bind:
            e["bind_placeholders"] = False
        e.update(extra)
        out.append(e)

    add("v01", "duplicate class id", "claims[2].class_id = 'c02'", mut(lambda d: d["claims"][2].update(class_id="c02")))
    add("v02", "secured class reads a statement row", "claims[0].amount_source = 'source_row'", mut(lambda d: d["claims"][0].update(amount_source="source_row")))
    add("v03", "source_row without a cited row", "claims[1].amount_quote = null, period_column = null", mut(lambda d: d["claims"][1].update(amount_quote=None, period_column=None)))
    add("v04", "amount quote not on the page", "claims[1].amount_quote.quote changed to 21.00", mut(lambda d: d["claims"][1]["amount_quote"].update(quote="Trade payables  17  17.75  18.50  19.25  21.00  21.00")))
    add("v05", "period column not in the statement", "claims[1].period_column = 'Q5 2026-03-31'", mut(lambda d: d["claims"][1].update(period_column="Q5 2026-03-31")))
    add("v06", "secured class not first", "claims[0].rank = '2'", mut(lambda d: d["claims"][0].update(rank="2")))
    add("v07", "support quote not on the page", "claims[0].support[0].quote altered", mut(lambda d: d["claims"][0]["support"][0].update(quote="Clause 1.3. The agreement governs a revolving facility.")))
    add("v08", "support from outside the step's scope", "claims[0].support[0].source_id = 'identity'", mut(lambda d: d["claims"][0]["support"][0].update(source_id="identity")))
    add("v09", "fulcrum names the wrong class", "fulcrum[1].class_ids = ['c01']", mut(lambda d: d["fulcrum"][1].update(class_ids=["c01"])))
    add("v10", "fulcrum names an unknown class", "fulcrum[2].class_ids = ['c09']", mut(lambda d: d["fulcrum"][2].update(class_ids=["c09"])))
    add("v11", "fulcrum named where the value break is not determinable", "gap payload: fulcrum[0].class_ids = ['c01']",
        mut(lambda d: d["fulcrum"][0].update(class_ids=["c01"]), SUBMISSION["gap"]), against="gap")
    add("v12", "plan treatment does not fit the recovery", "plan[1].treatments[1].treatment = 'Paid in full' (c02 recovers part of its claim in v02)",
        mut(lambda d: d["plan"][1]["treatments"][1].update(treatment="Paid in full")))
    add("v13", "confidence High", "assessment.confidence = 'High'", mut(lambda d: d["assessment"].update(confidence="High")))
    add("v14", "plan misses a class", "plan[0].treatments loses equity", mut(lambda d: d["plan"][0]["treatments"].pop()))
    add("v15", "bare figure in prose", "claims[1].rationale states '5 percent'", mut(lambda d: d["claims"][1].update(rationale="Trade creditors are cut by 5 percent.")))
    add("v16", "unresolved reference", "valuation[0].rationale names {T9.9.value|x}", mut(lambda d: d["valuation"][0].update(rationale="The base value rests on {T9.9.value|x} of earnings.")))
    add("v17", "unit-mismatched reference", "claims[0].rationale: total_debt_ltm token unit 'US$ m' replaced by 'x'",
        mut(lambda d: d["claims"][0].update(rationale=pos["claims"][0]["rationale"].replace("{{FIG:total_debt_ltm|US$ m}}", "{{FIG:total_debt_ltm|x}}"))))
    add("v18", "figure placeholder left unreplaced", "the payload is sent with every {{FIG:..}} still in place", deepcopy(pos), bind=False)
    add("v19", "empty prose", "fulcrum[0].rationale = ''", mut(lambda d: d["fulcrum"][0].update(rationale="")))
    add("v20", "peer ranking", "valuation[1].rationale adds 'ranks above peers'",
        mut(lambda d: d["valuation"][1].update(rationale=pos["valuation"][1]["rationale"] + " The loan ranks above peers' loans.")))
    add("v21", "instrument recommendation", "fulcrum[2].rationale adds 'We recommend the term loan.'",
        mut(lambda d: d["fulcrum"][2].update(rationale=pos["fulcrum"][2]["rationale"] + " We recommend the term loan.")))
    add("v22", "outcome certainty", "plan[1].rationale adds 'Recovery is guaranteed.'", mut(lambda d: d["plan"][1].update(rationale=pos["plan"][1]["rationale"] + " Recovery is guaranteed.")))
    add("v23", "probability weighting", "assessment.rationale adds 'probability-weighted'",
        mut(lambda d: d["assessment"].update(rationale=pos["assessment"]["rationale"] + " The recoveries are probability-weighted.")))
    for rid, up, seed in (("v24", "CP-2A", "a different CP-2A head"), ("v25", "CP-2G", "a different CP-2G head"), ("v26", "CP-4", "a different CP-4 head"), ("v27", "CP-1", "a different CP-1 head")):
        cur = hashlib.sha256(f"cp4c-owner {rid}: {seed}".encode()).hexdigest()
        out.append({"id": rid, "class": "stale or unbound inputs", "issue_kind": "content", "composer_only": True,
                    "mutation": f"the positive payload validated against a literal Upstream whose current {up} Input differs from the attempt's bound {up} Input; validator only",
                    "expected_issues": [f"Stale input {up}: bound restricted <12 hex of the attempt's bound {up} input sha256>, current restricted {cur[:12]}"],
                    "payload": deepcopy(pos),
                    "upstream_literal": {"current": [{"input_id": up, "sha256": cur, "status": "restricted"}], "note": f"every other Input of the bound tuple is unchanged, so only {up} is reported"},
                    "run_level": {"outcome": "stale_binding", "consumes_attempt": False, "journals_step": False,
                                  "clone": f"a clone of the positive store taken after the CP-4C begin whose bound snapshot then changes (a new {up} head)",
                                  "direct_caller": "Execution.submit_step raises ValueError('Ticket inputs have changed')"},
                    "issue_prefix": f"Stale input {up}: bound restricted "})
    # the prose-issue classes were written by hand in CP-2G and probed on prose.issues; here the oracle derived them: assert the intended text
    byid = {r["id"]: r for r in out}
    assert byid["v15"]["expected_issues"] == ["claims[1].rationale: Bare figure: 5"], byid["v15"]["expected_issues"]
    assert byid["v16"]["expected_issues"] == ["valuation[0].rationale: Unresolved reference: T9.9.value"], byid["v16"]["expected_issues"]
    assert byid["v17"]["expected_issues"] == ["claims[0].rationale: Unit x differs from the fact's unit US$ m: {{FACT_ID:total_debt_ltm}}"], byid["v17"]["expected_issues"]
    return out


# --- 9. tool calls (search rule of cases/cpdr-owner: a span matches when it contains any query term, case-insensitive substring) --------
def spans_matching(query, scope, legal_key):
    terms = [t.lower() for t in dict.fromkeys(query.split())]
    texts = {"financial": PAGE, "legal-covenants": LEGAL_PAGE[legal_key]}[scope]
    return [{"source_id": scope, "locator": loc} for loc, t in texts.items() if any(w in t.lower() for w in terms)]


def tool_calls(legal_key):
    def search(q, scope):
        hits = spans_matching(q, scope, legal_key)
        return {"module": "CP-4C", "tool": "search_pack", "arguments": {"query": q, "source_id": scope},
                "expect_header": f"{len(hits)} spans match {q!r}; showing {min(10, len(hits))}.", "expect_matching_spans": hits}

    def read(scope, n):
        return {"module": "CP-4C", "tool": "read_pages", "arguments": {"source_id": scope, "first_page": n, "last_page": n}, "expect_spans": [{"source_id": scope, "locator": f"page:{n}"}]}

    return [{"module": "CP-4C", "tool": "read_inputs", "arguments": None}, search("Trade payables", "financial"), read("financial", 4), search("senior secured", "legal-covenants"), read("legal-covenants", 1)]


def cite(sid, loc, quote, pages):
    assert quote in pages[(sid, loc)]
    return {"source_id": sid, "source_sha256": SRC[sid]["sha256"] if sid in SRC else None, "locator": loc, "quote": quote}


CITE_ID = {"source_id": "identity", "source_sha256": SRC["identity"]["sha256"], "locator": "page:1", "quote": "Northbridge Synthetic Group is the issuer and consolidated group."}
CITE_FIN = {"source_id": "financial", "source_sha256": SRC["financial"]["sha256"], "locator": "page:1", "quote": "Currency: USD; amounts in millions."}
CP0_ROW_CP4C = {
    "module_id": "CP-4C", "readiness": "READY_WITH_LIMITATIONS",
    "evidence_demand": "Settled CP-1 debt and EBITDA, the CP-2A scenario, CP-2G forecast EBITDA and CP-4 facility terms, plus located balance-sheet liabilities",
    "source_ids": ["identity", "financial", "legal-covenants"],
    "rationale": "The recovery waterfall can run on settled upstream outputs and located liabilities with inherited source and scope limitations; multiples and ranks are analyst assumptions.",
    "citations": [CITE_ID, CITE_FIN], "missing_source": None,
    "limitations": ["Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable.", "Selected executed terms only; omitted security, guarantees, default/cure/voting terms; no overall lender-protection rating supported."],
}
CP1_READINESS_CP4C = {
    "entry": "CP-4C",
    "requirements": [{"requirement": "consumer_specific_cp1_sufficiency", "status": "limited",
                      "evidence_ids": ["{{EVID:kpi total_debt, LTM Q4 25 basis}}", "{{EVID:kpi ebitda, LTM Q4 25 basis}}"],
                      "rationale": "Settled twelve-month debt and EBITDA give the waterfall its secured claim and a cross-check; other liabilities are read from the cited balance sheet.",
                      "actions": ["Retain the unaudited-statement limitation in the recovery model."]}],
    "gaps": [{"gap_ids": ["{{ALL narrative gap ids}}"], "relevance": "relevant", "evidence_ids": [], "rationale": "Every retained source and context warning bears on the claims the waterfall allocates."}],
}


def review_literal(case):
    rv = deepcopy(CP4_SUB[case]["readiness_review"])
    cons = {c["module_id"]: c for c in rv["consumers"]}
    rv["consumers"] = [cons["CP-1"], CP2A_SUB["cp0_consumer_row_cp2a"], cons["CP-4"], CP2G_SUB["cp0_consumer_row_cp2g"], CP0_ROW_CP4C]
    return rv


def readiness_literal():
    return {"inputs_sha256": "{{INPUTS_SHA256}}",
            "consumers": [deepcopy(CP2A_SUB["cp1_downstream_review"]["consumers"][0]), deepcopy(next(c for c in CP2G_SUB["cases"]["gap"]["cp1_readiness"]["consumers"] if c["entry"] == "CP-2G")),
                          deepcopy(CP1_READINESS_CP4C)],
            "note": "CP-2A and CP-2G entries are the frozen literals of cases/cp2a-owner and cases/cp2g-owner (gap) unchanged; CP-4C new with the same marker style; CP-4 has no CP-1 readiness entry in its oracle"}


def pointer(rel, jpath):
    return {"file": rel, "sha256": PINS[rel], "path": jpath}


TAMPER_TARGET, TAMPER_FROM, TAMPER_TO = "T4E.7.v03.value_break", "Senior secured term loan", "Equity (every creditor class is paid in full)"


def main():
    built = {name: build_case(name) for name in PCASE}
    ref_list = refusals(built)
    by_id = {r["id"]: r for r in ref_list}
    base_run = dict(FIN["run"])
    runs = {k: dict(base_run, run_id=f"cp4c-owner-{k.replace('_', '-')}", pathway="distressed_restructuring", requested_modules=["CP-4C"])
            for k in ("positive", "gap", "refused", "blocked", "cp2g_blocked")}
    plan = ["CP-0", "CP-1", "CP-2A", "CP-4", "CP-2G", "CP-4C"]
    inputs = ["prepared-pack", "CP-0", "CP-1", "CP-2A", "CP-4", "CP-2G"]
    for k in ("positive", "gap"):
        assert built[k]["module_status"] == "restricted"
    pos, gp = built["positive"]["waterfall"], built["gap"]["waterfall"]
    # worked checks of the headline numbers (exact rationals)
    assert pos["v02"]["ev"] == "55.62" and pos["v03"]["ev"] == "37.08" and pos["v01"]["ev"] == "123.6"
    assert pos["v02"]["recovery"]["c02"] == norm(q38(Fraction(562, 100) / 30)) and pos["v03"]["recovery"]["c01"] == "0.7416"
    assert pos["v01"]["break"] == ["equity"] and pos["v02"]["break"] == ["c02", "c03"] and pos["v03"]["break"] == ["c01"]
    assert gp["v01"]["break"] is None and gp["v02"]["break"] is None and gp["v03"]["break"] is None
    assert built["fixture_ev_zero"]["waterfall"]["v02"]["ev"] == "0" and built["fixture_ev_zero"]["waterfall"]["v02"]["break"] == ["c01"]

    manifest = {
        "schema_version": "cp4c-owner-cases/1",
        "scope": "CP-4C Restructuring fulcrum: CP-0, CP-1, CP-2A, CP-4, CP-2G (required) over the identity, financial and legal-covenants frozen sources; CP-3C (optional) is not read",
        "status": "DRAFT revision 2 (fix round 1 on review-precise-1) by the cp4c-owner preparation task, 2026-10-28; scoped re-review review-precise-2 (two Low text fixes applied); not executed",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "pins": PINS,
        "sources": {
            "identity": {"path": "cases/financial/manifest.json", "sha256": SRC["identity"]["sha256"]},
            "financial": {"path": "cases/financial/manifest.json", "sha256": SRC["financial"]["sha256"], "scope_pages": "page:4 (balance sheet rows) read; page:5 not cited"},
            "legal-covenants": {"positive": {"path": "cases/legal/manifest.json", "case": LEGAL_CASE["positive"], "sha256": LEG[LEGAL_CASE["positive"]]["sha256"]},
                                "gap": {"path": "cases/legal/manifest.json", "case": LEGAL_CASE["gap"], "sha256": LEG[LEGAL_CASE["gap"]]["sha256"]}},
        },
        "no_new_source": "No synthetic source is added: the claim classes are the frozen balance-sheet rows (financial page:4) and the frozen sole senior secured term loan (CP-1 total debt, legal Clause 1.3). Trade payables 20 and other current liabilities 10 are read from the cited rows, Q4 2025-12-31 column.",
        "edges": {"decision": "D4: methodology.json as is. CP-4C required CP-0, CP-1, CP-2G, CP-4, CP-2A, each edge rule block; optional CP-3C, rule restricted; no edge_rules entry.",
                  "required": MOD["CP-4C"]["required"], "optional": MOD["CP-4C"]["optional"],
                  "plans": {"CP-4C": plan, "CP-4C+CP-3C": ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-2A", "CP-4", "CP-2D", "CP-2G", "CP-3C", "CP-4C"]},
                  "optional_edge_unread": "CP-3C is not requested: it brings CP-1A, CP-2 and CP-2D (a business source and a second CP-1 promotion path), has no distressed_restructuring entry in contracts.PATHWAY_MODULES, and its frozen oracle runs in covenant_refinancing. An unread optional edge is absent from attempt.inputs, the view and the trace.",
                  "input_order": f"positive and gap: {inputs}"},
        "cases": {
            "positive": {"run": runs["positive"], "pack": "identity + financial + legal-covenants (matching definition)", "execution": "closed run: CP-0, CP-1, CP-2A (frozen CP-2A positive literal), CP-4 (frozen CP-4 positive literals), CP-2G (frozen CP-2G gap literal: CP-1D not requested, minimum liquidity not assessed), CP-4C"},
            "gap": {"run": runs["gap"], "pack": "identity + financial + legal-covenants (missing Schedule A)", "execution": "same plan; CP-4 settles its gap literal; CP-4C: administrative claims not stated, stress multiple not assessed"},
            "refused": {"run": runs["refused"], "pack": "financial source missing", "execution": "CP-0 only; CP-1 begin refused (cp1_not_authorized); no later attempt"},
            "blocked": {"run": runs["blocked"], "pack": "as positive", "execution": "closed run to CP-2G (clone before CP-4C), then CP-4C attempt 0 invalid (rejected) and attempt 1 invalid (blocked)"},
            "cp2g_blocked": {"run": runs["cp2g_blocked"], "pack": "as positive", "execution": "closed run to CP-4, then CP-2G settles blocked (CP-2G refusals r01 then v13); CP-4C begin raises ValueError('Required upstream is unrun, stale or blocked')"},
            "fixture_ev_zero": {"run": None, "execution": "composer only: CP-2G fixture_total_loss facts (downside EBITDA a known 0): enterprise value a known 0, every creditor recovery a known 0"},
            "fixture_ebitda_missing": {"run": None, "execution": "composer only: CP-2G T2H.4.d26.ebitda set to status missing (synthetic upstream variant): downside and stress EV missing"},
            "fixture_debt_missing": {"run": None, "execution": "composer only: CP-1 total_debt set to status missing: the secured claim and every recovery are missing"},
        },
        "fact_selection_rule": {
            "cp1": {"table_id": "T4.10", "period": LTM_PERIOD, "predicate": "label == 'LTM Q4 25 (2025-01-01 to 2025-12-31) · <metric>'; exactly one match", "metrics": ["total_debt", "ebitda"],
                    "observed_value_class": {m: OBS_CLASS[m] for m in ("total_debt", "ebitda")}, "source": "cases/cp2g-owner/manifest.json fact_selection_rule (observed on the S1 promoted head)"},
            "cp1_t418": {"table_id": "T4.18", "facility_id": "term-loan", "fields": ["secured_status", "seniority", "facility_name"], "observed": {k: v["observed_on_promoted_head"] for k, v in T418.items()},
                         "source": "cases/cp3c-owner/manifest.json fact_bindings (observed on a promoted head)", "rule": "the QUARTER period at the latest period end wins over its FY alias; unlisted fact ids are bound at run time"},
            "cp2g": "T2H.4.{b|d}{26|27|28}.ebitda and T2H.7.b01.{base|down}_first, literal ids read from cases/cp2g-owner/expected.json cases.gap (pinned) and from the settled CP-2G head at run time",
            "cp2a": "T2B.1.<row>.{name,ebitda_decline,interest_increase} where <row> is named by the cp2a: entry in the derives_from of T2H.4.d26.ebitda (CP-2G lineage); literal ids read from cases/cp2a-owner/expected.json cases.positive",
            "cp4": "T4C.11.r01.{facility_id,facility}, T4.10.r02.{permits,conditions}, T4.13.rating.rating; literal ids read from cases/cp4-owner/expected.json {positive|gap}.CP-4",
        },
        "run_time_bindings": {
            "figure_placeholders": "{{FIG:name|token}} -> {<fact_id>|<token>}: cp1 names by fact_selection_rule, cp2g names to the literal ids; the uncited analyst cells (multiples, ranks, CP-2A shock sizes) are never FIG names",
            "fact_id_marker": "{{FACT_ID:name}} in an expected issue -> the fact id bound to FIG name",
            "cp0_consumer_rows": "positive and gap: CP-1, CP-2A, CP-4 (cases/cp4-owner submissions readiness_review), CP-2G, CP-4C (submissions.json cases.<case>.cp0_readiness_review); T8 commands Run CP-1, Run CP-2A, Run CP-4, Run CP-2G, Run CP-4C",
            "cp1_readiness": "submissions.json cases.<case>.cp1_readiness (consumers CP-2A, CP-2G, CP-4C); markers bound as in the CP-2A and CP-2G manifests",
            "pack_hash": "PreparedPack.content_hash() of the run's pack", "ticket_and_call_ids": "structural only",
        },
        "figures": deepcopy(FIGS),
        "tool_use": {
            "CP-4C": "sourced owner-only step: SourceSession over the fixed host-side scope financial + legal-covenants (no identity, no extract_statements); one ok read_inputs (exact view context_block, a D2 exception frozen by this lease) before the submit; every cited page:N read first (UNREAD_PAGE rule); search_pack before the submit as complete participation",
            "view_tree_draft": {"note": "a proposal; the implementer commits cases/cp4c-owner/cp4c-view-tree.json from a product-settled head; no quote, citations or record_json key at any depth",
                                "keys": {"upstream": "[{module_id, status}] CP-0, CP-1, CP-2A, CP-4, CP-2G", "claims_offered": "{secured: {ref, shown, secured_status, seniority, facility_id, facility}, statement_rows: [{label, columns}] page:4 liability rows with their column headers}",
                                         "ebitda_offered": "[{case: base|down, year, ref, shown, status, limitation|null}] the six CP-2G T2H.4 EBITDA facts", "cp2a": "{scenario_row, name, ebitda_decline: {shown}, interest_increase: {shown}}",
                                         "cp4": "{facility, lender_protection, additional_debt_conditions}", "bounds": "{multiple: {max 99.99, places 2, may_be_not_assessed}, ranks: 1..9, treatments: [...]}",
                                         "cp1_facts": "[{ref, label, period, unit, shown}]", "cp2g_facts": "[{ref, label, period, unit, shown}]", "inherited_limitations": "[str]"}},
            "calls_positive": tool_calls("positive"), "calls_gap": tool_calls("gap"),
        },
    }
    submissions = {
        "schema_version": "cp4c-owner-submissions/1",
        "note": ("Literal analyst submissions for the restructuring_fulcrum step. {{FIG:name|token}} is replaced mechanically by {<fact_id>|<token>} after the heads are inspected; unreplaced it is malformed run text "
                 "(v18). Claim ranks, multiples, the fulcrum and plan treatment are analyst input; amounts come from the cited rows and the settled heads. Upstream step literals are pointers into the frozen oracles (pinned sha256), "
                 "not copies."),
        "figures": deepcopy(FIGS),
        "upstream_step_literals": {
            "CP-2A": {"source": pointer("cases/cp2a-owner/submissions.json", "positive.downside_pathway"), "downside_pathway": CP2A_SUB["positive"]["downside_pathway"],
                      "cp0_consumer_row": "cases/cp2a-owner/submissions.json cp0_consumer_row_cp2a"},
            "CP-2G": {"source": pointer("cases/cp2g-owner/submissions.json", "cases.gap.forward_credit_model"), "forward_credit_model": CP2G_SUB["cases"]["gap"]["forward_credit_model"],
                      "tool_calls": CP2G_SUB["cases"]["gap"]["tool_calls"],
                      "blocked": {"attempt_0": "cases/cp2g-owner/submissions.json refusals r01", "attempt_1": "cases/cp2g-owner/submissions.json refusals v13"}},
            "CP-4": {"positive": {"source": pointer("cases/cp4-owner/submissions.json", "positive"), "cp1_source_context": CP4_SUB["positive"]["cp1_source_context"], "legal_covenants": CP4_SUB["positive"]["legal_covenants"]},
                     "gap": {"source": pointer("cases/cp4-owner/submissions.json", "gap"), "cp1_source_context": CP4_SUB["gap"]["cp1_source_context"], "legal_covenants": CP4_SUB["gap"]["legal_covenants"]},
                     "run_time_bindings": CP4_SUB["run_time_bindings"], "tool_calls": "the CP-4 tool sequence of cases/cp4-owner/manifest.json / expected.json (read_pages legal-covenants 1-3, search_pack, one read_inputs)"},
        },
        "cases": {k: {"restructuring_fulcrum": SUBMISSION[k], "cp0_readiness_review": review_literal(k), "cp1_readiness": readiness_literal(), "tool_calls": tool_calls(k)} for k in ("positive", "gap")},
        "fixtures": {k: {"restructuring_fulcrum": FIXTURE_SUB[k]} for k in FIXTURE_SUB},
        "refused": {"cp0_consumer_rows": {m: {"module_id": m, "readiness": "CONDITIONAL", "evidence_demand": "Settled upstream outputs", "source_ids": ["identity"],
                                            "rationale": "Quarterly financial statements were not supplied.", "citations": [CITE_ID], "missing_source": "Quarterly financial statements",
                                            "limitations": ["Quarterly financial statements were not supplied."]} for m in ("CP-1", "CP-2A", "CP-4", "CP-2G", "CP-4C")},
                    "gap_row": {"gap_id": "missing-financial", "kind": "source", "severity": "material", "description": "Quarterly financial statements were not supplied.",
                                "affected_modules": ["CP-1", "CP-2A", "CP-4", "CP-2G", "CP-4C"], "remediation": "Supply quarterly financial statements"}},
        "refusals": [{k: v for k, v in r.items() if k in ("id", "class", "mutation", "payload", "payload_text", "composer_only", "bind_placeholders", "against", "upstream_literal", "run_level")} for r in ref_list],
        "blocked": {"attempt_0": "refusals r01", "attempt_1": "refusals v13"},
    }
    expected = {
        "schema_version": "cp4c-owner-expected/1",
        "derivation": ("Recipes of work/lead/cp4c-owner-preparation/lease-draft.md applied by cases/cp4c-owner/builder/build.py (stdlib only; deploy_vii never imported or run) to the frozen financial and legal pages, the pinned "
                       "CP-2A, CP-2G and CP-4 oracle facts and the literal submissions. Every value is the correctly rounded 38-digit half-even result of an exact rational, cross-checked against decimal.Context(prec=38, "
                       "ROUND_HALF_EVEN); sums and products are exact (Inexact trapped). Display follows display.py (ROUND_HALF_UP; amount 2 dp, multiple 2 dp 'x', percent 1 dp '%', negative in parentheses). "
                       "A percentage-point amount is (a - b) in the 38-digit context then .scaleb(2), unit 'pp', shown as the exact text + ' pp' (no pp display class exists; pending product task)."),
        "cell_notation": {"shown": "exact displayed text; missing -> state gap '∅ G#'; not_applicable -> state not_meaningful '∅ G# n.m.' (G# bound at run time)", "amount_exact": "canonical exact decimal; null means unsettled",
                          "status": "known | missing | not_applicable", "derives_from": "cp1:<metric>, cp2a:<id>, cp2g:<id>, cp4:<id> = a settled upstream fact (reference tables); any other id = a fact of this module",
                          "citations": "listed only where the cell is itself backed by a literal quote of the submission (claim amounts read from a statement row; the secured class's support quote)"},
        "id_rules": {"fact_id": "<table_id>.<row_id>.<field>", "calculation_id": "calc:<fact_id> on calculated facts",
                     "rows": "T4E.2: the claim class ids c01.. in submission order, then eq; T4E.3, T4E.7, T4E.9: v01..v03; T4E.4, T4E.5, T4E.8: <case><class> e.g. v02c01, and <case>eq; T4E.6: <case><class> for creditor classes",
                     "claims": "analyst: T4E.2.<class>.rationale, T4E.3.<case>.rationale, T4E.7.<case>.rationale, T4E.8.<case>.rationale, T4E.3.assessment; Python: T4E.3.<case>.ev, T4E.5.<case>, T4E.7.<case>.fulcrum"},
        "lineage_rule": ("A calculated fact's citations are the ordered, de-duplicated concatenation of the citations of the facts in its derives_from list (cp4_legal._computed pattern); a fact backed by a literal quote lists it in citations here. "
                         "A known fact never derives from a fact that is not known (asserted). A T4E cell that restates a CP-1, CP-2G, CP-2A or CP-4 fact is this module's own fact with an upstream lineage id (CP-2G ruling M3); "
                         "only the four reference tables carry the upstream facts verbatim."),
        "references_rule": "cp1_references, cp2g_references, cp2a_references, cp4_references carry the upstream facts verbatim under their own fact ids; prose resolves through them; a multiple or rank (analyst_judgment, no citation or calculation) cannot be referenced in prose; each row projects the upstream fact, and the module's reference fact equals the upstream oracle fact (cases/cp2g-owner, cp2a-owner, cp4-owner expected.json, by fact_id) in every key, including currency, scale, decimals and calculation_id; cp1 rows are bound at run time.",
        "waterfall_rules": {
            "order": "classes by the analyst's rank number, lowest first; classes of one rank share pro rata; the secured_debt class must rank strictly first",
            "distributable": "enterprise value only (EBITDA x multiple); cash is not added, costs are not deducted",
            "recipe": "paid = min(available, group total); recovery = paid / group total (one division); distribution = claim x paid / group total (one division of an exact product); shortfall = claim - distribution; next available = available - paid; equity residual = what remains (a known 0 when creditors absorb all value)",
            "missing": "a missing claim blocks its rank group and every lower rank and the equity residual; a missing or unassessed EV blocks everything; a known EV of 0 gives known 0 recoveries; nothing becomes 0",
            "value_break": "the first rank group whose paid < total; if none, equity; not determinable (missing with the root reason) when an earlier group is blocked",
            "attachment": "claims ahead / EBITDA and claims through the class / EBITDA (the multiple at which the class is covered in full); missing when EBITDA is missing, zero or negative",
            "plan_fit": "creditor: Paid in full <=> recovery 1; Receives reorganised equity <=> 0 < recovery < 1; No recovery <=> recovery 0; Not determined <=> recovery missing. Equity: Equity retained <=> residual > 0; No recovery <=> residual 0; Not determined <=> residual missing",
        },
        "property_tests": {
            "conservation": "for every case with all inputs known: sum of creditor distributions + equity residual = enterprise value exactly (T4E.9 balance = 0)",
            "priority": "no class receives value while a better-ranked class has a shortfall; recoveries are non-decreasing in enterprise value",
            "pari_passu": "classes of one rank have equal recovery",
            "break_monotone": "as the multiple rises the value break moves to the same or a more junior rank",
            "missing_never_zero": "removing a claim amount or the multiple never produces a known 0",
        },
        "d8_table_ids": {"collision_found": None, "cp4c_table_ids": list(TABLES), "check": "T4E.1-T4E.10 appear only in the CP-4C entry of the pinned methodology.json (asserted); module tables besides: cp1_references, cp2g_references, cp2a_references, cp4_references"},
        "d7_rendering": {"decision": "two blocks, owner CP-4C, kind dense, producers (CP-4C,), route 'Full analysis', in distressed_restructuring: recovery-by-class (tabs T4E.5, T4E.7, T4E.8) and value-allocation-claims (tabs T4E.2, T4E.3, T4E.4, T4E.6); both block ids already exist in report_view._PRESETS; evidence rail T4E.1, T4E.9 and the four reference tables; limitations rail T4E.10; no chart",
                         "design_reference": "DEPLOY VII design/reference rbot-fp-05 'Recovery by class' (scenario/EBITDA/multiple/EV/fulcrum table, recovery twin) and 'Value allocation / claims' (claims, amount, rank); read only"},
        "guard": {
            "kind": "phrase guard, not a semantic review. CP-4C owns fulcrum and recovery conclusions, so the product's 'recovery conclusion' kind (business_context.PROHIBITED, NEAR_INSTRUMENT) is NOT checked and the word 'fulcrum' is not refused (CP-3C's core-local check refuses it in CP-3C prose).",
            "product_kinds_checked": ["peer ranking", "instrument recommendation"], "product_kinds_not_checked": ["recovery conclusion", "instrument action"],
            "core_local_kinds": {"outcome certainty": list(OUTCOME_CERTAINTY), "probability weighting": list(PROB_WEIGHT)},
            "order": "per text field: product phrases in table order (peer ranking, instrument recommendation, near-instrument), then outcome certainty, then probability weighting; issue form 'path: prohibited conclusion (kind): \"phrase\"'",
            "probe": [{"sentence": s, "class": k, "issues": guard_issues("p", s)} for s, k in GUARD_PROBE],
            "cannot_catch": ["a recovery or fulcrum claim in prose that contradicts the waterfall (only the submitted class_ids are checked against it)", "unlisted advice or certainty wordings (guard_limit probes)",
                             "'probability of' over-blocks innocent text and an unlisted weighting wording is missed", "a figure spelled in a field that is not run text (limitation, gap fields) is only caught by the builder's digit assertion on the literals"],
        },
        "execution": {
            "plan_order": plan, "inputs": inputs,
            "statuses": {"CP-0": "restricted", "CP-1": "restricted", "CP-2A": "restricted", "CP-4": "restricted (frozen CP-4 oracle)", "CP-2G": "restricted", "CP-4C": "restricted: own limitations non-empty and the case is synthetic"},
            "tool_use": "CP-4C: one ok read_inputs, ok read_pages financial page:4 and legal-covenants page:1 and ok search_pack before the submit; every cited page:N read; extract_statements and identity refused not_permitted",
            "consumption": ("CP-4C closes D3 for CP-2G (reads T2H.4 EBITDA and T2H.7 first break; attempt inputs bind the CP-2G head hash; T4E.3 ebitda lists cp2g:T2H.4.<row>.ebitda and first_break lists cp2g:T2H.7.b01.<case>_first), "
                            "for CP-2A (T4E.3 cp2a_scenario and ebitda_decline list cp2a:T2B.1.<row>.*, the row named by CP-2G's lineage) and for CP-4 (T4E.2 facility, lender_protection and additional_debt list cp4:T4C.11.r01.facility, cp4:T4.13.rating.rating, cp4:T4.10.r02.conditions). "
                            "CP-4C's own consumption stays OPEN: CP-5 counts only after a lease extends its scope."),
            "inherited_limitations": "execution.inherited_limitations rule over the directly bound heads in input order, bound at run time",
        },
        "refusals": [{k: v for k, v in r.items() if k in ("id", "class", "issue_kind", "expected_issues", "issue_prefix", "run_level", "against")} for r in ref_list],
        "refusal_rules": {
            "journal": "each refusal is one invalid CP-4C step on attempt 0: attempt consumed, status rejected, limitations equal the issues (bounded 20 lines of 600 characters)",
            "order": "shape issues alone; then claims, valuation, case ids, fulcrum, plan (class-reference and waterfall checks only when the claims and valuation are structurally valid), assessment, then per text field prose issues and guard issues",
            "multi_issue": "v21 (instrument recommendation) and v18 (figure placeholder left unreplaced) are product multi-issue payloads: the product validator reports every guard phrase it finds in the text and every unreplaced placeholder, so their expected_issues lists hold more than one entry; every other refusal payload gives exactly one issue (v02 included: after the kind/source mismatch the source-specific amount checks are skipped)",
            "stale": "v24 to v27 validator-only on a literal Upstream; run level: stale_binding at the next G1 call, no attempt consumed, no step journaled; one clone test per upstream (CP-1, CP-2A, CP-4, CP-2G)",
            "not_refusals": "a missing claim amount, an unassessed multiple, a missing CP-2G EBITDA, a missing CP-1 total debt (honest gaps), and a CP-1 T4.18 that does not show the term loan SECURED and SENIOR is a validator issue not exercised by any payload (the frozen CP-1 shows both)",
        },
        "cases": {},
    }
    for name, b in built.items():
        e = dict(b)
        e["execution"] = manifest["cases"].get(name, {}).get("execution") or PCASE_EXEC.get(name)
        expected["cases"][name] = e
    expected["cases"]["positive"]["plan_order"] = plan
    expected["cases"]["gap"]["plan_order"] = plan
    for k in ("positive", "gap"):
        expected["cases"][k]["cp0"] = {"consumer_rows": ["CP-1", "CP-2A", "CP-4", "CP-2G", "CP-4C"], "validator_issues": [], "T8_commands": [[m, f"Run {m}"] for m in ("CP-1", "CP-2A", "CP-4", "CP-2G", "CP-4C")]}
    expected["cases"]["refused"] = {"execution": "run", "plan_order": plan, "cp0": {"validator_issues": [], "settled_status": "restricted", "T8_commands": [[m, "DO NOT RUN"] for m in ("CP-1", "CP-2A", "CP-4", "CP-2G", "CP-4C")]},
                                    "refused_begins": [{"module_id": "CP-1", "reason": "CP-0 has not authorized this consumer's source readiness"}], "refusal": "cp1_not_authorized",
                                    "attempts": ["CP-0"], "heads": ["CP-0"], "receipt": "verifies", "must_not_appear": ["a CP-2A, CP-4, CP-2G or CP-4C ticket, attempt, head or table", "a recovery of 0 standing for a missing one"]}
    expected["cases"]["blocked"] = {"plan_order": plan, "attempt_0": {"payload": "r01", "result_status": "rejected", "limitations": by_id["r01"]["expected_issues"]},
                                    "attempt_1": {"payload": "v13", "repair_of": "attempt_0", "repair_issues": by_id["r01"]["expected_issues"], "result_status": "blocked", "limitations": by_id["v13"]["expected_issues"]},
                                    "head": {"module_id": "CP-4C", "status": "blocked", "tables": 0, "facts": 0}, "receipt": "verifies", "must_not_appear": ["a CP-4C table or fact", "a third attempt"]}
    expected["cases"]["cp2g_blocked"] = {"plan_order": plan, "cp2g": {"attempt_0": "CP-2G refusals r01 (rejected)", "attempt_1": "CP-2G refusals v13 (blocked)", "head": "blocked, no tables"},
                                         "cp4c_begin": {"refused": True, "error": "ValueError", "message": "Required upstream is unrun, stale or blocked", "rule": "a blocked head is bound only under a restricted edge; CP-2G is a required edge (block)",
                                                        "consumes_attempt": False, "journals_step": False},
                                         "refusal": "cp4c_blocked", "refusal_note": "the 'refusal' field of the review outcome returned by the CP-2G attempt-1 submit (_refusal_code: module 'CP-4C' -> 'cp4c', kind 'blocked')",
                                         "must_not_appear": ["a CP-4C attempt, head, table or fact"]}
    tf = next(f for f in built["positive"]["facts"] if f["fact_id"] == TAMPER_TARGET)
    assert tf["text"] == TAMPER_FROM
    expected["tamper"] = {
        "case": "positive (closed run, receipt sealed)", "target_fact": TAMPER_TARGET, "from": TAMPER_FROM, "to": TAMPER_TO,
        "why_this_fact": "the table cell holds only the fact id and the step output holds the submission, so the value-break text lives only in the result Module; cp4c.probe rebuilds it from the journaled payload and the bound heads (stress valuation breaks at the term loan)",
        "recipe": [
            "1. Copy the closed positive store directory (blobs, snapshots, current, audit) to a scratch path.",
            f"2. Load the CP-4C head's result Module; replace only the text of fact {TAMPER_TARGET} (its shown spelling is that text); every other fact, table, claim and limitation unchanged.",
            "3. Serialise the forged Module as Execution._store does (model_dump_json); its sha256 R2 equals Module.content_hash(); write blobs/R2.",
            "4. Build a new ExecutionSnapshot equal to the current one with the CP-4C Attempt.result_sha256 and Head.result_sha256 set to R2 and the same parent; write snapshots/<its sha256>.json and rewrite current.",
            "5. In the retained receipt: set the CP-4C SettledHead.result_sha256 to R2; set receipt.snapshot_sha256 and the CP-4C settling OwnerSubmission.snapshot_after_sha256 to the new digest (record re-retained under its new content hash, the old record deleted); rewrite audit/receipt.sha256 with the forged receipt's content_hash.",
        ],
        "expect": {"passes": "everything upstream of the probe: audit inventory, blob and snapshot hashes, ancestor walk, head_of equality, begin and publication records, call and read replay, journaled-step replay",
                   "refuses": "cp4c.probe raises WorkflowError('identity_mismatch'); verify_owner_run_receipt raises identity_mismatch",
                   "test_asserts": "_verify_audit and every check before _PROBES pass on the forged copy; then cp4c.probe raises identity_mismatch (asserting identity_mismatch alone would not show the probe was reached)"},
        "step_output_edit": "an edited CP-4C step output is caught by the store's blob hash check, not by the probe (recorded limitation)",
    }
    # digit-free literals and no spelled upstream figure in stored text
    for case in ("positive", "gap"):
        sub = SUBMISSION[case]
        for t_ in prose_texts(sub):
            assert not re.search(r"[0-9]", re.sub(r"CP-[0-9]{1,2}[A-Z]?", "", re.sub(r"\{\{FIG:[a-z_0-9]+\|[^}]*\}\}", "", t_))), t_
        for _, t_, _ in split_text_fields(sub):
            if t_:
                assert not re.search(r"[0-9{}\[\]]", re.sub(r"\{\{FIG:[a-z_0-9]+\|[^}]*\}\}", "", t_)), t_
                assert not guard_issues("p", t_), t_
        assert content_issues(sub, built[case]["waterfall"], pages_of(case)) == [], (case, content_issues(sub, built[case]["waterfall"], pages_of(case)))
    for k, sub in FIXTURE_SUB.items():
        assert content_issues(sub, built[k]["waterfall"], pages_of("positive")) == [], (k, content_issues(sub, built[k]["waterfall"], pages_of("positive")))
    for name, b in built.items():
        spelled = {v["spelled"] for v in b["figures"].values() if v.get("spelled")}
        for x in b["facts"]:
            for key in ("text", "limitation"):
                assert not any(sp in str(x.get(key) or "") for sp in spelled), (name, x["fact_id"], key)
        for t_ in b["own_limitations"]:
            assert not any(sp in t_ for sp in spelled), (name, t_)
        # one fact per column in every row, and every registered table id is a methodology id
        for t in b["tables"]:
            assert t["table_id"] in MOD["CP-4C"]["table_ids"]
            fields = None
            for r in t["rows"]:
                fl = [f.rsplit(".", 1)[1] for f in r["fact_ids"]]
                fields = fields or fl
                assert fl == fields and len(set(fl)) == len(fl), (name, t["table_id"], r["row_id"])
    OUT.mkdir(parents=True, exist_ok=True)
    for fname, obj in (("manifest.json", manifest), ("submissions.json", submissions), ("expected.json", expected)):
        (OUT / fname).write_text(json.dumps(obj, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


PCASE_EXEC = {"positive": "run", "gap": "run", "fixture_ev_zero": "composer_only", "fixture_ebitda_missing": "composer_only", "fixture_debt_missing": "composer_only"}

if __name__ == "__main__":
    sys.exit(main())
