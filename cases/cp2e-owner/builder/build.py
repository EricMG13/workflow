"""Writes cases/cp2e-owner/{manifest,submissions,expected}.json (stdlib only).

Oracle for CP-2E (macro, FX and hedging sensitivity). Independent transcription of the documented
method (work/lead/cp2e-owner-preparation/lease-draft.md): no product code is imported or run. It reads
only data files, each checked against a pinned sha256 before use: the frozen financial manifest, the three
S1 oracle files (the CP-0 base literal) and methodology.json.

Every arithmetic value is an exact Decimal derivation with the conventions stated in
expected.json#arithmetic. Every checkable property of the literal inputs (quotes on their page, whole-line
rows, value_text inside its quote, digit-free analyst text, prohibited phrases, claim references) is
asserted here, so an inconsistent input fails the build.

Run from the repository root:  python3 -I cases/cp2e-owner/builder/build.py
"""

import copy
import hashlib
import json
import re
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "cases" / "cp2e-owner"

PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    "cases/snapshot/expected.json": "d1aa1af9677cc4bd77b890261f0ceeca664acc72aac77f91da55cf36d7279baa",
    "src/deploy_vii/methodology.json": "348fbc4b877e4f0351ecc238ea005adf815291b15a6267f263459203a08f8d45",
}


def sha_file(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def load_pinned(rel):
    assert sha_file(rel) == PINS[rel], f"{rel}: sha256 differs from the pin"
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


def norm(s):
    return re.sub(r"\s+", " ", s)


def dedupe(items):
    return list(dict.fromkeys(items))


FIN = load_pinned("cases/financial/manifest.json")
S1M = load_pinned("cases/snapshot/manifest.json")
S1S = load_pinned("cases/snapshot/submissions.json")
S1E = load_pinned("cases/snapshot/expected.json")
METH = load_pinned("src/deploy_vii/methodology.json")

ISSUER = FIN["run"]["issuer_name"]
ISSUER_ID = FIN["run"]["issuer_id"]
AS_OF = FIN["run"]["as_of"]
SYNTH = "Synthetic case; not real issuer qualification"
LIMIT_FIN = S1M["financial_pack_limitation"]["text"]
assert LIMIT_FIN == "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."

# --- sources (frozen bytes reused, hash-checked) ---------------------------------------------------------
fin_src = {s["source_id"]: s for s in FIN["sources"]}
for _sid, _s in fin_src.items():
    assert page_sha([p["text"] for p in _s["pages"]]) == _s["sha256"], _sid
BUS = S1M["business_source"]  # used only by the CP-0 transcription self-check against S1
assert page_sha([p["text"] for p in BUS["positive"]["pages"]]) == BUS["positive"]["sha256"]

FIN_PAGES = {p["locator"]: p["text"] for p in fin_src["financial"]["pages"]}
assert list(FIN_PAGES) == [f"page:{i}" for i in range(1, 6)]
# The gap pack keeps pages 1-4 of the financial source byte for byte and drops page 5 (the facility schedule);
# its source hash is recomputed by the pack rule, so it is a derived variant, not a frozen source.
GAP_PAGES = {k: v for k, v in FIN_PAGES.items() if k != "page:5"}
PAGES_OF = {"positive": FIN_PAGES, "gap_no_facility_schedule": GAP_PAGES}
FIN_SHA = {"positive": fin_src["financial"]["sha256"],
           "gap_no_facility_schedule": page_sha([GAP_PAGES[k] for k in GAP_PAGES])}
assert FIN_SHA["gap_no_facility_schedule"] != FIN_SHA["positive"]
ID_SHA = fin_src["identity"]["sha256"]
NAMES = {"identity": fin_src["identity"]["name"], "financial": fin_src["financial"]["name"],
         "business": BUS["common"]["name"]}
LIMIT = {"identity": None, "financial": LIMIT_FIN, "business": None}
SRC = "financial"  # the only source the CP-2E step may read (fixed host scope)


def sha_map(case):
    return {"identity": ID_SHA, "financial": FIN_SHA[case]}


def line_of(locator, start):
    """The one whole page line of the financial source that starts with `start`."""
    hits = [ln for ln in FIN_PAGES[locator].split("\n") if ln.startswith(start)]
    assert len(hits) == 1, (locator, start, hits)
    return hits[0]


def sentence(locator, span):
    assert span in FIN_PAGES[locator] and FIN_PAGES[locator].count(span) == 1, (locator, span)
    return span


def q(locator, quote):
    assert norm(quote) in norm(FIN_PAGES[locator]), (locator, quote)
    return {"source_id": SRC, "locator": locator, "quote": quote}


# Quotes used by the literals: each is a verbatim span (sentence or whole row) of one financial page.
Q_CCY = sentence("page:1", "Currency: USD; amounts in millions.")
Q_FX_NONE = sentence("page:1", "There were no pro-forma adjustments, subsequent events, FX cash movements, or noncash debt changes through January 10, 2026.")
Q_TRANSLATION = sentence("page:1", "no capital contributions, share issuance, repurchases, revaluations, currency translation, perimeter changes, reserve transfers or other equity adjustments occurred")
Q_ROW_EBITDA = line_of("page:2", "Reported EBITDA")
Q_ROW_INTEREST = line_of("page:3", "Cash interest paid")
Q_ROW_FCF = line_of("page:3", "Levered free cash flow")
Q_ROW_FX = line_of("page:3", "FX effect on cash")
Q_ROW_DEBT = line_of("page:4", "Total debt")
Q_ONE_FACILITY = sentence("page:5", "There is exactly one debt facility: Northbridge Term Loan, facility_id term-loan.")
Q_DEBT_CCY = sentence("page:5", "USD millions; consolidated group; IFRS carrying values.")
Q_BALANCE = sentence("page:5", "FY2025 and Q4 share the same December 31, 2025 closing facility balance of 50.")
Q_RATE = sentence("page:5", "floating rate type with SOFR reference rate")
Q_SPREAD = sentence("page:5", "spread 0 basis points")
Q_FLOOR = sentence("page:5", "floor 0 basis points")
Q_SOFR_SPREAD = sentence("page:5", "SOFR reference rate, spread 0 basis points")  # names SOFR, states neither floating nor fixed
Q_TWO_LINES = sentence("page:2", Q_ROW_EBITDA + "\n" + line_of("page:2", "Adjusted EBITDA"))  # two whole lines, one quote
Q_ROW_PBT = line_of("page:2", "Profit before tax")
Q_NO_OTHER_DEBT = sentence("page:5", "No leases, unsecured debt, revolving commitments or revolving drawings exist at any reporting date.")
GAP_FACILITY = "No facility schedule in the pack, so the CP-2E rate terms and debt currency are absent"

# --- Decimal conventions -------------------------------------------------------------------------------
D = Decimal


def with_ctx(fn):
    with localcontext() as c:
        c.prec = 38
        c.rounding = ROUND_HALF_EVEN
        return fn()


def dstr(x):
    """Exact stored string of a Decimal (trailing zeros normalised away)."""
    if x is None:
        return None
    with localcontext() as c:
        c.prec = 80  # normalize() rounds to the context precision: keep every stored digit
        text = format(x.normalize(), "f")
    return "0" if text in ("-0", "") else text


NUM_RE = re.compile(r"^[0-9]{1,3}(?:\.[0-9]{1,4})?$")
ROW_NUM_RE = re.compile(r"^\(?[0-9]+(?:\.[0-9]+)?\)?$")


def row_decimal(token):
    neg = token.startswith("(")
    value = D(token.strip("()"))
    return -value if neg else value


def token_once(value_text, quote):
    """value_text occurs exactly once in the quote as a whole numeric token."""
    return len(re.findall(r"(?<![0-9.])" + re.escape(value_text) + r"(?![0-9]|\.[0-9])", quote)) == 1


def show(d, unit_class, decimals=None):
    """Product spelling of a known number (display.format_value, as cases/cpl10-owner): half-up on the exact value."""
    places, scale, suffix = {"amount": (0, 1, ""), "multiple": (2, 1, "x"), "percent": (1, 100, "%")}[unit_class]
    if decimals is not None:
        places = decimals
    rounded = (d * scale).quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP)
    body = f"{abs(rounded):,.{places}f}"
    return (f"({body})" if rounded < 0 else body) + suffix


UNIT_CLASS = {"MILLIONS": "amount", "MULTIPLE": "multiple", "PERCENT": "percent"}
# Currency and scale of a MILLIONS fact (as cases/cpl10-owner: CP-1's facts carry USD and scale 1000000); a
# MULTIPLE, PERCENT or basis_points fact carries no currency and the default scale 1.
CURRENCY_LABEL = {"USD": "US$"}  # report_view._CURRENCY_LABEL
SCALE_LABEL = {"MILLIONS": "m"}  # report_view._SCALE_LABEL
MILLIONS_SCALE = "1000000"


def figure_unit(unit, currency):
    """Transcription of report_view.figure_unit for the units of this oracle: the label a figure in prose shows
    after its number. MILLIONS -> scale_label (currency label + scale label), so USD gives 'US$ m' and no
    currency gives 'm'; MULTIPLE -> x; PERCENT -> %; basis_points -> bp (the ' bp' suffix stripped)."""
    if unit == "MILLIONS":
        return " ".join(part for part in (CURRENCY_LABEL.get(currency or "", currency or ""), SCALE_LABEL[unit]) if part)
    return {"MULTIPLE": "x", "PERCENT": "%", "basis_points": "bp"}[unit]


def spell(amount, unit, decimals):
    if unit == "basis_points":
        return dstr(amount) + " bp"
    return show(amount, UNIT_CLASS[unit], decimals)


# --- the validator (independent transcription of the lease's rules) ----------------------------------------
SECTIONS = ("interest_rate", "fx", "hedging")
CATEGORIES = ("Documentary Fact", "Analyst Interpretation", "Insufficient Information")
PROHIBITED = ("recommend", "buy", "sell", "overweight", "underweight", "downgrade", "upgrade", "covenant breach")
PROHIBITED_RE = re.compile(r"\b(?:" + "|".join(PROHIBITED) + r")\b", re.I)
ROW_LABELS = {"ebitda": "Reported EBITDA", "interest": "Cash interest paid", "fcf": "Levered free cash flow",
              "total_debt": "Total debt", "fx_cash_effect": "FX effect on cash"}
MAX_RATE_SHOCKS, MAX_FX_SHOCKS = 3, 3
RATE_BP_RANGE, FX_PCT_RANGE = (1, 1000), (1, 50)


def digit_free(path, text, issues):
    if text is not None and any(ch.isnumeric() for ch in text):
        issues.append(f"{path}: digits are not allowed")


def on_page(ref, path, issues, pages):
    sid, loc = ref["source_id"], ref["locator"]
    if sid != SRC:
        issues.append(f"{path}: source {sid} is outside the CP-2E scope (financial)")
        return False
    if loc not in pages or norm(ref["quote"]) not in norm(pages[loc]):
        issues.append(f"{path}: quote not found on {sid} {loc}")
        return False
    return True


def row_value(op, key, path, issues, pages):
    """A statement-row operand: the quote is a whole page line, labelled as `key`, ends in the FY column and
    value_text is its last value. Returns the signed Decimal or None."""
    if not on_page(op, path, issues, pages):
        return None
    lines = [ln.strip() for ln in pages[op["locator"]].split("\n")]
    if op["quote"].strip() not in lines:
        issues.append(f"{path}: quote is not a whole page line")
        return None
    if not op["quote"].startswith(ROW_LABELS[key] + "  "):
        issues.append(f"{path}: the row is not {ROW_LABELS[key]}")
        return None
    header = next((ln for ln in lines if ln.startswith("Period")), "")
    if not re.search(r"FY 2025(?:-12-31)?$", header):
        issues.append(f"{path}: the page header does not end in the FY column")
        return None
    last = op["quote"].split()[-1]
    if not ROW_NUM_RE.match(op["value_text"]) or op["value_text"] != last:
        issues.append(f"{path}: value_text {op['value_text']} is not the last value of the row")
        return None
    return row_decimal(op["value_text"])


def labelled_value(op, field, label, path, issues, pages):
    """A sentence operand: value_text occurs once as a whole token and follows `label` in the quote."""
    if not on_page(op, path, issues, pages):
        return None
    v = op[field]
    if not NUM_RE.match(v) or not token_once(v, op["quote"]):
        issues.append(f"{path}: {field} {v} does not occur in the quote")
        return None
    if not re.search(rf"{label}\s+{re.escape(v)}(?![0-9])", norm(op["quote"])):
        issues.append(f"{path}: {field} {v} is not labelled {label} in the quote")
        return None
    return D(v)


def code_value(op, path, issues, pages):
    if not on_page(op, path, issues, pages):
        return None
    c = op["code_text"]
    if not re.match(r"^[A-Z]{3}$", c) or not re.search(rf"(?<![A-Za-z]){c}(?![A-Za-z])", op["quote"]):
        issues.append(f"{path}: code_text {c} does not occur in the quote")
        return None
    return c


