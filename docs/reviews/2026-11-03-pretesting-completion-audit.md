# Pre-testing sessions and worktrees: completion audit

Reviewed 2026-11-03. Integrated baseline: `b2dcf6a220227030e762ec4eb56b8b6f233a9ca8`.
Current Pre-Testing candidate: `codex/cp1-chain-proof` at `e5a65b0f`.
This is a read-only assessment of product work. Historical passes below were not rerun.
No credentials were read, no provider calls made, and no branches merged.

## Review method and scope

Read README, SPEC, PLAN, CLAUDE, MODULES, QUEUE, current source interfaces, case mappings,
handoffs, reviews, ledgers and relevant conversation turns. Enumerated Git worktrees;
checked current controller and candidate heads, dirty files and ancestry. Historical
worker trees were traced through their integrators rather than treated as separate work
to resume. Commit ancestry is evidence of inclusion; lack of ancestry alone does not
prove changes were never cherry-picked.

The app's conversation reader supplied actual messages, including imported Claude
sessions. These imports sometimes end before the worktree's latest edits. For the
OCR bake-off, the reader returned `thread/items/list is not supported yet`; the two
identified native Claude transcripts and retained results were read instead.
Recent decisions and handoffs were reviewed; this is not a claim to have read every
message or every historical worker diff.

## Sessions reconciled

| Session | Conversation evidence | Reconciled result |
|---|---|---|
| Pre-Testing | `01a19e99-1022-7c82-bbd3-f970feca89ab`, latest six turns through Nov 3 16:34 UTC | Stopped after its goal was cleared. One fourth RUN-P5 auditor round and one new USD25 attempt were already approved. Dirty work preserved; no new attempt launched. |
| Act as PR Manager | `01a1a111-4b2b-7652-83db-07bd0bd48cf6`, latest monitoring turns | PR #3 integrated at `b2dcf6a2`; no completed Pre-Testing handoff. Observe completed successful checks before merge; auto-merge previously merged while checks were pending. |
| Modules | `01a19e65-b6f8-73d2-9a0a-5a86994d7f95` | User approved D4: Python writes source statement lines; model maps columns and supplies judgments. XBRL-first approach was rejected. Actual PDFs and OCR backup were requested. |
| Modules, earlier continuations | `01a1912f-c54f-77a3-9804-28bfe89c7752`, `01a18425-6263-7211-b5f8-9cfbb89a4b51`, `01a18425-63db-7b73-849b-8c90baff13c3` | Stage/cohort history, chart duties and distinct portfolio-owner requirement retained; old running states are superseded by later merges. |
| src/deploy_vii fixes: H03, H09, D1–D3, cash scope | `01a1912f-c549-7fb2-a14f-348e405c7f62` | Source-context/header/cash fixes have later implementation records. Do not restart from the old transcript's task state. |
| CONTEXT | `01a19e65-bb32-7e70-91ca-7054a04f4f6b`, recent O7/release/CI turns | O1–O7/context consumers are implemented; O7 post-merge fixes through `3aa74360` are in main. Full delivery and deferred tests were never proved merely by this release. |
| MANAGER | `01a19e65-b3ca-7531-aef5-59523a0cba2b`, through Nov 2 22:33 | Confirms D4 approval and staged spending; O7 review provenance exists, partly in ignored SDD files. Preserve reviews in a portable handoff. |
| Model-testing framework: plan fixes, then offline build | `01a19e65-b4ab-7780-a4e0-b2d0c5d32b66`, through Nov 2 22:13 | Framework code is integrated. Three unmerged ledger commits correct run3/4 diagnoses. Run5 reservation and run6 hold are historical accounting evidence to reconcile, not new authorization requests. |
| Codex findings review | `01a19e65-b65a-7170-89cc-4b58c9af997b`, all 17 returned turns | Product orchestrator owns prompts, model calls and tools; testing observes and scores. Fully orchestrated operation is required. Final request to review a shared ChatGPT reuse link had no response in this thread; later fulfillment was not established. |
| PR Manager, Claude | `01a19e65-b222-7363-8f76-c51d108f75d1` | PR #2 merged at `71b78b04` with tests/heavy pending. Merged does not mean verified. Later user instruction allowed approvals from MANAGER. |
| Close remaining open owner items | `01a18e9c-8c7b-74d1-a58f-4c45a22b17bb` | `c429723` is integrated; prior fast results and deferred long tests are historical evidence. |
| Do nothing | `01a19e65-b3b8-7ec3-ad16-f295092dce61` | Terminal instruction was to do nothing. Builder-verifier task commits `18deaf89`/`922bb227` are now ancestors of main; do not revive its old PR state. |
| Cut full test-suite time (10h09m) | `01a18c09-69e2-7ce3-b369-e8ab5915733f`; native transcript `a7602679-ae64-4c02-8226-e6f192f844e1` | P1–P3 integrated. Byte-identity and timing evidence is bounded; concurrent load confounded the long comparison. F1/F2 were transferred to Modules and built. |
| OCR engine bake-off (temporary, test only) | Native Claude transcripts `adcf4d91-b53c-4264-9c99-fdc66cf8db98` and `8677b067-4823-4217-b2ef-cf65a443a319` | Later rounds actually tested PyMuPDF, LiteParse, Docling and a local Qwen/DPP arm. Earlier statements that these were unrun are obsolete. No product change was made. |
| Docling OCR exploration | `01a18c09-69ca-7361-80c2-5e2a1b7b24a8`, returned history | Synthetic image-only page demonstration; useful fallback research, not issuer-level acceptance. |
| Evaluate OCR Providers and Usage | `01a1a121-c0a7-7501-9be1-33dce99abc27` | Saved research report is useful, but its earlier research inventory omits the later local bake-off above. |
| Critique Deliverables Information IA | `01a18c21-4fa4-74c0-af31-93774ebe985e`, latest four turns | User wants Model as the cash-flow section and critique score at least 32/40. Historical preview scored 33/40; two P2 issues remain. Forecast/populated distress/portfolio behavior was not qualified. |
| LEAD; Workflow Test; C2/C3/C1 source-host | `01a18425-626e-7f41-8b45-5e616617ef20`, `01a18425-642d-7872-a01c-0f015360a747`, `01a17e9d-0331-7be2-b26b-cfbefe2762de`, `01a17e9d-0332-75d3-9eb8-8c6d69ef942c`, `01a17e9d-032e-7cb1-93cc-4a47395b8e74` | Historical slice/oracle/role handoffs and interrupted work reviewed. Current integrated code and later lane evidence supersede those old implementation states. |

