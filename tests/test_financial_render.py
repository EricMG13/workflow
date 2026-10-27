"""Financial delivery checks; actual participant and native browser proof are separate."""

import hashlib
import importlib
import importlib.util
import json
import shutil
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path

import pytest

from deploy_vii.execution import Execution

MANIFEST = json.loads((Path(__file__).parents[1] / "cases/financial/manifest.json").read_text())


def _renderer():
    assert importlib.util.find_spec("deploy_workflow.financial_rendering") is not None, (
        "Task3-B financial rendering entrypoint is absent"
    )
    return importlib.import_module("deploy_workflow.financial_rendering")


def test_financial_rendering_entrypoint_is_available():
    """The first RED has no dependency on C1's pending producer implementation."""
    assert callable(_renderer().render_financial_slice)


@pytest.fixture(scope="module")
def financial_cases(tmp_path_factory):
    # This test-only helper is explicitly agreed with C1. It will be consumed
    # only from reviewed integrated code, never copied from mutable C1 WIP.
    # It drives genuine bounded workflow stages and the actual core publisher;
    # component review builders are not actual analytical participant evidence.
    from test_financial_workflow import completed_financial_case

    root = tmp_path_factory.mktemp("financial-component-inputs")
    completed = {}

    def get_case(*, gap=False):
        if gap not in completed:
            completed[gap] = completed_financial_case(
                root / ("gap" if gap else "positive"), gap=gap
            )
        return completed[gap]

    return get_case


@pytest.fixture
def case(tmp_path, financial_cases):
    def copy_case(*, gap=False):
        source_store, source_receipt, source_model = financial_cases(gap=gap)
        root = tmp_path / ("gap-inputs" if gap else "positive-inputs")
        root.mkdir()
        store = root / "execution"
        receipt = root / "financial-slice.json"
        model = None if source_model is None else root / "publication"
        shutil.copytree(source_store, store)
        shutil.copyfile(source_receipt, receipt)
        if model is not None:
            shutil.copytree(source_model, model)
        return store, receipt, model

    return copy_case


def _payload(path):
    # Component data assertions supplement, but never replace, native DOM proof.
    text = path.read_text()
    return json.loads(
        text.split('<script id="report-data" type="application/json">', 1)[1].split("</script>", 1)[
            0
        ]
    )


