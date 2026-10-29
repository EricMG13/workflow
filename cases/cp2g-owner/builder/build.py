"""Writes cases/cp2g-owner/{manifest,submissions,expected}.json (stdlib only).

An independent transcription of the CP-2G (Forward credit model) composition rules written in
work/lead/cp2g-owner-preparation/lease-draft.md. deploy_vii is never imported or run here.
Every input file is pinned by sha256 and checked before use: the frozen financial pack
(cases/financial/manifest.json), the frozen CP-2A and CP-1D oracles (their expected, submissions and
manifest files, read as the settled upstream facts CP-2G consumes under their D3 pins) and
src/deploy_vii/methodology.json (edges and table ids). Every number is derived by exact rational
arithmetic (fractions.Fraction) from the frozen source pages and the literal analyst drivers, and
cross-checked against decimal.Context(prec=38, ROUND_HALF_EVEN), the context of model/_cells.py.

Run: python3 -I cases/cp2g-owner/builder/build.py   (from the repository root)
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
OUT = ROOT / "cases" / "cp2g-owner"
CTX = Context(prec=38, rounding=ROUND_HALF_EVEN)
# sums, differences and products of the short analyst decimals and CP-1 operands must be exact: the Inexact trap fails the build otherwise
CTX_EXACT = Context(prec=38, rounding=ROUND_HALF_EVEN, traps=[Inexact, InvalidOperation, DivisionByZero, Overflow])
D = Decimal

# --- 0. pinned inputs -------------------------------------------------------------------------

PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/cp2a-owner/manifest.json": "5219f063dcb130b38b8059397a73ff890ccb14ef03f8c2a6188b971dce7ead1a",
    "cases/cp2a-owner/submissions.json": "4f10743e9203e2fa6e9795f93c33af46d056e3574a58b85e71948a1a206974a3",
    "cases/cp2a-owner/expected.json": "4b6138d79be7e8e0780eeade0cc09881658cf175b0c0b1cee1f0a083b1ea126a",
    "cases/cp1d-owner/manifest.json": "07dd8530a7f53aa5fe2c1b4840554c0fc6392e26e53bf01ad2858458ecdfe955",
    "cases/cp1d-owner/submissions.json": "e19bc64bf6b9d388ca355fcb5de5160be1c4c0e7e27d3b348f1996a17fbd93d7",
    "cases/cp1d-owner/expected.json": "293120368b5d791727738d56e4078129e4b4de07d5c8287cf0cef7cade2e58c3",
    "src/deploy_vii/methodology.json": "0932d9fbcd9272d62bcb7681e1dd16d9bc944319c64716b41dc79715699796e8",
}


def pinned(rel):
    data = (ROOT / rel).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == PINS[rel], (rel, digest)
    return json.loads(data)


FIN = pinned("cases/financial/manifest.json")
CP2A_MAN = pinned("cases/cp2a-owner/manifest.json")
CP2A_SUB = pinned("cases/cp2a-owner/submissions.json")
CP2A_EXP = pinned("cases/cp2a-owner/expected.json")
CP1D_MAN = pinned("cases/cp1d-owner/manifest.json")
CP1D_SUB = pinned("cases/cp1d-owner/submissions.json")
CP1D_EXP = pinned("cases/cp1d-owner/expected.json")
METHODOLOGY = pinned("src/deploy_vii/methodology.json")


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


SRC = {s["source_id"]: s for s in FIN["sources"]}
for _sid, _s in SRC.items():
    assert page_sha([p["text"] for p in _s["pages"]]) == _s["sha256"], _sid
PAGE = {p["locator"]: p["text"] for p in SRC["financial"]["pages"]}
BRIDGE = CP1D_MAN["synthetic_source"]["positive"]
assert page_sha([p["text"] for p in BRIDGE["pages"]]) == BRIDGE["sha256"]

# the edges and tables CP-2G registers, from the pinned methodology (D4, D8)
MOD = {m["module_id"]: m for m in METHODOLOGY}
assert MOD["CP-2G"]["required"] == ["CP-0", "CP-1", "CP-2A"] and MOD["CP-2G"]["optional"] == ["CP-1D", "CP-2D"]
assert "edge_rules" not in MOD["CP-2G"]
T2H_IDS = [f"T2H.{n}" for n in range(1, 10)]
assert MOD["CP-2G"]["table_ids"] == T2H_IDS
assert not any(t in m["table_ids"] for m in METHODOLOGY if m["module_id"] != "CP-2G" for t in T2H_IDS)


# --- 1. exact arithmetic ----------------------------------------------------------------------


def fr(x):
    return x if isinstance(x, Fraction) else Fraction(x)


def q38(x):
    """The correctly rounded 38-significant-digit half-even Decimal of an exact rational."""
    f = fr(x)
    if f == 0:
        return D(0)
    with localcontext(CTX):
        return D(f.numerator) / D(f.denominator)


def div(a, b):
    """One division of exact decimals in the 38-digit half-even context; equals the correctly rounded rational (asserted)."""
    with localcontext(CTX):
        value = a / b
    assert value == q38(fr(a) / fr(b)), (a, b)
    return value


def sub38(a, b):
    """One subtraction in the 38-digit half-even context; equals the correctly rounded rational (asserted)."""
    with localcontext(CTX):
        value = a - b
    assert value == q38(fr(a) - fr(b)), (a, b)
    return value


def ex(fn):
    """Evaluate one sum, difference or product in the 38-digit context with the Inexact trap (a rounded result raises)."""
    with localcontext(CTX_EXACT):
        return fn()


def norm(d):
    text = format(d, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def show(d, unit_class, decimals=None):
    """display.format_value for a known number: ROUND_HALF_UP on the exact value."""
    places, scale, suffix = {"amount": (0, 1, ""), "multiple": (2, 1, "x"), "percent": (1, 100, "%")}[unit_class]
    if decimals is not None:
        places = decimals
    rounded = (d * scale).quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP)
    assert not (rounded == 0 and d < 0), ("negative value rounds to zero", d)
    body = f"{abs(rounded):,.{places}f}"
    return (f"({body})" if rounded < 0 else body) + suffix


def amt(d):
    return show(d, "amount", 2)


def pct(d):
    return show(d, "percent")


def mult(d):
    return show(d, "multiple")


# --- 2. the CP-1 operands, derived from the frozen statement pages ----------------------------


def row_values(page, label, count):
    for line in PAGE[page].split("\n"):
        if line.startswith(label + "  "):
            tokens = line[len(label) :].split()
            assert len(tokens) == count, (label, tokens)
            return [D(t[1:-1]) * -1 if t.startswith("(") else D(t) for t in tokens]
    raise AssertionError(label)


REVENUE_Q = row_values("page:2", "Revenue", 5)
EBITDA_Q = row_values("page:2", "Reported EBITDA", 5)
INTEREST_Q = row_values("page:3", "Cash interest paid", 5)
TAX_Q = row_values("page:3", "Cash tax paid", 5)
WC_Q = row_values("page:3", "Working capital cash movement", 5)
CAPEX_Q = row_values("page:3", "Total capital expenditure", 5)
FCF_Q = row_values("page:3", "Levered free cash flow", 5)
CFO_Q = row_values("page:3", "Operating cash flow", 5)
DEBT_BS = row_values("page:4", "Total debt", 6)
CASH_BS = row_values("page:4", "Cash and cash equivalents", 6)
RCF_COMMIT = row_values("page:4", "RCF commitment", 6)
RCF_DRAWN = row_values("page:4", "RCF drawings", 6)
for _series in (REVENUE_Q, EBITDA_Q, INTEREST_Q, TAX_Q, WC_Q, CAPEX_Q, FCF_Q, CFO_Q):
    assert sum(_series[:4]) == _series[4]
LTM = {
    "revenue": sum(REVENUE_Q[:4]),
    "ebitda": sum(EBITDA_Q[:4]),
    "interest": sum(INTEREST_Q[:4]),  # outflow magnitude
    "taxes": sum(TAX_Q[:4]),
    "wc": -sum(WC_Q[:4]),  # outflow magnitude (the statement shows a negative movement)
    "capex": -sum(CAPEX_Q[:4]),
    "fcf": sum(FCF_Q[:4]),
    "total_debt": DEBT_BS[4],
    "cash": CASH_BS[4],
    "undrawn": RCF_COMMIT[4] - RCF_DRAWN[4],
}
_o = FIN["q4_ltm_derived_source_units"]
assert LTM["revenue"] == D(_o["revenue"]) and LTM["ebitda"] == D(_o["ebitda"]) and LTM["fcf"] == D(_o["fcf"])
assert -LTM["capex"] == D(_o["capex"]) and LTM["total_debt"] == D(_o["total_debt"])
assert LTM["total_debt"] - LTM["cash"] == D(_o["net_debt"]) and sum(CFO_Q[:4]) == D(_o["cfo"])
assert LTM["ebitda"] - LTM["interest"] - LTM["taxes"] - LTM["wc"] - LTM["capex"] == LTM["fcf"]  # the statement identity
_mo = FIN["q4_ltm_metric_oracle"]
RATIO_REPORTED = {"total_leverage": "total_leverage_reported", "net_leverage": "net_leverage_reported",
                  "interest_coverage": "interest_coverage_reported", "fcf_to_debt": "fcf_to_debt"}
assert (_mo["total_leverage_reported"]["numerator"], _mo["total_leverage_reported"]["denominator"]) == ("50", "30")
assert (_mo["interest_coverage_reported"]["numerator"], _mo["interest_coverage_reported"]["denominator"]) == ("30", "5")

LTM_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
LTM_COLUMN = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
BASE_YEAR = 2025
YEARS = [BASE_YEAR + n for n in (1, 2, 3)]
FY = [f"FY{y}" for y in YEARS]
FY_PERIOD = [f"FY{y}: {y}-01-01 to {y}-12-31" for y in YEARS]
FY_SPAN_PERIOD = f"{FY[0]}-{FY[-1]}: {YEARS[0]}-01-01 to {YEARS[-1]}-12-31"

# CP-1 T4.10 value classes observed on the S1 positive promoted CP-1 head (probe, read only copy r2pos-orig,
# 2026-10-28, LTM Q4 25 column, 500 T4.10 facts): the amount is derived above, only the class is observed
CP1_METRICS = {  # metric -> (observed value_class, unit class, amount in CP-1 sign convention)
    "revenue": ("calculated", "amount", LTM["revenue"]),
    "ebitda": ("calculated", "amount", LTM["ebitda"]),
    "cash_interest": ("calculated", "amount", -LTM["interest"]),
    "cash_taxes": ("calculated", "amount", -LTM["taxes"]),
    "working_capital_change": ("calculated", "amount", -LTM["wc"]),
    "capex": ("calculated", "amount", -LTM["capex"]),
    "fcf": ("calculated", "amount", LTM["fcf"]),
    "total_debt": ("source", "amount", LTM["total_debt"]),
    "cash_closing": ("source", "amount", LTM["cash"]),
    "undrawn_rcf": ("calculated", "amount", LTM["undrawn"]),
    "ebitda_margin": ("calculated", "percent", q38(Fraction(LTM["ebitda"]) / Fraction(LTM["revenue"]))),
    "capex_to_revenue": ("calculated", "percent", q38(Fraction(LTM["capex"]) / Fraction(LTM["revenue"]))),
    "total_leverage_reported": ("calculated", "multiple", q38(Fraction(LTM["total_debt"]) / Fraction(LTM["ebitda"]))),
    "net_leverage_reported": ("calculated", "multiple", q38(Fraction(LTM["total_debt"] - LTM["cash"]) / Fraction(LTM["ebitda"]))),
    "interest_coverage_reported": ("calculated", "multiple", q38(Fraction(LTM["ebitda"]) / Fraction(LTM["interest"]))),
    "fcf_to_debt": ("calculated", "percent", q38(Fraction(LTM["fcf"]) / Fraction(LTM["total_debt"]))),
}
assert CP1_METRICS["total_leverage_reported"][2] == q38(Fraction(_mo["total_leverage_reported"]["fraction"]))
assert CP1_METRICS["fcf_to_debt"][2] == D(_mo["fcf_to_debt"]["decimal"])
OPERAND_KEY = {  # engine operand -> CP-1 metric
    "revenue": "revenue", "ebitda": "ebitda", "interest": "cash_interest", "taxes": "cash_taxes", "wc": "working_capital_change",
    "capex": "capex", "fcf": "fcf", "debt": "total_debt", "cash": "cash_closing", "undrawn": "undrawn_rcf",
}
WORDS = {"revenue": "revenue", "ebitda": "EBITDA", "interest": "cash interest", "taxes": "cash taxes", "wc": "working capital movement",
         "capex": "capital expenditure", "fcf": "free cash flow", "debt": "total debt", "cash": "cash and cash equivalents",
         "undrawn": "undrawn revolver"}
NOT_DISCLOSED = {"cash": "Cash and cash equivalents are not disclosed in the supplied statements."}


def cp1_facts(missing=()):
    """The CP-1 T4.10 facts CP-2G reads for the LTM column; `missing` metrics are status missing."""
    out = {}
    for metric, (klass, uc, amount) in CP1_METRICS.items():
        known = metric not in missing
        out[metric] = {
            "label": f"{LTM_COLUMN} · {metric}", "period": LTM_PERIOD, "status": "known" if known else "missing",
            "amount_exact": norm(amount) if known else None, "value_class": klass, "unit_class": uc,
            "cell_text": show(amount, uc, None) if known else None,
            "limitation": None if known else NOT_DISCLOSED.get(metric, f"{metric} is not disclosed in the supplied statements."),
        }
    return out


def operands(cp1):
    """Engine operands (outflows as positive magnitudes) and the reason of each missing one."""
    op, why = {}, {}
    for key, metric in OPERAND_KEY.items():
        fact = cp1[metric]
        if fact["status"] != "known":
            op[key], why[key] = None, f"Not calculable: base {WORDS[key]} is missing in CP-1 ({LTM_PERIOD})"
        else:
            value = D(fact["amount_exact"])
            op[key] = -value if key in ("interest", "taxes", "wc", "capex") else value
            why[key] = None
    return op, why


# --- 3. the frozen upstream facts CP-2G consumes (D3 pins) ------------------------------------


def cp2a_head(case):
    """CP-2A's settled T2B.1 scenarios and T2B.6 break register, read from the frozen CP-2A oracle."""
    exp = CP2A_EXP["cases"][case]
    facts = {f["fact_id"]: f for f in exp["facts"]}
    scenarios = {}
    for fid, f in facts.items():
        m = re.fullmatch(r"T2B\.1\.(s\d\d)\.name", fid)
        if m:
            row = m.group(1)
            scenarios[row] = {"name": f["text"], "decline": facts[f"T2B.1.{row}.ebitda_decline"],
                              "increase": facts[f"T2B.1.{row}.interest_increase"]}
    breaks = []
    for fid, f in facts.items():
        m = re.fullmatch(r"T2B\.6\.(b\d\d)\.origin", fid)
        if m:
            row = m.group(1)
            breaks.append({"row": row, "origin": f["text"], "test": facts[f"T2B.6.{row}.test"]["text"], "level": facts[f"T2B.6.{row}.level"],
                           "required_decline": facts[f"T2B.6.{row}.required_decline"], "outcome": facts[f"T2B.6.{row}.outcome"]["text"]})
    return {"base_period": exp["base_period"], "scenarios": scenarios, "breaks": breaks, "source": f"cases/cp2a-owner/expected.json cases.{case}"}


DEF_FCF = "Free cash flow at or below zero"
DEF_COV = "EBITDA no longer covers cash interest"


def cp1d_head(state):
    """CP-1D's settled supported EBITDA and supported leverage (T1D.3 and T1D.6), from the frozen CP-1D positive oracle."""
    if state != "bound":
        return {"state": state, "facts": None}
    facts = {f["fact_id"]: f for f in CP1D_EXP["cases"]["positive"]["facts"]}
    ids = ("T1D.3.supported.value", "T1D.6.supported.total_leverage", "T1D.6.supported.net_leverage")
    return {"state": state, "facts": {i: facts[i] for i in ids}}


# --- 4. the literal analyst submissions -------------------------------------------------------

DRIVERS = ("revenue_growth", "ebitda_margin", "capex_pct_revenue", "tax_wc_pct_revenue", "interest_rate", "dividends", "debt_repayment")
DRIVER_LABEL = {
    "revenue_growth": "Revenue growth", "ebitda_margin": "EBITDA margin", "capex_pct_revenue": "Capital expenditure, share of revenue",
    "tax_wc_pct_revenue": "Cash taxes and working capital outflow, share of revenue", "interest_rate": "Cash interest rate on opening debt",
    "dividends": "Distributions to shareholders (outflow)", "debt_repayment": "Debt repayment (outflow)",
}
DRIVER_UC = {"revenue_growth": "percent", "ebitda_margin": "percent", "capex_pct_revenue": "percent", "tax_wc_pct_revenue": "percent",
             "interest_rate": "percent", "dividends": "amount", "debt_repayment": "amount"}
GROWTH_PATTERN = r"^-?(0|1|0\.\d{1,4}|1\.0{1,4})$"
FRACTION_PATTERN = r"^(0|1|0\.\d{1,4}|1\.0{1,4})$"
AMOUNT_PATTERN = r"^[0-9]{1,6}(\.[0-9]{1,4})?$"
LIQUIDITY_PATTERN = r"^([0-9]{1,6}(\.[0-9]{1,4})?|not assessed)$"
SCENARIO_PATTERN = r"^s[0-9]{2}$"
BREAK_PATTERN = r"^b[0-9]{2}$"
NOT_ASSESSED = "not assessed"
TAMPER_TARGET, TAMPER_FROM, TAMPER_TO = "T2H.7.b03.down_first", "FY2026", "Not reached by FY2028"
FORECAST_LIMITATION = "Forecast on analyst-assumed drivers"
LIQ_HEADROOM_FY25 = "Minimum liquidity is a forecast-year assumption and is not applied to the FY2025 actual"
METRICS = ("total_leverage", "net_leverage", "interest_coverage")

FIGS = {  # name -> source, CP-1 metric (or fixed upstream fact id), token and spelling
    "revenue_ltm": {"source": "cp1", "metric": "revenue", "unit_token": "US$ m"},
    "ebitda_margin_ltm": {"source": "cp1", "metric": "ebitda_margin", "unit_token": "%"},
    "capex_to_revenue_ltm": {"source": "cp1", "metric": "capex_to_revenue", "unit_token": "%"},
    "total_debt_ltm": {"source": "cp1", "metric": "total_debt", "unit_token": "US$ m"},
    "total_leverage_reported": {"source": "cp1", "metric": "total_leverage_reported", "unit_token": "x"},
    "total_leverage_supported": {"source": "cp1d", "fact_id": "T1D.6.supported.total_leverage", "unit_token": "x"},
}


