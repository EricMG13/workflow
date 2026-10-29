"""Stage 3 chart oracles, group A: S.5, RV.3, CR.1 and the populated FP 04 S.4 (stdlib only).

    python3 -I cases/charts/builder/build_a.py

Writes cases/charts/{s5,rv3,cr1,s4fp04}-expected.json deterministically (sorted keys, indent 2, one
trailing newline). Every number, text and fact id is read from the frozen module oracles named in
``SOURCES``. The only literals are form fields (titles, kinds, series captions, placement, units),
each with the design or brief line it comes from, and the display spelling rules of
src/deploy_vii/display.py (restated in ``spell`` and cross-checked against the oracles' own ``shown``
strings wherever an oracle has them). The oracle files are source-first: nothing here imports src/.
"""

import hashlib
import json
import pathlib
import re
import sys
from decimal import ROUND_HALF_UP, Context, Decimal

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "cases" / "charts"
SOURCES = {
    "financial": "cases/financial/manifest.json",
    "chart_s1_s4": "cases/charts/expected.json",
    "cp1c": "cases/cp1c-owner/expected.json",
    "cp2d": "cases/cp2d-owner/expected.json",
    "cp4": "cases/cp4-owner/expected.json",
}
DESIGN = "/Users/ericguei/Documents/DEPLOY VII/design/reference/"
BRIEF = "design pack content/"  # the design pack's content briefs (read only, outside git)
GAP = "∅ G#"  # the product gap spelling; the number is assigned report-wide at render
GAP_PATTERN = "∅ G\\d+"
CONTEXT = Context(prec=120, rounding=ROUND_HALF_UP)
STAMP = "independent-stage3-chart-expectations/1"
REVIEW_PHASE = "pre-implementation; independent of candidate renderer output"


def load(key):
    return json.loads((ROOT / SOURCES[key]).read_text(encoding="utf-8"))


def sha(key):
    return hashlib.sha256((ROOT / SOURCES[key]).read_bytes()).hexdigest()


def authority(keys, **form):
    return {
        "modules": [{"path": SOURCES[k], "sha256": sha(k)} for k in keys],
        "order_of_authority": "approved page decides appearance; pack brief decides provider and data path; inference last",
        "values": "settled module facts only; the pack sets form and owner, never numbers",
        **form,
    }


def spell(amount, unit_class):
    """display.py `_NUMERIC`: amount 0 dp, multiple 2 dp + x, percent 1 dp of x100 + %, ROUND_HALF_UP."""
    places, scale, suffix = {
        "amount": (0, 1, ""),
        "multiple": (2, 1, "x"),
        "percent": (1, 100, "%"),
    }[unit_class]
    rounded = CONTEXT.multiply(amount, Decimal(scale)).quantize(
        Decimal(1).scaleb(-places), context=CONTEXT
    )
    body = f"{rounded.copy_abs():,.{places}f}"
    return (f"({body})" if rounded < 0 else body) + suffix


def facts_of(module_case):
    return {f["fact_id"]: f for f in module_case["facts"]}


def table_labels(module_case, table_id):
    table = next(t for t in module_case["tables"] if t["table_id"] == table_id)
    return {row["row_id"]: row["label"] for row in table["rows"]}


def companion(fact):
    known = fact["status"] == "known"
    return {
        "fact_id": fact["fact_id"],
        "label": fact["label"],
        "shown": fact["shown"] if known else GAP,
    }


def point(series, category, fact, companions, unit_class):
    """One chart point from a settled module fact (`fact` is the module oracle's fact dict)."""
    known = fact["status"] == "known"
    if known and fact.get("amount_exact") is not None:
        assert spell(Decimal(fact["amount_exact"]), unit_class) == fact["shown"], fact["fact_id"]
    return {
        "series": series,
        "category": category,
        "fact_id": fact["fact_id"],
        "companion_fact_ids": [c["fact_id"] for c in companions],
        "state": "plotted" if known else "gap",
        "settled_status": fact["status"],
        "amount_exact": fact.get("amount_exact") if known else None,
        "shown": fact["shown"] if known else GAP,
        "gap_ref_pattern": None if known else GAP_PATTERN,
        "gap_reason": None if known else fact.get("limitation"),
        "companions": [companion(c) for c in companions],
    }


def twin(points):
    """Exact table twin: one row per point, in point order; cell text equals the mark text."""
    rows = []
    for index, p in enumerate(points):
        parts = [f"{p['series']} · {p['category']}"]
        parts += [f"{c['label']}: {c['shown']}" for c in p["companions"]]
        rows.append({"row": index, "label_parts": parts, "cell": p["shown"]})
    return {
        "columns": ["Value"],
        "rows": rows,
        "rule": "label = ' · '.join(label_parts) with a run-time ' [ref]' suffix after a companion that has a report reference; cell texts equal the mark texts in order",
    }


def gaps_of(points):
    return [
        {
            "series": p["series"],
            "category": p["category"],
            "fact_id": p["fact_id"],
            "reason": p["gap_reason"],
        }
        for p in points
        if p["state"] == "gap"
    ]


def write(name, document):
    text = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    (OUT / name).write_text(text, encoding="utf-8")


# --- S.5 -----------------------------------------------------------------------------------------

PERIOD_FIELDS = (  # src/deploy_workflow/financial_series.py:46-49 `_PERIOD_FIELDS`
    "period_id",
    "period_type",
    "fiscal_year",
    "fiscal_quarter",
    "start_date",
    "end_date",
    "currency",
    "unit",
    "accounting_basis",
    "entity_perimeter",
)


