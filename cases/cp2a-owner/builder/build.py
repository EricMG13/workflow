"""Writes cases/cp2a-owner/{manifest,submissions,expected}.json (stdlib only).

An independent transcription of the CP-2A (Downside pathway) composition rules written in
work/lead/cp2a-owner-preparation/lease-draft.md. deploy_vii is never imported or run here.
Every number is derived from the frozen financial source bytes (cases/financial/manifest.json,
hash-checked) by exact rational arithmetic (fractions.Fraction) and cross-checked against the
recipe in decimal.Context(prec=38, ROUND_HALF_EVEN), the context of model/_cells.py.

Revision 2 (after review-precise-1 and the LEAD rulings of 2026-10-28): cp1_references and
lineage (M2), literal refusals and the two-failure blocked case (M4), the CP-1 readiness literal and
its frozen run-time predicates (M5), claim-based scenario rationales (M7), FP05 state words (M3),
literal CP-0 rows (L1), own limitations for left-out items (L4-L6), CP-1 constants asserted against
the financial oracle (L7), the exact-Fraction round trip (M1).

Revision 3 (fix round 2, review-precise-2): refusal v17 is validator-only with a literal Upstream
(M1); T2B.8 level copies take the T2B.6 level's own value_class and the two definition constants
T2B.6.b01/b02.level carry value_class None (L2).

Run: python3 -I cases/cp2a-owner/builder/build.py   (from the repository root)
"""

import hashlib
import json
import re
import sys
from copy import deepcopy
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "cases" / "cp2a-owner"
FIN_PATH = ROOT / "cases" / "financial" / "manifest.json"
FIN_BYTES = FIN_PATH.read_bytes()
FIN_SHA = hashlib.sha256(FIN_BYTES).hexdigest()
FIN = json.loads(FIN_BYTES)
assert FIN_SHA == "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432", FIN_SHA

CTX = Context(prec=38, rounding=ROUND_HALF_EVEN)
D = Decimal


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


SRC = {s["source_id"]: s for s in FIN["sources"]}
for _sid, _s in SRC.items():
    assert page_sha([p["text"] for p in _s["pages"]]) == _s["sha256"], _sid
PAGE = {p["locator"]: p["text"] for p in SRC["financial"]["pages"]}


# --- 1. the base operands, parsed from the frozen statement pages -----------------------------


def row_values(page, label, count):
    """The `count` numbers after `label` on a statement line; (x) is negative."""
    for line in PAGE[page].split("\n"):
        if line.startswith(label + "  "):
            tokens = line[len(label) :].split()
            assert len(tokens) == count, (label, tokens)
            return [D(t[1:-1]) * -1 if t.startswith("(") else D(t) for t in tokens]
    raise AssertionError(label)


EBITDA_Q = row_values("page:2", "Reported EBITDA", 5)  # Q1..Q4, FY
INTEREST_Q = row_values("page:3", "Cash interest paid", 5)
FCF_Q = row_values("page:3", "Levered free cash flow", 5)
DEBT_BS = row_values("page:4", "Total debt", 6)  # opening, Q1..Q4, FY
CASH_BS = row_values("page:4", "Cash and cash equivalents", 6)
for _series in (EBITDA_Q, INTEREST_Q, FCF_Q):
    assert sum(_series[:4]) == _series[4]  # the FY column is the sum of the quarters
LTM = {
    "ebitda": sum(EBITDA_Q[:4]),
    "interest": sum(INTEREST_Q[:4]),
    "fcf": sum(FCF_Q[:4]),
    "total_debt": DEBT_BS[4],
    "cash": CASH_BS[4],
}
oracle = FIN["q4_ltm_derived_source_units"]
assert LTM["ebitda"] == D(oracle["ebitda"]) and LTM["fcf"] == D(oracle["fcf"])
assert LTM["total_debt"] == D(oracle["total_debt"])
assert LTM["total_debt"] - LTM["cash"] == D(oracle["net_debt"])
assert LTM["interest"] == D("5")  # q4_ltm_metric_oracle.interest_coverage_reported denominator
Q3 = {
    "ebitda": EBITDA_Q[2],
    "interest": INTEREST_Q[2],
    "fcf": FCF_Q[2],
    "total_debt": DEBT_BS[3],
    "cash": CASH_BS[3],
}
# Q4 25 quarter base (fixture_quarter_known, round 6 P1-W item 7): the quarter flows are asserted
# against the ruled values, which must equal the frozen source's Q4 25 column parsed above.
Q4 = {
    "ebitda": EBITDA_Q[3],
    "interest": INTEREST_Q[3],
    "fcf": FCF_Q[3],
    "total_debt": DEBT_BS[4],
    "cash": CASH_BS[4],
}
assert (Q4["ebitda"], Q4["interest"], Q4["fcf"]) == (D("7.5"), D("1.25"), D("2.25")), Q4
assert (Q4["total_debt"], Q4["cash"]) == (D("50"), D("20")), Q4

LTM_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
Q4_PERIOD = "Q4 25: 2025-10-01 to 2025-12-31"
Q4_COLUMN = "Q4 25 (2025-10-01 to 2025-12-31)"
Q3_PERIOD = "Q3 25: 2025-07-01 to 2025-09-30"
LTM_COLUMN = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
Q3_COLUMN = "Q3 25 (2025-07-01 to 2025-09-30)"
# CP-1 text observed on the S1 positive promoted head (probe, read only) for a month-less ratio:
Q3_GATE = "COMPONENT_MISSING; Four complete contiguous quarters spanning 364-371 days are required"
# P1-W (round 6): a ratio whose CP-1 fact is known, asked of a single-quarter base, is not meaningful
P1W_REASON = "Not meaningful: the base period is a single quarter, and ratios need a twelve-month base"
P1W_COMPARE = "Not compared: CP-2A's ratio is not meaningful on a single-quarter base"
P1W_OUTCOME = "Not meaningful on a single-quarter base"
P1W_LINE = ("Ratios are not calculated on a single-quarter base: CP-1 reads each ratio from the twelve months ending that quarter, "
            "while CP-2A's base operands are one quarter's flows.")
NOT_DISCLOSED = "Cash interest is not disclosed in the supplied statements."

# --- 1b. the CP-1 facts CP-2A reads, as observed on the S1 positive promoted CP-1 head ----------
# (probe, read only copy r2pos-orig, 2026-10-28). Amounts below are NOT observed constants: they
# are derived from the frozen pages and asserted against the financial oracle; only the CP-1
# value_class and the CP-1 table cell text are observed strings (and the cell text is cross-checked
# against `show`, this builder's transcription of display.format_value).

METRICS = ("ebitda", "cash_interest", "fcf", "total_debt", "cash_closing",
           "total_leverage_reported", "net_leverage_reported", "interest_coverage_reported", "fcf_to_debt")
RATIO_REPORTED = {"total_leverage": "total_leverage_reported", "net_leverage": "net_leverage_reported",
                  "interest_coverage": "interest_coverage_reported", "fcf_to_debt": "fcf_to_debt"}
OBSERVED_CLASS = {
    "LTM": {"ebitda": "calculated", "cash_interest": "calculated", "fcf": "calculated", "total_debt": "source",
            "cash_closing": "source", "total_leverage_reported": "calculated", "net_leverage_reported": "calculated",
            "interest_coverage_reported": "calculated", "fcf_to_debt": "calculated"},
    "Q3": {"ebitda": "source", "cash_interest": "normalized", "fcf": "calculated", "total_debt": "source",
           "cash_closing": "source", "total_leverage_reported": "calculated", "net_leverage_reported": "calculated",
           "interest_coverage_reported": "calculated", "fcf_to_debt": "calculated"},
}
OBSERVED_CLASS["Q4"] = dict(OBSERVED_CLASS["Q3"])  # round 6 P1-W item 7: the value classes follow the gap case's Q3 25 facts
OBSERVED_CELL = {  # the CP-1 T4.10 cell text (fact_spelling) observed on the probe head (LTM and Q3 entries)
    "LTM": {"ebitda": "30", "cash_interest": "(5)", "fcf": "9", "total_debt": "50", "cash_closing": "20",
            "total_leverage_reported": "1.67x", "net_leverage_reported": "1.00x",
            "interest_coverage_reported": "6.00x", "fcf_to_debt": "18.0%"},
    "Q3": {"ebitda": "8", "cash_interest": "(1)", "fcf": "2", "total_debt": "49", "cash_closing": "19"},
    # Q4 25 quarter flows with the LTM Q4 25 ratios and closing balances (CP-1 reads a quarter's ratio from its twelve months); derived via show(), not observed
    "Q4": {"ebitda": "8", "cash_interest": "(1)", "fcf": "2", "total_debt": "50", "cash_closing": "20",
           "total_leverage_reported": "1.67x", "net_leverage_reported": "1.00x",
           "interest_coverage_reported": "6.00x", "fcf_to_debt": "18.0%"},
}
_mo = FIN["q4_ltm_metric_oracle"]
ORACLE_RATIO = {rn: Fraction(_mo[m]["numerator"]) / Fraction(_mo[m]["denominator"]) for rn, m in RATIO_REPORTED.items()}
assert ORACLE_RATIO["total_leverage"] == Fraction(_mo["total_leverage_reported"]["fraction"])
for _rn in ("net_leverage", "interest_coverage", "fcf_to_debt"):
    assert ORACLE_RATIO[_rn] == Fraction(D(_mo[RATIO_REPORTED[_rn]]["decimal"])), _rn
# L7: every CP-1 constant the oracle holds is asserted against the frozen financial oracle
assert ORACLE_RATIO["total_leverage"] == Fraction(LTM["total_debt"]) / Fraction(LTM["ebitda"])
assert ORACLE_RATIO["net_leverage"] == Fraction(LTM["total_debt"] - LTM["cash"]) / Fraction(LTM["ebitda"])
assert ORACLE_RATIO["interest_coverage"] == Fraction(LTM["ebitda"]) / Fraction(LTM["interest"])
assert ORACLE_RATIO["fcf_to_debt"] == Fraction(LTM["fcf"]) / Fraction(LTM["total_debt"])
assert (_mo["total_leverage_reported"]["numerator"], _mo["total_leverage_reported"]["denominator"]) == ("50", "30")
assert (_mo["interest_coverage_reported"]["numerator"], _mo["interest_coverage_reported"]["denominator"]) == ("30", "5")
assert (_mo["fcf_to_debt"]["numerator"], _mo["fcf_to_debt"]["denominator"]) == ("9", "50")


# --- 2. exact arithmetic ----------------------------------------------------------------------


def fr(x):
    return Fraction(x) if not isinstance(x, Fraction) else x


def q38(x):
    """The correctly rounded 38-significant-digit half-even Decimal of an exact rational."""
    f = fr(x)
    if f == 0:
        return D(0)
    with localcontext(CTX):
        return D(f.numerator) / D(f.denominator)


def norm(d):
    """Canonical exact string of a Decimal (fixed-point, no trailing zeros, no exponent)."""
    text = format(d, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def show(d, unit_class, decimals=None):
    """display.format_value for a known number: ROUND_HALF_UP on the exact value."""
    places, scale, suffix = {"amount": (0, 1, ""), "multiple": (2, 1, "x"), "percent": (1, 100, "%")}[unit_class]
    if decimals is not None:
        places = decimals
    scaled = d * scale
    rounded = scaled.quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP)
    body = f"{abs(rounded):,.{places}f}"
    return (f"({body})" if rounded < 0 else body) + suffix


def pct(d):
    return show(d, "percent")


def mult(d):
    return show(d, "multiple")


def amt(d, decimals=2):
    return show(d, "amount", decimals)


