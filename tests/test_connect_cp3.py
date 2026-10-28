"""Stage 2 connection of CP-3 (relative value), the fast tests: no promotion, no owner run.

Scope is `docs/CP3-OWNER-LEASE.md` (CP-3 half) and LEAD ruling Q2: CP-3 is a live-contract module,
so the connection is `owners.cp3.QUALIFICATION/probe/ENTRY_VALIDATOR`, the registrations in
`owner_workflow.py` and the R3 run driver `tests/cp3_cp6_runs.py` (`cp3_closed`). CP-6 is not
registered here and the CP-3 consumption proof (D3) stays open until the CP-6 lease run verifies;
no reader exists because the lease names none.
"""

import hashlib
import json
import tempfile
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import cp3_cp6_runs as runs
import pytest
import test_method_cp3 as stage1
from defect_classes import BLANK_VALUES
from pydantic import ValidationError
from test_method_cp3 import make_inputs, mutate

from deploy_vii import cp3_relative_value
from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Fact, ModuleView, Run, View
from deploy_vii.cp3_relative_value import (
    RelativeValueReport,
    RelativeValueSubmission,
    cp3_module,
    submit_cp3_step,
)
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    StepSubmission,
    head_of,
)
from deploy_vii.live.tools import cited_locators
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import plan, step_chain
from deploy_vii.report_view import _spec_of
from deploy_workflow import owner_workflow as ow
from deploy_workflow.owner_workflow import OwnerSpec, OwnerWorkflow, StepSpec
from deploy_workflow.owners import cp3
from deploy_workflow.owners.cp3 import compute
from deploy_workflow.workflow import WorkflowError

ROOT = Path(__file__).parents[1]
SUBMISSIONS = stage1.SUBMISSIONS
EXPECTED = stage1.EXPECTED
STEP = "relative_value"

# --- registration rows equal the lease (Public API additions) ------------------------------------


def test_owner_spec_row_equals_the_lease() -> None:
    assert ow.OWNER_SPECS["CP-3"] == OwnerSpec(
        module_id="CP-3",
        steps=(
            StepSpec(
                step_id="relative_value",
                schema=RelativeValueSubmission,
                sources=True,
                extract=False,
                upstream_grant=None,
                inputs="none",
                rules="journaled",
            ),
        ),
        entry="model_payload",
        kind="analytical",
        publish=None,
    )


def test_registration_rows_are_appended_and_complete() -> None:
    assert list(ow.OWNER_SPECS) == ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL", "CP-3"]
    assert ow.SUPPORTED_ANALYTICAL == {"CP-0", "CP-1", "CP-1A", "CP-2", "CP-3"}
    assert ow._QUALIFICATION["CP-3"] is cp3_relative_value.PROMOTED
    assert ow._QUALIFICATION["CP-3"] is cp3.QUALIFICATION
    assert ow._PROBES["CP-3"] is cp3.probe
    assert ow._ENTRY_VALIDATORS["CP-3"] is cp3.ENTRY_VALIDATOR
    assert cp3.ENTRY_VALIDATOR is cp3_relative_value._validate_step
    assert list(ow._PROBES) == ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-3"]
    assert list(ow._ENTRY_VALIDATORS) == ["CP-1A", "CP-2", "CP-3"]
    assert list(ow._QUALIFICATION) == ["CP-1", "CP-1A", "CP-2", "CP-MODEL", "CP-3"]


def test_live_contract_module_takes_no_owner_core_parts() -> None:
    """The lease adds no seam of its own: no `_CORES` row, no view (inputs "none"), no gate."""
    assert "CP-3" not in ow._CORES
    assert STEP not in ow._VIEWS
    assert "CP-3" not in ow._PRECHECKS
    for absent in ("view", "STEP_IDS", "SCHEMAS", "RULES", "submit", "precheck"):
        assert not hasattr(cp3, absent), absent


def test_check_steps_accepts_the_row() -> None:
    ow._check_steps("CP-3", ow.OWNER_SPECS["CP-3"])
    chain = step_chain("CP-3")
    assert chain.steps == (STEP,)
    assert STEP in chain.pack_sources


@pytest.mark.parametrize(
    "change",
    [{"sources": False}, {"extract": True}, {"inputs": "module_context"}, {"rules": "precheck"}],
)
def test_check_steps_refuses_a_row_that_departs_from_the_chain(change: dict[str, Any]) -> None:
    spec = ow.OWNER_SPECS["CP-3"]
    step = StepSpec(**{**spec.steps[0].__dict__, **change})
    forged = OwnerSpec(spec.module_id, (step,), spec.entry, spec.kind, spec.publish)
    with pytest.raises(WorkflowError) as error:
        ow._check_steps("CP-3", forged)
    assert error.value.args[0] == "not_permitted"


