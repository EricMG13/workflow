"""Writes cases/cp8-owner/{manifest,submissions,expected}.json (stdlib only).

Oracle for CP-8 (decision ledger and post-mortem). Independent transcription of the documented
method (the r14 CP-8 skill, cited in work/lead/cp8-owner-preparation/lease-draft.md): no product code
is imported or run. It reads only files inside this repository, each checked against a pinned sha256
before use: the frozen financial manifest, the three S1 oracle files (the CP-0 base literal),
methodology.json, and cases/cp3-cp6-owner/manifest.json (the frozen third-party market sheet; the file
itself is pinned and its page bytes are also pinned by the source sha256). It reads nothing outside the
repository: the r14 skill and the DEPLOY VII design references are provenance literals (path and
sha256, verified once by hand by the reviewer), never opened here.

Three synthetic sources are new (the Prior Case record, the quarterly update note and a later dealer
sheet): no frozen source carries a decision record or a post-decision outcome. Every figure in them
is checked here against the frozen figures (financial manifest oracle, frozen market sheet). Every page
of each says it is invented test data, and each carries the pack limitation SYN_LIM (CP-1C precedent).

Every arithmetic value is an exact Decimal derivation (expected.json#arithmetic). Every checkable
property of the literal inputs (quotes on their page, numeral inside its quote and labelled,
digit-free analyst text, prohibited phrases, claim references) is asserted here, so an inconsistent
input fails the build.

Run from the repository root:  python3 -I cases/cp8-owner/builder/build.py
"""

import copy
import hashlib
import json
import re
from datetime import date
from decimal import ROUND_HALF_UP, Context, Decimal, DivisionByZero, Inexact, InvalidOperation, setcontext
from fractions import Fraction
from pathlib import Path

# Exact arithmetic is enforced, not assumed: 28 significant digits, and any rounding signals (Inexact).
setcontext(Context(prec=28, rounding=ROUND_HALF_UP, traps=[Inexact, InvalidOperation, DivisionByZero]))

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "cases" / "cp8-owner"

PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    "cases/snapshot/expected.json": "d1aa1af9677cc4bd77b890261f0ceeca664acc72aac77f91da55cf36d7279baa",
    "src/deploy_vii/methodology.json": "1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6",
    "cases/cp3-cp6-owner/manifest.json": "e3cb221737a3930278924eb16ad67208d9967cad455043565a79b24dcfae25c6",
}
MARKET_FILE = "cases/cp3-cp6-owner/manifest.json"
MARKET_SHA = "c175d14bf4b1fd245d3c971bff6e9499a789aabc820cd340d0ea40e369f774b7"
# Provenance literals: outside this repository, never opened by this builder (the reviewer verifies them once).
R14_SKILL = "/Users/ericguei/Documents/Deploy VI/reference/deploy-v-r14/skills/cp-8-decision-ledger-post-mortem/SKILL.md"
R14_SKILL_SHA = "1ace999e7224a0f003d09e045c331cadef89ca4a3d64ecfe5ec971029eee2248"
R14_STEPS = "/Users/ericguei/Documents/Deploy VI/reference/deploy-v-r14/skills/cp-8-decision-ledger-post-mortem/references/REF_CP-8_STEPS.md"
R14_STEPS_SHA = "54e85dad34e3a2e30e9ad89d5e335bc780097d582a277259c14a7c4f666c54bc"
DESIGN_DIR = "/Users/ericguei/Documents/DEPLOY VII/design/reference/"
DESIGN_SHA = {
    "rbot-fp-01-credit-snapshot.dc.html": "a279fc907774025a67e082dcca0a38b014f2093b2415106f5d47733fbbe44f8c",
    "rbot-fp-06-portfolio-decision.dc.html": "10d49a0cb2f6da34a30e286a9caf3ec4695e15e7909fc246df399380c4d29271",
    "rbot-design-system.dc.html": "765d190eafae9658371395062c734b6954c7fcb2896458768ab81be0f5716a96",
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
SYNTH = "Synthetic case; not real issuer qualification"
RUN_AS_OF = "2026-04-30"  # the run is later than the Prior Case record and the outcome sources

# --- frozen sources (bytes reused, hash-checked) ---------------------------------------------------
fin_src = {s["source_id"]: s for s in FIN["sources"]}
for _sid, _s in fin_src.items():
    assert page_sha([p["text"] for p in _s["pages"]]) == _s["sha256"], _sid
IDENT_PAGES = {p["locator"]: p["text"] for p in fin_src["identity"]["pages"]}
BUS = S1M["business_source"]
BUS_PAGES = BUS["positive"]["pages"]
assert page_sha([p["text"] for p in BUS_PAGES]) == BUS["positive"]["sha256"]
_mk = load_pinned(MARKET_FILE)["market_source"]
MARKET_PAGES = {p["locator"]: p["text"] for p in _mk["pages"]}
assert page_sha([p["text"] for p in _mk["pages"]]) == MARKET_SHA, "market source bytes differ from the pin"

# Frozen figures the Prior Case record must agree with (rounded as the product shows them).
_ltm = FIN["q4_ltm_metric_oracle"]
assert _ltm["total_leverage_reported"]["fraction"] == "5/3" and _ltm["interest_coverage_reported"]["decimal"] == "6"
LEV_AT_DECISION = "1.67"  # 5/3 shown to two places (display.py multiple, half-up)
assert Fraction(1665, 1000) < Fraction(5, 3) < Fraction(1675, 1000)
COVER_AT_DECISION = "6.00"
assert "bid 98.50 and offer 99.25" in MARKET_PAGES["page:1"] and "December 31, 2029" in MARKET_PAGES["page:1"]
assert "January 9, 2026" in MARKET_PAGES["page:1"]

# --- the three new synthetic sources -----------------------------------------------------------------
PRIOR_PAGES = {
    "page:1": (
        "NORTHBRIDGE SYNTHETIC GROUP\n"
        "Prior Case record\n"
        "Recorded at Approval on January 10, 2026.\n"
        "This invented case is test data, not evidence about a real issuer.\n"
        "Decision: Neutral action bias with Medium confidence on the Northbridge Term Loan.\n"
        "Decision-maker role: Investment Committee.\n"
        "Portfolio posture and position size were not recorded.\n"
        "Thesis as decided: The credit is sound on reported figures and the single dealer quotation sits just below par.\n"
        "Greatest uncertainty as decided: Thin market evidence from one dealer quotation."
    ),
    "page:2": (
        "NORTHBRIDGE SYNTHETIC GROUP\n"
        "Prior Case record: figures and expectations\n"
        "This invented case is test data, not evidence about a real issuer.\n"
        f"Total leverage recorded at Approval on January 10, 2026 was {LEV_AT_DECISION}x.\n"
        f"Interest cover recorded at Approval on January 10, 2026 was {COVER_AT_DECISION}x.\n"
        "Dealer quotation recorded at Approval, as of January 9, 2026: bid 98.50 and offer 99.25, expressed as a percentage of par.\n"
        "Expectation recorded: leverage and cover to stay near these levels and the quotation to hold.\n"
        "Downside paths named: weaker unaudited earnings, sized as total leverage above 1.75x or interest cover below 5.75x; and liquidity that depends on steady cash generation.\n"
        "Exit trigger recorded: a sharp move in the quotation. No threshold was recorded.\n"
        "Expected spread or return, expected rating path and expected holding period were not recorded."
    ),
}
UPDATE_PAGES = {
    "page:1": (
        "NORTHBRIDGE SYNTHETIC GROUP\n"
        "Quarterly update note\n"
        "Published April 30, 2026.\n"
        "This invented case is test data, not evidence about a real issuer.\n"
        "Total leverage for the twelve months to December 31, 2025 was reported as 1.67x.\n"
        "No default or restructuring had occurred as of December 31, 2025.\n"
        "Total leverage for the twelve months to February 28, 2026 was reported as 1.70x.\n"
        "Total leverage for the twelve months to March 31, 2026 is reported as 1.80x.\n"
        "Interest cover for the twelve months to March 31, 2026 is reported as 5.50x.\n"
        "The figures are unaudited.\n"
        "No default or restructuring has occurred as of April 30, 2026."
    ),
}
MARKET2_PAGES = {
    "page:1": (
        "SYNTHETIC LOAN MARKET DESK\n"
        "Secondary loan quotation sheet\n"
        "Published April 30, 2026. Quotations are as of the close on April 29, 2026.\n"
        "This invented case is test data, not evidence about a real issuer.\n"
        "Instrument: Northbridge Term Loan, the senior secured term loan of Northbridge Synthetic Group, "
        "with final maturity on December 31, 2029.\n"
        "Dealer quotation on April 29, 2026: bid 98.00 and offer 98.75, expressed as a percentage of par.\n"
        "The quotation comes from one dealer."
    ),
}
PAGES = {
    "identity": IDENT_PAGES,
    "prior_case": PRIOR_PAGES,
    "update": UPDATE_PAGES,
    "market_update": MARKET2_PAGES,
}
SHA = {
    "identity": fin_src["identity"]["sha256"],
    "prior_case": page_sha(list(PRIOR_PAGES.values())),
    "update": page_sha(list(UPDATE_PAGES.values())),
    "market_update": page_sha(list(MARKET2_PAGES.values())),
}
NAMES = {
    "identity": fin_src["identity"]["name"],
    "prior_case": "Prior Case record",
    "update": "Quarterly update note",
    "market_update": "Third-party loan market quotation sheet (April 2026)",
}
AUTHORITY = {"identity": "issuer", "prior_case": "unknown", "update": "issuer", "market_update": "third_party"}
LIM_PRIOR = "The Prior Case record is a supplied file of unknown authority; its authenticity is its hash only."
LIM_UPDATE = "The quarterly update figures are unaudited."
SYN_LIM = "Synthetic test source (invented); not an issuer or market fact."
LIMIT = {"identity": None, "prior_case": SYN_LIM, "update": SYN_LIM, "market_update": SYN_LIM}
SYN_LABEL = "This invented case is test data, not evidence about a real issuer."
for _sid in ("prior_case", "update", "market_update"):
    for _loc, _txt in PAGES[_sid].items():
        assert SYN_LABEL in _txt, (_sid, _loc, "synthetic label missing")
DECISION_SOURCE = "prior_case"
OUTCOME_SOURCES = ("update", "market_update")
SCOPE_SOURCES = ("prior_case", "update", "market_update")  # the fixed host-side scope of the step (D9)

# The consistency of the market-update sheet with the frozen sheet: same dealer desk, instrument and maturity.
for _line in ("Instrument: Northbridge Term Loan, the senior secured term loan of Northbridge Synthetic Group, "
              "with final maturity on December 31, 2029.", "The quotation comes from one dealer."):
    assert _line in MARKET_PAGES["page:1"] and _line in MARKET2_PAGES["page:1"], _line


def Q(sid, locator, quote):
    assert norm(quote) in norm(PAGES[sid][locator]), (sid, locator, quote)
    return {"source_id": sid, "locator": locator, "quote": quote}


def cite(sid, locator, quote):
    return {**Q(sid, locator, quote), "source_sha256": SHA[sid]}


# --- Decimal conventions ------------------------------------------------------------------------------
def qz(x, places):
    return x.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def dstr(x):
    return None if x is None else format(x, "f")


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


NUM_RE = re.compile(r"^[0-9]{1,3}\.[0-9]{2}$")


def token_once(value_text, quote):
    return len(re.findall(r"(?<![0-9.])" + re.escape(value_text) + r"(?![0-9]|\.[0-9])", quote)) == 1


def spell(amount, unit, decimals):
    """Product spelling of a known numeric fact (display.py _number; report_view.fact_spelling)."""
    a = Decimal(amount)
    if unit == "MULTIPLE":
        places = 2 if decimals is None else decimals
        r = qz(a, places)
        body = f"{r.copy_abs():,.{places}f}"
        return (f"({body})" if r < 0 else body) + "x"
    if unit == "decimal_fraction":
        places = 1 if decimals is None else decimals
        r = qz(a * 100, places)
        body = f"{r.copy_abs():,.{places}f}"
        return (f"({body})" if r < 0 else body) + "%"
    return format(a, "f") + {"days": " days", "decisions": " decisions", "attributions": " attributions",
                             "metrics": " metrics", "basis_points": " bp"}[unit]


def figure_unit(unit):
    """report_view.figure_unit for the units used here (the token a {ref|unit} reference may carry)."""
    return {"MULTIPLE": "x", "decimal_fraction": "%", "days": "days", "decisions": "decisions",
            "attributions": "attributions", "metrics": "metrics", "basis_points": "bp"}[unit]


# --- vocabularies -----------------------------------------------------------------------------------------
ACTION_BIASES = ("Overweight", "Neutral", "Underweight", "Insufficient Information")  # cp6_committee.ACTION_BIASES
CONFIDENCES = ("Insufficient Information", "Low", "Medium", "High")  # cp6_committee.CONFIDENCES
LABELS6 = ("Thesis Confirmed", "Flagged Risk Materialized", "Unflagged Risk Materialized", "Right for Wrong Reason",
           "Premature / Mistimed", "Insufficient Information")  # r14 CP-8 attribution taxonomy
LEVELS = ("High", "Medium", "Low")
PROCESS = ("Y", "N", "Not assessed")
METRICS = ("total_leverage", "interest_cover", "loan_mid")
SIZE_METRICS = ("total_leverage", "interest_cover")  # the measures a recorded downside size can name
COMPARATORS = ("above", "below")
SIZE_LABEL = {"total_leverage": "total leverage", "interest_cover": "interest cover"}
OBS_METRICS = ("total_leverage", "interest_cover", "loan_bid", "loan_offer")
METRIC_NAME = {"total_leverage": "Total leverage", "interest_cover": "Interest cover",
               "loan_mid": "Mid level of the term loan quotation", "loan_bid": "Dealer bid", "loan_offer": "Dealer offer"}
OBS_UNIT = {"total_leverage": ("MULTIPLE", 2), "interest_cover": ("MULTIPLE", 2),
            "loan_bid": ("decimal_fraction", 2), "loan_offer": ("decimal_fraction", 2)}
GATE_MIN = 3  # r14 REF_CP-8_06: at least 3 comparable decisions
MODULE_IDS = [m["module_id"] for m in METH]
PROHIBITED = ("blame", "fault", "should have", "in hindsight", "with hindsight", "recommend", "overweight",
              "underweight", "buy", "sell", "adjust the prior")
PROHIBITED_RE = re.compile(r"(?<![A-Za-z])(?:" + "|".join(PROHIBITED) + r")|calibrat", re.I)
COMMON_UNREAD = "Cited page not read through read_pages"  # live/tools.py UNREAD_PAGE
UNBACKED_ABSENCE = "Absence claim without a recorded search"  # live/tools.py UNBACKED_ABSENCE


# --- the validator (independent transcription of the lease's rules) --------------------------------------
def digit_free(path, text, issues):
    if text is None:
        return
    if not text.strip():
        issues.append(f"{path}: text is empty")
    elif any(ch.isnumeric() for ch in text):
        issues.append(f"{path}: digits are not allowed")
    elif re.search(r"[{}\[\]]", text):
        issues.append(f"{path}: reference syntax is not allowed")
    elif PROHIBITED_RE.search(text):
        issues.append(f"{path}: prohibited conclusion: {PROHIBITED_RE.search(text).group(0).lower()}")


def prefix(quote):
    """readiness.citation_issues quote fragment (quotes.prefix): normalised, cut at 200 characters on a word boundary."""
    n = norm(quote).strip()
    if len(n) <= 200:
        return n
    cut = n.rfind(" ", 0, 201)
    return n[: cut if cut > 0 else 200] + "\u2026"


def quote_not_found(sid, loc, quote):
    """The product wording of readiness.citation_issues for a quote that is not on its page (probed: r03, r54).
    The label 'normalised whitespace, quote marks and dashes' is the one quotes.explain prints when no class
    (case variant, column interleave, page straddle) applies; the first two are asserted absent here, the
    third is not modelled (the pages carry no running header or footer) and is covered by the product probe."""
    page, n = norm(PAGES[sid][loc]), norm(quote)
    assert n.lower() not in page.lower(), (sid, loc, "a case variant: the product would name it")
    words = n.split(" ")
    for k in range(len(words) - 2, 1, -1):
        first, rest = " ".join(words[:k]), " ".join(words[k:])
        at = page.find(first)
        assert not (at >= 0 and rest in page[at + len(first):]), (sid, loc, "a column interleave: the product would name it")
    return (f"Quote/locator mismatch: quote not found under {sid} {loc} "
            f'(normalised whitespace, quote marks and dashes): "{prefix(quote)}"')


def ref_ok(path, ref, pack_ids, only=None):
    """Citation issues. Source, locator and quote failures carry the product wording of readiness.citation_issues
    (no path, as the CP-DR lease); the scope and the must-cite rules are this oracle's (a host rule, not a pack fact)."""
    sid, loc = ref["source_id"], ref["locator"]
    if sid not in pack_ids:
        return [f"Unavailable or changed source: {sid}"]
    if sid not in SCOPE_SOURCES:
        return [f"{path}: source {sid} is outside the CP-8 scope"]
    if only is not None and sid != only:
        return [f"{path}: must cite {only}"]
    if loc not in PAGES[sid]:
        return [f'Quote/locator mismatch: no locator {loc} in {sid}: "{prefix(ref["quote"])}"']
    if norm(ref["quote"]) not in norm(PAGES[sid][loc]):
        return [quote_not_found(sid, loc, ref["quote"])]
    return []


def labelled(metric, value, quote):
    q_ = norm(quote)
    if metric in ("total_leverage", "interest_cover"):
        lab = "total leverage" if metric == "total_leverage" else "interest cover"
        i = q_.lower().find(lab)
        if i < 0:
            return False
        m = re.search(r"[0-9]+\.[0-9]+x", q_[i + len(lab):])
        return bool(m) and m.group(0) == value + "x"
    lab = "bid " if metric == "loan_bid" else "offer "
    i = q_.lower().find(lab)
    if i < 0:
        return False
    m = re.search(r"[0-9]+\.[0-9]+", q_[i + len(lab):])
    return bool(m) and m.group(0) == value


def breach_of(size, value):
    """Python decides whether a recorded downside size is breached: strictly beyond the level
    ("above": value > level; "below": value < level). None when no size or no value exists."""
    if size is None or value is None:
        return None
    comparator, level = size
    return value > level if comparator == "above" else value < level


def compared_of(sub):
    """Metrics with an expected and a realized value (loan_mid needs bid and offer on both sides)."""
    have = {(o["side"], o["metric"]) for o in sub["observations"]}
    out = []
    for m in METRICS:
        parts = ("loan_bid", "loan_offer") if m == "loan_mid" else (m,)
        if all((s, p) in have for s in ("expected", "realized") for p in parts):
            out.append(m)
    return out


def authority_of(sid):
    return AUTHORITY[sid]


def check_submission(sub, pack_ids):
    """Issues of the validator, in rule order (journaled: an invalid step consumes the attempt)."""
    issues = []
    dec = sub["decision"]
    ddate = None
    for fld in ("action_bias", "confidence", "instrument", "decision_date", "decision_maker_role", "posture", "size"):
        item = dec[fld]
        path = f"decision.{fld}"
        if "absence" in item and "text" in item:
            issues.append(f"{path}: exactly one of text and absence is required")
            continue
        if "absence" in item:
            if fld not in ("posture", "size"):
                issues.append(f"{path}: a required decision field cannot be absent")
                continue
            a = item["absence"]
            digit_free(f"{path}.absence.reason", a["reason"], issues)
            digit_free(f"{path}.absence.follow_up", a["follow_up"], issues)
            if a.get("quote"):
                issues += ref_ok(f"{path}.absence.quote", a["quote"], pack_ids, DECISION_SOURCE)
            continue
        found = ref_ok(f"{path}.quote", item["quote"], pack_ids, DECISION_SOURCE)
        if found:
            issues += found
            continue
        text = item["text"]
        if fld == "action_bias" and text not in ACTION_BIASES:
            issues.append(f"{path}: {text} is not one of {', '.join(ACTION_BIASES)}")
        elif fld == "confidence" and text not in CONFIDENCES:
            issues.append(f"{path}: {text} is not one of {', '.join(CONFIDENCES)}")
        elif text not in item["quote"]["quote"]:
            issues.append(f"{path}: text {text} does not occur in the quote")
        elif fld == "decision_date":
            ddate = parse_date(text)
            if ddate is None:
                issues.append(f"{path}: text {text} is not a date (Month D, YYYY)")
    th = sub["thesis"]
    for fld in ("thesis", "greatest_uncertainty", "downside_paths", "exit_trigger", "expected_spread_return",
                "expected_rating_path", "expected_hold"):
        item = th[fld]
        path = f"thesis.{fld}"
        if "absence" in item and "quote" in item:
            issues.append(f"{path}: exactly one of quote and absence is required")
        elif "absence" in item:
            if fld in ("thesis", "greatest_uncertainty", "downside_paths"):
                issues.append(f"{path}: a required thesis field cannot be absent")
                continue
            a = item["absence"]
            digit_free(f"{path}.absence.reason", a["reason"], issues)
            digit_free(f"{path}.absence.follow_up", a["follow_up"], issues)
            if a.get("quote"):
                issues += ref_ok(f"{path}.absence.quote", a["quote"], pack_ids, DECISION_SOURCE)
        else:
            issues += ref_ok(f"{path}.quote", item["quote"], pack_ids, DECISION_SOURCE)
    # recorded downside sizes (S3): each names a measure, a comparator and a level inside a span of the
    # recorded downside paths; size_state[metric] is (comparator, level) when valid, None when reported invalid
    down = th["downside_paths"].get("quote", {}).get("quote", "")
    size_state = {}
    for i, z in enumerate(th["downside_sizes"]):
        p = f"thesis.downside_sizes[{i}]"
        m, cmpr, lt = z["metric_id"], z["comparator"], z["level_text"]
        if m not in SIZE_METRICS:
            issues.append(f"{p}: metric {m} is not one of {', '.join(SIZE_METRICS)}")
            continue
        if m in size_state:
            issues.append(f"thesis.downside_sizes: {m} appears more than once")
            continue
        size_state[m] = None
        if cmpr not in COMPARATORS:
            issues.append(f"{p}: comparator {cmpr} is not one of {', '.join(COMPARATORS)}")
            continue
        found = ref_ok(f"{p}.quote", z["quote"], pack_ids, DECISION_SOURCE)
        if found:
            issues += found
            continue
        zq = z["quote"]["quote"]
        if norm(zq) not in norm(down):
            issues.append(f"{p}.quote: not a span of the recorded downside paths")
        elif not NUM_RE.match(lt) or not token_once(lt, zq):
            issues.append(f"{p}: level_text {lt} does not occur in the quote")
        elif f"{SIZE_LABEL[m]} {cmpr} {lt}x" not in norm(zq).lower():
            issues.append(f"{p}: quote does not state {SIZE_LABEL[m]} {cmpr} {lt}x")
        else:
            size_state[m] = (cmpr, Decimal(lt))
    obs = sub["observations"]
    seen = {}
    for i, o in enumerate(obs):
        p = f"observations[{i}]"
        key = (o["side"], o["metric"])
        if o["side"] not in ("expected", "realized"):
            issues.append(f"{p}: side {o['side']} is not expected or realized")
            continue
        if o["metric"] not in OBS_METRICS:
            issues.append(f"{p}: metric {o['metric']} is not one of {', '.join(OBS_METRICS)}")
            continue
        if key in seen:
            issues.append(f"observations: ({o['side']}, {o['metric']}) appears more than once")
            continue
        sid = o["quote"]["source_id"]
        if o["side"] == "expected":
            found = ref_ok(f"{p}.quote", o["quote"], pack_ids, DECISION_SOURCE)
        else:
            found = ref_ok(f"{p}.quote", o["quote"], pack_ids)
            if not found and sid == DECISION_SOURCE:
                found = [f"{p}.quote: a realized observation cannot cite {DECISION_SOURCE}"]
            if not found:
                want = "third_party" if o["metric"] in ("loan_bid", "loan_offer") else "issuer"
                if authority_of(sid) != want:
                    found = [f"{p}: {o['metric']} needs {'an' if want[0] in 'aeiou' else 'a'} {want} source, {sid} is {authority_of(sid)} (CP-0 T3)"]
        if found:
            issues += found
            continue
        v = o["value_text"]
        if not NUM_RE.match(v) or not token_once(v, o["quote"]["quote"]):
            issues.append(f"{p}: value_text {v} does not occur in the quote")
            continue
        if not labelled(o["metric"], v, o["quote"]["quote"]):
            issues.append(f"{p}: {o['metric']} value_text {v} is not labelled {o['metric']} in the quote")
            continue
        at = o["as_of_text"]
        if at not in o["quote"]["quote"] or parse_date(at) is None:
            issues.append(f"{p}: as_of_text {at} does not occur in the quote")
            continue
        if o["side"] == "realized" and ddate is not None and parse_date(at) <= ddate:
            issues.append(f"{p}: realized as_of {at} is not after the decision date")
            continue
        seen[key] = Decimal(v)
    for side in ("expected", "realized"):
        if ("loan_bid" in {m for s, m in seen if s == side}) != ("loan_offer" in {m for s, m in seen if s == side}):
            issues.append(f"observations: {side} loan_bid and loan_offer must be given together")
        elif (side, "loan_bid") in seen and seen[(side, "loan_bid")] > seen[(side, "loan_offer")]:
            issues.append(f"observations: {side} bid exceeds offer")
    has_real = any(s == "realized" for s, _ in seen) or any(o["side"] == "realized" for o in obs)
    ab = sub.get("outcome_absence")
    if has_real and ab:
        issues.append("observations: realized observations and outcome_absence are mutually exclusive")
    elif not has_real and not ab:
        issues.append("observations: no realized observation and no outcome_absence")
    if ab:
        digit_free("outcome_absence.reason", ab["reason"], issues)
        digit_free("outcome_absence.follow_up", ab["follow_up"], issues)
    inc = sub["default_restructuring"]
    if has_real and ab:
        pass  # reported above
    elif inc is not None and ab:
        issues.append("default_restructuring: not allowed together with outcome_absence")
    elif inc is None and has_real:
        issues.append("default_restructuring: required when a realized outcome is given")
    elif inc is not None:
        found = ref_ok("default_restructuring.quote", inc["quote"], pack_ids)
        if not found and authority_of(inc["quote"]["source_id"]) != "issuer":
            found = [f"default_restructuring: needs an issuer source, {inc['quote']['source_id']} is "
                     f"{authority_of(inc['quote']['source_id'])} (CP-0 T3)"]
        if found:
            issues += found
        elif not re.search(r"default|restructuring", norm(inc["quote"]["quote"]).lower()):
            issues.append("default_restructuring.quote: does not state default or restructuring incidence")
        else:
            at = inc["as_of_text"]
            if at not in inc["quote"]["quote"] or parse_date(at) is None:
                issues.append(f"default_restructuring: as_of_text {at} does not occur in the quote")
            elif ddate is not None and parse_date(at) <= ddate:
                issues.append(f"default_restructuring: as_of {at} is not after the decision date")
    comp = compared_of(sub)
    conf = {c["metric_id"]: c["level"] for c in sub["confidence"]}
    for i, c in enumerate(sub["confidence"]):
        if c["metric_id"] not in comp:
            issues.append(f"confidence[{i}]: {c['metric_id']} is not a compared metric")
        elif c["level"] not in LEVELS:
            issues.append(f"confidence[{i}]: {c['level']} is not one of {', '.join(LEVELS)}")
    for m in comp:
        if m not in conf:
            issues.append(f"confidence: no confidence for {m}")
    attrs = sub["attributions"]
    named = [a["metric_id"] for a in attrs]
    for i, a in enumerate(attrs):
        p = f"attributions[{i}]"
        if a["metric_id"] not in comp and a["metric_id"] != "overall":
            issues.append(f"{p}: {a['metric_id']} is not a compared metric or overall")
            continue
        if named.count(a["metric_id"]) > 1:
            issues.append(f"attributions: {a['metric_id']} appears more than once")
            continue
        lab = a["label"]
        if lab not in LABELS6:
            issues.append(f"{p}: label {lab} is not one of {', '.join(LABELS6)}")
            continue
        digit_free(f"{p}.basis", a["basis"], issues)
        if a["process_sound"] not in PROCESS:
            issues.append(f"{p}: process_sound {a['process_sound']} is not one of {', '.join(PROCESS)}")
        elif lab == "Insufficient Information" and a["process_sound"] != "Not assessed":
            issues.append(f"{p}: Insufficient Information requires process_sound Not assessed")
        elif lab != "Insufficient Information" and a["process_sound"] == "Not assessed":
            issues.append(f"{p}: {lab} cannot have process_sound Not assessed")
        elif lab == "Flagged Risk Materialized" and a["process_sound"] != "Y":
            issues.append(f"{p}: Flagged Risk Materialized requires process_sound Y")
        elif lab == "Unflagged Risk Materialized" and a["process_sound"] != "N":
            issues.append(f"{p}: Unflagged Risk Materialized requires process_sound N")
        if lab == "Flagged Risk Materialized":
            if not a.get("flag_quote"):
                issues.append(f"{p}: Flagged Risk Materialized needs flag_quote")
            elif norm(a["flag_quote"]) not in norm(down):
                issues.append(f"{p}.flag_quote: not a span of the recorded downside paths")
        elif a.get("flag_quote"):
            issues.append(f"{p}: flag_quote is only for Flagged Risk Materialized")
        if lab == "Flagged Risk Materialized" and a["metric_id"] != "overall":
            m = a["metric_id"]
            if m not in size_state:
                issues.append(f"{p}: Flagged Risk Materialized needs a recorded downside size for {m}")
            # a metric whose realized observation was itself reported invalid has no value: its own issue stands
            elif size_state[m] is not None and ("realized", m) in seen and not breach_of(size_state[m], seen[("realized", m)]):
                issues.append(f"{p}: Flagged Risk Materialized needs the downside size breached, "
                              f"but {m} {format(seen[('realized', m)], 'f')} is not {size_state[m][0]} {format(size_state[m][1], 'f')}x")
        elif lab == "Flagged Risk Materialized" and comp:
            if not any(b["label"] == "Flagged Risk Materialized" and b["metric_id"] != "overall"
                       and size_state.get(b["metric_id"]) is not None
                       and breach_of(size_state[b["metric_id"]], seen.get(("realized", b["metric_id"])))
                       for b in attrs):
                issues.append(f"{p}: Flagged Risk Materialized overall needs at least one flagged metric with a breached downside size")
        if lab == "Unflagged Risk Materialized":
            if not a.get("originating_module"):
                issues.append(f"{p}: Unflagged Risk Materialized needs originating_module")
            elif a["originating_module"] not in MODULE_IDS:
                issues.append(f"{p}: originating_module {a['originating_module']} is not a methodology module")
        elif a.get("originating_module"):
            issues.append(f"{p}: originating_module is only for Unflagged Risk Materialized")
    for m in comp + ["overall"]:
        if m not in named:
            issues.append(f"attributions: no attribution for {m}")
    ov = next((a for a in attrs if a["metric_id"] == "overall"), None)
    if ov is not None and not comp and ov["label"] != "Insufficient Information":
        issues.append("attributions[overall]: with no compared metric the label must be Insufficient Information")
    lessons = sub["lessons"]
    if len(lessons) > 2:
        issues.append("lessons: at most 2 lessons")
    for i, x in enumerate(lessons):
        p = f"lessons[{i}]"
        digit_free(f"{p}.lesson", x["lesson"], issues)
        if not x["metric_ids"] or any(m not in comp for m in x["metric_ids"]):
            issues.append(f"{p}: metric_ids must name compared metrics")
    for i, g in enumerate(sub["extra_gaps"]):
        for k in ("gap", "missing_item", "why_it_matters", "impact_on_output", "follow_up"):
            digit_free(f"extra_gaps[{i}].{k}", g[k], issues)
    digit_free("synthesis.text", sub["synthesis"]["text"], issues)
    return issues


def refs_of(sub):
    """Every quote reference of a literal in order of first appearance."""
    out = []

    def add(ref):
        if ref is not None and ref not in out:
            out.append(ref)

    dec, th = sub["decision"], sub["thesis"]
    for f in ("action_bias", "confidence", "instrument", "decision_date", "decision_maker_role", "posture", "size"):
        add(dec[f].get("quote") or dec[f].get("absence", {}).get("quote"))
    for f in ("thesis", "greatest_uncertainty", "downside_paths", "exit_trigger", "expected_spread_return",
              "expected_rating_path", "expected_hold"):
        add(th[f].get("quote") or th[f].get("absence", {}).get("quote"))
    for z in th["downside_sizes"]:
        add(z["quote"])
    for o in sub["observations"]:
        add(o["quote"])
    if sub["default_restructuring"] is not None:
        add(sub["default_restructuring"]["quote"])
    return out


def cited_pages(sub):
    seen = []
    for r in refs_of(sub):
        k = (r["source_id"], r["locator"])
        if k not in seen:
            seen.append(k)
    return seen


def absence_paths(sub):
    out = [f"decision.{f}.absence" for f in ("posture", "size") if "absence" in sub["decision"][f]]
    out += [f"thesis.{f}.absence" for f in ("exit_trigger", "expected_spread_return", "expected_rating_path",
                                            "expected_hold") if "absence" in sub["thesis"][f]]
    if sub.get("outcome_absence"):
        out.append("outcome_absence")
    return out


def tool_rule_issues(sub, read, searched):
    """RULES(text, seen) result in ToolRules order: the absence rule, then unread citations in the product's
    sorted (source_id, locator) order (live/tools.py unread_citation_issues)."""
    out = [UNBACKED_ABSENCE] if absence_paths(sub) and not searched else []
    out += [f"{COMMON_UNREAD}: {s} {loc}" for s, loc in sorted(cited_pages(sub)) if (s, loc) not in read]
    return out


# --- literal submissions ----------------------------------------------------------------------------------------
P1, P2 = "page:1", "page:2"
QD = "Decision: Neutral action bias with Medium confidence on the Northbridge Term Loan."
Q_DATE = "Recorded at Approval on January 10, 2026."
Q_ROLE = "Decision-maker role: Investment Committee."
Q_NOREC1 = "Portfolio posture and position size were not recorded."
Q_THESIS = ("Thesis as decided: The credit is sound on reported figures and the single dealer quotation sits just "
            "below par.")
Q_UNC = "Greatest uncertainty as decided: Thin market evidence from one dealer quotation."
Q_LEV0 = f"Total leverage recorded at Approval on January 10, 2026 was {LEV_AT_DECISION}x."
Q_COV0 = f"Interest cover recorded at Approval on January 10, 2026 was {COVER_AT_DECISION}x."
Q_QUOTE0 = ("Dealer quotation recorded at Approval, as of January 9, 2026: bid 98.50 and offer 99.25, expressed as a "
            "percentage of par.")
Q_DOWN = ("Downside paths named: weaker unaudited earnings, sized as total leverage above 1.75x or interest cover below "
          "5.75x; and liquidity that depends on steady cash generation.")
FLAG_LEV = "weaker unaudited earnings, sized as total leverage above 1.75x"
FLAG_COV = "interest cover below 5.75x"
FLAG_ALL = "weaker unaudited earnings, sized as total leverage above 1.75x or interest cover below 5.75x"
SIZE_LEV = "total leverage above 1.75x"
SIZE_COV = "interest cover below 5.75x"  # the two sizes stated in Q_DOWN (FLAG_COV is the same span)
Q_EXIT = "Exit trigger recorded: a sharp move in the quotation. No threshold was recorded."
Q_NOREC2 = "Expected spread or return, expected rating path and expected holding period were not recorded."
Q_LEV_PRE = "Total leverage for the twelve months to December 31, 2025 was reported as 1.67x."
Q_NODEF_PRE = "No default or restructuring had occurred as of December 31, 2025."
Q_LEV_FEB = "Total leverage for the twelve months to February 28, 2026 was reported as 1.70x."
Q_LEV1 = "Total leverage for the twelve months to March 31, 2026 is reported as 1.80x."
Q_COV1 = "Interest cover for the twelve months to March 31, 2026 is reported as 5.50x."
Q_QUOTE1 = "Dealer quotation on April 29, 2026: bid 98.00 and offer 98.75, expressed as a percentage of par."
Q_NODEF = "No default or restructuring has occurred as of April 30, 2026."


def L(text, ref):
    return {"text": text, "quote": ref}


def A(ref, reason, follow_up):
    return {"absence": {"quote": ref, "reason": reason, "follow_up": follow_up}}


def OB(side, metric, value, as_of, ref):
    return {"side": side, "metric": metric, "value_text": value, "as_of_text": as_of, "quote": ref}


def decision_block():
    qd = Q(DECISION_SOURCE, P1, QD)
    nr = Q(DECISION_SOURCE, P1, Q_NOREC1)
    return {
        "action_bias": L("Neutral", qd),
        "confidence": L("Medium", qd),
        "instrument": L("Northbridge Term Loan", qd),
        "decision_date": L("January 10, 2026", Q(DECISION_SOURCE, P1, Q_DATE)),
        "decision_maker_role": L("Investment Committee", Q(DECISION_SOURCE, P1, Q_ROLE)),
        "posture": A(nr, "The Prior Case record states that the portfolio posture was not recorded",
                     "Obtain the portfolio posture from the committee minutes"),
        "size": A(nr, "The Prior Case record states that the position size was not recorded",
                  "Obtain the position size from the committee minutes"),
    }


def thesis_block():
    nr2 = Q(DECISION_SOURCE, P2, Q_NOREC2)
    return {
        "thesis": {"quote": Q(DECISION_SOURCE, P1, Q_THESIS)},
        "greatest_uncertainty": {"quote": Q(DECISION_SOURCE, P1, Q_UNC)},
        "downside_paths": {"quote": Q(DECISION_SOURCE, P2, Q_DOWN)},
        "downside_sizes": [
            {"metric_id": "total_leverage", "comparator": "above", "level_text": "1.75", "quote": Q(DECISION_SOURCE, P2, SIZE_LEV)},
            {"metric_id": "interest_cover", "comparator": "below", "level_text": "5.75", "quote": Q(DECISION_SOURCE, P2, SIZE_COV)},
        ],
        "exit_trigger": {"quote": Q(DECISION_SOURCE, P2, Q_EXIT)},
        "expected_spread_return": A(nr2, "The Prior Case record states that no expected spread or return was recorded",
                                    "Obtain the expected return from the committee minutes"),
        "expected_rating_path": A(nr2, "The Prior Case record states that no expected rating path was recorded",
                                  "Obtain the expected rating path from the committee minutes"),
        "expected_hold": A(nr2, "The Prior Case record states that no expected holding period was recorded",
                           "Obtain the expected holding period from the committee minutes"),
    }


def expected_obs():
    return [
        OB("expected", "total_leverage", LEV_AT_DECISION, "January 10, 2026", Q(DECISION_SOURCE, P2, Q_LEV0)),
        OB("expected", "interest_cover", COVER_AT_DECISION, "January 10, 2026", Q(DECISION_SOURCE, P2, Q_COV0)),
        OB("expected", "loan_bid", "98.50", "January 9, 2026", Q(DECISION_SOURCE, P2, Q_QUOTE0)),
        OB("expected", "loan_offer", "99.25", "January 9, 2026", Q(DECISION_SOURCE, P2, Q_QUOTE0)),
    ]


def realized_obs():
    return [
        OB("realized", "total_leverage", "1.80", "March 31, 2026", Q("update", P1, Q_LEV1)),
        OB("realized", "interest_cover", "5.50", "March 31, 2026", Q("update", P1, Q_COV1)),
        OB("realized", "loan_bid", "98.00", "April 29, 2026", Q("market_update", P1, Q_QUOTE1)),
        OB("realized", "loan_offer", "98.75", "April 29, 2026", Q("market_update", P1, Q_QUOTE1)),
    ]


EXTRA_GAPS = [
    {"gap": "No tolerance was recorded for the leverage and cover expectations",
     "why_it_matters": "A drift cannot be called a breach or a normal movement without a recorded tolerance",
     "impact_on_output": "The attribution rests on direction of movement, not on a breach of a stated limit",
     "missing_item": "Tolerance for the leverage and cover expectations",
     "follow_up": "Record a tolerance for each expectation at the next Approval"},
    {"gap": "No threshold was recorded for the exit trigger",
     "why_it_matters": "Exit discipline cannot be judged when a sharp move has no stated size",
     "impact_on_output": "The quotation move is not attributed",
     "missing_item": "Size of the exit trigger",
     "follow_up": "Record a size for the exit trigger at the next Approval"},
]


def literal_positive():
    return {
        "decision": decision_block(),
        "thesis": thesis_block(),
        "observations": expected_obs() + realized_obs(),
        "outcome_absence": None,
        "default_restructuring": {"as_of_text": "April 30, 2026", "quote": Q("update", P1, Q_NODEF)},
        "confidence": [{"metric_id": "total_leverage", "level": "Medium"},
                       {"metric_id": "interest_cover", "level": "Medium"},
                       {"metric_id": "loan_mid", "level": "Low"}],
        "attributions": [
            {"metric_id": "total_leverage", "label": "Flagged Risk Materialized", "process_sound": "Y",
             "originating_module": None,
             "basis": "Leverage moved up against the recorded expectation and beyond the size named for the flagged downside path",
             "flag_quote": FLAG_LEV},
            {"metric_id": "interest_cover", "label": "Flagged Risk Materialized", "process_sound": "Y",
             "originating_module": None,
             "basis": "Interest cover moved down against the recorded expectation and beyond the size named for the flagged downside path",
             "flag_quote": FLAG_COV},
            {"metric_id": "loan_mid", "label": "Insufficient Information", "process_sound": "Not assessed",
             "originating_module": None,
             "basis": "The exit trigger records no threshold, so whether the quotation moved sharply cannot be judged",
             "flag_quote": None},
            {"metric_id": "overall", "label": "Flagged Risk Materialized", "process_sound": "Y",
             "originating_module": None,
             "basis": "Two of the three compared measures moved against the recorded expectation and beyond the sizes named for the flagged downside path",
             "flag_quote": FLAG_ALL},
        ],
        "lessons": [{"lesson": "A recorded expectation of stable leverage and cover needs an explicit tolerance so that a later drift can be judged against it",
                     "metric_ids": ["total_leverage", "interest_cover"]}],
        "extra_gaps": copy.deepcopy(EXTRA_GAPS),
        "synthesis": {"text": "Leverage and interest cover moved against the expectations recorded at Approval and beyond the sizes the record named for its flagged downside, so the decision is judged a flagged risk with a sound process; timing and exit discipline cannot be judged because the record holds no exit threshold and no holding plan"},
    }


def literal_no_outcome():
    lit = literal_positive()
    lit["observations"] = expected_obs()
    lit["default_restructuring"] = None
    lit["outcome_absence"] = {"reason": "No post-decision outcome source is in the pack",
                              "follow_up": "Supply the next issuer update and a dated dealer quotation"}
    lit["confidence"] = []
    lit["attributions"] = [{
        "metric_id": "overall", "label": "Insufficient Information", "process_sound": "Not assessed",
        "originating_module": None,
        "basis": "No realized outcome is available to compare with the recorded expectations", "flag_quote": None}]
    lit["lessons"] = []
    lit["synthesis"] = {"text": "No realized outcome is available, so the recorded decision and its expectations stand as the contemporaneous record and no attribution is made; the observation window is open or no outcome source was supplied"}
    return lit


LITERALS = {"positive": literal_positive(), "no_outcome": literal_no_outcome()}
PACK_IDS = {
    "positive": ["identity", "prior_case", "update", "market_update"],
    "no_outcome": ["identity", "prior_case"],
    "no_record": ["identity", "update", "market_update"],
}
RUNS = {"positive": "slice-cp8-positive", "no_outcome": "slice-cp8-no-outcome", "no_record": "slice-cp8-no-record"}
for _c, _lit in LITERALS.items():
    _iss = check_submission(_lit, PACK_IDS[_c])
    assert not _iss, (_c, _iss)


# --- composer (Decimal) --------------------------------------------------------------------------------------------
def inputs_of(sub, records):
    exp, real, exp_asof, real_asof = {}, {}, {}, {}
    for o in sub["observations"]:
        d = Decimal(o["value_text"])
        (exp if o["side"] == "expected" else real)[o["metric"]] = d
        (exp_asof if o["side"] == "expected" else real_asof)[o["metric"]] = parse_date(o["as_of_text"])
    ddate = parse_date(sub["decision"]["decision_date"]["text"])
    ov = next(a for a in sub["attributions"] if a["metric_id"] == "overall")["label"]
    sizes = {z["metric_id"]: (z["comparator"], Decimal(z["level_text"])) for z in sub["thesis"]["downside_sizes"]}
    return {"exp": exp, "real": real, "exp_asof": exp_asof, "real_asof": real_asof, "decision_date": ddate,
            "sizes": sizes, "records": records, "overall": ov, "labels": [a["label"] for a in sub["attributions"] if a["metric_id"] != "overall"]}


def direction(v):
    return "Higher" if v > 0 else "Lower" if v < 0 else "Unchanged"


def derive(inp):
    """Every derived value, exact Decimal; None marks a value that cannot be calculated (never 0)."""
    exp, real = inp["exp"], inp["real"]
    out = {}
    for m in ("total_leverage", "interest_cover"):
        out[m] = {"expected": exp.get(m), "realized": real.get(m)}
    for side, vals in (("expected", exp), ("realized", real)):
        bo = (vals.get("loan_bid"), vals.get("loan_offer"))
        out.setdefault("loan_mid", {})[side] = ((bo[0] + bo[1]) / 2 / 100) if None not in bo else None
    for m in METRICS:
        e, r = out[m]["expected"], out[m]["realized"]
        out[m]["variance"] = (r - e) if None not in (e, r) else None
        out[m]["direction"] = direction(out[m]["variance"]) if out[m]["variance"] is not None else None
        out[m]["magnitude"] = abs(out[m]["variance"]) if out[m]["variance"] is not None else None
    # the quotation moves in points of par: shown in basis points of par (product unit basis_points), exact
    mid_mag = out["loan_mid"]["magnitude"]
    out["loan_mid"]["magnitude_bp"] = (mid_mag * 10000).normalize() if mid_mag is not None else None
    # Python decides the breach of a recorded downside size (strictly beyond the level); null when no size or no
    # realized value exists, and always null for the quotation (no size can be recorded for it)
    for m in METRICS:
        out[m]["downside_breach"] = breach_of(inp["sizes"].get(m) if m in SIZE_METRICS else None, real.get(m))
    dates = list(inp["real_asof"].values())
    out["window_days"] = (max(dates) - inp["decision_date"]).days if dates else None
    out["window_end"] = max(dates) if dates else None
    out["compared"] = [m for m in METRICS if out[m]["variance"] is not None]
    # nothing compared: no count exists, so the counts are missing (None), never a stored 0
    out["by_direction"] = ({d: sum(1 for m in out["compared"] if out[m]["direction"] == d)
                            for d in ("Higher", "Lower", "Unchanged")} if out["compared"] else None)
    ov = inp["overall"]
    out["labelled"] = 0 if ov == "Insufficient Information" else 1
    out["confirmed"] = 1 if ov == "Thesis Confirmed" else 0
    out["hit_rate"] = (Decimal(out["confirmed"]) / Decimal(out["labelled"])) if out["labelled"] else None
    out["distribution"] = ({lab: inp["labels"].count(lab) for lab in LABELS6} if out["compared"] else None)
    out["decisions_recorded"] = inp["records"]
    out["decisions_required"] = GATE_MIN
    return out


def stored(d):
    s = {}
    for m in METRICS:
        s[m] = {k: (dstr(v) if isinstance(v, Decimal) else v) for k, v in d[m].items()}
    s["window_days"] = d["window_days"]
    s["window_end"] = d["window_end"].isoformat() if d["window_end"] else None
    for k in ("compared", "by_direction", "labelled", "confirmed", "distribution", "decisions_recorded",
              "decisions_required"):
        s[k] = d[k]
    s["hit_rate"] = dstr(d["hit_rate"])
    return s


def current_decision_text(prior_bias, prior_conf, current):
    """The decision line of the what-changed block (D5 diff against the prior decision record).
    current is None (no CP-6 head in the run) or (action_bias, confidence) of the settled CP-6 head
    (cp6_committee T6-FINAL.final_bias.action_bias / .confidence). Returns (kind, text_or_reason)."""
    if current is None:
        return "missing", "CP-6 is not in this run, so no current decision is available to compare"
    bias, conf = current
    if bias == "Insufficient Information" or conf == "Insufficient Information":
        return "missing", "CP-6 states Insufficient Information, so there is no comparable current decision"
    b = (f"Action bias unchanged at {bias}" if bias == prior_bias
         else f"Action bias changed from {prior_bias} to {bias}")
    c = (f"confidence unchanged at {conf}" if conf == prior_conf
         else f"confidence changed from {prior_conf} to {conf}")
    return "known", f"{b}; {c}."


# --- facts and tables ----------------------------------------------------------------------------------------------
def trace(cites):
    out = []
    for c in cites:
        k = [c["source_id"], c["locator"]]
        if k not in out:
            out.append(k)
    return out


def N(amount, unit, decimals, cites=(), vc="calculated", calc=None, formula=None, per=None):
    return {"kind": "num", "per": per, "amount": dstr(amount), "unit": unit, "decimals": decimals,
            "cites": trace(cites), "vc": vc, "calc": calc, "formula": formula}


def T(text, cites=(), vc=None, calc=None):
    return {"kind": "text", "text": text, "cites": trace(cites), "vc": vc, "calc": calc}


def G(reason, unit=None, status="missing", cites=()):
    return {"kind": "gap", "reason": reason, "unit": unit, "status": status, "cites": trace(cites)}


def fact(tid, rid, field, label, c, per_q):
    f = {"fact_id": f"{tid}.{rid}.{field}", "column": label, "period": None, "amount": None, "unit": None,
         "decimals": None, "text": None, "shown": None, "status": "known", "cites": c["cites"],
         "value_class": c.get("vc"), "calculation_id": None, "formula": None, "limitation": None}
    if c["kind"] == "num":
        f.update(amount=c["amount"], period=c["per"] or per_q, unit=c["unit"], decimals=c["decimals"],
                 calculation_id=c["calc"], formula=c["formula"], shown=spell(c["amount"], c["unit"], c["decimals"]))
    elif c["kind"] == "text":
        f.update(text=c["text"], shown=c["text"], calculation_id=c.get("calc"))
    else:
        f.update(unit=c["unit"], status=c["status"], limitation=c["reason"], value_class=None,
                 shown="∅ G#" if c["status"] == "missing" else "∅ G# n.m.")
    return f


def table(tid, title, cols, rows, row_header="Item", per_q="Run as of " + RUN_AS_OF):
    out = []
    for rid, label, cells in rows:
        assert len(cells) == len(cols), (tid, rid)
        out.append({"row_id": rid, "label": label,
                    "facts": [fact(tid, rid, fld, lab, c, per_q) for (fld, lab), c in zip(cols, cells)]})
    # table shape (contracts.py:270-272, validate_tables): one fact per column in every row, in column order,
    # fact id <table>.<row>.<field>, no fact id repeated in the table
    assert len({r["row_id"] for r in out}) == len(out), tid
    seen = set()
    for r in out:
        assert len(r["facts"]) == len(cols), (tid, r["row_id"], len(r["facts"]), len(cols))
        for (fld, _lab), f in zip(cols, r["facts"]):
            assert f["fact_id"] == f"{tid}.{r['row_id']}.{fld}", (tid, r["row_id"], fld)
            assert f["fact_id"] not in seen, f["fact_id"]
            seen.add(f["fact_id"])
    return {"table_id": tid, "title": title, "row_header": row_header,
            "columns": [{"field": f, "label": l} for f, l in cols], "rows": out}


def src_label(ref):
    return f"{NAMES[ref['source_id']]}, {ref['locator']}"


def compose_case(case, sub, inp, d, cp6=None):
    """Tables, claims, limitations of one case from the literal, its inputs and derive() result."""
    s = stored(d)
    comp = d["compared"]
    obs = {(o["side"], o["metric"]): o for o in sub["observations"]}
    dec, th = sub["decision"], sub["thesis"]
    attrs = {a["metric_id"]: a for a in sub["attributions"]}
    conf = {c["metric_id"]: c["level"] for c in sub["confidence"]}
    ab = sub.get("outcome_absence")
    ddate = inp["decision_date"]
    PER_DEC = f"Recorded at Approval {ddate.isoformat()}"
    NO_OUT = (ab["reason"] if ab else None)

    def cell_l(item, vc="source"):
        return T(item["text"], [item["quote"]], vc)

    def cell_optional(item, label):
        if "absence" in item:
            a = item["absence"]
            return G(a["reason"], None, "missing", [a["quote"]] if a.get("quote") else [])
        return T(item["quote"]["quote"], [item["quote"]], "source")

    tables = []
    # Interim or Final of every realized entry: no source here states that the observation window is closed,
    # so every entry is Interim (T7.3); r14 REF_CP-8_01: Completed only when no realized entry is Interim.
    interim = {m: "Interim" for m in OBS_METRICS if ("realized", m) in obs}
    if sub["default_restructuring"] is not None:
        interim["default_restructuring"] = "Interim"
    if d["window_days"] is not None:
        interim["window"] = "Interim"
    module_status = ("Completed" if (not ab and len(comp) == len(METRICS) and "Interim" not in interim.values())
                     else "Completed with Limitations")
    # T7.1
    dd = dec["decision_date"]
    t71 = [("d01", "Decision", [
        cell_l(dec["action_bias"]), cell_l(dec["confidence"]), cell_optional(dec["posture"], "posture"),
        cell_l(dec["instrument"]), cell_optional(dec["size"], "size"),
        T(fmt_date(parse_date(dd["text"])), [dd["quote"]], "source"), cell_l(dec["decision_maker_role"]),
        T(module_status, [], "calculated", "calc:T7.1.d01.module_status")])]
    tables.append(table("T7.1", "Decision record",
                        [("action_bias", "Action bias"), ("confidence", "Confidence"), ("posture", "Posture"),
                         ("instrument", "Instrument"), ("size", "Size"), ("decision_date", "Decision date"),
                         ("decision_maker_role", "Decision-maker role"), ("module_status", "Module status")],
                        t71, "Decision"))
    # T7.2
    ev_refs = [th[f]["quote"] for f in ("thesis", "greatest_uncertainty", "downside_paths", "exit_trigger")]
    evidence = "; ".join(dedupe(src_label(r) for r in ev_refs))
    t72 = [("t01", "Thesis as decided", [
        cell_optional(th["thesis"], "thesis"), cell_optional(th["greatest_uncertainty"], "uncertainty"),
        cell_optional(th["downside_paths"], "downside"), cell_optional(th["expected_spread_return"], "spread"),
        cell_optional(th["expected_rating_path"], "rating"), cell_optional(th["expected_hold"], "hold"),
        cell_optional(th["exit_trigger"], "exit"), T(evidence, ev_refs, "calculated", "calc:T7.2.t01.evidence_id")])]
    tables.append(table("T7.2", "Thesis and expectation register",
                        [("thesis", "Thesis"), ("greatest_uncertainty", "Greatest uncertainty"),
                         ("downside_paths", "Flagged catalysts and downside paths"),
                         ("expected_spread_return", "Expected spread or return"),
                         ("expected_rating_path", "Expected rating path"), ("expected_hold", "Expected hold"),
                         ("exit_triggers", "Exit triggers"), ("evidence_id", "Evidence")], t72, "Decision"))
    # T7.3
    t73 = []
    INTERIM_CALC = "Interim"
    for m in OBS_METRICS:
        unit, dp = OBS_UNIT[m]
        o = obs.get(("realized", m))
        if o:
            val = Decimal(o["value_text"]) / (100 if unit == "decimal_fraction" else 1)
            per = (f"Twelve months to {parse_date(o['as_of_text']).isoformat()}" if m in ("total_leverage", "interest_cover")
                   else f"Quotation of {parse_date(o['as_of_text']).isoformat()}")
            cells = [N(val, unit, dp, [o["quote"]], vc="source", per=per),
                     T(fmt_date(parse_date(o["as_of_text"])), [o["quote"]], "source"),
                     T(src_label(o["quote"]), [o["quote"]], "source"),
                     T(interim[m], [], "calculated", f"calc:T7.3.{m}.interim_final"),
                     T(src_label(o["quote"]), [o["quote"]], "calculated", f"calc:T7.3.{m}.evidence_id")]
        else:
            why = NO_OUT or "Not observed: no realized observation was submitted"
            cells = [G(why, unit), G(why), G(why), T(INTERIM_CALC, [], "calculated", f"calc:T7.3.{m}.interim_final"), G(why)]
        t73.append((m, METRIC_NAME[m], [T(METRIC_NAME[m])] + cells))
    # default / restructuring incidence (r14 SKILL.md Outcome Metrics): the issuer statement, verbatim
    inc = sub["default_restructuring"]
    if inc is not None:
        iq = inc["quote"]
        t73.append(("default_restructuring", "Default or restructuring incidence", [
            T("Default or restructuring incidence"), T(iq["quote"], [iq], "source"),
            T(fmt_date(parse_date(inc["as_of_text"])), [iq], "source"), T(src_label(iq), [iq], "source"),
            T(interim["default_restructuring"], [], "calculated", "calc:T7.3.default_restructuring.interim_final"),
            T(src_label(iq), [iq], "calculated", "calc:T7.3.default_restructuring.evidence_id")]))
    else:
        why = NO_OUT or "Not observed: no default or restructuring statement was submitted"
        t73.append(("default_restructuring", "Default or restructuring incidence", [
            T("Default or restructuring incidence"), G(why), G(why), G(why),
            T(INTERIM_CALC, [], "calculated", "calc:T7.3.default_restructuring.interim_final"), G(why)]))
    if d["window_days"] is not None:
        refs_real = [o["quote"] for o in sub["observations"] if o["side"] == "realized"]
        refs_dec = [dd["quote"]]
        wcells = [T("Observation window since the decision"),
                  N(Decimal(d["window_days"]), "days", None, refs_dec + refs_real, calc="calc:T7.3.window.realized_value",
                    formula="latest realized as-of date - decision date (calendar days)",
                    per=f"Decision {ddate.isoformat()} to {d['window_end'].isoformat()}"),
                  T(fmt_date(d["window_end"]), refs_real, "calculated", "calc:T7.3.window.as_of"),
                  T("Derived from the decision date and the latest realized as-of date", [], "calculated", "calc:T7.3.window.source"),
                  T(interim["window"], [], "calculated", "calc:T7.3.window.interim_final"),
                  T("; ".join(dedupe(src_label(r) for r in refs_dec + refs_real)), refs_dec + refs_real, "calculated",
                    "calc:T7.3.window.evidence_id")]
    else:
        why = NO_OUT or "Not calculable: no realized observation"
        wcells = [T("Observation window since the decision"), G(why, "days"), G(why), G(why),
                  T(INTERIM_CALC, [], "calculated", "calc:T7.3.window.interim_final"), G(why)]
    t73.append(("window", "Observation window", wcells))
    tables.append(table("T7.3", "Realized outcome log",
                        [("metric", "Metric"), ("realized_value", "Realized value"), ("as_of", "As-of date"),
                         ("source", "Source"), ("interim_final", "Interim or final"), ("evidence_id", "Evidence")],
                        t73, "Metric"))
    # T7.4
    t74 = []
    for m in METRICS:
        parts = ("loan_bid", "loan_offer") if m == "loan_mid" else (m,)
        unit, dp = ("decimal_fraction", 3) if m == "loan_mid" else ("MULTIPLE", 2)
        e_refs = [obs[("expected", p)]["quote"] for p in parts if ("expected", p) in obs]
        r_refs = [obs[("realized", p)]["quote"] for p in parts if ("realized", p) in obs]
        v = s[m]
        e_asof = inp["exp_asof"].get(parts[0])
        r_asof = inp["real_asof"].get(parts[0])
        pe = (f"Quotation of {e_asof.isoformat()}" if m == "loan_mid" else f"Recorded at Approval {e_asof.isoformat()}") if e_asof else None
        pr = (f"Quotation of {r_asof.isoformat()}" if m == "loan_mid" else f"Twelve months to {r_asof.isoformat()}") if r_asof else None
        mid_formula = "(bid + offer) / 2"
        if d[m]["expected"] is not None:
            ecell = (N(d[m]["expected"], unit, dp, e_refs, vc="calculated", calc=f"calc:T7.4.{m}.expected", formula=mid_formula, per=pe)
                     if m == "loan_mid" else N(d[m]["expected"], unit, dp, e_refs, vc="source", per=pe))
        else:
            ecell = G("Not recorded: the Prior Case record states no expected value for this measure", unit)
        if d[m]["realized"] is not None:
            rcell = (N(d[m]["realized"], unit, dp, r_refs, vc="calculated", calc=f"calc:T7.4.{m}.realized", formula=mid_formula, per=pr)
                     if m == "loan_mid" else N(d[m]["realized"], unit, dp, r_refs, vc="source", per=pr))
        else:
            rcell = G(NO_OUT or "Not observed: no realized value was submitted", unit)
        pv = f"{PER_DEC} to {(r_asof or ddate).isoformat()}" if r_asof else None
        if v["variance"] is not None:
            dcell = T(v["direction"], e_refs + r_refs, "calculated", f"calc:T7.4.{m}.direction")
            if m == "loan_mid":
                mcell = N(d[m]["magnitude_bp"], "basis_points", None, e_refs + r_refs, calc=f"calc:T7.4.{m}.magnitude",
                          formula="abs(realized - expected) x 10000 (basis points of par)", per=pv)
            else:
                mcell = N(d[m]["magnitude"], unit, dp, e_refs + r_refs, calc=f"calc:T7.4.{m}.magnitude",
                          formula="abs(realized - expected)", per=pv)
        else:
            why = "Not calculable: needs an expected and a realized value"
            dcell, mcell = G(why), G(why, unit)
        ccell = (T(conf[m], [], "analyst_judgment") if m in conf else G("Not assessed: the measure is not compared"))
        evid = "; ".join(dedupe(src_label(r) for r in e_refs + r_refs)) or None
        evcell = T(evid, e_refs + r_refs, "calculated", f"calc:T7.4.{m}.evidence_id") if evid else G("No evidence cited")
        t74.append((m, METRIC_NAME[m], [T(METRIC_NAME[m]), ecell, rcell, dcell, mcell, ccell, evcell]))
    tables.append(table("T7.4", "Variance table",
                        [("metric", "Metric"), ("expected", "Expected"), ("realized", "Realized"),
                         ("direction", "Variance direction"), ("magnitude", "Variance magnitude"),
                         ("confidence", "Confidence"), ("evidence_id", "Evidence")], t74, "Metric"))
    # T7.5
    t75 = []
    size_q = {z["metric_id"]: z["quote"] for z in th["downside_sizes"]}
    for m in comp + ["overall"]:
        a = attrs[m]
        var = (f"{METRIC_NAME[m]}: {d[m]['direction'].lower()}" if m != "overall" else "Decision overall")
        if m != "overall" and d[m]["downside_breach"] is not None:
            breach_cell = T("Breached" if d[m]["downside_breach"] else "Not breached",
                            [size_q[m], obs[("realized", m)]["quote"]], "calculated", f"calc:T7.5.{m}.breach")
        else:
            breach_cell = G("Not applicable: " + ("a downside size applies to a measure, not to the decision overall" if m == "overall"
                                                  else ("no downside size can be recorded for the quotation" if m == "loan_mid"
                                                       else "no downside size is recorded for this measure")), None, "not_applicable")
        flag_ref = th["downside_paths"]["quote"] if a.get("flag_quote") else None
        ev_cell = (T(f"{src_label(flag_ref)} (named downside path)", [flag_ref], "calculated", f"calc:T7.5.{m}.evidence_id")
                   if flag_ref else G("Not applicable: no named downside path is cited", None, "not_applicable"))
        mod_cell = (T(a["originating_module"], [], "analyst_judgment") if a.get("originating_module")
                    else G("Not applicable: no originating process gap is named", None, "not_applicable"))
        t75.append((m, METRIC_NAME.get(m, "Decision overall"), [
            T(var, [], "calculated", f"calc:T7.5.{m}.variance"), breach_cell, T(a["label"], [], "analyst_judgment"),
            T(a["process_sound"], [], "analyst_judgment"), mod_cell, T(a["basis"], [], "analyst_judgment"), ev_cell]))
    tables.append(table("T7.5", "Attribution table",
                        [("variance", "Variance"), ("breach", "Downside size breached"), ("label", "Attribution label"),
                         ("process_sound", "Process sound"),
                         ("originating_module", "Originating module"), ("basis", "Basis"), ("evidence_id", "Evidence")],
                        t75, "Measure"))
    # T7.6 calibration (pattern-gated)
    nm = "Not meaningful: the calibration gate is not met"
    t76 = [("gate", "Calibration gate", [
        T("No pattern assessed: the calibration gate needs at least three comparable decisions", [], "calculated", "calc:T7.6.gate.pattern"),
        G(nm, None, "not_applicable"), G(nm, None, "not_applicable"), G(nm, None, "not_applicable"),
        G(nm, None, "not_applicable"),
        N(Decimal(d["decisions_recorded"]), "decisions", None, [], calc="calc:T7.6.gate.decisions_recorded",
          formula="count of Prior Case records in the pack (decision-record sources read by this step)"),
        N(Decimal(d["decisions_required"]), "decisions", None, [], calc="calc:T7.6.gate.decisions_required",
          formula="schema rule: the calibration gate needs at least 3 comparable decisions (r14 REF_CP-8_06 constant)")])]
    tables.append(table("T7.6", "Calibration register (advisory)",
                        [("pattern", "Pattern"), ("target_module", "Target module"), ("specific_prior", "Specific prior"),
                         ("supporting_decisions", "Supporting decisions"),
                         ("advisory_recommendation", "Advisory recommendation"),
                         ("decisions_recorded", "Decisions recorded"), ("decisions_required", "Decisions required")],
                        t76, "Gate"))
    # T7.7 track-record dashboard
    cols7 = [("value", "Value"), ("basis", "Basis")]
    t77 = []
    if d["hit_rate"] is not None:
        t77.append(("hit_rate", "Hit rate", [N(d["hit_rate"], "decimal_fraction", 1, [], calc="calc:T7.7.hit_rate.value",
                                               formula="decisions labelled Thesis Confirmed / decisions with a label other than Insufficient Information"),
                                              T("Over the decisions recorded in this run")]))
    else:
        t77.append(("hit_rate", "Hit rate", [G("Not calculable: no decision carries an attribution label other than Insufficient Information"),
                                              T("Over the decisions recorded in this run")]))
    t77.append(("decisions_labelled", "Decisions with an attribution label", [
        N(Decimal(d["labelled"]), "decisions", None, [], calc="calc:T7.7.decisions_labelled.value", formula="count"),
        T("Labels other than Insufficient Information")]))
    t77.append(("decisions_confirmed", "Decisions labelled Thesis Confirmed", [
        N(Decimal(d["confirmed"]), "decisions", None, [], calc="calc:T7.7.decisions_confirmed.value", formula="count"),
        T("Overall label of the decision")]))
    t77.append(("cut", "Realized against expected by pathway, sector and sponsor", [
        G("Not recorded: the pathway, sector and sponsor of the prior decision are not in the Prior Case record"),
        T("A cut needs the attributes of the decision")]))
    if comp:
        for lab in LABELS6:
            slug = re.sub(r"[^a-z]+", "_", lab.lower()).strip("_")
            t77.append((f"dist_{slug}", f"Attribution: {lab}", [
                N(Decimal(d["distribution"][lab]), "attributions", None, [], calc=f"calc:T7.7.dist_{slug}.value",
                  formula="count of metric attributions with this label"), T("Metric attributions, overall excluded")]))
    else:
        t77.append(("distribution", "Attribution distribution", [
            G("Not calculable: no metric was compared, so no metric attribution exists"), T("Metric attributions, overall excluded")]))
    if sub["lessons"]:
        for i, x in enumerate(sub["lessons"], 1):
            t77.append((f"lesson_{i:02d}", f"Lesson {i}", [T(x["lesson"], [], "analyst_judgment"),
                                                           T("Supported by " + ", ".join(METRIC_NAME[m] for m in x["metric_ids"]),
                                                             [], "calculated", f"calc:T7.7.lesson_{i:02d}.basis")]))
    else:
        t77.append(("lessons", "Lessons", [G("Not stated: no compared metric supports a lesson"), T("A lesson needs a compared metric")]))
    tables.append(table("T7.7", "Track-record dashboard", cols7, t77, "Measure"))
    # T7.8 gaps ledger: Gap (the row label), Missing Item, Why It Matters, Impact on Output, Required Follow-Up
    t78 = []
    imp_port = "Portfolio-level attribution is limited"
    for f in ("posture", "size"):
        if "absence" in dec[f]:
            a = dec[f]["absence"]
            t78.append((f, f"Decision {f} not recorded", [T(f"Decision {f}"), T(a["reason"]), T(imp_port), T(a["follow_up"])]))
    for f, item, impact in (("expected_spread_return", "Expected spread or return", "Spread and return variance cannot be compared"),
                            ("expected_rating_path", "Expected rating path", "Rating migration cannot be compared"),
                            ("expected_hold", "Expected holding period", "Holding period against plan cannot be compared")):
        if "absence" in th[f]:
            a = th[f]["absence"]
            t78.append((f, f"{item} not recorded", [T(item), T(a["reason"]), T(impact), T(a["follow_up"])]))
    if ab:
        t78.append(("outcome", "No realized outcome", [T("Realized outcomes"), T(ab["reason"]),
                                                      T("Outcome log, variances and attribution are absent"), T(ab["follow_up"])]))
    for m in METRICS:
        if m not in comp and not ab and (d[m]["expected"] is None or d[m]["realized"] is None):
            t78.append((f"realized_{m}", f"{METRIC_NAME[m]} not compared", [
                T(METRIC_NAME[m]), T("Either the expected or the realized value was not submitted"),
                T("Variance and attribution are absent for this measure"), T("Supply the missing value with its source")]))
    if cp6 is None:
        t78.append(("current_decision", "No current decision to compare", [
            T("Current committee decision"), T("CP-6 is not in this run"),
            T("The decision line of the what-changed block is missing"), T("Select CP-6 in the run")]))
    t78.append(("calibration_gate", "Calibration gate not met", [
        T("Comparable decisions"), T("A single decision cannot show a pattern"),
        T("No calibration recommendation is produced"), T("Supply further comparable Prior Case records")]))
    rows78 = [(rid, lab, [T(lab), *cs]) for rid, lab, cs in t78]
    for i, g in enumerate(sub["extra_gaps"], 1):
        rows78.append((f"extra_{i:02d}", g["gap"], [T(g["gap"], [], "analyst_judgment"), T(g["missing_item"], [], "analyst_judgment"),
                                                    T(g["why_it_matters"], [], "analyst_judgment"),
                                                    T(g["impact_on_output"], [], "analyst_judgment"), T(g["follow_up"], [], "analyst_judgment")]))
    tables.append(table("T7.8", "Gaps ledger",
                        [("gap", "Gap"), ("missing_item", "Missing item"), ("why_it_matters", "Why it matters"),
                         ("impact_on_output", "Impact on output"), ("follow_up", "Required follow-up")],
                        rows78, "Gap"))
    claims = compose_claims(case, sub, d, tables, cp6)
    # the rendered block: one line per row, the resolved claim text (CP-6's cp6.committee_challenge pattern)
    lines = []
    kind, text = current_decision_text(th_bias(dec), th_conf(dec), cp6)
    lines.append(("decision", "Decision",
                  T(text, [], "calculated", "calc:cp8.what_changed.decision.value") if kind == "known"
                  else G(text)))
    for c in claims:
        if c["claim_id"] in ("CP-8-VAR-01", "CP-8-VAR-02", "CP-8-VAR-03", "CP-8-OUT-01", "CP-8-ATT-01"):
            row = {"CP-8-VAR-01": "total_leverage", "CP-8-VAR-02": "interest_cover", "CP-8-VAR-03": "loan_mid",
                   "CP-8-OUT-01": "outcome", "CP-8-ATT-01": "attribution"}[c["claim_id"]]
            lab = {"total_leverage": "Total leverage", "interest_cover": "Interest cover", "loan_mid": "Term loan quotation",
                   "outcome": "Outcome", "attribution": "Attribution"}[row]
            lines.append((row, lab, T(c["resolved"], [], "calculated", f"calc:cp8.what_changed.{row}.value")))
    lines.append(("summary", "Summary", T(sub["synthesis"]["text"], [], "analyst_judgment")))
    tables.append(table("cp8.what_changed", "What changed since the last Report",
                        [("value", "Value")], [(rid, lab, [cell]) for rid, lab, cell in lines], "Change"))
    return tables, claims, own_limitations(sub, d, cp6)


def th_bias(dec):
    return dec["action_bias"]["text"]


def th_conf(dec):
    return dec["confidence"]["text"]


def shown_of(by_id, ref):
    f = by_id[ref]
    return f["shown"]


def compose_claims(case, sub, d, tables, cp6):
    by_id = {f["fact_id"]: f for t in tables for r in t["rows"] for f in r["facts"]}
    comp = d["compared"]
    attrs = {a["metric_id"]: a for a in sub["attributions"]}
    claims = []

    def add(cid, text, limitation=None):
        refs = []
        resolved = text
        for m in re.finditer(r"\{([^{}|]+)\|([^{}]+)\}", text):
            fid, unit = m.group(1), m.group(2)
            f = by_id[fid]
            assert f["status"] == "known" and f["amount"] is not None and (f["cites"] or f["calculation_id"]), fid
            assert unit == figure_unit(f["unit"]), (fid, unit)
            refs.append(f"{fid}|{unit}")
            resolved = resolved.replace(m.group(0), f["shown"])
        for m in re.finditer(r"\[([^\[\]]+)\]", text):
            f = by_id[m.group(1)]
            assert f["status"] != "known", m.group(1)
            refs.append(m.group(1))
            resolved = resolved.replace(m.group(0), f["shown"])
        literal = re.sub(r"\{[^{}]+\}|\[[^\[\]]+\]", "", text)
        assert not any(ch.isnumeric() for ch in literal), (cid, literal)
        claims.append({"claim_id": cid, "text": text, "refs": refs, "limitation": limitation, "resolved": resolved,
                       "literal_text_outside_references": literal})

    for cid, m, lead, tail_unit in (("CP-8-VAR-01", "total_leverage", "Total leverage was recorded at", "x"),
                                    ("CP-8-VAR-02", "interest_cover", "Interest cover was recorded at", "x"),
                                    ("CP-8-VAR-03", "loan_mid", "The mid level of the term loan quotation was recorded at", "%")):
        if m not in comp:
            continue
        dirn = d[m]["direction"]
        e, r = f"T7.4.{m}.expected|{tail_unit}", f"T7.4.{m}.realized|{tail_unit}"
        g = f"T7.4.{m}.magnitude|{'bp' if m == 'loan_mid' else tail_unit}"
        if dirn == "Unchanged":
            text = f"{lead} {{{e}}} and is now {{{r}}}, unchanged."
        else:
            text = f"{lead} {{{e}}} and is now {{{r}}}, {dirn.lower()} by {{{g}}}."
        add(cid, text)
    if d["window_days"] is not None:
        add("CP-8-WIN-01", "The latest realized observation falls {T7.3.window.realized_value|days} after the decision.")
    else:
        add("CP-8-OUT-01", "No realized outcome is recorded, so the window since the decision [T7.3.window.realized_value] and every variance are missing.")
    ov = attrs["overall"]
    proc = {"Y": "the process is judged sound", "N": "the process is judged unsound",
            "Not assessed": "process quality is not assessed"}[ov["process_sound"]]
    add("CP-8-ATT-01", f"The attribution is {ov['label']}; {proc}.")
    add("CP-8-CAL-01", "The calibration gate is not met: {T7.6.gate.decisions_recorded|decisions} recorded and "
                       "{T7.6.gate.decisions_required|decisions} needed, so no recalibration is advised.")
    add("CP-8-VIEW-01", sub["synthesis"]["text"], None)
    return claims


def own_limitations(sub, d, cp6):
    out = [LIM_PRIOR]
    if any("absence" in sub["decision"][f] for f in ("posture", "size")) or any(
            "absence" in sub["thesis"][f] for f in ("expected_spread_return", "expected_rating_path", "expected_hold")):
        out.append("Portfolio posture, position size, expected spread or return, rating path and holding period are not recorded in the Prior Case record")
    if "absence" not in sub["thesis"]["exit_trigger"]:
        out.append("The exit trigger records no threshold, so exit discipline cannot be measured")
    if sub.get("outcome_absence"):
        out.append("No post-decision outcome source was supplied, so no realized outcome, variance or attribution is shown")
    else:
        out.append("Realized figures are interim: no source states that the observation window is closed")
    out.append("One decision is recorded, so no calibration recommendation is possible (at least three comparable decisions are needed)")
    if cp6 is None:
        out.append("No current CP-6 decision is in this run, so the decision itself is not compared")
    return out


# --- CP-0 (readiness.py:408-531 transcription, as cases/cp3d-owner/builder/build.py) ---------------------------------
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


# Self-check: the transcription reproduces the frozen S1 positive CP-0 from the frozen S1 literal review.
PACK_NAMES_S1 = {"identity": NAMES["identity"], "financial": fin_src["financial"]["name"], "business": BUS["common"]["name"]}
_S1SHA = {"identity": fin_src["identity"]["sha256"], "financial": fin_src["financial"]["sha256"], "business": BUS["positive"]["sha256"]}
_S1LIM = {"identity": None, "financial": S1M["financial_pack_limitation"]["text"], "business": None}
_saved = (dict(NAMES), dict(SHA), dict(LIMIT))
NAMES.update(PACK_NAMES_S1)
SHA.update(_S1SHA)
LIMIT.update(_S1LIM)
_s1_pos = cp0_expected([(s, NAMES[s], "ready", LIMIT[s]) for s in ("identity", "financial", "business")],
                       S1S["positive"]["readiness_review"], "slice-snapshot-positive",
                       ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL"], ["CP-1", "CP-1A", "CP-2"])
for _k in ("status", "why", "live_consumers", "plan_order", "exact_commands", "limitations", "facts"):
    assert _s1_pos[_k] == S1E["positive"]["CP-0"][_k], f"CP-0 transcription differs from the S1 oracle at {_k}"
NAMES.clear(); NAMES.update(_saved[0])
SHA.clear(); SHA.update(_saved[1])
LIMIT.clear(); LIMIT.update(_saved[2])


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


PLAN, CAT = meth_plan(["CP-8"])
assert PLAN == ["CP-0", "CP-8"], PLAN
assert CAT["CP-8"]["required"] == ["CP-0"] and CAT["CP-8"]["optional"] == ["CP-6"] and CAT["CP-8"]["edge_rules"] == {"CP-6": "block"}
PLAN_WITH_CP6, _ = meth_plan(["CP-8", "CP-6"])
assert PLAN_WITH_CP6 == ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-3", "CP-5", "CP-6", "CP-8"], PLAN_WITH_CP6
CP8_TABLES = CAT["CP-8"]["table_ids"]
assert CP8_TABLES == [f"T7.{i}" for i in range(1, 9)]
for _m in METH:
    if _m["module_id"] != "CP-8":
        assert not any(t.startswith("T7.") for t in _m["table_ids"]), _m["module_id"]
assert [t for t in next(m for m in METH if m["module_id"] == "CP-0")["table_ids"] if t.startswith("T7")] == ["T7"]


def readiness_review(case):
    sub = copy.deepcopy(S1S["positive"]["readiness_review"])
    ident = sub["sources"][0]["citations"][0]
    sub["sources"] = [sub["sources"][0]]
    sub["objective"] = "Decision ledger and post-mortem of the recorded committee decision"
    sub["reporting_period"] = "Decision recorded January 10, 2026; outcome sources to April 30, 2026"
    pc = cite("prior_case", P1, QD)
    up = cite("update", P1, Q_LEV1)
    mk = cite("market_update", P1, Q_QUOTE1)
    prior_src = {
        "source_id": "prior_case", "document_family": "Prior Case record", "authority": "unknown",
        "entity": ISSUER, "period": "Recorded January 10, 2026",
        "version_relationship": "Prior committee decision record supplied offline for the post-mortem",
        "fidelity": "verified", "citations": [pc], "limitations": [LIM_PRIOR, SYN_LIM],
    }
    update_src = {
        "source_id": "update", "document_family": "Quarterly update note", "authority": "issuer",
        "entity": ISSUER, "period": "Twelve months to March 2026",
        "version_relationship": "Issuer update published after the recorded decision",
        "fidelity": "verified", "citations": [up], "limitations": [LIM_UPDATE, SYN_LIM],
    }
    market_src = {
        "source_id": "market_update", "document_family": "Loan market quotation sheet", "authority": "third_party",
        "entity": ISSUER, "period": "April 2026",
        "version_relationship": "Standalone third-party dealer quotation sheet published after the recorded decision",
        "fidelity": "verified", "citations": [mk], "limitations": [SYN_LIM],
    }
    gap_prior = "No Prior Case record is in the pack, so there is no decision record to attribute"
    gap_out = "No post-decision outcome source is in the pack, so realized outcomes and variances are absent"
    if case == "positive":
        sub["sources"] += [prior_src, update_src, market_src]
        sub["consumers"] = [{
            "module_id": "CP-8", "readiness": "READY_WITH_LIMITATIONS",
            "evidence_demand": "A dated decision record with its recorded expectations and independently sourced, dated outcomes",
            "source_ids": ["prior_case", "update", "market_update"],
            "rationale": "The ledger can run on the located decision record and the later issuer and dealer sources, with source limitations.",
            "citations": [pc, up, mk], "missing_source": None,
            "limitations": ["Outcome figures come from one issuer note and one dealer quotation"],
        }]
        sub["gaps"] = []
        cites = [ident, pc, up, mk]
        claim = "The located decision record and the later issuer and dealer sources support a decision ledger with limitations."
    elif case == "no_outcome":
        sub["sources"] += [prior_src]
        sub["consumers"] = [{
            "module_id": "CP-8", "readiness": "READY_WITH_LIMITATIONS",
            "evidence_demand": "A dated decision record; no post-decision outcome source is available",
            "source_ids": ["prior_case"],
            "rationale": "The ledger can record the decision and its expectations and shows every outcome as missing.",
            "citations": [pc], "missing_source": None, "limitations": [gap_out],
        }]
        sub["gaps"] = [{
            "gap_id": "missing-outcome-source", "kind": "source", "severity": "material", "description": gap_out,
            "affected_modules": ["CP-8"], "remediation": "Supply the next issuer update and a dated dealer quotation",
            "citations": [],
        }]
        cites = [ident, pc]
        claim = "The located decision record supports a ledger of the decision only; no outcome source is available."
    else:
        sub["sources"] += [update_src, market_src]
        sub["consumers"] = [{
            "module_id": "CP-8", "readiness": "BLOCKED",
            "evidence_demand": "A dated decision record is required; none is in the pack",
            "source_ids": ["update", "market_update"],
            "rationale": "Outcome sources exist, but there is no decision record to attribute them to, and the thesis must not be reconstructed.",
            "citations": [up, mk], "missing_source": "prior_case", "limitations": [gap_prior],
        }]
        sub["gaps"] = [{
            "gap_id": "missing-prior-record", "kind": "source", "severity": "critical", "description": gap_prior,
            "affected_modules": ["CP-8"], "remediation": "Supply the Prior Case record accepted at Approval",
            "citations": [],
        }]
        cites = [ident, up, mk]
        claim = "The located outcome sources cannot be attributed: the pack holds no decision record."
    sub["analysis"] = [{"claim_id": "source-assessment", "text": claim, "citations": cites,
                        "limitation": None}]
    return sub


# --- refusal mutations -----------------------------------------------------------------------------------------------
def setp(obj, path, value):
    cur = obj
    for key in path[:-1]:
        cur = cur[key]
    cur[path[-1]] = value


def mut(base, edits):
    out = copy.deepcopy(base)
    for path, value in edits:
        setp(out, path, value)
    return out


def removed(obj, path):
    cur = obj
    for key in path[:-1]:
        cur = cur[key]
    del cur[path[-1]]
    return obj


POS = LITERALS["positive"]
NOO = LITERALS["no_outcome"]
MUT_SPEC = [
    ("r01", "bias outside the vocabulary", POS, [(("decision", "action_bias", "text"), "Hold")],
     "decision.action_bias: Hold is not one of Overweight, Neutral, Underweight, Insufficient Information"),
    ("r02", "bias text not in its quote", POS, [(("decision", "action_bias", "text"), "Underweight")],
     "decision.action_bias: text Underweight does not occur in the quote"),
    ("r03", "decision quote not on the page", POS,
     [(("decision", "decision_maker_role", "quote", "quote"), "Decision-maker role: Risk Committee.")],
     'Quote/locator mismatch: quote not found under prior_case page:1 (normalised whitespace, quote marks and dashes): "Decision-maker role: Risk Committee."'),
    ("r04", "decision source not in the pack", POS, [(("decision", "decision_maker_role", "quote", "source_id"), "board_minutes")],
     ["Unavailable or changed source: board_minutes"]),
    ("r05", "decision field cites an outcome source", POS,
     [(("decision", "decision_maker_role", "quote", "source_id"), "update"),
      (("decision", "decision_maker_role", "quote", "locator"), "page:1"),
      (("decision", "decision_maker_role", "quote", "quote"), Q_LEV1)],
     "decision.decision_maker_role.quote: must cite prior_case"),
    ("r06", "decision date not a date", POS,
     [(("decision", "decision_date", "text"), "Approval"), (("decision", "decision_date", "quote", "quote"), "Recorded at Approval on January 10, 2026.")],
     "decision.decision_date: text Approval is not a date (Month D, YYYY)"),
    ("r07", "required decision field absent", POS,
     [(("decision", "instrument"), {"absence": {"quote": None, "reason": "Not stated", "follow_up": "Ask"}})],
     "decision.instrument: a required decision field cannot be absent"),
    ("r08", "expected value not in its quote", POS, [(("observations", 0, "value_text"), "1.68")],
     "observations[0]: value_text 1.68 does not occur in the quote"),
    ("r09", "value labelled as another measure", POS,
     [(("observations", 1, "quote", "quote"), Q_LEV0), (("observations", 1, "value_text"), LEV_AT_DECISION)],
     "observations[1]: interest_cover value_text 1.67 is not labelled interest_cover in the quote"),
    ("r10", "expected observation cites an outcome source", POS,
     [(("observations", 0, "quote"), Q("update", P1, Q_LEV1)), (("observations", 0, "value_text"), "1.80")],
     "observations[0].quote: must cite prior_case"),
    ("r11", "realized observation on a non-issuer source", POS,
     [(("observations", 4, "quote"), Q("market_update", P1, Q_QUOTE1))],
     "observations[4]: total_leverage needs an issuer source, market_update is third_party (CP-0 T3)"),
    ("r12", "realized date not after the decision", POS,
     [(("observations", 4, "as_of_text"), "December 31, 2025"), (("observations", 4, "value_text"), "1.67"),
      (("observations", 4, "quote"), Q("update", P1, Q_LEV_PRE))],
     "observations[4]: realized as_of December 31, 2025 is not after the decision date"),
    ("r13", "duplicate observation", POS, [],
     "observations: (realized, total_leverage) appears more than once"),
    ("r14", "bid without offer", POS, [], "observations: realized loan_bid and loan_offer must be given together"),
    ("r15", "realized and absence together", POS,
     [(("outcome_absence",), {"reason": "No outcome", "follow_up": "Supply one"})],
     "observations: realized observations and outcome_absence are mutually exclusive"),
    ("r16", "neither realized nor absence", NOO, [(("outcome_absence",), None)],
     "observations: no realized observation and no outcome_absence"),
    ("r17", "attribution label outside the taxonomy", POS, [(("attributions", 0, "label"), "Mixed")],
     "attributions[0]: label Mixed is not one of Thesis Confirmed, Flagged Risk Materialized, Unflagged Risk Materialized, Right for Wrong Reason, Premature / Mistimed, Insufficient Information"),
    ("r18", "flagged risk without a flag quote", POS, [(("attributions", 0, "flag_quote"), None)],
     "attributions[0]: Flagged Risk Materialized needs flag_quote"),
    ("r19", "flag quote not a recorded downside path", POS, [(("attributions", 0, "flag_quote"), "a new competitor")],
     "attributions[0].flag_quote: not a span of the recorded downside paths"),
    ("r20", "flagged risk judged unsound", POS, [(("attributions", 0, "process_sound"), "N")],
     "attributions[0]: Flagged Risk Materialized requires process_sound Y"),
    ("r21", "unflagged risk without an originating module", POS,
     [(("attributions", 0, "label"), "Unflagged Risk Materialized"), (("attributions", 0, "process_sound"), "N"),
      (("attributions", 0, "flag_quote"), None)],
     "attributions[0]: Unflagged Risk Materialized needs originating_module"),
    ("r22", "a compared metric left unattributed", POS, [], "attributions: no attribution for total_leverage"),
    ("r23", "digit in analyst text", POS, [(("attributions", 0, "basis"), "Leverage rose by 2 tenths against the recorded expectation")],
     "attributions[0].basis: digits are not allowed"),
    ("r24", "reference syntax in analyst text", POS, [(("synthesis", "text"), "The decision is a flagged risk {x|x} with a sound process")],
     "synthesis.text: reference syntax is not allowed"),
    ("r25", "hindsight conclusion", POS, [(("lessons", 0, "lesson"), "The committee should have sized the position smaller")],
     "lessons[0].lesson: prohibited conclusion: should have"),
    ("r26", "calibration advice from one decision", POS, [(("lessons", 0, "lesson"), "The prior for leverage should be recalibrated downwards")],
     "lessons[0].lesson: prohibited conclusion: calibrat"),
    ("r27", "empty text", POS, [(("synthesis", "text"), "  ")], "synthesis.text: text is empty"),
    ("r28", "confidence missing for a compared metric", POS, [], "confidence: no confidence for interest_cover"),
    # revision 2 (review H4): one literal per validator class that r00-r28 left unreached
    ("r29", "decision field with both text and absence", POS, [(("decision", "posture", "text"), "Not recorded")],
     "decision.posture: exactly one of text and absence is required"),
    ("r30", "decision field cites a source outside the CP-8 scope", POS,
     [(("decision", "decision_maker_role", "quote", "source_id"), "identity"),
      (("decision", "decision_maker_role", "quote", "quote"), "Northbridge Synthetic Group is the issuer and consolidated group.")],
     ["decision.decision_maker_role.quote: source identity is outside the CP-8 scope"]),
    ("r31", "confidence outside the vocabulary", POS, [(("decision", "confidence", "text"), "Moderate")],
     "decision.confidence: Moderate is not one of Insufficient Information, Low, Medium, High"),
    ("r32", "thesis field with both quote and absence", POS,
     [(("thesis", "exit_trigger", "absence"), {"quote": None, "reason": "Not stated", "follow_up": "Ask"})],
     "thesis.exit_trigger: exactly one of quote and absence is required"),
    ("r33", "required thesis field absent", POS,
     [(("thesis", "thesis"), {"absence": {"quote": None, "reason": "Not stated", "follow_up": "Ask"}})],
     "thesis.thesis: a required thesis field cannot be absent"),
    ("r34", "observation side outside the vocabulary", POS, [],
     "observations[8]: side forecast is not expected or realized"),
    ("r35", "observation metric outside the vocabulary", POS, [],
     "observations[8]: metric recovery is not one of total_leverage, interest_cover, loan_bid, loan_offer"),
    ("r36", "realized observation cites the decision record", POS,
     [(("observations", 4, "quote"), Q(DECISION_SOURCE, P2, Q_LEV0))],
     "observations[4].quote: a realized observation cannot cite prior_case"),
    ("r37", "realized as_of_text not in its quote", POS, [(("observations", 4, "as_of_text"), "March 30, 2026")],
     "observations[4]: as_of_text March 30, 2026 does not occur in the quote"),
    ("r39", "confidence for a measure that is not compared", POS, [],
     "confidence[3]: loan_bid is not a compared metric"),
    ("r40", "confidence level outside the vocabulary", POS, [(("confidence", 0, "level"), "Moderate")],
     "confidence[0]: Moderate is not one of High, Medium, Low"),
    ("r41", "attribution names a measure that is not compared", POS, [],
     "attributions[4]: loan_bid is not a compared metric or overall"),
    ("r42", "an attribution metric named twice", POS, [],
     ["attributions: total_leverage appears more than once", "attributions: total_leverage appears more than once"]),
    ("r43", "process_sound outside the vocabulary", POS, [(("attributions", 0, "process_sound"), "Maybe")],
     "attributions[0]: process_sound Maybe is not one of Y, N, Not assessed"),
    ("r44", "Insufficient Information judged on process", POS, [(("attributions", 2, "process_sound"), "Y")],
     "attributions[2]: Insufficient Information requires process_sound Not assessed"),
    ("r45", "a label with process_sound Not assessed", POS, [(("attributions", 0, "process_sound"), "Not assessed")],
     "attributions[0]: Flagged Risk Materialized cannot have process_sound Not assessed"),
    ("r46", "unflagged risk judged sound", POS,
     [(("attributions", 0, "label"), "Unflagged Risk Materialized"), (("attributions", 0, "originating_module"), "CP-3"),
      (("attributions", 0, "flag_quote"), None)],
     "attributions[0]: Unflagged Risk Materialized requires process_sound N"),
    ("r47", "flag quote on a label that is not Flagged Risk Materialized", POS,
     [(("attributions", 2, "flag_quote"), FLAG_ALL)],
     "attributions[2]: flag_quote is only for Flagged Risk Materialized"),
    ("r48", "originating module on a label that is not Unflagged Risk Materialized", POS,
     [(("attributions", 0, "originating_module"), "CP-3")],
     "attributions[0]: originating_module is only for Unflagged Risk Materialized"),
    ("r49", "originating module is not a methodology module", POS,
     [(("attributions", 0, "label"), "Unflagged Risk Materialized"), (("attributions", 0, "process_sound"), "N"),
      (("attributions", 0, "originating_module"), "CP-99"), (("attributions", 0, "flag_quote"), None)],
     "attributions[0]: originating_module CP-99 is not a methodology module"),
    ("r50", "flagged metric with no recorded downside size", POS,
     [(("thesis", "downside_sizes"), [copy.deepcopy(POS["thesis"]["downside_sizes"][1])])],
     "attributions[0]: Flagged Risk Materialized needs a recorded downside size for total_leverage"),
    ("r51", "overall attribution other than Insufficient Information with nothing compared", NOO,
     [(("attributions", 0, "label"), "Flagged Risk Materialized"), (("attributions", 0, "process_sound"), "Y"),
      (("attributions", 0, "flag_quote"), FLAG_ALL)],
     "attributions[overall]: with no compared metric the label must be Insufficient Information"),
    ("r52", "more than two lessons", POS, [], "lessons: at most 2 lessons"),
    ("r53", "lesson names a measure that is not compared", POS, [(("lessons", 0, "metric_ids"), ["loan_bid"])],
     "lessons[0]: metric_ids must name compared metrics"),
    ("r54", "default statement quote not on the page", POS,
     [(("default_restructuring", "quote", "quote"), "No default has occurred.")],
     'Quote/locator mismatch: quote not found under update page:1 (normalised whitespace, quote marks and dashes): "No default has occurred."'),
    ("r55", "default statement from a non-issuer source", POS,
     [(("default_restructuring", "quote"), Q("market_update", P1, "The quotation comes from one dealer."))],
     "default_restructuring: needs an issuer source, market_update is third_party (CP-0 T3)"),
    ("r56", "default statement as_of_text not in its quote", POS, [(("default_restructuring", "as_of_text"), "May 1, 2026")],
     "default_restructuring: as_of_text May 1, 2026 does not occur in the quote"),
    ("r57", "default statement not after the decision date", POS,
     [(("default_restructuring", "quote"), Q("update", P1, Q_NODEF_PRE)),
      (("default_restructuring", "as_of_text"), "December 31, 2025")],
     "default_restructuring: as_of December 31, 2025 is not after the decision date"),
    ("r58", "default statement together with outcome_absence", NOO,
     [(("default_restructuring",), {"as_of_text": "January 10, 2026", "quote": Q(DECISION_SOURCE, P1, Q_DATE)})],
     "default_restructuring: not allowed together with outcome_absence"),
    ("r59", "default statement missing with a realized outcome", POS, [(("default_restructuring",), None)],
     "default_restructuring: required when a realized outcome is given"),
    # revision 3 (review-precise-2 S3, S4)
    ("r60", "default statement that is not about default or restructuring", POS,
     [(("default_restructuring", "quote"), Q("update", P1, Q_LEV1)), (("default_restructuring", "as_of_text"), "March 31, 2026")],
     "default_restructuring.quote: does not state default or restructuring incidence"),
    ("r61", "downside size for a measure outside the vocabulary", POS, [],
     "thesis.downside_sizes[2]: metric loan_mid is not one of total_leverage, interest_cover"),
    ("r62", "downside size comparator outside the vocabulary", POS, [(("thesis", "downside_sizes", 0, "comparator"), "beyond")],
     "thesis.downside_sizes[0]: comparator beyond is not one of above, below"),
    ("r63", "downside size recorded twice for one measure", POS, [],
     "thesis.downside_sizes: total_leverage appears more than once"),
    ("r64", "downside size quote cites another source", POS,
     [(("thesis", "downside_sizes", 0, "quote"), Q("update", P1, Q_LEV1)), (("thesis", "downside_sizes", 0, "level_text"), "1.80")],
     "thesis.downside_sizes[0].quote: must cite prior_case"),
    ("r65", "downside size quote is not a span of the recorded downside paths", POS,
     [(("thesis", "downside_sizes", 0, "quote"), Q(DECISION_SOURCE, P2, Q_LEV0)), (("thesis", "downside_sizes", 0, "level_text"), LEV_AT_DECISION)],
     "thesis.downside_sizes[0].quote: not a span of the recorded downside paths"),
    ("r66", "downside size level_text not in its quote", POS, [(("thesis", "downside_sizes", 0, "level_text"), "1.80")],
     "thesis.downside_sizes[0]: level_text 1.80 does not occur in the quote"),
    ("r67", "downside size quote does not state the comparator", POS, [(("thesis", "downside_sizes", 0, "comparator"), "below")],
     "thesis.downside_sizes[0]: quote does not state total leverage below 1.75x"),
    ("r68", "flagged metric whose recorded downside size is not breached", POS,
     [(("observations", 4), OB("realized", "total_leverage", "1.70", "February 28, 2026", Q("update", P1, Q_LEV_FEB)))],
     "attributions[0]: Flagged Risk Materialized needs the downside size breached, but total_leverage 1.70 is not above 1.75x"),
    ("r69", "overall flagged with no flagged metric whose size is breached", POS,
     [(("attributions", 0, "label"), "Thesis Confirmed"), (("attributions", 0, "flag_quote"), None),
      (("attributions", 1, "label"), "Thesis Confirmed"), (("attributions", 1, "flag_quote"), None)],
     "attributions[3]: Flagged Risk Materialized overall needs at least one flagged metric with a breached downside size"),
]
# RULES part (the tool-use evidence rules, G1-X RULES(text, seen); the base's pages are the ones read) of the
# complete journaled tuple, for the two classes that are one defect with two consequences (CP-DR precedent)
RULES_PART = {
    "r04": [f"{COMMON_UNREAD}: board_minutes page:1"],
    "r30": [f"{COMMON_UNREAD}: identity page:1"],
}
# A literal that appends to a list (the mutated list is otherwise valid): id -> (path of the list, items appended)
APPENDS = {
    "r34": (("observations",), [{**POS["observations"][0], "side": "forecast"}]),
    "r35": (("observations",), [{**POS["observations"][0], "metric": "recovery"}]),
    "r39": (("confidence",), [{"metric_id": "loan_bid", "level": "Low"}]),
    "r41": (("attributions",), [{"metric_id": "loan_bid", "label": "Insufficient Information", "process_sound": "Not assessed",
                                 "originating_module": None, "basis": "The quotation side is not a compared measure",
                                 "flag_quote": None}]),
    "r42": (("attributions",), [POS["attributions"][0]]),
    "r52": (("lessons",), [POS["lessons"][0], POS["lessons"][0]]),
    "r61": (("thesis", "downside_sizes"), [{"metric_id": "loan_mid", "comparator": "above", "level_text": "1.75",
                                            "quote": Q(DECISION_SOURCE, P2, SIZE_LEV)}]),
    "r63": (("thesis", "downside_sizes"), [POS["thesis"]["downside_sizes"][0]]),
}
# Validator classes with no one-issue literal, stated rather than silently skipped (review H4, LEAD ruling):
UNTESTED_CLASSES = [
    {"class": "bid exceeds offer (observations: <side> bid exceeds offer)",
     "why": "unreachable by construction: a bid and an offer must each be the first number after its own label inside a verbatim quote, and every quotation line in the pack states a bid below its offer, so no literal can reach the branch without altering a source"},
]


def build_mutations():
    out = []
    for mid, title, base, edits, issue in MUT_SPEC:
        lit = mut(base, edits)
        if mid == "r13":
            lit["observations"].append(copy.deepcopy(POS["observations"][4]))
        elif mid == "r14":
            lit["observations"] = [o for o in lit["observations"] if not (o["side"] == "realized" and o["metric"] == "loan_offer")]
            lit["confidence"] = [c for c in lit["confidence"] if c["metric_id"] != "loan_mid"]
            lit["attributions"] = [a for a in lit["attributions"] if a["metric_id"] != "loan_mid"]
        elif mid == "r22":
            lit["attributions"] = [a for a in lit["attributions"] if a["metric_id"] != "total_leverage"]
        elif mid == "r28":
            lit["confidence"] = [c for c in lit["confidence"] if c["metric_id"] != "interest_cover"]
        if mid in APPENDS:
            cur = lit
            for key in APPENDS[mid][0]:
                cur = cur[key]
            cur += copy.deepcopy(APPENDS[mid][1])
        case = "positive" if base is POS else "no_outcome"
        validator = [issue] if isinstance(issue, str) else list(issue)
        rules = RULES_PART.get(mid, [])
        # the complete journaled tuple: validator issues, then the RULES issues (ToolRules order); the base's
        # cited pages are the ones read through read_pages
        got = check_submission(lit, PACK_IDS[case])
        assert got == validator, (mid, got, validator)
        got_rules = tool_rule_issues(lit, set(cited_pages(base)), True)
        assert got_rules == rules, (mid, got_rules, rules)
        out.append({"id": mid, "title": title, "base": case,
                    "edits": [{"path": list(p), "value": v} for p, v in edits]
                    + ([{"path": ["observations", "[end]"], "value": "append a copy of observations[4]"}] if mid == "r13" else [])
                    + ([{"path": ["observations", "[realized loan_offer]"], "value": "removed"},
                        {"path": ["confidence", "[loan_mid]"], "value": "removed"},
                        {"path": ["attributions", "[loan_mid]"], "value": "removed"}] if mid == "r14" else [])
                    + ([{"path": ["attributions", "[total_leverage]"], "value": "removed"}] if mid == "r22" else [])
                    + ([{"path": ["confidence", "[interest_cover]"], "value": "removed"}] if mid == "r28" else [])
                    + ([{"path": [*APPENDS[mid][0], "[end]"], "value": "append " + json.dumps(APPENDS[mid][1], sort_keys=True)}]
                       if mid in APPENDS else []),
                    "issues": validator + rules, "validator_issues": validator, "rules_issues": rules, "literal": lit})
    return out


MUT_LIST = build_mutations()
# shape error (the product's pydantic shape_issues format "<field.path>: <message>"): one required key removed
SHAPE_ISSUE = "observations: Field required"
SHAPE_LITERAL = removed(copy.deepcopy(POS), ["observations"])

# blocked: attempt 0 invalid, attempt 1 invalid
BLOCKED = {
    "attempt_0": {"mutation": "r23", "issues": next(m["issues"] for m in MUT_LIST if m["id"] == "r23")},
    "attempt_1": {"mutation": "r03", "issues": next(m["issues"] for m in MUT_LIST if m["id"] == "r03")},
}

# tool-use refusals: journaled RULES(text, seen) issues
_all_pages = set(cited_pages(POS))
TOOL_USE = [
    {"id": "t01", "title": "decision page cited but never read", "literal": "positive",
     "read": sorted(_all_pages - {("prior_case", P1)}), "searched": True,
     "issues": tool_rule_issues(POS, _all_pages - {("prior_case", P1)}, True)},
    {"id": "t02", "title": "two pages never read", "literal": "positive",
     "read": sorted(_all_pages - {("update", P1), ("market_update", P1)}), "searched": True,
     "issues": tool_rule_issues(POS, _all_pages - {("update", P1), ("market_update", P1)}, True)},
    {"id": "t03", "title": "absence claimed without a search", "literal": "positive",
     "read": sorted(_all_pages), "searched": False, "issues": tool_rule_issues(POS, _all_pages, False)},
]
assert TOOL_USE[0]["issues"] == [f"{COMMON_UNREAD}: prior_case page:1"]
assert TOOL_USE[1]["issues"] == [f"{COMMON_UNREAD}: market_update page:1", f"{COMMON_UNREAD}: update page:1"]
assert TOOL_USE[2]["issues"] == [UNBACKED_ABSENCE]
assert not tool_rule_issues(POS, _all_pages, True)
assert not tool_rule_issues(NOO, set(cited_pages(NOO)), True)

# --- fixtures (composer only, derived values; not pack runs) -------------------------------------------------------
D0 = date(2026, 1, 10)
FIX_SIZES = {z["metric_id"]: (z["comparator"], Decimal(z["level_text"])) for z in POS["thesis"]["downside_sizes"]}


def fx(exp, real, exp_asof, real_asof, overall="Flagged Risk Materialized", labels=()):
    return {"exp": {k: Decimal(v) for k, v in exp.items()}, "real": {k: Decimal(v) for k, v in real.items()},
            "exp_asof": exp_asof, "real_asof": real_asof, "decision_date": D0, "sizes": FIX_SIZES, "records": 1,
            "overall": overall, "labels": list(labels)}


E_ALL = {"total_leverage": "1.67", "interest_cover": "6.00", "loan_bid": "98.50", "loan_offer": "99.25"}
EXP_DATES = {"total_leverage": D0, "interest_cover": D0, "loan_bid": date(2026, 1, 9), "loan_offer": date(2026, 1, 9)}
FIXTURE_INPUTS = {
    "fixture_unchanged": fx(E_ALL, E_ALL, EXP_DATES, {k: date(2026, 3, 31) for k in E_ALL}, "Thesis Confirmed",
                            ["Thesis Confirmed"] * 3),
    "fixture_partial": fx(E_ALL, {"total_leverage": "1.80"}, EXP_DATES, {"total_leverage": date(2026, 3, 31)},
                          "Flagged Risk Materialized", ["Flagged Risk Materialized"]),
    "fixture_price_up": fx(E_ALL, {"loan_bid": "99.00", "loan_offer": "99.50"}, EXP_DATES,
                           {"loan_bid": date(2026, 4, 29), "loan_offer": date(2026, 4, 29)}, "Thesis Confirmed",
                           ["Thesis Confirmed"]),
    "fixture_no_label": fx(E_ALL, {}, EXP_DATES, {}, "Insufficient Information", []),
    "fixture_improved": fx(E_ALL, {"total_leverage": "1.50", "interest_cover": "7.25"}, EXP_DATES,
                           {"total_leverage": date(2026, 6, 30), "interest_cover": date(2026, 6, 30)},
                           "Right for Wrong Reason", ["Right for Wrong Reason", "Right for Wrong Reason"]),
    # leverage moved up (1.70 > 1.67) but not beyond the size (1.75); cover moved down to exactly the level (5.75,
    # not below it): neither size is breached, so the breach is a known false, not a missing value
    "fixture_not_breached": fx(E_ALL, {"total_leverage": "1.70", "interest_cover": "5.75"}, EXP_DATES,
                               {"total_leverage": date(2026, 3, 31), "interest_cover": date(2026, 3, 31)},
                               "Thesis Confirmed", ["Thesis Confirmed", "Thesis Confirmed"]),
}
FIXTURES = {}
for _name, _inp in FIXTURE_INPUTS.items():
    _d = derive(_inp)
    FIXTURES[_name] = {"inputs": {"expected": {k: dstr(v) for k, v in _inp["exp"].items()},
                                  "realized": {k: dstr(v) for k, v in _inp["real"].items()},
                                  "decision_date": D0.isoformat(),
                                  "realized_as_of": {k: v.isoformat() for k, v in _inp["real_asof"].items()},
                                  "downside_sizes": {k: {"comparator": c, "level": dstr(v)} for k, (c, v) in _inp["sizes"].items()},
                                  "overall_label": _inp["overall"], "metric_labels": _inp["labels"]},
                       "stored": stored(_d)}
assert FIXTURES["fixture_unchanged"]["stored"]["total_leverage"]["direction"] == "Unchanged"
assert FIXTURES["fixture_unchanged"]["stored"]["total_leverage"]["magnitude"] == "0.00"
assert FIXTURES["fixture_unchanged"]["stored"]["hit_rate"] == "1"
assert FIXTURES["fixture_partial"]["stored"]["interest_cover"]["variance"] is None
assert FIXTURES["fixture_partial"]["stored"]["loan_mid"]["realized"] is None
assert FIXTURES["fixture_price_up"]["stored"]["loan_mid"]["variance"] == "0.00375"
assert FIXTURES["fixture_price_up"]["stored"]["loan_mid"]["magnitude_bp"] == "37.5"
assert FIXTURES["fixture_no_label"]["stored"]["hit_rate"] is None and FIXTURES["fixture_no_label"]["stored"]["window_days"] is None
# nothing compared: the distribution and the direction counts are missing, never a stored 0 (review M4)
assert FIXTURES["fixture_no_label"]["stored"]["distribution"] is None and FIXTURES["fixture_no_label"]["stored"]["by_direction"] is None
assert FIXTURES["fixture_unchanged"]["stored"]["by_direction"] == {"Higher": 0, "Lower": 0, "Unchanged": 3}
assert FIXTURES["fixture_improved"]["stored"]["interest_cover"]["variance"] == "1.25"
assert FIXTURES["fixture_improved"]["stored"]["window_days"] == 171
# the recorded downside size is decided in Python: strictly beyond the level; null without a realized value or a size
_br = {n: {m: f["stored"][m]["downside_breach"] for m in METRICS} for n, f in FIXTURES.items()}
assert _br["fixture_unchanged"] == {"total_leverage": False, "interest_cover": False, "loan_mid": None}
assert _br["fixture_partial"] == {"total_leverage": True, "interest_cover": None, "loan_mid": None}
assert _br["fixture_price_up"] == {"total_leverage": None, "interest_cover": None, "loan_mid": None}
assert _br["fixture_no_label"] == {"total_leverage": None, "interest_cover": None, "loan_mid": None}
assert _br["fixture_improved"] == {"total_leverage": False, "interest_cover": False, "loan_mid": None}
assert _br["fixture_not_breached"] == {"total_leverage": False, "interest_cover": False, "loan_mid": None}
assert FIXTURES["fixture_not_breached"]["stored"]["total_leverage"]["direction"] == "Higher"
assert FIXTURES["fixture_not_breached"]["stored"]["interest_cover"]["direction"] == "Lower"
# the expected values of the Prior Case record do not breach its own sizes (the sizes are not trivially met)
assert breach_of(FIX_SIZES["total_leverage"], Decimal(LEV_AT_DECISION)) is False
assert breach_of(FIX_SIZES["interest_cover"], Decimal(COVER_AT_DECISION)) is False
DECISION_FIXTURES = {}
for _name, _cur in (("fixture_cp6_absent", None), ("fixture_cp6_same", ("Neutral", "Medium")),
                    ("fixture_cp6_conf_changed", ("Neutral", "Low")),
                    ("fixture_cp6_changed", ("Underweight", "Low")),
                    ("fixture_cp6_insufficient", ("Insufficient Information", "Low"))):
    _k, _t = current_decision_text("Neutral", "Medium", _cur)
    DECISION_FIXTURES[_name] = {"prior": ["Neutral", "Medium"], "current_cp6": list(_cur) if _cur else None,
                                "kind": _k, "text": _t}
assert DECISION_FIXTURES["fixture_cp6_same"]["text"] == "Action bias unchanged at Neutral; confidence unchanged at Medium."
assert DECISION_FIXTURES["fixture_cp6_changed"]["text"] == "Action bias changed from Neutral to Underweight; confidence changed from Medium to Low."
assert DECISION_FIXTURES["fixture_cp6_absent"]["kind"] == "missing" and DECISION_FIXTURES["fixture_cp6_insufficient"]["kind"] == "missing"


# --- assembly --------------------------------------------------------------------------------------------------------------
def run_of(case):
    return {"run_id": RUNS[case], "issuer_id": ISSUER_ID, "issuer_name": ISSUER, "as_of": RUN_AS_OF,
            "method_version": "deploy-v-r14", "case_kind": "synthetic", "pathway": "credit_snapshot",
            "requested_modules": ["CP-8"]}


def main():
    reviews = {c: readiness_review(c) for c in ("positive", "no_outcome", "no_record")}
    cp0 = {c: cp0_expected(pack_rows(PACK_IDS[c]), reviews[c], RUNS[c], PLAN, ["CP-8"]) for c in reviews}
    assert cp0["positive"]["exact_commands"] == {"CP-8": "Run CP-8"} and cp0["no_outcome"]["exact_commands"] == {"CP-8": "Run CP-8"}
    assert cp0["no_record"]["exact_commands"] == {"CP-8": "DO NOT RUN"}
    cases = {}
    for c, lit in LITERALS.items():
        inp = inputs_of(lit, PACK_IDS[c].count(DECISION_SOURCE))
        d = derive(inp)
        tables, claims, own = compose_case(c, lit, inp, d)
        by_id = {f["fact_id"]: f for t in tables for r in t["rows"] for f in r["facts"]}
        for cl in claims:
            for ref in cl["refs"]:
                assert ref.split("|")[0] in by_id, ref
        missing = [f["fact_id"] for f in by_id.values() if f["status"] != "known"]
        inherited = [t for t in cp0[c]["limitations"] if t not in own]
        cases[c] = {
            "run": run_of(c),
            "pack_sources": [{"source_id": sid, "name": NAMES[sid], "sha256": SHA[sid], "status": "ready"} for sid in PACK_IDS[c]],
            "status": "restricted",
            "derived": stored(d),
            "missing_not_zero": missing,
            "tables": tables,
            "claims": claims,
            "own_limitations": own,
            "inherited_limitations": inherited,
            "inherited_rule": "CP-0 head limitations then CP-0 inherited, de-duplicated, own removed (execution.py:345-366)",
            "module_inputs": ["prepared-pack", "CP-0", "decision-ledger-submission"],
            "tool_use_required": {"read_pages_cover": [list(p) for p in cited_pages(lit)],
                                  "search_pack_min": 1 if absence_paths(lit) else 0, "read_inputs_calls": 0},
        }
    pos = cases["positive"]["derived"]
    assert pos["total_leverage"] == {"expected": "1.67", "realized": "1.80", "variance": "0.13", "direction": "Higher", "magnitude": "0.13", "downside_breach": True}
    assert pos["interest_cover"] == {"expected": "6.00", "realized": "5.50", "variance": "-0.50", "direction": "Lower", "magnitude": "0.50", "downside_breach": True}
    assert pos["loan_mid"] == {"expected": "0.98875", "realized": "0.98375", "variance": "-0.00500", "direction": "Lower", "magnitude": "0.00500", "magnitude_bp": "50", "downside_breach": None}
    assert pos["window_days"] == 109 and pos["window_end"] == "2026-04-29" and pos["hit_rate"] == "0"
    assert cases["no_outcome"]["derived"]["window_days"] is None and cases["no_outcome"]["derived"]["hit_rate"] is None
    assert cases["no_outcome"]["derived"]["distribution"] is None and cases["no_outcome"]["derived"]["by_direction"] is None
    assert pos["decisions_recorded"] == 1 and cases["no_outcome"]["derived"]["decisions_recorded"] == 1
    manifest = {
        "schema_version": "cp8-owner-cases/1",
        "scope": "CP-8 decision ledger and post-mortem owner inputs: a two-module run CP-0 then CP-8 over a pack with a Prior Case record (the D5 prior-report input) and later issuer and dealer sources",
        "status": "DRAFT revision 3 (fix round 2) by owner-preparation task cp8-owner, 2026-10-28; not executed",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "pins": {**PINS},
        "method_source": {"path": R14_SKILL, "sha256": R14_SKILL_SHA, "steps_path": R14_STEPS, "steps_sha256": R14_STEPS_SHA,
                          "provenance_literal": True, "read_by_builder": False,
                          "note": "r14 CP-8 skill and its step bundle: outside this repository, never opened by the builder (a provenance literal; the reviewer verifies the hashes by hand once). The T7.1-T7.8 columns follow its Output profile (T7.3 Evidence and T7.8 Missing Item included); the adaptations (titles, extra columns, split columns, the metric set and every rule below) are recorded in work/lead/cp8-owner-preparation/methods-cp8-draft.md"},
        "design_reference": {"directory": DESIGN_DIR, "sha256": DESIGN_SHA, "provenance_literal": True, "read_by_builder": False,
                             "note": "outside this repository, never opened by the builder (a provenance literal; verified by hand once)",
                             "not_produced": ["Design-system band tile 'Since last Report' with the state word 'Deteriorated', 'Prior Case <date>' and '<N> changes' (rbot-design-system.dc.html line 95; FP01 'C · Not in this Pathway, Prior Case present, Blocked module in the band'): this oracle produces no band tile, no state word (Deteriorated or any other) and no change count; the what-changed block is the only rendered CP-8 section"]},
        "market_source_pin": {"file_read": MARKET_FILE, "file_pinned": True, "file_sha256": PINS[MARKET_FILE], "source_sha256": MARKET_SHA,
                              "why": "the file is pinned by its own sha256 (committed 4e6997c) and its page bytes by the source sha256; only used to check the Prior Case record's dealer quotation and the later sheet's instrument line against the frozen sheet. A change to either hash fails the build"},
        "reuse": {"identity": "cases/financial/manifest.json source identity, bytes unchanged (the only frozen source in the pack; it carries the issuer-confirmation citation CP-0 needs)"},
        "synthetic_sources": {
            "SYNTHETIC": True,
            "label": "Invented test data. No figure, name or statement in the three new sources is an issuer or market fact; every page of each says so (asserted).",
            "page_label": SYN_LABEL, "pack_limitation": SYN_LIM, "pack_limitation_in": "CP-0 P5 and T8 limits of every row that attaches the source, and the CP-0 limitations (readiness_review source limitations)",
            "never_part_of_a_product_pack": True,
        },
        "new_sources": {sid: {"name": NAMES[sid], "authority_in_cp0": AUTHORITY[sid], "sha256": SHA[sid],
                              "pack_limitation": LIMIT[sid],
                              "status": "ready", "media_type": "text/plain", "extractor": "supplied-representation",
                              "extraction_status": "complete",
                              "representation_scope": "Supplied located-page UTF-8 text only; not PDF or text_content extraction",
                              "pages": [{"locator": l, "text": t} for l, t in PAGES[sid].items()]}
                        for sid in ("prior_case", "update", "market_update")},
        "consistency_with_frozen_sources": [
            f"Prior Case record page:2 total leverage {LEV_AT_DECISION}x is the frozen LTM Q4 2025 total_leverage_reported 5/3 shown to two places (cases/financial/manifest.json q4_ltm_metric_oracle); interest cover {COVER_AT_DECISION}x is the frozen 6",
            "Prior Case record page:2 dealer quotation bid 98.50 and offer 99.25 as of January 9, 2026 equals the frozen market sheet page:1 (cases/cp3-cp6-owner/manifest.json market_source, sha256 c175d14b...)",
            "Instrument name, senior secured term loan and final maturity December 31, 2029 in the later sheet equal the frozen sheet page:1 and financial page:5",
            "The decision (Neutral, Medium, thesis, single dealer quotation just below par) is consistent with, but does not depend on, the CP-6 oracle draft (cases/cp3-cp6-owner); that file is not read for its CP-6 content",
            "All outcome figures (1.80x, 5.50x, bid 98.00, offer 98.75) are dated after the frozen period (March 31 and April 29, 2026) and contradict no frozen figure",
            f"The pre-decision comparative on update page:1 (twelve months to December 31, 2025, {LEV_AT_DECISION}x) is the same frozen LTM Q4 2025 leverage as the Prior Case record; it exists so the validator's rule that a realized observation must be dated after the decision is reachable (refusal r12); the line 'No default or restructuring had occurred as of December 31, 2025.' beside it makes the same rule reachable for the default statement (refusal r57) without also failing the subject rule (r60)",
            "The update note's line 'Total leverage for the twelve months to February 28, 2026 was reported as 1.70x.' is invented; it is used only by refusal r68 (a realized figure that does not breach the recorded size) and by no accepted literal",
            "The sizes named in the Prior Case record's downside line (total leverage above 1.75x, interest cover below 5.75x) are invented; Python (breach_of, strictly beyond the level) decides the breach: 1.80x and 5.50x breach them, the expected 1.67x and 6.00x do not, and the fixtures fixture_unchanged, fixture_improved and fixture_not_breached (1.70x; 5.75x equal to the level) do not (asserted)",
        ],
        "run": {"requested_modules": ["CP-8"], "plan_order": PLAN, "live_consumers_of_cp0": ["CP-8"],
                "pathway": "credit_snapshot", "pathway_note": "an explicit requested_modules overrides the preset (as the CP-L10 and CP-DR runs); FP01 carries the what-changed block",
                "plan_with_cp6": PLAN_WITH_CP6, "optional_cp6": "CP-6 is not selected in the cases; the edge is probed by registry only"},
        "cases": [{"case_id": c, "run": run_of(c), "pack_sources": [{"source_id": s, "sha256": SHA[s]} for s in PACK_IDS[c]],
                   "submission": f"submissions.json#{c}" if c in LITERALS else None,
                   "readiness_review": f"submissions.json#readiness_review.{c}"} for c in ("positive", "no_outcome", "no_record")],
        "table_ids": {"CP-8": CP8_TABLES, "used": CP8_TABLES, "unregistered_rails_table": "cp8.what_changed",
                      "cp0_table_id_T7": "CP-0 registers the single id T7, a different string; fact ids are module-scoped"},
    }
    submissions = {
        "schema_version": "cp8-owner-submissions/1",
        "note": "Literal analyst submissions for the CP-8 step decision_ledger. Quoted values (decision fields, figures, dates) must occur in their own verbatim quote; the core parses them with Python. Cell text of the thesis register is the verbatim quote, never a paraphrase. The analyst supplies no computed number. Only the readiness pack_sha256 placeholder is a run-time binding.",
        "readiness_review": reviews,
        "positive": LITERALS["positive"],
        "no_outcome": LITERALS["no_outcome"],
        "refusal_mutations": {"entries": MUT_LIST},
        "shape_refusal": {"id": "r00", "base": "positive", "removed_key": "observations", "issues": [SHAPE_ISSUE], "literal": SHAPE_LITERAL},
        "blocked": {"attempt_0": {**BLOCKED["attempt_0"], "literal": next(m["literal"] for m in MUT_LIST if m["id"] == "r23")},
                    "attempt_1": {**BLOCKED["attempt_1"], "literal": next(m["literal"] for m in MUT_LIST if m["id"] == "r03")}},
        "tool_use_refusals": TOOL_USE,
    }
    expected = {
        "schema_version": "cp8-owner-expected/1",
        "derivation": "Each value is an exact Decimal derivation from the quoted figures in the new sources (submissions.json) by the conventions in 'arithmetic'; nothing is read from code under test. Gap cells are spelled with the product's gap spelling; G# is bound at run time.",
        "cell_notation": {
            "num_basis_points": "unit basis_points is exact text plus ' bp' (report_view._UNIT_SUFFIX; no unit class): amount 50 shows '50 bp'",
            "num": "amount is the exact stored Decimal string; unit is the Fact unit; decimals is Fact.decimals; shown is the product spelling (display.py _number; report_view.fact_spelling): MULTIPLE shows the amount to `decimals` places with an x; decimal_fraction shows amount x 100 to `decimals` places with a percent sign; days, decisions and attributions are units with no class: exact text plus ' days' etc. (a count of one reads '1 decisions', cosmetic)",
            "gap": "status missing -> shown '∅ G#'; status not_applicable -> shown '∅ G# n.m.'; G# is bound at run time",
            "value_class": "source (quoted figure or verbatim quote), calculated (Python), analyst_judgment (label, process, basis, confidence, lessons, extra gaps, synthesis)",
            "calculated_cites": "a calculated fact carries the page-level cites of its inputs, or a calculation id when it has none",
            "claims": "text holds {fact_id|unit} figure references and [fact_id] gap chips only; resolved is the Python spelling; literal_text_outside_references holds no digit",
        },
        "arithmetic": {
            "decimal_context": "the builder sets its decimal context explicitly: 28 significant digits, ROUND_HALF_UP, and the Inexact, InvalidOperation and DivisionByZero signals trapped, so any rounding fails the build; every stored value is an exact decimal (the only divisions are by 2 and by 100: mid = (bid + offer) / 2 / 100)",
            "variance": "variance = realized - expected, exact; direction is Higher if variance > 0, Lower if < 0, Unchanged if 0 (descriptive only: r14 step 4 assigns no cause and no favourable/adverse reading); magnitude = abs(variance), shown unsigned in the unit of the measure. A zero variance is a known 0.00x, not a missing value",
            "multiples": "total leverage and interest cover are quoted to two places and stored as MULTIPLE decimals 2 (1.67, 6.00, 1.80, 5.50)",
            "loan_mid": "(bid + offer) / 2 in points of par, then / 100 stored as decimal_fraction decimals 3: expected (98.50 + 99.25) / 2 = 98.875 -> 0.98875 shown 98.875%; realized (98.00 + 98.75) / 2 = 98.375 -> 0.98375 shown 98.375%; variance -0.00500 (a fraction of par); the magnitude is shown in basis points of par, abs(variance) x 10000 = 50 (unit basis_points, shown '50 bp'; review L2: 0.500 is points of par, the relative move is 0.506%, so the percent spelling was withdrawn); derived.loan_mid.magnitude keeps the fraction 0.00500 and magnitude_bp carries 50",
            "observation_window": "days = latest realized as-of date - decision date (calendar days): 2026-04-29 - 2026-01-10 = 109 (21 + 28 + 31 + 29); missing, never 0, when no realized observation exists. The latest as-of is the March 31 period end for the issuer figures and the April 29 quotation date; the run as-of (April 30) is not used",
            "hit_rate": "decisions labelled Thesis Confirmed / decisions whose overall label is not Insufficient Information; stored as a decimal fraction (decimals 1: positive 0 shown 0.0%, a known zero over one labelled decision); missing, never 0, when no decision carries a label other than Insufficient Information (the no-outcome case). The definition is this preparation's adaptation (r14 REF_CP-8_07 names the measure without a formula)",
            "attribution_distribution": "count of metric attributions (overall excluded) per label of the six-label taxonomy, unit attributions; every label has a row, so a zero count is a known 0 only when at least one metric was compared; with none compared the distribution is missing (T7.7 gap cell) and the stored derived.distribution and derived.by_direction are null, never 0 (review M4)",
            "calibration_gate": "decisions recorded = the count of Prior Case (decision record) sources in the pack, Python-counted (1 here: one source, one record); required = 3, a schema rule and r14 REF_CP-8_06 constant, not a calculation (its formula text says so; review L1); gate met only if recorded >= required, so it is never met here: target module, specific prior, supporting decisions and advisory recommendation are not_applicable (shown n.m.), never 0 and never a recommendation",
            "module_status_cell": "Completed only when no outcome_absence, all three measures are compared AND no realized entry is Interim; otherwise Completed with Limitations (r14 REF_CP-8_01: 'decision recorded but observation window still open - interim tracking only'). Every realized entry here is Interim, so both cases are Completed with Limitations (review H2). Blocked is never a head status here: a missing decision record is refused at begin through CP-0 (DO NOT RUN)",
            "interim_final": "r14 marks an entry interim whenever the closing of the observation window is not observable (not observable -> interim): no source type here states that a window is closed, so every row of T7.3 is Interim, the four observation rows, the default or restructuring row and the window, including a row with no realized entry (its value cells are gaps, its Interim cell is a known fact); Final never occurs here",
            "downside_breach": "a recorded downside size (thesis.downside_sizes: metric total_leverage or interest_cover, comparator above or below, level N.NN, each metric once, with a quote that is a span of the recorded downside paths and states '<measure> <comparator> <level>x') is breached when the realized figure is strictly beyond the level, decided by Python in Decimal: above -> realized > level, below -> realized < level; equal is not breached. derived.<metric>.downside_breach is true, false or null (null without a size or without a realized value; always null for loan_mid); T7.5 carries the calculated fact T7.5.<metric>.breach 'Breached' or 'Not breached' citing the size quote and the realized quote (a gap cell, not applicable, for loan_mid and overall). A Flagged Risk Materialized metric attribution needs a recorded size and breached true; an overall Flagged Risk Materialized needs at least one Flagged metric attribution with breached true (not checked when nothing is compared: the dedicated rule reports it). The analyst quotes the size; the comparison is not the analyst's",
            "default_restructuring": "T7.3 row from the issuer statement 'No default or restructuring has occurred as of April 30, 2026.' (update page:1), shown verbatim with its as-of date (the validator requires the quote to state default or restructuring, an issuer source, and a date after the decision); r14 SKILL.md Outcome Metrics 'Default / restructuring incidence' (review M3). Missing (never 'none occurred') when no outcome source exists",
        },
        "table_id_check": {
            "registered_for_CP-8": CP8_TABLES,
            "occurs_in_other_module_table_ids": [],
            "cp0_registers": ["T7"],
            "note": "CP-0's single table id T7 is a different string from T7.1-T7.8 and fact ids are module-scoped; the builder asserts no module other than CP-8 lists a T7.n id. cp8.what_changed is an unregistered rails table (as cp6.committee_challenge)",
        },
        "cp0": cp0,
        "cases": cases,
        "fixtures": FIXTURES,
        "decision_fixtures": DECISION_FIXTURES,
        "refusals": [{"id": "r00", "issues": [SHAPE_ISSUE], "rules_issues": []}]
        + [{"id": m["id"], "issues": m["issues"], "rules_issues": m["rules_issues"]} for m in MUT_LIST],
        "refusal_coverage": {
            "rule": "one literal per validator class, each pinned with its complete journaled tuple (validator issues in rule order, then the RULES issues of the base's unread pages; asserted by the builder: check_submission(literal) == validator_issues and tool_rule_issues(literal, cited_pages(base), True) == rules_issues). One defect, one issue, with three pinned exceptions: r04 and r30 (a source outside the pack or the scope is also a cited page that was never read, so the validator issue is followed by one RULES issue; the CP-DR citation_outside_pack precedent) and r42 (the validator reports a metric attributed twice once per occurrence, so the tuple holds the same issue twice; the core's validator must not de-duplicate it; G1's _with_rules de-duplicates only when RULES adds issues, and RULES adds none here). r38 is a reserved id that carries no literal (untested class below)",
            "untested_classes": UNTESTED_CLASSES,
            "shared_code": "digit_free (digits, reference syntax, prohibited conclusion, empty) is one function applied to every analyst text path and ref_ok (pack, scope, page, quote) to every citing path; each class is exercised once (r23-r27, r03-r05, r30) and the path is not repeated per field. Source, locator and quote failures of ref_ok carry the product wording of readiness.citation_issues (r03, r04, r54, blocked attempt 1; probed); the scope and must-cite rules are this oracle's",
        },
        "tool_use_refusals": [{"id": t["id"], "issues": t["issues"]} for t in TOOL_USE],
        "blocked": {"attempt_0_issues": BLOCKED["attempt_0"]["issues"], "attempt_1_issues": BLOCKED["attempt_1"]["issues"],
                    "result": "attempt 0 invalid and re-begun as attempt 1 (repair_of set), attempt 1 invalid: module blocked, no tables, limitations = attempt 1's issues"},
        "refused": {
            "no_record": {
                "run": run_of("no_record"),
                "cp0_readiness": "BLOCKED, missing_source prior_case",
                "cp0_exact_command": cp0["no_record"]["exact_commands"],
                "begin": "refused with NotAuthorized: str(error) == \"CP-0 has not authorized this consumer's source readiness\"; commands == ('DO NOT RUN',); recorded as one RefusedBegin; no CP-8 attempt and no head",
                "rendered": "CP-8 has no head, so its status is unrun and FP01 what-changed shows state not_run with the note 'Not run: CP-8 has not run.' (report_view._honest_state; probed); this is not the design's 'Not shown: no Prior Case was accepted at Approval' (state condition, never produced)",
            },
            "edge_cp6_blocked": "plan(CP-8, CP-6) puts CP-6 before CP-8 and edge_rule(CP-8, CP-6) == block, so a blocked CP-6 refuses begin of CP-8 (execution.py:243-245); not run-level in this oracle (needs the S2 CP-6 owner run)",
            "begin_refused_cp0_blocked": "CP-0 blocked or stale refuses begin of CP-8 (edge block, no attempt consumed)",
            "stale_binding": "a snapshot change between the last read_pages and the submit refuses stale_binding",
        },
        "g1_refusals": {
            "invoke_extract_statements": "refused not_permitted receipt",
            "read_inputs": "refused not_permitted receipt (inputs=none: the step has no view)",
            "submit_before_any_read_pages": "valid payload still refused by RULES with one 'Cited page not read through read_pages' issue per unread cited page (journaled: consumes the attempt)",
            "audit": "a refused submit (not_permitted, stale_binding) is recorded in G1's audit and receipt, is not journaled and consumes no attempt",
        },
        "tamper": {
            "case": "positive (closed run: CP-0 and CP-8 settled, receipt sealed)",
            "target": "owners.cp8.probe rebuild refuses with identity_mismatch",
            "target_fact": "T7.4.total_leverage.direction",
            "from": "Higher",
            "to": "Lower",
            "why_this_fact": "the direction is Python-derived (variance sign) and lives only in the settled CP-8 result Module; the step output holds the submission references and no direction, and the table cell is in the Module. It is the one fact the probe's rebuild (derive over the journaled payload) contradicts. Frozen CP-DR recipe (docs/CPDR-OWNER-LEASE.md Tamper; cases/cpdr-owner/expected.json tamper) applied to this fact",
            "recipe": [
                "1. Copy the closed positive store directory (blobs, snapshots, current, audit) to a scratch path.",
                "2. Load the CP-8 head's result Module; replace only the text of fact T7.4.total_leverage.direction (Higher -> Lower); leave every other fact (including T7.4.total_leverage.magnitude and the cp8.what_changed lines), table, claim and limitation unchanged.",
                "3. Serialise the forged Module as Execution._store does (model_dump_json); its sha256 R2 must equal Module.content_hash(); write blobs/R2.",
                "4. Build a new ExecutionSnapshot equal to the current one with the CP-8 Attempt.result_sha256 and Head.result_sha256 set to R2 (status, inputs and commands unchanged, so head_of(forged Module) equals the Head) and the same parent; write snapshots/<its sha256>.json and rewrite current to that digest.",
                "5. In the retained receipt: set the CP-8 SettledHead.result_sha256 to R2; set receipt.snapshot_sha256 and every coordinate that named the old final snapshot (the CP-8 settling OwnerSubmission.snapshot_after_sha256: owner_workflow.py _advance -> _finish_walk; its record is retained as audit/submissions/<content_hash> by _retain) to the new digest; delete audit/submissions/<old record hash> and write the edited OwnerSubmission as audit/submissions/<its content_hash> (model_dump_json bytes); rewrite audit/receipt.sha256 with the forged receipt's content_hash (S1a R3-5 and CP-3 A4 pattern: the audit file travels under its new hash).",
            ],
            "expect": {
                "passes": "everything upstream of the probe: _verify_audit (owner_workflow.py:802-830) and every check before _PROBES (audit inventory, blob and snapshot hashes, ancestor walk, head_of equality, begin and publication records, call and read replay, journaled-step replay: the payload and step are untouched)",
                "refuses": "cp8.probe raises WorkflowError('identity_mismatch') (reached through _PROBES[head.module_id], owner_workflow.py:1182); verify_owner_run_receipt raises identity_mismatch",
                "test_asserts": "on the forged copy _verify_audit and every check before _PROBES pass; then cp8.probe raises identity_mismatch. Asserting identity_mismatch alone would not show that the probe was reached.",
            },
            "step_output_edit": "an edited CP-8 step output (or payload blob) is caught by the store's own blob hash check, not by the probe's output comparison (recorded limitation, S1a R3-5); this is why the target is a Module fact and not the step output",
        },
        "tool_use": {
            "rules": "the core RULES(text, seen) attribute (G1X protocol section 2): live/tools.py unread_citation_issues (sorted by source_id, locator) and the UNBACKED_ABSENCE text when any absence object (decision posture/size, thesis optional absences, outcome_absence) is present and no search was recorded; ToolRules order (absence, then unread)",
            "positive": "ok read_pages covers prior_case page:1, prior_case page:2, update page:1 and market_update page:1 before the submit; at least one ok search_pack; zero read_inputs; zero extract_statements",
            "no_outcome": "ok read_pages covers prior_case page:1 and page:2; at least one ok search_pack",
            "refused_calls": "extract_statements and read_inputs are refused not_permitted receipts for CP-8; identity is outside the host scope",
            "scope": {"sources": list(SCOPE_SOURCES), "excluded": ["identity"], "mechanism": "fixed host-side mapping (H1), never caller-supplied"},
        },
        "consumption": {
            "status": "OPEN",
            "reason": "No consumer core reads CP-8: CP-5 does not fan in over CP-8 (registry._NOT_CP5_FAN_IN), CP-2 reads only CP-1 and CP-1A, and no CP-1C or CP-3A core exists. The what-changed block is an assigned rendered section, not a consumer core (D3)",
            "reader_pinned": {
                "function": "cp8_reader(store, head)",
                "exposes": ["head sha256", "status", "overall attribution label and process_sound", "per measure direction and magnitude",
                            "observation window days", "hit rate or its absence", "decisions recorded and required", "own limitations"],
                "positive_values": {"overall": "Flagged Risk Materialized", "process_sound": "Y", "window_days": 109, "hit_rate": "0",
                                    "directions": {m: pos[m]["direction"] for m in METRICS}},
            },
            "cp6_reads": "CP-8 is itself a consumer of an optional producer: when CP-6 is in the run it reads CP-6's final-bias cells (T6-FINAL.final_bias.action_bias and .confidence, cp6_committee.settled_call) for the decision line; fixtures pin the text. Not exercised at run level here",
        },
        "render": {
            "pathway": "credit_snapshot",
            "design_reference": {"file": DESIGN_DIR + "rbot-fp-01-credit-snapshot.dc.html", "sha256": DESIGN_SHA["rbot-fp-01-credit-snapshot.dc.html"],
                                 "provenance_literal": True, "read_by_builder": False,
                                 "also": {DESIGN_DIR + k: v for k, v in DESIGN_SHA.items() if k != "rbot-fp-01-credit-snapshot.dc.html"},
                                 "rule": "read only; governs block ownership: the block 'What changed since the last Report' is owned by CP-8 (code CP-8) in FP01 to FP06 and sits in the collapsed rows"},
            "blocks": {"what-changed": {"owner": "CP-8", "layout": "prose _Spec (report_view.py:1099, exists)", "primary": "cp8.what_changed",
                                        "lines": "one per row of cp8.what_changed, in order: decision, then the metric lines, attribution, summary",
                                        "state_as_is": "populated (the _Spec has collapsed False)",
                                        "design_divergence": "the design draws the block in the collapsed rows (relative-value, company-profile, transaction-summary, portfolio-fit, committee-challenge, what-changed); the five siblings are collapsed=True, this one is not. One-line registration proposed: collapsed=True; the state would then be collapsed with a summary of the first line"}},
            "rails": {"evidence": ["T7.1", "T7.2", "T7.3", "T7.4", "T7.5", "T7.6", "T7.7"], "limitations": ["T7.8"]},
            "slot_prefix": "cp8-",
            "lines_positive": [f["shown"] for r in next(t for t in cases["positive"]["tables"] if t["table_id"] == "cp8.what_changed")["rows"] for f in r["facts"]],
            "gap_cells": "shown '∅ G<n>' with n bound at run time (the decision line in every case here)",
            "not_produced": "the design-system band tile 'Since last Report' with state word 'Deteriorated', 'Prior Case <date>' and '<N> changes' (rbot-design-system.dc.html line 95) is not produced: no state word, no tile, no change count; recorded, not hidden",
        },
        "not_verified": [
            "no CP-8 core, validator or composer exists; no value was compared with product output",
            "the CP-0 literals were probed with the product validators only on a hand-built pack (see the report)",
            "the G1-X RULES routing, owner-only pack-source seam and the fixed H1 scope are protocol text, not yet code",
            "display spellings follow display.py and report_view.py reading plus the probes listed in the report, not a render",
            "the authority value 'unknown' for the Prior Case record is the only fit in readiness.Authority; its limitation is required by validate_review",
            "the r14 skill, its step bundle and the design references are provenance literals (path and sha256): this builder never opens them, so only the reviewer's hand verification ties the hashes to the files",
            "the tamper recipe was not executed (no CP-8 core exists); the bid-exceeds-offer validator class has no literal (refusal_coverage.untested_classes)",
            "every validator issue string except 'Field required', the tool-use texts and the three citation failures (source outside the pack, no such locator, quote not found; readiness.citation_issues) is this oracle's wording; the page-straddle class of quotes.explain is not modelled by the builder (no running header or footer on the pages) and the three product-worded literals were compared with the product by hand",
            "the sizes 1.75x and 5.75x, the lines of 1.70x (February 28, 2026) and of no default at December 31, 2025, and the statement of no default at April 30, 2026 are invented test data",
        ],
    }
    for name, obj in (("manifest.json", manifest), ("submissions.json", submissions), ("expected.json", expected)):
        (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
