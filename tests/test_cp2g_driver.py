"""Fast checks of the CP-2G driver's readiness payload selection (no workflow, no run)."""

import cp2g_runs
import pytest


def test_every_oracle_readiness_literal_submits_only_the_schema_keys() -> None:
    cases = cp2g_runs.oracle()["submissions"]["cases"]
    assert cases
    for name, case in cases.items():
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
