"""Figure producers of the Distressed & Restructuring Front Page (Stage 3 W2 group d).

DR.2 (recovery by class) and DR.3 to DR.5 (value allocation waterfalls) read a settled CP-4C
through ``deploy_workflow.restructuring_series``; DR.6 is CP-2H's rating trigger headroom frame.
Values come only from the settled module view: amount, status, unit and the report's ``G#`` are
read from the facts, a missing or not-meaningful fact is a gap mark with its ``G#`` and never 0,
and no chart recomputes a value. ``report_view`` registers ``PRODUCERS`` in its group d block.
"""

from collections.abc import Mapping

from deploy_vii.contracts import Fact, ModuleView, View
from deploy_vii.display import UnitClass, format_value
from deploy_vii.report_view import (
    Block,
    Cell,
    ChartMark,
    ChartSpec,
    Figure,
    FigureProducer,
    Row,
    _cell,
    _chart_fact_cell,
    _chart_mark,
    scale_label,
)

_SETTLED = frozenset({"accepted", "restricted"})
_Refs = Mapping[tuple[str, str], tuple[str, ...]]

# DR.6 frame copy (cases/charts/dr6-expected.json render.frame_texts). The approved page's "no
# agency report in the Source Pack" (G31) is not true here: CP-2H reads one synthetic agency
# source, so the frame says a chart waits for a real report.
DR6_TITLE = "Rating trigger headroom"
DR6_CHIP = "Not computable"  # the design's block-head chip for the n/a frame (OI-13)
DR6_SYNTHETIC = "agency source is synthetic; a headroom chart waits for a real agency report"
DR6_UNSTATED = (
    "a trigger threshold is not stated in the synthetic agency source; "
    "a headroom chart waits for a real agency report"
)
_HEADROOM_TABLES = frozenset({"T2R.4", "T2R.5"})


def _module(view: View, module_id: str) -> ModuleView | None:
    module = next((m for m in view.modules if m.module_id == module_id), None)
    return module if module is not None and module.status in _SETTLED else None


def _point_cell(fact: Fact, unit_class: UnitClass, refs: tuple[str, ...]) -> Cell:
    """A known fact reads through the canonical chart path; any other status is a gap cell."""
    if fact.status == "known":
        return _chart_fact_cell(fact, unit_class, refs)
    cell = _cell(fact, refs)
    if cell.unit_class != unit_class or cell.gap_ref is None:
        raise ValueError(f"CP-4C chart gap has no compatible G# passport: {fact.fact_id}")
    return cell


def _cp4c_figures(
    view: View, refs: _Refs, block_id: str, wanted: frozenset[str]
) -> tuple[Figure, ...]:
    from deploy_workflow.restructuring_series import cp4c_chart_series

    module = _module(view, "CP-4C")
    if module is None:
        return ()
    facts = {fact.fact_id: fact for fact in module.facts}

    def current(fact_id: str) -> tuple[Fact, tuple[str, ...]]:
        if fact_id not in facts:
            raise ValueError(f"CP-4C chart references an unknown fact: {fact_id}")
        return facts[fact_id], refs.get((module.module_id, fact_id), ())

    figures = []
    for spec in cp4c_chart_series(module):
        if spec.fig_id not in wanted:
            continue
        unit = "%" if spec.unit_class == "percent" else scale_label(spec.unit, spec.currency)
        marks: list[ChartMark] = []
        cells: list[Cell] = []
        for point in spec.points:
            fact, fact_refs = current(point.fact_id)
            for companion in point.companion_fact_ids:
                current(companion)  # every companion belongs to this settled module
            cell = _point_cell(fact, spec.unit_class, fact_refs)
            mark = _chart_mark(
                fact, cell, series=point.series, label=point.category, role=point.role
            )
            marks.append(mark.model_copy(update={"hatched": point.hatched}))
            cells.append(cell)
        if spec.fig_id == "DR.2":  # one row per class, one cell per scenario, class-major
            categories = list(dict.fromkeys(p.category for p in spec.points))
            by_category = {
                category: tuple(
                    c for c, p in zip(cells, spec.points, strict=True) if p.category == category
                )
                for category in categories
            }
            header, columns = "Class", spec.series
            rows = tuple(
                Row(row_id=f"DR.2.class.{n}", label=category, cells=by_category[category])
                for n, category in enumerate(categories)
            )
        else:  # one row per waterfall step, one cell
            header, columns = "Step", (unit or spec.unit,)
            rows = tuple(
                Row(row_id=f"{spec.fig_id}.step.{n}", label=p.category, cells=(c,))
                for n, (p, c) in enumerate(zip(spec.points, cells, strict=True))
            )
        twin = Block(
            block_id=f"{block_id}-{spec.fig_id.replace('.', '').lower()}-twin",
            title=f"{spec.title} table",
            owner=module.module_id,
            state="populated" if rows else "absent",
            kind="dense",
            scale=unit,
            row_header=header,
            columns=columns,
            rows=rows,
            note=spec.reason,
        )
        figures.append(
            Figure(
                fig_id=spec.fig_id,
                title=spec.title,
                placement="above",
                chart=ChartSpec(
                    kind=spec.kind,
                    series=spec.series,
                    table_twin=twin,
                    marks=tuple(marks),
                    unit=unit,
                    unit_class=spec.unit_class,
                    reason=spec.reason,
                ),
            )
        )
    return tuple(figures)


