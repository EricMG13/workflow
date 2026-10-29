"""Writes cases/cp2d-owner/{manifest,submissions,expected}.json (stdlib only, imports nothing from src/).

Independent oracle for the CP-2D (Liquidity) owner. Every number is derived here, with Decimal,
from the FROZEN source bytes (cases/financial/manifest.json pages 3, 4, 5, parsed as text) and the
method rules written in work/lead/cp2d-owner-preparation/lease-draft.md section "Method".
No product module is imported or executed. The CP-1 head facts the product reads at run time are
not consulted here; they are bound at run time by the predicates in manifest.json and compared
with the source-derived values below.

Run: python3 -I cases/cp2d-owner/builder/build.py   (from the repository root)
"""

import hashlib
import json
import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, getcontext
from pathlib import Path

getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "cases" / "cp2d-owner"

PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    "cases/snapshot/expected.json": "d1aa1af9677cc4bd77b890261f0ceeca664acc72aac77f91da55cf36d7279baa",
    "cases/snapshot/cp2-view-tree.json": "f739395cbcf30ae2af710d8423927a8f810c8c4b948c07c6e6583e2a3b86f446",
    "cases/legal/manifest.json": "d6a8ec15285dbe16a6e2ff3f167c26a295b675decfb4df7231901b0243305168",
}
for rel, want in PINS.items():
    got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    assert got == want, (rel, got)

FIN = json.loads((ROOT / "cases/financial/manifest.json").read_text())
SNAP = json.loads((ROOT / "cases/snapshot/manifest.json").read_text())
SNAPSUB = json.loads((ROOT / "cases/snapshot/submissions.json").read_text())


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


SRC = {s["source_id"]: s for s in FIN["sources"]}
for sid, s in SRC.items():
    assert page_sha([p["text"] for p in s["pages"]]) == s["sha256"], sid
PAGE = {p["locator"]: p["text"] for p in SRC["financial"]["pages"]}
BUS = SNAP["business_source"]["positive"]
assert page_sha([p["text"] for p in BUS["pages"]]) == SNAP["cases"][0]["business_source_sha256"]
ISSUER = FIN["run"]["issuer_name"]
AS_OF = FIN["run"]["as_of"]
ENTITY = "Northbridge Synthetic Group, IFRS consolidated group"
LIMIT_FIN = SNAP["financial_pack_limitation"]["text"]
SYNTH = "Synthetic case; not real issuer qualification"

D = Decimal


# --- parse the frozen financial pages (text only) ---------------------------------------------


def num(tok):
    tok = tok.strip()
    neg = tok.startswith("(") and tok.endswith(")")
    v = D(tok.strip("()"))
    return -v if neg else v


def table(page, header_prefix):
    """rows[label] = [values] for the lines after the header line that starts with header_prefix."""
    lines = PAGE[page].split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith(header_prefix))
    rows = {}
    for ln in lines[start + 1 :]:
        parts = re.split(r"\s{2,}", ln.strip())
        if len(parts) >= 2:
            rows[parts[0]] = [num(p) for p in parts[1:]]
    return rows


CF = table("page:3", "Period")  # columns Q1 Q2 Q3 Q4 FY
BS = table("page:4", "Period end")  # columns Opening Q1 Q2 Q3 Q4 FY


def ltm(label):
    """Twelve months to 2025-12-31 = sum of the four quarters; must equal the reported FY."""
    q = CF[label][:4]
    total = sum(q, D(0))
    assert total == CF[label][4], (label, total, CF[label][4])
    return total


def bs_q4(label):
    v = BS[label]
    assert v[4] == v[5], label  # Q4 and FY balance columns are the same date
    return v[4]


# Opening cash is a balance at 2024-12-31 (not a sum of quarters); closing is a balance at 2025-12-31.
OPENING_CASH = CF["Opening cash"][0]
assert CF["Opening cash"][4] == OPENING_CASH == BS["Cash and cash equivalents"][0]
CLOSING_CASH_CF = CF["Closing cash"][3]
assert CLOSING_CASH_CF == CF["Closing cash"][4]
CFO = ltm("Operating cash flow")
INVEST = ltm("Net cash used in investing")
DEBT_ISS = ltm("Debt issuance")
DEBT_REP = ltm("Debt repayment")
NET_DEBT = ltm("Net debt issuance")
assert NET_DEBT == DEBT_ISS - DEBT_REP
EQ_ISS = ltm("Equity issuance")
EQ_BUY = ltm("Equity repurchases")
DIVID = ltm("Dividends paid")
OTHER_FIN = ltm("Other investing and financing")
FINANCING = ltm("Net cash used in financing")
FX = ltm("FX effect on cash")
assert NET_DEBT + EQ_ISS + EQ_BUY + DIVID + OTHER_FIN == FINANCING
CASH = bs_q4("Cash and cash equivalents")
RESTRICTED = bs_q4("Restricted cash")
RCF_COMMIT = bs_q4("RCF commitment")
RCF_DRAWN = bs_q4("RCF drawings")
TOTAL_DEBT = bs_q4("Total debt")
assert OPENING_CASH + CFO + INVEST + FINANCING + FX == CASH == CLOSING_CASH_CF

# facility page (page:5): one facility, the Q4 / FY row of the schedule
fac_text = PAGE["page:5"]
assert "exactly one debt facility: Northbridge Term Loan, facility_id term-loan" in fac_text
row = re.search(r"^2025-12-31\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$", fac_text, re.M)
FAC_CARRY, FAC_PRINCIPAL, FAC_DRAWN, FAC_COMMIT = (D(row.group(i)) for i in range(1, 5))
assert FAC_PRINCIPAL == TOTAL_DEBT == FAC_DRAWN
mm = re.search(r"final maturity is ([A-Z][a-z]+) (\d+), (\d{4})", fac_text)
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
MATURITY = date(int(mm.group(3)), MONTHS.index(mm.group(1)) + 1, int(mm.group(2)))
AMORT = D(re.search(r"Mandatory annual amortisation is (\S+?)[;.]", fac_text).group(1))
assert MATURITY == date(2029, 12, 31) and AMORT == 0
assert "no revolving credit facility" in PAGE["page:1"] and RCF_COMMIT == 0 == RCF_DRAWN
BAL_DATE = date(2025, 12, 31)


# --- spelling (display.py rules, transcribed): amounts 0 dp half-up, negatives in brackets -----


def q(d, places):
    return d.quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP)


def amt(d):
    r = q(d, 0)
    body = f"{abs(r):,}"
    return f"({body})" if r < 0 else body


def amt_prose(d):
    return amt(d) + " US$ m"


def pct(d):
    r = q(d * 100, 1)
    return (f"({abs(r):,})" if r < 0 else f"{r:,}") + "%"


def dec(d):
    s = format(d.normalize(), "f") if d != 0 else "0"
    return s


def fmt_date(d):
    return f"{d.day} {MONTHS[d.month - 1][:3]} {d.year}"


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    last = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30,
            31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d.day, last))


def months_between(d0, d1):
    """The largest whole number of months n with add_months(d0, n) on or before d1 (A1, round 6)."""
    n = (d1.year - d0.year) * 12 + (d1.month - d0.month)
    return n - 1 if add_months(d0, n) > d1 else n


# --- the method (lease section "Method"): Decimal, Python-owned -------------------------------


def method(flows, horizon, min_cash, *, rcf=None):
    """flows: dict of annual operands (default = the frozen source). rcf: undrawn revolver or None
    (None = undisclosed: missing, never zero)."""
    cfo, invest, fin, netdebt = flows["cfo"], flows["invest"], flows["fin"], flows["netdebt"]
    f_annual = cfo + invest + fin - netdebt
    f_month = f_annual / 12
    f_horizon = f_annual * D(horizon) / 12
    h_end = add_months(BAL_DATE, horizon)
    mature_in = MATURITY <= h_end
    mat_h = FAC_PRINCIPAL if mature_in else D(0)
    amort_h = D(0) if mature_in else min(AMORT * D(horizon) / 12, FAC_PRINCIPAL)
    end_cash = CASH + f_horizon - amort_h - mat_h
    su_closing = OPENING_CASH + cfo + invest + fin + FX  # sources and uses: calculated closing cash
    out = {
        "f_annual": f_annual, "f_month": f_month, "f_horizon": f_horizon, "horizon_end": h_end,
        "mature_in": mature_in, "mat_h": mat_h, "amort_h": amort_h, "end_cash": end_cash,
        "months_to_maturity": months_between(BAL_DATE, MATURITY),
        "su_closing": su_closing, "su_difference": su_closing - CLOSING_CASH_CF,
        "rcf_undrawn": rcf, "avail": None if rcf is None else CASH + rcf,
        "resources": None if rcf is None else end_cash + rcf,
        "cash_only_headroom": None, "headroom": None, "gap": None, "min_cash": min_cash,
        "runway_months": None, "runway_state": None, "runway_reason": None,
    }
    if min_cash is not None:
        out["cash_only_headroom"] = end_cash - min_cash
        if rcf is not None:
            out["headroom"] = out["resources"] - min_cash
            out["gap"] = max(D(0), min_cash - out["resources"])
    # Runway from run-rate cash flow ALONE (maturities and amortisation excluded, own limitation).
    if min_cash is None:
        out["runway_state"] = "missing"
        out["runway_reason"] = "minimum cash not assessed"
    elif rcf is None:
        if f_annual >= 0 and CASH - min_cash >= 0:  # revolver >= 0, so cash alone already clears it
            out["runway_state"] = "not_reached"
        else:
            out["runway_state"] = "missing"
            out["runway_reason"] = "revolver undisclosed"
    else:
        start = CASH + rcf - min_cash
        if f_annual >= 0 and start >= 0:
            out["runway_state"] = "not_reached"
        else:  # F < 0, or F >= 0 with cash + revolver below minimum cash (0 months)
            out["runway_state"] = "months"
            out["runway_months"] = q(max(D(0), start) / (-f_month), 1) if f_annual < 0 else q(D(0), 1)
    return out


