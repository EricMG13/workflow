"""Phase 7 Task 3: CP-1C composes the context EV/EBITDA tables T1C.9-T1C.11 and exposes them.

Every expectation is read at run time from the frozen oracle `cases/valuation-context-owner/`
(`expected.json`, `manifest.json`, the context files) or from `cases/cp1c-owner/` (the eight tables
without a context). Nothing is computed here: a figure, a text, a fact id, a citation (`line:<n>`,
checked against the context file's own bytes) or a limitation comes from the key. The tests drive
`compute`, `_compose`, `_with_context`, `_checked` and the reader directly, so no node runs a store.
"""

import json
from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any

import pytest
import test_method_cp1c as stage1
import test_method_cp4c as cp4c_tests
from test_connect_cp1c import _cp1_module, _pack, _submission, _upstream

from deploy_vii.contracts import Fact, Module, Run, validate_tables
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow.context import ContextRefused, load_context
from deploy_workflow.owners import cp1c, cp2g, cp4c
from deploy_workflow.owners.period_basis import DEFAULT_BASIS

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "valuation-context-owner"
CP4C_CASE = ROOT / "cases" / "cp4c-owner"
GAP_DR = "No peer figures: cp_dr_public peers come from the CP-DR peer pack (Part B O7d)"
GAP_UL = "No peer figures: user_list peers need the peer lookup (O7d)"


def _load(path: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return document


@cache
def expected() -> dict[str, Any]:
    return _load(CASE / "expected.json")


@cache
def manifest() -> dict[str, Any]:
    return _load(CASE / "manifest.json")


CASES = tuple(expected()["cases"])


def case_of(name: str) -> dict[str, Any]:
    case: dict[str, Any] = expected()["cases"][name]
    return case


def context_bytes(name: str) -> bytes:
    return (CASE / "contexts" / f"{name}.json").read_bytes()


def context_source(name: str, raw: bytes | None = None) -> Any:
    request = SourceRequest(
        source_id="context",
        path=f"cases/valuation-context-owner/contexts/{name}.json",
        media_type="text/plain",
    )
    return prepare_source(request, context_bytes(name) if raw is None else raw)


# --- CP-1's facts: the EBITDA is the frozen CP-4C oracle's (`cp1_inputs.ebitda`) ---------------------


@cache
def cp1_ebitda() -> Fact:
    cp4c_expected = _load(CP4C_CASE / "expected.json")
    record = cp4c_expected["cases"]["positive"]["cp1_inputs"]["ebitda"]
    assert record["amount_exact"] == "30"  # the figure the oracle's implied EVs are built on
    return cp4c_tests._cp1_t410("ebitda", record)


def cp1_t410_facts(ebitda: Fact | None = None) -> tuple[Fact, ...]:
    """CP-1's T4.10 LTM facts as `cp2g.select_cp1` selects them: one per metric, the EBITDA from
    the oracle. The other metrics are fillers (label and table are all the selector reads)."""
    head = cp1_ebitda() if ebitda is None else ebitda
    facts = []
    for metric in cp2g.CP1_METRICS:
        label = f"{DEFAULT_BASIS.ltm_column} · {metric}"
        facts.append(
            head
            if metric == "ebitda"
            else head.model_copy(
                update={"fact_id": f"filler-{metric}", "label": label, "row_id": metric}
            )
        )
    return tuple(facts)


# --- the inputs of one oracle case --------------------------------------------------------------------


def base_case(name: str) -> str:
    return "positive" if case_of(name)["pack"] == "peers" else "no_peers"


def inputs_of(name: str, ebitda: Fact | None = None) -> cp1c.PeerBenchmarkInputs:
    return replace(
        stage1.inputs(base_case(name)),
        context=load_context(context_bytes(name)),
        context_source=context_source(name),
        cp1_ebitda=cp1_ebitda() if ebitda is None else ebitda,
    )


@cache
def result_of(name: str) -> cp1c.PeerBenchmarkResult:
    return cp1c.compute(inputs_of(name))


def ev_facts(result: cp1c.PeerBenchmarkResult) -> list[cp1c.PeerFact]:
    return [f for f in result.facts if f.fact.table_id in cp1c.EV_TABLES]


def by_id(result: cp1c.PeerBenchmarkResult) -> dict[str, cp1c.PeerFact]:
    return {f.fact.fact_id: f for f in result.facts}


def run_of(name: str) -> Run:
    return Run.model_validate_json(json.dumps(manifest()["contexts"][name]["run"]))


def pack_of(name: str, source: Any = None) -> PreparedPack:
    held = stage1.sources(base_case(name))
    return PreparedPack(
        run=run_of(name), sources=(*held, context_source(name) if source is None else source)
    )


# --- the comparison -------------------------------------------------------------------------------------


def cites(items: Any) -> list[tuple[str, str, str]]:
    return [(c["source_id"], c["locator"], c["quote"]) for c in items]


def assert_fact(item: cp1c.PeerFact, want: dict[str, Any], sha: str) -> None:
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
    assert fact.calculation_id == want.get("calculation_id"), where
    assert list(item.derives_from) == want.get("derives_from", []), where
    assert cites(c.model_dump() for c in fact.citations) == cites(want.get("citations", [])), where
    assert all(c.source_sha256 == sha for c in fact.citations), where
    assert cp1c.shown(fact) == want["shown"], where


@pytest.mark.parametrize("name", CASES)
def test_the_oracle_citations_are_the_context_files_lines(name: str) -> None:
    """The key's own `line:<n>` spans quote the stripped line of the context file's bytes."""
    lines = context_bytes(name).decode("utf-8").splitlines()
    for fact in case_of(name)["cp1c"]["facts"]:
        for c in fact.get("citations", []):
            number = int(c["locator"].removeprefix("line:"))
            assert c["source_id"] == "context"
            assert c["quote"] == lines[number - 1].strip(), fact["fact_id"]


@pytest.mark.parametrize("name", CASES)
def test_every_row_of_the_oracle_table(name: str) -> None:
    """Row ids, labels and fact ids of T1C.9-T1C.11, in the oracle's order."""
    want = case_of(name)["cp1c"]
    got = [
        {
            "table_id": t.table_id,
            "title": t.title,
            "columns": [{"field": f, "label": lb} for f, lb in cp1c.EV_COLUMNS[t.table_id]],
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)} for r in t.rows
            ],
        }
        for t in result_of(name).tables
        if t.table_id in cp1c.EV_TABLES
    ]
    assert got == want["tables"]
    assert [t.table_id for t in result_of(name).tables] == want["table_ids"]


