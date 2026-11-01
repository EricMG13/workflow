"""The host keeps no second parsed copy of a settled module (stage 8 F1).

`deploy_vii.execution._canonical_result` is the only result parse cache, so a result blob is parsed
once per process whether it is read through `Execution` or through the host's `_ParsedExecution`.
"""

from datetime import date
from pathlib import Path

import pytest

from deploy_vii.contracts import Module
from deploy_vii.execution import Execution, _canonical_result
from deploy_workflow.host import _ParsedExecution


def _module() -> Module:
    return Module(run_id="run-1", issuer_id="issuer-1", as_of=date(2026, 1, 1), module_id="CP-0")


def _store(directory: Path) -> Execution:
    (directory / "blobs").mkdir(parents=True)
    return Execution(directory)


@pytest.fixture(autouse=True)
def _cold_cache() -> None:
    _canonical_result.cache_clear()


def test_host_and_execution_share_one_parsed_module(tmp_path: Path) -> None:
    store = _store(tmp_path / "a")
    sha = store._store(_module().model_dump_json())
    via_host = _ParsedExecution(store.directory).result(sha)
    via_execution = Execution(store.directory).result(sha)
    assert via_host is via_execution
    assert via_host == _module()


def test_tampered_blob_still_refuses_through_the_host_store(tmp_path: Path) -> None:
    store = _store(tmp_path / "a")
    sha = store._store(_module().model_dump_json())
    host_store = _ParsedExecution(store.directory)
    host_store.result(sha)
    path = store.directory / "blobs" / sha
    path.chmod(0o644)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        host_store.result(sha)