BASE = {"cfo": CFO, "invest": INVEST, "fin": FINANCING, "netdebt": NET_DEBT}
assert method(BASE, 24, D(10), rcf=RCF_COMMIT - RCF_DRAWN)["f_annual"] == 0

SCEN = {
    "positive": {"horizon": 24, "min": D(10), "flows": BASE, "rcf": D(0)},
    "long_horizon": {"horizon": 60, "min": D(10), "flows": BASE, "rcf": D(0)},
    "gap_minimum_cash": {"horizon": 24, "min": None, "flows": BASE, "rcf": D(0)},
    # composer-level fixtures (no pack run): see manifest.fixtures
    "fixture_rcf_undisclosed": {"horizon": 24, "min": D(10), "flows": BASE, "rcf": None},
    # minimum cash 30 exceeds cash 20 and the revolver is undisclosed: the runway is missing, not "not reached"
    "fixture_rcf_undisclosed_min_above_cash": {"horizon": 24, "min": D(30), "flows": BASE, "rcf": None},
    "fixture_burn": {"horizon": 24, "min": D(10), "flows": dict(BASE, cfo=D("13.00")), "rcf": D(0)},
}
R = {k: method(v["flows"], v["horizon"], v["min"], rcf=v["rcf"]) for k, v in SCEN.items()}

# --- literal analyst submissions (judgment only; run-time tokens {{FACT:name}}) ---------------

FACT_NAMES = {  # name -> predicate (frozen in manifest.fact_bindings)
    "cash_closing": ("T4.10", "LTM", "cash_closing"),
    "undrawn_rcf": ("T4.10", "LTM", "undrawn_rcf"),
    "liquidity": ("T4.10", "LTM", "liquidity"),
    "total_debt": ("T4.10", "LTM", "total_debt"),
    "liquidity_to_debt": ("T4.10", "LTM", "liquidity_to_debt"),
    "cfo_reported": ("T4.10", "LTM", "cfo_reported"),
}
T45 = {  # T4.5 line -> sign convention is the CP-1 fact's own
    "opening_cash": "Opening cash", "cfo": "Operating cash flow", "investing": "Net cash used in investing",
    "debt_issuance": "Debt issuance", "debt_repayment": "Debt repayment", "net_debt_issuance": "Net debt issuance",
    "equity_issuance": "Equity issuance", "equity_repurchases": "Equity repurchases",
    "dividends_paid": "Dividends paid", "other_investing_financing": "Other investing and financing",
    "financing": "Net cash used in financing", "fx_effect": "FX effect on cash",
    "closing_cash": "Closing cash", "fcf_unlevered": "Fcf unlevered",
}
T46 = {"cash_bs": "Cash and cash equivalents", "restricted_cash": "Restricted cash",
       "rcf_commitment": "RCF commitment", "rcf_drawn": "RCF drawings", "total_debt_bs": "Total debt"}
T418 = ("principal", "maturity_date", "commitment", "drawn_amount", "annual_amortisation")


def tok(name):
    return "{{FACT:" + name + "}}"


JUDG = {
    "positive": {
        "liquidity_runway": (
            "Analyst Interpretation",
            "Cash is the only liquidity source because there is no revolving credit facility, so the runway rests on operating cash flow covering capital spending and distributions.",
            "Distributions absorb the free cash flow the business generates, leaving little internal capacity to build a liquidity cushion or reduce debt early.",
            ["cash_closing", "undrawn_rcf", "cfo_reported"],
            None,
        ),
        "maturity_wall": (
            "Documentary Fact",
            "The single term loan is the whole debt stack and falls due on one date after the horizon assessed, so no repayment is scheduled inside it.",
            "Debt service inside the horizon is limited to interest, because no principal falls due before the horizon ends.",
            ["total_debt", "T4.18 maturity_date"],
            None,
        ),
        "funding_gap": (
            "Analyst Interpretation",
            "Cash alone covers the assumed minimum cash with room to spare, so no external funding need is identified inside the horizon.",
            "The absence of committed undrawn funding means any shortfall beyond the horizon would depend on lender consent, so headroom should be monitored each period.",
            ["liquidity", "undrawn_rcf"],
            None,
        ),
    },
    "long_horizon": {
        "liquidity_runway": (
            "Analyst Interpretation",
            "Cash is the only liquidity source because there is no revolving credit facility, so the runway rests on operating cash flow covering capital spending and distributions.",
            "Distributions absorb the free cash flow the business generates, leaving no internal capacity to repay principal at maturity.",
            ["cash_closing", "undrawn_rcf", "cfo_reported"],
            None,
        ),
        "maturity_wall": (
            "Documentary Fact",
            "The single term loan is the whole debt stack and falls due inside the horizon assessed, as one payment of the full principal.",
            "A single bullet maturity concentrates repayment risk on one date and requires resources the issuer does not hold today.",
            ["total_debt", "T4.18 maturity_date"],
            None,
        ),
        "funding_gap": (
            "Analyst Interpretation",
            "Resources at the horizon end fall short of the assumed minimum cash once the term loan falls due, so an external funding need is identified.",
            "The shortfall equals the amount that must be raised or extended, and no committed undrawn facility exists to absorb it.",
            ["liquidity", "undrawn_rcf"],
            None,
        ),
    },
    "gap_minimum_cash": {
        "liquidity_runway": (
            "Analyst Interpretation",
            "Cash is the only liquidity source because there is no revolving credit facility, so the runway rests on operating cash flow covering capital spending and distributions.",
            "Distributions absorb the free cash flow the business generates, leaving little internal capacity to build a liquidity cushion or reduce debt early.",
            ["cash_closing", "undrawn_rcf", "cfo_reported"],
            None,
        ),
        "maturity_wall": (
            "Documentary Fact",
            "The single term loan is the whole debt stack and falls due on one date after the horizon assessed, so no repayment is scheduled inside it.",
            "Debt service inside the horizon is limited to interest, because no principal falls due before the horizon ends.",
            ["total_debt", "T4.18 maturity_date"],
            None,
        ),
        "funding_gap": (
            "Insufficient Information",
            "No minimum cash level is stated in the sources, so the funding need cannot be sized.",
            "Without a minimum cash level the headroom and any funding gap stay unquantified, which weakens the liquidity view.",
            ["liquidity"],
            "The minimum operating cash level is not stated in the pack sources; headroom and funding gap are not calculated.",
        ),
    },
}
MIN_CASH_TEXT = {
    "amount": "10",
    "rationale": "A cash cushion of this size is held as an analyst assumption for operating needs and is not a source figure.",
    "basis_refs": [],
}
MIN_CASH_ABSENCE = {
    "reason": "No minimum cash covenant or liquidity policy is stated in any pack source.",
    "follow_up": "Obtain the issuer's treasury policy or any minimum liquidity undertaking before sizing the funding gap.",
}


def judgments(case):
    out = []
    for section, (cat, text, impl, refs, lim) in JUDG[case].items():
        out.append({
            "section": section,
            "category": cat,
            "text": text,
            "credit_implication": impl,
            "basis_refs": [tok(r) for r in refs],
            "limitation": lim,
        })
    return out


def submission(case):
    h = SCEN[case]["horizon"]
    sub = {
        "horizon_months": h,
        "minimum_cash": dict(MIN_CASH_TEXT) if SCEN[case]["min"] is not None else None,
        "minimum_cash_absence": None if SCEN[case]["min"] is not None else dict(MIN_CASH_ABSENCE),
        "assessments": judgments(case),
    }
    return sub


SUBS = {c: submission(c) for c in ("positive", "long_horizon", "gap_minimum_cash")}

# --- builder self-checks on the literal inputs ------------------------------------------------