def check_submission(sub, pages):
    """Issues of the validator, in rule order."""
    issues = []
    code_value(sub["reporting_currency"], "reporting_currency", issues, pages)
    re_, ra = sub.get("rate_exposure"), sub.get("rate_absence")
    if bool(re_) == bool(ra):
        issues.append("rate_exposure: exactly one of rate_exposure and rate_absence is required")
    rate_type = None
    balance = None
    if re_:
        balance = labelled_value(re_["facility_balance"], "value_text", "balance of", "rate_exposure.facility_balance", issues, pages)
        rb = re_["rate_basis"]
        if on_page(rb, "rate_exposure.rate_basis", issues, pages):
            low = rb["quote"].lower()
            said = "FLOATING" if "floating" in low else ("FIXED" if "fixed" in low else None)
            if said is None:
                issues.append("rate_exposure.rate_basis: the quote states neither a floating nor a fixed rate")
            elif rb["rate_type"] != said:
                issues.append(f"rate_exposure.rate_basis: rate_type {rb['rate_type']} contradicts the quote")
            elif said == "FLOATING" and rb["reference_rate"] not in rb["quote"]:
                issues.append("rate_exposure.rate_basis: reference_rate does not occur in the quote")
            else:
                rate_type = said
        labelled_value(re_["spread"], "bps_text", "spread", "rate_exposure.spread", issues, pages)
        labelled_value(re_["floor"], "bps_text", "floor", "rate_exposure.floor", issues, pages)
    total_debt = None
    for key, path in (("ebitda", "earnings.ebitda"), ("interest", "earnings.interest"), ("fcf", "earnings.fcf"),
                      ("total_debt", "earnings.total_debt")):
        value = row_value(sub["earnings"][key], key, path, issues, pages)
        if key == "total_debt":
            total_debt = value
    # Cross-check (LEAD ruling 9): the one facility cannot exceed total debt; only when both values parse.
    if balance is not None and total_debt is not None and balance > total_debt:
        issues.append(f"rate_exposure.facility_balance: value_text {re_['facility_balance']['value_text']} "
                      f"exceeds total debt {sub['earnings']['total_debt']['value_text']}")
    fx = sub["fx"]
    row_value(fx["fx_cash_effect"], "fx_cash_effect", "fx.fx_cash_effect", issues, pages)
    dc, da = fx.get("debt_currency"), fx.get("debt_currency_absence")
    if bool(dc) == bool(da):
        issues.append("fx.debt_currency: exactly one of debt_currency and debt_currency_absence is required")
    elif dc:
        code_value(dc, "fx.debt_currency", issues, pages)  # a code other than the reporting currency is valid input
    fe, fa = fx.get("foreign_ebitda_share"), fx.get("operating_fx_absence")
    if bool(fe) == bool(fa):
        issues.append("fx.foreign_ebitda_share: exactly one of foreign_ebitda_share and operating_fx_absence is required")
    elif fe:
        if on_page(fe, "fx.foreign_ebitda_share", issues, pages):
            pt = fe["percent_text"]
            if not NUM_RE.match(pt) or not token_once(pt, fe["quote"]) or not (D(0) <= D(pt) <= 100):
                issues.append(f"fx.foreign_ebitda_share: percent_text {pt} does not occur in the quote")
    hr, ha = sub.get("hedge_ratio"), sub.get("hedge_absence")
    if bool(hr) == bool(ha):
        issues.append("hedge_ratio: exactly one of hedge_ratio and hedge_absence is required")
    elif hr:
        digit_free("hedge_ratio.rationale", hr["rationale"], issues)
        ok = re.match(r"^[0-9]{1,3}(?:\.[0-9]{1,2})?$", hr["percent_text"])
        if not ok or not (D(0) <= D(hr["percent_text"]) <= 100):
            issues.append("hedge_ratio: percent must be at least 0 and at most 100")
    for key in ("rate_absence", "debt_currency_absence", "operating_fx_absence", "hedge_absence"):
        a = sub.get(key) or fx.get(key)
        if a:
            digit_free(f"{key}.reason", a["reason"], issues)
            digit_free(f"{key}.follow_up", a["follow_up"], issues)
    rs = sub["rate_shocks_bp"]
    if not (1 <= len(rs) <= MAX_RATE_SHOCKS):
        issues.append(f"rate_shocks_bp: between 1 and {MAX_RATE_SHOCKS} shocks are required")
    rv = []
    for i, t in enumerate(rs):
        if not re.match(r"^[0-9]{1,4}$", t) or not (RATE_BP_RANGE[0] <= int(t) <= RATE_BP_RANGE[1]):
            issues.append(f"rate_shocks_bp[{i}]: shock must be a whole number of basis points from {RATE_BP_RANGE[0]} to {RATE_BP_RANGE[1]}")
        else:
            rv.append(int(t))
    if len(rv) == len(rs) and rv != sorted(set(rv)):
        issues.append("rate_shocks_bp: shocks must be strictly increasing")
    fs = sub["fx_shocks_percent"]
    if not (1 <= len(fs) <= MAX_FX_SHOCKS):
        issues.append(f"fx_shocks_percent: between 1 and {MAX_FX_SHOCKS} shocks are required")
    fv = []
    for i, t in enumerate(fs):
        if not re.match(r"^[0-9]{1,2}$", t) or not (FX_PCT_RANGE[0] <= int(t) <= FX_PCT_RANGE[1]):
            issues.append(f"fx_shocks_percent[{i}]: shock must be a whole percent from {FX_PCT_RANGE[0]} to {FX_PCT_RANGE[1]}")
        else:
            fv.append(int(t))
    if len(fv) == len(fs) and fv != sorted(set(fv)):
        issues.append("fx_shocks_percent: shocks must be strictly increasing")
    digit_free("shock_rationale", sub["shock_rationale"], issues)
    sections = [x["section"] for x in sub["assessments"]]
    for i, x in enumerate(sub["assessments"]):
        p = f"assessments[{i}]"
        if x["section"] not in SECTIONS:
            issues.append(f"{p}: section {x['section']} is not one of {', '.join(SECTIONS)}")
        elif sections.count(x["section"]) > 1:
            issues.append(f"{p}: section {x['section']} appears more than once")
        if x["category"] not in CATEGORIES:
            issues.append(f"{p}: category {x['category']} is not allowed")
        digit_free(f"{p}.text", x["text"], issues)
        if PROHIBITED_RE.search(x["text"]):
            issues.append(f"{p}.text: text carries a prohibited conclusion")
        if (x["category"] == "Insufficient Information") != bool(x.get("limitation")):
            issues.append(f"{p}: limitation is required for Insufficient Information and only for it")
        if x["category"] == "Documentary Fact" and not x["basis"]:
            issues.append(f"{p}: a Documentary Fact needs at least one basis quote")
        for j, b in enumerate(x["basis"]):
            on_page(b, f"{p}.basis[{j}]", issues, pages)
    for s in SECTIONS:
        if s not in sections:
            issues.append(f"assessments: section {s} is missing")
    digit_free("summary.text", sub["summary"]["text"], issues)
    if PROHIBITED_RE.search(sub["summary"]["text"]):
        issues.append("summary.text: text carries a prohibited conclusion")
    return issues


def refs_of(sub):
    """Every quote reference of a literal, in order of appearance."""
    out = [sub["reporting_currency"]]
    if sub.get("rate_exposure"):
        r = sub["rate_exposure"]
        out += [r["facility_balance"], r["rate_basis"], r["spread"], r["floor"]]
    out += [sub["earnings"][k] for k in ("ebitda", "interest", "fcf", "total_debt")]
    fx = sub["fx"]
    out.append(fx["fx_cash_effect"])
    if fx.get("debt_currency"):
        out.append(fx["debt_currency"])
    if fx.get("foreign_ebitda_share"):
        out.append(fx["foreign_ebitda_share"])
    for x in sub["assessments"]:
        out += x["basis"]
    return out


def cited_pages(sub):
    seen = []
    for ref in refs_of(sub):
        k = (ref["source_id"], ref["locator"])
        if k not in seen:
            seen.append(k)
    return seen


ABSENCE_ISSUE = "Absence claim without a recorded search"  # live/tools.py UNBACKED_ABSENCE
UNREAD_ISSUE = "Cited page not read through read_pages"  # live/tools.py UNREAD_PAGE


def absence_paths(sub):
    out = []
    for key in ("rate_absence", "hedge_absence"):
        if sub.get(key):
            out.append(key)
    for key in ("debt_currency_absence", "operating_fx_absence"):
        if sub["fx"].get(key):
            out.append(f"fx.{key}")
    return out


def tool_rule_issues(sub, read, searched):
    """The core RULES(text, seen) result in ToolRules order: the absence rule, then unread citations in the
    product's sorted (source_id, locator) order (live/tools.py unread_citation_issues)."""
    out = [ABSENCE_ISSUE] if absence_paths(sub) and not searched else []
    out += [f"{UNREAD_ISSUE}: {s} {loc}" for s, loc in sorted(cited_pages(sub)) if (s, loc) not in read]
    return out


# --- literal submissions ---------------------------------------------------------------------------------------
def row(locator, text, key, value):
    return {**q(locator, text), "value_text": value}


def earnings():
    return {"ebitda": row("page:2", Q_ROW_EBITDA, "ebitda", "30.0"),
            "interest": row("page:3", Q_ROW_INTEREST, "interest", "5.00"),
            "fcf": row("page:3", Q_ROW_FCF, "fcf", "9.00"),
            "total_debt": row("page:4", Q_ROW_DEBT, "total_debt", "50.00")}


ASSESS_RATE = (
    "The term loan is the only debt and its coupon floats on the reference rate, so every upward move passes "
    "straight into cash interest; the shocks tested leave interest cover well inside what the earnings can carry."
)
ASSESS_FX = (
    "The statements report no foreign-currency cash movements and no currency translation, and the only debt is "
    "stated in the reporting currency; the split of earnings by currency is not stated, so an operating currency "
    "effect cannot be sized."
)
ASSESS_HEDGE = "The sources do not state whether any hedging instrument exists, so every shock effect is shown before any hedge."
SUMMARY_POS = (
    "The credit's measurable macro sensitivity is to the reference rate, because all of the debt floats; "
    "currency sensitivity is nil on the debt and unsized on earnings, and the hedge position is not disclosed."
)
SHOCK_RATIONALE = (
    "Parallel upward moves of increasing size in the reference rate; a downward move is not tested because no "
    "source states the reference rate level against its floor; the currency moves are the foreign currency "
    "strengthening against the reporting currency."
)


def assessments_positive():
    return [
        {"section": "interest_rate", "category": "Analyst Interpretation", "text": ASSESS_RATE,
         "basis": [q("page:5", Q_RATE), q("page:5", Q_NO_OTHER_DEBT)], "limitation": None},
        {"section": "fx", "category": "Analyst Interpretation", "text": ASSESS_FX,
         "basis": [q("page:1", Q_FX_NONE), q("page:1", Q_TRANSLATION), q("page:5", Q_DEBT_CCY)], "limitation": None},
        {"section": "hedging", "category": "Insufficient Information", "text": ASSESS_HEDGE, "basis": [],
         "limitation": "No source in the pack states any hedging instrument or hedge ratio"},
    ]


def literal_positive():
    return {
        "reporting_currency": {**q("page:1", Q_CCY), "code_text": "USD"},
        "rate_exposure": {
            "facility_balance": {**q("page:5", Q_BALANCE), "value_text": "50"},
            "rate_basis": {**q("page:5", Q_RATE), "rate_type": "FLOATING", "reference_rate": "SOFR"},
            "spread": {**q("page:5", Q_SPREAD), "bps_text": "0"},
            "floor": {**q("page:5", Q_FLOOR), "bps_text": "0"},
        },
        "rate_absence": None,
        "earnings": earnings(),
        "fx": {
            "fx_cash_effect": row("page:3", Q_ROW_FX, "fx_cash_effect", "0"),
            "debt_currency": {**q("page:5", Q_DEBT_CCY), "code_text": "USD"},
            "debt_currency_absence": None,
            "foreign_ebitda_share": None,
            "operating_fx_absence": {
                "reason": "No source in the pack states the split of revenue, costs or earnings by currency",
                "follow_up": "Supply the segment or currency disclosure of the issuer",
            },
        },
        "hedge_ratio": None,
        "hedge_absence": {
            "reason": "No source in the pack states a hedging instrument or a hedge ratio",
            "follow_up": "Supply the hedging policy or derivative schedule of the issuer",
        },
        "rate_shocks_bp": ["100", "200"],
        "fx_shocks_percent": ["10"],
        "shock_rationale": SHOCK_RATIONALE,
        "assessments": assessments_positive(),
        "summary": {"text": SUMMARY_POS},
    }


