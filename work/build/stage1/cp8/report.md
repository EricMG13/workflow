# CP-8 Stage 1 report (controller-saved from the implementer's hand-back)

- **Branch and commit:** `worktree-agent-a3cc9818386e8861a`, commit **1cf8b93** "feat(cp8): Stage 1 calculation against the frozen oracle", based on ae65b75.
- **Files:** `src/deploy_workflow/owners/cp8.py` (new, 1922 lines) and `tests/test_method_cp8.py` (new, 410 lines).
- **Tests:** 102 passed in 0.44 s. RED was first seen as ModuleNotFoundError. The run used pyproject's `pythonpath`, because the guard refused the `PYTHONPATH=src` form.
- **Gates:** final exits are all 0: ruff check, ruff format --check, and `mypy --strict` on both files. The first run was not green (ISC004, a format fix, and test typing).

## Public surface (pure, no I/O)
- `DecisionLedgerSubmission`. Vocabulary fields are plain `str` on purpose, so refusal literals reach the validator's wording.
- `validate_ledger(*, submission, upstream, pack)`. It applies the rules in field order and never removes duplicate issues (r42). The check order is pack, then the CP-8 scope, then the field's source rule, then locator and quote (`readiness.citation_issues`).
- `Upstream(as_of, authority, cp6)` and `source_authority(facts)`, which reads CP-0 `T3.<sid>.authority`.
- `ledger_inputs`, `derive(*, inputs)` and `breached`. `derive` runs under an exact Decimal context. A breach is strictly beyond the level; equal is not breached.
- `current_decision(*, prior, cp6)`.
- `decision_ledger(*, pack, submission, upstream)` returns a `LedgerReport`: Facts, T7.1–T7.8 and `cp8.what_changed`, Claims and limitations. It refuses to compose an invalid submission.

## Input fields (the manifest has no `fact_bindings`; sources come from the lease Public API and `manifest.cases`)
| Field | Type | Stage 2 source |
|---|---|---|
| `DecisionLedgerSubmission` | pydantic `Contract` | Judgment and verbatim quotes: the analyst's `decision_ledger` payload |
| `Upstream.as_of` | `date` | `Run.as_of` |
| `Upstream.authority` | `Mapping[str, str]` | CP-0 head `T3.<sid>.authority`, via `cp8_upstream` |
| `Upstream.cp6` | `tuple[str, str] \| None` | Settled CP-6 `T6-FINAL.final_bias.action_bias` and `.confidence` when bound |
| `pack` | `tuple[Source, ...]` | The prepared pack |
| `LedgerInputs.expected`, `.realized`, `.realized_as_of`, `.decision_date`, `.downside_sizes` | Decimal and date mappings | Python parses the quoted texts |
| `LedgerInputs.overall_label`, `.metric_labels` | `str`, `tuple[str, ...]` | Judgment (attributions) |
| `LedgerInputs.pack_source_ids` | `tuple[str, ...]` | The pack |

## Oracle coverage
- **`cases.positive` and `cases.no_outcome`:**
  - the validator gives `()`;
  - `derived` matches;
  - all 9 tables match cell for cell, 181 and 153 facts;
  - `validate_tables` passes;
  - `missing_not_zero`, claims and limitations match.
- **Fixtures:** all 6 fixtures and all 5 decision fixtures.
- **Refusals:** r01–r69, 68 literals (r38 is reserved); r00 through `readiness.shape_issues`.
- **Left to Stage 2/4:**
  - the RULES part of r04 and r30;
  - `tool_use_refusals`, `g1_refusals`, `blocked` and `refused`;
  - CP-0 readiness and inherited limitations;
  - `module_inputs`, tamper, render and consumption;
  - the seams (`probe`, `submit`, `RULES`, `SCHEMAS`, `STEP_IDS`, `QUALIFICATION`, `cp8_upstream`, `cp8_module`, `cp8_reader`).

**Engine/oracle disagreements:** none.

## Rulings needed from LEAD before first review (they currently raise ValueError)
**Composition:**
1. A partial outcome: the T7.3/T7.4 gap reasons and T7.8 not-compared rows.
2. A missing expected value: the T7.4 gap reason.
3. Variance claim wording for an unchanged direction.
4. CP-8-ATT-01 wording when the overall process is N.
5. A compared leverage or cover measure with no recorded size: the T7.5 gap reason.
6. Partly unrecorded fields (some, not all, of posture, size and the three expectations).
7. Bid and offer dates differ on one side.
8. The calibration gate over anything other than one recorded decision.
9. A prior Case record whose CP-0 authority is not `unknown`.

**Validator:**
10. Text without a quote, or a posture or size absence that also carries a quote.
11. A repeated confidence entry for one metric.
12. An in-scope source that has no CP-0 T3 authority.

**Choices to confirm:**
13. "Neither form given" uses the "exactly one of ..." wording.
14. Duplicates and pairing count every in-vocabulary observation; the builder counts only accepted ones. They differ only in unpinned multi-defect cases.
15. `value_text` is N.NN, and "first figure" is defined.
16. Prohibited phrases match only at the start of a word; "calibrat" matches anywhere.
17. The exit-trigger limitation is emitted whenever the exit trigger is quoted.
18. T7.2 evidence lists only the quoted fields.
19. `cp8.what_changed.outcome.value` carries the literal `∅ G#`; the binding at render is to be decided.
20. With CP-6 present, the T7.8 `current_decision` row and the no-CP-6 limitation are omitted (builder parity).
21. Labels and claim citations.
22. The model-facing schema has no enums.
23. Size: 1922 lines against an estimate of about 450.

## Confidence review and mutation
- **Fixed:** an unready pack source was reported as out of scope. A test covers it.
- **Mutation:**
  - 20 mutants killed.
  - 5 survive because no frozen page reaches them: "value occurs once" relaxed, "first figure" relaxed, the after-decision date check, the prohibited-phrase word boundary, and the CP-6-present T7.8 row.
  - A sixth, citation de-duplication, survives because cites are compared at page level.
- **Rewrite tournament:** `derive` holds. `_Checker._outcome` was rewritten for readability with the same behaviour.

Not verified: the Stage 2/4 sections; the five oracle-limited surviving mutants; composition with CP-6 bound beyond the decision line; the fail-closed points (they have no product output to compare against); the brief's exact `PYTHONPATH=src` command form.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
