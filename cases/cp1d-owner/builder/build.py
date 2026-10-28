"""Writes cases/cp1d-owner/{manifest,submissions,expected}.json (stdlib only).

Independent transcription of the CP-1D (Earnings quality) composition rules written in
work/lead/cp1d-owner-preparation/lease-draft.md. deploy_vii is never imported here. Every number is
derived from the frozen financial pages (cases/financial/manifest.json, hash-checked) and the
synthetic bridge source defined below, by exact rational arithmetic (fractions.Fraction) checked
against decimal.Context(prec=38, ROUND_HALF_EVEN).

Run: python3 -I cases/cp1d-owner/builder/build.py   (from the repository root)
"""

import copy
import hashlib
import json
import re
import sys
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "cases" / "cp1d-owner"
D = Decimal
CTX = Context(prec=38, rounding=ROUND_HALF_EVEN)


def pinned(path, sha):
    data = (ROOT / path).read_bytes()
    assert hashlib.sha256(data).hexdigest() == sha, path
    return json.loads(data)


FIN_SHA = "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432"
SNAP_SUB_SHA = "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c"
METH_SHA = "1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6"
FIN = pinned("cases/financial/manifest.json", FIN_SHA)
SNAP = pinned("cases/snapshot/submissions.json", SNAP_SUB_SHA)
METH = pinned("src/deploy_vii/methodology.json", METH_SHA)


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


SRC = {s["source_id"]: s for s in FIN["sources"]}
for _s in SRC.values():
    assert page_sha([p["text"] for p in _s["pages"]]) == _s["sha256"]
FPAGE = {p["locator"]: p["text"] for p in SRC["financial"]["pages"]}

# --- 1. CP-1 operands from the frozen pages -----------------------------------------------------


def row_values(page, label, count):
    for line in FPAGE[page].split("\n"):
        if line.startswith(label + "  "):
            tokens = line[len(label):].split()
            assert len(tokens) == count, (label, tokens)
            return [D(t[1:-1]) * -1 if t.startswith("(") else D(t) for t in tokens]
    raise AssertionError(label)


EBITDA_Q = row_values("page:2", "Reported EBITDA", 5)
ADJ_Q = row_values("page:2", "Adjusted EBITDA", 5)
CFO_Q = row_values("page:3", "Operating cash flow", 5)
DEBT_BS = row_values("page:4", "Total debt", 6)
CASH_BS = row_values("page:4", "Cash and cash equivalents", 6)
SGA_Q = row_values("page:2", "Selling general and administrative expenses including depreciation", 5)
assert sum(EBITDA_Q[:4]) == EBITDA_Q[4] and sum(ADJ_Q[:4]) == ADJ_Q[4] and sum(CFO_Q[:4]) == CFO_Q[4]
CP1 = {
    "ebitda": sum(EBITDA_Q[:4]),
    "adjusted_ebitda": sum(ADJ_Q[:4]),
    "cfo_adjusted": sum(CFO_Q[:4]),  # cfo_reported + lease cash + interest in financing, all zero
    "total_debt": DEBT_BS[4],
    "net_debt": DEBT_BS[4] - CASH_BS[4],
}
o = FIN["q4_ltm_derived_source_units"]
assert CP1["ebitda"] == D(o["ebitda"]) == D(o["adjusted_ebitda"]) == CP1["adjusted_ebitda"]
assert CP1["cfo_adjusted"] == D(o["cfo"]) and CP1["total_debt"] == D(o["total_debt"])
assert CP1["net_debt"] == D(o["net_debt"])
assert "No EBITDA adjustments or add-backs occurred in any quarter or FY2025; this disclosure is complete." in FPAGE["page:1"]
assert "There were no pro-forma adjustments, subsequent events, FX cash movements, or noncash debt changes through January 10, 2026." in FPAGE["page:1"]

LTM_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
LTM_COLUMN = "LTM Q4 25 (2025-01-01 to 2025-12-31)"

# --- 2. the synthetic bridge source ---------------------------------------------------------------

BR_HEAD = [
    "NORTHBRIDGE SYNTHETIC GROUP",
    "Management financing-case EBITDA bridge",
    "Published January 10, 2026.",
    "This invented case is test data, not evidence about a real issuer.",
    "Basis: FY2025 (January 1-December 31, 2025); USD; amounts in millions; unaudited management presentation.",
    "Reported EBITDA and statement Adjusted EBITDA for FY2025 are 30.0 each, as in the unaudited statements, which record no adjustment.",
    "The items below are management's proposed financing-case adjustments. None is recorded in the statements. These proposals are not pro-forma adjustments to the statements. Costs and savings are shown as positive add-backs.",
    "Item  Type  Status  Amount",
]
ITEMS = [
    ("Procurement programme savings", "Saving", "Unrealised", "3.00"),
    ("Head-office reorganisation savings", "Saving", "Unrealised", "1.20"),
    ("Legal and advisory fees", "Cost", "Incurred", "0.80"),
    ("Insurance and facilities savings", "Saving", "Unrealised", "1.00"),
]
TOTAL_LABEL = "Total proposed adjustments"
MGMT_LABEL = "Management financing-case EBITDA"


def bridge_page1(gap):
    rows = []
    for label, typ, status, amount in ITEMS:
        if gap and label.startswith("Insurance"):
            amount = "Not stated"
        rows.append(f"{label}  {typ}  {status}  {amount}")
    rows.append(f"{TOTAL_LABEL}  {'Not stated' if gap else '6.00'}")
    rows.append(f"{MGMT_LABEL}  {'Not stated' if gap else '36.00'}")
    return "\n".join(BR_HEAD + rows)


BR_PAGE2 = "\n".join(
    [
        "NORTHBRIDGE SYNTHETIC GROUP",
        "Management financing-case EBITDA bridge: supporting schedule",
        "Published January 10, 2026.",
        "Procurement programme savings: the annualised saving of 3.00 is identified across ten supplier categories. Signed supplier contracts cover an annualised saving of 1.80. Contracts covering the remaining 1.20 are under negotiation. One-time costs to achieve the saving are expected in 2026.",
        "Head-office reorganisation savings: the reorganisation is a management proposal under review. No board approval has been given and no notice has been issued to employees.",
        "Legal and advisory fees: the fees were incurred in FY2025 and are included in selling, general and administrative expenses in the statements. They were 0.20 in each of the four quarters of 2025, and similar fees are expected in 2026.",
        "Insurance and facilities savings: no supporting schedule, contract or quotation is supplied for this item.",
    ]
)
BRIDGE = {
    "positive": [bridge_page1(False), BR_PAGE2],
    "gap": [bridge_page1(True)],
}
# fixture for the "Bridge table not found" refusal: positive page:1 without the table header line
BRIDGE["unparseable"] = [bridge_page1(False).replace("Item  Type  Status  Amount\n", "")]
assert "Item  Type  Status  Amount" not in BRIDGE["unparseable"][0]
BR_NAME = "Management financing-case EBITDA bridge"
BR_LIMIT = "Management-supplied proposals; unaudited and not recorded in the statements."
BR_LIMIT_GAP = BR_LIMIT + " No supporting schedule is supplied."
BR_SHA = {k: page_sha(v) for k, v in BRIDGE.items()}

# consistency of the synthetic source with every frozen figure it touches
assert "Reported EBITDA  7.5  7.5  7.5  7.5  30.0" in FPAGE["page:2"]
assert "Adjusted EBITDA  7.5  7.5  7.5  7.5  30.0" in FPAGE["page:2"]
assert D("1.80") + D("1.20") == D("3.00")
# the bridge says the proposals are not pro-forma adjustments; the frozen page says none occurred: consistent
assert "These proposals are not pro-forma adjustments to the statements." in BRIDGE["positive"][0]
assert sum(D(i[3]) for i in ITEMS) == D("6.00") and CP1["adjusted_ebitda"] + D("6.00") == D("36.00")
assert D("0.20") * 4 == D("0.80") and all(x >= D("0.20") for x in SGA_Q[:4])  # fees fit inside SG&A


def parse_bridge(pages):
    """The builder's own reading of the bridge table (the lease's rule for the core)."""
    p1 = pages[0].split("\n")
    assert any(l.startswith("Basis: FY2025 (January 1-December 31, 2025)") for l in p1)
    start = p1.index("Item  Type  Status  Amount")
    items, totals = [], {}
    for line in p1[start + 1:]:
        parts = re.split(r"  +", line)
        amt = lambda t: None if t == "Not stated" else D(t)  # noqa: E731
        if len(parts) == 4:
            items.append({"label": parts[0], "type": parts[1], "status": parts[2], "amount": amt(parts[3]), "line": line})
        else:
            assert len(parts) == 2, line
            totals[parts[0]] = {"amount": amt(parts[1]), "line": line}
    return items, totals


# --- 3. arithmetic & display ----------------------------------------------------------------------


def q38(f):
    f = Fraction(f)
    if f == 0:
        return D(0)
    with localcontext(CTX):
        return D(f.numerator) / D(f.denominator)


def div(n, d):
    """One division of exact decimals; asserted equal to the correctly rounded rational."""
    with localcontext(CTX):
        v = n / d
    assert v == q38(Fraction(n) / Fraction(d)), (n, d)
    return v


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
    body = f"{abs(r):,.{places}f}"
    return (f"({body})" if r < 0 else body) + suffix


UNIT = {"amount": "MILLIONS", "multiple": "MULTIPLE", "percent": "PERCENT"}
TOKEN = {"amount": "US$ m", "multiple": "x", "percent": "%"}

# --- 4. CP-1 figure references (fact ids bound at run time) -----------------------------------------

FIGS = {
    "adjusted_ebitda_ltm": ("adjusted_ebitda", "amount", None),
    "ebitda_ltm": ("ebitda", "amount", None),
    "cfo_ltm": ("cfo_adjusted", "amount", None),
    "total_debt_ltm": ("total_debt", "amount", None),
    "net_debt_ltm": ("net_debt", "amount", None),
    "total_leverage_adjusted": ("total_leverage_adjusted", "multiple", Fraction(5, 3)),
    "net_leverage_adjusted": ("net_leverage_adjusted", "multiple", Fraction(1)),
}
CP1_AMT = {"adjusted_ebitda": D("30.0"), "ebitda": D("30.0"), "cfo_adjusted": D("19.00"), "total_debt": D("50.00"), "net_debt": D("30.00")}
for _k, _v in CP1_AMT.items():
    assert _v == CP1[_k]
