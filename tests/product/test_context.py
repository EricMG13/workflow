"""context/1 reader: the form's build() rules (docs/templates/context-form.html)."""

from __future__ import annotations

import copy
import dataclasses
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow.context import (
    ASSUMPTION_LIMITS,
    NUM,
    PERIOD,
    SCHEMA,
    SLUG,
    SNUM,
    ContextRefused,
    RunContext,
    amount,
    load_context,
)

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
        {
            "assumptions.cp2a": pin(
                scenarios=[{"ebitda_decline_pct": "20.123", "interest_increase_pct": "5"}]
            )
        },
        "assumptions.cp2a.scenarios[0].ebitda_decline_pct",
        "use at most 2 decimal places.",
    ),
    (
        {
            "assumptions.cp2a": pin(
                scenarios=[{"ebitda_decline_pct": "20", "interest_increase_pct": "5.001"}]
            )
        },
        "assumptions.cp2a.scenarios[0].interest_increase_pct",
        "use at most 2 decimal places.",
    ),
    (
        {"assumptions.cp3c": pin(repricing_bps="50.5")},
        "assumptions.cp3c.repricing_bps",
        "enter a whole number.",
    ),
    (
        {
            "assumptions.cp2e": pin(
                rate_shocks_bps=["100"], fx_shocks_pct=["10.5"], hedge_ratio_pct=""
            )
        },
        "assumptions.cp2e.fx_shocks_pct",
        '"10.5": enter a whole number.',
    ),
    (
        {
            "assumptions.cp2e": pin(
                rate_shocks_bps=["200", "100"], fx_shocks_pct=["10"], hedge_ratio_pct=""
            )
        },
        "assumptions.cp2e.rate_shocks_bps",
        "values must increase.",
    ),
    (
        {
            "assumptions.cp2e": pin(
                rate_shocks_bps=["100", "100"], fx_shocks_pct=["10"], hedge_ratio_pct=""
            )
        },
        "assumptions.cp2e.rate_shocks_bps",
        "values must increase.",
    ),
    (
        {
            "assumptions.cp2e": pin(
                rate_shocks_bps=["100"], fx_shocks_pct=["20", "10"], hedge_ratio_pct=""
            )
        },
        "assumptions.cp2e.fx_shocks_pct",
        "values must increase.",
    ),
    (
        {
            "assumptions.cp2e": pin(
                rate_shocks_bps=["100"], fx_shocks_pct=["10"], hedge_ratio_pct="60.123"
            )
        },
        "assumptions.cp2e.hedge_ratio_pct",
        "use at most 2 decimal places.",
    ),
    (
        {"assumptions.cp4c": pin(ev_multiple="100.123")},
        "assumptions.cp4c.ev_multiple",
        "use at most 2 decimal places.",
    ),
    (
        {"assumptions.cp3d": pin(recovery_pct="65.123")},
        "assumptions.cp3d.recovery_pct",
        "use at most 2 decimal places.",
    ),
    (
        {"assumptions.cp4c": pin(ev_multiple="8.555")},
        "assumptions.cp4c.ev_multiple",
        "use at most 2 decimal places.",
    ),
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


def test_huge_integer_refused_as_context_refused() -> None:
    raw = b'{"schema": "context/1", "x": ' + b"1" * 5000 + b"}"
    with pytest.raises(ContextRefused, match=r"not valid JSON \(ValueError\)"):
        load_context(raw)


def test_deep_nesting_refused_as_context_refused() -> None:
    raw = b'{"schema": "context/1", "run": ' + b"[" * 100000 + b"]" * 100000 + b"}"
    with pytest.raises(ContextRefused, match=r"not valid JSON \(RecursionError\)"):
        load_context(raw)


@pytest.mark.parametrize("depth", [1500, 33])
def test_nested_too_deeply_refused(depth: int) -> None:
    raw = b'{"schema": "context/1", "run": ' + b"[" * (depth - 1) + b"]" * (depth - 1) + b"}"
    with pytest.raises(ContextRefused) as caught:
        load_context(raw)
    assert list(caught.value.problems) == ["$: nested too deeply (more than 32 levels)."]


def test_root_validation_error_path_is_dollar() -> None:
    from deploy_workflow.context import _path

    assert _path(()) == "$"


def test_form_shaped_user_list_peer_loads() -> None:
    peer = row(PEER, ev_m="", ebitda_m="", as_of="", source="", ticker="PEER")
    obj = with_changes({"valuation.peer_source": "user_list", "valuation.peers": [peer]})
    ctx = load_context(json.dumps(obj).encode())
    assert ctx.valuation.peers[0].name == "Peer"
    assert ctx.valuation.peers[0].ticker == "PEER"


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


