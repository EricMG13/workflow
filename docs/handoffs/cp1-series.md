# C1 CP1 chart series — Task3-C

Lease C1-SERIES-1 starts at `adcd5671e18b98f28595d7db8003ff0df646d802` on
`codex/cp1-series`. Exactly the new financial_series.py, test_financial_series.py
and this handoff belong to C1. Prior branch and untracked actual-run evidence are
preserved. Paid/provider/live tests stay paused.

LEAD explicitly assigned GPT-6.1 Sol/high for financial/provenance implementation
and sensitive review. This records the requested assignment, not hidden model
telemetry. Frozen authority: docs/CP1-CHART-SLICE.md, cases/charts/expected.json,
docs/reviews/cp1-chart-contract.md. The oracle predates candidate code.

## Interface and boundaries

The new pure leaf returns immutable figure/point records containing canonical
fact IDs and companion IDs only. C2 resolves existing facts and report passports;
the producer has no financial arithmetic, source/state access, ChartSpec dependency
or duplicate values. Existing financial-model/3 JSON remains unchanged.

The strict quarter join uses the adopted length-prefixed model-basis identity for
historical Q:<period_id>, checked against T4.14 QUARTER metadata. FY/LTM labels or
equal values are never alternate joins. Monetary values retain USD MILLIONS and
scale1000000; ratio units remain MULTIPLE/scale1.

## Verification ledger

- Initial requested RED launch did not start pytest: C1 has no local .venv.
  FileNotFoundError occurred in the launcher before a child could start. Empty
  work/cp1-series/red.log retained. Corrected pinned-runtime admission requested;
  this is not a RED test result.
- At the initial draft, implementation and all reviews were pending. The executed
  evidence and final closure below supersede that initial state.

Fresh actual CP0→five CP1 stages→QA/promotion→Model→sealed receipt will follow
integration and separate resource admission, using a new directory. Old sealed
stores/publications will never be repointed, reopened or overwritten.

## Executed component evidence

