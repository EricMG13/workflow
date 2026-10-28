"""S1a acceptance: the credit-snapshot run over the pinned oracle, CP-0 -> CP-MODEL.

Expectations come from `cases/snapshot/{expected,submissions,cp2-view-tree}.json` and the S1a
lease only, never from the code under test. The slow fixtures promote CP-1 for real (11-26
minutes per case) and are built once per module; every refusal test forks a copy of them.
"""

import hashlib
import importlib
import itertools
import json
import re
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from deploy_vii.contracts import Fact, Input, Module, Run
from deploy_vii.cp2_synthesis import _validate_step as cp2_validate_step
from deploy_vii.cp_model_workflow import verify_cp_model_publication
from deploy_vii.execution import (
    Attempt,
    Execution,
    NotAuthorized,
    StepSubmission,
    StepValidation,
    bounded_issues,
    current_inputs,
    head_of,
)
from deploy_vii.live.tools import UNBACKED_ABSENCE, cited_locators
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import plan
from deploy_workflow.financial_workflow import _FrozenExecution, _snapshot
from deploy_workflow.owner_workflow import (
    OWNER_SPECS,
    OwnerRunReceipt,
    OwnerWorkflow,
    _verify_audit,
    _verify_calls_reads,
    _verify_submissions,
)
from deploy_workflow.workflow import SourceEvidence, WorkflowError

runs: Any = importlib.import_module("s1a_runs")
submission_module: Any = importlib.import_module("deploy_vii.live.submission")
ORACLE: dict[str, Any] = runs.oracle()
EXPECTED: dict[str, Any] = ORACLE["expected"]
SUBMISSIONS: dict[str, Any] = ORACLE["submissions"]
TREE: dict[str, Any] = ORACLE["tree"]
CASES = ("positive", "gap")
FORBIDDEN_KEYS = {"quote", "citations", "record_json"}
ID_PLACEHOLDER = re.compile(r"<fact_id of the CP-1 fact for FIG:([a-z0-9_]+), bound at run time>")
LABEL_PLACEHOLDER = re.compile(r"<label and period of FIG:([a-z0-9_]+)>")
CITES_PLACEHOLDER = "<the CP-1 fact's own citations, bound at run time>"
REFERENCE_NOTES = ("spelled_as", "note", "table_coordinate")
JUDGED_NOT_ESTABLISHED = {"", "0", "N/A", "TBD"}
# sha256 of the reviewed literal cases/snapshot/cp2-blocked-cp1a-submission.json (lease R3-4)
BLOCKED_CP2_SHA256 = "0616a4a278104665122a474b434d3122637934845c0593290ddc68317cdb06e3"


def _status(module_id: str) -> str:
    """The oracle's settled status of a module: the first word of its `statuses_S1a` entry."""
    return str(EXPECTED["execution"]["statuses_S1a"][module_id]).split()[0]


# --- helpers ---------------------------------------------------------------------------------


def _verify(root: Path, receipt: Any) -> None:
    from deploy_workflow.owner_workflow import verify_owner_run_receipt

    verify_owner_run_receipt(
        Execution(root / "store"), receipt, publication_directory=root / "model"
    )


def _tree(*roots: Path) -> dict[str, bytes]:
    return {
        str(p): p.read_bytes() for root in roots for p in sorted(root.rglob("*")) if p.is_file()
    }


def _head(store: Execution, module_id: str) -> Any:
    return next(h for h in store.read().heads if h.module_id == module_id)


def _module(store: Execution, module_id: str) -> Module:
    return store.head_module(_head(store, module_id))


def _attempt(store: Execution, module_id: str) -> Attempt:
    result = _head(store, module_id).result_sha256
    return next(a for a in store.read().attempts if a.result_sha256 == result)


def _table_view(module: Module) -> list[dict[str, Any]]:
    """The oracle's table notation: per fact the text, status, [source_id, locator] cites,
    value class and limitation, under the table's columns and rows. A Front Page table
    (`cp2.*`) names its line's own label as the column, as the oracle does."""
    facts = {f.fact_id: f for f in module.facts}
    out = []
    for table in module.tables:
        rows = []
        for row in table.rows:
            cells = []
            for fact_id, column in zip(row.fact_ids, table.columns, strict=True):
                fact = facts[fact_id]
                cells.append(
                    {
                        "fact_id": fact_id,
                        "column": fact.label if table.table_id.startswith("cp2.") else column.label,
                        "text": fact.text,
                        "status": fact.status,
                        "cites": [[c.source_id, c.locator] for c in fact.citations],
                        "value_class": fact.value_class,
                        "limitation": fact.limitation,
                    }
                )
            rows.append({"row_id": row.row_id, "label": row.label, "facts": cells})
        out.append(
            {
                "table_id": table.table_id,
                "title": table.title,
                "row_header": table.row_header,
                "columns": [{"field": c.field, "label": c.label} for c in table.columns],
                "rows": rows,
            }
        )
    return out


def _compare_tables(actual: list[dict[str, Any]], expected: list[dict[str, Any]]) -> None:
    assert [t["table_id"] for t in actual] == [t["table_id"] for t in expected]
    for got, want in zip(actual, expected, strict=True):
        assert got == want, got["table_id"]


def _label_period(fact: Fact) -> str:
    return f"{fact.label} · {fact.period}" if fact.period else fact.label


def _bind_expected(value: Any, bindings: dict[str, tuple[str, str]], facts: dict[str, Fact]) -> Any:
    """Substitute the oracle's run-time placeholders (ids, labels and periods, citations)."""
    if isinstance(value, str):
        value = ID_PLACEHOLDER.sub(lambda m: bindings[m[1]][0], value)
        return LABEL_PLACEHOLDER.sub(lambda m: _label_period(facts[bindings[m[1]][0]]), value)
    if isinstance(value, list):
        return [_bind_expected(v, bindings, facts) for v in value]
    if isinstance(value, dict):
        return {k: _bind_expected(v, bindings, facts) for k, v in value.items()}
    return value


def _shape(value: Any) -> Any:
    """Key tree with scalar type names; a list keeps its distinct element shapes."""
    if isinstance(value, dict):
        return {k: _shape(v) for k, v in value.items()}
    if isinstance(value, list):
        shapes: list[Any] = []
        for item in value:
            if (s := _shape(item)) not in shapes:
                shapes.append(s)
        return shapes
    return type(value).__name__


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def _ok_reads(receipt: OwnerRunReceipt, binding: Any) -> set[tuple[str, str]]:
    pages = set()
    for call in receipt.calls:
        if call.binding == binding and call.tool == "read_pages" and call.status == "ok":
            a = call.arguments
            pages |= {
                (a["source_id"], f"page:{n}") for n in range(a["first_page"], a["last_page"] + 1)
            }
    return pages


def _searches(receipt: OwnerRunReceipt, binding: Any) -> list[str | None]:
    return [
        c.arguments.get("source_id")
        for c in receipt.calls
        if c.binding == binding and c.tool == "search_pack" and c.status == "ok"
    ]


@dataclass
class Closed:
    case: str
    root: Path
    store: Execution
    pack: PreparedPack
    receipt: OwnerRunReceipt
    expected: dict[str, Any]
    body: dict[str, Any]
    bindings: dict[str, tuple[str, str]]


_PROMOTED: dict[str, tuple[OwnerWorkflow, PreparedPack]] = {}


