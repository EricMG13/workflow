"""Writes cases/cp2h-owner/{manifest,submissions,expected}.json (stdlib only).

An independent transcription of the CP-2H (Ratings migration trigger) composition rules written in
work/lead/cp2h-owner-preparation/lease-draft.md. deploy_vii is never imported or run here.
Every input file is pinned by sha256 and checked before use: the frozen financial pack
(cases/financial/manifest.json), the CP-0/CP-1 snapshot literals (cases/snapshot/submissions.json, the base of the
CP-0 review and CP-1 source context), the frozen CP-2G oracle (manifest, submissions, expected: the settled CP-2G
facts CP-2H consumes under their D3 pin) and src/deploy_vii/methodology.json (edges and table ids). The agency
rating source is SYNTHETIC (no frozen source carries a rating, a scale or a trigger term): its pages are literals of
this builder, parsed by the rule below, and agree with every frozen figure (consistency list in the manifest).
Every number is derived by exact arithmetic from the parsed source terms and the settled CP-2G facts in the
38-digit half-even context (decimal.Context(prec=38), the context of model/_cells.py), and cross-checked
against fractions.Fraction.

Run: python3 -I cases/cp2h-owner/builder/build.py   (from the repository root)
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
OUT = ROOT / "cases" / "cp2h-owner"
CTX = Context(prec=38, rounding=ROUND_HALF_EVEN)
D = Decimal

# --- 0. pinned inputs -------------------------------------------------------------------------

PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    "cases/cp2g-owner/manifest.json": "d69738e224d57c8f81ed4f966a6db8ea06dd2c6f5d4f2c58013d663a0b1cf95d",
    "cases/cp2g-owner/submissions.json": "25a96ebb6c0a16fca291684407161d53a4b1ee48c5fa7963bcc59d4d7f3bc69e",
    "cases/cp2g-owner/expected.json": "97328745be246b3bf67fe5840f291afb3da3cbae99b51db1ba7bd24d2eef406c",
    "src/deploy_vii/methodology.json": "0932d9fbcd9272d62bcb7681e1dd16d9bc944319c64716b41dc79715699796e8",
}


def pinned(rel):
    data = (ROOT / rel).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == PINS[rel], (rel, digest)
    return json.loads(data)


FIN = pinned("cases/financial/manifest.json")
SNAP = pinned("cases/snapshot/submissions.json")
G_MAN = pinned("cases/cp2g-owner/manifest.json")
G_SUB = pinned("cases/cp2g-owner/submissions.json")
G_EXP = pinned("cases/cp2g-owner/expected.json")
METHODOLOGY = pinned("src/deploy_vii/methodology.json")


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


SRC = {s["source_id"]: s for s in FIN["sources"]}
for _sid, _s in SRC.items():
    assert page_sha([p["text"] for p in _s["pages"]]) == _s["sha256"], _sid

MOD = {m["module_id"]: m for m in METHODOLOGY}
assert MOD["CP-2H"]["required"] == ["CP-0", "CP-1", "CP-2G"] and MOD["CP-2H"]["optional"] == ["CP-1D"]
assert "edge_rules" not in MOD["CP-2H"]
T2R_IDS = [f"T2R.{n}" for n in range(1, 11)]
assert sorted(MOD["CP-2H"]["table_ids"]) == sorted(T2R_IDS)
assert not any(t in m["table_ids"] for m in METHODOLOGY if m["module_id"] != "CP-2H" for t in T2R_IDS)
assert MOD["CP-2H"]["purpose"] == "Maps rating migration risk, trigger headroom and agency divergence."


# --- 1. exact arithmetic ----------------------------------------------------------------------


def fr(x):
    return x if isinstance(x, Fraction) else Fraction(x)


def q38(x):
    f = fr(x)
    if f == 0:
        return D(0)
    with localcontext(CTX):
        return D(f.numerator) / D(f.denominator)


def sub38(a, b):
    """One subtraction in the 38-digit half-even context; equals the correctly rounded rational (asserted)."""
    with localcontext(CTX):
        value = a - b
    assert value == q38(fr(a) - fr(b)), (a, b)
    return value


def norm(d):
    text = format(d, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def show(d, uc):
    """display.format_value for a known number: ROUND_HALF_UP on the exact value."""
    places, scale, suffix = {"multiple": (2, 1, "x"), "percent": (1, 100, "%")}[uc]
    rounded = (d * scale).quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP)
    assert not (rounded == 0 and d < 0), ("negative value rounds to zero", d)
    body = f"{abs(rounded):,.{places}f}"
    return (f"({body})" if rounded < 0 else body) + suffix


# --- 2. the synthetic agency source (pages are literals; the parse rule is the lease's) --------

HEAD = "NORTHBRIDGE SYNTHETIC GROUP\n"
PUBLISHED = "Published January 10, 2026.\n"
FICTION = "This invented case is test data, not evidence about a real issuer. Alder Ratings and Brook Credit are fictional agencies.\n"
REG_HEADER = "Agency  Instrument  Rating  Outlook  Date"
SCALE_HEADER = "Position  Alder Ratings  Brook Credit"
TRIG_HEADER = "Agency  Direction  Metric  Comparison  Threshold"
ALDER_REG = "Alder Ratings  Issuer rating  BB  Negative  2025-11-14"
BROOK_REG = "Brook Credit  Issuer rating  Ba3  Stable  2025-10-02"
BROOK_REG_WD = "Brook Credit  Issuer rating  Withdrawn  Not applicable  2025-12-05"
BROOK_WD_NOTE = "Brook Credit withdrew its issuer rating on 2025-12-05 and no longer publishes trigger terms."
T_TL = "Alder Ratings  Downgrade  Total debt to EBITDA  Above  2.75x"
T_IC = "Alder Ratings  Downgrade  EBITDA to cash interest  Below  3.50x"
T_FCF = "Alder Ratings  Downgrade  Free cash flow to total debt  Below  10.0%"
T_FCF_NS = "Alder Ratings  Downgrade  Free cash flow to total debt  Below  Not stated"
T_NL = "Brook Credit  Downgrade  Net debt to EBITDA  Above  2.25x"
T_NL_B = "Brook Credit  Downgrade  Net debt to EBITDA  Above  1.00x"  # boundary fixture: equals the FY2025 net leverage exactly
T_NU = "Brook Credit  Upgrade  Net debt to EBITDA  Below  0.50x"
SCALE_ROWS = ["9  BBB-  Baa3", "10  BB+  Ba1", "11  BB  Ba2", "12  BB-  Ba3", "13  B+  B1", "14  B  B2", "15  B-  B3"]


def page1(brook_withdrawn=False, header=True):
    lines = [HEAD.rstrip("\n"), "Credit rating summary", PUBLISHED.rstrip("\n"), FICTION.rstrip("\n"),
             "Ratings and outlooks are shown as published on the dates given. Page:2 maps each agency's scale to one combined scale."]
    if header:
        lines.append(REG_HEADER)
    lines += [ALDER_REG, BROOK_REG_WD if brook_withdrawn else BROOK_REG]
    if brook_withdrawn:
        lines.append(BROOK_WD_NOTE)
    return "\n".join(lines)


PAGE2 = "\n".join([HEAD.rstrip("\n"), "Rating scale equivalence", PUBLISHED.rstrip("\n"),
                   "A lower position number is a higher rating. Each position is one notch.", SCALE_HEADER, *SCALE_ROWS])
TERMS = ("Each agency states the terms below as conditions it would treat as a trigger for a rating review. Terms are tested at each fiscal year end "
         "on the Group's reported figures: total debt as reported in the statements, EBITDA as reported EBITDA, cash interest as cash interest paid, "
         "net debt as total debt less cash and cash equivalents, and free cash flow as levered free cash flow.")


def page3(rows, header=True):
    lines = [HEAD.rstrip("\n"), "Published rating trigger terms", PUBLISHED.rstrip("\n"), TERMS]
    if header:
        lines.append(TRIG_HEADER)
    return "\n".join(lines + rows)


SOURCES = {
    "positive": [page1(), PAGE2, page3([T_TL, T_IC, T_FCF, T_NL, T_NU])],
    "gap": [page1(brook_withdrawn=True), PAGE2, page3([T_TL, T_IC, T_FCF_NS])],
    "boundary": [page1(), PAGE2, page3([T_TL, T_IC, T_FCF, T_NL_B, T_NU])],
    "register_not_found": [page1(header=False), PAGE2, page3([T_TL, T_IC, T_FCF, T_NL, T_NU])],
    "terms_not_found": [page1(), PAGE2, page3([T_TL, T_IC, T_FCF, T_NL, T_NU], header=False)],
}
SRC_SHA = {k: page_sha(v) for k, v in SOURCES.items()}
RATINGS_ID = "ratings"
WITHDRAWN = ("Withdrawn", "Not rated")
METRIC_MAP = {  # source metric label -> (CP-2G T2H.6 field, unit class, CP-2G label, CP-1 reported metric)
    "Total debt to EBITDA": ("total_leverage", "multiple", "Total leverage", "total_leverage_reported"),
    "Net debt to EBITDA": ("net_leverage", "multiple", "Net leverage", "net_leverage_reported"),
    "EBITDA to cash interest": ("interest_coverage", "multiple", "Interest coverage", "interest_coverage_reported"),
    "Free cash flow to total debt": ("fcf_to_debt", "percent", "Free cash flow to debt", "fcf_to_debt"),
}


def fields_of(line):
    return re.split(r"\s{2,}", line.strip())


def parse_source(pages):
    """The core's parse rule. Page 1 holds the register after the header `Agency  Instrument  Rating  Outlook  Date`
    (consecutive lines of exactly five fields), page 2 the scale after `Position  Alder Ratings  Brook Credit`
    (position then one symbol per agency), page 3 the trigger terms after `Agency  Direction  Metric  Comparison  Threshold`.
    Fields split on two or more spaces. A missing header is an invalid attempt (returned alone)."""
    def block(page_text, header, width):
        """Rows after the header: a line with `width` fields is a row; a line with zero or one field ends the block;
        a line with two or more fields and any other count makes the block invalid (round 11 B2). Returns
        (rows, invalid); rows is None when the header is absent."""
        lines = page_text.split("\n")
        if header not in lines:
            return None, False
        rows = []
        for line in lines[lines.index(header) + 1:]:
            f = fields_of(line)
            if len(f) == width:
                rows.append((line, f))
            elif len(f) <= 1:
                break
            else:
                return rows, True
        return rows, False

    reg, reg_bad = block(pages[0], REG_HEADER, 5)
    scale, scale_bad = block(pages[1], SCALE_HEADER, 3)
    terms, terms_bad = block(pages[2], TRIG_HEADER, 5)
    # item 8 step 1: the headers, and a block ended at once by a line of one field or fewer, as built
    if reg is None or (not reg and not reg_bad):
        raise ValueError("Rating register not found")
    if scale is None or (not scale and not scale_bad):
        raise ValueError("Rating scale not found")
    if terms is None:
        raise ValueError("Trigger terms not found")
    # B2 then follows item 8's row steps: scale rows, register rows (with `Rating not on the scale`), terms rows
    if scale_bad:
        raise ValueError("Rating scale not found")
    agencies = fields_of(SCALE_HEADER)[1:]
    positions = {a: {} for a in agencies}
    for line, (pos, *syms) in scale:
        for a, s in zip(agencies, syms, strict=True):
            positions[a][s] = (int(pos), line)
    register = []
    for line, (agency, instrument, rating, outlook, date) in reg:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", date), line
        if rating in WITHDRAWN:
            pos = None
        else:
            if rating not in positions.get(agency, {}):
                raise ValueError(f"Rating not on the scale: {agency} {rating}")
            pos = positions[agency][rating]
        register.append({"line": line, "agency": agency, "instrument": instrument, "rating": rating, "outlook": outlook, "date": date, "position": pos})
    if reg_bad:
        raise ValueError("Rating register not found")
    if terms_bad:
        raise ValueError("Trigger terms not found")
    triggers = []
    for line, (agency, direction, metric, comparison, threshold) in terms:
        assert direction in ("Downgrade", "Upgrade") and comparison in ("Above", "Below"), line
        if metric not in METRIC_MAP:
            raise ValueError(f"Unrecognised trigger metric: {metric}")
        uc = METRIC_MAP[metric][1]
        if threshold == "Not stated":
            value = None
        else:
            m = re.fullmatch(r"(?:([0-9]+\.[0-9]{2})x|([0-9]+\.[0-9])%)", threshold)  # round 11 B1: N.NNx or N.N%
            assert m and (m.group(1) is not None) == (uc == "multiple"), line
            if uc == "multiple":
                value = D(m.group(1))
            else:  # exact exponent shift, no context rounding
                _t = D(m.group(2)).as_tuple()
                value = D((_t.sign, _t.digits, _t.exponent - 2))
        triggers.append({"line": line, "agency": agency, "direction": direction, "metric": metric, "comparison": comparison,
                         "threshold_text": threshold, "threshold": value})
    return {"register": register, "triggers": triggers}


PARSED = {k: parse_source(v) for k, v in SOURCES.items() if k in ("positive", "gap", "boundary")}
for _k in ("register_not_found", "terms_not_found"):
    try:
        parse_source(SOURCES[_k])
    except ValueError as _e:
        assert str(_e) == {"register_not_found": "Rating register not found", "terms_not_found": "Trigger terms not found"}[_k]
    else:
        raise AssertionError(_k)
assert [r["position"][0] for r in PARSED["positive"]["register"]] == [11, 12]
assert PARSED["gap"]["register"][1]["position"] is None and len(PARSED["gap"]["triggers"]) == 3


def cite(variant, page, quote):
    text = SOURCES[variant][page - 1]
    assert quote in text.split("\n"), quote
    return {"source_id": RATINGS_ID, "source_sha256": SRC_SHA[variant], "locator": f"page:{page}", "quote": quote}


# --- 3. the settled upstream facts CP-2H consumes ----------------------------------------------

ROWS = ["a25", "b26", "b27", "b28", "d26", "d27", "d28"]
YEAR_ROWS = {"base": ["b26", "b27", "b28"], "down": ["d26", "d27", "d28"]}
BASE_YEAR = 2025
YEARS = [BASE_YEAR + n for n in (1, 2, 3)]
FY = [f"FY{y}" for y in YEARS]
FY_PERIOD = [f"FY{y}: {y}-01-01 to {y}-12-31" for y in YEARS]
FY_SPAN = f"{FY[0]}-{FY[-1]}: {YEARS[0]}-01-01 to {YEARS[-1]}-12-31"
LTM_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
CASE_LABEL = {"base": "Base", "down": "Downside"}
GAP_SPELLING = {"missing": ("gap", "∅ G#"), "not_applicable": ("not_meaningful", "∅ G# n.m.")}
UNIT = {"multiple": "MULTIPLE", "percent": "PERCENT"}


def cp2g_head(case):
    """CP-2G's settled T2H.6 credit-metric facts (the four ratios for the FY2025 actual and the six forecast rows), read from the frozen
    CP-2G oracle; the head's own facts, copied verbatim into cp2g_references."""
    exp = G_EXP["cases"][case]
    facts = {f["fact_id"]: f for f in exp["facts"]}
    ratio = {}
    for r in ROWS:
        for _label, (field, *_rest) in METRIC_MAP.items():
            ratio[(r, field)] = facts[f"T2H.6.{r}.{field}"]
    cp1 = exp["cp1_inputs"]
    return {"case": case, "ratio": ratio, "cp1": cp1, "status": exp["module_status"], "source": f"cases/cp2g-owner/expected.json cases.{case}"}


