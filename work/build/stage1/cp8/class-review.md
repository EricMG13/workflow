## CP-8 Stage 1 class round (round 11) review: commit d648582, diff 864ffe3..d648582

**Verdict: APPROVE.** There are no High or Medium findings. Two Low test gaps and three Info notes can ride with the next fix or the end-of-lane batch.

Spec verdict: **pass**. B1, B3, blank text and the round 10 Lows are all applied as ruled. No frozen case changed. `cases/`, `src/deploy_vii` and `tests/defect_classes.py` are not in the diff. The only test changes are additions; the existing parametrize lists only gained rows.

Quality verdict: **pass**, with Low-1 and Low-2 below. There is no stub, no fake value and no catch-all in the diff.

### Checks by ruling id

**1. B1 (edge cut): correct.**
- **Implicit edge gate.** I tried to refute it. `p_edge_refute.py` compares `_on_page` with a literal reading of the ruling text: only a figure at a needle edge is checked, using the ruling's start and end page conditions. It covered 11,541 random page/quote pairs that the quote reader accepts, with minus signs, parentheses, `.`, digits, `-\n` wraps and letters in the mix. There were 0 disagreements (exit 0).
  - The reason it holds: `_whole` reads at most 2 characters before the figure and 2 after it. Away from an edge, all of those characters are inside the needle.
  - The one case where the lookbehind reaches past the quote start is a quote that starts with `-` before the figure. That quote is already refused by `_token_once` under round 10, which treats a `-` at the quote start as a minus.
- **Observation path has only an end edge.** True. `_labelled` (cp8.py:445) needs the label before the figure, so a figure can never sit at the start edge. The claim is moot anyway, because `_on_page` checks every figure in every occurrence.
- **Both needles and both page readings** are covered (cp8.py:419-436). The guard on `_page()` holds: it is reached only after `_cite` passes (cp8.py:675, cp8.py:730).
- **Frozen pairs:** `p_frozen_on_page.py` ran 16 frozen observation and size pairs; none is refused by B1 (exit 0).

**2. B3 (wrap refusal): wired at all three analyst-text callers.**
- The callers are the decision text (cp8.py:627), the size-quote span (cp8.py:670) and the flag span (cp8.py:893). The ruling also lists the size statement and the default subject, which are not wired.
- **Not wiring those two is safe.** The statement is built from `MEASURE_LABEL` × `COMPARATORS` × an N.NN level, and the level passes `_FIGURE` first. The subject is the fixed pattern `default|restructuring`. Neither can hold `"- "`: `p_b3_owner_built.py` exits 0.

**3. Blank text: behaviour is complete, but the test misses one field (Low-2).**
- Every field I could find refuses whitespace-only text with `<path>: text is empty`.
- `flag_quote` is a span, not text. Its whitespace value gets its own pinned issue, `Flagged Risk Materialized needs flag_quote` (cp8.py:892). I read that in the code; no probe ran it.

**4. Riding Lows: present and mutant-killed.**
- `s-1.80x` is a test row, and its mutant (low1) is killed.
- `("350", "s-350")` is a test row.
- `(see 1.80)` is asserted True, and its mutant (low2) is killed.

**5. Unpinned cases: a LEAD question, not a defect (Info-1).**

**6.** Nothing was changed in frozen cases. No stub, fake value or catch-all.

### Findings
- **Low-1. The overlapping-occurrence step survives mutation.** At cp8.py:434, changing `at = text.find(needle, at + 1)` to `at + len(needle)` leaves all 370 tests passing.
  - The behaviour itself is right. On page `1.25 -1.25 -1.2` with quote `1.25 -1.2`, the original returns False (the second, overlapping occurrence is signed). The mutant returns True.
  - Fix: add `assert not cp8_module._on_page("1.25", "1.25 -1.2", "1.25 -1.25 -1.2")` to `test_r11_b1_every_occurrence_of_the_quote_on_the_page_is_read` (tests/test_method_cp8.py:1682).
  - Probe: `p_overlap_mutant.py`, exit 1 (the mutant survives).
