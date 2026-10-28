"""Writes cases/cp3d-owner/{manifest,submissions,expected}.json (stdlib only).

Oracle for CP-3D (market implied risk). Independent transcription of the documented method
(work/lead/cp3d-owner-preparation/lease-draft.md): no product code is imported or run. It reads
only data files, each checked against a pinned sha256 before use: the frozen financial manifest,
the three S1 oracle files (the CP-0 base literal), methodology.json, and the frozen third-party
market quotation sheet, whose two pages are taken from cases/cp3-cp6-owner/manifest.json and
checked against the pinned source sha256 (the file itself is not pinned: another preparation owns it).

Every arithmetic value is an exact Decimal derivation with the conventions stated in
expected.json#arithmetic. Every checkable property of the literal inputs (quotes on their page,
digit-free text, value_text inside its quote, prohibited phrases, claim references) is asserted
here, so an inconsistent input fails the build.

Run from the repository root:  python3 -I cases/cp3d-owner/builder/build.py
"""

import copy
import hashlib
import json
import re
from datetime import date
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "cases" / "cp3d-owner"

PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    "cases/snapshot/expected.json": "d1aa1af9677cc4bd77b890261f0ceeca664acc72aac77f91da55cf36d7279baa",
    "src/deploy_vii/methodology.json": "1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6",
}
MARKET_FILE = "cases/cp3-cp6-owner/manifest.json"
MARKET_SHA = "c175d14bf4b1fd245d3c971bff6e9499a789aabc820cd340d0ea40e369f774b7"


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

# --- sources (bytes reused, hash-checked) --------------------------------------------------------
fin_src = {s["source_id"]: s for s in FIN["sources"]}
for _sid, _s in fin_src.items():
    assert page_sha([p["text"] for p in _s["pages"]]) == _s["sha256"], _sid
_mk = json.loads((ROOT / MARKET_FILE).read_text(encoding="utf-8"))["market_source"]
MARKET_PAGES = [(p["locator"], p["text"]) for p in _mk["pages"]]
assert page_sha([t for _, t in MARKET_PAGES]) == MARKET_SHA, "market source bytes differ from the pin"
MARKET_NAME = _mk["name"]
assert MARKET_NAME == "Third-party loan market quotation sheet" and _mk["status"] == "ready"
BUS = S1M["business_source"]  # used only by the CP-0 transcription self-check against S1
BUS_PAGES = BUS["positive"]["pages"]
assert page_sha([p["text"] for p in BUS_PAGES]) == BUS["positive"]["sha256"]

PAGES = {
    "identity": {p["locator"]: p["text"] for p in fin_src["identity"]["pages"]},
    "financial": {p["locator"]: p["text"] for p in fin_src["financial"]["pages"]},
    "business": {p["locator"]: p["text"] for p in BUS_PAGES},
    "market": dict(MARKET_PAGES),
}
SHA = {
    "identity": fin_src["identity"]["sha256"],
    "financial": fin_src["financial"]["sha256"],
    "business": BUS["positive"]["sha256"],
    "market": MARKET_SHA,
}
NAMES = {
    "identity": fin_src["identity"]["name"],
    "financial": fin_src["financial"]["name"],
    "business": BUS["common"]["name"],
    "market": MARKET_NAME,
}
LIMIT = {"identity": None, "financial": LIMIT_FIN, "business": None, "market": None}


def cite(sid, locator, quote):
    assert norm(quote) in norm(PAGES[sid][locator]), (sid, locator, quote)
    return {"source_id": sid, "source_sha256": SHA[sid], "locator": locator, "quote": quote}


def q(sid, locator, quote):
    assert norm(quote) in norm(PAGES[sid][locator]), (sid, locator, quote)
    return {"source_id": sid, "locator": locator, "quote": quote}


# Quotes used by the literals (each is a verbatim span of one page).
Q_BID = "Dealer quotation on January 9, 2026: bid 98.50 and offer 99.25, expressed as a percentage of par."
Q_TALK = "Dealers describe the indicative fair value of the Northbridge Term Loan as around 99.75."
Q_INSTRUMENT = (
    "Instrument: Northbridge Term Loan, the senior secured term loan of Northbridge Synthetic Group, "
    "with final maturity on December 31, 2029."
)
Q_MARGIN = "spread 0 basis points"
Q_SOFR = "SOFR reference rate"
Q_AMORT = "Mandatory annual amortisation is 0"
Q_FIN_MATURITY = "final maturity is December 31, 2029"
Q_FIN_INSTRUMENT = "There is exactly one debt facility: Northbridge Term Loan, facility_id term-loan."
Q_ONE_DEALER = "The quotation comes from one dealer."
Q_NO_TRADE = "No trade in the instrument was reported in the 30 days to January 9, 2026."
Q_TALK_NOTE = "This is talk and not a quotation or a trade."
Q_NO_RATING = "No rating agency has assigned a rating to the instrument."
GAP_MARKET = "No third-party market quotation source in the pack, so CP-3D market levels are absent"


# --- Decimal conventions -------------------------------------------------------------------------
def qz(x, places):
    return x.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def dstr(x):
    return None if x is None else format(x, "f")


def with_ctx(fn):
    with localcontext() as c:
        c.prec = 28
        c.rounding = ROUND_HALF_EVEN
        return fn()


MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
     "November", "December"], 1)}
DATE_RE = re.compile(r"^(" + "|".join(MONTHS) + r") ([1-9]|[12][0-9]|3[01]), ((?:19|20)[0-9]{2})$")
MON_SHORT = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def parse_date(text):
    m = DATE_RE.match(text)
    if not m:
        return None
    try:
        return date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    except ValueError:
        return None


def fmt_date(d):
    return f"{d.day} {MON_SHORT[d.month - 1]} {d.year}"


NUM_RE = re.compile(r"^[0-9]{1,3}(?:\.[0-9]{1,4})?$")


def token_once(value_text, quote):
    """value_text occurs exactly once in the quote as a whole numeric token."""
    return len(re.findall(r"(?<![0-9.])" + re.escape(value_text) + r"(?![0-9]|\.[0-9])", quote)) == 1


def spell(amount, unit, decimals):
    """Product spelling of a known numeric fact (display.py _number; report_view.fact_spelling)."""
    if unit == "decimal_fraction":
        places = decimals if decimals is not None else 1
        scaled = amount * 100
        body = f"{qz(scaled, places):,.{places}f}"
        return ("(" + body.lstrip("-") + ")" if scaled < 0 and qz(scaled, places) < 0 else body) + "%"
    suffix = {"basis_points": " bp", "years": " years", "days": " days"}[unit]
    return format(amount, "f") + suffix


# --- the validator (independent transcription of the lease's rules) -------------------------------
KINDS = ("bid", "offer", "indicative_talk")
ASPECTS = ("quote_quality", "trading_activity", "talk_versus_quote", "rating")
CATEGORIES = ("Documentary Fact", "Analyst Interpretation", "Insufficient Information")
PROHIBITED = ("buy", "sell", "overweight", "underweight", "recommend", "cheap", "undervalued",
              "overvalued", "outperform", "attractive")
PROHIBITED_RE = re.compile(r"\b(?:" + "|".join(PROHIBITED) + r")\b", re.I)
THIRD_PARTY = {"market"}  # CP-0 T3 authority third_party sources of the run's CP-0 literal


def digit_free(path, text, issues):
    if text is not None and any(ch.isnumeric() for ch in text):
        issues.append(f"{path}: digits are not allowed")


def on_page(ref, path, issues, pack_ids):
    sid, loc = ref["source_id"], ref["locator"]
    if sid not in pack_ids:
        issues.append(f"{path}: source {sid} is not in the pack")
        return False
    if loc not in PAGES[sid] or norm(ref["quote"]) not in norm(PAGES[sid][loc]):
        issues.append(f"{path}: quote not found on {sid} {loc}")
        return False
    return True


