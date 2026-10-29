# CP-L10 Stage 2 review (mx-adversary)

**CP-L10 Stage 2 review (adversary + precise), branch claude/s2-cpl10 at 6e7f5b3 on lane 8b46132**

**Verdict: REQUEST CHANGES.** There are three Medium findings. The product logic held under every probe I ran. The defects are in the view's text form, the run driver and the deferred tests.

I reran the gates. The five-file set passed 498 with exit 0. `ruff check`, `ruff format --check` and `mypy --strict` on the 7 changed files all exit 0. The worktree is untouched.

### Medium

**M1. On genuine CP-0/CP-1 heads, the `read_inputs` view does not equal the frozen oracle.**
- `context_block` writes `amount_exact` as `format(amount, "f")`. A real CP-1 stores `17.50`, `20.00`, `47.50`, `50.00` and `30.00`, but `expected.cases.positive.view_topics` pins `17.5`, `20`, `47.5`, `50` and `30`.
- 8 leaves differ: cash Q2/Q4, total_debt Q2/Q4 and net_debt Q1–Q4. The values are equal as decimals, and `shown` and `pair_screens` match.
- The lease says D2's `topics` tree equals `view_topics`, and that `amount_exact` is "CP-1's canonical exact decimal".
- The fast test passes only because its CP-1 facts are built from the oracle strings.
- Fix: write the canonical text, for example `format(amount.normalize(), "f")`, or ask LEAD to rule on the oracle.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpl10-s2-review/p7_view_vs_oracle_genuine.py` (exit 1). It needs P5d's store.

**M2. `tests/cpl10_runs.py` cannot run, so `cpl10_closed` (which G2 imports) and both tests in `test_owner_cpl10.py` fail at the fixture.** There are two defects in `readiness_literal`:
- **(a)** The `fact_selection_rule.columns` rows hold `label` and `period`, so `q["column"]` raises `KeyError: 'column'`.
- **(b)** Even keyed on `label`, the readiness read spells a kpi period `Q1 25`, not the T4.10 column label. The driver then raises `RuntimeError: no kpi evidence for ebitda, quarter 1`.

With both worked around in memory (period `Q<N> 25`), the run completes:
- CP-1 promotes in 80 s.
- The positive and limited runs settle all three heads restricted.
- Their receipts and the blocked walk's receipt verify, and verification leaves the store bytes unchanged.
- The reader's counts, materiality and rank equal the oracle.
- Submit before `read_inputs` gives `not_permitted`, and `invoke` is refused `not_permitted`.

Your question 1.4: the key+period binding is not a fail-open. It fails loudly, and with the right label it picks exactly the records the lease's `observation_ids` rule picks (`driver == lease rule: True`). The `inputs_sha256` try/except always takes the fallback, because the read body is line text, not JSON. The product then pre-fills and checks the hash, so this is dead code, not a fail-open.

Probes:
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpl10-s2-review/p5_closed_run.py` (exit 1, the KeyError)
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpl10-s2-review/p5b_closed_run_patched.py` (exit 1, the RuntimeError)
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpl10-s2-review/p5c_readiness_rows.py` (exit 0, dumps the kpi rows)
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpl10-s2-review/p5d_closed_run_short_labels.py` (about 13 min). It exits 1 only on M1 and on my own TL10.1 marker-template comparisons, which are probe artifacts: the run-bound cells are correct.

**M3. Brief §7 store tests are missing (same as CP-DR M1).** `test_owner_cpl10.py` has 2 tests. These are not written:
- the limited case;
- the tamper at verifier level (`_verify_audit` and every check before `_PROBES` pass, then `cpl10.probe` raises). The fast test only subclasses `head_module` for `probe`;
- `stale_binding`;
- submit before `read_inputs`;
- `invoke` refused `not_permitted`, with exactly one ok read and zero pack calls;
- the blocked walk through `OwnerWorkflow`, with a receipt;
- the frozen CP-1-missing `RefusedBegin`;
- the blocked-CP-1 `RefusedBegin`;
- "store bytes unchanged";
- acceptance 1 cell for cell: inputs hash-equal to the heads, copied cells including `calculation_id`, the TL10.1 run-bound cells, claims and citations, `validate_tables`. Today only table ids and limitations are checked;
- the render states (acceptance 6).

### Low

**L1. Test strength.** I ran 19 mutants of my own.
- 6 survived and are not equivalent:
  - the adapter's `issuer_name` and `as_of` hard-coded to the oracle run;
  - `cp1_status_word` hard-coded to "With limitations". No fixture has an accepted CP-1, which reads "Pass" (P2 d);
  - the reader's status, counts and rank hard-coded to the positive oracle, which is the only head the reader is tested on.
- Equivalent survivors: the synthetic line in a public run, the quantize context, raw-text validation, disposition taken from materiality, and a current-head read (staleness cannot reach the adapter).
- A latin-1 decode of the bytes input also survives, but the host never passes bytes.
- Script: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpl10-s2-review/p9_mutants.py` (exit 1, output in `p9_mutants.out`).

