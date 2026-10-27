# C2 shared CP1 chart consumer — C2-CHART-1

The report and canonical Model destination now share actual S.1–S.4 chart series
through the existing report-view builder. The former populated KPI-table fallback
showed four unavailable figures despite canonical financial facts. This consumer
resolves C1's immutable typed coordinates into existing facts, passports, marks
and exact table twins. Financial arithmetic, source values and calculation JSON
are unchanged.

## Lease, authority and exact identities

Exclusive C2 lease: `src/deploy_vii/report_view.py`, new
`tests/test_cp1_chart_render.py`, and this handoff. Branch `codex/cp1-chart-render`
started at reviewed contract integration `adcd5671e18b98f28595d7db8003ff0df646d802`.
It fast-forwarded to reviewed C1 integration
`3831b1827dbe2e7d2b51d391a734f5ecf077706f`; the exact two owned code/test hashes
were preserved. `work/cp1-chart-consumer/dependency-ff.json` records the transition.
Prior branches, untracked scratch and immutable output packages were preserved.
PR MANAGER owns the reuse-manifest post-import patch record and integration.

LEAD explicitly selected GPT-6.1 Sol/high for financial/provenance implementation
and independent sensitive review. This records assignment and selected route,
not hidden provider telemetry. Paid/provider/live tests remained paused.

SHA256 pins:

| Input / output | SHA256 |
| --- | --- |
| `docs/CP1-CHART-SLICE.md` | `e6e3f4a1853dbdcd142ab9afcfdadeabae5452d48a354c8db00a873359457936` |
| Independent `cases/charts/expected.json` | `2ca2606c46c09ab285d0602b5f95d06a36d61a6aa4e467fbb45e71afbf665276` |
| Independent contract PASS `docs/reviews/cp1-chart-contract.md` | `33ea3771ce732c1b1885441dbf6894ddab8e1bc6cc528a46634e85b981bf0360` |
| Integrated C1 `src/deploy_workflow/financial_series.py` | `9f4d0df14cb14e8dd3e8c3d0c7ed20afa9beadff2ced229a38047478e18caa8c` |
| Final `src/deploy_vii/report_view.py` | `571ee44cbac0a39c3dd77871e13f7f9cc414c4e6700e9e887a70a64b74b7c4cc` |
| Final `tests/test_cp1_chart_render.py` | `ebc353e5dae6154259ea6aa33838fe8e52750b4523da7a7f778582bb04506b63` |
| Historical real-shape probe script | `3745c09dbd7467c75841e2447fc971b6aa170548209a83c7f83ddfd4902d6f0c` |
| Probe serialized figures | `0218b8125ddc3b947285fe1a419400215d447dafa261f5b70809c7810eca3896` |

## Behavior and caller contract

`_chart_fact_cell` reads canonical source-native Decimal amounts through the
existing cell formatter/index. `_cp1_strip` consumes
`cp1_chart_series(ModuleView) -> tuple[FinancialFigureSeries, ...]`; no alternate
producer, duplicate value or private state is added. Primary and companion IDs
must resolve in the selected settled CP1. Raw series membership is checked before
human caption translation. Malformed dimensions/metadata/references fail closed.

S.1 and S.2 are reported leverage and interest-cover lines; early unavailable
ratios retain their G passports. S.3 is three lines for cash, undrawn RCF and total
liquidity, preserving actual numeric zero. S.4 is grouped current principal by
contractual maturity, with current snapshot and not-a-forecast convention visible.
No stacking, future zero bins, annual/Q4 double-counting or recalculation is added.
Each mark and its twin cell are constructed together with identical display text.
Companion context retains period/maturity metadata and existing passport references.
Empty/all-gap shapes preserve actual unavailable reasons. Other lifecycle states
retain existing unavailable output. The three-figure earnings strip is exercised
only for component isolation; broad pathway qualification is not claimed.

Impact set (repository `rg`; no GitNexus index):
`_chart_fact_cell -> _cp1_strip -> _block -> build -> render.render`.
Both `financial_rendering.render_financial_slice` and
`deploy_vii.cp1_render.model_destination_html` use that same render/build path.
SVG rendering, browser assets, toggles, keyboard handling, canonical Model
publication authentication and financial-model/3 schema were not modified.

