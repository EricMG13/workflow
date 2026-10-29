"""Writes cases/cp3c-owner/{manifest,submissions,expected}.json (stdlib only, imports nothing from src/).

Independent oracle for the CP-3C (Refinancing and liability-management risk) owner. Every number is derived
here, with Decimal, from the FROZEN source bytes (cases/financial/manifest.json pages 2, 3, 4, 5, parsed as
text), from the frozen CP-2D oracle cells it consumes (cases/cp2d-owner/expected.json, sha256-pinned) and from
the method in work/lead/cp3c-owner-preparation/lease-draft.md. No product module is imported or executed.
The CP-1 head facts the product reads at run time are bound at run time by the predicates in manifest.json.

Run: python3 -I cases/cp3c-owner/builder/build.py   (from the repository root)
"""

import hashlib
import json
import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, getcontext
from pathlib import Path

getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "cases" / "cp3c-owner"

PINS = {
    "src/deploy_vii/methodology.json": "0932d9fbcd9272d62bcb7681e1dd16d9bc944319c64716b41dc79715699796e8",
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    "cases/cp2d-owner/manifest.json": "d92861e03dc43b6e92504b10b61fdd2d4a61d243c378e2d3b4bf816b3aed4503",
    "cases/cp2d-owner/submissions.json": "cf0a4a773053f5925e0ab69ec64f0962e75d5e051287a1176ff994c74319946c",
    "cases/cp2d-owner/expected.json": "c60797a22c9700fb3ded9cb5de58d64349bf6672a445a6cbbc9c595bc3a124dc",
    "cases/cp2d-owner/builder/build.py": "0dd71e009ee8c95f39253de0658b9c46783655f6d490b56d5f6611c7e5d9a1bc",
    "src/deploy_vii/business_context.py": "895cab5e09dd4e3eb48ddc41a2928e0441f74f1acb402539e85622934a2c9cde",
}
for rel, want in PINS.items():
    got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    assert got == want, (rel, got)

D = Decimal
METH = json.loads((ROOT / "src/deploy_vii/methodology.json").read_text())
FIN = json.loads((ROOT / "cases/financial/manifest.json").read_text())
SNAP = json.loads((ROOT / "cases/snapshot/manifest.json").read_text())
C2D_SUB = json.loads((ROOT / "cases/cp2d-owner/submissions.json").read_text())
C2D_EXP = json.loads((ROOT / "cases/cp2d-owner/expected.json").read_text())
C2D_MAN = json.loads((ROOT / "cases/cp2d-owner/manifest.json").read_text())

# --- edges and table ids (D4, D8) from the pinned methodology.json -------------------------------

MOD = {m["module_id"]: m for m in METH}
CP3C = MOD["CP-3C"]
assert CP3C["required"] == ["CP-0", "CP-1", "CP-2D"], CP3C["required"]
assert CP3C["optional"] == ["CP-1A", "CP-2A", "CP-4", "CP-3D"], CP3C["optional"]
assert CP3C["table_ids"] == sorted(f"T3D.{n}" for n in range(1, 12)) or set(CP3C["table_ids"]) == {
    f"T3D.{n}" for n in range(1, 12)
}
for other_id, other in MOD.items():
    if other_id != "CP-3C":
        assert not any(t.startswith("T3D.") for t in other["table_ids"]), other_id  # D8: no collision
USED_TABLES = [f"T3D.{n}" for n in range(1, 10)]  # T3D.10 and T3D.11 are registered and unused


def closure(module_id, seen=None):
    seen = set() if seen is None else seen
    for r in MOD[module_id]["required"]:
        if r not in seen:
            seen.add(r)
            closure(r, seen)
    return seen


assert closure("CP-3C") == {"CP-0", "CP-1", "CP-1A", "CP-2", "CP-2D"}, closure("CP-3C")
PLAN_ORDER = ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-2D", "CP-3C"]
OPTIONAL_UNREAD = ["CP-1A", "CP-2A", "CP-4", "CP-3D"]


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


SRC = {s["source_id"]: s for s in FIN["sources"]}
for sid, s in SRC.items():
    assert page_sha([p["text"] for p in s["pages"]]) == s["sha256"], sid
PAGE = {p["locator"]: p["text"] for p in SRC["financial"]["pages"]}
BUS = SNAP["business_source"]["positive"]
assert page_sha([p["text"] for p in BUS["pages"]]) == SNAP["cases"][0]["business_source_sha256"]
BUS_SHA = SNAP["cases"][0]["business_source_sha256"]
ISSUER = FIN["run"]["issuer_name"]
AS_OF = FIN["run"]["as_of"]
ENTITY = "Northbridge Synthetic Group, IFRS consolidated group"
LIMIT_FIN = SNAP["financial_pack_limitation"]["text"]
FINANCIAL_SHA = SRC["financial"]["sha256"]
IDENT_SHA = SRC["identity"]["sha256"]
BAL_DATE = date(2025, 12, 31)
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


# --- parse the frozen financial pages (text only) ---------------------------------------------


def num(tok):
    tok = tok.strip()
    neg = tok.startswith("(") and tok.endswith(")")
    v = D(tok.strip("()"))
    return -v if neg else v


def table(page, header_prefix):
    lines = PAGE[page].split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith(header_prefix))
    rows = {}
    for ln in lines[start + 1:]:
        parts = re.split(r"\s{2,}", ln.strip())
        if len(parts) >= 2:
            try:
                rows[parts[0]] = [num(p) for p in parts[1:]]
            except InvalidOperation:  # a text row (a note or label) is not a numeric table row
                continue
    return rows


IS = table("page:2", "Period")  # Q1 Q2 Q3 Q4 FY
CF = table("page:3", "Period")  # Q1 Q2 Q3 Q4 FY
BS = table("page:4", "Period end")  # Opening Q1 Q2 Q3 Q4 FY


def ltm(tbl, label):
    q = tbl[label][:4]
    total = sum(q, D(0))
    assert total == tbl[label][4], (label, total, tbl[label][4])
    return total


EBITDA_ADJ = ltm(IS, "Adjusted EBITDA")  # 30.0 (CP-1 T4.10 adjusted_ebitda)
CASH_INTEREST = ltm(CF, "Cash interest paid")  # 5.00 paid (CP-1 T4.10 cash_interest = -5.00, an outflow)
CFO = ltm(CF, "Operating cash flow")
INVEST = ltm(CF, "Net cash used in investing")
NET_DEBT_ISS = ltm(CF, "Net debt issuance")
FINANCING = ltm(CF, "Net cash used in financing")
CASH = BS["Cash and cash equivalents"][4]
assert BS["Cash and cash equivalents"][4] == BS["Cash and cash equivalents"][5]
RCF_COMMIT = BS["RCF commitment"][4]
RCF_DRAWN = BS["RCF drawings"][4]
UNDRAWN = RCF_COMMIT - RCF_DRAWN
TOTAL_DEBT = BS["Total debt"][4]
F_ANNUAL = CFO + INVEST + FINANCING - NET_DEBT_ISS  # CP-2D run-rate annual flow (re-derived, then pinned below)
assert F_ANNUAL == D(C2D_EXP["cases"]["positive"]["derived"]["run_rate_net_cash_flow_annual"]) == 0

fac_text = PAGE["page:5"]
assert "exactly one debt facility: Northbridge Term Loan, facility_id term-loan" in fac_text
assert "It is a senior secured term loan, not a lease." in fac_text
assert "floating rate type with SOFR reference rate, spread 0 basis points and floor 0 basis points" in fac_text
row = re.search(r"^2025-12-31\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$", fac_text, re.M)
FAC_PRINCIPAL = D(row.group(2))
assert FAC_PRINCIPAL == TOTAL_DEBT == D(row.group(3))
mm = re.search(r"final maturity is ([A-Z][a-z]+) (\d+), (\d{4})", fac_text)
MATURITY = date(int(mm.group(3)), MONTHS.index(mm.group(1)) + 1, int(mm.group(2)))
AMORT = D(re.search(r"Mandatory annual amortisation is (\S+?)[;.]", fac_text).group(1))
assert MATURITY == date(2029, 12, 31) and AMORT == 0
# "senior secured term loan" -> CP-1 T4.18 secured_status SECURED, seniority SENIOR (observed on a promoted CP-1 head)
TL_SECURED, TL_SENIORITY = "SECURED", "SENIOR"
assert UNDRAWN == 0 and CASH == 20 and EBITDA_ADJ == 30 and CASH_INTEREST == 5


# --- spelling (display.py rules, transcribed) ---------------------------------------------------


def q(d, places):
    return d.quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP)


def amt(d):
    r = q(d, 0)
    body = f"{abs(r):,}"
    return f"({body})" if r < 0 else body


def mult(d):
    r = q(d, 2)
    body = f"{abs(r):,.2f}"
    return (f"({body})" if r < 0 else body) + "x"


def pct(d):
    r = q(d * 100, 1)
    body = f"{abs(r):,.1f}"
    return (f"({body})" if r < 0 else body) + "%"


def dec(d):
    return format(d.normalize(), "f") if d != 0 else "0"


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


def r4(x):
    """Ratios are stored quantised to 4 dp half-up (the shown value rounds from the stored one)."""
    return q(x, 4)


# --- the method (lease section "Method"): Decimal, Python-owned -------------------------------

SEC_RANK = {"SECURED": 0, "UNSECURED": 1}
SEN_RANK = {"SUPER_SENIOR": 0, "SENIOR": 1, "SENIOR_SUBORDINATED": 2, "SUBORDINATED": 3, "JUNIOR": 4}
NM = "nm"  # not_applicable: a defined-but-meaningless ratio (non-positive denominator), distinct from missing (None)


def rank_of(f):
    s, n = SEC_RANK.get(f["secured"]), SEN_RANK.get(f["seniority"])
    return None if s is None or n is None else (s, n)


def ratio(a, b):
    if a is None or b is None:
        return None
    if b <= 0:
        return NM
    return r4(a / b)


def compose(fac, *, cash, undrawn, f_annual, min_cash, ebitda, interest, step_up):
    """Pure oracle composer. None = missing. fac: dicts with id, name, principal, maturity, months, inside,
    amort (None = missing), secured, seniority."""
    fs = sorted(fac, key=lambda f: (f["months"], f["id"]))
    base = None if None in (cash, undrawn, min_cash, f_annual) else cash + undrawn - min_cash
    rows = []
    paid_before = D(0)
    for f in fs:
        m = D(f["months"])
        amort_own = None if f["amort"] is None else min(f["amort"] * m / 12, f["principal"])
        balloon = None if amort_own is None else f["principal"] - amort_own
        parts = [None if g["amort"] is None else min(g["amort"] * D(min(f["months"], g["months"])) / 12, g["principal"])
                 for g in fs]
        amort_to = None if any(p is None for p in parts) else sum(parts, D(0))
        if base is None or amort_to is None or paid_before is None:
            res = None
        else:
            res = base + f_annual * m / 12 - amort_to - paid_before
        if res is None or balloon is None:
            paid = need = cover = None
            paid_before = None
        else:
            paid = min(balloon, max(D(0), res))
            need = balloon - paid
            cover = NM if balloon == 0 else r4(paid / balloon)
            paid_before += paid
        rows.append({**f, "amort_before": amort_own, "balloon": balloon, "resources": res, "paid": paid,
                     "need": need, "cover": cover})

    def tot(key, subset=None):
        vals = [r[key] for r in rows if subset is None or subset(r)]
        return None if any(v is None for v in vals) else sum(vals, D(0))

    tot_principal = sum((r["principal"] for r in rows), D(0))
    tot_balloon, tot_paid, tot_need = tot("balloon"), tot("paid"), tot("need")
    beyond = tot("balloon", lambda r: not r["inside"])
    near = rows[0]
    incr = None if step_up is None or tot_balloon is None else tot_balloon * step_up / 10000
    pf_int = None if interest is None or incr is None else interest + incr

    def cover_x(e, i):
        if e is None or i is None:
            return None
        return NM if i <= 0 else r4(e / i)

    ranks = {r["id"]: rank_of(r) for r in rows}
    known_ranks = all(v is not None for v in ranks.values())
    order = sorted(rows, key=lambda r: (ranks[r["id"]], r["months"], r["id"])) if known_ranks else list(rows)
    cred = []
    for r in order:
        claims = sum((g["principal"] for g in rows if ranks[g["id"]] <= ranks[r["id"]]), D(0)) if known_ranks else None
        cred.append({"id": r["id"], "name": r["name"], "secured": r["secured"], "seniority": r["seniority"],
                     "principal": r["principal"], "share": r4(r["principal"] / tot_principal),
                     "claims": claims, "claims_x": ratio(claims, ebitda)})
    junior = max((c["claims"] for c in cred), default=None) if known_ranks else None
    return {
        "rows": rows, "cred": cred, "base": base, "cash": cash, "undrawn": undrawn, "f_annual": f_annual,
        "min_cash": min_cash, "ebitda": ebitda, "interest": interest, "step_up": step_up,
        "tot_principal": tot_principal, "tot_balloon": tot_balloon, "tot_paid": tot_paid, "tot_need": tot_need,
        "beyond": beyond, "near_date": near["maturity"], "near_months": near["months"],
        "balloon_x": ratio(tot_balloon, ebitda), "need_x": ratio(tot_need, ebitda),
        "incr": incr, "pf_int": pf_int, "cover_now": cover_x(ebitda, interest), "cover_pf": cover_x(ebitda, pf_int),
        "junior": junior, "junior_x": ratio(junior, ebitda), "known_ranks": known_ranks,
    }


def tl(*, principal=FAC_PRINCIPAL, maturity=MATURITY, horizon=24, amort=AMORT, secured=TL_SECURED,
       seniority=TL_SENIORITY, fid="term-loan", name="Northbridge Term Loan"):
    return {"id": fid, "name": name, "principal": principal, "maturity": maturity,
            "months": months_between(BAL_DATE, maturity), "inside": maturity <= add_months(BAL_DATE, horizon),
            "amort": amort, "secured": secured, "seniority": seniority}