def cp1_inputs(which, column, period, base, *, gate, undisclosed=False):
    """The nine CP-1 T4.10 facts CP-2A reads for one base: label, period, status, exact amount (CP-1
    stores cash interest negative), CP-1's own value_class and cell text; where CP-1 has no known
    fact, the limitation CP-1 carries. `which` selects the observed value classes."""
    amounts = {
        "ebitda": base["ebitda"], "cash_interest": None if base["interest"] is None else -base["interest"],
        "fcf": base["fcf"], "total_debt": base["total_debt"], "cash_closing": base["cash"],
    }
    for rn, metric in RATIO_REPORTED.items():
        amounts[metric] = q38(ORACLE_RATIO[rn]) if which in ("LTM", "Q4") else None
    out = {}
    for metric in METRICS:
        value = amounts[metric]
        known = value is not None and (gate or metric in ("ebitda", "cash_interest", "fcf", "total_debt", "cash_closing"))
        if undisclosed and metric in ("cash_interest", "interest_coverage_reported"):
            known = False
        reason = None
        if not known:
            reason = NOT_DISCLOSED if undisclosed else Q3_GATE
        cell = None
        if known:
            cell = OBSERVED_CELL[which][metric]
            unit_class = "multiple" if metric.endswith("_reported") else "percent" if metric == "fcf_to_debt" else "amount"
            assert show(value, unit_class, None) == cell, (metric, show(value, unit_class, None), cell)
        out[metric] = {
            "label": f"{column} · {metric}", "period": period, "status": "known" if known else "missing",
            "amount_exact": norm(value) if known else None, "value_class": OBSERVED_CLASS[which][metric],
            "cell_text": cell, "limitation": reason,
        }
    return out


# --- 3. the stress recipes --------------------------------------------------------------------
# Every quantity is an exact rational because numerators and denominators are products or sums of
# short decimals; each Decimal result is one division of exact operands, so the Decimal path and
# the Fraction path must agree to the last digit (asserted).

NC_DENOM = "Not calculable: stressed EBITDA is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"


def stress(base, s, k, gate_ratios, gate_reason, gate_na=False):
    """One scenario. `base` holds Decimals (None where CP-1 has no known fact)."""
    e, i, f, d, c = (base[x] for x in ("ebitda", "interest", "fcf", "total_debt", "cash"))
    out = {}
    # exact flows
    out["ebitda"] = e * (1 - s)
    out["interest"] = None if i is None else i * (1 + k)
    if f is None:
        out["fcf"] = None
    elif k != 0 and i is None:
        out["fcf"] = None
    else:
        out["fcf"] = f - e * s - (D(0) if k == 0 else i * k)
    e2, i2, f2 = out["ebitda"], out["interest"], out["fcf"]
    why = {}
    na = set()  # ratios that are not_applicable (P1-W), not missing

    def ratio(name, num, den, den_zero_reason, needs=()):
        for what in needs:
            if base[what] is None:
                why[name] = f"Not calculable: base {WORDS[what]} is missing"
                return None
        if not gate_ratios:
            if gate_na:
                why[name] = P1W_REASON
                na.add(name)
            else:
                why[name] = f"Not calculable: {gate_reason}"
            return None
        if den <= 0:
            why[name] = den_zero_reason
            return None
        r = fr(num) / fr(den)
        with localcontext(CTX):
            val = num / den
        assert val == q38(r), (name, val, q38(r))
        return val

    out["total_leverage"] = ratio("total_leverage", d, e2, NC_DENOM, ("total_debt",))
    out["net_leverage"] = ratio("net_leverage", None if (c is None or d is None) else d - c, e2, NC_DENOM, ("total_debt", "cash"))
    out["interest_coverage"] = ratio(
        "interest_coverage", e2, i2, "Not calculable: stressed cash interest is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)", ("interest",)
    )
    out["fcf_to_debt"] = None
    if f2 is None:
        why["fcf_to_debt"] = "Not calculable: stressed free cash flow is missing"
    else:
        out["fcf_to_debt"] = ratio("fcf_to_debt", f2, d, "Not calculable: debt is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)", ("total_debt",))
    if f2 is None:  # A4: formula order puts F before I, so a missing base FCF is named first
        why["fcf"] = ("Not calculable: base free cash flow is missing" if f is None
                      else "Not calculable: base cash interest is missing, so an interest increase cannot be applied")
    out["why"] = why
    out["na"] = na
    return out


WORDS = {"total_debt": "total debt", "cash": "cash", "interest": "cash interest", "ebitda": "EBITDA", "fcf": "free cash flow"}


def breaks_for(base, thresholds, gate_ratios, gate_reason, gate_na=False):
    """Register of break points: required EBITDA decline s* at base cash interest."""
    e, i, f, d, c = (base[x] for x in ("ebitda", "interest", "fcf", "total_debt", "cash"))
    rows = []

    def add(bid, origin, test, kind, level, s_num, s_den, at_break, ratio_based, needs, label=None):
        row = {"bid": bid, "origin": origin, "test": test if label is None else label, "kind": kind, "level": level}
        miss = [x for x in needs if base[x] is None]
        if miss:
            row.update(outcome="Not calculable", reason=f"Not calculable: base {WORDS[miss[0]]} is missing")
        elif ratio_based and not gate_ratios and gate_na:
            row.update(outcome=P1W_OUTCOME, reason=P1W_REASON, na=True)
        elif ratio_based and not gate_ratios:
            row.update(outcome="Not calculable", reason=f"Not calculable: {gate_reason}")
        elif s_den <= 0:
            row.update(outcome="Not calculable", reason="Not calculable: the denominator is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)")
        else:
            sf = fr(s_num) / fr(s_den)
            with localcontext(CTX):
                sv = s_num / s_den
            assert sv == q38(sf)
            row["s"] = sv
            row["s_fraction"] = f"{sf.numerator}/{sf.denominator}"
            if sf <= 0:
                row["outcome"] = "Already reached at base"
            elif sf > 1:
                row["outcome"] = "Not reached by a decline of up to 100%"
            else:
                row["outcome"] = "Reached at the stated decline"
            row["at_break"] = at_break(sv) if at_break else None
        rows.append(row)

    add("fcf_zero", "Definition", "Free cash flow at or below zero", "fcf", D(0), f, e, lambda s: e - f if f is not None else None, False, ("fcf",))
    # EBITDA equal to cash interest (coverage 1.00x): s* = (E - I) / E
    add("coverage_floor", "Definition", "EBITDA no longer covers cash interest", "coverage", D(1), None if i is None else e - i, e, lambda s: i, True, ("interest",))
    for t in thresholds:
        lvl = D(t["level"])
        if t["metric"] == "total_leverage":
            add(t["bid"], "Analyst assumption", t["label"], "total_leverage", lvl, None if d is None else lvl * e - d, lvl * e, lambda s, lvl=lvl: d / lvl, True, ("total_debt",))
        elif t["metric"] == "net_leverage":
            nd = None if (d is None or c is None) else d - c
            if nd is not None and nd <= 0 and gate_ratios:  # A8: missing operands, then the gate, then this short-circuit
                rows.append({"bid": t["bid"], "origin": "Analyst assumption", "test": t["label"], "kind": "net_leverage", "level": lvl,
                             "outcome": "Not reached by a decline of up to 100%", "reason": "Net debt is not positive, so no EBITDA decline raises net leverage"})
            else:
                add(t["bid"], "Analyst assumption", t["label"], "net_leverage", lvl, None if nd is None else lvl * e - nd, lvl * e,
                    lambda s, lvl=lvl, nd=nd: nd / lvl, True, ("total_debt", "cash"))
        else:
            add(t["bid"], "Analyst assumption", t["label"], "coverage", lvl, None if i is None else e - lvl * i, e, lambda s, lvl=lvl: lvl * i, True, ("interest",))
    return rows


def rank(rows):
    ranked = [r for r in rows if "s" in r and r["outcome"] != "Not reached by a decline of up to 100%"]
    return sorted(ranked, key=lambda r: (r["s"], [x["bid"] for x in rows].index(r["bid"])))


def crossing(row, sc):
    """Whether a scenario's stressed metric is at or beyond a break's level."""
    kind, lvl = row["kind"], row["level"]
    if kind == "fcf":
        v = sc["fcf"]
        return (v, None if v is None else v <= lvl)
    if kind == "coverage":
        v = sc["interest_coverage"]
        return (v, None if v is None else v <= lvl)
    v = sc[kind]
    return (v, None if v is None else v >= lvl)


# --- 4. the literal analyst submissions -------------------------------------------------------

FIGS = {
    "total_leverage_reported": {"metric": "total_leverage_reported", "unit_token": "x", "spelled": "1.67x", "oracle_ratio": "50/30"},
    "net_leverage_reported": {"metric": "net_leverage_reported", "unit_token": "x", "spelled": "1.00x", "oracle_ratio": "30/30"},
    "interest_coverage_reported": {"metric": "interest_coverage_reported", "unit_token": "x", "spelled": "6.00x", "oracle_ratio": "30/5"},
    "fcf_to_debt": {"metric": "fcf_to_debt", "unit_token": "%", "spelled": "18.0%", "oracle_ratio": "9/50"},
    "ebitda_ltm": {"metric": "ebitda", "unit_token": "US$ m", "spelled": "30 US$ m", "oracle_ratio": "30"},
    "total_debt_ltm": {"metric": "total_debt", "unit_token": "US$ m", "spelled": "50 US$ m", "oracle_ratio": "50"},
    "fcf_ltm": {"metric": "fcf", "unit_token": "US$ m", "spelled": "9 US$ m", "oracle_ratio": "9"},
}
CP1_LTM = cp1_inputs("LTM", LTM_COLUMN, LTM_PERIOD, LTM, gate=True)
for _n, _f in FIGS.items():
    _f["cp1_label"] = f"{LTM_COLUMN} · {_f['metric']}"
    _f["cp1_coordinate"] = f"T4.10 {_f['metric']}, twelve-month (LTM) basis ending Q4 2025, 2025-01-01 to 2025-12-31"
    _f["cell_text"] = CP1_LTM[_f["metric"]]["cell_text"]
    _f["value_class"] = CP1_LTM[_f["metric"]]["value_class"]
    # the prose spelling is the CP-1 cell text, with the scale label after an amount
    assert _f["spelled"] == _f["cell_text"] + (" US$ m" if _f["unit_token"] == "US$ m" else ""), _n
    # the CP-1 amount, the oracle ratio and the FIG spelling agree (L7)
    assert D(CP1_LTM[_f["metric"]]["amount_exact"]) == q38(Fraction(_f["oracle_ratio"])), _n


def fig(name):
    return "{{FIG:" + name + "|" + FIGS[name]["unit_token"] + "}}"


def spell_figs(text):
    return re.sub(r"\{\{FIG:([a-z_]+)\|[^}]*\}\}", lambda m: FIGS[m.group(1)]["spelled"], text)


