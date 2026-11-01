"""Cap-enforcing budget and durable markers. Real files in tmp_path, no network."""

import json
import os
from decimal import Decimal
from pathlib import Path

import pytest

from deploy_workflow.model.budget import (
    Budget,
    BudgetError,
    BudgetExhausted,
    DuplicateCall,
    OverrunStop,
    RetryUsed,
    RunStopped,
)

D = Decimal
CFG = "sol-medium"


def _marker_dir(run_dir: Path) -> Path:
    return run_dir / "owner-run-audit" / "reservations"


def _reserve(b: Budget, call_id: str, usd: str, retry_of: str | None = None) -> None:
    b.reserve(call_id, D(usd), retry_of, config_id=CFG)


def test_cap_arithmetic(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.6")
    with pytest.raises(BudgetExhausted):
        _reserve(b, "b", "0.5")
    assert b.reserved == D("0.6")
    assert not (_marker_dir(tmp_path) / "b").exists()
    b.settle("a", D("0.4"))
    assert (b.reserved, b.spent) == (D(0), D("0.4"))
    _reserve(b, "c", "0.5")
    _reserve(b, "d", "0.1")  # exactly to the cap
    with pytest.raises(BudgetExhausted):
        _reserve(b, "e", "0.01")


def test_overrun_is_recorded_in_full_and_stops(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.1")
    with pytest.raises(OverrunStop):
        b.settle("a", D("0.3"))
    assert b.spent == D("0.3") and b.reserved == D(0)
    with pytest.raises(RunStopped):
        _reserve(b, "b", "0.1")
    assert Budget(D("1"), tmp_path).spent == D("0.3")
    with pytest.raises(RunStopped):
        _reserve(Budget(D("1"), tmp_path), "b", "0.1")


def test_unknown_keeps_hold_and_stops(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.1")
    b.settle("a", None)
    assert b.spent == D("0.1") and b.reserved == D(0)
    with pytest.raises(RunStopped):
        _reserve(b, "b", "0.1")


def test_retry_of_a_5xx_hold_once(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.1")
    b.settle("a", None, retryable=True)
    _reserve(b, "a2", "0.1", retry_of="a")
    assert b.spent == D("0.1") and b.reserved == D("0.1")  # the hold stays counted
    b.settle("a2", None, retryable=True)
    with pytest.raises(RetryUsed):
        _reserve(b, "a3", "0.1", retry_of="a2")
    with pytest.raises(RunStopped):
        _reserve(b, "a4", "0.1")


def test_retry_needs_a_retryable_unknown_hold_and_cap_room(tmp_path: Path) -> None:
    b = Budget(D("0.25"), tmp_path)
    _reserve(b, "a", "0.1")
    b.settle("a", None)  # not marked retryable
    with pytest.raises(RunStopped):
        _reserve(b, "r", "0.1", retry_of="a")
    b2 = Budget(D("0.15"), tmp_path / "second")
    _reserve(b2, "a", "0.1")
    b2.settle("a", None, retryable=True)
    with pytest.raises(BudgetExhausted):  # 0.1 held + 0.1 > 0.15
        _reserve(b2, "r", "0.1", retry_of="a")
    _reserve(b2, "r", "0.05", retry_of="a")  # the retry was not consumed by the refusal


def test_retry_of_a_known_or_overrun_call_is_refused(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.1")
    with pytest.raises(OverrunStop):
        b.settle("a", D("0.2"))
    with pytest.raises(RunStopped):
        _reserve(b, "r", "0.1", retry_of="a")
    with pytest.raises(RunStopped):
        _reserve(b, "r", "0.1", retry_of="never-seen")


def test_marker_exists_before_return_and_is_create_once(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.25")
    path = _marker_dir(tmp_path) / "a"
    assert json.loads(path.read_text())["usd"] == "0.25"
    assert json.loads(path.read_text())["config_id"] == CFG
    with pytest.raises(DuplicateCall):
        _reserve(b, "a", "0.25")
    assert b.reserved == D("0.25")
    b.settle("a", D("0.2"))
    assert (_marker_dir(tmp_path) / "a.settled").exists()
    with pytest.raises(DuplicateCall):
        b.settle("a", D("0.2"))
    with pytest.raises(DuplicateCall):
        b.release("a")


def test_new_budget_recomputes_from_markers(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.25")
    _reserve(b, "b", "0.25")
    b.settle("b", D("0.1"))
    _reserve(b, "c", "0.25")
    b.release("c")
    again = Budget(D("1"), tmp_path)
    assert (again.reserved, again.spent) == (D("0.25"), D("0.1"))
    assert again.unsettled == ("a",)
    with pytest.raises(DuplicateCall):
        _reserve(again, "a", "0.1")


def test_unknown_stop_survives_a_restart(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.1")
    b.settle("a", None, retryable=True)
    again = Budget(D("1"), tmp_path)
    with pytest.raises(RunStopped):
        _reserve(again, "b", "0.1")
    _reserve(again, "r", "0.1", retry_of="a")
    with pytest.raises(RetryUsed):
        _reserve(Budget(D("1"), tmp_path), "r2", "0.1", retry_of="a")


def test_release_frees_the_hold(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.9")
    b.release("a")
    assert (b.reserved, b.spent) == (D(0), D(0))
    _reserve(b, "b", "1")


def test_corrupt_or_orphan_markers_fail_closed(tmp_path: Path) -> None:
    Budget(D("1"), tmp_path)
    (_marker_dir(tmp_path) / "a").write_text("{not json")
    with pytest.raises(BudgetError):
        Budget(D("1"), tmp_path)
    (_marker_dir(tmp_path) / "a").unlink()
    (_marker_dir(tmp_path) / "z.settled").write_text(
        json.dumps({"status": "settled", "usd": "0", "retryable": False})
    )
    with pytest.raises(BudgetError):
        Budget(D("1"), tmp_path)


def test_inputs_are_validated(tmp_path: Path) -> None:
    with pytest.raises(BudgetError):
        Budget(0.5, tmp_path)  # type: ignore[arg-type]
    b = Budget(D("1"), tmp_path)
    for bad_id in ("", "../x", "a.settled", "a/b"):
        with pytest.raises(BudgetError):
            _reserve(b, bad_id, "0.1")
    with pytest.raises(BudgetError):
        b.reserve("f", 0.1, config_id=CFG)  # type: ignore[arg-type]
    with pytest.raises(BudgetError):
        _reserve(b, "n", "-0.1")
    with pytest.raises(BudgetError):
        b.settle("never-reserved", D(0))
    _reserve(b, "g", "0.1")
    with pytest.raises(BudgetError):
        b.settle("g", D("NaN"))


def test_marker_is_fsynced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    synced: list[int] = []
    real = os.fsync

    def recording_fsync(fd: int) -> None:
        synced.append(fd)
        real(fd)

    monkeypatch.setattr(os, "fsync", recording_fsync)
    _reserve(Budget(D("1"), tmp_path), "a", "0.1")
    assert len(synced) == 2  # the file and its directory
