"""Writes cases/charts/{cr2,cr3,dr2,dr345,dr6}-expected.json (Stage 3 chart oracles, group B).

Stdlib only; imports nothing from src/. Every value is read from the four frozen module oracles
(cases/cp2d-owner, cp3c-owner, cp4c-owner, cp2h-owner `expected.json`) and copied or checked with
Decimal; nothing is retyped. The only literals are form fields taken from the approved design
pages and the pack briefs (each with its source line in a comment) and the method labels of the
producer records (CP1-CHART-SLICE.md:66). Output is deterministic: sorted keys, indent 2, LF.

Run: python3 -I cases/charts/builder/build_b.py   (from the repository root)
"""

import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal, getcontext
from pathlib import Path

getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "cases" / "charts"

SCHEMA = "independent-stage3-chart-expectations/1"
PHASE = "pre-implementation; independent of candidate renderer output; derived from the frozen module oracles only"
GAP_SPELLING = "∅ G#"  # display.py gap spelling; G<n> is bound at run time (A7 exception)

# ---- form fields from the design pages and briefs (D = DEPLOY VII/design/reference) ----------
D_FP04 = "design/reference/rbot-fp-04-covenant-refinancing.dc.html"
D_FP05 = "design/reference/rbot-fp-05-distressed-restructuring.dc.html"
D_CHARTS = "design/reference/lib/charts.js"
SHA_D_FP04 = "57f921b3b4c1ed53ab3c5cd39295dd5bd9f29b46d4b5978f3974cab1f78169ad"
SHA_D_FP05 = "cae34879e839be531affa30bf5f513ecfb748c1c75a874b70c179c7734984f18"
SHA_D_CHARTS = "c892cbe3a4e2dc0d5b2f560b469356ca8502d4a14f07d9f4cfdf19d95be40f03"
B_FP04 = "docs/design-pack/content/04-covenant-refinancing.md"
B_FP05 = "docs/design-pack/content/05-distressed-restructuring.md"
SHA_B_FP04 = "9cd89c17b26e666d7d7e86f52edeef90fd492031118b65c23850212e9c532ade"  # MANIFEST.md:18
SHA_B_FP05 = "1990e9fd9a4c1b3e9703cb5c9aaaf8c59127fe642ebe7697391cb49b19eb3276"  # MANIFEST.md:19

# Q-C3 (user, 2026-10-29): draw CP-2D's settled steps, state the difference from the design.
CR2_NOTE = (
    "Steps are CP-2D's settled cash bridge: cash at the balance date, run-rate net cash flow over "
    "the horizon, scheduled amortisation, maturities, and cash at horizon end before refinancing. "
    "The design bridge (accessible liquidity plus inflow less mandatory uses less discretionary "
    "capex, rbot-fp-04 :39) is not drawn: CP-2D settles no lease or capex split."
)
# CR.2 bridge steps: questions.md item 4 and charts-inventory.md CR.2 row (fact ids; role = waterfall role)
CR2_STEPS = (
    ("T2E.2.r01", "total"),
    ("T2E.3.r05", "value"),
    ("T2E.3.r06", "value"),
    ("T2E.3.r07", "value"),
    ("T2E.3.r08", "total"),
)
CR2_HORIZON_FACTS = ("T2E.3.r03", "T2E.3.r04")  # horizon months and end date: period identity
# DR.6 n/a frame literals: rbot-fp-05 :112 (C.naFrame call), :54 (status chip), charts.js:166-174
DR6_FRAME = {
    "title": "Rating trigger headroom",
    "reason": "no agency report in the Source Pack",
    "design_ref_literal": "G31",
    "text_rule": "'n/a' + ' · ' + ref, then the reason (charts.js:171-173)",
    "width": 200,
    "height": 96,
}
DR6_CHIP = "Not computable"
# Ruling 2026-10-29-stage3 item 6.5: the frame text must be true per case (the agency source is synthetic).
FRAME_REASON_POSITIVE = (
    "agency source is synthetic; a headroom chart waits for a real agency report"
)
FRAME_REASON_GAP = "a trigger threshold is not stated in the synthetic agency source; a headroom chart waits for a real agency report"
# Design figure ids and headers: CR.2 fp04 :38, CR.3 fp04 :43, DR.2 fp05 :37, DR.3-5 fp05 :40
FIG_TITLES = {
    "CR.2": "Liquidity runway",
    "CR.3": "Funding gap",
    "DR.2": "Recovery by class",
    "DR.3-5": "Value allocation",
    "DR.6": "Rating triggers",
}
SCENARIO_FIGS = {
    "v01": "DR.3",
    "v02": "DR.4",
    "v03": "DR.5",
}  # fp05 :40 "Fig. DR.3-5", one per scenario


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def write(name: str, obj: dict) -> None:
    text = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    (OUT / name).write_text(text, encoding="utf-8")


def module_authority(rel: str) -> dict:
    return {"path": rel, "sha256": sha(rel), "schema_version": load(rel).get("schema_version")}


def fmt_amount(value: Decimal, places: int) -> str:
    """display.py amount spelling: fixed places, half away from zero, negatives in brackets."""
    quant = Decimal(1).scaleb(-places)
    q = value.quantize(quant, rounding=ROUND_HALF_UP)
    body = f"{abs(q):f}"
    return f"({body})" if q < 0 else body


def gap_point(
    series: str, category: str, fact_id: str, companions: list, reason, extra: dict
) -> dict:
    point = {
        "series": series,
        "category": category,
        "fact_id": fact_id,
        "companion_fact_ids": companions,
        "state": "gap",
        "value": None,
        "shown": GAP_SPELLING,
        "reason": reason,
        "gap_rule": "never zero; the G# reference is bound at run time in report order",
    }
    point.update(extra)
    return point


def known_point(
    series: str, category: str, fact_id: str, companions: list, shown, amount, extra: dict
) -> dict:
    point = {
        "series": series,
        "category": category,
        "fact_id": fact_id,
        "companion_fact_ids": companions,
        "state": "known",
        "value": amount,
        "shown": shown,
    }
    point.update(extra)
    return point


def twin(columns: list, point_rows: list) -> dict:
    """Table twin: one row per category, one cell per series, flattened order equals mark order."""
    return {"columns": columns, "rows": point_rows}


def figure_record(fig_id, title, kind, unit_class, unit, series, points, reason, extra) -> dict:
    rec = {
        "fig_id": fig_id,
        "title": title,
        "kind": kind,
        "unit_class": unit_class,
        "unit": unit,
        "series": series,
        "points": points,
        "reason": reason,
        "gap_count": sum(1 for p in points if p["state"] == "gap"),
        "point_count": len(points),
    }
    rec.update(extra)
    return rec


def kind_or_na(points: list, preferred: str) -> tuple:
    """A chart with no plottable point is the n/a frame and says why (report_view.ChartSpec)."""
    if any(p["state"] == "known" for p in points):
        return preferred, None
    reasons = [p["reason"] for p in points if p.get("reason")]
    return "na", reasons[0] if reasons else "no plottable point"


# ================================================================== CR.2 (CP-2D) =============
def cp2d_cells(case: dict) -> dict:
    cells = {}
    for table_id in ("T2E.2", "T2E.3"):
        for label, cell in case["tables"][table_id]["rows"]:
            cells[cell["fact_id"]] = (label, cell)
    return cells


