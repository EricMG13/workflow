# CP-2E rounds 5 and 6 report (controller-saved from the implementer's hand-back)

# CP-2E report: E6–E8 (round 5) and A3–A4 (round 6)

E6, E7, E8, A3 and A4 are applied test-first and committed. One branch has no ruled wording and now fails closed for LEAD: a fixed-rate facility with a floor above zero.

**Commit:** `af23f7f` on `worktree-agent-a219254fe68cc1c2d`.
- Its base: `bdad3c8` merged, then `8483de4` (E6) and `3674158` (round 6) cherry-picked as `c906687` and `5fe9a1f`.
- The CP-2E pins after the cherry-picks match: expected `8f507e10…`, builder `de0d14fc…`.
- No test asserts those pins, so nothing needed re-pinning. Other modules' files were left as they came.

## Each ruling and its test
- **E6:** the strict xfail is removed. `test_composer_fixture[fixture_no_rate_terms]` is now the live E4a test against the amended oracle, with the oracle unedited. The separate live test from 900dce4 was redundant and is removed.
- **E7:** `test_e7_coverage_after_not_meaningful_with_base_known`.
  - `cov_after` and `cov_change` are not_applicable with `Not meaningful: interest after the shock is zero`, or `… is negative` under A3.
  - The claim text is exactly the round's wording, with "zero" or "negative".
- **E8:** `test_e8_hyphenated_rate_phrases_count` covers `floating-rate`, `Fixed-Rate` and `floating -  rate`. `test_e8_both_stems_hyphenated_is_neither` is a guard; the old code also met it. The regex is `\b(floating|fixed)[\s-]+rate\b`, case-insensitive, and both or neither gives the existing issue. The E5 tests are still green.
- **A3:** `test_a3_negative_divisors_are_not_meaningful` and `test_a3_negative_base_coverage_falls_under_e3`.
  - A divisor ≤ 0 is not_applicable on every ratio: base coverage, coverage after the shock, leverage, both shares of total debt, the share of EBITDA, and leverage after the currency move.
  - The zero reasons are unchanged, and negatives read `<divisor> is negative`.
  - Negative base interest takes the E3 path.
- **A4:** `test_a4_floor_above_zero_limitation` and `test_a4_fixed_rate_with_a_floor_above_zero_fails_closed`.
  - `_LIM_FLOOR` appears only for a known zero floor; the positive case is unchanged.
  - A floating rate with a floor above zero gets the ruled text.
- **Grid:** `test_valid_inputs_settle_with_clean_claims` now runs 648 combinations, with negative EBITDA added. Every one settles with prose-clean claims, except the 108 fixed-rate, floor-25 combinations, which fail closed under A4.

## The group A reviewer's `fig()` raise
That raise fired when base coverage was known and after-shock coverage was not meaningful. It is now covered:
- **Validated inputs:** under A3, base coverage is known only when cash interest is above zero. Interest after the shock is then above zero too, since a validated added interest is never negative. So the old repro (cash interest −0.5) now takes E3 with a chip.
- **E7's branch:** this is the only path to base-known with after-n.m. It is reachable only from inputs built directly with a negative added interest, which is how the E7 test reaches it.
- Nothing from validated input reaches `fig()` on an unknown fact, which the grid confirms.

## Raises left
- **A4, fixed rate with floor above zero:** raises `ValueError("Floor limitation: …")`. This is reachable through validation, given a quote containing "fixed rate" and "floor 25 basis points". The A4 text would say "the rate shocks are not calculated", which is false here because the added interest is a known 0. Listed for LEAD.
- **Unreachable guards that fail closed:**
  - an unknown reason for a missing added interest (`_gross_needs`);
  - an E7 reason outside zero/negative;
  - a negative floor, which only direct construction can give;
  - `fig()` on an unknown fact.
- **A4's floor-not-stated text** is not implemented. It has no path, because `FacilityTerms` requires a quoted floor; T2F.1 r06 also has no pinned gap wording. Listed for LEAD.

## Probes (exit codes)
- `stage1-review-A/probe_cp2e_negative_denominator.py`: exit **1**. It printed `negative coverage is a known value: False`: cash interest −2 now gives base coverage not_applicable with "cash interest is negative". As expected, since it exits 0 only while the old behaviour reproduces.
- `probe3.py` (fix-1 reviewer): exit 0. Both oracle cases' claims are equal, P2/P3/P4 compose, and the old and new row-value patterns agree on all tokens.
- `cp2e-r6/probe_new_strings.py` (new): exit 0.
  - It ran 20 claims from the E7, A3/E3, A4 and negative-EBITDA paths through `prose.issues`, and their literal text outside references through `bare_figures`.
  - It also ran every limitation and reason through `bare_figures`. No hits; the control `control 20 here` returns `('20',)`.
  - A first draft wrongly ran `bare_figures` over whole claim text, where the digits in reference ids such as `r01` counted as hits. That was corrected.
- `cp2e-r6/mutants.sh` (new; each mutant runs from a full rsync copy, to avoid the `pythonpath` shadowing): exit 0. All four mutants are killed:
  - A3 `<= 0` changed to `== 0`;
  - E8 `[\s-]+` changed to `\s+`;
  - A4 `floor == 0` changed to `>= 0`;
  - E7 branch switched off.
- Both new scripts are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-r6/`.

## Tests and gates
- **Tests:** `PYTHONPATH=src …/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp2e.py` gives **84 passed** in 1.38 s, exit 0, with no xfail. The new ruling tests each failed before their change, apart from the guard noted under E8.
- **Gates:** `ruff check` 0, `ruff format --check` 0, `MYPYPATH=src mypy --strict` on both files 0. The first gate run failed on 3 ruff FURB157 hits and 2 mypy errors in the test helpers, all fixed.

## For LEAD and Stage 2
- **Hits:** no `prose.issues` or `bare_figures` hits.
- **Builder sync:** none outstanding for CP-2E. LEAD's A3 sync is already in `3674158`.
- **Stage 2 notes:**
  - A4's floor-not-stated text needs a path only if the Stage 2 schema allows a missing floor. If it does, T2F.1 r06 also needs gap wording.
  - Since E8, a hyphenated "fixed-rate" counts.
  - The A4 fixed-rate wording is needed from LEAD.

Not verified: wording for a fixed-rate facility with a floor above zero; A4's floor-not-stated text; Module/Fact assembly with real Citations; inherited limitations; `RULES`, tool-use refusals, tamper and probe; rendering; any settled run; validator behaviour on payloads that aren't schema-normalised. No rewrite tournament was run this round.

Ledger line:
`2026-10-28T13:57Z cp2e-stage1-round5-6 pytest tests/test_method_cp2e.py exit=0 84 passed 0 failed agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n`
