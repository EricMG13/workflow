# Task4-A1 — C3 paired-period earnings core

This is the first implementation slice of CP1B, not module/checkpoint acceptance.
The user added C3 and uncapped implementation on2026-10-27. The one-heavy-job rule,
exact exclusive leases, independent sensitive expectations and paid/provider pause
remain. Numeric source/oracle authority: cases/earnings/expected.json and unchanged
cases/financial/manifest.json; C3 preparation07cf6dee33006d629cee3aab2702cbc590eb5030.

## Exact ownership and base

C3 alone may create/modify:

- src/deploy_workflow/earnings.py
- tests/test_earnings.py
- docs/handoffs/cp1b-earnings-core.md

No other product/test/case/shared file is leased. In particular, no registry,
methodology, upstream/submission, Execution/host, binding, report_view, prior
workflow/receipt/publication or Model edits in A1. C1 prepares registration/access;
C2 prepares FP02 binding/render; their preparation is docs-only until separate
reviewed leases. LEAD owns this contract, cases, plan/queue/team/matrix. PM alone
integrates exact accepted commits.

Integrated source-lineage base: d04c19cb237c4125dcb3765cb0745479913a4430, whose
131 source/test/case files equal closed Task3-C source8f9. The implementation
checkout base is the exact subsequent PM-integrated lease/case revision named
in LEAD's admission. Use a fresh branch at that revision; preserve preparation
branch/work. No source writes before committed independent review and admission.

## Public immutable API

Only this pure callable is public in A1:

`build_earnings_delta(module: ModuleView, prior_period_id: str,
current_period_id: str) -> EarningsDeltaReport`

Both return records are frozen dataclasses with slots. Exact fields:

- EarningsDeltaReport: producer_sha256:str; prior_period_id:str;
  current_period_id:str; prior_basis_id:str|None; current_basis_id:str;
  points:tuple[EarningsDeltaPoint,...]; limitations:tuple[str,...].
- EarningsDeltaPoint: measure_id:str; prior_fact_id:str|None;
  current_fact_id:str; companion_fact_ids:tuple[str,...];
  prior_value:Decimal|None; current_value:Decimal|None;
  prior_status:FactStatus; current_status:FactStatus; delta:Decimal|None;
  delta_status:FactStatus; delta_unit:str; growth:Decimal|None;
  growth_status:FactStatus; reason:str|None; unit:str; currency:str|None;
  scale:Decimal. FactStatus is known/missing/conflicting/not_applicable.

Point order/measure IDs are exactly the twelve in the frozen positive oracle.
No I/O, source access, Execution mutation, provider calls or caller-supplied numeric
answers. Never mutate ModuleView/facts. ModuleView must be CP-1 with a present
artifact hash and accepted/restricted status; this is structural checking, not
cryptographic run/issuer/current-attempt authentication. That belongs to the later
workflow/access lease. A1 cannot establish actual stale/foreign-run refusals.

## Coordinate and calculation rules

Use T4.14 exact reported period identities and T4.10 canonical measure rows.
Join own historical basis by identity, never labels, equal values, FY/Q4 aliases
or rolling bases. Adopt the existing length-prefixed model-basis identity for
historical Q:<period_id> / FY:<period_id>; retain selected basis IDs, primary fact
IDs and metric/period companion fact IDs. Do not recompute CP1 ratios or accounting.
Preserve underlying citations by references to the actual selected facts; invent
no source handle/quote/operand or absent prior-period metadata.

Supported scope: reported QUARTER or FY, IFRS consolidated group, USD MILLIONS
scale1000000 for amounts; MULTIPLE or PERCENT with currencyNone/scale1 for ratios.
The two known periods must have the same kind and duration and current follows
prior without overlap. Reject same/reverse or incompatible periods with
ValueError('incompatible_periods'). This chronological earnings-update policy is
an explicit LEAD scope choice, not a source disclosure. Unknown current period
refuses with ValueError('incomplete_register').