def cr2_points(case: dict) -> list:
    cells = cp2d_cells(case)
    for fact_id in CR2_HORIZON_FACTS:
        assert fact_id in cells, fact_id
    operands = [fid for fid, _ in CR2_STEPS[:-1]]
    points = []
    for fact_id, role in CR2_STEPS:
        label, cell = cells[fact_id]
        companions = list(CR2_HORIZON_FACTS)
        if fact_id == CR2_STEPS[-1][0]:
            companions += operands
        extra = {
            "role": role,
            "unit": cell.get("unit"),
            "currency": "USD",
            "value_class": cell.get("value_class"),
            "period": cell.get("period"),
        }
        if cell["state"] == "known":
            points.append(
                known_point(
                    "Cash bridge", label, fact_id, companions, cell["shown"], cell["amount"], extra
                )
            )
        else:
            points.append(
                gap_point("Cash bridge", label, fact_id, companions, cell.get("reason"), extra)
            )
    return points


def cr2_identity(case: dict) -> dict:
    cells = cp2d_cells(case)
    amounts = [Decimal(cells[fid][1]["amount"]) for fid, _ in CR2_STEPS]
    opening, flow, amortisation, maturities, closing = amounts
    # Table amounts are signed cash movements: outflows are negative (T2E.3.r07 = -50 in long_horizon).
    assert opening + flow + amortisation + maturities == closing, "CR.2 bridge identity broken"
    return {
        "rule": "closing = opening + flow + amortisation + maturities, every term the settled signed table amount "
        "(equivalently closing = opening + flow - |amortisation| - |maturities|, CP2D-OWNER-LEASE.md:50)",
        "terms": {fid: str(a) for (fid, _), a in zip(CR2_STEPS, amounts)},
        "sum": str(opening + flow + amortisation + maturities),
        "holds": True,
    }


def render_block(
    owner_oracle: dict,
    source: str,
    block_id: str,
    producers: list,
    fig_id: str,
    placement: str,
    chart_kind: str,
) -> dict:
    spec = owner_oracle["fp04_render"]["blocks"][block_id]
    return {
        "pathway": owner_oracle["fp04_render"]["pathway"],
        "block_id": block_id,
        "owner": spec["owner"],
        "producers": producers,
        "block_kind": spec["kind"],
        "state": spec["state"],
        "primary_tab": spec["primary_tab"],
        "tabs": spec["tabs"],
        "tabs_source": source,
        "figure": {"fig_id": fig_id, "placement": placement, "chart_kind": chart_kind},
    }


