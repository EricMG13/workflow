# CP-3D Stage 2 report (mx-feature)

CP-3D Stage 2: commit 094b1ef on claude/s2-cp3d. The fast gates are green. `submit`, `probe`, `RULES` inside a real workflow and the cp3d_runs/test_owner_cp3d code were never run, because the brief defers store runs to Stage 5.

Step 0: HEAD is e5e63af, the corrected tip. The diff to ce98319 is docs only.

**Files**
- `src/deploy_workflow/owners/cp3d.py`. A "Stage 2 connections" section is appended, plus a small `cited_refs` refactor. The earlier sections are unchanged apart from the blank-quote check and the `_whole_on_page` docstring.
- `src/deploy_workflow/owner_workflow.py`: import, `SUPPORTED_ANALYTICAL`, `_CORES`, `_QUALIFICATION`, `_PROBES`, `_ENTRY_VALIDATORS` and the `OWNER_SPECS` row. Every addition is appended at the end of its dict or tuple.
- `src/deploy_vii/bindings/cp3d.py` (new), `bindings/shipped.py` (`CP3D` placed after `CP3`, as the lease says), `report_view.py` (`_RELATIVE_VALUE` and its `_spec_of` loop entry).
- `src/deploy_vii/methods/cp3d.md` (new).
- `tests/test_connect_cp3d.py` (111 tests), `tests/cp3d_runs.py` and `tests/test_owner_cp3d.py` (the last two written, not run).
- `tests/test_host_h1.py`: one line. It assumed CP-3D had no registered core, so it now unregisters the real core there. The docstring is updated.

**Lease line to symbol**
- Public API: `STEP_IDS`, `SCHEMAS`, `QUALIFICATION`, `probe`, `submit`, `RULES`, `cp3d_upstream`, `validate_market_implied`, `market_implied`, `cp3d_module`, `cp3d_reader` -> `Cp3dHead`. `compose` already existed.
- The `OWNER_SPECS` row is exactly the lease line. `ENTRY_VALIDATOR` is `_validate_step`.
- `view` and `precheck` are absent, as the lease says. `_VIEWS` and `_PRECHECKS` have no CP-3D row.
- The H1 scope row already existed, and its sources are market and financial, matching the spec's `sources=True`. A test checks `_check_steps` and the pending `sources == _OWNER_SCOPES` guard.
- `_RELATIVE_VALUE` holds one block and can take CP-1C's `peer-positioning` row.
- Q10, Q6 and Q8 are applied: `_RELATIVE_VALUE` is created with its `_spec_of` entry, `cp3d_reader` stays in `owners/cp3d.py`, and there is no `MODULE_FAMILY` row.
- Deviations from the lease signatures:
  - `validate_market_implied` takes no `pack` argument.
  - `cp3d_upstream` takes an optional `pack` argument.
  - `upstream_of(pack=, cp0=)` is a new pure adapter underneath `cp3d_upstream`.

**Backlog rows**
- Done:
  - the rule W, item 8 and round 10 guard-limit notes in `methods/cp3d.md`, each pinned by a test (`GUARD_COSTS`);
  - the signed `value_text` Info (pin test);
  - the raw-vs-normalised Info (pin test);
  - the `_whole_on_page` docstring Low;
  - the blank quote row: the defect was present at all seven quote sites, and a single zero-width quote was accepted. A blank quote now gets `<path>: empty text` before the page check;
  - `listed_issues`/`clipped`: `RULES` reuses `unread_citation_issues` and the `UNBACKED_ABSENCE` constant, so it has no f-string site of its own.
- "Every module" rows that don't apply: B8 is CP-2H's, and there is no CP-3D precheck.
- Blocked, left untouched: the `amortisation_nonzero` re-pin and `STAGE2_REFUSAL_DELTA`.
- The `prose.is_blank` Cc/default-ignorables change is in LEAD's end batch, so I did not touch it.

**Test-first**
- The blank-quote tests failed first (7 failures), because the page-holds-it case was accepted or gave a different issue.
- The connect tests first failed at collection, with `_RELATIVE_VALUE` and the `cp3d` symbols missing. I then built the code and fixed test mistakes in the same session, so there is no per-test red record for every test.
- The signed-`value_text`, raw-vs-normalised and guard-limit tests are pins of existing behaviour and passed immediately.
- Fake stores that exist only in tests cover the `submit` flow and the entry validator.

**Gates**
- The pytest gate over `test_connect_cp3d`, `test_method_cp3d`, `test_owner_g1x`, `test_host_h1` and `test_defect_classes_selfcheck` ran: 1260 passed, exit 0.
- `ruff check` and `ruff format --check` on the changed files: exit 0. A pre-existing SIM102 at `report_view.py:293` fails `ruff check` at HEAD too (confirmed by running ruff on HEAD's copy); I left it.
- `mypy --strict` on the changed src files and the tests: exit 0.
- Mutants: 32, covering each adapter field, each registration row, the `SHIPPED_MAPS` position, the `_spec_of` loop entry, the spec row, the binding order and the blank check. All 32 were killed. The scripts are in `<S>/cp3d-s2/mutate.py`, where `<S>` is the scratchpad path from the brief.

**For LEAD**
- `docs/reuse/manifest.json`: I did not add the D12 record. The brief does not list it, and the record needs the merge sha.
- TOOL-CONTRACT matrix row: CP-3D `market_implied` has `search_pack` and `read_pages` over the market and financial sources, with no upstream view, no `read_inputs` and no `extract_statements`.
- D2 view row: none, since `inputs="none"`.
- `methodology.json`: no edit needed.
- `DELIVERY_SCOPES` row, copied word for word from lease :92: "G2 `owner_rendering.py` `DELIVERY_SCOPES` entry for `(relative_value, [CP-3D], synthetic)` (not on this branch)."
- Facts cite pages, not quotes. Each `Citation.quote` is the first submitted quote on that page (`page_quotes`); a cited page with no submitted quote raises. LEAD may want to confirm this reading.

**Deferred commands (for `work/build/deferred-runs.md`)**
- `PYTHONPATH=src "<venv>/bin/python" -m pytest -q -p no:cacheprovider tests/test_owner_cp3d.py`
- `cp3d_closed` drives all three cases through `tests/cp3d_runs.py`.
- Also run `test_owner_workflow.py`, `test_owner_s1a.py` and the render suites. These might be affected by the new CP-3D registration and `_RELATIVE_VALUE`.
- Not written in `test_owner_cp3d.py`: the `begin`-refused-on-blocked-CP-0 test, the stale-binding test and the probe-tamper test.

Not verified: the store runs. `submit`, `probe` and `RULES` inside a real `OwnerWorkflow` and the verifier, and the `tests/cp3d_runs.py` / `tests/test_owner_cp3d.py` code, were never executed, so they may carry runtime or mypy-clean-but-wrong errors. Settlement of the real candidate through `Execution.finish` with citations was also not executed. The render of the `market-against-fundamentals` block was not exercised. The `sources == _OWNER_SCOPES` guard is in the pending s2-g1x commit and is not in this tree; I only checked the agreement by test. The full suite and the PR size gate (about 1,870 lines added, over the 800 line cap, mostly tests and the core) were not run. D3 is OPEN, with a reader and a pin test and no completion claim.

agent=mx-feature fix-rounds=0 gates-first-pass=n (the first ruff run failed on SIM102 and F402; the first mypy run failed on test store types; test_host_h1 needed its one-line fix)