def check_submission(sub, pack_ids):
    """Issues of the validator, in rule order."""
    issues = []
    obs = sub["observations"]
    if bool(obs) == bool(sub.get("market_absence")):
        issues.append("observations: exactly one of observations and market_absence is required")
    kinds = [o["kind"] for o in obs]
    for k in dict.fromkeys(kinds):
        if kinds.count(k) > 1:
            issues.append(f"observations: kind {k} appears more than once")
    levels, dates = {}, {}
    for i, o in enumerate(obs):
        p = f"observations[{i}]"
        if o["kind"] not in KINDS:
            issues.append(f"{p}: kind {o['kind']} is not one of bid, offer, indicative_talk")
            continue
        if o["source_id"] in pack_ids and o["source_id"] not in THIRD_PARTY:
            issues.append(f"{p}: source {o['source_id']} is not a third_party source (CP-0 T3)")
            continue
        if not on_page(o, p, issues, pack_ids):
            continue
        if not NUM_RE.match(o["level_text"]):
            issues.append(f"{p}: level_text {o['level_text']} is not a decimal number")
            continue
        if not token_once(o["level_text"], o["quote"]):
            issues.append(f"{p}: level_text {o['level_text']} does not occur in the quote")
            continue
        label = rf"\b(?:bid|offer)\s+{re.escape(o['level_text'])}(?![0-9])"
        if o["kind"] == "indicative_talk":
            if re.search(label, norm(o["quote"]), re.I):
                issues.append(f"{p}: indicative_talk level_text {o['level_text']} is a bid or offer level in the quote")
                continue
        elif not re.search(rf"\b{o['kind']}\s+{re.escape(o['level_text'])}(?![0-9])", norm(o["quote"]), re.I):
            issues.append(f"{p}: {o['kind']} level_text {o['level_text']} is not labelled {o['kind']} in the quote")
            continue
        lv = Decimal(o["level_text"])
        if not (0 < lv <= 200):
            issues.append(f"{p}: level must be above 0 and at most 200")
            continue
        levels[o["kind"]] = lv
        at = o.get("as_of_text")
        if at is None:
            if o["kind"] != "indicative_talk":
                issues.append(f"{p}: {o['kind']} needs as_of_text")
        elif at not in o["quote"] or parse_date(at) is None:
            issues.append(f"{p}: as_of_text {at} does not occur in the quote")
        else:
            dates[o["kind"]] = parse_date(at)
    if "bid" in levels and "offer" in levels:
        if levels["bid"] > levels["offer"]:
            issues.append("observations: bid exceeds offer")
        if dates.get("bid") and dates.get("offer") and dates["bid"] != dates["offer"]:
            issues.append("observations: bid and offer have different dates")
    for key in ("market_absence", "recovery_absence"):
        a = sub.get(key)
        if a:
            digit_free(f"{key}.reason", a["reason"], issues)
            digit_free(f"{key}.follow_up", a["follow_up"], issues)
    inst = sub["instrument"]
    digit_free("instrument.name", inst["name"], issues)
    if on_page(inst["quote"], "instrument.quote", issues, pack_ids) and inst["name"] not in inst["quote"]["quote"]:
        issues.append("instrument: name does not occur in the quote")
    t = sub["terms"]
    mat = t["maturity"]
    qdate = dates.get("bid") or dates.get("offer")
    if bool(mat.get("date_text")) == bool(mat.get("absence")):
        issues.append("maturity: exactly one of date_text and absence is required")
    elif mat.get("date_text"):
        if on_page(mat["quote"], "maturity", issues, pack_ids):
            md = parse_date(mat["date_text"])
            if md is None or mat["date_text"] not in mat["quote"]["quote"]:
                issues.append(f"maturity: date_text {mat['date_text']} does not occur in the quote")
            elif qdate is not None and md <= qdate:
                issues.append("maturity: date is not after the quotation date")
    for key, label in (("margin", "bps_text"), ("amortisation", "value_text")):
        term = t[key]
        if bool(term.get(label)) == bool(term.get("absence")):
            issues.append(f"{key}: exactly one of {label} and absence is required")
        elif term.get(label):
            if on_page(term["quote"], key, issues, pack_ids):
                if not NUM_RE.match(term[label]) or not token_once(term[label], term["quote"]["quote"]):
                    issues.append(f"{key}: {label} {term[label]} does not occur in the quote")
                elif key == "amortisation" and Decimal(term[label]) != 0:
                    issues.append("amortisation: the simple margin convention requires zero amortisation")
    rr = t["reference_rate"]
    digit_free("reference_rate.name", rr["name"], issues)
    if on_page(rr["quote"], "reference_rate.quote", issues, pack_ids) and rr["name"] not in rr["quote"]["quote"]:
        issues.append("reference_rate: name does not occur in the quote")
    if bool(rr.get("level")) == bool(rr.get("absence")):
        issues.append("reference_rate: exactly one of level and absence is required")
    elif rr.get("level") and on_page(rr["level"]["quote"], "reference_rate.level.quote", issues, pack_ids):
        pt = rr["level"]["percent_text"]
        if not NUM_RE.match(pt) or not token_once(pt, rr["level"]["quote"]["quote"]):
            issues.append(f"reference_rate: level percent_text {pt} does not occur in the quote")
    if rr.get("absence"):
        digit_free("reference_rate.absence.reason", rr["absence"]["reason"], issues)
        digit_free("reference_rate.absence.follow_up", rr["absence"]["follow_up"], issues)
    rec, ra = sub.get("recovery"), sub.get("recovery_absence")
    if bool(rec) == bool(ra):
        issues.append("recovery: exactly one of recovery and recovery_absence is required")
    elif rec:
        digit_free("recovery.rationale", rec["rationale"], issues)
        ok = re.match(r"^[0-9]{1,3}(?:\.[0-9]{1,2})?$", rec["percent_text"])
        if not ok or not (Decimal("0") <= Decimal(rec["percent_text"]) < 100):
            issues.append("recovery: percent must be at least 0 and below 100")
    aspects = [x["aspect"] for x in sub["technicals"]]
    for i, x in enumerate(sub["technicals"]):
        p = f"technicals[{i}]"
        if x["aspect"] not in ASPECTS:
            issues.append(f"{p}: aspect {x['aspect']} is not one of {', '.join(ASPECTS)}")
        elif aspects.count(x["aspect"]) > 1:
            issues.append(f"{p}: aspect {x['aspect']} appears more than once")
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
            on_page(b, f"{p}.basis[{j}]", issues, pack_ids)
    digit_free("summary.text", sub["summary"]["text"], issues)
    if PROHIBITED_RE.search(sub["summary"]["text"]):
        issues.append("summary.text: text carries a prohibited conclusion")
    return issues


def cited_pages(sub):
    """Every (source_id, locator) the literal cites, in order of first appearance."""
    seen = []

    def add(ref):
        k = (ref["source_id"], ref["locator"])
        if k not in seen:
            seen.append(k)

    for o in sub["observations"]:
        add(o)
    add(sub["instrument"]["quote"])
    t = sub["terms"]
    for key in ("maturity", "margin", "amortisation"):
        if t[key].get("quote"):
            add(t[key]["quote"])
    add(t["reference_rate"]["quote"])
    if t["reference_rate"].get("level"):
        add(t["reference_rate"]["level"]["quote"])
    for x in sub["technicals"]:
        for b in x["basis"]:
            add(b)
    return seen


ABSENCE_ISSUE = "Absence claim without a recorded search"  # live/tools.py UNBACKED_ABSENCE
UNREAD_ISSUE = "Cited page not read through read_pages"  # live/tools.py UNREAD_PAGE


def absence_paths(sub):
    """Every absence object of a literal that claims a source does not state something (recovery_absence says
    only that the analyst did not assess it, so it is not one)."""
    out = []
    if sub.get("market_absence"):
        out.append("market_absence")
    for key in ("maturity", "margin", "amortisation", "reference_rate"):
        if sub["terms"][key].get("absence"):
            out.append(f"terms.{key}.absence")
    return out


def tool_rule_issues(sub, read, searched):
    """The core RULES(text, seen) result in ToolRules order: the absence rule, then unread citations in the
    product's sorted (source_id, locator) order (live/tools.py unread_citation_issues)."""
    out = [ABSENCE_ISSUE] if absence_paths(sub) and not searched else []
    out += [f"{UNREAD_ISSUE}: {s} {loc}" for s, loc in sorted(cited_pages(sub)) if (s, loc) not in read]
    return out


# --- literal submissions -----------------------------------------------------------------------------
def technicals_positive():
    return [
        {"aspect": "quote_quality", "category": "Analyst Interpretation",
         "text": "The observed level is one dealer quotation, so it indicates the market and is not a consensus level.",
         "basis": [q("market", "page:1", Q_ONE_DEALER)], "limitation": None},
        {"aspect": "trading_activity", "category": "Documentary Fact",
         "text": "The sheet reports no trade in the instrument in the period to the quotation date.",
         "basis": [q("market", "page:1", Q_NO_TRADE)], "limitation": None},
        {"aspect": "talk_versus_quote", "category": "Analyst Interpretation",
         "text": "Dealer talk is shown beside the quotation for context only; it is not a quotation or a trade and no calculation uses it.",
         "basis": [q("market", "page:2", Q_TALK_NOTE)], "limitation": None},
        {"aspect": "rating", "category": "Insufficient Information",
         "text": "No rating is available to compare with the market level.",
         "basis": [q("market", "page:2", Q_NO_RATING)],
         "limitation": "No rating agency has assigned a rating to the instrument"},
    ]


def base_terms(maturity_ref):
    return {
        "maturity": {"quote": maturity_ref[0], "date_text": "December 31, 2029", "absence": None},
        "margin": {"quote": q("financial", "page:5", Q_MARGIN), "bps_text": "0", "absence": None},
        "amortisation": {"quote": q("financial", "page:5", Q_AMORT), "value_text": "0", "absence": None},
        "reference_rate": {
            "name": "SOFR",
            "quote": q("financial", "page:5", Q_SOFR),
            "level": None,
            "absence": {
                "reason": "No reference rate level or forward curve appears in any source of the pack",
                "follow_up": "Supply a dated reference rate fixing or forward curve source",
            },
        },
    }


RECOVERY = {
    "percent_text": "70",
    "rationale": "Analyst assumption following the first-lien loan CDS convention; not a source figure and not a view on the recovery outcome",
}
SUMMARY_POS = (
    "On the observed quotation the loan is priced close to par, so the market-implied credit risk is low on a "
    "spread basis; the evidence is one dealer quotation, so the read is indicative and not a market consensus."
)


def literal_positive():
    mat = q("market", "page:1", Q_INSTRUMENT)
    return {
        "instrument": {"name": "Northbridge Term Loan", "quote": q("market", "page:1", Q_INSTRUMENT)},
        "observations": [
            {"kind": "bid", **q("market", "page:1", Q_BID), "level_text": "98.50", "as_of_text": "January 9, 2026"},
            {"kind": "offer", **q("market", "page:1", Q_BID), "level_text": "99.25", "as_of_text": "January 9, 2026"},
            {"kind": "indicative_talk", **q("market", "page:2", Q_TALK), "level_text": "99.75", "as_of_text": None},
        ],
        "market_absence": None,
        "terms": base_terms([mat]),
        "recovery": dict(RECOVERY),
        "recovery_absence": None,
        "technicals": technicals_positive(),
        "summary": {"text": SUMMARY_POS},
    }


def literal_gap_no_recovery():
    s = literal_positive()
    s["recovery"] = None
    s["recovery_absence"] = {
        "reason": "No recovery assumption was assessed for this run",
        "follow_up": "Supply an analyst recovery assumption for the instrument",
    }
    return s


def literal_gap_no_market():
    fin_mat = q("financial", "page:5", Q_FIN_MATURITY)
    s = {
        "instrument": {"name": "Northbridge Term Loan", "quote": q("financial", "page:5", Q_FIN_INSTRUMENT)},
        "observations": [],
        "market_absence": {
            "reason": "The pack holds no third-party market quotation source",
            "follow_up": "Supply a dated dealer quotation or trade record",
        },
        "terms": base_terms([fin_mat]),
        "recovery": dict(RECOVERY),
        "recovery_absence": None,
        "technicals": [
            {"aspect": "quote_quality", "category": "Insufficient Information",
             "text": "No market level is available to assess.", "basis": [],
             "limitation": "The pack holds no third-party market quotation source"},
        ],
        "summary": {"text": "No market level is available, so the market-implied credit risk cannot be assessed from this pack."},
    }
    s["terms"]["maturity"]["date_text"] = "December 31, 2029"
    return s


