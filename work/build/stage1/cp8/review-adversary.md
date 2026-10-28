# CP-8 Stage 1 first adversary review (mx-adversary; controller-saved)

# CP-8 Stage 1: first adversary review (tip a5c4011)

**Verdict: CHANGES REQUIRED.** One Medium finding (M1) blocks. It is a defect in the new code, and fixing it needs no new wording. Everything else is Low or Info, or is a gap that already exists in the frozen lease or oracle and goes to LEAD.

**Target.** Worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a`, files `src/deploy_workflow/owners/cp8.py` and `tests/test_method_cp8.py`. History is 1cf8b93, then 63237ad, then a5c4011, and those three commits touch only these two files. `git diff 86e760e a5c4011` names only the two files, so `src/deploy_vii` is not edited. The worktree is clean; I edited nothing.

**Gates (run by me, all exit 0):**
- pytest: 129 passed in 0.78 s. The `PYTHONPATH=src` form was accepted.
- `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-adversary/`. Each one imports `_common.py` from that folder.

## Blocking

**M1 (Medium): a soft hyphen inside a quoted figure makes Python store a figure the page does not state.**
- **Where:** `cp8.py:493-508` (`_cite` delegates to `readiness.citation_issues`), with `:382-399` (`_token_once`, `_labelled`) and `:645-665`.
- **Cause:** `citation_issues` matches quotes through `quotes.normalise`, which deletes U+00AD (`quotes.py:64-69`). The value checks then run on the raw quote, where the soft hyphen is still present.
- **Scenario:** the realized bid quote reads `bid 9­8.00` and `value_text` is `8.00`. The validator returns `()`. T7.3 then shows bid 0.08 where the frozen market_update page states 98.00. The mid becomes 53.375%, the move 4550 bp, and the rails line reads "...is now 53.375%, lower by 4550 bp."
- **Code only:** the builder's own check (`build.py:76`, `:351`, whitespace only) would refuse this quote. The probe prints `builder ref_ok would accept the quote: False`.
- **Fix, no new wording:** run `_token_once`, `_labelled` and the `as_of_text`/`text in quote` checks on `quotes.normalise(quote)`. The existing `value_text 8.00 does not occur in the quote` issue then fires. Write the failing test first.
- **Probe:** `p01_soft_hyphen_figure.py`, exit 1 (reproduces).

## Checked and holding

**Calculation (against the Method text):**
- variance = realized - expected; direction; unsigned magnitude.
- mid = (bid + offer) / 2 / 100; magnitude in bp.
- The window uses the latest realized as-of; the default statement's date and the run date are not used (oracle: 109 days).
- Breach is strictly beyond the level.
- Gate: recorded 1, required 3, never met.
- Hit rate, distribution and direction counts are `None`, never 0, when nothing is compared.
- `derive` runs under the EXACT context.
- 8-7: a split quotation is not compared in both the validator and `derive`, and the window still takes the latest date.

**Rulings 8-1 to 8-24 and corrections (a), (b), (f):** applied. Every static ruled string is byte-exact against the ruling document and reached in composed output (`p12_ruled_strings.py`, exit 0). 8-9 keeps the pinned unknown-authority text.

**The one remaining `_unpinned` raise (`:1829`):** fails closed in both directions, and validates first in both:
- expected side split, realized side missing (tested);
- realized side split, expected side missing (untested).

Under `outcome_absence`, an expected split composes the 6c (b) row. Probe: `p04_split_plus_missing.py`, exit 0.

**Invariants:**
- 8-8 is reachable only with a pack holding prior_case twice, which `preparation.py:44` refuses.
- 8-12 (the composer's prior_case authority) is reachable only with an Upstream missing CP-0's T3 row.
- Both raise "invariant:" and nothing composes (`p05_invariants.py`, exit 0).
- A fuzz of 21,000 mutated literals found no validator crash, no crash after validation, no `validate_tables` or prose failure, and no unsettled fact carrying a value (`p06_fuzz.py`: 6000 seed 7 and 15000 seed 13, exit 0).

**Validator:**
- Field order and the pack, scope, source-rule, locator/quote order for decision, thesis, size and expected quotes match the brief.
- r42 is not de-duplicated (mutant killed).
- 8-10, 8-11 and 8-14 counting is correct.

**Standing rules:** no stub and no catch-all (the only `except` is the narrow `date()` one at `:367`). No store, host, session or render call; `report_view.fact_spelling` has precedent in five other owners. No clash with the seam names in protocol §2.

## Low and Info (they ride with the M1 fix)

**L1 (Low, test strength): 12 + 2 survivors** (`p07_mutate.py` and `p07b_mutate.py`, both exit 1, control killed):
- **Two of the Stage 1 survivors are not justified.** The report says no frozen page reaches them, but both are reachable:
  - "First figure" relaxed: two frozen spans reach it (realized bid valued 98.75; the February/March leverage span), shown by `p09_first_figure_reachable.py`, exit 0.
  - The CP-6-present T7.8 `current_decision` row (`:1886`): `test_decision_line_reads_the_cp6_call` composes that exact state but does not assert T7.8.
- **Still surviving, edited-pack tests would kill them:** "value occurs once" relaxed, and the equal-day boundary of the realized after-decision check. (The `edited_pack` helper is already used for 8-3 and 6c (f).)
- **The prohibited-word-boundary survivor is now killed.** Citation de-duplication (`:1196-1208`) still survives; it is harmless, because the oracle compares cites by page.
- **New survivors:**
  - the EXACT context dropped (derive and compose);
  - the `N.NN` format (8-15);
  - the equal-day boundary of the default statement;
  - blank `flag_quote`;
  - `isnumeric` replaced by `isdigit`;
  - bid exceeds offer (oracle-reserved r38, justified);
  - the two `source_authority` guards (Stage 2).

**I1 (Info):** `registry.modules()` (`:459`) reads the packaged `methodology.json` once (cached). It is the sanctioned source of methodology ids, not a store call.

## Pre-existing or unruled: to LEAD, not counted in the verdict

1. **Empty or blank decision text validates** (`:555`). The rule "text occurs in its quote" holds trivially for `""` and `" "`, as it does in `build.py:427`. Instrument `""` gives a known blank T7.1 cell. Posture `" "` with a quote removes the 8-6 limitation and the T7.8 posture row. Needs a refusal wording. Probe: `p02_empty_decision_text.py`, exit 1.
2. **`as_of_text` is not bound to its figure** (r37, `:648`, matching the builder). Realized leverage can take April 30 from a longer verbatim span: T7.3 then reads "Twelve months to 2026-04-30" and the window becomes 110 days. A same-day quotation can be split under 8-7 by picking the publication date, which the 8-7 tests themselves rely on. Probe: `p03_as_of_not_bound_to_figure.py`, exit 1.
3. **Under 8-9, a default statement can cite prior_case.** Once CP-0 classifies prior_case as issuer, nothing like r36 refuses it, so a Prior Case page becomes the realized T7.3 default row. Needs an edited pack. Probe: `p10_prior_case_default_statement.py`, exit 1.
4. **The source rule runs after locator and quote** for realized observations and the default statement (`:667-683`, `:708-721`), contrary to lease :60 but matching `build.py:498-505` and `546-549`. With two defects, the locator/quote issue is the one reported. No pinned literal tells the two orders apart. Probe: `p11_source_rule_order.py`, exit 1.
5. **An exit-trigger absence's `follow_up` is validated but never composed;** 8-17 adds no T7.8 row. Probe: `p08_exit_absence_follow_up.py`, exit 1.

Not verified: whether the M1 fix changes any frozen output (none is expected, because no frozen quote holds U+00AD, but the full suite must be re-run after the fix); the Stage 2/4 sections (RULES, seams, tamper, render, consumption), which are outside Stage 1; prose and bare-figure runs of new strings (I did not run the implementer's `probe_prose.py`); whether cp8.py is classed as sensitive code under §3's Test strength row; the 8-12 and 8-8 reachability argument at run level (it rests on `preparation.py:44` and the 8-12 ruling text, not on an executed G1-X run).