def recovery_by_class_figures(block_id: str, view: View, refs: _Refs) -> tuple[Figure, ...]:
    """DR.2 beside CP-4C's recovery tables (``recovery-by-class``)."""
    return _cp4c_figures(view, refs, block_id, frozenset({"DR.2"}))


def value_allocation_figures(block_id: str, view: View, refs: _Refs) -> tuple[Figure, ...]:
    """DR.3 to DR.5 above CP-4C's claims and valuation tables (``value-allocation-claims``)."""
    return _cp4c_figures(view, refs, block_id, frozenset({"DR.3", "DR.4", "DR.5"}))


def rating_trigger_figures(block_id: str, view: View, refs: _Refs) -> tuple[Figure, ...]:
    """DR.6, the n/a frame of a settled CP-2H (``rating-triggers``): no T2R.4 or T2R.5 mark.

    The reason is true for the run: the agency source is synthetic. Where settled T2R.4 or
    T2R.5 facts are missing it says a threshold is not stated and cites their ``∅ G<n>``, bound
    from the report index; nothing is drawn for those facts and no gap becomes 0.
    """
    module = _module(view, "CP-2H")
    if module is None:
        return ()
    if "synthetic source" not in " ".join(module.limitations):
        raise ValueError("CP-2H no longer states a synthetic agency source; DR.6 text is stale")
    cited: list[str] = []
    for fact in module.facts:
        if fact.table_id in _HEADROOM_TABLES and fact.status == "missing":
            gap = next(
                (r for r in refs.get((module.module_id, fact.fact_id), ()) if r.startswith("G")),
                None,
            )
            if gap is None:
                raise ValueError(f"CP-2H missing fact has no G# passport: {fact.fact_id}")
            cited.append(gap)
    if cited:
        gaps = ", ".join(format_value(None, "text", "gap", gap_id=g) for g in dict.fromkeys(cited))
        reason = f"{DR6_UNSTATED} ({gaps})"
    else:
        reason = DR6_SYNTHETIC
    twin = Block(
        block_id=f"{block_id}-dr6-twin",
        title=f"{DR6_TITLE} table",
        owner=module.module_id,
        state="absent",
        kind="dense",
        note=f"Absent: {reason}.",
    )
    chart = ChartSpec(
        kind="na",
        series=(),
        table_twin=twin,
        marks=(),
        unit_class="multiple",
        reason=reason,
    )
    return (
        Figure(
            fig_id="DR.6", title=DR6_TITLE, chart=chart, placement="above", status_chip=DR6_CHIP
        ),
    )


# block id -> producer, for report_view's group d registration block.
PRODUCERS: tuple[tuple[str, FigureProducer], ...] = (
    ("recovery-by-class", recovery_by_class_figures),
    ("value-allocation-claims", value_allocation_figures),
    ("rating-triggers", rating_trigger_figures),
)