@pytest.mark.parametrize("name", CASES)
def test_every_fact_equals_the_oracle(name: str) -> None:
    """Ids and order, status, shown text, value class, formula, derives, calculation id and
    citations (with the context's sha256 from the manifest) of every EV fact."""
    got = ev_facts(result_of(name))
    want = case_of(name)["cp1c"]["facts"]
    assert [f.fact.fact_id for f in got] == [w["fact_id"] for w in want]
    sha = manifest()["contexts"][name]["sha256"]
    for item, expect in zip(got, want, strict=True):
        assert_fact(item, expect, sha)


@pytest.mark.parametrize("name", CASES)
def test_limitations_equal_the_oracle(name: str) -> None:
    want = case_of(name)["cp1c"]
    assert list(result_of(name).limitations) == want["own_limitations"]


@pytest.mark.parametrize("name", CASES)
def test_selection_and_statistics_equal_the_oracle(name: str) -> None:
    """The shown figures of the selection and of every statistics row."""
    want = case_of(name)["cp1c"]
    facts = by_id(result_of(name))

    def shown(fact_id: str) -> str | None:
        return cp1c.shown(facts[fact_id].fact)

    sel = want["selection"]
    for field, key in (
        ("requested_basis", "requested_basis"),
        ("ebitda_basis", "ebitda_basis"),
        ("reason", "reason"),
        ("selected_multiple", "selected_multiple"),
        ("issuer_ebitda", "issuer_ebitda"),
        ("implied_ev", "implied_ev"),
    ):
        text = shown(f"T1C.11.selection.{field}")
        assert (text or "").removesuffix("x") == (sel[key] or ""), (name, field)
    assert facts["T1C.11.selection.selected_basis"].fact.text == sel["selected_basis"]
    rows = {**want["statistics"], **want["single_value_rows"]}
    for row_id, stats in rows.items():
        if f"T1C.10.{row_id}.n_total" not in facts:
            continue
        for field in ("min", "median", "max"):
            text = shown(f"T1C.10.{row_id}.{field}")
            assert (text or "").removesuffix("x") == (stats[field] or ""), (name, row_id, field)
        assert facts[f"T1C.10.{row_id}.n_admitted"].fact.amount == stats["n_admitted"]
        assert facts[f"T1C.10.{row_id}.n_total"].fact.amount == stats["n_total"]