## Executed verification and causal history

Cwd for all C2 execution: `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-2`.
Pinned runtime and exact focused command (no dependency sync):

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_cp1_chart_render.py
```

All runtime work had exact LEAD admission and ran sequentially. Logs and JSON
records retain argv, PID, UTC interval, exit and input hashes before/after.

| Run | PID | UTC on 2026-10-27 | Exit / result |
| --- | --- | --- | --- |
| RED-1 | 55656 | 06:18:07.360230–07.626743 | 4; fixture import setup failure, not causal RED |
| RED-2 | 55747 | 06:19:34.478773–34.864217 | 4; second fixture import setup failure |
| RED-3 | 57184 | 06:23:41.064297–41.515079 | 1; one causal failure: four `na` instead of line/line/line/grouped |
| GREEN-1 | 59176 | 06:30:38.137950–39.139298 | 1; 23 passed, one candidate/accepted View fixture error before consumer |
| RED-4 | 59607 | 06:34:33.921127–34.451902 | 1; three causal failures for caption alias and two all-gap reason cases |
| GREEN-2 | 59639 | 06:34:57.566521–58.847011 | 1; 26 passed, one old expected-error regex mismatch after correct new guard |
| GREEN-3 | 60225 | 06:37:52.944664–53.791839 | 0; 27 passed in 0.67s |
| FINAL-1 pytest | 61038 | 06:43:25.778478–26.413393 | 0; 27 passed in 0.46s on integrated C1 dependency |
| FINAL-1 probe | 61039 | 06:43:26.413724–29.752933 | 0; all ten historical actual-basis component checks pass |

Final admission: `C2-CHART-FINAL-1`. Source, test, producer and probe-script pins
above were unchanged through both final children. All resource slots were released
to LEAD after completion. No further runtime was started.

The 27 tests cover independent literal expectations, exact precision/zero/gaps,
selected IDs, companion context, twin text and passports, malformed metadata,
dimensions/scale/currency and missing passports, raw/display series collisions,
empty/all-gap reasons and nonsettled/pathway isolation. They use a small typed
producer seam fixture. Real SVG serialization is exercised. The canonical Model
caller test mocks envelope reading; it proves shared consumption, not publication
authentication.

The separate final probe uses the actual integrated C1 producer and shared builder
over the retained immutable actual CP1 raw module
`87af2b93ae1e2a30df57fe0997c1e89f75bee07932501c7074d51155e59f846f`.
It proves four figures, 25 points, nine gaps, Q4 exact 5/3, 1 and 6, four cash
amounts 16.25/17.50/18.75/20, four known RCF zeros, one current principal 50 at
2029-12-31, not-forecast title, exact twins and resolving passports. The raw blob
and inputs remain unchanged. It performs no Execution/financial engine/publication
operation and writes only new C2 component artifacts.

Evidence directories in the C2 checkout:
`artifacts/cp1-chart-red-{1,2,3,4}`, `artifacts/cp1-chart-green-{1,2,3}`,
`artifacts/cp1-chart-final-1`, and `artifacts/cp1-chart-real-shape-1`.
Scratch probe: `work/cp1-chart-consumer/real_shape_probe.py`.
The probe's inner record retains its original REAL-SHAPE-1 label; the outer final
runner record is the authoritative exact admission `C2-CHART-FINAL-1`.

Static checks passed on the final integrated bytes:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m mypy --follow-imports=silent src/deploy_vii/report_view.py
'/Users/ericguei/Documents/Deploy Workflow/.venv/bin/ruff' check --no-cache --select I,F src/deploy_vii/report_view.py tests/test_cp1_chart_render.py
'/Users/ericguei/Documents/Deploy Workflow/.venv/bin/ruff' format --check src/deploy_vii/report_view.py tests/test_cp1_chart_render.py
git diff --check
```

Results: no mypy issues in one source file, all import/F checks passed, two files
already formatted, and clean diff whitespace.

## Confidence and independent sensitive review closure