def literal_gap():
    s = literal_positive()
    s["rate_exposure"] = None
    s["rate_absence"] = {
        "reason": "The pack holds no facility schedule, so the rate terms of the debt are not stated",
        "follow_up": "Supply the complete facility and classification schedule",
    }
    s["fx"]["debt_currency"] = None
    s["fx"]["debt_currency_absence"] = {
        "reason": "The pack holds no facility schedule, so the currency of the debt is not stated",
        "follow_up": "Supply the complete facility and classification schedule",
    }
    s["assessments"] = [
        {"section": "interest_rate", "category": "Insufficient Information",
         "text": "The rate terms of the debt are not stated, so the rate sensitivity cannot be assessed from this pack.",
         "basis": [], "limitation": "The pack holds no facility schedule"},
        {"section": "fx", "category": "Insufficient Information",
         "text": "The currency of the debt is not stated, so only the reported cash movements can be read.",
         "basis": [q("page:1", Q_FX_NONE)], "limitation": "The pack holds no facility schedule"},
        {"section": "hedging", "category": "Insufficient Information", "text": ASSESS_HEDGE, "basis": [],
         "limitation": "No source in the pack states any hedging instrument or hedge ratio"},
    ]
    s["summary"] = {"text": "Without the facility schedule neither the rate sensitivity nor the currency of the debt can be assessed."}
    return s


LITERALS = {"positive": literal_positive(), "gap_no_facility_schedule": literal_gap()}
for _case, _lit in LITERALS.items():
    _iss = check_submission(_lit, PAGES_OF[_case])
    assert not _iss, (_case, _iss)


# --- composer (pure Decimal) -------------------------------------------------------------------------------
# A derived value is ("known", Decimal) | ("missing", reason) | ("not_applicable", reason).
def K(x):
    return ("known", x)


def MISS(why):
    return ("missing", why)


def NA(why):
    return ("not_applicable", why)


def ratio(num, den, why_zero):
    """num / den over derived values; missing propagates, a zero denominator is not applicable."""
    for v in (num, den):
        if v[0] == "missing":
            return v
    if den[0] == "not_applicable" or num[0] == "not_applicable":
        return NA("an input is not applicable")
    if den[1] == 0:
        return NA(why_zero)
    return K(num[1] / den[1])


def comb(a, b, fn):
    """fn over two derived values; the first value that is not known (in argument order) propagates."""
    for v in (a, b):
        if v[0] != "known":
            return v
    return K(fn(a[1], b[1]))


def maybe(value, why):
    return K(value) if value is not None else MISS(why)


def derive(inp):
    """inp keys (Decimal | None unless stated): total_debt, facility_balance, rate_type (str|None), floor_bp,
    ebitda, interest, fcf, hedge (fraction|None), rate_shocks (list of bp), debt_foreign (True|False|None),
    foreign_ebitda_share (fraction|None), fx_shocks (list of fractions). Returns exact 38-digit intermediates."""

    def run():
        o = {}
        debt = maybe(inp.get("total_debt"), "total debt not stated")
        ebitda = maybe(inp.get("ebitda"), "EBITDA not stated")
        interest = maybe(inp.get("interest"), "cash interest not stated")
        fcf = maybe(inp.get("fcf"), "free cash flow not stated")
        bal, rt = inp.get("facility_balance"), inp.get("rate_type")
        if bal is None or rt is None:
            floating = MISS("the facility rate terms are not stated")
        else:
            floating = K(bal if rt == "FLOATING" else D(0))
        o["floating"] = floating
        o["floating_share"] = ratio(floating, debt, "total debt is zero")
        o["cov_base"] = ratio(ebitda, interest, "cash interest is zero")
        o["lev_base"] = ratio(debt, ebitda, "EBITDA is zero")
        floor, hedge = inp.get("floor_bp"), inp.get("hedge")
        o["hedge"] = maybe(hedge, "no hedge ratio is stated")
        o["floating_after_hedge"] = comb(floating, o["hedge"], lambda f, h: f * (1 - h))
        o["rate"] = []
        for k in inp.get("rate_shocks", []):
            r = {"shock_bp": K(k)}
            if floating[0] != "known":
                gross = floating
            elif floating[1] == 0:
                gross = K(D(0))  # nothing floats: a known zero, whatever the floor
            elif floor is None:
                gross = MISS("the floor of the facility is not stated")
            elif floor != 0:
                gross = MISS("the reference rate level is not stated, so a floor above zero may bind")
            else:
                gross = K(floating[1] * k / 10000)
            r["gross"] = gross
            r["net"] = comb(gross, o["hedge"], lambda g, h: g * (1 - h))
            r["interest_after"] = comb(gross, interest, lambda g, i: i + g)
            r["cov_after"] = ratio(ebitda, r["interest_after"], "interest after the shock is zero")
            r["cov_change"] = comb(r["cov_after"], o["cov_base"], lambda a, b: a - b)
            r["fcf_after"] = comb(gross, fcf, lambda g, f: f - g)
            r["share_of_ebitda"] = ratio(gross, ebitda, "EBITDA is zero")
            o["rate"].append(r)
        df = inp.get("debt_foreign")
        if df is None or bal is None:
            foreign_debt = MISS("the currency of the debt is not stated")
        else:
            foreign_debt = K(bal if df else D(0))
        o["foreign_debt"] = foreign_debt
        o["foreign_debt_share"] = ratio(foreign_debt, debt, "total debt is zero")
        fes = inp.get("foreign_ebitda_share")
        o["fx"] = []
        for m in inp.get("fx_shocks", []):
            r = {"shock": K(m)}
            r["debt_change"] = comb(foreign_debt, K(m), lambda f, mm: f * mm)
            r["debt_after"] = comb(r["debt_change"], debt, lambda c, d: d + c)
            if fes is None:
                r["ebitda_change"] = MISS("the share of EBITDA earned in other currencies is not stated")
            else:
                r["ebitda_change"] = comb(ebitda, K(m), lambda e, mm: e * fes * mm)
            r["ebitda_after"] = comb(r["ebitda_change"], ebitda, lambda c, e: e + c)
            r["lev_after"] = ratio(r["debt_after"], r["ebitda_after"], "EBITDA after the shock is zero")
            o["fx"].append(r)
        return o

    return with_ctx(run)


def stored(v):
    """JSON form of a derived value."""
    if v[0] == "known":
        return {"state": "known", "amount": dstr(v[1])}
    return {"state": v[0], "reason": v[1]}


def stored_all(d):
    out = {}
    for k, v in d.items():
        if isinstance(v, tuple):
            out[k] = stored(v)
        elif k in ("rate", "fx"):
            out[k] = [{kk: stored(vv) for kk, vv in r.items()} for r in v]
    return out


def inputs_of(sub):
    ex = sub["earnings"]
    inp = {"total_debt": row_decimal(ex["total_debt"]["value_text"]), "ebitda": row_decimal(ex["ebitda"]["value_text"]),
           "interest": row_decimal(ex["interest"]["value_text"]), "fcf": row_decimal(ex["fcf"]["value_text"])}
    re_ = sub.get("rate_exposure")
    if re_:
        inp["facility_balance"] = D(re_["facility_balance"]["value_text"])
        inp["rate_type"] = re_["rate_basis"]["rate_type"]
        inp["floor_bp"] = D(re_["floor"]["bps_text"])
    inp["hedge"] = D(sub["hedge_ratio"]["percent_text"]) / 100 if sub.get("hedge_ratio") else None
    inp["rate_shocks"] = [D(t) for t in sub["rate_shocks_bp"]]
    fx = sub["fx"]
    if fx.get("debt_currency"):
        inp["debt_foreign"] = fx["debt_currency"]["code_text"] != sub["reporting_currency"]["code_text"]
    if fx.get("foreign_ebitda_share"):
        inp["foreign_ebitda_share"] = D(fx["foreign_ebitda_share"]["percent_text"]) / 100
    inp["fx_shocks"] = [D(t) / 100 for t in sub["fx_shocks_percent"]]
    return inp


# --- facts and tables ----------------------------------------------------------------------------------------
PER_FLOW = "FY 2025: 2025-01-01 to 2025-12-31"
PER_BAL = "Balance at 2025-12-31"
PER_RUN = "Run as of 2026-01-10"
PER_SHOCK = "FY 2025 base with a shock"


def trace(cites):
    out = []
    for c in cites:
        k = [c["source_id"], c["locator"]]
        if k not in out:
            out.append(k)
    return out


def N(amount, unit, decimals, cites=(), vc="calculated", calc=None, formula=None, per=PER_SHOCK):
    return {"kind": "num", "per": per, "amount": dstr(amount), "unit": unit, "decimals": decimals,
            "cites": trace(cites), "vc": vc, "calc": calc, "formula": formula}


def T(text, cites=(), vc=None):
    return {"kind": "text", "text": text, "cites": trace(cites), "vc": vc}


def G(reason, unit=None, status="missing", cites=()):
    return {"kind": "gap", "reason": reason, "unit": unit, "status": status, "cites": trace(cites)}


def fact(tid, rid, field, label, c, ccy):
    f = {"fact_id": f"{tid}.{rid}.{field}", "column": label, "period": None, "amount": None, "unit": None,
         "currency": None, "scale": "1",
         "decimals": None, "text": None, "shown": None, "status": "known", "cites": c["cites"],
         "value_class": c.get("vc"), "calculation_id": None, "formula": None, "limitation": None}
    if c["kind"] == "num":
        f.update(amount=c["amount"], period=c["per"], unit=c["unit"], decimals=c["decimals"], calculation_id=c["calc"],
                 formula=c["formula"], shown=spell(D(c["amount"]), c["unit"], c["decimals"]))
        if c["unit"] == "MILLIONS":
            f.update(currency=ccy, scale=MILLIONS_SCALE)
    elif c["kind"] == "text":
        f.update(text=c["text"], shown=c["text"])
    else:
        f.update(unit=c["unit"], status=c["status"], limitation=c["reason"], value_class=None,
                 shown="∅ G#" if c["status"] == "missing" else "∅ G# n.m.")
        if c["unit"] == "MILLIONS":
            f.update(currency=ccy, scale=MILLIONS_SCALE)
    return f


def table(tid, title, cols, rows, row_header="Item", ccy=None):
    out = []
    for rid, label, cells in rows:
        assert len(cells) == len(cols), (tid, rid)
        out.append({"row_id": rid, "label": label,
                    "facts": [fact(tid, rid, fld, lab, c, ccy) for (fld, lab), c in zip(cols, cells)]})
    return {"table_id": tid, "title": title, "row_header": row_header,
            "columns": [{"field": f, "label": lab} for f, lab in cols], "rows": out}


def cell(v, unit, decimals, cites, calc, formula, per=PER_SHOCK):
    """A derived value as a cell: known -> calculated number; missing -> gap; not_applicable -> n.m. gap."""
    if v[0] == "known":
        return N(v[1], unit, decimals, cites, calc=calc, formula=formula, per=per)
    return G(("Not calculable: " if v[0] == "missing" else "Not meaningful: ") + v[1], unit, v[0])




ORD = ("first", "second", "third")