@pytest.mark.parametrize("name", CASES)
def test_the_eight_tables_are_untouched_by_the_context(name: str) -> None:
    """T1C.1-T1C.8 and their facts equal the no-context composition over the same inputs; the
    new tables follow them and the frozen limitations lead."""
    with_context = result_of(name)
    plain = cp1c.compute(stage1.inputs(base_case(name)))
    ids = [t.table_id for t in with_context.tables]
    assert ids[:8] == list(cp1c.TABLES) == [t.table_id for t in plain.tables]
    assert with_context.tables[:8] == plain.tables
    assert with_context.facts[: len(plain.facts)] == plain.facts
    assert with_context.claims == plain.claims
    assert with_context.limitations[: len(plain.limitations)] == plain.limitations
    assert [f.fact.table_id for f in with_context.facts[len(plain.facts) :]] == [
        f.fact.table_id for f in ev_facts(with_context)
    ]


def test_credit_plus_comps_leaves_t1c1_to_8_untouched() -> None:
    """A pack with a peers source and a context: the peers' eight tables are the frozen
    `positive` head, byte for byte, and the user comps are only T1C.9-T1C.11."""
    frozen = stage1.expected()["cases"]["positive"]
    got = result_of("credit-plus-comps")
    assert [f.fact.fact_id for f in got.facts[: len(frozen["facts"])]] == [
        f["fact_id"] for f in frozen["facts"]
    ]
    assert [t.table_id for t in got.tables[:8]] == [t["table_id"] for t in frozen["tables"]]
    assert list(got.limitations[: len(frozen["own_limitations"])]) == frozen["own_limitations"]


def test_peers_source_never_feeds_ev_tables() -> None:
    """The `peers` source's rows are not EV records: T1C.9 holds the context's comps only."""
    got = result_of("credit-plus-comps")
    sheet = cp1c.parse_peer_source(
        next(s for s in stage1.sources("positive") if s.source_id == "peers"),
        issuer_name=stage1.inputs("positive").issuer_name,
    )
    assert sheet is not None
    peer_labels = {p.label for p in sheet.peers}
    records = next(t for t in got.tables if t.table_id == "T1C.9").rows
    assert peer_labels
    assert not peer_labels & {r.label for r in records}
    context_names = [
        p.name for p in load_context(context_bytes("credit-plus-comps")).valuation.peers
    ]
    assert [r.label for r in records] == context_names
    facts = by_id(got)
    assert all(
        facts[f"T1C.9.{r.row_id}.name"].fact.citations[0].source_id == "context" for r in records
    )


def test_no_context_composes_eight_tables() -> None:
    """Without a context the frozen positive, gap and no-peers heads are the eight tables of
    the cp1c-owner oracle: no EV table, fact or limitation."""
    want = stage1.expected()["cases"]
    for case in stage1.CASES:
        inputs = stage1.inputs(case)
        assert (inputs.context, inputs.context_source, inputs.cp1_ebitda) == (None, None, None)
        got = cp1c.compute(inputs)
        assert [t.table_id for t in got.tables] == list(cp1c.TABLES)
        assert [f.fact.fact_id for f in got.facts] == [f["fact_id"] for f in want[case]["facts"]]
        assert list(got.limitations) == want[case]["own_limitations"]
        assert not ev_facts(got)


def test_a_context_with_nothing_to_show_composes_eight_tables() -> None:
    """`peer_source none` with `blend` and no precedents has no valuation to show."""
    context = load_context(context_bytes("precedents"))
    bare = context.model_copy(
        update={
            "valuation": context.valuation.model_copy(update={"precedents": (), "basis": "blend"})
        }
    )
    assert not cp1c.shows_valuation(bare.valuation)
    inputs = replace(stage1.inputs("no_peers"), context=bare)
    got = cp1c.compute(inputs)
    assert [t.table_id for t in got.tables] == list(cp1c.TABLES)


