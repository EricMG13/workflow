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
import test_cp1c_valuation_context as valuation
import test_method_cp1c as stage1
import test_method_cp4c as cp4c_tests
from test_connect_cp1c import SYNTHETIC, _cp1_module, _upstream
from test_connect_cp1c import _submission as _connect_submission
from test_period_basis import _oracle_facts

from deploy_vii.contracts import Fact, Module, Run, Source
from deploy_vii.execution import Attempt, ExecutionSnapshot, candidate_issues, settle, text_sha256
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
    assert inputs.basis.ltm_tag == EXPECTED["period_basis"][SETTLED[label]]["ltm_tag"]
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
    # the composer yields rows only; the columns are CP-1C's report's (next test)
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


def _blank_usd_pack() -> PreparedPack:
    """R1's pack with a blank `current_period` (the P8-R3 fail-open: the 2025 labels bind)."""
    pack = _pack("R1")
    context = json.loads(_context_bytes("R1"))
    context["run"]["current_period"] = ""
    request = SourceRequest(source_id="context", path="blank.json", media_type="text/plain")
    source = prepare_source(
        request, (json.dumps(context, indent=2, ensure_ascii=False) + "\n").encode()
    )
    return PreparedPack(run=pack.run, sources=(*pack.sources[:-1], source))


def test_blank_usd_run_over_a_2026_head_is_refused_at_selection() -> None:
    """P8-R3 guard: the blank-base USD fail-open binds the 2025 labels, so a 2026 CP-1 is an
    issue line from the validator, not a mislabelled composition."""
    blank = _blank_usd_pack()
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
    assert isinstance(peers, dict)
    assert len(peers["rows"]) == ORACLE["EUR"]["operands_summary"]["peers_in_source"]


# --- the report's tables, the settled head (L1, L2) ----------------------------------------------------


def _report(label: str) -> cp1c.PeerBenchmarkReport:
    return cp1c.peer_benchmark(
        pack=_pack(label),
        submission=_submission(SETTLED[label]),
        upstream=_upstream(_cp1_head(label)),
    )


@pytest.mark.parametrize("label", sorted(SETTLED))
def test_report_table_columns_equal_the_key(label: str) -> None:
    """The EV tables' columns are CP-1C's own (`_columns`); the key pins them per table."""
    want = {t["table_id"]: t for t in ORACLE[SETTLED[label]]["tables"]}
    got = {t.table_id: t for t in _report(label).tables}
    assert list(got) == list(want)
    for table_id in cp1c.EV_TABLES:
        assert [c.model_dump() for c in got[table_id].columns] == want[table_id]["columns"]


@pytest.mark.parametrize("label", sorted(SETTLED))
def test_settled_head_status_and_limitations_equal_the_key(label: str) -> None:
    """`settle` over the candidate (store-free, as test_connect_cp1c's settlement test): the head's
    status and settled limitations are the key's. The synthetic line is the frozen case's."""
    want = ORACLE[SETTLED[label]]
    pack, up = _pack(label), _upstream(_cp1_head(label))
    candidate = cp1c.cp1c_module(_report(label), inputs=up.bound, attempt=0)
    payload = candidate.model_dump_json()
    attempt = Attempt(
        ticket_id="t1",
        module_id="CP-1C",
        inputs=up.bound,
        number=0,
        payload_sha256=text_sha256(payload),
    )
    snapshot = ExecutionSnapshot(run=pack.run, pack_sha256=pack.content_hash(), attempts=(attempt,))
    assert candidate_issues(snapshot, attempt, candidate, pack=pack) == ()
    finished, head = settle(
        snapshot,
        attempt,
        payload,
        lambda supplied: () if supplied == candidate else ("Candidate differs",),
        pack=pack,
        load=lambda _head: candidate,
    )
    assert finished.issues == ()
    assert head.status == want["module_status"]
    assert list(head.limitations) == want["settled_limitations"]
    assert want["settled_limitations"][-1] == SYNTHETIC


# --- basis-dependent text the settled runs do not reach (L3) -------------------------------------------