STEP_UP = D(400)
BASE_IN = dict(cash=CASH, undrawn=UNDRAWN, f_annual=F_ANNUAL, ebitda=EBITDA_ADJ, interest=CASH_INTEREST)
SCEN = {  # pack-run cases: inputs mirror the CP-2D case they consume (cp2d_case)
    "positive": {"cp2d_case": "positive", "horizon": 24, "min": D(10), "step": STEP_UP},
    "gap_minimum_cash": {"cp2d_case": "gap_minimum_cash", "horizon": 24, "min": None, "step": STEP_UP},
    "gap_no_repricing": {"cp2d_case": "positive", "horizon": 24, "min": D(10), "step": None},
}
FIXT = {  # composer-level fixtures (no pack run); inputs are pure-function vectors, not source figures
    "fixture_two_facilities": {
        "note": "two synthetic facilities (a second, amortising secured loan and unsecured notes) exercise ordering, amortisation, earlier principal paid from resources and the ranking walk; minimum cash 0 is a known zero",
        "fac": [tl(amort=D(6)), tl(maturity=date(2028, 7, 31), principal=D(30), amort=D(0), secured="UNSECURED",
                                   seniority="SENIOR", fid="notes", name="Synthetic Notes")],
        "kw": dict(BASE_IN, min_cash=D(0), step_up=STEP_UP), "horizon": 24},
    "fixture_burn": {
        "note": "negative run-rate flow (CP-2D fixture_burn annual flow): resources at maturity negative, nothing paid from resources",
        "fac": [tl()], "kw": dict(BASE_IN, f_annual=D(-6), min_cash=D(10), step_up=STEP_UP), "horizon": 24},
    "fixture_long_horizon": {
        "note": "CP-2D long_horizon (horizon 60, maturity inside it): the net refinancing need equals the CP-2D funding gap",
        "fac": [tl(horizon=60)], "kw": dict(BASE_IN, min_cash=D(10), step_up=STEP_UP), "horizon": 60},
    "fixture_rank_not_stated": {
        "note": "secured status NOT_STATED: ranking unknown, so every claims-at-or-ahead cell is missing",
        "fac": [tl(secured="NOT_STATED")], "kw": dict(BASE_IN, min_cash=D(10), step_up=STEP_UP), "horizon": 24},
    "fixture_zero_ebitda": {
        "note": "adjusted EBITDA 0 (a known zero): leverage-type ratios are not_applicable, interest cover is a known 0",
        "fac": [tl()], "kw": dict(BASE_IN, ebitda=D(0), min_cash=D(10), step_up=STEP_UP), "horizon": 24},
    "fixture_zero_step_up": {
        "note": "margin step-up 0 bp is a known zero, distinct from an unassessed step-up",
        "fac": [tl()], "kw": dict(BASE_IN, min_cash=D(10), step_up=D(0)), "horizon": 24},
    "fixture_amortisation_missing": {
        "note": "annual amortisation missing for the only facility: principal known, balloon, resources-dependent values and totals missing",
        "fac": [tl(amort=None)], "kw": dict(BASE_IN, min_cash=D(10), step_up=STEP_UP), "horizon": 24},
}
R = {}
for k, v in SCEN.items():
    R[k] = compose([tl(horizon=v["horizon"])], min_cash=v["min"], step_up=v["step"], **BASE_IN)
for k, v in FIXT.items():
    R[k] = compose(v["fac"], **v["kw"])

# cross-checks of the source-derived values against the frozen CP-2D oracle (D3 consumption pins)
for case in ("positive", "gap_minimum_cash"):
    cp2d_t = C2D_EXP["cases"][case]["tables"]
    wall = cp2d_t["T2E.4"]["rows"][0][1]
    assert D(wall[0]["amount"]) == FAC_PRINCIPAL and wall[1]["shown"] == MATURITY.isoformat()
    assert wall[2]["amount"] == "48" == str(R[case]["near_months"]) and wall[3]["shown"] == "No"
    assert D(cp2d_t["T2E.3"]["rows"][0][1]["amount"]) == F_ANNUAL
    assert (cp2d_t["T2E.5"]["rows"][3][1]["state"] == "known") == (SCEN[case]["min"] is not None)
assert R["positive"]["tot_need"] == 40 and R["fixture_long_horizon"]["tot_need"] == 40
assert D(C2D_EXP["cases"]["long_horizon"]["derived"]["funding_gap"]) == R["fixture_long_horizon"]["tot_need"]
assert D(C2D_EXP["cases"]["fixture_burn"]["derived"]["run_rate_net_cash_flow_annual"]) == -6
assert R["positive"]["tot_principal"] == TOTAL_DEBT  # facility principal total equals CP-1 total debt (not read)

# --- literal analyst submissions (judgment only; run-time tokens {{FACT:name}}) ---------------

KINDS = ("repay_from_resources", "amend_and_extend", "market_refinancing", "asset_sale_or_equity",
         "liability_management")
KIND_LABEL = {
    "repay_from_resources": "Repay from internal resources",
    "amend_and_extend": "Amend and extend",
    "market_refinancing": "Market refinancing",
    "asset_sale_or_equity": "Asset sale or equity support",
    "liability_management": "Liability-management exercise",
}
II = "Insufficient Information"
AI = "Analyst Interpretation"

CP1_NAMES = {  # name -> predicate (frozen in manifest.fact_bindings; observed on a promoted CP-1 head)
    "cash_closing": ("T4.10", "cash_closing"),
    "undrawn_rcf": ("T4.10", "undrawn_rcf"),
    "adjusted_ebitda": ("T4.10", "adjusted_ebitda"),
    "cash_interest": ("T4.10", "cash_interest"),
}
CP1_FACILITY_FIELDS = ("secured_status", "seniority", "annual_amortisation", "facility_name")
CP2D_NAMES = {  # name -> (CP-2D stable fact id, what it is)
    "cp2d.horizon": ("T2E.3.r03", "horizon in months (analyst judgment)"),
    "cp2d.run_rate": ("T2E.3.r01", "run-rate net cash flow before new borrowing, per year"),
    "cp2d.min_cash": ("T2E.5.r04", "minimum cash (analyst judgment) or its gap"),
    "cp2d.funding_gap": ("T2E.5.r07", "funding gap at the CP-2D horizon end, or its gap"),
    "cp2d.term-loan.principal": ("T2E.4.r01.c1", "maturity-wall principal"),
    "cp2d.term-loan.maturity_date": ("T2E.4.r01.c2", "maturity-wall maturity date"),
    "cp2d.term-loan.months": ("T2E.4.r01.c3", "maturity-wall months from the balance date"),
    "cp2d.term-loan.inside_horizon": ("T2E.4.r01.c4", "maturity-wall inside-horizon flag"),
}
VALID_NAMES = (set(CP1_NAMES) | set(CP2D_NAMES)
               | {f"term-loan.{f}" for f in CP1_FACILITY_FIELDS})


def tok(name):
    return "{{FACT:" + name + "}}"


REPAY_MIN = (
    "Cash held at the balance date, with no revolving facility and a flat run rate, covers only part of the principal payable at maturity.",
    "Repayment from internal resources alone would leave a large remainder to be refinanced from external lenders.",
)
JUDG_COMMON = {
    "amend_and_extend": (
        "Medium", AI,
        "The whole debt stack is one senior secured term loan, so an extension would be negotiated on a single instrument.",
        "Moderate leverage and comfortable interest cover give existing lenders a basis to extend, subject to a higher margin.",
        ["adjusted_ebitda", "cash_interest", "term-loan.secured_status"], None),
    "market_refinancing": (
        "Medium", AI,
        "Leverage on the adjusted earnings base is moderate and interest cover is comfortable, which supports access to new term debt.",
        "The cost of a new placement is the main sensitivity and is shown as a margin step-up.",
        ["adjusted_ebitda", "cash_interest", "cp2d.term-loan.principal"], None),
    "asset_sale_or_equity": (
        II, II,
        "No owner support or asset-sale evidence is bound to this analysis.",
        "Support from owners or disposal proceeds cannot be weighed against the principal payable at maturity.",
        [], "Business and ownership context is not read in this version, and no source describes disposable assets or owner support."),
    "liability_management": (
        II, II,
        "Document capacity for a liability-management exercise is not available to this analysis.",
        "Whether creditors could be primed or excluded cannot be judged without the legal covenant analysis.",
        [], "The legal covenant and basket evidence is not bound, so liability-management capacity is not assessed."),
}
JUDG = {
    "positive": {
        "repay_from_resources": ("Low", AI, REPAY_MIN[0], REPAY_MIN[1],
                                 ["cash_closing", "undrawn_rcf", "cp2d.run_rate", "cp2d.min_cash"], None),
        **JUDG_COMMON,
    },
    "gap_minimum_cash": {
        "repay_from_resources": (
            II, II,
            "No minimum cash level is assessed upstream, so the resources available to repay principal at maturity cannot be sized.",
            "Without a sized remainder the external refinancing need stays unquantified, which weakens the refinancing view.",
            ["cash_closing", "undrawn_rcf"],
            "The minimum cash assumption of the liquidity analysis is not assessed, so resources at maturity and the refinancing need are not calculated."),
        **JUDG_COMMON,
    },
    "gap_no_repricing": {
        "repay_from_resources": ("Low", AI, REPAY_MIN[0], REPAY_MIN[1],
                                 ["cash_closing", "undrawn_rcf", "cp2d.run_rate", "cp2d.min_cash"], None),
        **JUDG_COMMON,
        "market_refinancing": (
            "Medium", AI,
            JUDG_COMMON["market_refinancing"][2],
            "The cost of a new placement is the main sensitivity and is not sized in this analysis.",
            JUDG_COMMON["market_refinancing"][4], None),
    },
}
STEP_UP_LIT = {
    "bps": 400,
    "rationale": "A margin step-up of this size is held as an analyst assumption for a refinancing of a single secured term loan and is not a source or market figure.",
}
STEP_UP_ABSENCE = {
    "reason": "No refinancing pricing evidence is bound and no margin step-up was assessed.",
    "follow_up": "Obtain a lender indication or a market comparable before sizing the cost of a refinancing.",
}


def submission(case):
    s = SCEN[case]
    paths = []
    for kind in KINDS:
        feas, cat, text, impl, refs, lim = JUDG[case][kind]
        paths.append({"kind": kind, "feasibility": feas, "category": cat, "text": text, "credit_implication": impl,
                      "basis_refs": [tok(r) for r in refs], "limitation": lim})
    return {
        "repricing": dict(STEP_UP_LIT) if s["step"] is not None else None,
        "repricing_absence": None if s["step"] is not None else dict(STEP_UP_ABSENCE),
        "paths": paths,
    }


SUBS = {c: submission(c) for c in SCEN}

# --- prohibited-conclusion guard (review-precise-1 M2) -----------------------------------------------
# The product guard is `deploy_vii.business_context.prohibited_issues(path, text)` with its default kinds
# (peer ranking, instrument recommendation, recovery conclusion; ACTIONS are not a default kind): its phrase
# tables are transcribed here (src/deploy_vii/business_context.py is sha256-pinned above, so a change to them
# fails this build) and `scripts` of the preparation probe that the transcription returns what the product
# returns. The core-local check adds covenant-compliance and refinancing-outcome wording, which the product
# guard does not hold. The issue form is the product's: `<path>: prohibited conclusion (<kind>): "<phrase>"`.
BC_PROHIBITED = {
    "peer ranking": (
        "peer ranking", "ranks above", "ranks below", "ranks among", "ranked first", "ranked last",
        "top quartile", "best-in-class", "best in class", "outperforms peers", "underperforms peers",
        "versus peers", "relative to peers", "compared with peers", "against its peers",
    ),
    "instrument recommendation": (
        "we recommend", "recommend buying", "recommend selling", "buy recommendation", "sell recommendation",
        "should buy", "should sell", "overweight", "underweight", "preferred instrument",
        "instrument recommendation",
    ),
    "recovery conclusion": (
        "recovery conclusion", "expected recovery", "recovery rate", "recovery estimate", "recovery value of",
        "recover par",
    ),
}
BC_NEAR = {  # regular expressions, matched within four words of an instrument noun
    "instrument recommendation": ("prefer the", "recommend", "recommendation"),
    "recovery conclusion": (
        "full recovery", "will recover", "would recover", "expect(?:ed)? to recover",
        "recover(?:y|ies)? (?:of|in full)", "repaid in full",
    ),
}
BC_NOUN = (r"(?:creditors?|lenders?|noteholders?|bondholders?|holders?|investors|claims?|bonds?|notes?|"
           r"loans?|instruments?|debts?|tranches?|securities|facility|revolver|lien)")
LOCAL_NEAR = {  # core-local: a covenant-compliance conclusion (within four words of the word covenant)
    "covenant compliance": ("complies", "complied", "complying", "compliant", "compliance", "breach", "breaches",
                            "breached", "met", "satisfied"),
}
LOCAL_NOUN = r"(?:covenants?)"
LOCAL_WORD = {
    "covenant compliance": ("headroom is sufficient",),
    "recovery conclusion": ("fulcrum",),  # naming a fulcrum security is a recovery conclusion (revision 3, LEAD ruling)
    "refinancing outcome": ("will be refinanced", "will refinance", "refinancing is assured",
                            "refinancing is certain", "will default"),
}


def _word(phrase):
    return rf"(?<![A-Za-z]){re.escape(phrase)}(?![A-Za-z])"


def _near(phrase, noun):
    bounded = rf"(?<![A-Za-z])(?:{phrase})(?![A-Za-z])"
    gap = r"(?:\W+\w+){0,4}?\W+"
    return rf"{bounded}{gap}{noun}\b|\b{noun}{gap}{bounded}"


GUARD = (
    [("product", k, p, re.compile(_word(p), re.I)) for k, ps in BC_PROHIBITED.items() for p in ps]
    + [("product", k, p, re.compile(_near(p, BC_NOUN), re.I)) for k, ps in BC_NEAR.items() for p in ps]
    + [("core-local", k, p, re.compile(_word(p), re.I)) for k, ps in LOCAL_WORD.items() for p in ps]
    + [("core-local", k, p, re.compile(_near(p, LOCAL_NOUN), re.I)) for k, ps in LOCAL_NEAR.items() for p in ps]
)


def guard(path, text):
    """[(origin, issue)] in the guard's order: the product's issues first, then the core-local ones."""
    return [(o, f'{path}: prohibited conclusion ({k}): "{p}"') for o, k, p, rx in GUARD if rx.search(text)]


def guard_issues(path, text):
    return [i for _, i in guard(path, text)]


FIELDS_OF = lambda p: [("repricing.rationale", p["repricing"]["rationale"])] if p["repricing"] else [
    ("repricing_absence.reason", p["repricing_absence"]["reason"]),
    ("repricing_absence.follow_up", p["repricing_absence"]["follow_up"])]


