Verdict: driver fix (claude/s3-cp2g-driver 419295e) APPROVE. Round 4 (claude/s3-fix4-g2 65e233c) APPROVE.

No High, Medium or Low findings.

Driver fix:
- Schema forbids extras: `DownstreamReview(Contract)` is at src/deploy_vii/downstream_readiness.py:80-83. Its fields are `schema_version` (defaulted), `inputs_sha256` and `consumers`. `Contract` sets `extra="forbid"` at src/deploy_vii/contracts.py:76. The fixer's comment is correct.
- Because `schema_version` has a default, omitting it from the payload is valid.
- `readiness_payload` (tests/cp2g_runs.py, new, above `readiness_literal`) raises RuntimeError on any key outside `inputs_sha256`, `consumers` and `note`. It also raises when `inputs_sha256` or `consumers` is missing. It drops only `note`.
- The cp2h and cp4c drivers call the same helper through `_driver("cp2g_runs").readiness_payload(literal)`: tests/cp2h_runs.py:155 and tests/cp4c_runs.py:142.
- The fast test is not vacuous. It reads `cases/{cp2g,cp2h,cp4c}-owner/submissions.json` and asserts `cases` is non-empty. In the 419295e tree, grep counts of `cp1_readiness` in those files are 6, 4 and 2, so real literals are exercised. It asserts the key set is exactly `inputs_sha256` and `consumers`. Two further tests cover the unknown-key and missing-key failures.

Round 4:
- The rule is the `if len(wants) == 1` branch at tests/test_owner_rendering.py:2068-2071. It sits only in the `elif "tabs" in oracle` branch, so a tabs-only oracle with exactly one entry is the only case it touches. Every other comparison, and the `primary` branch, is unchanged.
- Rows are still checked: the `_register_ok` loop runs after the rule, and the third new assertion pins this.
- Probe: I copied 65e233c to `<S>/fix-drivers-r4-review/b` and deleted the two rule lines. The directory is /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/fix-drivers-r4-review/b. Running `pytest tests/test_owner_rendering.py -k test_fast_block_rule_handles` there fails (1 failed) with "At index 0 diff: None != 'Binding'". I ran it inline and saved no probe script.

Info:
- Only the first new assertion, the positive untabbed case, goes red without the rule. The other two are `pytest.raises` guards that keep strictness: a tabbed block against a one-entry oracle, and a wrong cell text. They pass with or without the rule, which is their purpose. The brief's "three assertions fail without the rule" is not literally true for them.
- The one-entry label is not compared in this helper. The comment points to tests/test_connect_cp1d.py:319-340 for that check, and I did not read that file.

I found no stub, fake value or hidden failure in either diff.

Not verified: I ran no real-data tests, no ruff or mypy, and no full suite. I did not open tests/test_connect_cp1d.py:319-340. I did not check that the oracle's `note` key is the only commentary key across all oracle files, beyond the 6, 4 and 2 literals' being covered by the controller's fast test run (5 passed).
