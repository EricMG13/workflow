"""CP-4 Stage 2 connection: the registrations, the `step_context` read path (rulings stage2 Q3,
Q4), the positional seams and the semantic-gate precheck.

Every expected value comes from `cases/cp4-owner/expected.json` through the Stage 1 test's frozen
builders. Nothing here runs a store run: those are deferred (`work/build/deferred-runs.md`).
"""

import hashlib
import importlib
import inspect
import json
import typing
from collections.abc import Callable
from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

import pytest

from deploy_vii import cp4_legal
from deploy_workflow import owner_workflow as owner
from deploy_workflow.owners import cp4
from deploy_workflow.workflow import WorkflowError

stage1: Any = importlib.import_module("test_method_cp4")

STEP = "legal_covenants"
# The lease's Public API literal (docs/CP4-OWNER-LEASE.md), written out here, not read back.
CP4_STEP = owner.StepSpec(
    step_id=STEP,
    schema=cp4_legal.CovenantInterpretationSubmission,
    sources=True,
    extract=False,
    upstream_grant=None,
    inputs="step_context",
    rules="journaled",
)
SPEC = owner.OwnerSpec(
    module_id="CP-4", steps=(CP4_STEP,), entry="model_payload", kind="analytical", publish=None
)


# --- the registrations equal the lease --------------------------------------------------------


def test_registration_rows_equal_the_lease() -> None:
    assert owner._ENTRY_VALIDATORS["CP-4"] is cp4_legal._validate_step
    assert cp4.ENTRY_VALIDATOR is cp4_legal._validate_step
    assert owner._PRECHECKS["CP-4"] is cp4.precheck
    assert owner._VIEWS[STEP] is cp4.view
    assert owner._PROBES["CP-4"] is cp4.probe
    assert owner._QUALIFICATION["CP-4"] == cp4_legal.PROMOTED
    assert "CP-4" in owner.SUPPORTED_ANALYTICAL


def test_registrations_are_appended_after_the_existing_rows() -> None:
    assert list(owner._ENTRY_VALIDATORS) == ["CP-1A", "CP-2", "CP-4"]
    assert list(owner._PROBES) == ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-4"]
    assert list(owner._VIEWS) == ["credit_synthesis", STEP]
    assert list(owner._PRECHECKS) == ["CP-4"]
    assert list(owner._QUALIFICATION) == ["CP-1", "CP-1A", "CP-2", "CP-MODEL", "CP-4"]
    assert list(owner.OWNER_SPECS) == ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL", "CP-4"]


def test_owner_spec_equals_the_lease_literal() -> None:
    assert owner.OWNER_SPECS["CP-4"] == SPEC


def test_the_reference_spec_is_one_g1_can_serve() -> None:
    owner._check_steps("CP-4", SPEC)


def test_step_inputs_literal_admits_step_context() -> None:
    hints = typing.get_type_hints(owner.StepSpec)
    assert set(typing.get_args(hints["inputs"])) == {
        "none",
        "projection",
        "module_context",
        "step_context",
    }


# --- _check_steps refusals --------------------------------------------------------------------


def _refused(spec: Any) -> None:
    with pytest.raises(WorkflowError) as caught:
        owner._check_steps("CP-4", spec)
    assert caught.value.code == "not_permitted"


def test_step_context_without_a_views_row_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(owner._VIEWS, STEP)
    _refused(SPEC)


def test_module_context_without_a_views_row_stays_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(owner._VIEWS, STEP)
    _refused(replace(SPEC, steps=(replace(CP4_STEP, inputs="module_context"),)))


def test_cp4_without_an_entry_validator_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(owner._ENTRY_VALIDATORS, "CP-4")
    _refused(SPEC)


@pytest.mark.parametrize(
    "variant",
    [
        replace(CP4_STEP, inputs="projection"),
        replace(CP4_STEP, rules="precheck"),
        replace(CP4_STEP, extract=True),
        replace(CP4_STEP, sources=False),
        replace(CP4_STEP, upstream_grant={"x": 1}),
    ],
    ids=["projection", "financial-precheck", "extract", "no-sources", "grant"],
)
def test_other_cp4_spec_variants_are_refused(variant: Any) -> None:
    _refused(replace(SPEC, steps=(variant,)))


