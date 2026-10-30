Verdict: APPROVE

1. Binding. Cause 1 is bound as `cp4_runs.metric_ref` binds it. `tests/test_owner_cp4.py:138-141` takes `s1a.figure_fact(cp1.facts, runs.METRIC)` from the store's CP-1 head (`store.head_module`). It then picks `ctx["metric"]` and `ctx["metric_row"]` out of `inputs.upstream`. The expected value is not read from the module under test.
   - Cause 2 (`:158-166`) builds the list word for word from `_cp4_expected_limitations` (`test_owner_rendering.py:2358-2366`) and the `test_cp3` rule, minus the settled limitations. The order is the oracle's `literal_head_from_CP-0`, then the CP-1 head's `limitations`, then its `inherited_limitations`, de-duplicated with `dict.fromkeys`. The rule's key name is the same one `_cp4_expected_limitations` reads. The CP-4 rule has no tail entry.

2. Nothing loosened.
   - Table order, `strict=True` zip, the bound counts, claims, `settled_limitations` and the inputs assertions are unchanged in the diff.
   - The inherited check is an exact list comparison, now against a computed list instead of the rule object.
   - The `:166` Low fix is stricter: it now uses `figure_fact`, and it also requires the metric to be in `inputs.upstream.facts`.

3. Mutation probe (a copy of the committed test plus a monkeypatch of `_cp4` that drops one CP-1 entry from the CP-4 module's `inherited_limitations`):
   - Script: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4-fix-review/probe.py`. Stores: `<S>/cp4-rca/stores`.
   - For positive, gap and gap_false_same_definition, the unmutated test passes and the mutant is killed (AssertionError). Exit code 0.
   - A survivor would have made the script exit 1.

Findings: none at Medium or above.

Not verified: the genuine pytest run (the controller is running it) and a fresh CP-1 promotion. The probe used the copied stores and called the test function directly, not under pytest. Other tests in the file and the bound counts 11, 9 and 9 were not re-run by me. I did not recheck ruff, mypy or the suppression counts.
