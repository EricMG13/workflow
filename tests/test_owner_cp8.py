"""CP-8 store runs, consumption (D3, OPEN) and tamper: DEFERRED to Stage 5, written here unrun.

Run: PYTHONPATH=src ".venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_owner_cp8.py
Expected values are read from `cases/cp8-owner/expected.json` only.
"""

from pathlib import Path
from typing import Any

import cp8_runs as runs
import pytest

from deploy_vii.execution import Execution
from deploy_workflow.owners import cp8

EXPECTED = runs.oracle()["expected"]


def _head(root: Path) -> Any:
    store = Execution(root / "store")
    head = next(h for h in store.read().heads if h.module_id == "CP-8")
    return store, head


@pytest.mark.parametrize("case", ["positive", "no_outcome"])
def test_closed_run_settles_restricted_with_the_expected_tables(case: str, tmp_path: Path) -> None:
    runs.cp8_closed(case, tmp_path)
    store, head = _head(tmp_path)
    module = store.head_module(head)
    expected = EXPECTED["cases"][case]
    assert head.status == module.status == expected["status"]
    assert [i.input_id for i in module.inputs] == expected["module_inputs"]
    assert [t.table_id for t in module.tables] == [t["table_id"] for t in expected["tables"]]
    assert [c.claim_id for c in module.claims] == [c["claim_id"] for c in expected["claims"]]
    assert module.limitations == tuple(expected["own_limitations"])


def test_receipt_verifies_and_probe_rebuilds(tmp_path: Path) -> None:
    from deploy_workflow import owner_workflow as owner

    workflow, _ = runs.cp8_closed("positive", tmp_path)
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    owner.verify_owner_run_receipt(Execution(tmp_path / "store"), receipt)
    store, head = _head(tmp_path)
    snapshot = store.read()
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    cp8.probe(store, snapshot, attempt)


def test_d3_the_reader_exposes_the_pinned_head_and_claims_no_consumption(tmp_path: Path) -> None:
    """D3 is OPEN (lease :93): no consumer core reads CP-8. This pins what the reader exposes
    over a settled head and the inputs it hash-binds; it is not a consumption proof."""
    runs.cp8_closed("positive", tmp_path)
    store, head = _head(tmp_path)
    pinned = EXPECTED["consumption"]["reader_pinned"]["positive_values"]
    got = cp8.cp8_reader(store, head)
    assert got.head_sha256 == head.result_sha256
    assert (got.overall_label, got.overall_process_sound) == (
        pinned["overall"],
        pinned["process_sound"],
    )
    assert str(got.window_days) == str(pinned["window_days"])
    assert dict(got.directions) == pinned["directions"]
    assert EXPECTED["consumption"]["status"] == "OPEN"
    cp0 = next(h for h in store.read().heads if h.module_id == "CP-0")
    module = store.head_module(head)
    assert next(i for i in module.inputs if i.input_id == "CP-0").sha256 == cp0.result_sha256
