# CP-2A rounds 5-6 scoped review (mx-precise; controller-saved)

## CP-2A rounds 5–6 scoped review (7ba456e vs da1f563)

### Spec verdict: CHANGES REQUIRED (one Medium, test-only)
Every ruling is applied word for word, and I found no code defect. The Medium finding is a ruled check order that nothing tests: the brief's check 2 asks for a test that fails without each ruling's code, and this one has none.

### Quality verdict: APPROVE
- Missing never becomes 0. Cells P1-W gates are gaps marked `not_applicable`. A ratio CP-1 doesn't know stays `missing` with A6's text.
- There are no stubs or fake values.
- There is no catch-all. The only new raise is `_spelled`'s `ValueError`, and validated input can't reach it (shown below).

### Ruling-by-ruling check (code at 7ba456e)
- **Names:**
  - The control-character wording is in `cp2a.py:561` and `:603-604` (Cc, Zl and Zp).
  - The reserved base label is in `:562-563` and `:616-617`.
  - The duplicate-label issue is at `:639-644`. It is emitted once per label. `validate` deduplicates at `:673`, so the output is the same as "per occurrence".
  - `|` composes (`test_round5_pipe_in_a_name_or_label_composes`). M4 is unchanged.
- **Limitation refs:** `_spelled` is at `:1238-1252` and uses `business_context.spelled` ("50 US$ m", "1.67x"). It is applied to the scenario and assessment limitations (`:1289`, `:1306`). The fact stays in `cp1_references` because `:1203-1206` still reads the raw limitation text.
- **A2:**
  - The claim is at `:1255-1274`. The first sentence is used alone, and the second is appended only when a break has `REACHED` (0 < s* <= 1), using that break's own rNN.
  - The own line is at `:1326-1331`, one per at-base break.
  - s* stays a known calculated figure (`-0.1`, shown as `(10.0)%`).
  - The ranking is unchanged (ascending).
- **P1-W:**
  - The four strings match byte for byte (`:120-129`).
  - The gate order is: missing operands, then the A6 gate, then P1-W, then the short-circuits or zero check. This is in `stress` (`:316-323`) and `_break` (`:437-446`).
  - T2B.5 `recomputed`/`difference` are `not_applicable` with "Not compared" (`:1055-1063`).
  - The T2B.6 and T2B.8 cells are `not_applicable`, and the outcome/result read "Not meaningful on a single-quarter base" (`:1108`, `:551`, `:1149-1151`).
  - The own line is emitted once and sits beside the A6 line (`:1350-1354`).
  - A CP-1 ratio that is not known keeps A6's text byte for byte (`test_p1w_mixed_quarter_base`).
- **fixture_quarter_known:** `git diff --stat da1f563 7ba456e` touches only the two files under review, so `cases/` is unedited. The case was added to `COMPOSED` (`tests/test_method_cp2a.py:44`), so all 11 parametrised cell-for-cell oracle tests and the loop at `:893` read it straight from `EXPECTED`/`SUBMISSIONS`.

### Findings

**Medium M1: P1-W item 2 (A8 order) has no test.**
- Where: `src/deploy_workflow/owners/cp2a.py:443-446` (`_break`) and `:319-325` (`stress`).
- Failure scenario: move the P1-W gate after the short-circuit or the zero-denominator check and the whole suite still passes.
- What would go wrong:
  - On a quarter base with negative interest, b02 would read `Not calculable`/`INTEREST_NOT_POSITIVE` instead of the P1-W outcome.
  - In a 100% EBITDA-decline scenario, T2B.4 leverage would turn `missing` with `NOT_POSITIVE_EBITDA` instead of `not_applicable` with the P1-W reason.
