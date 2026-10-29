# CP-5 fix round 1 report (tests only)

The suite alone now kills every mutant from the adversary review except A08, which is equivalent. No new test exposed a defect, so `cp5.py` is unchanged.

**Commit:** `81e8c0b test(cp5): kill the quote-leaking and construction mutants (review-adversary F1, F2)` on `claude/cp5-stage1`, on top of `4e2d687`. The lane was not merged. Only `tests/test_method_cp5.py` changed (+185/−10). Nothing outside the worktree was touched except my runner and logs in the scratchpad.

## New tests in `tests/test_method_cp5.py`
- **`_rescope`**: a helper that rebuilds a positive-case scope over modified heads, rebinding every input hash and status from the head itself.
- **`test_view_cuts_every_mark_of_a_claim_with_several_failing_citations`** (kills A02 and A11):
  - Every citation of the CP-1A claim with the most citations is made to fail, so there are at least two.
  - It asserts one `claim_citation` finding and one mark per citation.
  - It asserts the top level equals the lease's step-5 list, at full length (no de-duplication).
  - It asserts no quote and no quote prefix reaches the body.
- **`test_view_keeps_a_blocked_heads_quotes_out`** (kills A03):
  - CP-1A is blocked and bound, and is listed with `evaluated: false` and status `blocked`.
  - There is no `quote` key, and none of CP-1A's claim or fact quotes appear outside the T3.3 exemption.
  - The only finding is `blocked_upstream`; `blocked_upstream == ["CP-1A"]`.
- **`test_view_marks_a_flagged_reference_as_kind_on_ref`** (kills A01, A09/M14 and A05). It is parametrized over the stand-in id and a genuine-form id `interface-fact:<sha256>`, which contains a `:`.
  - The CP-2 copy of the leverage figure is made to disagree with CP-1.
  - Every claim that names the figure (including CP-1 leverage and CP-2 T2.10.kf01) is marked exactly `figure_identity on <id>` (the lease's step-4 mark).
  - The top level equals the step-5 list.
- **`test_view_over_an_empty_evaluated_set`** (kills A05 on the one finding that has no module): the top level equals the step-5 list, and the modules list is empty.
- **`test_view_keeps_the_head_citation_order`** (kills A04), run on both cases: each claim's citations equal the head's `#c1..#cn` refs with their source and locator, in order.
- **`test_view_refuses_a_scope_with_issues`** (kills A06): now parametrized over four `review_scope` issue forms, two "Stale…" and two "Unreadable upstream head…".
- A typing fix so `mypy --strict` also passes on the test file: `_bound_status` narrows to `InputStatus`, and a `_quotes(head)` helper was added.

## Mutants and the tests that kill them
| Mutant | Killed by |
|---|---|
| A01 (drops ` on <ref>`) | `test_view_marks_a_flagged_reference_as_kind_on_ref`, both parameters |
| A02 (cuts only the first mark) | `test_view_cuts_every_mark_of_a_claim_with_several_failing_citations` |
| A03 (strips quotes from evaluated heads only) | `test_view_keeps_a_blocked_heads_quotes_out` |
| A04 (citations reversed) | `test_view_keeps_the_head_citation_order` |
| A05 (top level uses modules[0] and subject) | the kind-on-ref, empty-set, blocked and several-citations tests (4 fail) |
| A06 (refuses only "Stale…" issues) | `test_view_refuses_a_scope_with_issues`, the two "Unreadable" parameters |
| A07 (`sort_keys`) | key-tree and compact-body tests |
| A09 = M14 (cut at `:`) | `test_view_marks_a_flagged_reference_as_kind_on_ref[interface-fact:…]` |
| A10 (known facts only) | `test_view_fact_projection` |
| A11 (top level de-duplicated) | `test_view_cuts_every_mark_of_a_claim_with_several_failing_citations` |
| A08 (`allow_nan` dropped) | not killed: equivalent, because the block holds no float |
| My M01–M21 and O01 | still all killed; M14 is now killed too |

## Probe and runner exit codes
- **My `cp5-stage1/mutate_run.py`: rc 0.**
  - It now includes A01–A07, A10 and A11, all expected killed by the suite alone, with no expected survivors.
  - It runs from full temporary copies with `PYTHONDONTWRITEBYTECODE=1`.
  - Baseline gives 55 passed. All 31 mutants are killed. Log: `cp5-stage1/fix1_mutate_run.log`.
- **`cp5-adversary/adv_mutate_run.py`: rc 0.**
  - Baseline passes the suite (55) and the adversary's tests (7).
  - The suite alone now fails on A01–A07 and A09–A11; only A08 passes, as expected.
  - Log: `cp5-stage1/fix1_adv_mutate_run.log`.
- **`cp5-adversary/leak_mutant_demo.py`: rc 1, which is the fixed outcome.**
  - Its docstring and exit logic return 0 only when the suite passes on a mutant and the leak is observed.
  - Now the suite fails on both A02 and A03 (1 failed each), even though the demo still sees the leak in the mutated copy.
  - Log: `cp5-stage1/fix1_leak_demo.log`.

All paths are under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/`.

## Gates (exit codes, both files)
| Gate | Exit code |
|---|---|
| `pytest tests/test_method_cp5.py` (55 passed in 2.27 s) | 0 |
| `ruff check` | 0 |
| `ruff format --check` | 0 (after one `ruff format`) |
| `MYPYPATH=src mypy --strict` on `cp5.py` and the test | 0 (after the typing fix for 4 test-file errors) |

`gates-first-pass=n`: the first run had a format diff and those 4 mypy errors in the test file.

Still for LEAD, unchanged in this round: controller choices 1–3, the CP-3 fact count (42/31 against the lease's 39/28), and I1 (`CP5Result` allows issues and a report together).

Not verified: the genuine CP-1 head (real `interface-fact:` ids and chip references in claim text, multi-citation narrative claims, its quotes, `python_checks` cost); the `interface-fact` case is built by re-keying the stand-in figure, not from a promotion; `view(historical, attempt)` and `review_scope` over a journal; blocked-head scopes as `review_scope` would build them (here the bound status is set by hand); Stage 2/4 sections as before.

agent=general-purpose(opus) fix-rounds=1 gates-first-pass=n
