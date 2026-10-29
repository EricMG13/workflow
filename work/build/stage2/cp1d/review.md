# CP-1D Stage 2 review (mx-adversary)

CP-1D Stage 2 review of 8a5d3d9 (claude/s2-cp1d, cut at 7a39384)

**Verdict: REQUEST CHANGES.** There are two Medium findings. The money path is sound: the adapter fails closed, nothing raises after validation, and no frozen value moves. The two Mediums are a view-versus-oracle spelling mismatch that breaks every deferred run, and an FP02 block title that disagrees with the frozen oracle.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-s2-review/`, which is "<R>/" below. They all run with `.venv/bin/python -B`, and `_h.py` there is the shared harness.

**Gate:** the brief's pytest command exits 0 (906 passed, 1 skipped). `ruff check`, `ruff format --check` and `mypy --strict` on the changed files also exit 0. The worktree is still clean.

## Medium

**M1. The view's `shown` disagrees with the oracle, so every deferred closed run fails at the CP-1D submit.**
- `owners/cp1d.py:2374` writes `"shown": spelled(fact)`. For an amount, `business_context.spelled` appends the unit, giving `30 US$ m`.
- The oracle `submissions.figures.adjusted_ebitda_ltm.spelled` is `30`.
- `tests/cp1d_runs.py:112` (`fig_bindings`) requires `(unit, shown) == (unit_token, spelled)`.
- Every case's literal references `adjusted_ebitda_ltm`. So `drive_cp1d` raises `RuntimeError("FIG adjusted_ebitda_ltm: unit/shown US$ m/30 US$ m")`.
- That breaks the `closed` fixture (24 tests), the unread-page, stale_binding and blocked forks, and G2's `cp1d_closed`.
- Probe `<R>/p11_driver_fig_bindings.py` (exit 1) runs the driver over the real `view` on a fast store, with CP-1 facts shaped as `model_interface` builds them (decimals None). Probe `<R>/p10_view_shown_vs_oracle.py` (exit 1) shows the fixture gives `30.00 US$ m` and real-shaped facts give `30 US$ m`.
- Fix: the lease key tree keeps `unit` and `shown` separate, so `shown` should be the cell spelling (`fact_spelling(fact, None)[2]`). Then run `fig_bindings` in a fast test over `_settled_store`. Brief §7 says a check that takes seconds is run, not deferred.

**M2. The FP02 `restated-leverage` title disagrees with the frozen oracle.**
- `report_view.py:1171` has `_Spec("Restated leverage", …)`.
- `expected.json cases.*.FP02.blocks.restated-leverage.title` is "Cash conversion and restated leverage" (builder :424).
- The T1D.6 binding label at `bindings/cp1d.py:35` is "Cash conversion and restated leverage", but the oracle tab label is "Cash conversion and leverage". The two strings look swapped.
- `test_connect_cp1d.py:259` pins the implementer's own value, so the fixture only matches itself. No test compares `_Spec` or tab labels with the oracle FP02 (lease A1: "FP02 equal expected").
- Probe `<R>/p5_fp02_render_vs_oracle.py` runs `report_view.build` over the fast module and exits 1 for all 3 cases.
- The other blocks, tabs and cells match the oracle. The only differences are gap cells, which differ in representation only.

## Low

- **L1. Ordinal window fail-open** (`cp1d.py:634-643`). The 32-character window is cut before the Cf/Mn/Me characters are skipped. So `2` followed by 31 or more combining marks, or 40 ZWSPs, and then `nd` reads as a basis of 2.
  - Probe `<R>/p4_ordinal_identifier_edges.py` exits 1 on 4 lines. The base fails open on 16 lines, so the remedy closed 12.
  - A mutant setting the window to 3 survives (p7).
  - Fix: skip the marks over the whole tail, then take the window.
- **L2. Test strength** (brief §7 "vary statuses … staleness"). Probe `<R>/p7_review_mutants.py` exits 1. These mutants survive:
  - the view's upstream `status` replaced by the constant "restricted";
  - `cp1d_upstream` using `current = attempt.inputs` instead of `current_inputs`;
  - the view's `known` filter removed.
- **L3. The deferred tamper test claims more than it proves** (`test_owner_cp1d.py:308-368`).
  - The SettledHead edits are refused before the probe (`owner_workflow.py:1856`).
  - The "probe itself" part calls `cp1d.probe` directly with an attempt that is not in the snapshot.
  - No edited step output is tested.
  - No test shows the verifier reaching `_PROBES["CP-1D"]` after the audit. CP-2A does this with a `monkeypatch.setitem` spy. I reasoned this through; it was not run.
- **L4. `OWNER_SPECS["CP-1D"]` is inserted before CP-MODEL** (`owner_workflow.py:247`). Brief §3 says rows are appended at the end, and every other Stage 2 branch appends after CP-MODEL. There is no runtime effect. Probe `<R>/p8_registration_order.py` exits 1.
- **L5. Suppressions rose.** `type: ignore` goes from 0 to 3, all in tests (`test_connect_cp1d.py:623,625`, `test_owner_cp1d.py:100`). The noqa count stays at 13, as required. Probe `<R>/p6_noqa_count.sh` exits 0, since it gates noqa only.
- **L6. CP-1 references are refused in assessment rationales.**
  - The Stage 1 core rejects a CP-1 reference in an assessment rationale as `Unresolved reference` (predates).
  - But the lease and the new `cp1_facts_note` admit CP-1 references in prose without restriction. Only `overall.rationale` binds them (`_checked`). The failure is closed, but a model following the note loses attempt 0.
  - Probe `<R>/p9_cp1_ref_in_assessment.py`.

## Info

- **I1.** The view's `inherited_limitations` is computed with own=() (`cp1d.py:2024`), so it lists the synthetic line. Settlement keeps that line in own (`test_connect_cp1d.py:818` against `:891-895`). The `context_block` docstring overstates this.
- **I2 (predates).** There is no USD check on the CP-1 operand currency. The bridge "USD; amounts in millions" line is never read, and CP-1's currency is stamped on the bridge facts. This is the CP-2A M2 class and is not reachable on the frozen pack.
- **I3.** The derived-citation rule has nothing to act on in real output: no composed calculated fact carries a citation (`<R>/p2_citation_rule.py` and `<R>/p2b_citation_two_quotes.py`, both exit 0). The first-quote and last-quote mutant kills rest on a hand-built cell. The code is correct.

## Confirmed, no finding

- **Adapter against CP-1.** Labels, period, units and the T4.17 row counting match `canonical_tables.py:779-815` and `model_interface.py:234-290`, and the manifest probes in three oracles agree.
- **Stale and swapped inputs.**
  - Submit and probe share `_checked` and `_inputs`.
  - Stale and swapped inputs are refused in the core, by G1 `stale_binding` and by the verifier's `current_inputs` check.
  - The view runs at the binding's historical snapshot.
- **Round 3 rules hold.**
  - Probe `<R>/p1_no_raise_after_validation.py` (exit 0): 24 edge and hostile payloads, and nothing raises after validation.
  - Probe `<R>/p3_facts_vs_oracle.py` (exit 0): every oracle fact field equals the oracle, citations included.
- **Round 5 item 12 residuals are still present**, as ruled. `a1_residual_bypass.py` exits 1 on the 6 ruled lines, and the method note does not yet record the `1.5-Q` reading.
- **Frozen values.** `p5_frozen_compare` on a base copy against the branch reports moved 0 and exits 0. `a7` exits 0.
- **Other registrations.** All other rows are appended, `shipped.py` has CP-1D last, and `_spec_of` and the preset insertion are as the lease says. `methodology.json`, `cases/` and `docs/` are untouched.

Not verified: no real CP-1 promotion or closed CP-1D run, and the deferred suite was not run. M1 is reproduced on a fast store, not a promoted head. The G1-level stale_binding and the verifier-level tamper tests were not run. FP02 was checked only through `report_view.build` over the fast module, not a run render. Not checked: the hostile-text set, GitNexus `detect_changes`, and mutants beyond the 7 in p7.