def check_payload(p):
    """The oracle's own statement of the validator rules (lease section Refusals). Returns the ordered issues:
    (1) repricing presence, (2) bps range, (3) one row per kind, (4) per text field in order (the repricing
    text fields, then per submitted path its text, credit_implication and limitation) a figure issue and then the
    guard's issues, for ALL paths, (5) per submitted path its basis_refs, feasibility/category, limitation,
    cites-a-fact and liability-management issues."""
    issues = []
    r, a = p["repricing"], p["repricing_absence"]
    if r is not None and a is not None:
        issues.append("repricing: give repricing or repricing_absence, not both")
    elif r is None and a is None:
        issues.append("repricing: give repricing or repricing_absence")
    if r is not None and not 0 <= r["bps"] <= 1000:
        issues.append("repricing.bps: must be between 0 and 1000")
    kinds = [x["kind"] for x in p["paths"]]
    if sorted(kinds) != sorted(KINDS):
        issues.append("paths: must hold exactly one row per kind")
    texts = list(FIELDS_OF(p)) if (r is None) != (a is None) else []
    for x in p["paths"]:
        k = x["kind"]
        for f in ("text", "credit_implication"):
            texts.append((f"paths[{k}].{f}", x[f]))
        if x["limitation"]:
            texts.append((f"paths[{k}].limitation", x["limitation"]))
    for field, t in texts:
        if re.search(r"\d", t):
            issues.append(f"{field}: must not contain a figure")
        issues.extend(guard_issues(field, t))
    for x in p["paths"]:
        k = x["kind"]
        for ref in x["basis_refs"]:
            if not (ref.startswith("{{FACT:") and ref.endswith("}}") and ref[7:-2] in VALID_NAMES):
                issues.append(f"paths[{k}].basis_refs: names a fact the view does not offer")
        is_ii = x["category"] == II
        if (x["feasibility"] == II) != is_ii:
            issues.append(f"paths[{k}].feasibility: must be Insufficient Information exactly when the category is")
        if is_ii and not x["limitation"]:
            issues.append(f"paths[{k}].limitation: an Insufficient Information assessment states its limitation")
        if not is_ii and x["limitation"]:
            issues.append(f"paths[{k}].limitation: only an Insufficient Information assessment carries a limitation")
        if x["feasibility"] in ("High", "Medium", "Low") and not x["basis_refs"]:
            issues.append(f"paths[{k}].basis_refs: a High, Medium or Low feasibility cites at least one fact")
        if k == "liability_management" and x["feasibility"] in ("High", "Medium", "Low"):
            issues.append("paths[liability_management].feasibility: needs legal covenant capacity evidence, which is not bound; state Insufficient Information")
    return issues


for c, s in SUBS.items():
    assert check_payload(s) == [], (c, check_payload(s))
    for x in s["paths"]:
        for t in (x["text"], x["credit_implication"], x["limitation"] or "."):
            assert t.isascii() and t.endswith("."), (c, t)
    for _, t in FIELDS_OF(s):
        assert t.isascii() and t.endswith("."), (c, t)


def payload_from(base_case, change):
    out = json.loads(json.dumps(SUBS[base_case]))
    change(out)
    assert out != SUBS[base_case], "a refusal payload must differ from its base"
    return {"base_case": base_case, "payload": out}


def _path(p, kind):
    return next(x for x in p["paths"] if x["kind"] == kind)


def _bps(v):
    def f(p):
        p["repricing"]["bps"] = v
    return f


def _append(kind, field, suffix):
    def f(p):
        _path(p, kind)[field] += suffix
    return f


def _set_path(kind, **kw):
    def f(p):
        _path(p, kind).update(kw)
    return f


def _drop(kind):
    def f(p):
        p["paths"] = [x for x in p["paths"] if x["kind"] != kind]
    return f


def _dup(kind):
    def f(p):
        p["paths"].append(dict(_path(p, kind)))
    return f


def _top(**kw):
    def f(p):
        p.update(kw)
    return f


def _rationale(suffix):
    def f(p):
        p["repricing"]["rationale"] += suffix
    return f


REFUSAL_INPUTS = {
    "step_up_negative": payload_from("positive", _bps(-1)),
    "step_up_over_limit": payload_from("positive", _bps(1001)),
    "step_up_and_absence": payload_from("positive", _top(repricing_absence=dict(STEP_UP_ABSENCE))),
    "neither_step_up_nor_absence": payload_from("positive", _top(repricing=None)),
    "path_missing": payload_from("positive", _drop("asset_sale_or_equity")),
    "path_repeated": payload_from("positive", _dup("market_refinancing")),
    "digit_in_text": payload_from("positive", _append("repay_from_resources", "text", " It is 5 per cent.")),
    "digit_in_rationale": payload_from("positive", _rationale(" It is 5 per cent.")),
    "prohibited_recommendation": payload_from("positive", _append("market_refinancing", "credit_implication", " We recommend this path.")),
    "prohibited_recovery": payload_from("positive", _append("amend_and_extend", "text", " The expected recovery is high.")),
    "covenant_compliance_wording": payload_from("positive", _append("repay_from_resources", "credit_implication", " The covenant test is met.")),
    "unknown_basis_ref": payload_from("positive", lambda p: _path(p, "repay_from_resources")["basis_refs"].append("{{FACT:not_a_fact}}")),
    "feasibility_without_basis": payload_from("positive", _set_path("amend_and_extend", basis_refs=[])),
    "insufficient_without_limitation": payload_from("positive", _set_path("asset_sale_or_equity", limitation=None)),
    "limitation_without_insufficient": payload_from("positive", _set_path("amend_and_extend", limitation="A limitation without a gap.")),
    "feasibility_category_mismatch": payload_from("positive", _set_path("repay_from_resources", category=II, limitation="A limitation for the mismatch case.")),
    "lme_judged_without_capacity_evidence": payload_from("positive", _set_path("liability_management", feasibility="Medium", category=AI, limitation=None, basis_refs=[tok("adjusted_ebitda")])),
}
REFUSALS = {
    "step_up_negative": "repricing.bps: must be between 0 and 1000",
    "step_up_over_limit": "repricing.bps: must be between 0 and 1000",
    "step_up_and_absence": "repricing: give repricing or repricing_absence, not both",
    "neither_step_up_nor_absence": "repricing: give repricing or repricing_absence",
    "path_missing": "paths: must hold exactly one row per kind",
    "path_repeated": "paths: must hold exactly one row per kind",
    "digit_in_text": "paths[repay_from_resources].text: must not contain a figure",
    "digit_in_rationale": "repricing.rationale: must not contain a figure",
    "prohibited_recommendation": 'paths[market_refinancing].credit_implication: prohibited conclusion (instrument recommendation): "we recommend"',
    "prohibited_recovery": 'paths[amend_and_extend].text: prohibited conclusion (recovery conclusion): "expected recovery"',
    "covenant_compliance_wording": 'paths[repay_from_resources].credit_implication: prohibited conclusion (covenant compliance): "met"',
    "unknown_basis_ref": "paths[repay_from_resources].basis_refs: names a fact the view does not offer",
    "feasibility_without_basis": "paths[amend_and_extend].basis_refs: a High, Medium or Low feasibility cites at least one fact",
    "insufficient_without_limitation": "paths[asset_sale_or_equity].limitation: an Insufficient Information assessment states its limitation",
    "limitation_without_insufficient": "paths[amend_and_extend].limitation: only an Insufficient Information assessment carries a limitation",
    "feasibility_category_mismatch": "paths[repay_from_resources].feasibility: must be Insufficient Information exactly when the category is",
    "lme_judged_without_capacity_evidence": "paths[liability_management].feasibility: needs legal covenant capacity evidence, which is not bound; state Insufficient Information",
}
for name, entry in REFUSAL_INPUTS.items():
    assert check_payload(entry["payload"]) == [REFUSALS[name]], (name, check_payload(entry["payload"]))

# --- CP-0 consumer entries ---------------------------------------------------------------------

Q_IDENT = "Northbridge Synthetic Group is the issuer and consolidated group."
Q_FIN1 = "Currency: USD; amounts in millions."
Q_FIN5 = "There is exactly one debt facility: Northbridge Term Loan, facility_id term-loan."
for src, loc, quote in (("identity", "page:1", Q_IDENT), ("financial", "page:1", Q_FIN1), ("financial", "page:5", Q_FIN5)):
    assert quote in SRC[src]["pages"][int(loc.split(":")[1]) - 1]["text"], (src, loc)


def cite(sid, sha, loc, quote):
    return {"source_id": sid, "source_sha256": sha, "locator": loc, "quote": quote}


CP0_CP2D = C2D_SUB["cp0_consumer_delta"]  # frozen CP-2D entry, reused byte for byte
CP0_CP3C = {
    "module_id": "CP-3C",
    "readiness": "READY_WITH_LIMITATIONS",
    "evidence_demand": "Settled CP-1 facility terms and cash flow facts and the CP-2D liquidity bridge",
    "source_ids": ["identity", "financial"],
    "rationale": "The refinancing assessment can run on settled upstream facts with explicit source and scope limitations.",
    "citations": [
        cite("identity", IDENT_SHA, "page:1", Q_IDENT),
        cite("financial", FINANCIAL_SHA, "page:1", Q_FIN1),
        cite("financial", FINANCIAL_SHA, "page:5", Q_FIN5),
    ],
    "missing_source": None,
    "limitations": [LIMIT_FIN],
}

# --- expected tables --------------------------------------------------------------------------

GAP_SHOWN = "∅ G#"
NM_SHOWN = "∅ G# n.m."


BAL_P = "2025-12-31"
LTM_P = "LTM Q4 25: 2025-01-01 to 2025-12-31"


def C(shown, amount=None, unit=None, vc="calculated", state="known", cp1=None, cp2d=None, formula=None, period=None):
    c = {"shown": shown, "state": state}
    if amount is not None:
        c["amount"] = amount if isinstance(amount, str) else dec(amount)
    if unit:
        c["unit"] = unit
    if amount is not None and unit == "MILLIONS":
        c["currency"] = "USD"  # report_view.figure_unit: an amount cell in US$ m carries its currency (review-precise-1 M1)
    if amount is not None:
        c["period"] = period or BAL_P  # a numeric fact requires an explicit period (contracts.Fact)
    c["value_class"] = vc
    if cp1:
        c["cp1_operand"] = cp1
    if cp2d:
        c["cp2d_operand"] = cp2d
    if formula:
        c["formula"] = formula
    return c


def GAP(reason, unit="MILLIONS", vc="calculated", cp2d=None):
    c = {"shown": GAP_SHOWN, "shown_pattern": "∅ G<n>", "state": "gap", "unit": unit, "value_class": vc,
         "reason": reason}
    if unit == "MILLIONS":
        c["currency"] = "USD"  # a gap cell carries its settled twin's unit and currency (the CP-1C rule)
    if cp2d:
        c["cp2d_operand"] = cp2d
    return c


def NMC(reason, unit):
    c = {"shown": NM_SHOWN, "shown_pattern": "∅ G<n> n.m.", "state": "not_applicable", "unit": unit,
         "value_class": "calculated", "reason": reason}
    if unit == "MILLIONS":
        c["currency"] = "USD"
    return c


def c2d_period(cp2d_case, fact_id):
    """The `period` of the frozen CP-2D oracle cell this copy reads (re-pinned at the Stage 2 close)."""
    cells = [c for t in C2D_EXP["cases"][cp2d_case]["tables"].values() for rw in t["rows"]
             for c in (rw[1] if isinstance(rw[1], list) else [rw[1]]) if c["fact_id"] == fact_id]
    assert len(cells) == 1, fact_id
    return cells[0]["period"]


def A(d, vc="calculated", cp1=None, cp2d=None, formula=None, period=None):
    return C(amt(d), d, "MILLIONS", vc, cp1=cp1, cp2d=cp2d, formula=formula, period=period)


def X(v, formula=None, reason="Not calculable: a non-positive denominator", cp1=None):
    """A multiple cell from a stored ratio (period: the LTM window); None -> missing is handled by the caller."""
    if v == NM:
        return NMC(reason, "MULTIPLE")
    return C(mult(v), v, "MULTIPLE", "calculated", formula=formula, cp1=cp1, period=LTM_P)


def P(v, formula=None):
    if v == NM:
        return NMC("Not calculable: principal payable at maturity is zero", "PERCENT")
    return C(pct(v), v, "PERCENT", "calculated", formula=formula)


def MON(n, vc="calculated", cp2d=None, formula=None):
    return C(f"{n} months", D(n), "months", vc, cp2d=cp2d, formula=formula)


def TXT(s, vc="calculated", cp1=None, cp2d=None, formula=None):
    return C(s, None, None, vc, cp1=cp1, cp2d=cp2d, formula=formula)


REASON_MIN = "Not calculable: minimum cash not assessed"
REASON_STEP = "Not calculable: margin step-up not assessed"
REASON_RANK = "Not calculable: ranking not stated for a facility"
REASON_LME = "Not calculable: liability-management capacity evidence is not bound"
REASON_STRESS = "Not calculable: no stressed case is bound"
REASON_AMORT = "Not calculable: annual amortisation missing"


def why_resources(r):
    """The missing operand behind a missing resources-dependent value: the base resources (the minimum cash is the
    only operand of them that can be missing in a pack case) or, with a base, an amortisation."""
    return REASON_MIN if r["base"] is None else REASON_AMORT


def opt_amt(v, reason, **kw):
    return GAP(reason) if v is None else A(v, **kw)


