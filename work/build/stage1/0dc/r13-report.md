Commit f316a20 on claude/r13-0dc (HEAD was 67df6a1, worktree clean at start). The one gate failure is the known cp3c pin; the method suite also has 210 other failures, which are on the base too (details under Gates).

**Tasks**
- **M1:** `_gate` in `src/deploy_workflow/owner_workflow.py` now calls `bounded_issues(tuple(precheck(frozen, binding, stored)))`. `bounded_issues` was already imported there.
- **M2:** The `_unbounded_step_issues` docstring now says "before the journal's bound (rule issues arrive capped, 0d-c)". I re-wrapped the docstring to stay within the line limit.
- **M-R1:** `test_precheck_gate_issues_are_bounded_and_replayed` is added. The gate returns 500 lines of 1,000 characters on `GATE_MARK`.
  - **Assertions:** the refusal holds 21 lines. The last line matches `\d+ further issues not listed`. Every line is ≤ 600 characters. The refused record is ≤ 64 KiB (`model_dump_json`). `_verdict == "accepted"`.
  - **Helper change:** `_refused_then_sealed` hard-coded `[GATE_ISSUE]`. I gave it a default parameter `issues=(GATE_ISSUE,)`, so existing callers are unchanged.
  - **Red without task 1:** it failed at the helper's refusal assertion, because the stored refusal held 500 unbounded lines.
- **B10:** `src/deploy_workflow/owners/blank.py` is now `from deploy_vii.prose import is_blank` plus `__all__`. The `unicodedata` import is gone. `tests/test_owner_blank.py` passes unchanged.

**Task 5 (read-only)**
- **No sites in scope today.** No file in `src/deploy_workflow/owners/*.py` defines `RULES` or registers a `_PRECHECKS` gate. `grep` finds only docstrings that say they come in later stages (cp2h:20, cp3d:10, cp8:7, cpdr:6). No core uses `listed_issues` or `clipped`.
- **Sites that will matter once those seams are wired.** These caller-quoting issue lines are built by f-string, not through `listed_issues`/`clipped`:
  - cp1c:1357 (unknown peer name), cp1c:1370 and cp1c:1372 (`a.peer`).
  - cp2a:620 (`sc.name`), cp2a:634 (`t.metric`), and the `f"{path}: {issue}"` lines from `prose.issues` at cp2a:593.
  - cp2g:716 (`prose.issues`), cp2g:771, cp2g:773 and cp2g:780 (`bm.break_id`), cp2g:785 (`bm.metric` and `bm.break_id`), cp2g:820 (`sub.downside.scenario`).
  - cp2h:324 (agency and rating), cp2h:354 (metric), cp2h:1482 (`prose.issues`), cp2h:1515 and cp2h:1517 (`v.agency`), cp2h:1524 (`citation_issues` lines).
  - cp3c:572 (flag value), cp3c:804 (flag), cp3c:1671, cp3c:1674 and cp3c:1679 (`fact_id`), cp3c:1689 (`claim_id` plus a joined list).
  - cp1d:105, cp1d:107, cp1d:111, cp1d:122 and cp1d:129 (`self.figure`), cp1d:638 and cp1d:645 (`item.label`), cp1d:872 (`source.source_id`).
  - cpdr:126 and cpdr:137 (`gap_id`), cpdr:155 and cpdr:161 (`fact_id`), cpdr:231 (`gap.gap_id`).
  - The cp1c, cp2d, cp1d, cp2a and cp2h entry validators also join their issues with `"; ".join(issues)`.
- **Not read:** cp2d, cp2e, cp3d, cp4, cp4c, cp5, cp8 and cpl10 only matched on my grep patterns, and I did not read them line by line.

**Mutant:** in a `git archive HEAD` copy, I reverted task 1. The new test failed there with exit code 1, so the test kills the mutant. The script is `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/0dc-r13/mutant.sh`.

**Gates**
- The five-file pytest set (`test_owner_g1x`, `test_owner_blank`, `test_host_h1`, `test_rule_issue_bounds`, `test_engine_blank_text`) exited 0, with 115 passed.
- `ruff check` exited 0.
- `ruff format --check` exited 0.
- `MYPYPATH=src mypy --strict` exited 0 on the three changed files.
- `tests/test_method_*.py` exited non-zero: 211 failed, 4279 passed. A run on a clean `git archive HEAD` copy gives the same 211 failures, so none of them come from this change. The 211 are:
  - `test_method_cp2e.py`: 89 (`test_class_blank_text` 68, `test_class_foreign_share_figure` 10, `test_class_labelled_operand_figure` 10, `test_class_cases_cover_the_bounds` 1).
  - `test_method_cp8.py`: 121 (`test_r11_blank_text_gets_the_pinned_frame` 116, `test_r11_shared_quote_cases` 5).
  - `test_method_cp3c.py::test_oracle_files_match_the_lease_pins`: 1, the known LEAD pin.
- The cp2e and cp8 failures are quote and blank-text cases. I did not investigate them. Route them to LEAD.

Not verified: replay of a bounded refusal through any real owner core, since none registers a gate; the cp2e and cp8 method failures (they predate this change); mutation testing of `blank.py`; the full test suite; task 5 beyond grep-level reading.

agent=mx-feature fix-rounds=0 gates-first-pass=n