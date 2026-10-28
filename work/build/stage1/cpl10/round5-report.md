# CP-L10 rulings round 5 report (controller-saved)

- **Commit:** `6e63383` on `worktree-agent-aa6ef474a0f78ec9e`, on top of the lane tip ac10dac (a clean merge). No re-pin was needed: the test asserts no methodology or frozen_inputs sha, and the expected.json change was prose only.
- **Tests:** 75 passed in 0.36 s.
- **Gates:** ruff, ruff format and `mypy --strict` all exit 0.

## Rulings
- **(f).** Code change, test-first. A copied cell that is missing or not_applicable takes the topic's unit, currency and scale. A known copied cell stays verbatim and keeps its unit check.
  - Test: `test_unsettled_copied_cell_takes_the_topics_unit`. It was red on the old twin rule.
  - Renamed: `test_unsettled_operand_without_unit_is_accepted`.
- **(e).** It already applied both ways from round 4. The Low-confidence case was added to `test_assessment_confidence_pairing`, which passed on the old code.
- **P2.** It already held. `test_reference_to_an_analyst_cell_is_refused` covers 5 analyst cells at 2 paths, each giving `<path>: Unresolved reference: <id>`. It passed on the old code.
- **Invariants kept.** The `Upstream` ValueErrors are binding invariants (B6, (f)).

## Probes (scratchpad)
- `l10_probe_r5.py`: 0.
- `l10_mutate_r1.py`: 0, with 21/21 killed (new: `topic_unit_ignored`, `pairing_one_way`, `analyst_cells_bound`).
- `cpl10-r1/probe_oracle.py`: 0.
- `probe_fuzz.py`: 0.
- `probe_survivors.py`: 0.

## Prose and bare figures
- This round adds no new user-facing string.
- `bare_figures` hits fall only on frozen oracle literals or run-bound values: quarter labels, CP-1 limitation page numbers, fact ids, shas and the module name.

## Stage 2 notes
- L10-b, `methods/cpl10.md`: prohibited words match as substrings.

Not verified:
- real CP-1 T4.10 units, currencies and scales on missing facts;
- product column labels;
- the red step for P2 and (e) (both passed before any change).

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