def fig(name):
    return "{{FIG:" + name + "|" + FIGS[name]["unit_token"] + "}}"


BASE_DRIVERS = {
    "revenue_growth": {"values": ["0.03", "0.03", "0.03"], "category": "Analyst Interpretation",
                       "rationale": f"Modest growth from the {fig('revenue_ltm')} twelve-month revenue base, with no price or volume guidance in the source pack.",
                       "limitation": "No management guidance or consensus supports the growth rates."},
    "ebitda_margin": {"values": ["0.25", "0.26", "0.27"], "category": "Analyst Interpretation",
                      "rationale": f"The margin starts at the {fig('ebitda_margin_ltm')} twelve-month level and widens slowly as fixed costs are spread over higher revenue.",
                      "limitation": "Margin expansion is an analyst view; the source pack states no cost programme."},
    "capex_pct_revenue": {"values": ["0.08", "0.08", "0.08"], "category": "Analyst Interpretation",
                          "rationale": f"Capital expenditure is held at a steady share of revenue, close to the twelve-month level of {fig('capex_to_revenue_ltm')}.",
                          "limitation": None},
    "tax_wc_pct_revenue": {"values": ["0.05", "0.05", "0.05"], "category": "Analyst Interpretation",
                           "rationale": "Cash taxes and working capital together stay at the twelve-month share of revenue.", "limitation": None},
    "interest_rate": {"values": ["0.10", "0.10", "0.10"], "category": "Analyst Interpretation",
                      "rationale": f"The rate is held at the level implied by twelve-month cash interest on the closing debt of {fig('total_debt_ltm')}.",
                      "limitation": None},
    "dividends": {"values": ["5", "5", "5"], "category": "Analyst Interpretation",
                  "rationale": "Distributions are cut below the twelve-month level to protect cash; the cut is the analyst's assumption.",
                  "limitation": "No dividend policy is disclosed in the source pack."},
    "debt_repayment": {"values": ["0", "5", "10"], "category": "Analyst Interpretation",
                       "rationale": "Repayments start in the second year from surplus cash; they are an analyst assumption, not a mandatory schedule.",
                       "limitation": None},
}
DOWNSIDE = {
    "scenario": "s03",
    "rationale": "The downside takes the CP-2A scenario with the larger earnings fall and the higher rate, held in every forecast year: earnings fall by its decline and the rate paid rises by its increase.",
    "limitation": "The shock is persistent and no mitigating action is modelled.",
}
BREAK_METRICS = [{"break_id": "b03", "metric": "total_leverage"}, {"break_id": "b04", "metric": "net_leverage"},
                 {"break_id": "b05", "metric": "interest_coverage"}]
GAPS = [{"gap": "No management guidance, consensus or covenant document is an input to the forecast.",
         "why_it_matters": "The driver values and the watch levels are the analyst's, so the timing of the first break may differ from lenders' own tests.",
         "affected_analysis": "Forecast drivers and first-break timing", "severity": "Material",
         "action": "Add guidance and the covenant package, then rerun the forecast."}]
SUBMISSION = {
    "positive": {
        "base_drivers": BASE_DRIVERS, "downside": DOWNSIDE, "break_metrics": BREAK_METRICS,
        "minimum_liquidity": {"amount": "10", "rationale": "A working minimum for a business of this size; the source pack states no minimum cash requirement."},
        "assessment": {
            "rationale": f"Opening total leverage is {fig('total_leverage_reported')} on reported earnings and {fig('total_leverage_supported')} on the earnings CP-1D supports; the base case deleverages through retained cash flow and repayments, while the downside reaches the watch levels in the first forecast year and runs short of cash in the second.",
            "category": "Analyst Interpretation", "confidence": "Medium", "limitation": "Every driver is an analyst assumption without a source citation."},
        "gaps": GAPS,
    },
    "gap": {
        "base_drivers": BASE_DRIVERS, "downside": DOWNSIDE, "break_metrics": BREAK_METRICS,
        "minimum_liquidity": {"amount": NOT_ASSESSED, "rationale": "The source pack states no minimum liquidity requirement, so none is assumed."},
        "assessment": {
            "rationale": f"Opening total leverage is {fig('total_leverage_reported')}; the base case deleverages through retained cash flow and repayments, while the downside reaches the watch levels in the first forecast year and runs short of cash in the second.",
            "category": "Analyst Interpretation", "confidence": "Low", "limitation": "Earnings quality and minimum liquidity were not assessed."},
        "gaps": [{"gap": "Earnings quality and minimum liquidity are not inputs to the forecast.",
                  "why_it_matters": "Without them the starting earnings are taken as reported and the liquidity break is not tested.",
                  "affected_analysis": "Starting leverage and liquidity break", "severity": "Material",
                  "action": "Run the earnings-quality owner and assess a minimum liquidity, then rerun the forecast."}],
    },
}
# ruling L4: the CP-1D-blocked run is positive-derived (minimum liquidity 10); its assessment names no CP-1D figure, as none was settled
SUBMISSION["cp1d_blocked"] = dict(deepcopy(SUBMISSION["positive"]), assessment={
    "rationale": f"Opening total leverage is {fig('total_leverage_reported')} on reported earnings; the base case deleverages through retained cash flow and repayments, while the downside reaches the watch levels in the first forecast year and runs short of cash in the second.",
    "category": "Analyst Interpretation", "confidence": "Medium", "limitation": "Every driver is an analyst assumption without a source citation."})
# composer-only variants of the gap submission (no run: a promoted head cannot be edited)
FIXTURE_SUBMISSION = {
    "fixture_total_loss": dict(deepcopy(SUBMISSION["positive"]), downside=dict(DOWNSIDE, scenario="s04",
                               rationale="The downside takes the CP-2A boundary scenario in which earnings fall to zero in every forecast year.",
                               limitation="The boundary shock is not a forecast; it shows which measures stop being meaningful."),
                               assessment={"rationale": "Opening leverage is as reported; the boundary downside shows which measures stop being meaningful.",
                                           "category": "Analyst Interpretation", "confidence": "Low", "limitation": "Every driver is an analyst assumption without a source citation."}),
    "fixture_cash_missing": deepcopy(SUBMISSION["gap"]),
    "fixture_debt_repaid": dict(deepcopy(SUBMISSION["gap"]), base_drivers=dict(BASE_DRIVERS, debt_repayment=dict(
        BASE_DRIVERS["debt_repayment"], values=["50", "0", "0"], rationale="The whole term loan is repaid in the first year, a boundary case for the composer."))),
    "fixture_cp2a_gap_head": dict(deepcopy(SUBMISSION["gap"]), downside=dict(DOWNSIDE, scenario="s02"), break_metrics=[{"break_id": "b03", "metric": "total_leverage"}]),
}
for _k in ("fixture_total_loss", "fixture_debt_repaid"):
    assert FIXTURE_SUBMISSION[_k]["minimum_liquidity"]
CASES = {
    "positive": {"submission": "positive", "cp2a": "positive", "cp1d": "bound", "missing": (), "execution": "run"},
    "gap": {"submission": "gap", "cp2a": "positive", "cp1d": "unbound", "missing": (), "execution": "run"},
    "cp1d_blocked": {"submission": "cp1d_blocked", "cp2a": "positive", "cp1d": "blocked", "missing": (), "execution": "run"},
    "fixture_total_loss": {"submission": "fixture_total_loss", "cp2a": "positive", "cp1d": "unbound", "missing": (), "execution": "composer_only"},
    "fixture_cash_missing": {"submission": "fixture_cash_missing", "cp2a": "positive", "cp1d": "unbound", "missing": ("cash_closing",), "execution": "composer_only"},
    "fixture_debt_repaid": {"submission": "fixture_debt_repaid", "cp2a": "positive", "cp1d": "unbound", "missing": (), "execution": "composer_only"},
    "fixture_cp2a_gap_head": {"submission": "fixture_cp2a_gap_head", "cp2a": "gap", "cp1d": "unbound", "missing": (), "execution": "composer_only"},
}
for _name, _spec in CASES.items():
    _spec["sub"] = FIXTURE_SUBMISSION[_spec["submission"]] if _spec["submission"].startswith("fixture") else SUBMISSION[_spec["submission"]]
    _spec["cp1"] = cp1_facts(_spec["missing"])
    _spec["cp2a_head"] = cp2a_head(_spec["cp2a"])
    _spec["cp1d_head"] = cp1d_head(_spec["cp1d"])
assert "fixture_cash_missing" in CASES and CASES["fixture_cash_missing"]["sub"]["minimum_liquidity"]["amount"] == NOT_ASSESSED


# --- 5. the forward engine --------------------------------------------------------------------

NC_E = "Not calculable: EBITDA is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
NC_I = "Not calculable: cash interest is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
NC_D = "Not calculable: debt is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
KIND_METRIC = {"fcf": "Free cash flow", "coverage": "Interest coverage", "total_leverage": "Total leverage", "net_leverage": "Net leverage",
               "liquidity": "Accessible liquidity"}


def run_engine(op, why0, drv, shock, shock_why):
    """The engine in CTX_EXACT (Inexact trapped); each ratio sets CTX itself, so only divisions may round, and they are asserted against the rational."""
    with localcontext(CTX_EXACT):
        return _run_engine(op, why0, drv, shock, shock_why)


def _run_engine(op, why0, drv, shock, shock_why):
    """Three forecast years for one case. `drv` holds the Decimal driver values; `shock` is None (base case) or (decline, increase)
    Decimals from CP-2A (None where CP-2A has no known fact, with the reason in `shock_why`). Every value is a Decimal built from exact
    operands (checked against Fraction); a value that cannot be calculated is None with its reason in `why`."""
    years = []
    prev = {"R": op["revenue"], "D": op["debt"], "C": op["cash"]}
    prev_why = {"R": why0["revenue"], "D": why0["debt"], "C": why0["cash"]}
    for t in range(3):
        v, w = {}, {}

        def put(name, deps, fn):
            for dep in deps:
                if v[dep] is None:
                    v[name], w[name] = None, w[dep]
                    return
            v[name], w[name] = fn(), None

        v["Ropen"], w["Ropen"] = prev["R"], prev_why["R"]
        v["Dopen"], w["Dopen"] = prev["D"], prev_why["D"]
        v["Copen"], w["Copen"] = prev["C"], prev_why["C"]
        g, m, c, x, rate, div, rep = (drv[k][t] for k in DRIVERS)
        put("R", ["Ropen"], lambda: v["Ropen"] * (1 + g))
        put("Ebase", ["R"], lambda: v["R"] * m)
        if shock is None:
            put("E", ["Ebase"], lambda: v["Ebase"])
        else:
            s, k = shock
            v["s"], w["s"] = s, shock_why["s"]
            v["k"], w["k"] = k, shock_why["k"]
            put("E", ["Ebase", "s"], lambda: v["Ebase"] * (1 - v["s"]))
        if shock is None:
            put("I", ["Dopen"], lambda: v["Dopen"] * rate)
        else:
            put("I", ["Dopen", "k"], lambda: v["Dopen"] * (rate * (1 + v["k"])))
        put("X", ["R"], lambda: v["R"] * x)
        put("K", ["R"], lambda: v["R"] * c)
        put("CFO", ["E", "I", "X"], lambda: v["E"] - v["I"] - v["X"])
        put("FCF", ["CFO", "K"], lambda: v["CFO"] - v["K"])
        v["div"], w["div"] = div, None
        v["rep"], w["rep"] = rep, None
        put("Dclose", ["Dopen"], lambda: v["Dopen"] - v["rep"])
        put("Cclose", ["Copen", "FCF"], lambda: v["Copen"] + v["FCF"] - v["div"] - v["rep"])
        v["U"], w["U"] = op["undrawn"], why0["undrawn"]
        put("Liq", ["Cclose", "U"], lambda: v["Cclose"] + v["U"])

        def ratio(name, num, den, den_why):
            if v[num] is None:
                v[name], w[name] = None, w[num]
            elif v[den] is None:
                v[name], w[name] = None, w[den]
            elif v[den] <= 0:
                v[name], w[name] = None, den_why
            else:
                with localcontext(CTX):
                    value = v[num] / v[den]
                assert value == q38(fr(v[num]) / fr(v[den])), name
                v[name], w[name] = value, None

        ratio("TL", "Dclose", "E", NC_E)
        if v["Dclose"] is None or v["Cclose"] is None:
            v["ND"], w["ND"] = None, w["Dclose"] if v["Dclose"] is None else w["Cclose"]
        else:
            v["ND"], w["ND"] = v["Dclose"] - v["Cclose"], None
        ratio("NL", "ND", "E", NC_E)
        ratio("IC", "E", "I", NC_I)
        ratio("FD", "FCF", "Dclose", NC_D)
        years.append((v, w))
        prev = {"R": v["R"], "D": v["Dclose"], "C": v["Cclose"]}
        prev_why = {"R": w["R"], "D": w["Dclose"], "C": w["Cclose"]}
    return years


def exact_check(op, drv, shock, years):
    """Re-derive every flow in Fractions and require equality with the Decimal path (no rounding in sums and products)."""
    R, Dd, C = (fr(op[k]) if op[k] is not None else None for k in ("revenue", "debt", "cash"))
    for t, (v, _w) in enumerate(years):
        g, m, c, x, rate, div, rep = (fr(drv[k][t]) for k in DRIVERS)
        if R is None:
            assert v["R"] is None
            return
        R = R * (1 + g)
        E = R * m * (1 - fr(shock[0])) if shock and shock[0] is not None else (R * m if not shock else None)
        assert fr(v["R"]) == R, (t, "R")
        if E is not None:
            assert fr(v["E"]) == E, (t, "E")
        if Dd is not None and E is not None and (shock is None or shock[1] is not None):
            I = Dd * (rate * (1 + fr(shock[1]))) if shock else Dd * rate
            assert fr(v["I"]) == I, (t, "I")
            F = E - I - R * x - R * c
            assert fr(v["FCF"]) == F, (t, "FCF")
            Dd = Dd - rep
            assert fr(v["Dclose"]) == Dd
            if C is not None:
                C = C + F - div - rep
                assert fr(v["Cclose"]) == C, (t, "C")
        else:
            Dd = None if Dd is None else Dd - rep
            C = None


# --- 6. the break tests (CP-2A levels along the forward path) ---------------------------------


def break_decline(kind, level, op):
    """The EBITDA decline that reaches `level` on the CP-1 base, the CP-2A recipe in exact rationals; None when not defined."""
    E, I, D0, C0 = (None if op[k] is None else fr(op[k]) for k in ("ebitda", "interest", "debt", "cash"))
    lvl = fr(level)
    if E is None or E <= 0:
        return None
    if kind == "total_leverage":
        return None if D0 is None else (lvl * E - D0) / (lvl * E)
    if kind == "net_leverage":
        return None if D0 is None or C0 is None or D0 - C0 <= 0 else (lvl * E - (D0 - C0)) / (lvl * E)
    if kind == "coverage":
        return None if I is None else (E - lvl * I) / E
    raise AssertionError(kind)


TEST_KEY = {"fcf": "FCF", "coverage": "IC", "total_leverage": "TL", "net_leverage": "NL", "liquidity": "Liq"}
BREAK_OPERANDS = {"total_leverage": ("ebitda", "debt"), "net_leverage": ("ebitda", "debt", "cash"), "coverage": ("ebitda", "interest")}  # formula order
UNVERIFIED_PERIOD = "CP-2A stressed a different base period from the twelve-month base, so its required decline is not comparable"
UNVERIFIED_CP2A = "CP-2A has no known level or required decline for it (missing or not applicable)"


def unverified_operand_reason(kind, op):
    """The first CP-1 operand (formula order) the CP-2A recipe needs and CP-1 lacks, named; any other cause is not constructed by a case."""
    for key in BREAK_OPERANDS[kind]:
        if op[key] is None:
            return f"base {WORDS[key]} is missing in CP-1 for {LTM_PERIOD}"
    raise AssertionError((kind, "no operand is missing: a non-positive denominator is not constructed by any case"))


def test_year(kind, level, v):
    """(stressed value, hit) in one forecast year; hit None when the metric is not calculable."""
    key = TEST_KEY[kind]
    value = v[key]
    if value is None or level is None:
        return value, None
    if kind in ("fcf", "coverage"):
        return value, value <= level
    if kind == "liquidity":
        return value, value < level
    return value, value >= level


def first_result(results):
    """Text of the first forecast year in which a test is met. A year that cannot be calculated before the first met year makes
    the answer unknowable; no year met and every year calculable is 'Not reached'."""
    unknown = False
    for t, (_value, hit) in enumerate(results):
        if hit is None:
            unknown = True
        elif hit:
            return "Not calculable" if unknown else FY[t]
    return "Not calculable" if unknown else f"Not reached by {FY[-1]}"


# --- 7. composition ---------------------------------------------------------------------------

TABLES = {
    "T2H.1": "Upstream register",
    "T2H.2": "Historical-to-base bridge",
    "T2H.3": "Assumption register",
    "T2H.4": "Operating forecast",
    "T2H.5": "Debt and cash roll-forward",
    "T2H.6": "Credit metrics",
    "T2H.7": "Break-point timing",
    "T2H.8": "Deleveraging path",
    "T2H.9": "Gaps ledger",
}
BLOCKS = {
    "forward-credit-path": {"title": "Forward credit path", "owner": "CP-2G", "kind": "dense", "producers": ["CP-2G"],
                            "tabs": [["T2H.4", "Operating forecast"], ["T2H.5", "Debt and cash"], ["T2H.6", "Credit metrics"]]},
    "forward-breakpoints": {"title": "Forward break points", "owner": "CP-2G", "kind": "dense", "producers": ["CP-2G"],
                            "tabs": [["T2H.7", "Break-point timing"], ["T2H.8", "Deleveraging path"]]},
}
EVIDENCE_TABLES = ["T2H.1", "T2H.2", "T2H.3", "cp1_references", "cp2a_references", "cp1d_references"]
LIMITATION_TABLES = ["T2H.9"]
GAP_SPELLING = {"missing": ("gap", "∅ G#"), "not_applicable": ("not_meaningful", "∅ G# n.m.")}
UC_UNIT = {"amount": "MILLIONS", "multiple": "MULTIPLE", "percent": "PERCENT"}
CASE_LABEL = {"base": "Base", "down": "Downside"}
ROW_PREFIX = {"base": "b", "down": "d"}


def fp05(facts, tables):
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
            tabs.append({"table_id": table_id, "label": label,
                         "rows": [{"row_id": r["row_id"], "label": r["label"], "cells": [cell(f) for f in r["fact_ids"]]} for r in table["rows"]]})
        out["blocks"][block_id] = {"title": block["title"], "owner": block["owner"], "kind": block["kind"], "state": "populated", "tabs": tabs}
    out["other_blocks"] = ("every other distressed_restructuring block keeps its idle wording; CP-2G fills none of them. "
                           "The CP-2A blocks downside-stress and break-points are filled from the CP-2A head the same page also binds and are asserted by the CP-2A lease, not here")
    out["evidence_rail_tables"] = EVIDENCE_TABLES
    out["limitations_rail_tables"] = LIMITATION_TABLES
    return out


