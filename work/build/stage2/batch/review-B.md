# Stage 2 review, lane B: covenant chain (mx-adversary)

## Lane B review: covenant chain (`claude/s2-batch` at a1a0574)

I did not edit anything. Probes and mutants ran on a `git archive` copy at `<P>/tree`, where `<P>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage2-review-B`.

### Verdicts
- **CP-2D fix round 1: APPROVE.** H1, M1, M2, M3 and M4 are closed.
- **CP-4 fix round 1: APPROVE.** M1 and M2 are closed.
- **CP-3C: REQUEST CHANGES** (one Medium, M1 below).

### Prior findings re-checked with the original reviewers' probes
**CP-2D**
- **H1, closed.** `test_legal_render` passes, and dropping a D7 `_Spec` row makes it fail (`<P>/b8_fp04_delta_mutants.py`, exit 0, 3 of 3 killed).
- **M1 and M2, closed.**
  - p5 and p6 exit 0 on the real CP-1 head copy.
  - In my mutant run, the original defects are killed: "USD required again" and the one-way alias compare. So are a dropped currency agreement, a dropped millions check and an uncompared basis.
- **M4, closed.** All 26 of the reviewer's `p7_new` mutants are killed at a1a0574. With my 5 added, that is 31 of 31 killed (`<P>/b1_cp2d_fix1_mutants.py`, exit 0).
- **M3, closed as written.** p13 exits 0 (`<P>/b2_cp2d_p13_acceptance.sh`). The store-run tests are deferred and have never run.
- p8, p10 and p11 exit 0. p14 exits 1 only because later modules were appended after CP-2D, which was its "last row" assumption; it is not a defect.
- The removed `period is None` guard really was dead: Fact's validator refuses that case (`<P>/b10_cp2d_known_without_period.py`, exit 0).

**CP-4**
- **M2, closed.** 17 of 17 mutants are killed, including R1–R3 through `test_probe_cp4.py` and P2 (`<P>/b4_cp4_p4_extended.py`; log `b4_cp4_p4_extended.log`).
- **M1, closed.** `p5_deferred_coverage` exits 0 and p2 exits 0 (`<P>/b3_cp4_p5.out`, `b3_cp4_p2.out`). I reasoned through two deferred tests:
  - A3b would read "accepted" if the verifier did not replay the gate.
  - The A5 consistent read-body forge passes `_verify_audit` and is refused by `_verify_calls_reads`.

  Neither has run (Stage 5).

### CP-3C checks that passed
- **Real upstream heads.** On a head settled by the real CP-2D core (the `make_store` fixture), the adapter returns the Stage 1 input object. `select_cp1` also reads the real promoted CP-1 head (`<P>/b6_cp3c_real_cp1_head.py`, exit 0).
- **One adapter.** `submit`, `probe` and `view` all go through `cp3c_upstream`, then `select`.
- **`_reader_agrees`.** Each pair (horizon, minimum cash, gap, labels, the four wall cells) is pinned by the lying-reader test. Mutants A2 and A3 are killed.
- **`run_rate`.** It is read from the bound head's `T2E.3.r01` cell, and that head is hash-checked as the bound input (mutants A1 and A8 killed). There is no reader cross-check, because the reader does not expose `run_rate`; the report's word "cross-checked" overstates this.
- **Stale and swapped inputs.** Both are refused (mutants A7 and A9 killed).
- **D7 rows.** The `_Spec` rows match lease :191-192.

### Findings
**M1 (Medium, test strength on money paths; same class as CP-2D review M4).** The code behaves correctly, but 8 of 17 mutants survive `test_connect_cp3c`, `test_method_cp3c` and the fast group of `test_owner_cp3c` (`<P>/b5_cp3c_mutants.py`, exit 1; log `b5_cp3c_mutants.log`). That breaks brief §7 and the Gates rule, and the report claims "69 killed".
- **Alias presence check, `cp3c.py:2231`.** This is exactly CP-2D's M2 fail-open. With the check off, a facility that has only an fy-2025 row is silently dropped from the refinancing need.
- **Alias terms, `_ALIAS_TERMS` (:2080) and `_same` (:2204).** Neither `currency`, `rate_type` nor `scale` is compared by any test. With `currency` removed, an alias currency mismatch is accepted.
- **CP-2D scale check, `_cp2d_fact` :2306.** A scale-1e3 fact is accepted as millions.
- **View run-id check, :2711.** Untested.
- **Reader, `total_principal_payable` :2909 and `base_claims` :2920.** A constant 50 passes, because it equals the oracle in every case. The deferred `expected_read` uses the same values, so it would pass too.

