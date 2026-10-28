**CP-2E Stage 1 class round 11 review: commit 38f0ddc, diff 864ffe3..38f0ddc**

Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a219254fe68cc1c2d

**Spec verdict: APPROVE.** **Quality verdict: APPROVE.** There are no High or Medium findings. There is one LEAD question (L1) and two Low test gaps (L2, L3), which can ride with the next CP-2E change.

Brief constraints:
- Only `src/deploy_workflow/owners/cp2e.py` and `tests/test_method_cp2e.py` changed (+369/−22).
- Nothing changed under `cases/` or `src/deploy_vii`, and no test line was deleted.
- The brief sets no diff ceiling; the global 800-line cap is not reached.
- I found no stub, fake value or catch-all in the diff.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-class-review/`.

### Check by check

**1. B1 (cp2e.py:497-544, called at :595 and :684-685)**
- It covers the share and the balance, spread and floor operands. All three labelled operands go through `labelled`, which now passes the page.
- Every occurrence: `_starts` steps by `at + 1`, so overlapping occurrences count.
- Every reading: the needles are plain plus joined when the quote is wrapped. The page readings are plain plus joined when the page is wrapped. All four pairings are checked. `quoted` uses the same needles and readings, so at least one pairing always matches.
- The claim that checking every span equals checking edge spans only stands; I could not refute it. A span away from the edges reads only the needle's own characters:
  - the lookbehinds need at most 2 characters, and the `-` case at index 1 is itself an edge ("only a sign before");
  - the lookahead and the parenthesis test need 1 to 2 characters.
- Evidence: `p1_every_vs_edge.py` (exit 0) and `p1b_every_vs_narrow_edge.py` (exit 0). Each ran 557,646 random page, quote and token triples with `-`, `(`, `)`, `.`, `+`, U+2212, `\n` and `-\n`. Neither edge definition (broad or narrow) produced a difference.

**2. B3 (cp2e.py:647-649, :665)**
- The rule is applied to `reference_rate` under FLOATING, which is correct.
- No other quote-read name or text value is missing it:
  - `code_text` must match `[A-Z]{3}`, so it cannot contain `- `;
  - the rate phrase `[\s-]+` reads the same either way, as the ruling says;
  - basis quotes are citations only;
  - under FIXED, `reference_rate` is not read from the quote.

**3. Blank text, and the implementer's extensions**
- **`reference_rate` in the blank class** (cp2e.py:667): consistent with the ruling. It is analyst-typed text (lease schema line 104), and before this change `" "` and `""` passed under FLOATING because a space is "in" any quote. This closes a real gap.
- **A `""` limitation on a non-Insufficient-Information assessment is now refused** (cp2e.py:714): consistent with the library. `blank_failure` requires some refusal for `""`, CP-2E has no schema refusal of `""`, and the field is analyst text (rendered as the cell's `limitation`). No frozen case carries `""` or blank text anywhere in `cases/cp2e-owner/` (grep exit 0, no hits).
  - On an Insufficient Information assessment, `""` now gets two issues: `empty text`, then the existing "limitation is required". The existing refusal stands, as the controller decided. (Info, `p2_behaviours.py` c2.)
- **Page minus followed by a line break: a LEAD question, not a defect.** See L1.
- **Frozen issue order does not move.** No frozen value is blank, and B1 and B3 fire only on new inputs. All 350 tests pass, frozen cases included.

**4. Owner item: confirmed, and it predates this diff.**
- At 864ffe3, lines 703-704 already read `chk.digit_free(f"{key}.reason", …)`, with no `fx.` prefix.
- Today the same field `fx.operating_fx_absence.reason` gets `fx.operating_fx_absence.reason: empty text` but `operating_fx_absence.reason: digits are not allowed` (`p2_behaviours.py` d1 and d2).
- No frozen case pins either spelling. It goes to the owner.

**5.** No frozen case changed, and no stub, fake value or catch-all was found.

**6.** Mutants: results below.

### Findings

**L1 (Low; for LEAD, not a defect): page `-` then a line break before the digits is read inconsistently inside CP-2E.** cp2e.py:497-544. Probe: `p2_behaviours.py` checks a1 to a4 (exit 0; it asserts the current behaviour). On the page `Earnings abroad were -\n25 percent of EBITDA.`, with value `25`:
- quote `25 percent of EBITDA.` is refused, because the joined page reading prints `-25` (the implementer's own test, test_method_cp2e.py, the `joined-page-minus` case);
- quote `were - 25 percent` is accepted: the figure is not at an edge, and round 10 reads `- 25` as unsigned;
- quote `-\n25 percent` is accepted, although its joined needle `-25 percent` has only a sign before the figure, so it is an edge. Literal B1 on the joined needle in the joined page would refuse it.
  - The cause: `_unsigned(token, needle)` leaves out figures that the needle itself prints signed, so that span is never checked on the page.
  - For labelled operands (`spread -\n25`), the label check refuses anyway. Only the share is exposed.

Round 11 lists this case as not examined, and you report that CP-3D and CP-8 treat it differently. LEAD's ruling on whether `-\n<digits>` is a sign settles a1 and a4 together. Until then, CP-2E refuses one spelling of the same page figure and accepts another.

**L2 (Low; test gap): no test accepts a figure that only the joined reading of a wrapped page holds.**
- Reviewer mutant "B1 page spans from the plain page reading only" survives (exit 0 in `mutants_extra.out`). It replaces `on_page = _unsigned(token, text)` at cp2e.py:539 with the plain page reading.
- The current code is correct: page `…first-\npriority unit were 25 percent.` with quote `first-priority unit were 25` is accepted (`p2_behaviours.py` b1). The mutant would refuse that genuine quote, failing closed.
- Fix: add the b1 page as an accepted twin in `test_b1_every_occurrence_in_every_reading`.

**L3 (Low; test gap): the limitation blank check is pinned only for the Insufficient Information assessment.**
- Reviewer mutant "blank limitation only when Insufficient Information" survives.
- The new refusal of `""` and `"  "` on a non-Insufficient-Information limitation (`p2_behaviours.py` c1 and c3) has no test, as the implementer's own `Not verified:` line says.
- Fix: add `assessments[0].limitation` to `_TEXT_FIELDS`. With the current set-up it would fail for whitespace text, since "only for it" also fires and the exact-match helper accepts only the expected issue among others. So pin c1 and c3 directly.

**I1 (Info): two surviving mutants are equivalent and need no test.**
- "B3 raw reference_rate (not normalised)": a value that differs only before normalisation is already refused by `reference_rate not in normalise(quote)`.
- "empty-text frame after digits": whitespace-only text never has digits, so the order cannot be observed.

### Probe and mutant exit codes
- `p1_every_vs_edge.py`: 0 (0 differences)
- `p1b_every_vs_narrow_edge.py`: 0 (0 differences)
- `p2_behaviours.py`: 0 (it confirms the behaviour behind L1, L2 and L3, the extensions and the owner item)
- `mutants_impl.py` (a copy of `<S>/cp2e-class/mutants.py`, run with `PYTHONDONTWRITEBYTECODE=1` in a full temporary copy): exit 0. The baseline exits 0 and all 16 mutants are killed.
- `mutants_extra.py` (8 reviewer mutants): exit 1.
  - Killed: `isspace` misses `""`; joined needle only when the page is wrapped; page parenthesis exclusion dropped; `reference_rate` blank check only under FLOATING.
  - Survived: plain page spans only (L2); limitation only for Insufficient Information (L3); raw `reference_rate` (I1, equivalent); frame order (I1, equivalent).

### Gates (run in the target worktree)
| Gate | Exit |
|---|---|
| `PYTHONPATH=src …/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp2e.py` (350 passed) | 0 |
| `ruff check` on both files | 0 |
| `ruff format --check` on both files | 0 |
| `MYPYPATH=src mypy --strict` on both files (cache kept in the scratchpad) | 0 |

Not verified: I did not compare against how CP-3D and CP-8 treat `-\n` (L1); I took that from your brief. I ran neither the full suite, `test_host_h1.py -k cp2e`, nor GitNexus `detect_changes`. B1 equivalence rests on random fuzzing over a small alphabet, not a proof. The `.mypy_cache/` and `.ruff_cache/` folders in the target worktree are git-ignored; I ran with `--no-cache` and a scratchpad mypy cache, so I believe they predate this review, but I did not prove it. No frozen oracle cases were rebuilt.