ANALYST_NOTE = "Scenario sizes and watch levels are analyst assumptions."
SUBMISSION = {
    "positive": {
        "base_period": LTM_PERIOD,
        "scenarios": [
            {"name": "Moderate downturn", "ebitda_decline": "0.20", "interest_increase": "0", "category": "Analyst Interpretation",
             "rationale": f"A moderate fall in volumes lowers earnings from the {fig('ebitda_ltm')} twelve-month level while debt of {fig('total_debt_ltm')} and cash interest stay as reported.",
             "limitation": None},
            {"name": "Severe downturn", "ebitda_decline": "0.40", "interest_increase": "0", "category": "Analyst Interpretation",
             "rationale": f"A severe fall in volumes cuts earnings by a larger share of the {fig('ebitda_ltm')} twelve-month level; debt and cash interest stay as reported.",
             "limitation": None},
            {"name": "Severe downturn with higher rates", "ebitda_decline": "0.40", "interest_increase": "0.20", "category": "Analyst Interpretation",
             "rationale": "The severe fall in volumes coincides with a rise in the rate paid on the term loan.",
             "limitation": "No rate curve or hedging disclosure supports the size of the interest increase."},
            {"name": "Total loss of earnings", "ebitda_decline": "1.00", "interest_increase": "0", "category": "Analyst Interpretation",
             "rationale": "A boundary case in which earnings fall to zero; it shows which ratios stop being meaningful and which stay calculable.",
             "limitation": None},
        ],
        "thresholds": [
            {"metric": "total_leverage", "level": "2.50", "label": "Total leverage watch level", "category": "Analyst Interpretation",
             "rationale": "An internal watch level, not a covenant; no covenant source is bound to this run."},
            {"metric": "net_leverage", "level": "2.00", "label": "Net leverage watch level", "category": "Analyst Interpretation",
             "rationale": "An internal watch level, not a covenant; no covenant source is bound to this run."},
            {"metric": "interest_coverage", "level": "2.00", "label": "Interest coverage watch level", "category": "Analyst Interpretation",
             "rationale": "An internal watch level, not a covenant; no covenant source is bound to this run."},
        ],
        "assessment": {
            "rationale": f"The credit starts from total leverage of {fig('total_leverage_reported')}, net leverage of {fig('net_leverage_reported')}, interest coverage of {fig('interest_coverage_reported')} and free cash flow of {fig('fcf_ltm')}; the scenarios test how far earnings can fall before those measures reach the watch levels.",
            "category": "Analyst Interpretation", "confidence": "Medium", "limitation": ANALYST_NOTE,
        },
        "gaps": [
            {"gap": "No covenant document or maturity schedule is an input to this stress.",
             "why_it_matters": "The watch levels are the analyst's, so the order in which lenders' own tests are reached may differ from the order shown.",
             "affected_analysis": "Break-point ranking", "severity": "Material",
             "action": "Run the covenant owner and compare its tests with the watch levels."},
        ],
    },
    "gap": {
        "base_period": Q3_PERIOD,
        "scenarios": [
            {"name": "Moderate downturn", "ebitda_decline": "0.20", "interest_increase": "0", "category": "Analyst Interpretation",
             "rationale": "A moderate fall in volumes lowers quarterly earnings while debt and cash interest stay as reported.",
             "limitation": None},
            {"name": "Severe downturn with higher rates", "ebitda_decline": "0.40", "interest_increase": "0.20", "category": "Analyst Interpretation",
             "rationale": "A severe fall in volumes coincides with a rise in the rate paid on the term loan.",
             "limitation": "No rate curve or hedging disclosure supports the size of the interest increase."},
        ],
        "thresholds": [
            {"metric": "total_leverage", "level": "2.50", "label": "Total leverage watch level", "category": "Analyst Interpretation",
             "rationale": "An internal watch level, not a covenant; no covenant source is bound to this run."},
        ],
        "assessment": {
            "rationale": "The chosen base period is a single quarter, so the twelve-month ratios are not available and only flow results can be stated.",
            "category": "Analyst Interpretation", "confidence": "Low", "limitation": "Twelve-month ratios are not calculable for the chosen quarter.",
        },
        "gaps": [
            {"gap": "Twelve-month leverage and coverage are not calculable for the third quarter.",
             "why_it_matters": "Only stressed earnings and free cash flow can be stated; no ratio and no leverage break point can be.",
             "affected_analysis": "Stressed credit metrics and the leverage watch level", "severity": "Material",
             "action": "Base the stress on the twelve-month column ending the fourth quarter."},
        ],
    },
}
# composer-only: the gap case's submission on the Q4 25 quarter base, whose CP-1 ratios are known (round 6 P1-W item 7)
SUBMISSION["fixture_quarter_known"] = deepcopy(SUBMISSION["gap"])
SUBMISSION["fixture_quarter_known"]["base_period"] = Q4_PERIOD
SUBMISSION["fixture_quarter_known"]["gaps"][0]["gap"] = "Twelve-month leverage and coverage are not calculable for the fourth quarter."
# composer-level gap: positive CP-1 facts with base cash interest missing (no run, no store).
SUBMISSION["interest_undisclosed"] = {
    "base_period": LTM_PERIOD,
    "scenarios": [
        {"name": "Severe downturn", "ebitda_decline": "0.40", "interest_increase": "0", "category": "Analyst Interpretation", "rationale": "A severe fall in volumes cuts earnings.", "limitation": None},
        {"name": "Severe downturn with higher rates", "ebitda_decline": "0.40", "interest_increase": "0.20", "category": "Analyst Interpretation", "rationale": "A severe fall in volumes with a higher rate.", "limitation": None},
    ],
    "thresholds": [],
    "assessment": {"rationale": "Cash interest was not disclosed, so coverage cannot be stated.", "category": "Insufficient Information", "confidence": "Insufficient Information",
                   "limitation": "Cash interest is not disclosed in the supplied statements."},
    "gaps": [],
}

CASES = {
    "positive": {"submission": "positive", "base": LTM, "period": LTM_PERIOD, "gate": True, "gate_reason": None, "execution": "run",
                 "which": "LTM", "column": LTM_COLUMN, "undisclosed": False},
    "gap": {"submission": "gap", "base": Q3, "period": Q3_PERIOD, "gate": False,
            "gate_reason": f"CP-1 has no twelve-month basis for this period ({Q3_GATE})", "execution": "run",
            "which": "Q3", "column": Q3_COLUMN, "undisclosed": False},
    "interest_undisclosed": {"submission": "interest_undisclosed", "base": dict(LTM, interest=None), "period": LTM_PERIOD, "gate": True,
                             "gate_reason": None, "execution": "composer_only", "which": "LTM", "column": LTM_COLUMN, "undisclosed": True},
    "fixture_quarter_known": {"submission": "fixture_quarter_known", "base": Q4, "period": Q4_PERIOD, "gate": False, "gate_na": True,
                              "gate_reason": P1W_REASON, "execution": "composer_only", "which": "Q4", "column": Q4_COLUMN,
                              "undisclosed": False, "cp1_ratios": True},
}
for _c in CASES.values():
    _c["cp1"] = cp1_inputs(_c["which"], _c["column"], _c["period"], _c["base"], gate=_c.get("cp1_ratios", _c["gate"]), undisclosed=_c["undisclosed"])
# the threshold ids are assigned in submission order after the two definition breaks
for _case in SUBMISSION.values():
    for _n, _t in enumerate(_case["thresholds"], 3):
        _t["bid"] = f"b{_n:02d}"


# --- 5. composition ---------------------------------------------------------------------------

TABLES = {
    "T2B.1": "Scenario register",
    "T2B.2": "Base operands",
    "T2B.3": "Stressed earnings and cash flow",
    "T2B.4": "Stressed credit metrics",
    "T2B.5": "Base reconciliation to CP-1",
    "T2B.6": "Break-point register",
    "T2B.7": "First-break ranking",
    "T2B.8": "Scenario against break points",
    "T2B.9": "Gaps ledger",
}
OPERANDS = (
    ("ebitda", "EBITDA", "amount", "ebitda"),
    ("interest", "Cash interest paid (outflow)", "amount", "cash_interest"),
    ("fcf", "Free cash flow", "amount", "fcf"),
    ("total_debt", "Total debt", "amount", "total_debt"),
    ("cash", "Cash and cash equivalents", "amount", "cash_closing"),
    ("net_debt", "Net debt", "amount", "total_debt - cash_closing"),
)
OPERAND_LINEAGE = {"ebitda": ["ebitda"], "interest": ["cash_interest"], "fcf": ["fcf"], "total_debt": ["total_debt"],
                   "cash": ["cash_closing"], "net_debt": ["total_debt", "cash_closing"]}
RATIO_NAMES = (
    ("total_leverage", "Total leverage", "multiple"),
    ("net_leverage", "Net leverage", "multiple"),
    ("interest_coverage", "Interest coverage", "multiple"),
    ("fcf_to_debt", "Free cash flow to debt", "percent"),
)


BLOCKS = {
    "downside-stress": {"title": "Downside stress", "owner": "CP-2A", "kind": "dense", "producers": ["CP-2A"], "tabs": [["T2B.3", "Earnings and cash flow"], ["T2B.4", "Credit metrics"]]},
    "break-points": {"title": "Break points", "owner": "CP-2A", "kind": "dense", "producers": ["CP-2A"], "tabs": [["T2B.6", "Break-point register"], ["T2B.7", "First-break ranking"]]},
}
EVIDENCE_TABLES = ["T2B.1", "T2B.2", "T2B.5", "T2B.8", "cp1_references"]
LIMITATION_TABLES = ["T2B.9"]


GAP_SPELLING = {"missing": ("gap", "\u2205 G#"), "not_applicable": ("not_meaningful", "\u2205 G# n.m.")}


def fp05(facts, tables):
    """What the assigned FP05 blocks must show: each bound table's rows with every cell's display
    text. A cell is `known` with its text, or unsettled and spelled as `report_view.fact_spelling`
    spells it: missing -> state `gap`, text `∅ G#`; not_applicable -> state `not_meaningful`, text
    `∅ G# n.m.` (G# is the report-wide gap number, not literal here)."""
    by_id = {x["fact_id"]: x for x in facts}
    out = {"pathway": "distressed_restructuring", "blocks": {}}

    def cell(fact_id):
        x = by_id[fact_id]
        if x["status"] == "known":
            return {"fact_id": fact_id, "field": x["field"], "shown": x["shown"], "state": "known"}
        state, text = GAP_SPELLING[x["status"]]
        return {"fact_id": fact_id, "field": x["field"], "shown": text, "state": state}

    for block_id, block in BLOCKS.items():
        tabs = []
        for table_id, label in block["tabs"]:
            table = next(t for t in tables if t["table_id"] == table_id)
            rows = [{"row_id": r["row_id"], "label": r["label"], "cells": [cell(f) for f in r["fact_ids"]]} for r in table["rows"]]
            tabs.append({"table_id": table_id, "label": label, "rows": rows})
        out["blocks"][block_id] = {"title": block["title"], "owner": block["owner"], "kind": block["kind"], "state": "populated", "tabs": tabs}
    out["other_blocks"] = "every other distressed_restructuring block keeps its idle wording (No module produces this block yet / unrun producers); CP-2A fills none of them"
    out["evidence_rail_tables"] = EVIDENCE_TABLES
    out["limitations_rail_tables"] = LIMITATION_TABLES
    return out


LIN_RATIO = {"total_leverage": ["total_debt", "ebitda"], "net_leverage": ["total_debt", "cash_closing", "ebitda"],
             "interest_coverage": ["ebitda", "cash_interest"]}
BREAK_DECLINE = {"fcf": ["fcf", "ebitda"], "coverage": ["ebitda", "cash_interest"], "total_leverage": ["total_debt", "ebitda"],
                 "net_leverage": ["total_debt", "cash_closing", "ebitda"]}
BREAK_AT = {"fcf": ["ebitda", "fcf"], "coverage": ["cash_interest"], "total_leverage": ["total_debt"], "net_leverage": ["total_debt", "cash_closing"]}
LIQUIDITY = "Liquidity is not tested: stressed free cash flow is not set against the cash balance or any undrawn facility and no liquidity runway is computed; the liquidity runway belongs to CP-2D."
COVENANT = "No covenant test is applied: the watch levels are not covenant tests; covenant compliance belongs to CP-4."
MATURITY = "No maturity or refinancing wall is stressed: debt maturities and refinancing risk belong to CP-2D and CP-3C."
BREAK_AT_BASE = ("Break points hold cash interest at the base period level (no interest increase). The break at which EBITDA no longer covers cash interest "
                 "compares same-period flows but is gated like a ratio: it is Not calculable wherever CP-1 has no twelve-month basis for the base period.")
BREAK_AT_BASE_NA = ("Break points hold cash interest at the base period level (no interest increase). The break at which EBITDA no longer covers cash interest "
                    "compares same-period flows but is gated like a ratio: it is Not calculable wherever CP-1 has no twelve-month basis for the base period, "
                    "and it is not calculated on a single-quarter base.")
NOT_CALC_CROSSING = ("A metric that is not calculable under a scenario shows Not calculable against every break point, "
                     "including a break whose required decline is below that scenario's decline.")


def lin_fcf(k):
    """The CP-1 facts a stressed free cash flow derives from: base FCF and EBITDA, plus cash interest only when the interest term is applied."""
    return ["fcf", "ebitda"] + (["cash_interest"] if k != 0 else [])


def lin_ratio(rn, k):
    return lin_fcf(k) + ["total_debt"] if rn == "fcf_to_debt" else LIN_RATIO[rn]


def prose_texts(sub):
    """Every submission prose field in reading order: scenarios, thresholds, assessment, gaps."""
    for sc in sub["scenarios"]:
        yield sc["rationale"]
    for t in sub["thresholds"]:
        yield t["rationale"]
    yield sub["assessment"]["rationale"]
    for g in sub["gaps"]:
        yield from (g["gap"], g["why_it_matters"], g["affected_analysis"], g["action"])


