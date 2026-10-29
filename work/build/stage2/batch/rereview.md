# Stage 2 fix batch scoped re-review (mx-adversary)

**Verdict: APPROVE.** All five Mediums are closed at c197434. I edited nothing in the s2-batch worktree. Every probe ran on `git archive` copies of c197434 (`tip/`) and a1a0574 (`base/`) under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage2-rereview/` (called `<R>` below).

**Mediums**
1. **CP-DR `gaps.*.questions.*.answer`: closed.**
   - `verify_findings_owner.py`, run through `OwnerWorkflow`: the hostile submit returns `invalid` with the issue `gaps[0].questions[0].answer: Value error, Malformed run text...`. The follow-up is `valid`.
   - `<R>/rr1_hostile_owner.py` tries 8 hostile values: the 3 `MODEL_TEXT_HOSTILE`, a 5000-bracket flood, a reference over 160 characters, an empty unit, and 2 well-formed references that do not resolve. Exit 0 on tip; exit 1 on base, where 12 values raise `ValidationError`.
   - On tip nothing raises, and every follow-up attempt finishes with head `restricted`.
   - Every issue is within `MAX_ISSUE_CHARS` and none echoes the sentinel. Issue lines use `include_input=False` and `clipped`, with one module-level `TypeAdapter`.
2. **CP-3D `summary.text`: closed.** Same probes, same results.
   - The strict xfails are gone: `FINDINGS = {}`, and the gate shows no xfail.
   - In a copy of tip with base `cpdr.py` and `cp3d.py` restored, `test_stage2_classes.py` fails exactly the `[CP-DR]` and `[CP-3D]` cases (exit 1).
3. **CP-3C test strength: closed.** `<R>/B/b5_cp3c_mutants.py` on tip: exit 0, `survivors: []`. All 19 mutants are killed, including R1, R2, A4, A5 and A10–A13, so no equivalence ruling was needed.
   - `b9_cp3c_alias_untested.py` exits 0; all three cases refuse.
   - The new tests are varied fixtures: principal 62.5, EUR, FIXED, scale 1e3, a real CP-2D head fact, and a foreign `run_id`.
4. **CP-2G D3: closed.** 5. **CP-4C D3: closed.**
   - `<R>/A/p4_d3_status_only_mutants.sh` on tip: exit 0. m1 is killed by `test_the_forecast_follows_the_cp1d_facts`; m3, m7 and m8b by `test_the_copies_follow_the_cp2g_cp2a_and_cp4_heads`.
   - The fixtures are heads settled through the real `Execution` (`_finish`). The tests assert their values differ from the oracle: 40.0/2.5/1.25 against 31.8/1.57/0.94; b26 ×1.1 and d26 ×0.9; s03 decline +1; a different facility text.

**CP-1D frozen values**
- Running `p5_frozen_dump.py` and `p5_frozen_compare.py` on tip against base gives "refusals 19, cases 3, frozen basis quotes 1, raised 19; moved 0" (exit 0).
- `json_object` change: `<R>/rr3_shape_dump.py` and `rr3_shape_compare.py` cover all 43 frozen CP-1D and CP-2D payloads (refusals, cases, blocked attempts). Each parses to a byte-identical submission or issue list; moved 0, exit 0.
  - None of these frozen payloads is actually refused at shape level. All are content refusals, so the parse stage is the only code that changed and it gives identical input to the unchanged validators.

**Gate:** the 10-file pytest command exits **0** (1419 passed, 1 skipped). `ruff check` on the changed files exits 0. `# noqa` stays at 13; `type: ignore` drops from 8 to 5.

**Low (introduced by the fix; rides with the next batch)**
- The CP-DR and CP-3D RunText check runs only when no other content issue was found.
- So a payload with a content issue plus a malformed answer reports only the content issue. The repair then meets the RunText issue, and the second invalid step blocks CP-DR. Probe: `<R>/rr4_cpdr_masked_runtext.py`; the head ends `blocked`.
- CP-2E runs `run_text` unconditionally. No frozen CP-DR or CP-3D text fails RunText (41 + 3 checked), so running the check unconditionally would not move any frozen refusal.

**Info**
- Hostile JSON with duplicate keys now gives one `Extra inputs` line instead of two in CP-1D and CP-2D. This is not a frozen refusal.

**Pre-existing, for the owner (reproduced at a1a0574)**
- A CP-DR `question_id` of 155–160 characters makes `Fact` raise `ValidationError` after the binding write. The follow-up gets `stale_binding`, so the run is wedged.
- This is the same invariant as finding 1 on another path. Probe: `<R>/rr2_cpdr_long_question_id.py`, exit 1 on both tip and base.
- A well-formed reference that does not resolve passes the CP-DR and CP-3D validators. The step is journaled valid and the issue only appears at settlement. CP-2E refuses it at validation. The follow-up still settles, so the run is not wedged.

Not verified: the deferred store runs (`test_owner_*`); the full suite; mypy; CP-3D's own `_validate_step`, which still parses raw (not in scope); other model-supplied identifier paths in CP-3D besides `question_id`-style ids; the Low items of fixers 2 and 3 beyond the Mediums; and whether the D3 fixture heads match what the real CP-1D and CP-2G cores would produce (they are oracle facts with edited values).