def prose_texts(sub):
    for name in DRIVERS:
        yield sub["base_drivers"][name]["rationale"]
    yield sub["downside"]["rationale"]
    yield sub["minimum_liquidity"]["rationale"]
    yield sub["assessment"]["rationale"]
    for g in sub["gaps"]:
        yield from (g["gap"], g["why_it_matters"], g["affected_analysis"], g["action"])


def spell_figs(text, figs):
    return re.sub(r"\{\{FIG:([a-z_]+)\|[^}]*\}\}", lambda m: figs[m.group(1)]["spelled"], text)


def build_case(name):
    spec = CASES[name]
    sub, cp1, cp2a, cp1d = spec["sub"], spec["cp1"], spec["cp2a_head"], spec["cp1d_head"]
    op, why0 = operands(cp1)
    facts, rows_by_table, claim_list, own_limits = [], {t: [] for t in TABLES}, [], []
    scen = cp2a["scenarios"][sub["downside"]["scenario"]]
    ds = scen["decline"], scen["increase"]

    # figure registry for this case: name -> spelled text and the fact it resolves to
    figs = {}
    for fname, f in FIGS.items():
        if f["source"] == "cp1":
            src = cp1[f["metric"]]
            figs[fname] = {"unit_token": f["unit_token"], "cp1_metric": f["metric"], "known": src["status"] == "known",
                           "spelled": None if src["status"] != "known" else src["cell_text"] + (" US$ m" if f["unit_token"] == "US$ m" else "")}
        else:
            if cp1d["state"] == "bound":
                src = cp1d["facts"][f["fact_id"]]
                figs[fname] = {"unit_token": f["unit_token"], "fact_id": f["fact_id"], "known": True, "spelled": src["shown"]}
            else:
                figs[fname] = {"unit_token": f["unit_token"], "fact_id": f["fact_id"], "known": False, "spelled": None}

    def fact(table, row, field, label, **kw):
        rec = {"fact_id": f"{table}.{row}.{field}", "table_id": table, "row_id": row, "field": field, "label": label}
        rec.update(kw)
        facts.append(rec)
        return rec

    by_id = {}

    def known_lineage(derives):
        for d in derives:
            if d.startswith("cp1:"):
                assert cp1[d[4:]]["status"] == "known", (name, d)
            # cp2a:/cp1d: ids are upstream facts (known by construction: only a known copy is read) and own ids are checked at the end

    def num(table, row, field, label, value, uc, formula, value_class="calculated", period=None, derives=(), keep_lineage=False):
        unit = UC_UNIT[uc]
        dec = 2 if uc == "amount" else None
        extra = {"currency": "USD", "scale": "1000000"} if uc == "amount" else {}
        derives = list(derives) if value_class == "calculated" or keep_lineage else []
        known_lineage(derives)
        rec = fact(table, row, field, label, status="known", unit=unit, period=period or LTM_PERIOD, amount_exact=norm(value), shown=show(value, uc, dec),
                   **extra, decimals=dec, value_class=value_class, formula=formula,
                   calculation_id=f"calc:{table}.{row}.{field}" if value_class == "calculated" else None, derives_from=derives)
        by_id[rec["fact_id"]] = rec
        return rec

    def gap(table, row, field, label, uc, reason, status="missing", period=None):
        rec = fact(table, row, field, label, status=status, unit=UC_UNIT[uc], period=period or LTM_PERIOD, amount_exact=None, shown=None, limitation=reason)
        by_id[rec["fact_id"]] = rec
        return rec

    def text(table, row, field, label, value, value_class=None, derives=()):
        rec = fact(table, row, field, label, status="known", text=value, shown=value, value_class=value_class)
        if derives:
            known_lineage(derives)
            rec["derives_from"] = list(derives)
        by_id[rec["fact_id"]] = rec
        return rec

    def missing_text(table, row, field, label, reason):
        """A text-valued cell that cannot be settled: status missing with its root reason (never a known 'Not calculable' text)."""
        rec = fact(table, row, field, label, status="missing", text=None, shown=None, limitation=reason)
        by_id[rec["fact_id"]] = rec
        return rec

    def add_first(table, row, case, kind, result, res, level_why, derives):
        """One first-year cell: a text for a year or 'Not reached', else missing with the root reason (the first year whose test is not calculable)."""
        label = f"First year reached, {CASE_LABEL[case].lower()} case"
        if result != "Not calculable":
            text(table, row, f"{case}_first", label, result, derives=derives)
            return
        t0 = next(t for t, (_value, hit) in enumerate(res) if hit is None)
        reason = level_why or path[case][t0][1][TEST_KEY[kind]]
        assert reason, (name, row, case)
        missing_text(table, row, f"{case}_first", label, reason)

    def reg(table, row_id, label, fields):
        rows_by_table[table].append({"row_id": row_id, "label": label, "fact_ids": [f"{table}.{row_id}.{f}" for f in fields]})

    def val_or_gap(table, row, field, label, value, why, uc, formula, derives, period=None, status="missing"):
        if value is None:
            gap(table, row, field, label, uc, why, status=status, period=period)
        else:
            num(table, row, field, label, value, uc, formula, derives=derives, period=period)

    # --- engine: base and downside ---
    drv = {k: [D(x) for x in sub["base_drivers"][k]["values"]] for k in DRIVERS}
    shock_vals = (D(ds[0]["amount_exact"]) if ds[0]["status"] == "known" else None, D(ds[1]["amount_exact"]) if ds[1]["status"] == "known" else None)
    shock_why = {"s": None if shock_vals[0] is not None else "Not calculable: the CP-2A EBITDA decline is not available",
                 "k": None if shock_vals[1] is not None else "Not calculable: the CP-2A interest increase is not available"}
    path = {"base": run_engine(op, why0, drv, None, {}), "down": run_engine(op, why0, drv, shock_vals, shock_why)}
    for t in range(3):  # the downside never beats the base case on EBITDA, interest or free cash flow (CP-2A shocks are >= 0)
        vb, vd = path["base"][t][0], path["down"][t][0]
        for key, sign in (("E", 1), ("FCF", 1), ("I", -1)):
            if vb[key] is not None and vd[key] is not None:
                assert sign * (vd[key] - vb[key]) <= 0, (name, t, key)
    exact_check(op, drv, None, path["base"])
    exact_check(op, drv, shock_vals, path["down"])
    # repayment never exceeds the opening debt on the base path (the validator rule; the downside holds the same repayments)
    for t, (v, _w) in enumerate(path["base"]):
        if v["Dopen"] is not None:
            assert v["rep"] <= v["Dopen"], (name, t)

    # --- base-year figures (the FY2025 row) ---
    E0, R0, I0, T0, W0, K0, F0, D0, C0, U0 = (op[k] for k in ("ebitda", "revenue", "interest", "taxes", "wc", "capex", "fcf", "debt", "cash", "undrawn"))
    A25 = {}  # FY2025 recomputed quantities
    A25["cfo"] = None if None in (E0, I0, T0, W0) else ex(lambda: E0 - I0 - T0 - W0)
    A25["fcf"] = None if A25["cfo"] is None or K0 is None else ex(lambda: A25["cfo"] - K0)

    up = {"cp1": "CP-1", "cp2a": "CP-2A", "cp1d": "CP-1D"}
    cp1d_why = {"unbound": "CP-1D (earnings quality) is not part of this run",
                "blocked": "CP-1D is blocked, so no supported earnings were settled", "bound": None}[cp1d["state"]]

    # T2H.1 upstream register
    status_cp1d = {"bound": "restricted", "unbound": "not part of this run", "blocked": "blocked"}[cp1d["state"]]
    for row, module, status, basis, read, lim in (
        ("u_cp1", "CP-1", "restricted", f"Base period {LTM_PERIOD}", "T4.10 twelve-month operands and reported ratios",
         "Inherits CP-1's own limitations."),
        ("u_cp2a", "CP-2A", "restricted", f"Base period {cp2a['base_period']}", "T2B.1 scenario shocks and T2B.6 break register",
         "Shock sizes and watch levels are analyst assumptions."),
        ("u_cp1d", "CP-1D", status_cp1d, "Base period " + LTM_PERIOD if cp1d["state"] == "bound" else "Not applicable",
         "T1D.3 supported EBITDA and T1D.6 supported leverage" if cp1d["state"] == "bound" else "Nothing read",
         "Supported EBITDA includes accepted savings not yet realised." if cp1d["state"] == "bound" else (cp1d_why + ".")),
        ("u_cp2d", "CP-2D", "not part of this run", "Not applicable", "Nothing read",
         "CP-2D (liquidity bridge) is an optional input that this version never reads."),
    ):
        text("T2H.1", row, "module", "Module", module)
        text("T2H.1", row, "status", "Status", status)
        text("T2H.1", row, "basis", "Basis", basis)
        text("T2H.1", row, "read", "Read", read)
        text("T2H.1", row, "limitation", "Limitation", lim)
        reg("T2H.1", row, module, ["module", "status", "basis", "read", "limitation"])

    # T2H.2 historical-to-base bridge
    def t2h2(row, label, value, why, uc, formula, derives, basis, check, period=None):
        val_or_gap("T2H.2", row, "value", label, value, why, uc, formula, derives, period)
        text("T2H.2", row, "basis", "Basis", basis)
        text("T2H.2", row, "check", "Check", check)
        reg("T2H.2", row, label, ["value", "basis", "check"])

    for key, label, metric in (("revenue", "Revenue", "revenue"), ("ebitda", "EBITDA", "ebitda"), ("interest", "Cash interest paid (outflow)", "cash_interest"),
                               ("taxes", "Cash taxes paid (outflow)", "cash_taxes"), ("wc", "Working capital movement (outflow)", "working_capital_change"),
                               ("capex", "Capital expenditure (outflow)", "capex")):
        t2h2(key, label, op[key], why0[key], "amount", f"CP-1 {metric}" + (", sign reversed" if key in ("interest", "taxes", "wc", "capex") else ""),
             [f"cp1:{metric}"], f"CP-1 T4.10 {metric} · {LTM_PERIOD}", "Copied from CP-1")
    fcf_ok = A25["fcf"] is not None and cp1["fcf"]["status"] == "known"
    t2h2("fcf", "Free cash flow recomputed", A25["fcf"], "Not calculable: an operand of the statement identity is missing", "amount",
         "EBITDA - cash interest - cash taxes - working capital outflow - capital expenditure", ["cp1:ebitda", "cp1:cash_interest", "cp1:cash_taxes", "cp1:working_capital_change", "cp1:capex"],
         "Statement identity against CP-1 fcf (cp1_references)",
         ("Reconciled to CP-1" if A25["fcf"] == D(cp1["fcf"]["amount_exact"]) else "Differs from CP-1") if fcf_ok else "Not compared")
    for key, label, metric in (("debt", "Total debt", "total_debt"), ("cash", "Cash and cash equivalents", "cash_closing"), ("undrawn", "Undrawn revolver", "undrawn_rcf")):
        t2h2(key, label, op[key], why0[key], "amount", f"CP-1 {metric}", [f"cp1:{metric}"], f"CP-1 T4.10 {metric} · {LTM_PERIOD}", "Copied from CP-1")
    # CP-1D supported figures (the D3 pin: T1D.3.supported.value, T1D.6.supported.total_leverage / net_leverage, read from the CP-1D head)
    s_val = s_tl = s_nl = None
    if cp1d["state"] == "bound":
        s_val, s_tl, s_nl = (cp1d["facts"][i] for i in ("T1D.3.supported.value", "T1D.6.supported.total_leverage", "T1D.6.supported.net_leverage"))
    sup = None if s_val is None else D(s_val["amount_exact"])
    t2h2("ebitda_supported", "EBITDA supported by CP-1D evidence", sup, cp1d_why, "amount", "Copy of CP-1D T1D.3.supported.value",
         ["cp1d:T1D.3.supported.value"], "CP-1D T1D.3 supported adjusted EBITDA", "Copied from CP-1D" if sup is not None else "Not compared")
    adj = None if sup is None or E0 is None else ex(lambda: sup - E0)
    t2h2("ebitda_adjustment", "Earnings-quality adjustment", adj, cp1d_why if sup is None else why0["ebitda"], "amount", "Supported EBITDA - CP-1 EBITDA",
         ["cp1d:T1D.3.supported.value", "cp1:ebitda"], "Supported EBITDA less CP-1 EBITDA", "Computed" if adj is not None else "Not compared")
    tl0 = None if None in (D0, E0) or (E0 is not None and E0 <= 0) else div(D0, E0)
    nl0 = None if None in (D0, C0, E0) or (E0 is not None and E0 <= 0) else div(ex(lambda: D0 - C0), E0)
    why_tl0 = why0["debt"] or why0["ebitda"] or NC_E
    why_nl0 = why0["debt"] or why0["cash"] or why0["ebitda"] or NC_E
    for key, label, val, why, formula, derives, ref_metric in (
        ("total_leverage", "Total leverage on CP-1 EBITDA", tl0, why_tl0, "Total debt / EBITDA", ["cp1:total_debt", "cp1:ebitda"], "total_leverage_reported"),
        ("net_leverage", "Net leverage on CP-1 EBITDA", nl0, why_nl0, "(Total debt - cash) / EBITDA", ["cp1:total_debt", "cp1:cash_closing", "cp1:ebitda"], "net_leverage_reported"),
    ):
        reported_known = cp1[ref_metric]["status"] == "known"
        check = ("Reconciled to CP-1" if val == D(cp1[ref_metric]["amount_exact"]) else "Differs from CP-1") if (val is not None and reported_known) else "Not compared"
        t2h2(key, label, val, why, "multiple", formula, derives, f"Recomputed against CP-1 {ref_metric} (cp1_references)", check)
    t2h2("total_leverage_supported", "Total leverage on CP-1D supported EBITDA", None if s_tl is None else D(s_tl["amount_exact"]), cp1d_why, "multiple",
         "Copy of CP-1D T1D.6.supported.total_leverage", ["cp1d:T1D.6.supported.total_leverage"], "CP-1D T1D.6 supported leverage", "Copied from CP-1D" if s_tl else "Not compared")
    t2h2("net_leverage_supported", "Net leverage on CP-1D supported EBITDA", None if s_nl is None else D(s_nl["amount_exact"]), cp1d_why, "multiple",
         "Copy of CP-1D T1D.6.supported.net_leverage", ["cp1d:T1D.6.supported.net_leverage"], "CP-1D T1D.6 supported leverage", "Copied from CP-1D" if s_nl else "Not compared")

    # T2H.3 assumption register: analyst drivers, the CP-2A shock copies, minimum liquidity
    for n, key in enumerate(DRIVERS, 1):
        row = f"a{n:02d}"
        text("T2H.3", row, "case", "Case", "Base")
        text("T2H.3", row, "driver", "Driver", DRIVER_LABEL[key])
        for t in range(3):
            num("T2H.3", row, f"fy{t + 1}", FY[t], drv[key][t], DRIVER_UC[key], "analyst input", "analyst_judgment", period=FY_PERIOD[t])
        text("T2H.3", row, "class", "Class", "analyst_judgment")
        text("T2H.3", row, "source", "Source", "Analyst assumption")
        reg("T2H.3", row, DRIVER_LABEL[key], ["case", "driver", "fy1", "fy2", "fy3", "class", "source"])
    for row, label, fact_ref, source in (("d01", "EBITDA decline against the base case", ds[0], f"CP-2A {ds[0]['fact_id']}"),
                                         ("d02", "Increase in the cash interest rate", ds[1], f"CP-2A {ds[1]['fact_id']}")):
        text("T2H.3", row, "case", "Case", "Downside")
        text("T2H.3", row, "driver", "Driver", label)
        for t in range(3):
            if fact_ref["status"] == "known":
                num("T2H.3", row, f"fy{t + 1}", FY[t], D(fact_ref["amount_exact"]), "percent", f"Copy of CP-2A {fact_ref['fact_id']}",
                    fact_ref["value_class"], period=FY_PERIOD[t])
            else:
                gap("T2H.3", row, f"fy{t + 1}", FY[t], "percent", fact_ref["limitation"], period=FY_PERIOD[t])
        text("T2H.3", row, "class", "Class", fact_ref["value_class"] or "analyst_judgment")
        text("T2H.3", row, "source", "Source", source)
        reg("T2H.3", row, label, ["case", "driver", "fy1", "fy2", "fy3", "class", "source"])
    min_amount = sub["minimum_liquidity"]["amount"]
    min_liq = None if min_amount == NOT_ASSESSED else D(min_amount)
    text("T2H.3", "m01", "case", "Case", "Both")
    text("T2H.3", "m01", "driver", "Driver", "Minimum liquidity")
    for t in range(3):
        if min_liq is None:
            gap("T2H.3", "m01", f"fy{t + 1}", FY[t], "amount", "Minimum liquidity was not assessed", period=FY_PERIOD[t])
        else:
            num("T2H.3", "m01", f"fy{t + 1}", FY[t], min_liq, "amount", "analyst input", "analyst_judgment", period=FY_PERIOD[t])
    text("T2H.3", "m01", "class", "Class", "analyst_judgment")
    text("T2H.3", "m01", "source", "Source", "Analyst assumption" if min_liq is not None else "Not assessed")
    reg("T2H.3", "m01", "Minimum liquidity", ["case", "driver", "fy1", "fy2", "fy3", "class", "source"])

    # T2H.4 / T2H.5 / T2H.6
    def ys(case):
        return path[case]

    a25 = "a25"
    base_derives = {"revenue": ["cp1:revenue"], "ebitda": ["cp1:ebitda"], "capex": ["cp1:capex"]}
    num_or = lambda table, row, field, label, value, why, uc, formula, derives, period=None, status="missing": val_or_gap(table, row, field, label, value, why, uc, formula, derives, period, status)
    num_or("T2H.4", a25, "revenue", "Revenue", R0, why0["revenue"], "amount", "CP-1 revenue", ["cp1:revenue"])
    num_or("T2H.4", a25, "ebitda", "EBITDA", E0, why0["ebitda"], "amount", "CP-1 EBITDA", ["cp1:ebitda"])
    marg0 = None if None in (E0, R0) or (R0 is not None and R0 <= 0) else div(E0, R0)
    num_or("T2H.4", a25, "margin", "EBITDA margin", marg0, why0["ebitda"] or why0["revenue"] or "Not calculable: revenue is zero or negative", "percent", "EBITDA / revenue", ["cp1:ebitda", "cp1:revenue"])
    num_or("T2H.4", a25, "cfo", "Cash flow after interest, taxes and working capital", A25["cfo"], why0["ebitda"] or why0["interest"] or why0["taxes"] or why0["wc"], "amount",
           "EBITDA - cash interest - cash taxes - working capital outflow", ["cp1:ebitda", "cp1:cash_interest", "cp1:cash_taxes", "cp1:working_capital_change"])
    num_or("T2H.4", a25, "capex", "Capital expenditure (outflow)", K0, why0["capex"], "amount", "CP-1 capital expenditure, sign reversed", ["cp1:capex"])
    num_or("T2H.4", a25, "fcf", "Free cash flow", A25["fcf"], why0["ebitda"] or why0["interest"] or why0["taxes"] or why0["wc"] or why0["capex"], "amount", "Cash flow after interest, taxes and working capital - capital expenditure",
           [f"T2H.4.{a25}.cfo", f"T2H.4.{a25}.capex"])
    reg("T2H.4", a25, "FY2025 actual", ["revenue", "ebitda", "margin", "cfo", "capex", "fcf"])
    rowlabels = {}
    for case in ("base", "down"):
        for t in range(3):
            v, w = ys(case)[t]
            r = f"{ROW_PREFIX[case]}{26 + t}"
            lab = f"{CASE_LABEL[case]} case {FY[t]}"
            rowlabels[(case, t)] = (r, lab)
            prev_r = a25 if t == 0 else f"{ROW_PREFIX[case]}{25 + t}"
            pr = FY_PERIOD[t]
            rev_d = [f"T2H.4.{prev_r}.revenue", f"T2H.3.a01.fy{t + 1}"]
            num_or("T2H.4", r, "revenue", "Revenue", v["R"], w["R"], "amount", "Prior revenue x (1 + growth)", rev_d, pr)
            e_d = [f"T2H.4.{r}.revenue", f"T2H.3.a02.fy{t + 1}"] + ([f"T2H.3.d01.fy{t + 1}", f"cp2a:{ds[0]['fact_id']}"] if case == "down" else [])
            e_f = "Revenue x margin" if case == "base" else "Revenue x margin x (1 - CP-2A EBITDA decline)"
            num_or("T2H.4", r, "ebitda", "EBITDA", v["E"], w["E"], "amount", e_f, e_d, pr)
            m_ = None if v["E"] is None or v["R"] is None else (div(v["E"], v["R"]) if v["R"] > 0 else None)
            num_or("T2H.4", r, "margin", "EBITDA margin", m_, w["E"] or w["R"] or "Not calculable: revenue is zero or negative", "percent", "EBITDA / revenue",
                   [f"T2H.4.{r}.ebitda", f"T2H.4.{r}.revenue"], pr)
            cfo_d = [f"T2H.4.{r}.ebitda", f"T2H.5.{r}.interest", f"T2H.3.a04.fy{t + 1}", f"T2H.4.{r}.revenue"]
            num_or("T2H.4", r, "cfo", "Cash flow after interest, taxes and working capital", v["CFO"], w["CFO"], "amount",
                   "EBITDA - cash interest - revenue x (taxes and working capital share)", cfo_d, pr)
            num_or("T2H.4", r, "capex", "Capital expenditure (outflow)", v["K"], w["K"], "amount", "Revenue x capital expenditure share",
                   [f"T2H.4.{r}.revenue", f"T2H.3.a03.fy{t + 1}"], pr)
            num_or("T2H.4", r, "fcf", "Free cash flow", v["FCF"], w["FCF"], "amount", "Cash flow after interest, taxes and working capital - capital expenditure",
                   [f"T2H.4.{r}.cfo", f"T2H.4.{r}.capex"], pr)
            reg("T2H.4", r, lab, ["revenue", "ebitda", "margin", "cfo", "capex", "fcf"])
    # T2H.5 needs the T2H.4 interest lineage id: interest lives in T2H.5
    for case in ("base", "down"):
        for t in range(3):
            v, w = ys(case)[t]
            r, lab = rowlabels[(case, t)]
            prev_r = None if t == 0 else rowlabels[(case, t - 1)][0]
            pr = FY_PERIOD[t]
            od = ["cp1:total_debt"] if t == 0 else [f"T2H.5.{prev_r}.closing_debt"]
            oc = ["cp1:cash_closing"] if t == 0 else [f"T2H.5.{prev_r}.closing_cash"]
            num_or("T2H.5", r, "opening_debt", "Opening debt", v["Dopen"], w["Dopen"], "amount", "CP-1 total debt" if t == 0 else "Prior closing debt", od, pr)
            num("T2H.5", r, "repayment", "Debt repayment (outflow)", v["rep"], "amount", "analyst input", "analyst_judgment", period=pr)
            num_or("T2H.5", r, "closing_debt", "Closing debt", v["Dclose"], w["Dclose"], "amount", "Opening debt - repayment", [f"T2H.5.{r}.opening_debt", f"T2H.3.a07.fy{t + 1}"], pr)
            i_d = [f"T2H.5.{r}.opening_debt", f"T2H.3.a05.fy{t + 1}"] + ([f"T2H.3.d02.fy{t + 1}", f"cp2a:{ds[1]['fact_id']}"] if case == "down" else [])
            i_f = "Opening debt x rate" if case == "base" else "Opening debt x rate x (1 + CP-2A interest increase)"
            num_or("T2H.5", r, "interest", "Cash interest (outflow)", v["I"], w["I"], "amount", i_f, i_d, pr)
            num_or("T2H.5", r, "opening_cash", "Opening cash", v["Copen"], w["Copen"], "amount", "CP-1 cash and cash equivalents" if t == 0 else "Prior closing cash", oc, pr)
            num_or("T2H.5", r, "fcf", "Free cash flow", v["FCF"], w["FCF"], "amount", "From T2H.4", [f"T2H.4.{r}.fcf"], pr)
            num("T2H.5", r, "dividends", "Distributions (outflow)", v["div"], "amount", "analyst input", "analyst_judgment", period=pr)
            num_or("T2H.5", r, "closing_cash", "Closing cash", v["Cclose"], w["Cclose"], "amount", "Opening cash + free cash flow - distributions - repayment",
                   [f"T2H.5.{r}.opening_cash", f"T2H.5.{r}.fcf", f"T2H.3.a06.fy{t + 1}", f"T2H.5.{r}.repayment"], pr)
            num_or("T2H.5", r, "undrawn_revolver", "Undrawn revolver", v["U"], w["U"], "amount", "CP-1 undrawn revolver, held", ["cp1:undrawn_rcf"], pr)
            num_or("T2H.5", r, "accessible_liquidity", "Accessible liquidity", v["Liq"], w["Liq"], "amount", "Closing cash + undrawn revolver",
                   [f"T2H.5.{r}.closing_cash", f"T2H.5.{r}.undrawn_revolver"], pr)
            reg("T2H.5", r, lab, ["opening_debt", "repayment", "closing_debt", "interest", "opening_cash", "fcf", "dividends", "closing_cash",
                                  "undrawn_revolver", "accessible_liquidity"])

    # T2H.6 credit metrics
    def t26(row, lab, pr, vals, whys, derive, liq_value, liq_why, liq_derive, liq_status="missing"):
        for field, label, uc, formula in (("total_leverage", "Total leverage", "multiple", "Closing debt / EBITDA"),
                                          ("net_leverage", "Net leverage", "multiple", "(Closing debt - closing cash) / EBITDA"),
                                          ("interest_coverage", "Interest coverage", "multiple", "EBITDA / cash interest"),
                                          ("fcf_to_debt", "Free cash flow to debt", "percent", "Free cash flow / closing debt")):
            num_or("T2H.6", row, field, label, vals[field], whys[field], uc, formula, derive[field], pr)
        num_or("T2H.6", row, "liquidity_headroom", "Accessible liquidity less minimum liquidity", liq_value, liq_why, "amount",
               "Accessible liquidity - minimum liquidity", liq_derive, pr, liq_status)
        reg("T2H.6", row, lab, ["total_leverage", "net_leverage", "interest_coverage", "fcf_to_debt", "liquidity_headroom"])

    vals25 = {"total_leverage": tl0, "net_leverage": nl0, "interest_coverage": None if None in (E0, I0) or (I0 is not None and I0 <= 0) else div(E0, I0),
              "fcf_to_debt": None if None in (A25["fcf"], D0) or (D0 is not None and D0 <= 0) else div(A25["fcf"], D0)}
    whys25 = {"total_leverage": why_tl0, "net_leverage": why_nl0, "interest_coverage": why0["ebitda"] or why0["interest"] or NC_I,
              "fcf_to_debt": why0["debt"] or why0["ebitda"] or why0["interest"] or why0["taxes"] or why0["wc"] or why0["capex"] or NC_D}
    t26_derive25 = {"total_leverage": ["cp1:total_debt", "cp1:ebitda"], "net_leverage": ["cp1:total_debt", "cp1:cash_closing", "cp1:ebitda"],
                    "interest_coverage": ["cp1:ebitda", "cp1:cash_interest"], "fcf_to_debt": [f"T2H.4.{a25}.fcf", "cp1:total_debt"]}
    # ruling L2: the minimum liquidity is a forecast-year assumption, so the FY2025 actual has no headroom to test
    t26(a25, "FY2025 actual", LTM_PERIOD, vals25, whys25, t26_derive25, None, LIQ_HEADROOM_FY25, [], "not_applicable")
    for case in ("base", "down"):
        for t in range(3):
            v, w = ys(case)[t]
            r, lab = rowlabels[(case, t)]
            vals = {"total_leverage": v["TL"], "net_leverage": v["NL"], "interest_coverage": v["IC"], "fcf_to_debt": v["FD"]}
            whys = {"total_leverage": w["TL"], "net_leverage": w["NL"], "interest_coverage": w["IC"], "fcf_to_debt": w["FD"]}
            dv = {"total_leverage": [f"T2H.5.{r}.closing_debt", f"T2H.4.{r}.ebitda"],
                  "net_leverage": [f"T2H.5.{r}.closing_debt", f"T2H.5.{r}.closing_cash", f"T2H.4.{r}.ebitda"],
                  "interest_coverage": [f"T2H.4.{r}.ebitda", f"T2H.5.{r}.interest"], "fcf_to_debt": [f"T2H.5.{r}.fcf", f"T2H.5.{r}.closing_debt"]}
            if min_liq is None:
                lv, lw = None, "Not calculable: minimum liquidity was not assessed"
            elif v["Liq"] is None:
                lv, lw = None, w["Liq"]
            else:
                lv, lw = ex(lambda: v["Liq"] - min_liq), None
            t26(r, lab, FY_PERIOD[t], vals, whys, dv, lv, lw, [f"T2H.5.{r}.accessible_liquidity", f"T2H.3.m01.fy{t + 1}"])
    # --- T2H.7 break-point timing (CP-2A levels along the forward path) ---
    metric_of = {m["break_id"]: m["metric"] for m in sub["break_metrics"]}
    breaks = []
    unverified = []  # (break row, reason text): why the analyst's metric could not be checked against CP-2A's required decline
    for b in cp2a["breaks"]:
        lvl = b["level"]
        if b["origin"] == "Definition":
            assert b["test"] in (DEF_FCF, DEF_COV), b["test"]
            kind = "fcf" if b["test"] == DEF_FCF else "coverage"
        else:
            kind = {"interest_coverage": "coverage"}.get(metric_of[b["row"]], metric_of[b["row"]])
            # the metric must reproduce CP-2A's required decline where CP-2A and CP-2G share the base period
            rd = b["required_decline"]
            if cp2a["base_period"] != LTM_PERIOD:
                unverified.append((b["row"], UNVERIFIED_PERIOD))
            elif rd["status"] != "known" or lvl["status"] != "known":
                unverified.append((b["row"], UNVERIFIED_CP2A))
            else:
                s_star = break_decline(kind, D(lvl["amount_exact"]), op)
                if s_star is None:  # a CP-1 operand the check needs is missing: the mapping cannot be verified
                    unverified.append((b["row"], unverified_operand_reason(kind, op)))
                else:
                    assert q38(s_star) == D(rd["amount_exact"]), (name, b["row"], kind)
        breaks.append(dict(b, kind=kind))
    for b in breaks:
        r = b["row"]
        lvl = b["level"]
        lvl_known = lvl["status"] == "known"
        lvl_d = D(lvl["amount_exact"]) if lvl_known else None
        uc_level = "amount" if b["kind"] == "fcf" else "multiple"
        text("T2H.7", r, "test", "Test", b["test"])
        text("T2H.7", r, "metric", "Metric", KIND_METRIC[b["kind"]])
        level_id = f"cp2a:T2B.6.{r}.level"
        if lvl_known:
            # a copy of a CP-2A cell lists the CP-2A fact it copies in derives_from whatever the cell's class (D3 proof, ruling H1)
            num("T2H.7", r, "level", "Level", lvl_d, uc_level, f"Copy of CP-2A T2B.6.{r}.level", lvl["value_class"], derives=[level_id], keep_lineage=True)
        else:
            gap("T2H.7", r, "level", "Level", uc_level, lvl["limitation"])
        rd = b["required_decline"]
        if rd["status"] == "known":
            num("T2H.7", r, "static_decline", "CP-2A required EBITDA decline", D(rd["amount_exact"]), "percent",
                f"Copy of CP-2A T2B.6.{r}.required_decline", rd["value_class"], derives=[f"cp2a:T2B.6.{r}.required_decline"], keep_lineage=True)
        else:
            gap("T2H.7", r, "static_decline", "CP-2A required EBITDA decline", "percent", rd["limitation"], status=rd["status"])
        level_why = None if lvl_known else lvl["limitation"]
        for case in ("base", "down"):
            res = [test_year(b["kind"], lvl_d, ys(case)[t][0]) for t in range(3)]
            b[case] = res
            b[case + "_first"] = first_result(res)
            add_first("T2H.7", r, case, b["kind"], b[case + "_first"], res, level_why, [level_id])
        reg("T2H.7", r, b["test"], ["test", "metric", "level", "static_decline", "base_first", "down_first"])
    # liquidity test (analyst minimum liquidity)
    liq = {"row": "m01", "kind": "liquidity", "test": "Accessible liquidity below the minimum liquidity"}
    text("T2H.7", "m01", "test", "Test", liq["test"])
    text("T2H.7", "m01", "metric", "Metric", KIND_METRIC["liquidity"])
    if min_liq is None:
        gap("T2H.7", "m01", "level", "Level", "amount", "Minimum liquidity was not assessed")
    else:
        num("T2H.7", "m01", "level", "Level", min_liq, "amount", "analyst input", "analyst_judgment")
    gap("T2H.7", "m01", "static_decline", "CP-2A required EBITDA decline", "percent", "CP-2A has no liquidity test", status="not_applicable")
    for case in ("base", "down"):
        res = [test_year("liquidity", min_liq, ys(case)[t][0]) for t in range(3)]
        liq[case] = res
        liq[case + "_first"] = first_result(res)
        add_first("T2H.7", "m01", case, "liquidity", liq[case + "_first"], res, "Not calculable: minimum liquidity was not assessed" if min_liq is None else None, [])
    reg("T2H.7", "m01", liq["test"], ["test", "metric", "level", "static_decline", "base_first", "down_first"])
    all_tests = breaks + [liq]
    # --- T2H.8 deleveraging path ---
    traj = {}
    for case in ("base", "down"):
        r = case
        tls = [ys(case)[t][0]["TL"] for t in range(3)]
        last = tls[-1]
        change = None if last is None or tl0 is None else sub38(last, tl0)
        peak = None if any(x is None for x in tls) else max(tls)
        peak_year = None if peak is None else FY[tls.index(peak)]
        why_t = ys(case)[2][1]["TL"] or why_tl0
        if change is None:  # ruling L5 applied to the trajectory: missing with the root reason, never a known 'Not calculable' text
            missing_text("T2H.8", r, "trajectory", "Trajectory", why_t if last is None else why_tl0)
        else:
            text("T2H.8", r, "trajectory", "Trajectory", "Deleveraging" if change < 0 else "Releveraging" if change > 0 else "Flat")
        val_or_gap("T2H.8", r, "total_leverage_fy28", f"Total leverage {FY[-1]}", last, why_t, "multiple", "From T2H.6", [f"T2H.6.{rowlabels[(case, 2)][0]}.total_leverage"], FY_PERIOD[-1])
        val_or_gap("T2H.8", r, "change_vs_fy25", f"Change from FY{BASE_YEAR}", change, why_t if last is None else why_tl0, "multiple", "Total leverage FY2028 - total leverage FY2025",
                   [f"T2H.8.{r}.total_leverage_fy28", f"T2H.2.total_leverage.value"], FY_PERIOD[-1])
        why_peak = next((ys(case)[t][1]["TL"] for t in range(3) if ys(case)[t][0]["TL"] is None), None)
        val_or_gap("T2H.8", r, "peak_total_leverage", "Peak total leverage in the forecast", peak, why_peak, "multiple", "Highest total leverage of the three forecast years",
                   [f"T2H.6.{rowlabels[(case, t)][0]}.total_leverage" for t in range(3)], FY_SPAN_PERIOD if peak is None else FY_PERIOD[tls.index(peak)])
        if peak_year is None:
            fact("T2H.8", r, "peak_period", "Peak year", status="missing", text=None, shown=None, limitation=why_peak)
            by_id[f"T2H.8.{r}.peak_period"] = facts[-1]
        else:
            text("T2H.8", r, "peak_period", "Peak year", peak_year)
        e26 = ys(case)[0][0]["E"]
        vs_sup = None if e26 is None or sup is None else ex(lambda: e26 - sup)
        val_or_gap("T2H.8", r, "ebitda_fy26_vs_supported", f"{FY[0]} EBITDA less CP-1D supported EBITDA", vs_sup,
                   cp1d_why if sup is None else ys(case)[0][1]["E"], "amount", "Forecast EBITDA - CP-1D supported EBITDA",
                   [f"T2H.4.{rowlabels[(case, 0)][0]}.ebitda", "cp1d:T1D.3.supported.value"], FY_PERIOD[0])
        text("T2H.8", r, "downstream", "Downstream modules", "CP-2H, CP-4C")
        reg("T2H.8", r, CASE_LABEL[case] + " case", ["trajectory", "total_leverage_fy28", "change_vs_fy25", "peak_total_leverage", "peak_period", "ebitda_fy26_vs_supported", "downstream"])
        traj[case] = {"change": change, "peak": peak, "peak_year": peak_year}
    # --- T2H.9 gaps ledger ---
    for n, g in enumerate(sub["gaps"], 1):
        r = f"g{n:02d}"
        text("T2H.9", r, "id", "Gap id", f"CP-2G-GAP-{n:03d}")
        for fld, label in (("gap", "Gap"), ("why_it_matters", "Why it matters"), ("affected_analysis", "Affected analysis")):
            text("T2H.9", r, fld, label, g[fld], "analyst_judgment")
        text("T2H.9", r, "severity", "Severity", g["severity"])
        text("T2H.9", r, "action", "Action", g["action"], "analyst_judgment")
        reg("T2H.9", r, f"Gap {n}", ["id", "gap", "why_it_matters", "affected_analysis", "severity", "action"])

    # --- references: CP-1, CP-2A, CP-1D facts copied verbatim ---
    named = []
    for t_ in prose_texts(sub):
        named += re.findall(r"FIG:([a-z_]+)", t_)
    cp1_named = [n_ for n_ in dict.fromkeys(named) if FIGS[n_]["source"] == "cp1"]
    for n_ in cp1_named:
        assert cp1[FIGS[n_]["metric"]]["status"] == "known", (name, n_)
    ref_metrics = list(dict.fromkeys([FIGS[n_]["metric"] for n_ in cp1_named] + ["fcf", "total_leverage_reported", "net_leverage_reported"]))
    ref_rows = []
    for n, metric in enumerate(ref_metrics, 1):
        src = cp1[metric]
        fig_name = next((k for k in cp1_named if FIGS[k]["metric"] == metric), None)
        ref_rows.append({
            "row_id": f"ref{n:02d}", "figure": fig_name, "label": f"{src['label']} · {src['period']}", "cp1_label": src["label"], "period": src["period"],
            "status": src["status"], "unit": {"amount": "US$ m", "percent": "%", "multiple": "x"}[src["unit_class"]], "shown": figs[fig_name]["spelled"] if fig_name else (src["cell_text"] + (" US$ m" if src["unit_class"] == "amount" else "") if src["status"] == "known" else None),
            "cell_text": src["cell_text"], "value_class": src["value_class"], "amount_exact": src["amount_exact"], "limitation": src["limitation"],
            "fact_id": "bound at run time: the unique T4.10 fact with label cp1_label (manifest.json fact_selection_rule); the module carries the CP-1 fact verbatim under this fact_id",
        })
    cp1_references = {"table_id": "cp1_references", "title": "CP-1 facts referenced in CP-2G text and compared in T2H.2", "row_header": "CP-1 fact", "rows": ref_rows}

    def up_row(n, f, figure=None):
        return {"row_id": f"ref{n:02d}", "figure": figure, "fact_id": f["fact_id"], "label": f.get("label"), "period": f.get("period"), "status": f["status"],
                "unit": f.get("unit"), "shown": f.get("shown"), "value_class": f.get("value_class"), "amount_exact": f.get("amount_exact"),
                "limitation": f.get("limitation")}

    cp2a_rows, n = [], 0
    for fobj in (scen["decline"], scen["increase"]):
        n += 1
        cp2a_rows.append(up_row(n, fobj))
    for b in cp2a["breaks"]:
        for fobj in (b["level"], b["required_decline"]):
            n += 1
            cp2a_rows.append(up_row(n, fobj))
    cp2a_references = {"table_id": "cp2a_references", "title": "CP-2A facts copied into CP-2G (T2B.1 scenario, T2B.6 breaks)", "row_header": "CP-2A fact", "rows": cp2a_rows}
    cp1d_rows = []
    if cp1d["state"] == "bound":
        for n, (fid, f) in enumerate(cp1d["facts"].items(), 1):
            cp1d_rows.append(up_row(n, f, "total_leverage_supported" if fid == "T1D.6.supported.total_leverage" else None))
    cp1d_references = {"table_id": "cp1d_references", "title": "CP-1D facts copied into CP-2G (T1D.3 and T1D.6)", "row_header": "CP-1D fact", "rows": cp1d_rows,
                       **({} if cp1d["state"] == "bound" else {"note": cp1d_why})}

    # every fact exists; a known fact never derives from an own fact that is not known
    by_final = {x["fact_id"]: x for x in facts}
    assert len(by_final) == len(facts), "duplicate fact id"
    for x in facts:
        for d_ in x.get("derives_from", []):
            if x["status"] == "known" and not d_.startswith(("cp1:", "cp2a:", "cp1d:")):
                assert by_final[d_]["status"] == "known", (name, x["fact_id"], d_)

    # --- claims (Python templates; analyst prose is resolved through the reference tables; chips for unsettled facts) ---
    def ref(fid, token):
        x = by_final[fid]
        return "{" + fid + "|" + token + "}" if x["status"] == "known" else "[" + fid + "]"

    def rendered(text_):
        def one(m):
            fid, token = m.group(1), m.group(2)
            x = by_final[fid]
            return x["shown"] + (" US$ m" if token == "US$ m" else "")
        out_ = re.sub(r"\{([A-Za-z0-9_.:-]+)\|([^}]*)\}", one, text_)
        return re.sub(r"\[([A-Za-z0-9_.:-]+)\]", lambda m: "[" + m.group(1) + "]", out_)

    def claim(cid, text_, limitation, refs=(), python=False):
        if python and cid.split(".")[0] == "T2H" and cid.split(".")[1] in ("4", "5", "6", "7", "8"):
            assert limitation is None
            limitation = FORECAST_LIMITATION  # ruling L12: a forecast claim carries the analyst-assumed-drivers limitation
        entry = {"claim_id": cid, "text": text_, "limitation": limitation, "citations": [], "cp1_references": list(refs)}
        if refs:
            entry["text_rendered"] = spell_figs(text_, figs)
        claim_list.append(entry)

    for key in DRIVERS:
        d_ = sub["base_drivers"][key]
        claim(f"T2H.3.{key}", d_["rationale"], d_["limitation"], re.findall(r"FIG:([a-z_]+)", d_["rationale"]))
    claim("T2H.3.downside", sub["downside"]["rationale"], sub["downside"]["limitation"], re.findall(r"FIG:([a-z_]+)", sub["downside"]["rationale"]))
    claim("T2H.3.minimum_liquidity", sub["minimum_liquidity"]["rationale"], None if min_liq is not None else "Minimum liquidity was not assessed.", [])
    for case in ("base", "down"):
        r28, r25 = rowlabels[(case, 2)][0], a25
        lab = CASE_LABEL[case].lower()
        claim(f"T2H.4.{case}", f"In the {lab} case, EBITDA reaches {ref(f'T2H.4.{r28}.ebitda', 'US$ m')} in {FY[2]} against {ref(f'T2H.4.{r25}.ebitda', 'US$ m')} in FY{BASE_YEAR} "
              f"and free cash flow reaches {ref(f'T2H.4.{r28}.fcf', 'US$ m')}.", None, python=True)
    for case in ("base", "down"):
        r28, r26 = rowlabels[(case, 2)][0], rowlabels[(case, 0)][0]
        lab = CASE_LABEL[case].lower()
        if case == "base":
            t_ = (f"In the base case, total leverage moves from {ref(f'T2H.6.{a25}.total_leverage', 'x')} in FY{BASE_YEAR} to {ref(f'T2H.6.{r28}.total_leverage', 'x')} in {FY[2]} "
                  f"and interest coverage from {ref(f'T2H.6.{a25}.interest_coverage', 'x')} to {ref(f'T2H.6.{r28}.interest_coverage', 'x')}.")
        else:
            t_ = (f"In the downside case, total leverage is {ref(f'T2H.6.{r26}.total_leverage', 'x')} in {FY[0]} and {ref(f'T2H.6.{r28}.total_leverage', 'x')} in {FY[2]}, "
                  f"and interest coverage in {FY[0]} is {ref(f'T2H.6.{r26}.interest_coverage', 'x')}.")
        claim(f"T2H.6.{case}", t_, None, python=True)
    d26, d27 = rowlabels[("down", 0)][0], rowlabels[("down", 1)][0]
    claim("T2H.5.down", f"In the downside case, closing cash is {ref(f'T2H.5.{d26}.closing_cash', 'US$ m')} in {FY[0]} and {ref(f'T2H.5.{d27}.closing_cash', 'US$ m')} in {FY[1]}.", None, python=True)
    for case in ("base", "down"):
        lab = CASE_LABEL[case].lower()
        reached = [(b, b[case + "_first"]) for b in all_tests if b[case + "_first"] not in ("Not calculable",) and not b[case + "_first"].startswith("Not reached")]
        if reached:
            first_year = min(FY.index(y) for _b, y in reached)
            names_ = [b["test"] for b, y in reached if FY.index(y) == first_year]
            joined = names_[0] if len(names_) == 1 else ", ".join(names_[:-1]) + " and " + names_[-1]
            claim(f"T2H.7.{case}", f"The first {'test' if len(names_) == 1 else 'tests'} reached in the {lab} case {'is' if len(names_) == 1 else 'are'} {joined} in {FY[first_year]}.", None, python=True)
        elif all(b[case + "_first"].startswith("Not reached") for b in all_tests):
            claim(f"T2H.7.{case}", f"No tested break point is reached in the {lab} case through {FY[-1]}.", None, python=True)
        else:
            claim(f"T2H.7.{case}", f"In the {lab} case no tested break point is reached, but not every test is calculable.", None, python=True)
    for case in ("base", "down"):
        lab = CASE_LABEL[case].lower()
        r = case
        if by_final[f"T2H.8.{r}.peak_total_leverage"]["status"] == "known" and by_final[f"T2H.8.{r}.total_leverage_fy28"]["status"] == "known":
            claim(f"T2H.8.{case}", f"In the {lab} case, total leverage peaks at {ref(f'T2H.8.{r}.peak_total_leverage', 'x')} in {traj[case]['peak_year']} and ends {FY[2]} at "
                  f"{ref(f'T2H.8.{r}.total_leverage_fy28', 'x')}.", None, python=True)
        else:
            claim(f"T2H.8.{case}", f"In the {lab} case, the leverage path is not fully calculable: peak [T2H.8.{r}.peak_total_leverage], {FY[2]} [T2H.8.{r}.total_leverage_fy28].", None, python=True)
    if cp1d["state"] == "bound":
        claim("T2H.2.cp1d", f"On the earnings CP-1D supports, opening total leverage is {ref('T2H.2.total_leverage_supported.value', 'x')} against {ref('T2H.2.total_leverage.value', 'x')} on reported earnings.",
              None, python=True)
    a = sub["assessment"]
    claim("T2H.3.assessment", a["rationale"], a["limitation"], re.findall(r"FIG:([a-z_]+)", a["rationale"]))
    for c in claim_list:
        if "text_rendered" not in c:
            c["text_rendered"] = rendered(c["text"])

    # --- own limitations (exact strings) ---
    own_limits.append("Driver values are analyst assumptions without a source citation; no management guidance or consensus is an input.")
    own_limits.append("The forecast is annual over three years from the CP-1 twelve-month base; no quarterly path is modelled.")
    own_limits.append("Cash interest is the analyst's rate applied to the opening debt balance; no hedging, floor or reference-rate curve is modelled.")
    own_limits.append("Cash taxes and working capital are modelled together as a share of revenue; no tax shield or working-capital cycle is modelled.")
    own_limits.append("No new borrowing, refinancing or covenant waiver is modelled: debt moves only by the analyst's repayments, and cash is not floored, so a negative cash balance is an unfunded requirement, not a forecast of events.")
    own_limits.append("The downside applies CP-2A's settled scenario shocks to every forecast year and holds revenue, capital expenditure, distributions and repayments at the base case; no mitigating action is modelled.")
    own_limits.append("The break tests reuse CP-2A's levels, which are watch levels and definitions, not covenant tests; covenant compliance belongs to CP-4.")
    own_limits.append("Accessible liquidity is closing cash plus CP-1's undrawn revolver; restricted, trapped or operationally required cash is not separated.")
    own_limits.append("Debt maturities and refinancing feasibility are not modelled; the maturity wall and funding gap belong to CP-2D and CP-3C.")
    if cp1d["state"] == "bound":
        own_limits.append("CP-1D's supported EBITDA includes accepted savings not yet realised; it is shown for starting leverage and comparison only and is not a forecast base.")
    elif cp1d["state"] == "unbound":
        own_limits.append("CP-1D (earnings quality) is not part of this run, so starting leverage is not restated on evidence-supported EBITDA and no comparison with it is made.")
    else:
        own_limits.append("CP-1D (earnings quality) is bound but blocked, so starting leverage is not restated on evidence-supported EBITDA and no comparison with it is made.")
    if min_liq is None:
        own_limits.append("Minimum liquidity was not assessed, so the liquidity break test and liquidity headroom are not calculated.")
    else:
        own_limits.append("Minimum liquidity is an analyst assumption, not a source figure.")
    for key, value in op.items():
        if value is None:
            own_limits.append(f"Base {WORDS[key]} is not available in CP-1 for {LTM_PERIOD}: every figure that needs it is Not calculable.")
    if cp2a["base_period"] != LTM_PERIOD:
        own_limits.append(f"CP-2A stressed the base period {cp2a['base_period']}; its required declines are shown for reference and are not comparable with the twelve-month forward path.")
    for row, reason in unverified:
        own_limits.append(f"The metric named for CP-2A break {row} could not be checked against its CP-2A required decline: {reason}.")
    for case in ("base", "down"):
        years_neg = [FY[t] for t in range(3) if ys(case)[t][0]["Cclose"] is not None and ys(case)[t][0]["Cclose"] < 0]
        if years_neg:
            own_limits.append(f"In the {CASE_LABEL[case].lower()} case closing cash is negative from {years_neg[0]}: an unfunded requirement, not a forecast of events.")
    if any(b[case + "_first"] == "Not calculable" for b in all_tests for case in ("base", "down")):
        own_limits.append("A break test whose metric is not calculable in a forecast year is missing, with the reason, when no earlier year has met it.")
    if any(x["change"] is None for x in traj.values()):
        own_limits.append("A leverage trajectory that cannot be calculated is missing, with the reason, not a known text.")
    for g in sub["gaps"]:
        own_limits.append(f"Gap ({g['severity']}): {g['gap']}")

    module_tables = [{"table_id": t, "title": title, "rows": rows_by_table[t]} for t, title in TABLES.items()]
    summary = {}
    for case in ("base", "down"):
        summary[case] = []
        for t in range(3):
            v, _w = ys(case)[t]
            summary[case].append({"year": FY[t], **{k: (None if v[k] is None else norm(v[k])) for k in
                                  ("R", "E", "I", "X", "K", "CFO", "FCF", "Dopen", "Dclose", "Copen", "Cclose", "Liq", "TL", "NL", "IC", "FD")}})
    return {
        "base_period": LTM_PERIOD, "forecast_years": FY,
        "base_operands": {k: (None if v is None else norm(v)) for k, v in op.items()},
        "base_missing": {k: w for k, w in why0.items() if w},
        "cp1_inputs": cp1, "cp2a_head": {"source": cp2a["source"], "base_period": cp2a["base_period"], "downside_scenario": sub["downside"]["scenario"],
                                         "downside_name": scen["name"], "break_rows": [b["row"] for b in cp2a["breaks"]]},
        "cp1d_head": {"state": cp1d["state"], "source": "cases/cp1d-owner/expected.json cases.positive" if cp1d["state"] == "bound" else None,
                      "facts": None if cp1d["facts"] is None else list(cp1d["facts"])},
        "figures": {k: {kk: vv for kk, vv in v.items() if kk != "known"} for k, v in figs.items()},
        "cp1_references": cp1_references, "cp2a_references": cp2a_references, "cp1d_references": cp1d_references,
        "forecast": summary,
        "facts": facts, "tables": module_tables, "claims": claim_list, "own_limitations": own_limits,
        "break_tests": [{"row": b["row"], "kind": b["kind"], "test": b["test"], "base_first": b["base_first"], "down_first": b["down_first"],
                         "base_values": [None if v_ is None else norm(v_) for v_, _h in b["base"]], "down_values": [None if v_ is None else norm(v_) for v_, _h in b["down"]],
                         "base_hits": [h for _v, h in b["base"]], "down_hits": [h for _v, h in b["down"]]} for b in all_tests],
        "trajectory": {c: {"change": None if x["change"] is None else norm(x["change"]), "peak": None if x["peak"] is None else norm(x["peak"]), "peak_year": x["peak_year"]} for c, x in traj.items()},
        "module_status": "restricted" if spec["execution"] == "run" else "composer_only",
        "FP05": fp05(facts, module_tables),
    }