- The current code is correct. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2a-r6-review/probe_p1w_order.py` exits 0.
- Surviving mutants: `break_gate_after_short_circuit` and `stress_gate_after_zero` in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2a-r6-review/mutants.py`, which exits 1.
- Fix: add one unit test on a quarter `BaseOperands` that covers both paths (the probe's cases).

**Low L1: the P1-W line's condition is half tested.**
- Where: `cp2a.py:1351-1353`.
- Failure scenario: keep only the break clause and the suite still passes. Without the row clause, a quarter base with interest missing and no leverage watch level would show P1-W cells in T2B.4 but no own line.
- Mutant: `quarter_line_points_only` survives (same `mutants.py`). The `quarter_line_rows_only` mutant also survives, but I believe it is equivalent: a P1-W break implies a P1-W row.

**Low L2: the confirmed Names choices are untested.**
- Where: `cp2a.py:603` (Zl/Zp) and `:616` (`.strip()` before the reserved-label compare).
- Failure scenario: neither U+2028 nor a padded " Base (no stress) " is in a test. The `control_cc_only` and `reserved_unstripped` mutants survive (same `mutants.py`).
- The behaviour itself is correct: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2a-r6-review/probe_names_edges.py` exits 0.

**Low L3: blank duplicate labels add a noise issue.**
- Where: `cp2a.py:640-644`.
- Failure scenario: two blank labels produce `thresholds:   appears more than once` next to the two `empty text` issues. The scenario duplicate check guards with `sc.name.strip()` (`:618`); the label check has no such guard. Seen in `probe_names_edges.py` (exit 0).

**Info I1: the `_spelled` invariant can't be reached from validated input.**
- I tried five limitation shapes: an unknown figure ref, a chip naming a known fact, a chip naming an unknown id, a ref to a not-known fact, and a ref with no unit.
- `validate` refuses the first four, and `compute` re-raises the `validate` message before `_spelled` runs. A ref with no unit is valid and spells as "30 US$ m".
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2a-r6-review/probe_spelled_unreachable.py`, exit 0.

### Implementer probes and mutants
- **`stage1-review-A/probe_cp2a_p1_quarter_gate.py`: exit 1, as expected.** It prints "P1 reproduces: False" because:
  - s00 total leverage is None with the P1-W reason;
  - T2B.5 reads "Not compared" with no difference amount;
  - the A6 gate line is gone (`gates: {}`).
- **`stage1-review-A/probe_cp2a_already_reached.py`: exit 0.** b01 is at base with s* -0.1, ranked first, and the claim uses the two-sentence A2 form with `{T2B.7.r02.required_decline|%}`.
- **`cp2a-r6/mutants.py`: exit 0.** All 8 mutants are killed.
- **My mutants (`cp2a-r6-review/mutants.py`, full copies in `cp2a-r6-review/copies/`): exit 1.** 13 mutants: 7 killed, 6 survived.
  - Survivors: `break_gate_after_short_circuit` and `stress_gate_after_zero` (M1), `quarter_line_points_only` (L1), `quarter_line_rows_only` (likely equivalent), `control_cc_only` and `reserved_unstripped` (L2).
  - Killed: T2B.5 difference text, status always missing, crossing outcome, T2B.6 quarter cells as missing, A2 second-sentence index, A2 own line on all ranked breaks, `_spelled` dropping the unit.

### Gates (target root)
- pytest `tests/test_method_cp2a.py`: exit 0, 104 passed, 1 skipped
- `ruff check` on both files: exit 0
- `ruff format --check` on both files: exit 0
- `MYPYPATH=src mypy --strict` on both files: exit 0

### Points for LEAD
- Choice 5 is still open: a `{ref|unit}` in a gap field is stored raw in T2B.9 and in its Gap own line. The limitation-refs ruling doesn't cover it.
- "Reported per occurrence" (duplicate labels) and one-per-label give the same output only because `validate` deduplicates (`:673`). If that ever changes, the ruling's wording decides.
- The `∅ G# n.m.` chip spelling (P1-W item 6) is a rendering matter left to Stage 2; this commit doesn't exercise it.

Not verified: rendering and G2 paths (the `∅ G# n.m.` chip, how a spelled limitation shows in the report); real promoted CP-1 head facts (the fact ids are test stand-ins); FY base periods; a Cf character in a name; the builder-side Q4 25 source assertion in da1f563 (out of scope); any suite other than `tests/test_method_cp2a.py`.