# --- the adapter: the pack's context, its source and CP-1's EBITDA --------------------------------------


def test_adapter_fills_the_context_source_and_the_cp4c_ebitda_fact() -> None:
    pack = pack_of("auto-public")
    base = stage1.inputs("no_peers")
    got = cp1c._with_context(base, pack, cp1_t410_facts())
    assert got.context == load_context(context_bytes("auto-public"))
    assert got.context_source is not None and got.context_source.sha256 is not None
    assert got.context_source.sha256 == manifest()["contexts"]["auto-public"]["sha256"]
    assert got.cp1_ebitda == cp1_ebitda()
    # P7-P11: CP-1C and CP-4C read the one EBITDA fact
    assert got.cp1_ebitda.fact_id == cp4c.select_cp1(cp1_t410_facts())["ebitda"].fact_id


def test_adapter_leaves_a_pack_without_context_unchanged() -> None:
    pack = _pack("no_peers")
    base = stage1.inputs("no_peers")
    assert cp1c._with_context(base, pack, ()) == base


def test_context_refused_is_issue() -> None:
    """A context that disagrees with the run is a named validator issue with the reader's text."""
    pack = pack_of("auto-public")
    other = pack.run.model_copy(update={"issuer_id": "other-issuer"})
    refused = PreparedPack(run=other, sources=pack.sources)
    with pytest.raises(ContextRefused) as caught:
        cp1c._with_context(stage1.inputs("no_peers"), refused, cp1_t410_facts())
    assert "identity.issuer_id" in str(caught.value)
    issues = cp1c.validate_peer_benchmark(
        pack=refused, submission=_submission("no_peers"), upstream=_upstream()
    )
    assert issues == (f"Context refused: {caught.value}",)


def test_a_context_source_that_cannot_be_cited_by_line_is_refused() -> None:
    pack = pack_of("auto-public")
    broken = pack.sources[-1].model_copy(update={"media_type": "application/pdf"})
    refused = PreparedPack(run=pack.run, sources=(*pack.sources[:-1], broken))
    with pytest.raises(ContextRefused):
        cp1c._with_context(stage1.inputs("no_peers"), refused, cp1_t410_facts())


def test_cp1_without_one_ebitda_fact_is_a_cp1_issue() -> None:
    pack = pack_of("auto-public")
    with pytest.raises(ValueError, match="needs exactly one T4.10 fact"):
        cp1c._with_context(stage1.inputs("no_peers"), pack, ())


def full_cp1() -> Module:
    base = _cp1_module()
    return base.model_copy(update={"facts": (*base.facts, *cp1_t410_facts())})


def test_the_report_over_a_context_pack_validates_and_the_module_reads() -> None:
    """The whole store-free path: bound upstream, validator, report, tables, module, reader."""
    pack, up = pack_of("auto-public"), _upstream(full_cp1())
    report = cp1c.peer_benchmark(pack=pack, submission=_submission("no_peers"), upstream=up)
    assert [t.table_id for t in report.tables] == [*cp1c.TABLES, *cp1c.EV_TABLES]
    validate_tables(report.tables, report.facts)  # one fact per column, no orphan fact
    module = cp1c.cp1c_module(report, inputs=up.bound, attempt=0)
    facts = cp1c.reader_facts(module)
    assert [f.fact_id for f in facts] == [*cp1c.READER_FACTS, *cp1c.EV_READER_FACTS]
    ev = {f.fact_id: cp1c.shown(f) for f in facts[len(cp1c.READER_FACTS) :]}
    selection = case_of("auto-public")["cp1c"]["selection"]
    assert ev["T1C.11.selection.selected_multiple"] == f"{selection['selected_multiple']}x"
    assert ev["T1C.11.selection.implied_ev"] == selection["implied_ev"]
    assert ev["T1C.11.selection.selected_basis"] is not None


def test_the_report_without_a_context_is_the_frozen_one() -> None:
    up = _upstream()
    report = cp1c.peer_benchmark(
        pack=_pack("positive"), submission=_submission("positive"), upstream=up
    )
    assert [t.table_id for t in report.tables] == list(cp1c.TABLES)
    module = cp1c.cp1c_module(report, inputs=up.bound, attempt=0)
    assert [f.fact_id for f in cp1c.reader_facts(module)] == list(cp1c.READER_FACTS)


