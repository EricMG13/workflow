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
from deploy_workflow.model.pricing import NoPrice

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
    again.settle("a", D("0.1"))
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
    again.settle("r", D("0.1"))
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
    budget = Budget(D("1"), tmp_path)
    synced: list[int] = []
    real = os.fsync

    def recording_fsync(fd: int) -> None:
        synced.append(fd)
        real(fd)

    monkeypatch.setattr(os, "fsync", recording_fsync)
    _reserve(budget, "a", "0.1")
    assert len(synced) == 2  # the file and its directory


def test_crash_left_unsettled_marker_stops_the_run(tmp_path: Path) -> None:
    first = Budget(D("1"), tmp_path)
    _reserve(first, "a", "0.1")
    _reserve(first, "ok", "0.1")
    first.settle("ok", None, retryable=True)
    again = Budget(D("1"), tmp_path)  # "a" has no .settled marker: it may have been sent
    assert again.unsettled == ("a",) and again.reserved == D("0.1")
    with pytest.raises(RunStopped):
        _reserve(again, "b", "0.1")
    with pytest.raises(RunStopped):
        _reserve(again, "b", "0.1", retry_of="a")
    with pytest.raises(RunStopped):  # a legitimate retryable hold does not lift the crash stop
        _reserve(again, "b", "0.1", retry_of="ok")
    again.settle("a", D("0.1"))  # the operator clears it
    _reserve(again, "b", "0.1", retry_of="ok")