LITERALS = {
    "positive": literal_positive(),
    "gap_no_recovery": literal_gap_no_recovery(),
    "gap_no_market": literal_gap_no_market(),
}
PACK_IDS = {
    "positive": ("identity", "financial", "market"),
    "gap_no_recovery": ("identity", "financial", "market"),
    "gap_no_market": ("identity", "financial"),
}
for _case, _lit in LITERALS.items():
    _iss = check_submission(_lit, PACK_IDS[_case])
    assert not _iss, (_case, _iss)


# --- composer -----------------------------------------------------------------------------------------
def derive(inp):
    """Pure Decimal composer over validated numeric inputs. inp keys: bid, offer, talk, asof, maturity,
    margin_bp, amort_zero (bool|None), recovery (fraction|None), ref_level (fraction|None).
    Returns exact (unrounded, 28 digits) intermediates and the quantised stored outputs."""
    def run():
        d = {"missing": []}
        bid, offer, talk = inp.get("bid"), inp.get("offer"), inp.get("talk")
        d["bid"], d["offer"], d["talk"] = bid, offer, talk
        mid = (bid + offer) / 2 if bid is not None and offer is not None else None
        d["mid"] = mid
        d["width"] = (offer - bid) if mid is not None else None
        d["discount_mid_pts"] = (100 - mid) if mid is not None else None
        d["talk_less_mid_pts"] = (talk - mid) if (talk is not None and mid is not None) else None
        asof, mat = inp.get("asof"), inp.get("maturity")
        days = (mat - asof).days if (asof is not None and mat is not None) else None
        d["days"] = days
        years = Decimal(days) / Decimal(365) if days is not None else None
        d["years"] = years
        d["years_q"] = qz(years, 2) if years is not None else None
        margin = inp.get("margin_bp")
        dm_ok = margin is not None and inp.get("amort_zero") is True
        d["margin_bp"] = margin
        points = {"bid": bid, "mid": mid, "offer": offer}
        for name, p in points.items():
            disc = (100 - p) / years * 100 if (p is not None and years is not None) else None  # bp per annum
            d[f"disc_{name}"] = disc
            dm = margin + disc if (disc is not None and dm_ok) else None
            d[f"dm_{name}"] = dm
            r = inp.get("recovery")
            if dm is None or r is None:
                d[f"lam_{name}"] = d[f"pd_{name}"] = None
                d[f"pd_state_{name}"] = "missing"
            elif dm <= 0:
                d[f"lam_{name}"] = d[f"pd_{name}"] = None
                d[f"pd_state_{name}"] = "not_applicable"
            else:
                lam = dm / (1 - r)  # bp per annum
                d[f"lam_{name}"] = lam
                d[f"pd_{name}"] = 1 - (-(lam / 10000) * years).exp()
                d[f"pd_state_{name}"] = "known"
            lvl = inp.get("ref_level")
            d[f"yield_{name}"] = lvl + dm / 10000 if (lvl is not None and dm is not None) else None
        return d

    return with_ctx(run)


def stored(d):
    """Quantised stored values (strings) of a derive() result."""
    out = {}
    for k in ("bid", "offer", "talk", "mid", "width", "discount_mid_pts", "talk_less_mid_pts"):
        out[k] = dstr(d[k] / 100) if d[k] is not None else None  # fraction of par
    out["days"] = dstr(Decimal(d["days"])) if d["days"] is not None else None
    out["years"] = dstr(d["years_q"])
    out["margin_bp"] = dstr(d["margin_bp"])
    for n in ("bid", "mid", "offer"):
        out[f"disc_{n}"] = dstr(qz(d[f"disc_{n}"], 1)) if d[f"disc_{n}"] is not None else None
        out[f"dm_{n}"] = dstr(qz(d[f"dm_{n}"], 1)) if d[f"dm_{n}"] is not None else None
        out[f"lam_{n}"] = dstr(qz(d[f"lam_{n}"], 1)) if d[f"lam_{n}"] is not None else None
        out[f"pd_{n}"] = dstr(qz(d[f"pd_{n}"], 4)) if d[f"pd_{n}"] is not None else None
        out[f"pd_state_{n}"] = d[f"pd_state_{n}"]
        out[f"yield_{n}"] = dstr(qz(d[f"yield_{n}"], 4)) if d[f"yield_{n}"] is not None else None
    return out


def inputs_of(sub):
    obs = {o["kind"]: o for o in sub["observations"]}
    inp = {}
    for k in ("bid", "offer"):
        if k in obs:
            inp[k] = Decimal(obs[k]["level_text"])
    if "indicative_talk" in obs:
        inp["talk"] = Decimal(obs["indicative_talk"]["level_text"])
    for k in ("bid", "offer"):
        if k in obs:
            inp["asof"] = parse_date(obs[k]["as_of_text"])
    m = sub["terms"]["maturity"]
    inp["maturity"] = parse_date(m["date_text"]) if m.get("date_text") else None
    mg = sub["terms"]["margin"]
    inp["margin_bp"] = Decimal(mg["bps_text"]) if mg.get("bps_text") else None
    am = sub["terms"]["amortisation"]
    inp["amort_zero"] = (Decimal(am["value_text"]) == 0) if am.get("value_text") else None
    if sub.get("recovery"):
        inp["recovery"] = Decimal(sub["recovery"]["percent_text"]) / 100
    lvl = sub["terms"]["reference_rate"].get("level")
    inp["ref_level"] = Decimal(lvl["percent_text"]) / 100 if lvl else None
    return inp


# --- facts and tables -----------------------------------------------------------------------------------
def trace(cites):
    out = []
    for c in cites:
        k = [c["source_id"], c["locator"]]
        if k not in out:
            out.append(k)
    return out


PER_TERMS = "Facility terms in the financial source published 2026-01-10"
PER_RUN = "Run as of 2026-01-10"
_pub = re.search(r"Published ((?:" + "|".join(MONTHS) + r") [0-9]{1,2}, [0-9]{4})", PAGES["market"]["page:2"])
assert _pub and parse_date(_pub.group(1)) == date(2026, 1, 10)
PER_TALK = f"Commentary published {parse_date(_pub.group(1)).isoformat()}"


def N(amount, unit, decimals, cites=(), vc="calculated", calc=None, formula=None, per=None):
    return {"kind": "num", "per": per, "amount": amount, "unit": unit, "decimals": decimals, "cites": trace(cites),
            "vc": vc, "calc": calc, "formula": formula}


def T(text, cites=(), vc=None):
    return {"kind": "text", "text": text, "cites": trace(cites), "vc": vc}


def G(reason, unit=None, status="missing", cites=()):
    return {"kind": "gap", "reason": reason, "unit": unit, "status": status, "cites": trace(cites)}


def fact(tid, rid, field, label, c, per_q):
    f = {"fact_id": f"{tid}.{rid}.{field}", "column": label, "period": None, "amount": None, "unit": None, "decimals": None,
         "text": None, "shown": None, "status": "known", "cites": c["cites"], "value_class": c.get("vc"),
         "calculation_id": None, "formula": None, "limitation": None}
    if c["kind"] == "num":
        f.update(amount=c["amount"], period=c["per"] or per_q, unit=c["unit"], decimals=c["decimals"], calculation_id=c["calc"],
                 formula=c["formula"], shown=spell(Decimal(c["amount"]), c["unit"], c["decimals"]))
    elif c["kind"] == "text":
        f.update(text=c["text"], shown=c["text"])
    else:
        f.update(unit=c["unit"], status=c["status"], limitation=c["reason"], value_class=None,
                 shown="∅ G#" if c["status"] == "missing" else "∅ G# n.m.")
    return f


def table(tid, title, cols, rows, row_header="Item", per_q=PER_RUN):
    out = []
    for rid, label, cells in rows:
        assert len(cells) == len(cols), (tid, rid)
        out.append({"row_id": rid, "label": label,
                    "facts": [fact(tid, rid, fld, lab, c, per_q) for (fld, lab), c in zip(cols, cells)]})
    return {"table_id": tid, "title": title, "row_header": row_header,
            "columns": [{"field": f, "label": l} for f, l in cols], "rows": out}


