# O1 Task 2 review (commit fdaae9e0), 2026-11-01

Probes: `scratchpad/probes-o1t2/` (mx-precise), `scratchpad/probes-o1t2/adv/` (mx-adversary).

## mx-precise: Spec ✅, Quality fix (1 Medium)
- Rows and `owners/cp6.py` as briefed; callers by node id pass (test_connect_cp5 ×7, test_owner_g1x ×3,
  test_owner_stage4 ×4, test_owner_order 21 non-promotion, test_owner_presets, cp6 fast ×2).
- **M1** tests/test_owner_cp6.py:362 `runs.literal(CASE, "committee_challenge")`: `literal()`
  (tests/cp3_cp6_runs.py:111-137) has no such case (KeyError), so both gated tests can never pass CP-6. Fix: read
  `oracle()["submissions"][CASE]["committee_challenge"]` or add the case to `literal()`. Probe
  `probe_literal_cp6.py`.
- Low: the CP-6 plan test lives in test_owner_cp6.py:326, not test_owner_presets.py (the brief's RED section
  allows it).

## R6 oracle finding (mx-autonomous root cause, read-only), 2026-11-01
Probe `scratchpad/r6probe/probe.py` over src at 2682310b, 562a3bc7, 01ee8514, 5a00d7be, fdaae9e0: identical R6
results (plan CP-0, CP-1, CP-1A, CP-2, CP-3, CP-5, CP-6; no CP-MODEL; CP-0 consumers match the oracle; CP-1A
consumers CP-2, CP-3, CP-5, CP-6, CP-MODEL).
- **Pre-existing oracle defect, not caused by O1:** `cp1a_consumers` (src/deploy_vii/business_context.py:344-353,
  check :681-685) adds "CP-MODEL always (r14)" whatever the run selects (since bootstrap df26ea82; present at
  2682310b, which froze R6). The builder `cases/cp3-cp6-owner/builder/build.py:209-216` requires `m in _sel`
  before the CP-MODEL clause, so its self-check passed on the wrong list (:171).
- Wrong frozen expectations: submissions `business_context.consumers.R6`; expected positive and gap
  `upstream.CP-1A.R6` (`consumers_judged`, `downstream_readiness` and T2D.10 rows, CP-MODEL as r05,
  `catalogue_size` 76→78 and 74→76); manifest `runs.R6.cp1a_consumers`.
- Recommended amendment (for the oracle owner): append "CP-MODEL" at build.py:171 (CP-1A judgment row only; no
  CP-MODEL stop, per the manifest's rev-1 intent "R6 has no CP-MODEL head"); fix the self-check at :209-216 to the
  code rule; rebuild; re-pin PINS.json and the cp5-owner, cp3d-owner, cp8-owner manifests (and
  docs/TOOL-CONTRACT.md if it pins them). Helpers need no change (`drive_cp6` never calls `publish_stop`).

## Controller rulings
- The R6 defect predates this plan: it goes to the oracle owner (user / Modules; final report), not into
  Task 2. Task 2's two gated tests stay deferred and blocked on it (`Not verified:`).
- Fix round 1 for Task 2: M1 (`drive_cp6` reads the CP-6 literal from `oracle()["submissions"][CASE]`), plus
  the adversary's findings when they arrive.

## mx-adversary: approve (no findings)
Probes `scratchpad/probes-o1t2/adv/` p1-p6 exit 0 (registration, probe tampering incl. cross-run and stale CP-5
heads, ordering across the CP-MODEL stop and refused/blocked CP-5, invalid replay, host producer, owner path).
Info: `_verify_chain` does not order modules inside a phase; `_expected_begin` does.
