"""context/1 reader: the form's build() rules (docs/templates/context-form.html)."""

from __future__ import annotations

import copy
import json
import re
from decimal import Decimal
from typing import Any

import pytest

from deploy_workflow.context import SCHEMA, ContextRefused, RunContext, amount, load_context

MINIMAL: dict[str, Any] = {
    "schema": SCHEMA,
    "run": {
        "run_type": "research",
        "pathway": "credit_snapshot",
        "case_kind": "public",
        "as_of": "2026-10-31",
        "current_period": "",
        "prior_period": "",
        "reporting_currency": "USD",
    },
    "identity": {
        "issuer_name": "Acme Corp",
        "issuer_id": "acme",
        "borrower_name": "",
        "parent_name": "",
        "guarantors": [],
        "aliases": [],
        "listed_equity": False,
        "ticker": "",
        "sector": "",
        "country": "",
        "sponsor": "",
    },
    "deal_terms": [],
    "quotes": [],
    "ratings": [],
    "valuation": {
        "peer_source": "cp_dr_public",
        "basis": "auto",
        "issuer_market": {
            "market_cap_m": "",
            "net_debt_m": "",
            "ev_m": "",
            "ebitda_basis": "LTM",
            "as_of": "",
            "source": "",
        },
        "peers": [],
        "precedents": [],
        "user_multiple": {"value": "", "basis": "LTM", "rationale": ""},
    },
    "assumptions": {k: None for k in ("cp2a", "cp2d", "cp2e", "cp3c", "cp3d", "cp4c")},
    "attachments": {
        "portfolio_workbook": False,
        "prior_case": False,
        "management_bridge": False,
        "legal_documents": "executed",
    },
    "research_questions": [],
}

DEAL = {
    "facility_id": "tlb",
    "instrument": "Term loan B",
    "currency": "USD",
    "size_m": "1250",
    "tenor_years": "7",
    "talk_spread_bps_low": "325",
    "talk_spread_bps_high": "350",
    "talk_oid_low": "99.0",
    "talk_oid_high": "99.5",
    "floor_pct": "0.50",
    "call_protection": "",
    "use_of_proceeds": "",
    "as_of": "2026-10-30",
    "provider": "",
}
QUOTE = {
    "facility_id": "tlb",
    "kind": "observed",
    "bid": "98.50",
    "ask": "99.00",
    "price": "",
    "yield_pct": "",
    "spread_bps": "",
    "as_of": "2026-10-30",
    "provider": "Desk",
}
RATING = {"agency": "Fitch", "scope": "issuer", "rating": "B+", "outlook": "", "as_of": ""}
PEER = {
    "name": "Peer",
    "ticker": "",
    "ev_m": "5400",
    "ebitda_m": "600",
    "as_of": "2026-10-01",
    "source": "10-K",
}
PREC = {
    "target": "T",
    "acquirer": "",
    "date": "",
    "ev_m": "1800",
    "ebitda_m": "200",
    "source": "PR",
}
MARKET = {
    "market_cap_m": "",
    "net_debt_m": "",
    "ev_m": "5000",
    "ebitda_basis": "LTM",
    "as_of": "2026-10-30",
    "source": "Bloomberg",
}
PRIMARY = {"run.run_type": "primary", "deal_terms": [DEAL]}


