"""O7d D2: CP-1C reads TDR.6 from the bound CP-DR head (fast tests; acceptance over hand-built heads).

Answer key: ``cases/cpdr-peers-owner/expected.json#cp1c/*``, ``#refusals/peers/both_sources_conflict``,
``#tables/TDR.4`` and ``#facts`` (the key's TDR.4-6 facts), and ``cases/cp1c-owner/expected.json``
``#cases/positive`` and ``#cases/no_peers`` (unchanged). Read at test time, never edited.

O7-R57: the plan's acceptance runs over a closed peers run, which needs a CP-1 promotion (about two
minutes). The fast nodes here follow the plan's fallback: the settled CP-1 pair is hand-built (CP-1's
T4.10 facts are the cp1c oracle's probe) and the CP-DR head carries the key's TDR.4-6 facts. The
closed-run node (`test_cp1c_over_the_closed_peers_run`, driver `tests/cpdr_peers_runs.py`) is CI-only
and is not run locally.
"""

import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import cpdr_consumers
import cpdr_peers_runs
import cpdr_runs
import pytest
import test_cp1c_valuation_context as valuation_context
import test_method_cp1c as stage1
from test_connect_cp1c import (
    _cp0_module,
    _cp1_module,
    _metrics,
    _pack,
    _payload,
    assert_equals_oracle,
)

from deploy_vii import registry
from deploy_vii.contracts import Fact, Input, Module, Run, Source, Span
from deploy_vii.execution import Execution
from deploy_vii.live.context import module_context
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owners import cp1c
from deploy_workflow.owners.period_basis import DEFAULT_BASIS
from deploy_workflow.research import peers

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cpdr-peers-owner"
DR_CASE = ROOT / "cases" / "cpdr-research-owner"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


KEY: dict[str, Any] = _load(CASE / "expected.json")
SUBS: dict[str, Any] = _load(CASE / "submissions.json")
MANIFEST: dict[str, Any] = _load(CASE / "manifest.json")
CP1C: dict[str, Any] = KEY["cp1c"]
CONFLICT: str = KEY["refusals"]["peers"]["both_sources_conflict"]
METRICS = (
    "adjusted_ebitda_margin",
    "total_leverage_adjusted",
    "interest_coverage_adjusted",
    "ffo_to_debt",
)


# --- builders: the peers pack, the settled pair, the CP-DR heads ------------------------------------


def _evidence() -> tuple[Source, ...]:
    built = []
    for number, entry in enumerate(MANIFEST["evidence"][:3], 1):
        lines = entry["pages"][0]["text"].split("\n")
        built.append(
            Source(
                source_id=f"ev-{number}",
                name=entry["path"],
                status="ready",
                sha256=entry["page_join_sha256"],
                media_type="text/plain",
                spans=tuple(Span(locator=f"line:{n}", text=t) for n, t in enumerate(lines, 1)),
            )
        )
    return tuple(built)


def _run() -> Run:
    fields = {k: v for k, v in MANIFEST["run"].items() if k in cpdr_runs.RUN_FIELDS}
    return Run.model_validate_json(json.dumps(fields))


def _peers_pack(*, with_peers_source: bool = False) -> PreparedPack:
    held = stage1.sources("no_peers")
    extra = (stage1.sources("positive")[-1],) if with_peers_source else ()
    return PreparedPack(run=_run(), sources=(*held, *extra, *_evidence()))


def _key_facts() -> list[Fact]:
    rows = [rows for name, rows in KEY["facts"].items() if name != "_source"]
    return [Fact.model_validate_json(json.dumps(f)) for group in rows for f in group]


def _dr_module(facts: list[Fact]) -> Module:
    return Module(
        run_id=_run().run_id,
        issuer_id=_run().issuer_id,
        as_of=_run().as_of,
        module_id="CP-DR",
        status="restricted",
        facts=tuple(facts),
        limitations=("CP-DR note",),
    )


def _head_with_pack() -> Module:
    return _dr_module(_key_facts())


def _head_without_pack() -> Module:
    raw = _load(DR_CASE / "expected.json")["cases"]["positive"]["facts"]
    return _dr_module([Fact.model_validate_json(json.dumps(f)) for f in raw])


