"""Writes cases/cp1c-owner/{manifest,submissions,expected}.json (stdlib only).

Independent transcription of the CP-1C (Peer benchmark) composition rules written in
work/lead/cp1c-owner-preparation/lease-draft.md. deploy_vii is never imported here. Every number is
derived from the frozen financial pages (cases/financial/manifest.json, hash-checked) and the
SYNTHETIC peer summary source defined below, by exact decimal arithmetic (decimal.Context(prec=38,
ROUND_HALF_EVEN)) cross-checked against exact rationals where the rule says one division.

The peer summary is invented test data (the frozen packs hold one issuer only). It is labelled
synthetic in every place it appears and no figure of it is a real market fact.

Run: python3 -I cases/cp1c-owner/builder/build.py   (from the repository root)
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
OUT = ROOT / "cases" / "cp1c-owner"
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
ISSUER = FIN["run"]["issuer_name"]
assert ISSUER == "Northbridge Synthetic Group"

# --- 0. D8: the table-id collision check, from methodology.json -----------------------------------

TABLES = {
    "T1C.1": "Peer universe",
    "T1C.2": "Peer source figures",
    "T1C.3": "Normalised metrics",
    "T1C.4": "Peer statistics",
    "T1C.5": "Outlier register",
    "T1C.6": "Definition alignment and tie-out",
    "T1C.7": "Gaps ledger",
    "T1C.8": "Peer universe totals",
}
ENTRY = {m["module_id"]: m for m in METH}
# The serialised methodology.json change replaced CP-1C's table_ids (the eleven T4.x ids) with T1C.1-T1C.8.
# The registry pinned above is the landed state: assert it, and rebuild the pre-change ownership from the
# landed registry plus the replaced list, so the recorded D8 evidence is unchanged.
CP1C_REPLACED = ["T4.1", "T4.10", "T4.11", "T4.2", "T4.3", "T4.4", "T4.5", "T4.6", "T4.7", "T4.8", "T4.9"]
assert ENTRY["CP-1C"]["table_ids"] == list(TABLES), "landed state: CP-1C owns exactly T1C.1-T1C.8"
OWNERS_LANDED = {}
OWNERS = {}
for _m in METH:
    for _t in _m.get("table_ids") or []:
        OWNERS_LANDED.setdefault(_t, []).append(_m["module_id"])
    for _t in (CP1C_REPLACED if _m["module_id"] == "CP-1C" else _m.get("table_ids") or []):
        OWNERS.setdefault(_t, []).append(_m["module_id"])
assert not [t for t in TABLES if len(OWNERS_LANDED[t]) > 1], "landed state: no T1C id is shared"
assert not [t for t in CP1C_REPLACED if "CP-1C" in OWNERS_LANDED.get(t, [])], "landed state: CP-1C no longer owns a T4.x id"
CP1C_CURRENT = CP1C_REPLACED
D8 = {
    "cp1c_table_ids_today": CP1C_CURRENT,
    "collisions_today": {t: OWNERS[t] for t in CP1C_CURRENT if len(OWNERS[t]) > 1},
    "unshared_today": [t for t in CP1C_CURRENT if len(OWNERS[t]) == 1],
    "proposed_ids": list(TABLES),
    "proposed_ids_collisions": [t for t in TABLES if t in OWNERS],
}
assert D8["collisions_today"] and not D8["proposed_ids_collisions"]
assert D8["unshared_today"] == ["T4.7"]
assert ENTRY["CP-1C"]["required"] == ["CP-0", "CP-1"] and ENTRY["CP-1C"]["optional"] == []

# --- 1. CP-1 issuer figures from the frozen pages (independent of CP-1's code) ----------------------


def row_values(page, label, count):
    for line in FPAGE[page].split("\n"):
        if line.startswith(label + "  "):
            tokens = line[len(label):].split()
            assert len(tokens) == count, (label, tokens)
            return [D(t[1:-1]) * -1 if t.startswith("(") else D(t) for t in tokens]
    raise AssertionError(label)


REV_Q = row_values("page:2", "Revenue", 5)
ADJ_Q = row_values("page:2", "Adjusted EBITDA", 5)
INT_Q = row_values("page:2", "Net interest expense", 5)
FFO_Q = row_values("page:3", "Operating cash flow before working capital", 5)
CASH_INT_Q = row_values("page:3", "Cash interest paid", 5)  # the peer sheet's own definition of interest expense
DEBT_BS = row_values("page:4", "Total debt", 6)
for _v in (REV_Q, ADJ_Q, INT_Q, FFO_Q, CASH_INT_Q):
    assert sum(_v[:4]) == _v[4]
assert sum(CASH_INT_Q[:4]) == sum(INT_Q[:4])  # CP-1 coverage uses net interest (page:2); equal to cash interest here
ISS = {"revenue": sum(REV_Q[:4]), "ebitda": sum(ADJ_Q[:4]), "debt": DEBT_BS[4], "interest": sum(INT_Q[:4]), "ffo": sum(FFO_Q[:4])}
o = FIN["q4_ltm_derived_source_units"]
assert ISS["revenue"] == D(o["revenue"]) and ISS["ebitda"] == D(o["adjusted_ebitda"]) and ISS["debt"] == D(o["total_debt"])
assert ISS["ffo"] == D(o["ffo"])
LTM_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
LTM_COLUMN = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
# period of every fact derived over the peers (T1C.8 counts, T1C.4, T1C.5): the issuer is on LTM Q4 25, each peer on its own
# twelve months (a peer period end can differ, e.g. p04); the peer's own period stays on its T1C.2 and T1C.3 cells
MIXED_PERIOD = "Mixed: issuer LTM Q4 25, each peer's own twelve months"

# --- 2. arithmetic and display -----------------------------------------------------------------------


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

MIN_PEERS = 3  # policy constant (lease open question 2)
OUTLIER = D("0.5")  # policy constant: strictly more than half the peer median (open question 3)

METRICS = [  # key, label, unit class, direction, numerator operand, denominator operand
    ("adjusted_ebitda_margin", "Adjusted EBITDA margin", "percent", "Higher is better", "ebitda", "revenue"),
    ("total_leverage_adjusted", "Total leverage (adjusted)", "multiple", "Lower is better", "debt", "ebitda"),
    ("interest_coverage_adjusted", "Interest coverage (adjusted)", "multiple", "Higher is better", "ebitda", "interest"),
    ("ffo_to_debt", "FFO to total debt", "percent", "Higher is better", "ffo", "debt"),
]
MKEY = [m[0] for m in METRICS]
CP1_FIGS = {  # CP-1 T4.10 facts, LTM Q4 25 column (probe of the real promoted head, 2026-10-28)
    "adjusted_ebitda_margin": (Fraction(1, 4), "calculated"),
    "total_leverage_adjusted": (Fraction(5, 3), "calculated"),
    "interest_coverage_adjusted": (Fraction(6), "calculated"),
    "ffo_to_debt": (Fraction(21, 50), "calculated"),
}
# the issuer's metrics recomputed from the frozen pages must equal CP-1's values exactly
ISS_METRIC = {}
for _k, _lab, _uc, _dir, _n, _d in METRICS:
    ISS_METRIC[_k] = div(ISS[_n], ISS[_d])
    assert ISS_METRIC[_k] == q38(CP1_FIGS[_k][0]), _k

# --- 3. the SYNTHETIC peer summary source ------------------------------------------------------------

SHEET_P1_HEAD = [
    "SYNTHETIC PEER DATA DESK",
    "Peer financial summary for credit benchmarking",
    "Published January 10, 2026.",
    "This invented case is test data, not evidence about real issuers. The peers named below do not exist.",
    "Basis: twelve months to the period end shown; USD; amounts in millions; unaudited desk summaries.",
    "Adjusted EBITDA is reported EBITDA with no add-backs, as in the Northbridge Synthetic Group statements. Total debt is gross financial debt at the period end. Interest expense is cash interest paid. FFO is operating cash flow before working capital.",
    "Peer  Period end  Revenue  Adjusted EBITDA  Total debt  Interest expense  FFO",
]
P1_HEADER = SHEET_P1_HEAD[-1]
ISSUER_ROW = [ISSUER, "2025-12-31", "120.0", "30.0", "50.0", "5.0", "21.0"]
PEER_ROWS = {
    "positive": [
        ["Alder Ridge Holdings", "2025-12-31", "200.0", "52.0", "104.0", "8.0", "41.6"],
        ["Brookmere Industries", "2025-12-31", "150.0", "33.0", "99.0", "11.0", "30.0"],
        ["Calder Vale Group", "2025-12-31", "90.0", "27.0", "40.5", "4.5", "18.9"],
        ["Dunmore Cross Corporation", "2025-09-30", "300.0", "48.0", "240.0", "24.0", "30.0"],
        ["Ellsworth Park Limited", "2025-12-31", "500.0", "150.0", "75.0", "7.5", "60.0"],
    ],
    "gap": [
        ["Alder Ridge Holdings", "2025-12-31", "200.0", "52.0", "104.0", "8.0", "41.6"],
        ["Brookmere Industries", "2025-12-31", "150.0", "33.0", "99.0", "11.0", "30.0"],
        ["Calder Vale Group", "2025-12-31", "90.0", "27.0", "40.5", "Not stated", "18.9"],
    ],
}
BASIS_ROWS = {
    "positive": [
        [ISSUER, "IFRS", "1", "December 31"],
        ["Alder Ridge Holdings", "IFRS", "1", "December 31"],
        ["Brookmere Industries", "IFRS", "1", "December 31"],
        ["Calder Vale Group", "IFRS", "1", "December 31"],
        ["Dunmore Cross Corporation", "IFRS", "1", "June 30"],
        ["Ellsworth Park Limited", "US GAAP", "6", "December 31"],
    ],
    "gap": [
        [ISSUER, "IFRS", "1", "December 31"],
        ["Alder Ridge Holdings", "IFRS", "1", "December 31"],
        ["Brookmere Industries", "IFRS", "1", "December 31"],
        ["Calder Vale Group", "IFRS", "1", "December 31"],
    ],
}
P2_HEAD = [
    "SYNTHETIC PEER DATA DESK",
    "Peer reporting basis and period alignment",
    "Published January 10, 2026.",
    "This invented case is test data, not evidence about real issuers. The peers named below do not exist.",
    "Each line is as stated by the peer in its own unaudited summary. The desk has restated no peer to the Northbridge Synthetic Group basis.",
]
P2_HEADER = "Peer  Reporting basis  Operating segments  Fiscal year end"
P2_NOTES = [
    "Dunmore Cross Corporation reports twelve months to September 30, 2025, which ends on a different date from the Northbridge Synthetic Group year end.",
    "Ellsworth Park Limited is a diversified group with six operating segments reporting under US GAAP; the desk offers it as a size reference only.",
]


def sheet_pages(case):
    p1 = "\n".join(SHEET_P1_HEAD + ["  ".join(r) for r in [ISSUER_ROW] + PEER_ROWS[case]])
    p2 = "\n".join(P2_HEAD + [P2_HEADER] + ["  ".join(r) for r in BASIS_ROWS[case]] + (P2_NOTES if case == "positive" else []))
    return [p1, p2]


SHEET = {"positive": sheet_pages("positive"), "gap": sheet_pages("gap")}
# fixture for the "Peer table not found" refusal: positive page:1 without the table header line
SHEET["unparseable"] = [SHEET["positive"][0].replace(P1_HEADER + "\n", ""), SHEET["positive"][1]]
assert P1_HEADER not in SHEET["unparseable"][0]
SHEET_NAME = "Peer financial summary (synthetic)"
SHEET_LIMIT = "Synthetic desk summary of invented peers; unaudited; not a market fact."
SHEET_SHA = {k: page_sha(v) for k, v in SHEET.items()}

# consistency of the synthetic source with every frozen figure it touches (asserted)
assert ISSUER_ROW[2:] == ["120.0", "30.0", "50.0", "5.0", "21.0"]
assert D(ISSUER_ROW[2]) == ISS["revenue"] and D(ISSUER_ROW[3]) == ISS["ebitda"] and D(ISSUER_ROW[4]) == ISS["debt"]
assert D(ISSUER_ROW[5]) == ISS["interest"] and D(ISSUER_ROW[6]) == ISS["ffo"]
assert D(ISSUER_ROW[5]) == sum(CASH_INT_Q[:4])
assert "Reporting basis: IFRS; entity perimeter: consolidated group." in FPAGE["page:1"]
assert "One operating segment, Consolidated Operations" in FPAGE["page:1"]
assert "Fiscal year end: December 31." in SRC["identity"]["pages"][0]["text"]
assert "Reported EBITDA  7.5  7.5  7.5  7.5  30.0" in FPAGE["page:2"] and "Adjusted EBITDA  7.5  7.5  7.5  7.5  30.0" in FPAGE["page:2"]
assert "Total debt  45  46.25  47.50  48.75  50.00  50.00" in FPAGE["page:4"]
assert "Cash interest paid  1.25  1.25  1.25  1.25  5.00" in FPAGE["page:3"]
assert "Net interest expense  1.25  1.25  1.25  1.25  5.00" in FPAGE["page:2"]
assert "Operating cash flow before working capital  5.25  5.25  5.25  5.25  21.00" in FPAGE["page:3"]
# no frozen page names a peer, a comparable or a peer-set statement (the case_kind is synthetic)
for _p in list(FPAGE.values()) + [SRC["identity"]["pages"][0]["text"]]:
    assert "peer" not in _p.lower(), "frozen text mentions a peer"


def parse_sheet(pages):
    """The builder's reading of the peer tables (the lease's rule for the core)."""
    p1 = pages[0].split("\n")
    start = p1.index(P1_HEADER)
    rows = []
    for line in p1[start + 1:]:
        parts = re.split(r"  +", line)
        assert len(parts) == 7, line
        def amt(t):
            return None if t == "Not stated" else D(t)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[1])
        rows.append({"label": parts[0], "period_end": parts[1], "revenue": amt(parts[2]), "ebitda": amt(parts[3]), "debt": amt(parts[4]),
                     "interest": amt(parts[5]), "ffo": amt(parts[6]), "line": line, "page1": line})
    p2 = pages[1].split("\n")
    basis = {}
    if P2_HEADER in p2:
        for line in p2[p2.index(P2_HEADER) + 1:]:
            parts = re.split(r"  +", line)
            if len(parts) != 4:
                break
            basis[parts[0]] = {"basis": parts[1], "segments": parts[2], "fye": parts[3], "line": line}
    issuer = next(r for r in rows if r["label"] == ISSUER)
    peers = [r for r in rows if r["label"] != ISSUER]
    for r in rows:
        r["page2"] = basis.get(r["label"])
    return issuer, peers, basis


# --- 4. citations -------------------------------------------------------------------------------------


def cite(source_id, page, quote, case="positive"):
    if source_id == "peers":
        text = SHEET[case][page - 1]
        sha = SHEET_SHA[case]
    else:
        text = SRC[source_id]["pages"][page - 1]["text"]
        sha = SRC[source_id]["sha256"]
    assert quote in text, quote
    return {"source_id": source_id, "source_sha256": sha, "locator": f"page:{page}", "quote": quote}


# --- 5. analyst submissions ---------------------------------------------------------------------------

CAT = "Analyst Interpretation"


def assessment(peer, comp, rationale, ev, limitation=None):
    return {"peer": peer, "comparability": comp, "category": CAT, "rationale": rationale, "evidence": ev, "limitation": limitation}


def line2(case, label):
    return "  ".join(next(r for r in BASIS_ROWS[case] if r[0] == label))


ALIGNED = "Same reporting basis, one operating segment and the same year end as the issuer, so its ratios sit on aligned definitions."
POS_ASSESS = [
    assessment("Alder Ridge Holdings", "Comparable", ALIGNED, [cite("peers", 2, line2("positive", "Alder Ridge Holdings"))]),
    assessment("Brookmere Industries", "Comparable", ALIGNED, [cite("peers", 2, line2("positive", "Brookmere Industries"))]),
    assessment("Calder Vale Group", "Comparable", ALIGNED, [cite("peers", 2, line2("positive", "Calder Vale Group"))]),
    assessment("Dunmore Cross Corporation", "Partly comparable",
               "The twelve months end on a different date from the issuer year end, so the peer covers a shifted window; it stays in the universe with that limitation.",
               [cite("peers", 2, P2_NOTES[0])], "Period end differs from the issuer's."),
    assessment("Ellsworth Park Limited", "Not comparable",
               "A different reporting basis and a diversified group of several operating segments, so its ratios are shown but kept out of every statistic.",
               [cite("peers", 2, line2("positive", "Ellsworth Park Limited"))]),
]
POS_OVERALL = {
    "rationale": ("The issuer's total leverage of {T1C.3.issuer.total_leverage_adjusted|x} is below the peer median of {T1C.4.total_leverage_adjusted.median|x}, "
                  "its interest coverage of {T1C.3.issuer.interest_coverage_adjusted|x} is above the median of {T1C.4.interest_coverage_adjusted.median|x}, "
                  "and its adjusted EBITDA margin of {T1C.3.issuer.adjusted_ebitda_margin|%} is close to the median of {T1C.4.adjusted_ebitda_margin.median|%}. "
                  "The outlier register shows which peers distort a metric, so the median is the reference."),
    "category": CAT, "confidence": "Medium", "limitation": "The universe is a small desk-supplied set of unaudited summaries.", "evidence": [],
}
POS_GAPS = [{"gap": "The peer summary is unaudited and covers a handful of peers.",
             "why_it_matters": "Medians and outlier flags move with one peer.",
             "affected_analysis": "Peer statistics", "severity": "Material",
             "action": "Obtain filed statements for each peer and widen the universe."}]
GAP_ASSESS = [
    assessment("Alder Ridge Holdings", "Comparable", ALIGNED, [cite("peers", 2, line2("gap", "Alder Ridge Holdings"), "gap")]),
    assessment("Brookmere Industries", "Comparable", ALIGNED, [cite("peers", 2, line2("gap", "Brookmere Industries"), "gap")]),
    assessment("Calder Vale Group", "Comparable",
               "Aligned reporting basis, segments and year end; its interest expense is not stated in the peer summary, so its coverage cannot be calculated.",
               [cite("peers", 2, line2("gap", "Calder Vale Group"), "gap")]),
]
GAP_OVERALL = {
    "rationale": ("The issuer's total leverage of {T1C.3.issuer.total_leverage_adjusted|x} is below the peer median of {T1C.4.total_leverage_adjusted.median|x}. "
                  "The peer median coverage is not available [T1C.4.interest_coverage_adjusted.median], so interest coverage is shown for the issuer without a comparison."),
    "category": CAT, "confidence": "Low", "limitation": "Only three peers are in the universe and one amount is not stated.", "evidence": [],
}
GAP_GAPS = [{"gap": "The peer summary omits one peer's interest expense.",
             "why_it_matters": "Interest coverage has too few peers for a median.",
             "affected_analysis": "Interest coverage comparison", "severity": "Material",
             "action": "Request the missing interest expense from the data desk."}]
NO_OVERALL = {
    "rationale": ("No peer source is in the pack, so no peer universe, median or outlier flag can be formed. "
                  "The issuer's own total leverage of {T1C.3.issuer.total_leverage_adjusted|x} is shown without a comparison."),
    "category": CAT, "confidence": "Low", "limitation": "No peer data is available.", "evidence": [],
}
NO_GAPS = [{"gap": "No peer financial source is in the pack.",
            "why_it_matters": "The issuer cannot be positioned against comparable companies.",
            "affected_analysis": "Peer benchmark", "severity": "Critical",
            "action": "Supply a peer financial summary with filed statements."}]
SUBMISSION = {
    "positive": {"assessments": POS_ASSESS, "overall": POS_OVERALL, "gaps": POS_GAPS},
    "gap": {"assessments": GAP_ASSESS, "overall": GAP_OVERALL, "gaps": GAP_GAPS},
    "no_peers": {"assessments": [], "overall": NO_OVERALL, "gaps": NO_GAPS},
}


def mutate(base, fn):
    p = copy.deepcopy(base)
    fn(p)
    return p


REFUSAL_DEFS = [
    ("r01", "unknown peer", "positive", lambda p: p["assessments"][1].__setitem__("peer", "Fenwick Dale Partners"),
     ["Unknown peer: Fenwick Dale Partners", "Assess each sheet peer exactly once: Brookmere Industries"]),
    ("r02", "peer not assessed", "positive", lambda p: p["assessments"].pop(4),
     ["Assess each sheet peer exactly once: Ellsworth Park Limited"]),
    ("r03", "peer assessed twice", "positive", lambda p: p["assessments"].append(copy.deepcopy(p["assessments"][0])),
     ["Assess each sheet peer exactly once: Alder Ridge Holdings"]),
    ("r04", "evidence required for a comparability assessment", "positive", lambda p: p["assessments"][0].__setitem__("evidence", []),
     ["Evidence required for a comparability assessment: Alder Ridge Holdings"]),
    ("r05", "limitation required for Partly comparable", "positive", lambda p: p["assessments"][3].__setitem__("limitation", None),
     ["Limitation required for Partly comparable: Dunmore Cross Corporation"]),
    ("r06", "bare figure in rationale", "positive",
     lambda p: p["assessments"][4].__setitem__("rationale", "A different reporting basis and a diversified group of 6 operating segments, so its ratios are shown but kept out of every statistic."),
     ["Bare figure: 6"]),
    ("r07", "quote not in the located page", "positive",
     lambda p: p["assessments"][0]["evidence"][0].__setitem__("quote", "Alder Ridge Holdings  IFRS  2  December 31"),
     ["Quote/locator mismatch: quote not found under peers page:2 ("]),
    ("r08", "confidence High", "positive", lambda p: p["overall"].__setitem__("confidence", "High"),
     ["Confidence cannot be High: the peer figures are desk-supplied and unaudited"]),
    ("r09", "prohibited conclusion", "positive",
     lambda p: p["overall"].__setitem__("rationale", p["overall"]["rationale"] + " Overweight the sector."),
     ['overall.rationale: prohibited conclusion (instrument recommendation): "overweight"']),
    ("r10", "assessment with no peer source in the pack", "no_peers", lambda p: p["assessments"].append(
        assessment("Alder Ridge Holdings", "Comparable", ALIGNED, [cite("financial", 1, "Currency: USD; amounts in millions.")])),
     ["Assessment given without a peer source in the pack: Alder Ridge Holdings"]),
    ("r11", "peer table not found", "positive", lambda p: [c.__setitem__("source_sha256", SHEET_SHA["unparseable"]) for x in p["assessments"] for c in x["evidence"]],
     ["Peer table not found"]),
    ("r12", "unresolved reference", "positive",
     lambda p: p["overall"].__setitem__("rationale", p["overall"]["rationale"] + " Compare {T1C.9.nothing.median|x}."),
     ["Unresolved reference: T1C.9.nothing.median"]),
    ("r13", "figure reference names a gap", "gap",
     lambda p: p["overall"].__setitem__("rationale", p["overall"]["rationale"].replace("[T1C.4.interest_coverage_adjusted.median]", "{T1C.4.interest_coverage_adjusted.median|x}")),
     ["Figure reference names a gap: T1C.4.interest_coverage_adjusted.median"]),
    ("r14", "run-time figure marker left unreplaced", "positive",
     lambda p: p["overall"].__setitem__("rationale", p["overall"]["rationale"] + " Compare {{FIG:total_leverage_adjusted|x}}."),
     ["Malformed run text: unbalanced or empty reference"]),
]
PACK_OF = {"r11": "unparseable"}
REFUSALS = []
for rid, klass, base, fn, issues in REFUSAL_DEFS:
    REFUSALS.append({"id": rid, "class": klass, "base_case": base, "pack": PACK_OF.get(rid, base), "payload": mutate(SUBMISSION[base], fn),
                     "expected_issues": issues,
                     "issue_match": "each expected issue appears (prefix match where the text ends in an open parenthesis); no other issue"})
REFUSALS[0]["note"] = "Renaming a row leaves the real row unassessed, so both issues appear"
REFUSALS[10]["note"] = "manifest synthetic_source.fixtures.peer_table_not_found: a peer source whose page:1 has no table header line; every citation carries that fixture's sha256 (page:2 is unchanged, so every quote still locates) so the table check, not a citation check, is what refuses; the issue returns alone"
REFUSALS[13]["note"] = "the rationale carries a CP-1 run-time marker the harness never bound; only a harness that skips the binding step produces it (fails closed)"
READ_PEERS = {"tool": "read_pages", "arguments": {"source_id": "peers", "first_page": 1, "last_page": 2},
              "expect_spans": [{"source_id": "peers", "locator": "page:1"}, {"source_id": "peers", "locator": "page:2"}]}
NO_PEER_SPANS = [{"source_id": s, "locator": loc} for s in ("identity", "financial")
                 for loc, t in ([("page:1", SRC["identity"]["pages"][0]["text"])] if s == "identity" else [(p["locator"], p["text"]) for p in SRC["financial"]["pages"]])
                 if "peer" in t.lower()]
assert NO_PEER_SPANS == []
TOOL_CALLS = {
    "positive": [{"tool": "read_inputs", "arguments": None}, READ_PEERS],
    "gap": [{"tool": "read_inputs", "arguments": None}, READ_PEERS],
    "no_peers": [
        {"tool": "read_inputs", "arguments": None},
        {"tool": "search_pack", "arguments": {"query": "peer", "source_id": None},
         "expect_header": "0 spans match 'peer'; showing 0.", "expect_matching_spans": []},
    ],
}
READ_FINANCIAL_P1 = {"tool": "read_pages", "arguments": {"source_id": "financial", "first_page": 1, "last_page": 1},
                     "expect_spans": [{"source_id": "financial", "locator": "page:1"}]}
# every refusal states the literal tool sequence before its submit: the base case's tool_calls, except r10, which cites
# financial page:1 and so must have read it (unread_citation_issues would otherwise add its own issue)
for _r in REFUSALS:
    _r["calls_before_submit"] = TOOL_CALLS[_r["base_case"]] + ([READ_FINANCIAL_P1] if _r["id"] == "r10" else [])
TOOL_REFUSALS = [
    {"id": "t01", "class": "cited_page_not_read", "base_case": "positive", "payload": "submissions.json positive peer_benchmark (valid)",
     "calls_before_submit": [{"tool": "read_inputs", "arguments": None}],
     "disposition": "invalid attempt 0 (journaled rule unread_citation_issues against Seen); re-begun as attempt 1 with repair_of set; a valid attempt 1 with tool_calls.positive yields a verifying receipt",
     "expected_issues": ["Cited page not read through read_pages: peers page:2"]},
    {"id": "t02", "class": "non-pack invoke", "base_case": "positive",
     "call": {"tool": "web_search", "arguments": {"query": "Alder Ridge Holdings leverage"}},
     "expected_receipt": {"status": "refused", "reason": "not_permitted"}, "journal": "none; no attempt consumed"},
    {"id": "t03", "class": "submit before read_inputs", "base_case": "positive", "calls_before_submit": [],
     "expected_receipt": {"status": "refused", "reason": "not_permitted"}, "journal": "none; no attempt consumed"},
]

# --- 6. composition -----------------------------------------------------------------------------------

BLOCKS = {
    "peer-positioning": {"title": "Peer positioning", "owner": "CP-1C", "kind": "dense", "producers": ["CP-1C"],
                         "tabs": [["T1C.1", "Peer universe"], ["T1C.8", "Peer universe totals"], ["T1C.3", "Normalised metrics"], ["T1C.4", "Peer statistics"], ["T1C.5", "Outlier register"]]},
}
EVIDENCE_TABLES = ["T1C.2", "T1C.6"]
LIMITATION_TABLES = ["T1C.7"]
SYNTHETIC = "Synthetic case; not real issuer qualification"
MISSING_PEER = "No peer source is in the pack"


def dsub(a, b):
    """One subtraction in the 38-digit half-even context (the default context has 28 digits)."""
    with localcontext(CTX):
        return a - b


def median(values):
    s = sorted(values)
    n = len(s)
    if n % 2:
        return s[n // 2]
    with localcontext(CTX):
        return (s[n // 2 - 1] + s[n // 2]) / 2


def better(a, b, direction):
    return a > b if direction == "Higher is better" else a < b


def build_case(name):
    sub = SUBMISSION[name]
    sheet = parse_sheet(SHEET[name]) if name != "no_peers" else None
    issuer_row, peers, _basis = sheet if sheet else (None, [], {})
    facts, rows, claims, limits = [], {t: [] for t in TABLES}, [], []

    def fact(table, row, field, label, **kw):
        r = {"fact_id": f"{table}.{row}.{field}", "table_id": table, "row_id": row, "field": field, "label": label}
        r.update(kw)
        facts.append(r)
        return r["fact_id"]

    def num(table, row, field, label, v, uc, formula, derives=(), value_class="calculated", citations=None, decimals=None, unit=None, period=LTM_PERIOD):
        if unit is None:
            unit = UNIT[uc]
            sh = show(v, uc, decimals if uc == "amount" else None)
        else:
            sh = f"{norm(v)} {unit}"
        extra = {"currency": "USD", "scale": "1000000", "decimals": decimals} if uc == "amount" and unit == "MILLIONS" else {}
        return fact(table, row, field, label, status="known", unit=unit, period=period, amount_exact=norm(v), shown=sh, **extra,
                    value_class=value_class, formula=formula, calculation_id=f"calc:{table}.{row}.{field}" if value_class == "calculated" else None,
                    derives_from=list(derives), **({"citations": citations} if citations else {}))

    def gapf(table, row, field, label, uc, reason, status="missing", unit="auto", period=LTM_PERIOD):
        return fact(table, row, field, label, status=status, unit=UNIT.get(uc) if unit == "auto" else unit, period=period, amount_exact=None, shown=None, limitation=reason)

    def text(table, row, field, label, v, value_class=None, citations=None, formula=None, derives=(), period=None):
        kw = {}
        if value_class == "calculated":
            kw.update(calculation_id=f"calc:{table}.{row}.{field}", formula=formula, derives_from=list(derives))
        return fact(table, row, field, label, status="known", text=v, shown=v, value_class=value_class, **({"period": period} if period else {}), **kw, **({"citations": citations} if citations else {}))

    def reg(table, row_id, label, fields):
        rows[table].append({"row_id": row_id, "label": label, "fact_ids": [f"{table}.{row_id}.{f}" for f in fields]})

    # ---- analysis state per peer
    amap = {a["peer"]: a for a in sub["assessments"]}
    if sheet:
        assert set(amap) == {p["label"] for p in peers} and len(amap) == len(sub["assessments"])
    pr = []
    for n, p in enumerate(peers, 1):
        a = amap[p["label"]]
        pr.append(dict(p, row=f"p{n:02d}", a=a, included=a["comparability"] != "Not comparable"))
    ids_cite = lambda p: [{"source_id": "peers", "locator": "page:1", "quote": p["page1"]}]  # noqa: E731
    pend = lambda r: f"Twelve months to {r['period_end']}"  # noqa: E731
    FIELDS = (("revenue", "Revenue"), ("ebitda", "Adjusted EBITDA"), ("debt", "Total debt"), ("interest", "Interest expense"), ("ffo", "FFO"))

    # ---- T1C.1 peer universe
    n_sheet = len(pr)
    for p in pr:
        r, a = p["row"], p["a"]
        b = p["page2"]
        c2 = [{"source_id": "peers", "locator": "page:2", "quote": b["line"]}] if b else None
        text("T1C.1", r, "period_end", "Period end", p["period_end"], "source", ids_cite(p))
        for f_, l_, k_ in (("reporting_basis", "Reporting basis", "basis"), ("segments", "Operating segments", "segments"), ("fiscal_year_end", "Fiscal year end", "fye")):
            text("T1C.1", r, f_, l_, b[k_], "source", c2)
        text("T1C.1", r, "comparability", "Comparability", a["comparability"], "analyst_judgment")
        text("T1C.1", r, "included", "Universe", "Included" if p["included"] else "Excluded", "calculated",
             formula="Included unless Not comparable", derives=(f"T1C.1.{r}.comparability",))
        text("T1C.1", r, "evidence", "Evidence", "; ".join(f"{c['source_id']} {c['locator']}" for c in a["evidence"]))
        reg("T1C.1", r, p["label"], ["period_end", "reporting_basis", "segments", "fiscal_year_end", "comparability", "included", "evidence"])
    n_inc = sum(1 for p in pr if p["included"])
    if sheet:
        for f_, l_, v_ in (("sheet", "Peers in the source", n_sheet), ("included", "Peers included", n_inc), ("excluded", "Peers excluded", n_sheet - n_inc)):
            num("T1C.8", "total", f_, l_, D(v_), "amount", "count of peer rows" if f_ == "sheet" else "count by universe flag",
                () if f_ == "sheet" else tuple(f"T1C.1.{p['row']}.included" for p in pr), unit="peers", period=MIXED_PERIOD)
        reg("T1C.8", "total", "Total", ["sheet", "included", "excluded"])
    else:
        for f_, l_ in (("period_end", "Period end"), ("reporting_basis", "Reporting basis"), ("segments", "Operating segments"),
                       ("fiscal_year_end", "Fiscal year end"), ("comparability", "Comparability"), ("included", "Universe"), ("evidence", "Evidence")):
            gapf("T1C.1", "none", f_, l_, "amount", MISSING_PEER, unit=None, period=None)
        reg("T1C.1", "none", "No peer source", ["period_end", "reporting_basis", "segments", "fiscal_year_end", "comparability", "included", "evidence"])
        for f_, l_ in (("sheet", "Peers in the source"), ("included", "Peers included"), ("excluded", "Peers excluded")):
            gapf("T1C.8", "total", f_, l_, "amount", MISSING_PEER, unit="peers", period=None)
        reg("T1C.8", "total", "Total", ["sheet", "included", "excluded"])

    # ---- T1C.2 peer source figures (issuer line, then peers)
    ent = [dict(issuer_row, row="issuer", included=None)] if sheet else []
    ent += pr
    for e in ent:
        r = e["row"]
        for f_, l_ in FIELDS:
            v = e[f_]
            if v is None:
                gapf("T1C.2", r, f_, l_, "amount", "Not stated in the peer source", period=pend(e))
            else:
                num("T1C.2", r, f_, l_, v, "amount", "Peer source amount", (), "source", ids_cite(e), 1, period=pend(e))
        reg("T1C.2", r, e["label"], [f for f, _ in FIELDS])
    if not sheet:
        for f_, l_ in FIELDS:
            gapf("T1C.2", "none", f_, l_, "amount", MISSING_PEER, period=None)
        reg("T1C.2", "none", "No peer source", [f for f, _ in FIELDS])

    # ---- T1C.3 normalised metrics
    val = {}  # (row, metric) -> Decimal | None | "na"
    for k, lab, uc, direction, nm, dn in METRICS:
        v, cls = CP1_FIGS[k]
        fid = fact("T1C.3", "issuer", k, lab, status="known", unit=UNIT[uc], period=LTM_PERIOD, amount_exact=norm(q38(v)), shown=show(q38(v), uc),
                   value_class=cls, copied_from_cp1=f"{LTM_COLUMN} · {k}", calculation_id="{{CP1_CALCULATION_ID}}", derives_from=[],
                   lineage="the CP-1 fact verbatim: its own calculation_id and citations are bound at run time")
        val[("issuer", k)] = q38(v)
    reg("T1C.3", "issuer", f"{ISSUER} (CP-1)", MKEY)
    for p in pr:
        r = p["row"]
        for k, lab, uc, direction, nm, dn in METRICS:
            nmv, dnv = p[nm], p[dn]
            der = (f"T1C.2.{r}.{nm}", f"T1C.2.{r}.{dn}")
            if nmv is None or dnv is None:
                miss = nm if nmv is None else dn
                gapf("T1C.3", r, k, lab, uc, f"Not calculable: {dict(FIELDS)[miss].lower()} is not stated in the peer source", period=pend(p))
                val[(r, k)] = None
            elif dnv <= 0:
                gapf("T1C.3", r, k, lab, uc, f"Not meaningful: {dict(FIELDS)[dn].lower()} is not positive", "not_applicable", period=pend(p))
                val[(r, k)] = "na"
            else:
                v = div(nmv, dnv)
                num("T1C.3", r, k, lab, v, uc, f"{dict(FIELDS)[nm]} / {dict(FIELDS)[dn]}", der, period=pend(p))
                val[(r, k)] = v
        reg("T1C.3", r, p["label"], MKEY)
    if not sheet:
        for k, lab, uc, *_ in METRICS:
            gapf("T1C.3", "none", k, lab, uc, MISSING_PEER, period=None)
        reg("T1C.3", "none", "No peer source", MKEY)

    # ---- T1C.4 statistics, T1C.5 outliers
    stats = {}
    inc = [p for p in pr if p["included"]]
    for k, lab, uc, direction, nm, dn in METRICS:
        text("T1C.4", k, "direction", "Direction", direction)
        # a missing or not-applicable fact carries the unit its settled twin carries: pp for a percent-minus-percent difference,
        # the metric's own unit for the median, the count units otherwise
        gap_unit = {"n": "peers", "median": UNIT[uc], "difference": "pp" if uc == "percent" else UNIT[uc], "position": "rank", "of": "entities", "outlier_count": "peers"}
        if not sheet:
            for f_, l_ in (("n", "Included peers with a value"), ("median", "Peer median"), ("difference", "Issuer minus median"),
                           ("position", "Issuer position"), ("of", "Entities compared"), ("outlier_count", "Peers flagged as outliers")):
                gapf("T1C.4", k, f_, l_, uc, MISSING_PEER, unit=gap_unit[f_], period=None)
            reg("T1C.4", k, lab, ["direction", "n", "median", "difference", "position", "of", "outlier_count"])
            stats[k] = None
            continue
        known = [(p["row"], val[(p["row"], k)]) for p in inc if isinstance(val[(p["row"], k)], Decimal)]
        nk = len(known)
        num("T1C.4", k, "n", "Included peers with a value", D(nk), "amount", "count of included peers with a calculated value",
            tuple(f"T1C.3.{r}.{k}" for r, _ in known), unit="peers", period=MIXED_PERIOD)
        if nk < MIN_PEERS:
            why = f"Not calculable: {nk} included peers have a stated value, at least {MIN_PEERS} are required"
            for f_, l_ in (("median", "Peer median"), ("difference", "Issuer minus median"), ("position", "Issuer position"),
                           ("of", "Entities compared"), ("outlier_count", "Peers flagged as outliers")):
                gapf("T1C.4", k, f_, l_, uc, why, unit=gap_unit[f_], period=MIXED_PERIOD)
            stats[k] = {"n": nk, "median": None}
        else:
            med = median([v for _, v in known])
            iv = val[("issuer", k)]
            vals = [v for _, v in known]
            pos = 1 + sum(1 for v in vals if better(v, iv, direction))
            ofn = len(vals) + 1
            ders = tuple(f"T1C.3.{r}.{k}" for r, _ in known)
            num("T1C.4", k, "median", "Peer median", med, uc, "median of included peers' values; even count: (a + b) / 2", ders, period=MIXED_PERIOD)
            if uc == "percent":
                # the room between two percentages is percentage points, not a percent (cp4_legal.py:970-972): the 38-digit
                # difference scaled by .scaleb(2) in that context (not CP-4's amount * 100), unit pp
                num("T1C.4", k, "difference", "Issuer minus median", dsub(iv, med).scaleb(2, context=CTX), uc, "(issuer value minus peer median) x 100, percentage points",
                    (f"T1C.3.issuer.{k}", f"T1C.4.{k}.median"), unit="pp", period=MIXED_PERIOD)
            else:
                num("T1C.4", k, "difference", "Issuer minus median", dsub(iv, med), uc, "issuer value minus peer median", (f"T1C.3.issuer.{k}", f"T1C.4.{k}.median"), period=MIXED_PERIOD)
            num("T1C.4", k, "position", "Issuer position", D(pos), "amount", "1 + number of entities strictly better than the issuer; ties share a position",
                (f"T1C.3.issuer.{k}",) + ders, unit="rank", period=MIXED_PERIOD)
            num("T1C.4", k, "of", "Entities compared", D(ofn), "amount", "included peers with a value + the issuer", ders + (f"T1C.3.issuer.{k}",), unit="entities", period=MIXED_PERIOD)
            stats[k] = {"n": nk, "median": med, "issuer": iv, "difference": dsub(iv, med).scaleb(2, context=CTX) if uc == "percent" else dsub(iv, med), "position": pos, "of": ofn, "sorted": [norm(v) for v in sorted(vals)]}
        reg("T1C.4", k, lab, ["direction", "n", "median", "difference", "position", "of", "outlier_count"])
    # outlier register
    if sheet:
        flag_rows = [("issuer", ISSUER, None)] + [(p["row"], p["label"], p) for p in pr]
        for r, label, p in flag_rows:
            cnt_der = []
            for k, lab, uc, *_ in METRICS:
                st = stats[k]
                v = val[(r, k)]
                if p is not None and not p["included"]:
                    gapf("T1C.5", r, f"{k}_deviation", f"{lab} · Deviation from median", "percent", "Not meaningful: the peer is excluded from the universe", "not_applicable", period=MIXED_PERIOD)
                    gapf("T1C.5", r, f"{k}_flag", f"{lab} · Flag", "percent", "Not meaningful: the peer is excluded from the universe", "not_applicable", unit=None, period=MIXED_PERIOD)
                    continue
                if st["median"] is None:
                    why = "Not calculable: no peer median (fewer than three included peers have a value)"
                    gapf("T1C.5", r, f"{k}_deviation", f"{lab} · Deviation from median", "percent", why, period=MIXED_PERIOD)
                    gapf("T1C.5", r, f"{k}_flag", f"{lab} · Flag", "percent", why, unit=None, period=MIXED_PERIOD)
                elif v is None:
                    why = "Not calculable: the peer's value is not stated"
                    gapf("T1C.5", r, f"{k}_deviation", f"{lab} · Deviation from median", "percent", why, period=MIXED_PERIOD)
                    gapf("T1C.5", r, f"{k}_flag", f"{lab} · Flag", "percent", why, unit=None, period=MIXED_PERIOD)
                elif st["median"] == 0:
                    why = "Not meaningful: the peer median is zero"
                    gapf("T1C.5", r, f"{k}_deviation", f"{lab} · Deviation from median", "percent", why, "not_applicable", period=MIXED_PERIOD)
                    gapf("T1C.5", r, f"{k}_flag", f"{lab} · Flag", "percent", why, "not_applicable", unit=None, period=MIXED_PERIOD)
                else:
                    with localcontext(CTX):
                        dev = (v - st["median"]) / st["median"]
                    flag = abs(dev) > OUTLIER
                    der = (f"T1C.3.{r}.{k}", f"T1C.4.{k}.median")
                    num("T1C.5", r, f"{k}_deviation", f"{lab} · Deviation from median", dev, "percent", "(value - peer median) / peer median", der, period=MIXED_PERIOD)
                    text("T1C.5", r, f"{k}_flag", f"{lab} · Flag", "Outlier" if flag else "Within range", "calculated",
                         formula="Outlier iff |deviation| is strictly above one half", derives=(f"T1C.5.{r}.{k}_deviation",), period=MIXED_PERIOD)
                    st.setdefault("flags", {})[r] = flag
                    st.setdefault("dev", {})[r] = dev
            reg("T1C.5", r, label if p else f"{ISSUER}", [f"{k}_{x}" for k in MKEY for x in ("deviation", "flag")])
    else:
        for f_ in [f"{k}_{x}" for k in MKEY for x in ("deviation", "flag")]:
            gapf("T1C.5", "none", f_, f_, "percent", MISSING_PEER, unit=None if f_.endswith("_flag") else "auto", period=None)
        reg("T1C.5", "none", "No peer source", [f"{k}_{x}" for k in MKEY for x in ("deviation", "flag")])
    # outlier_count facts of T1C.4 (peers flagged), needs the register
    if sheet:
        for k, lab, uc, *_ in METRICS:
            st = stats[k]
            if st["median"] is None:
                continue
            tested = [p["row"] for p in inc if p["row"] in st.get("flags", {})]
            flagged = [r for r in tested if st["flags"][r]]
            st["outliers"] = flagged
            num("T1C.4", k, "outlier_count", "Peers flagged as outliers", D(len(flagged)), "amount", "count of included peers flagged",
                tuple(f"T1C.5.{r}.{k}_flag" for r in tested), unit="peers", period=MIXED_PERIOD)

    # ---- T1C.6 definition alignment: the sheet's issuer line against CP-1
    for k, lab, uc, direction, nm, dn in METRICS:
        if not sheet:
            # CP-1 is in the pack: its cell is the same known copy as T1C.3.issuer.<metric>; only the peer-source side is missing
            gapf("T1C.6", k, "sheet", "Issuer line on the peer source", uc, MISSING_PEER, period=None)
            cv = q38(CP1_FIGS[k][0])
            fact("T1C.6", k, "cp1", "CP-1", status="known", unit=UNIT[uc], period=LTM_PERIOD, amount_exact=norm(cv), shown=show(cv, uc), value_class=CP1_FIGS[k][1],
                 copied_from_cp1=f"{LTM_COLUMN} · {k}", calculation_id="{{CP1_CALCULATION_ID}}", derives_from=[],
                 lineage="the CP-1 fact verbatim: its own calculation_id and citations are bound at run time")
            gapf("T1C.6", k, "difference", "Difference", uc, MISSING_PEER, unit="pp" if uc == "percent" else "auto", period=None)
            text("T1C.6", k, "result", "Result", "Not compared")
        else:
            sv = div(issuer_row[nm], issuer_row[dn])
            cv = q38(CP1_FIGS[k][0])
            num("T1C.6", k, "sheet", "Issuer line on the peer source", sv, uc, f"{dict(FIELDS)[nm]} / {dict(FIELDS)[dn]} from the issuer line", (f"T1C.2.issuer.{nm}", f"T1C.2.issuer.{dn}"), period="Twelve months to 2025-12-31")
            fact("T1C.6", k, "cp1", "CP-1", status="known", unit=UNIT[uc], period=LTM_PERIOD, amount_exact=norm(cv), shown=show(cv, uc), value_class=CP1_FIGS[k][1],
                 copied_from_cp1=f"{LTM_COLUMN} · {k}", calculation_id="{{CP1_CALCULATION_ID}}", derives_from=[],
                 lineage="the CP-1 fact verbatim: its own calculation_id and citations are bound at run time")
            if uc == "percent":
                # percent minus percent: percentage points, exact shift as T1C.4
                num("T1C.6", k, "difference", "Difference", dsub(sv, cv).scaleb(2, context=CTX), uc, "(peer-source ratio minus CP-1 ratio) x 100, percentage points", (f"T1C.6.{k}.sheet", f"T1C.6.{k}.cp1"), unit="pp")
            else:
                num("T1C.6", k, "difference", "Difference", dsub(sv, cv), uc, "peer-source ratio minus CP-1 ratio", (f"T1C.6.{k}.sheet", f"T1C.6.{k}.cp1"))
            assert sv == cv
            text("T1C.6", k, "result", "Result", "Reconciled" if sv == cv else "Differs", "calculated", formula="Reconciled iff the difference is zero", derives=(f"T1C.6.{k}.difference",))
        reg("T1C.6", k, lab, ["sheet", "cp1", "difference", "result"])

    # ---- T1C.7 gaps
    for n, g in enumerate(sub["gaps"], 1):
        r = f"g{n:02d}"
        text("T1C.7", r, "id", "Gap id", f"CP-1C-GAP-{n:03d}")
        for k, l_ in (("gap", "Gap"), ("why_it_matters", "Why it matters"), ("affected_analysis", "Affected analysis"), ("severity", "Severity"), ("action", "Action")):
            text("T1C.7", r, k, l_, g[k], "analyst_judgment" if k != "severity" else None)
        reg("T1C.7", r, f"Gap {n}", ["id", "gap", "why_it_matters", "affected_analysis", "severity", "action"])

    # ---- limitations
    if sheet:
        limits.append("Peer figures come from the peer summary source, which is supplied by a data desk and unaudited; no peer is restated to the issuer's basis.")
        limits.append("Peer ratios use the definitions stated in the peer summary; the issuer line on the same summary is tied to CP-1 in the definition alignment table.")
    else:
        limits.append("No peer source is in the pack: no peer universe, median, position or outlier flag can be formed.")
    for p in pr:
        if p["a"]["comparability"] == "Partly comparable":
            limits.append(f"Partly comparable peer included: {p['label']}: {p['a']['limitation']}")
    if sheet and n_inc < 5:
        limits.append("Medians over fewer than five peers move with a single peer.")
    for p in pr:
        for f_, l_ in FIELDS:
            if p[f_] is None:
                limits.append(f"Peer amount not stated: {p['label']} {l_.lower()}: every figure that needs it is Not calculable.")
    if sheet:
        for k, lab, *_ in METRICS:
            if stats[k]["median"] is None:
                limits.append(f"Peer median not calculable for {lab.lower()}: fewer than three included peers have a stated value.")
        limits.append("Outlier flags use a fixed distance of half the peer median; they are screens, not credit judgments.")
        limits.append("Peer positioning is a description of the peer set and is not a valuation or a recommendation; relative value belongs to CP-3.")
    for g in sub["gaps"]:
        limits.append(f"Gap ({g['severity']}): {g['gap']}")

    # ---- lineage citations: a calculated fact's citations are the ordered, de-duplicated concatenation of the citations of the
    # facts in derives_from (transitively through calculated facts). A copied CP-1 cell's citations are bound at run time and
    # are not literal here; a fact that depends on one has them bound at run time from derives_from.
    by_id = {x["fact_id"]: x for x in facts}
    memo = {}

    def lineage(fid):
        if fid in memo:
            return memo[fid]
        f = by_id[fid]
        if f.get("copied_from_cp1"):
            memo[fid] = ([], [fid])
            return memo[fid]
        if f.get("derives_from") and f.get("value_class") == "calculated":
            cites, bound = [], []
            for d in f["derives_from"]:
                c2, b2 = lineage(d)
                cites += [c for c in c2 if c not in cites]
                bound += [b for b in b2 if b not in bound]
            memo[fid] = (cites, bound)
        else:
            memo[fid] = (list(f.get("citations") or []), [])
        return memo[fid]

    for f in facts:
        if f.get("derives_from") and f.get("value_class") == "calculated" and not f.get("copied_from_cp1"):
            cites, _bound = lineage(f["fact_id"])
            if cites:
                f["citations"] = cites

    # ---- claims

    def ref(fid, tok):
        return ("{" + fid + "|" + tok + "}") if by_id[fid]["status"] == "known" else ("[" + fid + "]")

    for p in pr:
        claims.append({"claim_id": f"T1C.1.{p['row']}", "text": p["a"]["rationale"], "limitation": p["a"]["limitation"], "evidence": p["a"]["evidence"]})
    claims.append({"claim_id": "T1C.1.universe", "limitation": None,
                   "text": (f"The peer source lists {ref('T1C.8.total.sheet', 'peers')} and {ref('T1C.8.total.included', 'peers')} are included in the universe."
                            if sheet else f"No peer source is in the pack, so no universe is formed {ref('T1C.8.total.sheet', 'peers')}.")})
    for k, lab, uc, direction, nm, dn in METRICS:
        tk = TOKEN[uc]
        t = (f"{lab} of the issuer is {ref(f'T1C.3.issuer.{k}', tk)} against a peer median of {ref(f'T1C.4.{k}.median', tk)} "
             f"across {ref(f'T1C.4.{k}.n', 'peers')}.")
        if sheet and stats[k]["median"] is not None:
            t += " The issuer is flagged an outlier on this metric." if stats[k].get("flags", {}).get("issuer") else " The issuer is not flagged an outlier on this metric."
        claims.append({"claim_id": f"T1C.4.{k}", "limitation": None, "text": t})
    o = sub["overall"]
    claims.append({"claim_id": "T1C.1.assessment", "text": o["rationale"], "limitation": o["limitation"], "evidence": o["evidence"]})
    tables = [{"table_id": t, "title": title, "rows": rows[t]} for t, title in TABLES.items()]
    # table shape (contracts.validate_tables): one fact per column in every row; every canonical fact of a table sits in exactly one row
    for t in TABLES:
        cols = [tuple(i.rsplit(".", 1)[1] for i in r["fact_ids"]) for r in rows[t]]
        assert rows[t] and all(c == cols[0] for c in cols), (t, "row does not match the columns")
        listed = [i for r in rows[t] for i in r["fact_ids"]]
        assert len(listed) == len(set(listed)) and set(listed) == {x["fact_id"] for x in facts if x["table_id"] == t}, (t, "cells differ from canonical facts")

    def sx(v):
        return None if v is None else norm(v)
    summary = {
        "peers_in_source": n_sheet if sheet else None, "included": n_inc if sheet else None,
        "peer_metrics": {f"{p['row']}.{k}": (sx(val[(p['row'], k)]) if isinstance(val[(p['row'], k)], Decimal) else val[(p['row'], k)]) for p in pr for k in MKEY},
        "stats": {k: (None if s is None else {"n": s["n"], "median": sx(s["median"]),
                                                **({} if s["median"] is None else {"difference": norm(s["difference"]), "position": s["position"], "of": s["of"],
                                                                                    "sorted_included_values": s["sorted"], "outliers": s.get("outliers", [])})})
                  for k, s in stats.items()},
    }
    return {
        "peer_source": None if not sheet else {"source_id": "peers", "sha256": SHEET_SHA[name], "pages": len(SHEET[name])},
        "operands_summary": summary,
        "facts": facts, "tables": tables, "claims": claims, "own_limitations": limits,
        "settled_limitations": list(dict.fromkeys([*limits, SYNTHETIC])),
        "settled_limitations_note": "execution.py:446-452: candidate limitations then 'Synthetic case; not real issuer qualification' (case_kind synthetic), de-duplicated; inherited_limitations are run-bound (execution.py:345-366) and not literal",
        "cp1_readiness": cp1_readiness(),
        "module_status": "restricted", "FP03": fp03(facts, tables),
    }


def fp03(facts, tables):
    by_id = {x["fact_id"]: x for x in facts}
    out = {"pathway": "relative_value", "blocks": {}}
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
    out["other_blocks"] = "instrument-levels, yield-against-maturity, market-against-fundamentals, compensation-preference, recommendation-portfolio-fit and the rest of relative_value keep their idle wording or their own owners: CP-1C fills none of them. The reference's range strip Fig. RV.3 is a chart and is not populated (table form only)"
    out["evidence_rail_tables"] = EVIDENCE_TABLES
    out["limitations_rail_tables"] = LIMITATION_TABLES
    return out


# --- 7. fixtures: the composer rules at their boundaries (hand-written expected, asserted) -----------


def fixtures():
    fx = {}
    # median
    cases = [([D(3), D(1), D(2)], D(2)), ([D(1), D(2), D(3), D(4)], D("2.5")), ([D(5)], D(5)), ([D(2), D(2), D(7), D(9)], D("4.5")),
             ([D("0.3030303030303030303030303030303030303"), D("0.4")], None)]
    out = []
    for vals, want in cases:
        got = median(vals)
        if want is not None:
            assert got == want, (vals, got)
        out.append({"values": [norm(v) for v in vals], "median": norm(got)})
    fx["median"] = {"rule": "odd count: middle value; even count: (a + b) / 2 in the 38-digit half-even context on the stored values; a and b are the stored Decimals", "cases": out}
    # outlier boundary: median 2, threshold one half
    bnd = []
    for v, want in ((D("3"), False), (D("3.01"), True), (D("1"), False), (D("0.99"), True), (D("2"), False)):
        with localcontext(CTX):
            dev = (v - D(2)) / D(2)
        flag = abs(dev) > OUTLIER
        assert flag is want
        bnd.append({"value": norm(v), "median": "2", "deviation": norm(dev), "flag": "Outlier" if flag else "Within range"})
    fx["outlier_boundary"] = {"rule": "Outlier iff |value - median| / median is strictly above 0.5; exactly 0.5 is Within range", "cases": bnd}
    # positions
    pos = []
    for vals, iv, dirn, want in (([D(30), D(26), D(22), D(16)], D(25), "Higher is better", 3), ([D(2), D(3), D("1.5"), D(5)], q38(Fraction(5, 3)), "Lower is better", 2),
                                 ([D("6.5"), D(3), D(6), D(2)], D(6), "Higher is better", 2), ([D(1), D(2)], D(1), "Lower is better", 1)):
        got = 1 + sum(1 for v in vals if better(v, iv, dirn))
        assert got == want
        pos.append({"peers": [norm(v) for v in vals], "issuer": norm(iv), "direction": dirn, "position": got, "of": len(vals) + 1})
    fx["position"] = {"rule": "1 + number of entities strictly better than the issuer; an equal value shares the issuer's position", "cases": pos}
    fx["minimum_universe"] = {"rule": "a metric needs at least 3 included peers with a calculated value for median, difference, position, entities compared, outlier count and every deviation and flag; fewer is missing (never 0); n is always shown",
                              "cases": [{"included_with_value": 2, "median": "missing"}, {"included_with_value": 3, "median": "known"}]}
    fx["zero_denominators"] = {"rule": "denominator not positive: the peer metric is not_applicable (Not meaningful); numerator or denominator Not stated: missing; a median of zero: deviation and flag not_applicable",
                               "cases": [{"revenue": "0", "margin": "not_applicable"}, {"ebitda": "0", "total_leverage_adjusted": "not_applicable"},
                                         {"interest": "Not stated", "interest_coverage_adjusted": "missing"}]}
    return fx


TAMPER = {
    "case": "positive (closed run: CP-0, CP-1 and CP-1C settled, receipt sealed)",
    "target_fact": "T1C.4.total_leverage_adjusted.position",
    "from": "2 (shown '2 rank')",
    "to": "1 (shown '1 rank')",
    "why_this_fact": "the table cell holds the fact id and the step output holds only the analyst's references and judgments (no computed number), so the position lives only in the result Module; no claim and no other fact quotes it; it is the one fact the probe's rebuild (Python recomputes the position from the CP-1 head and the peer pages over the journaled payload) contradicts",
    "recipe": [
        "1. Copy the closed positive store directory (blobs, snapshots, current, audit) to a scratch path.",
        "2. Load the CP-1C head's result Module; replace only the amount of fact T1C.4.total_leverage_adjusted.position (2 -> 1); leave every other fact, table, claim and limitation unchanged.",
        "3. Serialise the forged Module as Execution._store does (model_dump_json); its sha256 R2 must equal Module.content_hash(); write blobs/R2.",
        "4. Build a new ExecutionSnapshot equal to the current one with the CP-1C Attempt.result_sha256 and Head.result_sha256 set to R2 (status, inputs and commands unchanged, so head_of(forged Module) equals the Head) and the same parent; write snapshots/<its sha256>.json and rewrite current to that digest.",
        "5. In the retained receipt: set the CP-1C SettledHead.result_sha256 to R2; set receipt.snapshot_sha256 and every coordinate that named the old final snapshot (the CP-1C settling OwnerSubmission.snapshot_after_sha256: owner_workflow.py _advance -> _finish_walk; its record is retained as audit/submissions/<content_hash> by _retain) to the new digest; delete audit/submissions/<old record hash> and write the edited OwnerSubmission as audit/submissions/<its content_hash> (model_dump_json bytes); rewrite audit/receipt.sha256 with the forged receipt's content_hash (S1a R3-5, CP-3 A4 and CP-DR rev 4 pattern: the audit file travels under its new hash).",
    ],
    "expect": {
        "passes": "everything upstream of the probe: audit inventory, blob and snapshot hashes, ancestor walk, head_of equality, begin and publication records, call and read replay (_verify_calls_reads), journaled-step replay (the payload and step are untouched)",
        "refuses": "cp1c.probe raises WorkflowError('identity_mismatch'); verify_owner_run_receipt raises identity_mismatch",
        "test_asserts": "on the forged copy, _verify_audit and every check before _PROBES pass (as CP-3 A4 (a)); then cp1c.probe raises identity_mismatch. A test asserting identity_mismatch alone would never show that the probe was reached.",
    },
    "read_body_edit": "an edited read body (a call or input_reads body) is caught before the probes, by _verify_calls_reads (owner_workflow.py:966-1010, called at :1175; _PROBES run at :1182); it is not a probe case",
    "step_output_edit": "an edited CP-1C step output is caught by the store's own blob hash check, not by the probe's output comparison (recorded limitation, S1a R3-5; CP-DR rev 4 tamper.step_output_edit)",
}

# --- 8. CP-0 / CP-1 literals ---------------------------------------------------------------------------

LIMIT = "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."
IDENT = cite("identity", 1, "Northbridge Synthetic Group is the issuer and consolidated group.")
FINC = cite("financial", 1, "Currency: USD; amounts in millions.")
PQ = "Basis: twelve months to the period end shown; USD; amounts in millions; unaudited desk summaries."
KPI_SPECS = {  # evidence selection for the CP-1 readiness literal (run-time bound)
    "ISV": ("statement_IS", "item_id == 'ebitda_adjusted' and period_id == 'fy-2025'"),
    "ISR": ("statement_IS", "item_id == 'revenue' and period_id == 'fy-2025'"),
    "CFS": ("statement_CFS", "item_id == 'cfo_ncfo' and period_id == 'fy-2025'"),
    "BS": ("statement_BS", "item_id == 'total_debt' and period_id == 'fy-2025'"),
    "SP": ("source_period", "period_id == 'fy-2025'"),
    "CON": ("construction", "column_key == 'LTM:fy-2025'"),
}


def cp1_readiness():
    return {
        "step": "readiness",
        "replaces": "the S1 literal {\"consumers\": []}; the run requests the consumer CP-1C (inputs.requested_consumers = (\"CP-1C\",), inputs.consumers = _requests((\"CP-1C\",)): policy step_12, requirements normalized_financials and period_coverage)",
        "payload": {
            "inputs_sha256": "{{PREFILLED:inputs_sha256}}",
            "consumers": [{
                "entry": "CP-1C",
                "requirements": [
                    {"requirement": "normalized_financials", "status": "limited",
                     "evidence_ids": ["{{EVID:ISR}}", "{{EVID:ISV}}", "{{EVID:CFS}}", "{{EVID:BS}}"],
                     "rationale": "Normalised income statement, cash flow and balance sheet lines for FY-2025 support the peer ratios; the statements are unaudited.",
                     "actions": ["Retain the unaudited-statement limitation in every peer comparison."]},
                    {"requirement": "period_coverage", "status": "limited",
                     "evidence_ids": ["{{EVID:SP}}", "{{EVID:CON}}"],
                     "rationale": "The last twelve months of the fiscal year are constructed as the trailing basis; peer period ends are matched by the analyst, not by CP-1.",
                     "actions": ["State any peer whose twelve months end on another date."]}],
                "gaps": [{"gap_ids": ["{{GAP_IDS}}"], "relevance": "relevant", "evidence_ids": [],
                          "rationale": "Every retained source-context and audit warning bears on the reliability of the issuer figures that anchor the peer comparison."}]}]},
        "run_time_bindings": {
            "{{PREFILLED:inputs_sha256}}": "inputs.content_hash() of the readiness step inputs (prefilled; never literal)",
            **{"{{EVID:" + k + "}}": f"evidence_id of the one catalogue record of kind {kind} with record.{pred}; none or several fails closed" for k, (kind, pred) in KPI_SPECS.items()},
            "{{GAP_IDS}}": "every inputs.narrative.gaps[*].gap_id in order (replaces the placeholder element)"},
        "validated_on": "copy of the S1 positive CP-1 head (read-only copy, 2026-10-28, 1132 gaps all WARN): validate_downstream_review() returns no issues; _assess_consumers gives CP-1C status ready_with_limitations, 0 unassessed requirements, 0 unassessed gaps, no blocking gaps",
        "expected_assessment": {"CP-1C": {"status": "ready_with_limitations", "unassessed_requirements": 0, "unassessed_gaps": 0, "blocking_gaps": [], "requirement_status": "limited"}},
        "negatives": [
            "empty review: CP-1C is not_ready",
            "no gap scope: CP-1C is not_ready",
            "normalized_financials citing only one statement kind: validate_downstream_review refuses 'Incompatible or unavailable dependency evidence: CP-1C normalized_financials'"],
    }


def readiness(case):
    rr = copy.deepcopy(SNAP["positive"]["readiness_review"])
    rr["objective"] = "Historical financial foundation and peer benchmark"
    srcs = [s for s in rr["sources"] if s["source_id"] != "business"]
    ids = ["identity", "financial"]
    cits = [IDENT, FINC]
    lims = [LIMIT]
    if case != "no_peers":
        pc = cite("peers", 1, PQ, case)
        srcs.append({"source_id": "peers", "document_family": "Peer financial summary (synthetic)", "authority": "third_party",
                     "entity": "Synthetic peers", "period": "Twelve months to the period ends shown",
                     "version_relationship": "Desk summary published with the statements", "fidelity": "verified",
                     "citations": [pc], "limitations": [SHEET_LIMIT]})
        ids.append("peers")
        cits.append(pc)
        lims.append(SHEET_LIMIT)
    rr["sources"] = srcs
    cp1 = next(c for c in rr["consumers"] if c["module_id"] == "CP-1")
    cp1c = {"module_id": "CP-1C", "readiness": "READY_WITH_LIMITATIONS",
            "evidence_demand": "Settled CP-1 ratios and a peer financial summary on aligned definitions" if case != "no_peers"
            else "Settled CP-1 ratios; no peer financial summary is supplied",
            "source_ids": ids,
            "rationale": "The benchmark can run on settled CP-1 figures and the located peer summary with explicit limitations." if case != "no_peers"
            else "No peer summary is supplied; the benchmark reduces to the issuer's own ratios and states that no comparison is possible.",
            "citations": cits, "missing_source": None, "limitations": lims}
    rr["consumers"] = [cp1, cp1c]
    rr["analysis"] = [{"claim_id": "source-assessment",
                       "text": "Located statements and the peer summary support a peer benchmark with limitations." if case != "no_peers"
                       else "Located statements support historical analysis; no peer summary is supplied.",
                       "citations": cits, "limitation": LIMIT}]
    return rr


def source_context(case):
    sc = copy.deepcopy(SNAP["positive"]["cp1_source_context"])
    sc["sources"] = [s for s in sc["sources"] if s["source_id"] != "business"]
    if case != "no_peers":
        c = cite("peers", 1, PQ, case)
        sc["sources"].append({"source_id": "peers", "classification": "nonfinancial", "document_type": "Peer financial summary (synthetic)",
                              "published_on": "2026-01-10", "evidence_class": "external",
                              "evidence_rationale": "Third-party desk summary without auditor or filing status",
                              "analytical_use": "Peer ratios for CP-1C", "citations": [c], "event_scan": "unassessed",
                              "event_scan_explanation": "A desk summary is not event evidence"})
    return sc


REFUSED_CP0 = {
    "note": "Literal CP-0 review for the refused case = tests/test_financial_workflow.py readiness(pack, gap=True) with this consumer row appended and this gap row",
    "cp0_consumer_row_cp1c": {"module_id": "CP-1C", "readiness": "CONDITIONAL", "evidence_demand": "Settled CP-1 figures",
                              "source_ids": ["identity"], "rationale": "Quarterly financial statements were not supplied.",
                              "citations": [IDENT], "missing_source": "Quarterly financial statements",
                              "limitations": ["Quarterly financial statements were not supplied."]},
    "gap_row": {"gap_id": "missing-financial", "kind": "source", "severity": "material",
                "description": "Quarterly financial statements were not supplied.", "affected_modules": ["CP-1", "CP-1C"],
                "remediation": "Supply quarterly financial statements"},
}


def main():
    built = {n: build_case(n) for n in ("positive", "gap", "no_peers")}
    run = dict(FIN["run"], pathway="relative_value", requested_modules=["CP-1C"])
    runs = {n: dict(run, run_id=f"cp1c-owner-{n.replace('_', '-')}") for n in ("positive", "gap", "no_peers", "refused")}
    srcs_ident = [{"source_id": s, "sha256": SRC[s]["sha256"], "reuse": "Every page text and locator stays byte-identical; read by reference, never edited"} for s in ("identity", "financial")]
    manifest = {
        "schema_version": "cp1c-owner-cases/1",
        "scope": "CP-1C Peer benchmark: CP-0 to CP-1 to CP-1C over the frozen financial pack alone (no peer source: limitation-only) and with one new SYNTHETIC peer financial summary source",
        "status": "DRAFT by the cp1c-owner preparation task, 2026-10-28; independent review pending; not executed",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "pins": {"cases/financial/manifest.json": FIN_SHA, "cases/snapshot/submissions.json": SNAP_SUB_SHA, "src/deploy_vii/methodology.json": METH_SHA},
        "financial_baseline": {"path": "cases/financial/manifest.json", "manifest_sha256": FIN_SHA, "sources": srcs_ident},
        "frozen_finding": "The frozen packs hold ONE issuer (Northbridge Synthetic Group). No frozen page names a peer or a comparable (asserted: the word 'peer' occurs on no frozen financial or identity page), so a peer benchmark cannot be formed from them. Case no_peers is the limitation-only design over the frozen pack; cases positive and gap add one SYNTHETIC source.",
        "synthetic_source": {
            "SYNTHETIC": True,
            "label": "Invented test data. The peers do not exist; no figure is a real market fact; every page says so.",
            "source_id": "peers", "name": SHEET_NAME, "status": "ready", "media_type": "text/plain", "extractor": "supplied-representation",
            "extraction_status": "complete", "pack_limitation": SHEET_LIMIT,
            "positive": {"pages": [{"locator": f"page:{n}", "text": t} for n, t in enumerate(SHEET["positive"], 1)], "sha256": SHEET_SHA["positive"]},
            "gap": {"pages": [{"locator": f"page:{n}", "text": t} for n, t in enumerate(SHEET["gap"], 1)], "sha256": SHEET_SHA["gap"],
                    "derivation": "three peers (Alder Ridge Holdings, Brookmere Industries, Calder Vale Group), Calder Vale Group's interest expense 'Not stated', no notes on page:2"},
            "fixtures": {"peer_table_not_found": {
                "pages": [{"locator": f"page:{n}", "text": t} for n, t in enumerate(SHEET["unparseable"], 1)], "sha256": SHEET_SHA["unparseable"],
                "derivation": "the positive page:1 without its 'Peer  Period end  ...' header line; used only by refusal r11 (no run)"}},
            "why": "No frozen source carries a second issuer. The source adds an invented peer summary so the median, outlier and position rules have something to compute.",
            "consistency_with_frozen_figures": [
                "The issuer line restates frozen FY2025 figures exactly: revenue 120.0 (page:2), adjusted EBITDA 30.0 (page:2), total debt 50.0 (page:4, 50.00), interest expense 5.0 (page:3 cash interest paid 5.00, the peer sheet's own definition; CP-1 coverage uses page:2 net interest expense, also 5.00, so the two are equal here), FFO 21.0 (page:3 operating cash flow before working capital 21.00); each asserted equal by the builder",
                "The issuer's basis line (IFRS, 1 operating segment, December 31 year end) equals frozen page:1 'Reporting basis: IFRS', 'One operating segment' and identity 'Fiscal year end: December 31'",
                "The issuer ratios recomputed from the issuer line equal CP-1's T4.10 LTM values exactly: 25.0%, 5/3 (1.67x), 6.00x, 42.0% (asserted)",
                "The source adds no fact about the issuer's business, ownership, debt terms or any frozen quantity beyond the five restated figures",
                "Peer names carry no digit (the claim check treats a digit outside a label or the issuer name as a bare figure)"],
            "peer_rows_positive": [r for r in PEER_ROWS["positive"]],
        },
        "cases": {
            "positive": {"run": runs["positive"], "pack": "identity + financial + peers (positive)", "submission": "submissions.json positive", "expected": "expected.json cases.positive",
                         "execution": "closed run: CP-0, CP-1 (five stages, readiness = cp1_readiness literal, source_context literal with the peers source), CP-1C"},
            "gap": {"run": runs["gap"], "pack": "identity + financial + peers (gap: three peers, one interest expense Not stated)", "submission": "submissions.json gap",
                    "expected": "expected.json cases.gap", "execution": "closed run: interest coverage has two peers with a value, below the minimum of three, so its median, position, outlier count and flags are missing; the other three metrics have three"},
            "no_peers": {"run": runs["no_peers"], "pack": "identity + financial, as tests/test_financial_workflow.py make_pack() (no peer source)", "submission": "submissions.json no_peers",
                         "expected": "expected.json cases.no_peers", "execution": "closed run: the limitation-only design: issuer cells known (CP-1), every peer-derived cell missing, never 0"},
            "refused": {"run": runs["refused"], "pack": "financial source missing (cases/financial/manifest.json negative_case); identity only", "submission": "submissions.json refused",
                        "expected": "expected.json cases.refused", "execution": "CP-0 only; CP-1 begin raises NotAuthorized; CP-1C never begun"},
        },
        "cp1_fact_selection_rule": {
            "table_id": "T4.10", "period": LTM_PERIOD,
            "predicate": "fact.table_id == 'T4.10' and fact.period == period and fact.label == '<column> · <metric>' with column 'LTM Q4 25 (2025-01-01 to 2025-12-31)'; exactly one match, zero or several fail closed",
            "metrics": {k: k for k in MKEY},
            "copy_rule": "T1C.3.issuer.<metric> and T1C.6.<metric>.cp1 copy the CP-1 fact: same unit, amount, decimals/currency/scale, value_class and citations; calculation_id is CP-1's own, bound at run time ({{CP1_CALCULATION_ID}}); the module fact id is its own",
            "probe": "S1 positive promoted CP-1 head, read-only copy, 2026-10-28: adjusted_ebitda_margin PERCENT 0.25 calculated (25.0%); total_leverage_adjusted MULTIPLE 1.6666666666666666666666666666666666667 calculated (1.67x); interest_coverage_adjusted MULTIPLE 6 calculated (6.00x); ffo_to_debt PERCENT 0.42 calculated (42.0%); all known; no currency/scale on ratios",
        },
        "plan": {"requested_modules": ["CP-1C"], "plan_order": ["CP-0", "CP-1", "CP-1C"],
                 "cp_model": "not requested. registry.plan(('CP-1C','CP-MODEL')) = (CP-0, CP-1, CP-1C, CP-MODEL): CP-MODEL would follow CP-1C"},
        "host_scope": {"CP-1C": "fixed H1 mapping, never caller-supplied: identity, financial and peers when the prepared pack holds a source with id 'peers' (no_peers: identity and financial)",
                       "protocol": "docs/G1X-OWNER-CORE-PROTOCOL.md section 3: an owner-only step may combine a module_context view with pack sources"},
        "d8": D8,
    }
    submissions = {
        "schema_version": "cp1c-owner-submissions/1",
        "note": "Literal analyst submissions for the peer_benchmark step. {T1C.x.y.z|token} references name the module's own facts and are literal; [T1C.x.y.z] is a gap chip. No CP-1 run-time figure marker is needed in analyst text: the issuer's CP-1 values are referenced through the module's own copied cells (T1C.3.issuer.*). Comparability is analyst judgment (Comparable, Partly comparable, Not comparable); Python derives inclusion, ratios, medians, positions and outlier flags. tool_calls.<case> is the literal tool sequence of the peer_benchmark attempt: one read_inputs, then read_pages covering every cited page (no_peers: one search_pack over the identity and financial sources returning no span). Each refusal's calls_before_submit is the literal tool sequence before its submit: its base case's tool_calls, except r10, which adds read_pages financial 1-1 for the page:1 it cites. CP-0 readiness and CP-1 source_context are derived from cases/snapshot/submissions.json (pinned) with the business source replaced by the peers source; the later CP-1 stages are those of the financial case, unchanged; the CP-1 readiness stage is cp1_readiness.",
        **{c: {"readiness_review": readiness(c), "cp1_source_context": source_context(c), "cp1_readiness": cp1_readiness(), "peer_benchmark": SUBMISSION[c],
               "tool_calls": TOOL_CALLS[c]} for c in ("positive", "gap", "no_peers")},
        "refused": REFUSED_CP0,
        "refusals": REFUSALS,
        "tool_refusals": TOOL_REFUSALS,
        "blocked": {"attempt_0": "refusals r04", "attempt_1": "refusals r04",
                    "note": "Both attempts invalid with the same issue; the CP-1C head settles blocked (S1a A3b pattern)"},
    }
    expected = {
        "schema_version": "cp1c-owner-expected/1",
        "derivation": "Hand-transcribed recipes of work/lead/cp1c-owner-preparation/lease-draft.md applied to the frozen financial pages and the SYNTHETIC peer pages by cases/cp1c-owner/builder/build.py (stdlib only). Each ratio is one division of exact decimals equal to the correctly rounded 38-significant-digit half-even rational (asserted); a median over an even count is (a + b) / 2 in that context on the stored values; a deviation is (value - median) / median in that context. Display follows display.py (ROUND_HALF_UP; amounts by the fact's decimals, multiples 2 dp 'x', percents 1 dp '%'; counts and positions '<n> <unit>'). CP-1 constants come from the frozen pages and are asserted against the manifest oracle.",
        "cell_notation": {"shown": "displayed text; unsettled cells follow report_view.fact_spelling (missing -> gap, '∅ G#'; not_applicable -> not_meaningful, '∅ G# n.m.'; G# is report-wide, not literal): shown is null there", "amount_exact": "canonical exact decimal, null when unsettled", "derives_from": "fact ids of this module, or empty on a copied CP-1 cell (copied_from_cp1)"},
        "id_rules": {"fact_id": "<table>.<row>.<field>", "calculation_id": "calc:<fact_id> on calculated facts; '{{CP1_CALCULATION_ID}}' on copied CP-1 cells (bound at run time)",
                     "peer_rows": "p01.. in peer-source order (issuer line excluded); 'issuer' is the issuer row; 'total' and 'none' are fixed rows; T1C.4 rows are metric keys",
                     "claims": "T1C.1.pNN (analyst comparability rationale), T1C.1.universe, T1C.4.<metric>, T1C.1.assessment"},
        "lineage_rule": "A calculated fact's citations (emitted literally) are the ordered, de-duplicated concatenation of the citations of the facts in derives_from, followed transitively through calculated facts; source facts cite the peer-source row; a calculated fact with no cited ancestor (counts and the inclusion flag, which rest on analyst judgment or on nothing quoted) carries none. A copied CP-1 cell keeps CP-1's citations, bound at run time and not literal: a fact that depends on one (T1C.4 difference, position, of; the T1C.5 issuer row; T1C.6 difference and result) has literal citations that exclude them (the copied cells are recoverable from derives_from and copied_from_cp1); the run-time list is CP-1's citations at that cell's place in derives_from order. A known fact never derives from a fact that is not known.",
        "policy_constants": {"minimum_included_peers": MIN_PEERS, "outlier_rule": "strictly more than one half of the peer median (relative deviation)", "inclusion": "Comparable and Partly comparable are included; Not comparable is excluded",
                             "position": "1 + number of entities strictly better than the issuer; ties share the position; direction per metric",
                             "difference": "multiples: issuer minus median, unit MULTIPLE ('x'); percent metrics: percentage points, unit pp, the unit and formula follow CP-4 (cp4_legal.py:970-972); the amount is (issuer - median) in the 38-digit context, then .scaleb(2), not CP-4's amount * 100 (which would give '1.00 pp' and a 28-digit cell); shown is exact text, compared as a string; spelled by report_view.fact_spelling as exact text + ' pp' (unit_class none); the same rule applies to every percent-minus-percent difference, including T1C.6.<percent metric>.difference",
                             "period_of_derived_facts": MIXED_PERIOD + " (T1C.8 counts, T1C.4, T1C.5); each peer's own period stays on its T1C.2 and T1C.3 cells", "status": "LEAD to confirm (open questions 2-4)"},
        "d8_table_ids": {**D8,
                         "register": "Proposal, applied nowhere in this preparation (LEAD ruling 8): T1C.1-T1C.8 replace CP-1C's table_ids in the serialised methodology.json change (CP-L10 D4, CP-1C D8), in which METH_SHA (builder pin) is re-pinned. T4.7 (the only unshared id) is dropped with them: nothing produces or reads it",
                         "repo_grep": "T1C. occurs nowhere under src, tests, docs or cases before this preparation; table_ids is read only by registry.Responsibility and tests/test_cp1b_registration.py (CP-1B ids)",
                         "module_tables_besides": []},
        "execution": {
            "entry_kind": "owner-only (registry.step_chain('CP-1C') raises 'CP-1C has no live step contract'); entry owner_core under docs/G1X-OWNER-CORE-PROTOCOL.md",
            "plan_order": ["CP-0", "CP-1", "CP-1C"],
            "statuses": {"CP-0": "restricted", "CP-1": "restricted (financial precedent)", "CP-1C": "restricted: own limitations non-empty and synthetic case"},
            "tool_use": {
                "CP-0": "pack tools plus submit",
                "CP-1": "as the financial slice",
                "CP-1C": {
                    "step": "peer_benchmark", "inputs": "module_context", "sources": True, "rules": "journaled",
                    "host_scope": "identity, financial and peers (no_peers: identity and financial) from the fixed H1 mapping",
                    "acceptance": "exactly one ok read_inputs before the submit; ok read_pages calls covering every page:N cited by the submit (assessments[*].evidence, overall.evidence); no_peers: at least one ok search_pack over identity and financial; the literal sequence is submissions.<case>.tool_calls",
                    "rules_mode": "rules='journaled' with the core's RULES(text, seen) (docs/G1X-OWNER-CORE-PROTOCOL.md section 2): unread_citation_issues only ('Cited page not read through read_pages: <source_id> page:<n>'); CP-1C's schema carries no ABSENCE_MARKERS value",
                    "view": "read_inputs serves the exact context_block view, no evidence lines: upstream [{module_id, status}], peers {state present|absent, source_id, pages, rows, issuer_line}, cp1_facts [{ref, label, period, unit, shown, value_class}], rules {minimum_included_peers, outlier_fraction, inclusion, position}, inherited_limitations; quotable evidence comes only from read_pages",
                },
            },
            "consumption": {
                "status": "open: no consumer core reads CP-1C; CP-1C is not complete until CP-3 (or another named consumer) reads it under its own lease amendment (PLAN.md:7-8); consumers may read the position but never re-rank (LEAD ruling 5)",
                "consumer_facts": ["T1C.4.<metric>.median", "T1C.4.<metric>.difference", "T1C.4.<metric>.position", "T1C.4.<metric>.outlier_count", "T1C.8.total.included"],
                "proof": "a consumer's attempt inputs bind Input('CP-1C', head.result_sha256, status) and a consumer fact or claim derives from those T1C.4 facts, read through the CP-1C head",
                "edges": "methodology.json lists CP-1C optional for CP-2, CP-3 and CP-5 only (registry.edge_rule restricted); cp3_relative_value.READ_OPTIONAL = CP-1A, CP-4; methods/cp3.md, cp6.md and cp2.md name CP-1C as the owner of peer ranking and forbid it in their own text; CP-5 counts only after a lease extends its integrity scope",
            },
            "cp0_t8": {"positive": [["CP-1", "Run CP-1"], ["CP-1C", "Run CP-1C"]]},
        },
        "refusals": [{"id": r["id"], "class": r["class"], "base_case": r["base_case"], "pack": r["pack"], "calls_before_submit": r["calls_before_submit"], "expected_issues": r["expected_issues"], "disposition": "invalid step on attempt 0 (journaled validator issues), re-begun as attempt 1"} for r in REFUSALS],
        "tool_refusals": TOOL_REFUSALS,
        "refusal_rules": {
            "order": "Content issues follow shape issues; a shape failure returns alone. Issue text is frozen here; the validator must produce each expected_issues entry (prefix match where it ends in an open parenthesis) and no other. Product-produced wording (probed): 'Bare figure: <token>' (prose.issues), 'Unresolved reference: <id>', 'Figure reference names a gap: <id>', 'Malformed run text: unbalanced or empty reference' (prose.tokenize), the prohibited-conclusion line (business_context.prohibited_issues, kinds instrument recommendation and recovery conclusion, never peer ranking), 'Quote/locator mismatch: quote not found under <source> page:<n> (' (readiness.citation_issues). Every other text is this draft's proposal.",
            "assessments": "exactly one per peer row of the sheet (issuer line excluded), by exact label; evidence (at least one citation) required for every assessment; Partly comparable requires a non-null limitation",
            "confidence": "High is refused whenever a peer source is present; with no peer source the rule does not apply (Low expected)",
            "no_peer_source": "no source with id 'peers' in the pack: any assessment is refused with 'Assessment given without a peer source in the pack: <peer>' (no Unknown peer issues)",
            "unparseable_peer_source": "a peers source whose page:1 lacks the table header line gives 'Peer table not found' alone",
            "prose": "the core calls prose.issues(text, bound, names=(issuer,)) on every rationale and the overall rationale after binding the module's facts, and emits its text unchanged; the module path for a settled claim prefixes 'Claim <claim_id>: '",
        },
        "blocked": {"attempt_0": "r04", "attempt_1": "r04", "head_status": "blocked", "tables": "none (a blocked head carries limitations only)",
                    "limitations_contain": "Evidence required for a comparability assessment: Alder Ridge Holdings"},
        "tamper": TAMPER,
        "fixtures": fixtures(),
        "cases": {},
    }
    for n, b in built.items():
        expected["cases"][n] = dict(b)
    expected["cases"]["refused"] = {
        "plan_order": ["CP-0", "CP-1", "CP-1C"],
        "CP-0": {"status": "restricted", "T8_commands": {"CP-1": "DO NOT RUN", "CP-1C": "DO NOT RUN"}},
        "refused_begins": [{"module_id": "CP-1", "reason": "str(NotAuthorized): CP-0 has not authorized this consumer's source readiness"}],
        "attempts": ["CP-0"], "heads": ["CP-0"], "cp1c": "never begun (G1 stops the walk after a RefusedBegin)", "model_publication": "not planned", "receipt": "verifies",
        "must_not_appear": ["a CP-1C ticket, attempt, head or table", "a median, position or flag of 0 standing for a missing one"],
    }
    # sanity on analyst prose: digits only inside references
    for case, sub in SUBMISSION.items():
        texts = [a["rationale"] for a in sub["assessments"]] + [sub["overall"]["rationale"]] + [a["limitation"] or "" for a in sub["assessments"]]
        for t in texts:
            t2 = re.sub(r"\{T1C\.[0-9a-z_.]+\|[^}]*\}|\[T1C\.[0-9a-z_.]+\]", "", t)
            assert not re.search(r"[0-9]", t2), t
    OUT.mkdir(parents=True, exist_ok=True)
    for name, obj in (("manifest", manifest), ("submissions", submissions), ("expected", expected)):
        (OUT / f"{name}.json").write_text(json.dumps(obj, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