def build_tables(case):
    s = SCEN[case]
    r = R[case]
    c2d = C2D_EXP["cases"][s["cp2d_case"]]["tables"]
    T = {}
    f = r["rows"][0]
    # T3D.1 refinancing need by maturity
    t1 = []
    for ri, x in enumerate(r["rows"], 1):
        w = f"T2E.4.r{ri:02d}"
        resource_gap = x["resources"] is None
        t1.append([f"{x['name']} ({x['id']})", [
            A(x["principal"], "source", cp2d=w + ".c1", period=c2d_period(s["cp2d_case"], w + ".c1")),
            TXT(x["maturity"].isoformat(), "source", cp2d=w + ".c2"),
            MON(x["months"], cp2d=w + ".c3"),
            TXT("Yes" if x["inside"] else "No", cp2d=w + ".c4"),
            opt_amt(x["amort_before"], REASON_AMORT, formula="min(annual amortisation x months / 12, principal)"),
            opt_amt(x["balloon"], REASON_AMORT, formula="principal - amortisation before maturity"),
            GAP(why_resources(r)) if resource_gap else A(x["resources"], formula="cash + undrawn revolver - minimum cash + run-rate flow x months / 12 - amortisation to the date - earlier principal paid from resources"),
            GAP(why_resources(r)) if x["paid"] is None else A(x["paid"], formula="min(principal payable at maturity, max(0, resources at maturity))"),
            GAP(why_resources(r)) if x["need"] is None else A(x["need"], formula="principal payable at maturity - resources applied"),
            GAP(why_resources(r), "PERCENT") if x["cover"] is None else P(x["cover"], formula="resources applied / principal payable at maturity"),
        ]])
    T["T3D.1"] = {"title": "Refinancing need by maturity", "row_header": "Facility",
                  "columns": ["Principal (US$ m)", "Maturity date", "Months from 2025-12-31", "Inside CP-2D horizon",
                              "Amortisation before maturity (US$ m)", "Principal payable at maturity (US$ m)",
                              "Resources at maturity (US$ m)", "Resources applied (US$ m)", "Refinancing need (US$ m)",
                              "Resources cover of principal at maturity"],
                  "rows": t1}
    # T3D.2 refinancing burden
    fg = c2d["T2E.5"]["rows"][6][1]
    mc = c2d["T2E.5"]["rows"][3][1]
    hz = c2d["T2E.3"]["rows"][2][1]
    fg_cell = GAP(fg["reason"], vc="calculated", cp2d="T2E.5.r07") if fg["state"] != "known" else A(D(fg["amount"]), "calculated", cp2d="T2E.5.r07")
    mc_cell = GAP(mc["reason"], vc="analyst_judgment", cp2d="T2E.5.r04") if mc["state"] != "known" else A(D(mc["amount"]), "analyst_judgment", cp2d="T2E.5.r04")
    if fg["state"] == "known":
        assert D(fg["amount"]) == 0
    t2 = [
        ["Principal payable at maturity, all facilities", opt_amt(r["tot_balloon"], REASON_AMORT, formula="sum of principal payable at maturity")],
        ["Resources applied at the maturity dates", GAP(why_resources(r)) if r["tot_paid"] is None else A(r["tot_paid"], formula="sum of resources applied")],
        ["Refinancing need after resources", GAP(why_resources(r)) if r["tot_need"] is None else A(r["tot_need"], formula="sum of refinancing need")],
        ["Principal maturing after the CP-2D horizon", opt_amt(r["beyond"], REASON_AMORT, formula="sum of principal payable at maturity of facilities outside the CP-2D horizon")],
        ["Nearest maturity date", TXT(r["near_date"].isoformat(), formula="earliest maturity date")],
        ["Months to the nearest maturity", MON(r["near_months"], formula="months from the balance date to the earliest maturity")],
        ["LTM adjusted EBITDA", A(r["ebitda"], "calculated", cp1="adjusted_ebitda", period=LTM_P)],
        ["Principal payable at maturity / LTM adjusted EBITDA", GAP(REASON_AMORT, "MULTIPLE") if r["balloon_x"] is None else X(r["balloon_x"], "principal payable at maturity / adjusted EBITDA")],
        ["Refinancing need / LTM adjusted EBITDA", GAP(why_resources(r), "MULTIPLE") if r["need_x"] is None else X(r["need_x"], "refinancing need / adjusted EBITDA")],
        ["CP-2D funding gap at its horizon end", fg_cell],
        ["Minimum cash applied (analyst assumption set in CP-2D)", mc_cell],
        ["CP-2D horizon (analyst judgment)", MON(int(hz["amount"]), "analyst_judgment", cp2d="T2E.3.r03")],
    ]
    T["T3D.2"] = {"title": "Refinancing burden", "row_header": "Line", "columns": ["Value"], "rows": t2}
    # T3D.3 refinancing cost sensitivity
    step = r["step_up"]
    t3 = [
        ["Cash interest paid, LTM", A(r["interest"], "calculated", cp1="cash_interest", formula="negation of the CP-1 cash interest outflow", period=LTM_P)],
        ["LTM adjusted EBITDA", A(r["ebitda"], "calculated", cp1="adjusted_ebitda", period=LTM_P)],
        ["Interest cover, LTM", X(r["cover_now"], "adjusted EBITDA / cash interest paid", "Not calculable: no cash interest")],
        ["Margin step-up (analyst assumption)", GAP("Margin step-up not assessed", "basis_points", "analyst_judgment") if step is None else C(f"{dec(step)} bp", step, "basis_points", "analyst_judgment", period=AS_OF)],
        ["Principal repriced (all principal payable at maturity)", opt_amt(r["tot_balloon"], REASON_AMORT, formula="sum of principal payable at maturity")],
        ["Added annual cash interest", GAP(REASON_STEP) if r["incr"] is None else A(r["incr"], formula="principal repriced x margin step-up / 10000", period=LTM_P)],
        ["Pro forma annual cash interest", GAP(REASON_STEP) if r["pf_int"] is None else A(r["pf_int"], formula="cash interest paid + added annual cash interest", period=LTM_P)],
        ["Pro forma interest cover", GAP(REASON_STEP, "MULTIPLE") if r["cover_pf"] is None else X(r["cover_pf"], "adjusted EBITDA / pro forma annual cash interest", "Not calculable: no pro forma cash interest")],
    ]
    T["T3D.3"] = {"title": "Refinancing cost sensitivity", "row_header": "Line", "columns": ["Value"], "rows": t3}
    # T3D.4 creditor position
    t4 = []
    for x in r["cred"]:
        ri = next(i for i, y in enumerate(r["rows"], 1) if y["id"] == x["id"])
        t4.append([f"{x['name']} ({x['id']})", [
            TXT(x["secured"], "source", cp1=f"T4.18 {x['id']} secured_status"),
            TXT(x["seniority"], "source", cp1=f"T4.18 {x['id']} seniority"),
            A(x["principal"], "source", cp2d=f"T2E.4.r{ri:02d}.c1", period=c2d_period(SCEN[case]["cp2d_case"], f"T2E.4.r{ri:02d}.c1")),
            P(x["share"], "principal / total facility principal"),
            GAP(REASON_RANK) if x["claims"] is None else A(x["claims"], formula="sum of principal of facilities ranking at or ahead (secured before unsecured, then seniority)"),
            GAP(REASON_RANK, "MULTIPLE") if x["claims"] is None else X(x["claims_x"], "claims at or ahead / adjusted EBITDA"),
        ]])
    T["T3D.4"] = {"title": "Creditor position", "row_header": "Facility",
                  "columns": ["Security", "Seniority", "Principal (US$ m)", "Share of total principal",
                              "Claims at or ahead (US$ m)", "Claims at or ahead / LTM adjusted EBITDA"],
                  "rows": t4}
    # T3D.5 LME capacity (Base, LME, Stress)
    jx = GAP(REASON_RANK) if r["junior"] is None else A(r["junior"], formula="largest claims at or ahead among the facilities")
    jxx = GAP(REASON_RANK, "MULTIPLE") if r["junior"] is None else X(r["junior_x"], "claims at or ahead of the most junior facility / adjusted EBITDA")
    t5 = [
        ["Claims at or ahead of the most junior facility (US$ m)", [jx, GAP(REASON_LME), GAP(REASON_STRESS)]],
        ["Claims at or ahead of the most junior facility / LTM adjusted EBITDA", [jxx, GAP(REASON_LME, "MULTIPLE"), GAP(REASON_STRESS, "MULTIPLE")]],
    ]
    T["T3D.5"] = {"title": "LME capacity", "row_header": "Measure", "columns": ["Base", "LME", "Stress"], "rows": t5}
    # T3D.6 refinancing paths (analyst)
    t6 = []
    for kind in KINDS:
        feas, cat, text, impl, refs, lim = JUDG[case][kind]
        t6.append([KIND_LABEL[kind], [
            TXT(feas, "analyst_judgment"), TXT(text, "analyst_judgment"), TXT(impl, "analyst_judgment"),
            TXT(", ".join(refs) if refs else "none", "analyst_judgment"),
        ]])
    T["T3D.6"] = {"title": "Refinancing paths", "row_header": "Path",
                  "columns": ["Feasibility", "Assessment", "Credit implication", "Basis"], "rows": t6}
    for tid, tab in T.items():
        for ri, rw in enumerate(tab["rows"], 1):
            cells = rw[1] if isinstance(rw[1], list) else [rw[1]]
            for ci, cell in enumerate(cells, 1):
                cell["fact_id"] = f"{tid}.r{ri:02d}" + (f".c{ci}" if len(cells) > 1 else "")
            # table shape (contracts.py: "Report row does not match its columns"): one fact per column in every row
            assert len(cells) == len(tab["columns"]), f"{tid} row {ri}: {len(cells)} facts for {len(tab['columns'])} columns"
    return T


def limitations(case):
    s, r = SCEN[case], R[case]
    out = [
        ("Run-rate basis", "Limitation", "Run-rate basis: the annual cash flow of the liquidity analysis is held flat to each maturity date, including dates after its horizon; no forecast, growth, seasonality or new borrowing is assumed."),
        ("Resources basis", "Limitation", "Resources at a maturity are cash and undrawn committed revolver at the balance date plus the held run-rate flow, less amortisation to that date, earlier principal paid from resources and the minimum cash; the refinancing of an earlier shortfall is not modelled."),
    ]
    out.append(("Revolver availability", "Limitation", "Any undrawn committed revolver is assumed to be available at every maturity date, even where it matures earlier; its own maturity is not read."))
    if s["min"] is None:
        out.append(("Minimum cash", "Gap", "Minimum cash was not assessed, so resources at maturity and the refinancing need are not calculated."))
    else:
        out.append(("Minimum cash", "Limitation", "Minimum cash is an analyst assumption, not a source figure."))
    if s["step"] is None:
        out.append(("Margin step-up", "Gap", "No margin step-up was assessed, so the cost effect of a refinancing is not calculated."))
    else:
        out.append(("Margin step-up", "Limitation", "The margin step-up is an analyst assumption applied to all principal payable at maturity; it is not a source or market figure."))
    out += [
        ("Reference rate level", "Limitation", "No reference rate level is stated in any source, so the all-in cost of a refinancing is not calculated; only a margin step-up over the current terms is shown."),
        ("Market access", "Limitation", "No market pricing or lender-appetite evidence is read, so feasibility judgments rest on the credit metrics alone."),
        ("Liability-management capacity", "Limitation", "Liability-management capacity is not calculated: the legal covenant analysis is not read, and it does not yet quantify basket amounts."),
        ("Stress case", "Limitation", "No stressed case is shown: the downside analysis is not read."),
        ("Business context", "Limitation", "Business and ownership context is not read, so owner support and asset-sale routes are not weighed."),
        ("Ranking basis", "Limitation", "Ranking follows the secured and seniority flags of each facility; guarantees, collateral value and structural subordination are not assessed."),
    ]
    for kind in KINDS:
        lim = JUDG[case][kind][5]
        if lim:
            out.append((KIND_LABEL[kind], "Gap", lim))
    return out


def prose_bare(template):
    t = re.sub(r"\{[^{}]*\}|\[[^\[\]]*\]", "", template)
    t = re.sub(r"\b\d{1,2} [A-Z][a-z]{2} \d{4}\b", "", t)
    return re.findall(r"\d", t)


def claims(case):
    r, s = R[case], SCEN[case]
    tabs = build_tables(case)
    cells = {c["fact_id"]: c for t in tabs.values() for rw in t["rows"] for c in (rw[1] if isinstance(rw[1], list) else [rw[1]])}
    d = fmt_date(BAL_DATE)

    def fig(fid, unit):
        c = cells[fid]
        assert c["state"] == "known" and c.get("amount") is not None and c["value_class"] != "analyst_judgment", fid
        assert c["unit"] == {"US$ m": "MILLIONS", "x": "MULTIPLE"}[unit], (fid, unit)
        return "{" + fid + "|" + unit + "}"

    def chip(fid):
        assert cells[fid]["state"] != "known", fid
        return "[" + fid + "]"

    def resolve(tpl):
        def one(m):
            c = cells[m.group(1)]
            return c["shown"] + (" US$ m" if m.group(2) == "US$ m" else "")
        out = re.sub(r"\{([^|{}]+)\|(US\$ m|x)\}", one, tpl)
        return re.sub(r"\[([^\[\]]+)\]", lambda m: GAP_SHOWN, out)

    def claim(cid, tpl, cites):
        assert not prose_bare(tpl), (cid, tpl)
        refs = re.findall(r"[\{\[]([^|{}\[\]]+)(?:\|[^{}]*)?[\}\]]", tpl)
        return {"claim_id": cid, "template": tpl, "text": resolve(tpl), "text_is_pattern": "[" in tpl,
                "references": list(dict.fromkeys(refs)), "cites_from": list(cites) + list(dict.fromkeys(refs))}

    if r["tot_need"] is None:
        assert r["base"] is None, "the claim's reason (minimum cash not assessed) must be the missing operand"
    need = fig("T3D.2.r03", "US$ m") if r["tot_need"] is not None else chip("T3D.2.r03")
    cl = [
        claim("CP-3C-NEED-01",
              f"Principal payable at maturity totals {fig('T3D.2.r01', 'US$ m')}; " + (
                  f"after the resources available at each maturity date the refinancing need is {need}." if r["tot_need"] is not None
                  else f"the refinancing need after resources is {need}, because the minimum cash has not been assessed."),
              ["term-loan.annual_amortisation", "cp2d.term-loan.principal", "cash_closing", "undrawn_rcf", "cp2d.run_rate", "cp2d.min_cash"]),
    ]
    gapc = "T3D.2.r10"
    gap_ref = fig(gapc, "US$ m") if cells[gapc]["state"] == "known" else chip(gapc)
    cl.append(claim("CP-3C-HORIZON-01",
                    f"The liquidity analysis reports a funding gap of {gap_ref} at its horizon end, while {fig('T3D.2.r04', 'US$ m')} falls due after that horizon.",
                    ["cp2d.funding_gap", "cp2d.horizon", "cp2d.term-loan.inside_horizon"]))
    bx = fig("T3D.2.r09", "x") if r["need_x"] not in (None,) and r["need_x"] != NM else chip("T3D.2.r09")
    cl.append(claim("CP-3C-BURDEN-01",
                    f"Principal payable at maturity is {fig('T3D.2.r08', 'x')} of adjusted EBITDA for the twelve months to {d}; the refinancing need is {bx} of the same earnings.",
                    ["adjusted_ebitda"]))
    if s["step"] is None:
        cl.append(claim("CP-3C-COST-01",
                        f"The cost of a margin step-up on the principal payable at maturity is not calculated: added annual cash interest is {chip('T3D.3.r06')} because no step-up was assessed.",
                        []))
    else:
        cl.append(claim("CP-3C-COST-01",
                        f"An assumed margin step-up on the principal payable at maturity adds {fig('T3D.3.r06', 'US$ m')} to annual cash interest and lowers interest cover from {fig('T3D.3.r03', 'x')} to {fig('T3D.3.r08', 'x')}.",
                        ["cash_interest", "adjusted_ebitda"]))
    cl.append(claim("CP-3C-LME-01",
                    f"Claims at or ahead of the most junior facility are {fig('T3D.5.r01.c1', 'US$ m')} before any liability-management exercise; the position after such an exercise is {chip('T3D.5.r01.c2')} because the legal capacity evidence is not bound.",
                    ["term-loan.secured_status", "term-loan.seniority", "cp2d.term-loan.principal"]))
    return cl