## Worktree disposition

Paths below are under `/Users/ericguei/`.

| Worktree / branch | Observed state | Disposition |
|---|---|---|
| `Documents/Deploy Workflow`, `codex/checkpoint` | `b2dcf6a2`; no tracked dirty files at review start; unrelated untracked research/settings | PR MANAGER integration checkout. |
| `.codex/worktrees/cp1-chain-proof/Deploy Workflow` | `e5a65b0f`, committed candidate, not integrated | Current CP1 aggregate; finish the two leased workers, retain existing reviews, then prepare an exact handoff. |
| `.codex/worktrees/cp1-audit-scope-round4/Deploy Workflow` | Same base; dirty `work/cp1-chain-runtime/audit.py` and `tests/test_chain_runtime.py` | Unreviewed round4 implementation; no completed report or test receipt. |
| `.codex/worktrees/cp1-budget-renewal/Deploy Workflow` | Same base; dirty ruling and driver checksum; untracked renewal brief | Complete mechanical renewal/report/review. No fresh launch gate yet. |
| `Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` | `acfe17ba`, not ancestor of main; dirty R23 notes and untracked review/scratch | Reconcile remaining documentary changes. R23 implementation is already incorporated into the newer CP1 candidate. |
| `.claude/worktrees/codex-project-context-a11b1b` | `36b4a620`, clean ancestor | Stale controller location, not current Modules source. |
| `.claude/worktrees/tool-use-m365-copilot-research-8ff28f` | `3aa74360`, ancestor of main; untracked `.agents/` | O7 complete as implementation; use existing integration, not another merge of the old lane. |
| `.claude/worktrees/agitated-meitner-5f25bb` | `b6754e36`; three unmerged commits affecting only framework ledger | Preserve `6521f59b`, `bb8cfa0a`, `b6754e36` selectively; do not restore old product source. |
| `.claude/worktrees/open-items-fd69c5` | Detached `9c018f7`; lane result `c429723` is integrated | Historical checkout; no new product task inferred. |
| `.claude/worktrees/reviewer-adversarial-comparison-46e5f9` | `d8dbbc5d`, ancestor | Historical MANAGER/review evidence. |
| `.claude/worktrees/codex-findings-review-64c673` | Detached `efe43725`, ancestor | Historical requirements and independent keys. |
| `.claude/worktrees/vigilant-mendel-070f6d` | `71b78b04`, ancestor; shared by multiple historical sessions | Perf/PR/OCR session identity cannot be inferred from its current branch name. |
| `.codex/worktrees/deliverable-design/Deploy Workflow` | `2b265890`; extensive dirty UI and untracked evaluation/source-preparation work | Separate UI changes from alternate evaluation framework. Preserve all WIP; no wholesale merge. |

The CP1 candidate directly contains `fe7bc244` (R23), `44f855bc` (R23 fixes),
`73a4e40c` (stale-test repair), `27c0f84e` and `02cbcb4a` (PDF headers).
It also includes reviewed typed-producer fixes and source-history replay (`67e1620b`).
These are not new implementation tasks. The main O7 post-merge tip `3aa74360` is not
an ancestor of this candidate, so integration must preserve both lines of work.

## Current blockers supported by source/evidence

