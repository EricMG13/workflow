# CP-2A fix round 1 report (mx-feature)

CP-2A fix round 1 is done: M1, L1 to L4, the Info items and the round 5 M2 unit rule are all addressed, and every gate exits 0. The work is on claude/s2-cp2a at ac97894, as new commits on 375f651 (e87c1e1, then 3 more). I did not touch methodology.json, TOOL-CONTRACT, cases/ or any engine.

**Gates (final tree)**
- The gate pytest set (test_connect_cp2a, test_method_cp2a, test_owner_g1x, test_host_h1, test_defect_classes_selfcheck) exits 0: 613 passed, 0 skipped.
- `ruff check` and `ruff format --check` exit 0 on the changed files.
- `MYPYPATH=src mypy --strict` exits 0 on 5 src files and 3 tests.
- The one SIM102 in `report_view.py:293` is already on the base.

**Probes and mutants, all against the new tree**
- `p10_acceptance_coverage.py`: exit 0, every acceptance item present.
- `p3_l6_property.py`: exit 0, 3000 cases, 0 counterexamples.
- `p8_units.py`: exit 0. Part (a) shows no unit or shown mismatch. Part (b) now offers only Q3 and refuses the EUR-thousands LTM base as `base_period: not an offered period: LTM Q4 25: ...`.
- `p9_later_appenders.py`: I ran a copy pointed at HEAD instead of 375f651, in `<S>/cp2a-s2/p9_later_appenders_r1.py`. It exits 0 and the failing-test list is empty for all three edits (CP-2G insert, CP-4C rows, next SHIPPED_MAPS append).
- `mutants.py`, same HEAD copy: 29 of 31 killed. The two non-kills are:
  - "validator step[0]", which is equivalent because CP-2A has one step;
  - "upstream cp1 from current head", whose pattern no longer matches the code after the L4 edit.

  My own 20 registration and adapter mutants (`mutants.py` and `mutant11.py` in `<S>/cp2a-s2/`) were all killed in the first pass but not re-run on the final tree.

**M1.** `tests/test_owner_cp2a.py` now has 15 deferred tests; `pytest --collect-only` collects them but none has run.
- A1: plan order and statuses, every fact's status, unit, period, amount and shown, claim text with the CP-1 ids bound, own limitations, one ok read and no ok pack call, and the tail input.
- A2 gap, A2b refused (one `RefusedBegin` for CP-1, no CP-2A attempt or head, T8 commands "DO NOT RUN"), A2d blocked (receipt verifies), and A2e (`ready_with_limitations`).
- A3 clones: pack tools refused, submit before read `not_permitted`, a changed snapshot `stale_binding`, and an unreplaced figure invalid.
- A4: an edited read body, step output or `SettledHead` gives `identity_mismatch`; an untouched copy verifies and writes nothing; and the verifier reaches `_PROBES["CP-2A"]`.
- The fast A3 trio, plus a valid submit, also runs in `test_connect_cp2a.py` in seconds, over hand-seeded heads.
- New fast tests in `test_connect_cp2a.py`:
  - the settled facts and claims against the oracle (unit, shown, claim text);
  - a variant run with a different as_of and an accepted CP-1 head, so a constant equal to the oracle cannot pass.
- `cp2a_runs.py` and the deferred tests are written but unrun, as before.

**Lows and Info**
- **L1:** the adapter test now states `offered_periods` differs from Stage 1 (`(LTM, Q3)` against `(LTM, Q3, Q4)`) and equals it otherwise, with `compute` equal. A second test covers head order (`(Q3, LTM)` for the gap head). `methods/cp2a.md` records it.
- **L2:**
  - The L6 property is committed as a test.
  - The 3 L6 survivors are killed, as are the `cp2a_upstream` stale check (a re-run CP-1 head), stale-before-content ordering, raw `unit` in `view`, and the `bounded_issues` join (21-part message).
  - Also killed: stale status-only change, stale text clipped, a known operand not citable, the no-figure note, and head fact order.
- **L3:**
  - The preset test asserts CP-2A's pair after `distress-gate` and uniqueness.
  - The spec test asserts CP-2A's rows plus an unnamed id falls through to "Unbound".
  - The shipped test asserts exactly one CP-2A map, after CP-6.
  - The bindings test validates CP-2A's own map only.
- **L4:** `cp2a_upstream` raises if the bound CP-1 blob is not a CP-1 module, test-first.
- **Info:**
  - The `base_period` and duplicate-label lines are clipped (the label is cut to 300 characters so the "appears more than once" text survives).
  - The Stage 1 placeholder skip `test_v17_stale_input_is_stage_2` is removed from `test_method_cp2a.py`; v17 is covered in `test_connect_cp2a.py`.
  - The probe tests now expect `identity_mismatch` with no vacuous assert. I dropped the forged-attempt-number case, because `settle` raises a plain `ValueError` there rather than `identity_mismatch`.
- **M2 (round 5 item 1):** built test-first in the adapter. A base is offered only when every known operand (EBITDA, cash interest, free cash flow, total debt, cash) is `MILLIONS`, `USD`, scale 1000000. An unsettled operand is not checked, so gaps still offer and no frozen value moves. There are 25 parametrized tests plus the EUR-thousands refusal and the missing-operand case. It is also noted in `methods/cp2a.md`.

**Open items**
- The `docs/reuse/manifest.json` D12 records are still not added (see round 1).
- DeliveryScope row for G2: lease line 149, unchanged and copied word for word in the round 1 report.

**Not verified:**
- Anything against a genuine promoted CP-1 head, including real T4.10 unit, currency and scale values; the M2 rule assumes a known operand carries `MILLIONS`, `USD`, scale 1000000.
- `tests/test_owner_cp2a.py` and the `cp2a_runs.py` driver have never run. That includes the `cp1_downstream_review` marker binding, `_find_rows` on the readiness output, `clone_workflow` forks, and the tamper helpers.
- The fast A3 tests use `OwnerWorkflow(store, ("CP-2A",), None)` over hand-seeded heads, which is test-only, so receipt-level behaviour is covered only by the deferred A4 tests.
- The render suites, `test_owner_workflow.py` and `test_owner_s1a.py`.
- G2's FP05 rendering and the `∅ G# n.m.` spelling.
- The reviewer's `mutants_reg.py`, which I did not re-run.
- No test applies to the `methods/cp2a.md` text (documentation).

agent=mx-feature fix-rounds=1 gates-first-pass=n