def build_cr2() -> dict:
    path = "cases/cp2d-owner/expected.json"
    d = load(path)
    cases = d["cases"]
    charts = {}
    twins = {}
    for name in ("positive", "long_horizon", "gap_minimum_cash"):
        case = cases[name]
        points = cr2_points(case)
        kind, reason = kind_or_na(points, "waterfall")
        charts[name] = figure_record(
            "CR.2",
            FIG_TITLES["CR.2"],
            kind,
            "amount",
            "MILLIONS",
            ["Cash bridge"],
            points,
            reason,
            {
                "currency": "USD",
                "axis_label": "US$ m",
                "note": CR2_NOTE,
                "module_case": name,
                "horizon_months": case["horizon_months"],
                "bridge_identity": cr2_identity(case),
                "hatched": False,
                "hatched_basis": "inference: the design hatches synthetic or illustrative steps (charts.js:80); every CP-2D bridge fact is value_class calculated or source, so none is hatched",
            },
        )
        twins[name] = twin(
            ["Step", "US$ m"],
            [{"label": p["category"], "cells": [p["shown"]]} for p in points],
        )
    # Derived-only cases (composer fixtures, no tables): the bridge arithmetic from `derived` alone.
    opening = Decimal(d["source_facts"]["closing_cash_2025_12_31"]["amount"])
    derived_only = {}
    for name in (
        "fixture_burn",
        "fixture_rcf_undisclosed",
        "fixture_rcf_undisclosed_min_above_cash",
    ):
        dv = cases[name]["derived"]
        flow = Decimal(dv["run_rate_net_cash_flow_horizon"])
        amortisation = Decimal(dv["amortisation_in_horizon"])
        maturities = Decimal(dv["maturities_in_horizon"])
        closing = Decimal(dv["cash_at_horizon_end_before_refinancing"])
        assert opening + flow - amortisation - maturities == closing, name
        derived_only[name] = {
            "opening": str(opening),
            "flow_over_horizon": str(flow),
            "amortisation_magnitude": str(amortisation),
            "maturities_magnitude": str(maturities),
            "closing": str(closing),
            "shown_derived": {"flow": fmt_amount(flow, 0), "closing": fmt_amount(closing, 0)},
            "fact_ids": "none: composer fixtures carry no tables; ids follow the T2E.3 row order of the pack cases",
        }
    assert [p["shown"] for p in charts["positive"]["points"]] == [
        p["shown"] for p in charts["gap_minimum_cash"]["points"]
    ]
    adversarial = [
        {
            "case": "zero_steps_are_known_zero",
            "module_case": "positive",
            "expected": "Flow, amortisation and maturities are settled known 0 (T2E.3.r05-r07): three plotted zero-height steps with text 0, never gaps and never omitted.",
        },
        {
            "case": "negative_closing_total",
            "module_case": "long_horizon",
            "expected": "Maturities (50) and cash at horizon end (30) are signed settled amounts (T2E.3.r07 amount -50, r08 amount -30). The closing total plots below zero; marks carry the bracket spelling of the settled cell.",
        },
        {
            "case": "minimum_cash_gap_does_not_touch_the_bridge",
            "module_case": "gap_minimum_cash",
            "expected": "Minimum cash is missing (headroom, gap and runway months are gaps in T2E.3/T2E.5) but every bridge fact T2E.2.r01 and T2E.3.r05-r08 is known and identical to positive; the bridge is drawn in full with no gap mark.",
        },
        {
            "case": "revolver_undisclosed_does_not_touch_the_bridge",
            "module_case": "fixture_rcf_undisclosed",
            "expected": "Undrawn revolver and available liquidity are missing, cash at horizon end before refinancing is known (derived-only fixture); the revolver is not a bridge step.",
        },
        {
            "case": "negative_run_rate_flow",
            "module_case": "fixture_burn",
            "expected": "Flow over the horizon -12 and closing 8 with opening 20 (derived-only fixture): the flow step is a negative delta; the identity holds.",
        },
        {
            "case": "bridge_operand_missing",
            "module_case": None,
            "expected": "Rule-derived, no settled case: when a bridge fact is missing (missing_rule, CP2D-OWNER-LEASE.md:50) its mark is a gap with its G# reference, never 0, and the closing total (which depends on it) is also a gap. A composer fixture or a forged module view must exercise it.",
        },
        {
            "case": "no_lease_or_capex_step",
            "module_case": None,
            "expected": "Q-C3: exactly five points; no lease, mandatory-use or capex step; the figure note states the difference from the design.",
        },
        {
            "case": "sign_convention",
            "module_case": "long_horizon",
            "expected": "A mark's value is the settled table amount (outflows negative), not the magnitude in `derived` (maturities_in_horizon 50).",
        },
    ]
    render = {
        "covenant_refinancing": render_block(
            d, path + "#fp04_render", "liquidity-runway", ["CP-2D"], "CR.2", "above", "waterfall"
        ),
        "distressed_restructuring": {
            "block_id": "liquidity-runway",
            "spec": "report_view._spec_of is by block id: one _Spec serves both Pathways (CP2D-OWNER-LEASE.md:139)",
            "owner": "CP-2D",
            "producers": ["CP-2D"],
            "figure": {"fig_id": "CR.2", "same_as": "covenant_refinancing", "placement": "above"},
            "render_equality": "For the same CP-2D head the figure's fig_id, title, kind, series, marks (series, label, text, value, ref_id), note and table twin rows equal the covenant_refinancing figure exactly (item 8).",
            "requires": "CP-2D in the run; contracts._PRESETS lists no CP-2D for distressed_restructuring, so the run requests it explicitly (the owner runs do) or the preset gains it (a contracts.py change that moves pins, raised as a question)",
            "without_cp2d": "no figure, no zero-fill: the block keeps its honest 'Not run' state",
            "design": {"page": D_FP05, "lines": [45, 46], "header": "CP-2D · Fig. CR.2 · US$ m"},
        },
    }
    return {
        "schema_version": SCHEMA,
        "review_phase": PHASE,
        "figure_group": "B",
        "figure": "CR.2",
        "also_covers": "item 8, CR.2 on distressed_restructuring (render equality only, no new series)",
        "source_authority": {
            "modules": [module_authority(path)],
            "design": [
                {
                    "page": D_FP04,
                    "sha256": SHA_D_FP04,
                    "lines": [38, 39, 40],
                    "what": "header 'CP-2D · Fig. CR.2', caption, bridge slot chBridge",
                },
                {
                    "page": D_FP05,
                    "sha256": SHA_D_FP05,
                    "lines": [45, 46, 47],
                    "what": "FP05 instance, header 'CP-2D · Fig. CR.2 · US$ m'",
                },
                {
                    "page": D_CHARTS,
                    "sha256": SHA_D_CHARTS,
                    "lines": [69, 85],
                    "what": "waterfall: total bars from zero, value bars float, residual bars",
                },
            ],
            "briefs": [
                {
                    "file": B_FP04,
                    "sha256": SHA_B_FP04,
                    "line": 29,
                    "what": "Liquidity runway (CP-2D), charts.fig-liquidity-bridge, waterfall US$ m",
                },
                {
                    "file": B_FP05,
                    "sha256": SHA_B_FP05,
                    "line": 30,
                    "what": "Liquidity runway (CP-2D), same chart id",
                },
            ],
            "rulings": [
                "Q-C3 (steps and note)",
                "item 4 and item 8 of questions.md 'Chart oracles to freeze'",
            ],
            "authority_order": "approved page decides figure, title, kind and look; brief decides provider and chart id; module oracle decides every number; inference marked per field",
        },
        "arithmetic": {
            "numeric_encoding": "Decimal strings from the CP-2D oracle; display spelling is the oracle cell `shown`",
            "no_recompute": "marks carry settled cells; the only arithmetic here is the bridge identity assertion in the builder",
        },
        "chart_series": {"CR.2": charts},
        "table_twins": twins,
        "derived_only_cases": derived_only,
        "adversarial_cases": adversarial,
        "scope_limits": [
            "Draws only CP-2D's settled bridge (T2E.2.r01, T2E.3.r05-r08); no lease, capex, mandatory-use or discretionary split (Q-C3).",
            "Run-rate flow is a held-flat assumption (CP-2D own limitation); the figure note does not turn it into a forecast.",
            "Pinch point, months of runway and the right-hand short table of the design are not part of this figure (T2E.3/T2E.5 tables carry them).",
            "Design deviation (Low, ruling 6.3): FP04 draws the chart beside a short table (fp04 :39-41); one shared _Spec serves both Pathways, so the figure is placed 'above' on both pages.",
        ],
        "render": render,
        "builder_targets": [
            {
                "test_file": "tests/test_chart_series_cr2.py (new)",
                "asserts": [
                    "cp2d_chart_series(module) on the CP-2D head of the positive and long_horizon owner runs (tests/cp2d_runs.py) returns one record whose fig_id, title, kind, unit_class, unit, series, reason and points (series, category, fact_id, companion_fact_ids, shown, value) equal chart_series.CR.2.<case>",
                    "the bridge identity holds on the returned values (opening + flow + amortisation + maturities == closing) and the closing mark of long_horizon is negative",
                    "no point is recomputed: each value equals Fact.amount of its fact_id; a forged view with T2E.3.r07 missing yields a gap point (value None) for r07 and r08, never 0",
                ],
            },
            {
                "test_file": "tests/test_chart_render_cr2.py (new)",
                "asserts": [
                    "report_view.build(view, covenant_refinancing pathway, SHIPPED_MAPS): block liquidity-runway has owner CP-2D, kind dense, state populated, one figure with fig_id CR.2, placement above, chart.kind waterfall, summary equal to the note, marks (series, label, text, value, role) equal the oracle points, roles total/value/value/value/total",
                    "chart.table_twin rows equal table_twins.<case> and flattened cell texts equal mark texts in order (ChartSpec.coherent)",
                    "tabs unchanged: primary T2E.3, tab T2E.1 (cases/cp2d-owner fp04_render)",
                    "distressed_restructuring run that includes CP-2D: the same figure is equal field by field (render_equality); a run without CP-2D has no figure",
                ],
            },
        ],
        "questions": [
            "contracts._PRESETS['distressed_restructuring'] lacks CP-2D, so item 8 renders only when CP-2D is requested explicitly (preset change moves pins).",
            "placement: FP04 page shows the chart beside a short table, FP05 page shows it above; one shared _Spec cannot differ per Pathway; the oracle pins 'above' for both.",
        ],
    }


# ================================================================== CR.3 (CP-3C) =============
CR3_SERIES = (
    ("c6", "Principal payable at maturity"),
    ("c7", "Resources at maturity"),
)  # questions.md item 5
CR3_COMPANIONS = ("c2", "c3")  # maturity date and months from the balance date


def cr3_pack_points(case: dict) -> list:
    points = []
    for label, cells in case["tables"]["T3D.1"]["rows"]:
        by_col = {cell["fact_id"].rsplit(".", 1)[1]: cell for cell in cells}
        row_id = cells[0]["fact_id"].split(".")[2]
        companions = [f"T3D.1.{row_id}.{c}" for c in CR3_COMPANIONS]
        for col, series in CR3_SERIES:
            cell = by_col[col]
            extra = {
                "currency": "USD",
                "unit": cell.get("unit"),
                "value_class": cell.get("value_class"),
                "period": cell.get("period"),
                "axis_sublabel": by_col["c2"]["shown"],
                "row_id": row_id,
            }
            if cell["state"] == "known":
                points.append(
                    known_point(
                        series,
                        label,
                        cell["fact_id"],
                        list(companions),
                        cell["shown"],
                        cell["amount"],
                        extra,
                    )
                )
            else:
                points.append(
                    gap_point(
                        series, label, cell["fact_id"], list(companions), cell.get("reason"), extra
                    )
                )
    return points


def cr3_fixture_points(case: dict) -> list:
    points = []
    for index, fac in enumerate(case["derived"]["facilities"], start=1):
        row_id = f"r{index:02d}"
        companions = [f"T3D.1.{row_id}.{c}" for c in CR3_COMPANIONS]
        for col, series, key in (
            ("c6", CR3_SERIES[0][1], "principal_payable_at_maturity"),
            ("c7", CR3_SERIES[1][1], "resources_at_maturity"),
        ):
            fact_id = f"T3D.1.{row_id}.{col}"
            extra = {
                "currency": "USD",
                "unit": "MILLIONS",
                "row_id": row_id,
                "fact_id_basis": "inferred: rows follow facility_order (months ascending, then id); fixtures carry no tables",
                "shown_basis": "derived: display.py 0 dp half away from zero, negatives in brackets",
            }
            value = fac[key]
            if value is None:
                points.append(
                    gap_point(
                        series,
                        fac["id"],
                        fact_id,
                        list(companions),
                        "Not calculable: a required operand is missing",
                        extra,
                    )
                )
            else:
                points.append(
                    known_point(
                        series,
                        fac["id"],
                        fact_id,
                        list(companions),
                        fmt_amount(Decimal(value), 0),
                        value,
                        extra,
                    )
                )
    return points