def basis_id(period_id):
    """financial_series._basis (:99-111): length-prefixed ('historical', 'Q:<period id>'), sha256."""
    parts = ("historical", f"Q:{period_id}")
    return (
        "model-basis:"
        + hashlib.sha256("".join(f"{len(p)}:{p}" for p in parts).encode()).hexdigest()
    )


def build_s5():
    manifest = load("financial")
    chart = load("chart_s1_s4")
    observed = manifest["quarter_observations"]
    quarters = [p for p in manifest["periods"] if p["period_type"] == "QUARTER"]
    assert [p["period_id"] for p in quarters] == [q["period_id"] for q in chart["quarters"]]
    assert len(quarters) == 4 and manifest["source_dimensions"]["unit"] == "MILLIONS"
    ltm = manifest["q4_ltm_derived_source_units"]
    for key in ("revenue", "adjusted_ebitda"):  # the four quarters sum to the LTM and FY2025 totals
        assert sum(Decimal(observed[key]) for _ in quarters) == Decimal(ltm[key])
        assert Decimal(manifest["fy2025_observations"][key]) == Decimal(ltm[key])
    # Series captions: pack charts.revenueEbitda.series[].label (rbot-data-base.json).
    captions = (("revenue", "Net revenues"), ("adjusted_ebitda", "Adjusted EBITDA"))
    points = []
    for key, caption in captions:
        for q in quarters:
            amount = Decimal(observed[key])
            points.append(
                {
                    "series": key,
                    "caption": caption,
                    "category": f"Q{q['fiscal_quarter']} {q['fiscal_year']}",  # producer rule financial_series.py:176
                    "fact_coordinate": {
                        "module": "CP-1",
                        "table_id": "T4.10",
                        "row_key": {"field": "field_1", "text": key},
                        "value_field": basis_id(q["period_id"]),
                        "period_dates": f"{q['start_date']} to {q['end_date']}",
                        "unit": "MILLIONS",
                        "currency": "USD",
                        "scale": "1000000",
                        "basis": "IFRS · consolidated group",
                    },
                    "fact_id_rule": "run-time id of the one T4.10 fact at (row field_1 = row_key.text, value_field); zero or several fail",
                    "companion_coordinates": [
                        {"table_id": "T4.10", "row_key": key, "field": "field_1"},
                        *(
                            {"table_id": "T4.14", "period_id": q["period_id"], "field": f}
                            for f in PERIOD_FIELDS
                        ),
                    ],
                    "state": "plotted",
                    "amount_exact": str(amount),
                    "shown": spell(amount, "amount"),
                }
            )
    record = {
        "fig_id": "S.5",
        "title": "Net revenues and Adjusted EBITDA",
        "kind": "grouped",
        "unit_class": "amount",
        "unit": "US$m",
        "series": [k for k, _ in captions],
        "series_captions": dict(captions),
        "points": points,
        "reason": None,
    }
    twin_input = [{**p, "series": p["caption"], "companions": []} for p in points]
    return {
        "schema_version": STAMP,
        "review_phase": REVIEW_PHASE,
        "figure": "S.5",
        "source_authority": authority(
            ("financial", "chart_s1_s4"),
            design={
                "file": DESIGN + "rbot-fp-01-credit-snapshot.dc.html",
                "lines": "66 (figure S.5 caption), 124 (`C.columns` on charts.revenueEbitda), 60 (block head: MODEL, US$ m)",
            },
            brief={
                "file": BRIEF + "01-credit-snapshot.md",
                "line": 36,
                "text": "charts.revenueEbitda",
            },
            fact_tables="T4.10 rows `revenue` and `adjusted_ebitda` (CP1B-ACCESS-LEASE.md:56 A1 measure rows), the same T4.10/T4.14 join as S.1 to S.3. T4.5 is the cash-flow statement and holds neither measure",
            source_locators={
                "quarter_values": "cases/financial/manifest.json:128-133 quarter_observations; :176-186 q4_ltm_derived_source_units; :1948-1953 fy2025_observations"
            },
        ),
        "form": {
            "kind": "grouped columns, two series (design: C.columns on charts.revenueEbitda)",
            "title": "design :66 / pack charts.revenueEbitda.title",
            "series_captions": "pack charts.revenueEbitda.series[].label",
            "unit": "US$m is the producer literal (financial_series.py); the design prints 'US$ m'",
            "placement": "beside (design :66 puts the figure in the right column of the period table)",
            "categories": "four reported QUARTER periods, producer rule (financial_series.py); inference, see scope_limits",
            "summary": "none: the design's summary sentence carries numbers that are not settled facts",
            "provider": "owner MODEL, producers (CP-1,) as report_view.py:1102-1108",
        },
        "chart_series": [record],
        "table_twin": {"S.5": twin(twin_input)},
        "gap_marks": {
            "rule": "a nonknown or missing T4.10 fact is a gap mark with its G# reference, never 0; a known 0 is plotted",
            "in_positive_case": [],
        },
        "adversarial_cases": [
            {
                "case": "tables",
                "expected": "Revenue and adjusted EBITDA are read from T4.10, never from T4.5 (cash-flow statement) or T4.4; a point whose fact is not T4.10 fails.",
            },
            {
                "case": "quarter_count",
                "expected": "Fewer or more than four reported QUARTER periods: reason set, no points, no interpolation; the same rule as S.1 to S.3.",
            },
            {
                "case": "fy_ltm_aliasing",
                "expected": "FY2025 (120 and 30) and LTM Q4 25 are equal in value and share an end date; neither is drawn as a fifth category, and the four quarters never sum into a drawn total.",
            },
            {
                "case": "display_rounding",
                "expected": "Adjusted EBITDA is exactly 7.5 per quarter and is spelled '8' (display.py 0 dp ROUND_HALF_UP); the mark carries the exact 7.5, the twin text '8'; no chart value is recomputed from the spelling.",
            },
            {
                "case": "nonknown_measure",
                "expected": "A missing revenue or adjusted_ebitda quarter is a gap mark with a G# reference and a twin cell '∅ G#', never 0, and the other series keep their marks.",
            },
            {
                "case": "missing_financial_source",
                "expected": "No CP-1 head: no S.5, the block keeps its table; no zero fill (same refusal as cases/charts/expected.json missing_financial_source).",
            },
            {
                "case": "foreign_currency_or_scale",
                "expected": "A revenue or adjusted_ebitda fact that is not USD MILLIONS scale 1000000 IFRS consolidated group fails closed (financial_series._numeric).",
            },
        ],
        "scope_limits": [
            "Synthetic frozen Northbridge case: four quarters and FY2025; the design's FY2023 to LTM Q2 2026 four-period axis cannot be drawn (no prior-year income statement: financial source page:1).",
            "FY2025 and LTM Q4 25 are not drawn: same value and end date as Q4's trailing basis (adversarial case fy_ltm_aliasing). Raised as a question.",
            "No segment or growth series; no summary sentence.",
        ],
        "render": {
            "pathway": "credit_snapshot",
            "block_id": "financials-credit-metrics",
            "owner": "MODEL",
            "producers": ["CP-1"],
            "kind": "period_grid",
            "state": "populated",
            "figures": [{"fig_id": "S.5", "placement": "beside", "summary": None}],
            "tabs": "unchanged: the CP-1 registers bound to this block (bindings/cp1.py:41-50)",
            "other_blocks": "model-chart-strip keeps S.1 to S.4 unchanged; metric-strip (FP 02) is not given S.5",
        },
        "builder_targets": [
            {
                "test_file": "tests/test_financial_series.py",
                "assert": [
                    "cp1_chart_series (or a second producer function, Modules decides) returns S.5 after S.4 with kind 'grouped', unit_class 'amount', unit 'US$m', series ('revenue', 'adjusted_ebitda') and the 8 points of chart_series[0].points, in series-then-quarter order",
                    "each point's fact is the one T4.10 fact at (field_1 text, basis_id(quarter)); companions are the field_1 fact and the ten T4.14 period facts of the same QUARTER row",
                    "a T4.10 fact that is not USD MILLIONS scale 1000000 raises ValueError; a nonknown fact stays a point (gap), never a zero",
                ],
            },
            {
                "test_file": "tests/test_cp1_chart_render.py",
                "assert": [
                    "report_view.build on a credit_snapshot run: block 'financials-credit-metrics' has figures [S.5] with placement 'beside', owner 'MODEL', kind 'period_grid', and its tabs unchanged",
                    "mark values of the revenue series == [Decimal('30')] * 4 and of adjusted_ebitda [Decimal('7.5')] * 4; mark texts '30' and '8'; table twin cell texts equal mark texts in order",
                    "a gap fact renders '∅ G<n>' with ref_id 'G<n>' and value None; the other series keep their marks",
                    "S.1 to S.4 in model-chart-strip are unchanged (regression)",
                ],
            },
        ],
    }