def round_trip(base, row):
    """M1: feeding the exact (rational) required decline back into the stress recipe gives exactly the level."""
    sf = Fraction(row["s_fraction"])
    e, i, f, d, c = (None if base[x] is None else Fraction(base[x]) for x in ("ebitda", "interest", "fcf", "total_debt", "cash"))
    e2 = e * (1 - sf)
    kind, lvl = row["kind"], Fraction(row["level"])
    if kind == "fcf":
        got = f - e * sf
    elif kind == "coverage":
        got = e2 / i
    elif kind == "total_leverage":
        got = d / e2
    else:
        got = (d - c) / e2
    assert got == lvl, (row["bid"], got, lvl)
    return True


def build_case(name):
    spec = CASES[name]
    sub = SUBMISSION[spec["submission"]]
    base, period = spec["base"], spec["period"]
    gate, gate_reason = spec["gate"], spec["gate_reason"]
    gate_na = spec.get("gate_na", False)
    cp1 = spec["cp1"]
    if not gate:  # P1-W item 2 is per ratio; this builder carries one gate flag per base, so a mixed base is refused
        _known = {cp1[m]["status"] == "known" for m in RATIO_REPORTED.values()}
        assert _known == {gate_na}, (name, "mixed CP-1 ratio statuses on a quarter base need the per-ratio gate")
    facts, rows_by_table, claims, own_limits = [], {t: [] for t in TABLES}, [], []

    def fact(table, row, field, label, **kw):
        rec = {"fact_id": f"{table}.{row}.{field}", "table_id": table, "row_id": row, "field": field, "label": label}
        rec.update(kw)
        facts.append(rec)
        return rec

    def num(table, row, field, label, value, unit_class, formula, value_class="calculated", decimals=None, derives=()):
        unit = {"amount": "MILLIONS", "multiple": "MULTIPLE", "percent": "PERCENT"}[unit_class]
        dec = 2 if unit_class == "amount" else None
        extra = {"currency": "USD", "scale": "1000000"} if unit_class == "amount" else {}
        derives = list(derives) if value_class == "calculated" else []
        for metric in derives:  # a known fact never derives from a CP-1 fact that is not known (M2)
            assert cp1[metric]["status"] == "known", (name, table, row, field, metric)
        return fact(table, row, field, label, status="known", unit=unit, period=period, amount_exact=norm(value), shown=show(value, unit_class, dec),
                    **extra, decimals=dec, value_class=value_class, formula=formula, calculation_id=f"calc:{table}.{row}.{field}" if value_class == "calculated" else None,
                    derives_from=derives)

    def gap(table, row, field, label, unit_class, reason, status="missing"):
        return fact(table, row, field, label, status=status, unit={"amount": "MILLIONS", "multiple": "MULTIPLE", "percent": "PERCENT"}[unit_class],
                    period=period, amount_exact=None, shown=None, limitation=reason)

    def text(table, row, field, label, value, value_class=None):
        return fact(table, row, field, label, status="known", text=value, shown=value, value_class=value_class)

    def reg(table, row_id, label, fields):
        rows_by_table[table].append({"row_id": row_id, "label": label, "fact_ids": [f"{table}.{row_id}.{f}" for f in fields]})

    scenarios = sub["scenarios"]
    thresholds = sub["thresholds"]
    for n, sc in enumerate(scenarios, 1):
        sc["row"] = f"s{n:02d}"
        sc["s"], sc["k"] = D(sc["ebitda_decline"]), D(sc["interest_increase"])

    # T2B.1: the rationale is a claim T2B.1.sNN (references resolved through cp1_references), not a stored text
    for sc in scenarios:
        r = sc["row"]
        text("T2B.1", r, "name", "Scenario", sc["name"], "analyst_judgment")
        num("T2B.1", r, "ebitda_decline", "EBITDA decline", sc["s"], "percent", "analyst input", "analyst_judgment")
        num("T2B.1", r, "interest_increase", "Cash interest increase", sc["k"], "percent", "analyst input", "analyst_judgment")
        text("T2B.1", r, "category", "Category", sc["category"])
        figs_used = re.findall(r"FIG:([a-z_]+)", sc["rationale"])
        text("T2B.1", r, "basis", "Basis", "; ".join(f"CP-1 {FIGS[x]['cp1_label']}" for x in figs_used) or "No located evidence")
        reg("T2B.1", r, sc["name"], ["name", "ebitda_decline", "interest_increase", "category", "basis"])
    # T2B.2
    e, i, f, d, c = (base[x] for x in ("ebitda", "interest", "fcf", "total_debt", "cash"))
    nd = None if (d is None or c is None) else d - c
    bvals = {"ebitda": e, "interest": i, "fcf": f, "total_debt": d, "cash": c, "net_debt": nd}
    for key, label, uc, src in OPERANDS:
        r = key
        if bvals[key] is None:
            gap("T2B.2", r, "value", label, uc, f"Not calculable: base {WORDS.get(key, 'net debt')} is missing in CP-1 ({period})" if key != "net_debt" else "Not calculable: debt or cash is missing")
        else:
            num("T2B.2", r, "value", label, bvals[key], uc, f"CP-1 {src}" + (", sign reversed" if key == "interest" else ""), derives=OPERAND_LINEAGE[key])
        text("T2B.2", r, "source", "Source", f"CP-1 T4.10 {src} · {period}")
        reg("T2B.2", r, label, ["value", "source"])
    # T2B.3 / T2B.4 including the base control s00
    runs = [dict(row="s00", name="Base (no stress)", s=D(0), k=D(0))] + [dict(row=sc["row"], name=sc["name"], s=sc["s"], k=sc["k"]) for sc in scenarios]
    results = {}
    for sc in runs:
        res = stress(base, sc["s"], sc["k"], gate, gate_reason, gate_na)
        results[sc["row"]] = res
        r, k = sc["row"], sc["k"]
        for fld, label, uc, key in (("ebitda", "Stressed EBITDA", "amount", "ebitda"), ("interest", "Stressed cash interest", "amount", "interest"), ("fcf", "Stressed free cash flow", "amount", "fcf")):
            if res[key] is None:
                gap("T2B.3", r, fld, label, uc, res["why"].get(key, f"Not calculable: base {WORDS[key]} is missing"))
            else:
                formula = {"ebitda": "EBITDA x (1 - decline)", "interest": "Cash interest x (1 + increase)", "fcf": "Free cash flow - EBITDA x decline - cash interest x increase"}[key]
                derives = {"ebitda": ["ebitda"], "interest": ["cash_interest"], "fcf": lin_fcf(k)}[key]
                num("T2B.3", r, fld, label, res[key], uc, formula, derives=derives)
        for fld, label, uc in (("ebitda_change", "EBITDA change", "amount"), ("fcf_change", "Free cash flow change", "amount")):
            key, bkey = ("ebitda", e) if fld == "ebitda_change" else ("fcf", f)
            if res[key] is None or bkey is None:
                gap("T2B.3", r, fld, label, uc, "Not calculable: the stressed or the base figure is missing")
            else:
                num("T2B.3", r, fld, label, res[key] - bkey, uc, "Stressed minus base", derives=["ebitda"] if key == "ebitda" else lin_fcf(k))
        reg("T2B.3", r, sc["name"], ["ebitda", "interest", "fcf", "ebitda_change", "fcf_change"])
        for rn, label, uc in RATIO_NAMES:
            formula = {"total_leverage": "Total debt / stressed EBITDA", "net_leverage": "(Total debt - cash) / stressed EBITDA",
                       "interest_coverage": "Stressed EBITDA / stressed cash interest", "fcf_to_debt": "Stressed free cash flow / total debt"}[rn]
            if res[rn] is None:
                gap("T2B.4", r, rn, label, uc, res["why"][rn], status="not_applicable" if rn in res["na"] else "missing")
            else:
                num("T2B.4", r, rn, label, res[rn], uc, formula, derives=lin_ratio(rn, k))
        reg("T2B.4", r, sc["name"], [x[0] for x in RATIO_NAMES])
    # T2B.5 reconciliation: the s00 control against CP-1's reported ratio, which sits in cp1_references (L7)
    reconciliation_refs = {}
    for rn, label, uc in RATIO_NAMES:
        r = rn
        recomputed = results["s00"][rn]
        reported = cp1[RATIO_REPORTED[rn]]
        assert (recomputed is None) == (reported["status"] != "known" or gate_na), (name, rn)
        reconciliation_refs[rn] = RATIO_REPORTED[rn]
        if recomputed is None and rn in results["s00"]["na"]:
            # P1-W: CP-1's ratio copy stays known in cp1_references; CP-2A's recomputation is not meaningful on a quarter base
            gap("T2B.5", r, "recomputed", "Recomputed from CP-2A base operands", uc, P1W_REASON, status="not_applicable")
            gap("T2B.5", r, "difference", "Difference", uc, P1W_COMPARE, status="not_applicable")
            text("T2B.5", r, "result", "Result", "Not compared")
        elif recomputed is None:
            gap("T2B.5", r, "recomputed", "Recomputed from CP-2A base operands", uc, results["s00"]["why"][rn])
            gap("T2B.5", r, "difference", "Difference", uc, "Not compared: one side is not calculable")
            text("T2B.5", r, "result", "Result", "Not compared")
        else:
            cp1_value = D(reported["amount_exact"])
            num("T2B.5", r, "recomputed", "Recomputed from CP-2A base operands", recomputed, uc, "Base operands, no stress", derives=lin_ratio(rn, D(0)))
            num("T2B.5", r, "difference", "Difference", recomputed - cp1_value, uc,
                f"Recomputed minus CP-1 reported (cp1_references {RATIO_REPORTED[rn]})", derives=[*lin_ratio(rn, D(0)), RATIO_REPORTED[rn]])
            text("T2B.5", r, "result", "Result", "Reconciled" if recomputed == cp1_value else "Differs")
        reg("T2B.5", r, label, ["recomputed", "difference", "result"])
    # T2B.6 break points
    brk = breaks_for(base, thresholds, gate, gate_reason, gate_na)
    for n, row in enumerate(brk):
        row["bid"] = f"b{n + 1:02d}"
    for row in brk:
        r, label = row["bid"], row["test"]
        text("T2B.6", r, "origin", "Origin", row["origin"], "analyst_judgment" if row["origin"] == "Analyst assumption" else None)
        text("T2B.6", r, "test", "Test", label)
        if row["kind"] == "fcf":
            num("T2B.6", r, "level", "Level", row["level"], "amount", "Definition: free cash flow of zero", None)
        elif row["origin"] == "Definition":
            num("T2B.6", r, "level", "Level", row["level"], "multiple", "Definition: EBITDA equal to cash interest", None)
        else:
            num("T2B.6", r, "level", "Level", row["level"], "multiple", "analyst input", "analyst_judgment")
        row["level_class"] = None if row["origin"] == "Definition" else "analyst_judgment"  # T2B.8 copies take the T2B.6 level's own value_class (L2)
        if "s" in row and row["outcome"] != "Not reached by a decline of up to 100%":
            formula = {"fcf": "Free cash flow / EBITDA", "coverage": "(EBITDA - level x cash interest) / EBITDA",
                       "total_leverage": "(level x EBITDA - total debt) / (level x EBITDA)", "net_leverage": "(level x EBITDA - net debt) / (level x EBITDA)"}[row["kind"]]
            num("T2B.6", r, "required_decline", "Required EBITDA decline", row["s"], "percent", formula, derives=BREAK_DECLINE[row["kind"]])
            num("T2B.6", r, "ebitda_at_break", "EBITDA at the break", row["at_break"], "amount", "EBITDA x (1 - required decline)", derives=BREAK_AT[row["kind"]])
            row["round_trip_exact"] = round_trip(base, row)
        elif row["outcome"].startswith("Not reached"):
            why = row.get("reason", "No decline up to 100% reaches the level")
            gap("T2B.6", r, "required_decline", "Required EBITDA decline", "percent", why, status="not_applicable")
            gap("T2B.6", r, "ebitda_at_break", "EBITDA at the break", "amount", why, status="not_applicable")
        else:
            st = "not_applicable" if row.get("na") else "missing"
            gap("T2B.6", r, "required_decline", "Required EBITDA decline", "percent", row["reason"], status=st)
            gap("T2B.6", r, "ebitda_at_break", "EBITDA at the break", "amount", row["reason"], status=st)
        text("T2B.6", r, "outcome", "Outcome", row["outcome"])
        reg("T2B.6", r, label, ["origin", "test", "level", "required_decline", "ebitda_at_break", "outcome"])
    # T2B.7 ranking
    ranked = rank(brk)
    for n, row in enumerate(ranked, 1):
        r = f"r{n:02d}"
        text("T2B.7", r, "break_point", "Break point", row["test"])
        num("T2B.7", r, "required_decline", "Required EBITDA decline", row["s"], "percent", f"= T2B.6.{row['bid']}.required_decline", derives=BREAK_DECLINE[row["kind"]])
        reg("T2B.7", r, f"Rank {n}", ["break_point", "required_decline"])
        row["rank_row"] = r
    # T2B.8 scenario against break points
    unreached_crossing = False
    for sc in scenarios:
        for row in brk:
            r = f"{sc['row']}-{row['bid']}"
            v, hit = crossing(row, results[sc["row"]])
            metric_uc = "amount" if row["kind"] == "fcf" else "multiple"
            if row.get("na"):  # P1-W: a ratio break on a quarter base has no meaningful stressed value
                gap("T2B.8", r, "stressed_value", "Stressed value", metric_uc, P1W_REASON, status="not_applicable")
                v, hit = None, P1W_OUTCOME
            elif v is None:
                gap("T2B.8", r, "stressed_value", "Stressed value", metric_uc, results[sc["row"]]["why"].get({"fcf": "fcf", "coverage": "interest_coverage"}.get(row["kind"], row["kind"]), "Not calculable"))
                unreached_crossing = unreached_crossing or "s" in row
            else:
                derives = lin_fcf(sc["k"]) if row["kind"] == "fcf" else lin_ratio("interest_coverage" if row["kind"] == "coverage" else row["kind"], sc["k"])
                num("T2B.8", r, "stressed_value", "Stressed value", v, metric_uc, "From T2B.3 or T2B.4", derives=derives)
            lvl_uc = "amount" if row["kind"] == "fcf" else "multiple"
            num("T2B.8", r, "level", "Level", row["level"], lvl_uc, "From T2B.6", row["level_class"])
            verdict = hit if isinstance(hit, str) else "Not calculable" if hit is None else ("Crossed" if hit else "Not crossed")
            text("T2B.8", r, "result", "Result", verdict)
            row.setdefault("cross", {})[sc["row"]] = verdict
            reg("T2B.8", r, f"{sc['name']} · {row['test']}", ["stressed_value", "level", "result"])
    # own limitations, gaps ledger
    own_limits.append("Scenario shock sizes are analyst assumptions without a source citation.")
    if thresholds:
        own_limits.append("Break-point watch levels are analyst assumptions, not covenants; no covenant owner is an input.")
    own_limits.append("Stress is applied to the base period's flows with debt and cash held at their reported closing balances; no forward cash build, refinancing or mitigating action is modelled.")
    own_limits.append("Cash taxes, capital expenditure and working capital are held at the base period; no tax shield is taken.")
    own_limits.extend((LIQUIDITY, COVENANT, MATURITY, BREAK_AT_BASE_NA if gate_na else BREAK_AT_BASE))
    if unreached_crossing:
        own_limits.append(NOT_CALC_CROSSING)
    for key, value in base.items():
        if value is None:
            own_limits.append(f"Base {WORDS[key]} is not available in CP-1 for {period}: every figure that needs it is Not calculable.")
    if gate_na:
        own_limits.append(P1W_LINE)
    elif not gate:
        own_limits.append(f"Twelve-month ratios are not calculable on the base period {period}: {gate_reason}")
    for n, g in enumerate(sub["gaps"], 1):
        r = f"g{n:02d}"
        text("T2B.9", r, "id", "Gap id", f"CP-2A-GAP-{n:03d}")
        text("T2B.9", r, "gap", "Gap", g["gap"], "analyst_judgment")
        text("T2B.9", r, "why_it_matters", "Why it matters", g["why_it_matters"], "analyst_judgment")
        text("T2B.9", r, "affected_analysis", "Affected analysis", g["affected_analysis"], "analyst_judgment")
        text("T2B.9", r, "severity", "Severity", g["severity"])
        text("T2B.9", r, "action", "Action", g["action"], "analyst_judgment")
        reg("T2B.9", r, f"Gap {n}", ["id", "gap", "why_it_matters", "affected_analysis", "severity", "action"])
        own_limits.append(f"Gap ({g['severity']}): {g['gap']}")
    if not sub["gaps"]:
        for fld in ("id", "gap", "why_it_matters", "affected_analysis", "severity", "action"):
            fact("T2B.9", "none", fld, fld, status="not_applicable", text=None, shown=None, limitation="None in the CP-2A submission (gaps ledger)")
        reg("T2B.9", "none", "None", ["id", "gap", "why_it_matters", "affected_analysis", "severity", "action"])

    # cp1_references (M2): the CP-1 facts the prose names, in reading order, then the reported ratios T2B.5 compares
    named = []
    for t in prose_texts(sub):
        named += re.findall(r"FIG:([a-z_]+)", t)
    for fig_name in named:
        assert cp1[FIGS[fig_name]["metric"]]["status"] == "known", (name, fig_name)
    ref_names = list(dict.fromkeys([*named, *RATIO_REPORTED.values()]))
    ref_rows = []
    for n, fig_name in enumerate(ref_names, 1):
        src = cp1[FIGS[fig_name]["metric"]]
        known = src["status"] == "known"
        ref_rows.append({
            "row_id": f"ref{n:02d}", "figure": fig_name, "label": f"{src['label']} · {src['period']}", "cp1_label": src["label"], "period": src["period"],
            "status": src["status"], "unit": FIGS[fig_name]["unit_token"], "shown": FIGS[fig_name]["spelled"] if known else None,
            "cell_text": src["cell_text"], "value_class": src["value_class"], "amount_exact": src["amount_exact"], "limitation": src["limitation"],
            "fact_id": "bound at run time: the unique T4.10 fact with label cp1_label (manifest.json fact_selection_rule); the module carries the CP-1 fact verbatim under this fact_id",
        })
    cp1_references = {"table_id": "cp1_references", "title": "CP-1 facts referenced in CP-2A text", "row_header": "CP-1 fact", "rows": ref_rows}

    # claims: scenario rationales (analyst text, references resolved through cp1_references), Python templates over
    # CP-2A's own facts, the analyst's assessment; chips for unsettled facts
    by_id = {x["fact_id"]: x for x in facts}

    def ref(fid, token):
        x = by_id[fid]
        return "{" + fid + "|" + token + "}" if x["status"] == "known" else "[" + fid + "]"

    def claim(cid, text_, limitation, refs=()):
        entry = {"claim_id": cid, "text": text_, "limitation": limitation, "citations": [], "cp1_references": list(refs)}
        if refs:
            entry["text_rendered"] = spell_figs(text_)
        claim_list.append(entry)

    claim_list = []
    for sc in scenarios:
        claim(f"T2B.1.{sc['row']}", sc["rationale"], sc["limitation"], re.findall(r"FIG:([a-z_]+)", sc["rationale"]))
    for sc in scenarios:
        r = sc["row"]
        text_ = (f"Under the {sc['name']} scenario, stressed EBITDA is {ref(f'T2B.3.{r}.ebitda', 'US$ m')} against {ref('T2B.3.s00.ebitda', 'US$ m')} at base, "
                 f"free cash flow is {ref(f'T2B.3.{r}.fcf', 'US$ m')}, net leverage is {ref(f'T2B.4.{r}.net_leverage', 'x')} "
                 f"and interest coverage is {ref(f'T2B.4.{r}.interest_coverage', 'x')}.")
        claim(f"T2B.4.{r}", text_, None)
    if ranked:
        first = ranked[0]
        claim("T2B.7.first", f"The first test reached is {first['test']} at an EBITDA decline of {ref('T2B.7.r01.required_decline', '%')}.", None)
    else:
        own_limits.append("No break point is calculable, so no first break is ranked.")
    a = sub["assessment"]
    claim("T2B.1.assessment", a["rationale"], a["limitation"], re.findall(r"FIG:([a-z_]+)", a["rationale"]))

    module_tables = []
    for t, title in TABLES.items():
        module_tables.append({"table_id": t, "title": title, "rows": rows_by_table[t]})
    return {
        "base_period": period, "base_operands": {k: (None if v is None else norm(v)) for k, v in bvals.items()},
        "cp1_inputs": cp1, "cp1_references": cp1_references, "reconciliation_refs": reconciliation_refs,
        "facts": facts, "tables": module_tables, "claims": claim_list, "own_limitations": own_limits,
        "stress": {r: {k: (norm(v) if isinstance(v, D) else v) for k, v in res.items() if k not in ("why", "na")} | {"not_calculable": res["why"]} for r, res in results.items()},
        "break_points": [
            {"break_id": b["bid"], "origin": b["origin"], "test": b["test"], "outcome": b["outcome"],
             "required_decline": None if "s" not in b else norm(b["s"]), "required_decline_fraction": b.get("s_fraction"),
             "required_decline_shown": None if "s" not in b else pct(b["s"]),
             "ebitda_at_break": None if b.get("at_break") is None else norm(b["at_break"]), "crossings": b.get("cross", {}),
             "round_trip_exact_in_fraction": b.get("round_trip_exact", False)}
            for b in brk
        ],
        "first_break": None if not ranked else {"break_id": ranked[0]["bid"], "test": ranked[0]["test"], "required_decline_shown": pct(ranked[0]["s"])},
        "ranking": [{"rank": n, "break_id": b["bid"], "test": b["test"], "required_decline_shown": pct(b["s"])} for n, b in enumerate(ranked, 1)],
        "module_status": "restricted" if spec["execution"] == "run" else "composer_only",
        "FP05": fp05(facts, module_tables),
    }