def compose_case(case, sub, d):
    """Tables, claims, limitations of one case from the literal and its derive() result."""
    s = stored(d)
    _q = next((o["as_of_text"] for o in sub["observations"] if o.get("as_of_text")), None)
    per_q = f"Quotation of {parse_date(_q).isoformat()}" if _q else PER_RUN
    obs = {o["kind"]: o for o in sub["observations"]}
    c_obs = {k: [obs[k]] if k in obs else [] for k in KINDS}
    mk_absent = bool(sub.get("market_absence"))
    NO_MKT = "No market level: the pack holds no third-party market quotation source"

    def tbl(*args, **kw):
        return table(*args, per_q=per_q, **kw)

    def why(reason):
        """A gap reason; with no market source in the pack the reason is that, not the operand it hides."""
        return NO_MKT if mk_absent else reason

    CALC_NEEDS = {"years": why("Not calculable: needs a quotation date and a final maturity date")}
    MID_NEEDS = why("Not calculable: needs both an observed bid and an observed offer")

    def lvl(kind, label):
        if kind in obs:
            o = obs[kind]
            return N(s["talk" if kind == "indicative_talk" else kind], "decimal_fraction", 2, [o], vc="source",
                     per=PER_TALK if kind == "indicative_talk" else None)
        return G(NO_MKT if mk_absent else f"Not calculable: no {label} was submitted", "decimal_fraction")

    def basis_of(kind):
        if kind not in obs:
            return G(NO_MKT if mk_absent else "Not stated: no observation submitted", None)
        return T("Observed dealer quotation" if kind != "indicative_talk"
                 else "Indicative talk; not a quotation or a trade", [obs[kind]])

    def asof_of(kind):
        o = obs.get(kind)
        if o is None:
            return G(NO_MKT if mk_absent else "Not stated: no observation submitted")
        if o.get("as_of_text"):
            return T(fmt_date(parse_date(o["as_of_text"])), [o])
        return T("None stated", [o])

    def src_of(kind):
        o = obs.get(kind)
        return G(NO_MKT if mk_absent else "Not stated: no observation submitted") if o is None else \
            T(f"{NAMES[o['source_id']]}, {o['locator']}", [o])

    tables = []
    tables.append(tbl("T3E.1", "Market levels", [("level", "Level (% of par)"), ("as_of", "As of"),
                                                   ("basis", "Basis"), ("source", "Source")], [
        ("r01", "Dealer bid", [lvl("bid", "bid"), asof_of("bid"), basis_of("bid"), src_of("bid")]),
        ("r02", "Dealer offer", [lvl("offer", "offer"), asof_of("offer"), basis_of("offer"), src_of("offer")]),
        ("r03", "Indicative dealer talk", [lvl("indicative_talk", "talk"), asof_of("indicative_talk"),
                                            basis_of("indicative_talk"), src_of("indicative_talk")]),
    ], "Level"))

    bo = c_obs["bid"] + c_obs["offer"]
    mid_cites = bo

    def calc_or_gap(val, unit, dec, cites, calc, formula, need, per=None):
        return N(val, unit, dec, cites, calc=calc, formula=formula, per=per) if val is not None else G(need, unit)

    mat_cite = [sub["terms"]["maturity"]["quote"]] if sub["terms"]["maturity"].get("quote") else []
    cites_days = bo[:1] + mat_cite
    t2 = [
        ("r01", "Mid of bid and offer", [calc_or_gap(s["mid"], "decimal_fraction", 3, mid_cites, "cp3d.mid",
                                                     "(bid + offer) / 2", MID_NEEDS),
                                         T("(bid + offer) / 2")]),
        ("r02", "Bid-offer width", [calc_or_gap(s["width"], "decimal_fraction", 2, mid_cites, "cp3d.width",
                                                "offer - bid", MID_NEEDS), T("offer - bid")]),
        ("r03", "Discount to par at mid", [calc_or_gap(s["discount_mid_pts"], "decimal_fraction", 3, mid_cites,
                                                       "cp3d.discount_mid", "par - mid", MID_NEEDS),
                                           T("par - mid")]),
        ("r04", "Indicative talk less mid (context only, not used in any calculation)",
         [calc_or_gap(s["talk_less_mid_pts"], "decimal_fraction", 3, mid_cites + c_obs["indicative_talk"],
                      "cp3d.talk_less_mid", "talk - mid", why("Not calculable: needs an indicative talk level and a mid"),
                      per=f"{PER_TALK} and {per_q[0].lower()}{per_q[1:]}"),
          T("talk - mid")]),
        ("r05", "Days from quotation date to final maturity",
         [calc_or_gap(s["days"], "days", None, cites_days, "cp3d.days", "maturity date - quotation date",
                      CALC_NEEDS["years"]), T("Calendar days")]),
        ("r06", "Years to final maturity",
         [calc_or_gap(s["years"], "years", None, cites_days, "cp3d.years", "days / 365 (Act/365 Fixed, unrounded in later steps)",
                      CALC_NEEDS["years"]), T("Act/365 Fixed; shown to two places, later steps use the unrounded value")]),
    ]
    tables.append(tbl("T3E.2", "Price metrics", [("value", "Value"), ("convention", "Convention")], t2, "Metric"))

    mg = sub["terms"]["margin"]
    mg_cite = [mg["quote"]] if mg.get("quote") else []
    amort = sub["terms"]["amortisation"]
    am_cite = [amort["quote"]] if amort.get("quote") else []
    cols3 = [("bid", "At bid"), ("mid", "At mid"), ("offer", "At offer"), ("convention", "Convention")]
    pt_cites = {"bid": c_obs["bid"], "mid": mid_cites, "offer": c_obs["offer"]}
    PT_NEED = {"bid": why("Not calculable: no observed bid"), "mid": MID_NEEDS, "offer": why("Not calculable: no observed offer")}
    DM_NEED = {n: (PT_NEED[n] if s[f"disc_{n}"] is None else
                   why("Not calculable: needs a stated contractual margin and a stated zero amortisation"))
               for n in ("bid", "mid", "offer")}
    disc_row = [calc_or_gap(s[f"disc_{n}"], "basis_points", None, pt_cites[n] + cites_days[1:], f"cp3d.disc_{n}",
                            "(par - price) / years", PT_NEED[n] if d["days"] is not None else CALC_NEEDS["years"])
                for n in ("bid", "mid", "offer")] + [T("Redemption at par at final maturity")]
    margin_cell = (N(s["margin_bp"], "basis_points", None, mg_cite, vc="source", per=PER_TERMS)
                   if s["margin_bp"] is not None else G("Not stated: no contractual margin cited", "basis_points"))
    margin_row = [margin_cell] * 3 + [T("Stated contractual spread over the reference rate")]
    dm_row = [calc_or_gap(s[f"dm_{n}"], "basis_points", None, pt_cites[n] + mg_cite + am_cite + cites_days[1:],
                          f"cp3d.dm_{n}", "contractual margin + annualised discount to par",
                          DM_NEED[n] if d["days"] is not None else CALC_NEEDS["years"])
              for n in ("bid", "mid", "offer")] + [T("Simple margin; no amortisation; quotation date as settlement")]
    rr = sub["terms"]["reference_rate"]
    RR_NEED = "Not calculable: no reference rate level in any source"
    ref_cells = ([N(dstr(Decimal(rr["level"]["percent_text"]) / 100), "decimal_fraction", 2, [rr["level"]["quote"]],
                    vc="source", per=PER_TERMS)] * 3 if rr.get("level") else [G(RR_NEED, "decimal_fraction")] * 3) + \
        [T("Dated reference rate level or curve required")]
    lvl_cite = [rr["level"]["quote"]] if rr.get("level") else []
    yld_row = [calc_or_gap(s[f"yield_{n}"], "decimal_fraction", 2,
                           pt_cites[n] + mg_cite + am_cite + cites_days[1:] + lvl_cite, f"cp3d.yield_{n}",
                           "reference rate level + simple discount margin",
                           RR_NEED if not rr.get("level") else DM_NEED[n] if d["days"] is not None else CALC_NEEDS["years"])
               for n in ("bid", "mid", "offer")] + [T("Reference rate level + simple discount margin")]
    tables.append(tbl("T3E.3", "Spread and yield", cols3, [
        ("r01", "Annualised discount to par", disc_row),
        ("r02", "Contractual margin", margin_row),
        ("r03", "Simple discount margin", dm_row),
        ("r04", "Reference rate level", ref_cells),
        ("r05", "All-in yield (simple)", yld_row),
    ], "Measure"))

    # T3E.4 assumptions and terms
    rec = sub.get("recovery")
    rec_cell = (N(dstr(Decimal(rec["percent_text"]) / 100), "decimal_fraction", 0, (), vc="analyst_judgment", per=PER_RUN)
                if rec else G("Not calculable: recovery assumption not assessed", "decimal_fraction"))
    rr_cell = T(rr["name"], [rr["quote"]])
    mat = sub["terms"]["maturity"]
    mat_cell = (T(fmt_date(parse_date(mat["date_text"])), [mat["quote"]]) if mat.get("date_text")
                else G("Not stated: no final maturity cited"))
    amort_cell = T("Zero, as stated", am_cite) if amort.get("value_text") else G("Not stated: amortisation not cited")
    tables.append(tbl("T3E.4", "Assumptions and terms", [("value", "Value")], [
        ("r01", "Recovery rate (analyst assumption)", [rec_cell]),
        ("r02", "Reference rate", [rr_cell]),
        ("r03", "Final maturity", [mat_cell]),
        ("r04", "Mandatory amortisation", [amort_cell]),
        ("r05", "Instrument", [T(sub["instrument"]["name"], [sub["instrument"]["quote"]])]),
    ], "Input"))

    # T3E.5 market-implied default
    def lam_cell(n):
        st = s[f"pd_state_{n}"]
        if st == "known":
            return N(s[f"lam_{n}"], "basis_points", None, pt_cites[n] + mg_cite + am_cite + cites_days[1:],
                     calc=f"cp3d.lambda_{n}", formula="simple discount margin / (1 - recovery)")
        if st == "not_applicable":
            return G("Not meaningful: the simple discount margin is not positive", "basis_points", "not_applicable")
        return G(why("Not calculable: needs a simple discount margin and a recovery assumption"), "basis_points")

    def pd_cell(n):
        st = s[f"pd_state_{n}"]
        if st == "known":
            return N(s[f"pd_{n}"], "decimal_fraction", 2, pt_cites[n] + mg_cite + am_cite + cites_days[1:],
                     calc=f"cp3d.pd_{n}", formula="1 - exp(-(intensity) x years)")
        if st == "not_applicable":
            return G("Not meaningful: the simple discount margin is not positive", "decimal_fraction", "not_applicable")
        return G(why("Not calculable: needs a simple discount margin and a recovery assumption"), "decimal_fraction")

    cols5 = [("bid", "At bid"), ("mid", "At mid"), ("offer", "At offer"), ("convention", "Convention")]
    tables.append(tbl("T3E.5", "Market-implied default", cols5, [
        ("r01", "Annual default intensity", [lam_cell(n) for n in ("bid", "mid", "offer")] +
         [T("Credit triangle: spread / (1 - recovery)")]),
        ("r02", "Cumulative default probability to final maturity", [pd_cell(n) for n in ("bid", "mid", "offer")] +
         [T("Constant intensity to final maturity; risk-neutral")]),
    ], "Measure"))

    # T3E.6 technicals + summary
    t6 = []
    for i, x in enumerate(sub["technicals"], 1):
        t6.append((f"r{i:02d}", x["aspect"].replace("_", " ").capitalize(), [
            T(x["category"], x["basis"], "analyst_judgment"),
            T(x["text"], x["basis"], "analyst_judgment")]))
    t6.append((f"r{len(t6) + 1:02d}", "Summary", [T("Analyst Interpretation", (), "analyst_judgment"),
                                                  T(sub["summary"]["text"], (), "analyst_judgment")]))
    tables.append(tbl("T3E.6", "Technicals", [("category", "Category"), ("assessment", "Assessment")], t6, "Aspect"))

    # missing-input ledger (T3E.7), evidence (T3E.8), own limitations (T3E.9)
    miss = []
    if mk_absent:
        miss.append(("market_levels", "Dealer levels, price metrics, days and years, discount margin and default measures",
                     "Pack holds no third-party market quotation source"))
    elif d["days"] is None:
        miss.append(("years", "Days and years to final maturity", "Needs a quotation date and a final maturity date"))
    if rr.get("absence"):
        miss.append(("reference_rate_level", "Reference rate level and all-in yield", rr["absence"]["reason"]))
    if sub.get("recovery_absence"):
        miss.append(("recovery", "Annual default intensity and cumulative default probability",
                     sub["recovery_absence"]["reason"]))
    if s["dm_mid"] is None and not mk_absent:
        miss.append(("discount_margin", "Simple discount margin", "Needs a contractual margin and stated zero amortisation"))
    t7 = [(f"r{i:02d}", name, [T(aff), T(why)]) for i, (_, name, _w) in enumerate(miss, 1)
          for aff, why in [(miss[i - 1][1], miss[i - 1][2])]]
    if not t7:
        t7 = [("r01", "Missing inputs", [T("None"), T("No input is missing")])]
    tables.append(tbl("T3E.7", "Missing inputs", [("affected", "Not calculated"), ("reason", "Reason")], t7, "Input"))

    ev = []
    for i, (sid, loc) in enumerate(cited_pages(sub), 1):
        ev.append((f"r{i:02d}", f"{NAMES[sid]}, {loc}", [T(sid), T(loc)]))
    tables.append(tbl("T3E.8", "Evidence", [("source", "Source"), ("locator", "Locator")], ev, "Page"))

    own = own_limitations(case, sub, d)
    tables.append(tbl("T3E.9", "Limitations", [("text", "Limitation")],
                        [(f"r{i:02d}", f"Limitation {i}", [T(t)]) for i, t in enumerate(own, 1)], "Limitation"))

    claims = compose_claims(case, sub, d, tables)
    return tables, claims, own