def test_step_context_without_a_views_row_is_refused_for_any_module() -> None:
    """Part (c) alone: a `step_context` step needs a `_VIEWS` row whatever its module."""
    cp1a = owner.OWNER_SPECS["CP-1A"]
    spec = replace(cp1a, steps=(replace(cp1a.steps[0], inputs="step_context"),))
    with pytest.raises(WorkflowError) as caught:
        owner._check_steps("CP-1A", spec)
    assert caught.value.code == "not_permitted"
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(owner._VIEWS, "business_context", lambda historical, attempt: ("", ""))
        owner._check_steps("CP-1A", spec)


# --- _inputs: the step_context serve path -----------------------------------------------------


class _Historical:
    def __init__(self) -> None:
        self.snapshot = object()

    def read(self) -> object:
        return self.snapshot


STORE: Any = object()  # stands for the store; the patched helpers never read it
BINDING: Any = SimpleNamespace(module_id="CP-4", step_id=STEP, ticket_id="ticket-1")


def _fake_world(monkeypatch: pytest.MonkeyPatch) -> tuple[_Historical, object]:
    historical, attempt = _Historical(), object()
    monkeypatch.setattr(owner, "_owner_historical", lambda store, binding: historical)

    def attempt_of(snapshot: object, ticket_id: str) -> object:
        assert snapshot is historical.snapshot and ticket_id == "ticket-1"
        return attempt

    monkeypatch.setattr(owner, "_attempt_of", attempt_of)
    return historical, attempt


def _recorder(calls: list[tuple[Any, ...]], result: tuple[str, str]) -> Callable[..., Any]:
    def view(*args: Any, **kwargs: Any) -> tuple[str, str]:
        assert not kwargs  # the protocol section 2 positional form
        calls.append(args)
        return result

    return view


def test_inputs_serves_step_context_from_the_views_row(monkeypatch: pytest.MonkeyPatch) -> None:
    historical, attempt = _fake_world(monkeypatch)
    calls: list[tuple[Any, ...]] = []
    monkeypatch.setitem(owner._VIEWS, STEP, _recorder(calls, ("d" * 64, "body")))
    assert owner._inputs(STORE, BINDING, CP4_STEP) == ("d" * 64, "body")
    assert calls == [(historical, attempt)]


def test_inputs_still_serves_module_context(monkeypatch: pytest.MonkeyPatch) -> None:
    historical, attempt = _fake_world(monkeypatch)
    calls: list[tuple[Any, ...]] = []
    monkeypatch.setitem(owner._VIEWS, STEP, _recorder(calls, ("a" * 64, "b")))
    spec = replace(CP4_STEP, inputs="module_context")
    assert owner._inputs(STORE, BINDING, spec) == ("a" * 64, "b")
    assert calls == [(historical, attempt)]


