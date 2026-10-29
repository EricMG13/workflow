"""G2 generic owner rendering (docs/OWNER-RENDERING-LEASE.md rev 2).

Naming scheme: `test_fast_*` build no genuine owner run (select them with `-k fast`);
`test_genuine_cp1_model_*` build the genuine G1 CP-1 + CP-MODEL runs once per module;
`test_genuine_deferred_*` drive the other scopes' genuine runs (11 to 26 minutes each) and run
once per branch. Every expected value is read from an oracle file, the lease or a producer, never
from `owner_rendering`.
"""

import hashlib
import html as html_lib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import test_cp1_chart_render

from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Run
from deploy_vii.execution import Execution
from deploy_vii.registry import modules as registry_modules
from deploy_vii.report_view import build, pathways
from deploy_workflow import owner_rendering as g2
from deploy_workflow.owner_workflow import BeginRecord, OwnerRunReceipt

ROOT = Path(__file__).resolve().parents[1]
LEASE = (ROOT / "docs/OWNER-RENDERING-LEASE.md").read_text(encoding="utf-8")
H = "0" * 64
BANNER_ANCHOR = '<div id="call-root"></div>'

# The 18 shipped rows (lease rev 2, R2.2; `cp3c-fp04-refinancing` since rulings item 22 M1); the
# `cp6-fp01-committee` row is absent until its prerequisite lands.
SHIPPED_IDS = (
    "cp1-model",
    "s1a-credit-snapshot",
    "cp3-fp01-relative-value",
    "cp1c-fp03-peers",
    "cp3d-fp03-market",
    "cp1d-fp02-quality",
    "cp2a-fp05-downside",
    "cp2g-fp05-forward",
    "cp2g-fp05-forward-gap",
    "cp2h-fp05-ratings",
    "cp4c-fp05-recovery",
    "cp2d-fp04-liquidity",
    "cp3c-fp04-refinancing",
    "cp4-fp04-covenants",
    "cp8-fp01-what-changed",
    "slice-cp2e-sensitivity",
    "slice-cpdr-research",
    "slice-cpl10-screen",
)
GATED_IDS = ("cp6-fp01-committee",)
# Rev 0 literals (lease lines 173-181); the s1a refused text is dropped by rev 1 M1.
REV0_BANNERS = {
    ("cp1-model", "complete"): (
        "Historical financial analysis and Model publication only. "
        "Remaining analytical owners and forward projections remain unqualified."
    ),
    ("cp1-model", "refused"): (
        "Financial source missing. CP1 financial analysis and Model publication did not run."
    ),
    ("s1a-credit-snapshot", "complete"): (
        "Credit snapshot: source readiness, historical financials, Model, business context and "
        "credit synthesis only. Integrity review and remaining analytical owners remain "
        "unqualified."
    ),
}
# Rev 2 R2.2 sections (pathway order); `cp1-model` is rev 3 R3.1.
EXPECTED_SECTIONS = {
    "cp1-model": ("model-chart-strip", "capital-structure", "financials-credit-metrics"),
    "s1a-credit-snapshot": (
        "key-findings",
        "company-operating-model",
        "strengths-weaknesses",
        "company-profile",
        "transaction-summary",
    ),
    "cp3-fp01-relative-value": ("relative-value",),
    "cp1c-fp03-peers": ("peer-positioning",),
    "cp3d-fp03-market": ("market-against-fundamentals",),
    "cp1d-fp02-quality": ("earnings-quality", "restated-leverage"),
    "cp2a-fp05-downside": ("downside-stress", "break-points"),
    "cp2g-fp05-forward": ("forward-credit-path", "forward-breakpoints"),
    "cp2g-fp05-forward-gap": ("forward-credit-path", "forward-breakpoints"),
    "cp2h-fp05-ratings": ("rating-triggers",),
    "cp4c-fp05-recovery": ("recovery-by-class", "value-allocation-claims"),
    "cp2d-fp04-liquidity": ("liquidity-runway", "funding-gap"),
    "cp3c-fp04-refinancing": ("funding-gap", "refinancing-paths", "lme-creditor-exposure"),
    "cp4-fp04-covenants": (
        "covenant-tests-headroom",
        "red-flags",
        "lender-protection-score",
        "capacity",
        "ebitda-definition",
        "documents-structure",
    ),
    "cp8-fp01-what-changed": ("what-changed",),
    "slice-cp2e-sensitivity": (),
    "slice-cpdr-research": (),
    "slice-cpl10-screen": (),
}
REFUSED_ROWS = {
    "cp1-model",
    "cp1c-fp03-peers",
    "cp2a-fp05-downside",
    "cp2g-fp05-forward-gap",
    "cp2h-fp05-ratings",
    "cp4c-fp05-recovery",
    "cp8-fp01-what-changed",
}
MODEL_ROWS = {"cp1-model", "s1a-credit-snapshot", "cp3-fp01-relative-value"}


def _lease_banners() -> dict[tuple[str, str], str]:
    """The R2.4 table, parsed from the frozen lease."""
    section = LEASE.split("### R2.4", 1)[1].split("### R2.5", 1)[0]
    rows = re.findall(
        r"^\| `([a-z0-9-]+)` \| (complete|refused) \| (.+) \|$", section, re.MULTILINE
    )
    return {(scope, outcome): literal for scope, outcome, literal in rows}


def _run_of(value: Any) -> Run:
    assert isinstance(value, Run)
    return value


def _match(run: Run) -> list[str]:
    return [
        scope.scope_id
        for scope in g2.DELIVERY_SCOPES.values()
        if (scope.pathway, tuple(scope.requested_modules), scope.case_kind)
        == (run.pathway, tuple(run.requested_modules), run.case_kind)
    ]


# ---------------------------------------------------------------- the scope table (fast)


def test_fast_scope_table_rows_and_gated_rows() -> None:
    assert tuple(g2.DELIVERY_SCOPES) == SHIPPED_IDS
    for gated in GATED_IDS:
        assert gated not in g2.DELIVERY_SCOPES
    for scope_id, scope in g2.DELIVERY_SCOPES.items():
        assert scope.scope_id == scope_id
        assert scope.rails == ("evidence", "limitations")
        assert scope.case_kind == "synthetic"


def test_fast_cp3c_row_is_the_lease_r22_row() -> None:
    """Rulings item 22 M1: the row ships exactly as lease R2.2 writes it."""
    section = LEASE.split("### R2.2", 1)[1].split("### R2.3", 1)[0]
    (row,) = re.findall(r"^\| `cp3c-fp04-refinancing` \|(.+)$", section, re.MULTILINE)
    cells = [cell.strip() for cell in row.split("|")]
    pathway, requested, sections, cases, refused = cells[:5]
    scope = g2.DELIVERY_SCOPES["cp3c-fp04-refinancing"]
    assert scope.pathway == pathway == "covenant_refinancing"
    assert tuple(scope.requested_modules) == tuple(re.findall(r'"([^"]+)"', requested))
    assert tuple(scope.requested_modules) == ("CP-1", "CP-1A", "CP-2", "CP-2D", "CP-3C")
    assert tuple(scope.sections) == tuple(re.findall(r"`([^`]+)`", sections))
    assert tuple(scope.sections) == EXPECTED_SECTIONS["cp3c-fp04-refinancing"]
    assert cases == "positive, gap_minimum_cash, gap_no_repricing"
    assert refused == "none"
    assert set(scope.banner) == {"complete"}
    assert scope.case_kind == "synthetic" and scope.rails == ("evidence", "limitations")


def test_fast_scope_banners_equal_the_frozen_lease_literals() -> None:
    literals = {**_lease_banners(), **REV0_BANNERS}
    expected_pairs = {pair for pair in literals if pair[0] in SHIPPED_IDS}
    got = {
        (scope_id, outcome): text
        for scope_id, scope in g2.DELIVERY_SCOPES.items()
        for outcome, text in scope.banner.items()
    }
    assert got == {pair: literals[pair] for pair in expected_pairs}
    # refused is offered exactly by the rows whose oracle pins a refused run and whose driver
    # can run it (R2.1, R2.5)
    assert {s for s, o in got if o == "refused"} == REFUSED_ROWS
    assert {s for s, o in got if o == "complete"} == set(SHIPPED_IDS)


def test_fast_scope_sections_follow_the_pathway_order() -> None:
    blocks = {item.id: item.blocks for item in pathways()}
    for scope_id, scope in g2.DELIVERY_SCOPES.items():
        assert tuple(scope.sections) == EXPECTED_SECTIONS[scope_id], scope_id
        order = [blocks[scope.pathway].index(section) for section in scope.sections]
        assert order == sorted(set(order)), scope_id
    for scope_id in ("slice-cp2e-sensitivity", "slice-cpdr-research", "slice-cpl10-screen"):
        assert g2.DELIVERY_SCOPES[scope_id].sections == ()


def test_fast_cp1_model_sections_are_the_blocks_produced_by_cp1_alone() -> None:
    """Rev 3 R3.1 derivation, read from the core's block specs rather than G2's table."""
    from deploy_vii.report_view import _spec_of

    credit = next(item for item in pathways() if item.id == "credit_snapshot")
    producers_cp1 = tuple(b for b in credit.blocks if _spec_of(b).producers == ("CP-1",))
    assert producers_cp1 == tuple(g2.DELIVERY_SCOPES["cp1-model"].sections)


def test_fast_expected_block_payload_equals_the_core_payload_for_figure_blocks() -> None:
    """The proof's expectation for a block (state spelling, chart svg, gaps note) is the core's."""
    cr1 = importlib.import_module("test_chart_render_cr1")

    from deploy_vii import render as core_render

    _, report = cr1._report("positive")
    payload = core_render._report_payload(report)
    assert any(block.figures for block in report.blocks)
    payload_blocks = payload["blocks"]
    assert isinstance(payload_blocks, list)
    for block, got in zip(report.blocks, payload_blocks, strict=True):
        assert g2._expected_block_payload(block) == got, block.block_id


def test_fast_refused_outcome_refuses_a_block_that_draws_a_figure() -> None:
    cr1 = importlib.import_module("test_chart_render_cr1")

    _, report = cr1._report("positive")
    block = next(b for b in report.blocks if b.figures)
    # model_copy skips the Block validator, which would itself refuse a not_run figure block
    hollow = block.model_copy(update={"state": "not_run"})
    scope = g2.DELIVERY_SCOPES["cp4-fp04-covenants"]
    with pytest.raises(ValueError, match=r"^owner_render_proof"):
        g2._sections(
            g2.DeliveryScope(
                scope.scope_id,
                scope.pathway,
                scope.requested_modules,
                scope.case_kind,
                (block.block_id,),
                scope.rails,
                scope.banner,
            ),
            "refused",
            {block.block_id: hollow},
            {},
            {},
            {},
            {},
        )