def test_in_flight_reservation_does_not_stop_the_same_run(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.1")
    _reserve(b, "b", "0.1")


def test_release_refuses_a_crash_left_id(tmp_path: Path) -> None:
    _reserve(Budget(D("1"), tmp_path), "a", "0.9")
    again = Budget(D("1"), tmp_path)
    with pytest.raises(RunStopped):
        again.release("a")
    assert again.reserved == D("0.9")
    again.settle("a", None)  # unknown keeps it counted and the run stopped
    assert again.spent == D("0.9")
    with pytest.raises(RunStopped):
        _reserve(again, "b", "0.05")


def _unknown_then_retry(tmp_path: Path) -> Budget:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.1")
    b.settle("a", None, retryable=True)
    _reserve(b, "r", "0.1", retry_of="a")
    return b


def test_stop_lifts_only_when_the_retry_settles_with_a_number(tmp_path: Path) -> None:
    b = _unknown_then_retry(tmp_path)
    with pytest.raises(RunStopped):  # retry still in flight
        _reserve(b, "n1", "0.1")
    b.release("r")  # retry never sent
    with pytest.raises(RunStopped):
        _reserve(b, "n2", "0.1")
    with pytest.raises(RetryUsed):  # reserved once means used
        _reserve(b, "r2", "0.1", retry_of="a")
    with pytest.raises(RunStopped):
        _reserve(Budget(D("1"), tmp_path), "n3", "0.1")


def test_retry_settled_unknown_or_overrun_keeps_the_stop(tmp_path: Path) -> None:
    b = _unknown_then_retry(tmp_path)
    b.settle("r", None)
    with pytest.raises(RunStopped):
        _reserve(b, "n", "0.1")
    other = _unknown_then_retry(tmp_path / "o")
    with pytest.raises(OverrunStop):
        other.settle("r", D("0.2"))
    with pytest.raises(RunStopped):
        _reserve(other, "n", "0.1")


def test_retry_settled_with_a_number_lifts_the_stop(tmp_path: Path) -> None:
    b = _unknown_then_retry(tmp_path)
    b.settle("r", D("0.05"))
    _reserve(b, "n", "0.1")
    b.settle("n", D("0.1"))
    _reserve(Budget(D("1"), tmp_path), "n2", "0.1")


def _stopped_by_overrun_and_unknown(tmp_path: Path, other: str) -> Budget:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.1")
    _reserve(b, "b", "0.1")
    b.settle("a", None, retryable=True)
    if other == "overrun":
        with pytest.raises(OverrunStop):
            b.settle("b", D("0.3"))
    else:
        b.settle("b", None)
    return b


@pytest.mark.parametrize("other", ["overrun", "unknown"])
def test_retry_is_refused_while_another_stop_stands(tmp_path: Path, other: str) -> None:
    b = _stopped_by_overrun_and_unknown(tmp_path, other)
    for budget in (b, Budget(D("1"), tmp_path)):
        with pytest.raises(RunStopped):
            _reserve(budget, "r", "0.1", retry_of="a")


def test_retry_is_admitted_when_nothing_else_stands(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.1")
    b.settle("a", None, retryable=True)
    again = Budget(D("1"), tmp_path)
    _reserve(again, "x", "0.1", retry_of="a")  # nothing else stands: admitted


def test_write_failure_sets_a_sticky_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.1")
    real = os.fsync

    def failing(fd: int) -> None:
        if os.path.isdir(f"/dev/fd/{fd}"):
            raise OSError(5, "EIO")
        real(fd)

    monkeypatch.setattr(os, "fsync", failing)
    with pytest.raises(OSError):
        b.settle("a", D("0.3"))
    monkeypatch.setattr(os, "fsync", real)
    with pytest.raises(RunStopped):
        _reserve(b, "n", "0.85")
    with pytest.raises(RunStopped):
        _reserve(b, "r", "0.1", retry_of="a")


def test_reserve_write_failure_sets_a_sticky_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    b = Budget(D("1"), tmp_path)
    real = os.fsync

    def failing(fd: int) -> None:
        raise OSError(5, "EIO")

    monkeypatch.setattr(os, "fsync", failing)
    with pytest.raises(OSError):
        _reserve(b, "a", "0.1")
    monkeypatch.setattr(os, "fsync", real)
    with pytest.raises(RunStopped):
        _reserve(b, "b", "0.1")


def test_directories_created_are_fsynced_into_their_parents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inodes: list[int] = []
    real = os.fsync

    def recording(fd: int) -> None:
        inodes.append(os.fstat(fd).st_ino)
        real(fd)

    monkeypatch.setattr(os, "fsync", recording)
    Budget(D("1"), tmp_path)
    audit = tmp_path / "owner-run-audit"
    assert {tmp_path.stat().st_ino, audit.stat().st_ino} <= set(inodes)


def test_cap_comparison_is_exact(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    _reserve(b, "a", "0.5")
    with pytest.raises(BudgetExhausted):
        _reserve(b, "b", "0.5000000000000000000000000000001")
    c = Budget(D("1"), tmp_path / "full")
    _reserve(c, "a", "1")
    with pytest.raises(BudgetExhausted):
        _reserve(c, "t", "1E-40")


def test_reserve_refuses_an_unpriced_config(tmp_path: Path) -> None:
    b = Budget(D("1"), tmp_path)
    with pytest.raises(NoPrice):
        b.reserve("a", D("0.1"), config_id="opus-high")
    assert not (_marker_dir(tmp_path) / "a").exists()


def test_settled_marker_with_an_unknown_status_fails_closed(tmp_path: Path) -> None:
    _reserve(Budget(D("1"), tmp_path), "a", "0.1")
    (_marker_dir(tmp_path) / "a.settled").write_text(
        json.dumps({"status": "paid", "usd": "0", "retryable": False})
    )
    with pytest.raises(BudgetError):
        Budget(D("1"), tmp_path)


def test_a_sum_wider_than_the_context_is_a_budget_error_and_writes_nothing(tmp_path: Path) -> None:
    b = Budget(D("2"), tmp_path)
    _reserve(b, "a", "1E-130")
    with pytest.raises(BudgetError, match="money sum not exact"):
        _reserve(b, "b", "1")
    assert not (_marker_dir(tmp_path) / "b").exists()


def test_stop_reason_and_settled_calls_read_the_state_without_changing_it(tmp_path: Path) -> None:
    b = Budget(Decimal(1), tmp_path)
    assert b.stop_reason is None and list(b.settled_calls) == []
    _reserve(b, "b-call", "0.1")
    _reserve(b, "a-call", "0.1")
    _reserve(b, "freed", "0.1")
    b.settle("b-call", Decimal("0.05"))
    b.release("freed")
    assert list(b.settled_calls) == [
        "b-call"
    ]  # released holds were never sent; open ones are unsettled
    assert b.stop_reason is None or "unsettled" in b.stop_reason
    again = Budget(Decimal(1), tmp_path)  # a-call is crash-left at load
    assert list(again.settled_calls) == ["b-call"]
    assert again.stop_reason is not None and "crash" in again.stop_reason
    again.settle("a-call", None)
    assert list(again.settled_calls) == ["a-call", "b-call"]  # an unknown charge was sent
    assert again.stop_reason is not None and "'a-call' has an unknown charge" in again.stop_reason
