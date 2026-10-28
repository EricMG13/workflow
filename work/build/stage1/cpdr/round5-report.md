# CP-DR follow-up (round 5 R4, R5 and round 6b C4) — controller-saved

- **Commit:** `5b25007` on `claude/cpdr-stage1` (worktree `cpdr-stage1`), on top of the merges of lane tips 95582c5 and a35ec2c.
- **Tests:** 59 passed, including `test_oracle_files_are_the_pinned_revision`.
- **Gates:** ruff check, ruff format --check and `mypy --strict` exit 0. mypy failed once on a name clash, so the gates did not pass on the first run.

## Rulings and their tests
- **R4.** Tests:
  - `test_r4_a_later_affects_that_names_no_module_is_not_a_split` (red first);
  - `test_r4_an_earlier_affects_that_names_no_module_is_not_a_split` (passed on the old code);
  - `test_r4_two_candidate_splits_parse_as_not_stated`;
  - `test_r4_two_candidate_splits_settle_with_missing_cells_and_the_own_line`;
  - `test_r4_text_outside_the_readiness_form_fails_closed` (three cases).
- **R5.** Tests: `test_r5_row_labels` and `test_r5_row_label_with_underscores_and_capitals`. The second kills two mutants that survived the first.
- **C4.** Test: `test_c4_rows_follow_the_agenda_order`. TDR.1 follows agenda order, and TDR.2 is grouped by gap in agenda order.

## Choices not ruled, left as fail-closed or compose-as-now (FYI to LEAD)
- A gap that names no consumer (`affects ; `): `compose` raises `CP-0 gap <id> names no consumer; no wording is pinned for its consumers cell`. Test: `test_a_gap_naming_no_consumer_does_not_compose`.
- No candidate split, or a kind or severity outside the vocabulary: an invariant raise.
- The R4 own line comes after the base line, in agenda order. This position is not pinned.
- The ambiguous cells carry no value_class, because they hold copied CP-0 text.
- C4 covers only TDR.1 and TDR.2. The answered-question claims, the "Unresolved:" lines, the consumption facts and the per-gap bookkeeping keep submission order.

## Probes (scratchpad)
- `stage1-review-C/probe_cpdr_gap_row_order.py`: exits 1, as expected. It exits 0 only while the order differs from the agenda.
- `cpdr/mutate_r5.py`: 0; 14 of 14 mutants killed.
- `cpdr/mutate_r2_order.py`: 0; 6 of 6 killed.
- `cpdr/mutate_r1_audit.py`: 0. The equivalent mutant `empty_line_from_submission` stands.
- `cpdr/mutate_r1.py` and `cpdr/mutate.py`: 1, on stale anchors, because R4 and the fix-1 rename replaced that code.
- `cpdr/probe1.py`: 0.
- `cpdr/prose_r5.py`: 0.
- `cpdr/lease_call.py`: 1. Pre-existing: `pack` is `tuple[Source, ...]`, not `PreparedPack`.

## Prose
The ruled strings give no hits. The implementer reworded its own no-consumer text to remove a `Bare figure: TDR.1` hit.

## Stage 2
- R4's preferred structured `ReadinessGap` reader.
- The `read_inputs` view must handle an ambiguous gap.
- Record the R4 amendment at lease :48.

Not verified:
- Stages 2–4;
- the structured reader;
- no oracle case exercises the ambiguous gap, the no-consumer gap or the two-gap order.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