def test_inputs_refuses_step_context_without_a_views_row(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_world(monkeypatch)
    monkeypatch.delitem(owner._VIEWS, STEP, raising=False)
    with pytest.raises(WorkflowError) as caught:
        owner._inputs(STORE, BINDING, CP4_STEP)
    assert caught.value.code == "not_permitted"


def test_inputs_refuses_a_step_that_reads_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_world(monkeypatch)
    with pytest.raises(WorkflowError) as caught:
        owner._inputs(STORE, BINDING, replace(CP4_STEP, inputs="none"))
    assert caught.value.code == "not_permitted"


def _receipt(digest: str, body: str, sequence: int = 1) -> Any:
    read = SimpleNamespace(binding=BINDING, sequence=sequence, inputs_sha256=digest, body=body)
    return SimpleNamespace(calls=[], input_reads=[read])


def test_verifier_recomputes_a_step_context_read_through_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    historical, attempt = _fake_world(monkeypatch)
    calls: list[tuple[Any, ...]] = []
    monkeypatch.setitem(owner._VIEWS, STEP, _recorder(calls, ("c" * 64, "served")))
    specs = {"CP-4": SPEC}
    owner._verify_calls_reads(STORE, _receipt("c" * 64, "served"), specs)
    assert calls == [(historical, attempt)]
    forged = (
        _receipt("c" * 64, "edited"),
        _receipt("e" * 64, "served"),
        _receipt("c" * 64, "served", 2),
    )
    for receipt in forged:
        with pytest.raises(WorkflowError) as caught:
            owner._verify_calls_reads(STORE, receipt, specs)
        assert caught.value.code == "identity_mismatch"


# --- the view ---------------------------------------------------------------------------------


class _Store:
    def __init__(self, pack: Any) -> None:
        self._pack = pack

    def pack(self) -> Any:
        return self._pack


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_view_is_the_context_block_over_the_bound_upstream(
    case: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack, upstream = stage1.make_pack(case), stage1.make_upstream(case)
    seen: list[Any] = []

    def upstream_of(store: Any, attempt: Any) -> cp4_legal.Upstream:
        seen.append((store, attempt))
        return cast(cp4_legal.Upstream, upstream)

    monkeypatch.setattr(cp4_legal, "upstream_of", upstream_of)
    store: Any = _Store(pack)
    attempt: Any = SimpleNamespace(tag="attempt")
    digest, body = cp4.view(store, attempt)
    assert seen == [(store, attempt)]
    assert body == json.dumps(
        cp4_legal.context_block(pack, upstream),
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    assert stage1._shape(json.loads(body)) == stage1.VIEW["key_tree"]
    for key in ('"quote"', '"citations"', '"record_json"'):
        assert key not in body


# --- the precheck gate (the Q1 semantic gate, protocol section 4) -----------------------------


def _gate(case: str, text: str | None = None) -> tuple[str, ...]:
    pack = stage1.make_pack(case)
    if text is None:
        submission = stage1.make_submission(case, pack, stage1.make_upstream(stage1.PACK_OF[case]))
        text = submission.model_dump_json()
    store: Any = _Store(pack)
    return cp4.precheck(store, SimpleNamespace(), text)


@pytest.mark.parametrize("case", ["positive", "gap", "gap_false_same_definition"])
def test_precheck_reproduces_the_oracle_gate(case: str) -> None:
    want = stage1.EXPECTED["semantic_gate"]["per_case"][case]["issues"]
    assert list(_gate(case)) == want


def test_precheck_refusal_string_is_the_frozen_one() -> None:
    refusal = stage1.EXPECTED["gap_false_same_definition"]["CP-4"]["refusal"]
    assert list(_gate("gap_false_same_definition")) == refusal["issues"]


HOSTILE = {
    "empty": "",
    "not-json": "not json",
    "array": "[]",
    "null": "null",
    "ill-shaped": '{"covenants": "x"}',
    "empty-object": "{}",
    "deep": '{"a":' * 5000 + "1" + "}" * 5000,
    "huge-int": "9" * 10000,
    "nan": '{"documents": NaN}',
    "lone-surrogate": '{"covenants": ["\\ud800"]}',
}


@pytest.mark.parametrize("text", HOSTILE.values(), ids=HOSTILE.keys())
def test_precheck_passes_text_the_journal_will_refuse(text: str) -> None:
    """Ill-formed text is not this gate's to judge: it yields no issue and never raises, so the
    step validator refuses it as a shape error at the journal (documented fail-through)."""
    assert _gate("gap_false_same_definition", text) == ()


def test_precheck_reads_model_text_only_through_the_bounded_parse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Protocol section 6: a payload the bounded `json_object` parse refuses is never validated
    by this gate, even when it would otherwise be refused (it is the journal's to refuse)."""
    assert _gate("gap_false_same_definition") != ()
    monkeypatch.setattr(cp4, "json_object", lambda text: None)
    assert _gate("gap_false_same_definition") == ()


def test_precheck_names_every_refused_covenant() -> None:
    case = "gap_false_same_definition"
    pack = stage1.make_pack(case)
    submission = stage1.make_submission(case, pack, stage1.make_upstream("gap"))
    (covenant,) = submission.covenants
    many = submission.model_copy(update={"covenants": (covenant,) * 3})
    issues = _gate(case, many.model_dump_json())
    assert [line.split("]")[0] for line in issues] == ["covenants[0", "covenants[1", "covenants[2"]
    assert all(len(line) <= 600 for line in issues)


# --- the seams --------------------------------------------------------------------------------


def test_seams_take_the_protocol_positional_forms() -> None:
    assert list(inspect.signature(cp4.probe).parameters) == ["store", "snapshot", "attempt"]
    assert list(inspect.signature(cp4.view).parameters) == ["historical", "attempt"]
    assert list(inspect.signature(cp4.precheck).parameters) == ["store", "binding", "stored"]
    for seam in (cp4.probe, cp4.view, cp4.precheck):
        kinds = {p.kind for p in inspect.signature(seam).parameters.values()}
        assert kinds == {inspect.Parameter.POSITIONAL_OR_KEYWORD}