# --- RV.3 ----------------------------------------------------------------------------------------

METRICS = (  # brief 03:36 and T1C.3 field order
    "adjusted_ebitda_margin",
    "total_leverage_adjusted",
    "interest_coverage_adjusted",
    "ffo_to_debt",
)
PANELS = (  # one unit class per panel (ChartSpec has one unit_class; Q-C8 precedent: never mixed on one axis)
    ("percent", "%", ("adjusted_ebitda_margin", "ffo_to_debt")),
    ("multiple", "x", ("total_leverage_adjusted", "interest_coverage_adjusted")),
)


def rv3_case(case):
    facts = facts_of(case)
    names = table_labels(case, "T1C.1")
    peers = [p for p in names if facts[f"T1C.1.{p}.included"]["shown"] == "Included"]
    excluded = [p for p in names if p not in peers]
    panels = []
    for unit_class, unit, metric_keys in PANELS:
        points = []
        for series, role in (("Issuer", "issuer"), ("Peer median", "median"), ("Peers", "peer")):
            for m in metric_keys:
                caption = facts[f"T1C.3.issuer.{m}"]["label"]
                if role == "issuer":
                    row = [
                        (
                            f"T1C.3.issuer.{m}",
                            caption,
                            [f"T1C.5.issuer.{m}_flag", f"T1C.4.{m}.direction"],
                        )
                    ]
                elif role == "median":
                    row = [(f"T1C.4.{m}.median", caption, [f"T1C.4.{m}.direction", f"T1C.4.{m}.n"])]
                else:
                    row = [
                        (
                            f"T1C.3.{p}.{m}",
                            f"{caption} · {names[p]}",
                            [f"T1C.1.{p}.included", f"T1C.5.{p}.{m}_flag"],
                        )
                        for p in peers
                    ]
                for fact_id, category, companion_ids in row:
                    points.append(
                        point(
                            series,
                            category,
                            facts[fact_id],
                            [facts[c] for c in companion_ids],
                            unit_class,
                        )
                    )
        panels.append(
            {
                "fig_id": "RV.3",
                "panel": unit_class,
                "title": "Peer positioning",
                "kind": "range",
                "unit_class": unit_class,
                "unit": unit,
                "series": ["Issuer", "Peer median", "Peers"],
                "rows": [facts[f"T1C.3.issuer.{m}"]["label"] for m in metric_keys],
                "points": points,
                "reason": None,
                "range_rule": "the drawn band spans the minimum and maximum of the plotted Peers marks of the row (included peers only, gap marks excluded); it is a drawing of the marks, not a fact, and carries no text",
            }
        )
    plotted = {p["fact_id"] for panel in panels for p in panel["points"]}
    excluded_facts = sorted(f"T1C.3.{p}.{m}" for p in excluded for m in METRICS)
    assert not plotted & set(excluded_facts)
    return {
        "module_status": case["module_status"],
        "included_peers": peers,
        "excluded_peers": {
            p: {
                "name": names[p],
                "inclusion_fact": f"T1C.1.{p}.included",
                "shown": facts[f"T1C.1.{p}.included"]["shown"],
            }
            for p in excluded
        },
        "excluded_facts_never_plotted": excluded_facts,
        "chart_series": panels,
        "table_twin": {panel["panel"]: twin(panel["points"]) for panel in panels},
        "gap_marks": [g for panel in panels for g in gaps_of(panel["points"])],
    }