def test_fast_scope_triples_are_unique_and_modules_are_known() -> None:
    triples = [
        (s.pathway, tuple(s.requested_modules), s.case_kind) for s in g2.DELIVERY_SCOPES.values()
    ]
    assert len(set(triples)) == len(triples)
    known = {entry.module_id for entry in registry_modules()}
    for scope in g2.DELIVERY_SCOPES.values():
        assert set(scope.requested_modules) <= known
        assert ("CP-MODEL" in scope.requested_modules) == (scope.scope_id in MODEL_ROWS)
        base = tuple(scope.requested_modules)
        # one module added, dropped or reordered matches no row (lease R2.8.5)
        for variant in ((*base, "CP-5"), base[::-1], base[:-1]):
            if variant and variant != base:
                run = Run(
                    run_id="r",
                    issuer_id="i",
                    issuer_name="I",
                    as_of=date(2025, 12, 31),
                    case_kind="synthetic",
                    pathway=scope.pathway,
                    requested_modules=variant,
                )
                assert scope.scope_id not in _match(run)


def _driver_runs() -> Iterator[tuple[str, str, Callable[[], Run]]]:
    """(label, expected scope id or '-', run builder) for every driver case in R2.2 and R2.5."""

    def pack_run(module: str, case: str | None = None) -> Callable[[], Run]:
        def build() -> Run:
            driver = importlib.import_module(module)
            return _run_of(
                driver.make_pack(case).run if case is not None else driver.make_pack().run
            )

        return build

    for case in ("positive", "gap"):
        yield f"s1a-{case}", "s1a-credit-snapshot", pack_run("s1a_runs", case)
    for case in ("positive", "gap", "no_peers", "refused", "blocked"):
        yield f"cp1c-{case}", "cp1c-fp03-peers", pack_run("cp1c_runs", case)
    for case in ("positive", "statements_only", "gap"):
        yield f"cp1d-{case}", "cp1d-fp02-quality", pack_run("cp1d_runs", case)
    for case in ("positive", "gap", "refused", "blocked"):
        yield f"cp2a-{case}", "cp2a-fp05-downside", pack_run("cp2a_runs", case)
    for case, scope in (
        ("positive", "cp2g-fp05-forward"),
        ("cp1d_blocked", "cp2g-fp05-forward"),
        ("gap", "cp2g-fp05-forward-gap"),
        ("refused", "cp2g-fp05-forward-gap"),
        ("blocked", "cp2g-fp05-forward-gap"),
        ("cp2a_blocked", "cp2g-fp05-forward-gap"),
    ):
        yield f"cp2g-{case}", scope, pack_run("cp2g_runs", case)
    for case in ("positive", "gap", "refused", "blocked", "cp2g_blocked"):
        yield f"cp2h-{case}", "cp2h-fp05-ratings", pack_run("cp2h_runs", case)
    for case in ("positive", "gap", "refused", "blocked", "cp2g_blocked"):
        yield f"cp4c-{case}", "cp4c-fp05-recovery", pack_run("cp4c_runs", case)
    for case in ("positive", "gap_no_recovery", "gap_no_market"):
        yield f"cp3d-{case}", "cp3d-fp03-market", pack_run("cp3d_runs", case)
    yield "cp2d", "cp2d-fp04-liquidity", pack_run("cp2d_runs")
    yield "cp3c", "cp3c-fp04-refinancing", pack_run("cp3c_runs")
    for case in ("positive", "gap"):
        yield f"cp3-{case}", "cp3-fp01-relative-value", _cp3_run(case)
    for case in ("positive", "gap", "gap_false_same_definition"):
        yield f"cp4-{case}", "cp4-fp04-covenants", _cp4_run(case)
    for case in ("positive", "no_outcome", "no_record"):
        yield f"cp8-{case}", "cp8-fp01-what-changed", pack_run("cp8_runs", case)
    for case in ("positive", "gap_no_facility_schedule"):
        yield f"cp2e-{case}", "slice-cp2e-sensitivity", pack_run("cp2e_runs", case)
    yield "cpdr", "slice-cpdr-research", pack_run("cpdr_runs")
    yield "cpl10", "slice-cpl10-screen", pack_run("cpl10_runs")


def _cp3_run(case: str) -> Callable[[], Run]:
    def build() -> Run:
        return _run_of(importlib.import_module("cp3_cp6_runs").make_pack(case).run)

    return build


def _cp4_run(case: str) -> Callable[[], Run]:
    def build() -> Run:
        return _run_of(importlib.import_module("test_method_cp4").make_pack(case).run)

    return build


_DRIVER_RUNS = list(_driver_runs())


@pytest.mark.parametrize(
    ("label", "expected", "build"), _DRIVER_RUNS, ids=[x[0] for x in _DRIVER_RUNS]
)
def test_fast_every_driver_run_matches_exactly_its_row(
    label: str, expected: str, build: Callable[[], Run]
) -> None:
    matched = _match(build())
    assert matched == ([] if expected == "-" else [expected]), label


def test_fast_cp6_run_is_outside_every_scope() -> None:
    manifest = json.loads((ROOT / "cases/cp3-cp6-owner/manifest.json").read_text())
    run = Run(
        run_id="r6",
        issuer_id="i",
        issuer_name="I",
        as_of=date(2025, 12, 31),
        case_kind="synthetic",
        pathway="credit_snapshot",
        requested_modules=tuple(manifest["runs"]["R6"]["requested_modules"]),
    )
    assert _match(run) == []


# Oracle pointers (R2.5): scope -> (oracle dir, pointer to the block tree for a case `{c}`).
ORACLE_POINTERS: dict[str, tuple[str, str]] = {
    "s1a-credit-snapshot": ("snapshot", "/{c}/FP01"),
    "cp1c-fp03-peers": ("cp1c-owner", "/cases/{c}/FP03"),
    "cp1d-fp02-quality": ("cp1d-owner", "/cases/{c}/FP02"),
    "cp2a-fp05-downside": ("cp2a-owner", "/cases/{c}/FP05"),
    "cp2g-fp05-forward": ("cp2g-owner", "/cases/positive/FP05"),
    "cp2g-fp05-forward-gap": ("cp2g-owner", "/cases/gap/FP05"),
    "cp2h-fp05-ratings": ("cp2h-owner", "/cases/{c}/FP05"),
    "cp4c-fp05-recovery": ("cp4c-owner", "/cases/{c}/FP05"),
    "cp2d-fp04-liquidity": ("cp2d-owner", "/fp04_render"),
    "cp3d-fp03-market": ("cp3d-owner", "/render"),
    "cp4-fp04-covenants": ("cp4-owner", "/render"),
    "cp8-fp01-what-changed": ("cp8-owner", "/render"),
}


def _oracle(name: str) -> Any:
    return json.loads((ROOT / "cases" / name / "expected.json").read_text(encoding="utf-8"))


def _pointer(document: Any, pointer: str) -> Any:
    for part in [p for p in pointer.split("/") if p]:
        document = document[int(part)] if isinstance(document, list) else document[part]
    return document


def _block_nodes(node: Any, sections: tuple[str, ...]) -> dict[str, Any]:
    """The oracle's per-block dicts, whether the node holds them directly or one level down.
    Fails loudly when a section is absent: no section is skipped."""
    candidates = [node]
    if isinstance(node, dict):
        candidates += [v for v in node.values() if isinstance(v, dict)]
    for candidate in candidates:
        if all(s in candidate for s in sections):
            return {s: candidate[s] for s in sections}
    raise AssertionError(f"oracle node lacks sections {sections}")


@pytest.mark.parametrize("scope_id", sorted(ORACLE_POINTERS))
def test_fast_sections_are_blocks_of_the_oracle_tree(scope_id: str) -> None:
    name, pointer = ORACLE_POINTERS[scope_id]
    node = _pointer(_oracle(name), pointer.format(c="positive"))
    sections = tuple(g2.DELIVERY_SCOPES[scope_id].sections)
    assert tuple(_block_nodes(node, sections)) == sections


# ---------------------------------------------------------------- receipt refusals (fast)


def _cp1_model_run() -> Run:
    return Run(
        run_id="g2-fast",
        issuer_id="issuer",
        issuer_name="Issuer",
        as_of=date(2025, 12, 31),
        case_kind="synthetic",
        pathway="credit_snapshot",
        requested_modules=("CP-1", "CP-MODEL"),
    )


def _receipt(run: Run) -> OwnerRunReceipt:
    return OwnerRunReceipt(
        run=run,
        pack_sha256=H,
        snapshot_sha256=H,
        participant="trusted-python",
        transport="python-api",
        plan=("CP-0", "CP-1", "CP-MODEL"),
        heads=(),
        model=None,
        begins=(
            BeginRecord(
                module_id="CP-0",
                ticket_id="t1",
                attempt=1,
                snapshot_before_sha256=H,
                snapshot_after_sha256=H,
            ),
        ),
        refusals=(),
        calls=(),
        input_reads=(),
        submissions=(),
        publications=(),
    )


def _render(tmp_path: Path, raw: bytes, destination: Path | None = None) -> Path:
    store, publication = tmp_path / "store", tmp_path / "publication"
    store.mkdir(exist_ok=True)
    receipt = tmp_path / "owner-run.json"
    receipt.write_bytes(raw)
    return g2.render_owner_slice(
        store, receipt, publication, destination or tmp_path / "out" / "delivery"
    )


def test_fast_noncanonical_receipt_spellings_are_refused(tmp_path: Path) -> None:
    (tmp_path / "out").mkdir()
    canonical = _receipt(_cp1_model_run()).model_dump_json()
    parsed = json.loads(canonical)
    assert '"attempt":1' in canonical
    reordered = json.dumps(dict(reversed(list(parsed.items()))), separators=(",", ":"))
    variants = {
        "float_spelling": canonical.replace('"attempt":1', '"attempt":1.0'),
        "exponent_spelling": canonical.replace('"attempt":1', '"attempt":1e0'),
        "reordered_keys": reordered,
        "duplicate_key": canonical.replace(
            '"participant":"trusted-python"',
            '"participant":"trusted-python","participant":"trusted-python"',
        ),
        "non_finite": canonical.replace('"attempt":1', '"attempt":NaN'),
        "not_json": "{",
        "typed_tamper": canonical.replace('"transport":"python-api"', '"transport":"carrier"'),
    }
    for name, text in variants.items():
        with pytest.raises(ValueError, match=r"^owner_render_receipt"):
            _render(tmp_path, text.encode(), tmp_path / "out" / name)
        assert not (tmp_path / "out" / name).exists(), name


def test_fast_whitespace_spelling_passes_the_spelling_gate(tmp_path: Path) -> None:
    """Only whitespace or escape spelling may differ; the refusal then comes from the store."""
    (tmp_path / "out").mkdir()
    pretty = json.dumps(json.loads(_receipt(_cp1_model_run()).model_dump_json()), indent=2)
    with pytest.raises(ValueError, match=r"^owner_render_") as error:
        _render(tmp_path, pretty.encode())
    assert not str(error.value).startswith("owner_render_receipt_spelling")
    assert not str(error.value).startswith("owner_render_receipt_wire")