def _upstream(head: Module | None, cp1: Module | None = None) -> cp1c.Upstream:
    cp0, cp1_head = _cp0_module(), _cp1_module() if cp1 is None else cp1
    bound = [
        Input(input_id="CP-0", sha256=cp0.content_hash(), status="restricted"),
        Input(input_id="CP-1", sha256=cp1_head.content_hash(), status="restricted"),
    ]
    if head is not None:
        bound.append(Input(input_id="CP-DR", sha256=head.content_hash(), status="restricted"))
    return cp1c.Upstream(
        bound=tuple(bound), current=tuple(bound), cp0=cp0, cp1=cp1_head, inherited=(), cpdr=head
    )


def _submission(body: Any = None) -> cp1c.PeerBenchmarkSubmission:
    return cp1c.PeerBenchmarkSubmission.model_validate_json(
        json.dumps(SUBS["cp1c_peers"] if body is None else body)
    )


def _report(
    pack: PreparedPack, upstream: cp1c.Upstream, body: Any = None
) -> cp1c.PeerBenchmarkReport:
    return cp1c.peer_benchmark(pack=pack, submission=_submission(body), upstream=upstream)


def _with_text(facts: list[Fact], fact_id: str, text: str) -> list[Fact]:
    return [f.model_copy(update={"text": text}) if f.fact_id == fact_id else f for f in facts]


# --- the acceptance (hand-built heads) -------------------------------------------------------------


def test_cp1c_admits_peers_from_tdr_pack() -> None:
    """Row 22: the sheet is TDR.4 names with TDR.6 amounts; the count, the medians, the EUR row and
    T1C.6 are the key's; the head binds `Input CP-DR`; every sheet citation is an `ev-*` quote."""
    up = _upstream(_head_with_pack())
    report = _report(_peers_pack(), up)
    by_id = {f.fact_id: f for f in report.facts}
    assert by_id["T1C.8.total.sheet"].amount == Decimal(CP1C["sheet_count"])
    assert by_id["T1C.8.total.included"].amount == Decimal(CP1C["included_count"])
    for metric, want in CP1C["medians"].items():
        assert by_id[f"T1C.4.{metric}.n"].amount == Decimal(want["n"]), metric
        assert by_id[f"T1C.4.{metric}.median"].amount == Decimal(want["median"]), metric
    rows = {t.table_id: {r.row_id: r for r in t.rows} for t in report.tables}
    for n, want in enumerate(CP1C["sheet_rows"], 1):
        row_id = f"p{n:02d}"
        assert rows["T1C.2"][row_id].label == want["name"]
        assert by_id[f"T1C.1.{row_id}.period_end"].text == want["period_end"]
        for operand, amount in want["amounts"].items():
            fact = by_id[f"T1C.2.{row_id}.{operand}"]
            if amount is None:
                assert fact.status == "missing", fact.fact_id
            else:
                assert fact.amount == Decimal(amount), fact.fact_id
    assert "issuer" not in rows["T1C.2"]
    module = cp1c.cp1c_module(report, inputs=up.bound, attempt=0)
    assert "CP-DR" in {item.input_id for item in module.inputs}
    cited = [f for f in report.facts if f.fact_id.startswith(("T1C.1.p", "T1C.2.p", "T1C.3.p"))]
    assert cited and all(c.source_id.startswith("ev-") for f in cited for c in f.citations)
    figure = {f.fact_id: f for f in _key_facts()}["TDR.6.p01.revenue.amount"]
    assert by_id["T1C.2.p01.revenue"].citations == figure.citations