def _eur_with_comps() -> cp1c.PeerBenchmarkReport:
    """R6 (EUR fy-2026) with the frozen auto-public valuation block, its peers dated inside the
    run's window, so the EV records and the selected multiple are known."""
    auto = json.loads(valuation.context_bytes("auto-public"))
    context = json.loads(_context_bytes("R6"))
    context["valuation"] = auto["valuation"]
    for peer in context["valuation"]["peers"]:
        peer["as_of"] = peer["as_of"].replace("2025-", "2026-").replace("2024-", "2026-")
    request = SourceRequest(source_id="context", path="r6-comps.json", media_type="text/plain")
    source = prepare_source(
        request, (json.dumps(context, indent=2, ensure_ascii=False) + "\n").encode()
    )
    pack = _pack("R6")
    pack = PreparedPack(run=pack.run, sources=(*pack.sources[:-1], source))
    return cp1c.peer_benchmark(
        pack=pack, submission=_submission("EUR"), upstream=_upstream(_cp1_head("R6"))
    )


def test_currency_period_line_names_the_runs_ltm_tag() -> None:
    """Text the key does not pin: the line's wording is the default's with the run's tag."""
    key = EXPECTED["period_basis"]["EUR"]
    line = next(
        (l for l in _eur_with_comps().limitations if l.startswith("The peers' and precedents'")),
        None,
    )
    forbidden = EXPECTED["runs"]["R6"]["stale_period_literals_forbidden_in_emitted_period_strings"]
    assert line is not None
    assert line.endswith(f"issuer's {key['ltm_tag']} EBITDA.")
    assert [s for s in forbidden if s in line] == []


def test_implied_ev_and_issuer_ebitda_carry_the_runs_currency_and_period() -> None:
    """A known implied EV (the key's runs select no multiple): T1C.11 follows the basis."""
    facts = {f.fact_id: f for f in _eur_with_comps().facts}
    key = EXPECTED["period_basis"]["EUR"]
    for fact_id in ("T1C.11.selection.issuer_ebitda", "T1C.11.selection.implied_ev"):
        fact = facts[fact_id]
        assert fact.status == "known", fact_id
        assert (fact.currency, fact.period) == (key["currency"], key["ltm_period"]), fact_id


# --- the view under a refusal (M1, P8-R3, P8-R5, P8T2-R1 to R3) -----------------------------------------


def _offered(block: dict[str, object]) -> list[Any]:
    facts = block["cp1_facts"]
    assert isinstance(facts, list)
    return facts


def _valuation_upstream() -> cp1c.Upstream:
    return _upstream(valuation.full_cp1())


@pytest.mark.parametrize("name", valuation.CASES)
def test_view_of_a_blank_usd_context_is_the_default_selection(name: str) -> None:
    """P8-R3 in the view: every frozen valuation context (blank current_period, USD) is accepted
    by the validator and offers the four CP-1 facts with no `context_issue`."""
    pack, up = valuation.pack_of(name), _valuation_upstream()
    base = valuation.base_case(name)
    issues = cp1c.validate_peer_benchmark(
        pack=pack, submission=_connect_submission(base), upstream=up
    )
    block = cp1c.context_block(pack=pack, upstream=up)
    assert issues == ()
    assert "context_issue" not in block
    assert len(_offered(block)) == len(cp1c.METRICS)


def test_view_of_a_refused_context_carries_the_issue_and_the_default_selection() -> None:
    """P8-R5 with P8T2-R1: a context refusal never raises out of the view; `context_issue` is
    the validator's line and the default basis's four facts are offered (the parent's view)."""
    up, pack = _valuation_upstream(), valuation.pack_of("auto-public")
    other = PreparedPack(
        run=pack.run.model_copy(update={"issuer_id": "other"}), sources=pack.sources
    )
    issues = cp1c.validate_peer_benchmark(
        pack=other, submission=_connect_submission("no_peers"), upstream=up
    )
    block = cp1c.context_block(pack=other, upstream=up)
    assert len(issues) == 1 and issues[0].startswith("Context refused: ")
    assert block["context_issue"] == issues[0]
    assert len(_offered(block)) == len(cp1c.METRICS)


