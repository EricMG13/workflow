# Current offline run guide

This is the working guide for the implemented, bounded slices. It is not an
all-module launcher or a completion claim. [PLAN](../PLAN.md),
[MODULES](MODULES.csv) and [QUEUE](QUEUE.md) retain the unfinished owners and
pathways. Update this guide with each actual supported owner/consumer/delivery;
the Task5 guide item stays open until the complete checkpoint is demonstrated.

## Runtime and ownership

Use this repository's Python3.13.15 environment with `PYTHONPATH=src`.
Dependencies and uv version are pinned in pyproject.toml/uv.lock. A matching
installed environment may be reused read-only; do not sync another project.
The integration checkout has its own `.venv`. For a new local environment with
cached dependencies, the documented setup is `uv sync --locked --offline`.
Product Completion coordinates product implementation, product fixes, design, integration
preparation and non-testing documentation. Pre-Testing owns keys, fixtures, verifiers,
harness/scoring changes, offline/live runs, CI verification, failure diagnosis and
acceptance. On 2026-11-03 the user resumed Product Completion and reported that
Pre-Testing had resumed its proof goal; this does not grant Product Completion provider
authority. The [Nov 2 model-testing ruling](rulings/2026-11-02-model-testing-live.md) is
the existing scoped testing authority. See the [Product Completion plan](superpowers/plans/2026-11-03-product-completion.md)
and [Pre-Testing plan](superpowers/plans/2026-11-03-project-completion.md) for scope and
safeguards, and the reported resumption in the Product Completion
[ledger](../work/product-completion/ledger.md#2026-11-03-resume--execution-batch-1).
Testing authorization does not confer product tool permission.

Current coding-agent routing and lane duties are in [AGENTS.md](../AGENTS.md). PR MANAGER
integrates admitted exact commits. Preserve old branches, work evidence and sealed case
directories. The Oct 28 heavy-job lock was removed; tests need no lock or per-run LEAD
admission record. Retain applicable exact source/runtime/case pins and actual process
evidence for runs.

## Inspect the qualified outputs

The chart slice's portable package is currently at:

`/Users/ericguei/Documents/Codex/2026-10-26/deploy-workflow-lead/outputs/cp1-chart-slice/`

Its README links `positive/report.html`, `positive/model/model.html`, canonical
`positive/model/calculation.json`, the missing-source report, raw evidence,
independent expectations/reviews and the complete SHA256 index. Serve or open the
whole package without rewriting it. Model HTML/calculation/publication receipt
are byte-identical to the recorded actual publication. The output package and
earlier source/Model slice packages are immutable evidence, not scratch inputs.

The qualified synthetic source has reported FY2025 and four quarters, as of
2026-01-10. S.1–S.4 preserve genuine gaps, known RCF zeros and current contractual
maturity. Whole-million visible cash labels retain exact underlying amounts.
The actual financial QA result is59/Restricted/Low; Model technical readiness is
READY. These are separate facts, not a general score/pass policy.
The missing-financial case has actual CP1/Model refusals and no calculation
publication/download. Read CP1-CHART-ACCEPTANCE.md for exact scope/revisions and
native proof. Real issuers, comparative income, forecasts and other pathways are
not qualified by these artifacts.

## Start a fresh supported financial slice

The existing implementation accepts exactly requested_modules=(CP-1,CP-MODEL)
under its frozen financial slice. Setup must supply a validated PreparedPack JSON
with a fresh Run and the independently frozen literal sources in
cases/financial/manifest.json. That case manifest is NOT PreparedPack JSON.
Do not copy settled heads, change an old run's descriptor, inject final Modules
or pass an earnings/legal selection through this exact-selection factory.

Trusted setup chooses new execution, publication and receipt paths. The current
CLI flags are:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  -m deploy_workflow.financial_workflow \
  --directory "$RUN_ROOT/execution" \
  --pack "$PREPARED_PACK" \
  --model-directory "$RUN_ROOT/model" \
  --receipt "$RUN_ROOT/financial-slice.json" \
  --participant offline-analyst
```

Set RUN_ROOT to a new scratch location and PREPARED_PACK to the validated pack.
This command starts the bounded JSON-lines transport; it does not invent reviews
or complete analysis by itself. These instructions were checked against the
current public parser; this documentation change did not execute a new run.

The exact operation tag is `operation`. Supported operations are invoke
(with tool/arguments), read_inputs, submit_review (payload is raw review JSON as a
string), publish_model and write_receipt. There is no arbitrary action, shell,
code or path operation. Keep complete newline-delimited JSON messages and preserve
all raw requests/responses, including validation refusals and repairs.

Run actual CP0 source_readiness, then CP1 source_context, financials, narrative,
readiness and quality in order. Source epochs have separate actual evidence;
search snippets do not substitute page reads. Financials requires all located
statement pages extracted and every extracted observation covered, with actual
period/unit/entity/citation bindings. Later stages read their offered inputs
before submitting the relevant typed review. Python owns arithmetic, validation,
QA and promotion. A review file or test builder alone is not participant proof.

Publish only through publish_model after the actual CP1 promotion permits it.
Then write_receipt seals the completed or genuinely refused run. EOF alone is
not successful closure. A sealed workflow is read-only; do not edit current,
receipt hashes, payloads or journal blobs to resume or manufacture acceptance.
The original financial adapter has no public open/resume factory; use only its
existing supported interruption/refusal behavior and retained evidence.

## Start from the context form

Fill in docs/templates/context-form.html and save the result as `context.json`
(schema context/1) beside the filings it describes. Then prepare a pack from the
context and the filings. Each `--source` is `ID=RELPATH:MEDIA`, where RELPATH is
relative to `--root` and MEDIA is `text`, `pdf` or `xlsx`; the id `context` is
reserved. `--run-id` must be a fresh identifier and `--destination` must not exist:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  -m deploy_workflow.context prepare \
  --context "$PACK_ROOT/context.json" \
  --root "$PACK_ROOT" \
  --run-id "$RUN_ID" \
  --source filing=filing.pdf:pdf \
  --destination "$PREPARED_PACK"
```

The command checks its arguments and the context, and refuses with one problem per
line on stderr (exit 2) before writing anything. It builds the Run (issuer, as-of date,
pathway and its modules) from the context and adds the context file itself to the
pack as the source `context`. CP-0 then assesses that source like any other, with
authority `unknown`. Start the existing workflow with the produced pack as
described in the section above; that section's frozen slice still accepts only its
own exact module selection.

CP-3 reads the context's `quotes` and deal talk as market evidence; CP-3D reads
`quotes` only, not deal talk. A quote older than 30 days is stale. A quote whose
facility id is unknown is a gap.

Beyond `Run`, the quotes above and the pinned assumptions of Phase 6, three more
things in the context are read:

- **List fields are one name per line.** The form writes aliases and guarantors with
  one name per line, so a name may contain a comma. The assumption lists (shocks) stay
  comma-separated.
- **The borrower name is checked, never imposed.** On a delivered credit snapshot the
  "Run context" page shows the borrower, aliases, sector and sponsor, each marked as
  user-supplied with the context line it came from. The borrower name is compared with
  the borrower entities CP-1 located. A mismatch is recorded as the gap
  `borrower_name_mismatch`; it never overrides what CP-1 located, and the CP-0 issuer
  gate is not changed by it.
- **Periods come from the context.** CP-L10 offers the four quarters ending at the
  context's current quarter, and CP-1B takes the context's current and prior period
  instead of the fixed test periods. An earnings run takes quarters or fiscal years of
  one kind (an `h` period or a mixed pair is refused by the reader). Two limits hold:
  CP-1B takes the context pair only for the two pairs its oracle names, q3-2025 to
  q4-2025 (flat) and fy-2024 (absent) to fy-2025; any other context pair is refused
  `unsupported_pair` until Phase 8. For a fiscal-year (non-quarter) context, CP-L10
  offers no quarter list and its step refuses with the issue
  `CP-L10: context_period_not_quarter`.

Every other setting in the file is carried in the pack but is not consumed until the
remaining phases of the context-file plan.

## Valuation from the context

CP-1C reads the context's valuation basis (section 7 of the form) and Python selects
one EV/EBITDA multiple; no model chooses it. Each basis reads these inputs:

- **Automatic** reads the public-peer comps first and takes their median when at least
  3 peers qualify; otherwise the precedent rows, again needing 3 qualifying; otherwise
  the result is Insufficient Information and no multiple is selected. It never blends.
- **Public comps** reads the peer rows (EV, EBITDA, date, source) and takes their median.
  Peer figures come only from `peer_source: user_comps`. With `user_list` (names only) or
  `cp_dr_public` the public comps have no figures: `public_comps` is a fixed gap and
  `auto` falls to the precedents.
- **Precedents** reads the private-transaction rows and takes their median.
- **Blend** takes the plain average of the public-comps median and the precedents
  median; each set needs 3 qualifying rows or the basis states a gap (no fallback).
- **Issuer's own trading multiple** reads the issuer's market cap and net debt (or a
  stated EV) over CP-1 LTM adjusted EBITDA. An NTM EBITDA basis is a gap.
- **My own multiple** takes your value and labels it user-supplied.

A requested basis that cannot be formed is stated as a gap; it never falls back to
another basis. A peer row needs EV and EBITDA above zero to qualify.

Currency and period: user-supplied peer figures carry no currency or period of their
own. The tables show those cells as `Not stated by the user` and do not restate or
convert the figures; the other CP-1C tables are unchanged.

Windows: a row qualifies only if its date falls within 12 months of the as-of date for
public comps and 36 months for precedents. The windows also apply to `blend`. A row
with no date is excluded.

CP-4C uses the selected multiple. A valuation case whose multiple differs from the
selected one is refused (fail closed), the stress case included. A multiple you pin in
the context assumptions for CP-4C wins over the selection; the selection is then
recorded in CP-4C's limitation.

The comparison is at two decimals. The selected multiple is rounded half-even to 2
decimal places, and CP-4C compares numerically, so `7` equals `7.00`.

A context with no valuation to show produces the same pack as before (the eight CP-1C
tables, no EV tables). A valuation is shown when any of these holds: the peer source is
`user_comps`; precedents are listed; the basis is automatic, the issuer's own trading
multiple or my own multiple; or the peer source is `user_list` or `cp_dr_public` and the
basis is automatic, public comps or blend.

## Verify and deliver a sealed financial slice

The public read-only verifier is
`verify_financial_slice_receipt(store, receipt, *, model_directory=None)` in
financial_workflow. It authenticates the actual sealed participation and selected
publication; loading a plausible JSON shape alone does not.

The delivery API is
`render_financial_slice(execution_directory, receipt_path, model_directory, destination)`
in financial_rendering. Use a NEW destination. It verifies current inputs, stages
export and reverifies before delivery. Positive delivery copies canonical Model
files and calculation JSON; the genuine refusal case supplies model_directory=None
and exposes no false Model/calculation link. Verification/rendering can replay a
large historical financial case and is a heavy job, not a cheap availability
check. It does not itself qualify a new analyst, settlement or pathway.

Native acceptance inspects actual selected-run sections, Chart/Table controls,
known-zero/gap marks, exact fact/source passports, Evidence/Limitations and clicked
calculation JSON. Use bounded visible DOM/screenshots and close the owned server/
browser after proof. Do not claim full-page accessibility export where it was not
read. Preserve delivered bytes and source inputs through the check.

## Checks and current limits

Use the currently admitted focused argv in QUEUE/handoffs. The relevant fast
component cohorts completed439 cases on c5c6a691:218 passed before an intentional
SIGINT of the historical financial-render fixture, then221 disjoint remaining
cases passed. The source/runtime stayed unchanged. This is NOT a single fully
passed broad-suite command. The remaining heavy historical-render cases and
full financial_workflow suite were excluded from that integration claim.

`tests/test_financial_render.py` indirectly builds full historical CP1/Model
fixtures via test_financial_workflow, even when the latter module is not selected.
Inspect fixture dependencies before scheduling a supposedly fast command.
Do not rerun successful scopes without changed bytes or a concrete unresolved
concern. Component fixtures, registered tools and direct composers stay component
evidence until actual permitted calls, settlement, consumer and rendered proof.

CP1B's pure core, registration/access and FP02 bindings are component-verified.
The additive projection pager and new owner workflow have separate exact leases;
their implemented/runtime status must come from QUEUE and MODULES, not contract
existence. Its first fresh selection is CP1B+CP5 with no Model publication; it
cannot reuse the old financial-only receipt/verifier. Actual complete CP5/final
seal and authenticated earnings delivery/native proof remain required.

The legal manifest freezes selected legal terms and expected positive/definition-gap
results only. It does not supply CP4 tool execution/settlement, complete CP5, typed
FP04/native proof or refinancing/recovery owners. All remaining owners and the six
assembled pathways remain open. See PRODUCTION-BACKLOG.md for deferred work;
checkpoint source/version/attachment safety is not deferred merely because it
also matters in production.
