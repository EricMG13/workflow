# Shared defect-class test review (mx-precise)

**Verdict: REQUEST CHANGES** (one Medium finding). The spec and quality verdicts are below.

**Spec verdict: REQUEST CHANGES**

- **M1 (Medium): the `require_issue=False` escape hatch covers the whole call, not individual fields, so a module that accepts every value passes the gate.**
  - Where: `tests/defect_classes.py:738` and `:757`, used at `tests/test_defect_classes_shared.py:88` and `:123`.
  - Round 3 item 2 says an issue must be journaled for every free-text field. With the flag off, an accepted hostile value is never a failure on any path, and the wedge check is skipped for it.
  - The selfcheck shows this: `tests/test_defect_classes_selfcheck.py:509` asserts that the fully lax fake gives `[]`.
  - The comment at `shared.py:86` says "Citation fields are still refused", but nothing asserts it. A regression that accepted `"{}"` in a citation quote would pass both CP-0 and CP-1.
  - Probe `.../defect-classes-review/p3_require_issue_scope.py` (exit 0): with `require_issue=True`, CP-0 accepts 25 of its 54 paths and no citation path today. So a correct allowlist is cheap to write.
  - Fix: replace the boolean with an explicit set of verbatim paths (for example `objective`, `reporting_period`, `sources.*.entity`). Assert that every other path journals an issue. Get LEAD to rule on the verbatim list, because it departs from "an issue must be journaled".
- **L1 (Low): Q5 coverage is narrower than LEAD's probe.**
  - Where: `_schemas` at `tests/test_defect_classes_shared.py:28`.
  - It collects 9 schemas. The probe collected 19 or more, so 15 are left out:
    - 4 live `STEPS` schemas (CP-3, CP-4, CP-5, CP-6). `host.py:675` can return these today.
    - 11 unregistered `*Submission` classes (cp1c, cp1d, cp2a, cp2d, cp2g, cp2h, cp3c, cp3d, cp4c, cp8, cpdr).
  - The ruling says "over its SCHEMAS", and both groups join automatically once they are registered, so this is Low.
  - Probe `p1_schema_coverage.py` (exit 1) lists the 15 missing schemas. Probe `p4_hostile_on_uncovered.py` (exit 0) shows the 4 `STEPS` schemas raise only `ValueError` today.
- **L2 (Low): free text that is missing from the positive payload is never tested.**
  - Where: `free_text_paths` at `tests/defect_classes.py:677` and `:699`. It walks values, not the schema alone, so fields that are null, or in empty lists, in the positive payload are skipped.
  - CP-0 misses `gaps[].description`, `remediation` and the citation `quote`/`locator`, plus `consumers[].missing_source`.
  - CP-1 misses `events[].description`, `effect` and the citation `quote`/`locator`, plus `scopes[].limitations[]`.
  - This is the literal reading of "the positive payload's fields", so it is a scope question for LEAD. Probe `p2_free_text_gaps.py` (exit 1).

Answers to the checks:
1. **Copy of the set.** It is faithful. All 8 inputs and both per-field floods match the probe byte for byte: `json.dumps` escapes nothing in them, and the field selection is the same `_str_fields`. Nothing is weakened. The probe's exit rule (an acceptance is not a failure) is kept.
2. **`free_text_paths`.** It handles `$ref`, a single-item `allOf`, `anyOf`/`oneOf`, `Optional`, nested models, lists and `additionalProperties`. `RunText`, `Identifier` and `Hash` resolve correctly. Every excluded leaf is an id, hash, enum, const, date or currency. Free text with a pattern does not occur today. The only miss is L2.
3. **`model_text_failures`.**
   - The binding write comes first: `owner_workflow.py:902-903` writes before `_fill`, `_gate` or any parse. So every hostile submit runs past the write.
   - The wedge check is sound. Each case uses a `fresh()` run, the reads are repeated before each submit, and a raise propagates. I found no case of a false wedge or a missed wedge.
4. **Selfcheck.** It catches all five broken fakes: build raise, wedge raise, wedge refuse, no issue, accepted.
5. **Coverage.** See L1. The model-text check runs on CP-0 and CP-1 `source_context` only. CP-1A and CP-2 are deferred and the docstring says so.
6. **Suppressions.** `noqa` is 13 at both 386f53a and 8c5bf8b. The diff adds no `type: ignore`, `pragma` or bare/blanket `except`. `assert_hostile_refused` catches only `ValueError`. ruff check and format both exit 0.
7. **Runtime.** Both files took 54.75 s (249 passed, exit 0). The shared file was about 52 s, and CP-1 `source_context` alone took 42 s. That is under 60 s but close (Low). Adding CP-1A or CP-2 here would go over.

**Quality verdict: APPROVE, apart from M1.** Two Info items:
- The test name `test_hostile_failures_adds_the_per_field_floods` (`selfcheck.py:418`) still uses the old helper name.
- `test_hostile_set_is_the_probes` (`selfcheck.py:377`) checks only the keys and the length of `huge_int`, not the values.

The probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/defect-classes-review/` (`p1_schema_coverage.py`, `p2_free_text_gaps.py`, `p3_require_issue_scope.py`, `p4_hostile_on_uncovered.py`). Run them from the worktree with `PYTHONPATH=src uv run python <probe>`. My first `uv run` also created a `.venv` in the s2-defect-classes worktree. It is gitignored, and the tree is otherwise clean.

Not verified: mypy was not run. I did not run CP-1 `source_context` with `require_issue=True`. I did not check whether text accepted verbatim (for example CP-0 `objective`) later breaks a downstream build or render. I did not read the implementer's report file or the brief's 60 s clause directly. Timings come from one local run.