def _promoted(case: str, factory: pytest.TempPathFactory) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 and CP-1 settled once per case (the slow part); CP-1A begun, untouched."""
    if case not in _PROMOTED:
        _PROMOTED[case] = runs.promoted(case, factory.mktemp(f"s1a-promoted-{case}"))
    return _PROMOTED[case]


@pytest.fixture(scope="module", params=CASES)
def closed(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Closed:
    case: str = request.param
    template, pack = _promoted(case, tmp_path_factory)
    root = tmp_path_factory.mktemp(f"s1a-closed-{case}")
    workflow = runs.clone_workflow(template, root)
    runs.close(workflow, pack, case, root / "owner-receipt.json")
    store = Execution(root / "store")
    receipt = OwnerRunReceipt.model_validate_json((root / "owner-receipt.json").read_bytes())
    read = next(r for r in receipt.input_reads if r.binding.module_id == "CP-2")
    body = json.loads(read.body)
    figures = SUBMISSIONS["figures"]
    names = runs.figure_names(runs.literal(case, "credit_synthesis"))
    bindings = runs.fig_bindings(store, body, {n: figures[n] for n in names})
    return Closed(case, root, store, pack, receipt, EXPECTED[runs.CASES[case][2]], body, bindings)


@pytest.fixture(scope="module")
def positive_promoted(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[OwnerWorkflow, PreparedPack]:
    return _promoted("positive", tmp_path_factory)


@pytest.fixture(scope="module")
def cp2_ready(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path_factory: pytest.TempPathFactory
) -> tuple[OwnerWorkflow, PreparedPack]:
    """Positive run with a valid CP-1A and CP-2 begun, before any CP-2 call."""
    template, pack = positive_promoted
    workflow = runs.clone_workflow(template, tmp_path_factory.mktemp("s1a-cp2-ready"))
    assert runs.drive_cp1a(workflow, pack, "positive")["status"] == "valid"
    return workflow, pack


# --- the oracle itself and the cheap refusals (no CP-1 promotion) -----------------------------


def test_oracle_pins_pack_and_plan() -> None:
    assert ORACLE["expected"]["schema_version"] == "snapshot-s1-expected/2"
    for case in CASES:
        pack = runs.make_pack(case)
        assert plan(pack.run.requested_modules) == tuple(EXPECTED["execution"]["plan_order"])
        assert [s.source_id for s in pack.sources] == ["identity", "financial", "business"]
        business = next(s for s in pack.sources if s.source_id == "business")
        manifest = ORACLE["manifest"]["business_source"][runs.CASES[case][1]]
        assert business.sha256 == manifest["sha256"]
        assert business.limitation == manifest["pack_limitation"]
        bound = runs.literal(case, "readiness_review", pack)
        assert "<<" not in bound and pack.content_hash() in bound


def test_figure_predicate_selects_exactly_one_ltm_fact() -> None:
    def fact(fid: str, period: str, label: str, table: str = "T4.10") -> Fact:
        return Fact(fact_id=fid, label=label, table_id=table, period=period, text="x")

    ltm_label = "LTM Q4 25 (2025-01-01 to 2025-12-31) · fcf_to_debt"
    ltm = fact("ltm", "LTM Q4 25: 2025-01-01 to 2025-12-31", ltm_label)
    fy = fact("fy", "FY25: 2025-01-01 to 2025-12-31", ltm_label.replace("LTM Q4 25", "FY25"))
    other = fact("t5", ltm.period or "", ltm_label, table="T5.1")
    assert runs.figure_fact([fy, other, ltm], "fcf_to_debt") is ltm
    with pytest.raises(RuntimeError):
        runs.figure_fact([fy, other], "fcf_to_debt")
    with pytest.raises(RuntimeError):
        runs.figure_fact([ltm, fact("again", ltm.period or "", ltm_label)], "fcf_to_debt")


def test_unreplaced_figure_stays_unreplaced_and_known_ones_resolve() -> None:
    text = "{{FIG:a}} and {{FIG:b}}"
    assert runs.bind_figures(text, {"a": ("id1", "x")}) == "{id1|x} and {{FIG:b}}"


def _selection(pack: PreparedPack, modules: tuple[str, ...]) -> PreparedPack:
    document = {**json.loads(pack.run.model_dump_json()), "requested_modules": modules}
    return PreparedPack(run=Run.model_validate_json(json.dumps(document)), sources=pack.sources)


def test_cp5_selection_and_spec_overrides_refuse_before_writing(tmp_path: Path) -> None:
    pack = runs.make_pack("positive")
    # On this branch CP-5 has no OWNER_SPECS row; once registered, round 2's rule refuses it
    # through the CP-5 -> CP-MODEL fan-in (DC-5 open on the CP-MODEL row).
    with pytest.raises(WorkflowError) as selected:
        OwnerWorkflow.create(
            tmp_path / "store",
            _selection(pack, ("CP-1", "CP-MODEL", "CP-1A", "CP-2", "CP-5")),
            publication_directory=tmp_path / "model",
        )
    assert selected.value.code == "not_permitted"
    assert list(tmp_path.iterdir()) == []
    cp1a, cp2 = OWNER_SPECS["CP-1A"], OWNER_SPECS["CP-2"]
    overrides = {
        "cp1a rules off": {
            **OWNER_SPECS,
            "CP-1A": replace(cp1a, steps=(replace(cp1a.steps[0], rules="none"),)),
        },
        "cp1a precheck": {
            **OWNER_SPECS,
            "CP-1A": replace(cp1a, steps=(replace(cp1a.steps[0], rules="precheck"),)),
        },
        "cp2 no view": {
            **OWNER_SPECS,
            "CP-2": replace(cp2, steps=(replace(cp2.steps[0], inputs="none"),)),
        },
        "cp2 pack tools": {
            **OWNER_SPECS,
            "CP-2": replace(cp2, steps=(replace(cp2.steps[0], sources=True),)),
        },
    }
    for label, specs in overrides.items():
        with pytest.raises(WorkflowError) as caught:
            OwnerWorkflow.create(
                tmp_path / "store", pack, specs=specs, publication_directory=tmp_path / "model"
            )
        assert caught.value.code == "not_permitted", label
        assert list(tmp_path.iterdir()) == [], label


# --- A1 positive and A2 gap: one closed run per case ------------------------------------------


def test_plan_attempts_heads_and_cp0(closed: Closed) -> None:
    snapshot = closed.store.read()
    assert closed.receipt.plan == tuple(EXPECTED["execution"]["plan_order"])
    assert [(a.module_id, a.number) for a in snapshot.attempts] == [
        (m, 0) for m in EXPECTED["execution"]["plan_order"]
    ]
    assert {h.module_id: h.status for h in snapshot.heads} == {
        m: _status(m) for m in EXPECTED["execution"]["plan_order"]
    }
    cp0 = closed.expected["CP-0"]
    commands = {c.row_id: c.text for c in _head(closed.store, "CP-0").commands}
    assert (
        commands
        == cp0["exact_commands"]
        == {
            "CP-1": "Run CP-1",
            "CP-1A": "Run CP-1A",
            "CP-2": "Run CP-2",
        }
    )
    module = _module(closed.store, "CP-0")
    assert len(module.facts) == len(cp0["facts"]) == 56
    assert [
        {
            "fact_id": f.fact_id,
            "text": f.text,
            "cites": [[c.source_id, c.locator] for c in f.citations],
        }
        for f in module.facts
    ] == cp0["facts"]
    assert list(module.limitations) == cp0["limitations"]


def test_cp1a_tables_match_oracle(closed: Closed) -> None:
    tables = closed.expected["CP-1A"]["tables"]
    assert len(tables) == 23
    _compare_tables(_table_view(_module(closed.store, "CP-1A")), tables)


def test_cp1a_claims_and_limitations(closed: Closed) -> None:
    module, expected = _module(closed.store, "CP-1A"), closed.expected["CP-1A"]
    assert [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "limitation": c.limitation,
            "cites": [[x.source_id, x.locator] for x in c.citations],
        }
        for c in module.claims
    ] == expected["claims"]
    candidate = Module.model_validate_json(
        closed.store.payload(_attempt(closed.store, "CP-1A").payload_sha256 or "")
    )
    assert list(candidate.limitations) == expected["own_limitations"]
    assert list(module.limitations) == expected["settled_limitations"]


def test_cp1a_gap_case_keeps_ownership_and_transaction_unsettled(closed: Closed) -> None:
    if closed.case != "gap":
        pytest.skip("gap case only")
    tables = {t["table_id"]: t for t in _table_view(_module(closed.store, "CP-1A"))}
    for table_id in ("ownership_register", "transaction_summary", "T2D.2"):
        for row in tables[table_id]["rows"]:
            for cell in row["facts"]:
                assert (
                    cell["text"] is not None and cell["text"].strip() not in JUDGED_NOT_ESTABLISHED
                )
    assert "Insufficient Information" in tables["ownership_register"]["rows"][0]["label"]
    assert (
        "Insufficient Information" in tables["transaction_summary"]["rows"][0]["facts"][0]["text"]
    )


def _cp2_expected_tables(closed: Closed) -> list[dict[str, Any]]:
    facts = {f.fact_id: f for f in _module(closed.store, "CP-1").facts}
    expected = _bind_expected(closed.expected["CP-2"]["tables"], closed.bindings, facts)
    figures = SUBMISSIONS["figures"]
    for table in expected:
        if table["table_id"] != "cp1_references":
            continue
        for row in table["rows"]:
            for cell in row["facts"]:
                name = next(n for n, (fid, _) in closed.bindings.items() if fid == cell["fact_id"])
                assert cell.pop("spelled_as") == figures[name]["spelled"]
                assert cell.pop("table_coordinate") == f"cp1_references.{row['row_id']}.value"
                assert cell.pop("note")
                assert cell["cites"] == CITES_PLACEHOLDER
                cell["cites"] = [[c.source_id, c.locator] for c in facts[cell["fact_id"]].citations]
    return cast(list[dict[str, Any]], expected)


def test_cp2_tables_match_oracle(closed: Closed) -> None:
    expected = _cp2_expected_tables(closed)
    assert len(expected) == 10
    module = _module(closed.store, "CP-2")
    _compare_tables(_table_view(module), expected)
    referenced = {f.fact_id: f for f in module.facts if f.table_id == "cp1_references"}
    assert len(referenced) == len(closed.expected["CP-2"]["figures_referenced"])
    for fact in referenced.values():
        assert fact.text is None and fact.amount is not None and fact.field == "value"
    # the copies keep the CP-1 facts' own ids, in first-spelling order
    assert list(referenced) == [
        closed.bindings[f["name"]][0] for f in closed.expected["CP-2"]["figures_referenced"]
    ]


def test_cp2_claims_signals_figures_and_limitations(closed: Closed) -> None:
    module, expected = _module(closed.store, "CP-2"), closed.expected["CP-2"]
    claims = [
        {
            "claim_id": c["claim_id"],
            "text": runs.bind_figures(c["text"], closed.bindings),
            "limitation": c.get("limitation"),  # the oracle omits a null limitation
        }
        for c in expected["claims"]
    ]
    assert [
        {"claim_id": c.claim_id, "text": c.text, "limitation": c.limitation} for c in module.claims
    ] == claims
    assert all(c.citations == () for c in module.claims)
    assert [(s["source"], s["ref"], s["status"]) for s in closed.body["cp1a_signals"]] == [
        (s["source"], s["ref"], s["status"]) for s in expected["signals"]
    ]
    assert len(closed.body["cp1a_signals"]) == (0 if closed.case == "positive" else 3)
    assert {f["name"] for f in expected["figures_referenced"]} == set(closed.bindings)
    for figure in expected["figures_referenced"]:
        fact_id, unit = closed.bindings[figure["name"]]
        shown = next(e for e in closed.body["cp1_facts"] if e["ref"] == fact_id)
        assert (unit, shown["unit"], shown["shown"]) == (
            figure["unit_token"],
            figure["unit_token"],
            figure["spelled"],
        )
    candidate = Module.model_validate_json(
        closed.store.payload(_attempt(closed.store, "CP-2").payload_sha256 or "")
    )
    assert list(candidate.limitations) == expected["own_limitations"]
    assert list(module.limitations) == expected["settled_limitations_own"]


def test_inherited_limitations_follow_the_rule(closed: Closed) -> None:
    rule = EXPECTED[runs.CASES[closed.case][2]]["inherited_limitations"]
    cp1 = _module(closed.store, "CP-1")
    cp1_entries = [*cp1.limitations, *cp1.inherited_limitations]
    cp1a, cp2 = _module(closed.store, "CP-1A"), _module(closed.store, "CP-2")
    for module, tail, own in (
        (cp1a, [], cp1a.limitations),
        (cp2, rule["CP-2"]["literal_tail_after_CP-1"], cp2.limitations),
    ):
        head = rule[module.module_id]["literal_head"]
        expected = [x for x in dict.fromkeys([*head, *cp1_entries, *tail]) if x not in own]
        assert list(module.inherited_limitations) == expected, module.module_id
    # the CP-2 view lists what settlement inherits, before own findings are removed
    view = closed.body["inherited_limitations"]
    assert [x for x in view if x not in cp2.limitations] == list(cp2.inherited_limitations)


def test_downstream_consumption_inputs(closed: Closed) -> None:
    snapshot = closed.store.read()
    heads = {h.module_id: h for h in snapshot.heads}

    def bound(module_id: str, upstream: list[str], submission: str) -> None:
        attempt, module = _attempt(closed.store, module_id), _module(closed.store, module_id)
        assert [i.input_id for i in attempt.inputs] == ["prepared-pack", *upstream]
        for item in attempt.inputs[1:]:
            assert (item.sha256, item.status) == (
                heads[item.input_id].result_sha256,
                heads[item.input_id].status,
            )
        assert attempt.inputs[0].sha256 == snapshot.pack_sha256
        assert module.inputs[:-1] == attempt.inputs
        assert module.inputs[-1].input_id == submission

    bound("CP-1A", ["CP-0", "CP-1"], "business-context-submission")
    bound("CP-2", ["CP-0", "CP-1", "CP-1A"], "credit-synthesis-submission")
    model = _module(closed.store, "CP-MODEL")
    assert {"CP-1A", "CP-2"}.isdisjoint(i.input_id for i in model.inputs)
    assert not any(i.input_id == "CP-2" for h in snapshot.heads for i in h.inputs)


def _quotes(value: Any) -> list[str]:
    if isinstance(value, dict):
        own = [value["quote"]] if isinstance(value.get("quote"), str) else []
        return own + [q for v in value.values() for q in _quotes(v)]
    if isinstance(value, list):
        return [q for v in value for q in _quotes(v)]
    return []


def test_cp2_read_body_is_the_frozen_core_view(closed: Closed) -> None:
    body, frozen = closed.body, TREE[closed.case]
    assert list(body) == frozen["top_level_keys"]
    shape = _shape(body)
    for key, value in frozen["tree"].items():
        if key != "cp1a_rows":  # its cells are register-specific, frozen below
            assert shape[key] == value, key
    assert all(
        list(row) == ["ref", "register", "row", "cells"]
        and all(isinstance(row[k], str) for k in ("ref", "register", "row"))
        and all(isinstance(v, str) for v in row["cells"].values())
        for row in body["cp1a_rows"]
    )
    assert _keys(body).isdisjoint(FORBIDDEN_KEYS)
    quotes = _quotes(SUBMISSIONS[runs.CASES[closed.case][1]])
    assert len(quotes) >= 30
    assert not [q for s in _strings(body) for q in quotes if q in s]
    groups = [
        (register, list(rows))
        for register, rows in itertools.groupby(body["cp1a_rows"], key=lambda r: r["register"])
    ]
    registers = frozen["cp1a_registers"]
    assert [g[0] for g in groups] == [r["register"] for r in registers]
    for (_, rows), want in zip(groups, registers, strict=True):
        assert len(rows) == want["rows"]
        assert all(list(r["cells"]) == want["cells"] for r in rows)
        assert all(r["ref"].startswith(want["ref_prefix"] + ".") for r in rows)
    assert (
        len(body["cp1a_rows"]) == closed.expected["CP-2"]["catalogue_size"] == frozen["cp1a_rows"]
    )
    assert body["upstream"] == [
        {"module_id": m, "status": _status(m)} for m in ("CP-0", "CP-1", "CP-1A")
    ]
    read = next(r for r in closed.receipt.input_reads if r.binding.module_id == "CP-2")
    assert read.inputs_sha256 == hashlib.sha256(read.body.encode()).hexdigest()


def test_tool_use_per_oracle(closed: Closed) -> None:
    receipt = closed.receipt
    steps = (
        ("CP-0", "source_readiness", "readiness_review"),
        ("CP-1", "source_context", "cp1_source_context"),
        ("CP-1A", "business_context", "business_context"),
    )
    for module_id, step_id, name in steps:
        submission = next(
            s
            for s in receipt.submissions
            if (s.binding.binding.module_id, s.binding.binding.step_id) == (module_id, step_id)
            and s.disposition == "valid"
        )
        pages = {
            (source, locator)
            for source, locator in cited_locators(runs.literal(closed.case, name, closed.pack))
            if re.fullmatch(r"page:\d+", locator)
        }
        assert pages <= _ok_reads(receipt, submission.binding.binding), module_id
        if module_id == "CP-1A":
            assert _searches(receipt, submission.binding.binding)  # `available: No` rows
        if module_id == "CP-1" and closed.case == "positive":
            assert "business" in _searches(receipt, submission.binding.binding)
    financials = next(
        s.binding.binding
        for s in receipt.submissions
        if s.binding.binding.step_id == "financials" and s.disposition == "valid"
    )
    assert any(
        c.tool == "extract_statements" and c.status == "ok"
        for c in receipt.calls
        if c.binding == financials
    )
    cp2_calls = [c for c in receipt.calls if c.binding.module_id == "CP-2"]
    assert not [c for c in cp2_calls if c.status == "ok"]
    reads = [r for r in receipt.input_reads if r.binding.module_id == "CP-2"]
    cp2_submit = [s for s in receipt.submissions if s.binding.binding.module_id == "CP-2"]
    assert len(reads) == len(cp2_submit) == 1
    assert reads[0].binding == cp2_submit[0].binding.binding and reads[0].sequence == 1


def test_model_publication_and_receipt_verify_read_only(closed: Closed) -> None:
    store, model = closed.store, closed.root / "model"
    assert verify_cp_model_publication(store, model) == ()
    assert closed.receipt.model is not None
    assert closed.receipt.model.cp1_result_sha256 == _head(store, "CP-1").result_sha256
    before = _tree(closed.root / "store", model)
    _verify(closed.root, closed.receipt)
    assert _tree(closed.root / "store", model) == before


def test_cp2_confidence_is_never_high(closed: Closed) -> None:
    table = next(t for t in _table_view(_module(closed.store, "CP-2")) if t["table_id"] == "T2.1")
    confidence = next(c for c in table["rows"][0]["facts"] if c["column"] == "Confidence")
    assert confidence["text"] != "High"


# --- A3 tool-use refusals (forks of the positive run) -----------------------------------------


def _fork(promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path) -> OwnerWorkflow:
    workflow: OwnerWorkflow = runs.clone_workflow(promoted[0], tmp_path)
    return workflow


def _finish_and_verify(workflow: OwnerWorkflow, pack: PreparedPack, root: Path) -> OwnerRunReceipt:
    runs.close(workflow, pack, "positive", root / "owner-receipt.json")
    receipt = OwnerRunReceipt.model_validate_json((root / "owner-receipt.json").read_bytes())
    _verify(root, receipt)
    return receipt


def _cp1a_attempts(root: Path) -> list[Attempt]:
    return [a for a in Execution(root / "store").read().attempts if a.module_id == "CP-1A"]


def test_cp1a_without_business_page3_read_is_invalid_and_repairs(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    pack = positive_promoted[1]
    workflow = _fork(positive_promoted, tmp_path)
    outcome = runs.drive_cp1a(workflow, pack, "positive", skip_reads=[("business", "page:3")])
    assert outcome["status"] == "invalid"
    assert any("business page:3" in issue for issue in outcome["issues"])
    first, second = _cp1a_attempts(tmp_path)
    assert (first.number, second.number) == (0, 1)
    assert second.repair_of == first.ticket_id and second.status == "pending"
    receipt = _finish_and_verify(workflow, pack, tmp_path)
    assert [
        s.disposition for s in receipt.submissions if s.binding.binding.module_id == "CP-1A"
    ] == [
        "invalid",
        "valid",
    ]


def test_cp1a_without_search_is_invalid_on_the_absence_rule(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    pack = positive_promoted[1]
    workflow = _fork(positive_promoted, tmp_path)
    outcome = runs.drive_cp1a(workflow, pack, "positive", searched=False)
    assert outcome["status"] == "invalid"
    assert outcome["issues"] and all(i.startswith(UNBACKED_ABSENCE) for i in outcome["issues"])
    assert _cp1a_attempts(tmp_path)[1].repair_of is not None
    _finish_and_verify(workflow, pack, tmp_path)


def _shape_broken(payload: str, count: int = 24) -> str:
    """The literal business_context with `count` citation quotes turned into integers: the
    model's schema then fails `count` times, whatever the rules read (they read the locators)."""
    document = json.loads(payload)
    left = [count]

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "quote" and isinstance(value, str) and left[0] > 0:
                    node[key] = 0
                    left[0] -= 1
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(document)
    assert left[0] == 0
    return json.dumps(document, ensure_ascii=False)


