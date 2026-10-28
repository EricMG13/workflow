# CP-2E fix round 1 re-review (mx-adversary)

## CP-2E fix round 1 re-review (0fa5b4a..2b58c89)

**Verdict: APPROVE.** H1, M1 and M2 are fixed, and the round 5 items 2 and 3 are in. No High or Medium finding is left; five Info notes follow. The worktree is still clean at 2b58c89. I re-ran the gates: the fast set gives 983 passed, and `tests/test_owner_cp2e.py` gives 50 passed and 1 skipped (the gap-case tamper, whose recipe is stated on the positive case only).

**H1: fixed, and the run is not wedged.**
- `_Check.run_text` checks the summary with `TypeAdapter(RunText)`, built once, inside `_check_text` within `validate_macro_fx`. That runs before `macro_fx` builds anything. Errors use `include_input=False` and are bounded by `clipped`.
- The summary is the only model string that becomes `Claim` text. Every other claim is fixed text plus fact ids; only `CP-2E-VIEW-01` takes `i.summary`.
- The "carries a reference" rule holds: `[abc]`, `{abc|x}` and `[a]` are refused with `summary.text: text carries a reference`.
- The fixer's `invalid` follow-up has a real cause. The refused summary is journaled invalid, and attempt 1 starts on a new binding. That binding needs fresh `read_pages` calls and a search, so the bare literal is refused by RULES: `Absence claim without a recorded search` plus pages 1 to 5 unread.
- With fresh reads and a search, the literal comes back `valid`. CP-2E settles `restricted` at attempt 1 and the receipt verifies (`p3b_after_refusal_settles.py`).

**M1: fixed.**
- Each `Cite` pair now carries the quote of the field it was read from. All 11 T2F.1 sourced facts quote their own field (p2).
- Derived facts quote the first of their own input quotes on each page, for example `fcf_after` quotes the free cash flow row on page:3 (`p10_derived_quotes.py`).
- The page-level cites and all frozen values are unchanged (the gates pass).
- The "first quote on the page", "last quote on the page" and keep-last `_dedupe` mutants are all killed (`p11_quote_mutants.py`).

**M2: fixed.** The new store tests assert the right things:
- **Tamper:** with `_PROBES["CP-2E"]` replaced by a no-op, the verifier accepts the forged copy; with the real probe it refuses `identity_mismatch`. So `cp2e.probe` is the only check that catches it.
- **Stale:** an interrupt between the reads and the submit gives `stale_binding`.
- **Blocked:** attempts 0 and 1 each give their pinned first issue, `repair_of` is set, the head is `blocked` (as ruled in round 5 item 8), and the receipt verifies.
- **Begin refused:** a blocked CP-0 gives a CP-2E refusal with no begin.
- **The 27 refusals:** each one's full `all_issues` list is asserted.
- **The hand-built page:** run on its pinned page and pack hashes, giving the exact issue.
- **Acceptance 1:** the fast test compares every fact field (p9: all 7 mutants killed). The store test compares the layouts, claim ids, settled own limitations (with the synthetic line) and inherited limitations. The settled head is tied to the validator output by the probe that the receipt verifier runs.

**Lows**
- **L2:** fixed. `normalise(name)` is stored (p7).
- **L3:** fixed. The earlier survivors are now killed. `parse_raw_json` behaves identically on 7 edge texts (duplicate keys either way, floats, 1e400, escapes, NUL) (`p12_parse_equivalence.py`). I accept it as an equivalent mutant.
- **L4:** fixed. The `shipped.py` record has prior hash `4ef3f9…` and current hash `01ebc258…`, and the current hash matches the file.
- **L5:** fixed. The row headers and columns are now in `methods/cp2e.md`.

**Round 5 items**
- **Item 2:** `spread 25.5` beside a whole `25` is refused with `is not labelled spread`, and `p_label_decimal.py` now exits 1, so the gap is closed. Plain `spread 25` still passes.
- **Item 3:** all four absence objects name the submission path, for example `fx.debt_currency_absence.reason` (`p13_round5_items.py`).

**Info (nothing reopens)**
- The module docstring of `tests/test_owner_cp2e.py` (lines 5-6) still says the tamper, stale_binding, blocked and begin-refused cases are not written.
- An empty summary `""` gets two issues: `empty text` and `String should have at least 1 character`. No frozen refusal changes.
- `copy.deepcopy` and `dataclasses.asdict` of a `Cite` raise `TypeError`. No `src` path does either today (`p14_cite_copy_and_empty_summary.py`, exit 1).
- The round 3 item 2 class test is not yet in `tests/defect_classes.py`. That is a Modules-wide task, not this one.

**Probe exit codes**

| Probe | Exit | Meaning |
|---|---|---|
| p1 | 0 | the summary is journaled, no raise |
| p2 | 0 | all 11 sourced quotes are their own field |
| p3 | 0 | bracket summary journaled; bare follow-up `invalid` |
| p3b | 0 | settles after fresh reads |
| p4 | 1 | only `parse_raw_json` survives (equivalent); the two `_quotes` mutants no longer apply |
| p7 | 0 | normalised name stored |
| p9 | 0 | all 7 fact-field mutants killed |
| p10 | 0 | derived quotes come from own inputs |
| p11 | 0 | first/last-quote mutants killed |
| p12 | 0 | parse paths identical |
| p13 | 0 | round 5 items 2 and 3 hold |
| p14 | 1 | Info: `Cite` copy fragility |

All probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-s2-review/`. The mutants ran on a `git archive 2b58c89` copy in `copy/` there.

Not verified: `tests/test_owner_workflow.py` and `tests/test_owner_s1a.py`; any render or browser run; whether the oracle's derived-fact quote choice is what Modules intended beyond the round 3 rule text; the 800-line PR cap.
