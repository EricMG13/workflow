# Cross-plan adversarial review, 2026-10-31

Plan A: `docs/superpowers/plans/2026-10-31-context-file-consumption.md` @ 36b4a620.
Plan B: `docs/superpowers/plans/2026-10-31-model-testing-framework.md` on
`claude/codex-findings-review-64c673` @ efe43725 (unchanged since 9ee77189).
Reviewer: one fresh Opus 5.5 reviewer (three personas), read-only. Its claims were re-checked by
the controller against the files; probes P9, P1, P4, P2 and P7 were re-run and reproduce.
Verdicts: Phase 1 CONCERNS; plans overall BLOCK on C1-C4.

User ruling (2026-10-31): "Fix Part B first", before Phase 1 starts.

## Disposition

| Finding | Severity | Owner | Disposition |
|---|---|---|---|
| C1 SEC HTML cannot become pack sources | CRITICAL | A | Fixed: Part B R1, O2 row and Done-when probe |
| C2 live gate is a filename check | CRITICAL | both | A fixed: R2 (gate in O5, `lifts`/`by: user`/`date`/`configs` lines; stated as a tripwire, the user's word is the control). B: Task 11 passes `--ruling` to `live_adapter`; its own check becomes a pre-check only |
| C3 web retrieval is an open fetch path | CRITICAL | A | Fixed: R4, OD3 |
| C4 `run_pathway` is only a name | CRITICAL | both | A fixed: call shape, run directory, `run.json` sole writer. B: Task 11 consumes that shape, builds `ModelSpec` from its `ModelConfig`, never writes `run.json`; Task 8 reads `outcome`, `mode` and the ruling fields from `run.json`, and adds a rule and a `test_stopped_run_without_receipt` test: with no `owner-run.json`, take the module list from the pathway's plan, score each absent, `rendered` false |
| W1 NATL scores CP-4, not in its plan | WARNING | B | B: move the 51 CP-4 facts to `not_golden`, or rule `requested_modules` for that case |
| W2 CP-1C/CP-1D hard-code the 2025 period | WARNING | A | Fixed: Phase 8 row |
| W3 mapping oracle before layout changes | WARNING | both | A: R7 (reports list layout changes). B: Task 6 per module after its phase lands, mapping records the module commit |
| W4 Task 11 needs O4 and O6 too | WARNING | B | A: R7 states it. B: Task 11 starts after O6 |
| W5 key checks catch too little, too late | WARNING | both | A fixed: R3 (redact before write). B: widen the regex to `sk-[A-Za-z0-9_-]{20,}` |
| W6 CP-DR on goldens undefined | WARNING | A | Fixed: R6, OD9 |
| W7 prompt faults have no owner | WARNING | both | A fixed: R7 and the O6 row follow the user's later ruling (design spec §1a, from "should this not be the responsibility of the orchestrator", 11:40): prompts are product code held by the orchestrator in `src/deploy_workflow`; prompt faults go to the O6 owner. B: the spec's §10.2 location (`model_testing/prompts/`, line 192) and "prompt → fixed in the framework" (line 126) are stale against §1a; update both |
| W8 reruns and retries in call records | WARNING | both | A fixed: one record per request; replays named in `run.json`, not re-recorded. B: count retries from `call_index` and `error_class`, not `attempt == 1` only |
| W9 honest gap can still fail | WARNING | both | A: O3 records named missing inputs. B: Task 7 scores a recorded refusal naming the missing input as an honest gap |
| N1 TDG fiscal vs calendar period | NOTE | A | Phase 1: Task 1 adds no "period ends before as_of" rule |
| N2 `check.py` SLUG drift | NOTE | B | B: Task 4 also calls `load_context` |
| N3 effort map, prices, timeouts, raw archive, cap semantics | NOTE | A | Fixed: R5 and the cap paragraph |
| N4 `schema_version` unnamed | NOTE | A | Fixed: record carries `schema_version`, no other field |
| P1-1 regex semantics | WARNING | A | Phase 1, before Task 1 is dispatched |
| P1-2 splitlines round trip | WARNING | A | Phase 1, before Task 4 is dispatched |
| P1-3 `model_validate_json` on raw bytes | NOTE | A | Phase 1 ruling 1 restated |
| P1-4 commas in list items | WARNING | A | Phase 1: Task 1 allows them; Task 2 records the form defect |

## Review of the amendments (mx-feature, scoped)

Verdict: fix (three Medium). All applied:
- Medium-1: `ModelAdapter` carries `config_id` and `ruling`; `run_pathway` reads them, refuses a
  config mismatch; `mode` follows `adapter.ruling`.
- Medium-2: a stopped run's files stated; Plan B Task 8 item added above (C4 row).
- Medium-3: rejected after reading the Codex findings review transcript. The reviewer read spec
  lines 126 and 192, which predate §1a (commit b6f109fd, 11:41), where the user moved prompts to
  the orchestrator and the framework "contains no provider client, no turn loop and no prompts".
  R7 keeps orchestrator ownership; the W7 row now names the stale spec lines as a Plan B fix.
- Re-review (mx-feature): Medium-1 closed; Medium-2 closed by rewording the framework's
  stopped-run scoring as a Task 8 addition (C4 row); O6 step count restored to the 13 owner-only
  steps and CP-1B, since CP-5 already has a prompt (orchestration review, 11:51).
- Also applied: R2 tripwire wording and `by`/`date` lines; `cp_dr=True` refused until O7b;
  pre-send refusal values (Low-5); named env vars, empty values skipped (Low-3); connect to the
  checked address (Low-1); O7b owns the publication-date check (Info).
- Left to the phase plans: HTML encoding detection and empty lines (R1, O2's plan; Low-2);
  timeout values, retry count and `raw/` naming (O5's plan; Low-6).

## Codex findings review session (transcript read 2026-10-31)

- Its branch tip is efe43725 (6e6731c, 11:08, is 36 commits earlier). Plan B (9ee77189) is
  written but not yet reviewed by the user.
- Its own cross-plan reviewer stopped after one command: the session hit its weekly limit at
  12:21 (resets 2026-11-04 07:00 London). This review is the only one.
- Open user request there, not acted on: "include a review of
  https://chatgpt.com/s/cx_6ae5dd1742ac81919697cdfa79cef437 for usable code within your plan"
  (12:21).
- Its §9a decisions (mapping table as an answer key, repair stop rule, inherited errors,
  untraceable numbers) and §10.3 (empty inputs, honest gaps) are consistent with Part B.

Plan B items above go to the testing session ("Codex findings review"); it stopped at its usage
limit on 2026-10-31 at 12:21, so they are not yet sent.

Not verified: no pytest; Part B code does not exist; provider key prefixes, effort parameters and
prices not checked against provider docs; R1's block-line conversion not run against the golden
quotes (O2's Done-when probe does that).