@pytest.mark.parametrize("gap", [False, True])
def test_authentic_financial_delivery_preserves_state_and_raw_publication(tmp_path, case, gap):
    from deploy_vii.cp1_workflow import read_cp1_envelope
    from deploy_vii.cp_model_workflow import verify_cp_model_publication
    from deploy_workflow.financial_workflow import FinancialSliceReceipt

    directory, receipt_path, model_directory = case(gap=gap)
    store = Execution(directory)
    before = store.read().content_hash()
    source_bytes = receipt_path.read_bytes()
    receipt = FinancialSliceReceipt.model_validate_json(source_bytes)
    destination = tmp_path / "published"
    html = _renderer().render_financial_slice(directory, receipt_path, model_directory, destination)
    assert html == destination / "report.html"
    assert store.read().content_hash() == before == receipt.snapshot_sha256
    assert receipt_path.read_bytes() == source_bytes
    assert (destination / "financial-slice.json").read_bytes() == source_bytes
    metadata = json.loads((destination / "render-receipt.json").read_text())
    assert metadata["schema_version"] == "cp1-model-slice-render/1"
    assert metadata["financial_receipt_sha256"] == hashlib.sha256(source_bytes).hexdigest()
    assert metadata["snapshot_sha256"] == before
    assert metadata["pack_sha256"] == receipt.pack_sha256
    for name, expected in metadata["files"].items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == expected
    payload = _payload(html)
    modules = {module["module_id"]: module for module in payload["modules"]}
    assert payload["run"]["run_id"] == receipt.run.run_id
    assert modules["CP-0"]["status_word"] == "With limitations"
    assert html.read_text().count('id="delivery-scope-banner"') == 1
    assert metadata["scope"] in html.read_text()
    if gap:
        assert metadata["refusal"] == "cp1_not_authorized"
        assert metadata["cp1_result_sha256"] is None
        assert metadata["model_result_sha256"] is None
        for module in (modules["CP-1"], modules["CP-MODEL"]):
            assert module["status_word"] == "Not run"
            assert not module["facts"] and not module["claims"]
        financial = next(
            source for source in payload["sources"] if source["source_id"] == "financial"
        )
        assert financial["status"] == "missing" and financial["sha256"] is None
        assert not financial["spans"]
        assert "Quarterly financial statements were not supplied." in html.read_text()
        assert not (destination / "model").exists()
        assert not (destination / "calculation.json").exists()
        assert not (destination / "cp1").exists()
    else:
        assert metadata["refusal"] is None
        assert modules["CP-1"]["status_word"] == "With limitations"
        assert modules["CP-MODEL"]["status_word"] == "With limitations"
        assert metadata["cp1_result_sha256"] == receipt.cp1.result_sha256
        assert metadata["model_result_sha256"] == receipt.model.result_sha256
        for name, expected in receipt.model.files.items():
            delivered = (destination / "model" / name).read_bytes()
            assert delivered == (model_directory / name).read_bytes()
            assert hashlib.sha256(delivered).hexdigest() == expected
        assert (destination / "calculation.json").read_bytes() == (
            destination / "model" / "calculation.json"
        ).read_bytes()
        assert verify_cp_model_publication(store, destination / "model") == ()
        envelope = read_cp1_envelope(store, destination / "cp1")
        assert envelope.module.content_hash() == receipt.cp1.result_sha256
        model = json.loads((destination / "calculation.json").read_text())
        assert model["schema_version"] == "financial-model/3"
        assert model["computations"] and model["metrics"] and model["values"]
        bases = {basis["basis_id"]: basis for basis in model["bases"]}
        own = next(
            basis
            for basis in bases.values()
            if basis["scope"] == "historical"
            and basis["kind"] == "QUARTER"
            and basis["end_date"] == "2025-12-31"
        )
        trailing = next(
            basis
            for basis in bases.values()
            if basis["scope"] == "trailing_four_quarters" and basis["end_date"] == "2025-12-31"
        )
        assert own["start_date"] == "2025-10-01" and own["days"] == 92
        assert trailing["start_date"] == "2025-01-01" and trailing["days"] == 365
        assert len(trailing["quarter_construction_ids"]) == 4
        values = {(value["basis_id"], value["key"]): value for value in model["values"]}
        fiscal = next(
            basis
            for basis in bases.values()
            if basis["scope"] == "historical"
            and basis["kind"] == "FY"
            and basis["period_id"] == "fy-2025"
        )
        display_ltm = next(
            basis
            for basis in bases.values()
            if basis["scope"] == "historical" and basis["kind"] == "LTM"
        )
        assert fiscal["start_date"] == display_ltm["start_date"] == "2025-01-01"
        assert fiscal["end_date"] == display_ltm["end_date"] == "2025-12-31"
        assert fiscal["days"] == display_ltm["days"] == 365
        assert display_ltm["basis_id"] != trailing["basis_id"]
        assert not any(basis["period_id"] == "fy-2024" for basis in bases.values())
        # Independent frozen literal values, in the Model's source-unit millions.
        for key in ("revenue", "ebitda", "fcf", "total_debt", "net_debt"):
            shown = values[trailing["basis_id"], key]
            assert Decimal(shown["value"]["amount"]) == Decimal(
                MANIFEST["q4_ltm_derived_source_units"][key]
            )
            assert shown["currency"] == "USD" and shown["unit"] == "MILLIONS"
        assert Decimal(values[own["basis_id"], "capex"]["value"]["amount"]) == Decimal("-2.5")
        assert Decimal(values[own["basis_id"], "acct:rcf_drawn"]["value"]["amount"]) == 0
        # V4 now genuinely reports functional COGS/gross profit; unknowns are
        # early twelve-month ratios and prior-year growth, not these amounts.
        assert Decimal(values[own["basis_id"], "cogs"]["value"]["amount"]) == -15
        assert Decimal(values[own["basis_id"], "gross_profit"]["value"]["amount"]) == 15
        for basis in (fiscal, display_ltm):
            assert Decimal(values[basis["basis_id"], "cogs"]["value"]["amount"]) == -60
            assert Decimal(values[basis["basis_id"], "gross_profit"]["value"]["amount"]) == 60
            for key in ("revenue", "ebitda", "fcf", "total_debt", "net_debt"):
                assert Decimal(values[basis["basis_id"], key]["value"]["amount"]) == Decimal(
                    MANIFEST["q4_ltm_derived_source_units"][key]
                )
        early_quarter_ids = {
            basis["basis_id"]
            for basis in bases.values()
            if basis["scope"] == "historical"
            and basis["kind"] == "QUARTER"
            and basis["end_date"] < "2025-12-31"
        }
        assert len(early_quarter_ids) == 3
        early_ratios = [
            metric
            for metric in model["metrics"]
            if metric["display_basis_id"] in early_quarter_ids
            and metric["key"]
            in {
                "metric:total_leverage_reported",
                "metric:interest_coverage_reported",
            }
        ]
        assert len(early_ratios) == 6
        for metric in early_ratios:
            assert metric["value"]["amount"] is None
            assert metric["value"]["reason"]
        metrics = {
            metric["key"]: metric
            for metric in model["metrics"]
            if metric["display_basis_id"] == own["basis_id"]
        }
        leverage = metrics["metric:total_leverage_reported"]
        assert Decimal(leverage["numerator"]["amount"]) == Decimal(50)
        assert Decimal(leverage["denominator"]["amount"]) == Decimal(30)
        with localcontext() as context:
            context.prec = 38
            context.rounding = ROUND_HALF_EVEN
            assert Decimal(leverage["value"]["amount"]) == Decimal(5) / Decimal(3)
        coverage = metrics["metric:interest_coverage_reported"]
        assert Decimal(coverage["numerator"]["amount"]) == Decimal(30)
        assert Decimal(coverage["denominator"]["amount"]) == Decimal(5)
        assert Decimal(coverage["value"]["amount"]) == Decimal(6)
        margin = metrics["metric:ebitda_margin"]
        assert Decimal(margin["numerator"]["amount"]) == Decimal("7.5")
        assert Decimal(margin["denominator"]["amount"]) == Decimal(30)
        assert Decimal(margin["value"]["amount"]) == Decimal("0.25")
        assert metrics["revenue_growth"]["value"]["amount"] is None
        assert metrics["revenue_growth"]["value"]["reason"]
        # Equal result values do not collapse Q4 and twelve-month operand bases.
        value_by_id = {value["value_id"]: value for value in model["values"]}
        for operand in leverage["denominator"]["operands"]:
            assert value_by_id[operand["value_id"]]["basis_id"] == trailing["basis_id"]
        for operand in margin["denominator"]["operands"]:
            assert value_by_id[operand["value_id"]]["basis_id"] == own["basis_id"]
        revenue = values[trailing["basis_id"], "revenue"]
        financial = next(
            source for source in MANIFEST["sources"] if source["source_id"] == "financial"
        )
        spans = {page["locator"]: page["text"] for page in financial["pages"]}
        assert revenue["value"]["citations"]
        for citation in revenue["value"]["citations"]:
            assert citation["source_id"] == "financial"
            assert citation["source_sha256"] == financial["sha256"]
            assert citation["quote"] in spans[citation["locator"]]
        computations = {item["computation_id"]: item for item in model["computations"]}
        assert computations[revenue["computation_id"]]["operation"] == "sum"