FIGURES = {}
for name, (metric, uc, ratio) in FIGS.items():
    val = q38(ratio) if ratio is not None else CP1_AMT[metric]
    FIGURES[name] = {
        "metric": metric, "table_id": "T4.10", "period": LTM_PERIOD,
        "label": f"{LTM_COLUMN} · {metric}", "unit": UNIT[uc], "unit_token": TOKEN[uc],
        "amount_exact": norm(val), "spelled": show(val, uc), "value_class": "source" if metric == "total_debt" else "calculated",
        "fact_id": "interface-fact:<sha256>; bound at run time, never literal",
    }
assert FIGURES["total_leverage_adjusted"]["spelled"] == "1.67x" and FIGURES["net_leverage_adjusted"]["spelled"] == "1.00x"
assert D(FIN["q4_ltm_metric_oracle"]["total_leverage_adjusted"]["numerator"]) / D(FIN["q4_ltm_metric_oracle"]["total_leverage_adjusted"]["denominator"]) == D(50) / D(30)


def fig(n):
    return "{{FIG:" + n + "|" + FIGURES[n]["unit_token"] + "}}"


# --- 5. citations -----------------------------------------------------------------------------------


def cite(source_id, page, quote):
    if source_id == "bridge":
        text = BRIDGE["positive"][page - 1]
        sha = BR_SHA["positive"]
    else:
        text = SRC[source_id]["pages"][page - 1]["text"]
        sha = SRC[source_id]["sha256"]
    assert quote in text.split("\n") or quote in text, quote
    return {"source_id": source_id, "source_sha256": sha, "locator": f"page:{page}", "quote": quote}


def gap_cite(source_id, page, quote):
    c = cite(source_id, page, quote) if source_id != "bridge" else {
        "source_id": "bridge", "source_sha256": BR_SHA["gap"], "locator": f"page:{page}", "quote": quote}
    if source_id == "bridge":
        assert quote in BRIDGE["gap"][page - 1]
    return c


# --- 6. submissions -----------------------------------------------------------------------------------

Q = {  # evidence quotes (verbatim substrings of bridge page:2)
    "a01": "Signed supplier contracts cover an annualised saving of 1.80.",
    "a02": "No board approval has been given and no notice has been issued to employees.",
    "a03": "They were 0.20 in each of the four quarters of 2025, and similar fees are expected in 2026.",
}
CAT = "Analyst Interpretation"


def assessment(label, ach, rec, frac, ev, rationale, limitation=None, basis=None):
    return {"addback": label, "achievability": ach, "recurrence": rec, "accepted_fraction": frac, "accepted_basis": basis,
            "category": CAT, "rationale": rationale, "evidence": ev, "limitation": limitation}


POS_ASSESS = [
    assessment("Procurement programme savings", "Partly supported", "Not applicable", None, [cite("bridge", 2, Q["a01"])],
               "Signed supplier contracts cover {T1D.2.a01.basis|US$ m} of the proposed saving of {T1D.1.a01.claimed|US$ m} and the remainder is still under negotiation, so only the contracted amount is accepted.",
               "The accepted amount is the contracted amount; contracts may not be delivered in full.", cite("bridge", 2, Q["a01"])),
    assessment("Head-office reorganisation savings", "Not supported", "Not applicable", None, [cite("bridge", 2, Q["a02"])],
               "The reorganisation is a proposal under review without approval, so the saving of {T1D.1.a02.claimed|US$ m} cannot be treated as achievable on the evidence."),
    assessment("Legal and advisory fees", "Supported", "Recurring", None, [cite("bridge", 2, Q["a03"])],
               "The fees were incurred in every quarter of the year and are expected again, so they are a recurring cost of the business and not an add-back."),
    assessment("Insurance and facilities savings", "Insufficient evidence", "Not applicable", None, [],
               "No schedule, contract or quotation supports the proposed saving of {T1D.1.a04.claimed|US$ m}."),
]
POS_OVERALL = {
    "rationale": f"The statements record no adjustment: adjusted EBITDA is {fig('adjusted_ebitda_ltm')} and total leverage is {fig('total_leverage_adjusted')}. Only the contracted part of the procurement saving is supported, so leverage on supported earnings is lower than on the statements and higher than in the management case.",
    "category": CAT, "confidence": "Medium", "limitation": "Add-back evidence is limited to management-supplied schedules.", "evidence": [],
}
POS_GAPS = [{"gap": "No independent evidence of contract delivery or board approval is in the pack.",
             "why_it_matters": "The accepted share rests on management's own schedule.",
             "affected_analysis": "Add-back assessment", "severity": "Material",
             "action": "Obtain signed contract copies and board minutes."}]
GAP_ASSESS = [
    assessment("Procurement programme savings", "Insufficient evidence", "Not applicable", None, [],
               "The bridge source supplies no supporting schedule, so the proposed saving of {T1D.1.a01.claimed|US$ m} cannot be tested."),
    assessment("Head-office reorganisation savings", "Insufficient evidence", "Not applicable", None, [],
               "The bridge source supplies no supporting schedule, so the proposed saving of {T1D.1.a02.claimed|US$ m} cannot be tested."),
    assessment("Legal and advisory fees", "Insufficient evidence", "Not assessable", None, [],
               "The bridge source supplies no schedule of the fees by quarter, so recurrence cannot be assessed."),
    assessment("Insurance and facilities savings", "Insufficient evidence", "Not applicable", None, [],
               "The proposed saving has no stated amount and no schedule."),
]
GAP_OVERALL = {
    "rationale": f"The bridge source supplies no supporting schedule and states no amount for one item, so no add-back is accepted and leverage is shown on the statements' earnings of {fig('adjusted_ebitda_ltm')} only.",
    "category": CAT, "confidence": "Low", "limitation": "No add-back could be tested against evidence.", "evidence": [],
}
GAP_GAPS = [{"gap": "The bridge source has no supporting schedule and omits one amount.",
             "why_it_matters": "No add-back can be tested, so management leverage cannot be compared with supported leverage.",
             "affected_analysis": "Add-back assessment", "severity": "Material",
             "action": "Request the supporting schedule and the missing amount from management."}]
STMT_OVERALL = {
    "rationale": f"The statements record no adjustment and no management bridge is supplied, so there is nothing to challenge: adjusted EBITDA is {fig('adjusted_ebitda_ltm')} and total leverage is {fig('total_leverage_adjusted')}.",
    "category": CAT, "confidence": "Medium", "limitation": "No management bridge is in the pack.",
    "evidence": [cite("financial", 1, "No EBITDA adjustments or add-backs occurred in any quarter or FY2025; this disclosure is complete.")],
}
SUBMISSION = {
    "positive": {"assessments": POS_ASSESS, "overall": POS_OVERALL, "gaps": POS_GAPS},
    "statements_only": {"assessments": [], "overall": STMT_OVERALL, "gaps": []},
    "gap": {"assessments": GAP_ASSESS, "overall": GAP_OVERALL, "gaps": GAP_GAPS},
}


def mutate(base, fn):
    p = copy.deepcopy(base)
    fn(p)
    return p


REFUSAL_DEFS = [
    ("r01", "unknown add-back", "positive", lambda p: p["assessments"][1].__setitem__("addback", "Pricing programme savings"),
     ["Unknown add-back: Pricing programme savings", "Assess each bridge add-back exactly once: Head-office reorganisation savings"]),
    ("r02", "add-back not assessed", "positive", lambda p: p["assessments"].pop(3),
     ["Assess each bridge add-back exactly once: Insurance and facilities savings"]),
    ("r03", "fraction and basis both missing on Partly supported", "positive", lambda p: p["assessments"][0].__setitem__("accepted_basis", None),
     ["Accepted basis or accepted fraction required for Partly supported: Procurement programme savings"]),
    ("r04", "fraction on another achievability", "positive", lambda p: p["assessments"][1].__setitem__("accepted_fraction", "0.50"),
     ["Accepted fraction only applies to Partly supported: Head-office reorganisation savings"]),
    ("r05", "fraction out of range", "positive", lambda p: p["assessments"][0].update(accepted_basis=None, accepted_fraction="1.50"),
     ["Accepted fraction must be a decimal above 0 and below 1 with at most two places: Procurement programme savings"]),
    ("r06", "evidence required for an accepted add-back", "positive", lambda p: p["assessments"][0].__setitem__("evidence", []),
     ["Evidence required for an accepted add-back: Procurement programme savings"]),
    ("r07", "recurrence does not fit the type", "positive", lambda p: p["assessments"][1].__setitem__("recurrence", "Recurring"),
     ["Recurrence does not fit the add-back type: Head-office reorganisation savings"]),
    ("r08", "not assessable without insufficient evidence", "positive", lambda p: p["assessments"][2].__setitem__("recurrence", "Not assessable"),
     ["Recurrence can be not assessable only with insufficient evidence: Legal and advisory fees"]),
    ("r09", "bare figure in rationale", "positive",
     lambda p: p["assessments"][1].__setitem__("rationale", "The reorganisation is a proposal under review without approval, so the saving of 1.2 cannot be treated as achievable on the evidence."),
     ["Bare figure: 1.2"]),
    ("r10", "quote not in the located page", "positive",
     lambda p: p["assessments"][0]["evidence"][0].__setitem__("quote", "Signed supplier contracts cover an annualised saving of 2.00."),
     ["Quote/locator mismatch: quote not found under bridge page:2 ("]),
    ("r11", "confidence High on the management basis", "positive", lambda p: p["overall"].__setitem__("confidence", "High"),
     ["Confidence cannot be High: the add-back evidence is management-supplied"]),
    ("r12", "accepting an unstated amount", "gap",
     lambda p: p["assessments"][3].update(achievability="Partly supported", accepted_fraction="0.50",
                                          evidence=[gap_cite("bridge", 1, "Insurance and facilities savings  Saving  Unrealised  Not stated")]),
     ["Cannot accept an unstated amount: Insurance and facilities savings"]),
    ("r13", "assessment with no bridge in the pack", "statements_only",
     lambda p: p["assessments"].append(assessment("Procurement programme savings", "Insufficient evidence", "Not applicable", None, [], "No bridge is supplied.")),
     ["Assessment given without a bridge in the pack: Procurement programme savings"]),
    ("r14", "bridge table not found", "statements_only", lambda p: None, ["Bridge table not found"]),
    ("r15", "evidence required when no bridge is supplied", "statements_only", lambda p: p["overall"].__setitem__("evidence", []),
     ["Evidence required when no bridge is supplied: the statements' add-back disclosure"]),
    ("r16", "fraction and basis both given", "positive", lambda p: p["assessments"][0].__setitem__("accepted_fraction", "0.60"),
     ["Give either an accepted basis or an accepted fraction, not both: Procurement programme savings"]),
    ("r17", "basis amount not below the proposed amount", "positive",
     lambda p: p["assessments"][0].__setitem__("accepted_basis", cite("bridge", 2, "the annualised saving of 3.00 is identified across ten supplier categories")),
     ["Accepted basis must be above 0 and below the proposed amount: Procurement programme savings"]),
    ("r18", "basis quote without exactly one amount", "positive",
     lambda p: p["assessments"][0].__setitem__("accepted_basis", cite("bridge", 2, "Signed supplier contracts cover an annualised saving of 1.80. Contracts covering the remaining 1.20 are under negotiation.")),
     ["Accepted basis quote must contain exactly one amount: Procurement programme savings"]),
    ("r19", "basis on another achievability", "positive", lambda p: p["assessments"][1].__setitem__("accepted_basis", cite("bridge", 2, Q["a01"])),
     ["Accepted basis only applies to Partly supported: Head-office reorganisation savings"]),
]
PACK_OF = {"r14": "unparseable"}
REFUSALS = []
for rid, klass, base, fn, issues in REFUSAL_DEFS:
    REFUSALS.append({"id": rid, "class": klass, "base_case": base, "pack": PACK_OF.get(rid, base), "payload": mutate(SUBMISSION[base], fn), "expected_issues": issues,
                     "issue_match": "each expected issue appears (prefix match where the text ends in an open parenthesis); no other issue"})