def build_rv3():
    oracle = load("cp1c")
    positive = rv3_case(oracle["cases"]["positive"])
    gap = rv3_case(oracle["cases"]["gap"])
    assert sorted(g["fact_id"] for g in gap["gap_marks"]) == [
        "T1C.3.p03.interest_coverage_adjusted",
        "T1C.4.interest_coverage_adjusted.median",
    ]
    assert not positive["gap_marks"] and gap["excluded_peers"] == {}
    assert list(positive["excluded_peers"]) == ["p05"]
    return {
        "schema_version": STAMP,
        "review_phase": REVIEW_PHASE,
        "figure": "RV.3",
        "source_authority": authority(
            ("cp1c",),
            design={
                "file": DESIGN + "rbot-fp-03-relative-value.dc.html",
                "lines": "53 (head 'Peer positioning', 'CP-1C · Fig. RV.3'), 54 (range strip legend '● CZR · ○ peers · band = peer range'), lib/charts.js:152 rangeStrip",
            },
            brief={
                "file": BRIEF + "03-relative-value.md",
                "line": 36,
                "text": "charts.peerRange (range strip)",
            },
            facts="T1C.3.issuer.<m>, T1C.3.pNN.<m>, T1C.4.<m>.median, T1C.1.pNN.included, T1C.5.pNN.<m>_flag for the four metrics of cases/cp1c-owner/expected.json",
        ),
        "form": {
            "kind": "range strip, one row per metric (design; ChartKind gains 'range')",
            "marks": "Issuer (design CZR marker), Peers (design hollow marks), Peer median (pack peerRange rows[].median)",
            "panels": "two panels, one unit class each (percent: margin, FFO to debt; multiple: leverage, coverage); inference: ChartSpec has one unit_class and mark text must equal format_value of it",
            "rows": "brief 03:36 lists margin, growth and yield; only the four CP-1C metrics are facts, growth and yield rows are left out",
            "placement": "above (design :54 puts the strip over the peer-set table); inference",
            "emphasis": "a peer mark whose settled T1C.5 flag text is 'Outlier' is marked from that fact; no outlier test is recomputed",
        },
        "cases": {"positive": positive, "gap": gap},
        "adversarial_cases": [
            {
                "case": "excluded_peer_widens_range",
                "expected": "p05 (T1C.1.p05.included 'Excluded'; leverage 0.50x, coverage 20.00x, FFO to debt 80.0%, margin 30.0%) contributes no mark and no range extent; its T1C.5 cells are not_meaningful and are never read.",
            },
            {
                "case": "gap_peer_value",
                "expected": "Gap case: T1C.3.p03.interest_coverage_adjusted is missing; the Peers mark is a gap '∅ G#', not 0, and the band spans the two plotted peers only.",
            },
            {
                "case": "gap_median",
                "expected": "Gap case: T1C.4.interest_coverage_adjusted.median is missing (two included peers with a value); the Peer median mark is a gap '∅ G#' with that fact's reason, never the mean or a median of two.",
            },
            {
                "case": "outlier_marking",
                "expected": "Positive case: p04 is flagged 'Outlier' on leverage, coverage and FFO to debt and 'Within range' on margin; the flag is read from T1C.5.p04.<m>_flag and p04 stays plotted (outliers are marked, not dropped).",
            },
            {
                "case": "no_peers_and_refused",
                "expected": "Cases no_peers and refused of the CP-1C oracle have no settled T1C.3 peer cells: no chart, no zero fill (the block's empty state).",
            },
            {
                "case": "position_not_recomputed",
                "expected": "Issuer position, difference and deviation (T1C.4 position/difference, T1C.5 deviation) stay table cells; the chart draws only marks and carries no rank text.",
            },
            {
                "case": "synthetic_peers",
                "expected": "The peers are invented (CP1C-OWNER-LEASE.md:31); the chart carries the module's limitation and no real-market claim, and the figure note names them synthetic.",
            },
        ],
        "scope_limits": [
            "Four CP-1C metrics only; no revenue growth, no TRACE or last-trade yield row (not CP-1C facts).",
            "Synthetic peer source; unaudited; the module status stays restricted and the chart does not upgrade it.",
            "EBITDAR and definition differences stay in T1C.6 (evidence rail), not drawn.",
        ],
        "render": {
            "pathway": "relative_value",
            "block_id": "peer-positioning",
            "owner": "CP-1C",
            "producers": ["CP-1C"],
            "kind": "dense",
            "state": "populated",
            "figures": [
                {"fig_id": "RV.3", "panel": "percent", "placement": "above"},
                {"fig_id": "RV.3", "panel": "multiple", "placement": "above"},
            ],
            "primary_tab": "T1C.1",
            "tabs": ["T1C.8", "T1C.3", "T1C.4", "T1C.5"],
            "note": "tabs as cases/cp1c-owner/expected.json cases.positive.FP03; the figures are added above them",
        },
        "builder_targets": [
            {
                "test_file": "tests/test_connect_cp1c.py (producer tests)",
                "assert": [
                    "a CP-1C chart producer (record fields as docs/CP1-CHART-SLICE.md:66, two panels) returns the points of cases.positive.chart_series from the CP-1C ModuleView of the oracle run, with the fact ids and companion fact ids in the file",
                    "the same producer on the gap run returns the two gap points of cases.gap.gap_marks with state 'gap'; no point reads T1C.3.p05.*",
                    "no_peers and refused runs return no panels",
                ],
            },
            {
                "test_file": "tests/test_connect_cp1c.py (render)",
                "assert": [
                    "report_view.build(view, relative_value pathway, SHIPPED_MAPS) block 'peer-positioning': owner CP-1C, kind dense, state populated, figures fig_id 'RV.3' x2 (percent then multiple), tabs unchanged",
                    "ChartSpec kind 'range' (ChartKind gains it; charts.py renders it); mark texts equal format_value of the panel unit_class; gap marks have value None and ref_id G<n>",
                    "table twin cell texts equal the mark texts, in point order, per panel",
                ],
            },
        ],
    }