@pytest.mark.parametrize(
    "variant",
    [
        "receipt",
        "snapshot",
        "pack",
        "cp1",
        "model",
        "model.html",
        "calculation.json",
        "receipt.json",
        "raw-newlines",
    ],
)
def test_forged_stale_or_changed_inputs_never_publish(tmp_path, case, variant):
    directory, receipt_path, model_directory = case()
    payload = json.loads(receipt_path.read_text())
    if variant == "receipt":
        payload["cp1"]["result_sha256"] = "a" * 64
        receipt_path.write_text(json.dumps(payload))
    elif variant == "snapshot":
        store = Execution(directory)
        snapshot = store.read()
        store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
    elif variant in {"pack", "cp1", "model"}:
        digest = payload["pack_sha256"] if variant == "pack" else payload[variant]["result_sha256"]
        (directory / "blobs" / digest).write_bytes(b"corrupt selected artifact")
    elif variant == "raw-newlines":
        path = model_directory / "model.html"
        original = path.read_bytes()
        changed = original.replace(b"\n", b"\r\n")
        assert changed != original
        path.write_bytes(changed)
    else:
        path = model_directory / variant
        path.write_bytes(path.read_bytes() + b" ")
    destination = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="financial_slice_render_refused"):
        _renderer().render_financial_slice(directory, receipt_path, model_directory, destination)
    assert not destination.exists()