REFUSALS[0]["note"] = "Renaming a row leaves the real row unassessed, so both issues appear"
REFUSALS[13]["note"] = "manifest synthetic_source.fixtures.bridge_table_not_found: a bridge source whose page:1 has no 'Item  Type  Status  Amount' header; the issue returns alone"
# the payloads that cite pages carry the pages a valid attempt reads (tool_calls); the unread-page refusal is a tool-level class
TOOL_CALLS = {
    "positive": [
        {"tool": "read_inputs", "arguments": None},
        {"tool": "read_pages", "arguments": {"source_id": "bridge", "first_page": 2, "last_page": 2},
         "expect_spans": [{"source_id": "bridge", "locator": "page:2"}]},
    ],
    "statements_only": [
        {"tool": "read_inputs", "arguments": None},
        {"tool": "read_pages", "arguments": {"source_id": "financial", "first_page": 1, "last_page": 1},
         "expect_spans": [{"source_id": "financial", "locator": "page:1"}]},
    ],
    "gap": [
        {"tool": "read_inputs", "arguments": None},
        {"tool": "read_pages", "arguments": {"source_id": "bridge", "first_page": 1, "last_page": 1},
         "expect_spans": [{"source_id": "bridge", "locator": "page:1"}]},
    ],
}
TOOL_REFUSALS = [
    {"id": "t01", "class": "cited_page_not_read", "base_case": "positive", "payload": "submissions.json positive earnings_quality (valid)",
     "calls_before_submit": [{"tool": "read_inputs", "arguments": None}],
     "disposition": "invalid attempt 0 (journaled rule unread_citation_issues against Seen); re-begun as attempt 1 with repair_of set; a valid attempt 1 with tool_calls.positive yields a verifying receipt",
     "expected_issues": ["Cited page not read through read_pages: bridge page:2"]},
    {"id": "t02", "class": "non-pack invoke", "base_case": "positive",
     "call": {"tool": "web_search", "arguments": {"query": "Northbridge Synthetic Group procurement contracts"}},
     "expected_receipt": {"status": "refused", "reason": "not_permitted"}, "journal": "refused receipt recorded; no step journaled; no attempt consumed"},
    {"id": "t03", "class": "submit before read_inputs", "base_case": "positive", "calls_before_submit": [],
     "expected_error": "not_permitted", "journal": "a raised WorkflowError(\"not_permitted\"); nothing written; no attempt consumed"},
]

# --- 7. composition --------------------------------------------------------------------------------

TABLES = {
    "T1D.1": "Add-back register", "T1D.2": "Add-back assessment", "T1D.3": "Adjusted EBITDA bridge",
    "T1D.4": "Source tie-out and CP-1 reconciliation", "T1D.5": "Add-back share",
    "T1D.6": "Cash conversion and restated leverage", "T1D.7": "Gaps ledger",
}
BLOCKS = {
    "earnings-quality": {"title": "Earnings quality", "owner": "CP-1D", "kind": "dense", "producers": ["CP-1D"],
                         "tabs": [["T1D.2", "Add-back assessment"], ["T1D.3", "Adjusted EBITDA bridge"], ["T1D.5", "Add-back share"]]},
    "restated-leverage": {"title": "Cash conversion and restated leverage", "owner": "CP-1D", "kind": "dense", "producers": ["CP-1D"],
                          "tabs": [["T1D.6", "Cash conversion and leverage"]]},
}
EVIDENCE_TABLES = ["T1D.1", "T1D.4", "cp1_references"]
LIMITATION_TABLES = ["T1D.7"]
EQ = {"Supported": D(1), "Not supported": D(0), "Insufficient evidence": D(0)}


SYNTHETIC = "Synthetic case; not real issuer qualification"
KPI_KEYS = ("adjusted_ebitda", "ebitda", "cfo_adjusted", "total_debt", "net_debt")


def cp1_readiness():
    """The CP-1 `readiness` step literal naming CP-1D (review-precise-1 answer 5); ids and hashes are run-time bound."""
    return {
        "step": "readiness",
        "replaces": "the S1 literal {\"consumers\": []}; the run requests the consumer CP-1D (inputs.requested_consumers = (\"CP-1D\",), inputs.consumers = _requests((\"CP-1D\",)))",
        "payload": {
            "inputs_sha256": "{{PREFILLED:inputs_sha256}}",
            "consumers": [{
                "entry": "CP-1D",
                "requirements": [{
                    "requirement": "consumer_specific_cp1_sufficiency", "status": "limited",
                    "evidence_ids": ["{{KPI:" + k + "|FY-2025}}" for k in KPI_KEYS],
                    "rationale": "Settled adjusted EBITDA, EBITDA, adjusted operating cash flow, total debt and net debt support the add-back challenge; the statements are unaudited.",
                    "actions": ["Retain the unaudited-statement limitation in the add-back challenge."]}],
                "gaps": [{
                    "gap_ids": ["{{GAP_IDS}}"], "relevance": "relevant", "evidence_ids": [],
                    "rationale": "Every retained source-context and audit warning bears on the reliability of the statement earnings CP-1D restates."}]}]},
        "run_time_bindings": {
            "{{PREFILLED:inputs_sha256}}": "inputs.content_hash() of the readiness step inputs (prefilled; never literal)",
            "{{KPI:<key>|FY-2025}}": "evidence_id of the first record of inputs.narrative.inputs.catalogue with kind 'kpi' and record.key == <key> whose record.value.observation_ids contains an id ending '-fy-2025'; keys in order " + ", ".join(KPI_KEYS) + "; none or an unexpected shape fails closed",
            "{{GAP_IDS}}": "every inputs.narrative.gaps[*].gap_id in order (replaces the placeholder element)"},
        "validated_on": "copy of the S1 positive CP-1 head (read-only copy, 2026-10-28, 1132 gaps all WARN): validate_downstream_review() returns no issues; _assess_consumers gives status ready_with_limitations, 0 unassessed requirements, 0 unassessed gaps, no blocking gaps",
        "expected_assessment": {"CP-1D": {"status": "ready_with_limitations", "unassessed_requirements": 0, "unassessed_gaps": 0, "blocking_gaps": [], "requirement_status": "limited"}},
        "negatives": [
            "no gap scope: CP-1D is not_ready",
            "empty evidence_ids: validate_downstream_review refuses ('Sufficiency requires prior evidence...' / '...register evidence...')",
            "requirement status sufficient without actions also validates (the product recommends limited)"],
    }