# --- 4. the literal analyst submissions --------------------------------------------------------

VIEWS = ("Downgrade pressure", "Stable", "Upgrade potential", "Not assessable")
FIGS = {
    "total_leverage_reported": {"metric": "total_leverage_reported", "unit_token": "x"},
    "net_leverage_reported": {"metric": "net_leverage_reported", "unit_token": "x"},
}


def fig(name):
    return "{{FIG:" + name + "|" + FIGS[name]["unit_token"] + "}}"


def views_positive():
    v = "positive"
    return [
        {"agency": "Alder Ratings", "view": "Downgrade pressure", "category": "Analyst Interpretation", "confidence": "Medium",
         "rationale": "Total debt to EBITDA leaves {T2R.4.t01.headroom|x} of headroom to the downgrade trigger on the latest reported fiscal year, and the base case widens it. "
                      "In the downside case the cash interest coverage and free cash flow triggers are both reached in the first forecast year, so the pressure comes from the downside path rather than from today's figures.",
         "evidence": [cite(v, 3, T_TL), cite(v, 3, T_IC), cite(v, 1, ALDER_REG)],
         "limitation": "The downside path rests on an analyst-chosen CP-2A shock and on CP-2G's analyst-assumed drivers."},
        {"agency": "Brook Credit", "view": "Stable", "category": "Analyst Interpretation", "confidence": "Low",
         "rationale": "The net debt to EBITDA downgrade trigger leaves {T2R.4.t04.headroom|x} of headroom on the latest reported fiscal year and is not reached in the base case; in the downside case it is reached from the second forecast year. "
                      "The upgrade trigger is reached in the base case only in the final forecast year, so an upgrade is not near.",
         "evidence": [cite(v, 3, T_NL), cite(v, 3, T_NU), cite(v, 1, BROOK_REG)],
         "limitation": "Both agencies' terms are read at fiscal year end; sustained-period conditions are not stated in the source."},
    ]


OVERALL_POS = {
    "rationale": f"On reported figures the issuer starts with {fig('total_leverage_reported')} total leverage and {fig('net_leverage_reported')} net leverage, inside every published downgrade trigger. "
                 "The two agencies' ratings differ by {T2R.8.p01.notches|notches} on the combined scale, and the downside forecast, not the opening position, is what puts a rating review in reach.",
    "category": "Analyst Interpretation", "confidence": "Medium",
    "limitation": "Every forecast driver behind the forward headroom is an analyst assumption without a source citation."}
GAPS_POS = [{"gap": "No agency report states how long a trigger must be breached before a rating review.",
             "why_it_matters": "Reaching a trigger in one fiscal year may not be a rating event, so the timing is the earliest possible, not the expected.",
             "affected_analysis": "Trigger timing and migration view", "severity": "Material",
             "action": "Obtain the agencies' full criteria and rerun the trigger test."}]
SUBMISSION = {"positive": {"views": views_positive(), "overall": OVERALL_POS, "gaps": GAPS_POS}}
_g = "gap"
SUBMISSION["gap"] = {
    "views": [
        {"agency": "Alder Ratings", "view": "Stable", "category": "Analyst Interpretation", "confidence": "Low",
         "rationale": "Total debt to EBITDA leaves {T2R.4.t01.headroom|x} of headroom to the downgrade trigger on the latest reported fiscal year. The free cash flow trigger has no stated threshold, so its headroom cannot be calculated.",
         "evidence": [cite(_g, 3, T_TL), cite(_g, 3, T_FCF_NS)],
         "limitation": "One of the three published downgrade triggers cannot be tested."},
        {"agency": "Brook Credit", "view": "Not assessable", "category": "Insufficient Information", "confidence": "Insufficient Information",
         "rationale": "The rating is withdrawn and no trigger terms are published, so no migration view is formed for this agency.",
         "evidence": [cite(_g, 1, BROOK_WD_NOTE)], "limitation": "No current rating or trigger terms exist for this agency."}],
    "overall": {"rationale": f"Only one agency now rates the issuer, so there is no divergence to assess; total leverage is {fig('total_leverage_reported')} on reported figures.",
                "category": "Analyst Interpretation", "confidence": "Low", "limitation": "The agency source is incomplete: one threshold is not stated and one agency has withdrawn."},
    "gaps": [{"gap": "The free cash flow trigger threshold is not stated and the second agency has withdrawn its rating.",
              "why_it_matters": "Headroom to that trigger and any agency divergence cannot be calculated.",
              "affected_analysis": "Trigger headroom and agency divergence", "severity": "Material",
              "action": "Obtain the full agency report and the withdrawal notice, then rerun."}]}


def neutral_views(variant, brook_line):
    """The composer-fixture views; each cites the fixture's own source variant (the quote is on the page it names)."""
    return [
        {"agency": "Alder Ratings", "view": "Stable", "category": "Analyst Interpretation", "confidence": "Low",
         "rationale": "Total debt to EBITDA leaves {T2R.4.t01.headroom|x} of headroom to the downgrade trigger on the latest reported fiscal year.",
         "evidence": [cite(variant, 3, T_TL)], "limitation": "A composer fixture view: it states nothing about the forecast."},
        {"agency": "Brook Credit", "view": "Stable", "category": "Analyst Interpretation", "confidence": "Low",
         "rationale": "The net debt to EBITDA downgrade trigger leaves {T2R.4.t04.headroom|x} of headroom on the latest reported fiscal year.",
         "evidence": [cite(variant, 3, brook_line)], "limitation": "A composer fixture view: it states nothing about the forecast."}]


NEUTRAL_OVERALL = {"rationale": f"On reported figures total leverage is {fig('total_leverage_reported')} and net leverage is {fig('net_leverage_reported')}.",
                   "category": "Analyst Interpretation", "confidence": "Low", "limitation": "A composer fixture assessment: it states nothing about the forecast."}
SUBMISSION["fixture"] = {"views": neutral_views("positive", T_NL), "overall": NEUTRAL_OVERALL, "gaps": GAPS_POS}
SUBMISSION["fixture_boundary"] = {"views": neutral_views("boundary", T_NL_B), "overall": NEUTRAL_OVERALL, "gaps": GAPS_POS}
CASES = {
    "positive": {"source": "positive", "cp2g": "gap", "sub": "positive", "execution": "run"},
    "gap": {"source": "gap", "cp2g": "gap", "sub": "gap", "execution": "run"},
    "fixture_total_loss": {"source": "positive", "cp2g": "fixture_total_loss", "sub": "fixture", "execution": "composer_only"},
    "fixture_boundary": {"source": "boundary", "cp2g": "gap", "sub": "fixture_boundary", "execution": "composer_only"},
}
NOTCH_UNIT, POS_UNIT, COUNT_UNIT = "notches", "scale position", "triggers"
FORECAST_LIMITATION = "Forward headroom rests on CP-2G's forecast, which uses analyst-assumed drivers"
THRESHOLD_NS = "Not calculable: the trigger threshold is not stated in the agency source"
TAMPER_TARGET, TAMPER_FROM, TAMPER_TO = "T2R.6.t04.down_first", "FY2027", "Not reached by FY2028"


def first_result(results):
    """Text of the first forecast year in which a trigger is reached; a year not calculable before it makes the answer unknowable."""
    unknown = False
    for t, hit in enumerate(results):
        if hit is None:
            unknown = True
        elif hit:
            return "Not calculable" if unknown else FY[t]
    return "Not calculable" if unknown else f"Not reached by {FY[-1]}"


# --- 5. composition ----------------------------------------------------------------------------

TABLES = {
    "T2R.1": "Upstream register", "T2R.2": "Agency rating register", "T2R.3": "Published trigger terms", "T2R.4": "Current trigger headroom",
    "T2R.5": "Forward trigger headroom", "T2R.6": "Trigger timing", "T2R.7": "Migration assessment", "T2R.8": "Agency divergence",
    "T2R.9": "Trigger summary", "T2R.10": "Gaps ledger"}
BLOCKS = {"rating-triggers": {"title": "Rating triggers", "owner": "CP-2H", "kind": "dense", "producers": ["CP-2H"],
                              "tabs": [["T2R.9", "Summary"], ["T2R.4", "Current headroom"], ["T2R.5", "Forward headroom"], ["T2R.6", "Trigger timing"],
                                       ["T2R.7", "Migration view"], ["T2R.8", "Agency divergence"]]}}
EVIDENCE_TABLES = ["T2R.1", "T2R.2", "T2R.3", "cp1_references", "cp2g_references"]
LIMITATION_TABLES = ["T2R.10"]


def spell_figs(text, figs):
    return re.sub(r"\{\{FIG:([a-z_]+)\|[^}]*\}\}", lambda m: figs[m.group(1)]["spelled"], text)


def phrase_texts(sub):
    """Every prose field the phrase guard covers: rationales, limitations (view and overall), gap fields."""
    yield from prose_texts(sub)
    for v in sub["views"]:
        yield v["limitation"] or ""
    yield sub["overall"]["limitation"] or ""


def prose_texts(sub):
    for v in sub["views"]:
        yield v["rationale"]
    yield sub["overall"]["rationale"]
    for g in sub["gaps"]:
        yield from (g["gap"], g["why_it_matters"], g["affected_analysis"], g["action"])