def own_limitations(case, sub, d):
    out = []
    if sub.get("market_absence"):
        out.append("No third-party market quotation source is in the pack, so no market level is shown")
    else:
        out.append("Single dealer quotation; the sheet reports no trade in the period to the quotation date")
    out += [x["limitation"] for x in sub["technicals"] if x.get("limitation")]
    if any(o["kind"] == "indicative_talk" for o in sub["observations"]):
        out.append("Indicative dealer talk is shown but is not used in any calculation")
    if sub["terms"]["reference_rate"].get("absence"):
        out.append("The reference rate level is not in any source, so the all-in yield is not calculated")
    if sub.get("recovery"):
        out.append("The recovery rate is an analyst assumption following the first-lien loan CDS convention, not a source "
                   "figure; the convention itself is not verified against a source")
        out.append("A higher recovery raises the implied default intensity and default probability for the same margin")
    else:
        out.append("The recovery rate was not assessed, so the default measures are not calculated")
    out.append("The simple discount margin assumes redemption at par at final maturity, no amortisation and the "
               "quotation date as settlement date; it is not a Z-spread; not divided by price; not the three-year-life convention")
    out.append("The whole spread is attributed to default risk and the intensity is constant, so the default "
               "measures are risk-neutral and overstate the default component if a liquidity premium is present")
    out.append("The contractual margin and the amortisation are read from the financial source page, not from a "
               "CP-1 fact")
    out.append("The alignment of the market-implied view with the fundamentals is not shown: no fundamental comparator "
               "is bound, so only the market-implied default half of the market-against-fundamentals block is populated")
    if absence_paths(sub):
        out.append("An absence is backed only by a recorded search over some source, not by a search for the specific item")
    return dedupe(out)


def fid(tid, rid, field):
    return f"{tid}.{rid}.{field}"


def compose_claims(case, sub, d, tables):
    by_id = {f["fact_id"]: f for t in tables for r in t["rows"] for f in r["facts"]}
    s = stored(d)
    mk_absent = bool(sub.get("market_absence"))
    claims = []

    def add(cid, text, refs):
        cites = []
        for r in refs:
            for c in by_id[r]["cites"]:
                if c not in cites:
                    cites.append(c)
        claims.append({"claim_id": cid, "text": text, "refs": refs, "cites": cites})

    asof = d["days"] is not None and next(
        (o["as_of_text"] for o in sub["observations"] if o["kind"] == "bid"), None)
    bidf, offf, midf = fid("T3E.1", "r01", "level"), fid("T3E.1", "r02", "level"), fid("T3E.2", "r01", "value")
    if mk_absent:
        add("CP-3D-LVL-01", f"No market level is available: [{bidf}] and [{offf}] are not stated because the pack holds no "
            "third-party market quotation source.", [bidf, offf])
    else:
        add("CP-3D-LVL-01", f"On {sub['observations'][0]['as_of_text']} the dealer quotation was {{{bidf}|%}} bid and "
            f"{{{offf}|%}} offer, a mid of {{{midf}|%}} of par.", [bidf, offf, midf])
    yrs = fid("T3E.2", "r06", "value")
    dmm = fid("T3E.3", "r03", "mid")
    mgf = fid("T3E.3", "r02", "mid")
    if s["dm_mid"] is not None:
        add("CP-3D-DM-01", f"At the mid the simple discount margin over the reference rate is {{{dmm}|bp}}, from a "
            f"contractual margin of {{{mgf}|bp}} and {{{yrs}|years}} to final maturity on December 31, 2029.",
            [dmm, mgf, yrs])
    else:
        add("CP-3D-DM-01", f"The simple discount margin is not calculated: [{dmm}] is not available.", [dmm])
    yld = fid("T3E.3", "r05", "mid")
    if s["yield_mid"] is not None:
        add("CP-3D-YLD-01", f"At the mid the all-in yield is {{{yld}|%}}, the reference rate level plus the simple "
            f"discount margin of {{{dmm}|bp}}.", [yld, dmm])
    else:
        add("CP-3D-YLD-01", f"The all-in yield is not calculated: [{yld}] needs a reference rate level that no source in "
            "the pack states.", [yld])
    lam, pdm = fid("T3E.5", "r01", "mid"), fid("T3E.5", "r02", "mid")
    if s["pd_state_mid"] == "known":
        add("CP-3D-PD-01", f"At the analyst recovery assumption the mid spread implies an annual default intensity of "
            f"{{{lam}|bp}} and a cumulative default probability to final maturity of {{{pdm}|%}}; both are "
            "risk-neutral measures.", [lam, pdm])
    else:
        needs = "simple discount margin" if sub.get("recovery") else "simple discount margin and a recovery assumption"
        add("CP-3D-PD-01", f"The market-implied default probability is not calculated: [{lam}] and [{pdm}] need a "
            f"{needs}.", [lam, pdm])
    claims.append({"claim_id": "CP-3D-VIEW-01", "text": sub["summary"]["text"], "refs": [], "cites": []})
    return claims


def claim_issues(claim, by_id):
    """Transcription of prose.issues for these claims: tokens resolve, figures need a known numeric fact with a
    citation or calculation id and an allowed unit, chips must name unsettled facts or non-numeric facts."""
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
            else:
                allowed = {f["unit"], {"decimal_fraction": "%", "basis_points": "bp", "years": "years",
                                       "days": "days"}[f["unit"]]}
                if m.group("u") not in allowed:
                    issues.append(f"Unit {m.group('u')} differs from the fact's unit: {ref}")
        elif f["status"] == "known" and f["amount"] is not None:
            issues.append(f"A numeric fact needs a figure reference: {ref}")
    rest.append(text[last:])
    return issues, "".join(rest)


# --- CP-0 (readiness.py:408-531 transcription, as cases/cp3-cp6-owner/builder/build.py) ----------------
def pack_rows(ids):
    return [(sid, NAMES[sid], "ready", LIMIT[sid]) for sid in ids]


def cp0_expected(pack, sub, run_id, plan_order, live_consumers):
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
        add("T2", sid, "source", f"{name}; {status}; SHA-256 {SHA[sid]}")
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