FORBIDDEN = ["refinanc", "recommend", "buy", "sell", "overweight", "underweight", "fulcrum", "recovery",
             "covenant breach", "covenant test is met", "in compliance with", "covenant compliance",
             "default will", "lme", "liability management"]
for c, s in SUBS.items():
    texts = [s["assessments"][i][k] for i in range(3) for k in ("text", "credit_implication")]
    texts += [a["limitation"] for a in s["assessments"] if a["limitation"]]
    if s["minimum_cash"]:
        texts.append(s["minimum_cash"]["rationale"])
    if s["minimum_cash_absence"]:
        texts += list(s["minimum_cash_absence"].values())
    for t in texts:
        assert not re.search(r"\d", t), (c, t)  # figures only as Python-owned facts
        low = t.lower()
        assert not any(w in low for w in FORBIDDEN), (c, t)
        assert t.isascii() and t.endswith("."), (c, t)
    assert [a["section"] for a in s["assessments"]] == ["liquidity_runway", "maturity_wall", "funding_gap"]
    assert (s["minimum_cash"] is None) != (s["minimum_cash_absence"] is None)
    for a in s["assessments"]:
        assert (a["category"] == "Insufficient Information") == bool(a["limitation"]), (c, a["section"])

# CP-0 delta (the one consumer entry to append to cases/snapshot/submissions.json#positive.readiness_review)
FINANCIAL_SHA = SRC["financial"]["sha256"]
IDENT_SHA = SRC["identity"]["sha256"]
Q_IDENT = "Northbridge Synthetic Group is the issuer and consolidated group."
Q_FIN1 = "Currency: USD; amounts in millions."
Q_FIN5 = "There is exactly one debt facility: Northbridge Term Loan, facility_id term-loan."
for src, loc, quote in (("identity", "page:1", Q_IDENT), ("financial", "page:1", Q_FIN1), ("financial", "page:5", Q_FIN5)):
    assert quote in SRC[src]["pages"][int(loc.split(":")[1]) - 1]["text"], (src, loc)
assert SRC["financial"]["pages"][0]["locator"] == "page:1"


def cite(sid, sha, loc, quote):
    return {"source_id": sid, "source_sha256": sha, "locator": loc, "quote": quote}


CP0_CONSUMER = {
    "module_id": "CP-2D",
    "readiness": "READY_WITH_LIMITATIONS",
    "evidence_demand": "Settled CP-1 cash flow, balance sheet and facility facts and the CP-2 credit view",
    "source_ids": ["identity", "financial"],
    "rationale": "The liquidity bridge can run on settled upstream facts with explicit source and scope limitations.",
    "citations": [
        cite("identity", IDENT_SHA, "page:1", Q_IDENT),
        cite("financial", FINANCIAL_SHA, "page:1", Q_FIN1),
        cite("financial", FINANCIAL_SHA, "page:5", Q_FIN5),
    ],
    "missing_source": None,
    "limitations": [LIMIT_FIN],
}

# --- expected tables --------------------------------------------------------------------------


def C(shown, amount=None, unit=None, vc=None, state="known", ref=None, reason=None):
    c = {"shown": shown, "state": state}
    if amount is not None:
        c["amount"] = amount if isinstance(amount, str) else dec(amount)
    if unit:
        c["unit"] = unit
    if vc:
        c["value_class"] = vc
    if ref:
        c["cp1_operand"] = ref
    if reason:
        c["reason"] = reason
    return c


# Copies of CP-1 facts: the CP-1 head carries the fact's own value_class (T4.5 'calculated', T4.6 and
# T4.18 'source') and unit 'currency' for T4.5/T4.6; the copy keeps the value_class and normalises the
# unit 'currency' -> MILLIONS (both USD, scale 1e6), so one table never mixes amount units.
CP1_CURRENCY_UNIT = set(T45) | set(T46) | {"equity_issuance+equity_repurchases"}  # the sum of two T4.5 calculated/currency copies


def A(d, vc="calculated", ref=None):
    c = C(amt(d), d, "MILLIONS", vc, ref=ref)
    if ref in CP1_CURRENCY_UNIT:
        c["cp1_unit"] = "currency"
    return c


# The CP-1 periods of the copied facts, verbatim as the manifest binds them (fact_bindings below).
PERIOD_T45 = "LTM Q4 25 · 2025-01-01 to 2025-12-31"
PERIOD_T46 = "q4-2025 · 2025-10-01 to 2025-12-31"
PERIOD_T418 = "q4-2025"
RECOMPUTED = {"undrawn_rcf", "liquidity", "liquidity_to_debt", "T4.18 commitment - drawn_amount"}


def period_of(ref):
    """Round 13 R1 M1: a copy carries its CP-1 fact's own period; a computed or recomputed cell (the
    cp1_operand tag of a recomputed cell is a twin pointer only) takes the balance date."""
    if ref is None or ref in RECOMPUTED:
        return BAL_DATE.isoformat()
    periods = set()
    for part in ref.split("+"):
        for name in part.split(" - "):
            name = name.strip()
            periods.add(PERIOD_T45 if name in T45 else PERIOD_T46 if name in T46 else PERIOD_T418)
    assert len(periods) == 1, ref
    return periods.pop()


GAP_SHOWN = "∅ G#"  # product spelling "∅ G<n>" (display.py); n is assigned by the report at run time


def GAP(reason, unit="MILLIONS", vc=None, currency=None):
    c = {"shown": GAP_SHOWN, "shown_pattern": "∅ G<n>", "state": "gap", "unit": unit, "reason": reason}
    if vc:  # Stage 2 close release (round 13 R1 M1): the gap cell names its value class
        c["value_class"] = vc
    if currency:  # a CP-2D gap twin carries its settled twin's currency (lease acceptance 1)
        c["currency"] = currency
    return c


RUNWAY_ROW = "Months until cash reaches minimum cash from run-rate cash flow alone (excludes maturities and amortisation)"