def test_cp1a_truncated_issue_list_still_verifies(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    """R3-2: a step with 20+ validator issues keeps no room for its rule issue (the core bounds
    the list), and the genuine run must still verify: the verifier recomputes exactly."""
    pack = positive_promoted[1]
    workflow = _fork(positive_promoted, tmp_path)
    broken = _shape_broken(runs.literal("positive", "business_context", pack))
    outcome = runs.drive_cp1a(workflow, pack, "positive", searched=False, text=broken)
    assert outcome["status"] == "invalid"
    step = _cp1a_attempts(tmp_path)[0].steps[0]
    assert step.status == "invalid" and len(step.issues) == 21
    assert re.fullmatch(r"\d+ further issues not listed", step.issues[-1])
    # the premise: the absence issue was cut off by the bound, so it is not in the step
    assert not any(i.startswith(UNBACKED_ABSENCE) for i in step.issues)
    _finish_and_verify(workflow, pack, tmp_path)


def test_cp1a_invented_validator_issue_refuses(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R3-2: a run made with a validator that invents an issue (a valid CP-1A turned invalid)
    refuses at the exact replay; the journaled rule issue alone cannot explain the step."""
    pack = positive_promoted[1]
    workflow = _fork(positive_promoted, tmp_path)
    real = submission_module.RULED_ENTRIES["CP-1A"]

    def forged(store: Execution, prepared: PreparedPack, attempt: Attempt) -> StepValidation:
        outcome: StepValidation = real(store, prepared, attempt)
        return StepValidation(
            output=outcome.output, issues=(*outcome.issues, "Invented validator issue")
        )

    with monkeypatch.context() as patch:
        patch.setitem(submission_module.RULED_ENTRIES, "CP-1A", forged)
        outcome = runs.drive_cp1a(workflow, pack, "positive", searched=False)
    assert outcome["status"] == "invalid"
    assert "Invented validator issue" in _cp1a_attempts(tmp_path)[0].steps[0].issues
    with pytest.raises(WorkflowError) as caught:
        runs.close(workflow, pack, "positive", tmp_path / "owner-receipt.json")
    assert caught.value.code == "identity_mismatch"


def test_cp1a_offers_no_extraction_and_no_inputs(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    workflow = _fork(positive_promoted, tmp_path)
    call = workflow.invoke("extract_statements", {"source_id": "financial", "locators": ["page:2"]})
    assert (call["status"], call["body"]) == ("refused", None)
    with pytest.raises(WorkflowError) as caught:
        workflow.read_inputs()
    assert caught.value.code == "not_permitted"


def test_cp2_pack_tools_refused_and_submit_before_read_not_permitted(
    cp2_ready: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    workflow = _fork(cp2_ready, tmp_path)
    call = workflow.invoke("read_pages", {"source_id": "business", "first_page": 1, "last_page": 1})
    assert (call["status"], call["error_code"], call["body"]) == ("refused", "not_permitted", None)
    with pytest.raises(WorkflowError) as unread:
        workflow.submit_review(runs.literal("positive", "credit_synthesis"))
    assert unread.value.code == "not_permitted"
    assert [c.status for c in workflow._calls if c.binding.module_id == "CP-2"] == ["refused"]
    assert not [s for s in workflow._submissions if s.binding.binding.module_id == "CP-2"]


def test_cp2_unreplaced_figure_is_invalid_then_repaired(
    cp2_ready: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    workflow = _fork(cp2_ready, tmp_path)
    runs.read_cp2(workflow)
    outcome = workflow.submit_review(runs.literal("positive", "credit_synthesis"))
    assert outcome["status"] == "invalid"
    # "Malformed run text" is the core's product wording for an unresolved run-text figure; the
    # oracle only says the submission fails closed.
    assert any("Malformed run text" in issue for issue in outcome["issues"])
    attempts = [a for a in Execution(tmp_path / "store").read().attempts if a.module_id == "CP-2"]
    assert [a.number for a in attempts] == [0, 1] and attempts[1].repair_of == attempts[0].ticket_id
    outcome = runs.drive_cp2(workflow, "positive", runs.read_cp2(workflow))
    assert outcome["status"] == "valid"
    runs.finish(workflow, tmp_path / "owner-receipt.json")
    receipt = OwnerRunReceipt.model_validate_json((tmp_path / "owner-receipt.json").read_bytes())
    _verify(tmp_path, receipt)
    assert len([r for r in receipt.input_reads if r.binding.module_id == "CP-2"]) == 2


def test_cp2_snapshot_change_between_read_and_submit_is_stale(
    cp2_ready: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    workflow = _fork(cp2_ready, tmp_path)
    body = runs.read_cp2(workflow)
    Execution(tmp_path / "store").interrupt(
        workflow._binding.ticket_id, "external change between read and submit"
    )
    with pytest.raises(WorkflowError) as caught:
        runs.drive_cp2(workflow, "positive", body)
    assert caught.value.code == "stale_binding"


# --- A3b blocked CP-1A ------------------------------------------------------------------------


def test_blocked_cp1a_still_begins_cp2_and_publishes(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    pack = positive_promoted[1]
    fixture = runs.BLOCKED_CP2
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == BLOCKED_CP2_SHA256
    blocked_text = runs.blocked_cp2_text()
    workflow = _fork(positive_promoted, tmp_path)
    skip = [("business", "page:3")]
    for _ in range(2):
        outcome = runs.drive_cp1a(workflow, pack, "positive", skip_reads=skip)
        assert outcome["status"] == "invalid"
    store = Execution(tmp_path / "store")
    snapshot = store.read()
    assert _head(store, "CP-1A").status == "blocked"
    assert [(a.module_id, a.number) for a in snapshot.attempts if a.module_id == "CP-1A"] == [
        ("CP-1A", 0),
        ("CP-1A", 1),
    ]
    cp2 = next(a for a in snapshot.attempts if a.module_id == "CP-2")
    assert next(i for i in cp2.inputs if i.input_id == "CP-1A").status == "blocked"
    body = runs.read_cp2(workflow)
    assert body["cp1a_rows"] == [] and body["cp1a_signals"] == []
    assert body["upstream"][-1] == {"module_id": "CP-1A", "status": "blocked"}
    outcome = runs.drive_cp2(
        workflow,
        "positive",
        body,
        text=blocked_text,
    )
    assert outcome["status"] == "valid", outcome["issues"]
    runs.finish(workflow, tmp_path / "owner-receipt.json")
    receipt = OwnerRunReceipt.model_validate_json((tmp_path / "owner-receipt.json").read_bytes())
    _verify(tmp_path, receipt)
    cp1a, cp2_module = _module(store, "CP-1A"), _module(store, "CP-2")
    assert (cp1a.status, cp2_module.status) == ("blocked", _status("CP-2"))
    prefixed = [
        x for x in cp2_module.inherited_limitations if x.startswith("Upstream CP-1A blocked:")
    ]
    assert prefixed == [f"Upstream CP-1A blocked: {x}" for x in cp1a.limitations]
    assert "business page:3" in prefixed[0]
    assert (
        receipt.model is not None and verify_cp_model_publication(store, tmp_path / "model") == ()
    )


# --- A3c unauthorized CP-1A (R3-1) -------------------------------------------------------------


@pytest.fixture(scope="module")
def conditional_promoted(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[OwnerWorkflow, PreparedPack, Path]:
    """CP-0 judges CP-1A CONDITIONAL (T8 `DO NOT RUN`); CP-1 promoted for real (slow: one more
    CP-1 promotion). The walk ends at the CP-1A begin, refused."""
    root = tmp_path_factory.mktemp("s1a-promoted-conditional")
    text = runs.cp0_cp1a_conditional("positive", runs.make_pack("positive"))
    workflow, pack = runs.promoted("positive", root, cp0_text=text)
    return workflow, pack, root


def test_unauthorized_cp1a_is_refused_and_cp_model_publishes(
    conditional_promoted: tuple[OwnerWorkflow, PreparedPack, Path],
) -> None:
    workflow, _, root = conditional_promoted
    store = Execution(root / "store")
    before = store.read()
    assert {h.module_id for h in before.heads} == {"CP-0", "CP-1"}
    assert not [a for a in before.attempts if a.module_id in ("CP-1A", "CP-2")]
    runs.finish(workflow, root / "owner-receipt.json")
    receipt = OwnerRunReceipt.model_validate_json((root / "owner-receipt.json").read_bytes())
    _verify(root, receipt)  # the seal itself verified it; this is the read-only audit
    assert [r.module_id for r in receipt.refusals] == ["CP-1A"]
    assert receipt.model is not None and receipt.publications
    assert verify_cp_model_publication(store, root / "model") == ()
    assert {h.module_id for h in store.read().heads} == {"CP-0", "CP-1", "CP-MODEL"}
    # the refusal was taken before CP-MODEL published, so it binds the snapshot before it
    assert (
        receipt.refusals[0].snapshot_sha256
        == receipt.publications[0].snapshot_before_sha256
        != receipt.snapshot_sha256
    )


# --- A4 tamper --------------------------------------------------------------------------------


def test_tampering_refuses_with_identity_mismatch(closed: Closed, tmp_path: Path) -> None:
    root = tmp_path / "audit"
    root.mkdir()
    for name in ("store", "model"):
        shutil.copytree(closed.root / name, root / name)
    _verify(root, closed.receipt)

    def refuses(receipt: Any = closed.receipt) -> None:
        with pytest.raises(WorkflowError) as caught:
            _verify(root, receipt)
        assert caught.value.code == "identity_mismatch"

    # a consistent forged CP-2 read body (R3-5): receipt copy, audit file under its new hash and
    # receipt.sha256 all agree, so only the view replay can refuse it
    reads = root / "store/owner-run-audit/input-reads"
    old = next(r for r in closed.receipt.input_reads if r.binding.module_id == "CP-2")
    assert "cp1a_rows_note" in old.body
    body = old.body.replace("cp1a_rows_note", "cp1a_rows_notX", 1)
    edited = old.model_copy(
        update={"body": body, "inputs_sha256": hashlib.sha256(body.encode()).hexdigest()}
    )
    forged = closed.receipt.model_copy(
        update={"input_reads": tuple(edited if r == old else r for r in closed.receipt.input_reads)}
    )
    (reads / old.content_hash()).unlink()
    (reads / edited.content_hash()).write_bytes(edited.model_dump_json().encode())
    sealed = root / "store/owner-run-audit/receipt.sha256"
    sealed.write_text(forged.content_hash())
    store = Execution(root / "store")
    _verify_audit(store, forged)  # the audit and the seal agree with the forged copy ...
    with pytest.raises(WorkflowError) as replay:  # ... so the view replay is what refuses
        _verify_calls_reads(store, forged, OWNER_SPECS)
    assert replay.value.code == "identity_mismatch"
    refuses(forged)
    (reads / edited.content_hash()).unlink()
    (reads / old.content_hash()).write_bytes(old.model_dump_json().encode())
    sealed.write_text(closed.receipt.content_hash())
    _verify(root, closed.receipt)

    # an edited CP-1A step output: caught by the store's own blob hash check, not by the
    # probe's output comparison (recorded limitation, R3-5)
    output = _attempt(Execution(root / "store"), "CP-1A").steps[0].output_sha256 or ""
    blob = root / "store/blobs" / output
    original = blob.read_bytes()
    blob.write_bytes(original + b" ")
    refuses()
    blob.write_bytes(original)
    _verify(root, closed.receipt)

    # an edited CP-2 SettledHead
    heads = tuple(
        h.model_copy(update={"status": "accepted"}) if h.module_id == "CP-2" else h
        for h in closed.receipt.heads
    )
    refuses(closed.receipt.model_copy(update={"heads": heads}))
    wrong = tuple(
        h.model_copy(update={"result_sha256": "0" * 64}) if h.module_id == "CP-2" else h
        for h in closed.receipt.heads
    )
    refuses(closed.receipt.model_copy(update={"heads": wrong}))


# --- fix round 2 (R4-1..R4-3): blocked heads, invalid-step settlements, the read rule -----------

FORGED_LIMITATION = "Ownership: the sponsor has pledged 100% of the shares to an undisclosed lender"
ow: Any = importlib.import_module("deploy_workflow.owner_workflow")


def _verdict(store: Execution, receipt: OwnerRunReceipt) -> str:
    try:
        ow.verify_owner_run_receipt(store, receipt)
    except WorkflowError as error:
        return error.code
    return "accepted"


def _reseal(store: Execution, receipt: OwnerRunReceipt) -> None:
    seal = store.directory / ow.AUDIT / "receipt.sha256"
    seal.unlink()
    ow._put(seal, receipt.content_hash().encode())


def _swap(store: Execution, kind: str, old: Any, new: Any) -> None:
    (store.directory / ow.AUDIT / kind / old.content_hash()).unlink()
    if new is not None:
        ow._retain(store, kind, new)


def _cp1a_only_pack() -> PreparedPack:
    """The positive case's pack with CP-1A the only requested module (plan CP-0, CP-1A)."""
    pack = runs.make_pack("positive")
    document = json.loads(pack.run.model_dump_json())
    document["requested_modules"] = ["CP-1A"]
    return PreparedPack(run=Run.model_validate_json(json.dumps(document)), sources=pack.sources)


def _cp0_review(pack: PreparedPack, *, conditional: bool = False) -> str:
    """The CP-1A-only CP-0 review: the oracle literal (READY, `Run CP-1A`) or its CONDITIONAL
    variant (`DO NOT RUN`), the pack hash and consumers bound to this plan."""
    text = (
        runs.cp0_cp1a_conditional("positive", pack)
        if conditional
        else runs.literal("positive", "readiness_review", pack)
    )
    review = json.loads(text)
    review["pack_sha256"] = pack.content_hash()
    review["consumers"] = [c for c in review["consumers"] if c["module_id"] == "CP-1A"]
    return json.dumps(review)


def _cp1a_only_run(root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """A CP-0 + CP-1A run (plan requested for CP-1A only; no CP-1 promotion) with its CP-0 review
    valid and CP-1A begun (about 0.2 s)."""
    pack = _cp1a_only_pack()
    workflow = OwnerWorkflow.create(root / "store", pack)
    review = _cp0_review(pack)
    runs.read_cited(workflow, review)
    assert workflow.submit_review(review)["status"] == "valid"
    return workflow, pack


@pytest.fixture(scope="module")
def blocked_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, OwnerRunReceipt]:
    """A genuine CP-0 + CP-1A run (plan requested for CP-1A only) whose CP-1A is invalid twice on
    the read rule alone (a cited page unread; the validator passes and its output is retained) and
    so blocks (no CP-1 promotion; about 1 s). Forks are made with `shutil.copytree`."""
    root = tmp_path_factory.mktemp("s1a-blocked-cp1a")
    workflow, pack = _cp1a_only_run(root)
    context = json.loads(runs.literal("positive", "business_context", pack))
    context["consumers"] = [c for c in context["consumers"] if c["module_id"] == "CP-MODEL"]
    for _ in range(2):
        outcome = runs.drive_cp1a(
            workflow,
            pack,
            "positive",
            skip_reads=[("business", "page:3")],
            text=json.dumps(context),
        )
        assert outcome["status"] == "invalid"
        assert outcome["issues"] == ["Cited page not read through read_pages: business page:3"]
    receipt = workflow.write_receipt(root / "receipt.json")
    return root, receipt


def _fork_blocked(
    blocked_run: tuple[Path, OwnerRunReceipt], tmp_path: Path
) -> tuple[Execution, OwnerRunReceipt]:
    shutil.copytree(blocked_run[0], tmp_path / "run")
    return Execution(tmp_path / "run" / "store"), blocked_run[1]


def test_genuine_blocked_cp1a_run_verifies(
    blocked_run: tuple[Path, OwnerRunReceipt], tmp_path: Path
) -> None:
    store, receipt = _fork_blocked(blocked_run, tmp_path)
    assert [(h.module_id, h.status) for h in store.read().heads] == [
        ("CP-0", "restricted"),
        ("CP-1A", "blocked"),
    ]
    assert _verdict(store, receipt) == "accepted"


def test_forgery_a_blocked_cp1a_limitations_rewritten_refuses(
    blocked_run: tuple[Path, OwnerRunReceipt], tmp_path: Path
) -> None:
    """R4-1: the blocked head's text is rewritten consistently (new blob, snapshot, submission
    record, resealed receipt); only the rebuilt settlement of the invalid step refuses it."""
    store, receipt = _fork_blocked(blocked_run, tmp_path)
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == "CP-1A")
    blocked = store.result(head.result_sha256)
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    module = blocked.model_copy(update={"limitations": (FORGED_LIMITATION,)})
    store._store(module.model_dump_json())
    forged_attempt = attempt.model_copy(update={"result_sha256": module.content_hash()})
    forged = snapshot.model_copy(
        update={
            "attempts": tuple(
                forged_attempt if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts
            ),
            "heads": tuple(
                head_of(module) if h.module_id == "CP-1A" else h for h in snapshot.heads
            ),
        }
    )
    store._write(forged)
    last = receipt.submissions[-1]
    assert last.snapshot_after_sha256 == snapshot.content_hash()
    moved = last.model_copy(update={"snapshot_after_sha256": forged.content_hash()})
    _swap(store, "submissions", last, moved)
    resealed = receipt.model_copy(
        update={
            "snapshot_sha256": forged.content_hash(),
            "heads": tuple(ow._settled(store, h.module_id) for h in forged.heads),
            "submissions": (*receipt.submissions[:-1], moved),
        }
    )
    _reseal(store, resealed)
    assert store.head_module(
        next(h for h in store.read().heads if h.module_id == "CP-1A")
    ).limitations == (FORGED_LIMITATION,)
    assert _verdict(store, resealed) == "identity_mismatch"


def test_forgery_b_blocked_at_attempt_zero_refuses(
    blocked_run: tuple[Path, OwnerRunReceipt], tmp_path: Path
) -> None:
    """R4-1: CP-1A is blocked at attempt 0 and the repair attempt (its begin, calls, submission)
    is removed; the repair chain check refuses a blocked head that is not attempt 1."""
    store, receipt = _fork_blocked(blocked_run, tmp_path)
    first, second = [s for s in receipt.submissions if s.binding.binding.module_id == "CP-1A"]
    after_first = _snapshot(store, first.snapshot_after_sha256)
    zero = next(a for a in after_first.attempts if a.ticket_id == first.binding.binding.ticket_id)
    module = Module(
        run_id=after_first.run.run_id,
        issuer_id=after_first.run.issuer_id,
        as_of=after_first.run.as_of,
        module_id="CP-1A",
        inputs=zero.inputs,
        attempt=0,
        status="blocked",
        limitations=zero.issues,
    )
    store._store(module.model_dump_json())
    forged_zero = zero.model_copy(update={"result_sha256": module.content_hash()})
    forged = after_first.model_copy(
        update={
            "attempts": tuple(
                forged_zero if a.ticket_id == zero.ticket_id else a for a in after_first.attempts
            ),
            "heads": (*after_first.heads, head_of(module)),
        }
    )
    store._write(forged)
    repair = second.binding.binding.ticket_id
    for call in receipt.calls:
        if call.binding.ticket_id == repair:
            _swap(store, "calls", call, None)
    for begin in receipt.begins:
        if begin.ticket_id == repair:
            _swap(store, "begins", begin, None)
    _swap(store, "bindings", second.binding, None)
    _swap(store, "submissions", second, None)
    moved = first.model_copy(update={"snapshot_after_sha256": forged.content_hash()})
    _swap(store, "submissions", first, moved)
    resealed = receipt.model_copy(
        update={
            "snapshot_sha256": forged.content_hash(),
            "heads": tuple(ow._settled(store, h.module_id) for h in forged.heads),
            "calls": tuple(c for c in receipt.calls if c.binding.ticket_id != repair),
            "begins": tuple(b for b in receipt.begins if b.ticket_id != repair),
            "submissions": tuple(
                moved if s is first else s for s in receipt.submissions if s is not second
            ),
        }
    )
    _reseal(store, resealed)
    assert [(a.module_id, a.number) for a in store.read().attempts] == [("CP-0", 0), ("CP-1A", 0)]
    assert _verdict(store, resealed) == "identity_mismatch"


# CP-2 invalid-step cases (R4-2, R4-3). They need a store with CP-2 begun over a settled CP-1A:
# the `cp2_ready` fixture (a real CP-1 promotion, heavy) or any equivalent store.


def _bound_cp2(store: Execution) -> tuple[Any, Attempt]:
    """The snapshot CP-2 was begun at (its attempt pending, no step) and that attempt."""
    cursor = store.read()
    ticket = next(a for a in cursor.attempts if a.module_id == "CP-2").ticket_id
    while True:
        attempt = next((a for a in cursor.attempts if a.ticket_id == ticket), None)
        if attempt is not None and attempt.status == "pending" and not attempt.steps:
            return cursor, attempt
        cursor = _snapshot(store, cursor.parent)


def forge_invalid_cp2(
    store: Execution, payload: str, invented: tuple[str, ...]
) -> tuple[Any, Any, Attempt]:
    """Journal `payload` as an invalid CP-2 step carrying `invented` issues, with a consistent
    rejected settlement, submission record and read. Returns (receipt stand-in, forged
    submission, bound attempt)."""
    bound, pending = _bound_cp2(store)
    binding = ow._owner_binding(bound, pending, "credit_synthesis")
    spec = ow.OWNER_SPECS["CP-2"].steps[0]
    digest, body = ow._inputs(store, binding, spec)
    read = ow.OwnerInputRead(binding=binding, sequence=1, inputs_sha256=digest, body=body)
    payload_sha = hashlib.sha256(payload.encode()).hexdigest()
    step = StepSubmission(
        step_id="credit_synthesis",
        inputs=pending.inputs,
        payload_sha256=store._store(payload),
        status="invalid",
        issues=invented,
    )
    empty = Module(
        run_id=bound.run.run_id,
        issuer_id=bound.run.issuer_id,
        as_of=bound.run.as_of,
        module_id="CP-2",
        inputs=pending.inputs,
        attempt=0,
    )
    rejected = empty.model_copy(
        update={"status": "rejected", "limitations": bounded_issues(invented)}
    )
    store._store(rejected.model_dump_json())
    finished = pending.model_copy(
        update={
            "steps": (step,),
            "status": "finished",
            "issues": bounded_issues(invented),
            "payload_sha256": store._store(empty.model_dump_json()),
            "result_sha256": rejected.content_hash(),
        }
    )
    after = bound.model_copy(
        update={
            "parent": bound.content_hash(),
            "attempts": tuple(
                finished if a.ticket_id == pending.ticket_id else a for a in bound.attempts
            ),
        }
    )
    store._write(after)
    sub_binding = ow.OwnerSubmissionBinding(
        binding=binding,
        payload_sha256=payload_sha,
        successful_call_ids=(),
        call_ids=(),
        source_evidence=SourceEvidence(),
    )
    ow._put(ow._audit(store, "payloads", payload_sha), payload.encode())
    submission = ow.OwnerSubmission(
        sequence=1,
        binding=sub_binding,
        stored_payload_sha256=payload_sha,
        canonical_review_sha256=spec.schema.model_validate_json(payload).content_hash(),
        disposition="invalid",
        issues=step.issues,
        snapshot_after_sha256=after.content_hash(),
        step_sha256=step.content_hash(),
        step_output_sha256=None,
    )
    receipt = SimpleNamespace(
        submissions=(submission,),
        calls=(),
        input_reads=(read,),
        run=bound.run,
        pack_sha256=bound.pack_sha256,
    )
    return receipt, read, pending


def _cp2_payload(workflow: OwnerWorkflow) -> str:
    """The literal credit_synthesis with its figures bound against the read view."""
    body = runs.read_cp2(workflow)
    text = runs.literal("positive", "credit_synthesis")
    figures = SUBMISSIONS["figures"]
    names = {n: figures[n] for n in runs.figure_names(text)}
    return str(runs.bind_figures(text, runs.fig_bindings(workflow._store, body, names)))


def test_cp2_invented_invalid_step_issues_refuse(
    cp2_ready: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    """R4-2 (heavy: real CP-1 promotion): a payload the CP-2 validator accepts is journaled
    invalid with invented issues and a consistent rejected settlement; the entry validator's
    replay at the historical snapshot refuses it."""
    workflow = _fork(cp2_ready, tmp_path)
    payload = _cp2_payload(workflow)
    store = workflow._store
    bound, pending = _bound_cp2(store)
    hist = _FrozenExecution(store, bound)
    probe = pending.model_copy(
        update={
            "steps": (
                StepSubmission(
                    step_id="credit_synthesis",
                    inputs=pending.inputs,
                    payload_sha256=store._store(payload),
                ),
            )
        }
    )
    assert cp2_validate_step(hist, hist.pack(), probe).issues == ()  # the premise
    invented = (
        "thesis: contradicts the CP-1 leverage figure",
        "assessment.confidence: capped below High because CP-1A is blocked",
    )
    receipt, _, _ = forge_invalid_cp2(store, payload, invented)
    with pytest.raises(WorkflowError) as caught:
        _verify_submissions(store, receipt, OWNER_SPECS)
    assert caught.value.code == "identity_mismatch"


def test_cp2_invalid_submission_without_a_read_refuses(
    cp2_ready: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    """R4-3 (heavy): a genuinely invalid CP-2 submission (an unreplaced figure) whose recorded
    read is missing from the receipt is refused, as the runtime refuses a submit before a read;
    with the read present the same history verifies."""
    workflow = _fork(cp2_ready, tmp_path)
    runs.read_cp2(workflow)
    text = runs.literal("positive", "credit_synthesis")
    assert runs.figure_names(text)
    outcome = workflow.submit_review(text)
    assert outcome["status"] == "invalid"
    store = workflow._store
    with_read = SimpleNamespace(
        submissions=tuple(workflow._submissions),
        calls=tuple(workflow._calls),
        input_reads=tuple(workflow._reads),
        run=store.read().run,
        pack_sha256=store.read().pack_sha256,
    )
    assert len(_verify_submissions(store, with_read, OWNER_SPECS)[0]) == 0
    without_read = SimpleNamespace(**{**vars(with_read), "input_reads": ()})
    with pytest.raises(WorkflowError) as caught:
        _verify_submissions(store, without_read, OWNER_SPECS)
    assert caught.value.code == "identity_mismatch"


def test_blocked_cp1a_forgery_a_refuses_on_the_a3b_store(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    """R4-1 (heavy: real CP-1 promotion): the A3b sequence (CP-1A invalid twice, so blocked),
    then the blocked module's limitations rewritten with a consistent snapshot and submission
    record. The rebuilt settlement of the invalid step refuses it."""
    pack = positive_promoted[1]
    workflow = _fork(positive_promoted, tmp_path)
    for _ in range(2):
        outcome = runs.drive_cp1a(workflow, pack, "positive", skip_reads=[("business", "page:3")])
        assert outcome["status"] == "invalid"
    store = workflow._store
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == "CP-1A")
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    run = snapshot.run
    receipt = SimpleNamespace(
        submissions=tuple(
            s for s in workflow._submissions if s.binding.binding.module_id == "CP-1A"
        ),
        calls=tuple(workflow._calls),
        input_reads=tuple(workflow._reads),
        run=run,
        pack_sha256=snapshot.pack_sha256,
    )
    receipt.submissions = tuple(
        s.model_copy(update={"sequence": i}) for i, s in enumerate(receipt.submissions, 1)
    )
    # control: the genuine blocked history passes the submission replay
    assert _verify_submissions(store, receipt, OWNER_SPECS)[0] == []
    module = store.result(head.result_sha256).model_copy(
        update={"limitations": (FORGED_LIMITATION,)}
    )
    store._store(module.model_dump_json())
    forged_attempt = attempt.model_copy(update={"result_sha256": module.content_hash()})
    forged = snapshot.model_copy(
        update={
            "attempts": tuple(
                forged_attempt if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts
            ),
            "heads": tuple(
                head_of(module) if h.module_id == "CP-1A" else h for h in snapshot.heads
            ),
        }
    )
    store._write(forged)
    last = receipt.submissions[-1]
    receipt.submissions = (
        *receipt.submissions[:-1],
        last.model_copy(update={"snapshot_after_sha256": forged.content_hash()}),
    )
    with pytest.raises(WorkflowError) as caught:
        _verify_submissions(store, receipt, OWNER_SPECS)
    assert caught.value.code == "identity_mismatch"


# --- fix round 3 (R5-1, R5-3): settlements bound to the final snapshot; invalid-step bytes --------
# Every forgery below keeps the genuine submission records and their settlement snapshots (or
# moves one record consistently) and changes only what the final snapshot says an attempt or head
# is. Only a verifier that binds the final snapshot to the submission that settled each attempt
# (and rebuilds blocked heads) refuses them.

financial: Any = importlib.import_module("test_financial_workflow")


@pytest.fixture(scope="module")
def valid_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, OwnerRunReceipt]:
    """A genuine CP-0 + CP-1A run (plan requested for CP-1A only) whose CP-1A is valid at attempt
    0 (restricted) with no invalid step (about 1 s). Forks are made with `shutil.copytree`."""
    root = tmp_path_factory.mktemp("s1a-valid-cp1a")
    workflow, pack = _cp1a_only_run(root)
    context = json.loads(runs.literal("positive", "business_context", pack))
    context["consumers"] = [c for c in context["consumers"] if c["module_id"] == "CP-MODEL"]
    outcome = runs.drive_cp1a(workflow, pack, "positive", text=json.dumps(context))
    assert outcome["status"] == "valid", outcome["issues"]
    receipt = workflow.write_receipt(root / "receipt.json")
    return root, receipt


@pytest.fixture(scope="module")
def blocked_cp1_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, OwnerRunReceipt]:
    """A genuine run on the financial case whose CP-1 blocks: an empty `source_context` is
    rejected within attempt 0, settles attempt 0, is rejected within attempt 1 and blocks it;
    CP-MODEL refuses (about 0.5 s; no promotion)."""
    root = tmp_path_factory.mktemp("s1a-blocked-cp1")
    pack = financial.make_pack()
    workflow = OwnerWorkflow.create(root / "store", pack, publication_directory=root / "model")
    financial.read_sources(workflow)
    assert workflow.submit_review(financial.readiness(pack))["status"] == "valid"
    for _ in range(4):
        for source in ("identity", "financial"):
            call = workflow.invoke(
                "read_pages", {"source_id": source, "first_page": 1, "last_page": 1}
            )
            assert call["status"] == "ok"
        assert (
            workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})[
                "status"
            ]
            == "ok"
        )
        assert workflow.submit_review("{}")["status"] == "invalid"
    assert workflow.publish()["status"] == "refused"
    receipt = workflow.write_receipt(root / "receipt.json")
    return root, receipt


