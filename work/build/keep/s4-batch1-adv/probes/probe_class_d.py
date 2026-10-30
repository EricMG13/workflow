"""Class D (documented known gap): a refused submission deleted, its binding too, later records
renumbered, seal rewritten. The doc says this cannot be detected; the probe records the verdict."""
import shutil
from pathlib import Path
from types import SimpleNamespace

import test_owner_g1x as g
from test_owner_g1x import g1x  # noqa: F401


def test_d_delete_refused_record(g1x: SimpleNamespace, tmp_path: Path) -> None:
    receipt = g._refused_then_sealed(tmp_path / "run")
    root = tmp_path / "deleted"
    shutil.copytree(tmp_path / "run", root)
    old = next(s for s in receipt.submissions if s.disposition == "refused")
    later = [s for s in receipt.submissions if s.sequence > old.sequence]
    renumbered = {s: s.model_copy(update={"sequence": s.sequence - 1}) for s in later}
    g._swap(root, "submissions", old, None)
    if all(s.binding != old.binding for s in receipt.submissions if s != old):
        g._swap(root, "bindings", old.binding, None)
    for s, n in renumbered.items():
        g._swap(root, "submissions", s, n)
    forged = receipt.model_copy(
        update={"submissions": tuple(renumbered.get(s, s) for s in receipt.submissions if s != old)}
    )
    g._reseal(root, forged)
    verdict = g._verdict(root, forged)
    print("VERDICT d-delete-refused", verdict)
    assert verdict == "accepted"  # the documented, unclosed gap (ruling D1)
