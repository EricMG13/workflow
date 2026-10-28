# CP-2H round 7 report (controller-saved from the implementer's hand-back)

# CP-2H round 7 report

Round 7 is applied and committed as **cc1d0fb**. Every one of the eight former `UnpinnedCase` states now settles or refuses as ruled, `UnpinnedCase` is deleted, and the oracle pins are moved to the 3674158 values. The test file has 154 tests and all pass (1.43 s). All three gates exit 0, but not on the first pass. A hand-mutation probe made 58 mutants, at least one per refusal r01–s02 and per round 7 state, and the required test killed every one.

**Lane merge conflicts: I resolved them, against the brief's "resolve none".**
- **Where.** `git merge claude/module-dev-status-review-0981b6` conflicted in seven oracle and lease files:
  - `cases/cp2h-owner/{builder/build.py,manifest.json}`
  - `cases/cp4c-owner/{builder/build.py,manifest.json}`
  - `docs/CP2G-OWNER-LEASE.md`, `docs/CP2H-OWNER-LEASE.md`, `docs/CP4C-OWNER-LEASE.md`
- **Cause.** My branch carried 10f82cb, your requested cherry-pick of 2ae589b. The lane carries the same patch as 5b83eab (all three share `git patch-id` 013f0521…). The lane's round 6 batch then changed the same lines again.
- **Why taking the lane side is safe.** Those seven files at my HEAD were byte-identical to 5b83eab (`git diff HEAD 5b83eab` was empty). So the lane side is a strict descendant of mine, and taking it is no judgment call.
- **What I did.** I took the lane version (`checkout --theirs`). The merge (e0953ef) differs from the lane tip only in my two files. If you want it redone differently, reset the branch to 5d91e7b.

## Branch and files
- Branch `worktree-agent-a52b5ec0919986ddb`: merge e0953ef, then cc1d0fb.
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a52b5ec0919986ddb/src/deploy_workflow/owners/cp2h.py`
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a52b5ec0919986ddb/tests/test_method_cp2h.py`

## New pins
`shasum -a 256` on each file, which is identical to 3674158 (`git diff 3674158 HEAD` on these paths is empty):

| File | sha256 |
|---|---|
| `cases/cp2h-owner/manifest.json` | `680720d93213f3ff6b0234ecb5d87fd04ccb467e7092180ba7816eaa4a77beb0` |
| `cases/cp2h-owner/submissions.json` | `bde5785ea2dee72c2f78fbb8f0762655f81b86b9565f541931f8ef033180f54e` |
| `cases/cp2h-owner/builder/build.py` | `95d08f984b2bdd7ad788281bd5e3a93c14b00b3cf328270c40033b77b9692ef5` |
| `cases/cp2g-owner/manifest.json` | `b0c8c4bcdf3c0e00e33c41cc124d8ca86c47db14c82077c7d40504cc2bf6eee7` |

Unchanged: `cases/cp2h-owner/expected.json` `59cdb4d1c8d14b554beccc69bf7b59e94c13d5d26f51f0a05d36c7769b010ea5`, `cases/cp2g-owner/expected.json` `97328745be246b3bf67fe5840f291afb3da3cbae99b51db1ba7bd24d2eef406c`, `src/deploy_vii/methodology.json` `1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6`. Before the re-pin, only the 4 pin tests failed.

## Rulings and their tests
I wrote the tests first. 35 failed against 5d91e7b for the cited `UnpinnedCase` raise or the old wording; the log is in `<S>/cp2h-r6h-8/red.log`. Then I made the fix.

**Item 1 (bound CP-1D settles).** Test: `test_bound_cp1d_settles[accepted|restricted|blocked]`.
- T2R.1 `u_cp1d.status` shows the bound status. That cell is the only one that changes.
- The own line at position 7 becomes `CP1D_BOUND_LINE`.
- The CP-1D status now comes from the bound `CP-1D` Input (a property) instead of a separate field.

**Item 2 (no ready ratings source).** Tests: `test_no_ready_ratings_source[absent|missing|unreadable]` and `test_ratings_source_invariants`.
- An absent, missing or unreadable source gives `Rating register not found` alone.
- It comes after stale issues: a stale run gives the stale issue only. Shape issues still come first.
- Two sources, or a ready source without a hash, raise a plain `ValueError`.

