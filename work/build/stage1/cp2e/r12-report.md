## CP-2E round 12: rule W, B10, and the bool() asymmetry

**Commit:** 3c883e5 on `worktree-agent-a219254fe68cc1c2d`, which I fast-forwarded to `claude/round12`. I confirmed HEAD = 128c3ca before starting. The commit changes two files: `src/deploy_workflow/owners/cp2e.py` and `tests/test_method_cp2e.py`.

### Each ruling with its test
I wrote every test first and saw it fail for its cause: 23 failures plus the 89 expected ones. All of them now pass.

- **Rule W in `_unsigned`.**
  - The pattern is now `(?<![0-9.])(?<!{minus})(?<!{minus} )<v>(?![0-9]|\.[0-9])`, with `minus = (?<![A-Za-z0-9])-`.
  - The accounting negative is now `(` or `( ` before the first digit, together with `)` or ` )` after the last.
  - The labelled reader and the B1 page check both go through `_once` → `_unsigned`, so they read W with no change of their own.
  - Tests:
    - the library W cases in `test_class_foreign_share_figure[w-*]` and `test_class_labelled_operand_figure[w-*]`;
    - the new `test_round12_w_labelled_operand`: `spread - 25` and `spread -\n25` are refused with `rate_exposure.spread: bps_text 25 does not occur in the quote`, and their twins `spread 25` and `spread\n25` validate;
    - the new `test_round12_w_spaced_parentheses`: `( 25)`, `(25 )`, `( 25 )`, `(\n25\n)` and `(25\n)` are refused. The library has no closing-space case, so this test is what kills that revert.
- **Bounds set.** `test_class_cases_cover_the_bounds` now lists `w-2024-2025-wrap` in both sets. 2025 is above the share bound and has four digits, which is off the operand shape.
- **B10.** `_Check.empty` now calls `blank.is_blank`. Test: `test_class_blank_text`, where all 16 fields now pass blank-5 to blank-8.
- **The `bool()` asymmetry (cp2e.py:715).**
  - A limitation now counts as stated only when `limitation is not None and not is_blank(limitation)`.
  - On a non-II assessment, `""`, `"  "` and the Cf values now all give only `assessments[0].limitation: empty text`.
  - On an II assessment, every blank value gives empty text plus `limitation is required for Insufficient Information and only for it`. That matches the confirmed Info item, and `""` behaves as before.
  - Tests: `test_class_blank_limitation_off_insufficient_information` and the new `..._on_insufficient_information`, both run over `dc.BLANK_VALUES`. The old test pinned the asymmetry; I replaced it.

I left the `fx.` path owner item at cp2e.py:757 as the dispatch notes say.

### Probes and mutants (under `<S>/cp2e-r12/`)
- **LEAD's `p_sign_breaks.py`:**
  - `p_sign_breaks_as_is.py` (only `LANE` changed to point at this worktree): **exit 1**. It fails only on fidelity (C) and on its "lane bypass must exist" checks (A), for CP-2E and CP-1D, because both now apply W. CP-1D already did on `claude/round12`.
  - `p_sign_breaks_w.py` compares the CP-2E and CP-1D readers with the reference under W: **exit 0**.
    - Every class case is refused, and the four controls are accepted.
    - Part D: 0 frozen readings move (CP-1D 4, CP-2E 15, CP-3D 15, CP-8 40), and the module and reference disagree on none.
    - Part E: 1759 plain/joined sign disagreements under round 10, 0 under W.
- **`p2_behaviours.py`, checks a1–a4:**
  - As-is: **exit 1**. a1 is still False. a2 (`were - 25 percent`), a3 (`were -\n25 percent`) and a4 (`-\n25 percent`) now read False, where they read True before W. c3 now gives one issue, from the bool() fix.
  - The copy `p2_behaviours_r12.py`, with those expectations updated: **exit 0**. b1, c1, c2, d1 and d2 are unchanged.
- **`mutants.py`** ran in a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`: **exit 0**. The unmutated copy passes, and all 6 mutants are killed (each run exits 1):
  - W minus space;
  - W parenthesis space, both sides;
  - opening space only;
  - closing space only;
  - the B10 Cf test, reverted to `not text.strip()`;
  - the `bool()` revert.

### Gates (all exit 0)
- `pytest tests/test_method_cp2e.py tests/test_defect_classes_selfcheck.py`: 679 passed.
- `ruff check`, `ruff format --check`, and `MYPYPATH=src mypy --strict` on both changed files.
- I also ran `tests/test_host_h1.py`, the only other test that references cp2e: 37 passed.

### Owner item (Low, predates this round, not fixed)
The label check `{label}\s+{v}(?![0-9])` (cp2e.py, `_Check.labelled`) accepts `spread 25.5` as labelling `25` when another whole `25` is the quote's one occurrence. The quote `"The margin is spread 25.5 basis points and the fee is 25 basis points."` with `bps_text` 25 validates with no issues. Probe: `<S>/cp2e-r12/p_label_decimal.py`; exit 0 means the gap is present.

Not verified: the full suite and the other modules' tests did not run. The guard-limit note for `methods/cp2e.md` is the controller's job and was not written. I did not run GitNexus `impact`/`detect_changes`; I have no MCP access as implementer. Only the two LEAD/reviewer probes named were rerun, not the other round 12 probes.

Ledger: `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n`. The first `ruff format --check` exited 1 on two lines; the formatter fixed them and nothing else changed.

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`