# --- CR.1 ----------------------------------------------------------------------------------------

DIRECTION = {  # src/deploy_vii/cp4_legal.py:750-756 `_COMPARISON_TEXT`; design bullet direction max/min
    "Not more than": "ceiling",
    "Not less than": "floor",
}
COMPANIONS = {
    "threshold": ("comparison",),
    "current": ("cp_1_metric", "test_on_cp_1_metric"),
    "headroom": ("headroom_share", "test_on_cp_1_metric"),
}


def cr1_case(case):
    table = next(t for t in case["tables"] if t["table_id"] == "T4.9")
    points, rows_meta = [], []
    for row in table["rows"]:
        by_field = {fact["fact_id"].rsplit(".", 1)[-1]: fact for fact in row["facts"]}
        comparison = by_field["comparison"]["text"]
        assert comparison in DIRECTION
        rows_meta.append(
            {
                "row_id": row["row_id"],
                "label": row["label"],
                "comparison_text": comparison,
                "direction": DIRECTION[comparison],
            }
        )
        for series, field in (
            ("Threshold", "threshold"),
            ("Current", "current"),
            ("Headroom", "headroom"),
        ):
            fact = by_field[field]
            reading = None
            if fact["status"] == "known":
                if "amount" in fact:
                    exact = fact["amount"]
                else:  # the threshold is a settled text cell '4.00x'; read as a coordinate, no arithmetic
                    assert re.fullmatch(r"\d+(\.\d+)?x", fact["text"])
                    exact = fact["text"][:-1]
                    reading = (
                        f"settled text {fact['text']!r} read as the number {exact}; no arithmetic"
                    )
                shown, state, gap_reason = spell(Decimal(exact), "multiple"), "plotted", None
                assert fact.get("text", shown) == shown
            else:
                exact, shown, state, gap_reason = None, GAP, "gap", fact["limitation"]
            companions = []
            for name in COMPANIONS[field]:
                c = by_field[name]
                if c["status"] != "known":
                    text = GAP
                elif "amount" in c:
                    text = spell(Decimal(c["amount"]), "percent")
                else:
                    text = c["text"]
                companions.append({"fact_id": c["fact_id"], "label": c["column"], "shown": text})
            points.append(
                {
                    "series": series,
                    "category": row["label"],
                    "fact_id": fact["fact_id"],
                    "companion_fact_ids": [c["fact_id"] for c in companions],
                    "state": state,
                    "settled_status": fact["status"],
                    "numeric_reading": reading,
                    "amount_exact": exact,
                    "shown": shown,
                    "gap_ref_pattern": GAP_PATTERN if state == "gap" else None,
                    "gap_reason": gap_reason,
                    "companions": companions,
                }
            )
    return {"rows": rows_meta, "points": points}


def cr1_record(case):
    return {
        "fig_id": "CR.1",
        "title": "Covenant tests and headroom",
        "kind": "bullet",
        "unit_class": "multiple",
        "unit": "x",
        "series": ["Threshold", "Current", "Headroom"],
        "points": case["points"],
        "rows": case["rows"],
        "reason": None,
    }