def build_case(name, sub=None):
    sub = SUBMISSION[name] if sub is None else sub
    bridge = None
    if name != "statements_only":
        bridge = parse_bridge(BRIDGE[name])
    items = bridge[0] if bridge else []
    totals = bridge[1] if bridge else {}
    facts, rows, claims, limits = [], {t: [] for t in TABLES}, [], []

    def fact(table, row, field, label, **kw):
        r = {"fact_id": f"{table}.{row}.{field}", "table_id": table, "row_id": row, "field": field, "label": label}
        r.update(kw)
        facts.append(r)
        return r

    def num(table, row, field, label, v, uc, formula, derives=(), value_class="calculated", citations=None):
        return fact(table, row, field, label, status="known", unit=UNIT[uc], period=LTM_PERIOD, amount_exact=norm(v),
                    shown=show(v, uc, 2 if uc == "amount" else None), **({"currency": "USD", "scale": "1000000", "decimals": 2} if uc == "amount" else {}),
                    value_class=value_class, formula=formula,
                    calculation_id=f"calc:{table}.{row}.{field}" if value_class == "calculated" else None,
                    derives_from=list(derives), **({"citations": citations} if citations else {}))

    def gapf(table, row, field, label, uc, reason, status="missing"):
        return fact(table, row, field, label, status=status, unit=UNIT[uc], period=LTM_PERIOD, amount_exact=None, shown=None, limitation=reason)

    def text(table, row, field, label, v, value_class=None, citations=None):
        return fact(table, row, field, label, status="known", text=v, shown=v, value_class=value_class, **({"citations": citations} if citations else {}))

    def reg(table, row_id, label, fields):
        rows[table].append({"row_id": row_id, "label": label, "fact_ids": [f"{table}.{row_id}.{f}" for f in fields]})

    start = CP1["adjusted_ebitda"]
    cfo, debt, ndebt = CP1["cfo_adjusted"], CP1["total_debt"], CP1["net_debt"]
    # per item
    amap = {a["addback"]: a for a in sub["assessments"]}
    if bridge:
        assert set(amap) == {i["label"] for i in items} and len(amap) == len(sub["assessments"])
    it = []
    for n, item in enumerate(items, 1):
        a = amap[item["label"]]
        ach, rec = a["achievability"], a["recurrence"]
        basis_amt, path = None, "rule"
        if ach == "Partly supported" and a["accepted_basis"] is not None:
            assert a["accepted_fraction"] is None
            digits = re.findall(r"[0-9]+(?:[.][0-9]+)?", a["accepted_basis"]["quote"])
            assert len(digits) == 1, a["accepted_basis"]["quote"]
            basis_amt, path = D(digits[0]), "source"
            assert item["amount"] is not None and 0 < basis_amt < item["amount"]
            frac = div(basis_amt, item["amount"])  # Python computes the share from the cited source amount
            assert frac * item["amount"] == basis_amt
        elif ach == "Partly supported":
            frac, path = D(a["accepted_fraction"]), "judgment"
        else:
            frac = EQ.get(ach, D(0))
        treatment = ("Excluded: recurring" if rec == "Recurring" else "Accepted in full" if ach == "Supported" else
                     "Accepted in part" if ach == "Partly supported" else "Excluded: not supported" if ach == "Not supported" else
                     "Excluded: insufficient evidence")
        if rec == "Recurring":
            frac = D(0)
        claimed = item["amount"]
        accepted = D(0) if frac == 0 else basis_amt if path == "source" else claimed * frac
        if frac != 0:
            assert claimed is not None
        it.append(dict(item, row=f"a{n:02d}", a=a, frac=frac, treatment=treatment, accepted=accepted, basis=basis_amt, path=path,
                       unsupported=None if claimed is None else claimed - accepted))
    # T1D.1
    for i in it:
        r = i["row"]
        cit = [{"source_id": "bridge", "locator": "page:1", "quote": i["line"]}]
        text("T1D.1", r, "type", "Type", i["type"], "source", cit)
        text("T1D.1", r, "status", "Status", i["status"], "source", cit)
        if i["amount"] is None:
            gapf("T1D.1", r, "claimed", "Proposed amount", "amount", "Not stated in the bridge source")
        else:
            num("T1D.1", r, "claimed", "Proposed amount", i["amount"], "amount", "Bridge source amount", (), "source", cit)
        reg("T1D.1", r, i["label"], ["type", "status", "claimed"])
    stmt_add = CP1["adjusted_ebitda"] - CP1["ebitda"]
    text("T1D.1", "stmt", "type", "Type", "Statement adjustment")
    text("T1D.1", "stmt", "status", "Status", "Recorded")
    num("T1D.1", "stmt", "claimed", "Recorded amount", stmt_add, "amount", "CP-1 adjusted_ebitda minus ebitda", ("cp1:adjusted_ebitda_ltm", "cp1:ebitda_ltm"))
    reg("T1D.1", "stmt", "Recorded in the statements (CP-1)", ["type", "status", "claimed"])
    assert stmt_add == 0
    # T1D.2
    for i in it:
        r, a = i["row"], i["a"]
        text("T1D.2", r, "achievability", "Achievability", a["achievability"], "analyst_judgment")
        text("T1D.2", r, "recurrence", "Recurrence", a["recurrence"], "analyst_judgment")
        if i["path"] == "source":
            bc = [{"source_id": "bridge", "locator": a["accepted_basis"]["locator"], "quote": a["accepted_basis"]["quote"]}]
            num("T1D.2", r, "basis", "Source-supported amount", i["basis"], "amount", "Amount in the cited quote", (), "source", bc)
            num("T1D.2", r, "applied_fraction", "Share accepted", i["frac"], "percent", "Source-supported amount / proposed amount",
                (f"T1D.2.{r}.basis", f"T1D.1.{r}.claimed"))
            num("T1D.2", r, "accepted", "Accepted amount", i["accepted"], "amount", "Source-supported amount", (f"T1D.2.{r}.basis",))
        else:
            gapf("T1D.2", r, "basis", "Source-supported amount", "amount", "No source amount is cited: the share follows the achievability rule or the analyst fraction", "not_applicable")
            if i["path"] == "judgment":
                num("T1D.2", r, "applied_fraction", "Share accepted", i["frac"], "percent", "Analyst accepted fraction", (), "analyst_judgment")
            else:
                num("T1D.2", r, "applied_fraction", "Share accepted", i["frac"], "percent", "Rule: Supported 100%; otherwise 0; Recurring 0")
            if i["frac"] == 0:
                num("T1D.2", r, "accepted", "Accepted amount", i["accepted"], "amount", "Zero by rule (share accepted is 0)", (f"T1D.2.{r}.applied_fraction",))
            else:
                num("T1D.2", r, "accepted", "Accepted amount", i["accepted"], "amount", "Proposed amount x share accepted", (f"T1D.1.{r}.claimed", f"T1D.2.{r}.applied_fraction"))
        text("T1D.2", r, "treatment", "Treatment", i["treatment"])
        if i["unsupported"] is None:
            gapf("T1D.2", r, "unsupported", "Not accepted", "amount", "Not calculable: the proposed amount is not stated")
        else:
            num("T1D.2", r, "unsupported", "Not accepted", i["unsupported"], "amount", "Proposed amount minus accepted amount", (f"T1D.1.{r}.claimed", f"T1D.2.{r}.accepted"))
        text("T1D.2", r, "evidence", "Evidence", "; ".join(f"{c['source_id']} {c['locator']}" for c in a["evidence"]) or "None located")
        reg("T1D.2", r, i["label"], ["achievability", "recurrence", "basis", "applied_fraction", "treatment", "accepted", "unsupported", "evidence"])
    if not it:
        for f_ in ("achievability", "recurrence", "basis", "applied_fraction", "treatment", "accepted", "unsupported", "evidence"):
            fact("T1D.2", "none", f_, f_, status="not_applicable", unit="PERCENT" if f_ == "applied_fraction" else None, shown=None,
                 limitation="No management bridge is in the pack, so there is no add-back to assess")
        reg("T1D.2", "none", "None", ["achievability", "recurrence", "basis", "applied_fraction", "treatment", "accepted", "unsupported", "evidence"])
    # T1D.3 bridge
    na = "No management bridge is in the pack"
    claimed = None if any(i["amount"] is None for i in it) else sum((i["amount"] for i in it), D(0))
    accepted = sum((i["accepted"] for i in it), D(0))
    mgmt = None if (claimed is None or not bridge) else start + claimed
    supported = start + accepted
    unsupp = None if (claimed is None or not bridge) else claimed - accepted
    num("T1D.3", "start", "value", "Adjusted EBITDA, statements (CP-1)", start, "amount", "CP-1 adjusted_ebitda", ("cp1:adjusted_ebitda_ltm",))
    for row, label, val, formula, der, why in (
        ("claimed", "Proposed add-backs (management)", claimed, "Sum of proposed amounts", ("T1D.1.<each>.claimed",), "Not calculable: a proposed amount is not stated"),
        ("mgmt", "Management financing-case EBITDA", mgmt, "Statement adjusted EBITDA plus proposed add-backs", ("T1D.3.start.value", "T1D.3.claimed.value"), "Not calculable: a proposed amount is not stated"),
    ):
        if not bridge:
            gapf("T1D.3", row, "value", label, "amount", na, "not_applicable")
        elif val is None:
            gapf("T1D.3", row, "value", label, "amount", why)
        else:
            num("T1D.3", row, "value", label, val, "amount", formula, der)
    num("T1D.3", "accepted", "value", "Accepted add-backs", accepted, "amount", "Sum of accepted amounts", ("T1D.2.<each>.accepted",) if it else ())
    num("T1D.3", "supported", "value", "Supported adjusted EBITDA", supported, "amount", "Statement adjusted EBITDA plus accepted add-backs", ("T1D.3.start.value", "T1D.3.accepted.value"))
    if not bridge:
        gapf("T1D.3", "unsupported", "value", "Add-backs not accepted", "amount", na, "not_applicable")
    elif unsupp is None:
        gapf("T1D.3", "unsupported", "value", "Add-backs not accepted", "amount", "Not calculable: a proposed amount is not stated")
    else:
        num("T1D.3", "unsupported", "value", "Add-backs not accepted", unsupp, "amount", "Proposed add-backs minus accepted add-backs", ("T1D.3.claimed.value", "T1D.3.accepted.value"))
    for row, label in (("start", "Adjusted EBITDA, statements (CP-1)"), ("claimed", "Proposed add-backs (management)"), ("mgmt", "Management financing-case EBITDA"),
                       ("accepted", "Accepted add-backs"), ("supported", "Supported adjusted EBITDA"), ("unsupported", "Add-backs not accepted")):
        reg("T1D.3", row, label, ["value"])
    # T1D.4 tie-out
    def tie(row, label, stated, recomputed, source_fact):
        if not bridge:
            for f_, l_ in (("reported", "Stated"), ("recomputed", "Recomputed"), ("difference", "Difference")):
                gapf("T1D.4", row, f_, l_, "amount", na, "not_applicable")
            text("T1D.4", row, "result", "Result", "Not compared")
        elif stated is None or recomputed is None:
            for f_, l_, v in (("reported", "Stated", stated), ("recomputed", "Recomputed", recomputed)):
                if v is None:
                    gapf("T1D.4", row, f_, l_, "amount", "Not stated in the bridge source" if f_ == "reported" else "Not calculable: a proposed amount is not stated")
                else:
                    num("T1D.4", row, f_, l_, v, "amount", "Bridge source amount" if f_ == "reported" else "Recomputed", (source_fact,) if f_ == "recomputed" else (), "source" if f_ == "reported" else "calculated")
            gapf("T1D.4", row, "difference", "Difference", "amount", "Not compared: one side is not available")
            text("T1D.4", row, "result", "Result", "Not compared")
        else:
            num("T1D.4", row, "reported", "Stated", stated, "amount", "Bridge source amount", (), "source")
            num("T1D.4", row, "recomputed", "Recomputed", recomputed, "amount", "Recomputed from the rows", (source_fact,))
            num("T1D.4", row, "difference", "Difference", recomputed - stated, "amount", "Recomputed minus stated", (f"T1D.4.{row}.recomputed", f"T1D.4.{row}.reported"))
            text("T1D.4", row, "result", "Result", "Reconciled" if recomputed == stated else "Differs")
        reg("T1D.4", row, label, ["reported", "recomputed", "difference", "result"])
    tie("proposed_total", "Proposed add-backs: stated total against rows", totals.get(TOTAL_LABEL, {}).get("amount") if bridge else None, claimed, "T1D.3.claimed.value")
    tie("mgmt_ebitda", "Management EBITDA: stated against statement EBITDA plus rows", totals.get(MGMT_LABEL, {}).get("amount") if bridge else None, mgmt, "T1D.3.mgmt.value")
    for row, label, key, fn, uc in (("cp1_total_leverage", "Statement total leverage against CP-1", "total_leverage_adjusted", debt, "multiple"),
                                     ("cp1_net_leverage", "Statement net leverage against CP-1", "net_leverage_adjusted", ndebt, "multiple")):
        rec = div(fn, start)
        cp1v = q38(FIGS[key][2])
        num("T1D.4", row, "reported", "CP-1 reported", cp1v, "multiple", "CP-1 " + key, (f"cp1:{key}",))
        num("T1D.4", row, "recomputed", "Recomputed", rec, "multiple", "Debt / statement adjusted EBITDA", ("cp1:" + ("total_debt_ltm" if row.endswith("total_leverage") else "net_debt_ltm"), "T1D.3.start.value"))
        num("T1D.4", row, "difference", "Difference", rec - cp1v, "multiple", "Recomputed minus CP-1", (f"T1D.4.{row}.recomputed", f"T1D.4.{row}.reported"))
        text("T1D.4", row, "result", "Result", "Reconciled" if rec == cp1v else "Differs")
        assert rec == cp1v
        reg("T1D.4", row, label, ["reported", "recomputed", "difference", "result"])
    # T1D.5 share
    def share(row, label, n, d_, formula, der, na_reason=None, miss=None):
        if na_reason:
            gapf("T1D.5", row, "value", label, "percent", na_reason, "not_applicable")
        elif n is None or d_ is None:
            gapf("T1D.5", row, "value", label, "percent", miss)
        else:
            num("T1D.5", row, "value", label, div(n, d_), "percent", formula, der)
        reg("T1D.5", row, label, ["value"])
    share("management", "Proposed add-backs / management EBITDA", claimed, mgmt, "Proposed add-backs / management financing-case EBITDA",
          ("T1D.3.claimed.value", "T1D.3.mgmt.value"), None if bridge else na, "Not calculable: a proposed amount is not stated")
    share("supported", "Accepted add-backs / supported EBITDA", accepted, supported, "Accepted add-backs / supported adjusted EBITDA",
          ("T1D.3.accepted.value", "T1D.3.supported.value"))
    acc_na = None if bridge else na
    if bridge and claimed == 0:
        acc_na = "No add-backs claimed"
    share("acceptance", "Accepted / proposed add-backs", accepted, claimed, "Accepted add-backs / proposed add-backs",
          ("T1D.3.accepted.value", "T1D.3.claimed.value"), acc_na, "Not calculable: a proposed amount is not stated")
    # T1D.6
    basis = (("statements", "Statements (CP-1)", start), ("management", "Management financing case", mgmt), ("supported", "Supported", supported))
    for row, label, e in basis:
        if e is None:
            why = na if not bridge else "Not calculable: a proposed amount is not stated"
            st = "not_applicable" if not bridge else "missing"
            gapf("T1D.6", row, "ebitda", "EBITDA", "amount", why, st)
        else:
            num("T1D.6", row, "ebitda", "EBITDA", e, "amount", "T1D.3 basis value", (f"T1D.3.{ {'statements': 'start'}.get(row, 'mgmt' if row == 'management' else row)}.value",))
        num("T1D.6", row, "cfo", "Operating cash flow", cfo, "amount", "CP-1 cfo_adjusted", ("cp1:cfo_ltm",))
        for f_, l_, n_, uc, fm in (("cfo_to_ebitda", "Operating cash flow / EBITDA", cfo, "percent", "Operating cash flow / EBITDA"),
                                    ("total_leverage", "Total leverage", debt, "multiple", "Total debt / EBITDA"),
                                    ("net_leverage", "Net leverage", ndebt, "multiple", "Net debt / EBITDA")):
            if e is None:
                gapf("T1D.6", row, f_, l_, uc, why, st)
            else:
                dv = ("cp1:cfo_ltm" if f_ == "cfo_to_ebitda" else "cp1:total_debt_ltm" if f_ == "total_leverage" else "cp1:net_debt_ltm", f"T1D.6.{row}.ebitda")
                num("T1D.6", row, f_, l_, div(n_, e), uc, fm, dv)
        reg("T1D.6", row, label, ["ebitda", "cfo", "cfo_to_ebitda", "total_leverage", "net_leverage"])
    # T1D.7 gaps
    for n, g in enumerate(sub["gaps"], 1):
        r = f"g{n:02d}"
        text("T1D.7", r, "id", "Gap id", f"CP-1D-GAP-{n:03d}")
        for k, l_ in (("gap", "Gap"), ("why_it_matters", "Why it matters"), ("affected_analysis", "Affected analysis"), ("severity", "Severity"), ("action", "Action")):
            text("T1D.7", r, k, l_, g[k], "analyst_judgment" if k != "severity" else None)
        reg("T1D.7", r, f"Gap {n}", ["id", "gap", "why_it_matters", "affected_analysis", "severity", "action"])
    if not sub["gaps"]:
        for k in ("id", "gap", "why_it_matters", "affected_analysis", "severity", "action"):
            fact("T1D.7", "none", k, k, status="not_applicable", text=None, shown=None, limitation="None in the CP-1D submission (gaps ledger)")
        reg("T1D.7", "none", "None", ["id", "gap", "why_it_matters", "affected_analysis", "severity", "action"])
    # cp1_references: the CP-1 figures the prose or Python references name (all of FIGS, fixed order)
    cp1_refs = [{"row_id": n, "figure": n, "label": FIGURES[n]["label"], "unit": FIGURES[n]["unit"], "period": LTM_PERIOD,
                 "amount_exact": FIGURES[n]["amount_exact"], "shown": FIGURES[n]["spelled"], "value_class": FIGURES[n]["value_class"], "status": "known"} for n in FIGS]
    # limitations
    if bridge:
        limits.append("Add-back amounts are management's proposals from the bridge source; none is recorded in the statements.")
    else:
        limits.append("No management bridge is in the pack: add-backs are tested only against the statements, which record none.")
    for i in it:
        if i["amount"] is None:
            limits.append(f"Proposed amount is not stated for {i['label']}: every figure that needs it is Not calculable.")
    if any(i["path"] == "judgment" for i in it):
        limits.append("Accepted fractions given without a source amount are analyst assumptions without a source calculation.")
    if any(i["accepted"] > 0 and i["type"] == "Saving" for i in it):
        limits.append("One-time costs to achieve accepted savings are not deducted from supported adjusted EBITDA.")
    if any(i["accepted"] > 0 and i["status"] == "Unrealised" for i in it):
        limits.append("Supported adjusted EBITDA includes accepted savings that are not yet realised; the statements record no adjustment.")
    limits.append("Cash conversion divides CP-1 operating cash flow by EBITDA over the same twelve months; working capital and timing are not separated.")
    limits.append("Supported adjusted EBITDA is an analyst view and does not replace the covenant EBITDA definition tested by CP-4.")
    limits.append("CP-1B (earnings update) is not part of this run, so its variance evidence is not read.")
    for g in sub["gaps"]:
        limits.append(f"Gap ({g['severity']}): {g['gap']}")
    # claims
    by_id = {x["fact_id"]: x for x in facts}

    def ref(fid, tok):
        return ("{" + fid + "|" + tok + "}") if by_id[fid]["status"] == "known" else ("[" + fid + "]")

    for i in it:
        claims.append({"claim_id": f"T1D.2.{i['row']}", "text": i["a"]["rationale"], "limitation": i["a"]["limitation"],
                       "evidence": i["a"]["evidence"]})
    claims.append({"claim_id": "T1D.3.restated", "limitation": None, "text": (
        f"Supported adjusted EBITDA is {ref('T1D.3.supported.value', 'US$ m')} against {ref('T1D.3.mgmt.value', 'US$ m')} in the management financing case "
        f"and {ref('T1D.3.start.value', 'US$ m')} in the statements, so total leverage restates to {ref('T1D.6.supported.total_leverage', 'x')} "
        f"from {ref('T1D.6.statements.total_leverage', 'x')} on the statements.")})
    claims.append({"claim_id": "T1D.5.share", "limitation": None, "text": (
        f"Proposed add-backs are {ref('T1D.5.management.value', '%')} of management financing-case EBITDA and accepted add-backs are "
        f"{ref('T1D.5.supported.value', '%')} of supported adjusted EBITDA.")})
    claims.append({"claim_id": "T1D.6.conversion", "limitation": None, "text": (
        f"Operating cash flow is {ref('T1D.6.statements.cfo_to_ebitda', '%')} of statement EBITDA, {ref('T1D.6.management.cfo_to_ebitda', '%')} of management "
        f"financing-case EBITDA and {ref('T1D.6.supported.cfo_to_ebitda', '%')} of supported adjusted EBITDA.")})
    o = sub["overall"]
    claims.append({"claim_id": "T1D.1.assessment", "text": o["rationale"], "limitation": o["limitation"], "evidence": o["evidence"]})
    tables = [{"table_id": t, "title": title, "rows": rows[t]} for t, title in TABLES.items()]
    return {
        "bridge_source": None if not bridge else {"source_id": "bridge", "sha256": BR_SHA[name], "pages": len(BRIDGE[name])},
        "operands": {k: norm(v) for k, v in {"start": start, "claimed": claimed if bridge else None, "mgmt": mgmt, "accepted": accepted, "supported": supported, "unsupported": unsupp}.items() if v is not None},
        "operands_unavailable": [k for k, v in {"claimed": claimed if bridge else None, "mgmt": mgmt, "unsupported": unsupp}.items() if v is None],
        "facts": facts, "tables": tables, "cp1_references": cp1_refs, "claims": claims, "own_limitations": limits,
        "settled_limitations": list(dict.fromkeys([*limits, SYNTHETIC])),
        "settled_limitations_note": "execution.py:446-452: candidate limitations then 'Synthetic case; not real issuer qualification' (case_kind synthetic), de-duplicated; inherited_limitations are run-bound (execution.py:345-366) and not literal",
        "cp1_readiness": cp1_readiness(),
        "module_status": "restricted", "FP02": fp02(facts, tables),
    }