def build_case(name):
    spec = CASES[name]
    sub, src, head = SUBMISSION[spec["sub"]], PARSED[spec["source"]], cp2g_head(spec["cp2g"])
    variant = spec["source"]
    facts, rows_by_table, claim_list, own_limits = [], {t: [] for t in TABLES}, [], []
    by_id, cites = {}, {}
    fields_by_table = {}

    def fact(table, row, field, label, **kw):
        rec = {"fact_id": f"{table}.{row}.{field}", "table_id": table, "row_id": row, "field": field, "label": label}
        rec.update(kw)
        facts.append(rec)
        by_id[rec["fact_id"]] = rec
        return rec

    def lineage(derives, own=()):
        out = list(own)
        for d_ in derives:
            if d_.startswith(("cp1:", "cp2g:")):
                continue
            assert d_ in by_id, d_
            assert by_id[d_]["status"] == "known", ("a known fact derives from an unsettled fact", d_)
            out += cites.get(d_, [])
        return [c for i, c in enumerate(out) if c not in out[:i]]

    def numeric(table, row, field, label, value, kind, formula, value_class="calculated", derives=(), period=None, citations=()):
        unit = {"multiple": "MULTIPLE", "percent": "PERCENT"}.get(kind, kind)
        shown = show(value, kind) if kind in ("multiple", "percent") else f"{norm(value)} {kind}"
        derives = list(derives) if value_class == "calculated" else []
        cs = lineage(derives, citations)
        rec = fact(table, row, field, label, status="known", unit=unit, period=period, amount_exact=norm(value), shown=shown, decimals=None,
                   value_class=value_class, formula=formula, calculation_id=f"calc:{table}.{row}.{field}" if value_class == "calculated" else None,
                   derives_from=derives)
        if cs:
            rec["citations"] = cs
        cites[rec["fact_id"]] = cs
        return rec

    def unsettled(table, row, field, label, kind, reason, status="missing", period=None):
        unit = {"multiple": "MULTIPLE", "percent": "PERCENT"}.get(kind, kind)  # the twin's unit, not a generic one
        return fact(table, row, field, label, status=status, unit=unit, period=period, amount_exact=None, shown=None, limitation=reason)

    def textf(table, row, field, label, value, value_class=None, derives=(), citations=()):
        rec = fact(table, row, field, label, status="known", text=value, shown=value, value_class=value_class)
        if derives:
            rec["derives_from"] = list(derives)
        cs = lineage(derives, citations)
        if cs:
            rec["citations"] = cs
        cites[rec["fact_id"]] = cs
        return rec

    def missing_text(table, row, field, label, reason, status="missing"):
        return fact(table, row, field, label, status=status, text=None, shown=None, limitation=reason)

    def reg(table, row_id, label, fields):
        rows_by_table[table].append({"row_id": row_id, "label": label, "fact_ids": [f"{table}.{row_id}.{f}" for f in fields]})

    # figure registry (CP-1 reported ratios, referenced in prose through cp1_references)
    figs = {}
    for fname, f in FIGS.items():
        c1 = head["cp1"][f["metric"]]
        assert c1["status"] == "known"
        figs[fname] = {"unit_token": f["unit_token"], "cp1_metric": f["metric"], "spelled": c1["cell_text"]}

    # T2R.1 upstream register
    for row, module, status, basis, read, lim in (
        ("u_cp1", "CP-1", "restricted", f"Base period {LTM_PERIOD}", "T4.10 reported leverage, coverage and free cash flow to debt",
         "Inherits CP-1's own limitations."),
        ("u_cp2g", "CP-2G", head["status"] if spec["execution"] == "run" else "restricted",  # B7: the bound Input status; composer-only cases use an explicit restricted stand-in
          f"Forecast {FY[0]}-{FY[-1]} on the base period {LTM_PERIOD}", "T2H.6 credit metrics for the FY2025 actual, base case and downside case",
         "Forecast on analyst-assumed drivers."),
        ("u_cp1d", "CP-1D", "not part of this run", "Not applicable", "Nothing read", "CP-1D (earnings quality) is an optional input that this version never reads.")):
        for f, l, v in (("module", "Module", module), ("status", "Status", status), ("basis", "Basis", basis), ("read", "Read", read), ("limitation", "Limitation", lim)):
            textf("T2R.1", row, f, l, v)
        reg("T2R.1", row, module, ["module", "status", "basis", "read", "limitation"])

    # T2R.2 agency rating register (source facts, cited)
    agency_row = {}
    for n, r in enumerate(src["register"], 1):
        row = f"r{n:02d}"
        agency_row[r["agency"]] = row
        c_line = [cite(variant, 1, r["line"])]
        period = f"Rating dated {r['date']}"
        textf("T2R.2", row, "agency", "Agency", r["agency"], "source", citations=c_line)
        textf("T2R.2", row, "instrument", "Instrument", r["instrument"], "source", citations=c_line)
        textf("T2R.2", row, "rating", "Rating", r["rating"], "source", citations=c_line)
        textf("T2R.2", row, "outlook", "Outlook", r["outlook"], "source", citations=c_line)
        textf("T2R.2", row, "date", "Rating date", r["date"], "source", citations=c_line)
        if r["position"] is None:
            unsettled("T2R.2", row, "position", "Position on the combined scale", POS_UNIT,
                      f"{r['agency']}'s rating is {r['rating'].lower()}, so it has no position on the scale", "not_applicable", period)
        else:
            numeric("T2R.2", row, "position", "Position on the combined scale", D(r["position"][0]), POS_UNIT, "scale position stated in the source mapping",
                    "source", period=period, citations=[cite(variant, 2, r["position"][1])])
        reg("T2R.2", row, r["agency"], ["agency", "instrument", "rating", "outlook", "date", "position"])

    # T2R.3 published trigger terms (source facts, cited)
    trig = []
    for n, t in enumerate(src["triggers"], 1):
        row = f"t{n:02d}"
        field, uc, cp2g_label, cp1_metric = METRIC_MAP[t["metric"]]
        c_line = [cite(variant, 3, t["line"])]
        textf("T2R.3", row, "agency", "Agency", t["agency"], "source", citations=c_line)
        textf("T2R.3", row, "direction", "Direction", t["direction"], "source", citations=c_line)
        textf("T2R.3", row, "metric", "Metric", t["metric"], "source", citations=c_line)
        textf("T2R.3", row, "comparison", "Comparison", t["comparison"], "source", citations=c_line)
        period = "Terms published 2026-01-10, tested at each fiscal year end"
        if t["threshold"] is None:
            unsettled("T2R.3", row, "threshold", "Threshold", uc, "The trigger threshold is not stated in the agency source", period=period)
        else:
            numeric("T2R.3", row, "threshold", "Threshold", t["threshold"], uc, "threshold stated in the agency source", "source", period=period, citations=c_line)
        reg("T2R.3", row, f"{t['agency']} {t['direction'].lower()}: {t['metric']}", ["agency", "direction", "metric", "comparison", "threshold"])
        trig.append(dict(t, row=row, field=field, uc=uc, cp2g_label=cp2g_label, cp1_metric=cp1_metric))

    def metric_value(r, t):
        fct = head["ratio"][(r, t["field"])]
        if fct["status"] != "known":
            return None, fct["limitation"], fct
        return D(fct["amount_exact"]), None, fct

    def headroom_of(t, v):
        """Distance to the trigger: threshold - metric for Above, metric - threshold for Below; percentages become percentage points."""
        raw = sub38(t["threshold"], v) if t["comparison"] == "Above" else sub38(v, t["threshold"])
        assert raw == q38(fr(t["threshold"]) - fr(v) if t["comparison"] == "Above" else fr(v) - fr(t["threshold"]))
        return raw.scaleb(2, context=CTX) if t["uc"] == "percent" else raw

    def hit_of(t, v):
        return v > t["threshold"] if t["comparison"] == "Above" else v < t["threshold"]

    hunit = lambda t: "pp" if t["uc"] == "percent" else "multiple"  # noqa: E731
    hform = lambda t: ("(threshold - metric)" if t["comparison"] == "Above" else "(metric - threshold)") + (" x 100, percentage points" if t["uc"] == "percent" else "")  # noqa: E731

    # T2R.4 current headroom (FY2025 actual); T2R.5 forward headroom; T2R.6 timing
    results = {}
    for t in trig:
        row, thr_id = t["row"], f"T2R.3.{t['row']}.threshold"
        thr_known = t["threshold"] is not None
        v0, why0, f0 = metric_value("a25", t)
        textf("T2R.4", row, "metric", "Metric", t["metric"], derives=[f"T2R.3.{row}.metric"])
        if v0 is None:
            unsettled("T2R.4", row, "actual", "FY2025 actual", t["uc"], why0, period=LTM_PERIOD)
        else:
            numeric("T2R.4", row, "actual", "FY2025 actual", v0, t["uc"], f"Copy of CP-2G {f0['fact_id']}", derives=[f"cp2g:{f0['fact_id']}"], period=LTM_PERIOD)
        reason0 = THRESHOLD_NS if not thr_known else why0
        if reason0 is None:
            h0 = headroom_of(t, v0)
            numeric("T2R.4", row, "headroom", "Headroom to the trigger", h0, hunit(t), hform(t), derives=[f"T2R.4.{row}.actual", thr_id], period=LTM_PERIOD)
            reached0 = hit_of(t, v0)
            textf("T2R.4", row, "status", "Status", "Reached" if reached0 else "Not reached", derives=[f"T2R.4.{row}.actual", thr_id])
        else:
            unsettled("T2R.4", row, "headroom", "Headroom to the trigger", hunit(t), reason0, period=LTM_PERIOD)
            missing_text("T2R.4", row, "status", "Status", reason0)
        c1 = head["cp1"][t["cp1_metric"]]
        if v0 is not None and c1["status"] == "known":
            check = "Reconciled to CP-1" if v0 == D(c1["amount_exact"]) else "Differs from CP-1"
            assert check == "Reconciled to CP-1", (name, row)
            textf("T2R.4", row, "check", "Check", check, derives=[f"T2R.4.{row}.actual", f"cp1:{t['cp1_metric']}"])
        else:
            textf("T2R.4", row, "check", "Check", "Not compared")
        reg("T2R.4", row, f"{t['agency']} {t['direction'].lower()}: {t['metric']}", ["metric", "actual", "headroom", "status", "check"])
        results[row] = {"fy25_headroom": None if reason0 else h0, "fy25_reached": None if reason0 else reached0}

        res = {}
        for case in ("base", "down"):
            hrs, hits, whys = [], [], []
            for k, r in enumerate(YEAR_ROWS[case]):
                v, why, fct = metric_value(r, t)
                reason = THRESHOLD_NS if not thr_known else why
                if reason:
                    hrs.append(None), hits.append(None), whys.append(reason)
                else:
                    hrs.append(headroom_of(t, v)), hits.append(hit_of(t, v)), whys.append(None)
            rid = f"{row}_{case}"
            for k, r in enumerate(YEAR_ROWS[case]):
                if hrs[k] is None:
                    unsettled("T2R.5", rid, f"y{k + 1}", FY[k], hunit(t), whys[k], period=FY_PERIOD[k])
                else:
                    ders = [f"cp2g:{head['ratio'][(r, t['field'])]['fact_id']}", thr_id]
                    numeric("T2R.5", rid, f"y{k + 1}", FY[k], hrs[k], hunit(t), hform(t), derives=ders, period=FY_PERIOD[k])
            if all(h is not None for h in hrs):
                tight = min(hrs)
                numeric("T2R.5", rid, "tightest", "Tightest headroom", tight, hunit(t), "lowest of the three forecast years",
                        derives=[f"T2R.5.{rid}.y{k + 1}" for k in range(3)], period=FY_SPAN)
                textf("T2R.5", rid, "tightest_year", "Tightest year", FY[hrs.index(tight)], derives=[f"T2R.5.{rid}.y{k + 1}" for k in range(3)])
            else:
                why_t = next(w for w in whys if w)
                unsettled("T2R.5", rid, "tightest", "Tightest headroom", hunit(t), why_t, period=FY_SPAN)
                missing_text("T2R.5", rid, "tightest_year", "Tightest year", why_t)
            reg("T2R.5", rid, f"{t['agency']} {t['metric']}, {CASE_LABEL[case].lower()} case", ["y1", "y2", "y3", "tightest", "tightest_year"])
            res[case] = {"headroom": hrs, "hits": hits, "whys": whys, "first": first_result(hits)}
        desc = f"{t['agency']} {t['direction'].lower()}: {t['metric']} {t['comparison'].lower()} its threshold"
        textf("T2R.6", row, "trigger", "Trigger", desc, derives=[f"T2R.3.{row}.agency", f"T2R.3.{row}.direction", f"T2R.3.{row}.metric", f"T2R.3.{row}.comparison"])
        for case in ("base", "down"):
            label = f"First year reached, {CASE_LABEL[case].lower()} case"
            if res[case]["first"] != "Not calculable":
                ders = [thr_id] + [f"cp2g:{head['ratio'][(r, t['field'])]['fact_id']}" for r in YEAR_ROWS[case]]
                textf("T2R.6", row, f"{case}_first", label, res[case]["first"], derives=ders)
            else:
                t0 = next(i for i, h in enumerate(res[case]["hits"]) if h is None)
                missing_text("T2R.6", row, f"{case}_first", label, res[case]["whys"][t0])
        reg("T2R.6", row, desc, ["trigger", "base_first", "down_first"])
        results[row].update(res)

    # T2R.7 migration assessment (analyst judgment, literal)
    for n, v in enumerate(sub["views"], 1):
        row = f"a{n:02d}"
        textf("T2R.7", row, "agency", "Agency", v["agency"], derives=[f"T2R.2.{agency_row[v['agency']]}.agency"])
        textf("T2R.7", row, "view", "Migration view", v["view"], "analyst_judgment")
        textf("T2R.7", row, "confidence", "Confidence", v["confidence"], "analyst_judgment")
        reg("T2R.7", row, v["agency"], ["agency", "view", "confidence"])

    # T2R.8 agency divergence (Python: notch difference on the combined scale)
    reg_rows = src["register"]
    pair = []
    for i in range(len(reg_rows)):
        for j in range(i + 1, len(reg_rows)):
            pair.append((reg_rows[i], reg_rows[j]))
    divergence = []
    for n, (ra, rb) in enumerate(pair, 1):
        row = f"p{n:02d}"
        ia, ib = agency_row[ra["agency"]], agency_row[rb["agency"]]
        textf("T2R.8", row, "first_agency", "First agency", ra["agency"], derives=[f"T2R.2.{ia}.agency"])
        textf("T2R.8", row, "second_agency", "Second agency", rb["agency"], derives=[f"T2R.2.{ib}.agency"])
        if ra["position"] is None or rb["position"] is None:
            who = ra if ra["position"] is None else rb
            why = f"{who['agency']}'s rating is {who['rating'].lower()}, so no notch comparison is made"
            unsettled("T2R.8", row, "notches", "Notches apart", NOTCH_UNIT, why, "not_applicable", "As of 2026-01-10")
            missing_text("T2R.8", row, "lower_rated", "Lower rated", why, "not_applicable")
            missing_text("T2R.8", row, "outlook_match", "Outlooks", why, "not_applicable")
            divergence.append({"row": row, "notches": None, "lower": None, "outlooks": None})
        else:
            pa, pb = ra["position"][0], rb["position"][0]
            numeric("T2R.8", row, "notches", "Notches apart", D(abs(pa - pb)), NOTCH_UNIT, "absolute difference of the two positions on the combined scale",
                    derives=[f"T2R.2.{ia}.position", f"T2R.2.{ib}.position"], period="As of 2026-01-10")
            lower = "Same rating" if pa == pb else (ra["agency"] if pa > pb else rb["agency"])
            textf("T2R.8", row, "lower_rated", "Lower rated", lower, derives=[f"T2R.2.{ia}.position", f"T2R.2.{ib}.position", f"T2R.2.{ia}.agency", f"T2R.2.{ib}.agency"])
            om = "Same" if ra["outlook"] == rb["outlook"] else "Different"
            textf("T2R.8", row, "outlook_match", "Outlooks", om, derives=[f"T2R.2.{ia}.outlook", f"T2R.2.{ib}.outlook"])
            divergence.append({"row": row, "notches": abs(pa - pb), "lower": lower, "outlooks": om})
        reg("T2R.8", row, f"{ra['agency']} and {rb['agency']}", ["first_agency", "second_agency", "notches", "lower_rated", "outlook_match"])

    # T2R.9 trigger summary (its own registered table: one totals row)
    def count(case, direction):
        return [t["row"] for t in trig if t["direction"] == direction and results[t["row"]][case]["first"] not in ("Not calculable",) and not results[t["row"]][case]["first"].startswith("Not reached")]

    ncalc = {c_: [t["row"] for t in trig if results[t["row"]][c_]["first"] == "Not calculable"] for c_ in ("base", "down")}
    totals = {"downgrade_base": count("base", "Downgrade"), "downgrade_down": count("down", "Downgrade"), "upgrade_base": count("base", "Upgrade"), "upgrade_down": count("down", "Upgrade")}
    numeric("T2R.9", "total", "triggers", "Triggers tested", D(len(trig)), COUNT_UNIT, "count of published trigger terms", derives=[f"T2R.3.{t['row']}.direction" for t in trig], period=FY_SPAN)
    for key, label in (("downgrade_base", "Downgrade triggers reached, base case"), ("downgrade_down", "Downgrade triggers reached, downside case"),
                       ("upgrade_base", "Upgrade triggers reached, base case"), ("upgrade_down", "Upgrade triggers reached, downside case")):
        case = "base" if key.endswith("base") else "down"
        numeric("T2R.9", "total", key, label, D(len(totals[key])), COUNT_UNIT, "count of triggers with a first year reached",
                derives=[f"T2R.6.{r}.{case}_first" for r in totals[key]], period=FY_SPAN)
    for case in ("base", "down"):
        numeric("T2R.9", "total", f"not_calculable_{case}", f"Triggers not calculable, {CASE_LABEL[case].lower()} case", D(len(ncalc[case])), COUNT_UNIT,
                f"count of triggers whose {CASE_LABEL[case].lower()}-case first-year result is missing", derives=[f"T2R.3.{r}.direction" for r in ncalc[case]], period=FY_SPAN)
    reg("T2R.9", "total", "All triggers", ["triggers", "downgrade_base", "downgrade_down", "upgrade_base", "upgrade_down", "not_calculable_base", "not_calculable_down"])

    # T2R.10 gaps ledger
    for n, g in enumerate(sub["gaps"], 1):
        r = f"g{n:02d}"
        textf("T2R.10", r, "id", "Gap id", f"CP-2H-GAP-{n:03d}")
        for fld, label in (("gap", "Gap"), ("why_it_matters", "Why it matters"), ("affected_analysis", "Affected analysis")):
            textf("T2R.10", r, fld, label, g[fld], "analyst_judgment")
        textf("T2R.10", r, "severity", "Severity", g["severity"])
        textf("T2R.10", r, "action", "Action", g["action"], "analyst_judgment")
        reg("T2R.10", r, f"Gap {n}", ["id", "gap", "why_it_matters", "affected_analysis", "severity", "action"])

    # table shape: one fact per column in every row, every fact in exactly one row (contracts.validate_tables)
    placed = set()
    for tid, rows in rows_by_table.items():
        assert rows, (name, tid)
        cols = [fid.split(".", 2)[2] if False else fid.rsplit(".", 1)[1] for fid in rows[0]["fact_ids"]]
        for r in rows:
            assert [fid.rsplit(".", 1)[1] for fid in r["fact_ids"]] == cols, (name, tid, r["row_id"])
            for fid in r["fact_ids"]:
                assert fid in by_id and fid not in placed, (name, fid)
                placed.add(fid)
        fields_by_table[tid] = cols
    assert placed == set(by_id), (name, sorted(set(by_id) - placed))
    for x in facts:  # status/value shape (contracts.Fact.value_semantics)
        if x["status"] == "known":
            assert (x.get("text") is None) != (x.get("amount_exact") is None) or x.get("text") is not None
            if x.get("amount_exact") is not None:
                assert x["unit"] and x["period"], x["fact_id"]
        else:
            assert x["limitation"] and x.get("shown") is None, x["fact_id"]

    # --- references: CP-1 reported ratios (verbatim) and the CP-2G facts read (verbatim) ---
    named = []
    for t_ in prose_texts(sub):
        named += re.findall(r"FIG:([a-z_]+)", t_)
    ref_metrics = list(dict.fromkeys([FIGS[n_]["metric"] for n_ in dict.fromkeys(named)] + [t["cp1_metric"] for t in trig]))
    cp1_rows = []
    for n, metric in enumerate(ref_metrics, 1):
        c1 = head["cp1"][metric]
        fig_name = next((k for k in dict.fromkeys(named) if FIGS[k]["metric"] == metric), None)
        cp1_rows.append({"row_id": f"ref{n:02d}", "figure": fig_name, "label": f"{c1['label']} · {c1['period']}", "cp1_label": c1["label"], "period": c1["period"],
                         "status": c1["status"], "unit": {"percent": "%", "multiple": "x"}[c1["unit_class"]], "shown": c1["cell_text"],
                         "cell_text": c1["cell_text"], "value_class": c1["value_class"], "amount_exact": c1["amount_exact"], "limitation": c1["limitation"],
                         "fact_id": "bound at run time: the unique T4.10 fact with label cp1_label (manifest.json cp1_fact_selection_rule); the module carries the CP-1 fact verbatim under this fact_id"})
    cp1_references = {"table_id": "cp1_references", "title": "CP-1 facts referenced in CP-2H text and compared in T2R.4", "row_header": "CP-1 fact", "rows": cp1_rows}
    g_rows = []
    for n, ((r, field), fct) in enumerate(((k, head["ratio"][k]) for k in head["ratio"] if any(t["field"] == k[1] for t in trig)), 1):
        g_rows.append({"row_id": f"ref{n:02d}", "fact_id": fct["fact_id"], "label": fct.get("label"), "period": fct.get("period"), "status": fct["status"], "unit": fct.get("unit"),
                       "shown": fct.get("shown"), "value_class": fct.get("value_class"), "amount_exact": fct.get("amount_exact"), "limitation": fct.get("limitation")})
    cp2g_references = {"table_id": "cp2g_references", "title": "CP-2G facts read by CP-2H (T2H.6 credit metrics)", "row_header": "CP-2G fact", "rows": g_rows}

    # --- claims ---
    def ref(fid, token):
        x = by_id[fid]
        return "{" + fid + "|" + token + "}" if x["status"] == "known" else "[" + fid + "]"

    def rendered(text_):
        return re.sub(r"\{([A-Za-z0-9_.:-]+)\|([^}]*)\}", lambda m: by_id[m.group(1)]["shown"], text_)

    def claim(cid, text_, limitation, citations=(), python=False):
        entry = {"claim_id": cid, "text": text_, "limitation": limitation, "citations": list(citations)}
        if "{{FIG:" in text_:
            entry["text_rendered"] = rendered(spell_figs(text_, figs))
            entry["cp1_references"] = re.findall(r"FIG:([a-z_]+)", text_)
        else:
            entry["cp1_references"] = []
        claim_list.append(entry)

    for n, v in enumerate(sub["views"], 1):
        claim(f"T2R.7.a{n:02d}", v["rationale"], v["limitation"], v["evidence"])
    claim("T2R.7.overall", sub["overall"]["rationale"], sub["overall"]["limitation"], [])
    for t in trig:
        h = f"T2R.4.{t['row']}.headroom"
        claim(f"T2R.4.{t['row']}", f"{t['agency']} {t['direction'].lower()} trigger on {t['metric']}: FY2025 headroom is {ref(h, 'pp' if t['uc'] == 'percent' else 'x')}.", None, python=True)
    for case in ("base", "down"):
        lab = CASE_LABEL[case].lower()
        claim(f"T2R.6.{case}", f"In the {lab} case, downgrade triggers reached by {FY[-1]}: {ref(f'T2R.9.total.downgrade_{case}', COUNT_UNIT)}; upgrade triggers reached: {ref(f'T2R.9.total.upgrade_{case}', COUNT_UNIT)}; "
              f"triggers not calculable: {ref(f'T2R.9.total.not_calculable_{case}', COUNT_UNIT)}.", FORECAST_LIMITATION, python=True)
    for d_ in divergence:
        fid = f"T2R.8.{d_['row']}.notches"
        if by_id[fid]["status"] == "known":
            claim("T2R.8." + d_["row"], f"The two agencies' ratings are {ref(fid, NOTCH_UNIT)} apart on the combined scale.", None, python=True)
        else:
            claim("T2R.8." + d_["row"], f"The agencies' ratings cannot be compared: {ref(fid, NOTCH_UNIT)}.", None, python=True)
    for c in claim_list:
        if "text_rendered" not in c:
            c["text_rendered"] = rendered(c["text"])

    # --- own limitations (exact strings) ---
    own_limits.append("Agency ratings, outlooks, scale mappings and trigger terms are read from one synthetic source naming fictional agencies; no real agency report is an input.")
    own_limits.append("Trigger terms are tested at each fiscal year end on CP-2G's reported-basis ratios; agency-adjusted definitions and any condition that a breach be sustained are not modelled.")
    own_limits.append("A trigger is reached only on a strict comparison: a metric equal to its threshold has not reached it and shows zero headroom.")
    own_limits.append("Headroom is the distance still to travel: for an upgrade trigger it is the distance to the level that would meet the term, and a reached upgrade trigger is not a rating change.")
    own_limits.append("Forward headroom is only as reliable as the CP-2G forecast, which uses analyst-assumed drivers.")
    own_limits.append("The migration view is the analyst's judgment on the published terms and the CP-2G path; no probability is computed, no rating is assigned and no agency action is predicted.")
    own_limits.append("The notch difference is measured on the source's combined scale; outlook weighting and sub-notch differences are not modelled.")
    own_limits.append("CP-1D (earnings quality) is not part of this run, so no earnings-quality adjustment is applied to the reported ratios.")
    for t in trig:
        if t["threshold"] is None:
            own_limits.append(f"The trigger threshold is not stated for {t['agency']} {t['direction'].lower()}: {t['metric']}: its headroom and timing are Not calculable.")
    for r in src["register"]:
        if r["position"] is None:
            own_limits.append(f"{r['agency']}'s rating is {r['rating'].lower()}: no notch comparison is made and no trigger terms are published.")
    for t in trig:
        for case in ("base", "down"):
            if results[t["row"]][case]["first"] == "Not calculable":
                own_limits.append("A trigger whose metric is not calculable in a forecast year is missing, with the reason, when no earlier year has reached it.")
                break
        else:
            continue
        break
    for g in sub["gaps"]:
        own_limits.append(f"Gap ({g['severity']}): {g['gap']}")
    own_limits = list(dict.fromkeys(own_limits))

    module_tables = [{"table_id": t, "title": title, "columns": fields_by_table[t], "rows": rows_by_table[t]} for t, title in TABLES.items()]
    fp = {"pathway": "distressed_restructuring", "blocks": {}}

    def cell(fid):
        x = by_id[fid]
        if x["status"] == "known":
            return {"fact_id": fid, "field": x["field"], "shown": x["shown"], "state": "known"}
        state, text = GAP_SPELLING[x["status"]]
        return {"fact_id": fid, "field": x["field"], "shown": text, "state": state}

    for bid, b in BLOCKS.items():
        tabs = []
        for tid, label in b["tabs"]:
            table = next(t for t in module_tables if t["table_id"] == tid)
            tabs.append({"table_id": tid, "label": label, "rows": [{"row_id": r["row_id"], "label": r["label"], "cells": [cell(f) for f in r["fact_ids"]]} for r in table["rows"]]})
        fp["blocks"][bid] = {"title": b["title"], "owner": b["owner"], "kind": b["kind"], "state": "populated", "tabs": tabs}
    fp["other_blocks"] = "every other distressed_restructuring block keeps its idle wording; CP-2H fills only rating-triggers (the CP-2A, CP-2G, CP-2D and CP-3C blocks are asserted by their own leases)"
    fp["evidence_rail_tables"] = EVIDENCE_TABLES
    fp["limitations_rail_tables"] = LIMITATION_TABLES
    return {
        "source_variant": variant, "source_sha256": SRC_SHA[variant],
        "parsed_source": {"register": [{k: v for k, v in r.items() if k != "line"} | {"position": None if r["position"] is None else r["position"][0]} for r in src["register"]],
                          "triggers": [{k: (norm(v) if isinstance(v, Decimal) else v) for k, v in t.items() if k != "line"} for t in src["triggers"]]},
        "cp2g_head": {"source": head["source"], "case": head["case"], "module_status": head["status"], "facts_read": sorted({r_["fact_id"] for r_ in g_rows})},
        "cp1_inputs": {m: head["cp1"][m] for m in ref_metrics}, "figures": {k: v for k, v in figs.items()},
        "cp1_references": cp1_references, "cp2g_references": cp2g_references,
        "results": {r: {"fy25_headroom": None if x["fy25_headroom"] is None else norm(x["fy25_headroom"]), "fy25_reached": x["fy25_reached"],
                        **{c: {"headroom": [None if h is None else norm(h) for h in x[c]["headroom"]], "hits": x[c]["hits"], "first": x[c]["first"]} for c in ("base", "down")}}
                    for r, x in results.items()},
        "divergence": divergence, "totals": {k: v for k, v in totals.items()} | {f"not_calculable_{c_}": ncalc[c_] for c_ in ("base", "down")},
        "facts": facts, "tables": module_tables, "claims": claim_list, "own_limitations": own_limits,
        "module_status": "restricted" if spec["execution"] == "run" else "composer_only", "FP05": fp,
    }