Independent `chart_sensitive_review` was explicitly dispatched Sol/high, read-only.
It found two concrete P2 issues: undeclared raw series accepted through caption
translation, and loss/refusal of overall all-gap reasons. RED-4 reproduced all
three cases. Root fixes validate raw membership before translation and derive
stable overall reasons from supplied reason plus canonical Fact limitations;
GREEN-3 and FINAL-1 pass. No further product change followed the final pins.

The confidence review ranked and investigated eight categories: identity/caption
trust seam; all-gap error paths; numeric dimensions/finite precision/zero; foreign
primary/companion IDs and duplicates; lifecycle/pathway boundaries; shared caller
seam; companion/twin/passport consistency; mutable state/concurrency/order.
C1's strict `_numeric` validates ratio currency=None and monetary basis/dimensions;
consumer and ChartSpec add display/passport closure. Helpers use local structures,
no I/O/state mutation and stable supplied order. The final actual-shape probe closes
the mock-versus-real producer concern within component scope. No confirmed consumer
defect remains. Full ranked investigation is preserved in
`work/cp1-chart-consumer/confidence-review.md`; execution ledger is alongside it.

Fresh CP0→CP1 actual analytical execution, Model publication/receipt and native
browser acceptance remain LEAD's separately admitted integration phase. Historical
component evidence cannot qualify that new chain or any broader owner/platform.
Old immutable publications and native proof remain unchanged.

## No-argument rewrite tournament

Winner: **Incumbent holds**, preserving `report_view.py:1446–1463` and
`report_view.py:1478–1583`. `_block` is mechanical wiring and was skipped as a
material rewrite target; test/doc changes are exempt.

- Every speed, memory and readability challenger retained the guarded incumbent;
  no verified improvement justified changing its semantics or caller contract.
- The blind arbiter compared identical anonymous snapshots; each match used the
  stable earlier-letter tie break, with no performance or readability win claimed.
- Orchestrator verification on the retained exact source passed all 27 tests,
  actual-data invariants, mypy and caller tracing; the actual final diff was read.

Distinct roles: `tournament_incumbent`, `tournament_speed`, `tournament_memory`,
`tournament_readability`, and fresh blind `chart_tournament_arbiter`. Snapshot
mapping A=speed, B=memory, C=readability, D=incumbent. Bracket A/B→A, A/C→A,
A/D→A; all code identical. Snapshot SHA256
`aaea6db99fbffdfa90857181a93f8e8005d721f87ec64dff308b77ee3ad22c9d`.
All roles were read-only and ran no tests. Anonymous snapshots are preserved in
`work/cp1-chart-consumer/tournament-anonymous.json`; no candidate rewrite was applied.

Verification: exact focused command above, FINAL-1 **27 passed in 0.46s**, plus
historical actual-data probe exit0. Impact-set signatures, return types and pure
behavior remain intact; mypy passes, both downstream paths trace to the same build,
and canonical caller/real SVG tests pass within the stated component scope.

Final retained code (the intervening immutable display-caption map is included):