def analyst_fraction_fixture(positive):
    """Composer fixture for the analyst-fraction path: positive with a01 given as accepted_fraction 0.60 and no basis."""
    payload = copy.deepcopy(SUBMISSION["positive"])
    a01 = payload["assessments"][0]
    a01["accepted_basis"], a01["accepted_fraction"] = None, "0.60"
    a01["rationale"] = ("Signed supplier contracts cover part of the proposed saving of {T1D.1.a01.claimed|US$ m} and the remainder is still under "
                        "negotiation, so only a fraction of the proposed saving is accepted.")
    alt = build_case("positive", payload)
    old = {f["fact_id"]: f for f in positive["facts"]}
    new = {f["fact_id"]: f for f in alt["facts"]}
    assert list(old) == list(new)
    changed = [k for k in old if old[k] != new[k]]
    assert changed == ["T1D.2.a01.basis", "T1D.2.a01.applied_fraction", "T1D.2.a01.accepted"], changed
    for k in ("operands", "operands_unavailable", "tables", "cp1_references"):
        assert alt[k] == positive[k], k
    cells = [(b, t["table_id"], r["row_id"], c["fact_id"]) for b in alt["FP02"]["blocks"] for t in alt["FP02"]["blocks"][b]["tabs"]
             for r in t["rows"] for c in r["cells"]]
    old_cells = [(b, t["table_id"], r["row_id"], c["fact_id"]) for b in positive["FP02"]["blocks"] for t in positive["FP02"]["blocks"][b]["tabs"]
                 for r in t["rows"] for c in r["cells"]]
    assert cells == old_cells
    diff_cells = [c["fact_id"] for b in alt["FP02"]["blocks"] for t, to in zip(alt["FP02"]["blocks"][b]["tabs"], positive["FP02"]["blocks"][b]["tabs"])
                  for r, ro in zip(t["rows"], to["rows"]) for c, co in zip(r["cells"], ro["cells"]) if c != co]
    assert diff_cells == ["T1D.2.a01.basis"], diff_cells
    assert new["T1D.2.a01.applied_fraction"]["amount_exact"] == old["T1D.2.a01.applied_fraction"]["amount_exact"]
    assert new["T1D.2.a01.accepted"]["amount_exact"] == old["T1D.2.a01.accepted"]["amount_exact"]
    added = [x for x in alt["own_limitations"] if x not in positive["own_limitations"]]
    assert added == ["Accepted fractions given without a source amount are analyst assumptions without a source calculation."]
    assert [x for x in positive["own_limitations"] if x not in alt["own_limitations"]] == []
    claims_changed = [c["claim_id"] for c, o in zip(alt["claims"], positive["claims"]) if c != o]
    assert claims_changed == ["T1D.2.a01"], claims_changed
    return {
        "call": "pure earnings_quality(pack=, submission=, upstream=) on the positive pack and upstream",
        "payload_delta": "submissions.positive.earnings_quality with assessments[0] (Procurement programme savings): accepted_basis null, accepted_fraction \"0.60\", rationale below (no basis reference); all else unchanged",
        "rationale": a01["rationale"],
        "fact_deltas": {
            "T1D.2.a01.basis": new["T1D.2.a01.basis"],
            "T1D.2.a01.applied_fraction": new["T1D.2.a01.applied_fraction"],
            "T1D.2.a01.accepted": new["T1D.2.a01.accepted"]},
        "added_limitation": {"text": added[0], "position": "after the per-item unstated-amount limitations, before the saving-cost limitations (same position as in the builder)", "index": alt["own_limitations"].index(added[0])},
        "changed_claims": claims_changed,
        "unchanged": "operands, totals, shares, leverage, every other fact, tables and cp1_references equal the positive case (asserted); FP02 differs only in the T1D.2.a01.basis cell (state not_meaningful); accepted stays 1.80",
        "expected_own_limitations": alt["own_limitations"],
    }


