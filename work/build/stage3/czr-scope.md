# CZR real-data case: scope check (Explore agent adbbc43f, read-only, s2-release ab9777f)

Case (Workflow Test, untracked in `../project-goals-overview-6dc197`): `case_kind="public"`, `earnings_update`, `requested_modules=(CP-1, CP-1B, CP-2, CP-5)`, three filed `.txt` documents; data-only test `tests/test_czr_case.py`; no recorded submissions.

## Gaps, smallest scope first
- **A. CP-0 only.** No code. Data: a pack of the three documents plus an authored CP-0 review. It proves nothing against the CZR keys.
- **B. CP-0 + CP-1.** Needs two code changes and authored data:
  - **Gap 1 (shared interface).** The CP-1 `financials` precheck heading regex (`financial_workflow.py:351-364`, duplicated at `earnings_workflow.py:1108`) matches none of the 10-Q headings ("CONSOLIDATED CONDENSED BALANCE SHEETS", "...STATEMENTS OF OPERATIONS"). `owner_workflow.py:5-6` treats the module as imported, never edited.
  - **Gap 2 (`src/deploy_vii`).** `statement_extract.py:11-14` splits cells on two or more spaces. CZR tables are delimited by ` | `, so no lines are extracted.
  - **Driver.** It must split each `.txt` into `page:N` spans (`live/tools.py:396-431`) while keeping `Source.sha256` as the file hash.
  - **Data.** Five authored CP-1 stages written from the documents, with real statement lines, facilities and FY/YTD/QUARTER periods.
- **C. CP-1, CP-2, CP-5.** The plan becomes CP-0, CP-1, CP-1A, CP-2, CP-5; CP-2 requires CP-1A.
  - Code: gaps 1 and 2.
  - Data: CP-1A `business_context` from the 10-K; a CP-0 review of all four modules; CP-2 and CP-5 submissions with run-time fact binding.
  - Driver: a CZR figure binding (`s1a_runs.figure_fact` hard-codes T4.10 and "LTM Q4 25"). No CP-5 run driver exists.
- **D. Full CP-1, CP-1B, CP-2, CP-5.** `_check_specs` refuses CP-1B today.
  - **Gap 3 (shared interface + registry).** CP-1B is not in `SUPPORTED_ANALYTICAL`, `OWNER_SPECS` or `_CORES`. It cannot be added as `model_payload` (registry `shared_live=False` keeps `earnings_delta` out of `STEPS`) or as a core (`_check_steps` :905). This needs a registry change or a dispatch-rule change.
  - **Gap 4.** `EarningsWorkflow` is pinned to synthetic data (three run ids, pack equality, fixed limitations), and `EarningsDeltaReview` cannot express a real comparison.
- **Oracle semantics.**
  - CP-1B, CP-2 and CP-5 quote no pack source, so their keys can be met only through upstream citations.
  - The CP-2 prose key needs a CP-1 or CP-1A cite.
  - `decision_scope: FULL` and `FULL_CREDIT_32` have no counterpart in src.
- **`case_kind`.** Nothing refuses `public`. It only changes labels: there is no "Synthetic case" limitation, and C# references are used instead of S#.

Every scope beyond A needs a shared-interface or `src/deploy_vii` change, so the scope goes to the user (AGENTS.md "LEAD stopped").