Probe `<P>/b9_cp3c_alias_untested.py` exits 0 at the tip (all three refuse) and 1 on the mutant copy `<P>/mut-a10` (facility dropped, mismatch accepted, scale accepted).

**L1 (Low, `GAP_CURRENCY` is mis-aimed in the release list and has no tripwire).**
- `close-release.md:32` says "CP-3C oracle … gap-cell currency to USD".
- But the CP-3C oracle gap cells already carry USD. What lacks a currency is the CP-2D oracle's `T2E.5.r04`/`r07`, and the Stage 1 stand-in (`test_method_cp3c.py:156-161`) never reads a currency at all.
- So re-pinning that oracle alone cannot retire the delta. Unlike `PRINCIPAL_PERIOD_DELTA` (tripwire at `test_connect_cp3c.py:657`), nothing fails once it goes stale.
- Probe: `<P>/b12_gap_currency_target.py`, exit 1.

**L2 (Low, a pin missing from the release list).**
- `cases/cp4-owner/expected.json:318` `other_five_sections` still says all five blocks "stay owner Unbound". After the two deltas that is false for all five.
- The CP-2D fix1 report listed it, but `close-release.md` does not. No test pins it.
- Probe: `<P>/b13_cp4_oracle_other_five.sh`, exit 1.

**Info**
- `test_legal_render.py:36-38` ("refinancing-paths … stay the Unbound fallback") and `:44` ("pending a LEAD ruling") are stale after round 5 item 18.
- `UNBOUND_FALLBACK` and the note fallback (`CP2D_D7_NOTE.get(id, block.note)`, a self-comparison) can no longer be reached.
- The connect fixture's `cp1_module` writes T4.10 `cash_closing` as `calculated`, but the real promoted head writes `source` (`<P>/b7_cp3c_real_vs_fixture_cp1.py`, exit 1). It changes no output, because no cell copies `cash_closing`.

### Answers to the dispatch questions
- **FP04 deltas.** The diff against 7317261 changes only the block loop. The five ids get the delta tuples and a note, and everything else in the test is unchanged and still asserted exactly. `producers` was not asserted before and is not now.
- **CP-3C oracle deltas.** All three are minimal:
  - `PRINCIPAL_PERIOD_DELTA`: 2 cells × 3 cases.
  - `GAP_CURRENCY`: the 2 CP-2D gap twins, in gap_minimum_cash only.
  - `CP1A_BOUND`: one input, and it guards itself.

  `PRINCIPAL_PERIOD_DELTA` and `CP1A_BOUND` are named for the close re-pin (`close-release.md:32-33`, lease acceptance 1). `GAP_CURRENCY` is named but aimed at the wrong file (L1).
- **CP-2D stale head.** No. In `negative_cases.begin_refused_cp2_blocked`, `attempt_consumed: false` and `head: "none"` both hold when begin raises. Only the `also` text claims a stale head refuses the same way. The CP-3C oracle scopes stale out explicitly (`begin_refused_cp2d_blocked.scope`).

### Gate exit codes
- The 10-file pytest gate: 0 (1102 passed, 9 skipped).
- `tests/test_probe_cp4.py`: 0 (5 passed, 56 s).
- Extra runs:
  - `test_owner_cp3c.py` with the stage class tests: 31 passed, 11 skipped, 2 xfailed.
  - `ruff check`: 0. `ruff format --check`: 0.
  - `mypy --strict` on 12 lane files: 0.

Not verified: none of the deferred store runs (`test_owner_cp2d`, `test_owner_cp3c` and `test_owner_cp4` with `*_STORE_RUNS`, or `cp3c_runs` end to end) has ever run, so receipts, tamper checks and D3 on genuine closed heads are untested. CP-3C was not settled over a real promoted CP-1 store; only `select_cp1` was run on that head. I did not run `test_financial_render`, `test_connected_render`, `test_owner_workflow` or `test_owner_s1a`. Not checked here: D12 manifest records (lane C), and the CP-1 readiness `refused_variants` (the builder wrote no test for them).
