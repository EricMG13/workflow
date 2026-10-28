# CP-2G Stage 1 first adversary review (mx-adversary; controller-saved)

# CP-2G Stage 1 adversary review (tip `0e28916`, worktree `agent-a4377a7580e8e70db`)

**Verdict: CHANGES REQUIRED.** There are two correctness Mediums and one test-strength Medium. The arithmetic itself is sound: it matches an independent Fraction recomputation built from the lease's Method table on all 7 cases. All the round 5 and 6d strings are byte-exact.

**Gates, run at the target root:**
- `pytest tests/test_method_cp2g.py`: 175 passed in 1.95 s, exit 0.
- `ruff check`: exit 0.
- `ruff format --check`: exit 0.
- `MYPYPATH=src mypy --strict` on both files: exit 0.
- `git status` is clean. I edited nothing.

Probe directory (P below): `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2g-adversary/`

## Medium

**M1. A CP-1 figure named by its calculation id validates, but the composed claim cannot be resolved.** `src/deploy_workflow/owners/cp2g.py:2063-2068` (`_references`) and `:2148`/`:2154` (`Claim.references`).
- `prose.bind` resolves a CP-1 fact by fact id and also by calculation id. Real T4.10 facts carry a separate `canonical-kpi:` id (`canonical_kpis.py:311`).
- So `{<calc id>|US$ m}` passes `content_issues`. But `_references` and `Claim.references` match fact ids only.
- Result: the CP-1 fact is dropped from `cp1_references`, `claim.references` is `()`, and the claim fails against the module's own facts with `Unresolved reference: calc:cp1-revenue`. In Stage 2 that is a failure at settle after validation passed.
- CP-2A `_figure_refs` (`cp2a.py:889`) and `cp2_synthesis._figures` (`:390`) resolve through the `bind` map; CP-2G should too.
- Probe: `P/p03_calc_id_reference.py`, exit 1.

**M2. CP-1 unit, scale and currency are never checked; a thousands or non-USD book composes silently as USD millions.** `cp2g.py:329-338` (`Operands.from_cp1`) and `:984-986`.
- T4.10 scalar KPIs carry the book's unit (UNITS, THOUSANDS or MILLIONS) and its currency (`canonical_kpis.py:334`, `canonical_tables.py:565-569`).
- I restated the positive CP-1 in EUR thousands. The CP-2A required declines do not depend on scale, so the payload validates with no issues.
- The output then has `T2H.4.a25.revenue` = 120000 MILLIONS USD. CP-1 amounts in thousands are mixed with the analyst's million-scale repayment, distributions and minimum liquidity: liquidity 29827 against a minimum of 10.
- The lease states "All amounts USD, unit MILLIONS". CP-1D already fails closed in this case (`cp1d.py:155-165`). The smallest fix is a ValueError invariant on the selected amount facts.
- If LEAD would rather carry the book's unit through, that is a lease change.
- Probe: `P/p11_unit_currency_unchecked.py`, exit 1.

**M3. Arithmetic and control mutants that the tests do not catch (sensitive code).** I ran 79 targeted mutants from a full temporary copy of the worktree; 25 survived (`P/p06_mutants.py` and `P/p06_mutants.out`). The tests miss these three lease rules:
- **A10:** `:436` accessible liquidity `cc + u` changed to `cc`. Every oracle case has undrawn = 0, and the roll-forward property test (`tests/test_method_cp2g.py:1149`) never asserts liquidity.
- **A22:** `:1254-1257` `_compared` always returning "Reconciled to CP-1". No case or test ever expects "Differs from CP-1".
- **A18:** `:1973` a change of 0 reported as "Deleveraging" instead of "Flat". No case has a zero change.

## Low

**L1. G-5: some downside cells under an unknown shock carry another reason.** All downside cells are missing, as ruled, but five do not carry the G-5 text:
- gap case: `T2H.6.d26-d28.liquidity_headroom` and `T2H.7.m01.down_first` carry "minimum liquidity was not assessed" (`:1799-1800`, `:545`);
- with a G-7 row: `T2H.7.b01.down_first` carries the G-7 reason.
- This is a precedence clash between G-5 and L5/G-7 → LEAD.
- Probe: `P/p01_g5_other_reasons.py`, exit 1.

**L2. G-9 with a known but non-LTM CP-1D total leverage: the output contradicts itself.**
- `T2H.2.cp1d` (`:2225-2235`) still spells the figure as "opening total leverage", while the own line says starting leverage "is not restated on it".
- `T2H.1.u_cp1d.basis` is hard-coded to the LTM period (`:1192`).
- Chip form cannot be applied: the product refuses a chip on a known fact ("A numeric fact needs a figure reference"). So the two parts of G-9 conflict ("copies keep CP-1D's status" and "uses chip form") → LEAD.
- Probes: `P/p02_g9_period_claim.py` exit 1; `P/p02b_chip_on_known.py` exit 0 (refusal confirmed).