1. **CP1 chain:** candidate `work/cp1-chain/offline-ready.md` records run `6522e7ec93`:
   22 authoritative calls, USD3.01044020 settled, all five CP1 steps valid, stopped
   during CP1A on `SourceError: identity_mismatch`. No CP2, Model publication, report
   or native proof. Source diagnostic matched 103 rows/280 cells/21 printed nils.
   Separate RUN-P5 scope-wording refusal is the approved fourth auditor round;
   it must not be described as the proven cause of the CP1A failure.
2. **Missing owners:** `owner_workflow.py:146` registers 22 analytical identities.
   CP3B/CP6A are still legacy aliases (`methodology.json:307,490`), contrary to
   SPEC's distinct-owner requirement. They are absent from the six presets.
3. **Full delivery:** `owner_rendering.py:579` accepts exact bounded delivery tuples;
   none is a full preset. `tests/test_o2_done_when.py:428` expects a render-scope stop.
   A full preset with CP-DR needs its own supported composition too.
4. **Earnings:** `owners/cp1b.py:145–168` supports narrow pairs, not the SHC Q2/Q2
   comparative required by its real case.
5. **Scoring:** checked-in mappings cover TDG 95/235, SHC 55/222, BGS 59/142,
   LTH 51/231, IHRT 63/197, NATL 37/148: **360/1,175**. The scorer's pass predicate
   does not itself fail solely on unmapped facts. CLI exit 0 can accompany stopped runs.
6. **Wider PDF qualification:** header parser covers 29 frozen units, not universal
   PDFs. Candidate verifier report retains VMO2Q3 55 uncovered rows, including an
   intentionally unmapped mixed-entity summary. OCR proof does not establish safe
   financial output from image-only TDG.
7. **Status drift:** top-level PLAN/TEAM/QUEUE/MODULES/RUN-GUIDE mix old limits and
   bounded evidence. Code existence must not automatically upgrade acceptance rows.

## Other work to preserve

- **Design:** `work/design/cashflow-design-backlog.md` in the design worktree retains
  snapshot currency/scale and exact selected-figure inspection context as the two
  P2 issues. Preview tests and 33/40 critique are historical, not live delivery proof.
- **Alternate 24-cell campaign:** latest `work/evaluation/public-campaign/STATUS.md`
  and `EXECUTION-HANDOFF.md` there describe six issuers × two efforts × coding/API,
  a separate historical USD100 API ceiling, zero new campaign calls, and 38/39
  retained sources over 4,438 PDF pages. P02 terminal accounting, A02 part provenance
  and A04 restricted-producer acceptance remain Medium; release is false. Exact
  independently verified TDG/SHC emitted gold is usable under its ruling18; its
  PG06 generator is not qualified for regeneration. Reuse only named pinned
  evidence through current project contracts. This campaign is not a completed
  replacement for the product model-testing framework, nor extra current budget.
- **OCR:** retained round2/3 report is under the native transcript `8677b067-...`
  scratchpad in `/private/tmp/claude-501/`. It reports local/network-blocked runs,
  but row-heuristic scoring fails its own complete self-match, round denominators
  differ, and round2 raw outputs were deleted. DPP/VLM still truncated a TDG page.
  Do not select a production engine or claim corpus accuracy from these totals.

## CI and verification limits

GitHub status read at approximately 16:40 UTC:

- [Checkpoint run 41624475483](https://github.com/EricMG13/workflow/actions/runs/41624475483),
  head `b2dcf6a2`: `suite (1)` failed; other jobs still running; several jobs passed.
- [PR heavy 41624419949](https://github.com/EricMG13/workflow/actions/runs/41624419949),
  head `3aa74360`: running.
- [PR checks/tests 41624420545](https://github.com/EricMG13/workflow/actions/runs/41624420545):
  checks passed, tests cancelled.

The failed-shard root cause was not retrieved: run-log access said the run was still
in progress, direct job-log access returned HTTP403; a later unrelated PR query
returned HTTP401. No authentication change was attempted. Refresh through the
existing PR Manager connection before diagnosing or declaring the candidate green.
CI omits the local public goldens; those require the retained corpus locally.

No fresh product tests, browser acceptance, external balance verification, full
corpus rehash, or current provider capability check was performed in this audit.

## Plan review

An independent `mx-precise` review of this audit and the final completion plan
returned PASS with one Low note and no High/Medium corrections. The note was
applied: expected refusal cases require refusal/downstream-gap evidence, not an
invented settled artifact or successful consumption. Documentation checks confirmed
26 unique owner identities and valid relative document links. This review validates
the plan's scope and evidence requirements, not the product's runtime completion.

The later [adversarial review](2026-11-03-completion-plan-adversarial.md) supersedes
the mixed plan's session assignment. The revised testing plan keeps all testing
and related preparation in Pre-Testing; the separate product plan owns implementation,
product fixes, design and other completion work. Historical findings in this audit
remain unchanged.