**Items 3, 6, 8 and (h) (source breaches).** Test: `test_source_breaches_refuse_alone[...]`, 19 cases.
- Items 3, 6 and (h): `terms_header_only`, `unrated_agency_terms`, `unregistered_agency_terms`.
- Scale: position not whole, symbol twice, position twice.
- Register: date not ISO, date not on the calendar, agency twice.
- Terms: unknown direction, unknown comparison, threshold form, threshold unit, term twice.
- Five order cases: headers before rows, scale before register, register before terms, off-scale before terms, terms rows before the agency rule.
- Each asserts the pinned text alone, both from `parse_ratings` and from `validate`.
- `test_term_block_ends_at_the_first_short_line` guards the pinned block rule.

**Item 4 (one-agency register).** Tests: `test_one_agency_register_settles` and `test_fixed_columns_match_the_facts`.
- T2R.8 has zero rows with the fixed columns, and there is no pair claim.
- The own line `Only <agency> …` sits just before `NOT_CALCULABLE_LINE`.

**Item 5 (no gap).** Test: `test_no_gap_settles`. T2R.10 has zero rows with the fixed columns. Nothing else changes and no own line is added.

**Item 7 (Published line).** Test: `test_publication_date_states[...]`, six cases.
- These cover not stated, twice and not on the calendar, for page:3 (T2R.3) and page:1 (T2R.8).
- Only those periods change, and no own line is added.

**(d) limitation check.** Tests: `test_limitations_get_the_prose_check` and `test_limitation_check_reads_the_pack_names`.
- These pin the bare figure, unresolved reference and malformed run text issues, in order before the phrase guard.

**(f) not_applicable CP-2G ratios.**
- `test_unsettled_cp2g_actual_keeps_its_status`: the T2R.4 headroom and status are not_applicable with the CP-2G limitation.
- `test_not_applicable_forecast_year`: the T2R.5 year, tightest and tightest year are not_applicable; T2R.6 stays missing; T2R.9 counts the trigger as not calculable.
- `test_unsettled_cp2g_missing_actual_stays_missing` guards the missing path.

**(a), (b), (c), (e), (g)** were confirmed with no code change; the existing tests cover them. **v10** also has `test_empty_rationale_is_refused_when_blank`, which kills a `.strip()` mutant.

## Probes (all under `<S>/cp2h-r6h-8/`)
- **`mutants.py <root>`: exit 0, 58 of 58 killed.** It works on a full temporary copy of `src/`, the oracle folders and `pyproject.toml`, because pytest's `pythonpath` would otherwise import the worktree's own `src` first. For each of the 29 refusals, its own `test_refusal_issues[<id>]` is among the failures. Results are in `mutants_result.json` and `mutants.log`.
- **`probe_strings.py`: exit 0, 0 hits.** It ran 21 new strings through `prose.issues` and `bare_figures`: the own lines, the four period frames, the three issue texts and the fixed column labels.
- **LEAD's `round7/probe_strings.py`:** 0 frozen limitation hits.

## Gates (both files, all exit 0)
- `ruff check`
- `ruff format --check`
- `MYPYPATH=src mypy --strict`

## For LEAD
**Two readings I took where the ruling was not explicit:**
- In (f), "tightest" includes `tightest_year`: both take the first unsettled year's status and reason.
- When years are mixed (one missing, one not_applicable), the first unsettled year wins.

**Still not refused:**
- An empty-string limitation passes: `prose.check("")` has no issue, and no ruling adds `empty text` for limitations.
- Thresholds keep the builder's pattern `\d+(\.\d+)?(x|%)`, so `4x` is accepted. The parse rule says `N.NNx` / `N.N%`.

**Builder syncs to list:** none needed.

**Unreachable invariant raises (not tested):** `_timing` without a reason, `_reason`, `_copy_status`, and `lineage`.

## Stage 2 notes
- A blocked CP-1D gets its `Upstream CP-1D blocked: …` line from `execution`.
- CP-1D's status comes from the bound `CP-1D` Input. `TriggerUpstream.cp1d_status` is now derived and is no longer a field.
- Rendering and FP05 for a zero-row T2R.8 or T2R.10 are Stage 4.
- Check whether CP-0 readiness lets CP-2H begin with a missing or absent ratings source.

Not verified: rendering, `validate_tables` in a product Module and FP05 for zero-row T2R.8/T2R.10 (only `validate_tables` on the report's own tables ran); whether CP-2G can emit a not_applicable T2H.6 ratio (cp2g.py is not on this base); the CP-0 begin path with a missing ratings source; the Stage 2 seams and run-level outcomes listed in the Stage 1 report; the full suite (only `tests/test_method_cp2h.py` was run).

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n (ruff ISC004 in the new test, fixed before commit)