def _head_attempt(store: Execution, module_id: str) -> tuple[Any, Any, Attempt]:
    """The final snapshot, the module's head and the finished attempt that produced it."""
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == module_id)
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    return snapshot, head, attempt


def _blocked_module(snapshot: Any, attempt: Attempt, limitations: tuple[str, ...]) -> Module:
    """The blocked result the core would store for `attempt` with `limitations` as its issues."""
    run = snapshot.run
    return Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=attempt.module_id,
        inputs=attempt.inputs,
        attempt=attempt.number,
        status="blocked",
        limitations=limitations,
    )


def _with_result(
    snapshot: Any, attempt: Attempt, module: Module, *, appended: bool, **changes: Any
) -> Any:
    """`snapshot` with `attempt` settled to `module` (its result hash, `changes` applied) and the
    module's head replaced by `module`'s; `appended` makes it a child of `snapshot`."""
    forged_attempt = attempt.model_copy(update={"result_sha256": module.content_hash(), **changes})
    update: dict[str, Any] = {
        "attempts": tuple(
            forged_attempt if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts
        ),
        "heads": tuple(
            head_of(module) if h.module_id == attempt.module_id else h for h in snapshot.heads
        ),
    }
    if appended:
        update["parent"] = snapshot.content_hash()
    return snapshot.model_copy(update=update)


