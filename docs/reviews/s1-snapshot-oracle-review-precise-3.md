<!-- Saved by LEAD from mx-precise review handback, 2026-10-27. -->
## S1 oracle revision 3: scoped re-review (mx-precise), review-precise-3

**Verdict: APPROVE.** N1, N2, N3 and N4 are fixed as ruled. Reproducibility holds and the builder imports no product code. I found no new misreading. One low documentation gap remains (L1), and it does not block the lease.

- **Spec verdict: APPROVE.**
- **Quality verdict: APPROVE.** I found no stubs, fake values or catch-alls. The run-time placeholders are explicit and fail closed.

Every run stayed under 60 s; the longest was about 8 s. No CP-1 `quality` stage was run, and there were no network or provider calls.

### 1. Reproducibility and imports: passed
- I rebuilt the oracle in a scratch copy with `python3 -I` (exit 0), at `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-codex-project-context-a11b1b/0917c043-263f-4fcf-9e1c-492a6fa1cd37/scratchpad/s1-review/r3/`.
- All three sha256 match the repo files: expected 1aa49dd7…70f4, submissions bff9ed18…b35c, manifest 9db0367f…61b1.
- The builder imports only hashlib, json, re, sys, pathlib and `s1_data` (build_s1_oracle.py:11-20). `s1_data.py` imports nothing.

### 2. N1, the S1 CP-1 `source_context`: fixed
- **Product validator.** `validate_source_context` returns 0 issues for both new `cp1_source_context` submissions over the three-source pack, with `pack_sha256` bound.
- **The positive case's `no_events_identified` precondition** (live/tools.py:1078-1088, called through `ToolRules().issues` at financial_workflow.py:346):
  - With no search over `business`, it refuses: "Absence claim without a recorded search: sources.2.event_scan no_events_identified for business; search_pack that source before claiming no events".
  - With `search_pack` scoped to `business`, or unscoped, it returns 0 issues.
  - The gap case's `unassessed` needs no search and gets 0 issues, which agrees with ruling R3-Q2.
- **Through the workflow.** I created the store with `Execution.create` and passed it to the `FinancialWorkflow` constructor directly, because `create()` refuses any `requested_modules` other than the G1 set. I submitted the S1 CP-0 review, then the S1 context, then the financial case's literal `financials`, `narrative` and `readiness` (`{"consumers": []}`).
  - Positive, with business pages 1-3 read and a business `search_pack`: source_context, financials, narrative and readiness all valid.
  - Positive with the same reads but no business search: source_context refused with the message above. This is the product enforcing the precondition.
  - Gap, with business pages 1-2 read: all four stages valid.

### 3. N2 and N3: fixed
- **N2.** The `cp1_references` copies now pin:
  - the fact id as a run-time binding of the CP-1 fact's own id, with the table coordinate kept separately;
  - `value_class` "calculated", which is what the real CP-1 head carried in review-precise-2;
  - cites as the CP-1 fact's own citations.
  
  This agrees with cp2_synthesis.py:837-857. In the composer diff, the only remaining `cp1_references` differences are these run-time placeholders: ids and labels. Everything else in CP-2 is identical.
- **N3.** FIGS names the twelve-month (LTM) basis ending Q4 2025, citing `metric_coordinate_rule`. This matches the LTM Q4 25 T4.10 facts on the real head.

### 4. N4, inherited limitations as ruled in R3-Q1: matches the product
I bound CP-1 text from a CP-1 head settled by the product's own `settle`. Its own limitations were three CP-1-style entries, one of which embeds the LIMIT text; settle added the synthetic-case text and the inherited CP-0 limitations itself. Then I rebuilt each inherited list from the oracle's rule: literal head, then the CP-1 head's limitations, then its inherited limitations, then the literal tail after CP-1; de-duplicated, with own findings removed. The result equals the product's settled `inherited_limitations` for:
- CP-1A positive;
- CP-1A gap, where CP-1 inherits all three CP-0 texts and de-duplication removes them;
- CP-2 positive;
- CP-2 gap.

The settled CP-0 limitations, the CP-1A and CP-2 own limitations and their settled limitations are all identical to expected.json.

### 5. Other changes since review-precise-2
- I re-ran the full composer diff:
  - CP-0: 56 of 56 facts identical; T8 gives "Run CP-1", "Run CP-1A" and "Run CP-2".
  - CP-1A: 410 of 410 facts (positive) and 374 of 374 (gap) identical; claims identical.
  - CP-2: identical apart from the ruled placeholders. Validators give 0 issues once figures are resolved, and refuse closed (6 and 5 issues) while they are unresolved.
- FP01 still matches in both cases on state, owner, kind, lines, tabs and summaries.
- **L1 (Low, documentation only).** The positive context also cites business page:3. live/tools.py `unread_citation_issues` refuses unless that page has been read: "Cited page not read through read_pages: business page:3".
  - expected.json `CP-1.business_entry.positive` names only the `search_pack` precondition, and `execution.tool_use` has no CP-1 entry.
  - Suggested text: "CP-1 source_context: read_pages business page:1 and page:3 and search_pack over business before submit."

Not verified:
- The CP-1 `quality` stage and promotion over the S1 context were excluded by brief, so CP-1's real own and inherited limitation text under R3-Q1 was bound only from a product-settled head with synthetic CP-1 limitations.
- The `FinancialWorkflow` constructor was called directly to bypass `create()`'s G1 `requested_modules` guard, so the G1 owner-workflow path itself was not exercised.
- FP01 was rendered with CP-1 unrun, through `report_view.build`, not owner_rendering or the HTML path.
- No live model run was made.
- Running the product may have refreshed `src/**/__pycache__`. Otherwise the repo is unchanged (git status shows only the untracked `cases/snapshot/` and `work/`).
