"""CP-1C takes its issuer period and currency from the run context (Phase 8 Task 2).

The answer key is the frozen oracle `cases/periods-currency-owner/` (`expected.json`,
`manifest.json`, `t414.json`, `submissions.json`), loaded at run time; no expected value is copied
here. The default (2025, USD, no context) behaviour stays pinned by `tests/test_method_cp1c.py`,
`tests/test_connect_cp1c.py` and `cases/cp1c-owner`. Every test drives `_inputs`, the composer,
the validator and the view directly over the oracle's packs (no store).
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any

import pytest
import test_method_cp1c as stage1
import test_method_cp4c as cp4c_tests
from test_connect_cp1c import _cp1_module, _upstream
from test_period_basis import _oracle_facts

from deploy_vii.contracts import Fact, Module, Run, Source
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow.context import load_context
from deploy_workflow.owners import cp1c, cp2g
from deploy_workflow.owners.period_basis import DEFAULT_BASIS, PeriodBasis, run_basis

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "periods-currency-owner"


def _load(name: str) -> Any:
    return json.loads((CASE / name).read_text(encoding="utf-8"))


EXPECTED = _load("expected.json")
MANIFEST = _load("manifest.json")
SUBMISSIONS = _load("submissions.json")
T414 = _load("t414.json")
RUNS = {r["label"]: r for r in MANIFEST["runs"]}
ORACLE = {cur: EXPECTED["module_oracles"][f"CP-1C@{cur}"]["expected"] for cur in ("USD", "EUR")}
# The runs that settle CP-1C: R1 is USD fy-2026, R6 is EUR fy-2026 (expected.json#runs).
SETTLED = {"R1": "USD", "R6": "EUR"}
PEERS_SHA = {
    cur: MANIFEST["sources"][f"peers@{cur}"]["sha256"] for cur in ("USD", "EUR")
}  # pinned page digests


# --- the oracle's packs --------------------------------------------------------------------------------


def _source(key: str) -> Source:
    raw = MANIFEST["sources"][key]
    return stage1._source(raw, source_id=raw["source_id"], name=raw["name"])


def _context_bytes(label: str) -> bytes:
    """The context file the way the oracle builder writes and hashes it (build.py `dumps`)."""
    return (json.dumps(RUNS[label]["context"], indent=2, ensure_ascii=False) + "\n").encode()


def _context_source(label: str) -> Source:
    request = SourceRequest(source_id="context", path=f"{label}.json", media_type="text/plain")
    source = prepare_source(request, _context_bytes(label))
    assert source.sha256 == RUNS[label]["context_sha256"]  # the pinned context is the one read
    return source


def _run(label: str) -> Run:
    return Run.model_validate_json(json.dumps(RUNS[label]["run"]))


def _pack(label: str, *, peers: str | None = None) -> PreparedPack:
    """The run's pack: identity, the peers page of `peers` (default: the run's own) and the context."""
    currency = RUNS[label]["pack_currency"]
    return PreparedPack(
        run=_run(label),
        sources=(
            _source("identity"),
            _source(peers or f"peers@{currency}"),
            _context_source(label),
        ),
    )


def _t414_rows(currency: str) -> list[Fact]:
    key = {"USD": "R1", "EUR": "R2"}[currency]
    return _oracle_facts(T414["contexts"][key]["rows"])


def _t410(metrics: list[dict[str, Any]]) -> list[Fact]:
    """The four T4.10 facts of the run's LTM column, as the key's `issuer_metrics` records them."""
    units = {m.key: m.unit for m in cp1c.METRICS}
    return [
        Fact(
            fact_id=f"T4.10.ltm.{m['fact_id'].rsplit('.', 1)[-1]}",
            label=m["cp1_fact_label"],
            table_id="T4.10",
            amount=Decimal(m["amount_exact"]),
            unit=units[m["fact_id"].rsplit(".", 1)[-1]],
            period=m["period"],
            value_class="calculated",
            calculation_id=f"cp1-calc-{m['fact_id'].rsplit('.', 1)[-1]}",
        )
        for m in metrics
    ]


def _ebitda(basis: PeriodBasis) -> Fact:
    """CP-1's LTM EBITDA: the frozen CP-4C oracle's figure, on the run's column and currency."""
    record = _load_cp4c()["cases"]["positive"]["cp1_inputs"]["ebitda"]
    fact = cp4c_tests._cp1_t410("ebitda", record)
    return fact.model_copy(
        update={
            "label": f"{basis.ltm_column} · ebitda",
            "period": basis.ltm_period,
            "currency": basis.currency,
        }
    )


