# CP-DR fix round 1 report (mx-feature)

CP-DR fix round 1 is done: M1, L1, L2 and L3 are all addressed, in three new commits on top of 1e3942a, ending at 28b2dce (b22972d fix, a3eeeed manifest record, 28b2dce format). Worktree /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-cpdr, branch claude/s2-cpdr. The b22972d commit message says the tests were written first, but they are in the same commit as the code. Each new test was red before the matching code existed (checked for the L1 and L2 tests), except the M1 tests, which only exercise existing behaviour.

**M1 – deferred tests.** The new tests are in tests/test_owner_cpdr.py, and I ran them: 30 passed in about 5 s.
- Acceptance 8: the tamper recipe at verifier level. `owner._verify_audit` passes on the forged copy, and the receipt verifier reaches the CP-DR probe, which raises identity_mismatch. A spy on `_PROBES["CP-DR"]` records that the probe was reached.
- Acceptance 5: run-level refusals. Submit before read_inputs is not_permitted. extract_statements is refused not_permitted. A snapshot change between read and submit gives stale_binding.
- Acceptance 6: the blocked case through OwnerWorkflow. Its receipt verifies, the head is blocked, and the reader returns status only.
- Acceptance 1: store bytes are identical before and after verifying the receipt, for all three positive cases.
- D3: the reader is called on the closed-run head and matches the oracle's bookkeeping and unresolved ids.
- tests/cpdr_runs.py: `replay` now asserts `expect_spans` and `expect_matching_spans` by parsing the tool body.

**L1 – mutants.** The varied fixtures kill A1/A13, A2, A3, R11 and R12.
- The test `Store` double's `head_only` mode makes `result()` fail and `head_module()` apply the head's live status.
- New tests cover CP-0 status `accepted`, a different run as_of, a `missing` pack source, and `accepted` and `stale` heads.
- The reviewer's review_mutants.py against the new tree: only A7 and A16 survived, which the reviewer classed as equivalent. R1, R9 and R13 were skipped because the code moved and their patterns no longer match; my own mutants cover them.
- My own mutants.py (in `<S>/cpdr-s2/`): 54 killed, 0 survivors, plus the one justified equivalent `submit-candidate-check`.

**L2 – reader fails closed.** `cpdr_reader` now refuses:
- a known share carried as text;
- a non-integral or negative count;
- a missing per-gap unresolved or answered_share fact;
- a per-gap unresolved count that differs from questions less answered.

I also added a refusal for a TDR.1 gap row whose answered share is not known, which you did not ask for; it follows from reading that fact.

**L3.** The `post_import_patches` record for shipped.py is in docs/reuse/manifest.json, in the CP-L10 form. It carries the current sha256, and its `project_commit` is b22972d. The controller fixes the commit at merge.

**Reviewer probes, exit codes:**
- probe_run_refusals.py: 0
- probe_rules_only_receipt.py: 0
- probe_closed_run.py: 0
- probe_reader_edges.py: 0, and it now prints "refused" for the three forged shapes

**Gates, all exit 0:**
- The fast set passed: test_connect_cpdr, test_method_cpdr, test_owner_g1x, test_host_h1, test_defect_classes_selfcheck, plus test_owner_cpdr. That is 561 passed in about 14 s.
- ruff check and ruff format --check pass on the changed files.
- mypy --strict passes on the 7 changed src and test files.

Not verified:
- test_owner_workflow.py, test_owner_s1a.py and the render suites were not run.
- Crash-resume between a valid step and `finish` is untested.
- The oracle builder rebuild was not run.
- jscpd and the suppression count were not run.
- The tamper test forges only the status fact. The other recipe variants (an edited step output, a receipt-only rewrite) are not covered.

agent=mx-feature fix-rounds=1 gates-first-pass=n