# --- 8. refusals, blocked case, readiness, runs -----------------------------------------------

PATTERN_MSG = {"growth": f"String should match pattern '{GROWTH_PATTERN}'", "fraction": f"String should match pattern '{FRACTION_PATTERN}'",
               "amount": f"String should match pattern '{AMOUNT_PATTERN}'", "liquidity": f"String should match pattern '{LIQUIDITY_PATTERN}'",
               "scenario": f"String should match pattern '{SCENARIO_PATTERN}'"}
HIGH_ISSUE = "assessment.confidence: High is not allowed: driver values are uncited analyst assumptions"


def refusals():
    """One literal invalid payload per refusal class, with the exact issues the core must produce. `shape` issues are Pydantic messages in
    `readiness.shape_issues` form (`<dotted.path>: <message>`), returned alone; `content` issues are `<path>: <issue>` with the path in bracket
    form, in the order base_drivers (canonical driver order), downside, break_metrics, minimum_liquidity, assessment, gaps."""
    pos = deepcopy(SUBMISSION["positive"])

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

    bd = "base_drivers"
    add("r01", "growth not a decimal string", "base_drivers.revenue_growth.values[0] = 'three percent'", mut(set_((bd, "revenue_growth", "values", 0), "three percent")),
        [f"base_drivers.revenue_growth.values.0: {PATTERN_MSG['growth']}"], "shape")
    add("r02", "growth below minus one", "base_drivers.revenue_growth.values[1] = '-1.50'", mut(set_((bd, "revenue_growth", "values", 1), "-1.50")),
        [f"base_drivers.revenue_growth.values.1: {PATTERN_MSG['growth']}"], "shape")
    add("r03", "margin above one", "base_drivers.ebitda_margin.values[0] = '1.50'", mut(set_((bd, "ebitda_margin", "values", 0), "1.50")),
        [f"base_drivers.ebitda_margin.values.0: {PATTERN_MSG['fraction']}"], "shape")
    add("r04", "rate with more than four places", "base_drivers.interest_rate.values[2] = '0.12345'", mut(set_((bd, "interest_rate", "values", 2), "0.12345")),
        [f"base_drivers.interest_rate.values.2: {PATTERN_MSG['fraction']}"], "shape")
    add("r05", "distribution negative", "base_drivers.dividends.values[0] = '-5'", mut(set_((bd, "dividends", "values", 0), "-5")),
        [f"base_drivers.dividends.values.0: {PATTERN_MSG['amount']}"], "shape")
    add("r06", "two yearly values instead of three", "base_drivers.ebitda_margin.values loses its last element",
        mut(lambda d: d[bd]["ebitda_margin"].update(values=["0.25", "0.26"])), ["base_drivers.ebitda_margin.values.2: Field required"], "shape")
    add("r07", "four yearly values instead of three", "base_drivers.capex_pct_revenue.values gains a fourth element",
        mut(lambda d: d[bd]["capex_pct_revenue"].update(values=["0.08", "0.08", "0.08", "0.08"])),
        ["base_drivers.capex_pct_revenue.values: Tuple should have at most 3 items after validation, not 4"], "shape")
    add("r08", "driver absent", "base_drivers.tax_wc_pct_revenue removed", mut(lambda d: d[bd].pop("tax_wc_pct_revenue")), ["base_drivers.tax_wc_pct_revenue: Field required"], "shape")
    add("r09", "unknown driver", "base_drivers.growth_extra added", mut(lambda d: d[bd].update(growth_extra=deepcopy(d[bd]["revenue_growth"]))),
        ["base_drivers.growth_extra: Extra inputs are not permitted"], "shape")
    add("r10", "unknown break metric", "break_metrics[0].metric = 'fcf_to_debt'", mut(set_(("break_metrics", 0, "metric"), "fcf_to_debt")),
        ["break_metrics.0.metric: Input should be 'total_leverage', 'net_leverage' or 'interest_coverage'"], "shape")
    add("r11", "confidence outside the enumeration", "assessment.confidence = 'Very High'", mut(set_(("assessment", "confidence"), "Very High")),
        ["assessment.confidence: Input should be 'High', 'Medium', 'Low' or 'Insufficient Information'"], "shape")
    add("r12", "required field absent", "assessment.limitation removed", mut(lambda d: d["assessment"].pop("limitation")), ["assessment.limitation: Field required"], "shape")
    add("r13", "unknown field", "top-level key 'extra' added", mut(lambda d: d.update(extra=1)), ["extra: Extra inputs are not permitted"], "shape")
    out.append({"id": "r14", "class": "not JSON", "mutation": "payload text '{not json'", "issue_kind": "shape",
                "expected_issues": ["(root): Invalid JSON: key must be a string at line 1 column 2"], "payload": None, "payload_text": "{not json"})
    add("r15", "minimum liquidity not a decimal string", "minimum_liquidity.amount = 'ten'", mut(set_(("minimum_liquidity", "amount"), "ten")),
        [f"minimum_liquidity.amount: {PATTERN_MSG['liquidity']}"], "shape")
    add("r16", "downside scenario id malformed", "downside.scenario = 'third'", mut(set_(("downside", "scenario"), "third")),
        [f"downside.scenario: {PATTERN_MSG['scenario']}"], "shape")
    # content issues
    add("v01", "downside scenario not in CP-2A", "downside.scenario = 's09'", mut(set_(("downside", "scenario"), "s09")), ["downside.scenario: not a CP-2A scenario: s09"], "content")
    add("v02", "repayment above the opening debt", "base_drivers.debt_repayment.values[0] = '60' (opening debt is below it)",
        mut(set_((bd, "debt_repayment", "values", 0), "60")), ["base_drivers.debt_repayment.values[0]: repayment exceeds the opening debt balance"], "content")
    add("v03", "a CP-2A watch level has no metric", "break_metrics loses b05", mut(lambda d: d["break_metrics"].pop()), ["break_metrics: no metric for CP-2A break b05"], "content")
    add("v04", "duplicate break id", "break_metrics[1].break_id = 'b03'", mut(set_(("break_metrics", 1, "break_id"), "b03")), ["break_metrics[1].break_id: duplicate break b03", "break_metrics: no metric for CP-2A break b04"], "content")
    add("v05", "break id not in CP-2A", "break_metrics[0].break_id = 'b09'", mut(set_(("break_metrics", 0, "break_id"), "b09")),
        ["break_metrics[0].break_id: not a CP-2A break: b09", "break_metrics: no metric for CP-2A break b03"], "content")
    add("v06", "definition break named", "break_metrics[0].break_id = 'b01'", mut(set_(("break_metrics", 0, "break_id"), "b01")),
        ["break_metrics[0].break_id: b01 is a definition break with a fixed metric", "break_metrics: no metric for CP-2A break b03"], "content")
    add("v07", "metric does not reproduce CP-2A's required decline", "break_metrics[0].metric = 'net_leverage' (b03 is a total leverage level)",
        mut(set_(("break_metrics", 0, "metric"), "net_leverage")), ["break_metrics[0]: metric net_leverage does not reproduce the CP-2A required decline of b03"], "content")
    add("v08", "bare figure in prose", "base_drivers.dividends.rationale states '5 percent'",
        mut(set_((bd, "dividends", "rationale"), "Distributions are cut by 5 percent to protect cash.")), ["base_drivers.dividends.rationale: Bare figure: 5"], "content")
    add("v09", "unresolved reference", "downside.rationale names {T9.9.value|x}",
        mut(set_(("downside", "rationale"), "The downside takes a rate rise of {T9.9.value|x} on the term loan.")), ["downside.rationale: Unresolved reference: T9.9.value"], "content")
    add("v10", "unit-mismatched reference", "base_drivers.revenue_growth.rationale: the revenue_ltm token unit 'US$ m' replaced by 'x'",
        mut(set_((bd, "revenue_growth", "rationale"), pos[bd]["revenue_growth"]["rationale"].replace("{{FIG:revenue_ltm|US$ m}}", "{{FIG:revenue_ltm|x}}"))),
        ["base_drivers.revenue_growth.rationale: Unit x differs from the fact's unit US$ m: {{FACT_ID:revenue_ltm}}"], "content")
    v11_paths = [f"base_drivers.{k}.rationale" for k in DRIVERS if "{{FIG" in pos[bd][k]["rationale"]] + [
        p_ for p_, t_ in (("downside.rationale", pos["downside"]["rationale"]), ("assessment.rationale", pos["assessment"]["rationale"])) if "{{FIG" in t_]
    assert v11_paths == ["base_drivers.revenue_growth.rationale", "base_drivers.ebitda_margin.rationale", "base_drivers.capex_pct_revenue.rationale",
                         "base_drivers.interest_rate.rationale", "assessment.rationale"]
    add("v11", "figure placeholder left unreplaced", "the payload is sent with every {{FIG:..}} still in place", deepcopy(pos),
        [f"{p_}: Malformed run text: unbalanced or empty reference" for p_ in v11_paths], "content", bind_placeholders=False)
    add("v12", "empty prose", "base_drivers.tax_wc_pct_revenue.rationale = ''", mut(set_((bd, "tax_wc_pct_revenue", "rationale"), "")), ["base_drivers.tax_wc_pct_revenue.rationale: empty text"], "content")
    add("v13", "confidence High", "assessment.confidence = 'High'", mut(set_(("assessment", "confidence"), "High")), [HIGH_ISSUE], "content")
    add("v14", "peer ranking", "downside.rationale adds 'versus peers'",
        mut(set_(("downside", "rationale"), "The downside is severe, weak versus peers.")), ['downside.rationale: prohibited conclusion (peer ranking): "versus peers"'], "content")
    add("v15", "instrument recommendation", "downside.rationale adds 'we recommend'",
        mut(set_(("downside", "rationale"), "The downside is severe, so we recommend caution.")), ['downside.rationale: prohibited conclusion (instrument recommendation): "we recommend"'], "content")
    add("v16", "recovery conclusion", "downside.rationale adds 'expected recovery'",
        mut(set_(("downside", "rationale"), "The downside is severe, with expected recovery unclear.")), ['downside.rationale: prohibited conclusion (recovery conclusion): "expected recovery"'], "content")
    add("v17", "probability weighting", "downside.rationale adds 'probability-weighted'",
        mut(set_(("downside", "rationale"), "The downside is severe and the cases are probability-weighted.")),
        ['downside.rationale: prohibited conclusion (probability weighting): "probability-weighted"'], "content")
    # stale inputs (ruling 10: the rule applies to every bound upstream): validator-only payloads, one per upstream, plus the run-level outcome
    for rid, upstream_id, seed in (("v18", "CP-2A", "cp2g-owner v18: a different CP-2A head"), ("v19", "CP-1D", "cp2g-owner v19: a different CP-1D head"),
                                   ("v20", "CP-1", "cp2g-owner v20: a different CP-1 head")):
        current = hashlib.sha256(seed.encode()).hexdigest()
        out.append({"id": rid, "class": "stale or unbound inputs", "issue_kind": "content", "composer_only": True,
                    "mutation": f"the positive payload, validated against a literal Upstream whose current {upstream_id} Input differs from the attempt's bound {upstream_id} Input; validator only, no run",
                    "expected_issues": [f"Stale input {upstream_id}: bound restricted <12 hex of the attempt's bound {upstream_id} input sha256>, current restricted {current[:12]}"],
                    "payload": deepcopy(SUBMISSION["positive"]),
                    "upstream_literal": {"bound": "the attempt's inputs, bound at run time (prepared-pack, CP-0, CP-1, CP-1D and CP-2A Input records)",
                                         "current": [{"input_id": upstream_id, "sha256": current, "status": "restricted"}],
                                         "note": f"every other Input of the bound tuple stays unchanged, so only {upstream_id} is reported"},
                    "run_level": {"outcome": "stale_binding", "clone": f"a clone of the positive store taken after the CP-2G begin whose bound snapshot then changes (a new {upstream_id} head is the case under test)",
                                  "raises": "WorkflowError('stale_binding') at the next G1 call (owner_workflow.py _current, :423-427: the snapshot content hash differs from the bound one)",
                                  "consumes_attempt": False, "journals_step": False,
                                  "direct_caller": "Execution.submit_step raises ValueError('Ticket inputs have changed') (execution.py:768-769)"},
                    "note": f"validate_forward(pack=<pack>, submission=<positive>, upstream=Upstream(bound=attempt.inputs, current=<bound tuple with only the {upstream_id} Input replaced>, cp1=..., cp2a=..., cp1d=...)) returns exactly this issue "
                            "(the cp2_synthesis._stale_issues form). Run level: see run_level; neither path consumes an attempt or journals a step",
                    "issue_prefix": f"Stale input {upstream_id}: bound restricted "})
    return out