def cr3_twin(points: list) -> dict:
    cats = []
    for p in points:
        if p["category"] not in cats:
            cats.append(p["category"])
    rows = [
        {"label": cat, "cells": [p["shown"] for p in points if p["category"] == cat]}
        for cat in cats
    ]
    return twin(["Facility"] + [s for _, s in CR3_SERIES], rows)


def build_cr3() -> dict:
    path = "cases/cp3c-owner/expected.json"
    d = load(path)
    cases = d["cases"]
    charts, twins = {}, {}
    series = [s for _, s in CR3_SERIES]
    for name in ("positive", "gap_minimum_cash", "gap_no_repricing"):
        points = cr3_pack_points(cases[name])
        kind, reason = kind_or_na(points, "grouped")
        charts[name] = figure_record(
            "CR.3",
            FIG_TITLES["CR.3"],
            kind,
            "amount",
            "MILLIONS",
            series,
            points,
            reason,
            {
                "currency": "USD",
                "axis_label": "US$ m",
                "module_case": name,
                "origin": "pack case with tables",
            },
        )
        twins[name] = cr3_twin(points)
    for name in (
        "fixture_two_facilities",
        "fixture_burn",
        "fixture_long_horizon",
        "fixture_amortisation_missing",
    ):
        points = cr3_fixture_points(cases[name])
        kind, reason = kind_or_na(points, "grouped")
        charts[name] = figure_record(
            "CR.3",
            FIG_TITLES["CR.3"],
            kind,
            "amount",
            "MILLIONS",
            series,
            points,
            reason,
            {
                "currency": "USD",
                "axis_label": "US$ m",
                "module_case": name,
                "origin": "composer fixture, derived only",
            },
        )
        twins[name] = cr3_twin(points)
    neg = {
        name: [
            p["fact_id"]
            for p in rec["points"]
            if p["state"] == "known" and Decimal(str(p["value"])) < 0
        ]
        for name, rec in charts.items()
    }
    assert neg["fixture_two_facilities"] and neg["fixture_burn"], (
        "negative resources must exist in the fixtures"
    )
    row = cases["positive"]["tables"]["T3D.1"]["rows"][0][1]
    assert (
        row[5]["amount"] == "50" and row[6]["amount"] == "10"
    )  # positive T3D.1.r01: c6 50, c7 10 (item 5)
    adversarial = [
        {
            "case": "negative_resources_plot_below_zero",
            "module_cases": ["fixture_two_facilities", "fixture_burn"],
            "negative_point_fact_ids": {k: v for k, v in neg.items() if v},
            "expected": "Resources at maturity that are negative (two_facilities term-loan -8.5, burn -14) are known values drawn below zero with the bracket spelling; never clipped to zero (design 'Columns with negatives', charts.js:44-55). Texts for these fixtures are derived (0 dp half away from zero).",
        },
        {
            "case": "resources_gap_keeps_principal",
            "module_case": "gap_minimum_cash",
            "expected": "Minimum cash not assessed: T3D.1.r01.c7 is a gap with its G# reference and reason; c6 (principal payable at maturity 50) stays a known mark.",
        },
        {
            "case": "no_repricing_leaves_t3d1_known",
            "module_case": "gap_no_repricing",
            "expected": "The repricing gap does not touch T3D.1: marks equal positive exactly.",
        },
        {
            "case": "all_gap_chart_is_the_na_frame",
            "module_case": "fixture_amortisation_missing",
            "expected": "Amortisation missing: principal payable and resources are both missing for the only facility, so no mark is plottable; the chart is kind na with a reason and both marks are gaps, never 0.",
        },
        {
            "case": "two_facilities_order",
            "module_case": "fixture_two_facilities",
            "expected": "Categories follow T3D.1 row order (facility_order: months ascending, then id): notes (31 months) before term-loan (48 months). One category per facility, no aggregation by year.",
        },
        {
            "case": "earlier_principal_paid_from_resources",
            "module_case": "fixture_two_facilities",
            "expected": "Resources at the later maturity are net of principal paid from resources at the earlier one (notes 4.5 then term-loan -8.5): marks carry the settled per-row value, never a recomputed running balance.",
        },
        {
            "case": "cp3c_not_in_the_run",
            "module_case": None,
            "expected": "Without a CP-3C head the funding-gap block has no CR.3 figure and keeps the CP-2D oracle's tabs (T2E.5 primary, T2E.2); nothing is drawn from T2E.5 as a stand-in.",
        },
    ]
    funding = {
        "pathway": "covenant_refinancing",
        "block_id": "funding-gap",
        "owner": "CP-2D",
        "owner_basis": "unchanged (report_view _Spec, CP2D-OWNER-LEASE.md:139); the figure's module is CP-3C (design fp04 :43 'CP-3C · Fig. CR.3')",
        "producers": ["CP-2D", "CP-3C"],
        "producers_change": "CP-3C is added to the funding-gap _Spec.producers at the wiring step (Q-C2)",
        "block_kind": "dense",
        "state": "populated",
        "primary_tab": "T2E.5",
        "tabs_with_cp3c": ["T2E.2", "T3D.1"],
        "tabs_without_cp3c": ["T2E.2"],
        "tabs_source": "cases/cp2d-owner/expected.json#fp04_render.blocks.funding-gap plus the Q-C2 binding move (docs/CP3C-OWNER-LEASE.md amendment)",
        "binding": {
            "fact_coord": "CP-3C / T3D.1",
            "block_id": "funding-gap",
            "cell_slot": "cp3c-t3d-1",
            "label": "Refinancing need by maturity",
            "moved_from": "refinancing-paths",
            "reason": "validate_bindings forbids one fact bound to two blocks of one Pathway (bindings/__init__.py:113)",
        },
        "refinancing_paths_tabs_after": d["fp04_render"]["blocks"]["refinancing-paths"]["tabs"],
        "figure": {
            "fig_id": "CR.3",
            "placement": "beside",
            "chart_kind": "grouped",
            "module": "CP-3C",
            "design": {"page": D_FP04, "lines": [43, 44]},
        },
    }
    return {
        "schema_version": SCHEMA,
        "review_phase": PHASE,
        "figure_group": "B",
        "figure": "CR.3",
        "source_authority": {
            "modules": [module_authority(path)],
            "design": [
                {
                    "page": D_FP04,
                    "sha256": SHA_D_FP04,
                    "lines": [43, 44],
                    "what": "header 'CP-3C · Fig. CR.3', 'before operating cash flow; pressure illustrative', chGap columns beside the Year / Maturing / Liq. left / Pressure table",
                },
                {
                    "page": D_CHARTS,
                    "sha256": SHA_D_CHARTS,
                    "lines": [44, 58],
                    "what": "columns with negatives (min below zero)",
                },
            ],
            "briefs": [
                {
                    "file": B_FP04,
                    "sha256": SHA_B_FP04,
                    "line": 33,
                    "what": "Funding gap (CP-3C), charts.fig-funding-gap columns, blocks.maturityPressure; maturing against liquidity left",
                }
            ],
            "rulings": [
                "Q-C2 (CP-3C produces the series, drawn in funding-gap, T3D.1 binding added)",
                "item 5 of questions.md",
            ],
            "authority_order": "approved page decides figure and look; brief decides the provider; CP-3C oracle decides every number; inference marked per field",
        },
        "chart_series": {"CR.3": charts},
        "table_twins": twins,
        "twin_rule": "One row per category (facility), one cell per series (c6, c7); flattened cell texts equal mark texts in order (category-major).",
        "category_basis": "inference: the design axis is a year; the oracle draws one category per T3D.1 row (facility), labelled by the row label, with the maturity date c2 as `axis_sublabel` and companion; no aggregation by year (no recompute), as ruled for S.4 in Q-C1.",
        "series_labels_basis": "inference: column headers of T3D.1 without the unit suffix",
        "adversarial_cases": adversarial,
        "scope_limits": [
            "Draws T3D.1 c6 and c7 only; the design's pressure chip (illustrative High/Medium/Low) and year buckets (2026 rest ... Thereafter) are not CP-3C facts and are not drawn.",
            "Resources at maturity restate CP-3C's own limitations (run-rate flow held flat); the figure adds none.",
            "LME capacity (T3D.5) and the FP05 funding-gap-lme block are deferred (Q-C10).",
            "Fixture-derived point texts use the display.py rule (0 dp half away from zero) because fixtures carry no tables.",
        ],
        "render": {"covenant_refinancing": funding},
        "lease_amendment": "docs/CP3C-OWNER-LEASE.md (Stage 3 group B amendment): T3D.1 moves from refinancing-paths to funding-gap; cases/cp3c-owner/expected.json#fp04_render.blocks.refinancing-paths.tabs becomes [T3D.2, T3D.3]",
        "builder_targets": [
            {
                "test_file": "tests/test_chart_series_cr3.py (new)",
                "asserts": [
                    "cp3c_chart_series(module) on the CP-3C head of the positive and gap_minimum_cash owner runs (tests/cp3c_runs.py) equals chart_series.CR.3.<case> (points, gap marks, series order)",
                    "fixture inputs of fixture_two_facilities and fixture_burn (composer) produce negative c7 values; the producer keeps them negative",
                    "fixture_amortisation_missing yields kind na with a reason and two gap points",
                ],
            },
            {
                "test_file": "tests/test_chart_render_cr3.py (new)",
                "asserts": [
                    "run covenant_refinancing with CP-0, CP-1, CP-1A, CP-2, CP-2D, CP-3C: block funding-gap owner CP-2D, one figure CR.3 placement beside kind grouped, marks and twin equal the oracle, tabs T2E.2 and T3D.1 behind primary T2E.5",
                    "gap_minimum_cash run: the c7 mark is a gap spelled '∅ G<n>' with n from the report's gap ledger, c6 is 50",
                    "the same run without CP-3C: no figure, tabs [T2E.2] as cases/cp2d-owner fp04_render",
                    "validate_bindings(view, SHIPPED_MAPS) returns no issue with T3D.1 bound to funding-gap only; refinancing-paths tabs are T3D.2 and T3D.3",
                ],
            },
        ],
        "questions": [
            "Q-C2 says the CP-3C binding 'gains a read'. validate_bindings makes a second binding of T3D.1 an error in FP04, so the lease amendment moves the binding. If the owner prefers T3D.1 to stay in refinancing-paths, the figure must read the CP-3C head without a binding (a producer-level read).",
            "Category labels: facility rows, not the design's year buckets (inference, flagged).",
        ],
    }


