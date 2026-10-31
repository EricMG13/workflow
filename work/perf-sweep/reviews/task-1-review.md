# Task 1 review: b0ac40c..17e07ba (mx-precise; returned as text, saved by the controller)

P2 (2ded26c): Spec ✅ · Task quality: Approved
P1 (17e07ba): Spec ✅ · Task quality: Approved

## P2
- Exactly the brief's edit (`contracts.py:265-267`, `:287`); loop variable `canonical` instead of
  `fact` (mypy --strict reuse of `fact` later); behaviour unchanged.
- Error order preserved: grouping pass runs after the three up-front checks and raises nothing;
  every raise keeps condition and position; old comprehension and new `.get(..., set())` are the
  same set (`Fact.table_id` non-optional, `contracts.py:167`).
- `probes/p2_equivalence.py` exit 0: b0ac40c body vs current on 60,000 random inputs from real
  contracts; all outcomes match; all 11 outcomes (no error + 10 messages) appeared.
- `probes/p2_test_on_base.sh`: new test 12/12 on b0ac40c src and on 2ded26c src.
- High none. Medium none.
- Low: `tests/test_validate_tables.py:272-334` has no declared table without facts, so the
  `.get(table.table_id, set())` default (`contracts.py:287`) is unpinned by the test (a
  `ids_by_table[...]` KeyError mutant survives); fuzz probe covers it. Add a case like
  `(table("tc", ()),)` with `FACTS`, expect no error.

## P1
- `_reference(producer_sha256: str, fact)` at `earnings_workflow.py:1685`; hash once at `:1698`;
  passed at `:1706`, `:1727`; no other callers (`financial_periods`/`statement_history`
  `_reference` are different functions).
- `probes/p1_lineage_bytes.py` exit 0 on b0ac40c and 17e07ba trees: producer hash `cd3427…3419`
  and each `OperandLineage` JSON sha256 (`f9d8d8…380e`, `715800…ddd4`) identical.
- `probes/p1_test_on_base.sh`: base fails at `tests/test_earnings_workflow.py:3864` `assert 4 == 1`
  only; head passes (~1 s). Its printed `exit=` is unreliable; read the pytest summary.
- High none. Medium none. Low none.

Not verified (reviewer): heavy owner-fixture earnings tests reaching `_operands`; the five
`test_method_*` files (relied on report: 1426 passed); ruff/format/mypy (relied on report); repo-wide
13/5 suppression count (diff adds none); P2 base timing on the blob; mutation testing.