def _reseal_on(
    store: Execution, receipt: OwnerRunReceipt, snapshot: Any, **changes: Any
) -> OwnerRunReceipt:
    """Write `snapshot` as the store's current one and reseal `receipt` on it (heads re-derived,
    `changes` applied); the forger's consistent resealing."""
    store._write(snapshot)
    resealed = receipt.model_copy(
        update={
            "snapshot_sha256": snapshot.content_hash(),
            "heads": tuple(ow._settled(store, h.module_id) for h in snapshot.heads),
            **changes,
        }
    )
    _reseal(store, resealed)
    return resealed


def _move_last_submission(
    store: Execution, receipt: OwnerRunReceipt, snapshot: Any, **changes: Any
) -> tuple[Any, ...]:
    """The receipt's submissions with the last one's `snapshot_after` moved to `snapshot` (and
    `changes` applied), its audit record swapped consistently."""
    last = receipt.submissions[-1]
    moved = last.model_copy(update={"snapshot_after_sha256": snapshot.content_hash(), **changes})
    _swap(store, "submissions", last, moved)
    return (*receipt.submissions[:-1], moved)


def test_genuine_valid_cp1a_run_verifies(
    valid_run: tuple[Path, OwnerRunReceipt], tmp_path: Path
) -> None:
    store, receipt = _fork_blocked(valid_run, tmp_path)
    _, head, attempt = _head_attempt(store, "CP-1A")
    assert (head.status, attempt.number, attempt.issues) == ("restricted", 0, ())
    assert _verdict(store, receipt) == "accepted"