# --- 6. refusals -------------------------------------------------------------------------------

HIGH = "High is not allowed: forward headroom rests on analyst-assumed drivers"
ENUM_VIEW = "Input should be 'Downgrade pressure', 'Stable', 'Upgrade potential' or 'Not assessable'"
ENUM_CONF = "Input should be 'High', 'Medium', 'Low' or 'Insufficient Information'"
ENUM_CAT = "Input should be 'Documentary Fact', 'Management Language', 'Analyst Interpretation' or 'Insufficient Information'"
RATING_CALL = ("rating call", ("will be downgraded", "will be upgraded", "will downgrade", "will upgrade", "is certain to be", "our rating", "we rate", "shadow rating", "implied rating"))
PROBABILITY = ("probability weighting", ("probability-weighted", "probability weighted", "weighted by probability", "expected value", "likelihood-weighted"))


def refusals():
    pos = SUBMISSION["positive"]

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
        e = {"id": rid, "class": klass, "mutation": mutation, "issue_kind": kind, "expected_issues": issues}
        e.update(extra)
        e["payload"] = payload
        out.append(e)

    add("r01", "view outside the enumeration", "views[0].view = 'Downgrade imminent'", mut(set_(("views", 0, "view"), "Downgrade imminent")), [f"views.0.view: {ENUM_VIEW}"], "shape")
    add("r02", "confidence outside the enumeration", "overall.confidence = 'Very High'", mut(set_(("overall", "confidence"), "Very High")), [f"overall.confidence: {ENUM_CONF}"], "shape")
    add("r03", "category outside the enumeration", "views[1].category = 'Opinion'", mut(set_(("views", 1, "category"), "Opinion")), [f"views.1.category: {ENUM_CAT}"], "shape")
    add("r04", "required field absent", "overall.limitation removed", mut(lambda d: d["overall"].pop("limitation")), ["overall.limitation: Field required"], "shape")
    add("r05", "unknown field", "top-level key 'extra' added", mut(lambda d: d.update(extra=1)), ["extra: Extra inputs are not permitted"], "shape")
    out.append({"id": "r06", "class": "not JSON", "mutation": "payload text '{not json'", "issue_kind": "shape",
                "expected_issues": ["(root): Invalid JSON: key must be a string at line 1 column 2"], "payload": None, "payload_text": "{not json"})
    add("r07", "no view at all", "views = []", mut(set_(("views",), [])), ["views: Tuple should have at least 1 item after validation, not 0"], "shape")
    add("r08", "view without evidence", "views[1].evidence = []", mut(set_(("views", 1, "evidence"), [])), ["views.1.evidence: Tuple should have at least 1 item after validation, not 0"], "shape")
    add("r09", "citation field absent", "views[0].evidence[0].quote removed", mut(lambda d: d["views"][0]["evidence"][0].pop("quote")), ["views.0.evidence.0.quote: Field required"], "shape")
    # content issues, order: views (register order), overall, gaps
    def extra_view(agency):
        def apply(d):
            d["views"].append(dict(deepcopy(d["views"][0]), agency=agency))
        return apply

    add("v01", "agency not in the register", "a third view is appended (a copy of views[0]) with agency 'Zeta Ratings'; both registered agencies keep their view", mut(extra_view("Zeta Ratings")),
        ["views[2].agency: not an agency in the rating register: Zeta Ratings"], "content")
    add("v02", "a registered agency has no view", "views loses Brook Credit", mut(lambda d: d["views"].pop()), ["views: no view for agency Brook Credit"], "content")
    add("v03", "duplicate agency", "a third view is appended (a copy of views[0]) for 'Alder Ratings'; both registered agencies keep their view", mut(extra_view("Alder Ratings")),
        ["views[2].agency: duplicate agency Alder Ratings"], "content")
    add("v04", "bare figure in prose", "views[0].rationale states '2.75x'", mut(set_(("views", 0, "rationale"), "The downgrade trigger sits at 2.75x total debt to EBITDA.")),
        ["views[0].rationale: Bare figure: 2.75x"], "content")
    add("v05", "unresolved reference", "views[0].rationale names {T9.9.value|x}", mut(set_(("views", 0, "rationale"), "The trigger leaves {T9.9.value|x} of headroom.")),
        ["views[0].rationale: Unresolved reference: T9.9.value"], "content")
    add("v06", "unit-mismatched reference", "views[0].rationale: the token unit 'x' replaced by '%'",
        mut(set_(("views", 0, "rationale"), pos["views"][0]["rationale"].replace("{T2R.4.t01.headroom|x}", "{T2R.4.t01.headroom|%}"))),
        ["views[0].rationale: Unit % differs from the fact's unit x: T2R.4.t01.headroom"], "content")
    ph_paths = ["overall.rationale"]
    add("v07", "figure placeholder left unreplaced", "the payload is sent with every {{FIG:..}} still in place", deepcopy(pos),
        [f"{p_}: Malformed run text: unbalanced or empty reference" for p_ in ph_paths], "content", bind_placeholders=False)
    add("v08", "confidence High", "views[0].confidence = 'High'", mut(set_(("views", 0, "confidence"), "High")), [f"views[0].confidence: {HIGH}"], "content")
    add("v09", "overall confidence High", "overall.confidence = 'High'", mut(set_(("overall", "confidence"), "High")), [f"overall.confidence: {HIGH}"], "content")
    add("v10", "empty prose", "views[1].rationale = ''", mut(set_(("views", 1, "rationale"), "")), ["views[1].rationale: empty text"], "content")
    add("v11", "peer ranking", "overall.rationale adds 'versus peers'", mut(set_(("overall", "rationale"), "The issuer looks weak versus peers.")),
        ['overall.rationale: prohibited conclusion (peer ranking): "versus peers"'], "content")
    add("v12", "instrument recommendation", "overall.rationale adds 'we recommend'", mut(set_(("overall", "rationale"), "The risk is high, so we recommend caution.")),
        ['overall.rationale: prohibited conclusion (instrument recommendation): "we recommend"'], "content")
    add("v13", "recovery conclusion", "overall.rationale adds 'expected recovery'", mut(set_(("overall", "rationale"), "A downgrade would leave expected recovery unclear.")),
        ['overall.rationale: prohibited conclusion (recovery conclusion): "expected recovery"'], "content")
    add("v14", "rating call", "views[0].rationale adds 'will be downgraded'", mut(set_(("views", 0, "rationale"), "The issuer will be downgraded in the downside case.")),
        ['views[0].rationale: prohibited conclusion (rating call): "will be downgraded"'], "content")
    add("v15", "probability weighting", "overall.rationale adds 'probability-weighted'", mut(set_(("overall", "rationale"), "The cases are probability-weighted.")),
        ['overall.rationale: prohibited conclusion (probability weighting): "probability-weighted"'], "content")
    add("v16", "quote not in the located page", "views[0].evidence[0].quote altered", mut(lambda d: d["views"][0]["evidence"][0].update(quote="Alder Ratings  Downgrade  Total debt to EBITDA  Above  9.99x")),
        ["views[0].evidence[0]: Quote/locator mismatch: quote not found under ratings page:3 ("], "content", issue_prefix="views[0].evidence[0]: Quote/locator mismatch: quote not found under ratings page:3 (")
    for rid, upstream_id, seed in (("v17", "CP-2G", "cp2h-owner v17: a different CP-2G head"), ("v18", "CP-1", "cp2h-owner v18: a different CP-1 head")):
        current = hashlib.sha256(seed.encode()).hexdigest()
        out.append({"id": rid, "class": "stale or unbound inputs", "issue_kind": "content", "composer_only": True,
                    "mutation": f"the positive payload, validated against a literal Upstream whose current {upstream_id} Input differs from the attempt's bound {upstream_id} Input; validator only, no run",
                    "expected_issues": [f"Stale input {upstream_id}: bound restricted <12 hex of the attempt's bound {upstream_id} input sha256>, current restricted {current[:12]}"],
                    "payload": deepcopy(pos),
                    "upstream_literal": {"bound": "the attempt's inputs, bound at run time (prepared-pack, CP-0, CP-1 and CP-2G Input records)",
                                         "current": [{"input_id": upstream_id, "sha256": current, "status": "restricted"}],
                                         "note": f"every other Input of the bound tuple stays unchanged, so only {upstream_id} is reported"},
                    "run_level": {"outcome": "stale_binding", "clone": f"a clone of the positive store taken after the CP-2H begin whose bound snapshot then changes (a new {upstream_id} head is the case under test)",
                                  "raises": "WorkflowError('stale_binding') at the next G1 call (the snapshot content hash differs from the bound one)",
                                  "consumes_attempt": False, "journals_step": False,
                                  "direct_caller": "Execution.submit_step raises ValueError('Ticket inputs have changed')"},
                    "issue_prefix": f"Stale input {upstream_id}: bound restricted "})
    # source-structure refusals: a malformed agency source makes the attempt invalid, returned alone (the CP-1D bridge_table_not_found pattern)
    for rid, key, issue in (("s01", "register_not_found", "Rating register not found"), ("s02", "terms_not_found", "Trigger terms not found")):
        out.append({"id": rid, "class": "agency source not parseable", "issue_kind": "source", "composer_only": True,
                    "mutation": f"the positive payload against the pack source {key} (derived from the positive source by dropping one header line); no run",
                    "expected_issues": [issue], "payload": deepcopy(pos), "source_fixture": key})
    return out


