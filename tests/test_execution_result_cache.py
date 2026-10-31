"""`Execution.result` parses each verified blob once per process (perf sweep P3).

The blob is still read and hash-checked on every call, so a missing or tampered blob refuses as
before; only the pydantic parse of bytes already proven identical is skipped.
"""

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.contracts import Module
from deploy_vii.execution import Execution, _canonical_result


def _module() -> Module:
    return Module(run_id="run-1", issuer_id="issuer-1", as_of=date(2026, 1, 1), module_id="CP-0")


def _store(directory: Path) -> Execution:
    (directory / "blobs").mkdir(parents=True)
    return Execution(directory)


def _blob(store: Execution, sha256: str) -> Path:
    path = store.directory / "blobs" / sha256
    path.chmod(0o644)
    return path


@pytest.fixture(autouse=True)
def _cold_cache() -> None:
    _canonical_result.cache_clear()


def test_two_reads_parse_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(tmp_path / "a")
    module = _module()
    sha = store._store(module.model_dump_json())
    parse: Callable[..., Module] = Module.model_validate_json
    calls: list[bytes] = []

    def counted(raw: Any, *args: Any, **kwargs: Any) -> Module:
        calls.append(raw)
        return parse(raw, *args, **kwargs)

    monkeypatch.setattr(Module, "model_validate_json", counted)
    first = store.result(sha)
    second = store.result(sha)
    assert len(calls) == 1
    assert first == module
    assert second == first


def test_cached_hit_still_refuses_tampered_or_missing_blob(tmp_path: Path) -> None:
    store = _store(tmp_path / "a")
    sha = store._store(_module().model_dump_json())
    store.result(sha)
    path = _blob(store, sha)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        store.result(sha)
    path.unlink()
    with pytest.raises(ValueError, match="is missing"):
        store.result(sha)


def test_non_canonical_bytes_refuse_and_are_not_cached(tmp_path: Path) -> None:
    store = _store(tmp_path / "a")
    sha = store._store(_module().model_dump_json() + " ")
    for _ in range(2):
        with pytest.raises(ValueError) as caught:
            store.result(sha)
        assert str(caught.value) == "Execution result blob is not the canonical module"


def test_cache_is_keyed_by_bytes_not_by_store(tmp_path: Path) -> None:
    module = _module()
    first = _store(tmp_path / "a")
    sha = first._store(module.model_dump_json())
    assert first.result(sha) == module
    second = _store(tmp_path / "b")
    with pytest.raises(ValueError, match="is missing"):
        second.result(sha)
    assert second._store(module.model_dump_json()) == sha
    assert second.result(sha) == module
