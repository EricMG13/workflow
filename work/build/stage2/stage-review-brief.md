# Stage 2 whole-stage review (stage contract)

This is one review phase for the whole Stage 2 batch (user, 2026-10-28: "no more per module work"). Three Opus reviewers (`mx-adversary`) run in parallel, one per lane below. Each lane reviews read-only and writes probes to the scratchpad. One fix batch follows; it takes the High and Medium findings plus the Lows and backlog batch.

## Inputs
| Item | File | Why |
|---|---|---|
| Branch | `claude/s2-batch`, worktree `../s2-batch` (read-only), tip named in dispatch | what is reviewed |
| Contract | `work/build/stage2/brief.md` (Process, §5-§7, "Rulings that bind every module", Source quotes), `work/build/stage2/batch-brief.md` | what "connected" means |
| Rulings | `docs/rulings/2026-10-28-stage2.md` rounds 1-5 (items 1-18), `work/build/stage2/questions.md` | settled questions; do not re-raise |
| Reports | `work/build/stage2/batch/*.md`, `work/build/stage2/<cp>/fix1-report.md` | builders' claims to verify |
| Prior reviews | `work/build/stage2/<cp>/review.md` | findings the fix rounds claim to close |
| Known items | `work/build/stage2/close-release.md`, `work/build/stage2/lows.md`, `work/build/stage2-backlog.md` | already recorded; do not re-raise |
| Leases | `docs/<CP>-OWNER-LEASE.md`, `docs/G1X-OWNER-CORE-PROTOCOL.md` | the spec |

## Lanes
- **A, distressed chain:** CP-2G, CP-2H and CP-4C. Check the reader chain CP-2A → CP-2G (`cp2g_reader`) → CP-2H and CP-4C, the D3 proofs, the `_DISTRESSED` rows and the CP-1D consumption in CP-2G.
- **B, covenant chain:** CP-3C plus the CP-2D fix1 and the CP-4 fix1 (re-review against `cp2d/review.md` and `cp4/review.md`). Check `cp2d_reader` → CP-3C, the `CP2D_D7_DELTA` and `CP3C_D7_DELTA`, and FP04.
- **C, the rest:**
  - CP-1C;
  - the CP-1D fixes (against `cp1d/review.md` M1, M2 and L4);
  - CP-L10 fix1 (against `cpl10/review.md`);
  - the stage-level class test `tests/test_stage2_classes*.py`;
  - the integration test-side fixes and the D12 manifest chain;
  - the G1 I2 check (backlog: does the receipt step-hash refuse forged step `issues` that `probe_one_step` does not recompute? If not, Medium).

## Process
For each module in your lane, check:
1. the adapter against the real upstream head shape (not only the fixtures);
2. one adapter shared by `submit`, `probe` and `view`, with stale and swapped inputs refused;
3. the round 3 rules (citations, `RunText`, synthetic limitation, aliases) and `listed_issues`/`clipped`;
4. registrations, bindings and `_Spec` rows against the lease and the oracle FP pages;
5. that each deferred acceptance test is real and would fail on the defect it names. Reason through at least two per module, or run one if it takes under 2 minutes.

Also:
- Re-run the lane's gates.
- Write a probe for each finding and name it in the finding.
- Do not edit anything.
- Rules for a finding: no stub or fake standing in for real behaviour, and no catch-all that hides a failure unless documented and logged.

## Outputs (report as text, at most about 2k tokens)
- A verdict per module (APPROVE or REQUEST CHANGES).
- Findings by severity, each with file:line, the failure scenario and its probe. Mark predating findings "predates".
- Gate exit codes.
- `Not verified:`.
