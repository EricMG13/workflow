# Stage 2 review, lane A: distressed chain (mx-adversary)

## Stage 2 whole-stage review, lane A (CP-2G, CP-2H, CP-4C) at a1a0574

I reviewed `claude/s2-batch` read-only. The worktree is still clean at a1a0574. Every probe ran on a `git archive` copy at `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage2-review-A/` (called `<A>` below).

### Verdicts
- **CP-2G: REQUEST CHANGES** (M1)
- **CP-2H: APPROVE**
- **CP-4C: REQUEST CHANGES** (M2)

### Gates
- Gate 1 (the eight-file set): **exit 0**, 2477 passed.
- `tests/test_stage2_classes_batch.py`: **exit 0**, 12 passed.

### Medium

**M1. CP-2G's CP-1D consumption proof (D3) cannot tell whether CP-2G reads CP-1D's facts.**
- **Where:** the read is at `src/deploy_workflow/owners/cp2g.py:2755`. Every fixture settles CP-1D from the positive oracle (`tests/test_connect_cp2g.py:391`), and only CP-1D's status ever varies.
- **Scenario:** a mutant keeps the bound CP-1D status but takes the three supported facts from a constant equal to the oracle. It survives every lane test: 2445 passed, including the D3 test at `:1110`.
- **Gaps behind it:**
  - The module docstring (`:10-11`) claims the fixtures prevent this, but they do not.
  - The builder's mutants only dropped CP-1D entirely or changed statuses.
  - The deferred `test_owner_cp2g.py` A6 test replays the frozen literals, so it would not catch this either.
- **Why it matters:** CP-1D's D3 closes on CP-2G's acceptance.
- **Fix (tests only):** seed a CP-1D head whose `T1D.3.supported.value` and `T1D.6` facts differ from the oracle, then assert that `T2H.2.*_supported` and `T2H.8.*.ebitda_fy26_vs_supported` follow it.
- **Probe:** `<A>/p4_d3_status_only_mutants.sh` (mutant m1); exits 1 now.

**M2. CP-4C's D3 proof cannot tell whether CP-4C reads the facts of CP-2G, CP-2A or CP-4.**
- **Where:** the reads are at `src/deploy_workflow/owners/cp4c.py:2685-2687`. The fixtures never vary these heads (`tests/test_connect_cp4c.py:583-591`):
  - CP-2A is always the positive oracle;
  - CP-2G is the gap oracle, or the real CP-2G core run on the gap literal, which gives the same values;
  - the CP-4 fields CP-4C reads are identical in the positive and gap cases.
- **Scenario:** three mutants each keep the bound status but take the values from a constant equal to the oracle: m3 (CP-2G), m7 (CP-2A) and m8b (CP-4, narrowed like `cp4_reader`). All three survive the full lane suite.
  - The spy test at `:1343` only checks that `cp2g_reader` is called, not that its output is used.
  - The docstring (`:10-11`) says "the CP-2G head" varies "so a constant equal to the oracle cannot pass". That claim is false.
  - The deferred A6 test (`test_owner_cp4c.py:527`) uses the same frozen literals.
- **Why it matters:** CP-2G's D3 closes on CP-4C's acceptance (lease D3).
- **Fix (tests only):** seed a CP-2G head with a scaled `T2H.4.b26/d26.ebitda`, a CP-2A head with a different `s03` decline and a CP-4 head with a different facility text, then assert that the T4E.3 and T4E.2 copies follow.
- **Probe:** `<A>/p4_d3_status_only_mutants.sh` (m3, m7, m8b).

For contrast, these mutants are killed:
- m2, CP-2G reading a constant CP-2A head: killed by `test_adapter_reads_the_frozen_cp2a_gap_head`;
- m4, CP-2H reading constant CP-2G metrics: killed by the `fixture_total_loss` adapter case;
- m5 and m6, reading the current head instead of the bound blob, in CP-4C and CP-2G.

### Low