@cache
def _load_cp4c() -> Any:
    return json.loads((ROOT / "cases" / "cp4c-owner" / "expected.json").read_text(encoding="utf-8"))


def _cp1_head(label: str) -> Module:
    """A CP-1 head of the run: its T4.14 rows, the four T4.10 facts the key names and the ten the
    EV tables select from (`cp2g.select_cp1`; fillers but the EBITDA)."""
    run = RUNS[label]
    currency = run["pack_currency"]
    basis = run_basis(load_context(_context_bytes(label)), _t414_rows(currency))
    key = EXPECTED["runs"][label]["modules"]["CP-1C"]["issuer_metrics"]
    ebitda = _ebitda(basis)
    selected = [
        ebitda
        if metric == "ebitda"
        else ebitda.model_copy(
            update={
                "fact_id": f"filler-{metric}",
                "label": f"{basis.ltm_column} · {metric}",
                "row_id": metric,
            }
        )
        for metric in cp2g.CP1_METRICS
    ]
    return Module(
        run_id=run["run"]["run_id"],
        issuer_id=run["run"]["issuer_id"],
        as_of=date.fromisoformat(run["run"]["as_of"]),
        module_id="CP-1",
        status="restricted",
        facts=(*_t414_rows(currency), *_t410(key), *selected),
        limitations=("CP-1 note",),
    )


def _submission(currency: str) -> cp1c.PeerBenchmarkSubmission:
    body = SUBMISSIONS["modules"][f"CP-1C@{currency}"]["submission"]["peer_benchmark"]
    return cp1c.PeerBenchmarkSubmission.model_validate_json(json.dumps(body))


def _composed(label: str) -> tuple[cp1c.PeerBenchmarkInputs, cp1c.PeerBenchmarkResult]:
    pack, upstream = _pack(label), _upstream(_cp1_head(label))
    inputs = cp1c._inputs(pack, _submission(SETTLED[label]), upstream)
    return inputs, cp1c.compute(inputs)


# --- the comparison ------------------------------------------------------------------------------------


def _cites(items: Any) -> list[tuple[str, str, str]]:
    return [(c["source_id"], c["locator"], c["quote"]) for c in items]


def _assert_fact(item: cp1c.PeerFact, want: dict[str, Any], shas: dict[str, str]) -> None:
    """The key's fact against the composed one. A cell copied from CP-1 keeps CP-1's calculation id
    and citations (bound at run time, so the key writes a placeholder for the id)."""
    fact, where = item.fact, want["fact_id"]
    assert (fact.table_id, fact.row_id, fact.field, fact.label) == (
        want["table_id"],
        want["row_id"],
        want["field"],
        want["label"],
    ), where
    assert fact.status == want["status"], where
    assert fact.text == want.get("text"), where
    assert fact.unit == want.get("unit"), where
    assert fact.period == want.get("period"), where
    assert stage1._exact(fact.amount) == want.get("amount_exact"), where
    assert fact.currency == want.get("currency"), where
    assert fact.scale == Decimal(want.get("scale", "1")), where
    assert fact.decimals == want.get("decimals"), where
    assert fact.value_class == want.get("value_class"), where
    assert fact.formula == want.get("formula"), where
    assert fact.limitation == want.get("limitation"), where
    assert list(item.derives_from) == want.get("derives_from", []), where
    assert item.copied_from_cp1 == want.get("copied_from_cp1"), where
    assert cp1c.shown(fact) == want["shown"], where
    if want.get("copied_from_cp1"):
        return
    assert fact.calculation_id == want.get("calculation_id"), where
    assert _cites(c.model_dump() for c in fact.citations) == _cites(want.get("citations", [])), (
        where
    )
    assert all(c.source_sha256 == shas[c.source_id] for c in fact.citations), where


@pytest.mark.parametrize("label", sorted(SETTLED))
def test_composed_facts_tables_and_limitations_equal_the_key(label: str) -> None:
    """(b) Over a 2026 head and a 2026 context the four metrics are found and every fact, table and
    own limitation, the EV tables T1C.9-T1C.11 included, equals the oracle's."""
    want = ORACLE[SETTLED[label]]
    inputs, got = _composed(label)
    assert inputs.basis.ltm_tag == "LTM Q4 26"
    shas = {"peers": PEERS_SHA[SETTLED[label]], "context": RUNS[label]["context_sha256"]}
    assert [i.fact.fact_id for i in got.facts] == [f["fact_id"] for f in want["facts"]]
    by_id = {i.fact.fact_id: i for i in got.facts}
    for fact in want["facts"]:
        _assert_fact(by_id[fact["fact_id"]], fact, shas)
    tables = [
        {
            "table_id": t.table_id,
            "title": t.title,
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)} for r in t.rows
            ],
        }
        for t in got.tables
    ]
    # the key's EV tables also list their columns, which the report (not the composer) adds
    assert tables == [{k: t[k] for k in ("table_id", "title", "rows")} for t in want["tables"]]
    assert list(got.limitations) == want["own_limitations"]
    assert [(c.claim_id, c.text) for c in got.claims] == [
        (c["claim_id"], c["text"]) for c in want["claims"]
    ]