def test_reader_exposes_ev_facts_only_when_present() -> None:
    """Without T1C.11 the reader's set is the frozen one; with it, a missing EV fact raises."""
    pack, up = pack_of("auto-public"), _upstream(full_cp1())
    report = cp1c.peer_benchmark(pack=pack, submission=_submission("no_peers"), upstream=up)
    module = cp1c.cp1c_module(report, inputs=up.bound, attempt=0)
    bare = module.model_copy(
        update={"tables": tuple(t for t in module.tables if t.table_id != "T1C.11")}
    )
    assert len(cp1c.reader_facts(bare)) == len(cp1c.READER_FACTS)
    gone = module.model_copy(
        update={
            "facts": tuple(f for f in module.facts if f.fact_id != "T1C.11.selection.implied_ev")
        }
    )
    with pytest.raises(ValueError, match="T1C.11.selection.implied_ev"):
        cp1c.reader_facts(gone)


# --- the Design 8 gaps, the thin sets, the NTM and EBITDA gaps -----------------------------------------


@pytest.mark.parametrize(("name", "gap"), [("user-list", GAP_UL), ("dr-public", GAP_DR)])
def test_user_list_and_dr_public_name_the_o7d_gap(name: str, gap: str) -> None:
    got = by_id(result_of(name))
    assert got["T1C.11.selection.reason"].fact.text == gap
    assert got["T1C.11.selection.selected_basis"].fact.status == "missing"
    assert got["T1C.11.selection.selected_multiple"].fact.limitation == gap
    assert f"Valuation basis not selected: {gap}." in result_of(name).limitations
    figures = [f for f in ev_facts(result_of(name)) if f.fact.table_id == "T1C.9"]
    assert any(f.fact.limitation == gap for f in figures)


def test_auto_with_dr_public_adds_the_precedent_count_to_the_gap() -> None:
    got = by_id(result_of("auto-dr-public"))
    assert (
        got["T1C.11.selection.reason"].fact.text == f"{GAP_DR}; precedents 0 admitted of 3 required"
    )
    assert got["T1C.11.selection.selected_basis"].fact.text == "Insufficient Information"


def test_auto_with_dr_public_still_selects_precedents_when_they_qualify() -> None:
    """The key's `precedents` case has 4 admitted precedents (median 9.50); under `auto` and
    `cp_dr_public` they are used, because the public side gives no figures and `auto` falls back."""
    context = load_context(context_bytes("precedents"))
    valuation = context.valuation.model_copy(
        update={"peer_source": "cp_dr_public", "basis": "auto"}
    )
    inputs = replace(
        inputs_of("precedents"), context=context.model_copy(update={"valuation": valuation})
    )
    got = by_id(cp1c.compute(inputs))
    want = case_of("precedents")["cp1c"]["selection"]
    assert got["T1C.11.selection.selected_basis"].fact.text == "precedents"
    assert (
        cp1c.shown(got["T1C.11.selection.selected_multiple"].fact)
        == f"{want['selected_multiple']}x"
    )


@pytest.mark.parametrize("name", ["auto-thin", "public-thin", "window-edges", "blend-thin"])
def test_fewer_than_three_never_zero(name: str) -> None:
    """Below three admitted records no median, outlier count, selected multiple or implied EV is
    shown, least of all zero; the cell is a missing fact with its reason."""
    facts = by_id(result_of(name))
    sets = [s for s in ("public_comps", "precedents") if f"T1C.10.{s}.median" in facts]
    thin = [s for s in sets if facts[f"T1C.10.{s}.median"].fact.status == "missing"]
    assert thin
    for s in thin:
        for field in ("median", "outliers"):
            fact = facts[f"T1C.10.{s}.{field}"].fact
            assert (fact.status, fact.amount) == ("missing", None)
            assert fact.limitation and "admitted of 3 required" in fact.limitation
    chosen = facts["T1C.11.selection.selected_multiple"].fact
    assert (chosen.status, chosen.amount) == ("missing", None)
    implied = facts["T1C.11.selection.implied_ev"].fact
    assert (implied.status, implied.amount) == ("missing", None)
    zero = [
        f.fact.fact_id
        for f in ev_facts(result_of(name))
        if f.fact.unit == cp1c.MULTIPLE and f.fact.amount is not None and f.fact.amount <= 0
    ]
    assert not zero


