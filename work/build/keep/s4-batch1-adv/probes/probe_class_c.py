"""Stage 4 batch 1 adversary probes, class C: forged raw payloads in the audit store, the
binding, submission, receipt and seal made consistent. Expect identity_mismatch, never
TypeError or RecursionError."""
import hashlib
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from deploy_vii.execution import Execution

import test_owner_g1x as g
from test_owner_g1x import g1x  # noqa: F401

owner = g.owner

CASES: dict[str, bytes] = {
    "nest65": ('{"note":"x","tags":' + "[" * 65 + "]" * 65 + "}").encode(),
    "nest300": ('{"note":"x","tags":' + "[" * 300 + "]" * 300 + "}").encode(),
    "nest5000": ('{"note":"x","tags":' + "[" * 5000 + "]" * 5000 + "}").encode(),
    "tag-dict": b'{"note":"x","parts":[{"kind":{"a":1},"text":"t"}]}',
    "tag-list": b'{"note":"x","parts":[{"kind":["prose"],"text":"t"}]}',
    "surrogate-escaped": b'{"note":"\\ud800"}',
    "surrogate-cesu-bytes": b'{"note":"\xed\xa0\x80"}',
    "nested-parts-300": ('{"note":"x","parts":[' + '{"kind":"prose","text":' * 1 + '"t"}' + "]}").encode(),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_forged_raw_payload(g1x: SimpleNamespace, tmp_path: Path, case: str) -> None:
    receipt = g._sealed(tmp_path / "run")
    root = tmp_path / case
    shutil.copytree(tmp_path / "run", root)
    store = Execution(root / "store")
    old = next(s for s in receipt.submissions if s.binding.binding.step_id == g.VIEWED)
    raw = CASES[case]
    digest = hashlib.sha256(raw).hexdigest()
    owner._put(owner._audit(store, "payloads", digest), raw)
    nb = old.binding.model_copy(update={"payload_sha256": digest})
    ns = old.model_copy(update={"binding": nb})
    forged = receipt.model_copy(
        update={"submissions": tuple(ns if s == old else s for s in receipt.submissions)}
    )
    g._swap(root, "bindings", old.binding, nb)
    g._swap(root, "submissions", old, ns)
    g._reseal(root, forged)
    try:
        verdict = g._verdict(root, forged)
    except BaseException as error:  # the probe reports what escapes; it does not hide it
        verdict = "RAISED " + type(error).__name__
    print("VERDICT", case, verdict)
    assert verdict == "identity_mismatch"