@pytest.mark.parametrize("label", sorted(SETTLED))
def test_issuer_period_and_metrics_follow_the_run(label: str) -> None:
    """The run's key: the issuer period, the selected T4.10 column and the four issuer cells."""
    key = EXPECTED["runs"][label]["modules"]["CP-1C"]
    inputs, got = _composed(label)
    assert cp1c.mixed_period(inputs.basis) == key["issuer_period"]
    assert {f.label for f in inputs.cp1_metrics.values()} == {
        m["cp1_fact_label"] for m in key["issuer_metrics"]
    }
    assert len(inputs.cp1_metrics) == key["t410_facts_selected"]
    by_id = {i.fact.fact_id: i.fact for i in got.facts}
    for metric in key["issuer_metrics"]:
        cell = by_id[metric["fact_id"]]
        assert (cell.period, cp1c.shown(cell)) == (metric["period"], metric["shown"])
        assert stage1._exact(cell.amount) == metric["amount_exact"]


@pytest.mark.parametrize("label", sorted(SETTLED))
def test_no_stale_period_literal_is_emitted(label: str) -> None:
    """expected.json#runs/<R>/stale_period_literals_forbidden_in_emitted_period_strings."""
    forbidden = EXPECTED["runs"][label]["stale_period_literals_forbidden_in_emitted_period_strings"]
    _, got = _composed(label)
    assert forbidden
    emitted = [i.fact.period or "" for i in got.facts]
    emitted += [i.fact.limitation or "" for i in got.facts] + list(got.limitations)
    assert [(s, p) for p in emitted for s in forbidden if s in p] == []


# --- (a) the default basis, (c) the stale column -------------------------------------------------------


def test_default_basis_selects_todays_frozen_head() -> None:
    """(a) `_cp1_metrics(cp1, DEFAULT_BASIS)` on the frozen CP-1 head is today's result."""
    got = cp1c._cp1_metrics(_cp1_module(), DEFAULT_BASIS)
    frozen = stage1.cp1_metrics()
    assert {k: f.fact_id for k, f in got.items()} == {k: f.fact_id for k, f in frozen.items()}
    assert cp1c.MIXED_PERIOD == cp1c.mixed_period(DEFAULT_BASIS)
    assert cp1c.MIXED_PERIOD in stage1.expected()["policy_constants"]["period_of_derived_facts"]


def test_the_2025_selection_finds_nothing_in_a_2026_head() -> None:
    """(c) The same head under the 2025 call raises, never labels 2026 figures as 2025."""
    head = _cp1_head("R1")
    with pytest.raises(ValueError, match="0 facts, expected exactly one"):
        cp1c._cp1_metrics(head, DEFAULT_BASIS)
    basis = run_basis(load_context(_context_bytes("R1")), head.facts)
    assert len(cp1c._cp1_metrics(head, basis)) == 4


def test_blank_usd_run_over_a_2026_head_is_refused_at_selection() -> None:
    """P8-R3 guard: the blank-base USD fail-open binds the 2025 labels, so a 2026 CP-1 is an
    issue line from the validator, not a mislabelled composition."""
    pack = _pack("R1")
    context = json.loads(_context_bytes("R1"))
    context["run"]["current_period"] = ""
    blank = PreparedPack(
        run=pack.run,
        sources=(
            *pack.sources[:-1],
            prepare_source(
                SourceRequest(source_id="context", path="blank.json", media_type="text/plain"),
                (json.dumps(context, indent=2, ensure_ascii=False) + "\n").encode(),
            ),
        ),
    )
    issues = cp1c.validate_peer_benchmark(
        pack=blank, submission=_submission("USD"), upstream=_upstream(_cp1_head("R1"))
    )
    assert len(issues) == 1
    assert issues[0].startswith("CP-1 facts unavailable: CP-1 T4.10 ")
    assert "0 facts, expected exactly one" in issues[0]


# --- (d) the peers page's currency ---------------------------------------------------------------------