def compose_case(case, sub, d):
    """Tables, claims and own limitations of one case from the literal and its derive() result."""
    ex, fx = sub["earnings"], sub["fx"]
    re_ = sub.get("rate_exposure")
    rate_cites = [re_["facility_balance"], re_["rate_basis"], re_["floor"]] if re_ else []
    ccy_cite = [sub["reporting_currency"]]
    debt_cite, ebitda_cite, int_cite, fcf_cite = [ex["total_debt"]], [ex["ebitda"]], [ex["interest"]], [ex["fcf"]]
    dc = [fx["debt_currency"]] if fx.get("debt_currency") else []
    fb = [re_["facility_balance"]] if re_ else []
    NO_RATE = "the pack holds no facility rate terms"
    NO_DEBT_CCY = "the pack holds no statement of the currency of the debt"

    def src(text, cites):
        return T(text, cites)

    tables = []
    ccy = sub["reporting_currency"]["code_text"]  # the currency every MILLIONS fact carries (the quoted reporting currency)

    def tbl(*args, **kw):
        return table(*args, ccy=ccy, **kw)

    # T2F.1 sourced operands
    t1 = [
        ("r01", "Reporting currency", [T(sub["reporting_currency"]["code_text"], ccy_cite), src("Financial statements header", ccy_cite)]),
        ("r02", "Total debt", [N(row_decimal(ex["total_debt"]["value_text"]), "MILLIONS", 2, debt_cite, "source", per=PER_BAL),
                               src("Balance sheet, FY column", debt_cite)]),
        ("r03", "Term loan balance",
         [N(D(re_["facility_balance"]["value_text"]), "MILLIONS", 2, [re_["facility_balance"]], "source", per=PER_BAL),
          src("Facility schedule, closing balance", [re_["facility_balance"]])] if re_ else
         [G(f"Not stated: {NO_RATE}", "MILLIONS"), G(f"Not stated: {NO_RATE}")]),
        ("r04", "Rate basis",
         [T(f"{'Floating' if re_['rate_basis']['rate_type'] == 'FLOATING' else 'Fixed'} rate, {re_['rate_basis']['reference_rate']} reference rate",
            [re_["rate_basis"]]), src("Facility schedule", [re_["rate_basis"]])] if re_ else
         [G(f"Not stated: {NO_RATE}"), G(f"Not stated: {NO_RATE}")]),
        ("r05", "Spread",
         [N(D(re_["spread"]["bps_text"]), "basis_points", None, [re_["spread"]], "source", per=PER_BAL),
          src("Facility schedule", [re_["spread"]])] if re_ else
         [G(f"Not stated: {NO_RATE}", "basis_points"), G(f"Not stated: {NO_RATE}")]),
        ("r06", "Floor",
         [N(D(re_["floor"]["bps_text"]), "basis_points", None, [re_["floor"]], "source", per=PER_BAL),
          src("Facility schedule", [re_["floor"]])] if re_ else
         [G(f"Not stated: {NO_RATE}", "basis_points"), G(f"Not stated: {NO_RATE}")]),
        ("r07", "Reported EBITDA", [N(row_decimal(ex["ebitda"]["value_text"]), "MILLIONS", 2, ebitda_cite, "source", per=PER_FLOW),
                                    src("Income statement, FY column", ebitda_cite)]),
        ("r08", "Cash interest paid", [N(row_decimal(ex["interest"]["value_text"]), "MILLIONS", 2, int_cite, "source", per=PER_FLOW),
                                       src("Cash flow statement, FY column", int_cite)]),
        ("r09", "Levered free cash flow", [N(row_decimal(ex["fcf"]["value_text"]), "MILLIONS", 2, fcf_cite, "source", per=PER_FLOW),
                                           src("Cash flow statement, FY column", fcf_cite)]),
        ("r10", "FX effect on cash", [N(row_decimal(fx["fx_cash_effect"]["value_text"]), "MILLIONS", 2, [fx["fx_cash_effect"]], "source", per=PER_FLOW),
                                      src("Cash flow statement, FY column", [fx["fx_cash_effect"]])]),
        ("r11", "Currency of the debt",
         [T(fx["debt_currency"]["code_text"], dc), src("Facility schedule header", dc)] if dc else
         [G(f"Not stated: {NO_DEBT_CCY}"), G(f"Not stated: {NO_DEBT_CCY}")]),
        ("r12", "Share of EBITDA earned in other currencies",
         [N(D(fx["foreign_ebitda_share"]["percent_text"]) / 100, "PERCENT", 1, [fx["foreign_ebitda_share"]], "source", per=PER_FLOW),
          src("Source statement", [fx["foreign_ebitda_share"]])] if fx.get("foreign_ebitda_share") else
         [G("Not stated: no source gives the split of earnings by currency", "PERCENT"),
          G("Not stated: no source gives the split of earnings by currency")]),
    ]
    tables.append(tbl("T2F.1", "Sourced operands", [("value", "Value"), ("basis", "Basis")], t1, "Operand"))

    # T2F.2 baseline
    t2 = [
        ("r01", "Floating-rate debt", [cell(d["floating"], "MILLIONS", 2, rate_cites[:2], "cp2e.floating", "facility balance if the rate is floating, else zero", PER_BAL),
                                       T("Closing balance of a floating-rate facility")]),
        ("r02", "Floating-rate debt share of total debt", [cell(d["floating_share"], "PERCENT", 1, rate_cites[:2] + debt_cite, "cp2e.floating_share", "floating-rate debt / total debt", PER_BAL),
                                                          T("Share of total debt")]),
        ("r03", "Interest coverage", [cell(d["cov_base"], "MULTIPLE", 2, ebitda_cite + int_cite, "cp2e.cov_base", "EBITDA / cash interest paid", PER_FLOW),
                                      T("Reported EBITDA over cash interest, FY 2025")]),
        ("r04", "Total leverage", [cell(d["lev_base"], "MULTIPLE", 2, debt_cite + ebitda_cite, "cp2e.lev_base", "total debt / EBITDA", PER_FLOW),
                                   T("Total debt over reported EBITDA, FY 2025")]),
        ("r05", "Foreign-currency debt", [cell(d["foreign_debt"], "MILLIONS", 2, fb + dc + ccy_cite, "cp2e.foreign_debt", "term loan balance if its currency differs from the reporting currency, else zero", PER_BAL),
                                          T("Debt denominated in a currency other than the reporting currency")]),
        ("r06", "Foreign-currency debt share of total debt", [cell(d["foreign_debt_share"], "PERCENT", 1, dc + ccy_cite + debt_cite, "cp2e.foreign_debt_share", "foreign-currency debt / total debt", PER_BAL),
                                                             T("Share of total debt")]),
    ]
    tables.append(tbl("T2F.2", "Baseline exposure", [("value", "Value"), ("convention", "Convention")], t2, "Measure"))

    # T2F.3 interest rate shocks
    cols3 = [("shock", "Rate shock"), ("gross", "Added annual interest before hedges"), ("net", "Added annual interest after hedges"),
             ("interest_after", "Cash interest after the shock"), ("cov_after", "Interest coverage after the shock"),
             ("cov_change", "Change in interest coverage"), ("fcf_after", "Free cash flow after the shock"),
             ("share", "Added interest as share of EBITDA")]
    t3 = []
    for i, r in enumerate(d["rate"]):
        n = f"r{i + 1:02d}"
        shock = N(r["shock_bp"][1], "basis_points", None, (), "analyst_judgment", per=PER_RUN)
        t3.append((n, f"Reference rate up, {ORD[i]} shock", [
            shock,
            cell(r["gross"], "MILLIONS", 2, rate_cites, f"cp2e.rate{i + 1}.gross", "floating-rate debt x shock / 10000", PER_SHOCK),
            cell(r["net"], "MILLIONS", 2, rate_cites, f"cp2e.rate{i + 1}.net", "added interest before hedges x (1 - hedge ratio)", PER_SHOCK),
            cell(r["interest_after"], "MILLIONS", 2, rate_cites + int_cite, f"cp2e.rate{i + 1}.interest_after", "cash interest + added interest before hedges", PER_SHOCK),
            cell(r["cov_after"], "MULTIPLE", 2, rate_cites + int_cite + ebitda_cite, f"cp2e.rate{i + 1}.cov_after", "EBITDA / cash interest after the shock", PER_SHOCK),
            cell(r["cov_change"], "MULTIPLE", 2, rate_cites + int_cite + ebitda_cite, f"cp2e.rate{i + 1}.cov_change", "coverage after the shock - coverage before", PER_SHOCK),
            cell(r["fcf_after"], "MILLIONS", 2, rate_cites + fcf_cite, f"cp2e.rate{i + 1}.fcf_after", "free cash flow - added interest before hedges", PER_SHOCK),
            cell(r["share_of_ebitda"], "PERCENT", 1, rate_cites + ebitda_cite, f"cp2e.rate{i + 1}.share", "added interest before hedges / EBITDA", PER_SHOCK),
        ]))
    tables.append(tbl("T2F.3", "Interest rate shock", cols3, t3, "Shock"))

    # T2F.4 currency shocks
    cols4 = [("shock", "Currency move"), ("debt_change", "Change in debt"), ("debt_after", "Total debt after the move"),
             ("ebitda_change", "Change in EBITDA"), ("lev_after", "Total leverage after the move")]
    fe = [fx["foreign_ebitda_share"]] if fx.get("foreign_ebitda_share") else []
    fc = fb + dc
    t4 = []
    for i, r in enumerate(d["fx"]):
        t4.append((f"r{i + 1:02d}", f"Foreign currency strengthens, {ORD[i]} move", [
            N(r["shock"][1], "PERCENT", 0, (), "analyst_judgment", per=PER_RUN),
            cell(r["debt_change"], "MILLIONS", 2, fc, f"cp2e.fx{i + 1}.debt_change", "foreign-currency debt x move", PER_SHOCK),
            cell(r["debt_after"], "MILLIONS", 2, fc + debt_cite, f"cp2e.fx{i + 1}.debt_after", "total debt + change in debt", PER_SHOCK),
            cell(r["ebitda_change"], "MILLIONS", 2, fe + ebitda_cite, f"cp2e.fx{i + 1}.ebitda_change", "EBITDA x share earned in other currencies x move", PER_SHOCK),
            cell(r["lev_after"], "MULTIPLE", 2, fc + debt_cite + fe + ebitda_cite, f"cp2e.fx{i + 1}.lev_after", "total debt after the move / EBITDA after the move", PER_SHOCK),
        ]))
    tables.append(tbl("T2F.4", "Currency shock", cols4, t4, "Shock"))

    # T2F.5 hedging
    hr = sub.get("hedge_ratio")
    t5 = [
        ("r01", "Hedge ratio (analyst assumption)",
         [N(D(hr["percent_text"]) / 100, "PERCENT", 0, (), "analyst_judgment", per=PER_RUN) if hr else G("Not stated: no hedge ratio is assumed or sourced", "PERCENT"),
          T("Share of floating-rate debt hedged")]),
        ("r02", "Floating-rate debt after hedges",
         [cell(d["floating_after_hedge"], "MILLIONS", 2, rate_cites[:2], "cp2e.floating_after_hedge", "floating-rate debt x (1 - hedge ratio)", PER_BAL),
          T("Unhedged floating-rate debt")]),
        ("r03", "Hedging instruments", [G("Not stated: no source states a hedging instrument"), T("Located in the sources")]),
    ]
    tables.append(tbl("T2F.5", "Hedging", [("value", "Value"), ("convention", "Convention")], t5, "Item"))

    # T2F.6 assessments
    t6 = []
    for i, x in enumerate(sub["assessments"], 1):
        t6.append((f"r{i:02d}", x["section"].replace("_", " ").capitalize(), [
            T(x["category"], x["basis"], "analyst_judgment"), T(x["text"], x["basis"], "analyst_judgment")]))
    t6.append((f"r{len(t6) + 1:02d}", "Shock basis", [T("Analyst Interpretation", (), "analyst_judgment"),
                                                       T(sub["shock_rationale"], (), "analyst_judgment")]))
    t6.append((f"r{len(t6) + 1:02d}", "Summary", [T("Analyst Interpretation", (), "analyst_judgment"),
                                                    T(sub["summary"]["text"], (), "analyst_judgment")]))
    tables.append(tbl("T2F.6", "Assessments", [("category", "Category"), ("assessment", "Assessment")], t6, "Section"))

    # T2F.7 missing inputs, T2F.8 evidence, T2F.9 limitations
    miss = []
    if sub.get("rate_absence"):
        miss.append(("Floating-rate debt, added interest and coverage after a rate shock", sub["rate_absence"]["reason"]))
    if fx.get("debt_currency_absence"):
        miss.append(("Foreign-currency debt and the debt effect of a currency shock", fx["debt_currency_absence"]["reason"]))
    if fx.get("operating_fx_absence"):
        miss.append(("Currency effect on EBITDA and on leverage", fx["operating_fx_absence"]["reason"]))
    if sub.get("hedge_absence"):
        miss.append(("Added interest after hedges", sub["hedge_absence"]["reason"]))
    t7 = [(f"r{i:02d}", aff, [T(aff), T(why)]) for i, (aff, why) in enumerate(miss, 1)] or \
        [("r01", "Missing inputs", [T("None"), T("No input is missing")])]
    tables.append(tbl("T2F.7", "Missing inputs", [("affected", "Not calculated"), ("reason", "Reason")], t7, "Input"))
    ev = [(f"r{i:02d}", f"{NAMES[sid]}, {loc}", [T(sid), T(loc)]) for i, (sid, loc) in enumerate(cited_pages(sub), 1)]
    tables.append(tbl("T2F.8", "Evidence", [("source", "Source"), ("locator", "Locator")], ev, "Page"))
    own = own_limitations(sub)
    tables.append(tbl("T2F.9", "Limitations", [("text", "Limitation")],
                        [(f"r{i:02d}", f"Limitation {i}", [T(t)]) for i, t in enumerate(own, 1)], "Limitation"))
    return tables, compose_claims(case, sub, d, tables), own


LIM_REMAINDER = ("The quoted facility is only part of total debt and the rate type of the remainder is not stated, "
                 "so the shock figures cover the quoted facility alone")


def remainder_applies(balance, total_debt):
    """LEAD ruling 9: a quoted balance below total debt leaves a remainder whose rate type no source states."""
    return balance < total_debt


def own_limitations(sub):
    out = ["Each shock is a static, parallel move applied once to the closing balances and the FY 2025 flows; no "
           "repricing date, no change in debt and no tax shield are modelled",
           "Interest income on the cash balance is not shocked, so the added interest is not offset by any higher "
           "income on cash"]
    if sub.get("rate_exposure"):
        out.append("The reference rate level is not in any source, so a floor of zero is treated as not binding for the "
                   "upward shocks and downward shocks are not tested")
        if remainder_applies(D(sub["rate_exposure"]["facility_balance"]["value_text"]),
                             row_decimal(sub["earnings"]["total_debt"]["value_text"])):
            out.append(LIM_REMAINDER)
    else:
        out.append("The facility rate terms are not stated, so the rate sensitivity is not calculated")
    if sub.get("hedge_absence"):
        out.append("Hedging is not disclosed, so every shock effect is shown before any hedge")
    else:
        out.append("The hedge ratio is an analyst assumption, not a source figure")
    if sub["fx"].get("operating_fx_absence"):
        out.append("The split of earnings by currency is not stated, so the currency effect on EBITDA and on leverage is not calculated")
    if sub["fx"].get("debt_currency"):
        out.append("The currency of the debt is read from the header of the facility schedule, which states the currency of its amounts; no denomination clause is cited")
    out.append("Macro drivers other than the reference rate and currency, such as demand, input costs and inflation, are "
               "not sourced and not assessed; the figures are unaudited FY 2025 statements")
    return out


