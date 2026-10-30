**Verdict: APPROVE.** I found no High, Medium or Low findings.

The change under review is `claude/s5-g2-gaps` `e37b73e..715f5a4`: 3 commits, `tests/test_owner_rendering.py` only, +1047/−4.

**Spec check** (frozen spec plus Revision 1, rulings 46 and 47)
- **`_page_cites`** (`tests/test_owner_rendering.py:2116-2146`): there is no fallback. It requires an entry when the status is not known, when the list `cites` is non-empty, or when a `calculation_id` is set. It then asserts exactly 1 entry, or 0 when none is required. It keeps only C/S refs, in index order, without de-duplication. The strict-parse G# comment is present.
- **cp4 limitations** (`:2358-2366`, `:2391`): these follow the oracle rule word for word. The order is the CP-0 literal, then `cp1.limitations`, then `cp1.inherited_limitations`; entries are de-duplicated and settled ones removed, and the page equals settled + inherited. `cp1` is `heads["CP-1"]` from `Execution(store).head_module` (`:3338-3341`, `:3366`), as ruling 46.4 requires.
- **Rails** (`:2467-2491`): the order is own, then SYNTH, then inherited. When the run is synthetic, the test asserts the oracle's inherited list contains SYNTH. Every rail table must be a table on the module's payload: cp3d `T3E.8/9/7`, cp8 `T7.1-8`, cp4 `:2389-2390`.
- **Cites on every oracle table:** cp3d `:2278`, cp4 `:2392`, cp8 `:2463`, s1a `:3361`. Each asserts at least 1 non-empty cite checked.
- **cp3d register rule** (`:2230-2280`), cp4 sections and literals with their closed prose mapping (`:2298-2355`), and cp8 gap and known lines (`:2410-2464`): all match the spec. The cp8 checks cover the label run `"<column>:"`, browser white-space collapse, pen if and only if `analyst_judgment`, and the K chip's `Calculation`. The `gap_false_same_definition` check reads only `rows[0]`, which is correct because T4.9 has one row in the oracle.
- **Wiring** (`:3409-3417`): `_assert_secondary_pointers` runs only for complete outcomes. All four scopes are in `ORACLE_POINTERS`, so the guard cannot skip any of them. s1a gets the cites check, cp3d gets tables and rails, cp4 gets the pointers, and cp8 gets lines and rails. Refused and blocked outcomes do not reach it.
- **No vacuous pass on a genuine page:** every assert requires at least 1 item checked, or a list length that must match the oracle (registers `:2275`, lines `:2457`, rails `assert rails` `:2478`, cites ≥ 1). Missing entries raise loudly through `KeyError` or the single-item unpacking `(x,) = ...`.

**Builder decisions**
- s1a `calculations` is built from every head in the store, keyed by `(module_id, fact_id)` (`:3355-3359`). It is a superset, which is fine.
- `_assert_rejected` (`:2612-2616`) catches only `AssertionError` and asserts its list of perturbed pages is non-empty.
- The test-only CP-1 head and `_CP1_ONLY_LIMITATION` appear only in `_cp4_page` and the fast test (`:2857`, `:2881`, `:2933`). The genuine path takes the store head. The `SimpleNamespace` stand-ins exist only in the fast fixtures, which call the product's own `inherited_limitations`.

**Weakening probe** (on the archive copy): `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g2-gaps-build-review/probe_weaken_rules.py` exits 0. I weakened four rules one at a time, and in each case the fast test failed (pytest exit 1):

| Rule weakened | Test that failed |
|---|---|
| `_page_cites` entry count changed to `<= 1` | cp3d tables test, 3 failed |
| SYNTH taken out of the middle of the rails order | cp8 rails test, 2 failed |
| `cp1.inherited_limitations` dropped from the cp4 rule | cp4 test, 3 failed |
| cp8 pen check removed | cp8 lines test, 2 failed |

**Other gates I ran on the copy**
- The new fast subset (`-k "fast and (cp3d or cp4 or cp8 or cites or rails)"`): 56 passed. I printed the exit code after a pipe, so it shows `tail`'s status, not pytest's.
- `ruff check`: exit 0. `ruff format --check`: exit 0.
- `noqa` / `type: ignore` count: 0 before and after the change.

**Quality verdict:** I found no stub or fake value on the genuine path, and no catch-all that hides a failure.

**Info**
- **Diff size:** the change is +1047/−4 lines, which is over the global 800-line PR cap. My contract sets no ceiling for this review, and the project amendments say nothing about Deploy Workflow, so I am reporting it rather than counting it as a finding.
- **Genuine timing:** the builder reports the genuine `cp3d-fp03-market-positive` run took 1.76 s, against the brief's 11–26 minutes. It is worth confirming in your genuine run that this was a real run and not a cached one.

I deleted the copy; only the probe script remains under `<S>/g2-gaps-build-review/`. No worktree was written.

Not verified: the genuine runs (the controller is running them), `mypy --strict`, the full `-k fast` suite, the genuine store's CP-1 head, settle-built limitations on genuine cp3d/cp8 pages, real K# passports on genuine cp8 pages, and the build brief's own constraints (not a declared input).
