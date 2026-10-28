# CP-2A rounds 5 and 6 report (controller-saved from the implementer's hand-back)

CP-2A rounds 5 and 6 are committed as **7ba456e** on `worktree-agent-a34fec3e9469279cd`. The tests pass (104, plus 1 skipped), the gates are green, all eight mutants are killed, and `fixture_quarter_known` matches cell for cell.

Step 0: I merged bdad3c8, then cherry-picked 8483de4 (now 5b9ab5a) and 3674158 (now da1f563). My test asserts no oracle sha, so there was nothing to re-pin.

**Ruling → test (all written first; each failed for the old behaviour before the fix):**
- **Owner P1 / P1-W:**
  - `fixture_quarter_known` is added to every cell-for-cell oracle test: facts, tables, `cp1_references`, claims, own limitations, stress rows, break points, ranking and FP05.
  - `test_p1w_mixed_quarter_base` covers a quarter base where one CP-1 ratio is unknown and the rest are known:
    - the unknown ratio keeps A6's missing text byte for byte, and its break is Not calculable;
    - the known ones are not_applicable with the P1-W reason;
    - b02 reads "Not meaningful on a single-quarter base";
    - both own lines appear.
  - The gap case (the A2 case) is unchanged.
- **Round 6 A2:**
  - `test_round6_a2_already_reached_at_base_with_a_later_break`: s* = -0.1 is a known calculated value; b01 ranks first; the claim has its two sentences; the own line appears once.
  - `test_round6_a2_already_reached_at_base_alone`: the claim has the first sentence only.
- **Round 5 Names:**
  - `test_round5_names_line_breaks_reserved_base_label_and_duplicate_labels` covers the control-character, reserved-label and duplicate-label wordings.
  - `test_round5_pipe_in_a_name_or_label_composes`.
- **Round 5 limitation refs:** `test_round5_limitation_references_are_stored_spelled`. A stored limitation now reads, for example, "Debt of 50 US$ m …" and "1.67x …"; no claim limitation contains a brace, and the fact stays in `cp1_references`.
- **Round 5 M4:** confirmed; it is covered by the existing `test_names_and_labels_are_guarded`.
- **Process:** `test_new_strings_pass_the_prose_rules`.

**Probes (scratchpad `stage1-review-A/`, run with `run.sh`):**

| Probe | Exit | What changed |
|---|---|---|
| `probe_cp2a_p1_quarter_gate.py` | 1 (was 0) | The defect no longer reproduces. s00 total leverage is None with the P1-W reason; T2B.5 reads "Not compared" with no difference amount; there is no twelve-month line. |
| `probe_cp2a_already_reached.py` | 0 (unchanged) | A2 confirms the ranking, so the probe's own check (b01 at base, ranked first) still holds. Only its output changed: T2B.7.first now uses the A2 two-sentence form with `{T2B.7.r02.required_decline|%}`. |

**Mutants:** I ran 8, each on a full copy of the worktree (`scratchpad/cp2a-r6/mutants.py`). Every one fails the suite:
- P1-W gate off
- A2 claim in the old form
- A2 own line off
- control-character check off
- reserved base label off
- duplicate-label check off
- raw limitation stored
- P1-W own line off

The script exits 0.

**Gates:**
- ruff check: 0
- ruff format --check: 0
- `MYPYPATH=src mypy --strict` on `cp2a.py` and the test file: 0
- Not green on first run: one reformat, and one mypy error in a test helper.

**prose.issues / bare_figures:** none of these new texts gets a hit: the P1-W reason, outcome, "Not compared" text and own line; the A2 claim sentences and own line; the duplicate-label issue.
- The control-character and reserved-label issues hit only on their path prefix (`scenarios[0]` reads as a bare figure and an unresolved reference). That is true of every pinned path issue, such as v12. The message bodies are clean.
- By ruling, a spelled limitation now carries a figure (for example "50 US$ m").

**Choices I made where no position or form is pinned (for LEAD):**
1. **Own-line order.** The A2 at-base lines sit right after the not-calculable-crossing line, in register order. On a mixed quarter base, the A6 twelve-month line comes before the P1-W line.
2. **Duplicate labels.** The issue text has no index, so it is reported once per duplicated label (`validate` would collapse identical lines anyway).
3. **Reserved label.** Compared after stripping whitespace. Control characters are Unicode categories Cc, Zl and Zp; format characters (Cf, such as zero-width spaces) are not refused.
4. **Name checks.** They apply to both scenario names and threshold labels.
5. **Gap texts.** They are not covered by the limitation-refs ruling. A `{ref|unit}` in a gap field would still be stored raw in T2B.9 and in its "Gap (…)" own line.
6. **New invariant.** `_spelled` raises ValueError on a reference that is not a known figure. `validate` makes that unreachable; it is an invariant, not a ruled raise.

**Stage 2 notes:**
- L6: take the base kind from the view's `base_periods[*].kind`. Until then `period_kind` parses the label and an unknown label raises.
- `validate` raises when an offered period lacks exactly one T4.10 fact per metric (CP-1 head integrity, for the G1-X precheck or begin).
- No Stage 2 run on a quarter base is admitted until this round is reviewed.
- C5: the Stage 1 fact ids are test-only stand-ins.

Not verified: real promoted CP-1 head facts (fact ids, citations and units are test-only stand-ins; C5's label and period checks belong to the Stage 2 adapter test); FY base periods; a format character (Cf) in a name; v17; any store, journal, view, G1-X or rendering path, including the FP05 "∅ G# n.m." spelling through G2.

Ledger: 2026-10-28, cp2a-round5-6, `PYTHONPATH=src pytest -q -p no:cacheprovider tests/test_method_cp2a.py`, exit 0, 104 pass / 1 skip, agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n

## Controller rulings on the choices (2026-10-28)
- 1 (own-line order), 2 (one issue per duplicated label), 3 (Cc/Zl/Zp refused, Cf not; reserved label compared stripped), 4 (checks on names and labels), 6 (`_spelled` invariant): confirmed.
- 5 (gap texts with `{ref|unit}` stored raw in T2B.9 and the Gap own line): sent to LEAD.