CITE_IDENTITY = {"source_id": "identity", "source_sha256": SRC["identity"]["sha256"], "locator": "page:1", "quote": "Northbridge Synthetic Group is the issuer and consolidated group."}
CITE_FINANCIAL = {"source_id": "financial", "source_sha256": SRC["financial"]["sha256"], "locator": "page:1", "quote": "Currency: USD; amounts in millions."}
LIMIT = "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."
RAT_LIMIT = "Synthetic agency summary naming fictional agencies; not evidence about a real issuer."
RAT_LIMIT_GAP = "Synthetic agency summary naming fictional agencies; one threshold is not stated and one rating is withdrawn."
RAT_Q = "Ratings and outlooks are shown as published on the dates given. Page:2 maps each agency's scale to one combined scale."


def cp0_row(variant):
    c = cite(variant, 1, RAT_Q)
    return {"module_id": "CP-2H", "readiness": "READY_WITH_LIMITATIONS",
            "evidence_demand": "Settled CP-1 reported ratios and the CP-2G credit-metric path, with the agencies' published ratings, scale mapping and trigger terms",
            "source_ids": ["identity", "financial", RATINGS_ID],
            "rationale": "The trigger headroom test can run on settled upstream outputs and the located agency summary with explicit limitations; trigger terms and ratings are the agencies' own.",
            "citations": [CITE_IDENTITY, CITE_FINANCIAL, c], "missing_source": None, "limitations": [LIMIT, RAT_LIMIT_GAP if variant == "gap" else RAT_LIMIT]}


def readiness(variant):
    rr = deepcopy(SNAP["positive"]["readiness_review"])
    rr["objective"] = "Historical financial foundation and rating trigger headroom"
    c = cite(variant, 1, RAT_Q)
    lim = RAT_LIMIT_GAP if variant == "gap" else RAT_LIMIT
    rr["sources"] = [s for s in rr["sources"] if s["source_id"] != "business"] + [{
        "source_id": RATINGS_ID, "document_family": "Agency rating summary", "authority": "third_party", "entity": "Northbridge Synthetic Group", "period": "January 2026",
        "version_relationship": "Summary of fictional agencies' published ratings and trigger terms", "fidelity": "verified", "citations": [c], "limitations": [lim]}]
    cp1 = next(x for x in rr["consumers"] if x["module_id"] == "CP-1")
    rr["consumers"] = [cp1, G_SUB["cp0_consumer_row_cp2a"], G_SUB["cp0_consumer_row_cp2g"], cp0_row(variant)]
    rr["analysis"] = [{"claim_id": "source-assessment", "text": "Located statements and the agency summary support historical and rating-trigger analysis with limitations.",
                       "citations": [CITE_IDENTITY, CITE_FINANCIAL, c], "limitation": LIMIT}]
    return rr


def source_context(variant):
    sc = deepcopy(SNAP["positive"]["cp1_source_context"])
    sc["sources"] = [s for s in sc["sources"] if s["source_id"] != "business"]
    sc["sources"].append({"source_id": RATINGS_ID, "classification": "nonfinancial", "document_type": "Agency rating summary", "published_on": "2026-01-10", "evidence_class": "rating",
                          "evidence_rationale": "Summary of agency ratings and trigger terms; the agencies are fictional", "analytical_use": "Rating trigger terms for CP-2H",
                          "citations": [cite(variant, 1, RAT_Q)], "event_scan": "unassessed", "event_scan_explanation": "A ratings summary is not event evidence"})
    return sc


CP1_READINESS_CP2H = {
    "entry": "CP-2H",
    "requirements": [{
        "requirement": "consumer_specific_cp1_sufficiency", "status": "limited",
        "evidence_ids": ["{{EVID:kpi ebitda, LTM Q4 25 basis}}", "{{EVID:kpi fcf, LTM Q4 25 basis}}", "{{EVID:kpi total_debt, LTM Q4 25 basis}}", "{{EVID:kpi cash_closing, LTM Q4 25 basis}}"],
        "rationale": "Settled twelve-month EBITDA, free cash flow, debt and cash give the reported ratios the triggers are tested against; the statements are unaudited.",
        "actions": ["Retain the unaudited-statement limitation in the trigger test."]}],
    "gaps": [{"gap_ids": ["{{ALL narrative gap ids}}"], "relevance": "relevant", "evidence_ids": [],
              "rationale": "Every retained source and context warning bears on the reliability of the ratios the triggers are tested against."}],
}


def readiness_literal():
    consumers = deepcopy(G_SUB["cases"]["gap"]["cp1_readiness"]["consumers"]) + [deepcopy(CP1_READINESS_CP2H)]
    assert [c["entry"] for c in consumers] == ["CP-2A", "CP-2G", "CP-2H"]
    return {"inputs_sha256": "{{INPUTS_SHA256}}", "consumers": consumers,
            "note": ("The CP-2A and CP-2G consumer entries are the frozen literals of cases/cp2g-owner/submissions.json cases.gap.cp1_readiness, unchanged; CP-2H is new with the CP-2A marker style "
                     "({{EVID:kpi <key>, LTM Q4 25 basis}} and {{ALL narrative gap ids}}, bound by cases/cp2a-owner/manifest.json run_time_bindings.cp1_readiness). The kpi keys ebitda, fcf, total_debt and cash_closing "
                     "are the ones the frozen CP-2G entry already uses. {{INPUTS_SHA256}} is the content hash of the step's prefilled DownstreamInputs.")}