Exact command, C1 cwd, pinned runtime read-only (no environment sync):

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_financial_series.py
```

- RED-1R PID55560, 06:17:47.685359–47.988880 UTC, exit2: expected missing
  financial_series import, 0.17s; test7c3d7531 unchanged.
- GREEN-1 PID56703, 06:21:39.092927–39.449579 UTC, exit1: all17 failed at
  fixture construction, before producer invocation. Numeric fixture facts lacked
  mandatory units. Corrected the fixture before initial Fact construction.
- GREEN-2 PID57498, 06:24:28.884366–29.157809 UTC, exit0:17 passed/0.14s.
  Source2f795f00/testa1547947 unchanged through exit.
- ADVERSE-RED-1 PID58566, 06:27:18.383128–18.679796 UTC, exit1:
 17 passed and3 expected DID NOT RAISE failures/0.17s. Exact source2f795f00 and
  test3ef37f99 were unchanged.
- ADVERSE-GREEN-1 PID59045, 06:29:14.252011–14.562860 UTC, exit0:
 20 passed/0.16s. Root guards added for hidden missing implementation under missing
  quarters, malformed nonknown maturity payloads and unsupported period kinds.
  Source0b1345e6/test3ef37f99 unchanged.
- REAL-SHAPE-1 PID59046, 06:29:14.563683–15.371955 UTC, exit0:
  pure projection over retained actual CP1 blob87af2b93, compared to independent
  oracle.25 exact point coordinates/amounts,9 existing null facts,4 known RCF0,
  native dimensions, current50 principal and2029-12-31 maturity all matched.
  Both raw old blob and source/test/probe hashes unchanged. This is historical
  component compatibility only, with no Execution, financial engine, old Model
  verifier, analytical tool or publication call.

Full separate logs, PID/UTC/argv/before-after hash JSON records and probe script
are retained in C1 work/cp1-series/. Source/test/probe hashes are in those records;
no output was copied into the prior actual-run directories.

## Confidence review — current projection

Least confident about (ranked):

1. Missing financial structure masking a missing implementation. Traced quarter
   coverage and required metric lookup; combined missing-quarter/missing-metric
   fixture causally failed. Fixed by checking required metric existence before
   coverage fallback; ADVERSE-GREEN-1 passes.
2. Gap early returns bypassing malformed maturity evidence. Causal nonknown
   maturity-with-text fixture failed; central register validation now rejects it.
   Scoped independent re-review identified a residual empty-period bypass;
   its dedicated causal check and minimal fix were pending at this checkpoint;
   they are closed by the final guard record below.
3. A forecast/unknown period selected as a current exposure. Causal FORECAST
   fixture failed; explicit supported QUARTER/FY/PERIOD_END kinds now refuse it.
4. FY/Q4 double-counting or stale facility fallback. Traced identity-based
   snapshot selection and required population; explicit duplicate alias returns
   one principal50, conflicting alias refuses, missing current row stays empty.
   Focused tests and REAL-SHAPE-1 verify the qualified real population.
5. Quarter/TTM confusion or value-based joins. Canonical field hash comes from
   historical Q:<source period id>; exact dates are a consistency check after
   that join. FY/LTM fields cannot substitute. Fixture and real artifact retain
   nine unavailable early ratios and Q4 exact5/3,1,6; Python arithmetic unchanged.
6. Native scale, zero/missing and liquidity composition. Every primary point has
   explicit dimension validation. No arithmetic or headroom computation exists;
   only cash_closing/undrawn_rcf/liquidity facts are selected. Source-first tests
   and actual-shape probe verify millions, four numeric zeros and missing RCF.
7. Current identity/provenance leaks or mutable results. Duplicate fact IDs and
   table/row/field coordinates refuse; point/companion IDs are selected directly
   from the same ModuleView. Records are frozen; no global mutable state or I/O.
   C2 resolves existing report-wide references. Authenticity, denominators and
   entirely omitted facilities remain upstream envelope/computation/validated-
   register obligations; the projection cannot manufacture that authority.

Independent sensitive review used fresh explicit gpt-6.1-sol/high dispatch
series_financial_review. Initial static no-material-findings did not cover the
later combined inputs; scoped re-review caught the residual described above.
An accidental fixed-medium role was immediately interrupted and disqualified;
none of its output is accepted as financial review evidence. Final scoped closure
and no-argument tournament were pending at this checkpoint; both are closed below.

## Tournament scope and impact

No-argument post-edit scope is the actual git diff against HEAD: new producer and
tests/handoff. Two most material symbols: _quarter_figures and _maturity_figure.
Skipped this pass: small helpers _text/_rows/_periods/_basis/_numeric and the
entry dispatcher; their guards are covered by confidence/sensitive review and
focused tests. Test/doc/generated evidence files are exempt.

No GitNexus index is present. Repository rg found the public dispatcher as the
only direct caller of both private targets. Public cp1_chart_series is used by
the focused test and the leased C2 report_view build/_block consumer. That seam
serves canonical _page→model_destination_html→render→build and delivered
render_financial_slice→render→build. Exact public signatures/record fields and
no-side-effect behavior are hard invariants; typed compilation is the local
caller oracle, with integrated C2 checks owned by the consumer/integrator.


## Final guard closure and independent review

The additional empty-period suspect was causally reproduced: PID59275,
06:32:11.386305–11.704062 UTC, exit1,20 passed/1 DID NOT RAISE (0.17s).
Moved existing T4.18 row validation before the empty-period gate. PID59276,
06:32:11.705164–11.991866 UTC, exit0,21 passed/0.15s; sourcefbd7daae and
test7dfeacfa unchanged. Historical probe PID59277,06:32:11.992564–12.755318
UTC, exit0,25 exact points/9 null/4 RCF0; old blob and inputs unchanged.

Existing independent Sol/high reviewer statically confirmed the one-line move
closes the residual. Reversing that move in a read-only byte stream exactly
recreates0b1345e6; no additional source changes. No findings remain in that scope.
The complete confidence sweep above now has four confirmed defects fixed at root;
all other points are verified as described or explicit upstream obligations.
No hidden runtime telemetry, independent executed-test claim, new financial
engine, provider call, production or broad owner qualification is implied.

## No-argument rewrite tournament result

Winner: **Snippet B**, replacing the two material symbols _quarter_figures and
_maturity_figure. Original guarded sourcefbd7daae was backed up before applying.

- Reuses four canonical quarter coordinate tuples instead of deriving them for
  every series; exact selected facts, categories and companion order remain intact.
- Makes quarter continuity explicit in a sequential loop; keeps all dimensional,
  gap and malformed-identity guards.
- Hoists facility field/period sets and avoids reflexive alias comparisons without
  weakening cross-period conflict checks or current principal semantics.

Distinct explicit gpt-6.1-sol/high roles: series_incumbent, series_speed,
series_memory, series_readability and blind series_arbiter. Maximum three active
review agents; none executed tests, engines, providers or product edits.

Anonymous bracket: A vs B → B; B vs C → B; B vs D → B. A/B/C were speed/memory/
readability proposals; D the guarded incumbent. After three root guards and the
fourth empty-period guard, the orchestrator mechanically carried the same guards
into every proposal before blind comparison. Common helpers were identical.
The arbiter saw anonymous complete sources, not role advocacy. Full proposals,
anonymous variants and the pre-apply backup are in work/cp1-series/tournament/.

Orchestrator read full winner and diff, applied B in-tree and statically rechecked
Ruff I/F, strict mypy and git diff --check. Existing independent financial reviewer
then compared exact9f4d0df1 againstfbd7daae: same financial acceptance/rejection,
series/quarter point order, primary and companion IDs, exact API, aliases and all
four guards; no counterexample or remaining finding. Executed winner verification
and its exact final identities will be recorded below before commit.

Final code for the two winning symbols:

```python
def _quarter_figures(
    module: ModuleView, periods: tuple[_Period, ...]
) -> tuple[FinancialFigureSeries, ...]:
    quarters = tuple(p for p in periods if p.kind == "QUARTER")
    reason = None
    if len(quarters) != 4:
        reason = "Charts require exactly four reported QUARTER periods; no periods were fabricated."
    else:
        year = _text(quarters[0].row["fiscal_year"])
        previous_end = None
        for number, period in zip(("1", "2", "3", "4"), quarters, strict=True):
            start = date.fromisoformat(_text(period.row["start_date"]))
            if (_text(period.row["fiscal_year"]) != year
                    or _text(period.row["fiscal_quarter"]).removeprefix("Q") != number
                    or start > period.end
                    or (previous_end is not None and start != previous_end + timedelta(days=1))):
                raise ValueError("Ambiguous or noncontiguous QUARTER identities")
            previous_end = period.end
    metrics: dict[str, dict[str, Fact]] = {}
    for row in _rows(module, "T4.10"):
        if "field_1" not in row:
            raise ValueError("Missing KPI metric identity")
        key = _text(row["field_1"])
        if key in metrics:
            raise ValueError("Duplicate KPI metric identity")
        metrics[key] = row

    coordinates = []
    if reason is None:
        for period in quarters:
            dates = f"{_text(period.row['start_date'])} to {period.end.isoformat()}"
            category = (f"Q{_text(period.row['fiscal_quarter']).removeprefix('Q')} "
                        f"{_text(period.row['fiscal_year'])}")
            companions = tuple(period.row[k].fact_id for k in _PERIOD_FIELDS)
            coordinates.append((period.identity, _basis(period.identity), dates, category, companions))

    figures = []
    for fig_id, title, series in _SERIES:
        money = fig_id == "S.3"
        points = []
        for key in series:
            if key not in metrics:
                raise ValueError(f"Missing chart metric implementation: {key}")
        if reason is None:
            for key in series:
                metric = metrics[key]
                metric_id = metric["field_1"].fact_id
                for identity, field, dates, category, period_companions in coordinates:
                    if field not in metric:
                        raise ValueError(f"Missing canonical QUARTER basis: {key}/{identity}")
                    fact = metric[field]
                    _numeric(fact, money)
                    if fact.period is None or fact.period.rsplit(": ", 1)[-1] != dates:
                        raise ValueError("Chart fact does not match its canonical QUARTER dates")
                    companions = (metric_id, *period_companions)
                    points.append(FinancialSeriesPoint(key, category, fact.fact_id, companions))
        figures.append(FinancialFigureSeries(fig_id, title, "line", "amount" if money else "multiple",
                                             "US$m" if money else "x", series, tuple(points), reason))
    return tuple(figures)

