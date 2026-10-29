# CP-2H fix 1 part b report

B2, B3, B5 and B6 are fixed and committed as **f843772**, on top of 87f2d9d. The test file passes: 185 passed and 1 strict xfail. All four gates exit 0. The 29 refusals are all still killed (27 from the original spec plus s01 and s02 retargeted, because B2 rewrote their sites).

**Decision needed: B5 conflicts with the frozen oracle in one cell.** The oracle's composer-only fixture `cases.fixture_total_loss` pins `T2R.1.u_cp2g.status` as `composer_only`, which is CP-2G's head status. Under B5 that cell is the bound CP-2G Input's status, and `InputStatus` can only be `accepted`, `restricted` or `blocked`.
- I followed the round 5 rule: a strict xfail, `test_frozen_composer_only_cp2g_status`, plus the live ruled behaviour.
- `test_facts[fixture_total_loss]` now expects the bound status, `restricted`, for that one cell only.
- For LEAD: either re-pin the fixture's cell, or rule that composer-only fixtures keep the CP-2G head status.

## Step 0: merge
`git merge claude/module-dev-status-review-0981b6` was clean (a plain merge, with no `docs/CP4C-OWNER-LEASE.md` conflict). `HEAD^2` of that merge is b6c33926a11d59a178b05020e9d4a20d85035bf0, which equals the lane tip. The merge brought no changes to the oracle or CP-2H files.

## Rulings and the tests that cover them
I wrote the tests first.
- These failed red for the reported cause:
  - B2's mid-block breaches, which did not raise `SourceIssue`;
  - B3, which returned no issues;
  - B5, where the status read `restricted` instead of `accepted`;
  - the unbound-upstream case.
- These passed on the old code, and their job is to kill the mutants:
  - the B2 cases where an empty block already refused;
  - the B6 stale tests.

**B2 (block rule, round 11).**
- **Change:**
  - `_block` returns `_Rows(rows, breached)`. A line of zero or one field ends the block. A line of two or more fields that is not the block's width breaches it.
  - The breach raises that block's text at the block's rows step: scale, then register, then terms. A block with no rows and no breach still reads as no header.
- **Tests:**
  - `test_block_row_breach_refuses[...]`, 9 cases: terms with 4 fields, 6 fields, a split metric and a breach on the first line; a register row with 4 fields; a scale row with 2 fields; three order cases.
  - `test_one_field_line_ends_a_block`: a blank line ends the scale, and gap page:1's withdrawal note still ends the register.

**B3 (blank limitation).**
- **Change:** in `_limitation`, before `prose.check`, a non-null blank limitation gets `<path>: empty text`. Null is still allowed.
- **Test:** `test_blank_limitation_is_refused`.

**B5 (T2R.1 statuses).**
- **Change:**
  - `u_cp1` and `u_cp2g` take `up.required_status("CP-1")` and `up.required_status("CP-2G")` from the bound Inputs. A required upstream that is not bound raises `ValueError`.
  - I removed the now-unused fields `TriggerUpstream.cp1_status` and `Cp2gMetrics.status`, so `Cp2gMetrics.select(facts)` no longer takes a status. This means there is now one source for each status.
- **Tests:**
  - `test_upstream_statuses_are_the_bound_inputs` (kills G4);
  - `test_upstream_status_needs_a_bound_input`;
  - the strict xfail above.

**B6 (stale issues).**
- **Change:** none.
- **Test:** `test_stale_issue_order_and_wording` (kills G2, G3 and C49). It covers:
  - four stale inputs in bound order, with the one that is only current last;
  - `current absent` and `bound absent`;
  - the `str` current path, both from `stale_issues` and through `validate`.

**B4 and round 11 Q7:** no change, as the controller confirmed.

## Mutation runners
All ran on a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`; the canary failed every run, as it should.

| Spec | Result | Exit |
|---|---|---|
| `spec_refusals.py` | 27/29 | 1 |
| `spec_fix1b_retarget.py` (s01′, s02′, C41′) | 3/3 | 0 |
| `spec_other.py` | 44/50 | 1 |
| `spec_more.py` | 3/4 | 1 |
| `spec_fix1_retarget.py` | 5/5 | 0 |
| `spec_fix1b.py` (each ruling's revert plus G4′) | 7/7 | 0 |

**Mutants not killed, and why:**
- **`spec_refusals.py`: s01 and s02.** B2 rewrote their sites in `parse_ratings`. With the retargeted versions in `spec_fix1b_retarget.py`, all 29 refusals stay killed.
- **`spec_other.py`: C20, C21, C45, C50 and C41.** Their sites are gone, rewritten by F1/F3 and by B2. C20, C45 and C50 are retargeted and killed in `spec_fix1_retarget.py`, and C41 in `spec_fix1b_retarget.py` (as C41′). C21 has no retarget; it was already rated equivalent.
- **`spec_other.py`: C44** is equivalent, as the review says.
- **`spec_more.py`: G4.** Its site (`up.cp1_status`) is gone; it is retargeted as G4′ and killed in `spec_fix1b.py`.
- **`spec_fix1b.py`** kills each ruling's revert. It contains:
  - B2: the breach reverted to `break`, a one-field line made a breach, and the breach raised at the header step;
  - B3: the blank check removed;
  - B5: both T2R.1 statuses made frozen literals, and the unbound raise removed.
- **`spec_block_safety.py`** was not rerun. It was the reviewer's proposal for B2, and its site no longer exists.

## Reviewer probes
- **p05: exit 0.** All three truncation variants now refuse with `Trigger terms not found`.
- **p01, p03, p06, p12: exit 0.**
- **p02: exit 1.** This is expected and unchanged from fix 1: its 30-place percent form is refused by the F1 grammar.
- **p09: exit 1.** B5 removed the `cp1_status` argument p09 uses, so it now fails with an `AttributeError`. The same checks are covered by `test_unsettled_reasons_take_the_first_year` and `test_root_reason_puts_the_threshold_first`.

## Gates
All four exit 0. First pass was **n**: ruff ISC004 on the new stale test, and `test_facts[fixture_total_loss]` needed the B5 exception for the frozen cell.
- pytest on the test file (185 passed, 1 xfailed);
- `ruff check` on both files;
- `ruff format --check` on both files;
- `MYPYPATH=src mypy --strict` on both files.

## Stage 2 notes (methods/cp2h.md)
- `TriggerUpstream` has no status fields now. Every T2R.1 status, including CP-1D's, comes from `bound`. Stage 2 binds the CP-1 and CP-2G heads as Inputs, and `Cp2gMetrics.select` takes only the facts.
- The composer-only fixture conflict needs a ruling or a re-pin (see the top of this report).
- Builder sync B1 is still open: the threshold grammar, the exact shift and the B2 block text in the manifest `parse_rule`.

## Files
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a52b5ec0919986ddb/src/deploy_workflow/owners/cp2h.py`
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a52b5ec0919986ddb/tests/test_method_cp2h.py`
- Specs and logs: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-r6h-8/` (`spec_fix1b.py`, `spec_fix1b_retarget.py`, `fix1_*.log`, `fix1_*.json`).

Not verified: how the composer-only fixture's T2R.1 status should read (frozen `composer_only` against B5, open for LEAD); the oracle and builder were not updated for B1/B2 (builder sync for LEAD); Stage 2 binding of real CP-1 and CP-2G heads as Inputs; the full suite (only this test file was run).

agent=general-purpose(opus) fix-rounds=1 gates-first-pass=n