def test_view_of_an_uncitable_context_carries_the_validators_line() -> None:
    """P8T2-R2: the `_with_context` refusal (a context source not citable by line) reaches the view."""
    up, pack = _valuation_upstream(), valuation.pack_of("auto-public")
    broken = pack.sources[-1].model_copy(update={"media_type": "application/pdf"})
    pdf = PreparedPack(run=pack.run, sources=(*pack.sources[:-1], broken))
    issues = cp1c.validate_peer_benchmark(
        pack=pdf, submission=_connect_submission("no_peers"), upstream=up
    )
    block = cp1c.context_block(pack=pdf, upstream=up)
    assert len(issues) == 1 and issues[0].startswith("Context refused: ")
    assert block["context_issue"] == issues[0]
    assert len(_offered(block)) == len(cp1c.METRICS)


def test_view_of_a_blank_usd_run_over_a_2026_head_names_the_validators_line() -> None:
    """P8T2-R3: the blank-USD fail-open over a 2026 CP-1 is a stated refusal, so the view returns
    with the validator's `CP-1 facts unavailable` line and offers nothing; it does not raise."""
    pack = _blank_usd_pack()
    up = _upstream(_cp1_head("R1"))
    issues = cp1c.validate_peer_benchmark(pack=pack, submission=_submission("USD"), upstream=up)
    block = cp1c.context_block(pack=pack, upstream=up)
    assert len(issues) == 1 and issues[0].startswith("CP-1 facts unavailable: ")
    assert block["context_issue"] == issues[0]
    assert block["cp1_facts"] == []


# --- the view states the validator's other refusals and offers nothing (P8T2-R4, L5, I11) ----------------


def _unavailable_line(
    pack: PreparedPack, up: cp1c.Upstream, sub: cp1c.PeerBenchmarkSubmission
) -> str:
    issues = cp1c.validate_peer_benchmark(pack=pack, submission=sub, upstream=up)
    assert len(issues) == 1 and issues[0].startswith("CP-1 facts unavailable: ")
    return issues[0]


def test_view_of_a_refused_currency_over_a_2025_head_offers_nothing() -> None:
    """L5 (a), P8-R5 and P8T2-R4: only a context refusal offers the default selection. A blank-base
    EUR run over the 2025 head, where that selection would succeed, offers no fact and no row and
    carries the validator's `Period basis:` line."""
    document = json.loads(valuation.context_bytes("auto-public"))
    document["run"]["reporting_currency"] = "EUR"
    raw = (json.dumps(document, indent=2) + "\n").encode()
    pack = valuation.pack_of("auto-public")
    pack = PreparedPack(
        run=pack.run, sources=(*pack.sources[:-1], valuation.context_source("auto-public", raw))
    )
    up = _valuation_upstream()
    issues = cp1c.validate_peer_benchmark(
        pack=pack, submission=_connect_submission("no_peers"), upstream=up
    )
    block = cp1c.context_block(pack=pack, upstream=up)
    assert len(issues) == 1 and issues[0].startswith("Period basis: ")
    assert block["context_issue"] == issues[0]
    assert block["cp1_facts"] == []
    peers = block["peers"]
    assert isinstance(peers, dict) and peers["rows"] == []


def test_view_of_a_valuation_context_without_cp1_ebitda_names_the_validators_line() -> None:
    """L5 (b): the view runs the EBITDA selection the validator runs for a valuation context.
    A 2025 head with no EBITDA fact offers nothing and carries `CP-1 facts unavailable`."""
    pack, up = valuation.pack_of("auto-public"), _upstream()
    line = _unavailable_line(pack, up, _connect_submission("no_peers"))
    block = cp1c.context_block(pack=pack, upstream=up)
    assert block["context_issue"] == line
    assert block["cp1_facts"] == []


def test_view_of_a_cp1_fact_breaking_the_stage_1_rules_names_the_validators_line() -> None:
    """I11: a known T4.10 metric in the wrong unit is the validator's `CP-1 facts unavailable`
    line; the view carries it and offers nothing (it offered the four facts, with no issue)."""
    head = _cp1_head("R1")
    broken = head.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"unit": "MULTIPLE"})
                if f.table_id == "T4.10" and f.label.endswith("adjusted_ebitda_margin")
                else f
                for f in head.facts
            )
        }
    )
    pack, up = _pack("R1"), _upstream(broken)
    line = _unavailable_line(pack, up, _submission("USD"))
    block = cp1c.context_block(pack=pack, upstream=up)
    assert block["context_issue"] == line
    assert block["cp1_facts"] == []