# --- 6. manifest, submissions, expected -------------------------------------------------------


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


# --- 6b. refusals, readiness, run-time bindings (M4, M5) ------------------------------------------

CP_PATTERN = r"^(0|1|0\.\d{1,4}|1\.0{1,4})$"
LEVEL_PATTERN = r"^[0-9]{1,6}(\.[0-9]{1,4})?$"
PATTERN_MSG = {"decline": f"String should match pattern '{CP_PATTERN}'", "level": f"String should match pattern '{LEVEL_PATTERN}'"}
HIGH_ISSUE = "assessment.confidence: High is not allowed: shock sizes and watch levels are uncited analyst assumptions"
NAME_RULE = "no digit, brace or bracket is allowed in a name"


def public(sub):
    """A submission as the analyst sends it: no builder-internal key (row, s, k, bid)."""
    out = deepcopy(sub)
    for sc in out["scenarios"]:
        for key in ("row", "s", "k"):
            sc.pop(key, None)
    for t in out["thresholds"]:
        t.pop("bid", None)
    return out


def refusals():
    """One literal invalid payload per refusal class of the lease, with the exact issues the core must produce.

    `shape` issues are Pydantic messages in `readiness.shape_issues` form (`<dotted.path>: <message>`, probed on a
    scratch model mirroring the lease schema, pydantic 2.14.1); they are returned alone (no content check runs on
    a payload that does not parse). `content` issues are `<path>: <issue>` with the path in bracket form; prose
    issues are `prose.issues` / `business_context.prohibited_issues` strings (probed against the real CP-1 facts),
    the rest are this oracle's frozen wording. `{{FACT_ID:name}}` is the CP-1 fact id bound at run time."""
    pos = public(SUBMISSION["positive"])

    def mut(fn):
        d = deepcopy(pos)
        fn(d)
        return d

    def set_(path, value):
        def apply(d):
            node = d
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = value
        return apply

    out = []

    def add(rid, klass, mutation, payload, issues, kind, **extra):
        entry = {"id": rid, "class": klass, "mutation": mutation, "issue_kind": kind, "expected_issues": issues}
        entry.update(extra)
        entry["payload"] = payload
        out.append(entry)

    for rid, klass, mutation, value, where in (
        ("r01", "decline above one", "scenarios[0].ebitda_decline = '1.50'", "1.50", ("scenarios", 0, "ebitda_decline")),
        ("r02", "decline negative", "scenarios[0].ebitda_decline = '-0.10'", "-0.10", ("scenarios", 0, "ebitda_decline")),
        ("r03", "decline with more than four places", "scenarios[0].ebitda_decline = '0.12345'", "0.12345", ("scenarios", 0, "ebitda_decline")),
        ("r04", "decline not a decimal string", "scenarios[0].ebitda_decline = 'twenty percent'", "twenty percent", ("scenarios", 0, "ebitda_decline")),
        ("r05", "interest increase above one", "scenarios[2].interest_increase = '1.50'", "1.50", ("scenarios", 2, "interest_increase")),
    ):
        add(rid, klass, mutation, mut(set_(where, value)), [f"{'.'.join(map(str, where))}: {PATTERN_MSG['decline']}"], "shape")
    add("r06", "no scenario", "scenarios = []", mut(set_(("scenarios",), [])), ["scenarios: Tuple should have at least 1 item after validation, not 0"], "shape")
    add("r07", "more than four scenarios", "a fifth scenario (copy of the first) appended",
        mut(lambda d: d["scenarios"].append(deepcopy(d["scenarios"][0]))), ["scenarios: Tuple should have at most 4 items after validation, not 5"], "shape")
    add("r08", "watch level not a decimal string", "thresholds[0].level = 'two point five'", mut(set_(("thresholds", 0, "level"), "two point five")),
        [f"thresholds.0.level: {PATTERN_MSG['level']}"], "shape")
    add("r09", "watch level negative", "thresholds[0].level = '-2'", mut(set_(("thresholds", 0, "level"), "-2")), [f"thresholds.0.level: {PATTERN_MSG['level']}"], "shape")
    add("r10", "unknown threshold metric", "thresholds[0].metric = 'fcf_to_debt'", mut(set_(("thresholds", 0, "metric"), "fcf_to_debt")),
        ["thresholds.0.metric: Input should be 'total_leverage', 'net_leverage' or 'interest_coverage'"], "shape")
    add("r11", "confidence outside the enumeration", "assessment.confidence = 'Very High'", mut(set_(("assessment", "confidence"), "Very High")),
        ["assessment.confidence: Input should be 'High', 'Medium', 'Low' or 'Insufficient Information'"], "shape")
    add("r12", "required field absent", "assessment.limitation removed", mut(lambda d: d["assessment"].pop("limitation")), ["assessment.limitation: Field required"], "shape")
    add("r13", "unknown field", "top-level key 'extra' added", mut(lambda d: d.update(extra=1)), ["extra: Extra inputs are not permitted"], "shape")
    out.append({"id": "r14", "class": "not JSON", "mutation": "payload text '{not json'", "issue_kind": "shape",
                "expected_issues": ["(root): Invalid JSON: key must be a string at line 1 column 2"], "payload": None, "payload_text": "{not json"})
    # content issues
    add("v01", "base period not offered by the view", "base_period = 'LTM Q4 24: 2024-01-01 to 2024-12-31'", mut(set_(("base_period",), "LTM Q4 24: 2024-01-01 to 2024-12-31")),
        ["base_period: not an offered period: LTM Q4 24: 2024-01-01 to 2024-12-31"], "content")
    add("v02", "base EBITDA missing or not positive", "positive payload; composer run on the positive CP-1 facts with the base EBITDA fact set to status missing",
        deepcopy(pos), [f"base_period: base EBITDA is missing or not positive for {LTM_PERIOD}"], "content", composer_only=True,
        note="no frozen period has a missing or non-positive EBITDA, so this class is exercised on the composer only (as interest_undisclosed)")
    add("v03", "duplicate scenario name", "scenarios[1].name = scenarios[0].name", mut(set_(("scenarios", 1, "name"), "Moderate downturn")),
        ["scenarios[1].name: duplicate scenario name: Moderate downturn"], "content")
    add("v04", "two thresholds for one metric", "thresholds[1].metric = 'total_leverage' (the first is total_leverage)", mut(set_(("thresholds", 1, "metric"), "total_leverage")),
        ["thresholds[1].metric: more than one threshold for total_leverage"], "content")
    add("v05", "watch level not positive", "thresholds[0].level = '0'", mut(set_(("thresholds", 0, "level"), "0")),
        ["thresholds[0].level: must be greater than zero"], "content")
    add("v06", "digit in a scenario name", "scenarios[0].name = 'Moderate downturn 2'", mut(set_(("scenarios", 0, "name"), "Moderate downturn 2")),
        [f"scenarios[0].name: {NAME_RULE}"], "content")
    add("v07", "brace in a threshold label", "thresholds[0].label = 'Total leverage {watch} level'", mut(set_(("thresholds", 0, "label"), "Total leverage {watch} level")),
        [f"thresholds[0].label: {NAME_RULE}"], "content")
    add("v08", "bare figure in prose", "scenarios[2].rationale states '20 percent'",
        mut(set_(("scenarios", 2, "rationale"), "The severe fall in volumes coincides with a 20 percent rise in the rate paid on the term loan.")),
        ["scenarios[2].rationale: Bare figure: 20"], "content")
    add("v09", "unresolved reference", "scenarios[2].rationale names {T9.9.value|x}",
        mut(set_(("scenarios", 2, "rationale"), "The severe fall in volumes coincides with a rate rise of {T9.9.value|x} on the term loan.")),
        ["scenarios[2].rationale: Unresolved reference: T9.9.value"], "content")
    add("v10", "unit-mismatched reference", "scenarios[0].rationale: the ebitda_ltm token unit 'US$ m' replaced by 'x'",
        mut(set_(("scenarios", 0, "rationale"), pos["scenarios"][0]["rationale"].replace("{{FIG:ebitda_ltm|US$ m}}", "{{FIG:ebitda_ltm|x}}"))),
        ["scenarios[0].rationale: Unit x differs from the fact's unit US$ m: {{FACT_ID:ebitda_ltm}}"], "content")
    add("v11", "figure placeholder left unreplaced", "the payload is sent with every {{FIG:..}} still in place",
        deepcopy(pos), ["scenarios[0].rationale: Malformed run text: unbalanced or empty reference",
                        "scenarios[1].rationale: Malformed run text: unbalanced or empty reference",
                        "assessment.rationale: Malformed run text: unbalanced or empty reference"], "content", bind_placeholders=False)
    add("v12", "empty prose", "scenarios[3].rationale = ''", mut(set_(("scenarios", 3, "rationale"), "")), ["scenarios[3].rationale: empty text"], "content")
    add("v13", "confidence High", "assessment.confidence = 'High'", mut(set_(("assessment", "confidence"), "High")), [HIGH_ISSUE], "content")
    add("v14", "peer ranking", "scenarios[3].rationale adds 'versus peers'",
        mut(set_(("scenarios", 3, "rationale"), "A boundary case in which earnings fall to zero, weak versus peers.")),
        ['scenarios[3].rationale: prohibited conclusion (peer ranking): "versus peers"'], "content")
    add("v15", "instrument recommendation", "scenarios[3].rationale adds 'we recommend'",
        mut(set_(("scenarios", 3, "rationale"), "A boundary case in which earnings fall to zero, so we recommend caution.")),
        ['scenarios[3].rationale: prohibited conclusion (instrument recommendation): "we recommend"'], "content")
    add("v16", "recovery conclusion", "scenarios[3].rationale adds 'expected recovery'",
        mut(set_(("scenarios", 3, "rationale"), "A boundary case in which earnings fall to zero, with expected recovery unclear.")),
        ['scenarios[3].rationale: prohibited conclusion (recovery conclusion): "expected recovery"'], "content")
    v17_current = hashlib.sha256(b"cp2a-owner v17: a different CP-1 head").hexdigest()
    out.append({"id": "v17", "class": "stale or unbound inputs",
                "mutation": "the positive payload, validated against a literal Upstream whose current CP-1 Input differs from the attempt's bound CP-1 Input; validator only, no run",
                "issue_kind": "content", "composer_only": True,
                "expected_issues": [f"Stale input CP-1: bound restricted <12 hex of the attempt's bound CP-1 input sha256>, current restricted {v17_current[:12]}"],
                "payload": public(SUBMISSION["positive"]),
                "upstream_literal": {"bound": "the attempt's inputs, bound at run time (prepared-pack, CP-0 and CP-1 Input records, CP-1 status restricted)",
                                     "current": [{"input_id": "prepared-pack", "sha256": "<the bound prepared-pack Input, unchanged>"},
                                                 {"input_id": "CP-0", "sha256": "<the bound CP-0 Input, unchanged>", "status": "<the bound CP-0 status, unchanged>"},
                                                 {"input_id": "CP-1", "sha256": v17_current, "status": "restricted"}]},
                "note": "validate_downside(pack=<pack>, submission=<positive>, upstream=Upstream(bound=attempt.inputs, current=<the bound tuple with only the CP-1 Input replaced by the literal above>, cp1=<bound CP-1 facts>)) returns exactly this one issue; prepared-pack and CP-0 stay equal so only CP-1 is reported. "
                        "Run level: through G1, a CP-1 head change after begin refuses stale_binding at the next G1 call (owner_workflow.py:423-427); a direct Execution.submit_step caller gets ValueError('Ticket inputs have changed') (execution.py:768-769); neither consumes an attempt or journals a step",
                "issue_prefix": "Stale input CP-1: bound restricted "})
    return out


