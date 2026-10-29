# Batch final: stage-level class test (general-purpose, opus)

## Stage 2 class test: report

**Commit:** `a1a0574` on `claude/s2-batch`, on top of 5977ae4. The tree is clean. The commit adds two files and edits no `src`, `cases/`, `tests/defect_classes.py` or `test_connect_*` file. It adds no `noqa` and no `type: ignore`.

- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-batch/tests/test_stage2_classes.py` holds the shared run, the Q5 test over every core, and the modules connected before the batch. It runs in about 49 s.
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-batch/tests/test_stage2_classes_batch.py` holds CP-1D, CP-2G, CP-1C, CP-3C, CP-2H and CP-4C. It also checks that the two files cover `_CORES` exactly once, and that five verbatim sets equal the ones their connect tests already state. It runs in about 51 s.

**Scope, checked against the registry:** `_CORES` holds 13 modules. CP-3, CP-5 and CP-4 have `entry="model_payload"`, no core and no `SCHEMAS`, so the rule leaves them out. Their step schemas are already in the Q5 set of `test_defect_classes_shared`.

**How each case runs:** `fresh()` copies a template store per case. The template is the real `Execution` that the module's connect test or run driver builds, imported and not copied. Each submit goes through `core.submit(..., rules=None)`. After a refusal, the next submit begins the repair attempt.

**Per module.** Every module has one schema. The count is the number of free-text paths in its positive payload. "Retained" means the value is kept only in the journaled submission.

| Module | Paths | Verbatim pattern → sink | Outcome |
|---|---|---|---|
| CP-DR (`partial`) | 14 | `questions.*.text` → TDR.2 Fact.text and `Unresolved:` limitation; `questions.*.limitation` → Fact.limitation and the limitations | **strict xfail** |
| CP-3D | 67 | `terms.reference_rate.absence.reason` → T3E.7 Fact.text; `.follow_up` and `recovery.rationale` → retained; `technicals.*.text` → T3E.6 Fact.text; `technicals.*.limitation` → Module.limitations and T3E.9 | **strict xfail** |
| CP-2E | 78 | `fx.operating_fx_absence.reason` and `hedge_absence.reason` → T2F.7 Fact.text; their `follow_up` and `assessments.*.limitation` → retained; `shock_rationale` and `assessments.*.text` → T2F.6 Fact.text | pass |
| CP-8 | 143 | none | pass |
| CP-2A | 22 | none | pass |
| CP-2D | 8 | `minimum_cash.rationale`, `assessments.*.text`, `assessments.*.credit_implication` → retained | pass |
| CP-L10 | 13 | `gaps.*.gap` → `Gap (<severity>): <gap>` limitation; `why_it_matters` and `action` → retained | pass |
| CP-1D | 23 | `assessments.*.limitation` and `overall.limitation` → Claim.limitation; the four gap fields → T1D.7 Fact.text (`gap` also a limitation) | pass |
| CP-2G | 19 | five `*.limitation` paths → Claim.limitation of T2H.3.* | pass |
| CP-1C | 27 | same set as `CP1C_VERBATIM`: Claim.limitation, T1C.7 Fact.text, limitations | pass |
| CP-3C | 13 | `repricing.rationale` → retained; `paths.*.text` and `paths.*.credit_implication` → T3D.6 Fact.text; `paths.*.limitation` → Module.limitations | pass |
| CP-2H | 24 | none | pass |
| CP-4C | 65 | same set as `CP4C_VERBATIM`: Claim.limitation, T4E.10 Fact.text | pass |

**Findings.** Each is marked `xfail(strict=True, raises=ValidationError)`, and neither path is in its module's verbatim set:
1. **CP-DR `gaps.*.questions.*.answer`** is built as `Claim.text` (`CPDR-ANS-<question_id>`) with no RunText check. A hostile value raises `ValidationError` inside `cpdr.submit` after the step is journaled.
2. **CP-3D `summary.text`** is built as `Claim.text` (`CP-3D-VIEW-01`) in the same way and raises inside `cp3d.submit`.

I confirmed both through the public `OwnerWorkflow` with `verify_findings_owner.py`. The raise comes after the binding write. The follow-up submit then raises `WorkflowError("stale_binding")`, so the run is wedged.

**Mutant evidence.** `run_mutants.py` copies the whole tree with `PYTHONDONTWRITEBYTECODE=1`. Every control passed and every mutant failed (script exit 0):
- CP-2E with `chk.run_text("summary.text")` removed: Claim raises `ValidationError`.
- CP-8 with reference syntax allowed in `_text`: `ValueError` "Claim CP-8-VIEW-01 does not resolve".
- CP-2H with claim text left unchecked: `ValueError` "Malformed run text".
- CP-4C with rationale left unchecked: the same `ValueError`.
- Q5 mutant, a CP-2A schema whose before-validator raises `KeyError`: the hostile test fails.

My first CP-2H and CP-4C mutants removed only the RunText check and were not caught, because `prose.issues` already refuses all three hostile values there. I replaced them with the two above.

**Gates (all exit 0):**
- `test_stage2_classes.py`: 18 passed, 2 xfailed, 49 s.
- `test_stage2_classes_batch.py`: 12 passed, 51 s.
- `test_defect_classes_selfcheck.py`: 244 passed, 0.6 s.
- `test_defect_classes_shared.py`: 64 passed, 9.6 s.
- `test_defect_classes_cp1.py`: 1 passed, 29 s.
- `ruff check` and `ruff format --check` on both new files.
- `MYPYPATH=src mypy --strict` on both new files.

Two more results outside the dispatch list:
- The fast set the batch brief asks for (every `test_connect_*` and `test_method_*` file) gave 8440 passed, 3 skipped, in 77 s, exit 0.
- Ruff over all of `src` and `tests` exits 1. All 124 lint findings and the 4 files ruff would reformat are in files I did not touch.

All scripts and their output are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage2-classes/`: `discover.py`, `verify_findings_owner.py`, `run_mutants.py`, `mutants.out` and `fastset.out`.

**Not verified:**
- The stage test drives the core's submit with `rules=None`. It does not go through `OwnerWorkflow`, the G1-X gate or the journaled tool-use rules; only the two findings were run that way.
- Free-text fields that are null or absent in the positive payloads are not exercised (round 5 item 10 L2 backlog). Examples are CP-3C `repricing_absence.*`, the CP-3D and CP-2E absences not stated, and the other CP-DR cases.
- Model text for CP-3, CP-4 and CP-5 is not run at stage level.
- jscpd was not run.
- Each sink was read from the core. For CP-1C, CP-2G, CP-3C and CP-4C it also matches their connect tests.

`agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n`. The pytest gates passed on their first run, but ruff (PYI025) and mypy (`SUBMISSIONS` re-export) each failed once while I was drafting.