@pytest.mark.parametrize("appended", [False, True], ids=["in_place", "appended_snapshot"])
def test_valid_cp1a_turned_blocked_refuses(
    valid_run: tuple[Path, OwnerRunReceipt], tmp_path: Path, appended: bool
) -> None:
    """R5-1 (HIGH 1a): the valid CP-1A (attempt 0, no invalid step, no issues) is shown as a
    blocked head with forged limitations; in place the settling submission's record moves with
    it, appended it keeps its genuine settlement snapshot. A blocked head must be attempt 1 with
    issues and a rebuilt invalid-step settlement."""
    store, receipt = _fork_blocked(valid_run, tmp_path)
    snapshot, _, attempt = _head_attempt(store, "CP-1A")
    module = _blocked_module(snapshot, attempt, (FORGED_LIMITATION,))
    store._store(module.model_dump_json())
    forged = _with_result(snapshot, attempt, module, appended=appended)
    changes: dict[str, Any] = {}
    if not appended:
        assert receipt.submissions[-1].snapshot_after_sha256 == snapshot.content_hash()
        changes["submissions"] = _move_last_submission(store, receipt, forged)
    resealed = _reseal_on(store, receipt, forged, **changes)
    _, head, shown = _head_attempt(store, "CP-1A")
    assert (head.status, shown.number, shown.issues) == ("blocked", 0, ())
    assert store.head_module(head).limitations == (FORGED_LIMITATION,)
    assert _verdict(store, resealed) == "identity_mismatch"


