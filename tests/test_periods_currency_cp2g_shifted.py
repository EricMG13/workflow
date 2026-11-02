"""Phase 8 Task 5, fix round 1: every frozen CP-2G fixture, restated on the EUR 2026 basis.

The key is the frozen CP-2G oracle `cases/cp2g-owner/expected.json` read through the mapping rules
of `cases/periods-currency-owner/manifest.json#mapping_rules` (every four-digit calendar year +1,
the two-digit `Q4 25` label +1, `US$`/`USD` to `EUR`; amounts never change). The inputs are the
frozen fixtures' own, restated the same way; the module is composed on `period_basis`'s EUR basis
and each cell, table row label, code-written claim and limitation is compared with the shifted
oracle. The first file compares the one shifted case the oracle itself pins (`CP-2G@EUR`).
"""

import dataclasses
import json
import re
from typing import Any

import pytest
import test_method_cp2g as g
import test_periods_currency_cp2g_cp2h as t

from deploy_vii.contracts import Fact
from deploy_workflow.owners import cp2g

CASES = g.CASES
_YEAR = re.compile(r"(?<!\d)(20\d\d)(?!\d)")
_LABEL = re.compile(r"\b((?:LTM )?Q[1-4]) 25\b")
# text keys the mapping rule applies to; amounts and ids are never shifted
_TEXT_KEYS = {"label", "period", "limitation", "text", "formula", "currency", "title", "shown"}


def shift(text: str) -> str:
    text = _YEAR.sub(lambda m: str(int(m[1]) + 1), text)
    text = _LABEL.sub(lambda m: f"{m[1]} 26", text)
    return text.replace("US$", "EUR").replace("USD", "EUR")


def _shifted_fact(fact: Fact) -> Fact:
    update: dict[str, Any] = {}
    for name in ("label", "period", "limitation", "currency"):
        value = getattr(fact, name)
        if isinstance(value, str) and shift(value) != value:
            update[name] = shift(value)
    return fact.model_copy(update=update) if update else fact


def _shifted_context(case: str) -> cp2g.ForwardContext:
    ctx = g._context(case)
    cp2a = ctx.cp2a
    head = dataclasses.replace(
        cp2a,
        base_period=shift(cp2a.base_period),
        scenarios=tuple(
            dataclasses.replace(
                s, decline=_shifted_fact(s.decline), increase=_shifted_fact(s.increase)
            )
            for s in cp2a.scenarios
        ),
        breaks=tuple(
            dataclasses.replace(
                b, level=_shifted_fact(b.level), required_decline=_shifted_fact(b.required_decline)
            )
            for b in cp2a.breaks
        ),
    )
    cp1d = ctx.cp1d
    if cp1d.supported is not None:
        cp1d = dataclasses.replace(
            cp1d,
            supported=_shifted_fact(cp1d.supported),
            total_leverage=_shifted_fact(cp1d.total_leverage)
            if cp1d.total_leverage is not None
            else None,
            net_leverage=_shifted_fact(cp1d.net_leverage)
            if cp1d.net_leverage is not None
            else None,
        )
    return dataclasses.replace(
        ctx,
        cp1_facts=tuple(_shifted_fact(f) for f in ctx.cp1_facts),
        cp2a=head,
        cp1d=cp1d,
        basis=t.EUR,
    )


def _inputs(case: str) -> cp2g.ForwardInputs:
    """The fixture's inputs restated on the EUR 2026 basis, the analyst payload included."""
    payload = json.loads(shift(json.dumps(g._bind_all(g._payload(case)))))
    submission = cp2g.ForwardSubmission.model_validate_json(json.dumps(payload))
    return cp2g.ForwardInputs(context=_shifted_context(case), submission=submission)


def _wanted(record: dict[str, Any]) -> dict[str, Any]:
    return {k: shift(v) if k in _TEXT_KEYS and isinstance(v, str) else v for k, v in record.items()}


@pytest.mark.parametrize("case", CASES)
def test_shifted_fixture_cells_equal_the_shifted_oracle(case: str) -> None:
    result = cp2g.compute(_inputs(case))
    want = g.EXPECTED["cases"][case]["facts"]
    got = [g._record(c) for c in result.cells]
    assert [r["fact_id"] for r in got] == [r["fact_id"] for r in want]
    for have, expected in zip(got, want, strict=True):
        assert have == _wanted(expected), expected["fact_id"]


@pytest.mark.parametrize("case", CASES)
def test_shifted_fixture_tables_and_limitations_equal_the_shifted_oracle(case: str) -> None:
    result = cp2g.compute(_inputs(case))
    tables = [
        {
            "table_id": tb.table_id,
            "title": tb.title,
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)}
                for r in tb.rows
            ],
        }
        for tb in result.tables
    ]
    want = g.EXPECTED["cases"][case]
    assert tables == [
        {
            **tb,
            "title": shift(tb["title"]),
            "rows": [{**r, "label": shift(r["label"])} for r in tb["rows"]],
        }
        for tb in want["tables"]
    ]
    assert list(result.own_limitations) == [shift(x) for x in want["own_limitations"]]
    assert [c.claim_id for c in result.claims] == [c["claim_id"] for c in want["claims"]]
    for claim, key in zip(result.claims, want["claims"], strict=True):
        assert claim.text == shift(g._bind(key["text"])), key["claim_id"]
        assert claim.limitation == (None if key["limitation"] is None else shift(key["limitation"]))
