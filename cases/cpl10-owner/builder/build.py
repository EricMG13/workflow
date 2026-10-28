"""Writes cases/cpl10-owner/{manifest,submissions,expected}.json (stdlib only).

An independent transcription of the CP-L10 (financial change screen) rules written in
work/lead/cpl10-owner-preparation/lease-draft.md. deploy_vii is never imported or run here. Amendment 1 (rulings F1-F5) is applied.
Every number is derived from the frozen financial source bytes (cases/financial/manifest.json,
hash-checked) with exact rational arithmetic (fractions.Fraction) and cross-checked against
decimal.Context(prec=38, ROUND_HALF_EVEN), the context of model/_cells.py.

Run: python3 -I cases/cpl10-owner/builder/build.py   (from the repository root)
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
OUT = ROOT / "cases" / "cpl10-owner"
D = Decimal
CTX = Context(prec=38, rounding=ROUND_HALF_EVEN)

# --- 0. pinned inputs (every file this builder reads) -------------------------------------------
PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "src/deploy_vii/methodology.json": "1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6",
}
RAW = {}
for _rel, _sha in PINS.items():
    RAW[_rel] = (ROOT / _rel).read_bytes()
    assert hashlib.sha256(RAW[_rel]).hexdigest() == _sha, _rel
FIN = json.loads(RAW["cases/financial/manifest.json"])
METH = {m["module_id"]: m for m in json.loads(RAW["src/deploy_vii/methodology.json"])}


def page_sha(pages):
    return hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()


SRC = {s["source_id"]: s for s in FIN["sources"]}
for _sid, _s in SRC.items():
    assert page_sha([p["text"] for p in _s["pages"]]) == _s["sha256"], _sid
PAGE = {p["locator"]: p["text"] for p in SRC["financial"]["pages"]}

# --- 0b. methodology facts the lease relies on (asserted, not assumed) ---------------------------
CPL10 = METH["CP-L10"]
assert CPL10["required"] == ["CP-0", "CP-1"] and CPL10["optional"] == []  # landed: D4 added CP-1 (it was ["CP-0"])
assert CPL10["table_ids"][-5:] == ["TL10.1", "TL10.2", "TL10.3", "TL10.4", "TL10.5"]  # landed: TL10.5 appended after TL10.4
TL10 = [t for t in CPL10["table_ids"] if t.startswith("TL10.")]
for _mid, _m in METH.items():  # D8: no other module lists a TL10.x id
    if _mid != "CP-L10":
        assert not set(TL10) & set(_m["table_ids"]), _mid
# Amendment 1 F1: the totals live in a new table TL10.5, registered by the single serialised methodology change.
TL10_NEW = "TL10.5"
assert not any(TL10_NEW in _m["table_ids"] for _m in METH.values() if _m is not CPL10)  # D8: TL10.5 belongs to CP-L10 only
assert TL10[-1] == TL10_NEW
TL10_PRODUCED = TL10
assert METH["CP-1"]["required"] == ["CP-0"]
TARGET_TITLE = {k: METH[k]["title"] for k in ("CP-1D", "CP-2A", "CP-2D")}
D4_PLAN = ["CP-0", "CP-1", "CP-L10"]  # plan(("CP-L10",)) after D4: CP-0, CP-1 required (block)

# --- 1. exact arithmetic ----------------------------------------------------------------------


def fr(x):
    return x if isinstance(x, Fraction) else Fraction(x)


def q38(x):
    f = fr(x)
    if f == 0:
        return D(0)
    with localcontext(CTX):
        return D(f.numerator) / D(f.denominator)


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
    body = f"{abs(rounded):,.{places}f}"
    return (f"({body})" if rounded < 0 else body) + suffix


# --- 2. the CP-1 facts CP-L10 reads (T4.10, '<column> · <metric>') -----------------------------


def row_values(page, label, count):
    for line in PAGE[page].split("\n"):
        if line.startswith(label + "  "):
            tokens = line[len(label):].split()
            assert len(tokens) == count, (label, tokens)
            return [D(t[1:-1]) * -1 if t.startswith("(") else D(t) for t in tokens]
    raise AssertionError(label)


EBITDA_Q = row_values("page:2", "Reported EBITDA", 5)  # Q1..Q4, FY
INTEREST_Q = row_values("page:3", "Cash interest paid", 5)
FCF_Q = row_values("page:3", "Levered free cash flow", 5)
DEBT_BS = row_values("page:4", "Total debt", 6)  # opening, Q1..Q4, FY
CASH_BS = row_values("page:4", "Cash and cash equivalents", 6)
for _s in (EBITDA_Q, INTEREST_Q, FCF_Q):
    assert sum(_s[:4]) == _s[4]
LTM_EBITDA, LTM_INTEREST = sum(EBITDA_Q[:4]), sum(INTEREST_Q[:4])
_mo = FIN["q4_ltm_metric_oracle"]
assert (D(_mo["total_leverage_reported"]["numerator"]), D(_mo["total_leverage_reported"]["denominator"])) == (DEBT_BS[4], LTM_EBITDA)
assert (D(_mo["interest_coverage_reported"]["numerator"]), D(_mo["interest_coverage_reported"]["denominator"])) == (LTM_EBITDA, LTM_INTEREST)
assert FIN["q4_ltm_derived_source_units"]["net_debt"] == norm(DEBT_BS[4] - CASH_BS[4])

QUARTERS = {  # key: (label column, period string, start, end)
    "Q1": ("Q1 25 (2025-01-01 to 2025-03-31)", "Q1 25: 2025-01-01 to 2025-03-31"),
    "Q2": ("Q2 25 (2025-04-01 to 2025-06-30)", "Q2 25: 2025-04-01 to 2025-06-30"),
    "Q3": ("Q3 25 (2025-07-01 to 2025-09-30)", "Q3 25: 2025-07-01 to 2025-09-30"),
    "Q4": ("Q4 25 (2025-10-01 to 2025-12-31)", "Q4 25: 2025-10-01 to 2025-12-31"),
}
QKEYS = tuple(QUARTERS)
# Marker for the calculation_id of a copied CP-1 cell: the CP-1 fact's own `canonical-kpi:<sha256>` id (every
# T4.10 fact has one, source-class and missing ratio facts too), bound at run time, never literal here.
CP1_CALCULATION_ID = "{{CP1_CALCULATION_ID}}"
CLAIM_CITATION_RULE = ("Claim.citations = the de-duplicated union, in first-reference order, of the citations of every fact the claim references, transitively through "
                       "derives_from and the copied CP-1 cells (the CP-1C L3 rule: a calculated fact's citations are the ordered, de-duplicated concatenation of "
                       "the citations of the facts in derives_from; a copied cell carries its CP-1 fact's citations). A claim that references no fact carries none")
CP1_CITATION_MARKER = "{{{{CP1_CITATIONS:{label}}}}}"  # the citations of the named CP-1 T4.10 fact, bound at run time
ORD = {"Q1": "first", "Q2": "second", "Q3": "third", "Q4": "fourth"}
# CP-1's own limitation text for a month-less ratio. OBSERVED on the real promoted CP-1 head (a copy of
# the S1 positive head, read-only probes of review-precise-1 and of revision 2, 2026-10-28): every
# Q1, Q2 and Q3 ratio fact is status missing, value_class calculated, with exactly this limitation.
GATE = "COMPONENT_MISSING; Four complete contiguous quarters spanning 364-371 days are required"

# (topic_id, CP-1 metric, label, unit class, unit token, value_class observed|inferred)
TOPICS = (
    ("ebitda", "ebitda", "EBITDA", "amount", "US$ m"),
    ("fcf", "fcf", "Free cash flow", "amount", "US$ m"),
    ("cash", "cash_closing", "Cash", "amount", "US$ m"),
    ("total_debt", "total_debt", "Total debt", "amount", "US$ m"),
    ("net_debt", "net_debt", "Net debt", "amount", "US$ m"),
    ("total_leverage", "total_leverage_reported", "Total leverage", "multiple", "x"),
    ("interest_coverage", "interest_coverage_reported", "Interest coverage", "multiple", "x"),
)
TID = [t[0] for t in TOPICS]
# value_class of the CP-1 T4.10 fact of each metric, OBSERVED in every quarter column Q1-Q4 on the real
# promoted head (all 500 T4.10 facts, no duplicate label); a missing ratio fact is `calculated` too.
VCLASS = {"ebitda": "source", "fcf": "calculated", "cash_closing": "source", "total_debt": "source",
          "net_debt": "calculated", "total_leverage_reported": "calculated", "interest_coverage_reported": "calculated"}
TARGET = {"ebitda": "CP-1D", "fcf": "CP-2D", "cash": "CP-2D", "total_debt": "CP-2D", "net_debt": "CP-2D",
          "total_leverage": "CP-2A", "interest_coverage": "CP-2A"}


def cp1_value(metric, qkey):
    """Exact CP-1 value of (metric, quarter) from the frozen pages, or None where CP-1 has none."""
    i = QKEYS.index(qkey)
    if metric == "ebitda":
        return EBITDA_Q[i]
    if metric == "fcf":
        return FCF_Q[i]
    if metric == "cash_closing":
        return CASH_BS[i + 1]
    if metric == "total_debt":
        return DEBT_BS[i + 1]
    if metric == "net_debt":
        return DEBT_BS[i + 1] - CASH_BS[i + 1]
    if qkey != "Q4":
        return None  # ratios: a twelve-month basis exists only for the quarter ending the year
    if metric == "total_leverage_reported":
        return q38(Fraction(DEBT_BS[4]) / Fraction(LTM_EBITDA))
    if metric == "interest_coverage_reported":
        return q38(Fraction(LTM_EBITDA) / Fraction(LTM_INTEREST))
    raise KeyError(metric)


def cp1_fact(metric, qkey):
    column, period = QUARTERS[qkey]
    value = cp1_value(metric, qkey)
    return {
        "label": f"{column} · {metric}", "period": period,
        "status": "known" if value is not None else "missing",
        "amount_exact": None if value is None else norm(value), "value_class": VCLASS[metric],
        "value_class_basis": "observed",
        "limitation": None if value is not None else GATE,
        "_value": value,
    }


def public_fact(f):
    return {k: v for k, v in f.items() if not k.startswith("_")}


# --- 3. the screening rules (Python's; transcription of the lease) -------------------------------
MATERIAL, WATCH = Fraction(1, 10), Fraction(1, 20)
CLASS_ORDER = {"Material": 0, "Watch": 1, "Not assessed": 2, "Stable": 3}
DISPOSITION = {"Material": "Upgrade to full module", "Watch": "Monitor", "Stable": "No action", "Not assessed": "Evidence needed"}


def rank_key(materiality, zero_base, pct_f, index):
    """Material, Watch, Not assessed, Stable; a zero-base Material first inside Material; then the
    larger |change on starting level|; then register order."""
    big = bool(zero_base) and materiality == "Material"
    return (CLASS_ORDER[materiality], 0 if big else 1, -(pct_f or Fraction(0)), index)


def screen_topic(from_v, to_v):
    """Exact rule for one topic: None operand = CP-1 has no known fact (never zero)."""
    if from_v is None or to_v is None:
        return {"status": "missing", "materiality": "Not assessed", "evidence": "Missing", "change": None, "pct": None, "pct_f": None,
                "pct_status": "missing"}
    change = fr(to_v) - fr(from_v)
    if fr(from_v) == 0:
        mat = "Stable" if change == 0 else "Material"
        return {"status": "known", "materiality": mat, "evidence": "Complete", "change": change, "pct": None, "pct_f": None,
                "pct_status": "not_applicable", "zero_base": True}
    pct = abs(change) / abs(fr(from_v))
    signed = change / abs(fr(from_v))
    mat = "Material" if pct >= MATERIAL else "Watch" if pct >= WATCH else "Stable"
    return {"status": "known", "materiality": mat, "evidence": "Complete", "change": change, "pct": signed, "pct_f": pct,
            "pct_status": "known"}


def screen(pair):
    a, b = pair
    rows = []
    for i, (tid, metric, label, ucl, tok) in enumerate(TOPICS):
        fa, fb = cp1_fact(metric, a), cp1_fact(metric, b)
        r = screen_topic(fa["_value"], fb["_value"])
        r.update(topic=tid, metric=metric, label=label, ucl=ucl, tok=tok, index=i, from_fact=fa, to_fact=fb)
        rows.append(r)
    # rank: Material, Watch, Not assessed, Stable; inside a class larger |pct| first (zero base first)
    for rank, r in enumerate(sorted(rows, key=lambda r: rank_key(r["materiality"], r.get("zero_base"), r["pct_f"], r["index"])), 1):
        r["rank"] = rank
    return rows


# --- 4. fixtures: the composer rule on literal operands (no run; boundaries and edge states) ------
FIXTURES = {}
for _name, _a, _b in (
    ("exactly_material", D("10"), D("11")),
    ("exactly_watch", D("20"), D("21")),
    ("just_below_watch", D("20"), D("20.99")),
    ("fall_is_signed", D("20"), D("17")),
    ("zero_base_nonzero_delta", D("0"), D("2")),
    ("zero_base_zero_delta", D("0"), D("0")),
    ("negative_base", D("-4"), D("-2")),
    ("from_missing", None, D("2")),
    ("both_missing", None, None),
):
    _r = screen_topic(_a, _b)
    _cross = None
    if _a is not None and _b is not None and _a != 0:  # the exact rule: |b-a|*10 >= |a| Material, *20 Watch
        _cross = {"material": abs(_b - _a) * 10 >= abs(_a), "watch": abs(_b - _a) * 20 >= abs(_a)}
        assert _r["materiality"] == ("Material" if _cross["material"] else "Watch" if _cross["watch"] else "Stable"), _name
    FIXTURES[_name] = {
        "from": None if _a is None else norm(_a), "to": None if _b is None else norm(_b),
        "materiality": _r["materiality"], "evidence": _r["evidence"], "disposition": DISPOSITION[_r["materiality"]],
        "change": None if _r["change"] is None else norm(q38(_r["change"])),
        "pct_status": _r["pct_status"],
        "pct": None if _r["pct"] is None else norm(q38(_r["pct"])),
        "pct_fraction": None if _r["pct"] is None else f"{_r['pct'].numerator}/{_r['pct'].denominator}",
        "pct_shown": None if _r["pct"] is None else show(q38(_r["pct"]), "percent"),
        "exact_test": None if _cross is None else {"abs(change)*10 >= abs(from)": _cross["material"], "abs(change)*20 >= abs(from)": _cross["watch"]},
    }
assert [FIXTURES[k]["materiality"] for k in ("exactly_material", "exactly_watch", "just_below_watch")] == ["Material", "Watch", "Stable"]
assert FIXTURES["just_below_watch"]["pct_shown"] == "5.0%" and FIXTURES["just_below_watch"]["materiality"] == "Stable"  # shown rounded, rated exact
assert FIXTURES["fall_is_signed"]["pct"] == "-0.15" and FIXTURES["negative_base"]["pct"] == "0.5"  # (-2 - -4) / |-4|
# ordering rule over seven topics (register order a..g): Watch 1/16; Material 1/8 and 1/4; two Stable
# (a tie, register order); a zero-base Material (no percentage; first inside Material); Not assessed.
FIXTURE_RANK = {
    "rows": [("a", "Watch", Fraction(1, 16), False), ("b", "Material", Fraction(1, 8), False), ("c", "Stable", Fraction(0), False),
             ("d", "Material", Fraction(1, 4), False), ("e", "Material", None, True), ("f", "Not assessed", None, False),
             ("g", "Stable", Fraction(0), False)],
}
_rk = sorted(enumerate(FIXTURE_RANK["rows"]), key=lambda t: rank_key(t[1][1], t[1][3], t[1][2], t[0]))
FIXTURE_RANK["expected_order"] = [t[1][0] for t in _rk]
assert FIXTURE_RANK["expected_order"] == ["e", "d", "b", "a", "f", "c", "g"]  # hand-checked
FIXTURE_RANK["rows"] = [[n, m, "zero base" if z else ("none" if p is None else f"{p.numerator}/{p.denominator}")] for n, m, p, z in FIXTURE_RANK["rows"]]

# --- 5. the literal analyst submissions --------------------------------------------------------
POS_PAIR, LIM_PAIR = ("Q1", "Q4"), ("Q2", "Q3")


def pair_json(p):
    return {"from_period": QUARTERS[p[0]][1], "to_period": QUARTERS[p[1]][1]}


GAP_NO_PRIOR_YEAR = {
    "gap": "No prior-year statements are in the pack, so annual change and growth cannot be screened.",
    "why_it_matters": "A comparison of two quarters cannot separate a seasonal pattern from a trend.",
    "affected_analysis": "overall",  # F4 (6): names a topic of the view or `overall`; the annual comparison concerns the whole screen
    "severity": "Material",
    "action": "Supply prior-year quarterly statements, then run the earnings quality and downside owners.",
}
SUBMISSIONS = {
    "positive": {
        "comparison": pair_json(POS_PAIR),
        "assessments": [
            {"topic_id": "cash", "category": "Analyst Interpretation", "confidence": "Medium",
             "assessment": "Cash built up while borrowings also rose, so the larger balance reflects drawing rather than retained earnings alone.",
             "credit_transmission": "A larger cash balance supports near-term liquidity but is funded by additional debt, so gross and net positions should be read together."},
            {"topic_id": "total_debt", "category": "Analyst Interpretation", "confidence": "Medium",
             "assessment": "Borrowing grew in step with cash, leaving net debt unchanged, so the increase does not by itself weaken credit capacity.",
             "credit_transmission": "Higher gross debt raises interest cost and rollover exposure even when net debt is flat."},
        ],
        "overall": {"rationale": "The screen finds balance sheet growth funded by debt, with earnings and cash generation unchanged between the two quarters.",
                    "category": "Analyst Interpretation", "confidence": "Medium", "limitation": None},
        "gaps": [GAP_NO_PRIOR_YEAR],
    },
    "limited": {
        "comparison": pair_json(LIM_PAIR),
        "assessments": [
            {"topic_id": "cash", "category": "Analyst Interpretation", "confidence": "Low",
             "assessment": "Cash edged up over the quarter with no sign of a break in the pattern.",
             "credit_transmission": "A modest rise in cash does not change the liquidity picture on its own."},
        ],
        "overall": {"rationale": "Nothing in the two middle quarters calls for a closer look beyond a small build in cash.",
                    "category": "Analyst Interpretation", "confidence": "Low", "limitation": None},  # F4 (5): a non-Insufficient-Information overall carries no limitation
        "gaps": [],
    },
}
SYNTHETIC = "Synthetic case; not real issuer qualification"  # execution.py:440-446, appended for case_kind synthetic
PROHIBITED = ("recommend", "recovery", "covenant")  # CP-1A's prohibited conclusions, as the CP-2A draft


def analyst_texts(sub):
    out = []
    for i, a in enumerate(sub["assessments"]):
        out.append((f"assessments[{i}].assessment", a["assessment"]))
        out.append((f"assessments[{i}].credit_transmission", a["credit_transmission"]))
    out.append(("overall.rationale", sub["overall"]["rationale"]))
    if sub["overall"]["limitation"]:
        out.append(("overall.limitation", sub["overall"]["limitation"]))
    for i, g in enumerate(sub["gaps"]):
        for f in ("gap", "why_it_matters", "affected_analysis", "action"):
            out.append((f"gaps[{i}].{f}", g[f]))
    return out


for _case, _sub in SUBMISSIONS.items():
    for _path, _text in analyst_texts(_sub):
        assert not re.search(r"[0-9{}\[\]]", _text), (_case, _path)  # digit-free, no references
        assert not any(w in _text.lower() for w in PROHIBITED), (_case, _path)

# --- 6. composition of one case ----------------------------------------------------------------
# Table shape (owner-preparation-brief.md, "Table shape"; contracts.validate_tables): every row of a table has exactly one
# fact per column, in column order, with fact id <table>.<row>.<field>; the table's facts are exactly the cells it references.
COLUMNS = {
    "TL10.1": ["subject_identity", "source_ref", "source_owner_module", "as_of_or_period", "scope_status", "topics_supported", "limitation"],
    "TL10.2": ["from_value", "to_value", "change", "change_pct", "materiality", "evidence_status", "disposition", "priority_rank",
               "source_owner_modules", "source_refs", "upgrade_module_ids"],
    "TL10.3": ["screen_item", "assessment", "evidence", "credit_transmission", "screening_implication", "confidence", "source_refs"],
    "TL10.4": ["topic_id", "trigger", "missing_inputs", "decision_impact", "required_source", "target_full_module_id",
               "expected_owned_object", "blocking_for_full_decision"],
    TL10_NEW: ["material", "watch", "stable", "not_assessed"],
}
assert list(COLUMNS) == TL10_PRODUCED
# F3: TL10.1 scope_status and source_ref are run-bound by a stated rule, never a literal.
HEAD_RESULT_SHA256 = {"CP-0": "{{CP0_RESULT_SHA256}}", "CP-1": "{{CP1_RESULT_SHA256}}"}
HEAD_STATUS_WORD = {"CP-0": "{{CP0_STATUS_WORD}}", "CP-1": "{{CP1_STATUS_WORD}}"}


def check_table_shape(case, facts, tables):
    by_id = {}
    for f in facts:
        assert f["fact_id"] not in by_id, (case, f["fact_id"])
        by_id[f["fact_id"]] = f
    assert [t["table_id"] for t in tables] == TL10_PRODUCED, case
    for t in tables:
        cols = COLUMNS[t["table_id"]]
        assert t["columns"] == cols, (case, t["table_id"])
        seen = set()
        assert len({r["row_id"] for r in t["rows"]}) == len(t["rows"]), (case, t["table_id"])
        for r in t["rows"]:
            assert len(r["fact_ids"]) == len(cols), (case, t["table_id"], r["row_id"], len(r["fact_ids"]), len(cols))  # contracts.py:270-272
            for col, fid in zip(cols, r["fact_ids"]):
                f = by_id[fid]
                assert fid not in seen, (case, fid)
                assert (f["table_id"], f["row_id"], f["field"]) == (t["table_id"], r["row_id"], col), (case, fid)
                seen.add(fid)
        assert seen == {f["fact_id"] for f in facts if f["table_id"] == t["table_id"]}, (case, t["table_id"])


def composed_case(name):
    sub = SUBMISSIONS[name]
    p = (next(k for k in QKEYS if QUARTERS[k][1] == sub["comparison"]["from_period"]),
         next(k for k in QKEYS if QUARTERS[k][1] == sub["comparison"]["to_period"]))
    rows = screen(p)
    required = [r["topic"] for r in rows if r["materiality"] in ("Material", "Watch")]
    assert sorted(required) == sorted(a["topic_id"] for a in sub["assessments"]), (name, required)
    analyst = {a["topic_id"]: a for a in sub["assessments"]}
    facts, tables, claims = [], [], []
    o1, o2 = ORD[p[0]], ORD[p[1]]
    span = f"between the {o1} quarter of 2025 and the {o2} quarter of 2025"

    def fact(table, row, field, label, **kw):
        f = {"fact_id": f"{table}.{row}.{field}", "table_id": table, "row_id": row, "field": field, "label": label}
        f.update(kw)
        if f.get("unit") == "MILLIONS":  # every MILLIONS fact carries its currency and scale (CP-1's facts do)
            f.update(currency="USD", scale="1000000")
        facts.append(f)
        return f["fact_id"]

    def text(table, row, field, label, value, vclass=None, derives=()):
        kw = {"status": "known", "text": value, "shown": value, "value_class": vclass}
        if vclass == "calculated":
            kw.update(calculation_id=f"calc:{table}.{row}.{field}", derives_from=list(derives))
        return fact(table, row, field, label, **kw)

    def num(table, row, field, label, value, ucl, unit, *, decimals=None, vclass="calculated", derives=(), formula=None, period=None):
        period = period or f"{QUARTERS[p[0]][1]} -> {QUARTERS[p[1]][1]}"
        return fact(table, row, field, label, status="known", unit=unit, period=period, amount_exact=norm(value),
                    shown=(f"{norm(value)} {unit}" if unit in ("rank", "topics") else show(value, ucl, decimals)), decimals=decimals, value_class=vclass,
                    formula=formula, calculation_id=f"calc:{table}.{row}.{field}" if vclass == "calculated" else None,
                    derives_from=list(derives))

    def gapf(table, row, field, label, unit, reason, status="missing", period=None):
        # fact_spelling: a missing cell reads `∅ G#`; a not_applicable cell reads `∅ G# n.m.`
        return fact(table, row, field, label, status=status, unit=unit, period=period,
                    shown="∅ G#" if status == "missing" else "∅ G# n.m.", limitation=reason,
                    value_class="calculated" if status != "missing" else None)

    def na(table, row, field, label, reason):
        """A not_applicable text cell (F1: the overall row's cells that have no meaning for it); nothing is derived, so no value class."""
        return fact(table, row, field, label, status="not_applicable", shown="\u2205 G# n.m.", limitation=reason)

    def copied(tid, field, label, ucl, cf, dec):
        """A TL10.2 cell that is the CP-1 T4.10 fact verbatim (value_class, calculation_id, citations, status)."""
        known = cf["status"] == "known"
        return fact("TL10.2", tid, field, label, status=cf["status"], unit=UNIT[ucl], period=cf["period"],
                    amount_exact=cf["amount_exact"] if known else None,
                    shown=show(D(cf["amount_exact"]), ucl, dec if ucl == "amount" else None) if known else "∅ G#",
                    decimals=dec if ucl == "amount" and known else None, value_class=cf["value_class"], copied_from_cp1=cf["label"],
                    value_class_basis=cf["value_class_basis"], limitation=cf["limitation"],
                    calculation_id=CP1_CALCULATION_ID, derives_from=[],
                    lineage="the CP-1 fact verbatim: its own calculation_id and citations are bound at run time")

    UNIT = {"amount": "MILLIONS", "multiple": "MULTIPLE", "percent": "PERCENT"}
    # --- TL10.2 topic screen
    t2 = []
    pair_period = f"{QUARTERS[p[0]][1]} -> {QUARTERS[p[1]][1]}"
    for r in rows:
        tid, ucl = r["topic"], r["ucl"]
        fa, fb = r["from_fact"], r["to_fact"]
        dec = 2
        ids = []
        for field, lab, cf, qk in (("from_value", "Starting value", fa, p[0]), ("to_value", "Closing value", fb, p[1])):
            ids.append(copied(tid, field, f"{r['label']} · {lab}", ucl, cf, dec))
        derives = [fa["label"], fb["label"]]
        if r["status"] == "known":
            ids.append(num("TL10.2", tid, "change", f"{r['label']} · Change", q38(r["change"]), ucl, UNIT[ucl],
                           decimals=dec if ucl == "amount" else None, derives=derives, formula="closing value - starting value",
                           period=f"{QUARTERS[p[0]][1]} -> {QUARTERS[p[1]][1]}"))
            if r["pct_status"] == "known":
                ids.append(num("TL10.2", tid, "change_pct", f"{r['label']} · Change on starting level", q38(r["pct"]), "percent", "PERCENT",
                               derives=derives, formula="(closing value - starting value) / |starting value|",
                               period=f"{QUARTERS[p[0]][1]} -> {QUARTERS[p[1]][1]}"))
            else:
                ids.append(gapf("TL10.2", tid, "change_pct", f"{r['label']} · Change on starting level", "PERCENT",
                                "Not applicable: the starting value is zero", status="not_applicable", period=pair_period))
        else:
            ends = 'either quarter' if fa['status'] == fb['status'] == 'missing' else 'the starting quarter' if fa['status'] == 'missing' else 'the closing quarter'
            reason = f"Not calculable: CP-1 carries no known value for {ends} ({fa['limitation'] or fb['limitation']})"  # CP-1's own limitation text
            ids.append(gapf("TL10.2", tid, "change", f"{r['label']} · Change", UNIT[ucl], reason, period=pair_period))
            ids.append(gapf("TL10.2", tid, "change_pct", f"{r['label']} · Change on starting level", "PERCENT", reason, period=pair_period))
        ids.append(text("TL10.2", tid, "materiality", "Materiality", r["materiality"], "calculated", derives))
        ids.append(text("TL10.2", tid, "evidence_status", "Evidence status", r["evidence"], "calculated", derives))
        ids.append(text("TL10.2", tid, "disposition", "Disposition", DISPOSITION[r["materiality"]], "calculated", derives))
        ids.append(num("TL10.2", tid, "priority_rank", "Priority rank", D(r["rank"]), "amount", "rank", decimals=0, derives=derives,
                       formula="Material, Watch, Not assessed, Stable; larger |change on starting level| first; register order"))
        ids.append(text("TL10.2", tid, "source_owner_modules", "Source owner modules", "CP-1", None))
        ids.append(text("TL10.2", tid, "source_refs", "Source references", f"CP-1 {fa['label']}; CP-1 {fb['label']}", None))
        ids.append(text("TL10.2", tid, "upgrade_module_ids", "Upgrade module ids", TARGET[tid], None))
        t2.append({"row_id": tid, "label": r["label"], "fact_ids": ids})
    counts = {k: sum(1 for r in rows if r["materiality"] == v) for k, v in
              (("material", "Material"), ("watch", "Watch"), ("stable", "Stable"), ("not_assessed", "Not assessed"))}
    assert sum(counts.values()) == len(TOPICS)
    tids = [num(TL10_NEW, "total", k, f"Topics rated {lab}", D(counts[k]), "amount", "topics", decimals=0,
                formula="count of topics by materiality") for k, lab in
            (("material", "Material"), ("watch", "Watch"), ("stable", "Stable"), ("not_assessed", "Not assessed"))]
    t5 = [{"row_id": "total", "label": "Total", "fact_ids": tids}]  # F1: its own table (the totals are not topic-screen columns)
    # --- TL10.1 scope and sources
    topics_ok = ", ".join(r["label"] for r in rows if r["evidence"] == "Complete")
    t1 = []
    for rid, mod, per, topics in (
        ("cp0", "CP-0", "as of 2026-01-10", "None: source readiness only"),
        ("cp1", "CP-1", f"{QUARTERS[p[0]][1]} -> {QUARTERS[p[1]][1]}", topics_ok),
    ):
        ids = [text("TL10.1", rid, "subject_identity", "Subject identity", "Northbridge Synthetic Group", None),
               text("TL10.1", rid, "source_ref", "Source reference", f"{mod}:{HEAD_RESULT_SHA256[mod]}", None),
               text("TL10.1", rid, "source_owner_module", "Source owner module", mod, None),
               text("TL10.1", rid, "as_of_or_period", "As of or period", per, None),
               text("TL10.1", rid, "scope_status", "Scope status", HEAD_STATUS_WORD[mod], None),
               text("TL10.1", rid, "topics_supported", "Topics supported", topics, "calculated" if rid == "cp1" else None),
               text("TL10.1", rid, "limitation", "Limitation", "Inherited limitations of the CP-0 and CP-1 heads apply; see the limitations rail.", None)]
        t1.append({"row_id": rid, "label": mod, "fact_ids": ids})
    # --- TL10.3 screen items (assessed topics + overall)
    t3 = []
    for r in rows:
        if r["topic"] not in analyst:
            continue
        a, tid = analyst[r["topic"]], r["topic"]
        ids = [text("TL10.3", tid, "screen_item", "Screen item", r["label"], None),
               text("TL10.3", tid, "assessment", "Assessment", a["assessment"], "analyst_judgment"),
               text("TL10.3", tid, "evidence", "Evidence", f"TL10.2.{tid}.from_value, TL10.2.{tid}.to_value, TL10.2.{tid}.change, TL10.2.{tid}.change_pct", None),
               text("TL10.3", tid, "credit_transmission", "Credit transmission", a["credit_transmission"], "analyst_judgment"),
               text("TL10.3", tid, "screening_implication", "Screening implication", DISPOSITION[r["materiality"]], "calculated", [r["from_fact"]["label"], r["to_fact"]["label"]]),
               text("TL10.3", tid, "confidence", "Confidence", a["confidence"], "analyst_judgment"),
               text("TL10.3", tid, "source_refs", "Source references", f"CP-1 {r['from_fact']['label']}; CP-1 {r['to_fact']['label']}", None)]
        t3.append({"row_id": tid, "label": r["label"], "fact_ids": ids})
    ov = sub["overall"]
    not_ov = "Not applicable to the overall row"  # F1: the overall row is a full row; these cells have no meaning for it
    t3.append({"row_id": "overall", "label": "Overall", "fact_ids": [
        text("TL10.3", "overall", "screen_item", "Screen item", "Overall", None),
        text("TL10.3", "overall", "assessment", "Assessment", ov["rationale"], "analyst_judgment"),
        na("TL10.3", "overall", "evidence", "Evidence", not_ov),
        na("TL10.3", "overall", "credit_transmission", "Credit transmission", not_ov),
        na("TL10.3", "overall", "screening_implication", "Screening implication", not_ov),
        text("TL10.3", "overall", "confidence", "Confidence", ov["confidence"], "analyst_judgment"),
        na("TL10.3", "overall", "source_refs", "Source references", not_ov)]})
    # --- TL10.4 upgrade triggers
    t4 = []
    for r in rows:
        if r["materiality"] == "Stable":
            continue
        tid = r["topic"]
        assessed = tid in analyst
        ids = [text("TL10.4", tid, "topic_id", "Topic", tid, None),
               text("TL10.4", tid, "trigger", "Trigger", {"Material": "Relative change at or above the Material threshold",
                                                          "Watch": "Relative change at or above the Watch threshold",
                                                          "Not assessed": "Change not calculable from CP-1 facts"}[r["materiality"]], "calculated"),
               text("TL10.4", tid, "missing_inputs", "Missing inputs",
                    "None" if r["evidence"] == "Complete" else "A CP-1 value for each quarter compared", "calculated"),
               (text("TL10.4", tid, "decision_impact", "Decision impact", analyst[tid]["credit_transmission"], "analyst_judgment") if assessed else
                gapf("TL10.4", tid, "decision_impact", "Decision impact", None, "No assessment: the change is not calculable from CP-1 facts")),
               text("TL10.4", tid, "required_source", "Required source",
                    "Settled CP-1 head (available)" if r["evidence"] == "Complete" else
                    f"A CP-1 known value for each quarter compared (CP-1: {r['from_fact']['limitation'] or r['to_fact']['limitation']})", "calculated"),
               text("TL10.4", tid, "target_full_module_id", "Target full module", TARGET[tid], None),
               text("TL10.4", tid, "expected_owned_object", "Expected owned object", TARGET_TITLE[TARGET[tid]], None),
               text("TL10.4", tid, "blocking_for_full_decision", "Blocking for full decision", "Yes" if r["materiality"] == "Material" else "No", "calculated")]
        t4.append({"row_id": tid, "label": r["label"], "fact_ids": ids})
    tables = [
        {"table_id": tid_, "title": title, "columns": list(COLUMNS[tid_]), "rows": rws} for tid_, title, rws in
        (("TL10.1", "Scope and sources", t1), ("TL10.2", "Topic screen", t2), ("TL10.3", "Screen items", t3),
         ("TL10.4", "Upgrade triggers", t4), (TL10_NEW, "Screen totals", t5))
    ]
    check_table_shape(name, facts, tables)
    # --- claims (Python templates; analyst text is digit-free and carries no reference)
    for r in rows:
        tid, u = r["topic"], r["tok"]
        base = f"TL10.2.{tid}"
        if r["status"] == "known":
            claims.append({"claim_id": base, "limitation": None, "refs": [f"{base}.from_value|{u}", f"{base}.to_value|{u}", f"{base}.change|{u}"]
                           + ([f"{base}.change_pct|%"] if r["pct_status"] == "known" else []),
                           "text": (f"{r['label']} moved from {{{base}.from_value|{u}}} to {{{base}.to_value|{u}}} {span}, a change of "
                                    f"{{{base}.change|{u}}}"
                                    + (f" or {{{base}.change_pct|%}} of the starting level" if r["pct_status"] == "known" else " from a zero starting level")
                                    + f"; the screen rates it {r['materiality']}.")})
        else:
            fa, fb = r["from_fact"]["status"], r["to_fact"]["status"]
            ends = "either quarter" if fa == fb == "missing" else "the starting quarter" if fa == "missing" else "the closing quarter"
            claims.append({"claim_id": base, "limitation": None, "refs": [f"{base}.change"],
                           "text": (f"{r['label']}: the change {span} cannot be screened; [{base}.change] is not calculable because CP-1 "
                                    f"carries no known value for {ends}.")})
    claims.append({"claim_id": "TL10.2.summary", "limitation": None,
                   "refs": [f"{TL10_NEW}.total.{k}|topics" for k in ("material", "watch", "stable", "not_assessed")],
                   "text": ("Of seven screened topics, {TL10.5.total.material|topics} rate Material, {TL10.5.total.watch|topics} Watch, "
                            "{TL10.5.total.stable|topics} Stable and {TL10.5.total.not_assessed|topics} cannot be assessed "
                            f"{span}.")})
    for r in rows:
        if r["topic"] in analyst:
            claims.append({"claim_id": f"TL10.3.{r['topic']}", "text": analyst[r["topic"]]["assessment"], "limitation": None, "refs": []})
    claims.append({"claim_id": "TL10.3.overall", "text": ov["rationale"], "limitation": ov["limitation"], "refs": []})
    # F5 (the CP-1C L3 rule): Claim.citations = the de-duplicated union, in first-reference order, of the citations of every fact the claim
    # references, transitively through derives_from and the copied CP-1 cells. Citations are CP-1's own (bound at run time), so the oracle
    # pins the ordered CP-1 T4.10 labels as markers.
    by_id = {f["fact_id"]: f for f in facts}

    def cit_labels(fid, trail=()):
        assert fid not in trail, fid
        f = by_id[fid]
        if f.get("copied_from_cp1"):
            return [f["copied_from_cp1"]]
        out = []
        for d in f.get("derives_from") or []:
            out.extend(cit_labels(d, trail + (fid,)) if d in by_id else [d])
        return out

    for c in claims:
        labels = list(dict.fromkeys(l for ref in c["refs"] for l in cit_labels(ref.split("|")[0])))
        assert all(re.fullmatch(r"Q[1-4] 25 \(.*\) \u00b7 [a-z_]+", l) for l in labels), labels
        c["citations"] = [CP1_CITATION_MARKER.format(label=l) for l in labels]
    # --- own limitations (exact)
    own = [
        "Relative-change thresholds are screening rules documented in the CP-L10 method; they are not covenant or credit tests.",
        "Only the two quarters named in the comparison are compared; no trend, seasonality or annual comparison is made, and the pack has no prior-year statements.",
        "Leverage and coverage are compared only where CP-1 carries a twelve-month basis for both quarters.",
        "A screen rates movement, not credit quality: no recommendation, covenant, recovery or refinancing conclusion is drawn.",
        "Each topic is rated on the exact change on its starting level; the percentage shown is rounded, so a shown value at a threshold can carry the lower rating.",
        "A small starting level inflates the relative change and a negative starting level is measured on its absolute value, so the rating reads the size of movement, not its economic meaning.",
    ]
    for r in rows:
        if r["evidence"] == "Missing":
            own.append(f"Not screened: {r['label']} (CP-1 has no known value for "
                       f"{'either quarter' if r['from_fact']['status'] == r['to_fact']['status'] == 'missing' else 'the starting quarter' if r['from_fact']['status'] == 'missing' else 'the closing quarter'}).")
    for g in sub["gaps"]:
        own.append(f"Gap ({g['severity']}): {g['gap']}")
    # --- the exact read_inputs view content that depends on Python's screens: every offered pair
    pairs = []
    for i, a in enumerate(QKEYS):
        for b in QKEYS[i + 1:]:
            pairs.append({"from_period": QUARTERS[a][1], "to_period": QUARTERS[b][1],
                          "topics": [{"topic_id": r["topic"], "materiality": r["materiality"]} for r in screen((a, b))]})
    view_topics = []
    for tid, metric, label, ucl, tok in TOPICS:
        vals = []
        for qk in QKEYS:
            cf = cp1_fact(metric, qk)
            known = cf["status"] == "known"
            vals.append({"period": QUARTERS[qk][1], "status": cf["status"], "amount_exact": cf["amount_exact"],
                         "shown": show(D(cf["amount_exact"]), ucl, 2) if known else "∅ G#", "limitation": cf["limitation"]})
        view_topics.append({"topic_id": tid, "label": label, "cp1_metric": metric, "unit": tok, "values": vals})
    return {
        "view_topics": view_topics,
        "pair": pair_json(p), "topics": [
            {"topic_id": r["topic"], "label": r["label"], "materiality": r["materiality"], "evidence": r["evidence"],
             "disposition": DISPOSITION[r["materiality"]], "rank": r["rank"], "change_exact": None if r["change"] is None else norm(q38(r["change"])),
             "change_pct_exact": None if r["pct"] is None else norm(q38(r["pct"])),
             "change_pct_fraction": None if r["pct"] is None else f"{r['pct'].numerator}/{r['pct'].denominator}",
             "from": public_fact(r["from_fact"]), "to": public_fact(r["to_fact"])} for r in rows],
        "required_assessments": required, "counts": counts,
        "facts": facts, "tables": tables, "claims": claims, "own_limitations": own,
        "settled_limitations": list(dict.fromkeys([*own, SYNTHETIC])), "module_status": "restricted",
        "view_pair_screens": pairs,
    }


# --- 7. refusals (journaled validator issues of attempt 0) ----------------------------------------


def refusals():
    base = SUBMISSIONS["positive"]
    out = []

    def add(rid, klass, mutate, issue, kind="content", src="this draft"):
        payload = deepcopy(base)
        mutate(payload)
        out.append({"id": rid, "class": klass, "issue_kind": kind, "issue_spelling": src, "payload": payload, "expected_issues": [issue]})

    def setp(path, value):
        def apply(d):
            cur = d
            for k in path[:-1]:
                cur = cur[k]
            cur[path[-1]] = value
        return apply

    add("r01", "starting period not offered", setp(("comparison", "from_period"), "Q0 25: 2024-10-01 to 2024-12-31"),
        "comparison.from_period: not an offered period")
    add("r02", "closing period not after starting period",
        setp(("comparison", "to_period"), QUARTERS["Q1"][1]), "comparison: to_period must come after from_period")
    add("r03", "unknown topic (a third assessment; the two required ones stay)",
        lambda d: d["assessments"].append({**d["assessments"][0], "topic_id": "gross_margin"}),
        "assessments[2].topic_id: unknown topic: gross_margin")
    add("r04", "assessed topic rated Stable (not assessable)",
        lambda d: d["assessments"].append({**d["assessments"][0], "topic_id": "ebitda"}),
        "assessments[2].topic_id: not assessable: ebitda is rated Stable")
    add("r05", "Material or Watch topic left unassessed", lambda d: d["assessments"].pop(1),
        "assessments: missing assessment for total_debt (Watch)")
    add("r06", "topic assessed twice", lambda d: d["assessments"].append(deepcopy(d["assessments"][0])),
        "assessments[2].topic_id: repeated: cash")
    add("r07", "confidence High (a content refusal: the product Confidence type admits High)",
        setp(("assessments", 0, "confidence"), "High"), "assessments[0].confidence: High is not allowed in a screen")
    add("r08", "bare figure in assessment (product text)",
        setp(("assessments", 0, "assessment"), "Cash rose by 20 percent because borrowings rose."),
        "assessments[0].assessment: Bare figure: 20", src="product")
    add("r09", "reference that resolves to no bound fact of the module (product text)",
        setp(("assessments", 0, "credit_transmission"), "Liquidity improves by {TL10.2.cash.nothing|US$ m}."),
        "assessments[0].credit_transmission: Unresolved reference: TL10.2.cash.nothing", src="product")
    add("r10", "prohibited conclusion", setp(("overall", "rationale"), "We recommend a purchase of the debt."),
        "overall.rationale: prohibited conclusion: recommend")
    add("r11", "whitespace-only text (passes the product Text type; a content refusal)", setp(("overall", "rationale"), "   "),
        "overall.rationale: empty")
    add("r12", "payload shape: comparison.from_period missing", lambda d: d["comparison"].pop("from_period"),
        "comparison.from_period: Field required", kind="shape")
    # Amendment 1 F4: validation steps (5) overall and (6) gaps as rules, one literal each (the CP-3C Insufficient-Information precedent).
    II = "Insufficient Information"
    add("r13", "overall confidence is Insufficient Information exactly when its category is (category Insufficient Information, confidence Medium)",
        lambda d: d["overall"].update(category=II, limitation="The comparison rests on two quarters only."),
        "overall.confidence: must be Insufficient Information exactly when the category is")
    add("r14", "Insufficient Information overall without its limitation",
        lambda d: d["overall"].update(category=II, confidence=II, limitation=None),
        "overall.limitation: an Insufficient Information overall states its limitation")
    add("r15", "limitation on an overall that is not Insufficient Information",
        setp(("overall", "limitation"), "A limitation without a gap."),
        "overall.limitation: only an Insufficient Information overall carries a limitation")
    add("r16", "gap names no topic of the view and not `overall`",
        setp(("gaps", 0, "affected_analysis"), "Earnings and cash generation topics"),
        "gaps[0].affected_analysis: must name a topic of the view or overall")
    add("r17", "gap with a whitespace-only missing item (passes the product Text type; a content refusal)",
        setp(("gaps", 0, "gap"), "   "), "gaps[0].gap: empty")
    add("r18", "gap text with a digit", setp(("gaps", 0, "gap"), "No statements for 2024 are in the pack."),
        "gaps[0].gap: must not contain a digit")
    add("r19", "gap repeated", lambda d: d["gaps"].append(deepcopy(d["gaps"][0])), "gaps[1]: repeated gap")
    # product-produced spellings are r08's and r09's (prose.check, probed); every other issue text is this draft's.
    return out


def blocked(refs):
    by = {r["id"]: r for r in refs}
    return {"attempt_0": "refusals r01", "attempt_1": "refusals r08",
            "expect": {"module_status": "blocked", "tables": [], "claims": [], "limitations": "attempt 1's issues",
                       "issues_attempt_1": by["r08"]["expected_issues"]}}


# --- 7b. CP-1 readiness literal (review-precise-1 answer 5, validated there on the real head) and the refused case rows
KPIS = ("ebitda", "fcf", "cash_closing", "total_debt", "net_debt")
CP1_DOWNSTREAM_REVIEW = {
    "inputs_sha256": "{{INPUTS_SHA256}}",
    "consumers": [{"entry": "CP-L10", "requirements": [
        {"requirement": "consumer_specific_cp1_sufficiency", "status": "limited",
         "evidence_ids": [f"{{{{EVID:kpi {k}, quarter {n}}}}}" for n in (1, 2, 3, 4) for k in KPIS],
         "rationale": "Settled quarterly EBITDA, free cash flow, closing cash, total debt and net debt support a two-quarter change screen; twelve-month leverage and coverage exist only for the fourth quarter.",
         "actions": ["Retain the missing twelve-month leverage and coverage basis for the first three quarters as a screen limitation."]}],
        "gaps": [{"gap_ids": ["{{ALL narrative gap ids}}"], "relevance": "relevant", "evidence_ids": [],
                  "rationale": "Every retained source and context warning applies to the change screen."}]}],
}
MISSING_FIN = "Quarterly financial statements were not supplied."
_IDQ = {"source_id": "identity", "source_sha256": SRC["identity"]["sha256"], "locator": "page:1",
        "quote": "Northbridge Synthetic Group is the issuer and consolidated group."}
REFUSED_CP1_ROW = {"module_id": "CP-1", "readiness": "CONDITIONAL", "evidence_demand": "Located historical statements, facility terms, definitions and scope",
                   "source_ids": ["identity"], "rationale": MISSING_FIN, "citations": [_IDQ],
                   "missing_source": "Quarterly financial statements", "limitations": [MISSING_FIN]}
REFUSED_CPL10_ROW = {"module_id": "CP-L10", "readiness": "CONDITIONAL", "evidence_demand": "Settled CP-1 figures for two quarters of one fiscal year",
                     "source_ids": ["identity"], "rationale": MISSING_FIN, "citations": [_IDQ],
                     "missing_source": "Quarterly financial statements", "limitations": [MISSING_FIN]}
REFUSED_GAP_ROW = {"gap_id": "missing-financial", "kind": "source", "severity": "material", "description": MISSING_FIN,
                   "affected_modules": ["CP-1", "CP-L10"], "remediation": "Supply quarterly financial statements"}

def _methodology_digest(rows):
    """tests/test_cp1b_registration.py:34 rule: sha256 of the rows with the CP-1B table_ids popped."""
    rows = deepcopy(rows)
    next(r for r in rows if r["module_id"] == "CP-1B").pop("table_ids")
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


_ROWS = json.loads(RAW["src/deploy_vii/methodology.json"])
DIGEST_BEFORE = "0573968460da16ff13f4590b3f65edc4ebe06685c2e2840c8001b229747d86c6"  # the test's pin before the serialised change (a literal)
DIGEST_AFTER = _methodology_digest(_ROWS)  # computed from the landed methodology.json bytes pinned above (the whole serialised change)
assert DIGEST_AFTER != DIGEST_BEFORE

GREP_LOCATE = "locate by grep for the hash 348fbc4b...8d45 at build time (untracked or still moving in this worktree, so no line number is pinned)"
# Navigator words probed on the committed report_view (sha256 51a6853e...0e12) with the reviewer's rp3 probe
# construction; written here as literals (no product import). Registry order, as report_view.navigator yields it.
NAV_OUTSIDE_CLOSURE = ["CP-1B", "CP-1C", "CP-1D", "CP-2A", "CP-2E", "CP-2G", "CP-2H", "CP-4C", "CP-8", "CP-DR", "CP-MEMO", "CP-OS", "CP-2D", "CP-3D", "CP-3C"]
NAV_PRESET_NOT_REQUESTED = ["CP-1A", "CP-2", "CP-3", "CP-4", "CP-5", "CP-6", "CP-MODEL"]
NAV_STATES = {
    "without_d4": {
        "statuses": {"CP-0": "unrun", "CP-L10": "unrun"},
        "rows": [{"number": 1, "module_id": "CP-0", "word": "Not run", "glyph": "unrun"},
                 {"number": 2, "module_id": "CP-L10", "word": "Not run", "glyph": "unrun"}],
        "footer": {"Not run": ["CP-1"] + NAV_PRESET_NOT_REQUESTED, "Not in this Pathway": NAV_OUTSIDE_CLOSURE},
        "module_display": {"Not run": ["CP-0", "CP-1"] + NAV_PRESET_NOT_REQUESTED[:-1] + ["CP-L10", "CP-MODEL"], "Not in this Pathway": NAV_OUTSIDE_CLOSURE},
        "cp1_status_word": "Not run", "cp1_status": "not_in_pathway", "row_count": 25, "footer_count": 23},
    "d4_cp1_unrun": {
        "statuses": {"CP-0": "unrun", "CP-1": "unrun", "CP-L10": "unrun"},
        "rows": [{"number": 1, "module_id": "CP-0", "word": "Not run", "glyph": "unrun"},
                 {"number": 2, "module_id": "CP-1", "word": "Not run", "glyph": "unrun"},
                 {"number": 3, "module_id": "CP-L10", "word": "Not run", "glyph": "unrun"}],
        "footer": {"Not run": NAV_PRESET_NOT_REQUESTED, "Not in this Pathway": NAV_OUTSIDE_CLOSURE},
        "module_display": {"Not run": ["CP-0", "CP-1"] + NAV_PRESET_NOT_REQUESTED[:-1] + ["CP-L10", "CP-MODEL"], "Not in this Pathway": NAV_OUTSIDE_CLOSURE},
        "cp1_status_word": "Not run", "cp1_status": "unrun", "row_count": 25, "footer_count": 22},
    "d4_cp1_settled": {
        "statuses": {"CP-0": "restricted", "CP-1": "restricted", "CP-L10": "unrun"},
        "rows": [{"number": 1, "module_id": "CP-0", "word": "With limitations", "glyph": "lim"},
                 {"number": 2, "module_id": "CP-1", "word": "With limitations", "glyph": "lim"},
                 {"number": 3, "module_id": "CP-L10", "word": "Not run", "glyph": "unrun"}],
        "footer": {"Not run": NAV_PRESET_NOT_REQUESTED, "Not in this Pathway": NAV_OUTSIDE_CLOSURE},
        "module_display": {"With limitations": ["CP-0", "CP-1"], "Not run": NAV_PRESET_NOT_REQUESTED[:-1] + ["CP-L10", "CP-MODEL"], "Not in this Pathway": NAV_OUTSIDE_CLOSURE},
        "cp1_status_word": "With limitations", "cp1_status": "restricted", "row_count": 25, "footer_count": 22},
}
assert NAV_PRESET_NOT_REQUESTED[-1] == "CP-MODEL" and len(NAV_OUTSIDE_CLOSURE) == 15
for _s in NAV_STATES.values():
    assert _s["row_count"] == len(_s["rows"]) + _s["footer_count"] == 25
    assert _s["footer_count"] == sum(len(v) for v in _s["footer"].values())
    assert sorted(sum(_s["module_display"].values(), [])) == sorted([r["module_id"] for r in _s["rows"]] + sum(_s["footer"].values(), []))
    assert next(r["word"] for r in _s["rows"] if r["module_id"] == "CP-L10") == "Not run"

D4_SIDE_EFFECTS = {
    "methodology_json": {"file": "src/deploy_vii/methodology.json", "sha256_before": "348fbc4b877e4f0351ecc238ea005adf815291b15a6267f263459203a08f8d45",
                         "sha256_after": PINS["src/deploy_vii/methodology.json"],
                         "change": "landed in the serialised change: CP-L10 `required` [\"CP-0\"] -> [\"CP-0\", \"CP-1\"] and CP-L10 `table_ids` gains TL10.5 (amendment 1, F1: appended after TL10.4); CP-1C `table_ids` become T1C.1-T1C.8 (the eleven T4.x ids dropped); CP-1D drops T1E.1-T1E.6; CP-2A drops T5.1-T5.7 (they stay CP-5's)",
                         "serialised_change": "one methodology.json change carrying CP-L10 D4 (required edge), the CP-L10 table_ids gaining TL10.5 (amendment 1) and CP-1C D8 (T1C.1-T1C.8, CP-1C amendment 1) together, with ONE re-pin pass of every builder that pins methodology.json (methodology_pinning_builders below); neither lands alone"},
    "test_pin": {"file": "tests/test_cp1b_registration.py", "line": 34, "test": "test_only_cp1b_table_ownership_changes",
                 "digest_before": DIGEST_BEFORE,
                 "digest_after": DIGEST_AFTER, "digest_after_note": "computed by this builder from the landed methodology.json (the whole serialised change: D4, TL10.5, CP-1C D8, the CP-1D and CP-2A id drops); the c19be178... of the pre-landing text covered D4 and TL10.5 only and was not final",
                 "rule": "sha256 of json.dumps(rows, sort_keys=True, separators=(',', ':')) with the CP-1B table_ids popped; the digest changes because of the serialised methodology.json change (computed by this builder from the pinned methodology.json)",
                 "action": "the pin is recomputed from methodology.json after the whole serialised change (not from D4 and TL10.5 alone) and updated in the same commit, a deliberate registry change; the test fails otherwise"},
    "methodology_pinning_builders": {
        "rule": "each asserts the methodology.json sha256 348fbc4b... and refuses after the edit. The build commit updates every pin in ONE re-pin pass (the serialised change with CP-1C D8), rebuilds each builder and compares: expected.json and submissions.json byte-identical; manifest.json differs only in the methodology pin value wherever the builder records it (key-limited diff). Any other output change goes back to LEAD (byte-identical manifest.json cannot hold: each builder writes the pin into it)",
        "files": [{"file": "cases/cp1c-owner/builder/build.py", "locate": GREP_LOCATE, "tracked": "untracked in this worktree (still moving)"},
                  {"file": "cases/cp1d-owner/builder/build.py", "line": 36, "tracked": "tracked; line re-grepped for revision 4"},
                  {"file": "cases/cp2e-owner/builder/build.py", "line": 31, "tracked": "tracked, frozen at ac82330; asserted at :60; line re-grepped for revision 4"},
                  {"file": "cases/cp2g-owner/builder/build.py", "locate": GREP_LOCATE, "tracked": "untracked in this worktree (still moving)"},
                  {"file": "cases/cp3-cp6-owner/builder/build.py", "line": 31, "tracked": "tracked; line re-grepped for revision 4"},
                  {"file": "cases/cp3c-owner/builder/build.py", "locate": GREP_LOCATE, "tracked": "untracked in this worktree (still moving)"},
                  {"file": "cases/cp3d-owner/builder/build.py", "line": 34, "tracked": "tracked; line re-grepped for revision 4"},
                  {"file": "cases/cp8-owner/builder/build.py", "locate": GREP_LOCATE, "tracked": "untracked in this worktree (still moving: the pin sat at :38 in revision 3 and at :45 when revision 4 grepped)"},
                  {"file": "cases/cpdr-owner/builder/build.py", "line": 30, "tracked": "tracked, re-pinned at e8ee084 after 0d and 0d(c); line re-grepped for revision 4 at that commit"},
                  {"file": "cases/cpos-owner/builder/build.py", "line": 25, "tracked": "tracked, re-pinned at e8ee084 after 0d and 0d(c); line re-grepped for revision 4 at that commit"}],
        "this_builder": {"file": "cases/cpl10-owner/builder/build.py",
                         "edits": "the build commit edits :30 (the pin) AND :51 (`assert CPL10[\"required\"] == [\"CP-0\"]` becomes [\"CP-0\", \"CP-1\"]); it fails at :51 as well as :30 after D4",
                         "sha256_before": "keep the literal 348fbc4b877e4f0351ecc238ea005adf815291b15a6267f263459203a08f8d45 in D4_SIDE_EFFECTS (a literal, independent of PINS, so re-striking the pin at :30 leaves it at the before-hash); the build commit also re-hashes the CP-L10 manifest.json"},
        "note": "seven builders pinned methodology.json in revision 2 (cp1d, cp3d, cpdr, cp3-cp6, cpos, cp2e, this one); revision 3 greps cases/*/builder/build.py again and finds cp1c-owner, cp8-owner, cp2g-owner and cp3c-owner too: ten other builders plus this one. Revision 4 (LEAD ruling on C2): the four untracked or still-moving builders carry no line number and are located by grep at build time; the six tracked builders keep their re-grepped line. cp2a, cp2d and cp4 mention methodology.json in prose only (no pin)",
    },
    "frozen_lease_headers": {
        "rule": "fifth side effect: the build commit amends these six frozen-lease headers and docs/INTEGRATION.md:969 under a LEAD note (the builder pin and the methodology hash they name change with the serialised methodology change)",
        "files": [{"file": "docs/CP1D-OWNER-LEASE.md", "line": 3, "names": "builder 037b3e9d... / manifest 842ced20...; line 27 names methodology.json 348fbc4b...8d45"},
                  {"file": "docs/CP2E-OWNER-LEASE.md", "line": 3, "names": "builder 06f6ee61... / manifest 5b5a5e53... (frozen at ac82330); line 42 names methodology.json 348fbc4b...8d45; its line 5 note (3) already announces this re-pin"},
                  {"file": "docs/CP3D-OWNER-LEASE.md", "line": 3, "names": "pins dee1a8... and 592444..."},
                  {"file": "docs/CP3-OWNER-LEASE.md", "lines": "286-289", "names": "manifest 2cb324be... / builder 80450c52..."},
                  {"file": "docs/CPOS-OWNER-LEASE.md", "line": 3, "names": "the CP-OS header as amended by the 0d re-pin (landed at e8ee084; its re-pin paragraph at :5 carries the current builder and manifest pins, which supersede the 68c15d6e... / 50a447... pair of :3). LEAD supplies the post-re-pin hashes; none is copied here"},
                  {"file": "docs/CPDR-OWNER-LEASE.md", "line": 3, "names": "the CP-DR header as amended by the 0d re-pin (landed at e8ee084; its re-pin paragraph at :7 carries the current builder pin, which supersedes the 11fc8db6... of :3; the :5 note already announces this methodology re-pin). LEAD supplies the post-re-pin hashes; none is copied here"},
                  {"file": "docs/INTEGRATION.md", "line": 969, "names": "the methodology.json hash 348fbc4b...8d45"}],
        "note": "the build commit re-pins, so each header's builder/manifest hash after the re-pin is struck from the rebuilt files (a methodology pin change alters the builder bytes and, where the manifest records the pin, the manifest bytes); no post-0d-re-pin hash is written here for CP-OS or CP-DR (LEAD supplies them)",
    },
    "reuse_manifest": {"file": "docs/reuse/manifest.json", "action": "append one entry for src/deploy_vii/methodology.json to the end of `local_patch_lineage` (new sha256, the D12 one-line registration reason, review pointer); the previous hash 348fbc4b... is at lines 1063-1069 (not a position to insert after)"},
    "run_behaviour": {
        "plan": {"plan(('CP-L10',))": [["CP-0", "CP-L10"], ["CP-0", "CP-1", "CP-L10"]], "plan(('CP-L20',))": [["CP-0", "CP-L10"], ["CP-0", "CP-1", "CP-L10"]],
                 "plan(('CP-L10','CP-5'))": [["CP-0", "CP-L10", "CP-5"], ["CP-0", "CP-1", "CP-L10", "CP-5"]]},
        "edge_rule('CP-L10','CP-1')": ["raises ValueError 'No dependency edge from CP-1 to CP-L10'", "block"],
        "required_by_other_modules": "no module lists CP-L10 as a required or optional input, before or after; edge_rule('CP-5','CP-L10') stays restricted",
        "idle_statuses": "CP-1 is in scope and unrun for a run that requests CP-L10 (in-scope unrun: CP-0, CP-L10 -> CP-0, CP-1, CP-L10)",
        "readiness_live_consumers": "live_consumers(pack) for a run requesting CP-L10: ('CP-L10',) -> ('CP-1', 'CP-L10'); the CP-0 review must assess CP-1 as well as CP-L10 (a CP-L10-only review is refused 'Assess each selected canonical live consumer exactly once')",
        "cp1_workflow_consumer_entries": "CP-1's readiness stage now requests the CP-L10 entry (cp1_workflow.consumer_entries), routed to consumer_specific_review with requirement consumer_specific_cp1_sufficiency; before the edit CP-1 ran with no CP-L10 request",
        "front_page_cp1_blocks": "model-chart-strip, capital-structure, financials-credit-metrics: on the committed report_view (sha256 51a6853e...0e12) CP-1 is a credit_snapshot preset module, so under the CP-L10 override these read not_run `Not run: CP-1 was not requested in this run.` without D4, not_run `Not run: CP-1 has not run.` with D4 and CP-1 unrun, populated once CP-1 settles; render probe in expected.rendered",
        "unaffected": "business_context.py:351 (read by review-precise-1: unaffected)",
    },
}

REFUSED_RUN = {"run_id": "cpl10-owner-refused", "issuer_id": "northbridge-synthetic", "issuer_name": "Northbridge Synthetic Group", "as_of": "2026-01-10",
               "method_version": "deploy-v-r14", "case_kind": "synthetic", "pathway": "credit_snapshot", "requested_modules": ["CP-L10"]}

# --- 8. manifest, submissions, expected -------------------------------------------------------


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cases = {n: composed_case(n) for n in ("positive", "limited")}
    pos = cases["positive"]
    # hand-checked anchors (independent of the rule code above)
    t = {x["topic_id"]: x for x in pos["topics"]}
    assert t["cash"]["materiality"] == "Material" and t["cash"]["change_pct_fraction"] == "3/13"
    assert t["total_debt"]["materiality"] == "Watch" and t["total_debt"]["change_pct_fraction"] == "3/37"
    assert all(t[k]["materiality"] == "Stable" for k in ("ebitda", "fcf", "net_debt"))
    assert all(t[k]["materiality"] == "Not assessed" for k in ("total_leverage", "interest_coverage"))
    assert [t[k]["rank"] for k in TID] == [5, 6, 1, 2, 7, 3, 4]
    lim = {x["topic_id"]: x for x in cases["limited"]["topics"]}
    assert lim["cash"]["change_pct_fraction"] == "1/14" and lim["cash"]["materiality"] == "Watch"
    assert lim["total_debt"]["materiality"] == "Stable" and lim["total_leverage"]["from"]["status"] == "missing"
    refs = refusals()
    manifest = {
        "schema_version": "cpl10-owner-cases/1",
        "scope": "CP-L10 (aliases CP-L20, CP-L23, CP-L30, CP-L40) financial change screen: CP-0 to CP-1 to CP-L10 over the frozen financial pack",
        "status": "AMENDMENT 1 of the frozen revision 4 (LEAD rulings F1-F5 of 2026-10-28, work/lead/cpl10-owner-preparation/amendment-1-rulings.md); scoped review pending; not executed; build-first (no test run)",
        "raw_rule": "Literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (same rule as cases/financial/manifest.json)",
        "inputs_pinned": PINS,
        "financial_baseline": {"path": "cases/financial/manifest.json", "sources": [
            {"source_id": s, "sha256": SRC[s]["sha256"], "reuse": "Every page text and locator byte-identical; read by reference, never edited"} for s in ("identity", "financial")]},
        "no_new_source": "CP-L10 reads only the settled CP-1 head; the financial pack carries every operand, so no synthetic source and no synthetic peer is added. One issuer is screened for change between periods, not against peers.",
        "d4_edge_change": {"file": "src/deploy_vii/methodology.json", "module": "CP-L10",
                           "required_before": ["CP-0"], "required_after": CPL10["required"],
                           "optional_after": [], "edge_rule": "CP-1 -> CP-L10 block (registry.edge_rule default for a required producer)",
                           "plan_L10": D4_PLAN, "cp1b": "not added: v1 reads no CP-1B fact (reading nothing would not be consumption); see lease question 3",
                           "lands_with": "landed in the serialised methodology.json change, together with every side effect below (re-pin pass, test pin, reuse manifest entry)",
                           "side_effects": D4_SIDE_EFFECTS},
        "run": {"run_id": "cpl10-owner-positive", "issuer_id": "northbridge-synthetic", "issuer_name": "Northbridge Synthetic Group",
                "as_of": "2026-01-10", "method_version": "deploy-v-r14", "case_kind": "synthetic", "pathway": "credit_snapshot",
                "requested_modules": ["CP-L10"]},
        "cases": {
            "positive": {"submission": "submissions.json positive", "expected": "expected.json cases.positive", "pair": pair_json(POS_PAIR),
                         "execution": "closed run: CP-0, CP-1 (five stages, readiness = submissions.json cp1_downstream_review), CP-L10"},
            "limited": {"submission": "submissions.json limited", "expected": "expected.json cases.limited", "pair": pair_json(LIM_PAIR),
                        "execution": "same settled CP-0 and CP-1 heads (clone before CP-L10 begins); the pair has no known ratio at either end"},
            "refused": {"run": REFUSED_RUN, "pack": "financial source missing: no pages/hash, extraction blocked, limitation 'Quarterly financial statements were not supplied.' (cases/financial/manifest.json negative_case)",
                        "submission": "submissions.json refused.cp0_consumer_row_cp1, refused.cp0_consumer_row_cpl10, refused.gap_row (no CP-L10 submission exists)", "expected": "expected.json refused",
                        "execution": "CP-0 only; CP-1 begin raises NotAuthorized (RefusedBegin for CP-1, kind not_authorized); CP-L10 is never begun"},
            "blocked": {"expected": "expected.json blocked", "execution": "closed run: CP-0, CP-1 as positive, then CP-L10 attempt 0 invalid (rejected: refusals r01) and attempt 1 invalid (blocked: refusals r08)"},
        },
        "fact_selection_rule": {
            "table_id": "T4.10",
            "predicate": "fact.table_id == 'T4.10' and fact.label == '<column> · <metric>'; exactly one fact per (column, metric) or the operand is refused as unbound (zero or several matches are not zero or first-wins)",
            "columns": {k: {"label": v[0], "period": v[1]} for k, v in QUARTERS.items()},
            "metrics": {t[0]: t[1] for t in TOPICS},
            "observed": "Q1, Q2, Q3 and Q4 columns on the real promoted CP-1 head (copy of the S1 positive head, 500 T4.10 facts, no duplicate label; review-precise-1 and the revision-2 probe): ebitda source; fcf calculated; cash_closing source; total_debt source; net_debt calculated; every fact has a `canonical-kpi:` calculation_id; every MILLIONS fact has currency USD and scale 1000000; Q1-Q3 ratio facts status missing, value_class calculated, limitation 'COMPONENT_MISSING; Four complete contiguous quarters spanning 364-371 days are required'; Q4 total_leverage_reported 1.6666666666666666666666666666666666667 and interest_coverage_reported 6, value_class calculated",
            "inferred_not_observed": "none: every copied cell (value_class, status, amount, unit, period) was read from the real head",
            "fact_ids": "interface-fact:<sha256>; bound at run time, never literal",
        },
        "run_time_bindings": {
            "cp1_readiness": {"literal": "submissions.json cp1_downstream_review",
                              "routing": "CP-L10 is not in downstream_readiness._DEPENDENCIES (:27-39), so the entry routes to `consumer_specific_review`, requirement `consumer_specific_cp1_sufficiency`; the dependency requirements `cash_flow_metrics` and `liquidity_data` are unknown for CP-L10 and refused",
                              "markers": {"{{INPUTS_SHA256}}": "content hash of the step's prefilled DownstreamInputs (consumers replaced by the CP-L10 request)",
                                          "{{EVID:kpi <K>, quarter <N>}}": "evidence_id of the FIRST catalogue record (catalogue order) of kind `kpi` whose record_json key is <K> (ebitda, fcf, cash_closing, total_debt, net_debt) and whose non-empty value.observation_ids all end in `-q<N>-2025`; a record whose observation ids include a later LTM match (Q4 cash, total debt, net debt) is selected by the Q4 observation, not the LTM one. 20 ids: N = 1..4 outer, K in that order inner",
                                          "{{ALL narrative gap ids}}": "every narrative.gaps[*].gap_id, in catalogue order"},
                              "validator_result": "validate_downstream_review: no issues; _assess_consumers row CP-L10 ready_with_limitations, 0 unassessed requirements, 0 unassessed gaps, no blocking gap; probed by review-precise-1 and re-run in revision 2 on this literal with markers bound (revision-2.md)"},
            "cp1_calculation_id": {"marker": "{{CP1_CALCULATION_ID}}", "rule": "a copied TL10.2 cell carries the calculation_id of the CP-1 T4.10 fact named by copied_from_cp1 (canonical-kpi:<sha256>), read at run time; never literal"},
            "tl10_1_scope_status": {"rule": "TL10.1 `scope_status` = the bound head's status word as `report_view.module_display` spells it (restricted reads `With limitations`); no literal",
                                    "markers": {"{{CP0_STATUS_WORD}}": "the CP-0 head's word", "{{CP1_STATUS_WORD}}": "the CP-1 head's word"},
                                    "closed_run": "both heads settle restricted, so both read `With limitations` (navigator d4_cp1_settled); the test compares against the run, not this note"},
            "tl10_1_source_ref": {"rule": "TL10.1 `source_ref` = `<module>:<result_sha256>`: the bound head's module id and its result sha256; no literal",
                                  "markers": {"{{CP0_RESULT_SHA256}}": "the CP-0 head's result_sha256", "{{CP1_RESULT_SHA256}}": "the CP-1 head's result_sha256"}},
            "claim_citations": {"rule": CLAIM_CITATION_RULE,
                                "marker": "{{CP1_CITATIONS:<CP-1 T4.10 label>}}: the citations of that CP-1 fact, bound at run time; each claim lists its markers in first-reference order, de-duplicated"},
            "inherited_limitations": "execution.py settle rule (execution.inherited_limitations)",
            "ticket_and_call_ids": "structural only",
        },
    }
    submissions = {
        "schema_version": "cpl10-owner-submissions/1",
        "note": "Literal analyst submissions for the screen step. Digit-free, no reference syntax; every figure in the module is Python's. CP-0 and the five CP-1 stages are reused unchanged from tests/test_financial_workflow.py except for the CP-0 consumer row below and the CP-1 readiness stage (cp1_downstream_review).",
        "cp0_consumer_row_cpl10": {
            "module_id": "CP-L10", "readiness": "READY_WITH_LIMITATIONS",
            "evidence_demand": "Settled CP-1 figures for two quarters of one fiscal year",
            "source_ids": ["identity", "financial"],
            "rationale": "The change screen can run on settled CP-1 quarter figures with inherited source and scope limitations.",
            "citations": [
                {"source_id": "identity", "source_sha256": SRC["identity"]["sha256"], "locator": "page:1",
                 "quote": "Northbridge Synthetic Group is the issuer and consolidated group."},
                {"source_id": "financial", "source_sha256": SRC["financial"]["sha256"], "locator": "page:1",
                 "quote": "Currency: USD; amounts in millions."}],
            "missing_source": None,
            "limitations": ["Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."],
        },
        "cp1_downstream_review": CP1_DOWNSTREAM_REVIEW,
        "refused": {"cp0_consumer_row_cp1": REFUSED_CP1_ROW, "cp0_consumer_row_cpl10": REFUSED_CPL10_ROW, "gap_row": REFUSED_GAP_ROW},
        "positive": SUBMISSIONS["positive"],
        "limited": SUBMISSIONS["limited"],
        "refusals": [{k: v for k, v in r.items() if k not in ("expected_issues", "issue_spelling")} for r in refs],
        "blocked": {"attempt_0": "refusals r01", "attempt_1": "refusals r08"},
    }
    expected = {
        "schema_version": "cpl10-owner-expected/1",
        "derivation": "Hand-transcribed rules of work/lead/cpl10-owner-preparation/lease-draft.md applied to the frozen financial pages with exact Fractions; cross-checked with decimal prec 38 ROUND_HALF_EVEN. No product code was imported or run by this builder; copied CP-1 cell classes were read from the real head by review probes (manifest.fact_selection_rule.observed).",
        "cell_notation": {
            "shown": "exact displayed text (report_view.fact_spelling); amounts decimals 2 (value cells MILLIONS, US$), percent 1 dp, multiple 2 dp, counts and rank 0 dp; a missing cell is `∅ G#` and a not_applicable cell is `∅ G# n.m.` (G# is the report-wide gap number bound at run time)",
            "currency_scale": "every fact with unit MILLIONS carries currency `USD` and scale `1000000` (CP-1's facts do); a MULTIPLE or PERCENT fact carries no currency and the default scale 1 (as CP-1's ratio facts)",
            "calculation_id": "a calculated own fact: `calc:<fact_id>`; a copied CP-1 cell: the marker `{{CP1_CALCULATION_ID}}`, the CP-1 fact's own canonical-kpi id bound at run time (every CP-1 T4.10 fact has one, source-class and missing ratio facts too); analyst and text-only cells: null",
            "amount_exact": "canonical exact decimal; null means unsettled",
            "status": "known | missing | not_applicable",
            "value_class_basis": "observed on the real CP-1 head for every copied cell (manifest.fact_selection_rule); a missing ratio fact keeps value_class `calculated`",
            "derives_from": "the CP-1 T4.10 labels a calculated fact derives from",
            "table_shape": "every table of every case has one fact per column in every row, fact id <table>.<row>.<field> in column order (contracts.py:270-272, validate_tables); `tables[].columns` pins the order of the field names only; column labels are the product's and are not pinned; the builder asserts the shape for every table of both cases",
            "not_applicable_text_cell": "a text cell with no meaning for its row (the TL10.3 overall row's evidence, credit_transmission, screening_implication and source_refs): status not_applicable, shown `\u2205 G# n.m.`, limitation `Not applicable to the overall row`, no value class, no calculation id",
            "run_bound_cells": "TL10.1 scope_status and source_ref carry a marker, never a literal (manifest.run_time_bindings.tl10_1_scope_status, tl10_1_source_ref)",
        },
        "rules": {
            "thresholds": {"material_at_or_above": "1/10", "watch_at_or_above": "1/20", "basis": "|closing - starting| / |starting| of CP-1 facts; screening-policy literals (D11) that no source states, stated in methods/cpl10.md with an own limitation, never presented as sourced",
                           "exact_comparison": "rated on the exact value, never on the rounded quotient or the shown percentage: Material iff abs(closing - starting) * 10 >= abs(starting); Watch iff abs(closing - starting) * 20 >= abs(starting); one rule for amounts and multiples; fixtures.composer pins the boundaries (99/2000 shows 5.0% yet is Stable)"},
            "zero_base": "starting value 0: change 0 -> Stable; change != 0 -> Material with change_pct not_applicable (never infinity, never 0)",
            "missing": "either end missing -> change and change_pct missing (CP-1's limitation kept), materiality Not assessed, evidence Missing, disposition Evidence needed; never 0",
            "rank": "Material, Watch, Not assessed, Stable; inside a class larger |change on starting level| first (zero-base Material first); then register order",
            "disposition": DISPOSITION,
            "topics": [{"topic_id": t[0], "cp1_metric": t[1], "label": t[2], "unit": t[4], "upgrade_module": TARGET[t[0]]} for t in TOPICS],
            "target_titles": TARGET_TITLE,
            "sign": "change = closing - starting (signed); change_pct = change / |starting| (signed)",
            "assessment_rule": "exactly one analyst assessment for each topic Python rates Material or Watch; none for Stable or Not assessed",
            "overall_rule": {"confidence_high": "High is refused for every confidence, the overall's included (r07 pins the assessments[0] spelling `<path>.confidence: High is not allowed in a screen`)",
                             "insufficient_information_pairing": "overall.confidence is Insufficient Information iff overall.category is Insufficient Information (r13; issue `overall.confidence: must be Insufficient Information exactly when the category is`)",
                             "limitation": "an Insufficient Information overall (category) carries a non-null limitation (r14; `overall.limitation: an Insufficient Information overall states its limitation`); a category other than Insufficient Information forbids one (r15; `overall.limitation: only an Insufficient Information overall carries a limitation`); the CP-3C precedent, keyed on the category",
                             "issue_order": "confidence High, then pairing, then limitation required, then limitation forbidden",
                             "literal_consequence": "cases.limited.overall.limitation is null (it was a sentence on a Low-confidence Analyst Interpretation overall, which the forbidden-limitation rule now refuses)"},
            "gaps_rule": {"topic": "each gap's `affected_analysis` equals a topic_id of the view or `overall` (r16; `gaps[<i>].affected_analysis: must name a topic of the view or overall`)",
                          "missing_item": "each gap's `gap` (the missing item) is non-empty after trimming (r17; `gaps[<i>].gap: empty`)",
                          "no_digit": "no gap text field (gap, why_it_matters, affected_analysis, action) contains a digit (r18; `gaps[<i>].<field>: must not contain a digit`)",
                          "duplicates": "a gap with the same `affected_analysis` and `gap` text as an earlier gap is refused (r19; `gaps[<i>]: repeated gap`)",
                          "issue_order": "per gap in order: topic, missing item, digit (field order gap, why_it_matters, affected_analysis, action), repeat",
                          "literal_consequence": "the positive gap's affected_analysis is `overall` (it was `Earnings and cash generation topics`, which the topic rule now refuses; r16 reuses that text)"},
            "claim_citations": CLAIM_CITATION_RULE,
            "lineage_citations": "a calculated own fact's citations follow the same rule over its derives_from (the CP-1C L3 rule); a count fact has no derives_from, and a missing change or change_pct cell has none either, so a claim that references only counts or only a missing change carries no citations as the facts stand (a derives_from on those cells would be a fact-value change outside amendment 1)",
            "submission_types": {"note": "the field types decide shape versus content; pinned here, frozen with the lease",
                                 "comparison.from_period, to_period": "Text (contracts.Text: str, min_length 1)",
                                 "assessments[].topic_id, assessment, credit_transmission, overall.rationale, gaps[].*": "Text (contracts.Text); whitespace-only text passes the type and is a content refusal",
                                 "category": "business_context.Category", "confidence": "business_context.Confidence (admits High: High is a content refusal, as CP-2A)",
                                 "gaps[].severity": "business_context.Severity", "overall.limitation": "Text or null",
                                 "shape issues": "missing field, wrong type, empty string (min_length): `<dotted.path>: <pydantic message>`, returned alone"},
            "validation_order": ["shape (alone)", "comparison (an issue here ENDS validation: the ratings depend on the pair)", "assessments[] in submission order, then the missing-assessment check",
                                 "analyst text of every assessment and overall: bare figures and references through the product prose path against the module's bound facts (fact ids and unique calculation ids), prohibited conclusions, empty text", "overall (rules.overall_rule)", "gaps (rules.gaps_rule)"],
        },
        "cases": cases,
        "fixtures": {"composer": FIXTURES, "rank": FIXTURE_RANK},
        "refusals": [{k: r[k] for k in ("id", "class", "issue_kind", "issue_spelling", "expected_issues")} for r in refs],
        "refusal_rules": {
            "journal": "each refusal is one invalid CP-L10 step on attempt 0 of the positive CP-1 head; attempt 0 is re-begun; two failures settle the head blocked",
            "shape_vs_content": "shape issues are returned alone (`<dotted.path>: <pydantic message>`); content issues are `<bracketed[path]>: <issue>` in the order comparison, assessments, overall, gaps",
            "bare_figure": "r08's spelling is prose.check's `Bare figure: <token>` (probed)",
            "reference": "r09's spelling is prose.check's `Unresolved reference: <id>` (probed); an analyst reference that resolves against the module's bound facts is NOT refused. The reference check runs the product path against the facts the composer built for the submitted pair",
            "own_spelling": "every other content issue text is this draft's proposal (issue_spelling `this draft`), frozen when LEAD accepts the lease",
            "g1_level": "invoke is a refused not_permitted receipt; submit without read_inputs is not_permitted; a snapshot change between read and submit is stale_binding; begin with CP-1 blocked or missing is a RefusedBegin",
        },
        "blocked": blocked(refs),
        "refused": {
            "run": "manifest.cases.refused.run", "plan_order": D4_PLAN,
            "cp0": {"rows": ["submissions.json refused.cp0_consumer_row_cp1", "submissions.json refused.cp0_consumer_row_cpl10"], "gap_row": "submissions.json refused.gap_row",
                    "validator_issues": [], "settled_status": "restricted", "T8_commands": [["CP-1", "DO NOT RUN"], ["CP-L10", "DO NOT RUN"]],
                    "probe": "revision-2.md: validate_review and build_readiness on the missing-financial pack with D4 patched in memory"},
            "refused_begins": [{"module_id": "CP-1", "kind": "not_authorized", "reason": "CP-0 has not authorized this consumer's source readiness"}],
            "attempts": ["CP-0"], "heads": ["CP-0"],
            "cpl10": "never begun (G1 stops the walk after a RefusedBegin: owner_workflow._begin retains the refusal and ends the walk)",
            "model_publication": "not planned", "receipt": "verifies",
            "must_not_appear": ["a CP-L10 ticket, attempt, head or table", "a change of 0 standing for a missing one"],
        },
        "blocked_cp1_refusal": {
            "status": "lease statement for the build's test, NOT a frozen oracle case",
            "search": "tests/ holds no frozen blocked-CP-1 history for this pack: tests/test_source_tools.py legal_history(root, blocked=True) (lines 683-721) builds one in code on the LEGAL pack (CP-1 attempts 0 and 1, two invalid `source_context` submissions of '{}' each, result status blocked) inside the session fixture `legal_histories`; no tests/*.json fixture exists; tests/test_owner_workflow.py::test_rejected_then_blocked_walk_retains_refusal blocks CP-0, not CP-1",
            "expect": "CP-1 blocked -> store.begin('CP-L10') raises ValueError 'Required upstream is unrun, stale or blocked' (owner_workflow.BLOCKED_EDGE, :78) and a head with status blocked exists -> exactly one RefusedBegin for CP-L10, kind `blocked`, reason that text (owner_workflow._begin :447-456); CP-1 has attempts 0 and 1; no CP-L10 attempt, head or table; receipt verifies",
            "not_retained": "a missing CP-1 head with no blocked head raises (not a retained refusal; owner_workflow._begin re-raises), which is why the frozen `refused` case above is the CP-1-missing variant",
        },
        "execution": {
            "plan_order": D4_PLAN, "statuses": {"CP-0": "restricted", "CP-1": "restricted (financial precedent)", "CP-L10": "restricted: own limitations non-empty and the case is synthetic"},
            "tool_use": "submit only: every invoke is a refused not_permitted receipt; exactly one ok read_inputs (the module_context view) before the submit; zero pack calls",
            "inherited_limitations": "execution.py:345-366: CP-0 head limitations, then CP-1 head, own removed; bound at run time",
            "view_keys": ["upstream", "periods", "topics", "pair_screens", "rules", "inherited_limitations"],
            "view_expectation": "pair_screens equals cases.positive.view_pair_screens (the six offered pairs, Python materiality per topic); topics[].values equals cases.positive.view_topics (the CP-1 value of each quarter spelled by Python at 2 dp from the CP-1 amount, never CP-1's own 0 dp cell text; a missing value reads `∅ G#` with CP-1's limitation); no analyst-quotable evidence line; no free text from a source page",
            "settled_limitations": "cases.<case>.settled_limitations: the candidate's own limitations then `Synthetic case; not real issuer qualification` (execution.py:440-446), de-duplicated; own_limitations is the candidate's list",
        },
        "consumption": "OPEN: no consumer core reads CP-L10. registry.edge_rule('CP-5','CP-L10') is restricted (fan-in) but D3 counts CP-5 only after a lease extends its integrity scope and binds the CP-L10 head hash. cpl10_reader(store, head) pins what a consumer reads: status, per topic id/materiality/evidence/disposition/rank/change, counts.",
        "d8_table_ids": {"registered": [t for t in TL10 if t != TL10_NEW], "added_by_the_serialised_methodology_change": [TL10_NEW], "other_registered_in_entry": [t for t in CPL10["table_ids"] if not t.startswith("TL10.")],
                          "collision": "none: no other module's table_ids lists a TL10.x id and TL10.5 is unused anywhere (asserted above); TL20-TL40 belong to the CP-L10 entry too and are left unchanged",
                          "produced": TL10_PRODUCED, "placement": "TL10.5 (Screen totals) joins the evidence rail block of TL10.2 (D7)"},
        "rendered": {"block": None, "rails": {"evidence": ["TL10.1", "TL10.2", "TL10.5", "TL10.3"], "limitations": ["TL10.4"]},
                     "note": "no pathway lists CP-L10 and r14 has no Front Page block for it (architecture study section 4: screening, no block); rails only, as CP-DR",
                     "front_page_states": {
                         "method": "report_view.build over the credit_snapshot pathway with requested_modules ('CP-L10',) and registry.modules patched in memory for D4 (never written under src/); re-probed in revision 3 on the committed product after 0d (41a8fdb) and 0d(c) (b4ae187) (docs/reviews/0d-product-defects.md); the CP-L10 rail population is not probed (no bindings exist)",
                         "probed_report_view_sha256": "51a6853ec0e80393a50cdf8ed577cddaf2eee8e26246609b85dea01712560e12",
                         "rule": "a preset module the override excludes (in registry.dependencies(PATHWAY_MODULES[run.pathway]) but not_in_pathway) reads `Not run: <modules> was not requested in this run.`, state not_run, call_withheld not_requested; a module outside the pathway's closure keeps `Not in this Pathway: <module> is not part of <Pathway>.`, state not_in_pathway",
                         "call": {"call_withheld": "not_requested", "call": "Assessment pending"},
                         "blocks_not_run_not_requested": {"key-findings": "Not run: CP-2 was not requested in this run.", "company-operating-model": "Not run: CP-1A was not requested in this run.",
                                                          "strengths-weaknesses": "Not run: CP-2 · CP-6 was not requested in this run.", "relative-value": "Not run: CP-3 was not requested in this run.",
                                                          "company-profile": "Not run: CP-1A was not requested in this run.", "committee-challenge": "Not run: CP-6 was not requested in this run."},
                         "blocks_not_in_pathway": {"what-changed": "Not in this Pathway: CP-8 is not part of Credit Snapshot."},
                         "blocks_absent": ["transaction-summary", "portfolio-fit"],
                         "cp1_blocks": ["model-chart-strip", "capital-structure", "financials-credit-metrics"],
                         "cp1_blocks_states": {"D4 not applied (today)": "not_run: Not run: CP-1 was not requested in this run.",
                                               "D4 applied, CP-1 unrun": "not_run: Not run: CP-1 has not run.",
                                               "D4 applied, CP-1 settled (restricted)": "populated"},
                         "navigator": {
                             "method": "report_view.navigator(view) and report_view.module_display(view) (0d(c), b4ae187) on the same three views as cp1_blocks_states: a fresh Execution with D4 off, a fresh Execution with D4 patched in memory (CP-1 unrun), and the settled CP-0/CP-1 store view with run.requested_modules set to ('CP-L10',) and registry.idle_statuses re-applied to its unrun and not_in_pathway modules (D4 on); probed in revision 4 on the committed product, written here as literals",
                             "probed_report_view_sha256": "51a6853ec0e80393a50cdf8ed577cddaf2eee8e26246609b85dea01712560e12",
                             "rule": "rows in registry order, 25 in every state (no rejected attempt); a module is numbered 1..N iff its status is not not_in_pathway, the rest are footer rows; a preset module (registry.dependencies(PATHWAY_MODULES['credit_snapshot'])) the CP-L10 override leaves out reads `Not run` (glyph unrun) in the footer, a module outside the closure reads `Not in this Pathway` (glyph na); module_display spells the same word for the module payload, so the CP-1 status word is `Not run` while CP-1 is not_in_pathway (without D4) or unrun (D4, before CP-1 runs) and `With limitations` once CP-1 settles restricted",
                             "footer_every_state": {"Not in this Pathway": NAV_OUTSIDE_CLOSURE, "Not run": NAV_PRESET_NOT_REQUESTED, "note": "without D4 the `Not run` footer group also holds CP-1 (eight modules); with D4 CP-1 is numbered"},
                             "states": NAV_STATES}}},
        "not_verified": [
            "no CP-L10 core, run, view, validator or bindings exists: no expected value was compared with product output of CP-L10",
            "the issue wording other than r08 and r09 is this draft's proposal",
            "the blocked-CP-1 RefusedBegin is a lease statement read from owner_workflow.py, not walked",
            "the CP-L10 rail population and the settled CP-L10 render states are not probed",
            "thresholds and the Material/Watch/Not assessed ranking are screening policy not stated in any source; LEAD confirms",
            "amendment 1: the issue wording of r13-r19 is this draft's proposal (the CP-3C pairing and limitation spellings adapted); the overall.confidence High spelling is pinned only for assessments[0] (r07)",
            "amendment 1: the run-bound markers (head result_sha256, status word, CP-1 citations) are bound by the test, not by this oracle; citation order across a claim's referenced facts is this draft's reading of first-reference order",
        ],
    }
    dump(OUT / "manifest.json", manifest)
    dump(OUT / "submissions.json", submissions)
    dump(OUT / "expected.json", expected)


if __name__ == "__main__":
    sys.exit(main())