# ================================================================== DR.2 / DR.3-5 (CP-4C) =====
def fact_index(case: dict) -> dict:
    return {f["fact_id"]: f for f in case["facts"]}


def class_ids(fx: dict) -> list:
    """Creditor class ids in waterfall order: (rank, id); equity is excluded."""
    ids = []
    for f in fx.values():
        if f["table_id"] == "T4E.2" and f["field"] == "name" and f["row_id"] != "eq":
            rank = fx[f"T4E.2.{f['row_id']}.rank"]["shown"]
            ids.append((int(rank), f["row_id"]))
    return [cid for _, cid in sorted(ids)]


def scenario_ids(fx: dict) -> list:
    return sorted(
        f["row_id"] for f in fx.values() if f["table_id"] == "T4E.3" and f["field"] == "scenario"
    )


def scenario_label(fx: dict, v: str) -> str:
    name = fx[f"T4E.3.{v}.scenario"]["shown"]
    mult = fx[f"T4E.3.{v}.multiple"]
    return f"{name} {mult['shown']}" if mult["status"] == "known" else name


def scenario_hatched(fx: dict, v: str) -> bool:
    return fx[f"T4E.3.{v}.multiple"].get("value_class") not in ("source", "cited")


def fact_point(series, category, f, companions, extra) -> dict:
    extra = {
        **extra,
        "unit": f.get("unit"),
        "currency": "USD" if f.get("unit") == "MILLIONS" else None,
        "value_class": f.get("value_class"),
        "period": f.get("period"),
    }
    if f["status"] == "known":
        return known_point(
            series, category, f["fact_id"], companions, f["shown"], f["amount_exact"], extra
        )
    return gap_point(series, category, f["fact_id"], companions, f.get("limitation"), extra)


def dr2_record(case_name: str, case: dict) -> tuple:
    fx = fact_index(case)
    classes, scens = class_ids(fx), scenario_ids(fx)
    series = [scenario_label(fx, v) for v in scens]
    points, dropped = [], []
    for c in classes:
        cat = fx[f"T4E.2.{c}.name"]["shown"]
        for v, label in zip(scens, series):
            f = fx[f"T4E.5.{v}{c}.recovery"]
            assert f["status"] in ("known", "missing"), (
                f"creditor recovery {f['fact_id']} is {f['status']}"
            )
            companions = [f"T4E.3.{v}.scenario", f"T4E.3.{v}.multiple", f"T4E.2.{c}.name"]
            extra = {"scenario_row": v, "class_row": c, "hatched": scenario_hatched(fx, v)}
            points.append(fact_point(label, cat, f, companions, extra))
    for v in scens:
        f = fx[f"T4E.5.{v}eq.recovery"]
        assert f["status"] == "not_applicable"
        dropped.append(
            {
                "fact_id": f["fact_id"],
                "state": "not_meaningful",
                "rule": "equity has no claim, so no recovery percentage; the mark drops out of the chart and the twin (item 6); the table keeps '∅ G# n.m.'",
            }
        )
    kind, reason = kind_or_na(points, "grouped")
    rec = figure_record(
        "DR.2",
        FIG_TITLES["DR.2"],
        kind,
        "percent",
        "PERCENT",
        series,
        points,
        reason,
        {
            "axis_label": "%",
            "module_case": case_name,
            "dropped_equity_marks": dropped,
            "series_label_rule": "scenario name + ' ' + multiple spelling when the multiple is known, else the scenario name alone (Q-C4)",
            "hatched_basis": "inference: design hatches illustrative multiples (fp05 :38 legend); a multiple is illustrative unless its fact value_class is source or cited; every CP-4C multiple is analyst_judgment, so every bar is hatched",
        },
    )
    cats = []
    for p in points:
        if p["category"] not in cats:
            cats.append(p["category"])
    rows = [
        {"label": cat, "cells": [p["shown"] for p in points if p["category"] == cat]}
        for cat in cats
    ]
    return rec, twin(["Class"] + series, rows)


