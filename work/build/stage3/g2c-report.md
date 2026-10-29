G2 continuation: rev 3 is in the code and the fast tests, but no genuine owner run has passed through G2. None was run: the disk is full and the brief forbids it.

**Worktree:** `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a16e092a817c84c4a`
**Branch/tip:** `claude/s3-g2c` at `ce17c2f178c983f9fc0e795d4fd645085b02378b`. The four setup steps were done. The merges are d737d8f then 234dfae on top of c43b681, and the saved patch is committed on its own.
**Background processes:** none started.

**Commits (each ends with the Co-Authored-By line, except the two merge commits)**
- The earlier builder's patch, committed alone.
- `cp1-model` sections.
- Assigned blocks may hold figures.
- Test rule against the chart oracles.

**What changed for rev 3**
1. **`cp1-model` sections.** They are now `model-chart-strip`, `capital-structure`, `financials-credit-metrics`. A fast test reads the core `_spec_of` producers (blocks whose producers are CP-1 alone), so it does not rely on G2's own table. The pathway-order test was red before the fix and green after.
2. **Product figure rule.** I removed the "no chart or figures" refusal. A refused page still refuses any figure. `_expected_block_payload` is new and reproduces `render._report_payload` (state spelling, chart svg, gaps note). Without it, every figure block would fail the payload equality check, because the payload adds svg and `gaps_note`. A test compares it with the core payload on a real CR.1 page.
3. **Test-side comparator** (`assert_figures_equal_oracle`) reads the frozen oracles only, never the payload.
   - Oracles covered: S.1-S.4, S.5, RV.3a/b, CR.1, CR.2, DR.2, DR.3-5, DR.6.
   - Checked per figure: fig_id order, placement, kind, title, unit, series, marks (category, text, value, role), table twin (cell texts equal mark texts), and `∅ G#` gap marks. A gap mark must have a null value and a `G\d+` ref whose text is `∅ <ref>`. Every ref must appear as `data-ref` in the svg.
   - Oracle fact ids and coordinates must each resolve to exactly one fact of the module.
   - Every other assigned block must have `figures == []`, and a refused page must have none.
   - It is wired into `_check_scope_run` and both genuine `cp1-model` tests.
4. **Cache dropped.** I removed the earlier builder's `G2_RUNS_CACHE`. It was keyed only on a path and a `ready` marker, so it could hide a changed store.

**Review of the earlier code against the lease.** I read capture, outcome rules, staging, rename and verify. I found no lease violation. Minor: staging dirs come from `mkdtemp` (mode 0700), and one `except OSError: continue` in the ancestor guard is commented.

**Gates (all exit 0)**
- `ruff check` and `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict` on both files.
- G2 `-k fast`: 139 passed. That includes 65 new figure tests: 16 oracle-built pages, 28 perturbed pages that must fail, 10 real pages from the repo's chart drivers (CR.1, RV.3, DR.2, DR.3-5, CR.2 x3, DR.6 x2, S.5, S.1-S.4), and the unresolvable/ambiguous fact ref and oracle-pointer tests.
- `tests/test_chart_seam.py` and `tests/test_legal_render.py`: 133 passed.
- Suppressions: `noqa` 13 (limit 13), `type: ignore` 5 (limit 5).

**Deferred genuine commands.** They are heavy, so run them when space is free. `<py>` is `L/.venv/bin/python`.
- `cp1-model`: `PYTHONPATH=src:tests <py> -m pytest -q -p no:cacheprovider tests/test_owner_rendering.py -k genuine_cp1_model`. The earlier run took about 22 minutes.
- The other scopes: the same command with `-k genuine_deferred`. The earlier builder never ran these.
- Disk: the earlier cp1-model run took about 22 minutes and the gate needs room for genuine stores.

**Questions for Modules**
1. S.4's real producer title is "Maturity wall — principal at <date> (not a forecast)" and the oracle pins "Maturity wall". I compare it as a prefix.
2. The S.1-S.4 oracle names series by raw id. I compare the page's captions against a literal table that copies the report-view captions. Mark text and twin are not checked against the oracle, as R3.2 says.
3. DR.6 reasons are compared as oracle text plus an optional `(∅ G#, ...)` suffix, because the page appends the cited gaps.

Ledger: `agent=mx-feature fix-rounds=0 gates-first-pass=y` (the fast tests only; the genuine ones are deferred, so by the ledger rule this should read n/a).

Not verified: any genuine G1 run through G2, including every `cp1-model` and S1a test, the other scopes, equivalence with `render_financial_slice`, refusals, timing, forgery, read-only and determinism on a real store; the figure comparison on genuine owner-run payloads (only repo chart fixtures were used, including a typed-seam CP-1 fixture for S.1-S.4); amount_exact versus mark value scaling on real runs; the case-variant alias test on darwin; the "extra attempt" test (it may fail on `Execution.begin`); `model-chart-strip` being populated on a real restricted CP-1 run; the refused-outcome figure guard fires only through a `model_copy` bypass of the Block validator, so it is a backstop.