def build_tables(case):
    r = R[case]
    s = SCEN[case]
    gap_min = s["min"] is None
    undisclosed = r["rcf_undrawn"] is None
    h = s["horizon"]
    cash_cell = A(CASH, "source", "cash_bs")
    T = {}
    # T2E.1 sources and uses (historical, twelve months to 2025-12-31)
    t1 = [
        ["Opening cash (2024-12-31)", A(OPENING_CASH, "calculated", "opening_cash")],
        ["Operating cash flow", A(CFO, "calculated", "cfo")],
        ["Net cash used in investing", A(INVEST, "calculated", "investing")],
        ["Net debt issued", A(NET_DEBT, "calculated", "net_debt_issuance")],
        ["Equity issuance and repurchases", A(EQ_ISS + EQ_BUY, "calculated", "equity_issuance+equity_repurchases")],
        ["Dividends paid", A(DIVID, "calculated", "dividends_paid")],
        ["Other investing and financing", A(OTHER_FIN, "calculated", "other_investing_financing")],
        ["FX effect on cash", A(FX, "calculated", "fx_effect")],
        ["Closing cash (calculated)", A(R[case]["su_closing"])],
        ["Closing cash (reported)", A(CLOSING_CASH_CF, "calculated", "closing_cash")],
        ["Difference (calculated less reported)", A(R[case]["su_difference"])],
    ]
    T["T2E.1"] = {"title": "Liquidity sources and uses", "row_header": "Line", "columns": ["Twelve months to 2025-12-31 (US$ m)"], "rows": t1}
    # T2E.2 liquidity position
    avail_missing = undisclosed
    t2 = [
        ["Cash and cash equivalents", cash_cell],
        ["Restricted cash", A(RESTRICTED, "source", "restricted_cash")],
        ["Revolver commitment", GAP("Revolver commitment not disclosed in the CP-1 register") if undisclosed else A(RCF_COMMIT, "source", "rcf_commitment")],
        ["Revolver drawn", GAP("Revolver drawings not disclosed in the CP-1 register") if undisclosed else A(RCF_DRAWN, "source", "rcf_drawn")],
        ["Undrawn committed revolver", GAP("Undrawn revolver not calculable: commitment undisclosed") if undisclosed else A(r["rcf_undrawn"], "calculated", "undrawn_rcf")],
        ["Undrawn term loan commitment (not counted as liquidity)", A(FAC_COMMIT - FAC_DRAWN, "calculated", "T4.18 commitment - drawn_amount")],
        ["Available liquidity", GAP("Available liquidity not calculable: revolver undisclosed") if avail_missing else A(r["avail"], "calculated", "liquidity")],
        ["Total debt", A(TOTAL_DEBT, "source", "total_debt_bs")],
        ["Liquidity to total debt", GAP("Not calculable: available liquidity missing", "PERCENT") if avail_missing else C(pct(r["avail"] / TOTAL_DEBT), r["avail"] / TOTAL_DEBT, "PERCENT", "calculated", ref="liquidity_to_debt")],
    ]
    T["T2E.2"] = {"title": "Liquidity position", "row_header": "Line", "columns": ["2025-12-31 (US$ m)"], "rows": t2}
    # T2E.3 cash runway (run-rate cash flow alone; maturities and amortisation excluded)
    if r["runway_state"] == "not_reached":
        runway_cell = C("Not reached at run rate", state="known", unit="months", vc="calculated")
    elif r["runway_state"] == "months":
        runway_cell = C(f"{r['runway_months']} months", format(r["runway_months"], "f"), "months", "calculated")
    else:
        runway_cell = GAP("Not calculable: " + r["runway_reason"], "months", "calculated")
    t3 = [
        ["Run-rate net cash flow before new borrowing, per year", A(r["f_annual"])],
        ["Run-rate net cash flow before new borrowing, per month", A(r["f_month"])],
        ["Horizon (analyst judgment)", C(f"{h} months", D(h), "months", "analyst_judgment")],
        ["Horizon end date", C(r["horizon_end"].isoformat(), None, None, "calculated")],
        ["Run-rate net cash flow over the horizon", A(r["f_horizon"])],
        ["Scheduled amortisation inside the horizon", A(-r["amort_h"])],
        ["Maturities inside the horizon", A(-r["mat_h"])],
        ["Cash at horizon end before refinancing", A(r["end_cash"])],
        [RUNWAY_ROW, runway_cell],
    ]
    T["T2E.3"] = {"title": "Cash runway", "row_header": "Line", "columns": ["Value"], "rows": t3}
    # T2E.4 maturity wall
    in_h = "Yes" if r["mature_in"] else "No"
    t4 = [["Northbridge Term Loan (term-loan)", [
        A(FAC_PRINCIPAL, "source", "T4.18 principal"),
        C(MATURITY.isoformat(), None, None, "source", ref="T4.18 maturity_date"),
        C(f"{r['months_to_maturity']} months", D(r["months_to_maturity"]), "months", "calculated"),
        C(in_h, None, None, "calculated"),
        C(pct(FAC_PRINCIPAL / TOTAL_DEBT), FAC_PRINCIPAL / TOTAL_DEBT, "PERCENT", "calculated"),
        C(pct(FAC_PRINCIPAL / TOTAL_DEBT), FAC_PRINCIPAL / TOTAL_DEBT, "PERCENT", "calculated"),
    ]]]
    T["T2E.4"] = {"title": "Maturity wall", "row_header": "Facility",
                  "columns": ["Principal (US$ m)", "Maturity date", "Months from 2025-12-31", "Inside horizon", "Share of total debt", "Cumulative share"],
                  "rows": t4}
    # T2E.5 funding gap
    miss_res = undisclosed
    t5 = [
        ["Cash at horizon end before refinancing", A(r["end_cash"])],
        ["Undrawn committed revolver", GAP("Undrawn revolver not calculable: commitment undisclosed") if undisclosed else A(r["rcf_undrawn"], "calculated", "undrawn_rcf")],
        ["Resources at horizon end", GAP("Not calculable: revolver undisclosed") if miss_res else A(r["resources"])],
        ["Minimum cash (analyst judgment)", GAP("Minimum cash not assessed", vc="analyst_judgment", currency="USD") if gap_min else A(s["min"], "analyst_judgment")],
        ["Cash-only headroom over minimum cash (excludes any revolver)", GAP("Not calculable: minimum cash not assessed", vc="calculated") if gap_min else A(r["cash_only_headroom"])],
        ["Headroom over minimum cash", GAP("Not calculable: " + ("minimum cash not assessed" if gap_min else "revolver undisclosed"), vc="calculated") if (gap_min or miss_res) else A(r["headroom"])],
        ["Funding gap", GAP("Not calculable: " + ("minimum cash not assessed" if gap_min else "revolver undisclosed"), vc="calculated", currency="USD") if (gap_min or miss_res) else A(r["gap"])],
    ]
    T["T2E.5"] = {"title": "Funding gap", "row_header": "Line", "columns": ["Value (US$ m)"], "rows": t5}
    for tid, tab in T.items():  # every cell is a fact: fact_id T2E.<n>.rNN (one value column) or T2E.<n>.rNN.cK
        for ri, rw in enumerate(tab["rows"], 1):
            cells = rw[1] if isinstance(rw[1], list) else [rw[1]]
            for ci, cell in enumerate(cells, 1):
                cell["fact_id"] = f"{tid}.r{ri:02d}" + (f".c{ci}" if len(cells) > 1 else "")
                if cell["state"] == "known" and "amount" in cell:
                    cell["period"] = period_of(cell.get("cp1_operand"))
    return T


# --- expected claims (wording frozen by the lease; Python composes) ---------------------------


def prose_bare(template):
    """Digits left in a claim template once references and the 'D Mon YYYY' period label are removed (stdlib
    mirror of the MC-2 rule for these templates; the product check is deploy_vii.prose.bare_figures)."""
    t = re.sub(r"\{[^{}]*\}", "", template)
    t = re.sub(r"\b\d{1,2} [A-Z][a-z]{2} \d{4}\b", "", t)
    return re.findall(r"\d", t)


def claims(case):
    """Run text: every figure is a {<fact_id>|<unit>} reference to a cell of CP-2D's own tables (MC-2); the
    date is a period label. `text` is the resolved spelling; `references` are the cell fact_ids."""
    r, s = R[case], SCEN[case]
    d = fmt_date(BAL_DATE)
    tabs = build_tables(case)

    def cell(tid, row):
        c = tabs[tid]["rows"][row - 1][1]
        assert c["state"] == "known" and c["unit"] == "MILLIONS", (case, tid, row)
        return c

    def ref(tid, row):
        return "{" + cell(tid, row)["fact_id"] + "|US$ m}"

    def resolve(template):
        def one(m):
            c = next(c for t in tabs.values() for rw in t["rows"] for c in (rw[1] if isinstance(rw[1], list) else [rw[1]]) if c["fact_id"] == m.group(1))
            return c["shown"] + " US$ m"
        return re.sub(r"\{([^|{}]+)\|US\$ m\}", one, template)

    def claim(cid, template, cites):
        refs = re.findall(r"\{([^|{}]+)\|US\$ m\}", template)
        assert not prose_bare(template), (cid, template)
        return {"claim_id": cid, "template": template, "text": resolve(template),
                "references": list(dict.fromkeys(refs)), "cites_from": list(cites) + list(dict.fromkeys(refs))}

    cl = [
        claim("CP-2D-LIQ-01", f"Available liquidity at {d} is {ref('T2E.2', 7)} (cash {ref('T2E.2', 1)} plus undrawn committed revolver {ref('T2E.2', 5)}).",
              ["cash_closing", "undrawn_rcf", "liquidity"]),
        claim("CP-2D-RUN-01", f"Run-rate net cash flow before new borrowing is {ref('T2E.3', 1)} a year on the twelve months to {d}; cash at the end of the assessed horizon before any refinancing is {ref('T2E.3', 8)}.",
              ["cfo", "investing", "financing", "net_debt_issuance", "cash_bs"]),
        claim("CP-2D-MAT-01", f"The cash outflow from debt maturing inside the horizon is {ref('T2E.3', 7)} against total debt of {ref('T2E.2', 8)}.",
              ["T4.18 principal", "T4.18 maturity_date", "total_debt"]),
    ]
    if s["min"] is None:
        cl.append(claim("CP-2D-GAP-01", "The funding gap is not calculated: the minimum cash has not been assessed.", []))
    elif r["gap"] == 0:
        cl.append(claim("CP-2D-GAP-01", f"Resources at the horizon end exceed the assumed minimum cash by {ref('T2E.5', 6)}; no funding gap arises.", ["cash_bs", "undrawn_rcf"]))
    else:
        cl.append(claim("CP-2D-GAP-01", f"Resources at the horizon end fall short of the assumed minimum cash by {ref('T2E.5', 7)}; a funding gap of {ref('T2E.5', 7)} arises.", ["cash_bs", "undrawn_rcf"]))
    return cl


def limitations(case):
    """(ledger label, kind, text) for the module's own limitations, in order."""
    r, s = R[case], SCEN[case]
    out = [("Run-rate basis", "Limitation", "Run-rate basis: the twelve months to 31 Dec 2025 are held flat over the horizon; no forecast, growth, seasonality or new borrowing is assumed.")]
    if s["min"] is None:
        out.append(("Minimum cash", "Gap", "Minimum cash was not assessed, so headroom and funding gap are not calculated."))
    else:
        out.append(("Minimum cash", "Limitation", "Minimum cash is an analyst assumption, not a source figure."))
    out.append(("Runway basis", "Limitation", "Months until cash reaches minimum cash use run-rate cash flow alone and exclude maturities and amortisation; the maturity wall and funding gap tables show their effect."))
    if r["mature_in"]:
        out.append(("Interest after maturity", "Limitation", "Cash interest stays in the run-rate cash flow after the maturity date; interest on a repaid facility is not removed, which is conservative."))
    if r["su_difference"] != 0:
        out.append(("Sources and uses difference", "Limitation", f"Sources and uses differ from reported closing cash by {amt_prose(r['su_difference'])}."))
    if r["rcf_undrawn"] is None:
        out.append(("Funding gap on cash alone", "Limitation", "The funding gap is not calculated because the revolver is undisclosed; the cash-only headroom over minimum cash is shown as a lower bound."))
    return out