def test_a_user_ntm_multiple_is_not_applied_to_ltm_ebitda() -> None:
    """Not pinned by the key: the multiple is carried with its label and the implied EV is a gap."""
    context = load_context(context_bytes("user-multiple"))
    um = context.valuation.user_multiple.model_copy(update={"basis": "NTM"})
    changed = context.model_copy(
        update={"valuation": context.valuation.model_copy(update={"user_multiple": um})}
    )
    got = by_id(cp1c.compute(replace(inputs_of("user-multiple"), context=changed)))
    assert cp1c.shown(got["T1C.11.selection.selected_multiple"].fact) == "8.50x"
    implied = got["T1C.11.selection.implied_ev"].fact
    assert implied.status == "missing"
    assert implied.limitation == "Not calculable: an NTM multiple is not applied to LTM EBITDA"


@pytest.mark.parametrize("change", ["missing", "zero", "unit"])
def test_an_unusable_cp1_ebitda_is_a_gap_never_zero(change: str) -> None:
    ebitda = cp1_ebitda()
    updates: dict[str, dict[str, Any]] = {
        "missing": {"status": "missing", "amount": None, "limitation": "x"},
        "zero": {"amount": Decimal(0)},
        "unit": {"unit": "PERCENT"},
    }
    update = updates[change]
    got = by_id(cp1c.compute(inputs_of("issuer-trading", ebitda.model_copy(update=update))))
    issuer = got["T1C.11.selection.issuer_ebitda"].fact
    assert (issuer.status, issuer.amount) == ("missing", None)
    assert issuer.limitation == "CP-1 LTM adjusted EBITDA is not a known positive amount"
    for field in ("selected_multiple", "implied_ev"):
        assert (
            got[f"T1C.11.selection.{field}"].fact.status,
            got[f"T1C.11.selection.{field}"].fact.amount,
        ) == ("missing", None)
    single = got["T1C.10.issuer_trading.median"].fact
    assert single.status == "missing"


def test_the_context_is_cited_by_line_in_any_layout() -> None:
    """The citation is the line the value sits on, whatever the file's indentation."""
    raw = json.dumps(json.loads(context_bytes("auto-public")), indent=4).encode() + b"\n"
    source = context_source("auto-public", raw)
    cite = cp1c.context_cites(source)
    path = ("valuation", "peers", 0, "ev_m")
    (got,) = cite(path)
    lines = raw.decode("utf-8").splitlines()
    assert lines[int(got.locator.removeprefix("line:")) - 1].strip() == got.quote
    assert got.quote == '"ev_m": "540",'
    with pytest.raises(ValueError, match="no citable value"):
        cite(("valuation", "peers", 9, "ev_m"))


def test_valuation_to_show() -> None:
    valuation = load_context(context_bytes("auto-public")).valuation
    for update, shows in (
        ({"peer_source": "none", "basis": "public_comps", "peers": ()}, False),
        ({"peer_source": "none", "basis": "blend", "peers": ()}, False),
        ({"peer_source": "cp_dr_public", "basis": "blend", "peers": ()}, True),
        ({"peer_source": "user_list", "basis": "precedents", "peers": ()}, False),
        ({"peer_source": "none", "basis": "auto", "peers": ()}, True),
        ({"peer_source": "none", "basis": "issuer_trading", "peers": ()}, True),
        ({"peer_source": "none", "basis": "user_multiple", "peers": ()}, True),
        ({"peer_source": "user_comps", "basis": "public_comps"}, True),
    ):
        assert cp1c.shows_valuation(valuation.model_copy(update=update)) is shows, update


# --- survivors of the Phase 7 Task 3 review (L3): derived contexts, expected from the key's rules ----------
#
# The key's rules (`expected.json#rules`): outlier = absolute relative deviation from the set median
# strictly above 0.5, flag only; a median needs 3 admitted records; `t1c10_rows` shows a set's row
# for its basis or when that set has records; the thin line stands under five admitted records.