def alloc_record(case_name: str, case: dict, v: str) -> tuple:
    fx = fact_index(case)
    classes = class_ids(fx)
    label = scenario_label(fx, v)
    series = ["Value allocation"]
    scen_comp = [f"T4E.3.{v}.scenario", f"T4E.3.{v}.multiple"]
    points = []
    for c in classes:
        f = fx[f"T4E.4.{v}{c}.distribution"]
        comp = scen_comp + [f"T4E.4.{v}{c}.claim", f"T4E.2.{c}.name"]
        points.append(
            fact_point(
                series[0],
                fx[f"T4E.2.{c}.name"]["shown"],
                f,
                comp,
                {"role": "value", "class_row": c},
            )
        )
    res = fx[f"T4E.9.{v}.equity_residual"]
    points.append(fact_point(series[0], res["label"], res, scen_comp, {"role": "residual"}))
    ev = fx[f"T4E.3.{v}.ev"]
    checks = [f"T4E.9.{v}.total_claims", f"T4E.9.{v}.creditor_distributions", f"T4E.9.{v}.balance"]
    points.append(fact_point(series[0], ev["label"], ev, scen_comp + checks, {"role": "total"}))
    if all(p["state"] == "known" for p in points):
        total = sum(Decimal(p["value"]) for p in points[:-1])
        assert total == Decimal(points[-1]["value"]), f"conservation {case_name} {v}"
        conservation = {
            "holds": True,
            "rule": "sum of class distributions + equity residual == enterprise value (T4E.9 balance 0)",
        }
    else:
        conservation = {
            "holds": None,
            "rule": "not asserted: a gap blocks the identity; no gap is replaced by 0",
        }
    kind, reason = kind_or_na(points, "waterfall")
    rec = figure_record(
        SCENARIO_FIGS[v],
        f"{FIG_TITLES['DR.3-5']}, {label}",
        kind,
        "amount",
        "MILLIONS",
        series,
        points,
        reason,
        {
            "currency": "USD",
            "axis_label": "US$ m",
            "module_case": case_name,
            "scenario": label,
            "conservation": conservation,
            "step_order": "classes by (rank, id), then equity residual (role residual), then enterprise value (role total)",
            "order_basis": "inference: ChartMark carries the settled non-negative cell text, so the waterfall builds up to EV; the brief's order (EV first, then allocations as deductions) would need negated marks that no settled cell carries (flagged)",
            "hatched": scenario_hatched(fx, v),
        },
    )
    return rec, twin(
        ["Step", "US$ m"], [{"label": p["category"], "cells": [p["shown"]]} for p in points]
    )


def block_spec(owner_oracle: dict, block_id: str) -> dict:
    fp = owner_oracle["cases"]["positive"]["FP05"]
    blk = fp["blocks"][block_id]
    tab_ids = [t["table_id"] for t in blk["tabs"]]
    return {
        "pathway": fp["pathway"],
        "block_id": block_id,
        "owner": blk["owner"],
        "block_kind": blk["kind"],
        "state": blk["state"],
        "primary_tab": tab_ids[0],
        "tabs": tab_ids[1:],
        "tabs_source": "cases/cp4c-owner/expected.json#cases.positive.FP05",
    }


CP4C_CASES = (
    "positive",
    "gap",
    "fixture_ev_zero",
    "fixture_ebitda_missing",
    "fixture_debt_missing",
)


def build_dr2() -> dict:
    path = "cases/cp4c-owner/expected.json"
    d = load(path)
    charts, twins = {}, {}
    for name in CP4C_CASES:
        charts[name], twins[name] = dr2_record(name, d["cases"][name])
    spec = block_spec(d, "recovery-by-class")
    spec["producers"] = ["CP-4C"]
    spec["figure"] = {
        "fig_id": "DR.2",
        "placement": "above",
        "chart_kind": "grouped",
        "design": {"page": D_FP05, "lines": [37, 38]},
    }
    adversarial = [
        {
            "case": "positive_recoveries",
            "module_case": "positive",
            "expected": "Three creditor classes by three scenarios, nine known marks; Base all 100.0%, Downside 100.0 / 18.7 / 18.7, Stress 74.2 / 0.0 / 0.0 (the points carry the settled texts); zero recoveries are known zeros plotted at zero.",
        },
        {
            "case": "equity_drops_out",
            "module_case": "positive",
            "expected": "T4E.5.v0Neq.recovery is not_applicable (n.m.): no mark, no twin cell, no gap mark; the series and twin contain creditor classes only (item 6).",
        },
        {
            "case": "gap_blocked_rank_groups",
            "module_case": "gap",
            "expected": "A missing administrative claim (c02) blocks its rank group and every lower rank: recoveries for c02-c04 are gap marks with the module reason, c01 Base and Downside stay 100.0%; the Stress scenario (multiple, EV missing) is all gaps and its series label is the bare scenario name. No gap is drawn as 0.",
        },
        {
            "case": "ev_zero_is_known_zero",
            "module_case": "fixture_ev_zero",
            "expected": "A known enterprise value of 0 gives known 0 recoveries for Downside and Stress: plotted at zero, not gaps, not n/a.",
        },
        {
            "case": "ebitda_missing_blocks_scenarios",
            "module_case": "fixture_ebitda_missing",
            "expected": "Downside and Stress EV missing: their recoveries are gap marks; Base stays 100.0%.",
        },
        {
            "case": "debt_missing_blocks_everything",
            "module_case": "fixture_debt_missing",
            "expected": "Claims missing: every recovery is a gap; no mark is plottable, so the chart is kind na with the module reason.",
        },
        {
            "case": "scenario_labels",
            "module_case": "positive",
            "expected": "Q-C4: series are Base 4.00x, Downside 3.00x, Stress 2.00x from T4E.3.v0N.scenario and .multiple, not the design's 'Merger value (cited EV)', 'Downside 5.0x', 'Stress 4.0x'.",
        },
        {
            "case": "hatching_follows_the_multiple",
            "module_case": "positive",
            "expected": "Every multiple is analyst_judgment, so every bar is hatched and the legend says 'hatched = illustrative'; a missing multiple hatches by default.",
        },
    ]
    return {
        "schema_version": SCHEMA,
        "review_phase": PHASE,
        "figure_group": "B",
        "figure": "DR.2",
        "source_authority": {
            "modules": [module_authority(path)],
            "design": [
                {
                    "page": D_FP05,
                    "sha256": SHA_D_FP05,
                    "lines": [37, 38, 71, 72],
                    "what": "header 'CP-4C · Fig. DR.2 · %', figure with legend, table twin 'Fig. DR.2 Recovery, %' (Class rows, scenario columns)",
                },
                {
                    "page": D_CHARTS,
                    "sha256": SHA_D_CHARTS,
                    "lines": [44, 66],
                    "what": "grouped columns, hatched patterns for illustrative series",
                },
            ],
            "briefs": [
                {
                    "file": B_FP05,
                    "sha256": SHA_B_FP05,
                    "line": 26,
                    "what": "Recoveries (CP-4C), charts.fig-recovery-by-class columns %",
                }
            ],
            "rulings": ["Q-C4 (scenario labels)", "item 6 of questions.md"],
            "authority_order": "approved page decides figure and look; brief decides the provider; CP-4C oracle decides every number; inference marked per field",
        },
        "chart_series": {"DR.2": charts},
        "table_twins": twins,
        "twin_rule": "Rows are creditor classes, cells are scenarios in series order (the design twin, fp05 :71-72); flattened texts equal mark texts, class-major.",
        "adversarial_cases": adversarial,
        "scope_limits": [
            "Draws T4E.5 recovery only; the fulcrum marker of the design twin (T4E.7), EV table (T4E.3) and vs-first pp (T4E.5.vs_first_pp) are table facts, not marks of this figure.",
            "Lease claims are excluded (G38 in the design); CP-4C settles creditor classes of the supplied pack only.",
            "All multiples are analyst assumptions; the figure is illustrative as CP-4C's own limitation says.",
            "cases/cp4c-owner d7_rendering.decision still reads 'no chart'; this oracle supersedes that sentence for Stage 3 (the owner oracle is not edited).",
        ],
        "render": {"distressed_restructuring": spec},
        "builder_targets": [
            {
                "test_file": "tests/test_chart_series_dr2.py (new)",
                "asserts": [
                    "cp4c_chart_series(module) on the CP-4C head of the positive and gap owner runs (tests/cp4c_runs.py) returns the DR.2 record equal to chart_series.DR.2.<case> (series labels, categories, points, gap marks, dropped equity)",
                    "fixture_ev_zero, fixture_ebitda_missing and fixture_debt_missing (composer fixtures) match their records, the last as kind na",
                    "no point value is recomputed; each equals Fact.amount of its fact_id",
                ],
            },
            {
                "test_file": "tests/test_chart_render_dr2.py (new)",
                "asserts": [
                    "report_view.build on a distressed_restructuring run with CP-4C: block recovery-by-class owner CP-4C kind dense, figure DR.2 placement above kind grouped; marks (series, label, text, value) and table twin rows equal the oracle; gap marks spelled '∅ G<n>'",
                    "tabs unchanged: primary T4E.5 behind the figure, further tabs T4E.7, T4E.8",
                ],
            },
        ],
        "questions": [
            "Hatching rule is inferred from the design legend; the brief does not state it."
        ],
    }


