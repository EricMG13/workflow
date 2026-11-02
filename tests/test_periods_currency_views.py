"""Probe B: a pack whose context is refused (pathway mismatch, the frozen pins-context case
`context-credit_snapshot.json` on the CP-2D / CP-3C base run).

Property (parent behaviour, and the P6-P3 contract that a refused context is one bounded
`Context refused:` issue at the validator): the step's read view still renders, so the model can
reach the validator. Exit 0 = the view renders; exit 1 = the view raises.

Run: PYTHONPATH=<tree>/tests:<tree>/src .venv/bin/python -m pytest -q -p no:cacheprovider <this>
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import test_connect_cp2d as c2d
import test_connect_cp3c as tc3
import test_owner_cp2d_pins as pins2d
import test_owner_cp3c_pins as pins3c

from deploy_workflow.owners import cp2d, cp3c

REFUSED_CONTEXT = "context-credit_snapshot.json"


def test_cp2d_view_renders_under_a_refused_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, attempt = pins2d._seed(tmp_path, monkeypatch, REFUSED_CONTEXT, "positive")
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(),
        submission=pins2d._submission(pins2d._payload("no_context")),
        upstream=pins2d._upstream(store, attempt),
    )
    assert issues and issues[-1].startswith("Context refused: ")  # the validator's contract
    _digest, body = cp2d.view(store, attempt)  # parent: renders; new: raises ContextRefused
    assert json.loads(body)["cp1_facts"]


def test_cp3c_view_renders_under_a_refused_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = pins3c._run(tmp_path, monkeypatch, "match")
    other = pins3c._pack(tmp_path / "other", REFUSED_CONTEXT)
    upstream = tc3.upstream_of(store, attempt)
    block = cp3c.context_block(pack=other, upstream=upstream)  # parent renders; new raises?
    assert block["facts"]


def test_cp2d_view_renders_under_a_refused_basis_r4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R4 (`expected.json#runs/R4/modules/CP-2D`: refused at the entry validator). The workflow
    reads the view first (owner_workflow.py:2252 refuses a submit with no read), so the view
    must not raise for the validator's refusal to be reachable. New tree only (the parent has no
    basis); exit 1 = PeriodRefused escapes the view."""
    import test_periods_currency_e2e_cp2d as a

    monkeypatch.setattr(cp2d, "context_facts", lambda pack: a.CONTEXT)
    store = c2d.make_store(tmp_path, a.cp1_2026("USD"))
    attempt = store.begin("CP-2D")
    sub = cp2d.LiquidityBridgeSubmission.model_validate_json(c2d._literal("positive"))
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(), submission=sub, upstream=cp2d.cp2d_upstream(store=store, attempt=attempt)
    )
    assert any("reporting_currency EUR, but CP-1 reports USD" in i for i in issues)
    cp2d.view(store, attempt)


def test_cp2d_view_renders_under_a_blank_eur_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import test_period_basis as tpb

    monkeypatch.setattr(cp2d, "context_facts", lambda pack: tpb._context("", "EUR"))
    store, attempt = c2d.make_upstream(tmp_path, "positive")
    cp2d.view(store, attempt)