def fp02(facts, tables):
    by_id = {x["fact_id"]: x for x in facts}
    out = {"pathway": "earnings_update", "blocks": {}}
    for bid, b in BLOCKS.items():
        tabs = []
        for tid, label in b["tabs"]:
            t = next(x for x in tables if x["table_id"] == tid)
            rws = [{"row_id": r["row_id"], "label": r["label"], "cells": [
                {"fact_id": f, "field": by_id[f]["field"], "shown": by_id[f].get("shown"),
                 "state": "known" if by_id[f]["status"] == "known" else "not_meaningful" if by_id[f]["status"] == "not_applicable" else "gap"}
                for f in r["fact_ids"]]} for r in t["rows"]]
            tabs.append({"table_id": tid, "label": label, "rows": rws})
        out["blocks"][bid] = {"title": b["title"], "owner": b["owner"], "kind": b["kind"], "state": "populated", "tabs": tabs}
    out["other_blocks"] = "headline-results, variance-drivers, kpi-changes, guidance-signals (CP-1B), ebitda-adjustments and metric-strip (CP-1/MODEL) keep their idle wording: CP-1D fills none of them"
    out["evidence_rail_tables"] = EVIDENCE_TABLES
    out["limitations_rail_tables"] = LIMITATION_TABLES
    return out


# --- 8. CP-0 / CP-1 literals ----------------------------------------------------------------------

LIMIT = "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."
IDENT = cite("identity", 1, "Northbridge Synthetic Group is the issuer and consolidated group.")
FINC = cite("financial", 1, "Currency: USD; amounts in millions.")
BRQ = "Reported EBITDA and statement Adjusted EBITDA for FY2025 are 30.0 each, as in the unaudited statements, which record no adjustment."


def readiness(case):
    rr = copy.deepcopy(SNAP["positive"]["readiness_review"])
    rr["objective"] = "Historical financial foundation and earnings quality"
    bridge_cit = cite("bridge", 1, BRQ) if case == "positive" else gap_cite("bridge", 1, BRQ)
    srcs = [s for s in rr["sources"] if s["source_id"] != "business"]
    if case != "statements_only":
        srcs.append({"source_id": "bridge", "document_family": "Management financing-case bridge", "authority": "issuer",
                     "entity": "Northbridge Synthetic Group", "period": "January 2026",
                     "version_relationship": "Management presentation accompanying the statements", "fidelity": "verified",
                     "citations": [bridge_cit], "limitations": [BR_LIMIT_GAP if case == "gap" else BR_LIMIT]})
    rr["sources"] = srcs
    cp1 = next(c for c in rr["consumers"] if c["module_id"] == "CP-1")
    ids = ["identity", "financial"] + ([] if case == "statements_only" else ["bridge"])
    cits = [IDENT, FINC] + ([] if case == "statements_only" else [bridge_cit])
    lims = [LIMIT] + ([] if case == "statements_only" else [BR_LIMIT_GAP if case == "gap" else BR_LIMIT])
    cp1d = {"module_id": "CP-1D", "readiness": "READY_WITH_LIMITATIONS",
            "evidence_demand": "Settled CP-1 earnings and cash flow, and the management add-back bridge with its supporting schedule" if case != "statements_only"
            else "Settled CP-1 earnings and cash flow and the statements' add-back disclosure",
            "source_ids": ids,
            "rationale": "The add-back challenge can run on settled CP-1 figures and the located bridge with explicit limitations." if case != "statements_only"
            else "The statements record no adjustment and no bridge is supplied; the challenge reduces to confirming that.",
            "citations": cits, "missing_source": None, "limitations": lims}
    rr["consumers"] = [cp1, cp1d]
    rr["analysis"] = [{"claim_id": "source-assessment",
                       "text": "Located statements and the management bridge support historical and earnings-quality analysis with limitations." if case != "statements_only"
                       else "Located statements support historical analysis; no management bridge is supplied.",
                       "citations": cits, "limitation": LIMIT}]
    return rr


def source_context(case):
    sc = copy.deepcopy(SNAP["positive"]["cp1_source_context"])
    sc["sources"] = [s for s in sc["sources"] if s["source_id"] != "business"]
    if case != "statements_only":
        c = cite("bridge", 1, BRQ) if case == "positive" else gap_cite("bridge", 1, BRQ)
        sc["sources"].append({"source_id": "bridge", "classification": "nonfinancial", "document_type": "Management financing-case bridge",
                              "published_on": "2026-01-10", "evidence_class": "internal",
                              "evidence_rationale": "Management presentation without auditor or filing status",
                              "analytical_use": "Add-back bridge for CP-1D", "citations": [c], "event_scan": "unassessed",
                              "event_scan_explanation": "A financing presentation is not event evidence"})
    return sc


REFUSED_CP0 = {
    "note": "Literal CP-0 review for the refused case = tests/test_financial_workflow.py readiness(pack, gap=True) with these two consumer rows appended and this gap row",
    "cp0_consumer_row_cp1d": {"module_id": "CP-1D", "readiness": "CONDITIONAL", "evidence_demand": "Settled CP-1 figures",
                              "source_ids": ["identity"], "rationale": "Quarterly financial statements were not supplied.",
                              "citations": [IDENT], "missing_source": "Quarterly financial statements",
                              "limitations": ["Quarterly financial statements were not supplied."]},
    "gap_row": {"gap_id": "missing-financial", "kind": "source", "severity": "material",
                "description": "Quarterly financial statements were not supplied.", "affected_modules": ["CP-1", "CP-1D"],
                "remediation": "Supply quarterly financial statements"},
}


