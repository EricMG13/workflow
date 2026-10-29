# Stage 2 module brief: connect one module (stage contract)

The plan is `docs/superpowers/plans/2026-10-28-verified-module-builds.md` "Stage 2". The analysis is `work/build/stage2/plan-draft.md`, sections 1, 3 and 4. The controller decisions and the questions open with LEAD are in `work/build/stage2/questions.md`. Routing: `mx-feature` builds and does the fix rounds. `mx-adversary` reviews the store adapter, the reader and the D3 test. `mx-precise` reviews the rest.

## Inputs
| Item | File | Why |
|---|---|---|
| Lane tip | named in your dispatch | Step 0 |
| Lease | `docs/<CP>-OWNER-LEASE.md`: the D12, Public API, D3 and D7 sections, and the amended headers | what you build |
| Protocol | `docs/G1X-OWNER-CORE-PROTOCOL.md` §2-§6 | the plug-in parts, and the §6 `json_object` parse and `listed_issues` rules |
| Oracle | `cases/<slug>-owner/{manifest,submissions,expected}.json`, `cases/PINS.json` | the expected values (never edit `cases/`) |
| Core | `src/deploy_workflow/owners/<cp>.py` and its Stage 1 input type | what the adapter fills |
| Patterns | `owners/cp1a.py:17-60`, `owners/cp2.py:13-34`, `src/deploy_vii/bindings/cp4.py:27-76`, `tests/s1a_runs.py:27-212`, `tests/test_owner_g1x.py:333-341` | the shape to copy |
| Backlog | `work/build/stage2-backlog.md`: "Every module" plus your module's rows | your first task |
| Analysis | `work/build/stage2/plan-draft.md` §1 (checklist), §4 (your row) | the file and symbol for each part |

## Process
0. **Step 0.** In your worktree, the tree is clean and HEAD equals the lane tip named in your dispatch. If either fails, stop.
1. **Backlog first.** Apply every row for your module, test-first:
   - the guard-limit notes in `src/deploy_vii/methods/<cp>.md`, written with the code;
   - the blank support/citation quote inventory and fix, if your module takes citations;
   - `listed_issues`/`clipped` for every caller-quoting issue line in `RULES`/`precheck`;
   - your per-module rows.

   A row that waits on a LEAD re-pin is reported as blocked. Do not work around it.
2. **Test-first, part by part.** Write each test and watch it fail for the right cause before you write the code.
   - Plug-in parts (§2).
   - The store adapter (settled head → the existing Stage 1 input object). Use the one adapter in `submit`, `probe` and `view`.
   - The `owner_workflow.py` registrations.
   - `src/deploy_vii/bindings/<cp>.py`.
   - The `shipped.py` and `_Spec` rows.
   - The reader your lease's Public API names, where it puts it (rulings stage2 Q6). Consumer Stage 1 types stay; a consumer adapter calls the producer's reader and selects into its own type.
   - The run driver `tests/<cp>_runs.py`.
   - The D3 test.
3. **Registrations are append-only.** Add your rows at the end of each dict or tuple, and never reorder existing rows. `SHIPPED_MAPS` takes the lease's stated position. If the lease names your module as the creator of a `report_view.py` composition, create it.
4. **No stub, fake value or catch-all in `src`.** A fake core or session is allowed only in tests. A missing operand settles as a gap, never 0.
5. **Library boundary.**
   - `src/deploy_vii` changes only by the lease's D12 one-liners, `bindings/<cp>.py` and `methods/<cp>.md`.
   - Never edit `methodology.json`, `docs/TOOL-CONTRACT.md`, `cases/` or any engine. Report any edit they need as text for LEAD.
   - Copy your lease's `DeliveryScope` row word for word into the report, or write "none in lease" (rulings stage2 Q1). Never write a new row.
   - No `MODULE_FAMILY` row in Stage 2 (Q8).
   - A composition creator (Q10) also appends it to the `_spec_of` loop (`report_view.py:1198`).