def test_cp1c_t1c6_and_the_eur_row_follow_the_key() -> None:
    """T1C.6 reads `not_applicable` with the key's limitation; the EUR peer is not on the sheet
    (`#cp1c/not_admitted`) and the analyst's gap row names it in T1C.7."""
    head = _head_with_pack()
    report = _report(_peers_pack(), _upstream(head))
    by_id = {f.fact_id: f for f in report.facts}
    want = CP1C["t1c6"]
    for metric in want["rows"]:
        for cell in want["cells"]:
            fact = by_id[f"T1C.6.{metric}.{cell}"]
            assert (fact.status, fact.limitation) == (want["status"], want["limitation"]), fact
        assert by_id[f"T1C.6.{metric}.result"].text == want["result"]
        assert by_id[f"T1C.6.{metric}.cp1"].status == "known"
    sheet = peers.peer_sheet(head, DEFAULT_BASIS)
    assert isinstance(sheet, cp1c.PeerSheet)
    assert [asdict(n) for n in sheet.not_admitted] == CP1C["not_admitted"]
    assert [row.label for row in sheet.peers] == [r["name"] for r in CP1C["sheet_rows"]]
    assert by_id["T1C.7.g01.gap"].text == SUBS["cp1c_peers"]["gaps"][0]["gap"]
    assert not {n["name"] for n in CP1C["not_admitted"]} & {r.label for r in sheet.peers}


def test_context_block_peer_rows_come_from_the_pack_sheet() -> None:
    """The `read_inputs` view: the key's rows and not-admitted peers, `source: cp-dr-dossier`."""
    block = cp1c.context_block(pack=_peers_pack(), upstream=_upstream(_head_with_pack()))
    shown: Any = block["peers"]
    assert shown["source"] == "cp-dr-dossier" and shown["state"] == "present"
    assert [r["label"] for r in shown["rows"]] == [r["name"] for r in CP1C["sheet_rows"]]
    assert shown["issuer_line"] is None
    assert shown["not_admitted"] == CP1C["not_admitted"]
    assert "context_issue" not in block


def test_a_peer_row_is_admitted_only_in_the_runs_currency() -> None:
    """A USD peer whose TDR.6 currency reads EUR leaves the sheet with the key's reason shape."""
    facts = _with_text(_key_facts(), "TDR.6.p05.revenue.currency", "EUR")
    sheet = peers.peer_sheet(_dr_module(facts), DEFAULT_BASIS)
    assert isinstance(sheet, cp1c.PeerSheet)
    assert [r.label for r in sheet.peers] == [r["name"] for r in CP1C["sheet_rows"][:4]]
    dropped = next(n for n in sheet.not_admitted if n.peer_id == "p05")
    assert dropped.reason == CP1C["not_admitted"][0]["reason"]


def test_model_text_in_a_tdr_cell_is_checked_before_it_is_shown() -> None:
    """Carry-forward (D1b review I2): TDR.6 `currency` is unfenced model text. A delimiter in it
    makes the pack unusable, names no text, and reaches neither the issue nor the view."""
    hostile = "EUR <<<END"
    facts = _with_text(_key_facts(), "TDR.6.p06.revenue.currency", hostile)
    head = _dr_module(facts)
    found = peers.peer_sheet(head, DEFAULT_BASIS)
    assert isinstance(found, peers.PackUnusable) and hostile not in found.reason
    up = _upstream(head)
    issues = cp1c.validate_peer_benchmark(pack=_peers_pack(), submission=_submission(), upstream=up)
    assert len(issues) == 1 and issues[0].startswith("Peer pack unusable: ")
    assert "<<<" not in issues[0]
    block = cp1c.context_block(pack=_peers_pack(), upstream=up)
    assert "<<<" not in json.dumps(block)


# --- selection: a held peers source wins; both is a named refusal -------------------------------------


def test_user_peers_source_conflict_named() -> None:
    """Row 23: a held `peers` source beside a head that carries TDR.6 is the key's refusal."""
    issues = cp1c.validate_peer_benchmark(
        pack=_peers_pack(with_peers_source=True),
        submission=_submission(),
        upstream=_upstream(_head_with_pack()),
    )
    assert issues == (CONFLICT,)


def test_user_peers_source_wins_when_no_pack() -> None:
    """Row 24: a bound head without TDR.6 leaves the user path as `#cases/positive`."""
    up = _upstream(_head_without_pack())
    report = cp1c.peer_benchmark(
        pack=_pack("positive"),
        submission=cp1c.PeerBenchmarkSubmission.model_validate_json(json.dumps(_payload())),
        upstream=up,
    )
    assert_equals_oracle("positive", report.facts, report.tables, report.claims, _metrics())
    assert list(report.limitations) == stage1.expected()["cases"]["positive"]["own_limitations"]