def own_limitations(case):
    return [t for _, _, t in limitations(case)]


def t2e6_rows(case):
    s = SCEN[case]
    cats = {a["section"]: a["category"] for a in SUBS[case]["assessments"]}
    return [["Horizon", f"{s['horizon']} months"],
            ["Minimum cash", "not assessed" if s["min"] is None else amt_prose(s["min"]) + " (analyst assumption)"],
            ["Liquidity runway", cats["liquidity_runway"]], ["Maturity wall", cats["maturity_wall"]],
            ["Funding gap", cats["funding_gap"]]]


def t2e7_rows(case):
    return [[label, kind] for label, kind, _ in limitations(case)]


def missing_list(r):
    """Values that are MISSING (never 0) in this case; a known zero is not listed."""
    out = [k for k, v in (("undrawn_revolver", r["rcf_undrawn"]), ("available_liquidity", r["avail"]),
                          ("resources_at_horizon_end", r["resources"]),
                          ("cash_only_headroom", r["cash_only_headroom"]), ("headroom", r["headroom"]),
                          ("funding_gap", r["gap"])) if v is None]
    if r["runway_state"] == "missing":
        out.append("months_to_minimum_cash")
    return out


def case_expected(case):
    r, s = R[case], SCEN[case]
    e = {
        "case_kind": "pack_run_clone" if case in SUBS else "composer_fixture",
        "horizon_months": s["horizon"],
        "minimum_cash": None if s["min"] is None else dec(s["min"]),
        "derived": {
            "run_rate_net_cash_flow_annual": dec(r["f_annual"]),
            "run_rate_net_cash_flow_monthly": dec(r["f_month"]),
            "run_rate_net_cash_flow_horizon": dec(r["f_horizon"]),
            "horizon_end": r["horizon_end"].isoformat(),
            "maturity_inside_horizon": r["mature_in"],
            "maturities_in_horizon": dec(r["mat_h"]),
            "amortisation_in_horizon": dec(r["amort_h"]),
            "months_to_maturity": r["months_to_maturity"],
            "cash_at_horizon_end_before_refinancing": dec(r["end_cash"]),
            "undrawn_revolver": None if r["rcf_undrawn"] is None else dec(r["rcf_undrawn"]),
            "available_liquidity": None if r["avail"] is None else dec(r["avail"]),
            "resources_at_horizon_end": None if r["resources"] is None else dec(r["resources"]),
            "cash_only_headroom": None if r["cash_only_headroom"] is None else dec(r["cash_only_headroom"]),
            "headroom": None if r["headroom"] is None else dec(r["headroom"]),
            "funding_gap": None if r["gap"] is None else dec(r["gap"]),
            "runway_state": r["runway_state"],
            "months_to_minimum_cash": None if r["runway_months"] is None else format(r["runway_months"], "f"),
            "sources_and_uses_closing_cash_calculated": dec(r["su_closing"]),
            "sources_and_uses_difference": dec(r["su_difference"]),
        },
        "missing_not_zero": missing_list(r),
    }
    e["own_limitations"] = own_limitations(case)
    if case in SUBS:
        e["tables"] = build_tables(case)
        e["T2E.6_rows"] = t2e6_rows(case)
        e["T2E.7_rows"] = t2e7_rows(case)
        e["claims"] = claims(case)
        e["status"] = "restricted"
    # composer fixtures carry `derived` and `own_limitations` only: tables would need the fixture's own
    # flows, and A4 compares `derived` only.
    return e


EXPECTED_CASES = {c: case_expected(c) for c in SCEN}

# --- cross-checks of the source-derived values against the frozen financial oracle -----------

Q4 = FIN["q4_ltm_derived_source_units"]
assert D(Q4["cfo"]) == CFO and D(Q4["capex"]) == INVEST and D(Q4["total_debt"]) == TOTAL_DEBT
assert D(Q4["net_debt"]) == TOTAL_DEBT - CASH
assert D(Q4["cash_change"]) == CASH - OPENING_CASH
LEGAL = json.loads((ROOT / "cases/legal/manifest.json").read_text())["unused_commitment_oracle"]
assert D(LEGAL["unused"]) == FAC_COMMIT - FAC_DRAWN == 0  # undrawn term loan commitment agrees
assert D(LEGAL["commitment"]) == FAC_COMMIT and D(LEGAL["drawn"]) == FAC_DRAWN

# --- manifest ---------------------------------------------------------------------------------

BUS_SHA = SNAP["cases"][0]["business_source_sha256"]
RUN = {
    "run_id": "slice-cp2d-positive",
    "issuer_id": FIN["run"]["issuer_id"],
    "issuer_name": ISSUER,
    "as_of": AS_OF,
    "method_version": FIN["run"]["method_version"],
    "case_kind": "synthetic",
    "pathway": "covenant_refinancing",
    "requested_modules": ["CP-1", "CP-1A", "CP-2", "CP-2D"],
}


def fact_bindings():
    b = {}
    LTM_P = "LTM Q4 25: 2025-01-01 to 2025-12-31"
    LTM = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
    for name, (tbl, _, metric) in FACT_NAMES.items():
        b[name] = {"table_id": tbl, "period": LTM_P, "label": f"{LTM} · {metric}",
                   "rule": "exactly one fact; zero or several fail"}
    for name, line in T45.items():
        b[name] = {"table_id": "T4.5", "period": PERIOD_T45, "label": f"{line} · LTM Q4 25",
                   "rule": "exactly one fact; status is read, never defaulted"}
    for name, line in T46.items():
        b[name] = {"table_id": "T4.6", "period": PERIOD_T46, "label": f"{line} · q4-2025",
                   "rule": "exactly one fact; status is read, never defaulted"}
    for f in T418:
        b["T4.18 " + f] = {"table_id": "T4.18", "field": f, "period": PERIOD_T418, "facility_id": "term-loan",
                           "rule": "the QUARTER period at the latest period end wins over its FY alias; the alias must agree on every term (financial_series._maturity_figure rule); one facility row per facility_id"}
    return b