def main():
    built = {n: build_case(n) for n in ("positive", "statements_only", "gap")}
    run = dict(FIN["run"], pathway="earnings_update", requested_modules=["CP-1D"])
    runs = {n: dict(run, run_id=f"cp1d-owner-{n.replace('_', '-')}") for n in ("positive", "statements_only", "gap", "refused")}
    srcs_ident = [{"source_id": s, "sha256": SRC[s]["sha256"], "reuse": "Every page text and locator stays byte-identical; read by reference, never edited"} for s in ("identity", "financial")]
    manifest = {
        "schema_version": "cp1d-owner-cases/1",
        "scope": "CP-1D (alias CP-1E) Earnings quality: CP-0 to CP-1 to CP-1D over the frozen financial pack, alone and with one new synthetic management bridge source",
        "status": "DRAFT by the cp1d-owner preparation task, 2026-10-28; independent review pending; not executed",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "pins": {"cases/financial/manifest.json": FIN_SHA, "cases/snapshot/submissions.json": SNAP_SUB_SHA, "src/deploy_vii/methodology.json": METH_SHA},
        "financial_baseline": {"path": "cases/financial/manifest.json", "manifest_sha256": FIN_SHA, "sources": srcs_ident},
        "frozen_finding": "The frozen financial pack carries NO add-back bridge: page:1 states 'No EBITDA adjustments or add-backs occurred in any quarter or FY2025; this disclosure is complete.', page:2 Adjusted EBITDA equals Reported EBITDA (30.0) and page:5 says 'Adjusted EBITDA equals reported EBITDA because there are no adjustments'. A promoted CP-1 head over it has an empty T4.17 (probe: 0 facts) and CP-1 refuses a partial or undisclosed add-back disclosure (financial_adapter._addbacks), so an empty T4.17 on a promoted head means a complete, zero bridge.",
        "synthetic_source": {
            "source_id": "bridge", "name": BR_NAME, "status": "ready", "media_type": "text/plain", "extractor": "supplied-representation",
            "extraction_status": "complete", "pack_limitation_positive": BR_LIMIT, "pack_limitation_gap": BR_LIMIT_GAP,
            "positive": {"pages": [{"locator": f"page:{n}", "text": t} for n, t in enumerate(BRIDGE["positive"], 1)], "sha256": BR_SHA["positive"]},
            "gap": {"pages": [{"locator": "page:1", "text": BRIDGE["gap"][0]}], "sha256": BR_SHA["gap"],
                    "derivation": "page:1 equals the positive page:1 except the Insurance and facilities amount and both totals read 'Not stated'; the supporting-schedule page:2 is absent"},
            "fixtures": {"bridge_table_not_found": {
                "pages": [{"locator": "page:1", "text": BRIDGE["unparseable"][0]}], "sha256": page_sha(BRIDGE["unparseable"]),
                "derivation": "the positive page:1 without its 'Item  Type  Status  Amount' header line; used only by refusal r14 (no run)"}},
            "why": "No frozen source carries an add-back to challenge. The source adds management's PROPOSED financing-case adjustments, not recorded in the statements.",
            "consistency_with_frozen_figures": [
                "Reported and statement Adjusted EBITDA for FY2025 are restated as 30.0 each (frozen page:2 rows 'Reported EBITDA' and 'Adjusted EBITDA', FY column 30.0); the source says the statements record no adjustment, as frozen page:1 and page:5 do",
                "FY2025 is January 1-December 31, 2025, the twelve months of CP-1's LTM Q4 25 column",
                "The items are proposals, not occurrences: no acquisition, disposal, pro-forma adjustment, subsequent event or exceptional item (all frozen as nil) is claimed",
                "Legal and advisory fees 0.20 per quarter (0.80) sit inside frozen selling, general and administrative expenses (8.75 per quarter) and change no frozen figure",
                "Item amounts sum to 6.00 and 30.0 + 6.00 = 36.00 (asserted by the builder); contracted 1.80 + under negotiation 1.20 = 3.00",
                "No frozen figure (cash flow, debt, interest, balance sheet) is restated or contradicted"],
        },
        "cases": {
            "positive": {"run": runs["positive"], "pack": "identity + financial + bridge (positive)", "submission": "submissions.json positive", "expected": "expected.json cases.positive",
                         "execution": "closed run: CP-0, CP-1 (five stages, source_context literal with the bridge source), CP-1D"},
            "statements_only": {"run": runs["statements_only"], "pack": "identity + financial, as tests/test_financial_workflow.py make_pack()", "submission": "submissions.json statements_only",
                                "expected": "expected.json cases.statements_only", "execution": "closed run; no bridge source: add-backs are a known zero from the statements, the management basis is not_applicable"},
            "gap": {"run": runs["gap"], "pack": "identity + financial + bridge (gap: no supporting page, one amount and both totals 'Not stated')", "submission": "submissions.json gap",
                    "expected": "expected.json cases.gap", "execution": "closed run: unstated amount is missing (never 0), every item Insufficient evidence, supported EBITDA equals the statements'"},
            "refused": {"run": runs["refused"], "pack": "financial source missing (cases/financial/manifest.json negative_case); identity only", "submission": "submissions.json refused",
                        "expected": "expected.json cases.refused", "execution": "CP-0 only; CP-1 begin raises NotAuthorized; CP-1D never begun"},
        },
        "cp1_fact_selection_rule": {
            "table_id": "T4.10", "period": LTM_PERIOD,
            "predicate": "fact.table_id == 'T4.10' and fact.period == period and fact.label == '<column> · <metric>' with column 'LTM Q4 25 (2025-01-01 to 2025-12-31)'; exactly one match, zero or several fail",
            "metrics": {n: v[0] for n, v in FIGS.items()},
            "probe": "S1 positive promoted CP-1 head, read-only copy, 2026-10-28: ebitda 30.0, adjusted_ebitda 30.0, cfo_adjusted 19.00, total_debt 50.00, net_debt 30.00, total_leverage_adjusted 1.6666666666666666666666666666666666667 (1.67x), net_leverage_adjusted 1.0 (1.00x); all known, value_class calculated except total_debt (source); T4.17 has 0 facts",
        },
        "figures": FIGURES,
        "plan": {"requested_modules": ["CP-1D"], "plan_order": ["CP-0", "CP-1", "CP-1D"], "cp_model": "not requested in these cases. registry.plan(('CP-MODEL','CP-1D')) = (CP-0, CP-1, CP-1D, CP-MODEL), so CP-MODEL would follow CP-1D; it precedes CP-1D only when CP-1B is also planned (plan(('CP-MODEL','CP-1D','CP-1B')) = CP-0, CP-1, CP-1B, CP-MODEL, CP-1D), which G1 refuses (analytical module after the deterministic one) until a lease supports it",
        "host_scope": {"CP-1D": "fixed H1 mapping, never caller-supplied: the pack sources identity, financial and bridge that the prepared pack holds (statements_only: identity, financial)",
                       "protocol": "docs/G1X-OWNER-CORE-PROTOCOL.md section 3: an owner-only step may combine a module_context view with pack sources"}},
    }
    sc_ids = {"positive": "positive", "statements_only": "statements_only", "gap": "gap"}
    submissions = {
        "schema_version": "cp1d-owner-submissions/1",
        "note": "Literal analyst submissions for the earnings_quality step. {{FIG:name|token}} is replaced mechanically by {<CP-1 fact_id>|<token>} after the CP-1 head is inspected (manifest cp1_fact_selection_rule); unreplaced it is malformed run text and fails closed. {T1D.x.y.z|token} references name the module's own facts and are literal. A Partly supported add-back gives either accepted_basis (a citation whose quote holds exactly one source amount; Python computes the share as that amount over the proposed amount) or accepted_fraction (an analyst judgment without a source amount, recorded as analyst_judgment with a limitation). tool_calls.<case> is the literal tool sequence of the earnings_quality attempt: one read_inputs, then read_pages covering every cited page. CP-0 readiness and CP-1 source_context are derived from cases/snapshot/submissions.json (pinned) with the business source replaced by the bridge source; the later CP-1 stages are those of the financial case, unchanged.",
        "figures": FIGURES,
        **{c: {"readiness_review": readiness(c), "cp1_source_context": source_context(c), "cp1_readiness": cp1_readiness(), "earnings_quality": SUBMISSION[c],
               "tool_calls": TOOL_CALLS[c]} for c in sc_ids},
        "refused": REFUSED_CP0,
        "refusals": REFUSALS,
        "tool_refusals": TOOL_REFUSALS,
        "blocked": {"attempt_0": "refusals r06", "attempt_1": "refusals r06",
                    "note": "Both attempts invalid with the same issue; the CP-1D head settles blocked (S1a A3b pattern)"},
    }
    a3b = {"limitations_prefix": "Upstream CP-1B blocked: "}
    expected = {
        "schema_version": "cp1d-owner-expected/1",
        "derivation": "Hand-transcribed recipes of work/lead/cp1d-owner-preparation/lease-draft.md applied to the frozen financial pages and the bridge pages by cases/cp1d-owner/builder/build.py (stdlib only). Each quotient is one division of exact decimals equal to the correctly rounded 38-significant-digit half-even rational (asserted); display follows display.py (ROUND_HALF_UP; amounts 2 dp by the fact's decimals, multiples 2 dp 'x', percents 1 dp '%'). CP-1 constants come from the frozen pages and are asserted against the manifest oracle.",
        "cell_notation": {"shown": "displayed text; unsettled cells follow report_view.fact_spelling (missing -> gap, '∅ G#'; not_applicable -> not_meaningful, '∅ G# n.m.'; G# is report-wide, not literal): shown is null there", "amount_exact": "canonical exact decimal, null when unsettled", "derives_from": "fact ids of this module (T1D...) or 'cp1:<figure>' (a cp1_references row); '<each>' = every row of that table"},
        "id_rules": {"fact_id": "<table>.<row>.<field>", "calculation_id": "calc:<fact_id> on calculated facts", "item_rows": "a01.. in bridge-source order; 'stmt' is the CP-1 statement row", "claims": "T1D.2.aNN (analyst rationale), T1D.3.restated, T1D.5.share, T1D.6.conversion, T1D.1.assessment"},
        "lineage_rule": "A calculated fact's citations are the ordered, de-duplicated concatenation of the citations of the facts in derives_from (CP-1 facts through cp1_references); source facts cite the bridge line. A known fact never derives from a fact that is not known.",
        "d8_table_ids": {
            "families_checked": "T1E.1-T1E.6 and T1D.1-T1D.7 appear only under CP-1D in methodology.json; no other module lists either family; neither is defined anywhere in the repository or the DEPLOY VII reference docs",
            "collisions": [], "register": "T1D.1-T1D.7 (matches the module id; the alias CP-1E canonicalises to CP-1D)",
            "drop": "T1E.1-T1E.6 (alias-named duplicates; no definition, no consumer)", "cp1d_table_ids": list(TABLES), "module_tables_besides": ["cp1_references"]},
        "execution": {
            "entry_kind": "owner-only (registry.step_chain('CP-1D') raises 'CP-1D has no live step contract'); entry owner_core under docs/G1X-OWNER-CORE-PROTOCOL.md",
            "plan_order": ["CP-0", "CP-1", "CP-1D"],
            "statuses": {"CP-0": "restricted", "CP-1": "restricted (financial precedent)", "CP-1D": "restricted: own limitations non-empty and synthetic case"},
            "tool_use": {
                "CP-0": "pack tools plus submit",
                "CP-1": "as the financial slice",
                "CP-1D": {
                    "step": "earnings_quality", "inputs": "module_context", "sources": True, "rules": "journaled",
                    "host_scope": "identity, financial and bridge from the fixed H1 mapping (statements_only: identity and financial)",
                    "acceptance": "exactly one ok read_inputs before the submit, and ok read_pages calls covering every page:N cited by the submit (evidence, accepted_basis, overall.evidence); the literal sequence is submissions.<case>.tool_calls",
                    "rules_mode": "rules='journaled' with the core's RULES(text, seen) (docs/G1X-OWNER-CORE-PROTOCOL.md section 2, amended 2026-10-28), pure over the payload text and the session's Seen; it reuses live/tools.py unread_citation_issues (exact text 'Cited page not read through read_pages: <source_id> page:<n>', product sorted order) and UNBACKED_ABSENCE for any absence claim backed by a recorded search; G1-X calls it at submit and in the verifier in place of ToolRules().issues (which raises for a step that is not a tool-loop step). CP-1D's schema carries no ABSENCE_MARKERS value, so only the cited-page rule can fire; a missed read costs attempt 0 (S1a lease :131 pattern)",
                    "refusals": "submissions.tool_refusals: cited_page_not_read (invalid attempt), invoke of any non-pack tool (refused receipt not_permitted recorded; no step journaled; no attempt consumed), submit before read_inputs (a raised WorkflowError not_permitted; nothing written)",
                    "view": "read_inputs serves the exact context_block view, with no evidence lines: keys upstream [{module_id, status}], bridge {state, source_id, pages, items, totals}, cp1_facts, cp1_t417_rows, cp1_facts_note, inherited_limitations; quotable evidence comes only from read_pages",
                },
            },
            "consumption": {
                "status": "open until a consumer core reads the settled CP-1D head",
                "consumer_facts": ["T1D.3.supported.value", "T1D.6.supported.total_leverage", "T1D.6.supported.net_leverage"],
                "proof": "the consumer's attempt inputs bind Input('CP-1D', head.result_sha256, status) and a consumer fact or claim derives from those facts, consumed through the CP-1D head, not through CP-1",
                "edges": "methodology.json lists CP-1D optional for CP-2, CP-2G, CP-2H, CP-3 and CP-4; CP-2G requires CP-2A and CP-2H requires CP-2G; CP-2G and CP-2H are unleased; cp2_synthesis reads CP-1 and CP-1A; cp3_relative_value.READ_OPTIONAL = CP-1A, CP-4; methods/cp4.md ruling 5; CP-6 has no edge; CP-5 counts only after a lease extends its integrity scope",
                "closure": "a lease amendment that has CP-2, CP-3 or CP-4 read CP-1D, or leases CP-2G/CP-2H, closes D3 (D3)",
            },
            "cp0_t8": {"positive": [["CP-1", "Run CP-1"], ["CP-1D", "Run CP-1D"]]},
        },
        "cp1b": {
            "edge": "CP-1D -> CP-1B is optional, edge rule restricted (registry.edge_rule probe)",
            "limitation_wordings": {
                "unbound": "CP-1B (earnings update) is not part of this run, so its variance evidence is not read.",
                "bound_settled": "CP-1B is bound but its variance evidence is not read in this version.",
                "bound_blocked": "CP-1B is bound but its variance evidence is not read in this version.",
                "bound_blocked_note": "the own line is the bound wording; the inherited line below follows it",
                "blocked_inherited": "Upstream CP-1B blocked: <each CP-1B limitation> (execution.inherited_limitations, not an own limitation)"},
            "unbound": "every case here: plan excludes CP-1B; attempt inputs prepared-pack, CP-0, CP-1 (+ submission tail); own limitation is the unbound wording",
            "settled": "contract only: bound as input with the head's status; v1 reads no CP-1B fact; inherited limitations carry CP-1B's own limitations then its inherited ones (execution.inherited_limitations); the own CP-1B limitation line is the bound wording",
            "blocked": {"contract": "restricted edge: CP-1D begins with input CP-1B status blocked; CP-1D reads nothing from it; its own CP-1B line is the bound wording, followed by the inherited lines prefixed " + a3b["limitations_prefix"] + "; CP-1D settles restricted. A blocked CP-0 or CP-1 blocks CP-1D (edge block) and G1 records a RefusedBegin.",
                        "fixture": {"cp1b_limitation": "Earnings update source missing", "expected_inherited": "Upstream CP-1B blocked: Earnings update source missing",
                                    "expected_own_cp1b_line": "CP-1B is bound but its variance evidence is not read in this version."}},
            "status": "NOT exercisable by a run until G1 supports CP-1B (offline-only step, B1 unintegrated); settled/blocked are contract text plus the literal fixture above for a hand-built snapshot test of execution.current_inputs / inherited_limitations",
        },
        "refusals": [{"id": r["id"], "class": r["class"], "base_case": r["base_case"], "pack": r["pack"], "expected_issues": r["expected_issues"], "disposition": "invalid step on attempt 0 (journaled validator issues), re-begun as attempt 1"} for r in REFUSALS],
        "tool_refusals": TOOL_REFUSALS,
        "refusal_rules": {
            "order": "Content issues follow shape issues; a shape failure returns alone. Issue text is frozen here; the validator must produce each expected_issues entry (prefix match where it ends in an open parenthesis) and no other.",
            "basis_fraction_order": {
                "rule": "The per-assessment basis/fraction rules are shape rules checked for each assessment in this fixed order; the first failure is returned alone for that item and the item's prose (rationale references) is not checked (LEAD ruling 2026-10-28)",
                "steps": [
                    "1 accepted_basis or accepted_fraction given on another achievability: 'Accepted basis only applies to Partly supported: <label>' (basis checked first), else 'Accepted fraction only applies to Partly supported: <label>'",
                    "2 both given: 'Give either an accepted basis or an accepted fraction, not both: <label>'",
                    "3 neither given: 'Accepted basis or accepted fraction required for Partly supported: <label>'",
                    "4 fraction not a decimal above 0 and below 1 with at most two places: 'Accepted fraction must be a decimal above 0 and below 1 with at most two places: <label>'",
                    "5 basis quote not exactly one amount: 'Accepted basis quote must contain exactly one amount: <label>'",
                    "6 basis amount not above 0 and below the proposed amount: 'Accepted basis must be above 0 and below the proposed amount: <label>'"],
                "covers": ["r03", "r04", "r05", "r16", "r17", "r18", "r19"]},
            "recurrence": "Saving requires Not applicable; Cost requires Non-recurring, Recurring or Not assessable; Not assessable only with Insufficient evidence (Cost, Not assessable, Insufficient evidence is valid: the gap legal-fees row)",
            "partly_supported": "exactly one of accepted_basis or accepted_fraction; neither on another achievability; accepted_basis quote holds exactly one amount (a digit run with an optional decimal part) above 0 and below the proposed amount; Python computes the share as that amount over the proposed amount (one division, 38 digits half-even) and the accepted amount equals the cited amount; accepted_fraction is an analyst_judgment with two decimals in (0,1)",
            "confidence": "High is refused whenever a bridge source is present (the evidence is management-supplied); with no bridge the rule does not apply",
            "no_bridge": "no bridge source: any assessment is refused with 'Assessment given without a bridge in the pack: <label>' (no 'Unknown add-back' issues); overall.evidence must be non-empty ('the statements' add-back disclosure')",
            "r15_ruling": "confirmed rule (LEAD 2026-10-28): when the pack has no bridge, overall.evidence (a located citation) is required so that tool use is never vacuous; any located citation satisfies it",
            "unparseable_bridge": "a bridge source whose page:1 lacks the Basis line or the 'Item  Type  Status  Amount' header gives 'Bridge table not found' alone",
            "bare_figure": "the core calls prose.issues(rationale, bound) and emits its text unchanged: exactly 'Bare figure: 1.2'; the module path for a settled claim prefixes 'Claim T1D.2.a02: '",
        },
        "blocked": {"attempt_0": "r06", "attempt_1": "r06", "head_status": "blocked", "tables": "none (a blocked head carries limitations only)",
                    "limitations_contain": "Evidence required for an accepted add-back: Procurement programme savings"},
        "cases": {},
    }
    for n, b in built.items():
        expected["cases"][n] = dict(b)
    expected["composer_fixtures"] = {"analyst_fraction": analyst_fraction_fixture(built["positive"])}
    expected["cases"]["refused"] = {
        "plan_order": ["CP-0", "CP-1", "CP-1D"],
        "CP-0": {"status": "restricted", "T8_commands": {"CP-1": "DO NOT RUN", "CP-1D": "DO NOT RUN"}},
        "refused_begins": [{"module_id": "CP-1", "reason": "str(NotAuthorized): CP-0 has not authorized this consumer's source readiness"}],
        "attempts": ["CP-0"], "heads": ["CP-0"], "cp1d": "never begun (G1 stops the walk after a RefusedBegin)", "model_publication": "not planned", "receipt": "verifies",
        "must_not_appear": ["a CP-1D ticket, attempt, head or table", "a leverage or share of 0 standing for a missing one"],
    }
    # sanity on analyst prose: no digit outside references
    for case, sub in SUBMISSION.items():
        texts = [a["rationale"] for a in sub["assessments"]] + [sub["overall"]["rationale"]]
        for t in texts:
            t2 = re.sub(r"\{\{FIG:[a-z_]+\|[^}]*\}\}|\{T1D\.[0-9a-z_.]+\|[^}]*\}", "", t)
            assert not re.search(r"[0-9]", t2), t
    OUT.mkdir(parents=True, exist_ok=True)
    for name, obj in (("manifest", manifest), ("submissions", submissions), ("expected", expected)):
        (OUT / f"{name}.json").write_text(json.dumps(obj, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
