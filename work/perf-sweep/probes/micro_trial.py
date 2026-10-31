"""Scratch micro-trial for P1/P2/P3 (no product file is edited).

Usage: python -I micro_trial.py <repo-root> <cp1-module-blob>
Exit 0 when every candidate is output-identical to the current code on the blob.
"""

import hashlib
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "src"))
from deploy_vii.contracts import Module, validate_tables  # noqa: E402


def validate_tables_grouped(tables, facts):
    """P2 candidate: contracts.validate_tables with the per-table fact scan hoisted."""
    if len({table.table_id for table in tables}) != len(tables):
        raise ValueError("Duplicate report table")
    interface_ids = [table.interface_id for table in tables if table.interface_id is not None]
    if len(interface_ids) != len(set(interface_ids)):
        raise ValueError("Duplicate table interface identity")
    facts_by_id = {fact.fact_id: fact for fact in facts}
    if len(facts_by_id) != len(facts):
        raise ValueError("Duplicate fact identity")
    ids_by_table: dict[str, set[str]] = {}
    for fact in facts:
        ids_by_table.setdefault(fact.table_id, set()).add(fact.fact_id)

    for table in tables:
        if table.interface_id and (
            table.row_header is not None
            or any(column.label != column.field for column in table.columns)
        ):
            raise ValueError(
                "Interface table requires exact field headings without an extra row header"
            )
        column_fields = [column.field for column in table.columns]
        if len(column_fields) != len(set(column_fields)):
            raise ValueError("Duplicate report column")
        if len({row.row_id for row in table.rows}) != len(table.rows):
            raise ValueError("Duplicate report row")
        referenced_fact_ids: set[str] = set()
        for row in table.rows:
            if len(row.fact_ids) != len(column_fields):
                raise ValueError("Report row does not match its columns")
            for field, fact_id in zip(column_fields, row.fact_ids, strict=True):
                fact = facts_by_id.get(fact_id)
                if fact_id in referenced_fact_ids or fact is None:
                    raise ValueError("Report cell repeats or references an unknown fact")
                if (fact.table_id, fact.row_id, fact.field) != (table.table_id, row.row_id, field):
                    raise ValueError("Report cell differs from its canonical fact coordinates")
                referenced_fact_ids.add(fact_id)
        if referenced_fact_ids != ids_by_table.get(table.table_id, set()):
            raise ValueError("Declared report table omits canonical facts")


def outcome(fn, *args):
    try:
        fn(*args)
        return "ok"
    except ValueError as error:
        return f"ValueError: {error}"


def best(fn, n=3):
    times = []
    for _ in range(n):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return min(times), max(times)


raw = pathlib.Path(sys.argv[2]).read_bytes()
sha = hashlib.sha256(raw).hexdigest()
module = Module.model_validate_json(raw)
print(f"blob {sha[:12]} {len(raw)} bytes facts={len(module.facts)} tables={len(module.tables)}")
assert module.content_hash() == sha, "blob is not the canonical module"

lo, hi = best(lambda: Module.model_validate_json(raw))
print(f"P3 model_validate_json per call: min {lo:.3f}s max {hi:.3f}s")
lo, hi = best(lambda: module.content_hash())
print(f"P1 content_hash per call: min {lo:.3f}s max {hi:.3f}s")
lo, hi = best(lambda: validate_tables(module.tables, module.facts))
print(f"P2 validate_tables current: min {lo:.3f}s max {hi:.3f}s")
lo, hi = best(lambda: validate_tables_grouped(module.tables, module.facts))
print(f"P2 validate_tables grouped: min {lo:.3f}s max {hi:.3f}s")

# Output identity of P2 on the real tables and on each failure class.
tables, facts = module.tables, module.facts
t0 = tables[0]
cases = {
    "real": (tables, facts),
    "drop-fact": (tables, facts[1:]),
    "extra-fact": (tables, (*facts, facts[0].model_copy(update={"fact_id": "zz-extra"}))),
    "dup-fact": (tables, (*facts, facts[0])),
    "dup-table": ((*tables, t0), facts),
    "dup-row": ((t0.model_copy(update={"rows": (*t0.rows, t0.rows[0])}), *tables[1:]), facts),
    "short-row": (
        (t0.model_copy(update={"rows": (t0.rows[0].model_copy(update={"fact_ids": ()}),)}),
         *tables[1:]),
        facts,
    ),
    "omit-rows": ((t0.model_copy(update={"rows": ()}), *tables[1:]), facts),
    "no-tables": ((), facts),
}
same = True
for name, args in cases.items():
    a, b = outcome(validate_tables, *args), outcome(validate_tables_grouped, *args)
    same &= a == b
    print(f"  {name:11} {'same' if a == b else 'DIFF'}: {a}")
sys.exit(0 if same else 1)
