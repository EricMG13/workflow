"""CP-2A store runs (Stage 5 only): genuine CP-0 and CP-1 promotions, then CP-2A, through the
public `OwnerWorkflow` API, compared with `cases/cp2a-owner/expected.json`. Each case is 11-26
minutes (module-scoped fixtures, one job under the heavy-job lock). Written in Stage 2, never run
there. The consumption proof (D3) is CP-2G's: here only the settled head and the receipt.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from cp2a_runs import cp2a_closed, oracle

from deploy_vii.execution import Execution
from deploy_workflow.owner_workflow import OwnerRunReceipt, verify_owner_run_receipt

EXPECTED: dict[str, Any] = oracle()["expected"]


@pytest.fixture(scope="module")
def positive(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, None]:
    return cp2a_closed("positive", tmp_path_factory.mktemp("cp2a-positive"))


@pytest.fixture(scope="module")
def blocked(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, None]:
    return cp2a_closed("blocked", tmp_path_factory.mktemp("cp2a-blocked"))


def _verify(closed: tuple[Path, Path, None]) -> Execution:
    store = Execution(closed[0])
    verify_owner_run_receipt(store, OwnerRunReceipt.model_validate_json(closed[1].read_bytes()))
    return store


def test_positive_head_equals_the_oracle(positive: tuple[Path, Path, None]) -> None:
    store = _verify(positive)
    snapshot = store.read()
    case = EXPECTED["cases"]["positive"]
    assert [h.module_id for h in snapshot.heads] == EXPECTED["execution"]["plan_order"]
    head = next(h for h in snapshot.heads if h.module_id == "CP-2A")
    assert head.status == "restricted"
    module = store.head_module(head)
    assert [t.table_id for t in module.tables if t.table_id.startswith("T2B.")] == [
        t["table_id"] for t in case["tables"]
    ]
    facts = {f.fact_id: f for f in module.facts}
    for expected in case["facts"]:
        fact = facts[expected["fact_id"]]
        assert fact.status == expected["status"]
        if expected.get("amount_exact") is not None:
            assert fact.amount == Decimal(expected["amount_exact"])
    assert list(module.limitations[: len(case["own_limitations"])]) == case["own_limitations"]


def test_blocked_run_leaves_a_blocked_head(blocked: tuple[Path, Path, None]) -> None:
    store = _verify(blocked)
    expected = EXPECTED["cases"]["blocked"]
    head = next(h for h in store.read().heads if h.module_id == "CP-2A")
    module = store.head_module(head)
    assert head.status == expected["head"]["status"] == "blocked"
    assert list(module.limitations) == expected["attempt_1"]["limitations"]
    assert module.tables == () and module.facts == ()
    assert json.loads(blocked[1].read_text())  # the sealed receipt is retained
