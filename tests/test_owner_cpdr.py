"""CP-DR store runs through `OwnerWorkflow` (Stage 5; deferred from Stage 2).

Slow: one CP-0 settlement per run, tool sessions and receipts. Expected values come from
`cases/cpdr-owner/expected.json` through `tests/cpdr_runs.py`; nothing is derived here. The fast
parts of the module (adapter, RULES, view, reader, registrations, a real-store submit and probe)
are `tests/test_connect_cpdr.py`.
"""

import json
from pathlib import Path

import cpdr_runs as runs
import pytest

from deploy_vii.execution import Execution
from deploy_workflow.owner_workflow import OwnerRunReceipt, verify_owner_run_receipt

EXPECTED = runs.oracle()["expected"]


def _verify(store: Path, receipt: Path) -> None:
    sealed = OwnerRunReceipt.model_validate_json(receipt.read_bytes())
    verify_owner_run_receipt(Execution(store), sealed)


@pytest.mark.parametrize("case", runs.CASES)
def test_closed_run_settles_the_oracle_module_and_the_receipt_verifies(
    case: str, tmp_path: Path
) -> None:
    want = EXPECTED["cases"][case]
    store_path, receipt_path = runs.cpdr_closed(case, tmp_path)
    store = Execution(store_path)
    snapshot = store.read()
    plan = runs.oracle()["manifest"]["plan_order_expected"]
    assert [a.module_id for a in snapshot.attempts] == plan
    head = next(h for h in snapshot.heads if h.module_id == "CP-DR")
    module = store.head_module(head)
    assert head.status == want["module_status"]
    assert list(module.limitations) == want["settled_limitations"]
    assert list(module.inherited_limitations) == want["inherited_limitations"]
    assert [t.table_id for t in module.tables] == list(want["tables"])
    _verify(store_path, receipt_path)


@pytest.mark.parametrize("name", list(EXPECTED["refusals"]))
def test_each_refusal_is_a_journaled_invalid_step(name: str, tmp_path: Path) -> None:
    item = runs.oracle()["submissions"]["refusal_inputs"][name]
    workflow, _ = runs.start(tmp_path, empty=item["cp0"] == "cp0_readiness_review_empty_agenda")
    outcome = runs.drive(workflow, json.dumps(item["payload"]), runs.calls_of(item["calls"]))
    assert outcome["status"] == "invalid"
    assert tuple(outcome["issues"]) == tuple(EXPECTED["refusals"][name]["step_issues"])