def fid(tid, rid, field):
    return f"{tid}.{rid}.{field}"


def compose_claims(case, sub, d, tables):
    by_id = {f["fact_id"]: f for t in tables for r in t["rows"] for f in r["facts"]}
    claims = []

    def add(cid, text, refs):
        cites = []
        for r in refs:
            for c in by_id[r]["cites"]:
                if c not in cites:
                    cites.append(c)
        claims.append({"claim_id": cid, "text": text, "refs": refs, "cites": cites})

    def fig(ref):
        f = by_id[ref]
        return "{" + ref + "|" + figure_unit(f["unit"], f["currency"]) + "}"

    float_f, cov_f = fid("T2F.2", "r01", "value"), fid("T2F.2", "r03", "value")
    for i, r in enumerate(d["rate"]):
        n = f"r{i + 1:02d}"
        gross, cova = fid("T2F.3", n, "gross"), fid("T2F.3", n, "cov_after")
        if r["gross"][0] == "known":
            add(f"CP-2E-RATE-{i + 1:02d}",
                f"For the {ORD[i]} rate shock tested, the floating-rate debt of {fig(float_f)} adds "
                f"{fig(gross)} of annual cash interest before any hedge, which takes interest coverage from "
                f"{fig(cov_f)} to {fig(cova)}.", [float_f, gross, cov_f, cova])
        else:
            add(f"CP-2E-RATE-{i + 1:02d}",
                f"The effect of the {ORD[i]} rate shock is not calculated: [{gross}] needs the facility rate terms, "
                "which the pack does not state.", [gross])
    fdebt = fid("T2F.2", "r05", "value")
    if d["fx"]:
        r0 = d["fx"][0]
        dafter, ech = fid("T2F.4", "r01", "debt_after"), fid("T2F.4", "r01", "ebitda_change")
        if r0["debt_after"][0] == "known":
            add("CP-2E-FX-01",
                f"The debt in a foreign currency is {fig(fdebt)}, so the first currency move leaves total debt "
                f"at {fig(dafter)}; the effect on EBITDA is not calculated: [{ech}] needs the share of earnings "
                "in other currencies, which no source states.", [fdebt, dafter, ech])
        else:
            add("CP-2E-FX-01",
                f"The currency effect on the debt is not calculated: [{fdebt}] needs the currency of the debt, which the "
                "pack does not state.", [fdebt])
    if d["rate"]:
        net = fid("T2F.3", "r01", "net")
        if d["rate"][0]["net"][0] == "known":
            add("CP-2E-HEDGE-01",
                f"After the analyst hedge assumption the first rate shock adds {fig(net)} of annual cash interest.",
                [net])
        else:
            add("CP-2E-HEDGE-01",
                f"The effect of the first rate shock after hedges is not calculated: [{net}] needs a hedge ratio that no "
                "source states.", [net])
    claims.append({"claim_id": "CP-2E-VIEW-01", "text": sub["summary"]["text"], "refs": [], "cites": []})
    return claims


def claim_issues(claim, by_id):
    """Transcription of prose.issues for these claims: tokens resolve, figures need a known numeric fact with a
    citation or calculation id and an allowed unit, chips must name unsettled or non-numeric facts."""
    tok = re.compile(r"\{(?P<f>[A-Za-z0-9][A-Za-z0-9_.:-]*)(?:\|(?P<u>[^{}\[\]|]+))?\}|\[(?P<c>[A-Za-z0-9][A-Za-z0-9_.:-]*)\]")
    issues, rest, last = [], [], 0
    text = claim["text"]
    for m in tok.finditer(text):
        rest.append(text[last:m.start()])
        last = m.end()
        ref = m.group("f") or m.group("c")
        f = by_id.get(ref)
        if f is None:
            issues.append(f"Unresolved reference: {ref}")
            continue
        if m.group("f"):
            if f["status"] != "known":
                issues.append(f"Figure reference names a gap: {ref}")
            elif f["amount"] is None:
                issues.append(f"Figure reference needs a known numeric fact: {ref}")
            elif not f["cites"] and f["calculation_id"] is None:
                issues.append(f"Figure reference has no citation or calculation: {ref}")
            elif m.group("u") != figure_unit(f["unit"], f["currency"]):
                issues.append(f"Unit {m.group('u')} differs from the fact's unit {figure_unit(f['unit'], f['currency'])}: {ref}")
        elif f["status"] == "known" and f["amount"] is not None:
            issues.append(f"A numeric fact needs a figure reference: {ref}")
    rest.append(text[last:])
    return issues, "".join(rest)




def pack_rows(ids):
    return [(sid, NAMES[sid], "ready", LIMIT[sid]) for sid in ids]


def cp0_expected(pack, sub, run_id, plan_order, live_consumers, sha):
    facts = []

    def add(table_, row, key, value, cites=()):
        facts.append({"fact_id": f"{table_}.{row}.{key}", "text": value,
                      "cites": [[c["source_id"], c["locator"]] for c in cites]})

    add("T1", "run", "objective", sub["objective"])
    add("T1", "run", "issuer", ISSUER)
    add("T1", "run", "reporting_period", sub["reporting_period"])
    add("T1", "run", "identity_gate", "confirmed" if sub["issuer_confirmed"] else "blocked")
    by = {a["source_id"]: a for a in sub["sources"]}
    assert [p[0] for p in pack] == [a["source_id"] for a in sub["sources"]]
    for sid, name, status, lim in pack:
        a = by[sid]
        for key, value in (("family", a["document_family"]), ("entity", a["entity"] or "Unconfirmed"),
                           ("period", a["period"] or "Unconfirmed"), ("version_relationship", a["version_relationship"])):
            add("P3", sid, key, value, a["citations"])
        add("P5", sid, "preparation", f"complete; fidelity {a['fidelity']}; {lim or 'No mechanical limitation'}")
        add("T2", sid, "source", f"{name}; {status}; SHA-256 {sha[sid]}")
        add("T3", sid, "authority", a["authority"], a["citations"])
        for i, c in enumerate(a["citations"]):
            add("T6", sid, f"evidence_{i}", c["quote"], [c])
    assert sorted(c["module_id"] for c in sub["consumers"]) == sorted(live_consumers)
    commands = {}
    for c in sorted(sub["consumers"], key=lambda x: plan_order.index(x["module_id"])):
        m = c["module_id"]
        add("T4", m, "demand", c["evidence_demand"], c["citations"])
        add("T4", m, "readiness", c["readiness"])
        add("T4", m, "rationale", c["rationale"], c["citations"])
        add("T8", m, "candidate_command", "Run " + m)
        commands[m] = "Run " + m if c["readiness"] in ("READY", "READY_WITH_LIMITATIONS") else "DO NOT RUN"
        add("T8", m, "exact_command", commands[m])
        add("T8", m, "sources", ", ".join(c["source_ids"]) or "None")
        lims = list(c["limitations"])
        for sid, name, status, lim in pack:
            if sid in c["source_ids"]:
                if lim:
                    lims.append(lim)
                lims.extend(by[sid]["limitations"])
        lims.extend(g["description"] for g in sub["gaps"] if m in g["affected_modules"])
        add("T8", m, "limits", "; ".join(dict.fromkeys(lims)) or "None identified")
        add("T8", m, "upstream", f"CP-0 {run_id}; analytical dependencies checked separately")
    for g in sub["gaps"]:
        add("T5", g["gap_id"], "gap",
            f"{g['kind']}/{g['severity']}: {g['description']}; affects {', '.join(g['affected_modules'])}; {g['remediation']}",
            g["citations"])
    if not sub["gaps"]:
        add("T5", "review", "gaps", "No gaps identified by this supplied review")
    add("T7", "run", "preparation", "<<PreparedPack.content_hash(), bound at run time>>")
    add("T7", "run", "method", "deploy-v-r14")
    add("T7", "run", "assertion_scope", "SOURCE_SUFFICIENCY_ONLY; CP_MODEL_INPUT_CONTRACT_NOT_EVALUATED")
    limitations = dedupe(
        [lim for _, _, _, lim in pack if lim]
        + [t for a in sub["sources"] for t in a["limitations"]]
        + [t for c in sub["consumers"] for t in c["limitations"]]
        + [g["description"] for g in sub["gaps"]]
        + [SYNTH]
    )
    return {"status": "restricted", "why": "own limitations are non-empty (readiness.py:518-531; execution.py:451-457)",
            "live_consumers": live_consumers, "plan_order": plan_order, "exact_commands": commands,
            "limitations": limitations, "facts": facts}


def meth_plan(requested):
    cat = {m["module_id"]: m for m in METH}
    order = [m["module_id"] for m in METH]
    selected = set(requested)
    pending = list(selected)
    while pending:
        for dep in cat[pending.pop()]["required"]:
            if dep not in selected:
                selected.add(dep)
                pending.append(dep)
    remaining = {m: set(cat[m]["required"]) | (set(cat[m]["optional"]) & selected) for m in selected}
    out = []
    while remaining:
        ready = [m for m in order if m in remaining and not remaining[m]]
        assert ready
        for m in ready:
            out.append(m)
            del remaining[m]
            for r in remaining.values():
                r.discard(m)
    return out, cat



# --- CP-0 base literal and expected facts (transcription of readiness.py, checked against the S1 oracle) -------
S1P = S1E["positive"]
_s1_pack = pack_rows(("identity", "financial", "business"))
_s1_pos = cp0_expected(_s1_pack, S1S["positive"]["readiness_review"], "slice-snapshot-positive",
                       ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL"], ["CP-1", "CP-1A", "CP-2"],
                       {"identity": ID_SHA, "financial": FIN_SHA["positive"], "business": BUS["positive"]["sha256"]})
for _k in ("status", "why", "live_consumers", "plan_order", "exact_commands", "limitations", "facts"):
    assert _s1_pos[_k] == S1P["CP-0"][_k], f"CP-0 transcription differs from the S1 oracle at {_k}"

PLAN, CAT = meth_plan(["CP-2E"])
assert PLAN == ["CP-0", "CP-2E"], PLAN
assert CAT["CP-2E"]["required"] == ["CP-0"] and CAT["CP-2E"]["optional"] == [], CAT["CP-2E"]
assert CAT["CP-2E"]["aliases"] == ["CP-2F"]
CP2E_TABLES = CAT["CP-2E"]["table_ids"]
assert sorted(CP2E_TABLES) == sorted([f"T2G.{i}" for i in range(1, 9)] + [f"T2F.{i}" for i in range(1, 10)])
_other_ids = {t for m in METH if m["module_id"] != "CP-2E" for t in m["table_ids"]}
assert not (set(CP2E_TABLES) & _other_ids), "table id collision (D8)"
assert [m["module_id"] for m in METH if "CP-2E" in m["required"] + m["optional"]] == ["CP-5", "CP-6"]

RUNS = {"positive": "slice-cp2e-positive", "gap_no_facility_schedule": "slice-cp2e-gap-no-facility-schedule"}


def cite(case, locator, quote):
    assert norm(quote) in norm(PAGES_OF[case][locator]), (case, locator, quote)
    return {"source_id": SRC, "source_sha256": FIN_SHA[case], "locator": locator, "quote": quote}


def readiness_review(case):
    sub = copy.deepcopy(S1S["positive"]["readiness_review"])
    ident = sub["sources"][0]["citations"][0]
    fin = cite(case, "page:1", Q_CCY)
    sub["sources"] = sub["sources"][:2]
    sub["sources"][1]["citations"] = [fin]
    sub["objective"] = "Macro, FX and hedging sensitivity of the credit"
    sub["reporting_period"] = "Reported FY2025 flows and the December 31, 2025 balance sheet"
    if case == "positive":
        fac = cite(case, "page:5", Q_ONE_FACILITY)
        sub["consumers"] = [{
            "module_id": "CP-2E", "readiness": "READY_WITH_LIMITATIONS",
            "evidence_demand": "Located facility rate terms, the currency of the debt and the reported interest and EBITDA",
            "source_ids": ["financial"],
            "rationale": "The rate and currency sensitivity can run on the stated facility terms and statements, with source limitations.",
            "citations": [fac, fin], "missing_source": None, "limitations": [LIMIT_FIN],
        }]
        sub["gaps"] = []
        cites = [ident, fin, fac]
        text = "The located statements and facility schedule support a rate and currency sensitivity with limitations."
    else:
        sub["consumers"] = [{
            "module_id": "CP-2E", "readiness": "READY_WITH_LIMITATIONS",
            "evidence_demand": "Reported interest and EBITDA; the facility schedule is not available",
            "source_ids": ["financial"],
            "rationale": "The assessment can run on the statements and records the absence of the facility terms.",
            "citations": [fin], "missing_source": None, "limitations": [GAP_FACILITY],
        }]
        sub["gaps"] = [{
            "gap_id": "missing-facility-schedule", "kind": "source", "severity": "material",
            "description": GAP_FACILITY, "affected_modules": ["CP-2E"],
            "remediation": "Supply the complete facility and classification schedule", "citations": [],
        }]
        cites = [ident, fin]
        text = "The located statements support only the reported flows; no facility schedule is available."
    sub["analysis"] = [{"claim_id": "source-assessment", "text": text, "citations": cites, "limitation": LIMIT_FIN}]
    return sub


