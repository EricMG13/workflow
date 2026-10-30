"""Probe: the CP-OS test's verifier cache is keyed on the store PATH, not store content.

A store edited in place after one accepted verification is never re-verified by the fixture.
Run from the s3-i4 tree: PYTHONPATH=src:tests python -m pytest -q -p no:cacheprovider <this file>
Exit 0 = defect reproduced (the in-place edit is hidden).
"""
import hashlib
from pathlib import Path

import test_owner_cpos as t
from deploy_vii.execution import Execution
from test_owner_cpos import verifier_runs_once_per_receipt_and_store  # noqa: F401  (autouse)

from deploy_workflow.owners import cpos


class _Receipt:
    def content_hash(self) -> str:
        return "r"


def _digest(d: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(d.rglob("*")):
        if p.is_file():
            h.update(p.name.encode() + p.read_bytes())
    return h.hexdigest()


def test_in_place_store_edit_is_hidden_by_the_cache(tmp_path, monkeypatch):
    store_dir = tmp_path / "store"
    store_dir.mkdir()
    (store_dir / "f").write_text("genuine")
    accepted = _digest(store_dir)
    calls = []

    def fake_verifier(store, receipt, *, publication_directory=None):
        calls.append(1)
        if _digest(store.directory) != accepted:
            raise ValueError("store changed")

    monkeypatch.setattr(t, "verify_owner_run_receipt", fake_verifier)
    store = Execution(store_dir) if False else type("S", (), {"directory": store_dir})()
    cpos.verify_owner_run_receipt(store, _Receipt(), publication_directory=tmp_path / "model")
    (store_dir / "f").write_text("tampered in place")
    # A content-keyed cache would re-verify and raise; the path-keyed one returns silently.
    cpos.verify_owner_run_receipt(store, _Receipt(), publication_directory=tmp_path / "model")
    assert calls == [1], calls
