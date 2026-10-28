# Stage 1 layer review, group B (CP-1C, CP-1D, CP-L10): mx-architect, controller-saved

**Branch and commit:** `worktree-agent-ac6940c087df14967`, at 4b46e19. No commit was made: every confirmed finding is an unruled case and goes to LEAD.

**Probes:** in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage1-review-B/`. Each exits 0 when it reproduces its finding.

## Findings
- **B1 (Medium, LEAD). CP-1C crashes when a CP-1 T4.10 ratio is not known.**
  - **Where:** `cp1c.py:729-739` (`_cp1_facts`) raises `ValueError("CP-1 fact unavailable for <metric>")`, reached from `calculation_issues` → `_compose` (:1356).
  - **Scenario:** an issuer with a not_applicable `interest_coverage_adjusted` (zero cash interest). The validator raises instead of composing.
  - **Unpinned cells:** T1C.3.issuer; T1C.4 difference, position and of; the T1C.5 issuer row; and T1C.6 cp1, difference and result. CP-1D 1D3 ("reported side keeps CP-1's status, `Not compared`") is the analogue.
  - **Latent:** `_Composer.copy` (:582-604) copies neither status nor limitation.
  - **Probe:** `probe_b1_cp1c_cp1_ratio_not_known.py`.
- **B2 (Low, LEAD). CP-1D crashes on a `ready` bridge source with `sha256=None`.**
  - **Where:** `cp1d.py:739-741` (`_cite`) raises `ValueError("Source without a hash: bridge")`. CP-1C maps the same state to `Peer table not found` (cp1c.py:314).
  - **Probe:** `probe_b2_cp1d_bridge_without_hash.py`.
- **B3 (Low, Stage 2 brief). The CP-1D overall rationale is not prose-checked at Stage 1.**
  - **Where:** `cp1d.py:1529-1555`. A bare figure or an unresolved `{ref}` in `overall.rationale` passes `validation_issues` and composes into `T1D.1.assessment`.
  - **Why deferred:** the frozen rationales carry `{{FIG:...}}` markers.
  - **Stage 2 must:** bind `{{FIG}}`, then run `prose.issues(overall.rationale, bound, names=(issuer,))` inside the validator.
  - **Probe:** `probe_b3_cp1d_overall_rationale_unchecked.py`.
- **Info.** `cpl10.py:26,770` calls `deploy_vii.registry.modules()`, a cached product registry read named by the lease. It is not a store, host, session or renderer call.

## Ledger Lows checked
- The CP-1C "provisional" comment was already replaced in 2524eb4.
- The three CP-L10 round-4 Lows have tests.
- CP-1D L-a/L-b are covered by `test_partial_composition_checks_like_the_full_module`.

## Calculation, inputs, boundaries
- **Calculation:** all three conform to the Method text and rulings, and missing never becomes 0.
- **Inputs:** none of the three manifests has `fact_bindings`. The fields were checked against the selection rules and the lease Public API, and every field can be bound in Stage 2.
- **Boundaries:**
  - no I/O;
  - no commit in the group touches `src/deploy_vii`;
  - no G1-X §2 name clashes. The CP-L10 `STEP_ID/STEP_IDS/SCHEMAS` are the lease's own attributes.

## Cross-group inconsistencies (report only)
- **Decimal contexts.**
  - cp1c, cp1d and cpl10 quantise at 38 digits, HALF_EVEN; cp1d also uses an exact trapping context for sums.
  - cp2d uses `Context(prec=60)` with default rounding.
  - cp2e and cp3d change `localcontext()` ad hoc.
- **`ZERO_OR_NEGATIVE_DENOMINATOR`.** cp1d, cp2a and cp2d carry it. cp1c (oracle-pinned) and cpl10 (not pinned) don't.
- **Prohibited-conclusion guards: three mechanisms.**
  - the product `prohibited_issues` (cp1c, cp2a);
  - closed substring lists (cpl10, cpdr, cp2d);
  - regexes (cp2e, cp3d).
- **Confidence type.** cp1c uses its own Literal (lease-pinned); the others use the product `Confidence`.
- **Spelling.** cp1c and cpl10 use `fact_spelling`. cp1d uses `display.format_value`, which is oracle-equal.
- **Number bounds.** Only cp1d enforces `financial_contracts.Number`.

## Reviews
- **confidence-review:** B1, B2 and B3 are confirmed. Nothing else is open, apart from what LEAD already holds.
- **rewrite-tournament:** the incumbents hold: cp1c `_universe`, cp1d `parse_bridge`, cpl10 `Upstream.__post_init__`.

## Tests and gates
All passed on the first run, exit 0.
- CP-1C: 105 passed.
- CP-1D: 85 passed, 1 skipped.
- CP-L10: 63 passed.
- ruff, ruff format and `mypy --strict`: exit 0 on all six files.

Not verified:
- Stage 2 binding from a real head;
- confidence-review and rewrite-tournament ran inline, so no rewrite candidate was tested;
- mutation testing;
- the 1D1 citations, because the oracle amendment was pending.

agent=mx-architect fix-rounds=0 gates-first-pass=y