S1P = S1E["positive"]
_s1_pack = pack_rows(("identity", "financial", "business"))
# Self-check: the transcription reproduces the frozen S1 positive CP-0 from the frozen S1 literal review.
_s1_pos = cp0_expected(_s1_pack, S1S["positive"]["readiness_review"], "slice-snapshot-positive",
                       ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL"], ["CP-1", "CP-1A", "CP-2"])
for _k in ("status", "why", "live_consumers", "plan_order", "exact_commands", "limitations", "facts"):
    assert _s1_pos[_k] == S1P["CP-0"][_k], f"CP-0 transcription differs from the S1 oracle at {_k}"


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


PLAN, CAT = meth_plan(["CP-3D"])
assert PLAN == ["CP-0", "CP-3D"], PLAN
assert CAT["CP-3D"]["required"] == ["CP-0"] and CAT["CP-3D"]["optional"] == ["CP-2H"]
CP3D_TABLES = CAT["CP-3D"]["table_ids"]
assert sorted(CP3D_TABLES) == sorted(f"T3E.{i}" for i in range(1, 11))
for _m in METH:
    if _m["module_id"] != "CP-3D":
        assert not any(t.startswith("T3E") for t in _m["table_ids"]), _m["module_id"]


def readiness_review(case):
    sub = copy.deepcopy(S1S["positive"]["readiness_review"])
    ident = sub["sources"][0]["citations"][0]
    fin = sub["sources"][1]["citations"][0]
    sub["sources"] = sub["sources"][:2]
    sub["objective"] = "Market-implied credit risk and trading technicals"
    sub["reporting_period"] = "Dealer quotation as of January 9, 2026 and the FY2025 facility terms"
    fin5 = cite("financial", "page:5", Q_FIN_INSTRUMENT)
    if case != "gap_no_market":
        mq = cite("market", "page:1", Q_BID)
        sub["sources"].append({
            "source_id": "market", "document_family": "Loan market quotation sheet", "authority": "third_party",
            "entity": ISSUER, "period": "January 2026",
            "version_relationship": "Standalone third-party dealer quotation sheet",
            "fidelity": "verified", "citations": [mq], "limitations": [],
        })
        sub["consumers"] = [{
            "module_id": "CP-3D", "readiness": "READY_WITH_LIMITATIONS",
            "evidence_demand": "Located dated third-party market quotations and the facility pricing terms",
            "source_ids": ["financial", "market"],
            "rationale": "The market-implied assessment can run on the located dealer quotation and the stated facility margin, with source limitations.",
            "citations": [mq, fin5], "missing_source": None, "limitations": [LIMIT_FIN],
        }]
        sub["gaps"] = []
    else:
        sub["consumers"] = [{
            "module_id": "CP-3D", "readiness": "READY_WITH_LIMITATIONS",
            "evidence_demand": "Facility pricing terms; no third-party market quotation is available",
            "source_ids": ["financial"],
            "rationale": "The assessment can run on the stated facility terms and records the absence of market levels.",
            "citations": [fin5], "missing_source": None, "limitations": [GAP_MARKET],
        }]
        sub["gaps"] = [{
            "gap_id": "missing-market-source", "kind": "source", "severity": "material",
            "description": GAP_MARKET, "affected_modules": ["CP-3D"],
            "remediation": "Supply a dated dealer quotation or trade record", "citations": [],
        }]
    cites = [ident, fin] + ([mq] if case != "gap_no_market" else [])
    sub["analysis"] = [{
        "claim_id": "source-assessment",
        "text": "The located statements and the dealer quotation sheet support a market-implied assessment with limitations."
        if case != "gap_no_market" else
        "The located statements support only the facility terms; no market quotation is available.",
        "citations": cites, "limitation": LIMIT_FIN,
    }]
    return sub


RUNS = {
    "positive": "slice-cp3d-positive",
    "gap_no_recovery": "slice-cp3d-positive",  # a clone of the settled CP-0; only the CP-3D submission differs
    "gap_no_market": "slice-cp3d-gap-no-market",
}

# --- refusal mutations -------------------------------------------------------------------------------------
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


MUTATIONS = [
    ("level_not_in_quote", [(["observations", 0, "level_text"], "98.60")],
     "observations[0]: level_text 98.60 does not occur in the quote"),
    ("level_not_numeric", [(["observations", 0, "level_text"], "ninety")],
     "observations[0]: level_text ninety is not a decimal number"),
    ("quote_off_page", [(["observations", 0, "locator"], "page:2")],
     "observations[0]: quote not found on market page:2"),
    ("source_not_third_party", [(["observations", 0, "source_id"], "financial"), (["observations", 0, "locator"], "page:5")],
     "observations[0]: source financial is not a third_party source (CP-0 T3)"),
    ("duplicate_kind", [(["observations", 1, "kind"], "bid"), (["observations", 1, "level_text"], "98.50")],
     "observations: kind bid appears more than once"),
    ("bid_level_is_the_offer", [(["observations", 0, "level_text"], "99.25")],
     "observations[0]: bid level_text 99.25 is not labelled bid in the quote"),
    ("talk_cites_bid_offer_sentence", [(["observations", 2, "locator"], "page:1"), (["observations", 2, "quote"], Q_BID),
                                       (["observations", 2, "level_text"], "99.25")],
     "observations[2]: indicative_talk level_text 99.25 is a bid or offer level in the quote"),
    ("as_of_not_in_quote", [(["observations", 0, "as_of_text"], "January 8, 2026")],
     "observations[0]: as_of_text January 8, 2026 does not occur in the quote"),
    ("margin_not_in_quote", [(["terms", "margin", "bps_text"], "25")], "margin: bps_text 25 does not occur in the quote"),
    ("recovery_out_of_range", [(["recovery", "percent_text"], "100")],
     "recovery: percent must be at least 0 and below 100"),
    ("recovery_both", [(["recovery_absence"], {"reason": "Not assessed", "follow_up": "Assess it"})],
     "recovery: exactly one of recovery and recovery_absence is required"),
    ("reference_level_not_in_quote", [(["terms", "reference_rate", "absence"], None),
                                      (["terms", "reference_rate", "level"],
                                       {"quote": q("financial", "page:5", Q_SOFR), "percent_text": "4.30"})],
     "reference_rate: level percent_text 4.30 does not occur in the quote"),
    ("reference_rate_neither", [(["terms", "reference_rate", "absence"], None)],
     "reference_rate: exactly one of level and absence is required"),
    ("digit_in_text", [(["technicals", 0, "text"], "The observed level is one dealer quotation of 1 dealer.")],
     "technicals[0].text: digits are not allowed"),
    ("prohibited_conclusion", [(["summary", "text"], "The loan looks cheap, so buy it.")],
     "summary.text: text carries a prohibited conclusion"),
    ("insufficient_without_limitation", [(["technicals", 3, "limitation"], None)],
     "technicals[3]: limitation is required for Insufficient Information and only for it"),
    ("observations_and_absence", [(["market_absence"], {"reason": "None", "follow_up": "None"})],
     "observations: exactly one of observations and market_absence is required"),
]


def run_mutations():
    base = LITERALS["positive"]
    out = []
    for name, edits, expect in MUTATIONS:
        s = mut(base, edits)
        iss = check_submission(s, PACK_IDS["positive"])
        assert iss == [expect], (name, iss)
        out.append({"id": name, "edits": [[".".join(str(x) for x in p), v] for p, v in edits],
                    "issue": expect, "all_issues": iss})
    return out


# crossed_quote (bid above offer) is retired as a literal: with the level-to-kind binding a verbatim quote of the
# sheet can only say bid 98.50 and offer 99.25, so the rule is unreachable through this pack. The core keeps the rule
# (bid exceeds offer); it is exercised by a core unit test over a synthetic page, not by this oracle.


def maturity_before_literal():
    """Replace the maturity with a date before the quotation: the quote is the one sentence that states a past date."""
    s = copy.deepcopy(LITERALS["positive"])
    s["terms"]["maturity"]["quote"] = q("market", "page:1", "Published January 10, 2026. Quotations are as of the close on January 9, 2026.")
    s["terms"]["maturity"]["date_text"] = "January 9, 2026"
    return s


_bm = maturity_before_literal()
_iss = check_submission(_bm, PACK_IDS["positive"])
assert _iss == ["maturity: date is not after the quotation date"], _iss


def amort_nonzero_literal():
    s = copy.deepcopy(LITERALS["positive"])
    s["terms"]["amortisation"] = {"quote": q("financial", "page:5", "Mandatory annual amortisation is 0; final maturity is December 31, 2029"),
                                  "value_text": "31", "absence": None}
    return s


_an = check_submission(amort_nonzero_literal(), PACK_IDS["positive"])
assert _an == ["amortisation: the simple margin convention requires zero amortisation"], _an

# Replace the two placeholder mutations by their concrete literals.
MUT_LIST = []
for m in [*run_mutations(), {"id": "maturity_before_quotation"}, {"id": "amortisation_nonzero"}]:
    if m["id"] == "maturity_before_quotation":
        m = {"id": m["id"], "edits": [["terms.maturity.quote", _bm["terms"]["maturity"]["quote"]],
                                      ["terms.maturity.date_text", "January 9, 2026"]],
             "issue": "maturity: date is not after the quotation date", "all_issues": _iss}
    if m["id"] == "amortisation_nonzero":
        m = {"id": m["id"], "edits": [["terms.amortisation.quote", amort_nonzero_literal()["terms"]["amortisation"]["quote"]],
                                      ["terms.amortisation.value_text", "31"]],
             "issue": "amortisation: the simple margin convention requires zero amortisation", "all_issues": _an,
             "note": "value_text 31 is the day-of-month numeral of 'December 31' in the quote, not an amortisation "
                     "figure; the quote's other numerals are the zero and the year"}
    MUT_LIST.append(m)

# Tool-use refusals: the core RULES(text, seen) attribute (protocol section 2), reusing live/tools.py
# unread_citation_issues (sorted by source_id, locator) and UNBACKED_ABSENCE, in ToolRules order (absence, then unread).
# The expected issues are exact strings; the oracle has no case in which both rules fire.
MARGIN_ABSENT = {"quote": None, "bps_text": None,
                 "absence": {"reason": "No contractual margin is stated", "follow_up": "Supply the facility pricing terms"}}


def term_absence_literal():
    s = copy.deepcopy(LITERALS["positive"])
    s["terms"]["margin"] = copy.deepcopy(MARGIN_ABSENT)
    return s


assert not check_submission(term_absence_literal(), PACK_IDS["positive"])


TOOL_USE = [
    {"id": "unread_market_page_1", "reads": [["market", "page:2"], ["financial", "page:5"]], "searches": 1,
     "issues": ["Cited page not read through read_pages: market page:1"]},
    {"id": "unread_financial_page_5", "reads": [["market", "page:1"], ["market", "page:2"]], "searches": 1,
     "issues": ["Cited page not read through read_pages: financial page:5"]},
    {"id": "unread_two_pages_sorted", "reads": [["market", "page:2"]], "searches": 1,
     "issues": ["Cited page not read through read_pages: financial page:5",
                "Cited page not read through read_pages: market page:1"]},
    {"id": "absence_without_search", "reads": [["market", "page:1"], ["market", "page:2"], ["financial", "page:5"]],
     "searches": 0, "issues": ["Absence claim without a recorded search"]},
    {"id": "term_absence_without_search", "edits": [["terms.margin", MARGIN_ABSENT]],
     "note": "the reference rate absence also holds in every pack case, so this case shows the term absence is reached, not that it alone fires",
     "reads": [["market", "page:1"], ["market", "page:2"], ["financial", "page:5"]],
     "searches": 0, "issues": ["Absence claim without a recorded search"]},
]
_pos_pages = set(cited_pages(LITERALS["positive"]))
assert _pos_pages == {("market", "page:1"), ("market", "page:2"), ("financial", "page:5")}, _pos_pages
for _t in TOOL_USE:
    _lit = term_absence_literal() if "edits" in _t else LITERALS["positive"]
    _got = tool_rule_issues(_lit, {tuple(r) for r in _t["reads"]}, _t["searches"] > 0)
    assert _got == _t["issues"], (_t["id"], _got)
    _t["issue"] = _t["issues"][0]
assert not tool_rule_issues(LITERALS["positive"], _pos_pages, True)
# every absence object is covered by the absence rule: each, alone, needs a search
_one = copy.deepcopy(LITERALS["positive"])
_one["terms"]["reference_rate"]["absence"] = None
assert absence_paths(_one) == [] and absence_paths(term_absence_literal()) == ["terms.margin.absence", "terms.reference_rate.absence"]
_alt = copy.deepcopy(_one)
for _k, _v in (("maturity", {"quote": None, "date_text": None}), ("amortisation", {"quote": None, "value_text": None})):
    _a = copy.deepcopy(_alt)
    _a["terms"][_k] = {**_v, "absence": {"reason": "Not stated", "follow_up": "Supply it"}}
    assert absence_paths(_a) == [f"terms.{_k}.absence"], _k
    assert tool_rule_issues(_a, _pos_pages, False) == [ABSENCE_ISSUE]
    assert tool_rule_issues(_a, _pos_pages, True) == []
_a = copy.deepcopy(_one)
_a["observations"], _a["market_absence"] = [], {"reason": "None", "follow_up": "None"}
assert absence_paths(_a) == ["market_absence"]

# Blocked case: attempt 0 and attempt 1 both invalid.
BLOCKED = {
    "attempt_0": {"edits": [["technicals.0.text", "The observed level is one dealer quotation of 1 dealer."]],
                  "issue": "technicals[0].text: digits are not allowed"},
    "attempt_1": {"edits": [["observations.0.level_text", "98.60"]],
                  "issue": "observations[0]: level_text 98.60 does not occur in the quote"},
}

# --- fixtures (composer only, derived values; not pack runs) -------------------------------------------------
def fixture(inp):
    d = derive(inp)
    return {"inputs": {k: (dstr(v) if isinstance(v, Decimal) else (v.isoformat() if isinstance(v, date) else v))
                       for k, v in inp.items()},
            "stored": stored(d)}


BASE_INP = inputs_of(LITERALS["positive"])
FIXTURES = {
    "fixture_with_benchmark": {**fixture({**BASE_INP, "ref_level": Decimal("0.043")}),
                               "note": "reference rate level 4.30 percent is a test vector for the pure function, not a source figure"},
    "fixture_above_par": {**fixture({**BASE_INP, "bid": Decimal("100.50"), "offer": Decimal("101.00")}),
                          "note": "price above par: discount negative, simple discount margin not positive, default measures not meaningful"},
    "fixture_bid_only": {**fixture({k: v for k, v in BASE_INP.items() if k != "offer"}),
                         "note": "no offer: mid, width and offer columns missing; bid column known"},
    "fixture_zero_recovery": {**fixture({**BASE_INP, "recovery": Decimal("0")}),
                              "note": "recovery 0: intensity equals the simple discount margin"},
    "fixture_no_margin": {**fixture({**BASE_INP, "margin_bp": None}),
                          "note": "contractual margin not cited: discount margin missing, annualised discount known"},
}
assert FIXTURES["fixture_above_par"]["stored"]["pd_state_mid"] == "not_applicable"
assert FIXTURES["fixture_bid_only"]["stored"]["mid"] is None and FIXTURES["fixture_bid_only"]["stored"]["dm_bid"] is not None
assert FIXTURES["fixture_zero_recovery"]["stored"]["lam_mid"] == FIXTURES["fixture_zero_recovery"]["stored"]["dm_mid"]
assert FIXTURES["fixture_no_margin"]["stored"]["dm_mid"] is None and FIXTURES["fixture_no_margin"]["stored"]["disc_mid"] is not None

# --- assembly ------------------------------------------------------------------------------------------------
CASE_META = {
    "positive": {"pack_ids": PACK_IDS["positive"], "run_id": RUNS["positive"]},
    "gap_no_recovery": {"pack_ids": PACK_IDS["gap_no_recovery"], "run_id": RUNS["gap_no_recovery"]},
    "gap_no_market": {"pack_ids": PACK_IDS["gap_no_market"], "run_id": RUNS["gap_no_market"]},
}


def run_of(case):
    return {"run_id": RUNS[case], "issuer_id": ISSUER_ID, "issuer_name": ISSUER, "as_of": AS_OF,
            "method_version": "deploy-v-r14", "case_kind": "synthetic", "pathway": "relative_value",
            "requested_modules": ["CP-3D"]}


def selftest_known_level():
    """Composes a literal whose reference rate level is quoted (no frozen source states one, so a throwaway page
    stands in for the build only; nothing of it is written out) and checks the all-in yield path end to end."""
    page = "The SOFR reference rate is 4.30 percent."
    PAGES["financial"]["page:9"] = page
    try:
        lit = copy.deepcopy(LITERALS["positive"])
        lit["terms"]["reference_rate"]["absence"] = None
        lit["terms"]["reference_rate"]["level"] = {"quote": q("financial", "page:9", page), "percent_text": "4.30"}
        assert not check_submission(lit, PACK_IDS["positive"])
        d = derive(inputs_of(lit))
        tables, claims, _own = compose_case("positive", lit, d)
        by_id = {f["fact_id"]: f for t in tables for r in t["rows"] for f in r["facts"]}
        assert by_id["T3E.3.r04.mid"]["shown"] == "4.30%" and by_id["T3E.3.r04.mid"]["status"] == "known"
        y = by_id["T3E.3.r05.mid"]
        assert y["status"] == "known" and y["amount"] == stored(d)["yield_mid"] and y["calculation_id"] == "cp3d.yield_mid"
        assert ["financial", "page:9"] in y["cites"] and y["shown"] == "4.58%", y
        claim = next(c for c in claims if c["claim_id"] == "CP-3D-YLD-01")
        assert not claim_issues(claim, by_id)[0], claim
        assert ("financial", "page:9") in cited_pages(lit)
    finally:
        del PAGES["financial"]["page:9"]


def main():
    selftest_known_level()
    reviews = {c: readiness_review(c) for c in LITERALS}
    cp0 = {}
    for c in ("positive", "gap_no_market"):
        cp0[c] = cp0_expected(pack_rows(PACK_IDS[c]), reviews[c], RUNS[c], PLAN, ["CP-3D"])
    cp0["gap_no_recovery"] = cp0["positive"]
    cases = {}
    for c, lit in LITERALS.items():
        inp = inputs_of(lit)
        d = derive(inp)
        tables, claims, own = compose_case(c, lit, d)
        by_id = {f["fact_id"]: f for t in tables for r in t["rows"] for f in r["facts"]}
        scan = []
        for cl in claims:
            iss, literal = claim_issues(cl, by_id)
            assert not iss, (c, cl["claim_id"], iss)
            scan.append({"claim_id": cl["claim_id"], "literal_text_outside_references": literal})
            for ref in cl["refs"]:
                assert ref in by_id
        cp0_lims = cp0[c]["limitations"]
        inherited = [t for t in cp0_lims if t not in own]
        missing = [f["fact_id"] for f in by_id.values() if f["status"] != "known"]
        cases[c] = {
            "run": run_of(c),
            "pack_sources": [{"source_id": sid, "name": NAMES[sid], "sha256": SHA[sid], "status": "ready"}
                             for sid in PACK_IDS[c]],
            "status": "restricted",
            "derived": stored(d),
            "missing_not_zero": missing,
            "tables": tables,
            "claims": claims,
            "claim_literal_text": scan,
            "own_limitations": own,
            "inherited_limitations": inherited,
            "inherited_rule": "CP-0 head limitations then CP-0 inherited, de-duplicated, own removed (execution.py:345-366)",
            "module_inputs": ["prepared-pack", "CP-0", "market-implied-submission"],
            "tool_use_required": {
                "read_pages_cover": [list(p) for p in cited_pages(lit)],
                "search_pack_min": 1 if absence_paths(lit) else 0,
                "read_inputs_calls": 0,
            },
        }
    # headline checks on the positive values
    pos = cases["positive"]["derived"]
    assert pos["mid"] == "0.98875" and pos["days"] == "1452" and pos["years"] == "3.98"
    assert cases["gap_no_recovery"]["derived"]["lam_mid"] is None and cases["gap_no_recovery"]["derived"]["dm_mid"] == pos["dm_mid"]
    assert cases["gap_no_market"]["derived"]["mid"] is None and cases["gap_no_market"]["derived"]["bid"] is None

    manifest = {
        "schema_version": "cp3d-owner-cases/1",
        "scope": "CP-3D market implied risk owner inputs: a two-module run CP-0 then CP-3D over a pack with the frozen third-party market quotation sheet",
        "status": "DRAFT revision 2 (fix round 1) by owner-preparation task cp3d-owner, 2026-10-28; not executed",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "pins": {**PINS},
        "market_source_pin": {"file_read": MARKET_FILE, "file_pinned": False,
                              "why": "that file belongs to another preparation and may be revised; the two page bytes are pinned by the source sha256",
                              "source_sha256": MARKET_SHA, "source_id": "market", "name": MARKET_NAME,
                              "pages": [{"locator": l, "text": t} for l, t in MARKET_PAGES]},
        "reuse": {"identity": "cases/financial/manifest.json source identity, bytes unchanged",
                  "financial": "cases/financial/manifest.json source financial, bytes unchanged",
                  "market": "cases/cp3-cp6-owner/manifest.json market_source, bytes unchanged (the CP-3 preparation's frozen third-party sheet)"},
        "no_new_source": "No second market source is added. The method needs no content the sheet and the financial schedule lack, except a reference rate level, which is deliberately absent so the all-in yield is shown Not calculable (see expected.json#arithmetic.reference_rate)",
        "run": {"requested_modules": ["CP-3D"], "plan_order": PLAN, "live_consumers_of_cp0": ["CP-3D"],
                "pathway": "relative_value", "optional_cp2h": "CP-2H is not built: treated as unbound, not selected, not read"},
        "cases": [{"case_id": c, "run": run_of(c), "pack_sources": cases[c]["pack_sources"],
                   "clone_of": "positive" if c == "gap_no_recovery" else None,
                   "submission": f"submissions.json#{c}"} for c in LITERALS],
        "table_ids": {"CP-3D": CP3D_TABLES, "used": [f"T3E.{i}" for i in range(1, 10)], "unused": ["T3E.10"]},
    }
    submissions = {
        "schema_version": "cp3d-owner-submissions/1",
        "note": "Literal analyst submissions for the CP-3D step market_implied. Levels, dates and terms are quoted: every *_text value must occur in its own verbatim quote, which the core parses with Python (analyst never supplies a computed number). The recovery percent is the one uncited analyst assumption (D11). No bound run-time values appear, except the readiness pack_sha256 placeholder.",
        "readiness_review": reviews,
        "positive": LITERALS["positive"],
        "gap_no_recovery": LITERALS["gap_no_recovery"],
        "gap_no_market": LITERALS["gap_no_market"],
        "refusal_mutations": {"base": "positive", "entries": MUT_LIST},
        "blocked": BLOCKED,
        "tool_use_refusals": TOOL_USE,
    }
    expected = {
        "schema_version": "cp3d-owner-expected/1",
        "derivation": "Each value is an exact Decimal derivation from cited source facts (the quotes in submissions.json) by the conventions in 'arithmetic'; nothing is read from code under test. Gap cells are spelled with the product's gap spelling; G# is bound at run time.",
        "cell_notation": {
            "num": "amount is the exact stored Decimal string; unit is the Fact unit; decimals is Fact.decimals; shown is the product spelling (display.py _number, report_view.fact_spelling): decimal_fraction shows amount x 100 to `decimals` places half-up with a percent sign; basis_points, years and days show the exact stored amount and ' bp', ' years', ' days'",
            "gap": "status missing -> shown '∅ G#'; status not_applicable -> shown '∅ G# n.m.'; G# is bound at run time (an A7-style exception)",
            "value_class": "source (quoted level or term), calculated (Python), analyst_judgment (recovery and technicals)",
            "calculated_cites": "a calculated fact carries the page-level cites of its inputs",
        },
        "arithmetic": {
            "decimal_context": "28 significant digits, ROUND_HALF_EVEN for division and exp; stored outputs are quantised ROUND_HALF_UP and are never the input of a later step (every output derives from unrounded intermediates)",
            "price_unit": "levels are quoted as a percentage of par; stored as decimal_fraction (98.50 -> 0.9850)",
            "mid": "(bid + offer) / 2, exact",
            "day_count": "Act/365 Fixed from the quotation date (as_of of bid and offer, which must be equal) to the final maturity date: days = maturity - quotation date; years = days / 365; years is stored quantised to 0.01 for display only: every later step (discount, margin, intensity, probability) uses the unrounded days / 365 (3.98 shown, 3.9780821917808... used; with 3.98 the offer margin would be 18.8 bp, not 18.9)",
            "annualised_discount_bp": "(100 - price) / years x 100 basis points per annum, price in points of par; stored quantised to 0.1 bp",
            "simple_discount_margin_bp": "contractual margin (bp, cited) + annualised discount; requires a cited zero amortisation; floor ignored (a floor on the reference rate does not enter a margin); stored quantised to 0.1 bp. Convention: the discounted-spread form of the loan market, margin + (100 - price) / years, NOT divided by price (dividing gives 38.3/28.6/19.0 bp at bid/mid/offer) and NOT the market's three-year-life convention (remaining life to final maturity is used instead); Act/365 Fixed; settlement taken as the quotation date (a settlement lag of about a week is ignored)",
            "reference_rate": "all-in yield (simple) = reference rate level + simple discount margin / 10000; the reference rate level must be quoted ({quote, percent_text}, percent_text a whole token once in its own verbatim quote) and is absent from every frozen source, so the yield is Not calculable in every pack case; fixture_with_benchmark exercises the pure function with a test vector, and the builder composes a throwaway quoted level to exercise the yield cells, claim and validator (nothing of it is written out)",
            "annual_default_intensity_bp": "simple discount margin / (1 - recovery) (credit triangle: the whole spread is default compensation), stored quantised to 0.1 bp; needs recovery in [0, 1) and a positive margin. A higher recovery raises the intensity for the same margin",
            "cumulative_default_probability": "1 - exp(-(intensity / 10000) x years) with unrounded intensity and years, stored quantised to 0.0001 (shown to two places as a percent); risk-neutral",
            "not_meaningful": "a simple discount margin <= 0 gives status not_applicable for both default measures (shown n.m.), never 0",
            "talk": "indicative talk is shown and compared with the mid (context row) but enters no spread, yield or default figure; its period is the commentary publication date (page:2), not the quotation date",
            "recovery": "analyst input in percent (D11), 0 <= x < 100; the literal is 70 percent, the first-lien loan CDS convention (the frozen financial page:5 states a senior secured term loan; the senior-unsecured CDS convention would be 40 percent). The convention is the analyst's knowledge: no source states it and it is not verified against one. At 40 percent the mid margin 28.3 bp would give 47.1 bp and 1.86 percent. Stored decimal_fraction decimals 0; an uncited analyst_judgment fact: it has no citation or calculation id so a claim cannot reference it as a figure",
        },
        "table_id_check": {
            "registered_for_CP-3D": CP3D_TABLES,
            "occurs_in_other_module_table_ids": [],
            "src_tests_docs_cases_grep_2026-10-28": "T3E appears only in src/deploy_vii/methodology.json before this preparation",
            "unused": ["T3E.10 is registered and left unused (no composed content); open question in the lease"],
        },
        "cp0": cp0,
        "cases": cases,
        "fixtures": FIXTURES,
        "refusals": [{"id": m["id"], "issue": m["issue"]} for m in MUT_LIST],
        "tool_use_refusals": [{"id": t["id"], "issues": t["issues"]} for t in TOOL_USE],
        "negative_cases": {
            "blocked_cp3d": {"attempt_0_issue": BLOCKED["attempt_0"]["issue"], "attempt_1_issue": BLOCKED["attempt_1"]["issue"],
                             "result": "attempt 0 invalid, re-begun as attempt 1 (repair_of set), attempt 1 invalid: module blocked, no head"},
            "begin_refused_cp0_blocked": "CP-0 blocked or stale refuses begin of CP-3D (edge_rule block, no attempt consumed); built by making CP-0 blocked on a clone (two invalid CP-0 attempts), no literal",
            "stale_binding": "a snapshot change between the last read_pages and the submit refuses stale_binding",
        },
        "tool_use": {
            "rules": "the core RULES(text, seen) attribute (G1X protocol section 2): live/tools.py unread_citation_issues (sorted by source_id, locator) and the UNBACKED_ABSENCE text when any absence object (market_absence, terms.maturity/margin/amortisation/reference_rate absence) is present and no search was recorded; ToolRules order (absence, then unread). recovery_absence is not an absence object here: it says the analyst did not assess, not that a source lacks something",
            "positive": "ok read_pages calls cover market page:1, market page:2 and financial page:5 before the submit; at least one ok search_pack (the reference_rate absence); zero read_inputs; zero extract_statements",
            "gap_no_market": "ok read_pages covers financial page:5; at least one ok search_pack (market_absence and reference_rate absence)",
            "refused_calls": "extract_statements and read_inputs are refused not_permitted receipts for CP-3D",
        },
        "consumption": {
            "status": "OPEN",
            "reason": "No consumer core reads CP-3D: cp3_relative_value.py:100 and cp6_committee.py:113 state they never read it; CP-5 counts only after a D3 scope lease; CP-3C (optional CP-3D edge) has no core, lease or chain",
            "reader_pinned_for_cp3c": {
                "function": "cp3d_reader(store, head)",
                "exposes": ["head sha256", "status", "simple discount margin at mid (fact id and amount)", "annual default intensity at mid",
                            "cumulative default probability at mid", "recovery assumption or its absence", "own limitations"],
                "positive_values": {k: cases["positive"]["derived"][k] for k in ("dm_mid", "lam_mid", "pd_mid")},
            },
        },
        "render": {
            "pathway": "relative_value",
            "design_reference": {
                "file": "/Users/ericguei/Documents/DEPLOY VII/design/reference/rbot-fp-03-relative-value.dc.html",
                "sha256": "89a15ee632ba4082a60ea8a895a6a9b0471e643e13e657782bdcf80e429d9a4f",
                "rule": "read only; outside this repository; governs block ownership (LEAD ruling 2026-10-28)",
            },
            "blocks": {
                "market-against-fundamentals": {
                    "owner": "CP-3D", "layout": "dense _Spec", "route_label": "Full analysis",
                    "tabs": [["T3E.5", "Market-implied default"], ["T3E.4", "Assumptions and terms"], ["T3E.6", "Technicals"], ["T3E.1", "Market levels"], ["T3E.2", "Price metrics"], ["T3E.3", "Spread and yield"]],
                    "primary": "T3E.5",
                    "populated": "the market-implied default panel (FP03 draws a market-implied default frame beside the alignment panel)",
                    "partial": "the alignment panel (market implication against fundamentals, per-row alignment chip) is not populated: CP-3D reads no fundamental comparator; the own limitation says so and T3E.9 carries it",
                },
                "evidence rail": ["T3E.8"],
                "limitations rail": ["T3E.9", "T3E.7"],
            },
            "slot_prefix": "cp3d-",
            "deferred": {
                "instrument-levels": "stays CP-3's (FP03 header 'CP-3 - 11 rows'); deferred to a later CP-3 FP03 lease",
                "yield-against-maturity": "CP-3D's own (FP03 header 'CP-3D - Fig. RV.1'); deferred: a chart, and the pack states no reference rate level so no yield exists to plot",
            },
            "architecture_row_conflict": "docs/reviews/owner-harness-architecture.md:68 gives instrument-levels to CP-3D; the FP03 design reference gives it to CP-3; the FP03 reference governs by LEAD ruling and the conflict is recorded in the lease",
            "not_asserted": "instrument-levels, yield-against-maturity, compensation-preference, peer-positioning, recommendation-portfolio-fit, loan-hy-relative-value, credit-view, capital-structure, what-changed",
            "gap_cells": "shown '∅ G<n>' with n bound at run time",
        },
        "not_verified": [
            "no CP-3D core, validator or composer exists; no value was compared with product output",
            "CP-0 literal for a CP-3D-only run never settled by the product (see probes in the report)",
            "the G1-X RULES routing and the owner-only pack-source seam are protocol text, not yet code",
            "display spelling for years, days, basis_points and decimals-override percent follows display.py/report_view.py reading",
            "Decimal.exp rounding is relied on only at 0.0001 quantisation",
        ],
    }
    for name, obj in (("manifest.json", manifest), ("submissions.json", submissions), ("expected.json", expected)):
        (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