manifest = {
    "schema_version": "cp2d-owner-cases/1",
    "scope": "CP-2D (Liquidity) owner inputs: a CP-0 -> CP-1 -> CP-1A -> CP-2 -> CP-2D run over the frozen S1 sources, one positive CP-2D attempt, one long-horizon attempt and one minimum-cash gap attempt cloned from the same settled upstream, plus three composer-level fixtures",
    "status": "DRAFT rev 3 2026-10-28 (preparation by mx-feature; LEAD rulings on review-precise-1 and review-precise-2 applied); independent review and LEAD adoption pending; not executed against any product core (none exists)",
    "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
    "frozen_inputs": [{"path": k, "sha256": v, "use": u} for (k, v), u in zip(PINS.items(), [
        "identity and financial sources, pages and shas reused by reference; oracle pointers q4_ltm_derived_source_units cross-checked",
        "business source pages and sha reused by reference (positive); CP-0/CP-1/CP-1A/CP-2 packs follow it",
        "literal CP-0 readiness review, CP-1 source_context, CP-1A business_context and CP-2 credit_synthesis reused unchanged except the CP-0 consumer delta below",
        "S1 expected values are NOT reused for CP-1A/CP-2 tables: the consumer set differs (no CP-MODEL), see lease open question 2",
        "CP-2 view tree (shape reference only; CP-2D's own view tree is a draft in this manifest)",
        "legal pack: unused_commitment_oracle cross-checked (undrawn term loan commitment 0); the legal source is NOT a CP-2D input (CP-4 is not an upstream edge of CP-2D)",
    ])],
    "sources": [
        {"source_id": "identity", "ref": "cases/financial/manifest.json#sources[identity]", "sha256": IDENT_SHA},
        {"source_id": "financial", "ref": "cases/financial/manifest.json#sources[financial]", "sha256": FINANCIAL_SHA, "limitation": LIMIT_FIN},
        {"source_id": "business", "ref": "cases/snapshot/manifest.json#business_source.positive", "sha256": BUS_SHA},
    ],
    "run": RUN,
    "run_note": "A new run (new run_id, pathway and requested_modules change PreparedPack.content_hash), over the S1 source bytes. The S1 positive run (slice-snapshot-positive, credit_snapshot) cannot be extended in place: Run is part of the pack (preparation.py:48-51), and FP04 composes only for pathway covenant_refinancing (render.py:130). CP-MODEL is left out of requested_modules: registry.plan puts CP-MODEL before CP-2D and G1 refuses an analytical module after a deterministic one.",
    "plan_order_expected": ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-2D"],
    "upstream_literals": {
        "CP-0": "cases/snapshot/submissions.json#positive.readiness_review with pack_sha256 bound at run time and cp0_consumer_delta appended to consumers",
        "CP-1": "cases/snapshot/submissions.json#cp1_submission and #positive.cp1_source_context (S1 CP-1 literals, imported as S1a does)",
        "CP-1A": "cases/snapshot/submissions.json#positive.business_context",
        "CP-2": "cases/snapshot/submissions.json#positive.credit_synthesis with {{FIG:name}} replaced as S1a lease rev 2 M2 freezes",
    },
    "cp0_consumer_delta": "submissions.json#cp0_consumer_delta",
    "analyst_judgment_policy": "Horizon, minimum cash and the three assessments are literal submission input. Figures never appear in submitted text (builder-checked: no digit, no refinancing/LME/recommendation/recovery word).",
    "fact_bindings": fact_bindings(),
    "fact_binding_note": "Predicates were observed on a real promoted CP-1 head (work/lead/s1a-task1/report.md store, probed read-only 2026-10-28): each of the names below selects exactly one fact there. {{FACT:name}} tokens in basis_refs are replaced by that fact's fact_id at run time.",
    "view_tree_draft": {
        "status": "DRAFT: shape proposed by this preparation, not observed (no core exists); LEAD freezes it after a probe on the first product-settled core, as S1a did for CP-2",
        "view": "owners.cp2d.view(historical, attempt) -> (sha256, body), registered in G1's _VIEWS['liquidity_bridge'] (docs/G1X-OWNER-CORE-PROTOCOL.md); NOT module_context(), which has no liquidity_bridge entry",
        "top_level_keys_in_order": ["upstream", "cp1_facts", "cp1_facts_note", "bounds", "inherited_limitations"],
        "upstream": "[{module_id, status}] for CP-0, CP-1, CP-2 (the three edges; CP-1A is not an edge and is not read)",
        "cp1_facts": "[{ref, name, label, period, unit, shown, status, limitation|null}] one entry per name in fact_bindings, INCLUDING missing facts (status missing, shown a gap word, never a number); sorted by name",
        "bounds": {"horizon_months": [1, 60], "minimum_cash": "decimal >= 0 in US$ m, or null with minimum_cash_absence"},
        "forbidden_keys": ["quote", "citations", "record_json", "formula", "source_amount", "stated_amount"],
    },
    "cases": [
        {"case_id": "positive", "base": "settled upstream of slice-cp2d-positive", "submission": "submissions.json#cp2d.positive"},
        {"case_id": "long_horizon", "base": "clone of the positive store before CP-2D begins", "submission": "submissions.json#cp2d.long_horizon"},
        {"case_id": "gap_minimum_cash", "base": "clone of the positive store before CP-2D begins", "submission": "submissions.json#cp2d.gap_minimum_cash"},
        {"case_id": "blocked_cp2d", "base": "clone of the positive store before CP-2D begins", "submission": "submissions.json#cp2d_blocked (attempts 0 and 1 both invalid)", "expected": "expected.json#negative_cases.blocked_cp2d"},
        {"case_id": "begin_refused_cp2_blocked", "base": "clone of the settled upstream with CP-2 re-settled blocked (CP-2 attempts 0 and 1 both fail a rule, as in docs/S1A-OWNER-RUN-LEASE.md, the unreplaced {{FIG}} case) before CP-2D begins", "submission": "none: begin is refused", "expected": "expected.json#negative_cases.begin_refused_cp2_blocked"},
    ],
    "fact_copy_rule": "A table cell copied from a CP-1 fact keeps that fact's value_class (T4.5 statement-history facts: calculated; T4.6 and T4.18: source) and normalises the unit 'currency' -> MILLIONS (both USD, scale 1e6) so a table never mixes amount units; copied cells carry cp1_unit='currency' in expected.json as the record of the normalisation.",
    "fixtures": [
        {"fixture_id": "fixture_rcf_undisclosed", "kind": "composer-level unit fixture, not a pack run",
         "construction": "the positive CP-1 fact set with these facts replaced by status missing and the limitation 'Required statement item not supplied': T4.6 RCF commitment, T4.6 RCF drawings, T4.10 undrawn_rcf and T4.10 liquidity (and liquidity_to_debt). Why not a run: the frozen financial source states 'There is no revolving credit facility' and shows RCF 0 (explicit zero); an undisclosed revolver needs a new financial source variant and a new CP-1 promotion, deferred (lease open question 1)."},
        {"fixture_id": "fixture_rcf_undisclosed_min_above_cash", "kind": "composer-level unit fixture, not a pack run",
         "construction": "as fixture_rcf_undisclosed (same missing facts) with minimum cash 30, above cash 20: cash alone does not clear the minimum and the revolver is unknown, so the runway is missing ('Not calculable: revolver undisclosed'), not 'not reached'; cash-only headroom (10) stays known."},
        {"fixture_id": "fixture_burn", "kind": "composer-level unit fixture, not a pack run",
         "construction": "the positive CP-1 fact set with T4.5 Operating cash flow (LTM Q4 25) replaced by 13.00 and every dependent total left as in the positive set (so sources and uses calculate closing cash 14 against reported 20, difference (6), shown as an own limitation); exercises a negative run-rate and the months-to-minimum-cash arithmetic that no frozen pack reaches (all frozen flows net to zero)."},
    ],
    "consumer": {
        "planned": "CP-3C (refinancing / LME risk; required edge CP-2D -> CP-3C, methodology.json)",
        "exists_today": False,
        "other_readers": "CP-3 and CP-6 never read CP-2D (cp3_relative_value.py:100, cp6_committee.py:113); CP-5 reads it only after a D3 scope lease",
        "consumption_proof": "OPEN: no consumer core exists, so no consumption can be proven in this lease",
    },
}

def payload_from(base_case, change):
    """A complete literal refusal payload: a deep copy of SUBS[base_case] with one defect applied here, so the
    written file carries no mutation directive. `change` takes and returns the payload dict."""
    out = json.loads(json.dumps(SUBS[base_case]))
    change(out)
    assert out != SUBS[base_case], "a refusal payload must differ from its base"
    return {"base_case": base_case, "payload": out}


def _row(p, section):
    return next(a for a in p["assessments"] if a["section"] == section)


def _append(section, field, suffix):
    def f(p):
        _row(p, section)[field] += suffix
    return f


def _set(key, value):
    def f(p):
        p[key] = value
    return f


def _drop(section):
    def f(p):
        p["assessments"] = [a for a in p["assessments"] if a["section"] != section]
    return f


def _duplicate(section):
    def f(p):
        p["assessments"].append(dict(_row(p, section)))
    return f


def _basis(section, ref):
    def f(p):
        _row(p, section)["basis_refs"].append(ref)
    return f


def _limit(section, text):
    def f(p):
        _row(p, section)["limitation"] = text
    return f


REFUSAL_INPUTS = {
    "horizon_zero": payload_from("positive", _set("horizon_months", 0)),
    "horizon_over_limit": payload_from("positive", _set("horizon_months", 61)),
    "minimum_cash_negative": payload_from("positive", _set("minimum_cash", dict(MIN_CASH_TEXT, amount="-1"))),
    "minimum_cash_and_absence": payload_from("positive", _set("minimum_cash_absence", dict(MIN_CASH_ABSENCE))),
    "neither_minimum_cash_nor_absence": payload_from("positive", _set("minimum_cash", None)),
    "section_missing": payload_from("positive", _drop("maturity_wall")),
    "section_repeated": payload_from("positive", _duplicate("funding_gap")),
    "digit_in_text": payload_from("positive", _append("liquidity_runway", "text", " It is 5 per cent.")),
    "covenant_compliance_wording": payload_from("positive", _append("maturity_wall", "credit_implication", " The covenant test is met.")),
    "figure_free_text_forbidden_word": payload_from("positive", _append("funding_gap", "credit_implication", " A refinancing path is available.")),
    "unknown_basis_ref": payload_from("positive", _basis("liquidity_runway", "{{FACT:not_a_fact}}")),
    "insufficient_without_limitation": payload_from("gap_minimum_cash", _limit("funding_gap", None)),
    "limitation_without_insufficient": payload_from("positive", _limit("maturity_wall", "A limitation without a gap.")),
}

