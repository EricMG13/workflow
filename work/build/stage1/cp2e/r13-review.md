## CP-2E round 13 review (ccdeeeb, `git diff 5fa075e ccdeeeb`)

**Spec verdict: APPROVE. Quality verdict: APPROVE.** There are no High, Medium or Low findings, and one Info finding that predates this change.

### Spec
1. **Item 8, `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/r13-cp2e/src/deploy_workflow/owners/cp2e.py:512-516`.**
   - The change adds `(?<![0-9],)(?<![0-9], )` and the trailing guard `(?![0-9]|[.,][0-9]|, [0-9])`. That is exactly LEAD's narrowed join ("For LEAD" item 8) and nothing broader.
   - Rule W's `(?<!minus)(?<!minus )` and the parenthesis filter are kept.
   - The pattern equals CP-3D `_tokens` on `claude/r13-cp3d` (cp3d.py:203), apart from the lookbehind order, which changes nothing.
   - A fuzz of 200k cases of `_unsigned` against an independent character-wise model of round 10 + W + item 8 found 0 disagreements.
   - Plain and joined page readings gave the same figure count in 0 of the wrapped-page fuzz cases that disagreed.
2. **Readers.**
   - The share reader and the labelled readers (spread, and the shared `labelled` path that balance and floor also use) refuse `1,25`, `1, 25` and `1,\n25` before the figure, and `25,1`, `25, 1` and `25,\n1` after it.
   - The report's untested gap, the labelled reader's trailing page edge, holds: the probe covers it with a plain page and with a wrapped page.
   - Letter twins (`25, a`) stay accepted. `2025, 25` is refused, which is the ruled cost.
3. **Frozen.**
   - Frozen triples: CP-2E 15, "moved: none" (`p13_comma_space_join.py` line (a)).
   - `p13_refusal_mutations.py` ran 28 CP-2E mutations, exit 0. No CP-2E mutation moves; the one change listed is CP-3D `amortisation_nonzero`, which addendum 2 rules.
   - That probe drives the module's real `validate_macro_fx`, but it compares against monkeypatched model readers rather than the oracle file. The frozen-oracle comparison itself comes from the pytest mutation pins (test_method_cp2e.py:300-310), which pass.
4. **B3, cp2e.py:498 and :661-671.**
   - `_W_SIGN` is exactly W's minus. It runs on `normalise(value)`, which maps U+2212 and the dashes to `-`, the same reading W uses.
   - The index-0 guard is `m.start() > 0`.
   - On 50k random names `_split` gave the same answer as CP-3D `_name_occurs` every time (0 disagreements).
   - The library cases `w-minus-wrap-text` and `b3-*` pass in the gate run.
5. **Coordinator's added check (the addendum 4 class: a quote edge at the page's `,` or `, `).** CP-2E does not have this defect.
   - `_once` (cp2e.py:549-556) checks every figure span of every needle occurrence against `_unsigned` run over the whole page reading. It does not decide edges by the quote's last character.
   - All 12 probes are refused, including `fee of 1,` on `1,250`, `,250 per year`, `, 250 per year`, `margin of 25,` on `25,5`, and the share and spread variants with `,`, `, ` and `,\n`.

### Quality
- No stub, no fake value and no catch-all in the diff.
- All 8 of the implementer's mutants are killed when re-run. Each one is caught by the test the report names.

### Findings
- **Info (predates this change), cp2e.py:687.** `rb["reference_rate"] not in quote` compares the raw value with the normalised quote.
  - Input: value `is − 1.25` (U+2212) on page `is −\n1.25`.
  - Output: refused with `reference_rate does not occur in the quote`, although W would read a signed figure.
  - This fails closed. CP-3D has the same check (`name not in normalise(quote)`), so it goes to the owner, not this task.
- **Info (test strength), test_method_cp2e.py:1350.** The `w-minus` case in the new B3 test uses an unwrapped quote, `The level is - 1.25 percent`, so `_split` returns False before the exemption is reached.
  - The exemption is still covered by the library case `w-minus-wrap-text` (it kills M5), so nothing is missing.

### Exit codes (all from the temporary copy of ccdeeeb)
| Check | Exit |
|---|---|
| pytest on cp2e, selfcheck and h1 (762 passed) | 0 |
| `ruff check` | 0 |
| `ruff format --check` | 0 |
| `MYPYPATH=src mypy --strict` | 0 |
| `run_mutants.py` (8 of 8 killed) | 0 |
| `p13_refusal_mutations.py` | 0 |
| `p_unsigned_fuzz.py` | 0 |
| `p_readers_edges.py` | 0 |
| `p_comma_edge_cp2e.py` | 0 |
| `p13_comma_space_join.py` | 1 |
| `p13_quote_classes.py` | 1 |

The last two exit 1 because of the probes' own model expectations, as the implementer reported. The frozen lines are unmoved.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-r13-review/`: `p_unsigned_fuzz.py`, `p_readers_edges.py`, `p_comma_edge_cp2e.py`, plus copies of `run_mutants.py` and the three `p13_*` probes repointed at `copy/`. The CP-3D reference was taken from `claude/r13-cp3d` into `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3d_ref.py`.

Not verified: the full suite and other modules' tests were not run; GitNexus `detect_changes` was not run; the CP-3D `p_comma_edge.py` probe was not run itself (its class was rebuilt for CP-2E); the fuzz alphabet is ASCII plus U+2212 only (no NBSP, soft hyphen or other Unicode dashes in the random strings); the frozen comparison for the 28 refusal mutations rests on the pytest pins, not on a direct check of the oracle file.