# --- refusal mutations ---------------------------------------------------------------------------------------
def setp(obj, path, value):
    cur = obj
    for key in path[:-1]:
        cur = cur[key]
    cur[path[-1]] = value


def mut(base, edits):
    s = copy.deepcopy(base)
    for path, value in edits:
        setp(s, path, value)
    return s


P_ = ["rate_exposure"]
MUTATIONS = [
    ("reporting_code_not_in_quote", [(["reporting_currency", "code_text"], "EUR")],
     "reporting_currency: code_text EUR does not occur in the quote"),
    ("source_outside_scope", [(["reporting_currency", "source_id"], "identity")],
     "reporting_currency: source identity is outside the CP-2E scope (financial)"),
    ("rate_exposure_and_absence", [(["rate_absence"], {"reason": "Not stated", "follow_up": "Supply it"})],
     "rate_exposure: exactly one of rate_exposure and rate_absence is required"),
    ("balance_not_in_quote", [(P_ + ["facility_balance", "value_text"], "55")],
     "rate_exposure.facility_balance: value_text 55 does not occur in the quote"),
    ("balance_not_labelled", [(P_ + ["facility_balance"], {**q("page:5", Q_FLOOR), "value_text": "0"})],
     "rate_exposure.facility_balance: value_text 0 is not labelled balance of in the quote"),
    ("rate_type_contradicts_quote", [(P_ + ["rate_basis", "rate_type"], "FIXED")],
     "rate_exposure.rate_basis: rate_type FIXED contradicts the quote"),
    ("rate_type_not_stated", [(P_ + ["rate_basis"], {**q("page:5", Q_SOFR_SPREAD), "rate_type": "FLOATING", "reference_rate": "SOFR"})],
     "rate_exposure.rate_basis: the quote states neither a floating nor a fixed rate"),
    ("reference_rate_not_in_quote", [(P_ + ["rate_basis", "reference_rate"], "EURIBOR")],
     "rate_exposure.rate_basis: reference_rate does not occur in the quote"),
    ("floor_not_in_quote", [(P_ + ["floor", "bps_text"], "25")],
     "rate_exposure.floor: bps_text 25 does not occur in the quote"),
    ("row_not_whole_line", [(["earnings", "ebitda", "quote"], Q_TWO_LINES)],
     "earnings.ebitda: quote is not a whole page line"),
    ("row_wrong_label", [(["earnings", "interest"], {**q("page:3", Q_ROW_FCF), "value_text": "9.00"})],
     "earnings.interest: the row is not Cash interest paid"),
    ("row_value_not_last", [(["earnings", "ebitda", "value_text"], "7.5")],
     "earnings.ebitda: value_text 7.5 is not the last value of the row"),
    ("quote_off_page", [(["earnings", "fcf", "locator"], "page:2")],
     "earnings.fcf: quote not found on financial page:2"),
    ("debt_currency_and_absence", [(["fx", "debt_currency_absence"], {"reason": "Not stated", "follow_up": "Supply it"})],
     "fx.debt_currency: exactly one of debt_currency and debt_currency_absence is required"),
    ("foreign_share_and_absence", [(["fx", "foreign_ebitda_share"], {**q("page:2", Q_ROW_PBT), "percent_text": "20"})],
     "fx.foreign_ebitda_share: exactly one of foreign_ebitda_share and operating_fx_absence is required"),
    ("hedge_ratio_and_absence", [(["hedge_ratio"], {"percent_text": "40", "rationale": "Assumed share of the floating debt that is hedged"})],
     "hedge_ratio: exactly one of hedge_ratio and hedge_absence is required"),
    ("hedge_ratio_out_of_range", [(["hedge_ratio"], {"percent_text": "101", "rationale": "Assumed share of the floating debt that is hedged"}),
                                  (["hedge_absence"], None)],
     "hedge_ratio: percent must be at least 0 and at most 100"),
    ("rate_shock_zero", [(["rate_shocks_bp"], ["0", "200"])],
     "rate_shocks_bp[0]: shock must be a whole number of basis points from 1 to 1000"),
    ("rate_shocks_not_increasing", [(["rate_shocks_bp"], ["200", "100"])],
     "rate_shocks_bp: shocks must be strictly increasing"),
    ("too_many_rate_shocks", [(["rate_shocks_bp"], ["100", "200", "300", "400"])],
     "rate_shocks_bp: between 1 and 3 shocks are required"),
    ("fx_shock_too_large", [(["fx_shocks_percent"], ["60"])],
     "fx_shocks_percent[0]: shock must be a whole percent from 1 to 50"),
    ("digit_in_text", [(["assessments", 0, "text"], "The term loan is the only debt and floats on 1 reference rate.")],
     "assessments[0].text: digits are not allowed"),
    ("prohibited_conclusion", [(["summary", "text"], "The credit looks weak, so downgrade it.")],
     "summary.text: text carries a prohibited conclusion"),
    ("insufficient_without_limitation", [(["assessments", 2, "limitation"], None)],
     "assessments[2]: limitation is required for Insufficient Information and only for it"),
    ("documentary_without_basis", [(["assessments", 0, "category"], "Documentary Fact"), (["assessments", 0, "basis"], [])],
     "assessments[0]: a Documentary Fact needs at least one basis quote"),
    ("section_missing", [(["assessments"], assessments_positive()[:2])],
     "assessments: section hedging is missing"),
    ("section_repeated", [(["assessments"], assessments_positive() + [assessments_positive()[0]])],
     "assessments[0]: section interest_rate appears more than once"),
]


def isolated_ok():
    """The share literal of foreign_share_and_absence is valid on its own: without the absence it raises nothing."""
    s = mut(LITERALS["positive"], [(["fx", "foreign_ebitda_share"], {**q("page:2", Q_ROW_PBT), "percent_text": "20"}),
                                   (["fx", "operating_fx_absence"], None)])
    assert not check_submission(s, PAGES_OF["positive"]), "foreign share literal is not valid in isolation"


isolated_ok()


def run_mutations():
    base = LITERALS["positive"]
    out = []
    for name, edits, expect in MUTATIONS:
        iss = check_submission(mut(base, edits), PAGES_OF["positive"])
        assert iss and iss[0] == expect, (name, iss)
        out.append({"id": name, "edits": [[".".join(str(x) for x in p), v] for p, v in edits],
                    "issue": expect, "all_issues": iss})
    return out


MUT_LIST = run_mutations()

# Hand-built page variant (LEAD ruling 9): the frozen pack states a balance equal to total debt, so no frozen-page
# payload can exceed it. The variant replaces one sentence of page:5 (closing balance 50 -> 55); its quote, the
# page text and the recomputed source hash are pinned; this literal sits outside the 27 frozen-page literals.
BAL_FROM, BAL_TO = Q_BALANCE, Q_BALANCE.replace("balance of 50.", "balance of 55.")
assert BAL_TO != BAL_FROM and FIN_PAGES["page:5"].count(BAL_FROM) == 1
_var_page5 = FIN_PAGES["page:5"].replace(BAL_FROM, BAL_TO)
VAR_PAGES = {**FIN_PAGES, "page:5": _var_page5}
VAR_SOURCE_SHA = page_sha([VAR_PAGES[k] for k in VAR_PAGES])
_var = copy.deepcopy(LITERALS["positive"])
_var["rate_exposure"]["facility_balance"] = {"source_id": SRC, "locator": "page:5", "quote": BAL_TO, "value_text": "55"}
BALANCE_ABOVE_DEBT = {
    "id": "balance_exceeds_total_debt",
    "page_locator": "page:5",
    "page_edit": {"from": BAL_FROM, "to": BAL_TO},
    "page_text_sha256": hashlib.sha256(_var_page5.encode("utf-8")).hexdigest(),
    "pack_source_sha256": VAR_SOURCE_SHA,
    "payload": _var,
    "issue": "rate_exposure.facility_balance: value_text 55 exceeds total debt 50.00",
}
_viss = check_submission(_var, VAR_PAGES)
assert _viss == [BALANCE_ABOVE_DEBT["issue"]], _viss
assert VAR_SOURCE_SHA != FIN_SHA["positive"] and "balance of 55" in _var_page5
# On the frozen page the same payload fails earlier: its quote is not on the frozen page (no cross-check issue).
assert check_submission(_var, FIN_PAGES)[0] == "rate_exposure.facility_balance: quote not found on financial page:5"

# Tool-use refusals (journaled rules; wording prefixes of live/tools.py UNREAD_PAGE and UNBACKED_ABSENCE).
_ALL_PAGES = [["financial", f"page:{i}"] for i in range(1, 6)]
TOOL_USE = [
    {"id": "unread_financial_page_3", "reads": [p for p in _ALL_PAGES if p[1] != "page:3"], "searches": 1,
     "issue": "Cited page not read through read_pages: financial page:3"},
    {"id": "unread_financial_page_5", "reads": [p for p in _ALL_PAGES if p[1] != "page:5"], "searches": 1,
     "issue": "Cited page not read through read_pages: financial page:5"},
    {"id": "absence_without_search", "reads": _ALL_PAGES, "searches": 0, "issue": ABSENCE_ISSUE},
]
_pos_pages = set(cited_pages(LITERALS["positive"]))
assert _pos_pages == {("financial", f"page:{i}") for i in range(1, 6)}, _pos_pages
for _t in TOOL_USE:
    _got = tool_rule_issues(LITERALS["positive"], {tuple(r) for r in _t["reads"]}, _t["searches"] > 0)
    assert _got == [_t["issue"]], (_t, _got)
assert not tool_rule_issues(LITERALS["positive"], _pos_pages, True)
_gap_pages = set(cited_pages(LITERALS["gap_no_facility_schedule"]))
assert _gap_pages == {("financial", f"page:{i}") for i in range(1, 5)}, _gap_pages

# Blocked case: attempt 0 and attempt 1 both invalid.
BLOCKED = {
    "attempt_0": {"edits": [["assessments.0.text", "The term loan is the only debt and floats on 1 reference rate."]],
                  "issue": "assessments[0].text: digits are not allowed"},
    "attempt_1": {"edits": [["rate_exposure.floor.bps_text", "25"]],
                  "issue": "rate_exposure.floor: bps_text 25 does not occur in the quote"},
}
for _a in ("attempt_0", "attempt_1"):
    _s = mut(LITERALS["positive"], [([int(x) if x.isdigit() else x for x in e[0].split(".")], e[1]) for e in BLOCKED[_a]["edits"]])
    assert check_submission(_s, PAGES_OF["positive"])[0] == BLOCKED[_a]["issue"], _a


# --- composer fixtures (derived values; no pack run) ----------------------------------------------------------
BASE_INP = inputs_of(LITERALS["positive"])


def fixture(inp, note):
    d = derive(inp)
    return {"inputs": {k: (dstr(v) if isinstance(v, Decimal) else ([dstr(x) for x in v] if isinstance(v, list) else v))
                       for k, v in inp.items()},
            "stored": stored_all(d), "note": note}