def _maturity_figure(module: ModuleView, periods: tuple[_Period, ...]) -> FinancialFigureSeries:
    rows = _rows(module, "T4.18")
    title = "Maturity wall"
    reason = "No complete current facility snapshot is supplied."
    points: list[FinancialSeriesPoint] = []
    series: list[str] = []
    if periods:
        latest = max(p.end for p in periods)
        current = tuple(p for p in periods if p.end == latest)
        # An explicit reported quarter wins over its FY alias, never by value or label.
        selected = tuple(p for p in current if p.kind == "QUARTER") or current
        if len(selected) != 1:
            raise ValueError("Ambiguous current facility snapshot period")
        period = selected[0]
        title = f"Maturity wall — principal at {latest.isoformat()} (not a forecast)"
        indexed: dict[tuple[str, str], dict[str, Fact]] = {}
        required = ("facility_id", "facility_name", "period_id", "facility_type", "principal",
                    "currency", "maturity_date", "annual_amortisation", "lease_classification")
        required_fields = frozenset(required)
        period_ids = {p.identity for p in periods}
        for row in rows:
            if not required_fields <= row.keys():
                raise ValueError("Incomplete facility chart coordinates")
            fid, pid = _text(row["facility_id"]), _text(row["period_id"])
            if pid not in period_ids or any(f.period != pid for f in row.values()):
                raise ValueError("Foreign facility period")
            if (fid, pid) in indexed:
                raise ValueError("Duplicate facility snapshot identity")
            indexed[fid, pid] = row
        population = {fid for fid, _ in indexed}
        actual = {fid for fid, pid in indexed if pid == period.identity}
        if population and actual == population:
            reason = ""
            for fid in sorted(population):
                row = indexed[fid, period.identity]
                # FY/Q4 are aliases only when the facility identity AND its terms agree.
                for alias in current:
                    other = indexed.get((fid, alias.identity))
                    if other is None:
                        raise ValueError("Incomplete same-date facility snapshot alias")
                    if other is row:
                        continue
                    for key in required:
                        if key == "period_id":
                            continue
                        a, b = row[key], other[key]
                        if (a.amount, a.text, a.status, a.unit, a.currency, a.scale, a.basis) != (
                                b.amount, b.text, b.status, b.unit, b.currency, b.scale, b.basis):
                            raise ValueError("Conflicting same-date facility snapshot aliases")
                if _text(row["currency"]) != "USD" or _text(row["lease_classification"]) != "NOT_LEASE":
                    raise ValueError("Unsupported facility currency or lease scope")
                _numeric(row["principal"], True)
                if row["maturity_date"].status != "known":
                    reason = f"Contractual maturity unavailable: {row['maturity_date'].fact_id}"
                    break
                maturity = date.fromisoformat(_text(row["maturity_date"]))
                label = f"{_text(row['facility_name'])} ({fid})"
                companions = tuple(row[k].fact_id for k in required if k != "principal") + tuple(
                    period.row[k].fact_id for k in _PERIOD_FIELDS)
                series.append(label)
                points.append(FinancialSeriesPoint(label, maturity.isoformat(), row["principal"].fact_id,
                                                   companions))
    return FinancialFigureSeries("S.4", title, "grouped", "amount", "US$m",
                                 tuple(series) if not reason else (),
                                 tuple(points) if not reason else (), reason or None)