def test_cross_case_receipt_and_unexpected_gap_publication_refuse(tmp_path, case):
    positive, _, publication = case()
    negative, gap_receipt, _ = case(gap=True)
    for directory, model_directory in ((positive, publication), (negative, publication)):
        destination = tmp_path / ("foreign" if directory == positive else "unexpected-model")
        with pytest.raises(ValueError, match="financial_slice_render_refused"):
            _renderer().render_financial_slice(directory, gap_receipt, model_directory, destination)
        assert not destination.exists()


def test_existing_destination_is_preserved(tmp_path, case):
    directory, receipt, model = case()
    destination = tmp_path / "earlier-delivery"
    destination.mkdir()
    marker = destination / "keep.txt"
    marker.write_bytes(b"earlier complete delivery")
    with pytest.raises(ValueError, match="financial_slice_render_refused"):
        _renderer().render_financial_slice(directory, receipt, model, destination)
    assert list(destination.iterdir()) == [marker]
    assert marker.read_bytes() == b"earlier complete delivery"


@pytest.mark.parametrize("change", ["snapshot", "receipt-bytes", "publication"])
def test_change_during_actual_core_render_refuses_publication(tmp_path, case, monkeypatch, change):
    from deploy_vii import render as core_render

    directory, receipt, model = case()
    original = core_render.render

    def render_then_change(*args, **kwargs):
        html = original(*args, **kwargs)
        if change == "snapshot":
            store = Execution(directory)
            snapshot = store.read()
            store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
        elif change == "receipt-bytes":
            receipt.write_text(json.dumps(json.loads(receipt.read_text()), indent=4) + "\n")
        else:
            path = model / "calculation.json"
            path.write_bytes(path.read_bytes() + b" ")
        return html

    monkeypatch.setattr(core_render, "render", render_then_change)
    destination = tmp_path / "changed-after-render"
    with pytest.raises(ValueError, match="financial_slice_render_refused"):
        _renderer().render_financial_slice(directory, receipt, model, destination)
    assert not destination.exists()


@pytest.mark.parametrize(
    "target", ["calculation.json", "model/model.html", "cp1/envelope.md", "render-receipt.json"]
)
def test_corrupt_staged_copy_is_never_delivered(tmp_path, case, monkeypatch, target):
    directory, receipt, model = case()
    original = Path.write_bytes

    def corrupt_copy(path, data):
        stage = next(
            (parent for parent in path.parents if parent.name.startswith(".financial-slice-")), None
        )
        if stage is not None and path.relative_to(stage).as_posix() == target:
            data += b"corrupted staged copy"
        return original(path, data)

    monkeypatch.setattr(Path, "write_bytes", corrupt_copy)
    destination = tmp_path / "corrupt-copy"
    with pytest.raises(ValueError, match="financial_slice_render_refused"):
        _renderer().render_financial_slice(directory, receipt, model, destination)
    assert not destination.exists()


def test_journal_change_during_staging_refuses(tmp_path, case, monkeypatch):
    directory, receipt, model = case()
    original = Path.write_bytes

    def write_then_change(path, data):
        result = original(path, data)
        if path.name == "financial-slice.json" and path.parent.name.startswith(".financial-slice-"):
            store = Execution(directory)
            snapshot = store.read()
            store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
        return result

    monkeypatch.setattr(Path, "write_bytes", write_then_change)
    destination = tmp_path / "stale-staging"
    with pytest.raises(ValueError, match="financial_slice_render_refused"):
        _renderer().render_financial_slice(directory, receipt, model, destination)
    assert not destination.exists()