def test_check_steps_refuses_without_an_entry_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(ow._ENTRY_VALIDATORS, "CP-3")
    with pytest.raises(WorkflowError):
        ow._check_steps("CP-3", ow.OWNER_SPECS["CP-3"])


# --- a real store: Stage 1 fixture heads, the product's own CP-3 step ----------------------------


def _begin(root: Path, case: str) -> tuple[Execution, Attempt]:
    """A store whose CP-0, CP-1, CP-1A and CP-2 heads are the Stage 1 fixtures (built from the
    frozen oracle); CP-0 carries the T8 command that authorises CP-3. CP-3 is begun, not run."""
    pack = stage1.make_pack(case)
    cp0 = stage1.make_cp0(pack, case)
    command = Fact(
        fact_id="run-consumer",
        table_id="T8",
        row_id="CP-3",
        field="exact_command",
        label="Run consumer",
        text="Run CP-3",
    )
    heads = (
        cp0.model_copy(update={"facts": (*cp0.facts, command)}),
        stage1.make_cp1(pack),
        stage1.make_cp1a(pack, case, blocked=False),
        stage1.make_cp2(pack),
    )
    store = Execution.create(root / "store", pack)
    for head in heads:
        store._store(head.model_dump_json())
    store._write(store.read().model_copy(update={"heads": tuple(head_of(h) for h in heads)}))
    return store, store.begin("CP-3")


def _settled(root: Path, case: str, *, repaired: bool = False) -> tuple[Execution, Attempt]:
    """CP-3 settled by the product's own step. `repaired`: attempt 0 first submits an invalid
    literal and finishes with issues, so the head settles on attempt 1 (repair_of set)."""
    store, attempt = _begin(root, case)
    payload = stage1._instantiate(SUBMISSIONS[case]["relative_value"])
    if repaired:
        bad = mutate(
            SUBMISSIONS[case]["relative_value"], [["set", "preference.confidence", "High"]]
        )
        first = submit_cp3_step(store, attempt.ticket_id, STEP, stage1._instantiate(bad))
        assert first.status == "finished"
        assert first.issues
        attempt = store.begin("CP-3")
        assert attempt.number == 1
        assert attempt.repair_of == first.ticket_id
    finished = submit_cp3_step(store, attempt.ticket_id, STEP, payload)
    assert finished.status == "finished"
    assert finished.number == (1 if repaired else 0)
    return store, finished


@pytest.fixture(scope="module", params=["positive", "gap", "positive-attempt-1"])
def settled(request: pytest.FixtureRequest) -> Iterator[tuple[Execution, Attempt]]:
    case, _, repair = str(request.param).partition("-attempt-")
    with tempfile.TemporaryDirectory() as root:
        yield _settled(Path(root), case, repaired=bool(repair))


def _head(snapshot: ExecutionSnapshot) -> Head:
    return next(h for h in snapshot.heads if h.module_id == "CP-3")


def test_probe_accepts_a_settled_attempt(settled: tuple[Execution, Attempt]) -> None:
    store, attempt = settled
    cp3.probe(store, store.read(), attempt)  # returns None; any mismatch raises


def test_probe_refuses_a_head_that_is_not_the_rebuild(settled: tuple[Execution, Attempt]) -> None:
    store, attempt = settled
    snapshot = store.read()
    head = _head(snapshot)
    module = store.head_module(head)
    other = module.model_copy(update={"limitations": (*module.limitations, "Tampered limitation")})
    store._store(other.model_dump_json())
    forged = snapshot.model_copy(
        update={"heads": tuple(head_of(other) if h is head else h for h in snapshot.heads)}
    )
    with pytest.raises(WorkflowError) as error:
        cp3.probe(store, forged, attempt)
    assert error.value.args[0] == "identity_mismatch"


def test_probe_refuses_an_attempt_without_exactly_one_valid_step(
    settled: tuple[Execution, Attempt],
) -> None:
    store, attempt = settled
    snapshot = store.read()
    for steps in ((), (*attempt.steps, *attempt.steps)):
        with pytest.raises(WorkflowError) as error:
            cp3.probe(store, snapshot, attempt.model_copy(update={"steps": steps}))
        assert error.value.args[0] == "identity_mismatch"