**L1. Round 3 citations: the close-release list leaves out CP-2G and CP-4C.**
- **What happens:**
  - On a head the real core settles, 31 of CP-2G's own facts carry 2 quotes from financial page:4 (probe `<A>/p1_cp2g_citations_round3.py`, exit 1).
  - 56 of CP-4C's own facts carry up to 3 quotes from one page (probe `<A>/p2_cp4c_citations_round3.py`, exit 1).
- **Why the code is not wrong:** both frozen oracles carry the concatenation lineage: CP-2G in its `lineage_rule` text, CP-4C in pinned citations. Under round 5 item 17 (extended), keeping that lineage until the close is correct.
- **The gap:**
  - `close-release.md` lists the round 3 re-pin for CP-2H and CP-1C only, so CP-2G and CP-4C would never switch.
  - `methods/cp2g.md` and `methods/cp4c.md` do not state the derived-fact rule, which brief.md requires.

**L2. CP-4C's required-head blocked refusal is untested.**
- `_required_module` (`cp4c.py:2609-2615`) refuses a blocked CP-1, CP-2A or CP-4 head, but no test covers it; only `cp2g_of`'s refusal is tested.
- Removing it survives the lane suite (probe `<A>/p5_cp4c_required_head_refusal.sh`, exit 1).
- It cannot be reached through G1, because a required edge is never bound blocked.

### Info
- **I1. `Upstream.inherited` defaults to `()`** in `cp2g.py:2718`, `cp2h.py:1930` and `cp4c.py:2642`. An `Upstream` built by hand would show no inherited limitations in the view. `submit`, `probe` and `view` always fill it, so nothing real is affected.
  - Separately, the view's `inherited_limitations` is computed with `own=()`, so it includes lines that settlement drops, such as the synthetic line. This is the same class as CP-1D I1.
- **I2. Docstring overstates the shared adapter.** In CP-2G and CP-4C, the `_inputs` docstring says `view` reaches the core through `_inputs`. In fact `context_block` reads `Upstream` directly. It uses the same selection functions, and I found no divergence.

### Checked and holding
- **Whole reader chain on real heads:** CP-2A settled by the real CP-2A core, then CP-2G by the real CP-2G core, then CP-4C settles. The CP-2A row CP-4C reads equals the real head's row s03, and CP-2H's 28 selected T2H.6 facts equal the CP-2G head's. Probe `<A>/p3_full_chain.py`, exit 0.
- **CP-1D consumption in CP-2G:**
  - bound and settled: the three facts are read from the bound blob;
  - blocked: status only;
  - not bound: `Cp1dHead(status=None)`.
  - `status()` takes each status from the bound inputs.
- **Rows:** the `_DISTRESSED` titles, owners and kinds, and each tab label, match every oracle's FP05. In `_PRESETS`, `forward-credit-path` and `forward-breakpoints` follow `break-points` as the lease says; the CP-2H and CP-4C ids were already in the preset.
- **CP-2H split citation rule:** `_with_upstream_citations` gives one citation per new page, taking the first upstream quote in `derives_from` order, after the frozen own citations. That matches round 5 item 17.
- **CP-4C:**
  - the `cp4_reader` narrowing leaves `compute` identical to Stage 1;
  - the v08 two-line form is pinned in both test files and recorded in `close-release.md`.
- **Deferred tests:** each A4 tamper test checks, through a `_PROBES` spy, that the verifier really reaches the module's probe. The A7 G2-render tests are skipped placeholders, blocked on Stage 3 (round 1 Q1).

Not verified: the genuine runs (`test_owner_cp2g.py`, `test_owner_cp2h.py`, `test_owner_cp4c.py`; the CP-1 promotions take 11–26 minutes per case); the G2 render; ruff and mypy were not re-run; the full suite was not run; a real CP-1D head whose supported facts are not known; CP-2H's rule ordering at verifier level, which I did not trace; and the content of the stage-level class test, which is lane C's.