def blocked_case(by_id):
    return {
        "plan_order": ["CP-0", "CP-1", "CP-2A", "CP-2G"],
        "attempt_0": {"payload": "r01", "result_status": "rejected", "limitations": by_id["r01"]["expected_issues"]},
        "attempt_1": {"payload": "v13", "repair_of": "attempt_0", "repair_issues": by_id["r01"]["expected_issues"], "result_status": "blocked", "limitations": by_id["v13"]["expected_issues"]},
        "head": {"module_id": "CP-2G", "status": "blocked", "tables": 0, "facts": 0},
        "downstream": "CP-2H and CP-4C (required edge block) cannot begin on a blocked CP-2G head",
        "rule": "execution.settle: attempt 0 invalid -> status rejected; attempt 1 invalid -> status blocked; limitations are the bounded issues (20 lines of at most 600 characters)",
        "receipt": "verifies; both journaled invalid steps are replayed by the verifier and must reproduce their issues exactly",
        "must_not_appear": ["a CP-2G table or fact", "a third attempt"],
    }


CITE_IDENTITY = {"source_id": "identity", "source_sha256": SRC["identity"]["sha256"], "locator": "page:1", "quote": "Northbridge Synthetic Group is the issuer and consolidated group."}
CITE_FINANCIAL = {"source_id": "financial", "source_sha256": SRC["financial"]["sha256"], "locator": "page:1", "quote": "Currency: USD; amounts in millions."}
CP0_ROW_CP2G = {
    "module_id": "CP-2G", "readiness": "READY_WITH_LIMITATIONS",
    "evidence_demand": "Settled CP-1 operating, cash-flow and debt figures and the CP-2A scenarios and break register, with CP-1D supported earnings where selected",
    "source_ids": ["identity", "financial"],
    "rationale": "The forward model can run on settled upstream outputs with inherited source and scope limitations; driver values are analyst assumptions.",
    "citations": [CITE_IDENTITY, CITE_FINANCIAL], "missing_source": None,
    "limitations": ["Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."],
}
CP1_READINESS_CP2G = {
    "entry": "CP-2G",
    "requirements": [{
        "requirement": "consumer_specific_cp1_sufficiency", "status": "limited",
        "evidence_ids": ["{{EVID:kpi revenue, LTM Q4 25 basis}}", "{{EVID:kpi ebitda, LTM Q4 25 basis}}", "{{EVID:kpi fcf, LTM Q4 25 basis}}",
                         "{{EVID:kpi total_debt, LTM Q4 25 basis}}", "{{EVID:kpi cash_closing, LTM Q4 25 basis}}", "{{EVID:kpi undrawn_rcf, LTM Q4 25 basis}}"],
        "rationale": "Settled twelve-month revenue, EBITDA, free cash flow, debt, cash and undrawn revolver give the forecast its base; the statements are unaudited.",
        "actions": ["Retain the unaudited-statement limitation in the forward model."],
    }],
    "gaps": [{"gap_ids": ["{{ALL narrative gap ids}}"], "relevance": "relevant", "evidence_ids": [],
              "rationale": "Every retained source and context warning bears on the reliability of the base the forecast starts from."}],
}


