# CP-L10 fix round 1 report (mx-feature)

CP-L10 fix round 1 is done on `claude/s2-cpl10` in one commit, 1ec5ba8, on top of 6e7f5b3. All three Mediums and the four Lows are fixed. Every new test was written first and seen red for the right cause. The exceptions are the M3 store tests, which I wrote after the code they exercise, and the run-driver fix (M2 part), whose old-code failure I took from your review (KeyError) rather than re-running it.

**Gates**
- **Test set:** the five-file set passes with 555 passed and 1 skipped; the skip is the Front Page / rail test, marked "blocked on G2 (Stage 3)".
- **Static checks:** `ruff check`, `ruff format --check` and `mypy --strict` on the 7 changed files all exit 0.
- **Mutants:** 32 of 32 of mine are killed, including the new ones for M1 normalise, the L3 narrowing, the blocked reader and the reader status.
- **Review mutant script:** `p9_mutants.py` exits 1 because 8 mutants still survive, none of them yours. Seven are the review's own equivalent ones:
  - the current-head read;
  - the synthetic line in a public run;
  - the quantize context;
  - raw-text validation;
  - the latin-1 bytes decode;
  - disposition taken from materiality;
  - the NOAPPLY line, `validate_reraise`, whose source text I changed when I narrowed the catch.
  The six non-equivalent survivors are all killed.

**Reviewer probes**

| Probe | Exit |
|---|---|
| `p1` | 0 |
| `p2` | 0 (it needs a tmp-dir argument; it exits 1 without one) |
| `p3` | 0 |
| `p4` | 0 |
| `p6` | 0 |
| `p7` | 0 |
| `p9` | 1 (8 survivors above) |

`p7` ran against a genuine store I built with a new script, `<S>/cpl10-s2-fix/build_positive.py` (`<S>` being the scratchpad directory), in one CP-1 promotion. CP-1 stores `17.50`, `20.00`, and so on, and the view now equals the oracle.

**What changed**
- **M1.** `_plain_text` now writes `format(amount.normalize(_EXACT), "f")`. The `_EXACT` context matters because the default 28-digit normalize rounds the oracle's 37-digit ratio. The fast fixture now stores padded amounts, and a parametrised test round-trips every oracle `amount_exact`. That test and `test_view_is_the_oracle_tree` went red before the fix.
- **M2.**
  - `readiness_literal` now keys the column on `label`, and binds the kpi period by the short spelling (`Q1 25`), taken from the T4.10 label up to its date range.
  - The dead `inputs_sha256` try/except is gone; the key is dropped and the step pre-fills it.
  - Two fast tests pin this: one binds the markers from the short spelling, the other fails loudly on an unmatched period.
- **M3.** `tests/test_owner_cpl10.py` now has 10 tests, and all 10 passed in one run (about 23 minutes under load).
  - **Positive and limited:** both run cell for cell.
    - Inputs are hash-equal to the heads.
    - Every fact is checked, including copied cells' `calculation_id`, the TL10.1 run-bound cells and citations.
    - Claim citations, `validate_tables` and the settled and inherited limitations are checked.
    - The recorded view equals the oracle.
    - Verification leaves the store bytes unchanged.
  - **Tool-use and order checks:** `invoke` refused with one ok read and no pack call; submit before `read_inputs` is `not_permitted`; `stale_binding`.
  - **Blocked walk:** it runs with a receipt, and the reader returns status and hash only.
  - **Tamper:** a consistently forged head, with a recorder confirming `cpl10.probe` is the check that refused.
  - **Fast tests (seconds):** the CP-1-missing `RefusedBegin` and the blocked-CP-1 `RefusedBegin`. `RefusedBegin` has no `kind` field, so these assert module and reason.
  - **Navigator:** the unrun and settled states are tested in `tests/test_connect_cpl10.py`, plus the settled screen's own row after a submit.
- **L1.** There are new fixtures: a public run of another issuer and `as_of` with CP-1 accepted ("Pass"), and a public run with CP-0 accepted and CP-1 restricted. The reader is also tested on the limited head and on a stale head.
- **L2.** A blocked head's reader returns `Cpl10Head("blocked", result_sha256, (), {})`.
- **L3.** A new `UpstreamError(ValueError)` is raised for unbound input, operand, unit and scale. `_validate_step` and `view` catch only that, so a store hash mismatch propagates (shown by `p2` cases e and f). A direct submit with an unbindable CP-1 still settles as an issue.
- **L4.** The manifest `project_commit` is now the full SHA of 6b679ca.
- **Model-text rule.** I fed `[a lot`, `{low`, `{}` and `x }` into every assessment, rationale and gap field, through the real store. The analyst claim fields journal `Malformed run text` and the gap fields are plain data. Nothing raises after the binding write. The 24 cases are pinned. They passed straight away, so this is a pin, not a red test. The shared `tests/defect_classes.py` test is not in this branch.

**For the deferred list** (`work/build/deferred-runs.md`)
- `PYTHONPATH=src:tests "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_owner_cpl10.py` (one CP-1 promotion).
- `test_owner_workflow.py`, `test_owner_s1a.py` and the render runs, as before.

Not verified:
- **Front Page blocks, call band and rail population** are not tested. They are blocked on G2 (Stage 3), and one test is skipped with that reason. The without-D4 navigator state is superseded, since D4 has landed.
- **The shared hostile-text class test** in `tests/defect_classes.py` is not run, because it has not landed in this branch.
- **A genuine unbound CP-1 operand** through `OwnerWorkflow` is not exercised (only the missing-input path and the direct-core path).
- **The readiness marker binding** matches kpi rows on key and period, not on `observation_ids`. The review found this equal to the lease rule for the financial pack only.
- **`p5d_closed_run_short_labels.py`** was not rerun; `test_owner_cpl10.py` covers the same ground.
- **The stale-head reader test** passes a hand-made stale head, not one produced by a real invalidation.

agent=mx-feature fix-rounds=1 gates-first-pass=n
