"""The `read_inputs` views of CP-2D and CP-3C carry a refused context or basis as
`context_issue`, the same text the entry validator returns (ruling P8-R5), and CP-3C keeps its
staleness line when the basis refuses (Phase 8 Task 4, fix 1)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2d as c2d
import test_connect_cp3c as tc3
import test_owner_cp2d_pins as pins2d
import test_owner_cp3c_pins as pins3c
import test_period_basis as tpb
import test_periods_currency_e2e_cp2d as a

from deploy_workflow.owners import cp2d, cp3c
from deploy_workflow.owners.period_basis import DEFAULT_BASIS

REFUSED_CONTEXT = "context-credit_snapshot.json"
EUR_RUN = tpb._context("fy-2026", "EUR")


def _view_2d(store: Any, attempt: Any) -> dict[str, Any]:
    body: dict[str, Any] = json.loads(cp2d.view(store, attempt)[1])
    return body


def _submission_2d() -> cp2d.LiquidityBridgeSubmission:
    return cp2d.LiquidityBridgeSubmission.model_validate_json(c2d._literal("positive"))


def test_cp2d_view_without_a_context_has_no_issue(tmp_path: Path) -> None:
    store, attempt = c2d.make_upstream(tmp_path, "positive")
    body = _view_2d(store, attempt)
    assert "context_issue" not in body and body["cp1_facts"]


def test_cp2d_refused_basis_view_offers_nothing_and_repeats_the_validator_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: EUR_RUN)
    store = c2d.make_store(tmp_path, a.cp1_2026("USD"))
    attempt = store.begin("CP-2D")
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(),
        submission=_submission_2d(),
        upstream=cp2d.cp2d_upstream(store=store, attempt=attempt),
    )
    body = _view_2d(store, attempt)
    assert body["cp1_facts"] == []
    assert issues == (body["context_issue"],)
    assert body["context_issue"].startswith("Period basis refused: ")


def test_cp2d_refused_context_view_keeps_the_parent_facts_and_adds_the_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, attempt = pins2d._seed(tmp_path, monkeypatch, REFUSED_CONTEXT, "positive")
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(),
        submission=pins2d._submission(pins2d._payload("no_context")),
        upstream=pins2d._upstream(store, attempt),
    )
    body = _view_2d(store, attempt)
    assert body["cp1_facts"]
    assert body["context_issue"] == issues[-1]
    assert body["context_issue"].startswith("Context refused: ")


def test_cp3c_refused_basis_view_offers_nothing_and_repeats_the_validator_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, attempt = tc3.seed(tmp_path)
    upstream = tc3.upstream_of(store, attempt)
    submission = tc3.submission_of(store, attempt)
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: EUR_RUN)
    block = cp3c.context_block(pack=pack, upstream=upstream)
    assert block["facts"] == [] and block["facilities"] == []
    assert cp3c._lines(pack, submission, upstream) == (block["context_issue"],)
    assert str(block["context_issue"]).startswith("Period basis refused: ")


def test_cp3c_currency_mismatch_view_offers_nothing_and_repeats_the_validator_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, attempt = tc3.seed(tmp_path)
    upstream = tc3.upstream_of(store, attempt)
    submission = tc3.submission_of(store, attempt)
    eur = replace(DEFAULT_BASIS, currency="EUR", money_unit="EUR m")
    monkeypatch.setattr(cp2d, "run_basis", lambda pack, cp1: eur)
    block = cp3c.context_block(pack=pack, upstream=upstream)
    assert block["facts"] == []
    assert cp3c._lines(pack, submission, upstream) == (block["context_issue"],)
    assert block["context_issue"] == (
        "Period basis refused: run.reporting_currency EUR, but CP-1 reports USD"
    )


def test_cp3c_refused_context_view_keeps_the_parent_facts_and_adds_the_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = pins3c._run(tmp_path, monkeypatch, "match")
    other = pins3c._pack(tmp_path / "other", REFUSED_CONTEXT)
    upstream = tc3.upstream_of(store, attempt)
    block = cp3c.context_block(pack=other, upstream=upstream)
    assert block["facts"]
    assert str(block["context_issue"]).startswith("Context refused: ")
    sub = tc3.submission_of(store, attempt)
    assert cp3c._lines(other, sub, upstream)[-1] == block["context_issue"]


def test_cp3c_keeps_the_stale_line_when_the_basis_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, attempt = tc3.seed(tmp_path)
    upstream = tc3.upstream_of(store, attempt)
    submission = tc3.submission_of(store, attempt)
    stale = replace(upstream, current="Required upstream is unrun, stale or blocked")
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: EUR_RUN)
    lines = cp3c._lines(pack, submission, stale)
    assert any(line.startswith("Stale") for line in lines), lines
    assert lines[-1].startswith("Period basis refused: ")