REPO = Path(__file__).resolve().parents[2]
CASES = REPO / "cases/context"
GOLDENS = REPO / "cases/goldens"
FORM = REPO / "docs/templates/context-form.html"


@pytest.mark.parametrize("name", ["research-minimal.json", "primary-full.json"])
def test_form_output_loads(name: str) -> None:
    raw = (CASES / name).read_bytes()
    assert {"schema": SCHEMA, **load_context(raw).model_dump(mode="json")} == json.loads(raw)


_PIN_OK = [
    (
        "assumptions.cp2a",
        pin(scenarios=[{"ebitda_decline_pct": "20.12", "interest_increase_pct": "5.5"}]),
    ),
    ("assumptions.cp3c", pin(repricing_bps="50")),
    (
        "assumptions.cp2e",
        pin(rate_shocks_bps=["100", "200"], fx_shocks_pct=["10", "20"], hedge_ratio_pct="60.12"),
    ),
    ("assumptions.cp3d", pin(recovery_pct="65.12")),
    ("assumptions.cp4c", pin(ev_multiple="8.55")),
]


@pytest.mark.parametrize(("path", "value"), _PIN_OK)
def test_pins_at_submission_precision_load(path: str, value: dict[str, Any]) -> None:
    load_context(json.dumps(with_changes({path: value})).encode())


def test_pinned_contexts_of_the_owner_oracle_load() -> None:
    files = sorted((REPO / "cases/pins-context-owner").glob("context-*.json"))
    assert files
    for f in files:
        load_context(f.read_bytes())


_SPEC = re.compile(r"\['(\w+)',\{((?:[^{}]|\{[^{}]*\})*)\}\]")


def _form_spec(html: str, field: str) -> dict[str, str]:
    found = [m for m in _SPEC.finditer(html) if m[1] == field]
    assert len(found) == 1, field
    body = found[0][2]
    item = re.search(r"item:\{([^{}]*)\}", body)
    if item:
        body = item[1] + "," + re.sub(r"item:\{[^{}]*\}", "", body)
    return dict(kv.split(":", 1) for kv in body.split(",") if kv)


def _bound(spec: dict[str, str], key: str) -> str | None:
    return None if key not in spec else str(Decimal(spec[key]))


@pytest.mark.parametrize("key", sorted(ASSUMPTION_LIMITS))
def test_form_limits_equal_reader_table(key: str) -> None:
    limit = ASSUMPTION_LIMITS[key]
    spec = _form_spec(FORM.read_text(), key.split(".")[1])
    assert (spec.get("int") == "true") == limit.whole, key
    assert (int(spec["dp"]) if "dp" in spec else None) == limit.places, key
    assert (spec.get("req") == "true") == limit.req, key
    got = tuple(_bound(spec, k) for k in ("min", "minEx", "max", "maxEx"))
    want = tuple(
        None if v is None else str(Decimal(v))
        for v in (limit.low, limit.low_excl, limit.high, limit.high_excl)
    )
    assert got == want, key


def test_form_messages_present() -> None:
    html = FORM.read_text()
    assert "use at most ' + r.dp + ' decimal places." in html
    assert "values must increase." in html
    assert "earnings runs compare quarters or fiscal years only." in html
    assert "must be the same kind as the current period." in html


def test_limits_table_covers_every_pin_field() -> None:
    assert {k.split(".")[0] for k in ASSUMPTION_LIMITS} == {
        "cp2a",
        "cp2d",
        "cp2e",
        "cp3c",
        "cp3d",
        "cp4c",
    }


def _cp2e_problems(rate: list[str]) -> tuple[str, ...]:
    pins = pin(rate_shocks_bps=rate, fx_shocks_pct=["10"], hedge_ratio_pct="")
    with pytest.raises(ContextRefused) as caught:
        load_context(json.dumps(with_changes({"assumptions.cp2e": pins})).encode())
    return tuple(p for p in caught.value.problems if "rate_shocks_bps" in p)


def test_unparseable_item_gets_no_increase_line() -> None:
    assert _cp2e_problems(["abc", "100"]) == (
        'assumptions.cp2e.rate_shocks_bps: "abc": enter a plain number such as 1250 or 99.5.',
    )


def test_descending_list_is_one_increase_line() -> None:
    assert _cp2e_problems(["300", "200", "100"]) == (
        "assumptions.cp2e.rate_shocks_bps: values must increase.",
    )


def test_form_regexes_match_reader() -> None:
    html = FORM.read_text()
    assert f"const NUM = /{NUM}/, SNUM = /{SNUM}/;" in html
    assert f"/{PERIOD}/.exec(p)" in html
    assert f"/{SLUG}/.test(v)" in html