def test_probe_refuses_a_step_whose_payload_no_longer_validates(
    settled: tuple[Execution, Attempt],
) -> None:
    store, attempt = settled
    mutated = mutate(
        SUBMISSIONS["positive"]["relative_value"], [["set", "preference.confidence", "High"]]
    )
    step = attempt.steps[0].model_copy(
        update={"payload_sha256": store._store(stage1._instantiate(mutated))}
    )
    with pytest.raises(WorkflowError) as error:
        cp3.probe(store, store.read(), attempt.model_copy(update={"steps": (step,)}))
    assert error.value.args[0] == "identity_mismatch"


def test_the_settled_head_is_the_product_candidate(settled: tuple[Execution, Attempt]) -> None:
    store, attempt = settled
    module = store.head_module(_head(store.read()))
    report = RelativeValueReport.model_validate_json(
        store.step_output(attempt.steps[0].output_sha256 or "")
    )
    candidate = cp3_module(report, attempt.inputs, attempt.number)
    # `settle` adds the status and the inherited limitations; the content is the candidate's.
    for field in ("facts", "tables", "claims", "inputs", "attempt"):
        assert getattr(module, field) == getattr(candidate, field), field
    assert set(candidate.limitations) <= set(module.limitations)
    assert module.status == "restricted"


# --- the submission schema ----------------------------------------------------------------------


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_schema_round_trips_and_tail_digest_is_the_submission_hash(case: str) -> None:
    text = stage1._instantiate(SUBMISSIONS[case]["relative_value"])
    submission = RelativeValueSubmission.model_validate_json(text)
    assert RelativeValueSubmission.model_validate_json(submission.model_dump_json()) == submission
    inputs = make_inputs(case)
    result = compute(inputs)
    assert result.report is not None
    assert result.report.submission_sha256 == submission.content_hash()
    module = cp3_module(result.report, inputs.bound, 0)
    assert module.inputs[-1].input_id == "relative-value-submission"
    assert module.inputs[-1].sha256 == submission.content_hash()


HOSTILE = (
    "",
    "[" * 5000 + "]" * 5000,
    '{"a":' * 5000 + "1" + "}" * 5000,
    "1" * 200_000,
    "NaN",
    '{"instruments": "\\ud800"}',
    "[]",
    '{"instruments": [], "instruments": []}',
    '{"instruments": ' + "{|}" * 5000 + "}",
)


@pytest.mark.parametrize("text", HOSTILE, ids=[str(i) for i in range(len(HOSTILE))])
def test_schema_raises_only_value_errors_on_hostile_text(text: str) -> None:
    """Rulings stage2 Q5: only a `ValueError` subclass may leave `model_validate_json`. This is a
    local copy of the probe's hostile set until the shared one lands in `defect_classes`."""
    try:
        RelativeValueSubmission.model_validate_json(text)
    except ValueError:
        return
    pytest.fail("hostile text was accepted")


# --- the oracle refusals reproduce through the registered validator ------------------------------

CP3_REFUSALS = [e for e in EXPECTED["refusals"]["validator_refusals"] if e["owner"] == "CP-3"]
MUTATIONS = {e["id"]: e for e in SUBMISSIONS["refusal_mutations"]["entries"]}


@pytest.mark.parametrize("entry", CP3_REFUSALS, ids=[e["id"] for e in CP3_REFUSALS])
def test_entry_validator_reproduces_the_oracle_refusal(
    entry: dict[str, Any], tmp_path: Path
) -> None:
    """The registered `ENTRY_VALIDATOR`, run over a store, refuses with the oracle's issue."""
    case = entry["case"]
    literal = mutate(SUBMISSIONS[case]["relative_value"], MUTATIONS[entry["id"]]["edits"])
    store, attempt = _begin(tmp_path, case)
    digest = store._store(stage1._instantiate(literal))
    retained = attempt.model_copy(
        update={
            "steps": (StepSubmission(step_id=STEP, inputs=attempt.inputs, payload_sha256=digest),)
        }
    )
    outcome = cp3.ENTRY_VALIDATOR(store, store.pack(), retained)
    assert outcome.output is None
    assert any(entry["issue_contains"] in issue for issue in outcome.issues), outcome.issues


# --- backlog: blank quotes (backlog "Every module", round 13 addendum 3) -------------------------

QUOTE_PATHS = (
    "market_evidence[0].quote.quote",
    "instruments[0].basis.quotes[0].quote",
    "preference.basis.quotes[0].quote",
)


