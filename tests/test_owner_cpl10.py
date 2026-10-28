"""CP-L10 store runs (DEFERRED to Stage 5, written not run): the closed positive run through
`OwnerWorkflow`, the receipt, the D3 pin and the lease acceptance items that need a genuine CP-1
promotion. Fast connection tests live in `tests/test_connect_cpl10.py`.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from cpl10_runs import POSITIVE, cpl10_closed, oracle

from deploy_vii.execution import Execution
from deploy_workflow.owner_workflow import verify_owner_run_receipt
from deploy_workflow.owners import cpl10


@pytest.fixture(scope="module")
def closed(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    return cpl10_closed(POSITIVE, tmp_path_factory.mktemp("cpl10-closed"))


def test_positive_run_settles_restricted_and_the_receipt_verifies(
    closed: tuple[Path, Path],
) -> None:
    store_path, receipt_path = closed
    store = Execution(store_path)
    heads = {h.module_id: h for h in store.read().heads}
    assert [h.status for h in heads.values()] == ["restricted"] * 3
    module = store.head_module(heads["CP-L10"])
    expected: dict[str, Any] = oracle()["expected"]["cases"][POSITIVE]
    assert [t.table_id for t in module.tables] == [t["table_id"] for t in expected["tables"]]
    assert list(module.limitations) == expected["settled_limitations"]
    from deploy_workflow.owner_workflow import OwnerRunReceipt

    receipt = OwnerRunReceipt.model_validate(json.loads(receipt_path.read_text()))
    verify_owner_run_receipt(store, receipt)


def test_consumption_is_recorded_open_and_the_reader_reads_the_head(
    closed: tuple[Path, Path],
) -> None:
    store = Execution(closed[0])
    head = next(h for h in store.read().heads if h.module_id == "CP-L10")
    read = cpl10.cpl10_reader(store, head)
    assert read.result_sha256 == head.result_sha256
    assert oracle()["expected"]["consumption"].startswith("OPEN")