def test_golden_contexts_exist() -> None:
    assert list(GOLDENS.glob("*/context.json"))


@pytest.mark.parametrize("case", sorted(p.parent.name for p in GOLDENS.glob("*/context.json")))
def test_golden_contexts_load(case: str) -> None:
    load_context((GOLDENS / case / "context.json").read_bytes())


def _rate_problems(rate: list[str]) -> list[str]:
    try:
        raw = with_changes(
            {
                "assumptions.cp2e": pin(
                    rate_shocks_bps=rate, fx_shocks_pct=["10"], hedge_ratio_pct=""
                )
            }
        )
        load_context(json.dumps(raw).encode())
    except ContextRefused as error:
        return [p for p in error.problems if "rate_shocks_bps" in p]
    return []


@pytest.mark.parametrize(
    ("change", "rate", "refused"),
    [
        ({"req": False}, [], False),
        ({"req": True}, [], True),
        ({"high": None, "high_excl": "1000"}, ["1000"], True),
        ({"high": None, "high_excl": "1000"}, ["999"], False),
        ({"low": None, "low_excl": "1"}, ["1"], True),
        ({"low": None, "low_excl": "1"}, ["2"], False),
    ],
)
def test_shock_lists_honour_every_field_of_their_limits_row(
    monkeypatch: pytest.MonkeyPatch, change: dict[str, Any], rate: list[str], refused: bool
) -> None:
    """The reader's shock check reads `req`, `low_excl` and `high_excl` of the table row, as the
    single-number fields do, not only `whole`, `places`, `low` and `high`."""
    key = "cp2e.rate_shocks_bps"
    row = dataclasses.replace(ASSUMPTION_LIMITS[key], **change)
    monkeypatch.setitem(ASSUMPTION_LIMITS, key, row)
    assert bool(_rate_problems(rate)) is refused


IDP = REPO / "cases/context-identity-periods"
IDP_EXPECTED = json.loads((IDP / "expected.json").read_text())


def _idp_refusal(name: str) -> tuple[str, ...]:
    with pytest.raises(ContextRefused) as caught:
        load_context((IDP / "contexts" / f"{name}.json").read_bytes())
    return caught.value.problems


def test_earnings_h_period_refused() -> None:
    assert list(_idp_refusal("ctx-h")) == IDP_EXPECTED["reader"]["refused"]["ctx-h"]["problems"]


def test_earnings_mixed_kinds_refused() -> None:
    expected = IDP_EXPECTED["reader"]["refused"]["ctx-mixed"]["problems"]
    assert list(_idp_refusal("ctx-mixed")) == expected


def test_research_h_period_still_loads() -> None:
    ctx = load_context((IDP / "contexts/ctx-h-research.json").read_bytes())
    assert (ctx.run.run_type, ctx.run.current_period, ctx.run.prior_period) == (
        "research",
        "h2-2025",
        "h1-2025",
    )


def test_every_oracle_context_that_should_load_loads() -> None:
    for name in IDP_EXPECTED["reader"]["loads"]["all_others"]:
        load_context((IDP / "contexts" / f"{name}.json").read_bytes())


def test_form_list_fields_one_per_line() -> None:
    html = FORM.read_text()
    assert re.search(r'<textarea[^>]*id="s2-aliases"', html)
    assert re.search(r'<textarea[^>]*id="s2-guarantors"', html)
    assert "fld(s2, 'aliases', {t:'lines'})" in html
    assert "fld(s2, 'guarantors', {t:'lines'})" in html
    assert "r.t === 'lines'" in html
    assert "split(/\\r?\\n/)" in html
    assert html.count("{t:'list'") >= 1 and "Comma-separated names" not in html


def test_form_rejoin_uses_newline() -> None:
    html = FORM.read_text()
    for k in ("guarantors", "aliases"):
        assert f"setV(s2, '{k}', id.{k}.map(txt).join('\\n')" in html


def test_form_mirrors_period_rules() -> None:
    html = FORM.read_text()
    for problem in IDP_EXPECTED["reader"]["refused"]["ctx-h"]["problems"][:1]:
        assert problem.split(": ", 1)[1] in html
    assert "must be the same kind as the current period." in html


def test_comma_name_round_trips() -> None:
    raw = (IDP / "contexts/ctx-comma.json").read_bytes()
    ctx = load_context(raw)
    form = IDP_EXPECTED["form"]["ctx-comma"]
    assert ctx.identity.borrower_name == form["reader_borrower_name"]
    assert list(ctx.identity.aliases) == form["reader_aliases"]
    assert list(ctx.identity.guarantors) == form["reader_guarantors"]
    assert {"schema": SCHEMA, **ctx.model_dump(mode="json")} == json.loads(raw)