@pytest.mark.parametrize("issues_too", [False, True], ids=["a_prime", "a_double_prime"])
def test_appended_snapshot_rewriting_blocked_cp1a_refuses(
    blocked_run: tuple[Path, OwnerRunReceipt], tmp_path: Path, issues_too: bool
) -> None:
    """R5-1 (HIGH 1b, A' and A''): the genuine settlement snapshot stays; a descendant snapshot
    rewrites the blocked CP-1A result and head (A'' also the attempt's issues). No step or
    submission record is touched, so only binding the final attempt and head to the settling
    submission's `snapshot_after` refuses it."""
    store, receipt = _fork_blocked(blocked_run, tmp_path)
    snapshot, head, attempt = _head_attempt(store, "CP-1A")
    module = store.result(head.result_sha256).model_copy(
        update={"limitations": (FORGED_LIMITATION,)}
    )
    store._store(module.model_dump_json())
    changes = {"issues": module.limitations} if issues_too else {}
    forged = _with_result(snapshot, attempt, module, appended=True, **changes)
    resealed = _reseal_on(store, receipt, forged)
    _, shown_head, shown = _head_attempt(store, "CP-1A")
    assert store.head_module(shown_head).limitations == (FORGED_LIMITATION,)
    assert (shown.number, shown.status, shown.issues == module.limitations) == (
        1,
        "finished",
        issues_too,
    )
    assert _verdict(store, resealed) == "identity_mismatch"


def test_appended_snapshot_dropping_the_repair_attempt_refuses(
    blocked_run: tuple[Path, OwnerRunReceipt], tmp_path: Path
) -> None:
    """R5-1 (HIGH 1b, B'): the genuine history stays; a descendant snapshot drops CP-1A attempt 1
    and turns the rejected attempt 0 into the blocked head; attempt 1's begin, calls and
    submission leave the receipt. The final attempt 0 differs from the one its settling submission
    left, and a blocked head is never attempt 0."""
    store, receipt = _fork_blocked(blocked_run, tmp_path)
    snapshot = store.read()
    zero, one = [a for a in snapshot.attempts if a.module_id == "CP-1A"]
    assert (zero.number, one.number) == (0, 1)
    module = _blocked_module(snapshot, zero, zero.issues)
    store._store(module.model_dump_json())
    forged = _with_result(snapshot, zero, module, appended=True)
    forged = forged.model_copy(
        update={"attempts": tuple(a for a in forged.attempts if a.ticket_id != one.ticket_id)}
    )
    repair = one.ticket_id
    for call in receipt.calls:
        if call.binding.ticket_id == repair:
            _swap(store, "calls", call, None)
    for read in receipt.input_reads:
        if read.binding.ticket_id == repair:
            _swap(store, "input-reads", read, None)
    for begin in receipt.begins:
        if begin.ticket_id == repair:
            _swap(store, "begins", begin, None)
    kept = []
    for submission in receipt.submissions:
        if submission.binding.binding.ticket_id == repair:
            _swap(store, "bindings", submission.binding, None)
            _swap(store, "submissions", submission, None)
        else:
            kept.append(submission)
    resealed = _reseal_on(
        store,
        receipt,
        forged,
        calls=tuple(c for c in receipt.calls if c.binding.ticket_id != repair),
        input_reads=tuple(r for r in receipt.input_reads if r.binding.ticket_id != repair),
        begins=tuple(b for b in receipt.begins if b.ticket_id != repair),
        submissions=tuple(kept),
    )
    _, head, shown = _head_attempt(store, "CP-1A")
    assert (head.status, shown.number) == ("blocked", 0)
    assert [(a.module_id, a.number) for a in store.read().attempts] == [("CP-0", 0), ("CP-1A", 0)]
    assert _verdict(store, resealed) == "identity_mismatch"


def test_appended_snapshot_rewriting_the_repair_chain_issues_refuses(
    blocked_run: tuple[Path, OwnerRunReceipt], tmp_path: Path
) -> None:
    """R5-1 (HIGH 1b, `forge_repair` appended): a descendant snapshot rewrites attempt 0's issues
    and attempt 1's `repair_issues` consistently (the chain check still holds). The final attempt
    0 no longer equals the one its settling submission left."""
    store, receipt = _fork_blocked(blocked_run, tmp_path)
    snapshot = store.read()

    def rewritten(attempt: Attempt) -> Attempt:
        if attempt.module_id != "CP-1A":
            return attempt
        field = "issues" if attempt.number == 0 else "repair_issues"
        return attempt.model_copy(update={field: (FORGED_LIMITATION,)})

    forged = snapshot.model_copy(
        update={
            "parent": snapshot.content_hash(),
            "attempts": tuple(rewritten(a) for a in snapshot.attempts),
        }
    )
    resealed = _reseal_on(store, receipt, forged)
    zero, one = [a for a in store.read().attempts if a.module_id == "CP-1A"]
    assert (zero.issues, one.repair_issues) == ((FORGED_LIMITATION,), (FORGED_LIMITATION,))
    assert _verdict(store, resealed) == "identity_mismatch"


def test_appended_snapshot_rewriting_blocked_cp1_refuses(
    blocked_cp1_run: tuple[Path, OwnerRunReceipt], tmp_path: Path
) -> None:
    """R5-1 (HIGH 1b, F4 on CP-1): the blocked CP-1 head and its attempt's issues are rewritten by
    a descendant snapshot; the refused CP-MODEL publication is moved onto it. The final attempt
    differs from the one its settling submission left, and the head is not the rebuilt one."""
    store, receipt = _fork_blocked(blocked_cp1_run, tmp_path)
    assert _verdict(store, receipt) == "accepted"  # control: the genuine blocked CP-1 run
    snapshot, head, attempt = _head_attempt(store, "CP-1")
    assert (head.status, attempt.number) == ("blocked", 1)
    module = store.result(head.result_sha256).model_copy(
        update={"limitations": (FORGED_LIMITATION,)}
    )
    store._store(module.model_dump_json())
    forged = _with_result(snapshot, attempt, module, appended=True, issues=(FORGED_LIMITATION,))
    moved = tuple(
        p.model_copy(
            update={
                "snapshot_before_sha256": forged.content_hash(),
                "snapshot_after_sha256": forged.content_hash(),
            }
        )
        for p in receipt.publications
    )
    for old, new in zip(receipt.publications, moved, strict=True):
        _swap(store, "publications", old, new)
    resealed = _reseal_on(store, receipt, forged, publications=moved)
    _, shown_head, _ = _head_attempt(store, "CP-1")
    assert store.head_module(shown_head).limitations == (FORGED_LIMITATION,)
    assert _verdict(store, resealed) == "identity_mismatch"


def _forge_blocked_step(
    store: Execution, receipt: OwnerRunReceipt, change: Any
) -> tuple[Any, OwnerRunReceipt]:
    """The blocking CP-1A step replaced by `change(step)` with the snapshot, submission record
    and receipt made consistent in place; returns the forged step and the resealed receipt."""
    snapshot = store.read()
    last = receipt.submissions[-1]
    attempt = next(a for a in snapshot.attempts if a.ticket_id == last.binding.binding.ticket_id)
    step = attempt.steps[-1]
    assert step.status == "invalid" and step.output_sha256 is not None  # a rule-only failure
    forged_step = change(step)
    forged_attempt = attempt.model_copy(update={"steps": (*attempt.steps[:-1], forged_step)})
    forged = snapshot.model_copy(
        update={
            "attempts": tuple(
                forged_attempt if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts
            )
        }
    )
    submissions = _move_last_submission(
        store,
        receipt,
        forged,
        step_sha256=forged_step.content_hash(),
        step_output_sha256=forged_step.output_sha256,
    )
    return forged_step, _reseal_on(store, receipt, forged, submissions=submissions)


def test_invalid_step_output_swapped_refuses(
    blocked_run: tuple[Path, OwnerRunReceipt], tmp_path: Path
) -> None:
    """R5-3 (L1): the blocking CP-1A step keeps the validator's output (its failure is the read
    rule's). That output is swapped for a forged report; the verifier must rebuild the output
    bytes, not reuse the stored hash."""
    store, receipt = _fork_blocked(blocked_run, tmp_path)

    def swapped(step: StepSubmission) -> StepSubmission:
        report = json.loads(store.step_output(step.output_sha256 or ""))
        report["limitations"] = [FORGED_LIMITATION]
        output = json.dumps(report)
        assert output != store.step_output(step.output_sha256 or "")
        return step.model_copy(update={"output_sha256": store._store(output)})

    forged_step, resealed = _forge_blocked_step(store, receipt, swapped)
    assert json.loads(store.step_output(forged_step.output_sha256 or ""))["limitations"] == [
        FORGED_LIMITATION
    ]
    assert _verdict(store, resealed) == "identity_mismatch"