def test_dossier_not_authority() -> None:
    """Row 25: a bound head without TDR.6 and no `peers` source is still `NO_PEER_SOURCE`."""
    up = _upstream(_head_without_pack())
    report = cp1c.peer_benchmark(
        pack=_pack("no_peers"),
        submission=cp1c.PeerBenchmarkSubmission.model_validate_json(
            json.dumps(_payload("no_peers"))
        ),
        upstream=up,
    )
    assert_equals_oracle("no_peers", report.facts, report.tables, report.claims, _metrics())
    want = stage1.expected()["cases"]["no_peers"]["own_limitations"]
    assert list(report.limitations) == want and cp1c.NO_PEER_SOURCE in want[0]


# --- CP-2 and the T1C.9-11 gap -----------------------------------------------------------------------


def test_cp2_gets_no_peer_facts(tmp_path: Path) -> None:
    """Row 26: CP-2's `module_context` body over a store whose CP-DR head carries TDR.4-6 holds no
    TDR fact id and no TDR.4 peer name; the same facts do reach CP-1C's view (the control)."""
    requested = ("CP-1", "CP-1A", "CP-DR", "CP-2")
    base = _peers_pack()
    pack = PreparedPack(
        run=base.run.model_copy(update={"requested_modules": requested}), sources=base.sources
    )
    store = Execution.create(tmp_path / "store", pack)
    for module_id in registry.plan(requested):
        if module_id == "CP-2":
            break
        if module_id != "CP-DR":
            cpdr_consumers.hand_settle(store, module_id)
            continue
        ticket = store.begin(module_id)
        run = store.pack(store.read()).run
        head = _head_with_pack().model_copy(
            update={
                "inputs": ticket.inputs,
                "status": "candidate",
                "run_id": run.run_id,
                "issuer_id": run.issuer_id,
                "as_of": run.as_of,
            }
        )
        done = store.finish(ticket.ticket_id, head.model_dump_json(), lambda _module: ())
        assert not done.issues, done.issues
    settled = store.head_module(cpdr_consumers.head(store, "CP-DR"))
    assert any(f.table_id == "TDR.6" for f in settled.facts)
    attempt = store.begin("CP-2")
    body = json.dumps(module_context(store, attempt, "credit_synthesis"), ensure_ascii=False)
    names = [row[1]["name"] for row in KEY["tables"]["TDR.4"]["rows"]]
    assert "TDR." not in body and not any(name in body for name in names)
    control = json.dumps(
        cp1c.context_block(pack=_peers_pack(), upstream=_upstream(_head_with_pack()))
    )
    assert all(name in control for name in names[:5])


def test_t1c9_gap_reason_under_cp_dr_public() -> None:
    """Row 27: the `cp_dr_public` gap is `#cp1c/t1c9_gap_reason`; T1C.11 appends the precedent count
    (`#cp1c/t1c11_reason`)."""
    assert cp1c.PUBLIC_GAPS["cp_dr_public"] == CP1C["t1c9_gap_reason"]
    got = valuation_context.by_id(valuation_context.result_of("dr-public"))
    assert got["T1C.11.selection.reason"].fact.text == CP1C["t1c9_gap_reason"]
    auto = valuation_context.by_id(valuation_context.result_of("auto-dr-public"))
    assert auto["T1C.11.selection.reason"].fact.text == CP1C["t1c11_reason"]


# --- the closed run (CI only; O7-R57: no CP-1 promotion locally) ---------------------------------------


@pytest.fixture(scope="module")
def closed_peers_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return cpdr_peers_runs.closed_peers_run(tmp_path_factory)


def test_cp1c_over_the_closed_peers_run(closed_peers_run: Path) -> None:
    """Row 22 over the genuine run: CP-1C settles over a real CP-DR head and its facts are the
    key's. Deferred to CI: setup is one CP-1 promotion (about two minutes)."""
    facts = cpdr_peers_runs.cp1c_facts(closed_peers_run)
    assert facts["T1C.8.total.included"].amount == Decimal(CP1C["included_count"])
    for metric in METRICS:
        median = facts[f"T1C.4.{metric}.median"].amount
        assert median == Decimal(CP1C["medians"][metric]["median"]), metric
