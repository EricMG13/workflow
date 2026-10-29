"""Fast checks of the CP-2G driver's readiness payload selection (no workflow, no run)."""

import json

import cp2g_runs
import pytest


@pytest.mark.parametrize("owner", ["cp2g", "cp2h", "cp4c"])
def test_every_oracle_readiness_literal_submits_only_the_schema_keys(owner: str) -> None:
    path = cp2g_runs.ROOT / "cases" / f"{owner}-owner" / "submissions.json"
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    assert cases
    for name, case in cases.items():
        if "cp1_readiness" not in case:
            continue
        payload = cp2g_runs.readiness_payload(case["cp1_readiness"])
        assert set(payload) == {"inputs_sha256", "consumers"}, name
        assert "note" not in payload


def test_unknown_readiness_key_fails_closed() -> None:
    literal = {"inputs_sha256": "x", "consumers": [], "note": "n", "extra": 1}
    with pytest.raises(RuntimeError, match="extra"):
        cp2g_runs.readiness_payload(literal)


def test_missing_readiness_key_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="consumers"):
        cp2g_runs.readiness_payload({"inputs_sha256": "x", "note": "n"})