- **Low-2. The blank-class test leaves out `thesis.exit_trigger.absence.{reason,follow_up}`.** `_ABSENT` (tests/test_method_cp8.py:1630) omits `exit_trigger`, because the frozen positive submission quotes it and the adapter cannot reach it.
  - The behaviour is correct: the same `_absence` path (cp8.py:592) gives `thesis.exit_trigger.absence.<key>: text is empty` for all 4 whitespace values on both keys.
  - Probe: `p_blank_exit_trigger.py`, exit 0. Fix: add the field to the test with an adapter that sets an absence.
- **Info-1. Two unpinned cases, on the realized bid:**
  - `bid -\n1.25` (a page minus, then a line break) is accepted.
  - `bid (-\n1.25)` (a wrapped quote that joins to `(-1.25`) is accepted.
  - The `-1.25` control is refused. Probe: `p_unpinned_linebreak_minus.py`, exit 0.
  - Under the letter of the rulings, neither is a defect. Round 10 reads the sign on `normalise(quote)`, which gives `- 1.25` with no minus directly before the digit. B1 applies only at an edge, and here the figure is inside the quote.
  - But `quotes.reading(join_wraps=True)` treats `-\n` as a wrap, so the page's joined reading prints `-1.25`, a signed figure. The defect-class inventory already lists this case as unpinned.
  - Recommend one question to LEAD covering CP-8 and CP-3D together.
- **Info-2. Field count in the report.** The report says 26 blank fields; the test has 27. The test collects 135 cases, which is 27 fields × 5 values.
- **Info-3. The two B3 callers not wired** (size statement, default subject) are not a gap; see check 2.

### Probe and mutant exit codes
All probe scripts and outputs are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-class-review/`.

| Probe | Exit | Result |
|---|---|---|
| `<S>/cp8-class/mutate.py`, rerun from a temp copy with `PYTHONDONTWRITEBYTECODE=1` (output `mutate_rerun.out`) | 0 | Unmutated copy passes; all 12 mutants killed (pytest exit 1) |
| `p_overlap_mutant.py` | 1 | The `at + len(needle)` mutant survives (Low-1) |
| `p_edge_refute.py` | 0 | 0 disagreements |
| `p_frozen_on_page.py` | 0 | No frozen pair refused |
| `p_blank_exit_trigger.py` | 0 | Behaviour correct |
| `p_b3_owner_built.py` | 0 | Neither value can hold `"- "` |
| `p_unpinned_linebreak_minus.py` | 0 | Behaviour as described in Info-1 |
| LEAD `round11/p_edge_pages.py` | 0 | Passes |
| LEAD `round10/p_signed_frozen.py` | 0 | 0 submission quotes with a minus |
| LEAD `round10/p_sign_rule.py` | 1 | Expected: see below |

LEAD's probes are not under `<S>`. They are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-review-wip-worktrees-0145fe/d412fa37-e0cf-4abc-a174-1970a42cd5dc/scratchpad/round10/` and `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-review-wip-worktrees-0145fe/d412fa37-e0cf-4abc-a174-1970a42cd5dc/scratchpad/round11/`; their outputs are saved as `lead_*.out` in my folder.

`p_sign_rule.py` exit 1 is expected, not a regression. Every FAIL is one of its "today" (pre-rule) expectations, which flip now that the rule is in. All of its "rule" and "frozen" checks pass, including "CP-8 frozen token pairs unchanged by the rule" over 711 pairs.

### Gates (worktree root, venv binaries): all exit 0
- `pytest tests/test_method_cp8.py`: 370 passed.
- `ruff check` on both files.
- `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict` on both files, with the cache in scratch.

`git status` was clean afterwards.

Not verified: whether `p_edge_refute.py`'s random alphabet covers every edge shape (it is evidence, not proof); the full repo suite; blank `flag_quote` and blank `QuoteRef.quote` (read in the code, not probed); attributions, lessons and extra_gaps beyond index 0 (same code path, not run); how LEAD rules on Info-1.