def blocked_case(by_id):
    return {
        "plan_order": ["CP-0", "CP-1", "CP-2A"],
        "attempt_0": {"payload": "r01", "result_status": "rejected", "limitations": by_id["r01"]["expected_issues"]},
        "attempt_1": {"payload": "v13", "repair_of": "attempt_0", "repair_issues": by_id["r01"]["expected_issues"], "result_status": "blocked",
                      "limitations": by_id["v13"]["expected_issues"]},
        "head": {"module_id": "CP-2A", "status": "blocked", "tables": 0, "facts": 0},
        "downstream": "CP-2G and CP-4C (required edge block) cannot begin on a blocked CP-2A head",
        "rule": "execution.settle: attempt 0 invalid -> status rejected; attempt 1 invalid -> status blocked; limitations are the bounded issues (20 lines of at most 600 characters)",
        "receipt": "verifies; both journaled invalid steps are replayed by the verifier and must reproduce their issues exactly",
        "must_not_appear": ["a CP-2A table or fact", "a third attempt"],
    }


CP1_DOWNSTREAM_REVIEW = {
    "inputs_sha256": "{{INPUTS_SHA256}}",
    "consumers": [{
        "entry": "CP-2A",
        "requirements": [
            {"requirement": "cash_flow_metrics", "status": "sufficient", "evidence_ids": ["{{EVID:kpi fcf, LTM Q4 25 basis}}"],
             "rationale": "Twelve-month levered free cash flow is available from the settled statements."},
            {"requirement": "liquidity_data", "status": "limited", "evidence_ids": ["{{EVID:kpi cash_closing, LTM Q4 25 basis}}"],
             "rationale": "Closing cash is available; there is no revolving facility.", "actions": ["Confirm undrawn committed facilities with the debt schedule."]},
        ],
        "gaps": [{"gap_ids": ["{{ALL narrative gap ids}}"], "relevance": "relevant", "evidence_ids": [],
                  "rationale": "Every retained source and context warning applies to the downside stress."}],
    }],
}
# Observed on the S1 positive promoted CP-1 head (probe, read only copy r2pos-orig, 2026-10-28; revision 2).
LTM_BASIS_ID = "model-basis:e6c56bc776bdd06c5151615c8e449eabd16878d4a2e027d5545a3216aab8efd2"
RUN_TIME_BINDINGS = {
    "figure_placeholders": "{{FIG:name|token}} -> {<CP-1 fact_id>|<token>} by fact_selection_rule; unreplaced it is malformed run text (refusal v11)",
    "fact_id_marker": "{{FACT_ID:name}} in an expected issue -> the CP-1 fact id bound to FIG name",
    "cp1_readiness": {
        "literal": "submissions.json cp1_downstream_review",
        "markers": {
            "{{INPUTS_SHA256}}": "the content hash of the step's prefilled DownstreamInputs",
            "{{EVID:kpi fcf, LTM Q4 25 basis}}": "the evidence_id of the one catalogue record matching evidence_predicate with key 'fcf'",
            "{{EVID:kpi cash_closing, LTM Q4 25 basis}}": "the same with key 'cash_closing'",
            "{{ALL narrative gap ids}}": "every narrative.gaps[*].gap_id, in catalogue order, as separate list elements",
        },
        "evidence_predicate": {
            "step": "the CP-1 narrative inputs (DownstreamInputs.narrative.inputs.catalogue)",
            "basis_record": {"kind": "basis", "record_json.label": "LTM Q4 25", "record_json.column_key": "LTM:fy-2025", "record_json.scope": "historical",
                             "must_match_exactly": 1, "basis_id_field": "record_json.basis_id",
                             "why_not_label_alone": "the label 'LTM Q4 25' matches two basis records: this one (column_key 'LTM:fy-2025', scope 'historical', the column the T4.10 'LTM Q4 25 (2025-01-01 to 2025-12-31)' facts read) and a trailing_four_quarters basis (column_key 'Q:q4-2025'), which no kpi record uses"},
            "kpi_record": {"kind": "kpi", "record_json.key": "<fcf | cash_closing>", "record_json.display_basis_id": "<basis_id of basis_record>", "must_match_exactly": 1},
        },
        "gap_predicate": {"all": "narrative.gaps[*].gap_id", "note": "every retained source and context warning applies to the stress (relevance 'relevant'); ids are cp1-gap:<sha256>"},
        "observed_on_probe_store": {
            "ltm_q4_25_display_basis_id": LTM_BASIS_ID,
            "basis_predicate_matches": 1, "basis_label_only_matches": 2,
            "fcf_evidence_id": "narrative-evidence:fff5b3c4a6fc5489d46b93b0c205877c4b056ba3cb37e6952314df62485b9663", "fcf_matches": 1,
            "cash_closing_evidence_id": "narrative-evidence:b22fc5fd4f518f053208ce285e5e09b9e60a1df9f6569263f6fea6d5895ec843", "cash_closing_matches": 1,
            "narrative_gaps": 1132, "distinct_gap_ids": 1132,
            "kpi_calculation_id_fcf": "canonical-kpi:5a3256748dcf5081aaa9c2e81f304336d76feb237a95cdbdb7a326cef21661ad (equals the calculation_id of the T4.10 'LTM Q4 25 (...) · fcf' fact)",
            "note": "ids are content hashes of the probe head; a run binds its own by the predicates, the observed values are evidence that the predicates are unique, not literals",
        },
        "validator_result": "validate_downstream_review: no issues; _assess_consumers row CP-2A status ready_with_limitations; an empty review is not_ready (review-precise-1 section 5, rerun in revision 2 on the literal with markers bound)",
    },
    "pack_hash": "PreparedPack.content_hash() of the run's pack", "inherited_limitations": "execution.py settle rule (see execution.inherited_limitations)",
    "ticket_and_call_ids": "structural only",
}