@pytest.mark.parametrize("path", QUOTE_PATHS)
@pytest.mark.parametrize("value", BLANK_VALUES, ids=[f"b{i}" for i in range(len(BLANK_VALUES))])
def test_a_blank_quote_is_never_accepted(path: str, value: str) -> None:
    """Inventory result: CP-3 refuses every blank quote (fail closed). The refusal text is the
    engine's own (`malformed citation` for `""`, `quote not found` otherwise), not the pinned
    `<path>: empty text` frame: that wording lives in `src/deploy_vii`, which Stage 2 does not
    edit, so the test pins the refusal, not the frame."""
    literal = mutate(SUBMISSIONS["positive"]["relative_value"], [["set", path, value]])
    try:
        result = compute(make_inputs("positive", literal))
    except ValidationError:
        return
    assert result.report is None
    assert result.issues


# --- bindings, `_Spec` rows ---------------------------------------------------------------------


def test_cp3_bindings_cover_the_composed_module_and_the_spec_row_exists() -> None:
    inputs = make_inputs("positive")
    result = compute(inputs)
    assert result.report is not None
    module = cp3_module(result.report, inputs.bound, 0)
    module_view = ModuleView(
        module_id="CP-3",
        title="Relative value",
        aliases=(),
        status="restricted",
        artifact_sha256=module.content_hash(),
        facts=module.facts,
        tables=module.tables,
        claims=module.claims,
        limitations=module.limitations,
    )
    view = View(run=inputs.pack.run, mode="candidate", modules=(module_view,))
    assert validate_bindings(view, SHIPPED_MAPS) == ()
    assert _spec_of("relative-value").owner == "CP-3"
    blocks = {e.block_id for m in SHIPPED_MAPS if m.module_id == "CP-3" for e in m.entries}
    assert blocks == {"relative-value", "evidence", "limitations"}


# --- the R3 run driver (`tests/cp3_cp6_runs.py`), assembled but not run -------------------------


def test_driver_exports_only_the_cp3_run() -> None:
    assert callable(runs.cp3_closed)
    assert not hasattr(runs, "cp6_closed")


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_driver_pack_and_run_equal_the_oracle(case: str) -> None:
    pack = runs.make_pack(case)
    manifest = runs.oracle()["manifest"]
    entry = next(c for c in manifest["cases"] if c["case_id"] == runs.CASES[case])
    assert {**entry["runs"]["R3"]["run"], "schema_version": "run/2"} == json.loads(
        pack.run.model_dump_json()
    )
    assert list(pack.run.requested_modules) == manifest["runs"]["R3"]["requested_modules"]
    assert [s.source_id for s in pack.sources] == [i["source_id"] for i in entry["pack_sources"]]
    assert list(plan(pack.run.requested_modules)) == manifest["runs"]["R3"]["plan_order"]
    if case == "positive":
        assert pack.sources[-1].sha256 == manifest["market_source"]["sha256"]


def test_driver_refuses_a_drifted_oracle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(runs.PINS, runs.CASE_DIR / "manifest.json", "0" * 64)
    with pytest.raises(RuntimeError, match="oracle drift"):
        runs.oracle()


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_driver_literals_compose_as_the_oracle_states(case: str) -> None:
    pack = runs.make_pack(case)
    s1 = json.loads((ROOT / "cases/snapshot/submissions.json").read_text())["positive"]
    business = json.loads(runs.literal(case, "business_context", pack))
    spec = SUBMISSIONS[case]["business_context"]
    assert business["sources"] == [*s1["business_context"]["sources"], *spec["sources_append"]]
    assert business["consumers"] == spec["consumers"]["R3"]
    keep = {k: v for k, v in business.items() if k not in ("sources", "consumers")}
    assert keep == {
        k: v for k, v in s1["business_context"].items() if k not in ("sources", "consumers")
    }
    readiness = json.loads(runs.literal(case, "readiness_review", pack))
    assert readiness["pack_sha256"] == pack.content_hash()
    assert readiness == json.loads(
        json.dumps(SUBMISSIONS[case]["readiness_review"]["R3"]).replace(
            runs.PACK_PLACEHOLDER, pack.content_hash()
        )
    )
    context = json.loads(runs.literal(case, "cp1_source_context", pack))
    assert context["pack_sha256"] == pack.content_hash()
    assert json.loads(runs.literal(case, "credit_synthesis")) == s1["credit_synthesis"]
    assert runs.PACK_PLACEHOLDER not in runs.literal(case, "relative_value", pack)