def judgments_rows(case):
    s = SCEN[case]
    rows = [["Margin step-up", "not assessed" if s["step"] is None else f"{dec(s['step'])} bp (analyst assumption)"]]
    for kind in KINDS:
        rows.append([KIND_LABEL[kind], JUDG[case][kind][1]])
    return rows


def trace_rows(case):
    s = SCEN[case]
    c2d = C2D_EXP["cases"][s["cp2d_case"]]["tables"]
    cell = {c["fact_id"]: c for t in c2d.values() for rw in t["rows"] for c in (rw[1] if isinstance(rw[1], list) else [rw[1]])}
    rows = [
        ["cash_closing", "CP-1", "T4.10 LTM Q4 25", amt(CASH)],
        ["undrawn_rcf", "CP-1", "T4.10 LTM Q4 25", amt(UNDRAWN)],
        ["adjusted_ebitda", "CP-1", "T4.10 LTM Q4 25", amt(EBITDA_ADJ)],
        ["cash_interest", "CP-1", "T4.10 LTM Q4 25", "(" + amt(CASH_INTEREST) + ")"],
        ["term-loan.facility_name", "CP-1", "T4.18 q4-2025", "Northbridge Term Loan"],
        ["term-loan.secured_status", "CP-1", "T4.18 q4-2025", TL_SECURED],
        ["term-loan.seniority", "CP-1", "T4.18 q4-2025", TL_SENIORITY],
        ["term-loan.annual_amortisation", "CP-1", "T4.18 q4-2025", amt(AMORT)],
    ]
    for name, (fid, _) in CP2D_NAMES.items():
        c = cell[fid]
        rows.append([name, "CP-2D", fid, c["shown"] if c["state"] == "known" else GAP_SHOWN])
    return rows


def case_expected(case):
    s, r = SCEN[case], R[case]
    e = {
        "case_kind": "pack_run_clone",
        "consumes_cp2d_case": s["cp2d_case"],
        "horizon_months": s["horizon"],
        "minimum_cash": None if s["min"] is None else dec(s["min"]),
        "margin_step_up_bps": None if s["step"] is None else dec(s["step"]),
        "derived": derived(r),
        "missing_not_zero": missing_list(r),
        "own_limitations": [t for _, _, t in limitations(case)],
        "tables": build_tables(case),
        "T3D.7_rows": judgments_rows(case),
        "T3D.8_rows": [[label, kind] for label, kind, _ in limitations(case)],
        "T3D.9_rows": trace_rows(case),
        "claims": claims(case),
        "status": "restricted",
    }
    return e


def sd(v):
    return None if v is None else (v if isinstance(v, str) else dec(v))


def derived(r):
    return {
        "base_resources_before_flows": sd(r["base"]),
        "run_rate_annual": sd(r["f_annual"]),
        "facilities": [
            {"id": x["id"], "months": x["months"], "inside_horizon": x["inside"], "principal": sd(x["principal"]),
             "amortisation_before_maturity": sd(x["amort_before"]), "principal_payable_at_maturity": sd(x["balloon"]),
             "resources_at_maturity": sd(x["resources"]), "resources_applied": sd(x["paid"]),
             "refinancing_need": sd(x["need"]), "cover": sd(x["cover"])}
            for x in r["rows"]],
        "total_principal": sd(r["tot_principal"]), "total_principal_payable_at_maturity": sd(r["tot_balloon"]),
        "total_resources_applied": sd(r["tot_paid"]), "total_refinancing_need": sd(r["tot_need"]),
        "principal_after_cp2d_horizon": sd(r["beyond"]), "nearest_maturity": r["near_date"].isoformat(),
        "months_to_nearest_maturity": r["near_months"],
        "principal_payable_over_ebitda": sd(r["balloon_x"]), "need_over_ebitda": sd(r["need_x"]),
        "added_annual_cash_interest": sd(r["incr"]), "pro_forma_cash_interest": sd(r["pf_int"]),
        "interest_cover": sd(r["cover_now"]), "pro_forma_interest_cover": sd(r["cover_pf"]),
        "creditor_position": [{"id": c["id"], "secured": c["secured"], "seniority": c["seniority"],
                               "principal": sd(c["principal"]), "share": sd(c["share"]), "claims_at_or_ahead": sd(c["claims"]),
                               "claims_over_ebitda": sd(c["claims_x"])} for c in r["cred"]],
        "claims_at_or_ahead_of_most_junior": sd(r["junior"]), "junior_over_ebitda": sd(r["junior_x"]),
    }


def missing_list(r):
    out = []
    for k, v in (("base_resources_before_flows", r["base"]), ("total_principal_payable_at_maturity", r["tot_balloon"]),
                 ("total_resources_applied", r["tot_paid"]), ("total_refinancing_need", r["tot_need"]),
                 ("principal_after_cp2d_horizon", r["beyond"]), ("principal_payable_over_ebitda", r["balloon_x"]),
                 ("need_over_ebitda", r["need_x"]), ("added_annual_cash_interest", r["incr"]),
                 ("pro_forma_cash_interest", r["pf_int"]), ("pro_forma_interest_cover", r["cover_pf"]),
                 ("claims_at_or_ahead_of_most_junior", r["junior"])):
        if v is None:
            out.append(k)
    return out


def fixture_expected(name):
    v, r = FIXT[name], R[name]
    return {"case_kind": "composer_fixture", "note": v["note"],
            "inputs": {"facilities": [{"id": f["id"], "principal": sd(f["principal"]), "maturity": f["maturity"].isoformat(),
                                       "annual_amortisation": sd(f["amort"]), "secured_status": f["secured"],
                                       "seniority": f["seniority"]} for f in v["fac"]],
                       "cash": sd(v["kw"]["cash"]), "undrawn_revolver": sd(v["kw"]["undrawn"]),
                       "run_rate_annual": sd(v["kw"]["f_annual"]), "minimum_cash": sd(v["kw"]["min_cash"]),
                       "adjusted_ebitda": sd(v["kw"]["ebitda"]), "cash_interest": sd(v["kw"]["interest"]),
                       "margin_step_up_bps": sd(v["kw"]["step_up"]), "cp2d_horizon_months": v["horizon"]},
            "derived": derived(r), "missing_not_zero": missing_list(r)}


EXPECTED_CASES = {c: case_expected(c) for c in SCEN}
for k in FIXT:
    EXPECTED_CASES[k] = fixture_expected(k)

# --- CP-1 downstream-readiness literal of THIS run (review-precise-1 M3, option (a)) -------------------------
# CP-1's readiness stage (DownstreamReview) assesses consumers by requirement (downstream_readiness.py:34, :178,
# :203). The S1 literal is `{"consumers": []}`, which leaves every consumer not_ready and supplies nothing for
# CP-2D or CP-3C. This run requests CP-1A, CP-2, CP-2D, CP-3C (registry order; CP-MODEL absent), assesses CP-2D and
# CP-3C and leaves CP-1A and CP-2 unassessed exactly as S1 does. Evidence and gap ids are catalogue/gap hashes of the
# promoted pack, so the literal names them by selector, resolved at run time against DownstreamInputs.
CP1_REQUESTED = ["CP-1A", "CP-2", "CP-2D", "CP-3C"]
GAPS_ALL = {"select": "every retained gap of DownstreamInputs.narrative.gaps, in one scope per consumer"}
FACILITY_EVIDENCE = {"select": "every catalogue record whose _evidence_tags contain observation:facilities"}
KPI_EVIDENCE = {"select": "every catalogue record whose _evidence_tags contain kpi:ebitda or kpi:adjusted_ebitda"}
CP1_DOWNSTREAM_REVIEW = {
    "note": "Replaces the S1 readiness literal {\"consumers\": []} for this run. inputs_sha256 is prefilled at run time (step-inputs). Selectors are resolved against the promoted pack's DownstreamInputs; the evidence is the facility observation register for CP-3C (debt_schedule, maturity_profile: _EVIDENCE_GROUPS) and the EBITDA key figures for CP-2D (earnings_quality_metrics). CP-1A and CP-2 are not assessed, as in S1.",
    "schema_version": "downstream-review/1",
    "inputs_sha256": "<<prefilled at run time>>",
    "requested_consumers": CP1_REQUESTED,
    "consumers": [
        {"entry": "CP-2D",
         "requirements": [{"requirement": "earnings_quality_metrics", "status": "sufficient", "evidence_ids": KPI_EVIDENCE,
                           "rationale": "The reported and adjusted EBITDA key figures carry the earnings base of the liquidity bridge.", "actions": []}],
         "gaps": [{"gap_ids": GAPS_ALL, "relevance": "relevant", "evidence_ids": [],
                   "rationale": "The retained gaps limit the earnings inputs of the liquidity bridge."}]},
        {"entry": "CP-3C",
         "requirements": [{"requirement": "debt_schedule", "status": "sufficient", "evidence_ids": FACILITY_EVIDENCE,
                           "rationale": "The facility register carries the principal and maturity of each facility.", "actions": []},
                          {"requirement": "maturity_profile", "status": "sufficient", "evidence_ids": FACILITY_EVIDENCE,
                           "rationale": "The facility register carries the principal and maturity of each facility.", "actions": []}],
         "gaps": [{"gap_ids": GAPS_ALL, "relevance": "relevant", "evidence_ids": [],
                   "rationale": "The retained gaps limit the refinancing inputs."}]},
    ],
}
CP1_READINESS_EXPECTED = {
    "requested_consumers": CP1_REQUESTED,
    "requirements": {"CP-1A": ["consumer_specific_cp1_sufficiency"], "CP-2": ["kpi_dashboard", "calculation_register", "fcf_build"],
                     "CP-2D": ["earnings_quality_metrics"], "CP-3C": ["debt_schedule", "maturity_profile"]},
    "validate_downstream_review": [],
    "consumer_status": {"CP-1A": "not_ready", "CP-2": "not_ready", "CP-2D": "ready_with_limitations", "CP-3C": "ready_with_limitations"},
    "t4_13": "T4.13 carries one row per consumer: [entry, status, relevant gap ids (every retained gap), actions]; the CP-3C row status is ready_with_limitations and the CP-2D row status is ready_with_limitations; CP-1A and CP-2 stay not_ready (unassessed, as in S1). CP-1 T4.13 is a CP-1 output; this oracle pins only the statuses.",
    "refused_variants": {
        "kpi_evidence_for_debt_schedule": ["Incompatible or unavailable dependency evidence: CP-3C debt_schedule"],
        "unknown_requirement_key_covenant_metrics_on_facility_evidence": [
            "Duplicate or unknown requirement: CP-3C covenant_metrics",
            "Incompatible or unavailable dependency evidence: CP-3C covenant_metrics",
        ],
    },
    "observed_on_s1_store": {"facility_observation_records": 42, "ebitda_kpi_records": 12, "retained_gaps": 1132,
                             "note": "counts on the S1 promoted CP-1 store; the selectors, not these counts, are the literal"},
    "does_not_gate_begin": "CP-3C begin is gated by the edge rule (CP-0, CP-1, CP-2D settled), not by T4.13 (execution.py:236-245)",
    "probed": "2026-10-28 on a scratch copy of the S1 promoted CP-1 store (DownstreamInputs with requested consumers set to this run's four): validate_downstream_review and _assess_consumers; a promotion of THIS pack was not run",
}

# --- manifest ---------------------------------------------------------------------------------

RUN = {
    "run_id": "slice-cp3c-positive",
    "issuer_id": FIN["run"]["issuer_id"],
    "issuer_name": ISSUER,
    "as_of": AS_OF,
    "method_version": FIN["run"]["method_version"],
    "case_kind": "synthetic",
    "pathway": "covenant_refinancing",
    "requested_modules": ["CP-1", "CP-1A", "CP-2", "CP-2D", "CP-3C"],
}


def fact_bindings():
    b = {}
    LTM_P = "LTM Q4 25: 2025-01-01 to 2025-12-31"
    LTM = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
    observed = {"cash_closing": "20.00", "undrawn_rcf": "0", "adjusted_ebitda": "30.0", "cash_interest": "-5.00"}
    for name, (tbl, metric) in CP1_NAMES.items():
        b[name] = {"source": "CP-1", "table_id": tbl, "period": LTM_P, "label": f"{LTM} · {metric}",
                   "observed_on_promoted_head": observed[name], "rule": "exactly one fact; status is read, never defaulted"}
    for f in CP1_FACILITY_FIELDS:
        b[f"term-loan.{f}"] = {"source": "CP-1", "table_id": "T4.18", "field": f, "period": "q4-2025", "facility_id": "term-loan",
                               "observed_on_promoted_head": {"secured_status": "SECURED", "seniority": "SENIOR",
                                                             "annual_amortisation": "0", "facility_name": "Northbridge Term Loan"}[f],
                               "rule": "the QUARTER period at the latest period end wins over its FY alias; the alias must agree on every term (financial_series._maturity_figure rule); one facility row per facility_id"}
    for name, (fid, what) in CP2D_NAMES.items():
        b[name] = {"source": "CP-2D", "fact_id": fid, "what": what,
                   "rule": "the stable CP-2D fact id of cases/cp2d-owner/expected.json; ref in the view equals the id; a missing CP-2D cell is offered with its status, never defaulted"}
    return b