def pointer(rel, jpath):
    return {"file": rel, "sha256": PINS[rel], "path": jpath}


def readiness_literal(with_cp1d):
    cp1d_entry = deepcopy(CP1D_SUB["positive"]["cp1_readiness"]["payload"]["consumers"][0])
    cp2a_entry = deepcopy(CP2A_SUB["cp1_downstream_review"]["consumers"][0])
    consumers = ([cp1d_entry] if with_cp1d else []) + [cp2a_entry, deepcopy(CP1_READINESS_CP2G)]
    return {
        "inputs_sha256": "{{INPUTS_SHA256}}", "consumers": consumers,
        "note": ("The consumer entries are the frozen literals of their owners, unchanged: CP-1D from cases/cp1d-owner/submissions.json positive.cp1_readiness.payload "
                 "(markers {{KPI:<key>|FY-2025}} and {{GAP_IDS}}, bound by that file's run_time_bindings), CP-2A from cases/cp2a-owner/submissions.json cp1_downstream_review "
                 "(markers {{EVID:kpi <key>, LTM Q4 25 basis}} and {{ALL narrative gap ids}}, bound by cases/cp2a-owner/manifest.json run_time_bindings.cp1_readiness), "
                 "CP-2G new with the CP-2A marker style. {{INPUTS_SHA256}} and {{PREFILLED:inputs_sha256}} are the same value: the content hash of the step's prefilled DownstreamInputs."),
    }


