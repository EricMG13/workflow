# CP-2D fix round 1 report (mx-feature)

CP-2D fix round 1 is done except `tests/test_financial_render.py`, which was still running when I stopped waiting (about 25 minutes). Its result is open. The branch is `claude/s2-cp2d` in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-cp2d`.

Commits on top of b47c667:
- 315ffea: the fix round
- ab7671a: a reader test that kills the R8 mutant

## Findings

- **H1 (LEAD ruling a):** `tests/test_legal_render.py` now has `CP2D_D7_DELTA`.
  - It covers exactly `liquidity-runway`, `maturity-wall` and `funding-gap`. Each is pinned to `("CP-2D", "dense", "not_run", None)` with the note "Not run: CP-2D was not requested in this run." and no rows or lines.
  - `refinancing-paths` and `lme-creditor-exposure` stay at the Unbound fallback `("Unbound", "prose", "not_run", None)`.
  - I did not edit `cases/` or the `_Spec` rows.
  - Pins that name the ids:
    - `cases/legal/render-expected.json#other_front_sections` (delta applied in the test).
    - `cases/cp4-owner/expected.json:318` (text only, no render test pins it).
    - No distressed render test pins the ids.
- **M1:** a non-USD facility now takes the lease FX path. `_facility_of` reads the facility's stated currency, requires millions units, and requires each money fact's currency to match the facility's. The `_row_facts` fixture now carries EUR money facts for a EUR facility.
- **M2:**
  - The alias check runs both ways: a facility missing its alias row, and an alias row with no `q4-2025` row, both refuse.
  - It compares every term in `_FACILITY_TERMS`, including terms present in only one row.
  - `_same_terms` now also compares `basis`.
- **M3:** `tests/test_owner_cp2d.py` is written and `tests/cp2d_runs.py` is extended.
  - 11 fast tests run now and pass. They cover:
    - the refused invoke with 0 ok calls
    - submit before `read_inputs` giving `not_permitted`
    - `stale_binding`
    - the three cases with inputs hash-equal to the final heads plus the tail
    - `blocked_cp2d` with a status-only reader
    - `begin_refused_cp2_blocked` consuming no attempt
    - a stale head re-raising at begin
  - 9 store-run tests are skipped unless `CP2D_STORE_RUNS=1` (see Deferred).
- **M4:** more money tests in `tests/test_connect_cp2d.py`:
  - long-horizon read through the reader (60 / Yes / gap 40)
  - stale head with status only
  - varied balance date
  - each adapter refusal
  - the view run-id check
  - the currency tests
  - the stale-head blob integrity check
- **L1:** both `post_import_patches` records in `docs/reuse/manifest.json` now name the full SHA of 8aef58d, which is where `shipped.py` and `report_view.py` landed. The recorded sha256 values still match the files.
- **L2, DeliveryScope row word for word from lease :127:** "Who renders: G2 `owner_rendering.py` with a new `DELIVERY_SCOPES` entry for `(covenant_refinancing, [CP-1, CP-1A, CP-2, CP-2D], synthetic)`, sections `liquidity-runway`, `maturity-wall`, `funding-gap` and the two rails. The other FP04 blocks are unasserted (CP-4 not requested; CP-3C has no core), as the CP-4 FP04 lease does."
- **L4:** `select_cp1(cp1) -> Selection` deviates from the lease's `operands(*, cp1) -> Operands`. It returns the selection (operands, facilities, balance date) in one value.
- **Plan note versus oracle:** a stale, non-blocked required head re-raises `ValueError` at begin (`owner_workflow.py` ~:770-774). The oracle says "a stale required head refuses the same way". I pinned the code behaviour in `test_a_stale_required_head_is_not_a_retained_refusal`. The conflict needs a ruling.
- **Equivalent mutant:** the `fact.period is None` guard was unreachable through `Fact`'s validator, so I removed the dead check.

## Probes and mutants

| Probe | Exit |
|---|---|
| p5 (`p5_fx_facility_unreachable.py`) | 0 |
| p6 (`p6_alias_only_facility.py`) | 0 |
| p13 (`p13_missing_acceptance.sh`) | 0 |
| p7 (new copy `p7_new.py`, 0 survivors) | 0 |

p5 and p6 ran on the real head copy. I could not run the original `p7_mutants.py` on the new code, because the round's edits changed the A3, A4 and A10 snippets (they came back "not applied"). The copy rewrites A3 and A4 against the new code and adds A3b (alias presence not compared) and A4b (alias-only row accepted). It drops A10 as the dead guard above.

The copy is at `<S>/cp2d-s2-review/p7_new.py`, with its log at `<S>/cp2d-s2/p7_new.log`.

## Gates

- **pytest:** the five-file gate plus `tests/test_owner_cp2d.py` gave 709 passed, 9 skipped, 17s. That ran before the R8 test; the `-k stale_head` selection (2 tests) passed after it, and I did not rerun the full set.
- **Render tests:**
  - `tests/test_legal_render.py`: 76 passed.
  - `tests/test_connected_render.py`: 14 passed.
  - `tests/test_financial_render.py`: not finished.
- **ruff check:** clean on the changed `src/` and `tests/` files, with two pre-existing exceptions. `tests/test_legal_render.py:231` C408 is in code I did not touch. `ruff check` on `report_view.py:293` SIM102 already fails at 8b46132, and I did not run it this round.
- **ruff format --check:** clean on the changed files.
- **mypy --strict:** clean on the changed files other than `tests/test_legal_render.py`. That file has 128 errors, the same count as at HEAD before my edits.

## Deferred (slow)

```
CP2D_STORE_RUNS=1 PYTHONPATH=src python -m pytest tests/test_owner_cp2d.py
```
This runs the store runs, receipt verification and tamper tests. They need a real CP-1 promotion, which takes 11 to 26 minutes.

Not verified: `tests/test_financial_render.py` (run was unfinished); the 9 store-run tests in `tests/test_owner_cp2d.py`, which have never executed; the tamper test's use of `ow._verify_audit` and `ow._verify_calls_reads` in the same file, whose signatures were not checked; my own 77-mutant run, which I did not repeat after the M1/M2 edits; the full pytest set after the R8 test was added; the lane brief's binding rulings (citations, `RunText`, synthetic limitation, aliases) beyond the fix items; and the hand-written new facility cases, which have no Hypothesis or property test.

Ledger: `agent=mx-feature fix-rounds=1 gates-first-pass=n`