Known values use finite Decimal arithmetic in a fresh local Context(prec=38,
rounding=ROUND_HALF_EVEN), restoring the caller context even on refusal. Repeating
results round only under that pinned arithmetic context; no display quantization
or operand pre-rounding. Do not inherit caller precision/rounding/Inexact traps.
Amount/multiple delta=current−prior. Margin
delta=100×(current−prior), in PERCENTAGE_POINTS. Growth is computed only for
revenue/ebitda/adjusted_ebitda as(current−prior)/prior, a PERCENT fraction. Other
growth is None/not_applicable. Known-zero prior leaves the delta known but growth
None/missing with ZERO_DENOMINATOR; no infinity or zero substitution.

If current exists and the requested prior period is absent, retain actual current
values/identities, prior_fact_id/basis/valueNone, prior/delta missing and applicable
growth missing with COMPARATIVE_NOT_SUPPLIED. This is no invented source period.
If either selected existing fact is nonknown, propagate conflict before missing
before not_applicable to the comparison, preserving its explicit limitation;
growth remains not_applicable when that measure has no growth calculation. Q3
trailing leverage remains missing even when Q4 standalone leverage is known.
Missing selected row/basis in a present register is incomplete_register, not a
fabricated source gap. Malformed known/nonknown/nonfinite facts refuse invalid_fact;
selected dimension/perimeter mismatch refuses incompatible_dimensions; duplicate
selected identity refuses ambiguous_coordinate. No partial result on refusal.

Report limitations retain source limitations and explicitly state core-only scope,
no causal-driver/guidance inference, missing comparative income and no broader
nonzero earnings qualification. A1 assigns no Module status or new QA/promotion
rule; actual candidate/restricted settlement policy is frozen with the later
owner bridge. All point statuses/units/values are fixed in the independent oracle.

## Evidence and checks

E-QOQ-FLAT uses source-grounded Q3→Q4 equal92-day quarters: known flat earnings,
cash/debt+1.25USDm, net debt unchanged, no prior leverage comparison. E-NO-YOY keeps
current FY2025 revenue120/EBITDA30 and missing prior/delta/growth. Incompatible
FY→Q4, same/reverse periods, wrong view, dimensions, duplicate/missing coordinates
and malformed facts refuse. Zero-denominator, five-percentage-point and caller-context guards are
explicitly artificial component tests, not actual issuer/nonzero-case proof.

Focused check command, only after a separate fresh per-job admission:

`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/ericguei/Documents/Deploy\ Workflow/.venv/bin/python -m pytest -q tests/test_earnings.py`

Run from the C3 clone. No environment sync or broad suites. Record exact argv,
runtime/source/case hashes, PID/UTC/exit, full failure/pass logs and changed files.
Initial implementation admission authorizes writes only; no heavy job is bundled.
Confidence-review, no-argument rewrite-tournament on changed functions and sensitive
Sol/high review are required before completion/commit. Return exact code commit,
causal cases, review records and source/expected hashes. No actual analytical or
checkpoint acceptance is inferred from these component tests.

## Subsequent dependencies and completion boundary

C1's later registration/access lease must cover CP1B earnings_delta registration,
CP1B-only current-CP1 grants and complete actual selected CP5 scope, with no quote
leakage/pooled identity or partial-review acceptance. C3's later workflow lease
must bind actual begin/tool calls/submission/validation/settlement and fresh upstream
execution; no old-run relabel/import API is presumed. C2's later binding/render
lease owns CP1B T1B.1/T1B.2/T1B.3 into FP02 headline-results, variance-drivers,
kpi-changes, guidance-signals, Evidence/Limitations with actual current passports.
Exact columns/owner bridge/receipt/consumer schemas require their own frozen lease.

The intended real downstream consumer is CP5 integrity_review over its complete
selected current producer set, with an actual settled evidence-referencing review.
Until that dependency is safely leased and demonstrated, downstream acceptance
remains open. Lookup or rendering alone never substitutes for that analytical link.
Do not claim complete CP1B/FP02/CP5 from A1. C1/C2 may prepare independently now;
their implementation need not wait for unrelated modules once their cases and
interfaces are reviewed/committed. No numerical lane cap is reintroduced.
