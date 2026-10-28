# CP-8 fix round 1 report (mx-feature)

CP-8 fix round 1 is done. M1, M2, L1, the rebase-time rulings (citations, model text, synthetic limitation) and the Info docstring are all addressed. Commit 1a2887f is on top of 8fab26b. Each new test was written first and watched red, except where noted below. The fast gates exit 0 and p4 still exits 1 on S1, which I believe cannot be killed (see S1 below).

**M1 (settled limitations).**
- The old `tests/test_owner_cp8.py` failed red on the extra synthetic line, as the review said.
- The tests now assert own = oracle own + "Synthetic case; not real issuer qualification", deduplicated.
- Inherited is checked two ways: the oracle's list minus that line, and the output of `execution.inherited_limitations` called on the real store.
- `cp8_reader.limitations` returns the settled own list. The reader docstring and the `Cp8Head` comment now say a synthetic run's line is included.
- The pin is a head built by `settle` (a real run), in `test_connect_cp8.py::test_the_reader_returns_the_own_limitations_settle_wrote` and in `test_owner_cp8.py`. Mutant R1 is killed.
- `p2` still exits 1. It compares the settled list to the oracle's pre-settle own list, which is the finding itself. It agrees with the tests only if it is changed to expect the synthetic line. That is for the controller or LEAD.

**M2 (lease acceptance store tests).**
- I ran `tests/test_owner_cp8.py` for the first time. It has 85 tests and takes about 15 s.
- The driver `tests/cp8_runs.py` gained `start`, `read_pages` and `submit`.
- Acceptance 3 (no_record): CP-0 gives "DO NOT RUN", there is one `RefusedBegin` with the NotAuthorized text, no CP-8 attempt or head, and the receipt verifies.
- Acceptance 5 at run level:
  - All 68 refusals r01-r69 plus r00 are journaled as validator issues then RULES issues.
  - r42 appears twice, in the step's journaled issues. The attempt-level issues de-duplicate it, so the test asserts the step.
  - t01-t03 pass.
  - Blocked: attempt 0 r23, attempt 1 r03, head blocked with no tables, `repair_of` set.
  - `extract_statements` and `read_inputs` are `not_permitted`, an identity read is not ok, and `stale_binding` fires after an external interrupt.
- Acceptance 6 (tamper, per the lease recipe):
  - The forged copy passes `_verify_audit`.
  - A spy confirms `verify_owner_run_receipt` reaches the CP-8 probe, which raises `identity_mismatch`.
  - A direct `cp8.probe` call raises `identity_mismatch` too.
- `submit` is exercised by the closed runs, the refusals and a drift spy. The drift spy kills S2.

**L1 pins.**
- R2: the reader refuses a missing or fractional count. R3: the reader refuses a missing overall label or process. R4: the head's status passes through.
- U1/U2: RULES counts an absence only on the optional fields. There are 8 required-field cases.
- B1/B2: a blank quote is judged after the pack, scope, must-cite and realized-source rules.
- P1: `NOT_AN_OBJECT` is tested directly and through the entry validator.
- The `cp8_upstream` docstring no longer claims the reader uses it.
- **S1 is equivalent, so `p4` exits 1 on it alone.** `_with_rules` returns the outcome unchanged when RULES adds nothing, so "always wrap the rules" cannot differ from the original. The run-level r42 test is in place.

**Round-3 rulings.**
- **Citations:**
  - A bug in `citations()` was found by the new test (red first). A derived fact kept one citation per distinct quote, so the same page appeared up to twice.
  - It is now one citation per page, quoting the first input quote on that page, in input order.
  - `test_a_fact_carries_one_citation_per_page_and_never_invents_a_quote`, `test_a_derived_fact_quotes_the_first_of_its_input_quotes_on_each_page` and `test_a_sourced_fact_quotes_its_own_field` pin this.
  - Both a last-quote mutant and a per-quote mutant are killed.
  - The oracle compares page pairs, so no expected value moved.
  - The derived rule is stated in `src/deploy_vii/methods/cp8.md`.
- **Model text:**
  - The validator's analyst-text check is stricter than `RunText`: it refuses digits, `{`, `}`, `[`, `]`, blanks and prohibited words.
  - So I made no `src` change. I added a hostile-text test: 15 values at every analyst-text site, giving an issue or a composed Module, never a raise. It is green on arrival.
  - Not done: a `RunText` `TypeAdapter` guard. It would be unreachable dead code, and no mutant could kill it.
  - The shared class test in `defect_classes.py` has not landed on the lane.

**Gates (all exit 0).**
- pytest on the connect, owner_cp8, method_cp8, owner_g1x, host_h1 and defect_classes_selfcheck files: 1665 passed in 34 s.
- ruff check and ruff format --check on the 7 changed files, and `mypy --strict` on the same files.
- My mutants: 38 run against a full copy, 38 killed, none survived. The script is `<S>/cp8-s2/mutants.py`.
- Reviewer probes:
  - `p1_quote_sites`: 0.
  - `p3_parse_and_digest`: 0.
  - `p2_synth_own_limitations`: 1, as explained above.
  - `p4_review_mutants`: 1, only S1, which is equivalent.

**Deferred registration data.** The D12 shas in `docs/reuse/manifest.json` are unchanged by this round, because none of the three D12 files changed.

**Not verified:**
- `tests/test_owner_workflow.py` and `tests/test_owner_s1a.py` were started but not finished (they run for minutes), so there is no exit code for them. The `owner_workflow.py` change from the first pass is registration rows only.
- The `defect_classes.py` shared model-text test is not on the lane, so it has not been run over the CP-8 payload.
- No CP-6-bound run-level case ran, because CP-6 cannot be bound in Stage 2.
- Whether `NOT_AN_OBJECT`'s wording is accepted, and whether LEAD flips the synthetic-limitation ruling, are open. A flip is one test line plus the reader docstring.
- The `docs/reuse/manifest.json` shas were not re-checked.
- The T7.2 binding label versus table-title difference from the review's Info was not touched.

agent=mx-feature fix-rounds=1 gates-first-pass=n
