"""P8-R5 on a 2026 run: a refused context (pathway mismatch, `context-credit_snapshot.json`) over a
2026 CP-1 (probe A's R6 CP-1, USD-stamped). P8-R5: the view never raises on a context refusal,
carries `context_issue`, and the entry validator refuses with that single line. Exit 0 = so;
exit 1 = the default-basis fallback (2025 bindings) raises at selection instead."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2d as c2d
import test_owner_cp2d_pins as p2
import test_period_basis as tpb
import test_periods_currency_e2e_cp2d as a

from deploy_workflow.owners import cp2d


def _store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any]:
    pack = p2._pack(tmp_path, "context-credit_snapshot.json")
    monkeypatch.setattr(c2d, "PACK", pack)
    store = c2d.make_store(tmp_path / "run", a.cp1_2026("USD"))
    return store, store.begin("CP-2D")


def test_cp2d_view_under_a_refused_context_on_a_2026_cp1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, attempt = _store(tmp_path, monkeypatch)
    import json

    body = json.loads(cp2d.view(store, attempt)[1])
    assert body["context_issue"].startswith("Context refused: run.pathway")


def test_cp2d_validator_under_a_refused_context_on_a_2026_cp1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, attempt = _store(tmp_path, monkeypatch)
    sub = cp2d.LiquidityBridgeSubmission.model_validate_json(c2d._literal("positive"))
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(), submission=sub, upstream=cp2d.cp2d_upstream(store=store, attempt=attempt)
    )
    assert issues and issues[-1].startswith("Context refused: run.pathway"), issues


def test_cp3c_view_under_a_refused_context_on_a_2026_cp1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import test_connect_cp3c as tc3
    import test_owner_cp3c_pins as p3
    import test_periods_currency_e2e_cp3c as a2

    from deploy_workflow import context as ctx
    from deploy_workflow.owners import cp3c

    usd = tpb._context("fy-2026", "USD")
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: usd)  # CP-2D settles as a 2026 run
    store, _ = tc3.make_store(
        tmp_path / "s", "positive", cp1=a2.cp1_for(tc3.make_pack().run, "USD")
    )
    attempt = store.begin("CP-3C")
    monkeypatch.setattr(cp2d, "context_facts", ctx.context_facts)  # the real reader again
    other = p3._pack(tmp_path / "other", "context-credit_snapshot.json")
    block = cp3c.context_block(pack=other, upstream=tc3.upstream_of(store, attempt))
    assert str(block["context_issue"]).startswith("Context refused: run.pathway")


def test_cp3c_select_names_the_run_unit_in_the_unsourced_currency_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    import test_connect_cp3c as tc3
    import test_method_cp3c as tm3

    from deploy_workflow.owners import cp3c
    from deploy_workflow.owners.period_basis import DEFAULT_BASIS

    store, _, attempt = tc3.seed(tmp_path)
    upstream = tc3.upstream_of(store, attempt)
    real_cp1, real_cp2d = cp3c.select_cp1, cp3c.select_cp2d
    shell = tm3._inputs("positive")

    def unknown(cp1: Any, cp2d: Any) -> tuple[Any, Any]:
        carrier = replace(shell, cp1=cp1, cp2d=cp2d)
        carrier = tc3._every_millions_fact(tc3._without_cash(carrier), tc3._missing)
        return carrier.cp1, carrier.cp2d

    def select_cp1(module: Any, basis: Any) -> Any:
        sel = real_cp1(module, basis)
        return replace(sel, operands=unknown(sel.operands, shell.cp2d)[0])

    def select_cp2d(*args: Any) -> tuple[Any, Any]:
        ops, offered = real_cp2d(*args)
        return unknown(shell.cp1, ops)[1], offered

    monkeypatch.setattr(cp3c, "select_cp1", select_cp1)
    monkeypatch.setattr(cp3c, "select_cp2d", select_cp2d)
    eur = replace(DEFAULT_BASIS, currency="EUR", money_unit="EUR m")
    with pytest.raises(ValueError, match="no known EUR m fact states a currency"):
        cp3c.select(upstream, eur)