def build_cr1():
    oracle = load("cp4")
    positive = cr1_case(oracle["positive"]["CP-4"])
    gap = cr1_case(oracle["gap"]["CP-4"])
    literals = oracle["render"]["displayed_literals"]
    for name, case in (("positive", positive), ("gap", gap)):
        spelled = {p["series"]: p["shown"] for p in case["points"]}
        want = literals[name]["T4.9"]
        assert spelled["Threshold"] == want["threshold"] and spelled["Current"] == want["current"]
    assert {p["series"]: p["shown"] for p in positive["points"]}["Headroom"] == literals[
        "positive"
    ]["T4.9"]["headroom"]
    assert [p["series"] for p in gap["points"] if p["state"] == "gap"] == ["Headroom"]
    refusal = oracle["gap_false_same_definition"]["CP-4"]
    return {
        "schema_version": STAMP,
        "review_phase": REVIEW_PHASE,
        "figure": "CR.1",
        "source_authority": authority(
            ("cp4",),
            design={
                "file": DESIGN + "rbot-fp-04-covenant-refinancing.dc.html",
                "lines": "34 (head 'Covenant tests and headroom', 'CP-4 · Fig. CR.1'), 35 (bullet beside the table), 58 (twin 'Fig. CR.1 Covenant tests'), lib/charts.js:90 bullet",
            },
            brief={
                "file": BRIEF + "04-covenant-refinancing.md",
                "line": 27,
                "text": "charts.fig-covenant-headroom (bullet, unit x, ceilings and floors)",
            },
            facts="T4.9.rNN.threshold, .comparison, .current, .headroom (+ .headroom_share, .cp_1_metric, .test_on_cp_1_metric as companions)",
        ),
        "form": {
            "kind": "bullet, one row per covenant test (design; ChartKind gains 'bullet')",
            "series": "Threshold, Current, Headroom (brief 04:27: threshold / current / headroom)",
            "direction": "ceiling for comparison text 'Not more than', floor for 'Not less than' (cp4_legal.py:750-756); any other comparison text: the row is not drawn and the figure reason names the fact",
            "unit": "x, unit_class multiple (brief 04:27 unit x)",
            "placement": "beside (design :34-35 puts the bullet beside the table in a two-column grid); inference",
            "status_column": "the design's Headroom/Tight/Breached status is not a settled CP-4 fact; not drawn",
            "headroom_share": "percent: a companion fact on the headroom mark and a table cell, never a plotted mark (one unit class per ChartSpec)",
        },
        "cases": {
            "positive": {
                "module_status": oracle["positive"]["CP-4"]["status"],
                "chart_series": [cr1_record(positive)],
                "table_twin": {"CR.1": twin(positive["points"])},
                "gap_marks": [],
            },
            "gap": {
                "module_status": oracle["gap"]["CP-4"]["status"],
                "chart_series": [cr1_record(gap)],
                "table_twin": {"CR.1": twin(gap["points"])},
                "gap_marks": gaps_of(gap["points"]),
            },
            "gap_false_same_definition": {
                "first_submission": "refused by the CP-4 semantic gate: no CP-4 head is settled, so no chart and no T4.9 row exists",
                "refusal_issues": refusal["refusal"]["issues"],
                "must_not_appear": refusal["semantic_acceptance"][
                    "values_the_documented_rules_would_compose_from_these_inputs_and_that_must_not_qualify"
                ],
                "corrected_resubmission_settles": refusal["corrected_resubmission"]["settles"],
                "corrected_resubmission_chart": "identical to cases.gap.chart_series",
            },
        },
        "adversarial_cases": [
            {
                "case": "gap_headroom",
                "expected": "Gap case: T4.9.r01.headroom is missing ('Not calculable: Whether the covenant definition is the CP-1 metric's is not determinable'); the Headroom mark is a gap '∅ G#', never 0 and never 3.00x; headroom_share is a gap companion; Threshold 4.00x and Current 1.00x stay plotted.",
            },
            {
                "case": "gap_false_same_definition",
                "expected": "The first submission is refused, so nothing is drawn and the values the documented rules would compose (3.00x, 75.0%, 'within threshold') never appear; the corrected resubmission draws the gap chart.",
            },
            {
                "case": "threshold_is_text",
                "expected": "T4.9.r01.threshold is a settled text cell '4.00x', not an amount: the mark reads it as the number 4.00 with no arithmetic. Raised as a question (the alternative amends CP-4).",
            },
            {
                "case": "current_is_cp1_fact",
                "expected": "T4.9.r01.current copies the CP-1 net_leverage_reported LTM Q4 25 fact (amount 1, MULTIPLE); its period and basis are the CP-1 fact's; the chart never reads CP-1 directly.",
            },
            {
                "case": "direction_not_inferred",
                "expected": "Direction comes only from the settled comparison text; a 'Not stated' comparison draws no bullet row.",
            },
            {
                "case": "no_legal_conclusion",
                "expected": "The chart states no breach or compliance verdict; 'Within threshold on the CP-1 metric' stays a companion table text, and the status words Tight and Breached are not drawn.",
            },
        ],
        "scope_limits": [
            "One covenant row (r01, Maximum net leverage ratio) in the frozen synthetic case; the pack's four-row example (6.50x/3.02x) is not data.",
            "Restricted CP-4 status stays; headroom is on the CP-1 metric, not a legal verdict.",
            "FP 05 'Covenant levers' (covenant-levers) reuses this series after its own lease (Q-C10); not wired here.",
        ],
        "render": {
            "pathway": "covenant_refinancing",
            "block_id": "covenant-tests-headroom",
            "owner": "CP-4",
            "producers": ["CP-4"],
            "kind": "dense",
            "state": "populated",
            "figures": [{"fig_id": "CR.1", "placement": "beside"}],
            "primary_tab": "T4.9",
            "tabs": [],
        },
        "builder_targets": [
            {
                "test_file": "tests/test_connect_cp4.py (producer tests)",
                "assert": [
                    "a CP-4 chart producer returns one CR.1 record (kind 'bullet', unit_class 'multiple', unit 'x', series Threshold/Current/Headroom) whose points are cases.positive.chart_series[0].points from the T4.9 facts of the oracle run, with companions as listed",
                    "the gap run returns the Headroom point as a gap (state 'gap', fact T4.9.r01.headroom) and the other two as plotted",
                    "the gap_false_same_definition first submission yields no head and the producer returns no figure",
                ],
            },
            {
                "test_file": "tests/test_legal_render.py (render)",
                "assert": [
                    "report_view.build on the covenant_refinancing CP-4 run: block 'covenant-tests-headroom' has figures [CR.1] (placement 'beside'), tab_label as before (T4.9 'Covenant tests and headroom'), no tabs; mark texts '4.00x', '1.00x', '3.00x'; twin cells equal mark texts in order",
                    "gap run: Headroom mark value None, ref_id G<n>, text '∅ G<n>'; Threshold and Current marks unchanged",
                    "ChartKind gains 'bullet'; the threshold mark value Decimal('4.00') is read from the text fact",
                ],
            },
        ],
    }


