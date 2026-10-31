# Test-suite performance sweep — report

Branch `claude/vigilant-mendel-070f6d`; base = Stage 5 release `05c3b27` (local `codex/checkpoint`).
Product changes, approved by the user in the sweep session (2026-10-30, "Yes, apply P1–P3"):

| Change | Commit | What |
|---|---|---|
| P2 | 2ded26c | `src/deploy_vii/contracts.py` `validate_tables`: group canonical fact ids by table once (was a rescan of every fact per table) |
| P1 | 17e07ba | `src/deploy_workflow/earnings_workflow.py` `_operands`: hash the CP-1 producer once per call (was once per operand reference) |
| P3 | 4af08ce | `src/deploy_vii/execution.py` `Execution.result`: parse each verified blob once per process (`lru_cache(maxsize=4)`; `_load` still reads and hash-checks every call) |
| Lows | 66cce2a | memory comment corrected; test pinning the empty-table default |

Reviews: per task `mx-precise` (approve ×3), `mx-adversary` on P1+P3 (approve), whole-branch
`mx-precise` (approve). No High or Medium finding. Briefs, reports, reviews and the
SDD ledger: `work/perf-sweep/reviews/`; reviewer probes: `work/perf-sweep/probes/review/`.

## Same outputs

- E-NO-YOY run with deterministic `uuid4` (`probes/seeded_uuid.py`, the code's only randomness)
  and `PYTHONHASHSEED=0` on base and branch: 131 vs 131 files, 0 missing, 0 differing
  (`identity-E-NO-YOY.txt`, sha256 of every file). Covers every module blob (CP-0, CP-1, CP-1B),
  snapshots, audit records, owner receipt and `receipt.json`.
- Per change: P2 old vs new on 60,000 random real-contract inputs, same result or message every time
  (`probes/review/p2_equivalence.py`); P1 lineage bytes identical on the real 44 MB CP-1 blob, 276
  references (`probes/review/adv_p1_real_cp1_operands.py`); P3 same result or error on every repeated
  call, including tamper-after-cache-hit (`probes/review/task2_equivalence.py`, `probes/review/adv_p3_real_blob_cache.py`).
- `python3 -I cases/pins.py --check`: exit 0, 86 paths, at 5ee6c9b (merged branch).
- All 18 heavy tests pass on base and branch; new tests pass (validate_tables 13, result cache 4,
  `_operands` 1). Suppressions 13 / 5 (baseline).

## Timings

Harness `probes/time_tests.sh`: one pytest process per line, `--durations=0`, peak RSS, load
average. Runs in concurrent pairs; snapshots T0 = base, T1 = +P2, T2 = +P2+P1, T3 = +P2+P1+P3.
Quiet-machine noise: two identical base runs differ by 0.79 % (s1a tampering[gap] 895/888 s) and
0.47 % (E-NO-YOY 1060/1055 s). Acceptance: gain > 2 × noise and > 5 % of the before time.

### Per change, quiet machine — E-NO-YOY (`test_fresh_actual_owner_cases…[E-NO-YOY]`)

| Tree | Seconds | Step gain | Cumulative vs base mean 1,051 |
|---|---|---|---|
| T0 base | 1,055 · 1,060 · 1,038 (seeded) | — | — |
| T1 +P2 | 999 | −52 s vs base mean (−4.9 %) | −4.9 % |
| T2 +P1 | 789 | −210 s (−21.0 %) | −24.9 % |
| T3 +P3 | 736 | −53 s (−6.7 %) | −30.0 % |

Peak RSS 5.72 GB base → 5.87 GB branch (+150 MB, P3's cache).
P2 on its own step (−4.9 %) sat just under the 5 % floor, so it was settled by a quiet leave-one-out
pair (19:25Z, load 2.5–3.4): T3 (all) **734 s** vs T4 = T3 without P2 **781 s** → P2 saves
**−47 s (−6.0 %)** on top of P1+P3: accepted. The T3 repeat (734 vs 736 s) is within 0.3 %.

### Heavy set, base ∥ branch, shared load

| Test | Base s | Branch s | Saved |
|---|---|---|---|
| earnings `real_retained_owner_submission[pending_validation]` | 2,196 | 1,549 | −647 (−29.5 %) |
| earnings `real_retained_owner_submission[after_valid_step]` | 1,918 | 1,277 | −642 (−33.4 %) |
| earnings `real_retained_owner_submission[after_settlement]` | 1,647 | 1,014 | −633 (−38.4 %) |
| earnings `fresh_actual_owner_cases[E-QOQ-FLAT]` | 1,454 | 768 | −686 (−47.2 %) |
| earnings `real_refused_session_then_same_session_completion` | 1,325 | 818 | −507 (−38.2 %) |
| earnings `fresh_actual_owner_cases[E-NO-YOY]` | 1,256 | 801 | −455 (−36.2 %) |
| earnings `actual_composed_new_money_figures` (incl. module fixture setup) | 1,050 | 590 | −459 (−43.8 %) |
| s1a `tampering_refuses_with_identity_mismatch[positive]` | 1,129 | 867 | −261 (−23.2 %) |
| s1a `tampering_refuses_with_identity_mismatch[gap]` | 1,087 | 950 | −137 (−12.6 %) |
| earnings `unresolved_empty_session_intent` (incl. module fixture setup) | 720 | 597 | −123 (−17.1 %) |
| financial_render `authentic_financial_delivery[False]` | 601 | 582 | −19 (−3.2 %) not accepted (< 5 %) |
| earnings `well_shaped_wrong_owner_review` ×5 | 516–553 | 442–471 | −50 to −110 (−9.6 to −20.0 %) |
| s1a `cp1a_without_business_page3_read` | 522 | 412 | −110 (−21.1 %) |
| **Total, 18 tests** (setup+call+teardown from `--durations=0`) | **17,582** | **12,517** | **−5,065 (−28.8 %)** |

Load caveat: from 13:08Z the pair shared the machine with the Modules final suites and then the
open-items rerun queue (≤ 6 processes each, load 8–10). The base side ran longer under that load:
E-NO-YOY was +20 % over its quiet time on the base side, +9 % on the branch side; s1a
tampering[gap] base +22 %. Heavy-set percentages therefore overstate the gain by up to ~10 points;
the quiet E-NO-YOY row (−30 %) is the clean figure.

## Not done / follow-ups (owner)

- F1: `host._ParsedExecution` keeps its own 4-entry parse cache; with P3 both caches together
  measured +2.58 GiB in a long-lived host. Removing the host copy is a `deploy_workflow` change.
- F2: `cases/cpos-owner` builder/manifest pin the base `contracts.py` hash; stale after P2
  (sibling pins were already stale at base; no test reads them).
- P5 `records` traversal, P6 skipping trusted recomputation (verification-policy ruling), and
  `pytest-xdist` (dependency decision) not attempted.
- Tier markers not added: `work/build/keep/fast-set.txt` is already the per-change fast set.

Not verified: byte identity on tests other than E-NO-YOY; heavy-set gains on a quiet machine;
the full suite on the branch (only the 18 heavy tests, the new tests, and the reviewers' 553 +
1,426 tests ran); P2's gain on tests other than E-NO-YOY (accepted on the E-NO-YOY leave-one-out only); free-threaded Python.

The reviewer probes under `probes/review/` read a real settled CP-1 Module blob (44 MB, not committed);
any current earnings owner store holds one under `blobs/` (the CP-1 head's `result_sha256`).

Measured on `05c3b27`. Later tip `b6c7053` (post-Stage-5): no file overlap, merges cleanly
(`git merge-tree`), and adds nothing that interacts with P3's cache; timings not re-run there.