def test_invalid_step_inputs_forged_refuses(
    blocked_run: tuple[Path, OwnerRunReceipt], tmp_path: Path
) -> None:
    """R5-3 (L1): the blocking CP-1A step's `inputs` gain a fake `step:` input; the verifier must
    rebuild them from the attempt's inputs and its completed steps."""
    store, receipt = _fork_blocked(blocked_run, tmp_path)
    fake = Input(input_id="step:forged", sha256="0" * 64)
    forged_step, resealed = _forge_blocked_step(
        store, receipt, lambda step: step.model_copy(update={"inputs": (*step.inputs, fake)})
    )
    assert forged_step.inputs[-1] == fake
    assert _verdict(store, resealed) == "identity_mismatch"


def _cp1a_context() -> str:
    """The positive business_context with its consumers cut to CP-MODEL (the CP-1A-only plan)."""
    context = json.loads(runs.literal("positive", "business_context", _cp1a_only_pack()))
    context["consumers"] = [c for c in context["consumers"] if c["module_id"] == "CP-MODEL"]
    return json.dumps(context)


def _side_ready_cp0(root: Path, store: Execution, pack: PreparedPack) -> tuple[Attempt, Any]:
    """A side run's genuine settlement of the READY review (CP-0 commands `Run CP-1A`): its CP-0
    attempt and head, the side run's blobs copied into `store` so that head resolves there."""
    side = OwnerWorkflow.create(root / "side", pack)
    review = _cp0_review(pack)
    runs.read_cited(side, review)
    assert side.submit_review(review)["status"] == "valid"
    state = side._store.read()
    for blob in (side._store.directory / "blobs").iterdir():
        target = store.directory / "blobs" / blob.name
        if not target.exists():
            shutil.copy2(blob, target)
    return (
        next(a for a in state.attempts if a.module_id == "CP-0"),
        next(h for h in state.heads if h.module_id == "CP-0"),
    )


def _cp0_state(store: Execution) -> tuple[Attempt, Any]:
    snapshot = store.read()
    return (
        next(a for a in snapshot.attempts if a.module_id == "CP-0"),
        next(h for h in snapshot.heads if h.module_id == "CP-0"),
    )


def _seal_with_cp0_restored(
    workflow: OwnerWorkflow, root: Path, genuine: tuple[Attempt, Any]
) -> str:
    """Append the final snapshot that restores CP-0's genuine attempt and head (dropping any other
    CP-0 attempt), let the runtime seal, and return the verdict (the runtime's own `_verify`
    refusing at `write_receipt` counts as the verdict)."""
    store = workflow._store
    attempt, head = genuine
    snapshot = store.read()
    restored = snapshot.model_copy(
        update={
            "parent": snapshot.content_hash(),
            "attempts": tuple(
                attempt if a.ticket_id == attempt.ticket_id else a
                for a in snapshot.attempts
                if a.module_id != "CP-0" or a.ticket_id == attempt.ticket_id
            ),
            "heads": tuple(head if h.module_id == "CP-0" else h for h in snapshot.heads),
        }
    )
    store._write(restored)
    workflow._current_sha256 = restored.content_hash()
    final = store.read()
    cp1a = next(h for h in final.heads if h.module_id == "CP-1A")
    assert [h.status for h in final.heads] == ["restricted", "restricted"]
    assert [i.sha256 for i in cp1a.inputs if i.input_id == "CP-0"] != [head.result_sha256]
    with pytest.raises(NotAuthorized):  # the final CP-0 head says `DO NOT RUN` for CP-1A
        current_inputs(final, "CP-1A")
    try:
        receipt = workflow.write_receipt(root / "receipt.json")
    except WorkflowError as error:
        return error.code
    assert not receipt.refusals and [b.module_id for b in receipt.begins] == ["CP-0", "CP-1A"]
    return _verdict(store, receipt)


def test_genuine_conditional_cp0_refuses_cp1a_and_verifies(tmp_path: Path) -> None:
    """Control: CP-0 judges CP-1A CONDITIONAL, the walk refuses CP-1A and the receipt verifies."""
    pack = _cp1a_only_pack()
    workflow = OwnerWorkflow.create(tmp_path / "store", pack)
    review = _cp0_review(pack, conditional=True)
    runs.read_cited(workflow, review)
    outcome = workflow.submit_review(review)
    assert (outcome["status"], outcome["refusal"]) == ("valid", "cp1a_not_authorized")
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert [r.module_id for r in receipt.refusals] == ["CP-1A"]
    assert _verdict(workflow._store, receipt) == "accepted"


def test_transient_cp0_authorization_refuses(tmp_path: Path, monkeypatch: Any) -> None:
    """HIGH 1 (fix 4): CP-0 genuinely judges CP-1A CONDITIONAL. One unrecorded snapshot X swaps
    CP-0's attempt and head for a side run's settlement of the READY review (ticket kept); the
    unmodified runtime begins, runs and settles CP-1A on X; a final snapshot restores CP-0's
    genuine attempt and head. Every recorded coordinate is an ancestor, so only a gapless chain
    or the final `current_inputs` binding of the CP-1A head can refuse it."""
    pack = _cp1a_only_pack()
    genuine: dict[str, tuple[Attempt, Any]] = {}
    original_begin = OwnerWorkflow._begin

    def forged_begin(self: OwnerWorkflow, module_id: str) -> bool:
        if module_id == "CP-1A" and self._store.directory == tmp_path / "store" and not genuine:
            genuine["cp0"] = _cp0_state(self._store)
            side_attempt, side_head = _side_ready_cp0(tmp_path, self._store, pack)
            snapshot = self._store.read()
            ticket = genuine["cp0"][0].ticket_id
            swapped = side_attempt.model_copy(update={"ticket_id": ticket})
            self._store._write(
                snapshot.model_copy(
                    update={
                        "parent": snapshot.content_hash(),
                        "attempts": tuple(
                            swapped if a.ticket_id == ticket else a for a in snapshot.attempts
                        ),
                        "heads": tuple(
                            side_head if h.module_id == "CP-0" else h for h in snapshot.heads
                        ),
                    }
                )
            )
        return original_begin(self, module_id)

    monkeypatch.setattr(OwnerWorkflow, "_begin", forged_begin)
    workflow = OwnerWorkflow.create(tmp_path / "store", pack)
    review = _cp0_review(pack, conditional=True)
    runs.read_cited(workflow, review)
    assert workflow.submit_review(review)["refusal"] is None
    assert runs.drive_cp1a(workflow, pack, "positive", text=_cp1a_context())["status"] == "valid"
    assert _seal_with_cp0_restored(workflow, tmp_path, genuine["cp0"]) == "identity_mismatch"


def test_extra_cp0_attempt_inside_cp0_submission_after_refuses(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """HIGH 1 variant (fix 4): the forged snapshot is CP-0's own recorded submission `after`: it
    keeps the genuine CONDITIONAL attempt, adds an extra finished CP-0 attempt (the side run's
    READY settlement under a new ticket) and shows that one as CP-0's head, so the runtime begins
    CP-1A from a recorded coordinate; the final snapshot drops the extra attempt and restores the
    genuine head."""
    pack = _cp1a_only_pack()
    genuine: dict[str, tuple[Attempt, Any]] = {}
    original_submit = ow.submit_cp0_review

    def forged_submit(store: Execution, ticket_id: str, payload: str) -> Attempt:
        attempt = original_submit(store, ticket_id, payload)
        if store.directory != tmp_path / "store" or genuine:  # the side run's own CP-0 passes
            return attempt
        genuine["cp0"] = _cp0_state(store)
        side_attempt, side_head = _side_ready_cp0(tmp_path, store, pack)
        snapshot = store.read()
        extra = side_attempt.model_copy(update={"ticket_id": str(uuid4())})
        store._write(
            snapshot.model_copy(
                update={
                    "parent": snapshot.content_hash(),
                    "attempts": (*snapshot.attempts, extra),
                    "heads": tuple(
                        side_head if h.module_id == "CP-0" else h for h in snapshot.heads
                    ),
                }
            )
        )
        return attempt

    monkeypatch.setattr(ow, "submit_cp0_review", forged_submit)
    workflow = OwnerWorkflow.create(tmp_path / "store", pack)
    review = _cp0_review(pack, conditional=True)
    runs.read_cited(workflow, review)
    outcome = workflow.submit_review(review)
    assert (outcome["status"], outcome["refusal"]) == ("valid", None)
    after = _snapshot(workflow._store, workflow._submissions[0].snapshot_after_sha256)
    assert [a.status for a in after.attempts if a.module_id == "CP-0"] == ["finished"] * 2
    assert runs.drive_cp1a(workflow, pack, "positive", text=_cp1a_context())["status"] == "valid"
    assert _seal_with_cp0_restored(workflow, tmp_path, genuine["cp0"]) == "identity_mismatch"


@pytest.mark.parametrize("module_id", ["CP-4", "CP-2", "CP-MODEL"])
def test_unplanned_module_head_refuses(
    valid_run: tuple[Path, OwnerRunReceipt], tmp_path: Path, module_id: str
) -> None:
    """HIGH 2 (fix 4): an appended final snapshot adds a finished attempt and an accepted head of
    a module outside the plan (CP-4, CP-2 and CP-MODEL, each with the qualification `head_of` expects),
    with no begin, submission or publication; the receipt heads are re-derived and resealed."""
    store, receipt = _fork_blocked(valid_run, tmp_path)
    assert module_id not in receipt.plan
    snapshot = store.read()
    run = snapshot.run
    cp1a = next(h for h in snapshot.heads if h.module_id == "CP-1A")
    inputs = tuple(i for i in cp1a.inputs if i.input_id == "prepared-pack")
    forged = Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=module_id,
        inputs=inputs,
        attempt=0,
        status="accepted",
        limitations=(),
    )
    attempt = Attempt(
        ticket_id=str(uuid4()),
        module_id=module_id,
        inputs=inputs,
        number=0,
        status="finished",
        payload_sha256=store._store(forged.model_dump_json()),
        result_sha256=forged.content_hash(),
    )
    final = snapshot.model_copy(
        update={
            "parent": snapshot.content_hash(),
            "attempts": (*snapshot.attempts, attempt),
            "heads": (*snapshot.heads, head_of(forged, ow._QUALIFICATION.get(module_id))),
        }
    )
    resealed = _reseal_on(store, receipt, final)
    assert [h.module_id for h in store.read().heads] == ["CP-0", "CP-1A", module_id]
    assert _verdict(store, resealed) == "identity_mismatch"