def build_dr345() -> dict:
    path = "cases/cp4c-owner/expected.json"
    d = load(path)
    charts, twins = {}, {}
    for name in CP4C_CASES:
        charts[name], twins[name] = {}, {}
        for v in scenario_ids(fact_index(d["cases"][name])):
            charts[name][SCENARIO_FIGS[v]], twins[name][SCENARIO_FIGS[v]] = alloc_record(
                name, d["cases"][name], v
            )
    spec = block_spec(d, "value-allocation-claims")
    spec["producers"] = ["CP-4C"]
    spec["figures"] = [
        {"fig_id": fid, "placement": "above", "chart_kind": "waterfall"}
        for fid in ("DR.3", "DR.4", "DR.5")
    ]
    spec["figure_order"] = (
        "DR.3 Base, DR.4 Downside, DR.5 Stress (scenario row order v01, v02, v03)"
    )
    spec["design"] = {"page": D_FP05, "lines": [40, 41]}
    adversarial = [
        {
            "case": "positive_conservation",
            "module_case": "positive",
            "expected": "Per scenario, class distributions plus the equity residual equal the enterprise value: Base 50 + 20 + 10 + 43.60 = 123.60; Downside 50 + 3.75 + 1.87 + 0 = 55.62 (exact 50 + 3.7466... + 1.8733... + 0); Stress 37.08 + 0 + 0 + 0 = 37.08. Marks carry the settled two-decimal texts; the builder asserts the exact identity.",
        },
        {
            "case": "equity_residual_zero_is_known",
            "module_case": "positive",
            "expected": "Downside and Stress residual 0.00 is a settled known 0 (T4E.9.v02/v03.equity_residual): plotted as a zero residual step, not a gap.",
        },
        {
            "case": "partial_gap_keeps_known_marks",
            "module_case": "gap",
            "expected": "Base and Downside: EV and the senior secured distribution are known, the other classes and the residual are gap marks (a missing claim blocks lower ranks and the residual); the chart stays a waterfall with gap marks.",
        },
        {
            "case": "ev_missing_is_the_na_frame",
            "module_case": "gap",
            "expected": "Stress (DR.5): EV, every distribution and the residual are missing, so the chart is kind na with the module reason 'the EV multiple was not assessed'.",
        },
        {
            "case": "ev_zero",
            "module_case": "fixture_ev_zero",
            "expected": "EV 0 gives all-zero known distributions and residual for Downside and Stress; plotted as zero steps with an EV total of 0, not n/a.",
        },
        {
            "case": "ebitda_missing",
            "module_case": "fixture_ebitda_missing",
            "expected": "Downside and Stress are n/a frames; Base is complete.",
        },
        {
            "case": "debt_missing",
            "module_case": "fixture_debt_missing",
            "expected": "EV is known in every scenario but every distribution and the residual are gaps: each chart has one known mark (EV total) and gap marks.",
        },
        {
            "case": "scenario_names",
            "module_case": "positive",
            "expected": "Q-C4: titles read 'Value allocation, Base 4.00x', '..., Downside 3.00x', '..., Stress 2.00x'; the design's 'Merger value' / 5.0x / 4.0x are not used.",
        },
        {
            "case": "checks_are_companions",
            "module_case": "positive",
            "expected": "T4E.9.v0N.total_claims, .creditor_distributions and .balance travel as companion ids of the EV mark and are not marks.",
        },
    ]
    return {
        "schema_version": SCHEMA,
        "review_phase": PHASE,
        "figure_group": "B",
        "figure": "DR.3-5",
        "source_authority": {
            "modules": [module_authority(path)],
            "design": [
                {
                    "page": D_FP05,
                    "sha256": SHA_D_FP05,
                    "lines": [40, 41],
                    "what": "header 'CP-4C · Fig. DR.3-5 · US$ m', scenario tabs, waterfall figure",
                },
                {
                    "page": D_CHARTS,
                    "sha256": SHA_D_CHARTS,
                    "lines": [69, 85],
                    "what": "waterfall: total, value and residual bars",
                },
            ],
            "briefs": [
                {
                    "file": B_FP05,
                    "sha256": SHA_B_FP05,
                    "line": 26,
                    "what": "Value allocation waterfalls per scenario: charts.fig-value-allocation-merger, -downside, -stress (EV, per-class allocation, residual)",
                }
            ],
            "rulings": ["Q-C4 (scenario labels)", "item 7 of questions.md"],
            "authority_order": "approved page decides figure and look; brief decides the provider and chart ids; CP-4C oracle decides every number; inference marked per field",
        },
        "chart_series": {"DR.3-5": charts},
        "table_twins": twins,
        "twin_rule": "One row per waterfall step with one cell (the settled text), in mark order.",
        "adversarial_cases": adversarial,
        "scope_limits": [
            "Draws distributions, equity residual and EV only; claims, shortfalls and value available (T4E.2/T4E.4 tabs) stay tables.",
            "Step order builds up to the enterprise value rather than starting from it (inference, flagged): marks keep the settled non-negative texts.",
            "Lease claims are excluded; the design's 'Merger value (cited EV)' scenario does not exist in CP-4C.",
        ],
        "render": {"distressed_restructuring": spec},
        "builder_targets": [
            {
                "test_file": "tests/test_chart_series_dr345.py (new)",
                "asserts": [
                    "cp4c_chart_series(module) returns DR.3, DR.4 and DR.5 after DR.2, equal to chart_series.DR.3-5.<case> for positive and gap",
                    "the three composer fixtures match, including the n/a frames and the zero EV case",
                    "conservation holds on the returned positive values; no value recomputed",
                ],
            },
            {
                "test_file": "tests/test_chart_render_dr345.py (new)",
                "asserts": [
                    "block value-allocation-claims owner CP-4C kind dense holds figures DR.3, DR.4, DR.5 in that order, each placement above kind waterfall (kind na for an n/a frame), marks roles value..., residual, total",
                    "twin rows equal table_twins; tabs primary T4E.2 then T4E.3, T4E.4, T4E.6 unchanged",
                ],
            },
        ],
        "questions": [
            "Step order (build-up to EV) departs from the brief's 'EV, then allocation, then residual'; the brief's order needs negated marks."
        ],
    }