manifest = {
    "schema_version": "cp3c-owner-cases/1",
    "scope": "CP-3C (Refinancing and liability-management risk) owner inputs: a CP-0 -> CP-1 -> CP-1A -> CP-2 -> CP-2D -> CP-3C run over the frozen S1 sources, one positive CP-3C attempt, one attempt over a CP-2D minimum-cash gap and one without a margin step-up, cloned from settled upstreams, plus seven composer-level fixtures",
    "status": "DRAFT rev 3 2026-10-28 (fix round 2 after review-precise-2, by mx-feature); scoped re-review and LEAD adoption pending; not executed against any product core (none exists)",
    "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
    "frozen_inputs": [{"path": k, "sha256": v, "use": u} for (k, v), u in zip(PINS.items(), [
        "edges and table ids: required CP-0, CP-1, CP-2D; optional CP-1A, CP-2A, CP-4, CP-3D; T3D.1-T3D.11 registered under CP-3C only (D4: used as is, no edit proposed)",
        "identity and financial sources, pages and shas reused by reference; facility, cash flow and EBITDA operands parsed from pages 2-5",
        "business source pages and sha reused by reference (positive)",
        "literal CP-0 readiness review, CP-1 source_context, CP-1A business_context and CP-2 credit_synthesis reused unchanged except the CP-0 consumer deltas",
        "frozen CP-2D manifest: CP-1 fact_bindings predicates reused by CP-2D's own step",
        "frozen CP-2D literals reused byte for byte: the CP-2D step (positive, gap_minimum_cash), the CP-0 CP-2D consumer entry and the cp2d_blocked attempts",
        "frozen CP-2D expected cells: the facts CP-3C consumes (D3 pins); every CP-2D cell read is asserted equal to the source-derived value here",
        "frozen CP-2D builder (pin only: the method of the upstream whose cells are consumed)",
        "prohibited-conclusion phrase tables transcribed (PROHIBITED, NEAR_INSTRUMENT, INSTRUMENT_NOUN of deploy_vii/business_context.py); pin only",
    ], strict=True)],
    "sources": [
        {"source_id": "identity", "ref": "cases/financial/manifest.json#sources[identity]", "sha256": IDENT_SHA},
        {"source_id": "financial", "ref": "cases/financial/manifest.json#sources[financial]", "sha256": FINANCIAL_SHA, "limitation": LIMIT_FIN},
        {"source_id": "business", "ref": "cases/snapshot/manifest.json#business_source.positive", "sha256": BUS_SHA},
    ],
    "design_reference": {
        "path": "/Users/ericguei/Documents/DEPLOY VII/design/reference/rbot-fp-04-covenant-refinancing.dc.html",
        "sha256": "57f921b3b4c1ed53ab3c5cd39295dd5bd9f29b46d4b5978f3974cab1f78169ad",
        "use": "read only, outside this repository, never edited and not depended on at run time; not read by the builder; assigns Refinancing paths and LME capacity and creditor exposure to CP-3C",
    },
    "run": RUN,
    "run_note": "A new run (new run_id and requested_modules change PreparedPack.content_hash), over the S1 source bytes. It is the CP-2D run plus CP-3C: pathway covenant_refinancing (FP04, render.py:130; contracts.py lists CP-3C in that pathway). CP-MODEL is left out (registry.plan would put it before CP-2D and G1 refuses an analytical module after a deterministic one). No legal source: CP-4 is an optional, unread edge in this version (see optional_edges).",
    "plan_order_expected": PLAN_ORDER,
    "edges": {
        "required": {"CP-0": "block", "CP-1": "block", "CP-2D": "block"},
        "optional": {m: "restricted" for m in OPTIONAL_UNREAD},
        "source": "src/deploy_vii/methodology.json (pinned) and registry.edge_rule (probed 2026-10-28); no edge_rules entry for CP-3C",
        "bound_in_attempt_inputs": ["prepared-pack", "CP-0", "CP-1", "CP-1A", "CP-2D", "refinancing-risk-submission (added when settled)"],
    },
    "optional_edges": {
        "read": [],
        "unread": {
            "CP-4": "LME capacity needs CP-4's basket capacity amounts, which the frozen CP-4 oracle always shows as missing ('Basket capacity amounts are not calculated'), and CP-4 runs on the legal pack (a different pack and promotion). Nothing computable would flow in; the LME half is shown as honest gaps (T3D.5) and the liability-management path is Insufficient Information",
            "CP-3D": "Market-implied spread and default intensity need the CP-3D market source (third_party) in the pack and the pack has no reference rate level; refinancing cost is shown as a margin step-up over current terms instead",
            "CP-2A": "A stressed refinancing case needs a CP-2A run; the Stress column of T3D.5 is a gap",
            "CP-1A": "Business and ownership context would inform owner-support and asset-sale paths; not read, the path is Insufficient Information",
        },
        "rule": "An unread optional edge is absent from attempt.inputs, from the view and from the trace; each unread edge is an own limitation",
    },
    "run_note_cp1_downstream": "CP-1's downstream-readiness stage names CP-3C requirements debt_schedule and maturity_profile (downstream_readiness.py:34, :178). The S1 readiness literal assesses no consumer (consumers: []), so on the S1 route CP-1 T4.13 shows every consumer not_ready and nothing supplies them; this run therefore ships its own CP-1 readiness literal (submissions.json#cp1_downstream_review) that assesses CP-2D and CP-3C, and expected.json#cp1_downstream_readiness pins the outcome (CP-3C and CP-2D ready_with_limitations). The CP-2D frozen run is unchanged. T4.13 does not gate begin (the edge rule does).",
    "upstream_literals": {
        "CP-0": "cases/snapshot/submissions.json#positive.readiness_review with pack_sha256 bound at run time and cp0_consumer_deltas appended to consumers in order (CP-2D, then CP-3C)",
        "CP-1": "cases/snapshot/submissions.json#cp1_submission and #positive.cp1_source_context, except the readiness stage: submissions.json#cp1_downstream_review replaces the S1 {\"consumers\": []}",
        "CP-1A": "cases/snapshot/submissions.json#positive.business_context",
        "CP-2": "cases/snapshot/submissions.json#positive.credit_synthesis with {{FIG:name}} replaced as S1a lease rev 2 M2 freezes",
        "CP-2D": "cases/cp2d-owner/submissions.json#cp2d.positive (cases positive, gap_no_repricing) and #cp2d.gap_minimum_cash (case gap_minimum_cash), {{FACT:name}} bound by cases/cp2d-owner/manifest.json fact_bindings",
    },
    "cp0_consumer_deltas": "submissions.json#cp0_consumer_deltas",
    "analyst_judgment_policy": "The margin step-up (or its absence) and the five path assessments are literal submission input. Text is digit-free; builder-checked against the oracle's own validator.",
    "fact_bindings": fact_bindings(),
    "fact_binding_note": "CP-1 predicates reuse the CP-2D forms and were observed read-only on a promoted CP-1 head (scratch copy of a CP-2D probe store, 2026-10-28; values listed as observed_on_promoted_head). The T4.18 text values SECURED, SENIOR are the head's, mapped from page 5 'senior secured term loan'. CP-2D facts are named by their stable ids. {{FACT:name}} tokens in basis_refs are replaced by the offered ref at run time (CP-1 fact id, or the CP-2D stable id).",
    "view_tree_draft": {
        "status": "DRAFT: shape proposed by this preparation, not observed (no core exists); LEAD freezes it after a probe on the first product-settled core",
        "view": "owners.cp3c.view(historical, attempt) -> (sha256, body), registered in G1's _VIEWS['refinancing_risk'] (docs/G1X-OWNER-CORE-PROTOCOL.md); NOT module_context()",
        "top_level_keys_in_order": ["upstream", "facts", "facilities", "unread_optional_edges", "bounds", "inherited_limitations"],
        "upstream": "[{module_id, status}] for CP-0, CP-1, CP-2D (the three required edges)",
        "facts": "[{ref, name, source, label, period, unit, shown, status, limitation|null}] one entry per name in fact_bindings (CP-1 and CP-2D), INCLUDING missing facts (status missing, shown a gap word, never a number); sorted by name",
        "facilities": "[{facility_id, facility_name, secured_status, seniority, rate_type}] one entry per T4.18 facility of the q4-2025 snapshot, text fields only",
        "unread_optional_edges": ["CP-1A", "CP-2A", "CP-4", "CP-3D"],
        "bounds": {"repricing_bps": [0, 1000], "path_kinds": list(KINDS), "feasibility": ["High", "Medium", "Low", II]},
        "forbidden_keys": ["quote", "citations", "record_json", "formula", "source_amount", "stated_amount"],
    },
    "cases": [
        {"case_id": "positive", "base": "settled upstream of slice-cp3c-positive (CP-2D positive)", "submission": "submissions.json#cp3c.positive"},
        {"case_id": "gap_minimum_cash", "base": "clone of the positive store before CP-2D begins; CP-2D settles its gap_minimum_cash literal; CP-3C then runs", "submission": "submissions.json#cp3c.gap_minimum_cash"},
        {"case_id": "gap_no_repricing", "base": "clone of the positive store before CP-3C begins", "submission": "submissions.json#cp3c.gap_no_repricing"},
        {"case_id": "blocked_cp3c", "base": "clone of the positive store before CP-3C begins", "submission": "submissions.json#cp3c_blocked (attempts 0 and 1 both invalid)", "expected": "expected.json#negative_cases.blocked_cp3c"},
        {"case_id": "begin_refused_cp2d_blocked", "base": "clone of the settled upstream with CP-2D settled blocked from cases/cp2d-owner/submissions.json#cp2d_blocked before CP-3C begins", "submission": "none: CP-2D attempt 1 settles blocked and the walk then retains the CP-3C begin as a refusal (no CP-3C attempt)", "expected": "expected.json#negative_cases.begin_refused_cp2d_blocked"},
    ],
    "fact_copy_rule": "A table cell copied from a CP-1 or CP-2D fact keeps that fact's own value_class and citations or calculation_id (CP-1 T4.18 source; CP-2D principal and maturity source, months and inside-horizon calculated, CP-2D horizon and minimum cash analyst_judgment); amounts are in unit MILLIONS with currency USD on every MILLIONS cell, a missing or not-applicable cell carrying its settled twin's unit and currency (CP-1 T4.10 facts already are; the CP-2D cells already are; CP-2D lease acceptance 1 pins currency USD on every amount cell; the CP-1C rule extends it to gap cells). Copies carry cp1_operand or cp2d_operand in expected.json. For a cp2d_operand copy the amount, unit, state and shown value equal the frozen CP-2D oracle cell; its period and value_class equal the CP-2D oracle cell's own `period` and `value_class` (re-pinned at the Stage 2 close release): the balance date 2025-12-31 on every copy except the principal copies, which keep CP-1's T4.18 period q4-2025, and, for a copied gap, the CP-2D gap cell's value_class. A copy of an analyst_judgment fact is never referenced by a claim.",
    "ratio_storage_rule": "Ratio facts (multiples, shares, cover) are stored quantised to 4 dp half-up; the shown value rounds from the stored one (display.py ROUND_HALF_UP); amounts are exact Decimals.",
    "fixtures": [{"fixture_id": k, "kind": "composer-level unit fixture, not a pack run", "construction": v["note"]} for k, v in FIXT.items()],
    "consumer": {
        "reads": "CP-2D (required edge): horizon, run-rate annual flow, minimum cash or its gap, funding gap or its gap, maturity-wall principal, maturity date, months and inside-horizon flag per facility, head hash and status",
        "consumption_of_cp2d": "closes CP-2D's D3 when a run of this lease passes (CP-3C is the actual consumer in an actual run)",
        "consumption_of_cp3c": "OPEN: CP-4C (optional edge CP-3C) has no core, CP-3 and CP-6 never read CP-3C (cp3_relative_value.py:99-104, cp6_committee.py:113), CP-5 counts only after a D3 scope lease",
    },
}

# --- submissions ------------------------------------------------------------------------------

submissions = {
    "schema_version": "cp3c-owner-submissions/1",
    "note": "Literal analyst input only. {{FACT:name}} tokens are replaced by offered refs at run time (manifest.fact_bindings). CP-0, CP-1, CP-1A and CP-2 literals are those of cases/snapshot/submissions.json, the CP-2D step and the CP-2D CP-0 entry are those of cases/cp2d-owner/submissions.json, unchanged.",
    "cp0_consumer_deltas": [CP0_CP2D, CP0_CP3C],
    "cp3c": SUBS,
    "cp3c_blocked": {
        "note": "Attempt 0 and attempt 1 are both invalid, so CP-3C settles blocked. Each attempt is a full literal payload (the same as refusal_inputs.step_up_over_limit and .step_up_negative); attempt 1 is begun with repair_of set.",
        "attempt_0": REFUSAL_INPUTS["step_up_over_limit"]["payload"],
        "attempt_1": REFUSAL_INPUTS["step_up_negative"]["payload"],
    },
    "cp1_downstream_review": CP1_DOWNSTREAM_REVIEW,
    "cp2d_blocked_ref": "cases/cp2d-owner/submissions.json#cp2d_blocked (attempt_0, attempt_1), reused to settle CP-2D blocked for begin_refused_cp2d_blocked",
    "refusal_inputs": dict({"note": "Each entry is a full literal payload (base_case names the cp3c case it was derived from); expected issue wording is fixed in expected.json#refusals. A wrong-typed bps is a schema type error owned by G1's generic schema refusal, not a CP-3C validator class."}, **REFUSAL_INPUTS),
}

# --- CP-0 facts added by the CP-3C consumer (pattern of cases/cp2d-owner/expected.json#cp0_with_cp2d) ---

cp0_with = {
    "status": "restricted",
    "live_consumers": ["CP-1", "CP-1A", "CP-2", "CP-2D", "CP-3C"],
    "plan_order": PLAN_ORDER,
    "exact_commands": {"CP-1": "Run CP-1", "CP-1A": "Run CP-1A", "CP-2": "Run CP-2", "CP-2D": "Run CP-2D", "CP-3C": "Run CP-3C"},
    "added_facts_cp3c": [
        {"fact_id": "T4.CP-3C.demand", "text": CP0_CP3C["evidence_demand"], "cites": [["identity", "page:1"], ["financial", "page:1"], ["financial", "page:5"]]},
        {"fact_id": "T4.CP-3C.readiness", "text": "READY_WITH_LIMITATIONS", "cites": []},
        {"fact_id": "T4.CP-3C.rationale", "text": CP0_CP3C["rationale"], "cites": [["identity", "page:1"], ["financial", "page:1"], ["financial", "page:5"]]},
        {"fact_id": "T8.CP-3C.candidate_command", "text": "Run CP-3C", "cites": []},
        {"fact_id": "T8.CP-3C.exact_command", "text": "Run CP-3C", "cites": []},
        {"fact_id": "T8.CP-3C.sources", "text": "identity, financial", "cites": []},
        {"fact_id": "T8.CP-3C.limits", "text": LIMIT_FIN, "cites": []},
        {"fact_id": "T8.CP-3C.upstream", "text": "CP-0 slice-cp3c-positive; analytical dependencies checked separately", "cites": []},
    ],
    "added_facts_cp2d": "as cases/cp2d-owner/expected.json#cp0_with_cp2d.added_facts",
    "note": "Fact ids and texts probed 2026-10-28 with the product build_readiness on a scratch pack of this run (identical to the CP-2D pattern); never settled by a product CP-0 submit.",
}

