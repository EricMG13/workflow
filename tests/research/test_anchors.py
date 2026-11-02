"""O7b-1a: check_anchors against expected.json#refusals/anchors and #cp0_cp1_pair."""

from datetime import date
from typing import Any

import pytest

from deploy_vii.contracts import Input, Module, Run
from deploy_vii.execution import Head, head_of
from deploy_workflow.research import anchors as a
from deploy_workflow.research import contracts as c

Pair = tuple[a.SettledAnchor, a.SettledAnchor]


def run_of(manifest: dict[str, Any]) -> Run:
    spec = manifest["run"]
    return Run(
        run_id=spec["run_id"],
        issuer_id=spec["issuer_id"],
        issuer_name=spec["issuer_name"],
        as_of=date.fromisoformat(spec["as_of"]),
        case_kind=spec["case_kind"],
        pathway=spec["pathway"],
        requested_modules=tuple(spec["requested_modules"]),
    )


def settled(
    run: Run, module_id: str, inputs: tuple[Input, ...] = (), **over: Any
) -> a.SettledAnchor:
    module = Module(
        run_id=run.run_id,
        issuer_id=over.get("issuer_id", run.issuer_id),
        as_of=over.get("as_of", run.as_of),
        module_id=module_id,
        status=over.get("status", "restricted"),
        inputs=inputs,
        limitations=("settled with limitations",),
    )
    return a.SettledAnchor(head=head_of(module), module=module)


def pair(
    run: Run, over0: dict[str, Any] | None = None, over1: dict[str, Any] | None = None
) -> Pair:
    cp0 = settled(run, "CP-0", **(over0 or {}))
    cp1 = settled(
        run, "CP-1", (Input(input_id="CP-0", sha256=cp0.head.result_sha256),), **(over1 or {})
    )
    return cp0, cp1


def with_head(anchor: a.SettledAnchor, **update: Any) -> a.SettledAnchor:
    return a.SettledAnchor(anchor.head.model_copy(update=update), anchor.module)


def refused(
    cp0: a.SettledAnchor | None, cp1: a.SettledAnchor | None, run: Run
) -> c.CpDrNotAnchored:
    with pytest.raises(c.CpDrNotAnchored) as caught:
        a.check_anchors(cp0, cp1, run)
    assert type(caught.value).__name__ == "CpDrNotAnchored"
    assert str(caught.value) == caught.value.reason
    return caught.value


def key_reason(expected: dict[str, Any], case: str) -> str:
    key = expected["refusals"]["anchors"][case]
    assert key["exception"] == "CpDrNotAnchored" and key["research_brief_json_written"] is False
    return str(key["reason"])


def test_settled_pair_anchors(manifest: dict[str, Any], expected: dict[str, Any]) -> None:
    run = run_of(manifest)
    cp0, cp1 = pair(run)
    assert set(expected["cp0_cp1_pair"]["statuses"].values()) <= {"accepted", "restricted"}
    anchor = a.check_anchors(cp0, cp1, run)
    assert anchor == c.Anchor(cp0_sha256=cp0.head.result_sha256, cp1_sha256=cp1.head.result_sha256)
    cp0, cp1 = pair(run, {"status": "accepted"}, {"status": "accepted"})
    assert a.check_anchors(cp0, cp1, run).cp1_sha256 == cp1.head.result_sha256


def test_status_refusals_equal_the_key(manifest: dict[str, Any], expected: dict[str, Any]) -> None:
    run = run_of(manifest)
    cp0, cp1 = pair(run)
    cases = [
        ("blocked_cp0", with_head(cp0, status="blocked"), cp1),
        ("blocked_cp1", cp0, with_head(cp1, status="blocked")),
        ("stale_head", with_head(cp0, status="stale"), cp1),
    ]
    for case, first, second in cases:
        assert refused(first, second, run).reason == key_reason(expected, case)


def test_identity_refusals_equal_the_key(
    manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    run = run_of(manifest)
    for case, over in (
        ("issuer_mismatch", {"issuer_id": "other-issuer"}),
        ("period_mismatch", {"as_of": date(2025, 12, 31)}),
    ):
        cp0, cp1 = pair(run, over, over)
        assert refused(cp0, cp1, run).reason == key_reason(expected, case)


def test_input_cp0_hash_altered_by_one_digit(
    manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    run = run_of(manifest)
    cp0, cp1 = pair(run)
    good = cp0.head.result_sha256
    bad = good[:-1] + ("0" if good[-1] != "0" else "1")
    altered = with_head(cp1, inputs=(Input(input_id="CP-0", sha256=bad),))
    assert refused(cp0, altered, run).reason == key_reason(expected, "input_cp0_hash")


def test_mixed_identity_names_each_head(manifest: dict[str, Any]) -> None:
    run = run_of(manifest)
    cp0, cp1 = pair(run, {"issuer_id": "other-issuer"})
    assert (
        "CP-0 head carries other-issuer and CP-1 head carries northbridge"
        in refused(cp0, cp1, run).reason
    )


def test_unsound_pairs_are_named(manifest: dict[str, Any]) -> None:
    run = run_of(manifest)
    cp0, cp1 = pair(run)
    forged = a.SettledAnchor(
        Head(**{**cp0.head.model_dump(), "result_sha256": "f" * 64}), cp0.module
    )
    assert refused(None, cp1, run).reason == "CP-0 head is missing"
    assert refused(cp0, None, run).reason == "CP-1 head is missing"
    assert refused(cp1, cp0, run).reason == "CP-0 slot holds module CP-1"
    assert refused(cp0, with_head(cp1, inputs=()), run).reason == "CP-1 head records no CP-0 input"
    assert refused(forged, cp1, run).reason == (
        "CP-0 head result_sha256 is not the hash of its settled module"
    )


def test_status_is_checked_before_identity(
    manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    run = run_of(manifest)
    cp0, cp1 = pair(run, {"issuer_id": "other-issuer"})
    assert refused(with_head(cp0, status="blocked"), cp1, run).reason == key_reason(
        expected, "blocked_cp0"
    )