def main():
    built = {name: build_case(name) for name in CASES}
    refusal_list = refusals()
    by_rid = {r["id"]: r for r in refusal_list}
    base_run = dict(FIN["run"])
    runs = {k: dict(base_run, run_id=f"cp2h-owner-{k.replace('_', '-')}", pathway="distressed_restructuring", requested_modules=["CP-2H"])
            for k in ("positive", "gap", "refused", "blocked", "cp2g_blocked")}
    g_expected = G_EXP["cases"]["gap"]
    # consistency with the frozen CP-2G oracle: the facts read are the head's own
    pos = built["positive"]
    for r_ in pos["cp2g_references"]["rows"]:
        x = next(f for f in g_expected["facts"] if f["fact_id"] == r_["fact_id"])
        assert (x["shown"], x["amount_exact"], x["status"]) == (r_["shown"], r_["amount_exact"], r_["status"])
    # the consistency list of manifest.json synthetic_source is asserted against the frozen pages, not only stated
    def fin_row(page, label):
        hits = [fields_of(ln) for ln in SRC["financial"]["pages"][page - 1]["text"].split("\n") if ln.startswith(label + "  ")]
        assert len(hits) == 1 and hits[0][0] == label, (page, label)
        return hits[0]

    assert "Fiscal year end: December 31." in SRC["identity"]["pages"][0]["text"].split("\n")
    assert fin_row(2, "Period")[-1] == "FY 2025" and fin_row(3, "Period")[-1] == "FY 2025" and fin_row(4, "Period end")[-1] == "FY 2025-12-31"
    ebitda, cash_int, fcf = D(fin_row(2, "Reported EBITDA")[-1]), D(fin_row(3, "Cash interest paid")[-1]), D(fin_row(3, "Levered free cash flow")[-1])
    debt, cash = D(fin_row(4, "Total debt")[-1]), D(fin_row(4, "Cash and cash equivalents")[-1])
    assert (ebitda, cash_int, fcf, debt, cash) == (D("30.0"), D("5.00"), D("9.00"), D("50.00"), D("20.00"))
    fy25 = {"total_leverage": Fraction(debt) / Fraction(ebitda), "net_leverage": (Fraction(debt) - Fraction(cash)) / Fraction(ebitda),
            "interest_coverage": Fraction(ebitda) / Fraction(cash_int), "fcf_to_debt": Fraction(fcf) / Fraction(debt)}
    assert fy25 == {"total_leverage": Fraction(5, 3), "net_leverage": Fraction(1), "interest_coverage": Fraction(6), "fcf_to_debt": Fraction(9, 50)}
    for (r_, field_), x in cp2g_head("gap")["ratio"].items():
        if r_ == "a25":
            assert D(x["amount_exact"]) == q38(fy25[field_]), (field_, x["amount_exact"])  # the recomputed ratios (38-digit half-even) equal the CP-2G gap a25 facts
    for variant_, parsed_ in PARSED.items():  # a threshold sits exactly on a FY2025 metric only in the boundary source
        on_metric = [t["line"] for t in parsed_["triggers"]
                     if t["threshold"] is not None and Fraction(t["threshold"]) == fy25[METRIC_MAP[t["metric"]][0]]]
        assert bool(on_metric) == (variant_ == "boundary"), (variant_, on_metric)
    # the tamper target is a known text of the positive case
    tf = next(f for f in pos["facts"] if f["fact_id"] == TAMPER_TARGET)
    assert tf["text"] == TAMPER_FROM and TAMPER_TO != TAMPER_FROM and TAMPER_TO.startswith("Not reached by ")
    # prose: no digit outside a reference or a CP-nn[A] label; names carry no digit
    for case in ("positive", "gap", "fixture", "fixture_boundary"):
        sub = SUBMISSION[case]
        for t_ in prose_texts(sub):
            stripped = re.sub(r"CP-[0-9]{1,2}[A-Z]?", "", re.sub(r"\{\{FIG:[a-z_]+\|[^}]*\}\}|\{[A-Za-z0-9_.:-]+\|[^}]*\}", "", t_))
            assert not re.search(r"[0-9]", stripped), t_
        for v in sub["views"]:
            assert not re.search(r"[0-9{}\[\]]", re.sub(r"CP-[0-9]{1,2}[A-Z]?", "", v["limitation"])) and v["agency"] in ("Alder Ratings", "Brook Credit")
        assert not re.search(r"[0-9{}\[\]]", re.sub(r"CP-[0-9]{1,2}[A-Z]?", "", sub["overall"]["limitation"]))
    # the prose guards: no submission trips the phrase guards
    for case in ("positive", "gap", "fixture", "fixture_boundary"):
        low = " ".join(phrase_texts(SUBMISSION[case])).lower()
        for _kind, phrases in (RATING_CALL, PROBABILITY):
            assert not any(p in low for p in phrases)
    # no stored text fact and no limitation spells a CP-1 or upstream figure
    for name, b in built.items():
        spelled = {v["spelled"] for v in b["figures"].values() if v.get("spelled")}
        for x in b["facts"]:
            for key in ("text", "limitation"):
                assert not any(sp in str(x.get(key) or "") for sp in spelled), (name, x["fact_id"], key)
    # derived headline values (positive): the lease quotes these
    r = pos["results"]
    assert r["t01"]["fy25_headroom"] and pos["totals"]["downgrade_down"] == ["t02", "t03", "t04"] and pos["totals"]["upgrade_base"] == ["t05"]
    # the literal positive views state these results; the oracle must agree with its own prose
    assert r["t02"]["down"]["first"] == "FY2026" and r["t03"]["down"]["first"] == "FY2026" and r["t01"]["down"]["first"].startswith("Not reached")
    assert r["t04"]["base"]["first"].startswith("Not reached") and r["t04"]["down"]["first"] == "FY2027"
    assert r["t05"]["base"]["first"] == "FY2028" and r["t05"]["down"]["first"].startswith("Not reached")
    assert D(r["t01"]["base"]["headroom"][0]) > D(r["t01"]["fy25_headroom"])  # the base case widens the total debt to EBITDA headroom
    assert r["t01"]["fy25_reached"] is False and all(r[t]["fy25_reached"] is False for t in r)  # "inside every published downgrade trigger"

    manifest = {
        "schema_version": "cp2h-owner-cases/1",
        "scope": "CP-2H Ratings migration trigger: CP-0, CP-1, CP-2A, CP-2G (frozen CP-2G gap literals) and CP-2H over the frozen financial pack plus one synthetic agency rating source",
        "status": "DRAFT revision 2 (fix round 1 of review-precise-1, re-pinned to methodology 1bb6c0bc and CP-2G manifest 05ac9f84) by the cp2h-owner preparation task, 2026-10-28; re-review pending; not executed",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "pins": PINS,
        "financial_baseline": {"path": "cases/financial/manifest.json", "manifest_sha256": PINS["cases/financial/manifest.json"],
                               "sources": [{"source_id": s, "sha256": SRC[s]["sha256"], "reuse": "Every page text and locator stays byte-identical; read by reference, never edited"} for s in ("identity", "financial")]},
        "frozen_finding": "No frozen source carries a rating, a rating scale, an outlook or a trigger term (grep of cases/*/manifest.json for rating, agency, Moody, Fitch: only unrelated words match; the DEPLOY VII design DR.6 'n/a frame' reads 'Rating trigger thresholds are not stated: no agency report in the Source Pack'). The ratings, scale and thresholds therefore come from one SYNTHETIC source, labelled so.",
        "synthetic_source": {
            "source_id": RATINGS_ID, "name": "Credit rating summary (fictional agencies)", "status": "ready", "media_type": "text/plain", "extractor": "supplied-representation", "extraction_status": "complete",
            "pack_limitation_positive": RAT_LIMIT, "pack_limitation_gap": RAT_LIMIT_GAP,
            "positive": {"pages": [{"locator": f"page:{n}", "text": t} for n, t in enumerate(SOURCES["positive"], 1)], "sha256": SRC_SHA["positive"]},
            "gap": {"pages": [{"locator": f"page:{n}", "text": t} for n, t in enumerate(SOURCES["gap"], 1)], "sha256": SRC_SHA["gap"],
                    "derivation": "page:1 lists Brook Credit as Withdrawn (outlook Not applicable) with a withdrawal note; page:2 is the positive page:2; page:3 drops the Brook Credit rows and states the Alder free cash flow threshold as Not stated"},
            "fixtures": {
                "boundary": {"pages": [{"locator": f"page:{n}", "text": t} for n, t in enumerate(SOURCES["boundary"], 1)], "sha256": SRC_SHA["boundary"],
                             "derivation": "the positive source with the Brook Credit net debt to EBITDA downgrade threshold 1.00x, exactly the FY2025 net leverage; used by the composer-only case fixture_boundary"},
                "register_not_found": {"pages": [{"locator": f"page:{n}", "text": t} for n, t in enumerate(SOURCES["register_not_found"], 1)], "sha256": SRC_SHA["register_not_found"],
                                       "derivation": "the positive source without the register header line; used only by refusal s01 (no run)"},
                "terms_not_found": {"pages": [{"locator": f"page:{n}", "text": t} for n, t in enumerate(SOURCES["terms_not_found"], 1)], "sha256": SRC_SHA["terms_not_found"],
                                    "derivation": "the positive source without the trigger-terms header line; used only by refusal s02 (no run)"}},
            "why": "No frozen source states a rating, a scale or a threshold. All of them are required to test headroom and divergence, and none may be invented by the analyst or the core.",
            "consistency_with_frozen_figures": [
                "No financial figure is restated: the source names ratios and thresholds only, so it cannot contradict a frozen amount",
                "Metric definitions use the frozen statement row labels: reported EBITDA, total debt, cash interest paid, cash and cash equivalents, levered free cash flow (frozen page:2-4)",
                "FY2025 is the twelve months to December 31, 2025, the base period of CP-1 and CP-2G; terms are tested at fiscal year end as the identity source's 31 December year end implies",
                "Every threshold is far enough from, or deliberately exactly at (boundary fixture only), a figure derived from the frozen pages: FY2025 total leverage 1.67x (50/30), net 1.00x (30/30), coverage 6.00x (30/5), free cash flow to debt 18.0% (9/50)",
                "The issuer is described only by the frozen name; the agencies are fictional (the source says so)",
                "The issuer ratings in this source coexist with CP-3D's unrated instrument: CP-3D's \"No rating agency has assigned a rating to the instrument\" concerns the quoted bond, while these are issuer ratings of the group; neither statement contradicts the other",
                "Asserted by the builder: page:2 Reported EBITDA FY 30.0; page:3 Cash interest paid FY 5.00 and Levered free cash flow FY 9.00; page:4 Total debt FY 50.00 and Cash and cash equivalents FY 20.00; identity page:1 'Fiscal year end: December 31.'; the recomputed FY2025 ratios (50/30, (50-20)/30, 30/5, 9/50) equal the CP-2G gap T2H.6.a25 facts; no threshold of a non-boundary source equals a FY2025 metric"],
            "parse_rule": "page:1 register after the header 'Agency  Instrument  Rating  Outlook  Date' (consecutive five-field lines), page:2 scale after 'Position  Alder Ratings  Brook Credit', page:3 terms after 'Agency  Direction  Metric  Comparison  Threshold'; fields split on two or more spaces; threshold 'N.NNx' (multiple), 'N.N%' (percent, stored as a fraction) or 'Not stated'; a line of two or more fields with another field count makes the source invalid; after a block ends at a line of zero or one field, a later line of two or more fields on that page makes the source invalid; a missing header is an invalid attempt returned alone (s01, s02); a rating of Withdrawn or Not rated has no position (not_applicable), any other rating must be on the scale or the source is invalid ('Rating not on the scale: <agency> <rating>')"},
        "edges": {
            "decision": "D4: methodology.json as is. CP-2H required CP-0, CP-1, CP-2G (rule block); optional CP-1D (rule restricted); no edge_rules entry. CP-2A is not an edge of CP-2H: it is in the plan only because CP-2G requires it.",
            "required": MOD["CP-2H"]["required"], "optional": MOD["CP-2H"]["optional"],
            "plans": {"CP-2H": ["CP-0", "CP-1", "CP-2A", "CP-2G", "CP-2H"], "CP-2H+CP-1D": ["CP-0", "CP-1", "CP-1D", "CP-2A", "CP-2G", "CP-2H"]},
            "input_order": "execution.current_inputs binds prepared-pack then CP-2H's own required and optional heads in plan order: [prepared-pack, CP-0, CP-1, CP-2G] (CP-1D is unbound in every case)",
            "probe": "registry.plan(('CP-2H',)) and registry.plan(('CP-2H','CP-1D')) as listed; registry.step_chain('CP-2H') raises 'CP-2H has no live step contract' (2026-10-28)"},
        "cases": {
            "positive": {"run": runs["positive"], "pack": "identity + financial + ratings (positive)", "submission": "submissions.json cases.positive", "expected": "expected.json cases.positive",
                         "execution": "closed run: CP-0, CP-1 (five stages, source_context literal with the ratings source), CP-2A (frozen CP-2A positive literal), CP-2G (frozen CP-2G gap literal: CP-1D unbound, minimum liquidity not assessed), CP-2H"},
            "gap": {"run": runs["gap"], "pack": "identity + financial + ratings (gap)", "submission": "submissions.json cases.gap", "expected": "expected.json cases.gap",
                    "execution": "closed run as positive with the limited agency source: one threshold Not stated (missing), one agency withdrawn (position, notches, lower rated and outlooks not_applicable)"},
            "refused": {"run": runs["refused"], "pack": "financial source missing (cases/financial/manifest.json negative_case)", "submission": "submissions.json refused", "expected": "expected.json cases.refused",
                        "execution": "CP-0 only; CP-1 begin raises NotAuthorized; CP-2A, CP-2G and CP-2H are never begun"},
            "blocked": {"run": runs["blocked"], "pack": "same pack as positive", "submission": "submissions.json refusals r01 (attempt 0) then v08 (attempt 1)", "expected": "expected.json cases.blocked",
                        "execution": "a clone of the positive store taken after CP-2G settles and before CP-2H begins (the refusal payloads r01 and v08 mutate the positive submission, so their issues are those on the positive facts and pages); CP-2H attempt 0 invalid (rejected) and attempt 1 invalid (blocked)"},
            "cp2g_blocked": {"run": runs["cp2g_blocked"], "pack": "same pack as gap", "submission": "cases/cp2g-owner/submissions.json refusals r01 then v13 for CP-2G", "expected": "expected.json cases.cp2g_blocked",
                             "execution": "closed run to CP-2A, then CP-2G settles blocked; CP-2H begin raises ValueError('Required upstream is unrun, stale or blocked') (edge rule block)"},
            "fixture_total_loss": {"run": None, "execution": "composer only: positive source and the frozen CP-2G fixture_total_loss facts (downside EBITDA zero: leverage missing, coverage a known 0.00x)"},
            "fixture_boundary": {"run": None, "execution": "composer only: the boundary source (a threshold exactly equal to the FY2025 metric): a known zero headroom, not reached"}},
        "cp1_fact_selection_rule": {"table_id": "T4.10", "period": LTM_PERIOD,
                                    "predicate": "fact.table_id == 'T4.10' and fact.label == 'LTM Q4 25 (2025-01-01 to 2025-12-31) · <metric>'; exactly one match per metric, zero or several fail",
                                    "metrics": ["total_leverage_reported", "net_leverage_reported", "interest_coverage_reported", "fcf_to_debt"],
                                    "observed_value_class": {m: G_EXP["cases"]["gap"]["cp1_inputs"][m]["value_class"] for m in ("total_leverage_reported", "net_leverage_reported", "interest_coverage_reported", "fcf_to_debt")},
                                    "fact_ids": "interface-fact:<sha256>; bound at run time, never literal",
                                    "note": "the settled values are those of cases/cp2g-owner/manifest.json fact_selection_rule probe (S1 positive promoted CP-1 head); the bridge-less pack of these cases is unprobed"},
        "upstream_fact_selection": {"CP-2G": {"head": "the settled CP-2G head of the run (module id CP-2G, status restricted in the frozen gap run)",
                                              "reader": "CP-2H has no reader of its own: it calls the frozen owners.cp2g.cp2g_reader(store, head) (docs/CP2G-OWNER-LEASE.md:67, wider payload) and selects the T2H.6 facts below from its result",
                                              "facts": "T2H.6.<row>.{total_leverage,net_leverage,interest_coverage,fcf_to_debt} for rows a25, b26-b28, d26-d28 (28 facts), selected by literal fact id from the cp2g_reader result",
                                              "fact_ids": "literal (table.row.field assigned by CP-2G); the frozen values are cases/cp2g-owner/expected.json cases.gap and cases.fixture_total_loss (pinned)"}},
        "run_time_bindings": {
            "figure_placeholders": "{{FIG:name|token}} -> {<fact_id>|<token>} for CP-1 names (fact_selection_rule); module-fact references {T2R.x.y.z|token} are literal; unreplaced a FIG placeholder is malformed run text (refusal v07)",
            "cp0_consumer_rows": "positive and gap: CP-1 (the snapshot row), CP-2A and CP-2G (cases/cp2g-owner/submissions.json cp0_consumer_row_cp2a, cp0_consumer_row_cp2g) and CP-2H (submissions.json cases.<case>.readiness_review.consumers[3]); T8 commands Run CP-1, Run CP-2A, Run CP-2G, Run CP-2H",
            "cp1_readiness": "submissions.json cases.<case>.cp1_readiness (consumer entries CP-2A, CP-2G, CP-2H); markers bound by the frozen run_time_bindings of the CP-2A manifest",
            "pack_hash": "PreparedPack.content_hash() of the run's pack", "inherited_limitations": "execution.inherited_limitations rule (see expected.execution)", "ticket_and_call_ids": "structural only"},
        "figures": FIGS,
        "tool_use": {
            "CP-2H": "owner-only step rating_triggers with inputs module_context and a SourceSession over the fixed host mapping (identity, financial, ratings): one ok read_inputs, then ok read_pages covering every cited page; submissions.json cases.<case>.tool_calls is the literal sequence",
            "view_tree_draft": {"note": "a proposal, not an observation: the implementer commits cases/cp2h-owner/cp2h-view-tree.json from a product-settled head; no quote, citations or record_json key at any depth",
                                "keys": {"upstream": "[{module_id, status}] for CP-0, CP-1 and CP-2G (CP-1D state unbound)",
                                         "register": "{state: present|absent, source_id, pages: [locator], agencies: [{row, agency, rating, outlook, date, position: int|null}]}",
                                         "triggers": "[{row, agency, direction, metric, comparison, threshold: {ref|null, shown|null, status}}] (terms, not citations)",
                                         "cp2g": "{status, rows: [{row, metrics: {total_leverage, net_leverage, interest_coverage, fcf_to_debt: {ref, shown, status, limitation|null}}}]}",
                                         "cp1_facts": "[{ref, label, period, unit, shown}] referencable CP-1 reported ratios",
                                         "inherited_limitations": "[str]"}}},
    }
    refused_cp1_row = {"module_id": "CP-1", "readiness": "CONDITIONAL", "evidence_demand": "Located historical statements, facility terms, definitions and scope", "source_ids": ["identity"],
                       "rationale": "Quarterly financial statements were not supplied.", "citations": [CITE_IDENTITY], "missing_source": "Quarterly financial statements",
                       "limitations": ["Quarterly financial statements were not supplied."]}

    def refused_row(mid, demand):
        return {"module_id": mid, "readiness": "CONDITIONAL", "evidence_demand": demand, "source_ids": ["identity"], "rationale": "Quarterly financial statements were not supplied.",
                "citations": [CITE_IDENTITY], "missing_source": "Quarterly financial statements", "limitations": ["Quarterly financial statements were not supplied."]}

    tool_calls = {
        "positive": [{"tool": "read_inputs", "arguments": None},
                     {"tool": "read_pages", "arguments": {"source_id": RATINGS_ID, "first_page": 1, "last_page": 1}, "expect_spans": [{"source_id": RATINGS_ID, "locator": "page:1"}]},
                     {"tool": "read_pages", "arguments": {"source_id": RATINGS_ID, "first_page": 3, "last_page": 3}, "expect_spans": [{"source_id": RATINGS_ID, "locator": "page:3"}]}],
        "gap": [{"tool": "read_inputs", "arguments": None},
                {"tool": "read_pages", "arguments": {"source_id": RATINGS_ID, "first_page": 1, "last_page": 1}, "expect_spans": [{"source_id": RATINGS_ID, "locator": "page:1"}]},
                {"tool": "read_pages", "arguments": {"source_id": RATINGS_ID, "first_page": 3, "last_page": 3}, "expect_spans": [{"source_id": RATINGS_ID, "locator": "page:3"}]}]}
    for case in ("positive", "gap"):  # every cited page is read (Cited page not read through read_pages otherwise)
        cited = {c["locator"] for v in SUBMISSION[case]["views"] for c in v["evidence"]}
        read = {s["locator"] for call in tool_calls[case] for s in call.get("expect_spans", [])}
        assert cited <= read, (case, cited, read)
    submissions = {
        "schema_version": "cp2h-owner-submissions/1",
        "note": ("Literal analyst submissions for the rating_triggers step. {{FIG:name|token}} marks a CP-1 figure reference replaced mechanically by {<fact_id>|<token>} after the CP-1 head is inspected "
                 "(manifest.json run_time_bindings); unreplaced it is malformed run text and fails closed (refusal v07). {T2R.x.y.z|token} references name this module's own facts and are literal. "
                 "Ratings, scales and trigger thresholds are never analyst input: Python parses them from the agency source. The analyst gives, per agency, a migration view (enumerated judgment), "
                 "a confidence, a rationale of references only and located citations that must have been read with read_pages. The upstream step literals (CP-2A downside_pathway, CP-2G forward_credit_model gap run, the "
                 "CP-0 rows and the CP-1 readiness consumers) are copies of the frozen oracles' own."),
        "figures": FIGS,
        "agency_source": {"positive": {"sha256": SRC_SHA["positive"], "pages": SOURCES["positive"]}, "gap": {"sha256": SRC_SHA["gap"], "pages": SOURCES["gap"]}},
        "upstream_step_literals": {
            "CP-2A": G_SUB["upstream_step_literals"]["CP-2A"],
            "CP-2G": {"source": {"file": "cases/cp2g-owner/submissions.json", "sha256": PINS["cases/cp2g-owner/submissions.json"], "path": "cases.gap"},
                      "forward_credit_model": G_SUB["cases"]["gap"]["forward_credit_model"], "tool_calls": G_SUB["cases"]["gap"]["tool_calls"],
                      "blocked": {"attempt_0": next(r for r in G_SUB["refusals"] if r["id"] == "r01"), "attempt_1": next(r for r in G_SUB["refusals"] if r["id"] == "v13")}}},
        "cases": {c: {"readiness_review": readiness(c), "cp1_source_context": source_context(c), "cp1_readiness": readiness_literal(), "rating_triggers": SUBMISSION[c], "tool_calls": tool_calls[c]}
                  for c in ("positive", "gap")},
        "fixtures": {k: {"rating_triggers": SUBMISSION[s_], "agency_source": k_} for k, s_, k_ in (("fixture_total_loss", "fixture", "positive"), ("fixture_boundary", "fixture_boundary", "boundary"))},
        "refused": {"cp0_consumer_row_cp1": refused_cp1_row, "cp0_consumer_row_cp2a": refused_row("CP-2A", "Settled CP-1 figures"),
                    "cp0_consumer_row_cp2g": refused_row("CP-2G", "Settled CP-1 and CP-2A outputs"), "cp0_consumer_row_cp2h": refused_row("CP-2H", "Settled CP-1 and CP-2G outputs"),
                    "gap_row": {"gap_id": "missing-financial", "kind": "source", "severity": "material", "description": "Quarterly financial statements were not supplied.",
                                "affected_modules": ["CP-1", "CP-2A", "CP-2G", "CP-2H"], "remediation": "Supply quarterly financial statements"}},
        "refusals": [{k: v for k, v in r.items() if k in ("id", "class", "mutation", "payload", "payload_text", "composer_only", "bind_placeholders", "upstream_literal", "run_level", "source_fixture")} for r in refusal_list],
        "tool_refusals": [
            {"id": "t01", "class": "cited_page_not_read", "base_case": "positive", "payload": "cases.positive.rating_triggers (valid)",
             "calls_before_submit": [{"tool": "read_inputs", "arguments": None}], "disposition": "invalid attempt 0 (journaled rule unread_citation_issues against Seen); re-begun as attempt 1 with repair_of set",
             "expected_issues": ["Cited page not read through read_pages: ratings page:1", "Cited page not read through read_pages: ratings page:3"]},
            {"id": "t02", "class": "non-pack invoke", "base_case": "positive", "call": {"tool": "web_search", "arguments": {"query": "Northbridge Synthetic Group rating"}},
             "expected_receipt": {"status": "refused", "reason": "not_permitted"}, "journal": "refused receipt recorded; no step journaled; no attempt consumed"},
            {"id": "t03", "class": "submit before read_inputs", "base_case": "positive", "calls_before_submit": [], "expected_error": "not_permitted",
             "journal": "a raised WorkflowError(\"not_permitted\"); nothing written; no attempt consumed"}],
        "blocked": {"attempt_0": "refusals r01", "attempt_1": "refusals v08"},
    }
    r01, v08 = by_rid["r01"], by_rid["v08"]
    expected = {
        "schema_version": "cp2h-owner-expected/1",
        "derivation": ("Hand-transcribed recipes of work/lead/cp2h-owner-preparation/lease-draft.md applied to the parsed synthetic agency source, the pinned CP-2G oracle facts and the literal analyst views by "
                       "cases/cp2h-owner/builder/build.py (stdlib only; deploy_vii never imported or run). A headroom is one subtraction in decimal.Context(prec=38, ROUND_HALF_EVEN) equal to the correctly rounded "
                       "rational (asserted); a percentage-point amount is (a - b).scaleb(2) in that context, with shown the exact text plus ' pp' (there is no pp display class: a pending product task); "
                       "multiples show 2 dp 'x', percents 1 dp '%', negatives in parentheses (display.py ROUND_HALF_UP); counts and notch differences show as exact text plus their unit."),
        "cell_notation": {"shown": "exact displayed text; an unsettled cell is spelled as report_view.fact_spelling spells it: missing -> state gap, text '∅ G#'; not_applicable -> state not_meaningful, text '∅ G# n.m.' (G# is the report-wide gap number, not literal)",
                          "amount_exact": "canonical exact decimal; null means unsettled", "status": "known | missing | not_applicable", "fact_id": "table.row.field, assigned by Python",
                          "derives_from": "cp1:<metric> = a CP-1 T4.10 fact (cp1_references); cp2g:<id> = a settled CP-2G fact (cp2g_references); any other id = a fact of this module; empty for source terms and analyst judgments",
                          "citations": "source facts carry the agency-source quote they state; calculated facts carry the ordered, de-duplicated concatenation of their own derives_from facts' citations (the cp4_legal._computed pattern); the citations of cp1:/cp2g: facts are appended at run time and not enumerated here",
                          "unit_twin": "an unsettled fact carries the unit its settled twin carries: MULTIPLE, PERCENT, pp, notches, scale position or triggers"},
        "id_rules": {"fact_id": "<table_id>.<row_id>.<field>", "calculation_id": "calc:<fact_id> on calculated facts",
                     "rows": "T2R.1 u_cp1, u_cp2g, u_cp1d; T2R.2 r01.. the agencies in register order; T2R.3 t01.. the trigger terms in source order; T2R.4 and T2R.6 one row per trigger (t01..); T2R.5 <trigger>_base and <trigger>_down; T2R.7 a01.. the views in register order; T2R.8 p01.. the agency pairs; T2R.9 total; T2R.10 g01..",
                     "claims": "T2R.7.a01.., T2R.7.overall, T2R.4.<trigger> (one per trigger), T2R.6.base, T2R.6.down, T2R.8.<pair>, in this order"},
        "method_rules": {
            "headroom": "threshold - metric for 'Above', metric - threshold for 'Below'; a positive headroom is room left (downgrade) or distance still to travel (upgrade); zero is a known zero; a percent metric gives percentage points via .scaleb(2)",
            "reached": "strict: metric > threshold for 'Above', metric < threshold for 'Below'; equal means not reached",
            "first_year": "the first of FY2026-FY2028 in which the trigger is reached; a year not calculable before it makes the answer Not calculable, stored as a missing fact with the root reason (threshold first, then the CP-2G limitation); none reached and all calculable is 'Not reached by FY2028'",
            "tightest": "the lowest of the three yearly headrooms, missing (with the first missing year's reason) if any year is missing",
            "notches": "absolute difference of the two source positions; lower rated is the agency with the larger position number; Withdrawn or Not rated gives not_applicable",
            "counts": "T2R.9 counts triggers by direction whose first year is a year; triggers with a missing first-year result are counted per case in not_calculable_base and not_calculable_down (each T2R.6 claim cites its own case's count), never in the reached counts"},
        "property_tests": {
            "reconciliation": "T2R.4 actual equals CP-2G T2H.6.a25 and CP-1's reported ratio exactly (check 'Reconciled to CP-1')",
            "headroom_sign": "headroom < 0 iff the trigger is reached (strict), headroom = 0 iff the metric equals the threshold",
            "monotone": "for an 'Above' trigger the headroom does not fall as the metric falls, for a 'Below' trigger it does not fall as the metric rises",
            "first_break": "first_result returns the earliest reached year; a year not calculable before it makes the answer Not calculable",
            "pp_scale": "pp headroom = (threshold or metric difference).scaleb(2) in the 38-digit context, never amount * 100"},
        "d8_table_ids": {"collision_found": None, "check": "T2R.1-T2R.10 appear only in the CP-2H entry of the pinned methodology.json and in no other module's table_ids; no definition exists in src/, tests/, docs/ or cases/ other than this oracle and the CP-2G lease's mention of the family (grep 2026-10-28)",
                         "resolution": "no change: CP-2H registers T2R.1-T2R.10 as they are", "cp2h_table_ids": list(TABLES), "module_tables_besides": ["cp1_references", "cp2g_references"],
                         "table_shape": "every table has one fact per column in every row; the totals row is its own registered table (T2R.9); the builder asserts both, and every probe runs contracts.validate_tables on a product Module built from each case"},
        "d7_rendering": {
            "design_reference": "design/reference of DEPLOY VII (read only): FP05 lists 'Rating triggers' (rbot-fp-05-distressed-restructuring.dc.html) and the design system's DR.6 'n/a frame' reads 'Rating trigger thresholds are not stated: no agency report in the Source Pack'; report_view._PRESETS distressed_restructuring already names the block id rating-triggers (report_view.py:570) with no _Spec (it falls back to the Unbound owner)",
            "decision": "one block, id rating-triggers (already in the preset, so no new id), owner CP-2H, kind dense, producers (CP-2H,), route label 'Full analysis', in the distressed_restructuring composition (CP-2A's _DISTRESSED, docs/CP2A-OWNER-LEASE.md:28); tabs Summary T2R.9, Current headroom T2R.4, Forward headroom T2R.5, Trigger timing T2R.6, Migration view T2R.7, Agency divergence T2R.8; evidence rail T2R.1, T2R.2, T2R.3, cp1_references, cp2g_references; limitations rail T2R.10; no chart (the DR.6 n/a frame is the design's chart and stays a later product task)",
            "pathway": "distressed_restructuring only: contracts.PATHWAY_MODULES lists CP-2H in that pathway alone (to be checked by the reviewer)"},
        "d4_edges": {"decision": "methodology.json as is (required CP-0, CP-1, CP-2G, rule block; optional CP-1D, rule restricted); no proposal"},
        "methodology_proposal": {"decision": "none required", "note": "CP-2H needs no methodology.json edit: its table ids are registered and its edges suffice. The builder pins methodology.json, so CP-2H joins the re-pin list of the single serialised methodology change (CP-L10 D4 and TL10.5, CP-1C D8 T1C.1-T1C.8): expected and submissions stay byte-identical, only the manifest pin changes."},
        "phrase_guard": {
            "reused": "business_context.prohibited_issues default kinds (peer ranking, instrument recommendation, recovery conclusion), quoted as 'path: prohibited conclusion (<kind>): \"<phrase>\"'",
            "core_local": {RATING_CALL[0]: list(RATING_CALL[1]), PROBABILITY[0]: list(PROBABILITY[1])},
            "form": "case-insensitive substring match over every prose field (view rationales and limitations, overall, gaps), the matched phrase quoted as prohibited_issues quotes it",
            "cannot_catch": ["a rating call or prediction in an unlisted wording ('is bound to fall a notch', 'a downgrade is coming')", "a numeric probability spelled in words ('one in three', caught only as a bare figure when written in digits)",
                             "a recommendation phrased without the listed words", "a semantic conclusion that contradicts the computed headroom (the guard is over phrases, not a review of meaning)",
                             "'probability of' is deliberately not listed: a qualitative migration view legitimately speaks of the chance of a rating review, so a numeric probability is stopped only by the Bare figure rule"]},
        "execution": {
            "plan_order": {"positive": ["CP-0", "CP-1", "CP-2A", "CP-2G", "CP-2H"], "gap": ["CP-0", "CP-1", "CP-2A", "CP-2G", "CP-2H"]},
            "inputs": {"positive": ["prepared-pack", "CP-0", "CP-1", "CP-2G"], "gap": ["prepared-pack", "CP-0", "CP-1", "CP-2G"]},
            "statuses": {"CP-0": "restricted", "CP-1": "restricted (financial precedent)", "CP-2A": "restricted (frozen CP-2A lease)", "CP-2G": "restricted (frozen CP-2G lease)",
                         "CP-2H": "restricted: own limitations are non-empty and the case is synthetic (execution.py settle)"},
            "tool_use": {"CP-2H": "owner-only step with a source session: exactly one ok read_inputs before the submit, then ok read_pages covering every page cited by a view; every invoke of a non-pack tool is a refused not_permitted receipt"},
            "consumption": ("CP-2H closes D3 for CP-2G: it reads the settled CP-2G T2H.6 credit-metric facts (not only the head status) and its attempt inputs bind the CP-2G head hash, so a new CP-2G head makes CP-2H stale. "
                            "Acceptance asserts in the positive run: (a) the CP-2H attempt's inputs equal [prepared-pack, CP-0, CP-1, CP-2G] hash-for-hash with the final heads; (b) the CP-2G head's result_sha256 equals the bound Input; "
                            "(c) in derives_from the T2R.4 actual facts list cp2g:T2H.6.a25.<field> (5 facts), the T2R.5 yearly headroom facts list cp2g:T2H.6.<row>.<field> (30 facts) and the T2R.6 first-year texts list the cp2g facts of their three rows (10 facts); "
                            "(d) every copied value equals the CP-2G head's own fact (cp2g_references). CP-2H's own consumption stays OPEN: CP-3 and CP-3D (optional), CP-5 (optional) do not read it yet."),
            "inherited_limitations": "execution.inherited_limitations: for each directly bound head in input order, the head's limitations then its inherited limitations, de-duplicated, own findings removed; bound at run time"},
        "cp1_readiness": {"literal": "submissions.json cases.<case>.cp1_readiness", "consumer_rows": {"CP-2H": {"entry": "CP-2H", "canonical_module": "CP-2H", "requirements": ["consumer_specific_cp1_sufficiency"], "policy": "consumer_specific_review", "status": "ready_with_limitations"}},
                          "validator_issues": "none expected; unprobed on the ratings-source pack (see the report)"},
        "refusals": [{k: v for k, v in r.items() if k in ("id", "class", "issue_kind", "expected_issues", "issue_prefix", "run_level", "source_fixture")} for r in refusal_list],
        "refusal_rules": {
            "journal": "each refusal is one invalid CP-2H step on attempt 0 of the positive CP-1/CP-2A/CP-2G heads: attempt consumed, module status rejected, limitations equal the issues (bounded: 20 lines of 600 characters)",
            "shape_vs_content": "shape issues (Pydantic messages in readiness.shape_issues form, dotted paths) are returned alone; content issues follow in the order views (register order), overall, gaps, with bracketed paths; the source issues s01 and s02 are returned alone",
            "composer_only": "v17, v18 (stale inputs) and s01, s02 (unparseable source) are exercised on the validator/composer, not as runs; the stale outcome at run level is WorkflowError('stale_binding') with no attempt consumed and no step journaled",
            "tool_level": "cited_page_not_read, non-pack invoke and submit-before-read are in submissions.json tool_refusals",
            "begin_refusals": "CP-2G blocked/unrun/stale: ValueError('Required upstream is unrun, stale or blocked') (edge rule block, no attempt consumed); G1 retains it as a RefusedBegin; the CP-2G attempt-1 submit returns refusal 'cp2h_blocked'"},
        "cases": {},
    }
    for name, b in built.items():
        entry = dict(b)
        entry["execution"] = CASES[name]["execution"]
        expected["cases"][name] = entry
    plan = ["CP-0", "CP-1", "CP-2A", "CP-2G", "CP-2H"]
    for c in ("positive", "gap"):
        expected["cases"][c]["plan_order"] = plan
        expected["cases"][c]["cp0"] = {"consumer_rows": ["the snapshot CP-1 row", "submissions.json cp0_consumer_row_cp2a (cases/cp2g-owner)", "cases/cp2g-owner cp0_consumer_row_cp2g", "cases.<case>.readiness_review.consumers[3] (CP-2H)"],
                                       "validator_issues": [], "T8_commands": [["CP-1", "Run CP-1"], ["CP-2A", "Run CP-2A"], ["CP-2G", "Run CP-2G"], ["CP-2H", "Run CP-2H"]]}
    expected["cases"]["refused"] = {
        "execution": "run", "plan_order": plan,
        "cp0": {"rows": ["submissions.json refused.cp0_consumer_row_cp1", "refused.cp0_consumer_row_cp2a", "refused.cp0_consumer_row_cp2g", "refused.cp0_consumer_row_cp2h"], "gap_row": "submissions.json refused.gap_row",
                "validator_issues": [], "settled_status": "restricted", "T8_commands": [["CP-1", "DO NOT RUN"], ["CP-2A", "DO NOT RUN"], ["CP-2G", "DO NOT RUN"], ["CP-2H", "DO NOT RUN"]]},
        "refused_begins": [{"module_id": "CP-1", "reason": "CP-0 has not authorized this consumer's source readiness"}], "refusal": "cp1_not_authorized",
        "refusal_note": "the 'refusal' field of the financial-review-outcome/1 returned by the CP-0 submit that settles CP-0 and triggers the CP-1 begin (the CP-2G refused case pins the same code)",
        "attempts": ["CP-0"], "heads": ["CP-0"], "later_modules": "CP-2A, CP-2G and CP-2H are never begun", "model_publication": "not planned", "receipt": "verifies",
        "must_not_appear": ["a CP-2A, CP-2G or CP-2H ticket, attempt, head or table", "a trigger headroom of 0 standing for a missing one"]}
    expected["cases"]["blocked"] = {
        "plan_order": plan,
        "attempt_0": {"payload": "r01", "result_status": "rejected", "limitations": r01["expected_issues"]},
        "attempt_1": {"payload": "v08", "repair_of": "attempt_0", "repair_issues": r01["expected_issues"], "result_status": "blocked", "limitations": v08["expected_issues"]},
        "head": {"module_id": "CP-2H", "status": "blocked", "tables": 0, "facts": 0},
        "store": "a clone of the positive store before the CP-2H begin (the payloads r01 and v08 mutate the positive submission: on the positive facts v08 yields only the High-confidence issue, and its citations carry the positive source sha)",
        "downstream": "no module requires CP-2H; CP-3, CP-3D and CP-5 list it as optional and would bind it with status blocked under their restricted edge",
        "rule": "execution.settle: attempt 0 invalid -> status rejected; attempt 1 invalid -> status blocked; limitations are the bounded issues",
        "receipt": "verifies; both journaled invalid steps are replayed by the verifier and must reproduce their issues exactly",
        "must_not_appear": ["a CP-2H table or fact", "a third attempt"]}
    expected["cases"]["cp2g_blocked"] = {
        "plan_order": plan,
        "cp2g": {"attempt_0": "CP-2G refusals r01 (rejected)", "attempt_1": "CP-2G refusals v13 (blocked)", "head": "blocked, no tables (frozen CP-2G oracle cases.blocked)"},
        "cp2h_begin": {"refused": True, "error": "ValueError", "message": "Required upstream is unrun, stale or blocked", "rule": "execution.current_inputs: a blocked head is bound only under a restricted edge; CP-2G is a required edge of CP-2H (block)",
                       "consumes_attempt": False, "journals_step": False},
        "refusal": "cp2h_blocked",
        "refusal_note": "the 'refusal' field of the financial-review-outcome/1 returned by the CP-2G attempt-1 submit that settles blocked (the _refusal_code of the first retained refusal: module 'CP-2H' -> 'cp2h', kind 'blocked'); the receipt verifier re-runs current_inputs on the pre-refusal snapshot and requires the same text",
        "must_not_appear": ["a CP-2H attempt, head, table or fact"]}
    expected["tamper"] = {
        "case": "positive (closed run: CP-0, CP-1, CP-2A, CP-2G and CP-2H settled, receipt sealed)",
        "target_fact": TAMPER_TARGET, "from": TAMPER_FROM, "to": TAMPER_TO,
        "why_this_fact": "the table cell holds only the fact id and the step output holds the submission, so the first-year text lives only in the result Module; it is the one fact the probe's rebuild (cp2h.probe: the step validator rerun on the journaled payload, then cp2h_module and settle back to the head) contradicts, because the rebuild reads the Brook Credit net debt to EBITDA downgrade trigger first reached in the downside case in FY2027",
        "recipe": [
            "1. Copy the closed positive store directory (blobs, snapshots, current, audit) to a scratch path.",
            f"2. Load the CP-2H head's result Module; replace only the text of fact {TAMPER_TARGET} (its shown spelling is that text); leave every other fact (including T2R.6.t04.base_first and every other row, T2R.9.total.*), table, claim (T2R.6.down included) and limitation unchanged.",
            "3. Serialise the forged Module as Execution._store does (model_dump_json); its sha256 R2 must equal Module.content_hash(); write blobs/R2.",
            "4. Build a new ExecutionSnapshot equal to the current one with the CP-2H Attempt.result_sha256 and Head.result_sha256 set to R2 (status, inputs and commands unchanged, so head_of(forged Module) equals the Head) and the same parent; write snapshots/<its sha256>.json and rewrite current to that digest.",
            "5. In the retained receipt: set the CP-2H SettledHead.result_sha256 to R2; set receipt.snapshot_sha256 and every coordinate that named the old final snapshot (the CP-2H settling OwnerSubmission.snapshot_after_sha256; its record is retained as audit/submissions/<content_hash>) to the new digest; delete audit/submissions/<old record hash> and write the edited OwnerSubmission as audit/submissions/<its content_hash> (model_dump_json bytes); rewrite audit/receipt.sha256 with the forged receipt's content_hash (the audit file travels under its new hash)."],
        "expect": {
            "passes": "everything upstream of the probe: audit inventory, blob and snapshot hashes, ancestor walk, head_of equality, begin and publication records, call and read replay (including the ok read_pages calls of the ratings source), journaled-step replay (the payload and step are untouched)",
            "refuses": "cp2h.probe raises WorkflowError('identity_mismatch'); verify_owner_run_receipt raises identity_mismatch",
            "test_asserts": "on the forged copy, _verify_audit and every check before _PROBES pass; then cp2h.probe raises identity_mismatch. A test asserting identity_mismatch alone would never show that the probe was reached."},
        "step_output_edit": "an edited CP-2H step output is caught by the store's own blob hash check (Module.content_hash / the step blob), not by the probe's output comparison (recorded limitation, S1a R3-5)"}
    OUT.mkdir(parents=True, exist_ok=True)
    for fname, obj in (("manifest.json", manifest), ("submissions.json", submissions), ("expected.json", expected)):
        (OUT / fname).write_text(json.dumps(obj, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
