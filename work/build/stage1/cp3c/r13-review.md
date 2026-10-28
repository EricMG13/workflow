**CP-3C round 13 review (commit 6373602 against d2cb626)**

**Spec verdict: APPROVE.** **Quality verdict: APPROVE.** There are no High, Medium or Low findings. Three Info notes are for LEAD.

**Spec check**
- **Scope.** Only `src/deploy_workflow/owners/cp3c.py` and `tests/test_method_cp3c.py` changed: 244 changed lines, under the 800 ceiling. Nothing under `cases/` moved, so no oracle changed.
- **Item 4 (R1 L1).** Every clause matches the ruling:
  - `Status` and `CellStatus` hold the four statuses (cp3c.py:36-37), and `GAP_SHOWN` spells `conflicting` as `∅ G#` (:971-975).
  - `_amount` (:788) and `_stated_text` (:805) use `status != "known"` and return None.
  - `_op` (:423-428) gives `Not calculable: <label> is <missing|conflicting|not applicable>` through `_STATE_WORD`, which copies the CP-4C pattern (cp4c.py:546). Each operand's status comes from `Operands.statuses`, which `compose_operands` fills (:943-953).
  - `_copy` (:1087-1089) keeps `fact.status` and `fact.reason` verbatim.
  - `_check_value` (:250-251) requires a reason and no value for every status other than known.
- **The two unchanged dependants** are not required to change. The ruling names only `_op` for the C-2 frame and says "Frozen. Nothing moves". `REASON_MINIMUM_CASH` is a fixed oracle reason (:376), and the claim text at :1800 depends on it. See Info 2.
- **Item 5 (R1 L2).** `check_currency` (:832-854) runs first in `compute` (:1899):
  - `cash_closing`, when known, must have a currency that is set and not blank, and equal to `Cp3cInputs.currency`.
  - Every other known MILLIONS fact read (CP-1 undrawn, EBITDA and interest, each T4.18 amortisation; CP-2D run-rate, minimum cash, funding gap and each wall principal) must equal it.
  - That covers every MILLIONS field in `Cp1Operands` and `Cp2dOperands` (:310-335). Horizon and months are not MILLIONS.
  - All three new strings are in the module's frame: `CP-3C cash_closing: …`, `CP-3C: reporting currency …` and `CP-3C <name>: …`. They match the existing `CP-3C: a facility_id repeats` and `CP-3C {what}: …` forms.
- **The two implementer calls.**
  - Checking known MILLIONS facts only is consistent with the ruling: a gap carries no value to sum.
  - When `cash_closing` is missing, the implementer's option still fails closed. Probe A: cash missing, `currency="EUR"`, the others USD raises `CP-3C undrawn_rcf: currency 'USD' is not 'EUR'`. A gap cash stays runnable: probe B (all EUR) runs, as does `test_r13_a_missing_cash_closing_needs_no_currency`. Refusing instead would make a gap cash unrunnable. See Info 1.
- **Frozen cases.** The only removed line in the test diff is the `typing` import. The helpers `_cp1_fact` and `_cp2d_fact` only add `currency=USD` on MILLIONS facts, and no frozen assertion changed.
- **CP-2D claim: verified.** The tests read `cases/cp2d-owner/expected.json` (test :34). Neither the tests nor cp3c.py import any CP-2D owner module: the tests import only `deploy_workflow.owners.cp3c`, and cp3c.py imports only from `deploy_vii` and `owners.blank`.
- **No stub, fake value or catch-all** was found in the diff.

**Info notes for LEAD (no ruling text breaks)**
1. **Unsourced currency (cp3c.py:837, :853).** When `cash_closing` is missing, `Cp3cInputs.currency` has no source and is only checked by equality against the other known MILLIONS facts.
   - If none of them is known, the input currency is stamped on every US$ m cell (:1121) unchecked.
   - If they all carry `""` and the input is `""`, the run passes, because the blank check applies only to cash. I read this from the code; no probe ran it.
   - The ruling's "must be set" covers cash_closing, so this is unruled.
2. **Status words in other dependants.**
   - A `conflicting` CP-2D `minimum_cash` gives the need reason `Not calculable: minimum cash not assessed` (probe C).
   - A `conflicting` T4.18 seniority gives `Not calculable: facility term-loan seniority is not stated` (probe D).
   - Neither names the actual status. The ruling scopes the C-2 status frame to `_op` only, so changing them is LEAD's call.
3. **`_check_value` message frame (:251).** The new message `CP-1 T4.10: a conflicting fact carries a reason and no value` keeps the existing `CP-1 …`/`CP-2D …` prefix, not `CP-3C`. This predates the change, and the brief's frame rule targets the item 5 strings.

**Exit codes** (run in a full archive copy, PYTHONDONTWRITEBYTECODE=1)
- pytest on `test_method_cp3c.py` and `test_defect_classes_selfcheck.py`: 0 (536 passed)
- `ruff check`: 0
- `ruff format --check`: 0
- `mypy --strict` on both files: 0
- Implementer mutants (`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-r13/mutants.py`): 0, with all 16 killed
- My probe (`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-r13-review/p_r13_review.py`, run from the copy root with PYTHONPATH=src:tests): 0

Not verified: the whole suite and other modules' tests; a real promoted head's T4.10 `currency`; how Stage 2 binds and renders a `conflicting` cell through the product; the blank-currency case in Info 1 (read from code, not probed); the cp3c lease-pin test (it was not in the gate set I ran).