FIXTURES = {
    "fixture_hedged": fixture({**BASE_INP, "hedge": D("0.4")},
                              "hedge ratio 40 percent (test vector, an analyst assumption): net increase is 60 percent of the gross increase"),
    "fixture_floor_may_bind": fixture({**BASE_INP, "floor_bp": D(25)},
                                      "floor above zero with an unstated reference rate level: the effect of an upward shock is missing, never the gross amount"),
    "fixture_fixed_rate": fixture({**BASE_INP, "rate_type": "FIXED"},
                                  "fixed-rate facility: nothing floats, so the increase is a known zero and coverage is unchanged"),
    "fixture_zero_interest": fixture({**BASE_INP, "interest": D(0)},
                                     "no cash interest: baseline coverage not applicable; coverage after the shock is known"),
    "fixture_zero_ebitda": fixture({**BASE_INP, "ebitda": D(0)},
                                   "EBITDA zero: coverage is a known 0; leverage and the share of EBITDA are not applicable"),
    "fixture_foreign_debt": fixture({**BASE_INP, "debt_foreign": True, "foreign_ebitda_share": D("0.2")},
                                    "debt in another currency and 20 percent of EBITDA earned abroad (test vectors, not source figures): both effects known"),
    "fixture_partial_facility": fixture({**BASE_INP, "facility_balance": D(30)},
                                        "quoted facility 30 below total debt 50 (test vector, not a source figure): the shock figures cover the quoted facility alone, the floating share stays known (balance / total debt) and the own limitation below is added"),
    "fixture_no_rate_terms": fixture({k: v for k, v in BASE_INP.items() if k not in ("facility_balance", "rate_type", "floor_bp")},
                                     "no facility terms: floating debt, increases and coverage after the shock are missing; baselines known"),
}
_fx = FIXTURES
assert remainder_applies(D(30), BASE_INP["total_debt"]) and not remainder_applies(BASE_INP["facility_balance"], BASE_INP["total_debt"])
FIXTURES["fixture_partial_facility"]["own_limitation_added"] = LIM_REMAINDER
assert _fx["fixture_partial_facility"]["stored"]["floating"] == {"state": "known", "amount": "30"}
assert _fx["fixture_partial_facility"]["stored"]["floating_share"] == {"state": "known", "amount": "0.6"}
assert _fx["fixture_partial_facility"]["stored"]["rate"][0]["gross"] == {"state": "known", "amount": "0.3"}
assert _fx["fixture_partial_facility"]["stored"]["rate"][1]["gross"] == {"state": "known", "amount": "0.6"}
assert not any(LIM_REMAINDER == t for c in LITERALS for t in own_limitations(LITERALS[c]))  # frozen pack: balance equals total debt
assert _fx["fixture_hedged"]["stored"]["rate"][0]["net"]["amount"] == "0.3"
assert _fx["fixture_floor_may_bind"]["stored"]["rate"][0]["gross"]["state"] == "missing"
assert _fx["fixture_fixed_rate"]["stored"]["rate"][0]["gross"] == {"state": "known", "amount": "0"}
assert _fx["fixture_fixed_rate"]["stored"]["rate"][0]["cov_change"] == {"state": "known", "amount": "0"}
assert _fx["fixture_zero_interest"]["stored"]["cov_base"]["state"] == "not_applicable"
assert _fx["fixture_zero_interest"]["stored"]["rate"][0]["cov_after"]["amount"] == "60"
assert _fx["fixture_zero_ebitda"]["stored"]["cov_base"] == {"state": "known", "amount": "0"}
assert _fx["fixture_zero_ebitda"]["stored"]["lev_base"]["state"] == "not_applicable"
assert _fx["fixture_foreign_debt"]["stored"]["fx"][0]["debt_after"]["amount"] == "55"
assert _fx["fixture_foreign_debt"]["stored"]["fx"][0]["ebitda_change"]["amount"] == "0.6"
assert _fx["fixture_no_rate_terms"]["stored"]["floating"]["state"] == "missing"


# --- assembly ------------------------------------------------------------------------------------------------
def run_of(case):
    return {"run_id": RUNS[case], "issuer_id": ISSUER_ID, "issuer_name": ISSUER, "as_of": AS_OF,
            "method_version": "deploy-v-r14", "case_kind": "synthetic", "pathway": "credit_snapshot",
            "requested_modules": ["CP-2E"]}


