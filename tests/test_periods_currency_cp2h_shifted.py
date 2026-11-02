"""Phase 8 Task 5, fix round 1: every frozen CP-2H case, restated on the EUR 2026 basis.

The key is the frozen CP-2H oracle `cases/cp2h-owner/expected.json` read through the mapping rules
of `cases/periods-currency-owner/manifest.json#mapping_rules` (every four-digit calendar year +1,
the two-digit `Q4 25` label +1, `US$`/`USD` to `EUR`; every digest to the sha256 of the shifted
source it names; amounts never change). The inputs are the frozen cases' own, restated the same
way, and the module is composed on `period_basis`'s EUR basis.
"""

import hashlib
import json
import re
from typing import Any

import pytest
import test_method_cp2h as h
import test_periods_currency_cp2g_cp2h as t

from deploy_vii.contracts import Fact
from deploy_workflow.owners import cp2h

_YEAR = re.compile(r"(?<!\d)(20\d\d)(?!\d)")
_LABEL = re.compile(r"\b((?:LTM )?Q[1-4]) 25\b")


def shift(text: str) -> str:
    text = _YEAR.sub(lambda m: str(int(m[1]) + 1), text)
    text = _LABEL.sub(lambda m: f"{m[1]} 26", text)
    return text.replace("US$", "EUR").replace("USD", "EUR")


def _shifted_pages(variant: str) -> tuple[list[dict[str, str]], str]:
    pages = [
        {"locator": p["locator"], "text": shift(p["text"])} for p in h._variant(variant)["pages"]
    ]
    return pages, hashlib.sha256("\f".join(p["text"] for p in pages).encode()).hexdigest()


def _digests(variant: str) -> dict[str, str]:
    """old source sha256 -> the sha256 of the shifted source it names."""
    return {h._variant(variant)["sha256"]: _shifted_pages(variant)[1]}


def deep(value: Any, digests: dict[str, str]) -> Any:
    if isinstance(value, str):
        return digests.get(value, shift(value))
    if isinstance(value, list):
        return [deep(x, digests) for x in value]
    if isinstance(value, dict):
        return {k: v if k == "amount_exact" else deep(v, digests) for k, v in value.items()}
    return value


def _fact(fact: Fact) -> Fact:
    update = {
        n: shift(v)
        for n in ("label", "period", "limitation")
        if isinstance(v := getattr(fact, n), str) and shift(v) != v
    }
    return fact.model_copy(update=update) if update else fact


def _inputs(case: str) -> tuple[cp2h.TriggerInputs, dict[str, str]]:
    variant, cp2g_case = h.spec(case)
    pages, sha = _shifted_pages(variant)
    digests = _digests(variant)
    ratings = h._source("ratings", h.MANIFEST["synthetic_source"]["name"], pages, sha)
    cp1 = tuple(_fact(f) for f in h.cp1_facts(cp2g_case))
    records = [deep(r, digests) for r in h.CP2G["cases"][cp2g_case]["facts"]]
    stream = cp2h.TriggerUpstream(
        bound=h.BOUND,
        current=h.BOUND,
        cp1_facts=cp1,
        cp2g=cp2h.Cp2gMetrics.select((h._cp2g_fact(r) for r in records), t.EUR),
        basis=t.EUR,
    )
    raw = deep(h.raw_payload(case), digests)
    by_metric = cp2h.select_cp1(cp1, t.EUR)
    ids = {n: by_metric[f["metric"]].fact_id for n, f in h.SUBMISSIONS["figures"].items()}
    payload = h.bind(raw, ids)
    pack = cp2h.PackScope(sources=(ratings,), names=(h.ISSUER,))
    submission = cp2h.TriggerSubmission.model_validate_json(json.dumps(payload))
    return cp2h.TriggerInputs(pack=pack, upstream=stream, submission=submission), digests


@pytest.mark.parametrize("case", h.COMPOSED)
def test_shifted_case_facts_tables_and_limitations_equal_the_shifted_oracle(case: str) -> None:
    inputs, digests = _inputs(case)
    assert cp2h.validate(inputs) == ()
    report = cp2h.compute(inputs)
    want = deep(h.EXPECTED["cases"][case], digests)
    assert [c.fact.fact_id for c in report.cells] == [f["fact_id"] for f in want["facts"]]
    for cell, expected in zip(report.cells, want["facts"], strict=True):
        h._assert_cell(cell, expected)
    tables = [
        {
            "table_id": tb.table_id,
            "title": tb.title,
            "columns": [c.field for c in tb.columns],
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)}
                for r in tb.rows
            ],
        }
        for tb in report.tables
    ]
    assert tables == want["tables"]
    assert list(report.own_limitations) == want["own_limitations"]
    assert [c.claim_id for c in report.claims] == [c["claim_id"] for c in want["claims"]]