**L2. `cpl10_reader` raises on a blocked head** (`CP-L10 head lacks TL10.2.ebitda.materiality`). So brief §7's "status-only reader" for the blocked case cannot be written. CP-DR returns status only. The lease's D3 is silent, so the controller or LEAD should decide.

**L3. The catch in `_validate_step` is wider than its docstring.** `except ValueError` also catches store-integrity failures. A hash-mismatched CP-1 blob raises `ValueError("Execution blob … hash mismatch")`, which a direct submit journals as an analyst issue, using up an attempt. This fails closed (no head, and the probe refuses), but the docstring covers only "cannot bind". Narrow the catch to the bind errors.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpl10-s2-review/p2_adapter_edges.py` (exit 0; cases e and f).

**L4. The `docs/reuse/manifest.json` record names the pre-rebase commit.** `project_commit` is 3b3ad2b, which is not an ancestor of 6e7f5b3 (`merge-base --is-ancestor` exits 1). The code commit is now 6b679ca. Both hashes in the record are correct: prior 4ef3f9ff is the base and 2be6922a is the tip. The report also cites the pre-rebase SHAs.

### Answers to your checks
- **Unbindable CP-1 (a missing T4.10 label): consistent and fail-closed.** `view` raises `identity_mismatch` (the cause is the unbound operand). A direct submit settles invalid attempt 0 with `CP-L10: unbound CP-1 operand: … (0 matches)`, and the entry-validator replay gives the same issue. Through `OwnerWorkflow` the failed read blocks submit, so the issue branch is reachable only by a direct core call and the attempt stays pending until interrupted. `cp2.view` behaves the same way.
- **A missing operand is a gap, never 0:** the topic is Not assessed, the change is None and the percentage is missing (P2 b).
- **`_plain` is exact.** Over 200k random decimals the value and sign never change, zero becomes `0`, and no positive exponent is left. It traps only at exponent 200 or more, beyond CP-1's bound magnitudes. The round 13 R2 L1 exact change is preserved.
  - Over the 60 frozen pairs no value moves. 39 zero-change texts move from `0.0`/`0.00` to `0`, which now equals the pinned `change_exact`.
  - What moves: the CP-L10 result hash (run-bound) and the reader's `change` text. The view never contains `change`, so the report is wrong to say the view moves.
  - Probes: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpl10-s2-review/p1_plain_exact.py` (exit 0) and `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpl10-s2-review/p6_plain_frozen.py` (exit 0).
- **The §6 rewire holds.**
  - Model text is read only through `json_object` and `exact_json`.
  - The 19 frozen refusals and the positive and limited literals are unchanged.
  - Hostile text (deep nesting, a non-object, NaN, a lone surrogate, truncated or empty text, a 200k-digit int, a BOM, trailing garbage) moves from Pydantic's issue text to the new shape issue.
  - Duplicate keys and wrong-type fields keep Pydantic's issues, and no payload Pydantic would accept is lost.
  - The wording follows the `(root): ` shape form and the lease does not pin it, so it is admissible, but it is new text for LEAD.
  - Text that passes validation never makes `screen_report` raise.
  - Probes: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpl10-s2-review/p3_parse_rewire.py` (exit 0) and `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpl10-s2-review/p4_text_after_validation.py` (exit 0).
- **Registrations are clean.**
  - Rows are appended only, and the spec equals the lease.
  - There is no `_PRECHECKS` or `_OWNER_SCOPES` row, and `SHIPPED_MAPS` ends with CPL10.
  - The bindings are right: TL10.1, TL10.2, TL10.5 and TL10.3 go to evidence and TL10.4 to limitations.
  - The defaulted `inherited_limitations` field is admissible.
  - Info: TL10.5 is bound as `amount` although the counts are in `topics`. The rails do not read that field.
- **Reader and D3:** the reader exposes the pinned fields plus `result_sha256`, as CP-DR's does. D3 is OPEN and nothing claims completion.
- **Library boundary:** clean. `methods/cpl10.md` is the draft plus TL10.5, and its L10-b text matches the ruling.
- **Info:** `screen_report` adds a product `assert`, which falls under the backlog's product-asserts owner item.
- I found no stub or fake value in `src`.

Not verified: the tamper at verifier level, `stale_binding`, both `RefusedBegin` cases and the render states (not probed); whether `format(amount.normalize(), "f")` reproduces every oracle `amount_exact`; claim citations against a genuine CP-1; and the lease's `observation_ids` rule on any pack other than the financial one. I appended no lane ledger line, because I am read-only.