6. **Fast tests** (each file under about 60 s), in a new `tests/test_connect_<cp>.py`:
   - `tests/test_method_<cp>.py` stays green;
   - the registration rows equal the lease, and `_check_steps(m, OWNER_SPECS[m])` passes;
   - `SCHEMAS` round-trips and gives the tail digest on the oracle literals;
   - `RULES`/`precheck` reproduce the oracle refusals;
   - the adapter over `Module` objects built from frozen oracle facts returns exactly the Stage 1 test's input object;
   - `view` matches the `view_tree_draft` keys and holds no quote strings;
   - `validate_bindings` over the expected tables returns `()`, and `_spec_of(block)` returns the row;
   - the reader exposes what the lease pins;
   - the shared hostile-text set in `tests/defect_classes.py` over your `SCHEMAS`, once it lands (rulings stage2 Q5);
   - `tests/test_owner_g1x.py` and `tests/test_host_h1.py` stay green.
7. **Deferred to Stage 5** (write these, do not run them). Write a test for **every** lease acceptance item that needs a store run: tamper at verifier level (audit and pre-`_PROBES` checks pass, then `probe` raises), stale_binding, submit before read_inputs, non-pack tools, the blocked case with receipt and status-only reader, store bytes unchanged, and the D3 reader call on the closed head. A fast one (seconds) is run, not deferred. Fixtures vary statuses, as_of and staleness so a constant equal to the oracle cannot pass (CP-DR review M1/L1). The list: store runs `tests/test_owner_<cp>.py`, `tests/<cp>_runs.py` runs, the D3 run assertions, receipts, promotion, `test_owner_workflow.py`, `test_owner_s1a.py`, the source suites and the render runs. List the exact commands in your report for `work/build/deferred-runs.md`.

## Gates (all exit 0)
- `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_connect_<cp>.py tests/test_method_<cp>.py tests/test_owner_g1x.py tests/test_host_h1.py tests/test_defect_classes_selfcheck.py`
- `ruff check` and `ruff format --check` on the changed files
- `MYPYPATH=src mypy --strict` on the changed `src` files and tests
- Mutants (from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`): one per adapter field and per registration row; each must be killed. Put the scripts under `<S>/<cp>-s2/`.

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`

## Outputs (report as text, at most about 1.5k tokens)
- The commit SHA and the files, with each lease line mapped to its symbol.
- Each backlog row, marked done or blocked.
- The test-first evidence, gate exit codes and mutant results.
- The text for LEAD (`methodology.json`, TOOL-CONTRACT, D2 view row) and the lease's `DeliveryScope` row copied word for word (or "none in lease").
- The deferred commands.
- `Not verified:`
- The ledger line `agent=mx-feature fix-rounds=0 gates-first-pass=<y|n|n/a>`.

Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Rulings that bind every module (Stage 2 round 3, lane cherry-pick of 8c8f557)
- **Citations:** a sourced fact quotes its own field; a derived fact gets one Citation per page quoting the first of its own input quotes on that page, in input order; never invent a quote. Kill both first-quote and last-quote mutants. State the derived rule in `methods/<cp>.md`.
- **Model text:** the validator checks each model-text field with the type the step later builds (`RunText` through a `TypeAdapter` built once), journaling `<path>: <msg>` with `include_input=False`, bounded by `listed_issues`/`clipped`. Nothing may raise after the binding write. The shared class test in `tests/defect_classes.py` runs over your positive payload.
- **Synthetic limitation:** own = oracle list then "Synthetic case; not real issuer qualification", deduplicated; inherited = `inherited_limitations`' output. Readers return the settled own list and say so. Pin with a head built by `settle`.
- **Aliases** canonicalise (no create refusal); receipts and MODULES.csv count no alias completion.
- **Source quotes (user, AGENTS.md "Source quotes", 8a8de7e):**
  - **Quote reading is frozen** in CP-1D, CP-3D, CP-8 and CP-2E. A new edge case fails closed and is recorded as a guard limit in `methods/<cp>.md`. No new reading rule is written unless a frozen case needs it.
  - **Not-yet-connected modules** (CP-1C, CP-2G, CP-2H, CP-3C, CP-4C, CP-OS and later) never read a figure from a model quote. A figure comes from one of:
    - an upstream fact;
    - a source table or row that Python parses from the pack page;
    - a Python-addressed figure id.
  - **Their citations** only check that the quote occurs on the page, plus the blank-quote refusal. Raise any oracle conflict in `questions.md`; never build around it.
