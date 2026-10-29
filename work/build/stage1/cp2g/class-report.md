CP-2G class round (round 11): the blank-text class and the Q12 raise are both done and committed. Every gate exits 0.

**Commit:** `4c4892c` on branch `worktree-agent-a4377a7580e8e70db` (worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a4377a7580e8e70db`).
- Step 0: the merge of `claude/module-dev-status-review-0981b6` was a fast-forward.
- HEAD after the merge was `12e9dcf`, the lane tip.
- `git diff 12e9dcf HEAD -- src tests cases docs/rulings` was empty before my commit.
- Only `src/deploy_workflow/owners/cp2g.py` (+16/−5) and `tests/test_method_cp2g.py` (+126) changed.

**Class by class**
- **B1 edge cut, B3 wrap:** not in class. CP-2G reads no value from an analyst quote (inventory note; the brief's row lists blank only).
- **Blank, 15 rationale and gap fields** (`base_drivers.*.rationale`, `downside.rationale`, `minimum_liquidity.rationale`, `assessment.rationale`, `gaps[0].{gap,why_it_matters,affected_analysis,action}`): already passed with the pinned `<path>: empty text` (V08).
- **Blank, 9 `*.limitation` fields** (7 drivers, `downside`, `assessment`): **fixed**, 45 of 45 cases red before the fix.
  - A new `_limitation_issues` in `content_issues` refuses whitespace-only text and `""` with `<path>: empty text`. `""` needs its own refusal because these fields are `str | None` and the schema accepts it. `None` is still allowed.
  - Each issue sits right after its field's rationale issue. For the assessment that puts it before the High issue. No existing order pin moves; the placement is my call and is unpinned.
  - No new wording: the frame is the pinned one, which is also `defect_classes.EMPTY_TEXT`.
- **Tests:**
  - `test_blank_text_is_refused`: all 24 fields × `BLANK_CASES`, run through `blank_failure`.
  - `test_blank_text_twin_is_accepted`: 24 twins.
  - `test_blank_fields_cover_every_analyst_text_field`: walks the `ForwardSubmission` schema and checks the list equals every plain `str` or `str | None` field with no pattern.
  - `test_blank_limitation_is_reported_in_place`: checks the issue order.

**Riding item, round 11 Q12**
- `_usd_millions` now takes the name to print, so one helper serves both checks:
  - M2 calls it with `CP-1 <metric>`; its text is unchanged and the existing M2 test passes.
  - `_supported` calls it with `CP-1D <label>`, for a known T1D.3 fact, before the period check. It is a plain `raise ValueError`, not an `assert`.
- `<label>` is the running-text label from `_t1d_label` (round 6d), giving `CP-2G: CP-1D supported adjusted EBITDA must be USD MILLIONS at scale 1000000, not EUR MILLIONS at scale 1000000`. The ruling only says `<label>`; I matched the module's other CP-1D frames.
- **Tests:**
  - `test_q12_cp1d_supported_ebitda_must_be_usd_millions`: 4 cases (THOUSANDS/1000, EUR, scale 1000, currency None), each checking the exact text on compose.
  - `test_q12_cp1d_other_period_book_still_fails_closed`: a known fact for another period is still copied into T2H.2 as US$ m, so the book check must come before the period check. The first mutant run showed this case was missing.
  - `test_q12_cp1d_usd_millions_twin_composes`: the frozen USD MILLIONS book composes.
- **Under `python -O`** the raise still fires: `<S>/cp2g-class/p_q12_optimised.py`, exit 0.

**Mutants:** `<S>/cp2g-class/p_mutants.py`, run on a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`. Final run exit 0, all 9 killed (pytest exit 1 for each):
- `_limitation_issues` returns nothing
- the driver, downside and assessment limitation checks each removed (3 mutants)
- only `""` refused
- the Q12 raise removed
- the label not in running text
- the raise moved after the period check (survived the first run; killed once the other-period test was added)
- M2 loses its `CP-1` prefix

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`

**Gates** (worktree root, all exit 0):
- pytest `tests/test_method_cp2g.py`: 379 passed. The 227 tests that predate this round pass unchanged, so every frozen case holds.
- `ruff check`: 0.
- `ruff format --check`: 0.
- `MYPYPATH=src mypy --strict` on both files: 0.
- `tests/test_defect_classes_selfcheck.py` (library untouched): 152 passed.
- First pass: pytest and mypy were 0. ruff flagged the import order of `defect_classes` (it sorts as third-party) and format reflowed two lines; I fixed both with `ruff --fix` and `ruff format`.

**Stage 2 notes (`methods/cp2g.md`):**
- A stated limitation that is blank or whitespace-only is refused with `<path>: empty text`; an absent (`None`) limitation stays allowed.
- Limitations get only this blank check, not the prose or prohibited-phrase checks the rationales get (that would be new scope).
- A CP-1D supported EBITDA in a book other than USD MILLIONS at scale 1000000 fails closed with the Q12 frame in composition.
- `validate_forward` does not read CP-1D, so Q12 cannot fire there. This differs from M2, which fires in both validation and composition.

Not verified:
- The Q12 path can't be reached from a real CP-1D head: CP-1D forces MILLIONS and one currency. The tests reach it only by editing the frozen fact with `model_copy`.
- The CP-1D leverage facts (multiples) get no book check; the ruling names only the EBITDA read.
- The full suite and other modules' tests were not run.
- No GitNexus impact or detect_changes was run.
- No Stage 2 reader or rendering of a blank-limitation refusal was checked.
- The mutant set is hand-picked; no full mutmut run.

Ledger: `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n` (pytest and mypy passed first time; ruff import order and format needed an autofix).
