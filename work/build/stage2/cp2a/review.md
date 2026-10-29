# CP-2A Stage 2 review (mx-adversary)

## CP-2A Stage 2 review (375f651 on claude/s2-cp2a, rebased on ab1093b)

**Verdict: REQUEST CHANGES.** One Medium finding in this change (M1) reopens the work. M2 is Medium but predates this change, so it goes to the owner or LEAD and does not reopen. The adapter, L6, `view` and the registrations hold up under probing.

The probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2a-s2-review/`. Run each as `run.sh <probe>`.

### Medium
**M1. `tests/test_owner_cp2a.py` (written now, run in Stage 5) leaves out most of the lease Acceptance section (:167-177).** Probe `p10_acceptance_coverage.py` exits 1.
- It calls `cp2a_closed` only for `positive` and `blocked`.
- There is no test for:
  - A2 gap;
  - A2b refused (one `RefusedBegin` for CP-1);
  - A2e (the CP-1 readiness row is `ready_with_limitations`);
  - A3 clones: `read_pages` refused, submit before read `not_permitted`, stale snapshot `stale_binding`;
  - A4 tamper: an edited read body, step output or `SettledHead` gives `identity_mismatch`.
- A1 checks only `status` and `amount_exact`. It does not check unit, `shown` or claims.
- The report's deferred list says the gap and refused cases are "driven via tests/cp2a_runs.py". The only deferred command, `pytest tests/test_owner_cp2a.py`, runs neither. Stage 5 would pass without exercising them.

**M2 (predating, for the owner or LEAD).** The adapter passes CP-1 operand facts to the core without checking unit, currency or scale. The core stamps every amount USD millions (cp2a.py:891-892, as the lease requires).
- `canonical_tables._dashboard` emits T4.10 cells in `metric.unit` and `metric.currency`, so a pack in THOUSANDS or EUR reaches the core.
- Probe `p8_units.py` (b): a LTM base in EUR thousands is offered, gives no issue, and composes T2B.2 ebitda `30 MILLIONS USD 1000000`.
- It cannot happen on the frozen USD-millions pack. A fail-closed offer rule would need a lease amendment.

### Low
- **L1. The adapter is not exactly the Stage 1 object.** Probe `p1_adapter_vs_stage1.py`:
  - Stage 1 `inputs_for` offers `(LTM, Q3, Q4)`. The adapter offers only the periods the head supports, in head order (`(LTM, Q3)`; gap case `(Q3, LTM)`).
  - `compute` is equal in all 4 cases.
  - `test_adapter_returns_the_stage_1_input_object` swaps in `offered_periods=(LTM, Q3)` instead of comparing with the Stage 1 object. Neither the test nor the report records the difference. L6 justifies it, but it should be written down.
- **L2. Test strength.** Probe `mutants.py`: 17 of 31 mutants killed and 14 survived. The survivors that break L6's "one derivation":
  - dropping `f.period == period` in `offered_bases`;
  - dropping the T4.10 filter;
  - building `_inputs.offered_periods` from every period.

  Each lets `validate` raise on a corrupt head. Probe `p3_l6_property.py` catches them; no committed test does. Also surviving:
  - `cp2a_upstream` with `bound=current`: no test drives the stale check through `cp2a_upstream`;
  - stale lines after content lines;
  - the raw `unit` in `view`;
  - the `bounded_issues` join in `compute`: this backlog row has no test.
- **L3. Tests break when later modules append rows.** Probe `p9_later_appenders.py`: the code takes appended rows, but the tests do not.
  - CP-2G's lease :52 insert fails `test_preset_inserts_the_two_blocks_after_the_gate` (`blocks[:4]`, `len == 13`).
  - CP-4C's lease :80 rows fail `test_spec_rows_are_the_lease_composition` (`recovery-by-class` must be "Unbound").
  - Any next `SHIPPED_MAPS` append fails `test_shipped_maps_end_with_cp2a` (it pins position [-1] and length 11).
- **L4. Forged facts.** Probe `p4_forged_and_stale.py` (c) and (d).
  - The public `validate_downside` and `downside_report` compose a caller-supplied `Upstream.cp1` with EBITDA ×10, with no issue (composed ebitda 300). CP-2's equivalent has `_provenance_issues`.
  - `cp2a_upstream` does not check the `module_id` of the CP-1 blob it loads.
  - Neither is reachable through submit, probe or view. The load is hash-checked: an edited blob is refused at (e), and a wrong blob fails closed as `Stale input CP-1`.

### Info
- **Unclipped lines.** The `base_period` line (:681) and the duplicate-label line (:667) still quote caller text without `clipped` (5047 and 5041 characters, probe `p6_unclipped_lines.py`). The journal stores 600. The backlog row covers only `RULES` and `_PRECHECKS`, so it is not required. Skipping the `:634` (now :659) line is justified, because `t.metric` is a `Literal`.
- **v17.** The Stage 1 `test_v17_stale_input_is_stage_2` placeholder still skips, with a stale "Stage 2" message. v17 really is covered: `test_stale_input_is_the_oracle_v17_issue` checks the exact oracle line, and the literal sha equals the test's derived one.
- **Predating.** `report_view.py:293` SIM102 is on ab1093b too.
- **Weak test.** `test_probe_refuses_a_head_that_does_not_rebuild` accepts `ValueError` and has a vacuous `assert name`.

### Checked and holding
- **Gates.** The gate set gives 568 passed, 1 skipped, exit 0. `ruff check` and `ruff format --check` exit 0 on the changed files. `mypy --strict` exits 0 on 8 files. The three render files that read `SHIPPED_MAPS` and `_spec_of` give 202 passed, exit 0.
- **Missing operands.** A missing operand settles as a gap through the store. An absent fact makes the period not offered and gives the v01 line, never 0 (`p2_missing_operand_gap.py`, exit 0).
- **L6 property.** Over 3000 random perturbations, a period is offered exactly when its label parses and `from_cp1` succeeds, and `validate` never raised. So no period that `from_cp1` would compose is silently dropped (`p3`, exit 0).
- **Stale inputs** (`p4`, exit 0):
  - a CP-1 change after begin gives "Ticket inputs have changed", with no step journaled;
  - the validator gives exactly one `Stale input CP-1` line;
  - a CP-0 that stops authorizing CP-2A gives `Stale inputs: …`.
- **Hostile payloads.** 13 hostile payloads through `submit` each become one invalid step, with no raise and lines ≤600 (`p7`, exit 0).
- **`view`.** The key tree matches the lease exactly in 4 cases. There is no quote, citation or record key, and no citation or source text. Decoys are absent. FIG unit and `shown` equal the oracle (`p5`, `p8` (a)).
- **Registrations.**
  - Rows are appended at the end. The spec equals the lease, and `sources=False` agrees with `_OWNER_SCOPES`. There is no `_PRECHECKS` row.
  - `_DISTRESSED`, the `_spec_of` loop and the `_PRESETS` insert after `distress-gate` match lease :32. `SHIPPED_MAPS` puts CP2A last.
  - `mutants_reg.py`: 15 of 16 killed. The survivor is the bindings `unit_class`, on which the lease is silent.
- **Q6.** No `cp2a_reader` is the correct reading: the lease Public API names none, and ruling Q6 says the CP-2A lease ships no reader.
- **Library boundary.** The change touches 9 files and none of `cases/`, `methodology.json` or TOOL-CONTRACT. The methods draft move is a git rename (R061). `methodology.json` already lists T2B.1-T2B.9.
- **Catch-alls.** The three new `except` clauses are documented and fail closed.

Not verified: anything against a genuine promoted CP-1 head (its real T4.10 labels, periods and units); `test_owner_cp2a.py` and the `cp2a_runs.py` driver, which were not run; `test_connected_render.py` and `test_financial_render.py`, which I stopped at about 90% because they are heavy-job runs; the receipt verifier end to end; the G2 FP05 rendering.