# --- expected ---------------------------------------------------------------------------------

# --- prohibited-conclusion probe (review-precise-1 M2) -------------------------------------------------------

PROBE_SENTENCES = [
    # (class, text): the three refusal literals, the reviewer's missed sentences and its false-positive sentences
    ("refusal_literal", "We recommend this path."),
    ("refusal_literal", "The expected recovery is high."),
    ("refusal_literal", "The covenant test is met."),
    ("missed_by_revision_1", "Expected recoveries are high."),
    ("missed_by_revision_1", "Lenders would recover par."),
    ("missed_by_revision_1", "The group complies with its covenants."),
    ("missed_by_revision_1", "The group is compliant with the leverage covenant."),
    ("missed_by_revision_1", "There is no breach of the covenant."),
    ("missed_by_revision_1", "The covenant is met."),
    ("missed_by_revision_1", "The issuer will be refinanced."),
    ("missed_by_revision_1", "We advise lenders to extend."),
    ("missed_by_revision_1", "Investors should buy the loan."),
    ("missed_by_revision_1", "Holders should avoid this credit."),
    ("missed_by_revision_1", "The recovery rate is high."),
    ("missed_by_revision_1", "A covenant breach is unlikely."),
    ("missed_by_revision_1", "Refinancing is assured."),
    ("missed_by_revision_1", "Default is likely."),
    ("missed_by_revision_1", "We suggest an amend and extend."),
    ("missed_by_revision_1", "Lenders should extend the maturity."),
    ("false_positive_in_revision_1", "The group could sell non-core assets to repay principal."),
    ("false_positive_in_revision_1", "No parent guarantee is bound to this analysis."),
    ("false_positive_in_revision_1", "Asset sale proceeds are not evidenced."),
    ("false_positive_in_revision_1", "A buyer for the division is not identified."),
    ("false_positive_in_revision_1", "The loan is held in compliance with no stated covenant evidence."),
    ("product_permitted", "The recovery is high."),
    # revision 3 (review-precise-2): "fulcrum" is carried by the core-local check; two further conclusions are recorded guard limits
    ("added_in_revision_3", "The term loan is the fulcrum security."),
    ("added_in_revision_3", "Refinancing is likely."),
    ("added_in_revision_3", "The issuer is in breach."),
]
# Sentences that state a conclusion but no phrase of the guard names: the guard is a phrase list, not a semantic review
# (business_context.prohibited_issues docstring), so these are valid text under this oracle, recorded as guard limits.
GUARD_LIMITS = {
    "Expected recoveries are high.", "We advise lenders to extend.", "Holders should avoid this credit.",
    "Default is likely.", "We suggest an amend and extend.", "Lenders should extend the maturity.",
    "Refinancing is likely.", "The issuer is in breach.",
}


def prohibited_probe():
    out = []
    for cls, text in PROBE_SENTENCES:
        g = guard("probe", text)
        flagged = [i for _, i in g]
        if cls in ("missed_by_revision_1", "refusal_literal"):
            assert flagged or text in GUARD_LIMITS, text
        if cls == "added_in_revision_3":
            assert bool(flagged) == (text not in GUARD_LIMITS), text
        if cls == "false_positive_in_revision_1":
            # the two revision-1 false positives (sell / guarantee) are valid; the last is a phrase-guard hit, kept visible
            assert bool(flagged) == (text == "The loan is held in compliance with no stated covenant evidence."), text
        entry = {"class": cls, "text": text, "issues": flagged, "origin": sorted({o for o, _ in g})}
        if text in GUARD_LIMITS:
            entry["guard_limit"] = "states a conclusion no guard phrase names; valid text under a phrase guard"
        if cls == "product_permitted":
            assert not flagged, text
            entry["note"] = "permitted by the product guard: a mention of recovery prospects as a credit mechanic is not a recovery outcome (business_context.py, PROHIBITED comment)"
        if flagged and cls == "false_positive_in_revision_1":
            entry["note"] = "a compliance word within four words of the word covenant; the guard cannot tell a negated or empty statement from a conclusion, so it refuses (a phrase guard, not a semantic review)"
        out.append(entry)
    return out


PROHIBITED_PROBE = prohibited_probe()
PROHIBITED_GUARD = {
    "product": "deploy_vii.business_context.prohibited_issues(path, text) with its default kinds (peer ranking, instrument recommendation, recovery conclusion; ACTIONS are not a default kind), transcribed in build.py (BC_PROHIBITED, BC_NEAR, BC_NOUN) with src/deploy_vii/business_context.py sha256-pinned; also used by CP-2 (cp2_synthesis.py:489)",
    "core_local": "one core-local check with three kinds: 'covenant compliance' (complies, complied, complying, compliant, compliance, breach, breaches, breached, met, satisfied within four words of covenant/covenants; and 'headroom is sufficient'), 'recovery conclusion' (the word fulcrum, in the product's issue form) and 'refinancing outcome' (will be refinanced, will refinance, refinancing is assured, refinancing is certain, will default)",
    "issue_form": "<path>: prohibited conclusion (<kind>): \"<phrase>\" , one issue per matching phrase, the product's issues first (guard table order), then the core-local ones",
    "dropped_from_revision_1": "the home-made list (recommend/buy/sell words, fulcrum, a bare 'recovery', guarantee): buy and sell as words and guarantee are no longer refused; 'fulcrum' is not held by the product guard and was not carried in revision 2; revision 3 carries it in the core-local check as kind 'recovery conclusion'",
}

# --- tamper (review-precise-1 H1; the recipe shape of cases/cpdr-owner/expected.json#tamper) ------------------

TAMPER_TARGET = "T3D.2.r02"  # Resources applied at the maturity dates: a computed total, not an input to any other fact
DERIVES_FROM = {  # the oracle's lineage of the computed cells of the positive case (the Calculation.inputs a product cell would name)
    "T3D.1.r01.c6": ["T3D.1.r01.c5"], "T3D.1.r01.c8": ["T3D.1.r01.c6", "T3D.1.r01.c7"],
    "T3D.1.r01.c9": ["T3D.1.r01.c6", "T3D.1.r01.c8"], "T3D.1.r01.c10": ["T3D.1.r01.c6", "T3D.1.r01.c8"],
    "T3D.2.r01": ["T3D.1.r01.c6"], "T3D.2.r02": ["T3D.1.r01.c8"], "T3D.2.r03": ["T3D.1.r01.c9"],
    "T3D.2.r04": ["T3D.1.r01.c6"], "T3D.2.r05": ["T3D.1.r01.c2"], "T3D.2.r06": ["T3D.1.r01.c3"],
    "T3D.2.r08": ["T3D.2.r01", "T3D.2.r07"], "T3D.2.r09": ["T3D.2.r03", "T3D.2.r07"],
    "T3D.3.r03": ["T3D.3.r01", "T3D.3.r02"], "T3D.3.r05": ["T3D.2.r01"], "T3D.3.r06": ["T3D.3.r04", "T3D.3.r05"],
    "T3D.3.r07": ["T3D.3.r01", "T3D.3.r06"], "T3D.3.r08": ["T3D.3.r02", "T3D.3.r07"],
    "T3D.4.r01.c4": ["T3D.4.r01.c3"], "T3D.4.r01.c5": ["T3D.4.r01.c3"], "T3D.4.r01.c6": ["T3D.3.r02", "T3D.4.r01.c5"],
    "T3D.5.r01.c1": ["T3D.4.r01.c5"], "T3D.5.r02.c1": ["T3D.3.r02", "T3D.5.r01.c1"],
}


def tamper_block():
    pos = EXPECTED_CASES["positive"]
    cells = {c["fact_id"]: c for t in pos["tables"].values() for rw in t["rows"] for c in (rw[1] if isinstance(rw[1], list) else [rw[1]])}
    cell = cells[TAMPER_TARGET]
    assert cell["state"] == "known" and cell["value_class"] == "calculated" and cell["amount"] == "10"
    assert "cp1_operand" not in cell and "cp2d_operand" not in cell
    assert all(TAMPER_TARGET not in srcs for srcs in DERIVES_FROM.values()), "the target must derive nothing else"
    assert all(TAMPER_TARGET not in c["references"] and TAMPER_TARGET not in c["cites_from"] for c in pos["claims"])
    assert TAMPER_TARGET not in json.dumps(SUBS["positive"]), "a computed fact is not in the step output"
    assert pos["derived"]["total_resources_applied"] == cell["amount"]
    return {
        "case": "positive (closed run: CP-0, CP-1, CP-1A, CP-2, CP-2D and CP-3C settled, receipt sealed)",
        "target_fact": TAMPER_TARGET,
        "from": "10",
        "to": "11",
        "why_this_fact": "a computed fact lives only in the CP-3C result Module: the table cell holds the fact id, the step output holds the judgment submission (no computed fact), no claim references it and no other computed fact derives from it (builder-asserted against DERIVES_FROM and the claims), so the forged Module stays internally consistent and only the probe's rebuild (the Python composer over the journaled payload and the bound CP-0, CP-1 and CP-2D heads, which gives resources applied 10) contradicts it",
        "recipe": [
            "1. Copy the closed positive store directory (blobs, snapshots, current, audit) to a scratch path.",
            "2. Load the CP-3C head's result Module; replace only the amount of fact T3D.2.r02 (Decimal 10 -> 11; unit, currency, period, value_class, calculation_id and formula unchanged); leave every other fact (T3D.2.r03 need 40, T3D.1.r01.c8 and c9, every claim, table and limitation) unchanged.",
            "3. Serialise the forged Module as Execution._store does (model_dump_json); its sha256 R2 must equal Module.content_hash(); write blobs/R2.",
            "4. Build a new ExecutionSnapshot equal to the current one with the CP-3C Attempt.result_sha256 and Head.result_sha256 set to R2 (status, inputs and commands unchanged, so head_of(forged Module) equals the Head) and the same parent; write snapshots/<its sha256>.json and rewrite current to that digest.",
            "5. In the retained receipt: set the CP-3C SettledHead.result_sha256 to R2; set receipt.snapshot_sha256 and every coordinate that named the old final snapshot (the CP-3C settling OwnerSubmission.snapshot_after_sha256: owner_workflow.py _advance -> _finish_walk; its record is retained as audit/submissions/<content_hash> by _retain) to the new digest; delete audit/submissions/<old record hash> and write the edited OwnerSubmission as audit/submissions/<its content_hash> (model_dump_json bytes); rewrite audit/receipt.sha256 with the forged receipt's content_hash (the CP-DR / CP-3 A4 / S1a R3-5 pattern: the audit file travels under its new hash). CP-3C is the last analytical module of the run and no deterministic module follows, so the CP-3C settling submission is the final one.",
        ],
        "expect": {
            "passes": "everything upstream of the probe: audit inventory, blob and snapshot hashes, ancestor walk, head_of equality, begin and publication records, call and read replay (the retained read_inputs body is untouched), journaled-step replay (the payload and step are untouched)",
            "refuses": "cp3c.probe raises WorkflowError('identity_mismatch'); verify_owner_run_receipt raises identity_mismatch",
            "test_asserts": "on the forged copy, _verify_audit and every check before _PROBES pass (as CP-3 A4 (a)); then cp3c.probe raises identity_mismatch. A test asserting identity_mismatch alone would never show that the probe was reached.",
        },
        "step_output_edit": "an edited CP-3C step output is caught by the store's own blob hash check, not by the probe's output comparison (recorded limitation, S1a R3-5); an edited retained read_inputs body is caught by the call and read replay, not by the probe",
    }