def test_driver_binds_figures_with_the_oracle_unit_tokens() -> None:
    text = runs.literal("positive", "relative_value")
    names = runs.figure_names(text)
    assert names
    figures = runs.oracle()["submissions"]["figures"]
    bound = runs.bind_figures(text, {n: (f"F-{n}", figures[n]["unit_token"]) for n in names})
    assert "{{FIG:" not in bound
    for name in names:
        assert "{F-" + name + "|" + figures[name]["unit_token"] + "}" in bound


def test_driver_cites_exactly_the_market_pages_the_oracle_reads() -> None:
    positive = runs.literal("positive", "relative_value")
    assert sorted(cited_locators(positive)) == [("market", "page:1"), ("market", "page:2")]
    assert sorted(cited_locators(runs.literal("gap", "relative_value"))) == []


def test_oracle_pins_match_cases_pins_json() -> None:
    pins = json.loads((ROOT / "cases/PINS.json").read_text())
    for name in ("manifest.json", "submissions.json", "expected.json"):
        key = f"cases/cp3-cp6-owner/{name}"
        assert hashlib.sha256((ROOT / key).read_bytes()).hexdigest() == pins[key]
        assert runs.PINS[ROOT / key] == pins[key]


# --- create-time refusals (lease :138-139): nothing is written ----------------------------------


def _selection(modules: list[str]) -> PreparedPack:
    pack = runs.make_pack("positive")
    document = {**json.loads(pack.run.model_dump_json()), "requested_modules": modules}
    return PreparedPack(run=Run.model_validate_json(json.dumps(document)), sources=pack.sources)


# R3 as pinned plans CP-MODEL before CP-3 and is refused for that ordering until the G1 ordering
# change lands (`claude/s2-g1x-order`), so the controls below drop CP-MODEL: they are the same
# selection that `create` accepts, and a refusal below is then due to the added module only.
CONTROL = ["CP-1", "CP-1A", "CP-2", "CP-3"]


def _create(
    root: Path, modules: list[str], specs: Mapping[str, OwnerSpec] | None = None
) -> OwnerWorkflow:
    return OwnerWorkflow.create(
        root / "store",
        _selection(modules),
        specs=ow.OWNER_SPECS if specs is None else specs,
        publication_directory=None,
    )


def test_control_selection_is_created(tmp_path: Path) -> None:
    workflow = _create(tmp_path, CONTROL)
    assert workflow._plan == ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-3")
    assert (tmp_path / "store").exists()


@pytest.mark.parametrize("extra", ["CP-4C", "CP-3D", "CP-2D", "CP-3C"])
def test_a_module_without_a_spec_in_a_cp3_run_refuses_and_writes_nothing(
    extra: str, tmp_path: Path
) -> None:
    assert extra not in ow.OWNER_SPECS
    with pytest.raises(WorkflowError) as error:
        _create(tmp_path, [*CONTROL, extra])
    assert error.value.args[0] == "not_permitted"
    assert list(tmp_path.iterdir()) == []


def test_a_plan_with_cp5_and_no_cp5_spec_refuses_and_writes_nothing(tmp_path: Path) -> None:
    if "CP-5" in ow.OWNER_SPECS:
        pytest.skip("CP-5 has a spec: the refusal is no longer about a missing spec")
    with pytest.raises(WorkflowError) as error:
        _create(tmp_path, [*CONTROL, "CP-5"])
    assert error.value.args[0] == "not_permitted"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "change",
    [
        {"rules": "none"},
        {"sources": False},
        {"inputs": "module_context"},
        {"schema": RelativeValueReport},
    ],
)
def test_a_spec_override_refuses_and_writes_nothing(change: dict[str, Any], tmp_path: Path) -> None:
    spec = ow.OWNER_SPECS["CP-3"]
    step = StepSpec(**{**spec.steps[0].__dict__, **change})
    specs = {m: ow.OWNER_SPECS[m] for m in ("CP-0", "CP-1", "CP-1A", "CP-2")}
    specs["CP-3"] = OwnerSpec(spec.module_id, (step,), spec.entry, spec.kind, spec.publish)
    with pytest.raises(WorkflowError) as error:
        _create(tmp_path, CONTROL, specs=specs)
    assert error.value.args[0] == "not_permitted"
    assert list(tmp_path.iterdir()) == []


def test_the_unmodified_spec_mapping_is_created(tmp_path: Path) -> None:
    """Control for the override test: the same mapping with the reference CP-3 row is accepted."""
    specs = {m: ow.OWNER_SPECS[m] for m in ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-3")}
    assert _create(tmp_path, CONTROL, specs=specs)._plan[-1] == "CP-3"