def test_fast_outside_scope_is_refused(tmp_path: Path) -> None:
    (tmp_path / "out").mkdir()
    for modules in (("CP-1",), ("CP-MODEL", "CP-1"), ("CP-1", "CP-MODEL", "CP-5")):
        run = _cp1_model_run().model_copy(update={"requested_modules": modules})
        with pytest.raises(ValueError, match=r"^owner_render_scope"):
            _render(tmp_path, _receipt(run).model_dump_json().encode())


@pytest.mark.parametrize("kind", ["file", "directory", "symlink", "dangling"])
def test_fast_existing_destination_kinds_are_refused(tmp_path: Path, kind: str) -> None:
    destination = tmp_path / "out" / "delivery"
    destination.parent.mkdir()
    if kind == "file":
        destination.write_text("x")
    elif kind == "directory":
        destination.mkdir()
    elif kind == "symlink":
        (tmp_path / "target").mkdir()
        destination.symlink_to(tmp_path / "target")
    else:
        destination.symlink_to(tmp_path / "missing")
    raw = _receipt(_cp1_model_run()).model_dump_json().encode()
    with pytest.raises(ValueError, match=r"^owner_render_destination_exists"):
        _render(tmp_path, raw, destination)
    assert os.path.lexists(destination)


def test_fast_destination_parent_overlapping_an_input_is_refused(tmp_path: Path) -> None:
    store, publication = tmp_path / "store", tmp_path / "publication"
    store.mkdir()
    publication.mkdir()
    (publication / "inner").mkdir()
    receipt = tmp_path / "owner-run.json"
    receipt.write_bytes(_receipt(_cp1_model_run()).model_dump_json().encode())
    for parent in (store, publication, publication / "inner"):
        with pytest.raises(ValueError, match=r"^owner_render_destination_overlap"):
            g2.render_owner_slice(store, receipt, publication, parent / "delivery")
    # a case-variant alias of the store (darwin's default volume is case-insensitive)
    alias = tmp_path / "STORE"
    if alias.exists() and alias.samefile(store):
        with pytest.raises(ValueError, match=r"^owner_render_destination_overlap"):
            g2.render_owner_slice(store, receipt, publication, alias / "delivery")
    assert not (store / "delivery").exists()
    with pytest.raises(ValueError, match=r"^owner_render_destination"):
        g2.render_owner_slice(store, receipt, publication, tmp_path / "absent" / "delivery")
    assert not (tmp_path / "absent").exists()


def test_fast_render_receipt_wire_is_strict() -> None:
    for raw in (b"{", b'{"a":1,"a":2}', b'{"a":NaN}', b"[" * 5000 + b"]" * 5000, b"\xff"):
        with pytest.raises(ValueError, match=r"^owner_render_"):
            g2.OwnerRenderReceipt.from_wire(raw)


# ---------------------------------------------------------------- genuine cp1-model runs


def _fw() -> Any:
    return importlib.import_module("test_financial_workflow")


