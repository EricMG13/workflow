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
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.contracts import Run
from deploy_vii.execution import Execution
from deploy_vii.registry import modules as registry_modules
from deploy_vii.report_view import pathways
from deploy_workflow import owner_rendering as g2
from deploy_workflow.owner_workflow import BeginRecord, OwnerRunReceipt

ROOT = Path(__file__).resolve().parents[1]
LEASE = (ROOT / "docs/OWNER-RENDERING-LEASE.md").read_text(encoding="utf-8")
H = "0" * 64
BANNER_ANCHOR = '<div id="call-root"></div>'

# The 17 shipped rows (lease rev 2, R2.2); the two gated rows are absent until their prerequisite.
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
    "cp4-fp04-covenants",
    "cp8-fp01-what-changed",
    "slice-cp2e-sensitivity",
    "slice-cpdr-research",
    "slice-cpl10-screen",
)
GATED_IDS = ("cp6-fp01-committee", "cp3c-fp04-refinancing")
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
# Rev 2 R2.2 sections (pathway order); `cp1-model` is not listed in the lease (see the report).
EXPECTED_SECTIONS = {
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
        if scope_id != "cp1-model":
            assert tuple(scope.sections) == EXPECTED_SECTIONS[scope_id], scope_id
        order = [blocks[scope.pathway].index(section) for section in scope.sections]
        assert order == sorted(set(order)), scope_id
    for scope_id in ("slice-cp2e-sensitivity", "slice-cpdr-research", "slice-cpl10-screen"):
        assert g2.DELIVERY_SCOPES[scope_id].sections == ()


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
    yield "cp3c", "-", pack_run("cp3c_runs")
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
        document = document[part]
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
    # G2_RUNS_CACHE keeps the 20-minute genuine runs between invocations (developer aid only).
    cache = os.environ.get("G2_RUNS_CACHE")
    base = Path(cache) if cache else tmp_path_factory.mktemp("g2-cp1-model")
    base.mkdir(parents=True, exist_ok=True)
    if (base / "ready").exists():
        return {
            "positive": base / "positive",
            "gap": base / "gap",
            "fin_positive": (
                base / "fin-positive" / "store",
                base / "fin-positive" / "receipt.json",
                base / "fin-positive" / "model",
            ),
        }

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
    (base / "ready").write_text("ok")
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