# ================================================================== DR.6 (CP-2H) =============
def build_dr6() -> dict:
    path = "cases/cp2h-owner/expected.json"
    d = load(path)
    cases = {}
    for name in ("positive", "gap"):
        fx = {f["fact_id"]: f for f in d["cases"][name]["facts"]}
        forbidden = sorted(fid for fid, f in fx.items() if f["table_id"] in ("T2R.4", "T2R.5"))
        missing = sorted(fid for fid in forbidden if fx[fid]["status"] == "missing")
        if name == "positive":
            frame_reason, cited = FRAME_REASON_POSITIVE, []
            g_rule = "no gap fact in this case, so the frame cites no G#"
        else:
            frame_reason, cited = FRAME_REASON_GAP, missing
            g_rule = "cites the settled missing T2R.4/T2R.5 facts below; G<n> is bound at run time"
        cases[name] = {
            "frame": "the n/a frame is drawn, no mark; its text is true for this case",
            "frame_reason": frame_reason,
            "g_ref_rule": g_rule,
            "cited_gap_fact_ids": cited,
            "departs_from_approved_page": "reason text and G# differ (page: 'no agency report in the Source Pack', ref G31, fp05 :112); title, 'n/a' form, dashed frame and chip are kept",
            "marks": [],
            "forbidden_mark_fact_ids": forbidden,
            "forbidden_count": len(forbidden),
            "gap_fact_ids_in_module": missing,
            "gap_count_in_module": len(missing),
            "module_status": d["cases"][name]["module_status"],
        }
    assert (
        not cases["positive"]["gap_fact_ids_in_module"] and cases["gap"]["gap_fact_ids_in_module"]
    )
    frame = dict(DR6_FRAME)
    frame.update(
        {
            "fig_id": "DR.6",
            "block_title": FIG_TITLES["DR.6"],
            "kind": "na",
            "unit_class": "multiple",
            "series": [],
            "points": [],
            "reason": "per case: see cases.<case>.frame_reason",
            "reason_page_literal": DR6_FRAME["reason"],
            "g_ref": "per case: cited only where a settled fact supplies it (cases.<case>.cited_gap_fact_ids); the design literal G31 is not pinned",
            "status_chip": DR6_CHIP,
        }
    )
    adversarial = [
        {
            "case": "frame_in_the_positive_case",
            "module_case": "positive",
            "expected": "The synthetic fictional-agency source settles T2R.4/T2R.5, but Q-C11 draws no trigger mark: the same n/a frame is rendered, with zero marks and an empty twin.",
        },
        {
            "case": "frame_in_the_gap_case",
            "module_case": "gap",
            "expected": "The gap case (trigger t03 has no stated threshold: T2R.4.t03.headroom and status, and every T2R.5.t03 cell, missing) renders the same frame; no gap mark and no 0 is drawn for those facts.",
        },
        {
            "case": "no_t2r_mark",
            "module_case": None,
            "expected": "No T2R.4 or T2R.5 fact id appears as a point or companion of the frame (forbidden_mark_fact_ids).",
        },
        {
            "case": "tables_unchanged",
            "module_case": None,
            "expected": "The CP-2H tabs (T2R.9 primary, T2R.4-T2R.8) render as in the cases/cp2h-owner FP05 pin; only the frame is added.",
        },
    ]
    fp = d["cases"]["positive"]["FP05"]
    blk = fp["blocks"]["rating-triggers"]
    tab_ids = [t["table_id"] for t in blk["tabs"]]
    return {
        "schema_version": SCHEMA,
        "review_phase": PHASE,
        "figure_group": "B",
        "figure": "DR.6",
        "source_authority": {
            "modules": [module_authority(path)],
            "design": [
                {
                    "page": D_FP05,
                    "sha256": SHA_D_FP05,
                    "lines": [54, 55, 56, 112],
                    "what": "header 'CP-2H · Fig. DR.6' with chip 'Not computable', chRating slot, naFrame call (title, ref G31, reason)",
                },
                {
                    "page": D_CHARTS,
                    "sha256": SHA_D_CHARTS,
                    "lines": [166, 174],
                    "what": "naFrame: dashed box, 'n/a · <ref>', reason",
                },
            ],
            "briefs": [
                {
                    "file": B_FP05,
                    "sha256": SHA_B_FP05,
                    "line": 36,
                    "what": "Rating triggers (CP-2H): thresholds n/a (G31), status Not computable, the bullet chart is an n/a frame",
                }
            ],
            "rulings": [
                "Q-C11 (draw the n/a frame now, existing CP-2H gap shape; a real chart waits for a real agency source)",
                "item 9 of questions.md",
            ],
            "authority_order": "approved page decides the frame; brief confirms; CP-2H oracle supplies the gap shape; inference marked",
        },
        "chart_series": {"DR.6": frame},
        "cases": cases,
        "adversarial_cases": adversarial,
        "scope_limits": [
            "n/a frame only: no T2R.4 or T2R.5 mark; the real headroom chart waits for a real agency source (CP2H-OWNER-LEASE.md:166 item 9).",
            "The design's rating rows table (agency, current, 'thr. G31') and migration view are not part of this figure.",
        ],
        "render": {
            "distressed_restructuring": {
                "pathway": fp["pathway"],
                "block_id": "rating-triggers",
                "owner": blk["owner"],
                "producers": ["CP-2H"],
                "block_kind": blk["kind"],
                "state": blk["state"],
                "primary_tab": tab_ids[0],
                "tabs": tab_ids[1:],
                "tabs_source": "cases/cp2h-owner/expected.json#cases.positive.FP05",
                "figure": {
                    "fig_id": "DR.6",
                    "placement": "above",
                    "chart_kind": "na",
                    "marks": 0,
                    "table_twin_rows": 0,
                },
                "frame_texts": {
                    "title": DR6_FRAME["title"],
                    "reason": {"positive": FRAME_REASON_POSITIVE, "gap": FRAME_REASON_GAP},
                    "ref_spelling": GAP_SPELLING,
                },
                "status_chip": DR6_CHIP,
            }
        },
        "builder_targets": [
            {
                "test_file": "tests/test_chart_render_dr6.py (new)",
                "asserts": [
                    "report_view.build on a distressed_restructuring run with CP-2H (positive and gap owner runs, tests/cp2h_runs.py): block rating-triggers has one figure DR.6 with chart.kind na, zero marks, empty twin and chart.reason equal to the frame reason; no fact id of T2R.4 or T2R.5 appears among the figure's refs",
                    "tabs unchanged: primary T2R.9, tabs T2R.4 to T2R.8",
                    "the frame cites a gap reference spelled '∅ G<n>' (n bound at run time) and the block shows the chip text 'Not computable'",
                ],
            }
        ],
        "questions": [
            "Settled (ruling 6.5): the frame reason is per case and true; the approved-page text is not used.",
        ],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, build in (
        ("cr2-expected.json", build_cr2),
        ("cr3-expected.json", build_cr3),
        ("dr2-expected.json", build_dr2),
        ("dr345-expected.json", build_dr345),
        ("dr6-expected.json", build_dr6),
    ):
        write(name, build())
        print(name, sha(f"cases/charts/{name}"))


if __name__ == "__main__":
    main()