def _tree(*roots: Path) -> dict[str, bytes]:
    return {
        f"{root}:{p.relative_to(root)}": p.read_bytes()
        for root in roots
        if root.exists()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Genuine G1 CP-1 + CP-MODEL runs (positive and gap) and the financial slice's own runs."""
    from deploy_workflow.owner_workflow import OwnerWorkflow

    fw = _fw()
    # Built fresh per module run: no cache of genuine runs (a cache keyed on a path or a marker
    # could hide a changed store or a changed producer).
    base = tmp_path_factory.mktemp("g2-cp1-model")

    def start(root: Path, gap: bool = False) -> Any:
        pack = fw.make_pack(gap)
        return OwnerWorkflow.create(
            root / "store", pack, publication_directory=root / "model"
        ), pack

    positive = base / "positive"
    patch = pytest.MonkeyPatch()
    patch.setattr(fw, "start", start)
    try:
        workflow = fw.promoted_case(positive)
    finally:
        patch.undo()
    assert workflow.publish()["status"] == "ok"
    workflow.write_receipt(positive / "owner-run.json")
    gap = base / "gap"
    gap.mkdir()
    workflow, pack = start(gap, gap=True)
    fw.read_sources(workflow, gap=True)
    assert workflow.submit_review(fw.readiness(pack, gap=True))["status"] == "valid"
    assert workflow.publish()["status"] == "refused"
    workflow.write_receipt(gap / "owner-run.json")
    financial = fw.completed_financial_case(base / "fin-positive")
    return {"positive": positive, "gap": gap, "fin_positive": financial}


@pytest.fixture
def inputs(tmp_path: Path, runs: dict[str, Any]) -> Callable[[str], tuple[Path, Path, Path | None]]:
    counter = iter(range(1000))

    def copy(kind: str) -> tuple[Path, Path, Path | None]:
        source = runs[kind]
        root = tmp_path / f"inputs-{kind}-{next(counter)}"
        root.mkdir()
        shutil.copytree(source / "store", root / "store")
        shutil.copyfile(source / "owner-run.json", root / "owner-run.json")
        model = None
        if (source / "model").exists():
            shutil.copytree(source / "model", root / "model")
            model = root / "model"
        return root / "store", root / "owner-run.json", model

    return copy


def _payload(html_text: str) -> dict[str, Any]:
    marker = '<script id="report-data" type="application/json">'
    payload: dict[str, Any] = json.loads(html_text.split(marker, 1)[1].split("</script>", 1)[0])
    return payload


def _render_ok(
    tmp_path: Path, store: Path, receipt: Path, model: Path | None, name: str = "delivery"
) -> tuple[Path, Path]:
    destination = tmp_path / "out" / name
    destination.parent.mkdir(exist_ok=True)
    report = g2.render_owner_slice(store, receipt, model, destination)
    assert report == destination / "report.html"
    return report, destination


def _banner_free(text: str) -> str:
    return re.sub(
        r'<section id="delivery-scope-banner".*?</section>', "", text, count=1, flags=re.DOTALL
    )


def test_genuine_cp1_model_positive_delivery(
    tmp_path: Path, inputs: Callable[..., Any], runs: dict[str, Any]
) -> None:
    store, receipt, model = inputs("positive")
    assert model is not None
    before = _tree(store, model)
    report, destination = _render_ok(tmp_path, store, receipt, model)
    assert _tree(store, model) == before
    text = report.read_text(encoding="utf-8")
    scope = g2.DELIVERY_SCOPES["cp1-model"]
    assert text.count('id="delivery-scope-banner"') == 1
    assert text.count(BANNER_ANCHOR + '<section id="delivery-scope-banner"') == 1
    assert (
        f'data-delivery-scope="cp1-model">{html_lib.escape(scope.banner["complete"])}</section>'
        in text
    )
    wire = g2.OwnerRenderReceipt.from_wire((destination / "render-receipt.json").read_bytes())
    assert wire.outcome == "complete" and wire.scope_id == "cp1-model"
    assert not (destination / "render-receipt.json").read_bytes().endswith(b"\n")
    assert (destination / "owner-run.json").read_bytes() == receipt.read_bytes()
    assert wire.owner_receipt_file_sha256 == hashlib.sha256(receipt.read_bytes()).hexdigest()
    names = {str(p.relative_to(destination)) for p in destination.rglob("*") if p.is_file()}
    assert names == {
        "report.html",
        "owner-run.json",
        "render-receipt.json",
        "calculation.json",
        "model/model.html",
        "model/calculation.json",
        "model/receipt.json",
    }
    assert not any(p.is_symlink() for p in destination.rglob("*"))
    assert set(wire.files) == names - {"render-receipt.json"}
    for name, digest in wire.files.items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == digest
    # Equivalence with the financial slice delivery (lease test 3)
    from deploy_workflow.financial_rendering import render_financial_slice

    fin_store, fin_receipt, fin_model = runs["fin_positive"]
    fin_destination = tmp_path / "financial-delivery"
    fin_report = render_financial_slice(fin_store, fin_receipt, fin_model, fin_destination)
    assert _banner_free(text) == _banner_free(fin_report.read_text(encoding="utf-8"))
    for name in ("model.html", "calculation.json", "receipt.json"):
        assert (destination / "model" / name).read_bytes() == (fin_model / name).read_bytes()
        assert (fin_destination / "model" / name).read_bytes() == (
            destination / "model" / name
        ).read_bytes()
    assert_scope_figures("cp1-model", "positive", "complete", _payload(text))
    heads = {h.module_id: h for h in wire.head_results}
    assert [h.module_id for h in wire.head_results][:2] == ["CP-0", "CP-1"]
    assert {h.status for h in wire.head_results} <= {"accepted", "restricted"}
    assert tuple(s.block_id for s in wire.sections) == tuple(scope.sections)
    for section in wire.sections:
        assert section.state in {"populated", "collapsed"} and section.facts
        for fact in section.facts:
            assert fact.result_sha256 == heads[fact.module_id].result_sha256
    delivered_before = _tree(destination)
    g2.verify_owner_rendered_slice(store, receipt, model, destination)
    assert _tree(destination) == delivered_before and _tree(store, model) == before


def test_genuine_cp1_model_gap_is_refused_outcome(
    tmp_path: Path, inputs: Callable[..., Any]
) -> None:
    store, receipt, model = inputs("gap")
    assert model is None
    report, destination = _render_ok(tmp_path, store, receipt, None)
    text = report.read_text(encoding="utf-8")
    wire = g2.OwnerRenderReceipt.from_wire((destination / "render-receipt.json").read_bytes())
    assert wire.outcome == "refused" and wire.model is None
    assert html_lib.escape(g2.DELIVERY_SCOPES["cp1-model"].banner["refused"]) in text
    assert_scope_figures("cp1-model", "gap", "refused", _payload(text))
    modules = {m["module_id"]: m for m in _payload(text)["modules"]}
    for module_id in ("CP-1", "CP-MODEL"):
        assert modules[module_id]["status_word"] == "Not run"
        assert not modules[module_id]["facts"] and not modules[module_id]["claims"]
    for section in wire.sections:
        assert not section.facts and section.state != "populated"
    assert not (destination / "model").exists()
    assert not (destination / "calculation.json").exists()
    g2.verify_owner_rendered_slice(store, receipt, None, destination)


def _refused(
    tmp_path: Path, store: Path, receipt: Path, model: Path | None, name: str, code: str = ""
) -> None:
    destination = tmp_path / "out" / name
    destination.parent.mkdir(exist_ok=True)
    with pytest.raises(ValueError, match=rf"^owner_render_{code}"):
        g2.render_owner_slice(store, receipt, model, destination)
    assert not destination.exists()
    assert [p for p in destination.parent.iterdir() if p.name.startswith(".")] == []


def test_genuine_cp1_model_receipt_store_and_publication_refusals(
    tmp_path: Path, inputs: Callable[..., Any]
) -> None:
    store, receipt, model = inputs("positive")
    assert model is not None
    raw = receipt.read_bytes()
    tampered = json.loads(raw)
    tampered["participant"] = "someone-else"
    receipt.write_bytes(json.dumps(tampered, separators=(",", ":")).encode())
    _refused(tmp_path, store, receipt, model, "typed")
    receipt.write_bytes(raw)
    gap_store, _, _ = inputs("gap")
    _refused(tmp_path, gap_store, receipt, model, "foreign")
    original = (model / "model.html").read_bytes()
    (model / "model.html").write_bytes(original + b" ")
    _refused(tmp_path, store, receipt, model, "changed-model")
    (model / "model.html").write_bytes(original)
    wrong = tmp_path / "wrong-publication"
    shutil.copytree(model, wrong)
    (wrong / "receipt.json").write_bytes((wrong / "receipt.json").read_bytes() + b" ")
    _refused(tmp_path, store, receipt, wrong, "wrong-publication")
    _refused(tmp_path, store, receipt, None, "missing-publication")
    snapshot = Execution(store).read()
    pack_blob = store / "blobs" / snapshot.pack_sha256
    pack_blob.write_bytes(pack_blob.read_bytes() + b" ")
    _refused(tmp_path, store, receipt, model, "tampered-pack")
    pack_blob.write_bytes(pack_blob.read_bytes()[:-1])
    head_blob = store / "blobs" / snapshot.heads[-1].result_sha256
    head_blob.write_bytes(head_blob.read_bytes() + b" ")
    _refused(tmp_path, store, receipt, model, "tampered-blob")
    head_blob.write_bytes(head_blob.read_bytes()[:-1])
    (store / "current").write_text("0" * 64 + "\n", encoding="ascii")
    _refused(tmp_path, store, receipt, model, "tampered-pointer")


def test_genuine_cp1_model_extra_attempt_is_refused(
    tmp_path: Path, inputs: Callable[..., Any]
) -> None:
    store, receipt, model = inputs("positive")
    Execution(store).begin("CP-1")  # a further attempt on the settled store
    _refused(tmp_path, store, receipt, model, "extra-attempt")


def test_genuine_cp1_model_store_change_during_staging_and_after_rename(
    tmp_path: Path, inputs: Callable[..., Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    store, receipt, model = inputs("positive")
    real_rename = os.rename

    real_mkdtemp = tempfile.mkdtemp

    def change_then_stage(*args: Any, **kwargs: Any) -> str:
        (store / "current").write_text("0" * 64 + "\n", encoding="ascii")
        return str(real_mkdtemp(*args, **kwargs))

    good = (store / "current").read_text(encoding="ascii")
    monkeypatch.setattr(tempfile, "mkdtemp", change_then_stage)
    _refused(tmp_path, store, receipt, model, "during-staging")
    (store / "current").write_text(good, encoding="ascii")

    def rename_then_change(src: Any, dst: Any) -> None:
        real_rename(src, dst)
        (store / "current").write_text("0" * 64 + "\n", encoding="ascii")

    monkeypatch.undo()
    monkeypatch.setattr(os, "rename", rename_then_change)
    destination = tmp_path / "out" / "after-rename"
    with pytest.raises(ValueError, match=r"^owner_render_"):
        g2.render_owner_slice(store, receipt, model, destination)
    assert (destination / "report.html").is_file(), "forensic output is preserved"


def test_genuine_cp1_model_forged_html_with_rehashed_receipt_is_refused(
    tmp_path: Path, inputs: Callable[..., Any]
) -> None:
    store, receipt, model = inputs("positive")
    _, destination = _render_ok(tmp_path, store, receipt, model)
    report = destination / "report.html"
    original = report.read_text(encoding="utf-8")
    forged = original.replace("<title>", "<title>forged ", 1)
    assert forged != original
    report.write_text(forged, encoding="utf-8")
    wire = json.loads((destination / "render-receipt.json").read_text())
    wire["files"]["report.html"] = hashlib.sha256(forged.encode()).hexdigest()
    (destination / "render-receipt.json").write_text(
        json.dumps(wire, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )
    with pytest.raises(ValueError, match=r"^owner_render_"):
        g2.verify_owner_rendered_slice(store, receipt, model, destination)


def test_genuine_cp1_model_verifier_refuses_inventory_and_symlinks_read_only(
    tmp_path: Path, inputs: Callable[..., Any]
) -> None:
    store, receipt, model = inputs("positive")
    assert model is not None
    _, destination = _render_ok(tmp_path, store, receipt, model)
    before = _tree(store, model, destination)
    (destination / "extra.txt").write_text("x")
    with pytest.raises(ValueError, match=r"^owner_render_"):
        g2.verify_owner_rendered_slice(store, receipt, model, destination)
    (destination / "extra.txt").unlink()
    link = destination / "calculation.json"
    original = link.read_bytes()
    link.unlink()
    link.symlink_to(destination / "model" / "calculation.json")
    with pytest.raises(ValueError, match=r"^owner_render_"):
        g2.verify_owner_rendered_slice(store, receipt, model, destination)
    link.unlink()
    link.write_bytes(original)
    assert _tree(store, model, destination) == before


def test_genuine_cp1_model_verifier_is_deterministic_across_hash_seeds(
    tmp_path: Path, inputs: Callable[..., Any]
) -> None:
    store, receipt, model = inputs("positive")
    _, destination = _render_ok(tmp_path, store, receipt, model)
    code = (
        "import sys; from pathlib import Path; from deploy_workflow import owner_rendering as g; "
        "a = [Path(x) for x in sys.argv[1:5]]; g.verify_owner_rendered_slice(*a)"
    )
    env = {
        **os.environ,
        "PYTHONHASHSEED": "12345",
        "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT)]),
    }
    done = subprocess.run(
        [sys.executable, "-c", code, str(store), str(receipt), str(model), str(destination)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr


# ---------------------------------------------------------------- figure rule (rev 3 R3.2)
#
# Expectations are read from the frozen chart oracles under `cases/charts/`; nothing is derived
# from the payload, the facts or the product. Report references (`G#`) are the renderer's, so a
# gap is compared as the pattern `∅ G#`.

CHARTS = ROOT / "cases" / "charts"
_GAP = re.compile(r"∅ G\d+")
_REF = re.compile(r"G\d+")
# Oracle unit literals against the payload's spelling (`_CP1_FORMS`, the CR/DR chart units).
_UNITS: dict[str, tuple[str, ...]] = {
    "MULTIPLE": ("x",),
    "MILLIONS": ("US$m", "US$ m"),
    "PERCENT": ("%",),
    "x": ("x",),
    "%": ("%",),
    "US$m": ("US$m", "US$ m"),
}
# The S.1-S.4 oracle names series by raw id; the page shows the CP-1 consumer's captions
# (`report_view._CP1_CHART_LABELS`). A literal table here, so a changed caption fails the test.
_S_CAPTIONS = {
    "total_leverage_reported": "Total leverage (reported)",
    "net_leverage_reported": "Net leverage (reported)",
    "interest_coverage_reported": "Interest cover (reported)",
    "cash_closing": "Cash",
    "undrawn_rcf": "Undrawn RCF",
    "liquidity": "Total liquidity",
}
_S_QUARTER_FIELD = {"cash_closing": "cash_millions", "undrawn_rcf": "undrawn_rcf_millions"}
_S_QUARTER_FIELD |= {"liquidity": "liquidity_millions"}


@dataclass(frozen=True)
class ExpMark:
    series: str
    category: str | None
    text: str | None
    value: Decimal | None
    role: str | None = None


@dataclass(frozen=True)
class FactRef:
    """A fact the oracle names: by id, or by the (table, row field and text, value field)
    coordinate. It must resolve to exactly one fact of the module's head."""

    module_id: str
    fact_id: str | None = None
    table_id: str | None = None
    row_field: str | None = None
    row_text: str | None = None
    value_field: str | None = None


@dataclass(frozen=True)
class ExpFigure:
    fig_id: str
    placement: str | None
    kind: str | None
    title: str | None
    unit: str | None
    series: tuple[str, ...] | None
    marks: tuple[ExpMark, ...]
    unordered: bool = False
    title_prefix: bool = False  # S.4: the producer appends its basis and date to the title
    twin: tuple[tuple[str, bool, tuple[str, ...]], ...] | None = None
    reason: str | None = None
    facts: tuple[FactRef, ...] = ()


def _chart_oracle(name: str) -> Any:
    """`s14` is the S.1-S.4 oracle (`expected.json`); the others are `<name>-expected.json`."""
    path = CHARTS / ("expected.json" if name == "s14" else f"{name}-expected.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _decimal(text: str | None) -> Decimal | None:
    return None if text is None else Decimal(text)


def _norm(text: str) -> str:
    return _REF.sub("G#", text).replace("G<n>", "G#")


def _point_marks(
    points: list[dict[str, Any]], caption: dict[str, str] | None = None
) -> tuple[ExpMark, ...]:
    marks = []
    for point in points:
        raw = point["value"] if "value" in point else point["amount_exact"]
        series = point["series"] if caption is None else caption[point["series"]]
        marks.append(
            ExpMark(series, point["category"], point["shown"], _decimal(raw), point.get("role"))
        )
    return tuple(marks)


def _point_facts(module_id: str, points: list[dict[str, Any]]) -> tuple[FactRef, ...]:
    refs: list[FactRef] = []
    for point in points:
        if "fact_id" in point:
            refs.append(FactRef(module_id, fact_id=point["fact_id"]))
        for companion in point.get("companion_fact_ids", ()):
            refs.append(FactRef(module_id, fact_id=companion))
        coordinate = point.get("fact_coordinate")
        if coordinate is not None:
            refs.append(
                FactRef(
                    coordinate["module"],
                    table_id=coordinate["table_id"],
                    row_field=coordinate["row_key"]["field"],
                    row_text=coordinate["row_key"]["text"],
                    value_field=coordinate["value_field"],
                )
            )
    return tuple(refs)


def _twin_rows(rows: list[dict[str, Any]]) -> tuple[tuple[str, bool, tuple[str, ...]], ...]:
    out = []
    for row in rows:
        if "cells" in row:
            out.append((row["label"], False, tuple(row["cells"])))
        else:  # label_parts is the label's prefix; companion parts are added at run time
            out.append((row["label_parts"][0], True, (row["cell"],)))
    return tuple(out)


def _s_figures() -> tuple[ExpFigure, ...]:
    """S.1-S.4 on the fields the oracle pins (R3.2): ids, title, unit, series, one mark per
    quarter and series with the oracle amount or a gap, S.4 from the maturity wall rows."""
    oracle = _chart_oracle("s14")
    quarters = oracle["quarters"]
    series_of = oracle["chart_series"]
    figures: list[ExpFigure] = []
    for fig_id in ("S.1", "S.2", "S.3"):
        spec = series_of[fig_id]
        names = spec["series"]
        marks = []
        for quarter in quarters:
            for name in names:
                if name in _S_QUARTER_FIELD:
                    value = _decimal(quarter[_S_QUARTER_FIELD[name]])
                else:
                    value = _decimal(quarter[name]["amount"])
                marks.append(ExpMark(_S_CAPTIONS[name], None, None, value))
        figures.append(
            ExpFigure(
                fig_id,
                "above",
                None,
                spec["title"],
                spec["unit"],
                tuple(_S_CAPTIONS[n] for n in names),
                tuple(marks),
                unordered=True,
                facts=(),
            )
        )
    wall = oracle["current_maturity_wall"]
    figures.append(
        ExpFigure(
            "S.4",
            "above",
            None,
            series_of["S.4"]["title"],
            series_of["S.4"]["unit"],
            None,
            tuple(ExpMark("", None, None, _decimal(row["outstanding_millions"])) for row in wall),
            unordered=True,
            title_prefix=True,
        )
    )
    return tuple(figures)


def _s5_figures() -> tuple[ExpFigure, ...]:
    oracle = _chart_oracle("s5")
    spec = oracle["chart_series"][0]
    captions = spec["series_captions"]
    return (
        ExpFigure(
            spec["fig_id"],
            oracle["render"]["figures"][0]["placement"],
            spec["kind"],
            spec["title"],
            spec["unit"],
            tuple(captions[name] for name in spec["series"]),
            _point_marks(spec["points"], captions),
            twin=_twin_rows(oracle["table_twin"]["S.5"]["rows"]),
            facts=_point_facts("CP-1", spec["points"]),
        ),
    )


def _rv3_figures(case: str) -> tuple[ExpFigure, ...]:
    oracle = _chart_oracle("rv3")
    if case not in ("positive", "gap"):
        return ()
    placements = {f["fig_id"]: f["placement"] for f in oracle["render"]["figures"]}
    data = oracle["cases"][case]
    out = []
    for spec in data["chart_series"]:
        out.append(
            ExpFigure(
                spec["fig_id"],
                placements[spec["fig_id"]],
                spec["kind"],
                spec["title"],
                spec["unit"],
                tuple(spec["series"]),
                _point_marks(spec["points"]),
                twin=_twin_rows(data["table_twin"][spec["panel"]]["rows"]),
                facts=_point_facts("CP-1C", spec["points"]),
            )
        )
    return tuple(out)


def _cr1_figures(case: str) -> tuple[ExpFigure, ...]:
    oracle = _chart_oracle("cr1")
    key = "gap" if case == "gap_false_same_definition" else case
    data = oracle["cases"][key]
    placement = oracle["render"]["figures"][0]["placement"]
    (spec,) = data["chart_series"]
    return (
        ExpFigure(
            spec["fig_id"],
            placement,
            spec["kind"],
            spec["title"],
            spec["unit"],
            tuple(spec["series"]),
            _point_marks(spec["points"]),
            twin=_twin_rows(data["table_twin"]["CR.1"]["rows"]),
            facts=_point_facts("CP-4", spec["points"]),
        ),
    )


def _cr2_figures(case: str) -> tuple[ExpFigure, ...]:
    oracle = _chart_oracle("cr2")
    spec = oracle["chart_series"]["CR.2"][case]
    placement = oracle["render"]["covenant_refinancing"]["figure"]["placement"]
    return (
        ExpFigure(
            spec["fig_id"],
            placement,
            spec["kind"],
            spec["title"],
            spec["unit"],
            tuple(spec["series"]),
            _point_marks(spec["points"]),
            twin=_twin_rows(oracle["table_twins"][case]["rows"]),
            facts=_point_facts("CP-2D", spec["points"]),
        ),
    )


def _cr3_figures(case: str) -> tuple[ExpFigure, ...]:
    oracle = _chart_oracle("cr3")
    spec = oracle["chart_series"]["CR.3"][case]
    placement = oracle["render"]["covenant_refinancing"]["figure"]["placement"]
    return (
        ExpFigure(
            spec["fig_id"],
            placement,
            spec["kind"],
            spec["title"],
            spec["unit"],
            tuple(spec["series"]),
            _point_marks(spec["points"]),
            twin=_twin_rows(oracle["table_twins"][case]["rows"]),
            facts=_point_facts("CP-3C", spec["points"]),
        ),
    )


def _dr2_figures(case: str) -> tuple[ExpFigure, ...]:
    oracle = _chart_oracle("dr2")
    spec = oracle["chart_series"]["DR.2"][case]
    placement = oracle["render"]["distressed_restructuring"]["figure"]["placement"]
    return (
        ExpFigure(
            spec["fig_id"],
            placement,
            spec["kind"],
            spec["title"],
            spec["unit"],
            tuple(spec["series"]),
            _point_marks(spec["points"]),
            twin=_twin_rows(oracle["table_twins"][case]["rows"]),
            facts=_point_facts("CP-4C", spec["points"]),
        ),
    )


def _dr345_figures(case: str) -> tuple[ExpFigure, ...]:
    oracle = _chart_oracle("dr345")
    placements = {
        f["fig_id"]: f["placement"] for f in oracle["render"]["distressed_restructuring"]["figures"]
    }
    out = []
    for fig_id in ("DR.3", "DR.4", "DR.5"):
        spec = oracle["chart_series"]["DR.3-5"][case][fig_id]
        out.append(
            ExpFigure(
                fig_id,
                placements[fig_id],
                spec["kind"],
                spec["title"],
                spec["unit"],
                tuple(spec["series"]),
                _point_marks(spec["points"]),
                twin=_twin_rows(oracle["table_twins"][case][fig_id]["rows"]),
                facts=_point_facts("CP-4C", spec["points"]),
            )
        )
    return tuple(out)


def _dr6_figures(case: str) -> tuple[ExpFigure, ...]:
    oracle = _chart_oracle("dr6")
    frame = oracle["chart_series"]["DR.6"]
    render = oracle["render"]["distressed_restructuring"]
    data = oracle["cases"][case]
    assert data["marks"] == [] and frame["points"] == []
    return (
        ExpFigure(
            frame["fig_id"],
            render["figure"]["placement"],
            render["figure"]["chart_kind"],
            frame["title"],
            None,
            (),
            (),
            twin=(),
            reason=data["frame_reason"],
        ),
    )


# (scope, block) -> loader of a case's expected figures. A case a loader does not cover, and
# every block not listed here, expects `()` (R3.2: no chart oracle, or the oracle draws nothing).
_NO_FIGURE_CASES: dict[tuple[str, str], frozenset[str]] = {
    ("cp1-model", "model-chart-strip"): frozenset({"gap"}),
    ("cp1c-fp03-peers", "peer-positioning"): frozenset({"no_peers", "refused"}),
}
_FIGURE_SOURCES: dict[tuple[str, str], Callable[[str], tuple[ExpFigure, ...]]] = {
    ("cp1-model", "model-chart-strip"): lambda case: _s_figures(),
    ("cp1-model", "financials-credit-metrics"): lambda case: _s5_figures(),
    ("cp1c-fp03-peers", "peer-positioning"): _rv3_figures,
    ("cp4-fp04-covenants", "covenant-tests-headroom"): _cr1_figures,
    ("cp2d-fp04-liquidity", "liquidity-runway"): _cr2_figures,
    ("cp3c-fp04-refinancing", "funding-gap"): _cr3_figures,
    ("cp4c-fp05-recovery", "recovery-by-class"): _dr2_figures,
    ("cp4c-fp05-recovery", "value-allocation-claims"): _dr345_figures,
    ("cp2h-fp05-ratings", "rating-triggers"): _dr6_figures,
}


def expected_figures(scope_id: str, block_id: str, case: str) -> tuple[ExpFigure, ...]:
    loader = _FIGURE_SOURCES.get((scope_id, block_id))
    if loader is None or case in _NO_FIGURE_CASES.get((scope_id, block_id), frozenset()):
        return ()
    return loader(case)


def _facts_of(modules: list[dict[str, Any]], module_id: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = next(m["facts"] for m in modules if m["module_id"] == module_id)
    return facts


def _resolve(ref: FactRef, modules: list[dict[str, Any]]) -> None:
    facts = _facts_of(modules, ref.module_id)
    if ref.fact_id is not None:
        assert sum(f["fact_id"] == ref.fact_id for f in facts) == 1, ref
        return
    rows = {
        f["row_id"]
        for f in facts
        if f["table_id"] == ref.table_id
        and f["field"] == ref.row_field
        and f.get("text") == ref.row_text
    }
    assert len(rows) == 1, ref
    (row,) = rows
    hits = [
        f
        for f in facts
        if f["table_id"] == ref.table_id and f["row_id"] == row and f["field"] == ref.value_field
    ]
    assert len(hits) == 1, ref


def _accepted_units(unit: str | None) -> tuple[str, ...] | None:
    return None if unit is None else _UNITS.get(unit, (unit,))


def _mark_value(mark: dict[str, Any]) -> Decimal | None:
    return None if mark["value"] is None else Decimal(str(mark["value"]))


def _marks_of(chart: dict[str, Any]) -> list[dict[str, Any]]:
    marks: list[dict[str, Any]] = chart["marks"]
    return marks


def _figure_equals(got: dict[str, Any], want: ExpFigure, modules: list[dict[str, Any]]) -> None:
    chart = got["chart"]
    assert got["fig_id"] == want.fig_id
    if want.placement is not None:
        assert got["placement"] == want.placement, want.fig_id
    if want.kind is not None:
        assert chart["kind"] == want.kind, want.fig_id
    if want.title is not None:
        if want.title_prefix:
            assert got["title"].startswith(want.title), want.fig_id
        else:
            assert got["title"] == want.title, want.fig_id
    units = _accepted_units(want.unit)
    if units is not None:
        assert chart["unit"] in units, (want.fig_id, chart["unit"])
    if want.series is not None:
        assert tuple(chart["series"]) == want.series, want.fig_id
    marks = _marks_of(chart)
    assert len(marks) == len(want.marks), want.fig_id
    if want.unordered:  # S.1-S.4: order is the producer's; series and values are the oracle's
        keyed = want.marks[0].series != ""
        have = sorted(
            (m["series"] if keyed else "", m["value"] is None, _mark_value(m) or Decimal(0))
            for m in marks
        )
        need = sorted((m.series, m.value is None, m.value or Decimal(0)) for m in want.marks)
        assert have == need, want.fig_id
    else:
        for mark, exp in zip(marks, want.marks, strict=True):
            assert mark["series"] == exp.series, (want.fig_id, mark)
            assert mark["label"] == exp.category, (want.fig_id, mark)
            assert _norm(mark["text"]) == exp.text, (want.fig_id, mark)
            assert _mark_value(mark) == exp.value, (want.fig_id, mark)
            if exp.role is not None:
                assert mark["role"] == exp.role, (want.fig_id, mark)
    for mark in marks:
        if mark["value"] is None:  # a gap is a reference, never a zero
            assert mark["ref_id"] is not None and _REF.fullmatch(mark["ref_id"]), mark
            assert mark["text"] == f"∅ {mark['ref_id']}", mark
            assert _GAP.fullmatch(mark["text"]), mark
        if mark["ref_id"] is not None:
            assert f'data-ref="{mark["ref_id"]}"' in chart["svg"], mark
    twin = chart["table_twin"]
    cells = [[cell["text"] for cell in row["cells"]] for row in twin["rows"]]
    assert [text for row in cells for text in row] == [m["text"] for m in marks]
    if want.twin is not None:
        assert len(twin["rows"]) == len(want.twin), want.fig_id
        for row, (label, prefix, texts) in zip(twin["rows"], want.twin, strict=True):
            assert row["label"].startswith(label) if prefix else row["label"] == label, (
                want.fig_id,
                row,
            )
            assert tuple(_norm(cell["text"]) for cell in row["cells"]) == texts, (want.fig_id, row)
    if want.reason is not None:
        # The frame reason is the oracle text; where facts are missing the renderer appends the
        # `∅ G<n>` of the cited gaps (dr6 oracle: frame_texts.per_case.<case>.reference).
        reason = _norm(chart["reason"] or "")
        assert reason.startswith(_norm(want.reason)), want.fig_id
        assert not re.sub(r"∅ G#|[\s,;·.()]", "", reason[len(_norm(want.reason)) :]), want.fig_id
    for ref in want.facts:
        _resolve(ref, modules)


def assert_figures_equal_oracle(
    block: dict[str, Any], want: tuple[ExpFigure, ...], modules: list[dict[str, Any]]
) -> None:
    """The block's figures are exactly the oracle's, in order: a missing, extra, moved or
    perturbed figure fails."""
    got = block["figures"]
    assert [f["fig_id"] for f in got] == [f.fig_id for f in want], block["block_id"]
    for figure, expected in zip(got, want, strict=True):
        _figure_equals(figure, expected, modules)


# Every (scope, block, case) the rev 3 table lists, and the module whose facts the refs resolve in.
FIGURE_CASES: tuple[tuple[str, str, str], ...] = (
    ("cp1-model", "model-chart-strip", "positive"),
    ("cp1-model", "financials-credit-metrics", "positive"),
    ("cp1c-fp03-peers", "peer-positioning", "positive"),
    ("cp1c-fp03-peers", "peer-positioning", "gap"),
    ("cp4-fp04-covenants", "covenant-tests-headroom", "positive"),
    ("cp4-fp04-covenants", "covenant-tests-headroom", "gap"),
    ("cp4-fp04-covenants", "covenant-tests-headroom", "gap_false_same_definition"),
    ("cp2d-fp04-liquidity", "liquidity-runway", "positive"),
    ("cp2d-fp04-liquidity", "liquidity-runway", "long_horizon"),
    ("cp2d-fp04-liquidity", "liquidity-runway", "gap_minimum_cash"),
    ("cp3c-fp04-refinancing", "funding-gap", "positive"),
    ("cp3c-fp04-refinancing", "funding-gap", "gap_minimum_cash"),
    ("cp3c-fp04-refinancing", "funding-gap", "gap_no_repricing"),
    ("cp4c-fp05-recovery", "recovery-by-class", "positive"),
    ("cp4c-fp05-recovery", "recovery-by-class", "gap"),
    ("cp4c-fp05-recovery", "value-allocation-claims", "positive"),
    ("cp4c-fp05-recovery", "value-allocation-claims", "gap"),
    ("cp2h-fp05-ratings", "rating-triggers", "positive"),
    ("cp2h-fp05-ratings", "rating-triggers", "gap"),
)


def _fixture_modules(want: tuple[ExpFigure, ...]) -> list[dict[str, Any]]:
    """Head facts the oracle's refs resolve in: one fact per named id, and per coordinate the
    row-key fact and the value fact. Built from the oracle's own coordinates."""
    modules: dict[str, list[dict[str, Any]]] = {}
    for figure in want:
        for ref in figure.facts:
            facts = modules.setdefault(ref.module_id, [])
            if ref.fact_id is not None:
                facts.append({"fact_id": ref.fact_id, "table_id": "t", "row_id": "r", "field": "f"})
            else:
                row = f"row-{ref.row_text}"
                facts.append(
                    {
                        "fact_id": f"{row}-key",
                        "table_id": ref.table_id,
                        "row_id": row,
                        "field": ref.row_field,
                        "text": ref.row_text,
                    }
                )
                facts.append(
                    {
                        "fact_id": f"{row}-{ref.value_field}",
                        "table_id": ref.table_id,
                        "row_id": row,
                        "field": ref.value_field,
                    }
                )
    modules.setdefault("CP-0", [])
    return [{"module_id": k, "facts": _dedupe(v)} for k, v in modules.items()]


def _dedupe(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for fact in facts:
        seen.setdefault((fact["fact_id"], fact["table_id"], fact["row_id"], fact["field"]), fact)
    return list(seen.values())


def _payload_block(want: tuple[ExpFigure, ...]) -> dict[str, Any]:
    """A `report-data` block built from the oracle: what a correct page must carry."""
    figures = []
    number = 20
    for figure in want:
        marks, refs = [], []
        for mark in figure.marks:
            gap = mark.value is None
            ref = None
            if gap:
                number += 1
                ref = f"G{number}"
                refs.append(ref)
            text = f"∅ {ref}" if gap else (mark.text if mark.text is not None else str(mark.value))
            marks.append(
                {
                    "series": mark.series,
                    "label": mark.category,
                    "text": text,
                    "ref_id": ref,
                    "value": None if gap else str(mark.value),
                    "role": mark.role or "value",
                }
            )
        texts = [m["text"] for m in marks]
        rows: list[dict[str, Any]] = []
        if figure.twin is not None:
            cursor = 0
            for label, prefix, cells in figure.twin:
                taken = texts[cursor : cursor + len(cells)]
                cursor += len(cells)
                rows.append(
                    {
                        "label": label + (" · extra" if prefix else ""),
                        "cells": [{"text": t} for t in taken],
                    }
                )
        else:
            rows = [{"label": "row", "cells": [{"text": t}]} for t in texts]
        figures.append(
            {
                "fig_id": figure.fig_id,
                "placement": figure.placement or "above",
                "title": figure.title or "t",
                "chart": {
                    "kind": figure.kind or "line",
                    "unit": (_accepted_units(figure.unit) or ("u",))[0],
                    "series": list(figure.series or ()),
                    "reason": figure.reason,
                    "marks": marks,
                    "table_twin": {"rows": rows},
                    "svg": "<svg>" + "".join(f'<g data-ref="{r}"/>' for r in refs) + "</svg>",
                },
            }
        )
    return {"block_id": "b", "figures": figures}


@pytest.mark.parametrize(("scope_id", "block_id", "case"), FIGURE_CASES)
def test_fast_figure_rule_accepts_the_page_the_oracle_describes(
    scope_id: str, block_id: str, case: str
) -> None:
    want = expected_figures(scope_id, block_id, case)
    assert want, "a listed chart row expects at least one figure"
    assert_figures_equal_oracle(_payload_block(want), want, _fixture_modules(want))


@pytest.mark.parametrize(
    ("scope_id", "block_id", "case"),
    [
        ("cp1c-fp03-peers", "peer-positioning", "no_peers"),
        ("cp1c-fp03-peers", "peer-positioning", "refused"),
        ("cp1-model", "model-chart-strip", "gap"),
        ("cp1-model", "capital-structure", "positive"),
        ("cp2d-fp04-liquidity", "funding-gap", "positive"),
        ("s1a-credit-snapshot", "key-findings", "positive"),
    ],
)
def test_fast_blocks_without_a_chart_oracle_expect_no_figure(
    scope_id: str, block_id: str, case: str
) -> None:
    assert expected_figures(scope_id, block_id, case) == ()
    assert_figures_equal_oracle({"block_id": block_id, "figures": []}, (), [])
    extra = _payload_block(
        expected_figures("cp4-fp04-covenants", "covenant-tests-headroom", "positive")
    )
    with pytest.raises(AssertionError):
        assert_figures_equal_oracle(extra, (), [])


def _perturbed(
    kind: str, block: dict[str, Any], want: tuple[ExpFigure, ...]
) -> tuple[dict[str, Any], tuple[ExpFigure, ...]]:
    block = json.loads(json.dumps(block))
    figure = block["figures"][0]
    marks = figure["chart"]["marks"]
    target = next(m for m in marks if m["value"] is not None)
    if kind == "text":
        target["text"] += "0"
    elif kind == "value":
        target["value"] = str(Decimal(target["value"]) + 1)
    elif kind == "ref":
        gap = next((m for m in marks if m["value"] is None), None)
        if gap is None:
            target["ref_id"] = "G1"  # a ref the svg does not carry
        else:
            gap["ref_id"] = "G999"
    elif kind == "zero_fill":
        target["value"], target["ref_id"] = None, None
    elif kind == "moved":
        figure["fig_id"] = "X.9"
    elif kind == "extra":
        block["figures"].append(json.loads(json.dumps(figure)) | {"fig_id": "X.8"})
    elif kind == "missing":
        block["figures"] = block["figures"][:-1]
    return block, want


@pytest.mark.parametrize("kind", ["text", "value", "ref", "zero_fill", "moved", "extra", "missing"])
@pytest.mark.parametrize(
    ("scope_id", "block_id", "case"),
    [
        ("cp4-fp04-covenants", "covenant-tests-headroom", "positive"),
        ("cp4c-fp05-recovery", "recovery-by-class", "positive"),
        ("cp1-model", "financials-credit-metrics", "positive"),
        ("cp1-model", "model-chart-strip", "positive"),
    ],
)
def test_fast_figure_rule_fails_a_perturbed_page(
    kind: str, scope_id: str, block_id: str, case: str
) -> None:
    want = expected_figures(scope_id, block_id, case)
    block, want = _perturbed(kind, _payload_block(want), want)
    with pytest.raises(AssertionError):
        assert_figures_equal_oracle(block, want, _fixture_modules(want))


def test_fast_figure_rule_fails_an_unresolvable_or_ambiguous_fact_ref() -> None:
    want = expected_figures("cp4-fp04-covenants", "covenant-tests-headroom", "positive")
    block = _payload_block(want)
    modules = _fixture_modules(want)
    modules[0]["facts"] = modules[0]["facts"][1:]  # a named fact is absent
    with pytest.raises(AssertionError):
        assert_figures_equal_oracle(block, want, modules)
    modules = _fixture_modules(want)
    modules[0]["facts"] = [*modules[0]["facts"], dict(modules[0]["facts"][0])]  # named twice
    with pytest.raises(AssertionError):
        assert_figures_equal_oracle(block, want, modules)


def test_fast_every_figure_oracle_pointer_exists() -> None:
    """A missing pointer fails here and is never skipped (R3.2 acceptance 4)."""
    for name, pointers in {
        "s14": ["/chart_series", "/quarters", "/q4_trailing_basis", "/current_maturity_wall"],
        "s5": ["/render", "/chart_series/0", "/table_twin/S.5"],
        "rv3": ["/render", "/cases/positive/chart_series", "/cases/gap/chart_series"],
        "cr1": ["/render", "/cases/positive/chart_series", "/cases/gap/chart_series"],
        "cr2": [
            "/render/covenant_refinancing",
            "/chart_series/CR.2/positive",
            "/table_twins/positive",
        ],
        "cr3": [
            "/render/covenant_refinancing",
            "/chart_series/CR.3/positive",
            "/chart_series/CR.3/gap_minimum_cash",
            "/chart_series/CR.3/gap_no_repricing",
            "/table_twins/positive",
        ],
        "dr2": ["/render/distressed_restructuring", "/chart_series/DR.2/gap", "/table_twins/gap"],
        "dr345": [
            "/render/distressed_restructuring",
            "/chart_series/DR.3-5/gap/DR.5",
            "/table_twins/gap",
        ],
        "dr6": [
            "/render/distressed_restructuring",
            "/chart_series/DR.6",
            "/render/distressed_restructuring/frame_texts/per_case/gap",
        ],
    }.items():
        for pointer in pointers:
            assert _pointer(_chart_oracle(name), pointer) is not None, (name, pointer)


# The comparator against the product's own figures (the repository's real chart drivers, each
# already pinned to its oracle by its own test file). Page payloads are rebuilt the way the core
# renderer builds them, so this is the figure rule on genuine `build` output, not on stand-ins.

chart_case = test_cp1_chart_render.chart_case


def _modules_of(view: Any) -> list[dict[str, Any]]:
    return [
        {"module_id": m.module_id, "facts": [f.model_dump(mode="json") for f in m.facts]}
        for m in view.modules
    ]


def _real_block(report: Any, block_id: str) -> dict[str, Any]:
    block = next(b for b in report.blocks if b.block_id == block_id)
    payload: dict[str, Any] = g2._expected_block_payload(block)
    return payload


def _real_check(
    scope_id: str, block_id: str, case: str, view: Any, report: Any, *, perturb: bool = True
) -> None:
    payload = _real_block(report, block_id)
    want = expected_figures(scope_id, block_id, case)
    assert want
    assert_figures_equal_oracle(payload, want, _modules_of(view))
    if perturb:  # the same real page with one mark's text changed fails
        mark = next(m for m in payload["figures"][0]["chart"]["marks"] if m["value"] is not None)
        mark["text"] += "0"
        with pytest.raises(AssertionError):
            assert_figures_equal_oracle(payload, want, _modules_of(view))


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_fast_figure_rule_on_real_cr1_and_rv3_pages(case: str) -> None:
    cr1 = importlib.import_module("test_chart_render_cr1")
    rv3 = importlib.import_module("test_chart_render_rv3")

    view, report = cr1._report(case)
    _real_check("cp4-fp04-covenants", "covenant-tests-headroom", case, view, report)
    view, report = rv3._report(case)
    _real_check("cp1c-fp03-peers", "peer-positioning", case, view, report)


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_fast_figure_rule_on_real_dr2_and_dr345_pages(case: str) -> None:
    support = importlib.import_module("chart_dr_support")

    view = support.view_with(support.composer_module(case), case)
    report = support.report_of(view)
    _real_check("cp4c-fp05-recovery", "recovery-by-class", case, view, report)
    _real_check("cp4c-fp05-recovery", "value-allocation-claims", case, view, report)


@pytest.mark.parametrize("case", ["positive", "long_horizon", "gap_minimum_cash"])
def test_fast_figure_rule_on_real_cr2_pages(case: str) -> None:
    wiring = importlib.import_module("chart_wiring_c")

    view = wiring.cp2d_view(case)
    _real_check("cp2d-fp04-liquidity", "liquidity-runway", case, view, wiring.report_of(view))
    funding = _real_block(wiring.report_of(view), "funding-gap")
    assert (
        funding["figures"] == []
        and expected_figures("cp2d-fp04-liquidity", "funding-gap", case) == ()
    )


@pytest.mark.parametrize("case", ["positive", "gap_minimum_cash", "gap_no_repricing"])
def test_fast_figure_rule_on_real_cr3_pages(case: str) -> None:
    wiring = importlib.import_module("chart_wiring_c")

    view = wiring.cp3c_view(case)
    _real_check("cp3c-fp04-refinancing", "funding-gap", case, view, wiring.report_of(view))
    for block_id in ("refinancing-paths", "lme-creditor-exposure"):
        assert _real_block(wiring.report_of(view), block_id)["figures"] == []
        assert expected_figures("cp3c-fp04-refinancing", block_id, case) == ()


def test_fast_funding_gap_facts_are_members_of_the_cp2d_or_cp3c_head() -> None:
    """Lease R2.8 item 7: each bound `funding-gap` fact comes from its own head's facts."""
    modules = [
        {"module_id": "CP-2D", "facts": [{"fact_id": "T2E.5.r01.c1"}]},
        {"module_id": "CP-3C", "facts": [{"fact_id": "T3D.1.r01.c6"}]},
    ]
    good = [("CP-2D", "T2E.5.r01.c1"), ("CP-3C", "T3D.1.r01.c6")]
    assert_funding_gap_heads("cp3c-fp04-refinancing", good, modules)
    assert_funding_gap_heads("cp2d-fp04-liquidity", good[:1], modules)
    for scope_id, bad in (
        ("cp3c-fp04-refinancing", good[:1]),  # T3D.1 is bound here: CP-3C must contribute
        ("cp3c-fp04-refinancing", [*good, ("CP-3C", "T3D.1.r09.c9")]),  # not in the head
        ("cp3c-fp04-refinancing", [*good, ("CP-2D", "T3D.1.r01.c6")]),  # the other head's fact
        ("cp3c-fp04-refinancing", [*good, ("CP-4", "T4.1.r01.c1")]),  # not a funding-gap head
        ("cp2d-fp04-liquidity", good),  # CP-3C is not in this run
        ("cp2d-fp04-liquidity", []),
    ):
        with pytest.raises(AssertionError):
            assert_funding_gap_heads(scope_id, bad, modules)


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_fast_figure_rule_on_real_dr6_pages(case: str, tmp_path: Path) -> None:
    dr6 = importlib.import_module("test_chart_render_dr6")

    store, _pack, _attempt, _done = dr6.connect.settled(tmp_path, case)
    view = store.view()
    _real_check(
        "cp2h-fp05-ratings", "rating-triggers", case, view, dr6._report(view), perturb=False
    )


def test_fast_figure_rule_on_real_s5_page() -> None:
    s5 = importlib.import_module("test_chart_render_s5")
    fixture = importlib.import_module("test_financial_series").fixture

    view = s5._view(fixture())
    pathway = next(p for p in pathways() if p.id == view.run.pathway)
    report = build(view, pathway, SHIPPED_MAPS)
    _real_check("cp1-model", "financials-credit-metrics", "positive", view, report)


def test_fast_figure_rule_on_the_real_s1_to_s4_strip(chart_case: Any) -> None:
    cp1 = importlib.import_module("test_cp1_chart_render")

    view, _, _ = chart_case
    _real_check("cp1-model", "model-chart-strip", "positive", view, cp1._report(view))


def assert_scope_figures(scope_id: str, case: str, outcome: str, payload: dict[str, Any]) -> None:
    """Every assigned block's figures equal its oracle expectation, or `()` (R3.2). A refused
    page draws no figure."""
    blocks = {b["block_id"]: b for b in payload["report"]["blocks"]}
    for section_id in g2.DELIVERY_SCOPES[scope_id].sections:
        want = () if outcome == "refused" else expected_figures(scope_id, section_id, case)
        assert_figures_equal_oracle(blocks[section_id], want, payload["modules"])


# Heads whose facts the `funding-gap` block binds (lease R2.8 item 7): CP-2D, and CP-3C for T3D.1.
_FUNDING_GAP_HEADS = {
    "cp2d-fp04-liquidity": frozenset({"CP-2D"}),
    "cp3c-fp04-refinancing": frozenset({"CP-2D", "CP-3C"}),
}


def assert_funding_gap_heads(
    scope_id: str, bound: list[tuple[str, str]], modules: list[dict[str, Any]]
) -> None:
    """`bound` is the section's (module_id, fact_id) pairs. Every one is a member of the facts of
    its own head in the page payload, and every head the scope names contributes."""
    heads = _FUNDING_GAP_HEADS[scope_id]
    assert {module_id for module_id, _ in bound} == heads, scope_id
    for module_id, fact_id in bound:
        assert sum(f["fact_id"] == fact_id for f in _facts_of(modules, module_id)) == 1, (
            module_id,
            fact_id,
        )


# ---------------------------------------------------------------- deferred scopes (heavy)


def _cell_ok(payload_cell: dict[str, Any], oracle_cell: dict[str, Any]) -> None:
    if oracle_cell["state"] == "known" and oracle_cell.get("shown") is not None:
        assert payload_cell["text"] == oracle_cell["shown"]
    else:  # gap spelling `∅ G#` / `∅ G# n.m.`, numbered by the renderer (oracle cell_notation)
        assert re.fullmatch(r"∅ G\d+( n\.m\.)?", payload_cell["text"]), payload_cell


def _register_ok(payload_rows: list[dict[str, Any]], oracle_rows: list[dict[str, Any]]) -> None:
    assert [r["label"] for r in payload_rows] == [r["label"] for r in oracle_rows]
    for got, want in zip(payload_rows, oracle_rows, strict=True):
        assert len(got["cells"]) == len(want["cells"])
        for got_cell, want_cell in zip(got["cells"], want["cells"], strict=True):
            _cell_ok(got_cell, want_cell)


def _line_text(line: dict[str, Any]) -> str:
    return "".join(run["text"] for run in line["runs"])


def assert_block_equals_oracle(block: dict[str, Any], oracle: dict[str, Any]) -> None:
    """title, owner, kind, state, numbered, summary, tabs and rows/lines against one oracle block.
    The gap spelling is a pattern; G numbers are the renderer's."""
    for key in ("title", "owner", "kind", "state", "numbered", "summary"):
        if key in oracle:
            assert block[key] == oracle[key], key
    if "primary" in oracle:
        assert block["tab_label"] == oracle["primary"]["tab"]
        _register_ok(block["rows"], oracle["primary"]["rows"])
    for got, want in zip(block["tabs"], oracle.get("tabs", []), strict=False):
        assert got["label"] == want["tab"]
        if "rows" in want:
            _register_ok(got["rows"], want["rows"])
    if "lines" in oracle:
        assert [_line_text(line) for line in block["lines"]] == [
            line["text"] for line in oracle["lines"]
        ]


def _s1a(case: str, root: Path) -> tuple[Path, Path, Path | None]:
    store, receipt, publication = importlib.import_module("s1a_runs").s1a_closed(case, root)
    return Path(store), Path(receipt), Path(publication)


def _wrap(module: str, function: str) -> Callable[[str, Path], tuple[Path, Path, Path | None]]:
    def run(case: str, root: Path) -> tuple[Path, Path, Path | None]:
        built = getattr(importlib.import_module(module), function)(case, root)
        return built[0], built[1], built[2] if len(built) > 2 else None

    return run


def _cp8(case: str, root: Path) -> tuple[Path, Path, Path | None]:
    driver = importlib.import_module("cp8_runs")
    workflow, _ = driver.start(case, root) if case == "no_record" else driver.cp8_closed(case, root)
    workflow.write_receipt(root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json", None


def _cp3c(case: str, root: Path) -> tuple[Path, Path, Path | None]:
    driver = importlib.import_module("cp3c_runs")
    template, _pack = driver.reach_cp2d(root / "template")
    store, receipt = driver.cp3c_closed(case, root, template)
    return Path(store), Path(receipt), None


Adapter = Callable[[str, Path], tuple[Path, Path, Path | None]]
# scope -> (driver adapter, complete cases, refused case or None, blocked cases the driver offers)
DEFERRED: dict[str, tuple[Adapter, tuple[str, ...], str | None, tuple[str, ...]]] = {
    "s1a-credit-snapshot": (_s1a, ("positive", "gap"), None, ()),
    "cp3-fp01-relative-value": (_wrap("cp3_cp6_runs", "cp3_closed"), ("positive", "gap"), None, ()),
    "cp1c-fp03-peers": (
        _wrap("cp1c_runs", "cp1c_closed"),
        ("positive", "gap", "no_peers"),
        "refused",
        ("blocked",),
    ),
    "cp3d-fp03-market": (
        _wrap("cp3d_runs", "cp3d_closed"),
        ("positive", "gap_no_recovery", "gap_no_market"),
        None,
        (),
    ),
    "cp1d-fp02-quality": (
        _wrap("cp1d_runs", "cp1d_closed"),
        ("positive", "statements_only", "gap"),
        None,
        (),
    ),
    "cp2a-fp05-downside": (
        _wrap("cp2a_runs", "cp2a_closed"),
        ("positive", "gap"),
        "refused",
        ("blocked",),
    ),
    "cp2g-fp05-forward": (
        _wrap("cp2g_runs", "cp2g_closed"),
        ("positive",),
        None,
        ("cp1d_blocked",),
    ),
    "cp2g-fp05-forward-gap": (
        _wrap("cp2g_runs", "cp2g_closed"),
        ("gap",),
        "refused",
        ("blocked", "cp2a_blocked"),
    ),
    "cp2h-fp05-ratings": (
        _wrap("cp2h_runs", "cp2h_closed"),
        ("positive", "gap"),
        "refused",
        ("blocked", "cp2g_blocked"),
    ),
    "cp4c-fp05-recovery": (
        _wrap("cp4c_runs", "cp4c_closed"),
        ("positive", "gap"),
        "refused",
        ("blocked", "cp2g_blocked"),
    ),
    "cp3c-fp04-refinancing": (
        _cp3c,
        ("positive", "gap_minimum_cash", "gap_no_repricing"),
        None,
        (),
    ),
    "cp4-fp04-covenants": (
        _wrap("cp4_runs", "cp4_closed"),
        ("positive", "gap", "gap_false_same_definition"),
        None,
        (),
    ),
    "cp8-fp01-what-changed": (_cp8, ("positive", "no_outcome"), "no_record", ()),
    "slice-cp2e-sensitivity": (
        _wrap("cp2e_runs", "cp2e_closed"),
        ("positive", "gap_no_facility_schedule"),
        None,
        (),
    ),
    "slice-cpdr-research": (
        _wrap("cpdr_runs", "cpdr_closed"),
        ("partial", "unresolved", "empty_agenda"),
        None,
        (),
    ),
    "slice-cpl10-screen": (_wrap("cpl10_runs", "cpl10_closed"), ("positive",), None, ()),
}


def _oracle_case_key(scope_id: str, case: str) -> str:
    if scope_id.startswith("s1a") and case == "gap":
        return "gap_business_without_ownership_transaction"
    return case


def _assert_cp3c_blocks(blocks: dict[str, Any]) -> None:
    """The three assigned blocks against the frozen oracles: `refinancing-paths` and
    `lme-creditor-exposure` from `cp3c-owner#/fp04_render`, `funding-gap` (T3D.1 moved there by
    the Q-C2 wiring) from `cr3-expected.json#/render/covenant_refinancing`."""
    wiring = importlib.import_module("chart_wiring_c")
    render = _oracle("cp3c-owner")["fp04_render"]["blocks"]
    funding = _chart_oracle("cr3")["render"]["covenant_refinancing"]
    wanted = {
        **{
            block_id: (
                spec["owner"],
                spec["kind"],
                spec["state"],
                [spec["primary_tab"], *spec["tabs"]],
            )
            for block_id, spec in render.items()
        },
        "funding-gap": (
            funding["owner"],
            funding["block_kind"],
            funding["state"],
            [funding["primary_tab"], *funding["tabs_with_cp3c"]],
        ),
    }
    for block_id, (owner, kind, state, tab_ids) in wanted.items():
        block = blocks[block_id]
        assert (block["owner"], block["kind"], block["state"]) == (owner, kind, state), block_id
        got = [block["tab_label"], *(tab["label"] for tab in block["tabs"])]
        assert got == wiring.labels_of(*tab_ids), block_id


def _check_scope_run(
    tmp_path: Path, scope_id: str, case: str, outcome: str, build: Adapter
) -> None:
    root = tmp_path / f"{scope_id}-{case}"
    root.mkdir()
    store, receipt, publication = build(case, root)
    scope = g2.DELIVERY_SCOPES[scope_id]
    destination = tmp_path / "out" / f"{scope_id}-{case}"
    destination.parent.mkdir(exist_ok=True)
    report = g2.render_owner_slice(store, receipt, publication, destination)
    text = report.read_text(encoding="utf-8")
    wire = g2.OwnerRenderReceipt.from_wire((destination / "render-receipt.json").read_bytes())
    assert wire.outcome == outcome and wire.scope_id == scope_id
    assert text.count('id="delivery-scope-banner"') == 1
    assert html_lib.escape(scope.banner[outcome]) in text
    assert (destination / "model").exists() == (
        "CP-MODEL" in scope.requested_modules and outcome == "complete"
    )
    assert tuple(s.block_id for s in wire.sections) == tuple(scope.sections)
    payload = _payload(text)
    blocks = {b["block_id"]: b for b in payload["report"]["blocks"]}
    heads = {h.module_id: h for h in wire.head_results}
    for section in wire.sections:
        if outcome == "complete":
            assert section.facts and section.state in {"populated", "collapsed"}
        else:
            assert not section.facts and section.state != "populated"
        for fact in section.facts:
            assert fact.result_sha256 == heads[fact.module_id].result_sha256
    assert_scope_figures(scope_id, case, outcome, payload)
    if scope_id in _FUNDING_GAP_HEADS:
        (gap,) = (s for s in wire.sections if s.block_id == "funding-gap")
        assert_funding_gap_heads(
            scope_id, [(f.module_id, f.fact_id) for f in gap.facts], payload["modules"]
        )
    if scope_id == "cp3c-fp04-refinancing":
        _assert_cp3c_blocks(blocks)
    if outcome == "complete" and scope_id in ORACLE_POINTERS and scope.sections:
        name, pointer = ORACLE_POINTERS[scope_id]
        node = _pointer(_oracle(name), pointer.format(c=_oracle_case_key(scope_id, case)))
        for section_id, oracle_block in _block_nodes(node, tuple(scope.sections)).items():
            assert_block_equals_oracle(blocks[section_id], oracle_block)
    for rail in wire.rails:
        for fact in rail.facts:
            module = next(m for m in payload["modules"] if m["module_id"] == fact.module_id)
            assert any(f["fact_id"] == fact.fact_id for f in module["facts"])
    g2.verify_owner_rendered_slice(store, receipt, publication, destination)


_COMPLETE_CASES = [(s, c) for s, row in DEFERRED.items() for c in row[1]]
_REFUSED_CASES = [(s, row[2]) for s, row in DEFERRED.items() if row[2]]
_BLOCKED_CASES = [(s, c) for s, row in DEFERRED.items() for c in row[3]]


@pytest.mark.parametrize(("scope_id", "case"), _COMPLETE_CASES)
def test_genuine_deferred_complete_cases(tmp_path: Path, scope_id: str, case: str) -> None:
    _check_scope_run(tmp_path, scope_id, case, "complete", DEFERRED[scope_id][0])


@pytest.mark.parametrize(("scope_id", "case"), _REFUSED_CASES)
def test_genuine_deferred_refused_cases(tmp_path: Path, scope_id: str, case: str | None) -> None:
    assert case is not None
    _check_scope_run(tmp_path, scope_id, case, "refused", DEFERRED[scope_id][0])


@pytest.mark.parametrize(("scope_id", "case"), _BLOCKED_CASES)
def test_genuine_deferred_blocked_cases_are_refused(
    tmp_path: Path, scope_id: str, case: str
) -> None:
    root = tmp_path / "blocked"
    root.mkdir()
    store, receipt, publication = DEFERRED[scope_id][0](case, root)
    with pytest.raises(ValueError, match=r"^owner_render_"):
        g2.render_owner_slice(store, receipt, publication, tmp_path / "out" / "delivery")


def test_genuine_deferred_s1a_gap_must_not_appear(tmp_path: Path) -> None:
    root = tmp_path / "s1a-gap"
    root.mkdir()
    store, receipt, publication = _s1a("gap", root)
    report = g2.render_owner_slice(store, receipt, publication, tmp_path / "delivery")
    blocks = {
        b["block_id"]: b for b in _payload(report.read_text(encoding="utf-8"))["report"]["blocks"]
    }
    for section_id in ("company-profile", "transaction-summary"):
        for row in blocks[section_id].get("rows", []):
            for cell in row["cells"]:
                assert cell["text"].strip() not in {"", "0", "N/A", "TBD"}
    strengths = " ".join(_line_text(line) for line in blocks["strengths-weaknesses"]["lines"])
    assert "High" not in strengths
