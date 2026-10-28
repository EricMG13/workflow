# CP-4 Stage 2 completion report (mx-feature)

CP-4 Stage 2 completion: the five missing items are done. New commit b640f77 on claude/s2-cp4, on top of 67b46ed. The fast gates all exit 0. The store runs in `tests/test_owner_cp4.py` are written and type-checked but never run.

**Files (all under tests/)**
- `cp4_runs.py` (new): the run driver. It copies `s1a_runs.py`'s pattern and takes the pack and frozen figures from `test_method_cp4`. It exports `cp4_closed(case, root) -> (store, receipt, None)`, plus `promoted`, `drive_reads`, `metric_ref`, `bind_metric` and `drive_cp4`.
  - Cases are `positive`, `gap` and `gap_false_same_definition`. The last is refused by the semantic gate, then settles the gap pack's literal on the same ticket.
  - The oracle writes the false-same `readiness_review` and `cp1_source_context` as `= gap.<name>` references. `literal` resolves them and fails on an unknown reference. The fast test caught this on its first run.
  - The FIG binding follows the lease predicate through `s1a.figure_fact`: exactly one candidate, and it must be an offered 1.00x ref.
- `test_owner_cp4.py` (new, 22 tests): store runs, not run.
  - It checks receipt verification with the store unchanged, statuses, and the plan.
  - Tables, claims and limitations are compared against the oracle through Stage 1's `_check_table` over the real `upstream_of`.
  - D3 reads: the attempt binds the CP-0 and CP-1 head hashes, and the settled module carries them.
  - The semantic refusal is pinned: the dispositions are refused then valid, with the frozen issue string, null step hashes and the same binding.
  - A4 tool-use refusals: the unread page `legal-covenants page:1` is invalid and repaired, identity and financial reads are `not_permitted`, `extract_statements` is refused, submit without `read_inputs` is `not_permitted`, and an unresolved FIG is invalid.
  - D3 stays OPEN: there is no publication, and no head or attempt after CP-4.
- `test_connect_cp4.py` (extended to 59 tests):
  - The adapter test builds CP-0 and CP-1 `Module` objects from frozen oracle facts. `cp4_legal.upstream_of` then returns the Stage 1 upstream with only the two head hashes replaced by the real modules' hashes. There is one parametrized test per `Upstream` field, plus a test that the field list is complete.
  - `validate_bindings(view, SHIPPED_MAPS) == ()` over the oracle-equal tables, for positive and gap.
  - `_spec_of(block)` returns the `_COVENANT_REFINANCING` row for each of the six CP-4 blocks, with owner CP-4, producers `("CP-4",)` and kind dense.
  - The D3 pin: `plan(("CP-4",))` is `("CP-0","CP-1","CP-4")`, the manifest lists no consumers, and CP-3, CP-3C, CP-4C and CP-5 are not planned. It claims nothing about completion.
  - Driver parts: the cases, searches, `PACK_PLACEHOLDER` replacement, `FIG` binding, and the zero and two-candidate failures.

**Tests-first**
- The adapter, bindings, spec and D3 tests exercise code that already exists, so none could fail first. The mutants below stand in as the sensitivity proof.
- The driver defect (references like `= gap.readiness_review`) went red first, then green.

**Gates (all exit 0)**
- pytest over `test_connect_cp4`, `test_method_cp4`, `test_owner_g1x`, `test_host_h1` and `test_defect_classes_selfcheck`: 366 passed.
- `ruff check` and `ruff format --check` on the 5 changed files: clean.
- `mypy --strict` on the 5 changed files: clean.
- `pytest --collect-only` on `test_owner_cp4.py` collects 22 tests. The one fast test in it, `two_ltm_candidates`, also passes when run alone.

**Mutants** (`<S>/cp4-s2/mutants.py`, log `mutants.log`): 37 run, 37 killed, no survivors.
- The earlier 21 are unchanged.
- 9 new ones, one per adapter field: `cp0_sha256`, `cp1_sha256`, `cp1_status`, `authority`, `legal_sources`, `facilities`, `facts`, `rows`, `cp1_gaps`.
- 7 on bindings, spec and driver: a dropped binding, a moved block, a changed `_spec_of` producer, the search query, the pack-hash binding, reference resolution, and the corrected map.

**`methods/cp4.md`:** no note. The guard-limit rows apply to other modules, and the lease and backlog call for none.

**Deferred commands** (for `work/build/deferred-runs.md`; `PY` is the repo venv python)
```
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PY -o faulthandler_timeout=1800 -m pytest -q -p no:cacheprovider tests/test_owner_cp4.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PY -m pytest -q -p no:cacheprovider tests/test_owner_workflow.py tests/test_owner_s1a.py
```
The first needs two real CP-1 promotions, one per pack. The false-same case reuses the gap pack.

Not verified:
- Nothing in `test_owner_cp4.py` or the `cp4_runs.py` store functions has executed: `cp4_closed`, `promoted`, `drive_reads` and `drive_cp1`, including the legal-pack `cp1_source_context` reads and whether `read_pages` pages 1 to 3 in one call is accepted.
- Unconfirmed in those tests: that `Head.status` strings match the oracle's first words, that the CP-4 T4F.1 hash cells are `text` facts (the D3 test assumes so), that `settled_limitations` and `inherited_limitations` equal the module fields as written, and that an unresolved FIG is "invalid" and not "refused".
- Also unrun: `create` with CP-4 requested, `read_inputs` through the real `step_context` path, the precheck refusal audit and the verifier's gate replay.
- The stale-binding refusal (A4) and the tamper tests (A5) are not written.
- The A7 render (`build` over a verified receipt) is not covered. `validate_bindings` ran on a seeded view built from Stage 1 output, not on the store.
- `test_owner_workflow.py` and `test_owner_s1a.py` were not run on this tip.
- The jscpd and complexipy gates were not run. `cp4_runs.py::drive_cp1` duplicates `s1a_runs.drive_cp1`, because the shared one binds the snapshot literals.

agent=mx-feature fix-rounds=0 gates-first-pass=y
