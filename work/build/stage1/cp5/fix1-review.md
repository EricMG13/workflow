## CP-5 fix round 1 re-review (cp5-stage1 @ 81e8c0b, diff 4e2d687..81e8c0b)

**Verdict: APPROVE.**

Every mutant the first review named now fails the suite on its own, and so does the test the fix report names for it. A08 is equivalent. `cp5.py` is unchanged: `git diff --stat 4e2d687 81e8c0b -- src` is empty, the diff touches only `tests/test_method_cp5.py`, and the target tree is clean at 81e8c0b. I found no new High or Medium finding.

All probes named below are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp5-fix1-review/`, each with a `.log` beside it. The adversary's probes ran from `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp5-adversary/`. All mutants ran from full temporary copies with PYTHONDONTWRITEBYTECODE=1.

### F1 (Medium): holds

**A02: killed by `test_view_cuts_every_mark_of_a_claim_with_several_failing_citations`** (`tests/test_method_cp5.py:1097`).
- **Suite alone:** 1 failed. The named test alone: rc 1.
- **State:** every citation of the CP-1A claim with the most citations gets a quote that is not found under its locator. That is a genuine failing citation, which `python_checks` finds itself. `_rescope` (line 1057) then rebinds each hash and status from the head, and builds `heads` the way `review_scope` does: it skips the pack and `NOT_EVALUATED`. This is faithful.
- **Assertions:**
  - one mark per citation, each exactly `claim_citation`;
  - the top level equals lease step 5 at full length;
  - no quote and no `prefix(quote)` in the body (line 1128).
- **Extra variants I added, all killed by this test:**
  - X1 cuts every mark but the last;
  - X2 cuts at the last `": "` (`rsplit`).

**A03: killed by `test_view_keeps_a_blocked_heads_quotes_out`** (line 1131).
- **Suite alone:** 1 failed. The named test alone: rc 1.
- **Extra variants, both killed by the suite:**
  - X3 skips blocked modules by `status`;
  - X5 leaks a blocked head's quote *prefix* under a new key. Probe `blocked_prefix_mutant.py`, rc 0.
- **Binding, faithful.** The A03 test's state matches what `review_scope` would build. Checked by `blocked_shape_probe.py`, rc 0.
  - The head's status is set by hand at line 1136.
  - The bound `Input.status` is then taken from the head, so it is `blocked`.
  - The head is in `scope.heads` and in `scope.blocked`, and not in `evaluated`.
  - `review_scope` does the same: it appends blocked results to `heads`, and `blocked_ancestors` adds any input whose status is `blocked`. The `ReviewScope.__post_init__` invariants pass.
- **Content, not settle-shaped.** The blocked head in the test does not look like one the product could produce.
  - `execution.settle` (execution.py:428-438) builds a blocked head as `Module(..., status="blocked", limitations=issues)`, with no claims, facts or tables.
  - The test instead marks the full CP-1A head blocked, quotes included.
  - So the state is a superset of reachable states. The test guards the invariant more strictly than needed and asserts nothing false.
  - The same probe shows a settle-shaped blocked head is listed with `evaluated` false, `status` blocked and 0 claims, and `blocked_upstream == ["CP-1A"]`.
  - I do not count this as a defect (Info I-a below).
- **Assertions:**
  - no `quote` key at any depth;
  - no whole CP-1A claim or fact quote outside the T3.3 exemption;
  - the only finding is `blocked_upstream`, and the top level matches step 5.
- **Gap:** unlike the A02 test, it does not check quote prefixes. That gap is harmless: a blocked head is not evaluated, so it gets no Python finding detail, and X5 (the prefix variant) is killed anyway.

### F2 (Low): holds

Probe `suite_only_mutants.py`, rc 0, runs the whole suite alone and then each named test alone.

| Mutant | Suite alone | Named test alone |
|---|---|---|
| A01 | 2 failed | kind_on_ref: 2 failed (both parameters) |
| A04 | 2 failed | `test_view_keeps_the_head_citation_order` (line 1192): 2 failed |
| A05 | 4 failed | kind_on_ref: 2 failed; `test_view_over_an_empty_evaluated_set` (line 1182): 1 failed |
| A06 | 2 failed | `test_view_refuses_a_scope_with_issues` (line 1010): 2 failed, 2 passed (the two "Unreadable" parameters fail) |
| A09 / M14 | 1 failed | `-k interface` parameter: 1 failed |
| A11 | 1 failed | the several-citations test: 1 failed |
| X4 (top level uses `subject` only) | 4 failed | not run separately |

- **A06 issue strings:** all four are copied from the forms `review_scope` actually builds.
- **The `interface-fact:<sha256>` parameter exercises a `:`-bearing id through the `kind on <ref>` mark.** Probe `kind_on_ref_probe.py`, rc 0.
  - Before the cut, `context_block` emits exactly `figure_identity on interface-fact:07ac…1909` on CP-1 leverage, CP-2 T2.1.assessment and CP-2 T2.10.kf01.
  - The view keeps these whole.
  - A09's cut at `:` would give `figure_identity on interface-fact`.
  - The id is substituted by a JSON string replace across the heads. The old id `T4.10.total_leverage_reported.ltm_q4_2025` occurs only as that fact id and as `{ref|unit}` chips.
  - The stand-in parameter alone does not kill A09, as expected; the interface parameter does.
- **A08 is equivalent.** Probe `a08_float_probe.py`, rc 0.
  - There is no float anywhere in either case's `context_block`, and the function source has no `float(`.
  - A Decimal value would make `json.dumps` raise rather than emit NaN.

### Adversary probes
- **`adv_mutate_run.py`: rc 0.**
  - Baseline: suite 55 passed, adversary tests 7 passed.
  - The suite fails on A01–A07 and A09–A11.
  - A08 passes the suite (equivalent).
  - No non-equivalent mutant is left unkilled.
- **`leak_mutant_demo.py`: rc 1, the fixed outcome.**
  - The suite now fails on both A02 and A03 (rc 1 each).
  - The demo still observes the leak inside each mutated copy, which is what the demo is meant to show.

### New findings
None at High, Medium or Low.

- **Info I-a:** the A03 fixture (`tests/test_method_cp5.py:1136`) marks a full head blocked, which `execution.settle` never produces. The binding is faithful and the test is stricter than reachable states require. A settle-shaped case would be faithful but would kill no further mutant.
- **Info I-b:** `test_view_over_an_empty_evaluated_set` (line 1182) uses a scope bound to CP-0 only. Whether `current_inputs` can produce such a scope for CP-5 is not checked. The test only pins the view to `python_checks` over that scope.
- **Fixtures and catch-alls:** none of the new code has a catch-all. `_bound_status` (line 571) asserts membership in `InputStatus` before its `cast`, so nothing fails silently.

### Gates (target root, venv tools, mypy cache in scratch)

| Gate | Result | Exit code |
|---|---|---|
| `PYTHONPATH=src … pytest -q -p no:cacheprovider tests/test_method_cp5.py` | 55 passed | 0 |
| `ruff check` (cp5.py and the test) | | 0 |
| `ruff format --check` (both files) | | 0 |
| `MYPYPATH=src mypy --strict` (both files) | | 0 |

### Probes (this review)

| Probe | Exit code |
|---|---|
| `suite_only_mutants.py` | 0 |
| `kind_on_ref_probe.py` | 0 |
| `blocked_shape_probe.py` | 0 |
| `a08_float_probe.py` | 0 |
| `blocked_prefix_mutant.py` | 0 |
| `adv_mutate_run.log` (rerun of the adversary probe) | 0 |
| `leak_mutant_demo.log` (rerun of the adversary probe) | 1, as expected |

Not verified: a genuine CP-1 head (real `interface-fact:` ids that come from promotion rather than the string re-key, chip references, multi-citation narrative claims); `review_scope` over a real journal holding a blocked optional head; whether `current_inputs` can produce a CP-0-only scope for CP-5; which test killed X5 (only the suite's exit code was recorded); `view(historical, attempt)`; the LEAD items (choices 1–3, the CP-3 fact count, I1), which are out of scope.