```python
def _chart_fact_cell(fact: Fact, unit_class: UnitClass, refs: tuple[str, ...]) -> Cell:
    """A chart reads the canonical source-native number, never a display-rounded value."""
    if unit_class == "multiple":
        supported = fact.unit == "MULTIPLE" and fact.scale == 1
    elif unit_class == "amount":
        supported = (
            fact.unit in {"MILLIONS", "currency"}
            and fact.currency == "USD"
            and fact.scale == 1000000
        )
    else:
        supported = False
    if not supported or (fact.status == "known" and fact.amount is None):
        raise ValueError("CP1 chart point has unsupported numeric dimensions")
    cell = _cell(fact, refs)
    if cell.unit_class != unit_class or not (cell.ref_id or cell.gap_ref):
        raise ValueError("CP1 chart point has no compatible canonical passport")
    return cell


_CP1_CHART_LABELS = MappingProxyType(
    {
        "total_leverage_reported": "Total leverage (reported)",
        "net_leverage_reported": "Net leverage (reported)",
        "interest_coverage_reported": "Interest cover (reported)",
        "cash_closing": "Cash",
        "undrawn_rcf": "Undrawn RCF",
        "liquidity": "Total liquidity",
    }
)


def _cp1_strip(
    block_id: str,
    module: ModuleView,
    refs: Mapping[tuple[str, str], tuple[str, ...]],
) -> tuple[Figure, ...]:
    """Render the typed producer's coordinates against this selected CP1 and its index."""
    if module.module_id != "CP-1" or module.status not in {"accepted", "restricted"}:
        return ()
    from deploy_workflow.financial_series import cp1_chart_series

    supplied = cp1_chart_series(module)
    if tuple(item.fig_id for item in supplied) != tuple(
        fig_id for fig_id, _, _ in _STRIP_FIGURES["model-chart-strip"]
    ):
        raise ValueError("CP1 chart producer must supply S.1 through S.4 in order")
    facts = {fact.fact_id: fact for fact in module.facts}
    wanted = {fig_id for fig_id, _, _ in _STRIP_FIGURES[block_id]}

    def current(fact_id: str) -> tuple[Fact, tuple[str, ...]]:
        if fact_id not in facts:
            raise ValueError("CP1 chart references an unknown selected fact")
        return facts[fact_id], refs.get((module.module_id, fact_id), ())

    figures = []
    for spec in supplied:
        if spec.fig_id not in wanted:
            continue
        expected_kind = "grouped" if spec.fig_id == "S.4" else "line"
        expected_class = "multiple" if spec.fig_id in {"S.1", "S.2"} else "amount"
        expected_unit = {"x"} if expected_class == "multiple" else {"US$m", "US$ m"}
        if (
            spec.kind != expected_kind
            or spec.unit_class != expected_class
            or spec.unit not in expected_unit
            or len(set(spec.series)) != len(spec.series)
            or (not spec.points and not spec.reason)
        ):
            raise ValueError("CP1 chart metadata is inconsistent")
        captions = {
            name: _CP1_CHART_LABELS.get(name, name) if spec.fig_id != "S.4" else name
            for name in spec.series
        }
        if len(set(captions.values())) != len(captions):
            raise ValueError("CP1 chart series captions must be distinct")
        marks, rows = [], []
        for index, point in enumerate(spec.points):
            if point.series not in captions:
                raise ValueError("CP1 chart point names an undeclared raw series")
            fact, fact_refs = current(point.fact_id)
            cell = _chart_fact_cell(fact, spec.unit_class, fact_refs)
            caption = captions[point.series]
            labels = [f"{caption} · {point.category}"]
            for companion_id in point.companion_fact_ids:
                companion, companion_refs = current(companion_id)
                companion_cell = _cell(companion, companion_refs)
                companion_ref = companion_cell.gap_ref or companion_cell.ref_id
                label = f"{companion.label}: {companion_cell.text}"
                labels.append(label + (f" [{companion_ref}]" if companion_ref else ""))
            marks.append(
                ChartMark(
                    series=caption,
                    label=point.category,
                    text=cell.text,
                    ref_id=cell.gap_ref or cell.ref_id,
                    value=fact.amount if fact.status == "known" else None,
                )
            )
            rows.append(
                Row(row_id=f"{spec.fig_id}.point.{index}", label=" · ".join(labels), cells=(cell,))
            )
        plottable = any(mark.value is not None for mark in marks)
        if plottable and spec.reason:
            raise ValueError("CP1 unavailable chart metadata carries numeric points")
        reason = spec.reason
        if marks and not plottable:
            limitations = [facts[point.fact_id].limitation for point in spec.points]
            reasons = [text for text in (reason, *limitations) if text]
            reason = "; ".join(dict.fromkeys(reasons))
        twin = Block(
            block_id=f"{block_id}-{spec.fig_id.replace('.', '').lower()}-twin",
            title=f"{spec.title} table",
            owner="MODEL",
            state="populated" if rows else "absent",
            kind="dense",
            scale=spec.unit,
            columns=("Value",),
            rows=tuple(rows),
            note=reason,
        )
        figures.append(
            Figure(
                fig_id=spec.fig_id,
                title=spec.title,
                placement="above",
                chart=ChartSpec(
                    kind=spec.kind,
                    series=tuple(captions.values()),
                    table_twin=twin,
                    marks=tuple(marks),
                    unit=spec.unit,
                    unit_class=spec.unit_class,
                    reason=reason,
                ),
            )
        )
    return tuple(figures)
```
