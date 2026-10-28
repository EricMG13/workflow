**Verdict: APPROVE.** I found no High, Medium or Low findings in commit 0de521a (`git diff 7f71516 0de521a`, files `src/deploy_workflow/owners/cp8.py` and `tests/test_method_cp8.py`).

**Spec**
- **Item 7** (`_labelled`, cp8.py:467-478). This matches the ruling as drafted.
  - The search scans `_NUMERAL_RUN` from just after the label. It stops at the first run that starts at or after the `_MULTIPLE`/`_DECIMAL` match. Before that point, any run that does not fullmatch `[0-9]+(?:\.[0-9]+)?` returns False, which gives the pinned not-labelled issue.
  - The join is on `,<digit>` only, so `, ?` is not joined.
  - Plain integer runs are skipped, and `bid on April 29, 2026 was 0.50.` still labels.
- **Item 8** (`_whole`, cp8.py:406-414).
  - It adds `(?<![0-9],)(?<![0-9], )`, and the trailing guard is now `(?![0-9]|[.,][0-9]|, [0-9])`. These are exactly the ruled `<digit>,` / `<digit>, ` joins on both sides.
  - `_on_page` and `_token_once` share this one pattern, so the page test gets the same joins and needs no other change.
- **Rule W, B10 and the B3 exemption (f99db43) are unchanged.** `_SIGN`, `_W_MINUS`, `_wrap_split` and the sign and parenthesis guards in `_whole` are not in the diff.
- There is no stub, fake value or catch-all in either file.

**Quality.** The new code has no defects I could find. My probes below checked it against independent models and against the frozen data.

**Probes** (all run in a full archive copy of 0de521a with `PYTHONDONTWRITEBYTECODE=1`, saved under `<S>/cp8-r13-review/`):
- **`probe_review.py`: exit 0, 0 disagreements.** It checks four things:
  - **Frozen labelled checks:** all 563 give the same result under the old `_labelled` (7f71516) as under the new one; 0 moved.
  - **15 pinned edge cases.** Refused, as ruled:
    - signed and parenthesised malformed runs: `bid -.75, or 0.50.`, `bid (.75) or 0.50.`, `bid - .75 or 0.50.`;
    - `bid 1.2.5 or 0.50.` and `bid 1,250 then 0.50.`;
    - multiple labels with the malformed run first: `bid .75 and bid 0.50`;
    - a malformed run before a multiple: `total leverage .5x then 4.50x`.

    Accepted, as ruled:
    - `bid 1, 250 then 0.50.` (the narrow join);
    - a malformed run after the value: `bid 0.50, then .75.`;
    - `bid 0.50 and bid .75`;
    - a plain decimal before a multiple: `total leverage 4.25 vs 4.50x`.

    `bid 1, 250 then 0.50.` labels, but `_whole` then refuses 0.50 because of the `5, ` before it, so it is refused end to end.
  - **200k random `_labelled` inputs** against a hand-written run-scan model of the ruling: no difference.
  - **200k random `_whole` inputs** against a string-slicing model of the ruled guards, and **60k random `_on_page` page/quote pairs** (comma, comma-newline and hyphen wraps) against the model applied to the plain and joined readings: no difference. The edge cases also pass: `250 per year.` on `1,\n250 per year.` is refused, and `1.25 a` on `2025, 1.25 a` is refused.
- **`p13_cp8_labelled_e2e.py`** (LANE re-pointed to the copy): exit 0. `bid .75, or 0.50 a week ago.` is refused end to end with `observations[6]: loan_bid value_text 0.50 is not labelled loan_bid in the quote`.
- **`p13_refusal_mutations.py`** (copied with `p13_quote_classes.py`, LANE re-pointed): exit 0, sanity ok. Of 134 mutations (CP-8 68), the only change is CP-3D `amortisation_nonzero`, which addendum 2 already rules. No CP-8 frozen refusal mutation moves.
- **`mutants.py`** (SRC re-pointed to the copy): exit 0, and all 8 mutants were killed.
- **Added check, the CP-3D comma-edge class** (`p_comma_edge_cp8.py`): exit 0, so CP-8 does not have this defect.
  - All 12 cases are refused. These are the 6 CP-3D cases (`fee of 1,` on `1,250`, `1, 250` and `1,\n250`; `,250 per year`; `, 250 per year`; `margin of 25,` on `25,5`) plus 6 in the N.NN shape (`bid 1.25,` on `1.25,5`, `1.25, 5` and `1.25,\n5`; `,1.25 today`; `, 1.25 today`; `1.25 today` on `5,\n1.25`).
  - Both controls are still accepted: `bid 1.25,` on `1.25, today.` and `, 1.25 today` on `up, 1.25 today.`.
  - CP-8 avoids the defect because `_on_page` (cp8.py:422-444) re-runs the whole `_whole` pattern at the figure's position in the page reading. The comma guards therefore see the page's characters beyond the quote edge, and there is no separate edge test that could miss them. The refusal comes from `_on_page`: for example, `_token_once("1", "fee of 1,")` returns True.

**Gates** (once, in the copy):
- pytest on `tests/test_method_cp8.py`, `tests/test_defect_classes_selfcheck.py` and `tests/test_host_h1.py`: 880 passed, 0 failed. The exit code I captured was the pipe's (`tail`), so the pass rests on the printed summary.
- `ruff check`: 0.
- `ruff format --check`: 0.
- `MYPYPATH=src mypy --strict` on both files: 0.

Not verified: real-world quotes outside the frozen cases and the fuzz alphabets; the readers in CP-1D, CP-2E and CP-3D; the `methods/cp8.md` guard-limit notes (not in this diff); `p13_quote_classes.py` and `p13_comma_space_join.py`, which I did not run end to end against this commit, relying instead on my own frozen-labelled and fuzz probes; and pytest's own exit code, which I did not capture (see Gates).