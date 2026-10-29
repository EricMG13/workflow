# CP-2H Stage 1 report (controller-saved from the implementer's hand-back)

- **Branch:** `worktree-agent-a52b5ec0919986ddb`, from 60e2348.
  - `10f82cb`: cherry-pick of LEAD 2ae589b; clean.
  - `5d91e7b`: `feat(cp2h): Stage 1 calculation against the frozen oracle`.
- **Files:** `src/deploy_workflow/owners/cp2h.py` (new, about 1,600 lines) and `tests/test_method_cp2h.py` (new).
- **Test-first not followed.** The module was written before the test, so no red run was seen. Mutation and probes are left to the first adversary review.
- **Tests:** 120 passed in 0.98 s.
- **Gates:** ruff check, ruff format --check, and `mypy --strict` on src and test all exit 0. The first pass was not green: one fixture bug, ISC004/FURB157, and one mypy error.

## Pins asserted (`test_oracle_pins`)
- **Changed:**
  - CP-2H manifest: 1c0aa69f…
  - CP-2H builder: 21c5ca8e…
  - CP-2G manifest: 1c36928c…
- **Unchanged:**
  - CP-2H expected 59cdb4d1… and submissions 9484d2a9…
  - CP-2G expected 97328745…
  - methodology 1bb6c0bc…

## Public surface (pure)
- **Constants:** `MODULE_ID`, `STEP_ID`, `SCHEMA_VERSION`.
- **Schema:** `TriggerSubmission`, `AgencyView`, `Overall`, `SynthesisGap`.
- **Helpers:** `parse_ratings`, `headroom` (one `CONTEXT.subtract`, with `.scaleb(2)` for percent metrics), `is_reached` (strict) and `first_year`.
- **Selection:** `select_cp1` and `Cp2gMetrics.select`.
- **Validation:** `stale_issues`, `phrase_issues`, `payload_issues` and `validate`.
- **Composition:** `compute(inputs) -> TriggerReport`, giving T2R.1–T2R.10, the references, claims, limitations, outcomes and totals.
- **Left for Stage 2:** the `validate_triggers` and `rating_triggers` names, plus `Upstream`, `RULES`, `view`, `probe` and `submit`.

## Input fields
| Field | Type | Stage 2 source |
|---|---|---|
| `pack.sources` | tuple[Source] | Pack sources in the H1 mapping (identity, financial, ratings) |
| `pack.names` | tuple[str] | `pack.run.issuer_name` |
| `upstream.bound` | tuple[Input] | Bound inputs: prepared-pack, CP-0, CP-1, CP-2G |
| `upstream.current` | tuple[Input] or str | `execution.current_inputs`, or its refusal text |
| `upstream.cp1_facts` | tuple[Fact] | CP-1 T4.10: 4 facts `LTM Q4 25 (2025-01-01 to 2025-12-31) · <metric>` |
| `upstream.cp1_status` | str | Bound CP-1 Input status |
| `upstream.cp2g.facts` | 28 Facts | `cp2g_reader`: `T2H.6.{a25,b26-b28,d26-d28}.{4 ratios}` |
| `upstream.cp2g.status` | str | CP-2G head status |
| `upstream.cp1d_status` | InputStatus or None | Bound CP-1D Input; fails closed if set |
| `submission` | TriggerSubmission | Judgment (FIGs bound at run time) |

## Oracle coverage
- **Cell for cell:**
  - cases: positive, gap, fixture_total_loss, fixture_boundary;
  - outputs: parsed source, facts, tables, claims, limitations, references, results, totals, divergence, FP05 cells.
- **Inputs:** built from the CP-2G oracle and checked against CP-2H's recorded inputs.
- **Refusals:** all 29 calculation-level refusals are exact, and so are the blocked attempt issues.
- **Property tests:**
  - the headroom sign matches "reached", and is monotonic;
  - percentage points come from `.scaleb(2)`;
  - `first_year` is the earliest year;
  - T2R.4 reconciles;
  - the D3 (c) lineage counts.
- **Left to Stage 2/4:**
  - binding and readers;
  - tool use and the view;
  - the seams;
  - module assembly;
  - run-level cases;
  - pack and run checks.

## Fail-closed states for LEAD (`UnpinnedCase`)
1. A bound CP-1D: the own line has no pinned wording.
2. No single ready `ratings` source. The implementer recommends `Rating register not found` alone.
3. A terms header with no trigger rows, which leaves T2R.3–T2R.6 empty.
4. A register with one agency, which leaves T2R.8 empty.
5. A submission with no gap, which leaves T2R.10 empty.
6. An unrated (Withdrawn or Not rated) agency that has trigger terms.
7. A page:1 or page:3 with other than exactly one `Published <Month D, YYYY>.` line, or with an invalid date.
8. A table-rule breach that the builder only asserts. The implementer recommends the matching `… not found` text alone.

## Decisions to confirm
- **Issue order:** views in register order, schema field order within a view, then the missing-view issues, then overall, then gaps.
- **T2R.7 row order:** register order. The builder uses submission order, which matches in every frozen case.
- **Alone-returned issues:** stale issues alone, and before the source parse; source issues alone.
- **Prose:** the checks cover rationales and gap fields, not limitations; the phrase guard covers limitations.
- **Bound set:** the module facts plus 4 CP-1 ratios. Analyst cells are not in it (P2), and CP-2G facts are not referencable.
- **Unsettled CP-2G a25 copy:** keeps its status (G-decisions/L10-c).
- **Period dates:** read from the Published lines.
- **Unregistered trigger agency:** composes with no issue (builder parity).

## Confidence review
- **Fixed:**
  - two `or ""` empty-limitation fallbacks now raise as invariants;
  - a dead dict;
  - a fixture self-check.
- **Rewrite tournament:** `_forward` became a single pass, and `_view_issues` holds.

Not verified:
- Stage 2 binding (stand-in fact ids and Input hashes);
- the CP-2G core output (not on this base);
- module assembly and rendering;
- tool use, view, probe and tamper;
- run-level outcomes;
- the wording of fail-closed states 1–8;
- the full suite.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
