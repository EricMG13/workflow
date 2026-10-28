# CP-3 fix round 1 report (mx-feature)

CP-3 fix round 1 is done and committed as f5d5bc4 and e2669a2, on top of 8704e1f. The fast gates and mutants are green. The deferred acceptance suite (38 tests) is written and has not been run.

**M1 (acceptance tests)**
- Run now, in `tests/test_connect_cp3.py` (105 tests):
  - **Create-time refusals:** a spec override (4 variants), CP-4C, CP-3D, CP-2D and CP-3C added to a CP-3 run, and a plan with CP-5 but no CP-5 spec. Each has a control selection (`CP-1, CP-1A, CP-2, CP-3`, no CP-MODEL) that `create` accepts. Each refusal asserts `not_permitted` and that nothing was written. The CP-5 test skips itself once CP-5 gets a spec.
  - **Context block checks:** run over a begun store for the positive, gap and blocked cases, including that the four optional ids are absent from the body.
  - **Settled head equals the oracle:** tables, claims, module inputs and the `settled_limitations` list.
  - **Blocked-CP-1A variant:** the receipt-level part is deferred. The fast part settles over a blocked CP-1A head, checks the input statuses, the settled limitations and the "Upstream CP-1A blocked: " prefix list, then re-derives the head with `cp3.probe`.
  - **Render:** the FP01 `relative-value` block (owner, kind, state, summary, lines), the rail table ids, and the own/settled module limitations.
- Deferred, in `tests/test_owner_cp3.py`:
  - the receipt, store bytes and plan;
  - the upstream equalities: CP-0 R3, the CP-1A deltas with `catalogue_size`, and CP-2 equal to S1;
  - the CP-2 read-body key tree and register counts;
  - the CP-3 head, the `inherited_limitations` order and the hash-equal inputs;
  - CONTEXT, render and the probe, over the real run;
  - the tool-use counts, including `read_pages market page:1` in CP-0, CP-1 and CP-1A;
  - the three refusals: unread page (re-begun as attempt 1), out-of-scope read (both cases) and `cp3-stale-snapshot`;
  - A4 tamper (a), (b) and (c) on a copy of the closed positive run;
  - the blocked-CP-1A variant with its receipt and re-derived head.
- Driver additions in `tests/cp3_cp6_runs.py`: `through_cp2`, `blocked_through_cp2`, and a `requested=` option on `make_pack`/`promoted`/`reach_cp3`/`cp3_closed`.
- **Not written:** a D3 test, which stays "blocked on CP-6 freeze". Also not written, as in the first report, the CP-3 head's cell-level `render` text over a real run is covered, but no test exists for the draft CP-6 half.

**M2 (CP-3B).** I followed LEAD's canonicalise ruling.
- Fast: a CP-3B selection plans the same as CP-3 and `create` accepts it. `CP-3B` is not in `OWNER_SPECS` or `SUPPORTED_ANALYTICAL`. A store run from a CP-3B-named pack settles heads and attempts named CP-3 only. `MODULES.csv` shows CP-3B all `unverified` with `case_evidence none`.
- Deferred: `test_an_alias_run_counts_no_alias_completion` checks the real receipt (plan and heads CP-3 only). It needs a third CP-1 promotion, because the pack hash changes with the module name.

**L1.** The attempt-1 fixture is a third `settled` parameter (an invalid first literal, then a repair). The `cp3_module(..., 0)` mutant is now killed.

**L2.** These four driver mutants survive the fast gate and only the Stage 5 run can kill them. They belong on the deferred list:
- `drive_cp1` ignoring `context=`;
- `cp1_bindings` taking the first match instead of exactly one;
- the market `extractor` dropped;
- `drive_cp3` skipping the reads.

**Other rulings.**
- **Synthetic limitation:** own is the oracle list then "Synthetic case; not real issuer qualification", deduplicated. Pinned on a head built by `settle` (fast) and over the real run (deferred).
- **Citations:** this does not apply to CP-3. There is no CP-3-side citation or adapter code, and the citation logic is in the engine (`src/deploy_vii`), which Stage 2 does not edit.
- **Model text:** the shared `defect_classes` class test has not landed on this branch, so the local hostile-text stand-in stays.

**Gates and mutants**
- pytest set (test_connect_cp3, test_method_cp3, test_owner_g1x, test_host_h1, test_defect_classes_selfcheck): exit 0, 421 passed.
- `ruff check`, `ruff format --check` and `mypy --strict`: exit 0 on the 6 changed files.
- My `<S>/cp3-s2/mutants.py`: 23 of 23 killed, exit 0.
- Reviewer `<S>/cp3-s2-review/mutants.py`: 4 killed, 4 survive (the L2 four), so it exits 1 as the review expected.
- Probes: the earlier `p_create.py`/`p_create2.py` behaviour (R3 as pinned is refused until the ordering change lands) is unchanged.
- Test-first: the new tests were written first, but I ran them only after the code existed. The one failing run was a helper bug in my own tests, not in `src`.

**Deferred commands** (add to the earlier list; all heavy, under the lock)
```
mkdir /tmp/deploy-workflow-heavy-job.lock && { PYTHONPATH=src:tests "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider -o faulthandler_timeout=1800 tests/test_owner_cp3.py; rc=$?; rmdir /tmp/deploy-workflow-heavy-job.lock; exit $rc; }
```
This single command covers every deferred test above. The R3 `create` still needs the `claude/s2-g1x-order` change to merge first.

Not verified: every test in `tests/test_owner_cp3.py` has never run (collect-only: 38 collected). In particular the following are unchecked:
- the CP-1A delta application;
- the `cp1a_rows` register-prefix counting;
- the inherited-limitations formula for CP-3;
- the tamper (a) audit-file rewrite;
- the stale-snapshot `interrupt`;
- the blocked-CP-2 literal staying valid under CP-3's cp2_refs;
- the alias run.

Also not run: R3 `create` with CP-MODEL, the receipt verifier on any CP-3 run, and GitNexus, jscpd, complexipy and bandit. The CP-1A blocked head's issue texts in the fast test are Stage 1 placeholders, not a real A3b head.

agent=mx-feature fix-rounds=1 gates-first-pass=n