def test_peers_page_of_another_currency_is_outside_the_table_rule() -> None:
    """(d) The EUR Basis clause is a table under an EUR run only; a USD run refuses it exactly as
    it refuses an unsupported clause."""
    eur = _source("peers@EUR")
    name = RUNS["R6"]["run"]["issuer_name"]
    with pytest.raises(cp1c.PeerTableError, match=cp1c.TABLE_NOT_FOUND):
        cp1c.parse_peer_source(eur, issuer_name=name, currency="USD")
    with pytest.raises(cp1c.PeerTableError, match=cp1c.TABLE_NOT_FOUND):
        cp1c.parse_peer_source(eur, issuer_name=name)
    sheet = cp1c.parse_peer_source(eur, issuer_name=name, currency="EUR")
    assert sheet is not None and sheet.currency == "EUR"
    usd = cp1c.parse_peer_source(_source("peers@USD"), issuer_name=name, currency="USD")
    assert usd is not None and usd.currency == "USD"
    with pytest.raises(cp1c.PeerTableError):
        cp1c.parse_peer_source(_source("peers@USD"), issuer_name=name, currency="EUR")


def test_validator_refuses_an_eur_peers_page_under_a_usd_run() -> None:
    """(d) Through the validator: the USD run R1 over the EUR peers page is `Peer table not found`."""
    pack = _pack("R1", peers="peers@EUR")
    issues = cp1c.validate_peer_benchmark(
        pack=pack, submission=_submission("USD"), upstream=_upstream(_cp1_head("R1"))
    )
    assert issues == (cp1c.TABLE_NOT_FOUND,)


# --- (e) refusals --------------------------------------------------------------------------------------


def _mismatch_upstream() -> cp1c.Upstream:
    """R4: an EUR run over a CP-1 head that reports USD (its T4.14 rows and column are R1's)."""
    return _upstream(_cp1_head("R1"))


def test_currency_mismatch_is_the_keys_validator_issue() -> None:
    """(e) R4: one issue line, the key's `issue_exact`, never an exception out of the validator."""
    key = EXPECTED["runs"]["R4"]["modules"]["CP-1C"]
    assert key["layer"] == "entry validator" and key["figures_produced"] is False
    issues = cp1c.validate_peer_benchmark(
        pack=_pack("R4"), submission=_submission("USD"), upstream=_mismatch_upstream()
    )
    assert issues == (key["issue_exact"],)
    assert key["issue_contains"] in issues[0]


def test_unsupported_period_base_is_a_period_basis_issue() -> None:
    """(e) R5: `h2-2026` is refused with the key's message, prefixed `Period basis: `."""
    message = EXPECTED["runs"]["R5"]["refusal"]["message"]
    issues = cp1c.validate_peer_benchmark(
        pack=_pack("R5"), submission=_submission("USD"), upstream=_upstream(_cp1_head("R1"))
    )
    assert issues == (f"Period basis: {message}",)


# --- the read_inputs view (P8-R5) ----------------------------------------------------------------------


def test_view_offers_nothing_and_names_the_same_issue_on_a_refusal() -> None:
    """The view never raises on a refusal: no rows, no facts, `context_issue` equal to the
    validator's single issue line."""
    pack, upstream = _pack("R4"), _mismatch_upstream()
    issues = cp1c.validate_peer_benchmark(
        pack=pack, submission=_submission("USD"), upstream=upstream
    )
    block = cp1c.context_block(pack=pack, upstream=upstream)
    assert block["context_issue"] == issues[0]
    assert block["cp1_facts"] == []
    peers = block["peers"]
    assert isinstance(peers, dict) and peers["rows"] == [] and peers["issuer_line"] is None


def test_view_of_a_refused_period_base_names_the_issue() -> None:
    message = EXPECTED["runs"]["R5"]["refusal"]["message"]
    block = cp1c.context_block(pack=_pack("R5"), upstream=_upstream(_cp1_head("R1")))
    assert block["context_issue"] == f"Period basis: {message}"
    assert block["cp1_facts"] == []


def test_view_of_a_settled_run_offers_the_run_column_and_rows() -> None:
    block = cp1c.context_block(pack=_pack("R6"), upstream=_upstream(_cp1_head("R6")))
    assert "context_issue" not in block
    key = EXPECTED["runs"]["R6"]["modules"]["CP-1C"]["issuer_metrics"]
    facts = block["cp1_facts"]
    assert isinstance(facts, list)
    assert [f["period"] for f in facts] == [m["period"] for m in key]
    assert [f["shown"] for f in facts] == [m["shown"] for m in key]
    peers = block["peers"]
    assert isinstance(peers, dict) and len(peers["rows"]) == 5