submissions = {
    "schema_version": "cp2d-owner-submissions/1",
    "note": "Literal analyst input only. {{FACT:name}} tokens are replaced by CP-1 fact ids at run time (manifest.fact_bindings). CP-0, CP-1, CP-1A and CP-2 literals are those of cases/snapshot/submissions.json, unchanged.",
    "cp0_consumer_delta": CP0_CONSUMER,
    "cp2d": SUBS,
    "cp2d_blocked": {
        "note": "L5: attempt 0 and attempt 1 are both invalid, so CP-2D settles blocked. Each attempt is a full literal payload (the same as refusal_inputs.horizon_zero and .horizon_over_limit); attempt 1 is begun with repair_of set.",
        "attempt_0": REFUSAL_INPUTS["horizon_zero"]["payload"],
        "attempt_1": REFUSAL_INPUTS["horizon_over_limit"]["payload"],
    },
    "refusal_inputs": dict({"note": "Each entry is a full literal payload (base_case names the cp2d case it was derived from); expected issue wording is fixed in expected.json#refusals. A wrong-typed horizon is a schema type error owned by G1's generic schema refusal, not a CP-2D validator class."}, **REFUSAL_INPUTS),
}

REFUSALS = {
    "horizon_zero": "horizon_months must be between 1 and 60",
    "horizon_over_limit": "horizon_months must be between 1 and 60",
    "minimum_cash_negative": "minimum_cash.amount must not be negative",
    "minimum_cash_and_absence": "give minimum_cash or minimum_cash_absence, not both",
    "neither_minimum_cash_nor_absence": "give minimum_cash or minimum_cash_absence",
    "section_missing": "assessments must hold exactly one row per section",
    "section_repeated": "assessments must hold exactly one row per section",
    "digit_in_text": "text must not contain a figure",
    "covenant_compliance_wording": "text carries a prohibited conclusion",
    "figure_free_text_forbidden_word": "text carries a prohibited conclusion",
    "unknown_basis_ref": "basis_refs names a fact the view does not offer",
    "insufficient_without_limitation": "an Insufficient Information assessment states its limitation",
    "limitation_without_insufficient": "only an Insufficient Information assessment carries a limitation",
}

DEPS = {
    "fixture_rcf_undisclosed_note": "available liquidity, resources, headroom and funding gap are missing (never 0); cash_only_headroom is the lower bound that stays known",
}

