"""Rewrite tournament T2 spot-check (plan class B2): a refused record whose issues are dropped or
reordered does not reproduce its recomputed gate issues and is refused."""
import re
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_owner_g1x import (  # noqa: F401
    GATE_MARK,
    MODULE,
    _refused_then_sealed,
    _reseal,
    _swap,
    _verdict,
    g1x,
)

from deploy_vii.execution import bounded_issues
from deploy_workflow import owner_workflow as owner


@pytest.mark.parametrize("change", ["drop", "reorder", "invalid"])
def test_refused_issue_forgeries_refuse(g1x: SimpleNamespace, tmp_path: Path, change: str) -> None:
    lines = tuple(f"{i:03d} issue" for i in range(5))
    g1x.monkeypatch.setitem(
        owner._PRECHECKS, MODULE, lambda store, binding, stored: lines if GATE_MARK in stored else ()
    )
    shown = bounded_issues(lines)
    receipt = _refused_then_sealed(tmp_path / "run", shown)
    assert _verdict(tmp_path / "run", receipt) == "accepted"
    old = next(s for s in receipt.submissions if s.disposition == "refused")
    update = {
        "drop": {"issues": old.issues[:-1]},
        "reorder": {"issues": tuple(reversed(old.issues))},
        "invalid": {"disposition": "invalid"},
    }[change]
    new = old.model_copy(update=update)
    forged = receipt.model_copy(
        update={"submissions": tuple(new if s == old else s for s in receipt.submissions)}
    )
    root = tmp_path / "forged"
    shutil.copytree(tmp_path / "run", root)
    _swap(root, "submissions", old, new)
    _reseal(root, forged)
    assert re.fullmatch("identity_mismatch", _verdict(root, forged))
