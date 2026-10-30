"""Pin the exact validate_tables outcomes (messages and order) on small real contracts."""

from __future__ import annotations

import re

import pytest

from deploy_vii.contracts import Fact, ReportTable, TableColumn, TableRow, validate_tables


def fact(fact_id: str, table: str, row: str, field: str = "value") -> Fact:
    return Fact(fact_id=fact_id, label=fact_id, table_id=table, row_id=row, field=field, text="x")


def table(
    table_id: str,
    rows: tuple[TableRow, ...],
    fields: tuple[str, ...] = ("value",),
    interface_id: str | None = None,
) -> ReportTable:
    return ReportTable(
        table_id=table_id,
        title=table_id,
        columns=tuple(TableColumn(field=f, label=f) for f in fields),
        rows=rows,
        interface_id=interface_id,
    )


def row(row_id: str, *fact_ids: str) -> TableRow:
    return TableRow(row_id=row_id, label=row_id, fact_ids=fact_ids)


FACTS = (
    fact("a1", "ta", "r1"),
    fact("a2", "ta", "r2"),
    fact("b1", "tb", "r1"),
)
TABLES = (
    table("ta", (row("r1", "a1"), row("r2", "a2"))),
    table("tb", (row("r1", "b1"),)),
)


def test_valid_input_passes() -> None:
    validate_tables(TABLES, FACTS)


def test_undeclared_tables_are_allowed() -> None:
    validate_tables((), FACTS)


CASES = {
    "Duplicate report table": (TABLES + (TABLES[0],), FACTS),
    "Duplicate table interface identity": (
        (
            table("ta", (row("r1", "a1"), row("r2", "a2")), interface_id="i1"),
            table("tb", (row("r1", "b1"),), interface_id="i1"),
        ),
        FACTS,
    ),
    "Duplicate fact identity": (TABLES, FACTS + (FACTS[0],)),
    "Interface table requires exact field headings without an extra row header": (
        (
            ReportTable(
                table_id="ta",
                title="ta",
                columns=(TableColumn(field="value", label="Value"),),
                rows=(row("r1", "a1"), row("r2", "a2")),
                interface_id="i1",
            ),
        ),
        FACTS,
    ),
    "Duplicate report column": (
        (table("ta", (row("r1", "a1", "a1"),), fields=("value", "value")),),
        FACTS,
    ),
    "Duplicate report row": ((table("ta", (row("r1", "a1"), row("r1", "a2"))),), FACTS),
    "Report row does not match its columns": (
        (table("ta", (row("r1", "a1"), row("r2", "a2")), fields=("value", "other")),),
        FACTS,
    ),
    "Report cell repeats or references an unknown fact": (
        (table("ta", (row("r1", "a1"), row("r2", "missing"))),),
        FACTS,
    ),
    "Report cell differs from its canonical fact coordinates": (
        (table("ta", (row("r1", "a1"), row("r2", "b1"))),),
        FACTS,
    ),
    "Declared report table omits canonical facts": (
        (table("ta", (row("r1", "a1"),)),),
        FACTS,
    ),
}


@pytest.mark.parametrize("message", list(CASES))
def test_invalid_input_raises_the_exact_message(message: str) -> None:
    tables, facts = CASES[message]
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        validate_tables(tables, facts)
