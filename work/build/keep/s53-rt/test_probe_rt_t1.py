"""Rewrite tournament T1 spot-check: R6-2 coordinate rule refuses before the audit, and the
order of refusals across _verify's stages is unchanged."""
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from test_owner_g1x import _reseal, _sealed, _verdict, g1x  # noqa: F401

from deploy_workflow import owner_workflow as owner


def _trip(*_a: Any, **_k: Any) -> None:
    raise AssertionError("_verify_audit reached")


def test_genuine_accepted(g1x: SimpleNamespace, tmp_path: Path) -> None:
    receipt = _sealed(tmp_path)
    assert _verdict(tmp_path, receipt) == "accepted"


def test_begin_before_outside_ancestry_refused_before_audit(
    g1x: SimpleNamespace, tmp_path: Path
) -> None:
    receipt = _sealed(tmp_path)
    begin = receipt.begins[0].model_copy(update={"snapshot_before_sha256": "0" * 64})
    forged = receipt.model_copy(update={"begins": (begin, *receipt.begins[1:])})
    _reseal(tmp_path, forged)
    g1x.monkeypatch.setattr(owner, "_verify_audit", _trip)
    assert _verdict(tmp_path, forged) == "identity_mismatch"


def test_head_dropped_from_receipt_refused_before_ancestry(
    g1x: SimpleNamespace, tmp_path: Path
) -> None:
    receipt = _sealed(tmp_path)
    forged = receipt.model_copy(update={"heads": receipt.heads[:-1]})
    _reseal(tmp_path, forged)
    g1x.monkeypatch.setattr(owner, "_snapshot", _trip)
    assert _verdict(tmp_path, forged) == "identity_mismatch"


def test_receipt_snapshot_mismatch_is_stale_binding(g1x: SimpleNamespace, tmp_path: Path) -> None:
    receipt = _sealed(tmp_path)
    forged = receipt.model_copy(update={"snapshot_sha256": "0" * 64})
    assert _verdict(tmp_path, forged) == "stale_binding"