def main():
    reviews = {c: readiness_review(c) for c in LITERALS}
    cp0 = {c: cp0_expected(pack_rows(("identity", "financial")), reviews[c], RUNS[c], PLAN, ["CP-2E"], sha_map(c))
           for c in LITERALS}
    cases = {}
    for c, lit in LITERALS.items():
        d = derive(inputs_of(lit))
        tables, claims, own = compose_case(c, lit, d)
        by_id = {f["fact_id"]: f for t in tables for r in t["rows"] for f in r["facts"]}
        scan = []
        for cl in claims:
            iss, literal = claim_issues(cl, by_id)
            assert not iss, (c, cl["claim_id"], iss)
            scan.append({"claim_id": cl["claim_id"], "literal_text_outside_references": literal})
            for ref in cl["refs"]:
                assert ref in by_id
        inherited = [t for t in cp0[c]["limitations"] if t not in own]
        cases[c] = {
            "run": run_of(c),
            "pack_sources": [{"source_id": "identity", "name": NAMES["identity"], "sha256": ID_SHA, "status": "ready"},
                             {"source_id": "financial", "name": NAMES["financial"], "sha256": FIN_SHA[c], "status": "ready",
                              "pages": list(PAGES_OF[c])}],
            "status": "restricted",
            "derived": stored_all(d),
            "missing_not_zero": [f["fact_id"] for f in by_id.values() if f["status"] == "missing"],
            "not_applicable": [f["fact_id"] for f in by_id.values() if f["status"] == "not_applicable"],
            "tables": tables,
            "claims": claims,
            "claim_literal_text": scan,
            "own_limitations": own,
            "inherited_limitations": inherited,
            "inherited_rule": "CP-0 head limitations then CP-0 inherited, de-duplicated, own removed (execution.py:345-366)",
            "module_inputs": ["prepared-pack", "CP-0", "macro-fx-submission"],
            "tool_use_required": {
                "read_pages_cover": [list(p) for p in cited_pages(lit)],
                "search_pack_min": 1,
                "read_inputs_calls": 0,
            },
        }
    pos = cases["positive"]["derived"]
    assert pos["floating"]["amount"] == "50" and pos["floating_share"]["amount"] == "1"
    assert pos["cov_base"]["amount"] == "6" and pos["lev_base"]["amount"].startswith("1.666666666666666666666666666666666666")
    assert [r["gross"]["amount"] for r in pos["rate"]] == ["0.5", "1"]
    assert pos["rate"][0]["cov_after"]["amount"].startswith("5.4545454545454545454545454545454545")
    assert pos["rate"][1]["cov_after"]["amount"] == "5"
    assert pos["rate"][0]["fcf_after"]["amount"] == "8.5" and pos["rate"][1]["fcf_after"]["amount"] == "8"
    assert pos["rate"][0]["net"]["state"] == "missing" and pos["fx"][0]["ebitda_change"]["state"] == "missing"
    assert pos["foreign_debt"] == {"state": "known", "amount": "0"}
    gap = cases["gap_no_facility_schedule"]["derived"]
    assert gap["floating"]["state"] == "missing" and gap["cov_base"]["amount"] == "6"
    assert gap["rate"][0]["gross"]["state"] == "missing" and gap["foreign_debt"]["state"] == "missing"

    # LEAD ruling 1: the positive operands equal the frozen CP-1 values for the same items (assertion only; no edge,
    # no runtime read). Sources: cases/financial/manifest.json (FY2025 observations; Q4 twelve-month derived units)
    # and the CP-1 ratios of the pinned S1 oracle (cases/snapshot/expected.json).
    ex_ = LITERALS["positive"]["earnings"]
    obs, ltm = FIN["fy2025_observations"], FIN["q4_ltm_derived_source_units"]
    assert row_decimal(ex_["ebitda"]["value_text"]) == D(obs["ebitda"]) == D("30")
    assert row_decimal(ex_["interest"]["value_text"]) == D(obs["cash_interest_paid"]) == D("5")
    assert row_decimal(ex_["fcf"]["value_text"]) == D(ltm["fcf"]) == D("9")
    assert row_decimal(ex_["total_debt"]["value_text"]) == D(ltm["total_debt"]) == D("50")
    cp1r = S1E["CP-1"]["ratios"]
    assert cp1r["interest_coverage_reported"][1:] == ["30/5", "x", "6.00x"] and cp1r["total_leverage_reported"][1:] == ["50/30", "x", "1.67x"]
    assert D(pos["cov_base"]["amount"]) == D(30) / D(5) and D(pos["lev_base"]["amount"]) == with_ctx(lambda: D(50) / D(30))
    assert show(D(pos["cov_base"]["amount"]), "multiple") == cp1r["interest_coverage_reported"][3]
    assert show(D(pos["lev_base"]["amount"]), "multiple") == cp1r["total_leverage_reported"][3]
    CP1_CROSS_CHECK = {
        "rule": "assertion only (LEAD ruling 1): no CP-1 edge, no runtime read; the two modules cannot disagree on the frozen pack",
        "operands": {
            "ebitda": {"cp2e": "30.0", "frozen": "cases/financial/manifest.json#fy2025_observations.ebitda = 30.0"},
            "cash_interest_paid": {"cp2e": "5.00", "frozen": "cases/financial/manifest.json#fy2025_observations.cash_interest_paid = 5.00"},
            "fcf": {"cp2e": "9.00", "frozen": "cases/financial/manifest.json#q4_ltm_derived_source_units.fcf = 9",
                    "basis": "twelve months to Q4 2025 equals FY 2025 in the frozen pack (metric_coordinate_rule)"},
            "total_debt": {"cp2e": "50.00", "frozen": "cases/financial/manifest.json#q4_ltm_derived_source_units.total_debt = 50",
                           "basis": "balance at 2025-12-31, equal to the Q4 twelve-month value (metric_coordinate_rule)"},
        },
        "ratios": {
            "T2F.2.r03.value": {"cp2e": "6.00x", "cp1": "cases/snapshot/expected.json#CP-1.ratios.interest_coverage_reported = 30/5 = 6.00x"},
            "T2F.2.r04.value": {"cp2e": "1.67x", "cp1": "cases/snapshot/expected.json#CP-1.ratios.total_leverage_reported = 50/30 = 1.67x"},
        },
        "no_frozen_cp1_head_file": "no CP-1 head file is frozen; the pinned S1 oracle is the CP-1 reference",
    }

    # H1 / ruling 3: every T2F table is bound (validate_bindings needs every restricted-module fact bound once);
    # T2F.1-6 to the evidence rail as bindings/cp5.py does for its non-limitation tables.
    LIMITATION_TABLES = ("T2F.7", "T2F.9")
    TABLE_TITLES = {t["table_id"]: t["title"] for t in cases["positive"]["tables"]}
    BINDINGS = [{"table_id": tid, "block_id": "limitations" if tid in LIMITATION_TABLES else "evidence",
                 "cell_slot": "cp2e-" + tid.lower().replace(".", "-"), "unit_class": "text", "label": TABLE_TITLES[tid]}
                for tid in (f"T2F.{i}" for i in range(1, 10))]
    for c in cases:
        cases[c]["module_tables"] = [
            {"table_id": t["table_id"], "title": t["title"], "row_header": t["row_header"], "columns": t["columns"],
             "rows": [{"row_id": r["row_id"], "label": r["label"], "fact_ids": [f["fact_id"] for f in r["facts"]]} for r in t["rows"]]}
            for t in cases[c]["tables"]]

    manifest = {
        "schema_version": "cp2e-owner-cases/1",
        "scope": "CP-2E macro, FX and hedging sensitivity owner inputs: a two-module run CP-0 then CP-2E over the frozen identity and financial sources (no new source, no CP-1 promotion)",
        "status": "DRAFT by owner-preparation task cp2e-owner, 2026-10-28; not executed",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "pins": {**PINS},
        "reuse": {"identity": "cases/financial/manifest.json source identity, bytes unchanged",
                  "financial": "cases/financial/manifest.json source financial, bytes unchanged (positive case)",
                  "financial_gap_variant": "pages page:1 to page:4 of the same source, bytes unchanged; page:5 (the facility schedule) dropped; source sha256 recomputed by the pack rule (gap case only)"},
        "no_new_source": "No synthetic source is added. The frozen financial source states the currency (USD), no FX cash movements, no currency translation, one floating-rate SOFR term loan (spread 0, floor 0 basis points) and the FY 2025 EBITDA, cash interest and free cash flow; it states no reference rate level, no revenue or earnings split by currency and no hedging instrument, which the oracle shows as missing, never 0",
        "run": {"requested_modules": ["CP-2E"], "plan_order": PLAN, "live_consumers_of_cp0": ["CP-2E"], "pathway": "credit_snapshot",
                "edges": {"required": CAT["CP-2E"]["required"], "optional": CAT["CP-2E"]["optional"], "aliases": CAT["CP-2E"]["aliases"]}},
        "step_scope": {"step": "macro_fx", "sources": ["financial"], "why": "every quote is a financial-source page; the identity source adds nothing the step cites"},
        "cases": [{"case_id": c, "run": run_of(c), "pack_sources": cases[c]["pack_sources"], "submission": f"submissions.json#{c}"}
                  for c in LITERALS],
        "table_ids": {"CP-2E": CP2E_TABLES, "used": [f"T2F.{i}" for i in range(1, 10)], "unused": [f"T2G.{i}" for i in range(1, 9)]},
    }
    submissions = {
        "schema_version": "cp2e-owner-submissions/1",
        "note": "Literal analyst submissions for the CP-2E step macro_fx. Every sourced operand is a verbatim quote: a statement row is quoted as a whole page line and value_text is its last value (the FY 2025 column); a sentence operand's value_text occurs once in its own quote after its label. The analyst supplies the shock sizes and the assessments (judgment) and no computed number. The pack_sha256 placeholder in readiness_review is bound at run time.",
        "readiness_review": reviews,
        "positive": LITERALS["positive"],
        "gap_no_facility_schedule": LITERALS["gap_no_facility_schedule"],
        "refusal_mutations": {"base": "positive", "entries": MUT_LIST},
        "blocked": BLOCKED,
        "tool_use_refusals": TOOL_USE,
        "hand_built_page_refusals": [BALANCE_ABOVE_DEBT],
    }
    expected = {
        "schema_version": "cp2e-owner-expected/1",
        "derivation": "Each value is an exact Decimal derivation from cited source facts (the quotes in submissions.json) by the conventions in 'arithmetic'; nothing is read from code under test. Gap cells are spelled with the product's gap spelling; G# is bound at run time.",
        "cell_notation": {
            "num": "amount is the exact stored Decimal string (38 significant digits, half-even, trailing zeros dropped); unit is the Fact unit; decimals is Fact.decimals; shown is the product spelling (display.format_value as cases/cpl10-owner): MILLIONS shows 2 places, MULTIPLE 2 places with x, PERCENT shows amount x 100 to `decimals` places with a percent sign, basis_points shows the exact amount and ' bp'; a negative number is parenthesised",
            "gap": "status missing -> shown '∅ G#'; status not_applicable -> shown '∅ G# n.m.'; G# is bound at run time",
            "currency_scale": "every fact with unit MILLIONS carries currency = the quoted reporting currency (USD) and scale 1000000 (as cases/cpl10-owner and CP-1's facts); a MULTIPLE, PERCENT or basis_points fact carries no currency and the default scale 1. A figure reference in a claim shows the unit report_view.figure_unit derives from the fact: MILLIONS in USD gives 'US$ m' (currency label + scale label), MULTIPLE 'x', PERCENT '%', basis_points 'bp'; without the currency the unit would read 'm' and prose.issues reports it",
            "value_class": "source (quoted operand), calculated (Python), analyst_judgment (shock sizes, hedge ratio, assessments); an analyst_judgment number has no citation or calculation id so a claim cannot reference it as a figure",
            "calculated_cites": "a calculated fact carries the page-level cites of its inputs in the order of its formula",
        },
        "arithmetic": {
            "decimal_context": "38 significant digits, ROUND_HALF_EVEN for division (as facility_fx arithmetic_context decimal-38-half-even); every output is derived from exact inputs; display rounding is half-up on the exact value",
            "operands": "FY 2025 column of the statements: EBITDA (page:2), cash interest paid, levered free cash flow, FX effect on cash (page:3); total debt at 2025-12-31 (page:4); term loan balance, rate type, reference rate, spread and floor (page:5)",
            "floating_debt": "term loan balance if the quoted rate type is floating, zero if fixed, missing when the rate terms are not stated",
            "rate_shock_gross": "floating debt x shock_bp / 10000 (annual, before hedges); computed only when the floor is quoted as zero (the reference rate level is in no source, so an upward move by k passes in full); a floor above zero or not stated makes it missing; a fixed-rate facility makes it a known zero; downward shocks are refused by the validator",
            "rate_shock_net": "gross x (1 - hedge ratio); missing without a hedge ratio",
            "interest_after": "cash interest paid + gross increase",
            "coverage": "EBITDA / cash interest; EBITDA / interest after the shock; change = after - before; a zero divisor is not_applicable, never infinity or 0",
            "fcf_after": "levered free cash flow - gross increase (no tax shield, no repricing date)",
            "share_of_ebitda": "gross increase / EBITDA; EBITDA zero is not_applicable",
            "leverage": "total debt / EBITDA",
            "foreign_debt": "term loan balance if the quoted currency of the debt differs from the quoted reporting currency, zero if equal, missing when the currency of the debt is not stated",
            "fx_shock": "the foreign currency strengthens by m percent against the reporting currency: change in debt = foreign-currency debt x m; change in EBITDA = EBITDA x share earned in other currencies x m (missing when the share is not stated); leverage after = (debt + change in debt) / (EBITDA + change in EBITDA), missing when either change is missing",
            "operand_bounds": "a sentence operand (facility balance, spread, floor) is accepted only as 1 to 3 digits with at most 4 decimals (NUM_RE, at most 999.9999), so a balance of 1000 or more cannot be quoted by this step; stated, not a source limit",
            "facility_balance_vs_total_debt": "validator rule (LEAD ruling 9): when the balance and total debt both parse, a balance above total debt is the issue 'rate_exposure.facility_balance: value_text <balance> exceeds total debt <total debt text>', raised after the earnings rows. A balance below total debt is valid: the shock figures cover the quoted facility alone, the floating share stays known (balance / total debt), and the own limitation 'fixture_partial_facility.own_limitation_added' names the remainder whose rate type is not stated. Equal is the frozen case",
            "missing_rule": "any missing operand makes each dependent value missing with its reason; nothing defaults to 0; a known zero (nothing floats, no foreign-currency debt, FX effect on cash 0) is a value",
        },
        "table_id_check": {
            "registered_for_CP-2E": CP2E_TABLES,
            "occurs_in_other_module_table_ids": [],
            "used": "T2F.1 to T2F.9 (the alias CP-2F depth)", "unused": "T2G.1 to T2G.8 stay registered and unproduced (open question in the lease)",
        },
        "cp1_cross_check": CP1_CROSS_CHECK,
        "cp0": cp0,
        "cases": cases,
        "fixtures": FIXTURES,
        "refusals": [{"id": m["id"], "issue": m["issue"]} for m in MUT_LIST],
        "hand_built_page_refusals": [{"id": BALANCE_ABOVE_DEBT["id"], "issue": BALANCE_ABOVE_DEBT["issue"],
                                      "rule": "outside the 27 frozen-page literals: a hand-built variant of page:5 (closing balance 55) with its own page and pack sha256, in submissions.json#hand_built_page_refusals"}],
        "tool_use_refusals": [{"id": t["id"], "issue": t["issue"]} for t in TOOL_USE],
        "tamper": {
            "case": "positive (closed run: CP-0 and CP-2E settled, receipt sealed)",
            "target_fact": "T2F.3.r01.cov_after",
            "from": {"amount": "5.4545454545454545454545454545454545455", "shown": "5.45x"},
            "to": {"amount": "6", "shown": "6.00x"},
            "why_this_fact": "the first-shock coverage after hedges lives only in the result Module (the table cell holds the fact id); it is the one fact cp2e.probe's rebuild over the journaled payload contradicts; every other fact, table, claim and limitation stays unchanged",
            "recipe": [
                "1. Copy the closed positive store directory (blobs, snapshots, current, audit) to a scratch path.",
                "2. Load the CP-2E head's result Module; replace only the amount of fact T2F.3.r01.cov_after (5.4545454545454545454545454545454545455 shown 5.45x becomes 6 shown 6.00x); leave every other fact, table, claim and limitation unchanged.",
                "3. Serialise the forged Module as Execution._store does (model_dump_json); its sha256 R2 must equal Module.content_hash(); write blobs/R2.",
                "4. Build a new ExecutionSnapshot equal to the current one with the CP-2E Attempt.result_sha256 and Head.result_sha256 set to R2 (status, inputs and commands unchanged, so head_of(forged Module) equals the Head) and the same parent; write snapshots/<its sha256>.json and rewrite current to that digest.",
                "5. In the retained receipt: set the CP-2E SettledHead.result_sha256 to R2; set receipt.snapshot_sha256 and the CP-2E settling OwnerSubmission.snapshot_after_sha256 to the new digest; delete audit/submissions/<old record hash> and write the edited OwnerSubmission as audit/submissions/<its content_hash> (model_dump_json bytes); rewrite audit/receipt.sha256 with the forged receipt's content_hash (the audit file travels under its new hash).",
            ],
            "expect": {
                "passes": "everything upstream of the probe: audit inventory, blob and snapshot hashes, ancestor walk, head_of equality, begin and publication records, call and read replay, journaled-step replay (the payload and step are untouched)",
                "refuses": "cp2e.probe raises WorkflowError('identity_mismatch'); verify_owner_run_receipt raises identity_mismatch",
                "test_asserts": "on the forged copy, _verify_audit and every check before _PROBES pass (owner_workflow.py:802, :80); then cp2e.probe raises identity_mismatch. A test asserting identity_mismatch alone would never show that the probe was reached.",
            },
            "step_output_edit": "an edited CP-2E step output is caught by the store's own blob hash check, not by the probe's output comparison (recorded limitation)",
        },
        "negative_cases": {
            "blocked_cp2e": {"attempt_0_issue": BLOCKED["attempt_0"]["issue"], "attempt_1_issue": BLOCKED["attempt_1"]["issue"],
                             "result": "attempt 0 invalid, re-begun as attempt 1 (repair_of set), attempt 1 invalid: module blocked, no head"},
            "begin_refused_cp0_blocked": "CP-0 blocked or stale refuses begin of CP-2E (edge_rule block, no attempt consumed); built on a clone with two invalid CP-0 attempts, no literal",
            "stale_binding": "a snapshot change between the last read_pages and the submit refuses stale_binding",
        },
        "tool_use": {
            "positive": "ok read_pages calls cover financial page:1 to page:5 before the submit; at least one ok search_pack (the absence objects); zero read_inputs; zero extract_statements",
            "gap_no_facility_schedule": "ok read_pages covers financial page:1 to page:4; at least one ok search_pack (rate_absence, debt_currency_absence, operating_fx_absence, hedge_absence)",
            "refused_calls": "extract_statements and read_inputs are refused not_permitted receipts for CP-2E",
        },
        "plan": {"requested": ["CP-2E"], "plan": PLAN, "alias": "plan(('CP-2F',)) equals it", "edge_rule_CP-2E_CP-0": "block",
                 "consumer_edges": {"CP-5": "restricted (fan-in, no core)", "CP-6": "restricted (optional; cp6_committee.py:112 never reads it)"}},
        "consumption": {
            "status": "OPEN",
            "completion": "CP-2E is not complete until a consumer reads it (PLAN.md:8: actual downstream consumption); docs/MODULES.csv row CP-2E stays open on consumption; no test of this lease claims it",
            "reason": "No consumer core reads CP-2E: cp6_committee.py:112-114 states CP-2E is never read whatever the run binds, and the frozen CP-3 lease lists it among the CP-6 optional inputs that are not read; CP-5 counts only after a D3 scope lease and has no core",
            "reader_pinned": {
                "function": "cp2e_reader(store, head)",
                "exposes": ["head sha256", "status", "floating-rate debt", "per rate shock: added interest before hedges, coverage after, state of the after-hedge value",
                            "foreign-currency debt", "hedge ratio or its absence", "own limitations"],
                "positive_values": {"floating": pos["floating"], "first_shock_gross": pos["rate"][0]["gross"],
                                    "first_shock_cov_after": pos["rate"][0]["cov_after"]},
            },
        },
        "render": {
            "pathway": "credit_snapshot (requested_modules overridden to CP-2E)",
            "d7_assignment": "CP-2E's assigned rendered deliverables for v1 are its module page (route #CP-2E, tables T2F.1 to T2F.9 as Module.tables layouts) and the evidence and limitations rails; no design reference assigns a macro/FX Front Page block, so none is added (LEAD ruling 3 / review M1)",
            "blocks": "no Front Page block and no pathway lists CP-2E",
            "module_page": {
                "route": "#CP-2E",
                "draws": "renderModule (src/deploy_vii/assets/app.js): claims, then one panel per Module.tables layout with each cell a fact button, then facts of undeclared tables; render.py serialises every non-rejected module",
                "layouts": "cases.<case>.module_tables: T2F.1 to T2F.9, each layout the table of cases.<case>.tables with fact_ids in row and column order (validate_tables: every fact of a laid-out table is referenced exactly once)",
                "probe": "acceptance 6: settle CP-2E, build the report view, and assert report.modules[CP-2E].tables ids = T2F.1..T2F.9 with rows and fact_ids equal to module_tables, claims equal to cases.<case>.claims, every fact shown as its 'shown' spelling; T2F.1 to T2F.6 and T2F.8 are bound to the Evidence rail and T2F.7 and T2F.9 to the Limitations rail (bound, not rendered there: the Evidence rail shows sources and the Limitations rail shows the module's own plus inherited limitations)",
            },
            "bindings": BINDINGS,
            "binding_rule": "validate_bindings (bindings/__init__.py) needs every fact of a restricted module bound exactly once, so all of T2F.1 to T2F.9 are bound; T2F.1 to T2F.6 and T2F.8 to the evidence rail (as bindings/cp5.py binds its non-limitation tables), T2F.7 and T2F.9 to limitations; unit_class text; no Front Page block is composed",
            "evidence rail": ["T2F.1", "T2F.2", "T2F.3", "T2F.4", "T2F.5", "T2F.6", "T2F.8"], "limitations rail": ["T2F.9", "T2F.7"],
            "slot_prefix": "cp2e-",
            "gap_cells": "shown '∅ G<n>' with n bound at run time",
        },
        "not_verified": [
            "no CP-2E core, validator or composer exists; no value was compared with product output",
            "CP-0 literal for a CP-2E-only run never settled by the product",
            "the G1-X owner-only seams for pack sources and rules, and the host scope mapping, are proposals",
            "the module page and rails were probed on a report view built from oracle facts (report_view.build and render data, HEAD copies), not on a settled run and not in a browser; whether a module page satisfies PLAN.md:8 is LEAD's D7 call",
            "display spelling of parenthesised negative multiples and of the percent decimals override follows display.py as transcribed by cases/cpl10-owner, not a render",
        ],
    }
    for name, obj in (("manifest.json", manifest), ("submissions.json", submissions), ("expected.json", expected)):
        (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