def derived_result(
    name: str, edit: Callable[[dict[str, Any]], None], ebitda: Fact | None = None
) -> cp1c.PeerBenchmarkResult:
    """CP-1C over the pinned context `name` edited by `edit`, read as the oracle's builder writes it."""
    document = json.loads(context_bytes(name))
    edit(document)
    raw = (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode()
    inputs = replace(
        stage1.inputs(base_case(name)),
        context=load_context(raw),
        context_source=context_source(name, raw),
        cp1_ebitda=cp1_ebitda() if ebitda is None else ebitda,
    )
    return cp1c.compute(inputs)


def thin_line() -> str:
    """The key's thin-universe line, as auto-public (3 admitted) carries it."""
    line = case_of("auto-public")["cp1c"]["own_limitations_new"][-1]
    assert "fewer than five" in line
    return str(line)


def admit_all_peers(document: dict[str, Any], *, spare_last: bool = False) -> None:
    """auto-public's peers D (stale) and E (EV zero) made admissible: 5 admitted, or 4 sparing E."""
    peers = document["valuation"]["peers"]
    peers[3]["as_of"] = "2025-12-01"
    if not spare_last:
        peers[4]["ev_m"] = "500"


def test_thin_line_stands_below_five_admitted_and_not_at_five() -> None:
    """M02: THIN_UNIVERSE is 5, so the line is for 3 and 4 admitted and absent at 5."""
    assert cp1c.THIN_UNIVERSE == 5
    five = derived_result("auto-public", admit_all_peers)
    four = derived_result("auto-public", lambda d: admit_all_peers(d, spare_last=True))
    assert by_id(five)["T1C.10.public_comps.n_admitted"].fact.amount == 5
    assert by_id(four)["T1C.10.public_comps.n_admitted"].fact.amount == 4
    assert thin_line() not in five.limitations
    assert thin_line() in four.limitations
    assert thin_line() in result_of("auto-public").limitations  # the key's own 3 admitted


@pytest.mark.parametrize(
    ("ev", "flag", "outliers"),
    [("630", "Within range", 0), ("631", "Outlier", 1), ("3000", "Outlier", 1)],
)
def test_the_flag_follows_the_rule_strictly_above_one_half(
    ev: str, flag: str, outliers: int
) -> None:
    """M11: peers A, B, C admitted with multiples EV/60, 6 and 7 (median 7 when A is above 7): A at
    10.5 is exactly one half above the median (within), above that it is an outlier."""

    def edit(document: dict[str, Any]) -> None:
        document["valuation"]["peers"][0]["ev_m"] = ev

    got = by_id(derived_result("auto-public", edit))
    # independent model of the rule: multiples 6 and 7 are B and C (330/55, 700/100)
    median = Fraction(7)
    assert (abs(Fraction(int(ev), 60) - median) / median > Fraction(1, 2)) == (flag == "Outlier")
    assert got["T1C.9.e01.flag"].fact.text == flag
    assert got["T1C.9.e02.flag"].fact.text == "Within range"
    assert got["T1C.10.public_comps.outliers"].fact.amount == outliers


def test_public_comps_present_under_precedents_get_their_row() -> None:
    """M08 (`t1c10_rows`: public_comps "when peer records exist"): the `precedents` basis with peer
    records still shows the public comps row. (The mirror, precedents under another basis, cannot
    be written: the context form refuses precedents unless the basis is precedents or blend.)"""
    peers = json.loads(context_bytes("auto-public"))["valuation"]["peers"]

    def with_peers(document: dict[str, Any]) -> None:
        document["valuation"]["peer_source"] = "user_comps"
        document["valuation"]["peers"] = peers

    got = by_id(derived_result("precedents", with_peers))
    assert got["T1C.10.public_comps.n_total"].fact.amount == len(peers)


def test_cp1_ebitda_without_a_period_is_a_gap() -> None:
    """M05: the EBITDA is usable only with an LTM period; without one it is the stated gap."""
    got = by_id(
        cp1c.compute(inputs_of("issuer-trading", cp1_ebitda().model_copy(update={"period": None})))
    )
    issuer = got["T1C.11.selection.issuer_ebitda"].fact
    assert (issuer.status, issuer.amount) == ("missing", None)
    assert issuer.limitation == "CP-1 LTM adjusted EBITDA is not a known positive amount"
    assert got["T1C.11.selection.implied_ev"].fact.status == "missing"