def main():
    built = {name: build_case(name) for name in CASES}
    refusal_list = refusals()
    by_id = {r["id"]: r for r in refusal_list}
    base_run = dict(FIN["run"])
    runs = {
        "positive": dict(base_run, run_id="cp2g-owner-positive", pathway="distressed_restructuring", requested_modules=["CP-2G", "CP-1D"]),
        "gap": dict(base_run, run_id="cp2g-owner-gap", pathway="distressed_restructuring", requested_modules=["CP-2G"]),
        "cp1d_blocked": dict(base_run, run_id="cp2g-owner-cp1d-blocked", pathway="distressed_restructuring", requested_modules=["CP-2G", "CP-1D"]),
        "refused": dict(base_run, run_id="cp2g-owner-refused", pathway="distressed_restructuring", requested_modules=["CP-2G"]),
        "blocked": dict(base_run, run_id="cp2g-owner-blocked", pathway="distressed_restructuring", requested_modules=["CP-2G"]),
        "cp2a_blocked": dict(base_run, run_id="cp2g-owner-cp2a-blocked", pathway="distressed_restructuring", requested_modules=["CP-2G"]),
    }
    manifest = {
        "schema_version": "cp2g-owner-cases/1",
        "scope": "CP-2G Forward credit model: CP-0, CP-1, CP-2A (required) and CP-1D (optional) over the frozen financial pack, CP-2G consuming the frozen CP-2A and CP-1D facts under their D3 pins",
        "status": "DRAFT revision 2 (fix round 1 on review-precise-1) by the cp2g-owner preparation task, 2026-10-28; scoped re-review pending; not executed",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "pins": PINS,
        "financial_baseline": {"path": "cases/financial/manifest.json", "manifest_sha256": PINS["cases/financial/manifest.json"],
                               "sources": [{"source_id": s, "sha256": SRC[s]["sha256"], "reuse": "Every page text and locator stays byte-identical; read by reference, never edited"} for s in ("identity", "financial")]},
        "bridge_source": {"path": "cases/cp1d-owner/manifest.json", "json_path": "synthetic_source.positive", "source_id": "bridge", "sha256": BRIDGE["sha256"],
                          "reuse": "the CP-1D positive bridge pages, byte-identical, in the pack of the positive and cp1d_blocked runs (CP-1D needs them); the gap, refused, blocked and cp2a_blocked runs use the identity and financial sources only",
                          "check": "builder asserts the U+000C-joined page sha256 equals the pinned value"},
        "tamper": "expected.json#tamper: the positive closed run, CP-2G result Module fact T2H.7.b03.down_first forged FY2026 -> Not reached by FY2028 (frozen CP-DR shape)",
        "no_new_source": "CP-2G reads the settled CP-1, CP-2A and CP-1D heads only and opens no SourceSession; no synthetic source is added by this lease. The analyst driver values are literal submission input.",
        "edges": {
            "decision": "D4: methodology.json as is. CP-2G required CP-0, CP-1, CP-2A (rule block); optional CP-1D, CP-2D (rule restricted); no edge_rules entry. The r14 skill also lists CP-1B and CP-2 as advisory; methodology.json does not and this lease does not add them.",
            "required": MOD["CP-2G"]["required"], "optional": MOD["CP-2G"]["optional"],
            "plans": {"CP-2G": ["CP-0", "CP-1", "CP-2A", "CP-2G"], "CP-2G+CP-1D": ["CP-0", "CP-1", "CP-1D", "CP-2A", "CP-2G"]},
            "input_order": "execution.current_inputs binds prepared-pack then the upstream heads in plan order: positive [prepared-pack, CP-0, CP-1, CP-1D, CP-2A]; gap [prepared-pack, CP-0, CP-1, CP-2A]",
        },
        "cases": {
            "positive": {"run": runs["positive"], "pack": "identity + financial + bridge (as cases/cp1d-owner positive)", "submission": "submissions.json cases.positive", "expected": "expected.json cases.positive",
                         "execution": "closed run: CP-0, CP-1 (five stages), CP-1D (frozen CP-1D positive), CP-2A (frozen CP-2A positive), CP-2G; CP-1D bound and read"},
            "gap": {"run": runs["gap"], "pack": "identity + financial, as tests/test_financial_workflow.py make_pack()", "submission": "submissions.json cases.gap", "expected": "expected.json cases.gap",
                    "execution": "closed run: CP-0, CP-1, CP-2A (frozen CP-2A positive), CP-2G; CP-1D not requested (optional edge unbound), minimum liquidity not assessed"},
            "cp1d_blocked": {"run": runs["cp1d_blocked"], "pack": "identity + financial + bridge", "submission": "submissions.json cases.cp1d_blocked (positive-derived: minimum liquidity 10, an assessment that names no CP-1D figure)", "expected": "expected.json cases.cp1d_blocked",
                             "execution": "closed run: CP-1D settles blocked (CP-1D refusals r06 twice); CP-2A positive; CP-2G begins under the restricted edge with Input CP-1D status blocked"},
            "refused": {"run": runs["refused"], "pack": "financial source missing (cases/financial/manifest.json negative_case)", "submission": "submissions.json refused", "expected": "expected.json cases.refused",
                        "execution": "CP-0 only; CP-1 begin raises NotAuthorized; CP-2A and CP-2G are never begun"},
            "blocked": {"run": runs["blocked"], "pack": "same pack as gap", "submission": "submissions.json refusals r01 (attempt 0) then v13 (attempt 1)", "expected": "expected.json cases.blocked",
                        "execution": "closed run to CP-2A, then CP-2G attempt 0 invalid (rejected) and attempt 1 invalid (blocked)"},
            "cp2a_blocked": {"run": runs["cp2a_blocked"], "pack": "same pack as gap", "submission": "cases/cp2a-owner/submissions.json refusals r01 then v13 for CP-2A", "expected": "expected.json cases.cp2a_blocked",
                             "execution": "closed run to CP-1, then CP-2A settles blocked; CP-2G begin raises ValueError('Required upstream is unrun, stale or blocked') (edge rule block)"},
            "fixture_total_loss": {"run": None, "execution": "composer only: positive CP-1 facts, CP-2A positive scenario s04 (EBITDA falls to zero) as the downside"},
            "fixture_cash_missing": {"run": None, "execution": "composer only: the positive CP-1 facts with cash_closing set to status missing (limitation 'Cash and cash equivalents are not disclosed in the supplied statements.')"},
            "fixture_debt_repaid": {"run": None, "execution": "composer only: the whole term loan repaid in the first year, so debt is a known zero and coverage and FCF-to-debt are not calculable"},
            "fixture_cp2a_gap_head": {"run": None, "execution": "composer only: CP-1 positive facts with the frozen CP-2A gap head (base period Q3 25; break b02 and b03 required declines missing)"},
        },
        "fact_selection_rule": {
            "table_id": "T4.10", "period": LTM_PERIOD,
            "predicate": "fact.table_id == 'T4.10' and fact.label == 'LTM Q4 25 (2025-01-01 to 2025-12-31) · <metric>'; exactly one match per metric (probe: 500 T4.10 facts, unique labels), zero or several fail",
            "metrics": sorted(CP1_METRICS),
            "operands": OPERAND_KEY,
            "sign": "CP-1 stores cash_interest, cash_taxes, working_capital_change and capex as negative outflows; CP-2G uses their magnitudes",
            "observed_value_class": {m: v[0] for m, v in CP1_METRICS.items()},
            "probe": "S1 positive promoted CP-1 head (read only copy r2pos-orig), 2026-10-28, LTM Q4 25 column: revenue 120, ebitda 30.0, cash_interest -5.00, cash_taxes -4, working_capital_change -2.0, capex -10.0, fcf 9.00, total_debt 50.00, cash_closing 20.00, undrawn_rcf 0, ebitda_margin 0.25, capex_to_revenue 0.0833...; all known; the other upstream facts are literal ids (below)",
            "fact_ids": "interface-fact:<sha256>; bound at run time, never literal",
        },
        "upstream_fact_selection": {
            "CP-2A": {"head": "the settled CP-2A head of the run", "scenario": "T2B.1.<row>.ebitda_decline and T2B.1.<row>.interest_increase of the row named by downside.scenario",
                      "breaks": "T2B.6.<row>.{origin,test,level,required_decline,outcome} for every row of the register, in register order",
                      "fact_ids": "literal (table.row.field assigned by CP-2A); read from cases/cp2a-owner/expected.json cases.positive (pinned)"},
            "CP-1D": {"head": "the settled CP-1D head of the run", "facts": ["T1D.3.supported.value", "T1D.6.supported.total_leverage", "T1D.6.supported.net_leverage"],
                      "fact_ids": "literal; read from cases/cp1d-owner/expected.json cases.positive (pinned)"},
        },
        "run_time_bindings": {
            "figure_placeholders": "{{FIG:name|token}} -> {<fact_id>|<token>}: cp1 names by fact_selection_rule, cp1d names to the literal ids above; only a fact with a citation or a calculation can be referenced in prose, so the uncited analyst cells of CP-2A (shock sizes, watch levels) are never FIG names; unreplaced it is malformed run text (refusal v11)",
            "fact_id_marker": "{{FACT_ID:name}} in an expected issue -> the fact id bound to FIG name",
            "cp0_consumer_rows": "positive and cp1d_blocked: CP-1, CP-1D (cases/cp1d-owner submissions positive.readiness_review.consumers), CP-2A (submissions.json cp0_consumer_row_cp2a) and CP-2G (cp0_consumer_row_cp2g); gap, blocked, cp2a_blocked: CP-1 (default), CP-2A, CP-2G; T8 commands Run <module> for each",
            "cp1_readiness": "submissions.json cases.<case>.cp1_readiness (consumer entries CP-1D?, CP-2A, CP-2G); markers bound by the frozen run_time_bindings of the CP-1D and CP-2A manifests; {{EVID:kpi <key>, LTM Q4 25 basis}} for the new CP-2G entry: the one kpi catalogue record with that key whose display_basis_id is the basis record (kind basis, label 'LTM Q4 25', column_key 'LTM:fy-2025', scope 'historical')",
            "pack_hash": "PreparedPack.content_hash() of the run's pack", "inherited_limitations": "execution.py inherited_limitations rule (see expected.execution)", "ticket_and_call_ids": "structural only",
        },
        "figures": {k: {kk: vv for kk, vv in v.items()} for k, v in FIGS.items()},
        "tool_use": {
            "CP-2G": "session-less and source-free: no SourceSession and no pack tool; the only tool use is one ok read_inputs (the exact view context_block, a D2 exception frozen by this lease) before the submit; every invoke is a refused not_permitted receipt",
            "view_tree_draft": {
                "note": "a proposal, not an observation: the implementer commits cases/cp2g-owner/cp2g-view-tree.json from a product-settled head; no quote, citations or record_json key at any depth",
                "keys": {
                    "upstream": "[{module_id, status}] for CP-0, CP-1, CP-2A and CP-1D (state bound|unbound|blocked)",
                    "base": "{period, forecast_periods: [FY2026, FY2027, FY2028], operands: {revenue, ebitda, cash_interest, cash_taxes, working_capital_change, capex, fcf, total_debt, cash_closing, undrawn_rcf: {ref|null, shown|null, status, limitation|null}}, ratios: {ebitda_margin, capex_to_revenue, total_leverage_reported, net_leverage_reported, interest_coverage_reported, fcf_to_debt: {...}}}",
                    "drivers": "[{name, label, unit_class, bounds: {min, max, places}}] for the seven drivers; minimum_liquidity: {places, may_be_not_assessed: true}",
                    "cp2a": "{base_period, scenarios: [{row, name, ebitda_decline: {shown, status}, interest_increase: {shown, status}}], breaks: [{row, origin, test, level: {shown, status}, required_decline: {shown|null, status, limitation|null}, outcome}]}",
                    "cp1d": "{state, supported_ebitda: {ref, shown}|null, supported_total_leverage: {ref, shown}|null, supported_net_leverage: {ref, shown}|null}",
                    "break_metrics_offered": "[total_leverage, net_leverage, interest_coverage]; the rows b01 and b02 (origin Definition) are fixed and not offered",
                    "cp1_facts": "[{ref, label, period, unit, shown}] referencable CP-1 operands and ratios (a fact with a citation or calculation only)",
                    "cp1d_facts": "[{ref, label, period, unit, shown}] referencable CP-1D facts (T1D.3.supported.value, T1D.6.supported.total_leverage, T1D.6.supported.net_leverage) when bound",
                    "inherited_limitations": "[str]",
                },
            },
        },
    }
    refused_cp1_row = {
        "module_id": "CP-1", "readiness": "CONDITIONAL", "evidence_demand": "Located historical statements, facility terms, definitions and scope",
        "source_ids": ["identity"], "rationale": "Quarterly financial statements were not supplied.", "citations": [CITE_IDENTITY],
        "missing_source": "Quarterly financial statements", "limitations": ["Quarterly financial statements were not supplied."],
    }
    submissions = {
        "schema_version": "cp2g-owner-submissions/1",
        "note": ("Literal analyst submissions for the forward_credit_model step. {{FIG:name|token}} marks a figure reference replaced mechanically by {<fact_id>|<token>} after the heads are inspected "
                 "(manifest.json run_time_bindings); unreplaced it is malformed run text and fails closed (refusal v11). Driver values, the minimum liquidity and the shock scenario id are analyst input, not computed values. "
                 "The upstream step literals (CP-1D earnings_quality, CP-2A downside_pathway, the CP-0 rows and CP-1 readiness) are copies of the frozen oracles' own, byte-identical in content, so the run needs no other file."),
        "figures": {k: dict(v) for k, v in FIGS.items()},
        "cp0_consumer_row_cp2g": CP0_ROW_CP2G,
        "cp0_consumer_row_cp2a": CP2A_SUB["cp0_consumer_row_cp2a"],
        "cp0_consumer_rows_cp1d": CP1D_SUB["positive"]["readiness_review"]["consumers"],
        "upstream_step_literals": {
            "CP-1D": {"source": pointer("cases/cp1d-owner/submissions.json", "positive"),
                      "readiness_review": CP1D_SUB["positive"]["readiness_review"], "cp1_source_context": CP1D_SUB["positive"]["cp1_source_context"],
                      "earnings_quality": CP1D_SUB["positive"]["earnings_quality"], "tool_calls": CP1D_SUB["positive"]["tool_calls"],
                      "blocked": {"attempt_0": "CP-1D refusals r06", "attempt_1": "CP-1D refusals r06",
                                  "payload": next(r for r in CP1D_SUB["refusals"] if r["id"] == "r06")}},
            "CP-2A": {"source": pointer("cases/cp2a-owner/submissions.json", "positive.downside_pathway"), "downside_pathway": CP2A_SUB["positive"]["downside_pathway"],
                      "blocked": {"attempt_0": next(r for r in CP2A_SUB["refusals"] if r["id"] == "r01"), "attempt_1": next(r for r in CP2A_SUB["refusals"] if r["id"] == "v13")}},
        },
        "cases": {
            "positive": {"forward_credit_model": SUBMISSION["positive"], "cp1_readiness": readiness_literal(True),
                         "tool_calls": [{"module": "CP-2G", "tool": "read_inputs", "arguments": None}],
                         "tool_note": "CP-2G is submit-only: exactly one ok read_inputs (the frozen view) before the submit, zero ok pack calls, every invoke a refused not_permitted receipt. The CP-1D steps keep their own tool_calls (upstream_step_literals.CP-1D.tool_calls)."},
            "gap": {"forward_credit_model": SUBMISSION["gap"], "cp1_readiness": readiness_literal(False), "tool_calls": [{"module": "CP-2G", "tool": "read_inputs", "arguments": None}]},
            "cp1d_blocked": {"forward_credit_model": SUBMISSION["cp1d_blocked"], "cp1_readiness": readiness_literal(True), "tool_calls": [{"module": "CP-2G", "tool": "read_inputs", "arguments": None}]},
        },
        "fixtures": {k: {"forward_credit_model": FIXTURE_SUBMISSION[k]} for k in FIXTURE_SUBMISSION},
        "refused": {"cp0_consumer_row_cp1": refused_cp1_row,
                    "cp0_consumer_row_cp2a": {"module_id": "CP-2A", "readiness": "CONDITIONAL", "evidence_demand": "Settled CP-1 figures", "source_ids": ["identity"],
                                              "rationale": "Quarterly financial statements were not supplied.", "citations": [CITE_IDENTITY],
                                              "missing_source": "Quarterly financial statements", "limitations": ["Quarterly financial statements were not supplied."]},
                    "cp0_consumer_row_cp2g": {"module_id": "CP-2G", "readiness": "CONDITIONAL", "evidence_demand": "Settled CP-1 and CP-2A outputs", "source_ids": ["identity"],
                                              "rationale": "Quarterly financial statements were not supplied.", "citations": [CITE_IDENTITY],
                                              "missing_source": "Quarterly financial statements", "limitations": ["Quarterly financial statements were not supplied."]},
                    "gap_row": {"gap_id": "missing-financial", "kind": "source", "severity": "material", "description": "Quarterly financial statements were not supplied.",
                                "affected_modules": ["CP-1", "CP-2A", "CP-2G"], "remediation": "Supply quarterly financial statements"}},
        "refusals": [{k: v for k, v in r.items() if k in ("id", "class", "mutation", "payload", "payload_text", "composer_only", "bind_placeholders", "upstream_literal", "run_level", "note")} for r in refusal_list],
        "blocked": {"attempt_0": "refusals r01", "attempt_1": "refusals v13"},
    }

    expected = {
        "schema_version": "cp2g-owner-expected/1",
        "derivation": ("Hand-transcribed recipes of work/lead/cp2g-owner-preparation/lease-draft.md applied to the frozen financial pages, the literal analyst drivers and the pinned CP-2A and CP-1D oracle facts by "
                       "cases/cp2g-owner/builder/build.py (stdlib only; deploy_vii never imported or run). Every value is the correctly rounded 38-significant-digit half-even result of an exact rational "
                       "(Fraction), cross-checked against decimal.Context(prec=38, ROUND_HALF_EVEN); sums and products of the short analyst decimals are exact. Display spelling follows display.py "
                       "(ROUND_HALF_UP; amount 2 dp by the fact's decimals, multiple 2 dp 'x', percent 1 dp '%', negative in parentheses). CP-1 constants are derived from the frozen pages and asserted against "
                       "the financial oracle; only CP-1's value_class is an observed string."),
        "cell_notation": {"shown": "exact displayed text; an unsettled cell is spelled as report_view.fact_spelling spells it: missing -> state gap, text '∅ G#'; not_applicable -> state not_meaningful, text '∅ G# n.m.' (G# is the report-wide gap number, not literal)",
                          "amount_exact": "canonical exact decimal; null means unsettled", "status": "known | missing | not_applicable", "fact_id": "table.row.field, assigned by Python",
                          "derives_from": "cp1:<metric> = a CP-1 T4.10 fact of the cp1_inputs; cp2a:<id> and cp1d:<id> = a settled upstream fact (cp2a_references, cp1d_references); any other id = a fact of this module; empty for analyst inputs and definition constants"},
        "id_rules": {"fact_id": "<table_id>.<row_id>.<field>", "calculation_id": "calc:<fact_id> on calculated facts",
                     "rows": "T2H.3: a01..a07 base drivers in the canonical order, d01 and d02 the CP-2A shocks, m01 minimum liquidity; T2H.4/5/6: a25 the FY2025 actual (T2H.4 and T2H.6 only), b26..b28 base case, d26..d28 downside; T2H.7: the CP-2A break rows b01.. then m01; T2H.8: base, down",
                     "claims": "T2H.3.<driver> (seven), T2H.3.downside, T2H.3.minimum_liquidity, T2H.4.base/down, T2H.6.base/down, T2H.5.down, T2H.7.base/down, T2H.8.base/down, [T2H.2.cp1d when CP-1D is bound], T2H.3.assessment, in this order"},
        "lineage_rule": "A calculated fact's citations are the ordered, de-duplicated concatenation of the citations of the facts in its derives_from list, in that order (cp4_legal._computed pattern), where an own fact contributes its own (transitively CP-1) citations; analyst inputs and CP-2A watch levels carry none. A known fact never derives from a fact that is not known (asserted by the builder). A copied upstream cell keeps the upstream fact's value_class (analyst_judgment, calculated, or None for the CP-2A definition constants) and carries a calculation_id only when calculated. A T2H cell that restates a CP-1 fact (T2H.2 copies, T2H.4 and T2H.5 openings, T2H.2 recomputed ratios) is this module's own calculated fact with cp1:<metric> lineage and calc:<fact_id>; it does not keep CP-1's class (calculated or source): only cp1_references carry the CP-1 fact verbatim with its class. A copy of a CP-2A cell in T2H.7 (level, static_decline) lists the CP-2A fact it copies in derives_from whatever the cell's class; the base_first and down_first texts of a CP-2A row list cp2a:T2B.6.<row>.level; the downside EBITDA (T2H.4) and interest (T2H.5) cells list the CP-2A shock fact they apply (D3 proof, ruling H1).",
        "references_rule": "cp1_references, cp2a_references and cp1d_references carry the upstream facts verbatim under their own fact ids with their own value_class, status and limitation; prose and T2H.2 reference them ({<fact_id>|<unit>}). No CP-2G table or claim stores a spelled upstream figure.",
        "property_tests": {
            "base_control": "FY2025 free cash flow recomputed from the CP-1 operands equals CP-1's reported fcf exactly (T2H.2 fcf 'Reconciled to CP-1'); total and net leverage recomputed equal the CP-1 reported ratios exactly",
            "roll_forward": "for every case and year, closing debt = opening debt - repayment, closing cash = opening cash + free cash flow - distributions - repayment, and each year's opening equals the prior closing (the first from CP-1); asserted in Fraction by the builder",
            "downside_dominance": "with the CP-2A shock (decline >= 0, increase >= 0) and every other driver equal, downside EBITDA <= base EBITDA, downside interest >= base interest and downside free cash flow <= base free cash flow in every year",
            "monotonic": "for a fixed driver set the downside EBITDA does not rise and the downside leverage does not fall as the CP-2A decline rises (where calculable)",
            "first_break": "first_result returns the earliest year met; a year not calculable before it makes the answer Not calculable; none met and all calculable is 'Not reached by FY2028'",
        },
        "d8_table_ids": {"collision_found": None, "check": "T2H.1-T2H.9 appear only in the CP-2G entry of the pinned methodology.json and in no other module's table_ids; no definition exists in src/ or tests/ (grep); the CP-2H family is T2R.*",
                         "resolution": "no change: CP-2G registers T2H.1-T2H.9 as they are", "cp2g_table_ids": list(TABLES), "module_tables_besides": ["cp1_references", "cp2a_references", "cp1d_references"]},
        "d7_rendering": {
            "design_reference": "design/reference of DEPLOY VII (read only): CP-2G has no Front Page block of its own. It appears only (a) as a navigation row in rbot-fp-01-credit-snapshot.dc.html (S.navRows list), (b) in the family colour table (lib/shell.js and lib/vm.js: CP-2G is family 'liquidity', mirrored by report_view.MODULE_FAMILY), and (c) as idle wording of blocks other modules own: FP02 Metric strip 'No projected series: no forecast ran (CP-2G Restricted)' and the workbench 'No Base or Downside. CP-2G Restricted: numeric forecast assumptions not supported'. FP05's own blocks (report_view._PRESETS distressed_restructuring) are distress-gate, recovery-by-class, value-allocation-claims, liquidity-runway (CP-2D), funding-gap-lme (CP-3C), covenant-levers, rating-triggers, restructuring-paths, instrument-decision, portfolio-fit and what-changed",
            "decision": "two new blocks, owner CP-2G, kind dense, producers (CP-2G,), route 'Full analysis', in distressed_restructuring only: forward-credit-path (tabs T2H.4, T2H.5, T2H.6) and forward-breakpoints (tabs T2H.7, T2H.8); evidence rail T2H.1, T2H.2, T2H.3 and the three reference tables; limitations rail T2H.9; no chart in this slice",
            "composition": "the two _Spec rows go in CP-2A's _DISTRESSED composition (docs/CP2A-OWNER-LEASE.md:28), not a separate _FORWARD one, and the two block ids are inserted in the distressed_restructuring entry of _PRESETS after the CP-2A pair (downside-stress, break-points) or, if the CP-2A lease has not landed, after distress-gate",
            "pathway": "distressed_restructuring is the right and only pathway: contracts.PATHWAY_MODULES lists CP-2G in that pathway alone (checked by the reviewer, review-precise-1 D7)",
            "design_extension": "the design reference has no CP-2G block, so the two blocks are a design extension (LEAD ruling 4); the lease records it as a note for the design owner, who may merge them into one block of five tabs",
            "wording_kept": "the FP02 'no forecast ran' wording and the workbench note are idle wording of MODEL-owned blocks and stay untouched; this lease does not make the MODEL strip read a CP-2G forecast",
            "block_ids_collision": "forward-credit-path and forward-breakpoints appear nowhere in src/, tests/ or docs/ (grep); no existing preset names them",
        },
        "d4_edges": {"decision": "methodology.json as is (required CP-0, CP-1, CP-2A, rule block; optional CP-1D and CP-2D, rule restricted)", "proposal_applied_nowhere": "none"},
        "execution": {
            "plan_order": {"positive": ["CP-0", "CP-1", "CP-1D", "CP-2A", "CP-2G"], "gap": ["CP-0", "CP-1", "CP-2A", "CP-2G"]},
            "inputs": {"positive": ["prepared-pack", "CP-0", "CP-1", "CP-1D", "CP-2A"], "gap": ["prepared-pack", "CP-0", "CP-1", "CP-2A"]},
            "statuses": {"CP-0": "restricted", "CP-1": "restricted (financial precedent)", "CP-1D": "restricted (frozen CP-1D lease)", "CP-2A": "restricted (frozen CP-2A lease)",
                         "CP-2G": "restricted: own limitations are non-empty and the case is synthetic (execution.py settle)"},
            "tool_use": {"CP-2G": "submit only: every invoke is a refused not_permitted receipt; exactly one read_inputs (the frozen view) before the submit; zero ok pack calls"},
            "consumption": ("CP-2G closes D3 for CP-2A (it reads the settled T2B.1 scenario and T2B.6 break facts and its attempt inputs bind the CP-2A head hash; in derives_from the downside T2H.4.d26-d28.ebitda facts list cp2a:T2B.1.<s>.ebitda_decline, "
                            "the downside T2H.5.d26-d28.interest facts list cp2a:T2B.1.<s>.interest_increase, and for every CP-2A break row the T2H.7 level and static_decline copies and the base_first and down_first texts list cp2a:T2B.6.<row>.level / .required_decline) "
                            "and for CP-1D (it reads T1D.3.supported.value and T1D.6.supported.total_leverage / net_leverage through the CP-1D head, bound as an optional input; T2H.2 and T2H.8 derive from them). "
                            "CP-2G's own consumption stays OPEN: CP-2H and CP-4C (required edges) are unleased; CP-5 counts only after a lease extends its scope."),
            "inherited_limitations": "execution.inherited_limitations: for each directly bound head in input order, the head's limitations then its inherited limitations (a blocked bound head contributes 'Upstream <id> blocked: <limitation>' per limitation), de-duplicated, own findings removed; bound at run time",
        },
        "cp1_readiness": {"literal": "submissions.json cases.<case>.cp1_readiness", "bindings": "manifest.json run_time_bindings.cp1_readiness",
                          "consumer_rows": {"CP-2G": {"entry": "CP-2G", "canonical_module": "CP-2G", "requirements": ["consumer_specific_cp1_sufficiency"], "policy": "consumer_specific_review", "status": "ready_with_limitations"}},
                          "validator_issues": "none expected; probed on a read-only copy of the S1 positive promoted CP-1 head (see the report)"},
        "refusals": [{k: v for k, v in r.items() if k in ("id", "class", "issue_kind", "expected_issues", "issue_prefix", "run_level")} for r in refusal_list],
        "refusal_rules": {
            "journal": "each refusal is one invalid CP-2G step on attempt 0 of the positive CP-1/CP-2A/CP-1D heads: attempt consumed, module status rejected, limitations equal the issues (bounded: 20 lines of 600 characters)",
            "shape_vs_content": "shape issues are returned alone (a payload that does not parse gets no content check); content issues follow in the order base_drivers (canonical driver order), downside, break_metrics, minimum_liquidity, assessment, gaps",
            "schema_patterns": {"growth": GROWTH_PATTERN, "fraction": FRACTION_PATTERN, "amount": AMOUNT_PATTERN, "minimum_liquidity.amount": LIQUIDITY_PATTERN, "downside.scenario": SCENARIO_PATTERN, "break_id": BREAK_PATTERN},
            "paths": "shape: dotted (base_drivers.revenue_growth.values.0); content: bracketed (base_drivers.debt_repayment.values[0])",
            "composer_only": "base operands missing (revenue, debt, cash, ...) are never refusals: they compose honest gaps (fixtures); v18, v19 and v20 are validator-only",
            "validator_only": "v18 (CP-2A), v19 (CP-1D) and v20 (CP-1) are each exercised on validate_forward with a literal Upstream (bound = the attempt's inputs; current = the bound tuple with only that Input replaced); the issue is the cp2_synthesis._stale_issues form 'Stale input <id>: bound <status> <12 hex>, current <status> <12 hex>'",
            "stale_run_level": {"rule": "the stale rule applies to every bound upstream (LEAD ruling 10)",
                                "outcome": "after the CP-2G begin, any change of the bound snapshot (a new CP-1, CP-1D or CP-2A head in a clone of the positive store) refuses WorkflowError('stale_binding') at the next G1 call (owner_workflow.py _current, :423-427); a direct Execution.submit_step caller gets ValueError('Ticket inputs have changed') (execution.py:768-769)",
                                "consumes_attempt": False, "journals_step": False, "pinned_in": "refusals v18, v19, v20 run_level; one clone test per upstream (CP-1, CP-1D, CP-2A)"},
            "probability_weighting": {"kind": "phrase guard, not a semantic check: a case-insensitive substring match over every prose field, quoting the matched phrase as business_context.prohibited_issues does; it over-blocks innocent text and misses unlisted wording",
                                      "phrases": ["probability-weighted", "probability weighted", "probability of", "weighted by probability", "expected value", "likelihood-weighted"],
                                      "note": "'probability of' is kept although 'probability of refinancing' over-blocks (LEAD ruling L11); 'expected value' and 'likelihood-weighted' were added by ruling L11; v17 exercises 'probability-weighted'"},
            "g1_level": "not_permitted (invoke, submit before read), stale_binding (snapshot change) and create-time refusals are G1's and are in the lease's A3, not here",
            "begin_refusals": "CP-2A blocked/unrun/stale: ValueError('Required upstream is unrun, stale or blocked') (execution.py:243-245 the raise; edge rule block, no attempt consumed); G1 retains it as a RefusedBegin (owner_workflow.py:443-479 _begin; the outcome's refusal code is f'{module}_{kind}' with module lower-cased without the hyphen, :658-663 and :670-674; the receipt verifier re-runs current_inputs on the pre-refusal snapshot, :884-897); CP-1D blocked: begin succeeds (edge rule restricted), the Input carries status blocked",
        },
        "cases": {},
    }
    for name, b in built.items():
        entry = dict(b)
        entry["execution"] = CASES[name]["execution"]
        expected["cases"][name] = entry
    pos = expected["cases"]["positive"]
    pos["cp0"] = {"consumer_rows": ["submissions.json cp0_consumer_rows_cp1d (CP-1, CP-1D)", "submissions.json cp0_consumer_row_cp2a", "submissions.json cp0_consumer_row_cp2g"], "validator_issues": [],
                  "T8_commands": [["CP-1", "Run CP-1"], ["CP-1D", "Run CP-1D"], ["CP-2A", "Run CP-2A"], ["CP-2G", "Run CP-2G"]]}
    expected["cases"]["gap"]["cp0"] = {"consumer_rows": ["default CP-1 row of make_pack()", "submissions.json cp0_consumer_row_cp2a", "submissions.json cp0_consumer_row_cp2g"], "validator_issues": [],
                                       "T8_commands": [["CP-1", "Run CP-1"], ["CP-2A", "Run CP-2A"], ["CP-2G", "Run CP-2G"]]}
    expected["cases"]["gap"]["plan_order"] = ["CP-0", "CP-1", "CP-2A", "CP-2G"]
    pos["plan_order"] = ["CP-0", "CP-1", "CP-1D", "CP-2A", "CP-2G"]
    cb = expected["cases"]["cp1d_blocked"]
    cb["plan_order"] = ["CP-0", "CP-1", "CP-1D", "CP-2A", "CP-2G"]
    cb["cp1d_blocked"] = {
        "cp1d_head": {"status": "blocked", "attempts": "r06 twice (frozen CP-1D oracle)", "limitations_contain": "Evidence required for an accepted add-back: Procurement programme savings"},
        "cp2g_inputs": ["prepared-pack", "CP-0", "CP-1", "CP-1D (status blocked)", "CP-2A"],
        "inherited_limitations_contain": "Upstream CP-1D blocked: Evidence required for an accepted add-back: Procurement programme savings",
        "rule": "execution.current_inputs binds a blocked head under a restricted edge with status blocked; inherited_limitations prefixes each of its limitations with 'Upstream CP-1D blocked: '; the CP-2G head settles restricted",
        "tables": "T2H.1 u_cp1d status 'blocked'; T2H.2 ebitda_supported, ebitda_adjustment and the two supported leverage cells missing (never 0); T2H.8 ebitda_fy26_vs_supported missing; cp1d_references empty",
    }
    expected["cases"]["refused"] = {
        "execution": "run", "plan_order": ["CP-0", "CP-1", "CP-2A", "CP-2G"],
        "cp0": {"rows": ["submissions.json refused.cp0_consumer_row_cp1", "submissions.json refused.cp0_consumer_row_cp2a", "submissions.json refused.cp0_consumer_row_cp2g"],
                "gap_row": "submissions.json refused.gap_row", "validator_issues": [], "settled_status": "restricted",
                "T8_commands": [["CP-1", "DO NOT RUN"], ["CP-2A", "DO NOT RUN"], ["CP-2G", "DO NOT RUN"]]},
        "refused_begins": [{"module_id": "CP-1", "reason": "CP-0 has not authorized this consumer's source readiness"}],
        "refusal": "cp1_not_authorized",
        "refusal_note": "the 'refusal' field of the financial-review-outcome/1 returned by the CP-0 submit that settles CP-0 and triggers the CP-1 begin (owner_workflow.py:649 the _advance after CP-0 finishes, :658-663 the outcome, :670-674 _refusal_code: module 'CP-1' -> 'cp1', kind 'not_authorized'); the refusal is retained (:443-479) and the receipt verifier re-runs current_inputs (:884-897)",
        "attempts": ["CP-0"], "heads": ["CP-0"],
        "later_modules": "CP-2A and CP-2G are never begun (G1 stops the walk after a RefusedBegin); current_inputs for CP-2G would raise ValueError 'Required upstream is unrun, stale or blocked'",
        "model_publication": "not planned", "receipt": "verifies",
        "must_not_appear": ["a CP-2A or CP-2G ticket, attempt, head or table", "a forecast value of 0 standing for a missing one"],
    }
    expected["cases"]["blocked"] = blocked_case(by_id)
    expected["cases"]["cp2a_blocked"] = {
        "plan_order": ["CP-0", "CP-1", "CP-2A", "CP-2G"],
        "cp2a": {"attempt_0": "CP-2A refusals r01 (rejected)", "attempt_1": "CP-2A refusals v13 (blocked)", "head": "blocked, no tables (frozen CP-2A oracle blocked)"},
        "cp2g_begin": {"refused": True, "error": "ValueError", "message": "Required upstream is unrun, stale or blocked", "rule": "execution.current_inputs: a blocked head is bound only under a restricted edge; CP-2A is a required edge (block)",
                       "consumes_attempt": False, "journals_step": False},
        "refusal": "cp2g_blocked",
        "refusal_note": "the 'refusal' field of the financial-review-outcome/1 returned by the CP-2A attempt-1 submit that settles blocked (owner_workflow.py:657 the attempt-1-blocked _advance that begins CP-2G, :658-663 the outcome with its refusal key, :670-674 _refusal_code: first retained refusal's module 'CP-2G' -> 'cp2g', kind 'blocked')",
        "g1": "the walk retains the begin as a RefusedBegin with the error text (owner_workflow.py:443-479); no CP-2G ticket exists; the receipt verifies (:884-897 re-runs current_inputs on the pre-refusal snapshot and requires the same ValueError text)",
        "must_not_appear": ["a CP-2G attempt, head, table or fact"],
    }
    # tamper recipe (ruling H2; frozen CP-DR shape, docs/CPDR-OWNER-LEASE.md Tamper, cases/cpdr-owner/expected.json tamper)
    target = next(f for f in built["positive"]["facts"] if f["fact_id"] == TAMPER_TARGET)
    assert target["text"] == TAMPER_FROM and TAMPER_TO != TAMPER_FROM and TAMPER_TO.startswith("Not reached by ")
    expected["tamper"] = {
        "case": "positive (closed run: CP-0, CP-1, CP-1D, CP-2A and CP-2G settled, receipt sealed)",
        "target_fact": TAMPER_TARGET, "from": TAMPER_FROM, "to": TAMPER_TO,
        "why_this_fact": "the table cell holds only the fact id and the step output holds the submission, so the first-year text lives only in the result Module; it is the one fact the probe's rebuild (cp2g.probe: the step validator rerun on the journaled payload, then cp2g_module and settle back to the head) contradicts, because the rebuild reads T2H.7 b03 downside first year FY2026",
        "recipe": [
            "1. Copy the closed positive store directory (blobs, snapshots, current, audit) to a scratch path.",
            f"2. Load the CP-2G head's result Module; replace only the text of fact {TAMPER_TARGET} (its shown spelling is that text); leave every other fact (including T2H.7.b03.base_first and every other row), table, claim (T2H.7.down included) and limitation unchanged.",
            "3. Serialise the forged Module as Execution._store does (model_dump_json); its sha256 R2 must equal Module.content_hash(); write blobs/R2.",
            "4. Build a new ExecutionSnapshot equal to the current one with the CP-2G Attempt.result_sha256 and Head.result_sha256 set to R2 (status, inputs and commands unchanged, so head_of(forged Module) equals the Head) and the same parent; write snapshots/<its sha256>.json and rewrite current to that digest.",
            "5. In the retained receipt: set the CP-2G SettledHead.result_sha256 to R2; set receipt.snapshot_sha256 and every coordinate that named the old final snapshot (the CP-2G settling OwnerSubmission.snapshot_after_sha256: owner_workflow.py _advance -> _finish_walk; its record is retained as audit/submissions/<content_hash> by _retain) to the new digest; delete audit/submissions/<old record hash> and write the edited OwnerSubmission as audit/submissions/<its content_hash> (model_dump_json bytes); rewrite audit/receipt.sha256 with the forged receipt's content_hash (S1a R3-5 and CP-3 A4 pattern: the audit file travels under its new hash).",
        ],
        "expect": {
            "passes": "everything upstream of the probe: audit inventory, blob and snapshot hashes, ancestor walk, head_of equality, begin and publication records, call and read replay, journaled-step replay (the payload and step are untouched)",
            "refuses": "cp2g.probe raises WorkflowError('identity_mismatch'); verify_owner_run_receipt raises identity_mismatch",
            "test_asserts": "on the forged copy, _verify_audit and every check before _PROBES pass (as CP-3 A4 (a)); then cp2g.probe raises identity_mismatch. A test asserting identity_mismatch alone would never show that the probe was reached.",
        },
        "step_output_edit": "an edited CP-2G step output is caught by the store's own blob hash check (Module.content_hash / the step blob), not by the probe's output comparison (recorded limitation, S1a R3-5)",
    }
    # sanity: the FIG oracle ratios equal the frozen financial oracle
    mo = FIN["q4_ltm_metric_oracle"]
    assert Fraction(mo["total_leverage_reported"]["numerator"]) / Fraction(mo["total_leverage_reported"]["denominator"]) == Fraction(5, 3)
    # sanity: no digits or brace characters in analyst names and prose outside FIG tokens
    for case in ("positive", "gap", "cp1d_blocked"):
        sub = SUBMISSION[case]
        for t_ in prose_texts(sub):
            assert not re.search(r"[0-9]", re.sub(r"CP-[0-9]{1,2}[A-Z]?", "", re.sub(r"\{\{FIG:[a-z_]+\|[^}]*\}\}", "", t_))), t_
        for key in DRIVERS:
            lim = sub["base_drivers"][key]["limitation"]
            assert lim is None or not re.search(r"[0-9{}\[\]]", lim)
        assert not re.search(r"[0-9]", sub["downside"]["limitation"]) and not re.search(r"[0-9]", sub["assessment"]["limitation"])
    # sanity: no stored text fact and no limitation spells a CP-1 or upstream figure; a numeric fact shows its own value only
    for name, b in built.items():
        spelled = {v["spelled"] for v in b["figures"].values() if v.get("spelled")}
        for x in b["facts"]:
            for key in ("text", "limitation"):
                assert not any(sp in str(x.get(key) or "") for sp in spelled), (name, x["fact_id"], key)
        for text_ in b["own_limitations"]:
            assert not any(sp in text_ for sp in spelled), (name, text_)
    # sanity: the published submissions carry no builder-internal key
    for case in ("positive", "gap"):
        sub = submissions["cases"][case]["forward_credit_model"]
        assert set(sub) == {"base_drivers", "downside", "break_metrics", "minimum_liquidity", "assessment", "gaps"}
        assert all(set(sub["base_drivers"][k]) == {"values", "category", "rationale", "limitation"} for k in DRIVERS)
    OUT.mkdir(parents=True, exist_ok=True)
    for fname, obj in (("manifest.json", manifest), ("submissions.json", submissions), ("expected.json", expected)):
        (OUT / fname).write_text(json.dumps(obj, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