expected = {
    "schema_version": "cp2d-owner-expected/1",
    "claims_note": "Claim templates are run text (decision 0005 MC-2, execution.py:296): every figure is a {<fact_id>|<unit>} reference to a cell of CP-2D's own tables, the date is a period label, the horizon length is not spelled (the horizon cell is an uncited analyst_judgment fact and cannot be a figure reference); `text` is the resolved spelling; `references` lists the cell fact_ids.",
    "derivation_note": "Every value is a Decimal derived by cases/cp2d-owner/builder/build.py from page:3, page:4 and page:5 of the frozen financial source (parsed as text) and the method in the lease. Comparison is numeric Decimal equality (trailing zeros irrelevant); `shown` is the exact display spelling (display.py rules: amounts 0 dp half-up, negatives in brackets, percent 1 dp). Entity: " + ENTITY + "; currency USD; unit MILLIONS (US$ m); period: balance date 2025-12-31, flows twelve months 2025-01-01 to 2025-12-31 (LTM Q4 25 = FY25, identical).",
    "source_facts": {
        "opening_cash_2024_12_31": {"amount": dec(OPENING_CASH), "source": "financial page:3 Opening cash (FY column); page:4 Cash and cash equivalents (Opening 2024-12-31)"},
        "operating_cash_flow_ltm": {"amount": dec(CFO), "derivation": "Q1+Q2+Q3+Q4 = 4.75 x 4", "source": "financial page:3 Operating cash flow; FY column 19.00 agrees"},
        "net_cash_used_in_investing_ltm": {"amount": dec(INVEST), "derivation": "(2.5) x 4", "source": "financial page:3"},
        "net_debt_issuance_ltm": {"amount": dec(NET_DEBT), "derivation": "debt issuance 5.00 less repayment 0", "source": "financial page:3"},
        "equity_issuance_plus_repurchases_ltm": {"amount": dec(EQ_ISS + EQ_BUY), "source": "financial page:3 (explicit zeros)"},
        "dividends_paid_ltm": {"amount": dec(DIVID), "derivation": "(2.25) x 4", "source": "financial page:3"},
        "other_investing_financing_ltm": {"amount": dec(OTHER_FIN), "source": "financial page:3 (explicit zero)"},
        "net_cash_used_in_financing_ltm": {"amount": dec(FINANCING), "derivation": "5 + 0 + 0 + (9) + 0 = (4)", "source": "financial page:3"},
        "fx_effect_ltm": {"amount": dec(FX), "source": "financial page:3 (explicit zero)"},
        "closing_cash_2025_12_31": {"amount": dec(CASH), "derivation": "15 + 19 + (10) + (4) + 0 = 20", "source": "financial page:3 Closing cash; page:4 Cash and cash equivalents (Q4)"},
        "restricted_cash": {"amount": dec(RESTRICTED), "source": "financial page:4 (explicit zero)"},
        "rcf_commitment": {"amount": dec(RCF_COMMIT), "source": "financial page:4 RCF commitment (explicit zero); page:1 'There is no revolving credit facility'"},
        "rcf_drawn": {"amount": dec(RCF_DRAWN), "source": "financial page:4 RCF drawings (explicit zero)"},
        "total_debt": {"amount": dec(TOTAL_DEBT), "source": "financial page:4 Total debt (Q4)"},
        "term_loan": {"facility_id": "term-loan", "principal": dec(FAC_PRINCIPAL), "drawn": dec(FAC_DRAWN), "commitment": dec(FAC_COMMIT), "maturity_date": MATURITY.isoformat(), "annual_amortisation": dec(AMORT), "source": "financial page:5; the legal pack Clause 1.3 and cases/legal unused_commitment_oracle (unused 0) agree"},
        "undrawn_term_loan_commitment": {"amount": dec(FAC_COMMIT - FAC_DRAWN), "derivation": "50 - 50"},
        "unlevered_free_cash_flow": {"state": "missing", "source": "financial page:1 'source-reported unlevered free cash flow ... not disclosed'; CP-1 fact status missing; never used and never shown as 0"},
    },
    "method_rules": {
        "balance_date": BAL_DATE.isoformat(),
        "horizon_end": "balance_date + horizon_months (month arithmetic, end of month clamped)",
        "run_rate_net_cash_flow_annual": "operating cash flow + net cash used in investing + net cash used in financing - net debt issuance (every non-debt flow of the twelve months; new borrowing is excluded because committed undrawn funding is zero)",
        "run_rate_over_horizon": "annual x horizon_months / 12",
        "maturities_in_horizon": "principal of a facility whose maturity_date <= horizon_end, else 0",
        "amortisation_in_horizon": "for a facility maturing after the horizon: min(annual_amortisation x horizon_months / 12, principal); 0 when it matures inside",
        "cash_at_horizon_end_before_refinancing": "closing cash + run-rate over horizon - amortisation - maturities",
        "available_liquidity": "closing cash + undrawn committed revolver (revolver commitment - revolver drawn); equals the CP-1 T4.10 liquidity fact, asserted",
        "resources_at_horizon_end": "cash at horizon end before refinancing + undrawn committed revolver",
        "headroom": "resources - minimum cash",
        "funding_gap": "max(0, minimum cash - resources); a computed 0 is 'no gap', distinct from missing",
        "months_to_minimum_cash": "run-rate cash flow alone (maturities and amortisation excluded; own limitation, the wall is in T2E.4/T2E.5). start = closing cash + undrawn revolver - minimum cash. Minimum cash missing: state 'missing' ('Not calculable: minimum cash not assessed'). Annual run-rate < 0: max(0, start) / (-annual / 12), 1 dp half-up. Annual >= 0: state 'not_reached' (text 'Not reached at run rate') when start >= 0, 0 months when start < 0. Revolver missing: 'not_reached' only when annual >= 0 and closing cash alone >= minimum cash (a revolver is never negative), else 'missing' ('Not calculable: revolver undisclosed'). The stored value is quantised to 1 dp ('20.0', never '2E+1')",
        "sources_and_uses_difference": "calculated closing cash (opening + operating + investing + financing + FX) less reported closing cash; shown as a known value (zero is a known zero); a non-zero difference adds the own limitation 'Sources and uses differ from reported closing cash by <x>' and never refuses",
        "missing_rule": "any missing operand makes the dependent value missing with a limitation; nothing defaults to 0; cash_only_headroom (excludes the revolver) is the only value that stays known when the revolver is missing",
        "horizon_bound": "1..60 months (near-term)",
        "table_signs": "`derived` values are magnitudes; tables show cash outflows (amortisation, maturities) and negative balances in brackets, so a 50 maturity is shown (50); display rounds half away from zero (display.py ROUND_HALF_UP on the exact decimal), so fixture_burn's monthly (0.5) outflow is shown (1)",
        "months_between": "largest whole number of months n with balance date + n months (end of month clamped) on or before the date",
    },
    "cases": EXPECTED_CASES,
    "cp0_with_cp2d": {
        "status": "restricted",
        "live_consumers": ["CP-1", "CP-1A", "CP-2", "CP-2D"],
        "plan_order": ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-2D"],
        "exact_commands": {"CP-1": "Run CP-1", "CP-1A": "Run CP-1A", "CP-2": "Run CP-2", "CP-2D": "Run CP-2D"},
        "added_facts": [
            {"fact_id": "T4.CP-2D.demand", "text": CP0_CONSUMER["evidence_demand"], "cites": [["identity", "page:1"], ["financial", "page:1"], ["financial", "page:5"]]},
            {"fact_id": "T4.CP-2D.readiness", "text": "READY_WITH_LIMITATIONS", "cites": []},
            {"fact_id": "T4.CP-2D.rationale", "text": CP0_CONSUMER["rationale"], "cites": [["identity", "page:1"], ["financial", "page:1"], ["financial", "page:5"]]},
            {"fact_id": "T8.CP-2D.candidate_command", "text": "Run CP-2D", "cites": []},
            {"fact_id": "T8.CP-2D.exact_command", "text": "Run CP-2D", "cites": []},
            {"fact_id": "T8.CP-2D.sources", "text": "identity, financial", "cites": []},
            {"fact_id": "T8.CP-2D.limits", "text": LIMIT_FIN, "cites": []},
            {"fact_id": "T8.CP-2D.upstream", "text": "CP-0 slice-cp2d-positive; analytical dependencies checked separately", "cites": []},
        ],
        "note": "Pattern copied from cases/snapshot/expected.json positive.CP-0 for CP-2 (T4.CP-2.*, T8.CP-2.*); the CP-0 limitations are those of the S1 literal (LIMIT_FIN, SYNTH). Not verified against a product CP-0 settle.",
    },
    "upstream_asserted_only": {
        "statuses": {"CP-0": "restricted", "CP-1": "restricted", "CP-1A": "restricted", "CP-2": "restricted"},
        "cp1_facts_equal_source": "each fact bound by manifest.fact_bindings has the amount/status derived above (source_facts) - this is the cross-check that the CP-1 head and the source agree",
        "not_reused": "S1 expected CP-1A and CP-2 tables, which depend on the CP-MODEL consumer; only the statuses and the CP-1 facts are asserted here",
    },
    "cp2d_module": {
        "module_id": "CP-2D",
        "status_rule": "restricted: own limitations are non-empty and CP-0, CP-1 and CP-2 heads are restricted",
        "attempt_inputs": ["prepared-pack", "CP-0", "CP-1", "CP-2"],
        "settled_module_adds_input": "liquidity-bridge-submission",
        "inherited_limitations_rule": "literal CP-0 limitations + CP-1 head (limitations then inherited) + CP-2 head (limitations then inherited), de-duplicated, own findings removed (execution.py:345-366); CP-1A is not an edge of CP-2D and is not read; values bound from the heads at run time",
        "table_ids": ["T2E.1", "T2E.2", "T2E.3", "T2E.4", "T2E.5", "T2E.6", "T2E.7", "T2E.9"],
        "table_titles_note": "T2E.6 Analyst judgments, T2E.7 Gaps ledger, T2E.9 CP-1 source trace: contents below; T2E.8 is unused (not in methodology.json)",
        "T2E.6": {"title": "Analyst judgments", "rows": "expected.cases.<case>.T2E.6_rows"},
        "T2E.7": {"title": "Gaps ledger", "rows": "expected.cases.<case>.T2E.7_rows (one row per own limitation, same order as own_limitations)"},
        "T2E.9": {"title": "CP-1 source trace", "rule": "one row per name in manifest.fact_bindings that the composer read: name, CP-1 fact_id (run time), table, period, shown or gap word; fcf_unlevered is listed as read-and-unused with status missing"},
        "evidence_rail": ["T2E.6", "T2E.9"], "limitations_rail": ["T2E.7"],
    },
    "refusals": REFUSALS,
    "negative_cases": {
        "blocked_cp2d": {
            "attempt_0": {"step": "invalid", "issues": [REFUSALS["horizon_zero"]]},
            "attempt_1": {"step": "invalid", "issues": [REFUSALS["horizon_over_limit"]], "repair_of": "attempt 0"},
            "module_status": "blocked",
            "tables": "none; a blocked head carries no T2E table and no claims",
            "head": "a blocked CP-2D head is published; cp2d_reader(store, head) on it exposes the status and no figures",
            "receipt": "verify_owner_run_receipt accepts the blocked head and every recomputed issue appears in the step issues",
        },
        "begin_refused_cp2_blocked": {
            "outcome": "begin refused (edge_rule block): 'Required upstream is unrun, stale or blocked'",
            "attempt_consumed": False,
            "head": "none",
            "also": "a stale required head is not a retained refusal: begin re-raises ValueError, an integrity fault in the store snapshot, and consumes no attempt",
        },
    },
    "tool_use": {
        "CP-2D": "zero ok pack calls (every invoke is a refused not_permitted receipt); exactly one read_inputs per attempt before submit; its body equals the frozen view tree (manifest.view_tree_draft after freeze); a submit without that read is not_permitted; a snapshot change between read and submit is stale_binding",
    },
    "consumption": {
        "consumer": "none today; CP-3C planned (required edge)",
        "reader_contract": "owners.cp2d.cp2d_reader(store, head) returns the settled CP-2D head's horizon, minimum cash (or its absence), maturity-wall rows, funding gap (or missing), the head hash and status",
        "status": "OPEN: acceptance of consumption waits for a CP-3C lease (or a D3 CP-5 scope lease); this oracle pins only what the reader must expose",
    },
    "fp04_render": {
        "pathway": "covenant_refinancing",
        "blocks": {
            "liquidity-runway": {"owner": "CP-2D", "kind": "dense", "primary_tab": "T2E.3", "tabs": ["T2E.1"], "state": "populated"},
            "maturity-wall": {"owner": "CP-2D", "kind": "dense", "primary_tab": "T2E.4", "tabs": [], "state": "populated"},
            "funding-gap": {"owner": "CP-2D", "kind": "dense", "primary_tab": "T2E.5", "tabs": ["T2E.2"], "state": "populated"},
        },
        "rails": {"evidence": ["T2E.6", "T2E.9"], "limitations": ["T2E.7"]},
        "cells": "block cell text equals the `shown` strings of expected.cases.<case>.tables for the same table id; gap cells render the product spelling '∅ G<n>' (display.py) with n assigned in report order: the expected `shown` of a gap cell is the pattern '∅ G#', an A7 exception that matches '∅ G' plus digits",
        "other_FP04_blocks": "CP-4 and CP-3C blocks are not asserted (CP-4 is not requested; CP-3C has no core)",
    },
    "table_id_collision_check": "T2E.1-T2E.7 and T2E.9 appear only under CP-2D in src/deploy_vii/methodology.json and in no other module, source file or test (grep and script, 2026-10-28); T2E.8 is not registered and stays unused",
    "not_verified": [
        "no product CP-2D core exists, so no expected value has been compared with product output",
        "the CP-1 head facts were observed (read-only) on the S1 positive store for the predicates and the equalities asserted here, but the CP-0 delta was never settled",
        "months-to-minimum-cash is exercised only by fixture_burn (20.0) and non-zero amortisation by no case; no frozen pack reaches them; the 0-month runway branch (F >= 0 with start < 0, stored 0.0) and the revolver-missing F < 0 branch are exercised by no case (fixture_rcf_undisclosed reaches 'not reached' and fixture_rcf_undisclosed_min_above_cash reaches 'missing: revolver undisclosed')",
        "claim references: the expected claims were probed read-only with deploy_vii.prose.bare_figures only; no product module has resolved the {<fact_id>|<unit>} references, and the T2E cell fact_ids (T2E.<n>.rNN[.cK]) are this oracle's proposal",
        "the value_class and unit normalisation of copied cells (cp1_unit currency -> MILLIONS) was read from the CP-1 head by probe, but the composer's T2E.1 table was never rendered",
        "the blocked_cp2d and begin_refused_cp2_blocked expectations follow the S1a lease pattern and were never run",
        "an undisclosed revolver in a real CP-1 promotion (fixture_rcf_undisclosed is composer-level only)",
        "table titles, columns and claim wording are this preparation's design: r14 CP-2D SKILL.md is not in the repository",
    ],
}


def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write("manifest.json", manifest)
    write("submissions.json", submissions)
    write("expected.json", expected)
    for n in ("manifest.json", "submissions.json", "expected.json"):
        print(n, hashlib.sha256((OUT / n).read_bytes()).hexdigest())