def set_path(base: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    out = copy.deepcopy(base)
    parts = re.findall(r"[^.\[\]]+", path)
    node: Any = out
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    last = parts[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value
    return out


def with_changes(changes: dict[str, Any]) -> dict[str, Any]:
    out = MINIMAL
    for path, value in changes.items():
        out = set_path(out, path, value)
    return out


def pin(**fields: Any) -> dict[str, Any]:
    return {**fields, "rationale": "because"}


def row(base: dict[str, Any], **fields: Any) -> dict[str, Any]:
    return {**base, **fields}


LISTED = {"identity.listed_equity": True}
INVALID_CASES: list[tuple[dict[str, Any], str, str]] = [
    ({"schema": "context/2"}, "schema", "must be"),
    ({"bogus": 1}, "bogus", "Extra inputs"),
    ({"run.bogus": 1}, "run.bogus", "Extra inputs"),
    ({"valuation.issuer_market.bogus": 1}, "valuation.issuer_market.bogus", "Extra inputs"),
    ({"run.run_type": "other"}, "run.run_type", "Input should be"),
    ({"run.pathway": "other"}, "run.pathway", "Input should be"),
    ({"run.as_of": "2026-02-30"}, "run.as_of", "YYYY-MM-DD"),
    ({"run.as_of": ""}, "run.as_of", "required"),
    ({"run.run_type": "earnings"}, "run.current_period", "required"),
    ({"run.run_type": "earnings"}, "run.prior_period", "required"),
    ({"run.current_period": "q5-2026"}, "run.current_period", "lowercase"),
    (
        {"run.current_period": "q2-2026", "run.prior_period": "q2-2026"},
        "run.prior_period",
        "earlier",
    ),
    (
        {"run.current_period": "q1-2026", "run.prior_period": "q4-2026"},
        "run.prior_period",
        "earlier",
    ),
    ({"run.reporting_currency": "usd"}, "run.reporting_currency", "three uppercase"),
    ({"run.reporting_currency": ""}, "run.reporting_currency", "required"),
    ({"identity.issuer_name": ""}, "identity.issuer_name", "required"),
    ({"identity.issuer_id": "-acme"}, "identity.issuer_id", "lowercase"),
    ({"identity.issuer_id": "Acme"}, "identity.issuer_id", "lowercase"),
    ({"identity.issuer_id": "bgs\n"}, "identity.issuer_id", "lowercase"),
    ({"identity.issuer_id": ""}, "identity.issuer_id", "required"),
    ({"identity.ticker": "ACM"}, "identity.ticker", "unlisted"),
    ({"deal_terms": [DEAL]}, "deal_terms", "primary run only"),
    ({"run.run_type": "primary"}, "deal_terms", "at least one"),
    (
        {**PRIMARY, "deal_terms[0].talk_spread_bps_low": "400"},
        "deal_terms[0].talk_spread_bps_low",
        "low must not exceed high",
    ),
    (
        {**PRIMARY, "deal_terms": [row(DEAL, talk_oid_low="100", talk_oid_high="99")]},
        "deal_terms[0].talk_oid_low",
        "low must not exceed high",
    ),
    (
        {**PRIMARY, "deal_terms": [row(DEAL, size_m="1,250")]},
        "deal_terms[0].size_m",
        "thousands separators",
    ),
    (
        {**PRIMARY, "deal_terms": [row(DEAL, size_m="１２５０")]},
        "deal_terms[0].size_m",
        "plain number",
    ),
    (
        {**PRIMARY, "deal_terms": [row(DEAL, size_m="1250\n")]},
        "deal_terms[0].size_m",
        "plain number",
    ),
    ({**PRIMARY, "deal_terms": [row(DEAL, size_m="-5")]}, "deal_terms[0].size_m", "plain number"),
    (
        {**PRIMARY, "deal_terms": [row(DEAL, currency="usd")]},
        "deal_terms[0].currency",
        "three uppercase",
    ),
    (
        {**PRIMARY, "deal_terms": [row(DEAL, as_of="2026-11-01")]},
        "deal_terms[0].as_of",
        "after the run as-of",
    ),
    ({**PRIMARY, "deal_terms": [DEAL] * 21}, "deal_terms", "at most 20"),
    ({"quotes": [row(QUOTE, as_of="2026-11-01")]}, "quotes[0].as_of", "after the run as-of"),
    ({"quotes": [row(QUOTE, provider="")]}, "quotes[0].provider", "required"),
    ({"quotes": [row(QUOTE, bid="99.5", ask="99")]}, "quotes[0].bid", "bid must not exceed ask"),
    ({"quotes": [row(QUOTE, kind="other")]}, "quotes[0].kind", "Input should be"),
    ({"quotes": [QUOTE] * 41}, "quotes", "at most 40"),
    ({"ratings": [row(RATING, as_of="2026-11-01")]}, "ratings[0].as_of", "after the run as-of"),
    ({"ratings": [row(RATING, agency="")]}, "ratings[0].agency", "required"),
    ({"ratings": [RATING] * 21}, "ratings", "at most 20"),
    (
        {"valuation.peer_source": "none", "valuation.peers": [PEER]},
        "valuation.peers",
        "must be empty",
    ),
    ({"valuation.peers": [PEER]}, "valuation.peers", "must be empty"),
    (
        {"valuation.peer_source": "user_comps", "valuation.peers": [row(PEER, as_of="2026-11-01")]},
        "valuation.peers[0].as_of",
        "after the run as-of",
    ),
    (
        {"valuation.peer_source": "user_comps", "valuation.peers": [row(PEER, ebitda_m="0")]},
        "valuation.peers[0].ebitda_m",
        "above 0",
    ),
    (
        {"valuation.peer_source": "user_comps", "valuation.peers": [PEER] * 31},
        "valuation.peers",
        "at most 30",
    ),
    (
        {"valuation.peer_source": "user_list", "valuation.peers": [row(PEER, name="")]},
        "valuation.peers[0].name",
        "required",
    ),
    (
        {"valuation.basis": "issuer_trading", "valuation.issuer_market": MARKET},
        "valuation.basis",
        "listed issuer",
    ),
    (
        {
            **LISTED,
            "valuation.basis": "issuer_trading",
            "valuation.issuer_market": row(MARKET, as_of="2026-11-01"),
        },
        "valuation.issuer_market.as_of",
        "after the run as-of",
    ),
    (
        {
            **LISTED,
            "valuation.basis": "issuer_trading",
            "valuation.issuer_market": row(MARKET, ev_m=""),
        },
        "valuation.issuer_market.ev_m",
        "give EV",
    ),
    (
        {"valuation.basis": "precedents", "valuation.precedents": [row(PREC, ebitda_m="0")]},
        "valuation.precedents[0].ebitda_m",
        "above 0",
    ),
    (
        {"valuation.basis": "blend", "valuation.precedents": [row(PREC, date="2026-11-01")]},
        "valuation.precedents[0].date",
        "after the run as-of",
    ),
    (
        {
            "valuation.basis": "user_multiple",
            "valuation.user_multiple": {"value": "0", "basis": "LTM", "rationale": "r"},
        },
        "valuation.user_multiple.value",
        "above 0",
    ),
    (
        {
            "valuation.basis": "user_multiple",
            "valuation.user_multiple": {"value": "100", "basis": "LTM", "rationale": "r"},
        },
        "valuation.user_multiple.value",
        "99.99 or less",
    ),
    (
        {
            "valuation.basis": "user_multiple",
            "valuation.user_multiple": {"value": "6", "basis": "LTM", "rationale": ""},
        },
        "valuation.user_multiple.rationale",
        "required",
    ),
    ({"assumptions.cp2a": pin(scenarios=[])}, "assumptions.cp2a.scenarios", "1 to 4"),
    (
        {
            "assumptions.cp2a": pin(
                scenarios=[{"ebitda_decline_pct": "10", "interest_increase_pct": "5"}] * 5
            )
        },
        "assumptions.cp2a.scenarios",
        "1 to 4",
    ),
    (
        {
            "assumptions.cp2a": pin(
                scenarios=[{"ebitda_decline_pct": "101", "interest_increase_pct": "5"}]
            )
        },
        "assumptions.cp2a.scenarios[0].ebitda_decline_pct",
        "100 or less",
    ),
    (
        {"assumptions.cp2d": pin(horizon_months="0", minimum_cash_m="1")},
        "assumptions.cp2d.horizon_months",
        "1 or more",
    ),
    (
        {"assumptions.cp2d": pin(horizon_months="61", minimum_cash_m="1")},
        "assumptions.cp2d.horizon_months",
        "60 or less",
    ),
    (
        {"assumptions.cp2d": pin(horizon_months="12.5", minimum_cash_m="1")},
        "assumptions.cp2d.horizon_months",
        "whole number",
    ),
    (
        {"assumptions.cp2d": pin(horizon_months="", minimum_cash_m="1")},
        "assumptions.cp2d.horizon_months",
        "required",
    ),
    (
        {
            "assumptions.cp2e": pin(
                rate_shocks_bps=["1", "2", "3", "4"], fx_shocks_pct=["10"], hedge_ratio_pct=""
            )
        },
        "assumptions.cp2e.rate_shocks_bps",
        "at most 3",
    ),
    (
        {
            "assumptions.cp2e": pin(
                rate_shocks_bps=["1001"], fx_shocks_pct=["10"], hedge_ratio_pct=""
            )
        },
        "assumptions.cp2e.rate_shocks_bps",
        "1000 or less",
    ),
    (
        {
            "assumptions.cp2e": pin(
                rate_shocks_bps=["100"], fx_shocks_pct=["51"], hedge_ratio_pct=""
            )
        },
        "assumptions.cp2e.fx_shocks_pct",
        "50 or less",
    ),
    (
        {"assumptions.cp2e": pin(rate_shocks_bps=["100"], fx_shocks_pct=[], hedge_ratio_pct="")},
        "assumptions.cp2e.fx_shocks_pct",
        "required",
    ),
    (
        {"assumptions.cp3c": pin(repricing_bps="1001")},
        "assumptions.cp3c.repricing_bps",
        "1000 or less",
    ),
    ({"assumptions.cp3d": pin(recovery_pct="100")}, "assumptions.cp3d.recovery_pct", "below 100"),
    ({"assumptions.cp4c": pin(ev_multiple="0")}, "assumptions.cp4c.ev_multiple", "above 0"),
    (
        {"assumptions.cp4c": {"ev_multiple": "6", "rationale": ""}},
        "assumptions.cp4c.rationale",
        "required",
    ),
    (
        {"assumptions.cp4c": {"ev_multiple": "6", "rationale": "a\u2028b"}},
        "assumptions.cp4c.rationale",
        "line separator",
    ),
    ({"attachments.legal_documents": "other"}, "attachments.legal_documents", "Input should be"),
    (
        {"research_questions": [{"text": "q", "focus_module": ""}] * 11},
        "research_questions",
        "at most 10",
    ),
    (
        {"research_questions": [{"text": "", "focus_module": ""}]},
        "research_questions[0].text",
        "required",
    ),
    ({"identity.issuer_name": "a\u0085b"}, "identity.issuer_name", "line separator"),
    (
        {"valuation.precedents": [PREC]},
        "valuation.precedents",
        "must be empty",
    ),
    (
        {"valuation.basis": "blend", "valuation.precedents": [PREC] * 31},
        "valuation.precedents",
        "at most 30",
    ),
    (
        {"valuation.issuer_market": row(MARKET, ev_m="-1")},
        "valuation.issuer_market",
        "must be blank",
    ),
    (
        {"valuation.user_multiple": {"value": "x", "basis": "LTM", "rationale": ""}},
        "valuation.user_multiple",
        "must be blank",
    ),
    (
        {"valuation.peer_source": "user_list", "valuation.peers": [row(PEER, ev_m="abc")]},
        "valuation.peers[0].ev_m",
        "must be blank",
    ),
    ({"identity.guarantors": [""]}, "identity.guarantors[0]", "must not be empty"),
    ({"identity.aliases": ["a", " "]}, "identity.aliases[1]", "must not be empty"),
]


def test_minimal_research_context_loads() -> None:
    ctx = load_context(json.dumps(MINIMAL).encode())
    assert ctx.run.run_type == "research" and ctx.run.pathway == "credit_snapshot"
    assert ctx.assumptions.cp2d is None and ctx.deal_terms == ()
    assert {"schema": SCHEMA, **ctx.model_dump(mode="json")} == MINIMAL


def test_bom_is_accepted() -> None:
    assert isinstance(load_context(b"\xef\xbb\xbf" + json.dumps(MINIMAL).encode()), RunContext)


def test_fully_populated_context_loads_and_round_trips() -> None:
    full = with_changes(
        {
            **PRIMARY,
            "run.current_period": "q3-2026",
            "run.prior_period": "q2-2026",
            "identity.guarantors": ["iHeartMedia Capital I, LLC"],
            "quotes": [QUOTE],
            "ratings": [RATING],
            "valuation.peer_source": "user_comps",
            "valuation.peers": [PEER],
            "assumptions.cp2e": pin(
                rate_shocks_bps=["100"], fx_shocks_pct=["10"], hedge_ratio_pct="50"
            ),
            "assumptions.cp3d": pin(recovery_pct="40"),
        }
    )
    ctx = load_context(json.dumps(full).encode())
    assert {"schema": SCHEMA, **ctx.model_dump(mode="json")} == full
    assert ctx.identity.guarantors == ("iHeartMedia Capital I, LLC",)


def test_empty_amount_is_none_not_zero() -> None:
    assert amount("") is None and amount("0") == Decimal(0)
    assert amount("99.50") == Decimal("99.50")


def test_duplicate_keys_refused() -> None:
    raw = b'{"schema": "context/1", "schema": "context/1"}'
    with pytest.raises(ContextRefused, match="duplicate key"):
        load_context(raw)


@pytest.mark.parametrize("raw", [b"\xff\xfe", b"{", b"[]", b'{"schema": NaN}'])
def test_unreadable_files_refused(raw: bytes) -> None:
    with pytest.raises(ContextRefused):
        load_context(raw)


def test_every_problem_is_listed() -> None:
    bad = with_changes(
        {
            "run.reporting_currency": "x",
            "identity.issuer_name": "",
            "quotes": [row(QUOTE, provider="")],
        }
    )
    with pytest.raises(ContextRefused) as caught:
        load_context(json.dumps(bad).encode())
    paths = {p.split(":")[0] for p in caught.value.problems}
    assert {"run.reporting_currency", "identity.issuer_name", "quotes[0].provider"} <= paths


@pytest.mark.parametrize(("changes", "path", "message"), INVALID_CASES)
def test_form_rules_refused(changes: dict[str, Any], path: str, message: str) -> None:
    obj = with_changes(changes)
    with pytest.raises(ContextRefused) as caught:
        load_context(json.dumps(obj).encode())
    assert any(p.startswith(path) and message in p for p in caught.value.problems), (
        caught.value.problems
    )