expected = {
    "schema_version": "cp3c-owner-expected/1",
    "claims_note": "Claim templates are run text (decision 0005 MC-2, execution.py:296): a figure is a {<fact_id>|<unit>} reference (unit US$ m or x) to a known numeric cell of CP-3C's own tables that carries a citation or a calculation id; a missing value is a [<fact_id>] chip naming a gap cell; the date is a period label. `text` is the resolved spelling (a chip resolves to the gap spelling, shown here as the pattern '∅ G#'); `references` lists the cell fact_ids.",
    "derivation_note": "Every value is a Decimal derived by cases/cp3c-owner/builder/build.py from pages 2-5 of the frozen financial source (parsed as text), the pinned CP-2D oracle cells and the method in the lease. Comparison is numeric Decimal equality; ratios are stored to 4 dp half-up; `shown` is the exact display spelling (display.py: amounts 0 dp half-up, negatives in brackets, multiples 2 dp with x, percent 1 dp, basis points and months as exact text with their unit). Entity: " + ENTITY + "; currency USD; unit MILLIONS (US$ m); balance date 2025-12-31; flows the twelve months 2025-01-01 to 2025-12-31 (LTM Q4 25 = FY25).",
    "source_facts": {
        "cash": {"amount": dec(CASH), "source": "financial page:4 Cash and cash equivalents (Q4); CP-1 T4.10 cash_closing"},
        "undrawn_revolver": {"amount": dec(UNDRAWN), "source": "financial page:4 RCF commitment and RCF drawings (explicit zeros); CP-1 T4.10 undrawn_rcf"},
        "adjusted_ebitda_ltm": {"amount": dec(EBITDA_ADJ), "derivation": "7.5 x 4", "source": "financial page:2 Adjusted EBITDA (FY column 30.0 agrees); CP-1 T4.10 adjusted_ebitda"},
        "cash_interest_paid_ltm": {"amount": dec(CASH_INTEREST), "derivation": "1.25 x 4; CP-1 shows the outflow as -5.00", "source": "financial page:3 Cash interest paid; CP-1 T4.10 cash_interest"},
        "run_rate_annual": {"amount": dec(F_ANNUAL), "derivation": "19 + (10) + (4) - 5 = 0 (CP-2D rule)", "source": "financial page:3; equals cases/cp2d-owner/expected.json positive T2E.3.r01"},
        "term_loan": {"facility_id": "term-loan", "principal": dec(FAC_PRINCIPAL), "maturity_date": MATURITY.isoformat(), "annual_amortisation": dec(AMORT), "secured_status": TL_SECURED, "seniority": TL_SENIORITY, "rate": "floating, SOFR, spread 0 bp, floor 0 bp", "source": "financial page:5"},
        "reference_rate_level": {"state": "missing", "source": "no source states a reference rate level; the all-in cost of a refinancing is never calculated"},
    },
    "method_rules": {
        "balance_date": BAL_DATE.isoformat(),
        "facility_order": "ascending months from the balance date (CP-2D's whole-month rule), ties by facility_id",
        "amortisation_before_maturity": "min(annual amortisation x months / 12, principal)",
        "principal_payable_at_maturity": "principal - amortisation before maturity",
        "base_resources": "cash + undrawn committed revolver - minimum cash (CP-2D's analyst assumption, read from CP-2D)",
        "resources_at_maturity": "base resources + run-rate annual flow x months / 12 - amortisation of all facilities up to that date (each to min(date, its own maturity)) - principal paid from resources at earlier maturities",
        "resources_applied": "min(principal payable at maturity, max(0, resources at maturity))",
        "refinancing_need": "principal payable at maturity - resources applied; a computed 0 is 'no need', distinct from missing",
        "cover": "resources applied / principal payable at maturity (not_applicable when the principal payable is 0)",
        "currency": "every cell in unit MILLIONS, amount or gap, carries currency USD (report_view.figure_unit; CP-2D lease acceptance 1)",
        "revolver_availability": "the undrawn committed revolver at the balance date is counted at every maturity date, including a date after the revolver's own maturity (not read); an own limitation",
        "run_rate_beyond_horizon": "the CP-2D annual flow is held flat to each maturity date, including dates after the CP-2D horizon (own limitation)",
        "added_annual_cash_interest": "total principal payable at maturity x margin step-up (bp) / 10000; 0 bp is a known 0, an unassessed step-up is missing",
        "interest_cover": "adjusted EBITDA / cash interest paid; pro forma: / (cash interest paid + added annual cash interest); a zero interest is not_applicable, a zero EBITDA gives a known 0",
        "leverage_type_ratios": "amount / adjusted EBITDA; a non-positive EBITDA is not_applicable (shown n.m.), a missing operand is missing",
        "ranking": "(secured_status: SECURED 0, UNSECURED 1; seniority: SUPER_SENIOR 0, SENIOR 1, SENIOR_SUBORDINATED 2, SUBORDINATED 3, JUNIOR 4) compared lexicographically; claims at or ahead = principal of facilities with rank <= the facility's rank; any NOT_STATED flag makes every claims cell missing",
        "lme_capacity": "CP-4 is not read: the LME and Stress columns of T3D.5 are gaps in every case; the Base column is the largest claims at or ahead",
        "missing_rule": "any missing operand makes each dependent value missing with a stated reason; nothing defaults to 0; not_applicable (a defined ratio with a non-positive denominator) is distinct from missing; blocked is the module-level state",
    },
    "cases": EXPECTED_CASES,
    "cp0_with_cp3c": cp0_with,
    "upstream_asserted_only": {
        "statuses": {"CP-0": "restricted", "CP-1": "restricted", "CP-1A": "restricted", "CP-2": "restricted", "CP-2D": "restricted"},
        "cp2d_tables_equal": "the CP-2D head of the positive case has tables equal to cases/cp2d-owner/expected.json cases.positive; of gap_minimum_cash to cases.gap_minimum_cash (the CP-0 delta adds a CP-3C consumer only; CP-0 limitations are unchanged)",
        "cp1_facts_equal_source": "each fact bound by manifest.fact_bindings has the amount/status/text in source_facts",
        "cross_checks_not_read": {"interest_coverage_adjusted": "6 (equals T3D.3 interest cover)", "total_leverage_adjusted": "1.6667 (equals T3D.5 Base multiple, 4 dp)", "note": "CP-1 T4.10 facts the core does not read; the test reads them from the CP-1 head and asserts equality, observed on a promoted head"},
    },
    "cp3c_module": {
        "module_id": "CP-3C",
        "status_rule": "restricted: own limitations are non-empty and CP-0, CP-1 and CP-2D heads are restricted",
        "attempt_inputs": ["prepared-pack", "CP-0", "CP-1", "CP-1A", "CP-2D"],
        "settled_module_adds_input": "refinancing-risk-submission",
        "inherited_limitations_rule": "CP-0 head + CP-1 head + CP-2D head, each its limitations then inherited, de-duplicated, own findings removed (execution.py:345-366); the CP-2D own limitation strings 'Minimum cash is an analyst assumption, not a source figure.' (and its other lines) arrive as inherited where CP-3C does not repeat them; CP-3C repeats the first so it appears once, as own; bound at run time",
        "table_ids": USED_TABLES,
        "table_titles": {"T3D.1": "Refinancing need by maturity", "T3D.2": "Refinancing burden", "T3D.3": "Refinancing cost sensitivity", "T3D.4": "Creditor position", "T3D.5": "LME capacity", "T3D.6": "Refinancing paths", "T3D.7": "Analyst judgments", "T3D.8": "Gaps ledger", "T3D.9": "Upstream trace"},
        "T3D.7": {"title": "Analyst judgments", "rows": "expected.cases.<case>.T3D.7_rows"},
        "T3D.8": {"title": "Gaps ledger", "rows": "expected.cases.<case>.T3D.8_rows (one row per own limitation, same order as own_limitations)"},
        "T3D.9": {"title": "Upstream trace", "rule": "rows [name, source module, table or stable id, shown or gap spelling] for each name read; fact ids bound at run time are not recorded; the CP-2D head hash is run-time and asserted in attempt.inputs"},
        "unused_registered": ["T3D.10", "T3D.11"],
        "evidence_rail": ["T3D.7", "T3D.9"], "limitations_rail": ["T3D.8"],
    },
    "refusals": REFUSALS,
    "refusal_order": "issues are returned in the oracle's order: (1) repricing presence, (2) bps range, (3) one row per kind, (4) for each text field in order (the repricing text fields, then per submitted path its text, credit_implication and limitation) the figure issue and then the guard issues, for all paths, (5) per submitted path its basis_refs, feasibility/category, limitation, cites-a-fact and liability-management issues; each literal refusal payload yields exactly one issue",
    "prohibited_guard": PROHIBITED_GUARD,
    "prohibited_probe": PROHIBITED_PROBE,
    "cp1_downstream_readiness": CP1_READINESS_EXPECTED,
    "tamper": tamper_block(),
    "negative_cases": {
        "blocked_cp3c": {
            "attempt_0": {"step": "invalid", "issues": [REFUSALS["step_up_over_limit"]]},
            "attempt_1": {"step": "invalid", "issues": [REFUSALS["step_up_negative"]], "repair_of": "attempt 0"},
            "module_status": "blocked",
            "tables": "none; a blocked head carries no T3D table and no claims",
            "head": "a blocked CP-3C head is published; cp3c_reader(store, head) on it exposes the status and no figures",
            "receipt": "verify_owner_run_receipt accepts the blocked head and every recomputed issue appears in the step issues",
        },
        "begin_refused_cp2d_blocked": {
            "setup": "clone of the settled upstream (CP-0, CP-1, CP-1A, CP-2); CP-2D attempt 0 and attempt 1 both submit the frozen cp2d_blocked literals (cases/cp2d-owner/submissions.json#cp2d_blocked). There is no separate CP-3C begin call and no CP-3C submission.",
            "mechanism": "CP-2D attempt 1 invalid -> _advance('CP-2D') (owner_workflow.py:657, :482-487) -> _begin('CP-3C') -> the store refuses the begin with BLOCKED_EDGE after a blocked producer -> the walk retains it as RefusedBegin with _refusal_kind 'blocked' (owner_workflow.py:448-478) and finishes",
            "cp2d_attempt_1_submit_outcome": {"status": "invalid", "refusal": "cp3c_blocked", "next_step": None},
            "receipt_refusals": [{"module_id": "CP-3C", "reason": "starts with 'Required upstream is unrun, stale or blocked' (owner_workflow.BLOCKED_EDGE)", "snapshot_sha256": "the snapshot after CP-2D settled blocked (the final snapshot of the run)"}],
            "attempt_consumed": False,
            "cp3c_attempt": "none: the snapshot holds no CP-3C attempt and no CP-3C head",
            "verifier": "verify_owner_run_receipt accepts the receipt: exactly one refusal, for the first analytical module without a head, and no later head (owner_workflow.py:855-892)",
            "scope": "this case pins only a blocked CP-2D producer. A blocked or stale CP-0 or CP-1 head is not retained as a refusal by the same path and is not pinned here.",
        },
    },
    "tool_use": {
        "CP-3C": "zero ok pack calls (every invoke is a refused not_permitted receipt); exactly one read_inputs per attempt before submit; its body equals the frozen view tree (manifest.view_tree_draft after freeze); a submit without that read is not_permitted; a snapshot change between read and submit is stale_binding",
    },
    "consumption": {
        "cp2d_consumed_by_cp3c": {
            "consumer": "owners.cp3c (the CP-3C core reads the settled CP-2D head through cp2d_reader(store, head))",
            "proof": [
                "CP-3C attempt.inputs carries CP-2D with sha256 equal to the final CP-2D head result_sha256, and the settled CP-3C module adds refinancing-risk-submission",
                "T3D.1 columns 1-4, T3D.2 rows 10-12 and T3D.4 column 3 are copies carrying cp2d_operand ids (expected cells) with the CP-2D cell's value and value_class",
                "the claim CP-3C-HORIZON-01 references the CP-2D funding gap copy",
                "in gap_minimum_cash the CP-2D missing minimum cash and funding gap arrive as gaps (never 0) and the dependent CP-3C values are gaps",
            ],
            "reads_beyond_the_cp2d_lease_pins": ["T2E.3.r01"],
            "pin_extension_needed": "cp2d_reader must also expose the run-rate annual flow (T2E.3.r01); the other reads are the CP-2D lease's pins (horizon, minimum cash or absence, wall rows, funding gap or missing, head hash, status)",
        },
        "cp3c_consumed_by": {
            "consumer": "none today; CP-4C lists CP-3C optional and has no core; CP-3 and CP-6 never read CP-3C",
            "reader_contract": "owners.cp3c.cp3c_reader(store, head) returns the settled CP-3C head's total principal payable at maturity, refinancing need or missing, per-facility need rows, added annual cash interest or missing, claims at or ahead of the most junior facility (Base), the path feasibility judgments, own limitations, the head hash and status",
            "status": "OPEN: acceptance of consumption waits for a CP-4C lease (or a D3 CP-5 scope lease); this oracle pins only what the reader must expose",
        },
    },
    "fp04_render": {
        "pathway": "covenant_refinancing",
        "design_reference": "rbot-fp-04-covenant-refinancing.dc.html: 'Refinancing paths' (CP-3C, path / feasibility chip / impact, ILLUSTRATIVE tag), 'LME capacity and creditor exposure' (CP-3C, collapsed, Base / LME / Stress); 'Funding gap' is headed CP-3C there but is registered to CP-2D by the frozen CP-2D lease (open question)",
        "blocks": {
            "refinancing-paths": {"owner": "CP-3C", "kind": "dense", "primary_tab": "T3D.6", "tabs": ["T3D.2", "T3D.3"], "state": "populated"},
            "lme-creditor-exposure": {"owner": "CP-3C", "kind": "dense", "collapsed": True, "primary_tab": "T3D.5", "tabs": ["T3D.4"], "state": "populated"},
        },
        "rails": {"evidence": ["T3D.7", "T3D.9"], "limitations": ["T3D.8"]},
        "cells": "block cell text equals the `shown` strings of expected.cases.<case>.tables; gap cells render '∅ G<n>' with n assigned in report order, not_applicable cells '∅ G<n> n.m.' (the expected shown is the pattern '∅ G#' / '∅ G# n.m.', an A7 exception)",
        "other_FP04_blocks": "CP-4 blocks (CP-4 not requested) and CP-2D blocks (asserted by the CP-2D lease) are not asserted here; T3D.1 moved from refinancing-paths to the funding-gap block (Q-C2, user 2026-10-29): it is a non-primary tab of funding-gap behind Fig. CR.3, and its expectations (tabs, figure, twin) are pinned in cases/charts/cr3-expected.json, not here",
    },
    "table_id_collision_check": "T3D.1-T3D.11 appear in src/deploy_vii/methodology.json only under CP-3C (asserted by this builder against the pinned file); a grep of src, tests, docs and cases on 2026-10-28 found them in methodology.json alone before this preparation; T3D.10 and T3D.11 are registered and unused",
    "not_verified": [
        "no product CP-3C core exists, so no expected value has been compared with product output",
        "the CP-0 consumer entries were probed with the product validate_review and build_readiness on a scratch pack (accepted; the added fact ids match this oracle) and never settled by a CP-0 submit",
        "the CP-1 head facts were observed (read-only) on a CP-2D probe store; the CP-1 promotion for the CP-3C run pack (new run id, requested modules) was never run",
        "the CP-2D cells are the CP-2D oracle's, not product output; the CP-2D oracle itself is unexecuted",
        "claim references: probed read-only with deploy_vii.prose.bare_figures only; no product module has resolved the references; the T3D cell fact_ids are this oracle's proposal; whether a copied cell of a calculated CP-2D fact carries its calculation_id is a core requirement",
        "the multi-facility ordering, amortisation, ranking and missing-amortisation rules are exercised only by composer fixtures with synthetic vectors, no pack case",
        "table titles, columns, path kinds and claim wording are this preparation's design: no r14 CP-3C SKILL.md is in the repository",
        "the blocked_cp3c and begin_refused_cp2d_blocked expectations follow owner_workflow.py as read and were never run",
        "the CP-1 readiness literal was validated (validate_downstream_review, _assess_consumers) on a scratch copy of the S1 promoted CP-1 store with this run's four requested consumers; a CP-1 promotion of THIS pack was never run, so the evidence selectors and the statuses are not observed on it",
        "the tamper recipe follows owner_workflow.py and execution.py as read and was never executed; that every check before the probe passes on the forged copy is unobserved",
        "the transcribed prohibited-conclusion phrase tables are compared with business_context.prohibited_issues by a read-only probe only, not by a test",
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