# --- FP 04 populated S.4 -------------------------------------------------------------------------


def build_s4fp04():
    chart = load("chart_s1_s4")
    cp2d = load("cp2d")
    wall = chart["current_maturity_wall"]
    assert len(wall) == 1
    facility = wall[0]
    term = cp2d["source_facts"]["term_loan"]
    assert facility["facility_id"] == term["facility_id"]
    assert Decimal(facility["principal_millions"]) == Decimal(term["principal"])
    assert facility["maturity_date"] == term["maturity_date"]
    t2e4 = cp2d["cases"]["positive"]["tables"]["T2E.4"]
    assert t2e4["rows"][0][1][0]["shown"] == spell(Decimal(term["principal"]), "amount")
    label = f"{facility['facility_name']} ({facility['facility_id']})"
    amount = Decimal(facility["principal_millions"])
    s4_point = {
        "series": label,
        "category": facility["maturity_date"],
        "fact_coordinate": {
            "module": "CP-1",
            "table_id": "T4.18",
            "row": {"facility_id": facility["facility_id"], "period_id": "q4-2025"},
            "field": "principal",
            "unit": "MILLIONS",
            "currency": "USD",
            "scale": "1000000",
        },
        "fact_id_rule": "run-time id of the T4.18 principal fact of the QUARTER alias row (an explicit QUARTER wins over the FY alias, financial_series._maturity_figure)",
        "companion_coordinates": [
            {"table_id": "T4.18", "row": "same", "field": f}
            for f in (
                "facility_id",
                "facility_name",
                "facility_type",
                "currency",
                "maturity_date",
                "annual_amortisation",
                "lease_classification",
                "period_id",
            )
        ]
        + [{"table_id": "T4.14", "period_id": "q4-2025", "field": f} for f in PERIOD_FIELDS],
        "state": "plotted",
        "amount_exact": str(amount),
        "shown": spell(amount, "amount"),
    }
    record = {
        "fig_id": "S.4",
        "title": f"Maturity wall — principal at {facility['as_of']} (not a forecast)",
        "kind": "grouped",
        "unit_class": "amount",
        "unit": "US$m",
        "series": [label],
        "points": [s4_point],
        "reason": None,
    }
    t2e4_tab = {
        "table_id": "T2E.4",
        "label": "Maturity wall",
        "label_source": "bindings/cp2d.py:33 binding label (Binding.title is the tab label)",
        "title": t2e4["title"],
        "row_header": t2e4["row_header"],
        "columns": t2e4["columns"],
        "rows": [
            {
                "label": row[0],
                "cells": [c["shown"] for c in row[1]],
                "fact_ids": [c["fact_id"] for c in row[1]],
            }
            for row in t2e4["rows"]
        ],
    }
    return {
        "schema_version": STAMP,
        "review_phase": REVIEW_PHASE,
        "figure": "S.4 (FP 04 populated)",
        "source_authority": authority(
            ("chart_s1_s4", "cp2d"),
            design={
                "file": DESIGN + "rbot-fp-04-covenant-refinancing.dc.html",
                "lines": "42 (head 'Maturity wall', 'MODEL · Fig. S.4')",
            },
            brief={
                "file": BRIEF + "04-covenant-refinancing.md",
                "line": 31,
                "text": "Maturity wall and capital structure (Model); charts.maturityWall",
            },
            ruling="Q-C1 revised (user, 2026-10-29): reuse the built MODEL S.4; CP-2D T2E.4 stays bound as a non-primary tab; no CP-2D figure",
            series_oracle="cases/charts/expected.json current_maturity_wall (one facility); T2E.4 and the term loan terms in cases/cp2d-owner/expected.json",
        ),
        "form": {
            "figure": "the same S.4 record the model-chart-strip draws (cp1_chart_series S.4); no new figure, no new producer",
            "placement": "above; inference (the design puts the wide chart left of a commentary panel)",
            "primary_tab": "CP-1 T4.18 register bound to maturity-wall (inference: label 'Capital structure' follows brief 04:31 'Maturity wall and capital structure'); its cells are not pinned here because the CP-1 head's T4.18 table layout is observed only at Stage 5",
            "non_primary_tab": "CP-2D T2E.4 with the label of its binding",
        },
        "chart_series": [record],
        "table_twin": {"S.4": twin([{**s4_point, "companions": []}])},
        "t2e4_tab": t2e4_tab,
        "gap_marks": {
            "in_positive_case": [],
            "rule": "an unavailable maturity date or incomplete facility population yields reason text and no points (financial_series._maturity_figure), never a zero bin",
        },
        "adversarial_cases": [
            {
                "case": "single_count",
                "expected": "Exactly one mark, value 50; the FY and Q4 alias rows never double it to 100 and T2E.4 (also 50) never adds a second mark.",
            },
            {
                "case": "model_first",
                "expected": "The Model figure leads: block.figures[0].fig_id == 'S.4' and the primary tab is the CP-1 register, so block.tab_label is not the T2E.4 tab's label.",
            },
            {
                "case": "t2e4_tab_cells_equal_cp2d",
                "expected": "The T2E.4 tab cells equal t2e4_tab.rows[].cells (the frozen CP-2D shown strings): '50', '2029-12-31', '48 months', 'No', '100.0%', '100.0%'.",
            },
            {
                "case": "cp1_absent",
                "expected": "A covenant_refinancing run without CP-1 settled (legal-render FP04 fixture, requested modules CP-4 and CP-5) keeps its pinned empty state 'Not run: CP-1 has not run.'; no figure, no T2E.4 tab.",
            },
            {
                "case": "cp2d_absent_cp1_present",
                "expected": "With CP-1 only, the block shows the S.4 figure and the CP-1 register, no tabs.",
            },
            {
                "case": "no_cp2d_figure",
                "expected": "CP-2D draws no figure in maturity-wall; the T2E.4 rows are table only.",
            },
        ],
        "scope_limits": [
            "Single synthetic facility (Northbridge Term Loan, USD 50m, 2029-12-31); the design's stacked-by-rank wall is S.6/deferred.",
            "Principal classified by contractual maturity at 2025-12-31, not a forecast.",
            "This oracle moves no frozen value: contracts.py already requests CP-1 for covenant_refinancing; the CP-MODEL plan edit and the legal-render pin at render-expected.json:1956 stay with the Q-C1 oracle check and are not needed for this populated render.",
        ],
        "render": {
            "pathway": "covenant_refinancing",
            "block_id": "maturity-wall",
            "owner": "MODEL",
            "producers": ["CP-1"],
            "spec_kind": "chart",
            "block_kind": "dense",
            "state": "populated",
            "route_label": None,
            "figures": [{"fig_id": "S.4", "placement": "above"}],
            "primary_tab": {"module": "CP-1", "table_id": "T4.18", "label": "Capital structure"},
            "tabs": [{"module": "CP-2D", "table_id": "T2E.4", "label": "Maturity wall"}],
            "strip_figures": {"maturity-wall": [["S.4", "Maturity wall", None]]},
        },
        "builder_targets": [
            {
                "test_file": "tests/test_connect_cp2d.py::test_fp04_maturity_wall_shows_model_content_first_with_t2e4_as_a_tab",
                "assert": [
                    "remove the xfail marker (strict XPASS)",
                    'replace `assert [tab.label for tab in block.tabs] == ["T2E.4"]` and `assert block.tab_label != "T2E.4"` with `== ["Maturity wall"]` and `block.tab_label == "Capital structure"`: a tab label is the binding label (Binding.title), never the table id, so the written literal cannot pass',
                    "make_upstream's CP-1 head (cp1_module) has three T4.14 fields per period and T4.18 rows without facility_type, period_id and lease_classification, so cp1_chart_series raises ValueError on it; extend the fixture to the full chart identity of tests/test_financial_series.py fixture() (T4.14 rows with all _PERIOD_FIELDS, T4.10 metric rows, T4.18 required fields) or give S.4 its own entry point; the oracle pins the series either way",
                    "block.figures[0] is S.4, kind 'grouped', series [label], one mark (label '2029-12-31', value Decimal('50'), text '50'); table twin cell '50'",
                ],
            },
            {
                "test_file": "tests/test_connect_cp2d.py::test_spec_rows_serve_the_three_blocks",
                "assert": [
                    "the maturity-wall row becomes (\"Maturity wall\", \"MODEL\", \"chart\", (\"CP-1\",), None); bindings/cp1.py binds T4.18 to maturity-wall (second placement, label 'Capital structure'); `_STRIP_FIGURES` gains 'maturity-wall': (('S.4', 'Maturity wall', None),)",
                ],
            },
            {
                "test_file": "tests/test_legal_render.py",
                "assert": [
                    "the FP04 fixture (CP-4, CP-5 only) still renders maturity-wall owner MODEL with the pinned empty state (regression)"
                ],
            },
        ],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    write("s5-expected.json", build_s5())
    write("rv3-expected.json", build_rv3())
    write("cr1-expected.json", build_cr1())
    write("s4fp04-expected.json", build_s4fp04())
    return 0


if __name__ == "__main__":
    sys.exit(main())