def main():
    built = {name: build_case(name) for name in CASES}
    refusal_list = refusals()
    by_id = {r["id"]: r for r in refusal_list}
    base_run = dict(FIN["run"])
    run_pos = dict(base_run, run_id="cp2a-owner-positive", pathway="distressed_restructuring", requested_modules=["CP-2A"])
    run_gap = dict(run_pos, run_id="cp2a-owner-gap")
    run_refused = dict(run_pos, run_id="cp2a-owner-refused")
    run_blocked = dict(run_pos, run_id="cp2a-owner-blocked")
    manifest = {
        "schema_version": "cp2a-owner-cases/2",
        "scope": "CP-2A (alias CP-2B) Downside pathway: CP-0 to CP-1 to CP-2A over the frozen financial pack, then the first consumer CP-2G (not yet leased)",
        "status": "DRAFT revision 4 (after review-precise-3 and the LEAD rulings of 2026-10-28); scoped re-review pending; not executed",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "financial_baseline": {
            "path": "cases/financial/manifest.json", "manifest_sha256": FIN_SHA,
            "sources": [{"source_id": s, "sha256": SRC[s]["sha256"], "reuse": "Every page text and locator stays byte-identical; read by reference, never edited"} for s in ("identity", "financial")],
            "oracle_pointers": ["q4_ltm_derived_source_units", "q4_ltm_metric_oracle", "quarter_observations", "negative_case"],
        },
        "no_new_source": "CP-2A reads only the settled CP-1 head; the financial pack already carries every operand, so no synthetic source is added",
        "cases": {
            "positive": {"run": run_pos, "pack": "identity + financial, as tests/test_financial_workflow.py make_pack()", "pack_limitation_financial": "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable.",
                         "base_period": LTM_PERIOD, "submission": "submissions.json positive", "expected": "expected.json positive", "execution": "closed run: CP-0, CP-1 (five stages, readiness = submissions.json cp1_downstream_review), CP-2A"},
            "gap": {"run": run_gap, "pack": "same pack as positive", "base_period": Q3_PERIOD, "submission": "submissions.json gap", "expected": "expected.json gap",
                    "execution": "closed run on the same CP-1 head construction; CP-1 has no twelve-month ratio for the quarter, so ratios are Not calculable, never 0"},
            "refused": {"run": run_refused, "pack": "financial source missing: no pages/hash, extraction blocked, limitation 'Quarterly financial statements were not supplied.' (cases/financial/manifest.json negative_case)",
                        "submission": "submissions.json refused.cp0_review (no CP-2A submission exists)", "expected": "expected.json refused",
                        "execution": "CP-0 only; CP-1 begin raises NotAuthorized; CP-2A is never begun"},
            "blocked": {"run": run_blocked, "pack": "same pack as positive", "submission": "submissions.json refusals r01 (attempt 0) then v13 (attempt 1)", "expected": "expected.json blocked",
                        "execution": "closed run: CP-0, CP-1 as positive, then CP-2A attempt 0 invalid (rejected) and attempt 1 invalid (blocked)"},
            "interest_undisclosed": {"run": None, "pack": None, "submission": "submissions.json interest_undisclosed", "expected": "expected.json interest_undisclosed",
                                     "execution": "composer only: the positive CP-1 module's facts with the base cash-interest fact and CP-1's coverage fact set to status missing (limitation '" + NOT_DISCLOSED + "'); no store, no run (a promoted head cannot be edited)"},
            "fixture_quarter_known": {"run": None, "pack": None, "base_period": Q4_PERIOD, "submission": "submissions.json fixture_quarter_known", "expected": "expected.json fixture_quarter_known",
                                      "execution": "composer only (round 6 P1-W item 7): the Q4 25 quarter base with CP-1 facts for the quarter flows (7.5, -1.25, 2.25), the closing balances (50, 20) and the four LTM Q4 25 ratios, all known; every ratio and ratio-based break is not_applicable on a single-quarter base; no store, no run"},
        },
        "refusal_cases": "submissions.json refusals (payloads) and expected.json refusals (exact issues); each is one journaled invalid step of CP-2A attempt 0 on the positive CP-1 head",
        "fact_selection_rule": {
            "table_id": "T4.10",
            "predicate": "fact.table_id == 'T4.10' and fact.label == '<column> · <metric>' where <column> is the base period column label and <metric> the T4.10 row's field_1 text; exactly one fact per (column, metric) (probe: 500 T4.10 facts, no duplicate label)",
            "ltm_column": LTM_COLUMN, "q3_column": Q3_COLUMN,
            "operand_metrics": {"ebitda": "ebitda", "interest": "cash_interest", "fcf": "fcf", "total_debt": "total_debt", "cash": "cash_closing"},
            "ratio_metrics": {"total_leverage": "total_leverage_reported", "net_leverage": "net_leverage_reported", "interest_coverage": "interest_coverage_reported", "fcf_to_debt": "fcf_to_debt"},
            "fy25_vs_ltm": "FY25 carries period 'FY25: 2025-01-01 to 2025-12-31' and label 'FY25 (...) · metric'; the LTM fact has period 'LTM Q4 25: ...' - the label and period strings differ, so the selection is unique",
            "sign": "CP-1 stores cash_interest as an outflow (negative, 'sign normalised'); CP-2A uses its magnitude as the interest operand",
            "probe": "S1 positive promoted CP-1 head (read only copy), 2026-10-28: LTM Q4 25 ebitda 30.0, cash_interest -5.00, fcf 9.00, total_debt 50.00, cash_closing 20.00, net_debt 30.00; Q3 25 ebitda 7.5, cash_interest -1.25, fcf 2.25, total_debt 48.75, cash_closing 18.75, net_debt 30.00; Q1-Q3 ratio facts status missing, limitation '" + Q3_GATE + "'",
            "observed_value_class_and_cell_text": "expected.json cases.<case>.cp1_inputs (value_class and cell_text as observed; amounts derived from the frozen pages and asserted against the financial oracle by the builder)",
            "fact_ids": "interface-fact:<sha256>; bound at run time, never literal",
        },
        "run_time_bindings": RUN_TIME_BINDINGS,
        "figures": FIGS,
    }
    refused_cp1_row = {
        "module_id": "CP-1", "readiness": "CONDITIONAL", "evidence_demand": "Located historical statements, facility terms, definitions and scope",
        "source_ids": ["identity"], "rationale": "Quarterly financial statements were not supplied.",
        "citations": [{"source_id": "identity", "source_sha256": SRC["identity"]["sha256"], "locator": "page:1", "quote": "Northbridge Synthetic Group is the issuer and consolidated group."}],
        "missing_source": "Quarterly financial statements", "limitations": ["Quarterly financial statements were not supplied."],
    }
    submissions = {
        "schema_version": "cp2a-owner-submissions/2",
        "note": "Literal analyst submissions for the downside_pathway step. {{FIG:name|token}} marks a CP-1 figure reference to be replaced mechanically by {<actual CP-1 fact_id>|<token>} after the CP-1 head is inspected (selection rule in manifest.json); unreplaced it is malformed run text and fails closed (refusal v11). Numbers in shock fields are analyst input, not computed values. CP-0 and the five CP-1 stages are reused unchanged from tests/test_financial_workflow.py except for the CP-0 consumer rows below and the CP-1 readiness stage, whose literal is cp1_downstream_review (markers bound by manifest.json run_time_bindings.cp1_readiness).",
        "figures": FIGS,
        "cp0_consumer_row_cp2a": {
            "module_id": "CP-2A", "readiness": "READY_WITH_LIMITATIONS",
            "evidence_demand": "Settled CP-1 EBITDA, cash interest, free cash flow, debt and cash for one base period",
            "source_ids": ["identity", "financial"],
            "rationale": "The downside pathway can run on settled CP-1 figures with inherited source and scope limitations.",
            "citations": [
                {"source_id": "identity", "source_sha256": SRC["identity"]["sha256"], "locator": "page:1", "quote": "Northbridge Synthetic Group is the issuer and consolidated group."},
                {"source_id": "financial", "source_sha256": SRC["financial"]["sha256"], "locator": "page:1", "quote": "Currency: USD; amounts in millions."},
            ],
            "missing_source": None,
            "limitations": ["Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."],
        },
        "cp1_downstream_review": CP1_DOWNSTREAM_REVIEW,
        "refused": {"cp0_consumer_row_cp1": refused_cp1_row,
                    "cp0_consumer_row_cp2a": {"module_id": "CP-2A", "readiness": "CONDITIONAL", "evidence_demand": "Settled CP-1 figures", "source_ids": ["identity"],
                                              "rationale": "Quarterly financial statements were not supplied.", "citations": [
                                                  {"source_id": "identity", "source_sha256": SRC["identity"]["sha256"], "locator": "page:1", "quote": "Northbridge Synthetic Group is the issuer and consolidated group."}],
                                              "missing_source": "Quarterly financial statements", "limitations": ["Quarterly financial statements were not supplied."]},
                    "gap_row": {"gap_id": "missing-financial", "kind": "source", "severity": "material", "description": "Quarterly financial statements were not supplied.",
                                "affected_modules": ["CP-1", "CP-2A"], "remediation": "Supply quarterly financial statements"}},
        "positive": {"downside_pathway": public(SUBMISSION["positive"])},
        "gap": {"downside_pathway": public(SUBMISSION["gap"])},
        "fixture_quarter_known": {"downside_pathway": public(SUBMISSION["fixture_quarter_known"])},
        "interest_undisclosed": {"downside_pathway": public(SUBMISSION["interest_undisclosed"])},
        "refusals": [{k: v for k, v in r.items() if k in ("id", "class", "mutation", "payload", "payload_text", "composer_only", "bind_placeholders", "upstream_literal", "note")} for r in refusal_list],
        "blocked": {"attempt_0": "refusals r01", "attempt_1": "refusals v13"},
    }
    expected = {
        "schema_version": "cp2a-owner-expected/2",
        "derivation": "Hand-transcribed recipes of work/lead/cp2a-owner-preparation/lease-draft.md applied to the frozen financial pages by cases/cp2a-owner/builder/build.py (stdlib only; deploy_vii never imported or run). Every value is the correctly rounded 38-significant-digit half-even quotient of an exact rational (Fraction), cross-checked against decimal.Context(prec=38, ROUND_HALF_EVEN); display spelling follows display.py (ROUND_HALF_UP; amount 2 dp by the fact's decimals, multiple 2 dp 'x', percent 1 dp '%', negative in parentheses). CP-1 constants are derived from the frozen pages and asserted against the financial oracle; only CP-1's value_class and cell text are observed strings.",
        "cell_notation": {"shown": "exact displayed text; an unsettled cell is spelled as report_view.fact_spelling spells it: missing -> state gap, text '∅ G#'; not_applicable -> state not_meaningful, text '∅ G# n.m.' (G# is the report-wide gap number, not literal)",
                          "amount_exact": "canonical exact decimal; null means unsettled",
                          "status": "known | missing | not_applicable", "fact_id": "table.row.field, assigned by Python",
                          "derives_from": "the CP-1 T4.10 metrics (cases.<case>.cp1_inputs keys) a calculated fact derives from; empty for analyst inputs and definition constants"},
        "id_rules": {"fact_id": "<table_id>.<row_id>.<field>", "calculation_id": "calc:<fact_id> on calculated facts", "scenario_rows": "s01.. in submission order; s00 is the Python base control",
                     "break_rows": "b01 fcf_zero, b02 coverage_floor, b03.. thresholds in submission order",
                     "claims": "T2B.1.sNN (scenario rationale), T2B.4.sNN, T2B.7.first, T2B.1.assessment, in this order",
                     "cp1_references_rows": "ref01.. : the CP-1 facts named by {{FIG}} references in the submission's prose in reading order (scenarios, thresholds, assessment, gaps), then the four reported ratios T2B.5 compares, each CP-1 fact once"},
        "lineage_rule": "M2: a calculated fact's citations are the ordered, de-duplicated concatenation of the citations of the CP-1 facts in its derives_from list, in that order (cp4_legal._computed pattern: tuple(dict.fromkeys((*first, *second)))); its period is the base period; a known fact never derives from a CP-1 fact that is not known (asserted by the builder). A stressed FCF lists cash_interest only when the interest increase is non-zero.",
        "cp1_references_rule": "Each row carries the CP-1 fact verbatim under its own fact_id (bound at run time), with the CP-1 fact's own value_class, status and limitation; prose and T2B.5 reference it ({<CP-1 fact_id>|<unit>}). No CP-2A table or claim stores a spelled CP-1 figure.",
        "property_tests": {
            "round_trip": "M1: for every break point with a required decline s*, evaluating the stress recipe in fractions.Fraction over the Decimal inputs at the exact rational s* gives exactly the break level; there is no tolerance and no 38-digit rounding in the statement (a 38-digit Decimal s* fed back can miss the level by one unit in the last place; the builder asserts the Fraction form for every break of every case)",
            "base_control": "stress with decline 0 and increase 0 equals the base ratios (s00)",
            "monotonic": "stressed EBITDA, FCF and coverage do not rise, and leverage does not fall, as the decline rises (where calculable)",
        },
        "d8_table_ids": {
            "collision_found": {"ids": ["T5.1", "T5.2", "T5.3", "T5.4", "T5.5", "T5.6", "T5.7"], "owners": ["CP-2A", "CP-5"], "source": "src/deploy_vii/methodology.json; CP-5 defines them in methods/cp5.md:59-66 and cp5_integrity.py (T5.9 is read by CP-6)"},
            "resolution": "CP-2A registers T2B.1-T2B.9 only; T5.1-T5.7 are removed from the CP-2A methodology entry (they stay CP-5's). No other CP-2A id collides (checked against every module).",
            "cp2a_table_ids": list(TABLES), "module_tables_besides": ["cp1_references"],
        },
        "execution": {
            "plan_order": ["CP-0", "CP-1", "CP-2A"],
            "statuses": {"CP-0": "restricted", "CP-1": "restricted (financial precedent)", "CP-2A": "restricted: own limitations are non-empty and the case is synthetic (execution.py settle)", "why": "synthetic case_kind; analyst-assumption limitation always recorded"},
            "tool_use": {"CP-0": "pack tools plus submit", "CP-1": "as the financial slice", "CP-2A": "submit only: every invoke is a refused not_permitted receipt; exactly one read_inputs (the frozen view) before the submit"},
            "consumption": "open in the first run: no consumer core exists. CP-2G (required CP-2A edge) is planned but not leased; CP-4C (required) and CP-3C (optional) follow it; CP-6 never reads CP-2A (cp6_committee.py READ_OPTIONAL); CP-5 counts only after a lease extends its scope (D3).",
            "inherited_limitations": "rule execution.py:345-366: CP-0 head (limitations, then inherited) then CP-1 head (limitations, then inherited), de-duplicated, own findings removed; bound at run time",
        },
        "cp1_readiness": {
            "literal": "submissions.json cp1_downstream_review", "bindings": "manifest.json run_time_bindings.cp1_readiness",
            "consumer_row": {"entry": "CP-2A", "canonical_module": "CP-2A", "requirements": ["cash_flow_metrics", "liquidity_data"], "policy": "step_12", "status": "ready_with_limitations"},
            "validator_issues": [], "empty_review_status": "not_ready",
            "alias": "an entry CP-2B maps to the same requirements with canonical_module CP-2A; the run requests CP-2A",
        },
        "refusals": [{k: v for k, v in r.items() if k in ("id", "class", "issue_kind", "expected_issues", "issue_prefix")} for r in refusal_list],
        "refusal_rules": {
            "journal": "each refusal is one invalid CP-2A step on attempt 0 of the positive CP-1 head: attempt consumed, module status rejected, limitations equal the issues (bounded: 20 lines of 600 characters)",
            "shape_vs_content": "shape issues are returned alone (a payload that does not parse gets no content check); content issues follow in the order base_period, scenarios, thresholds, assessment, gaps",
            "schema_patterns": {"decline_and_increase": CP_PATTERN, "level": LEVEL_PATTERN},
            "paths": "shape: dotted (scenarios.0.name); content: bracketed (scenarios[0].name)",
            "composer_only": "v02 has no frozen period with a missing or non-positive EBITDA; it is exercised on the composer with the positive CP-1 facts, EBITDA set to missing",
            "validator_only": "v17 is exercised on validate_downside with a literal Upstream (bound = the attempt's inputs bound at run time: prepared-pack, CP-0 and CP-1 Input records; current = the bound tuple with only the CP-1 Input replaced); through G1, a CP-1 head change after begin refuses stale_binding at the next G1 call (owner_workflow.py:423-427); a direct Execution.submit_step caller gets ValueError('Ticket inputs have changed') (execution.py:768-769); neither consumes an attempt or journals a step",
            "g1_level": "not_permitted (invoke, submit before read), stale_binding (snapshot change) and create-time refusals are G1's and are in the lease's A3, not here",
        },
        "cases": {},
    }
    for name, b in built.items():
        entry = dict(b)
        spec = CASES[name]
        entry["execution"] = spec["execution"]
        if name == "positive":
            entry["figures_from_oracle"] = {k: FIGS[k]["spelled"] for k in FIGS}
            entry["assessment_claim_shown"] = spell_figs(SUBMISSION["positive"]["assessment"]["rationale"])
        expected["cases"][name] = entry
    expected["cases"]["positive"]["cp0"] = {"consumer_row": "submissions.json cp0_consumer_row_cp2a", "validator_issues": [], "T8_commands": [["CP-1", "Run CP-1"], ["CP-2A", "Run CP-2A"]]}
    expected["cases"]["refused"] = {
        "execution": "run", "plan_order": ["CP-0", "CP-1", "CP-2A"],
        "cp0": {
            "rows": ["submissions.json refused.cp0_consumer_row_cp1", "submissions.json refused.cp0_consumer_row_cp2a"], "gap_row": "submissions.json refused.gap_row",
            "validator_issues": [], "settled_status": "restricted", "T8_commands": [["CP-1", "DO NOT RUN"], ["CP-2A", "DO NOT RUN"]],
            "probe": "validate_review and build_readiness on a copy of make_pack(gap=True) with these rows (0.2 s); CP-0 settled through Execution.begin / submit_cp0_review in a scratch store gave heads [('CP-0', 'restricted')]",
        },
        "refused_begins": [{"module_id": "CP-1", "reason": "CP-0 has not authorized this consumer's source readiness"}],
        "attempts": ["CP-0"], "heads": ["CP-0"], "cp2a": "never begun (G1 stops the walk after a RefusedBegin; current_inputs for CP-2A would raise ValueError 'Required upstream is unrun, stale or blocked')",
        "model_publication": "not planned", "receipt": "verifies",
        "must_not_appear": ["a CP-2A ticket, attempt, head or table", "a stressed value of 0 standing for a missing one"],
    }
    expected["cases"]["blocked"] = blocked_case(by_id)
    # sanity: the FIG oracle ratios equal the frozen financial oracle
    mo = FIN["q4_ltm_metric_oracle"]
    assert Fraction(mo["total_leverage_reported"]["numerator"]) / Fraction(mo["total_leverage_reported"]["denominator"]) == Fraction(5, 3)
    assert D(mo["fcf_to_debt"]["decimal"]) == D("0.18") and D(mo["interest_coverage_reported"]["decimal"]) == 6
    # sanity: no digits or brace characters in analyst names, labels and prose outside FIG tokens
    for case in ("positive", "gap", "interest_undisclosed", "fixture_quarter_known"):
        sub = SUBMISSION[case]
        for sc in sub["scenarios"]:
            assert not re.search(r"[0-9{}\[\]]", sc["name"]), sc["name"]
            assert not re.search(r"[0-9]", re.sub(r"\{\{FIG:[a-z_]+\|[^}]*\}\}", "", sc["rationale"])), sc["rationale"]
        for t in sub["thresholds"]:
            assert not re.search(r"[0-9{}\[\]]", t["label"]) and not re.search(r"[0-9]", t["rationale"])
        assert not re.search(r"[0-9]", re.sub(r"\{\{FIG:[a-z_]+\|[^}]*\}\}", "", sub["assessment"]["rationale"]))
        for g in sub["gaps"]:
            assert not re.search(r"[0-9]", "".join(g.values()))
    # sanity (M7): no stored text fact and no limitation spells a CP-1 figure; a numeric fact shows its own computed value only
    spelled = {f["spelled"] for f in FIGS.values()}
    for name, b in built.items():
        for x in b["facts"]:
            for key in ("text", "limitation"):
                assert not any(sp in str(x.get(key) or "") for sp in spelled), (name, x["fact_id"])
        for text_ in b["own_limitations"]:
            assert not any(sp in text_ for sp in spelled), (name, text_)
    # sanity: the published submissions carry no builder-internal key
    for case in ("positive", "gap", "interest_undisclosed", "fixture_quarter_known"):
        sub = submissions[case]["downside_pathway"]
        assert all(set(sc) == {"name", "ebitda_decline", "interest_increase", "category", "rationale", "limitation"} for sc in sub["scenarios"])
        assert all(set(t) == {"metric", "level", "label", "category", "rationale"} for t in sub["thresholds"])
    OUT.mkdir(parents=True, exist_ok=True)
    dump(OUT / "manifest.json", manifest)
    dump(OUT / "submissions.json", submissions)
    dump(OUT / "expected.json", expected)


if __name__ == "__main__":
    sys.exit(main())