**L3. G-5 ("the claims use chips"):** the `T2H.7.down` claim (`:2118`) says "no tested break point is reached" when no downside test could be calculated. This wording is unruled → LEAD. Probe: `P/p07_g5_claims.py`, exit 1.

**L4. Crash instead of a fail-closed invariant.** A G-7 row whose unsettled CP-2A level has no unit raises `KeyError('None')` at `:1868`, where a ValueError is expected. This needs two defensive upstream conditions at once. Probe: `P/p10_g7_unitless_level.py`, exit 1.

**L5. Other mutation survivors (missed order, guard and selection rules):**
- reason and cause order: A13 (ratio reason order), B10, B13 and B14 (G-8 and operand order);
- B15: the 6d rule "level cause for leverage kinds only" is untested;
- probability guard (L11): V03 (case-insensitivity), V04 and V05 (the "expected value" and "probability of" phrases);
- issue order and prose paths: V06 (High position), V11 (driver issue order), V12 and V13 (prose checks on `gaps[].action` and `minimum_liquidity.rationale`);
- other guards: V08 (whitespace-only prose accepted), V09 (stale check comparing sha only);
- S01: the `table_id == "T4.10"` selection predicate;
- ruled branches: R01 (G-5 decline before increase); R04, R05b and R06 (own-line positions of G-6, G-5 and G-7 against the 6d order); R07 (order of the two G-9 reasons);
- A23: the canonical form from `_exact`.
- Follow-up mutants in `P/p06b_mutants_followup.py`: R05b survived; A28, A29, A30 and R19 were killed.

## Info
- With extreme valid drivers, a CP-1 revenue carrying 16 or more decimal places raises `decimal.Inexact`, not a ValueError. This follows the lease's 38-digit trap (L7); 14 places still compose. Probe: `P/p09_inexact_headroom.py`.
- S05 is an equivalent mutant: the `Fact` validator already forbids an amount on an unsettled fact.

## Checked and clean
- **Arithmetic:** `P/p00_independent_recompute.py` exit 0. Roll-forward, shocks, interest on the opening balance, no cash floor, ratios each rounded to 38 digits half-even in one division, margin with revenue ≤ 0 (G-4).
- **Contexts and break checks:** `_RATIO` and `_EXACT` are prec 38 half-even, and `_EXACT` traps Inexact. `break_decline` is an exact Fraction. `_round38` is correctly rounded, and CP-2A computes its required decline the same way (a single `CONTEXT.divide` of exact terms).
- **`first_result` and G-8:** `first_result` matches the lease and builder. G-8 causes run in the ruled order: level ≤ 0 counts for the leverage kinds only, and the net-debt guard is removed.
- **No missing value becomes 0:** fuzzing ran 600 payloads (`P/p04_fuzz_validate_compose.py`, exit 0) and 500 upstream states, of which 435 composed (`P/p05_fuzz_context.py`, exit 0). Nothing raised, and no known cell derives from an unknown one.
- **Ruled strings (G-1, G-4 to G-7, the 6d G-7 issue, G-9):** byte-exact, `P/p08_ruled_strings.py` exit 0. G-2, G-3 and G-8 are covered by tests and by reading the code.
- **Raises:** none of the nine LEAD-to-word raises from `53816b7` remain; the remaining raises are invariants. Under G-5 every downside cell is missing, and unknown CP-2A copies keep their upstream status (mutant R10 was killed).
- **Stale issues:** `stale_issues` is identical to `cp2_synthesis._stale_issues`. Stage 1 has no combined validator.
- **Selection:** follows the manifest predicate; zero or several matches fail.
- **Standing rules:**
  - No I/O, store, host, session or render call.
  - No name clashes with protocol §2.
  - No catch-all; the only catch is `except ValidationError`.
  - The three CP-2G commits touch only the two files. The `src/deploy_vii` change in the range is LEAD's `ede9ffe`.

Not verified: Stage 2 binding against real CP-1, CP-2A and CP-1D heads (readers, `Upstream`, `validate_forward`, the view, the probe, run-level `stale_binding`); whether the analyst view exposes CP-1 calculation ids (how likely M1 is); whether any real pack uses a THOUSANDS, UNITS or non-USD book (how likely M2 is); the full suite and the builder re-run (not run, as instructed); full mutmut (only 84 hand-picked mutants were run); `prose.issues` and `bare_figures` over the new strings (I did not re-run them); confidence-review and rewrite-tournament (not re-run).