```


## Final executed winner verification and confidence closure

Winner B is applied in-tree. Exact source SHA256:
`9f4d0df14cb14e8dd3e8c3d0c7ed20afa9beadff2ced229a38047478e18caa8c`.
Exact test SHA256:
`7dfeacfa8fbe704990bc357cdfd7e11bf7fee57fadcd2c451075d7750acc46e6`.

- Orchestrator verification: exact focused pytest command above, PID59781,
  2026-10-27 06:35:51.660864–51.951079 UTC, exit0: **21 passed in0.15s**.
- Concrete invariant spot-check: same pinned runtime, env and cwd, with
  `work/cp1-series/real-shape-probe.py`, PID59782,
  06:35:51.951800–52.722900 UTC, exit0. The retained raw87af CP1 module produces
  exactly25 points,9 nulls,4 actual RCF zeros, exact quarter identities/amounts,
  native units/basis and one current principal50 at contractual2029-12-31.
- Full separate logs/JSON are work/cp1-series/tournament-verify.{log,json} and
  real-shape-final.{log,json}. Before/after source/test/probe hashes match. Probe
  SHA is `c59a6533e47dd8360a61e51965cf485efd0abcbafb672061426d35a2ab550304`.
  The old87af raw blob hash is unchanged. No old publication was verified/rebuilt.
- Caller contract check: Ruff I/F and strict mypy (`--follow-imports=silent`)
  pass on the actual winning producer; focused tests import the unchanged public
  signature. Actual C2 downstream build/publication integration remains consumer/
  integrator acceptance, not a claim made by this leaf component check.
- Orchestrator inspected the actual diff and full winning code. Four confirmed
  confidence/sensitive-review defects have causal RED→GREEN checks. All seven
  ranked categories above are resolved by execution/static tracing or explicitly
  bounded upstream obligations. No remaining material producer finding.
- No concurrency mutation or state transition exists in the projection. Source
  stayed frozen through every child; all admitted C1 test/probe children exited.

By design: unsupported period kinds/currency/unit/perimeter fail closed; absent
four-quarter coverage yields explicit unsupported figures; absent current
facility/maturity evidence yields an explicit empty wall. Nonsettled/foreign
modules return no series. Missing metric implementations and malformed accepted
coordinates refuse. Entirely omitted facilities, authenticity and denominator
correctness require upstream accepted-register/envelope/computation validation.

Still outside this component closure: fresh actual analytical chain/publication,
C2 SVG/table/passport/native proof, integrated same-revision assembled acceptance,
and broader owners/pathways/provider/production qualification. These are not
replaced by the historical-shape probe. Paid/provider/live tests remain paused.
