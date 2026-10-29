"""0d-d: the work after the binding write is linear in the payload. A payload the contract
accepts as a string can make a validator or the pre-fill do work that grows with the square of
its rows (or with a number the payload writes), so one submit costs minutes. Each case times one
call at a size that fits the line limit and holds it to a bound the linear code meets by a wide
margin; the guards pin the outputs, so the replay every verifier repeats stays exact."""

import copy
import hashlib
import importlib
import json
import random
import tempfile
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Annotated, Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import TypeAdapter, ValidationError

from deploy_vii import business_context as bc
from deploy_vii import cp3_relative_value as cp3
from deploy_vii import cp4_legal as cp4
from deploy_vii.contracts import Module, Run
from deploy_vii.live.submission import PREFILLED, STEPS, known_bindings, prefill
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import (
    ReadinessReview,
    absence_issues,
    shape_issues,
    validate_review,
)
from deploy_vii.source_context import (
    SourceContextReview,
    source_context,
    validate_source_context,
)

fw = importlib.import_module("test_financial_workflow")

pack = fw.make_pack()
READINESS = json.loads(fw.readiness(pack))
CONTEXT = json.loads(fw.context(pack))
EVENT_CITE = CONTEXT["sources"][1]["event_scan_citations"][0]


def _event(i: int, citations: list[Any]) -> dict[str, Any]:
    return {
        "event_id": f"ev{i}",
        "reporting_scope_id": CONTEXT["sources"][1]["scopes"][-1]["scope_id"],
        "event_date": "2026-01-05",
        "known_on": "2026-01-06",
        "status": "completed",
        "description": "x",
        "effect": "x",
        "citations": citations,
    }


# --- one timed call per site --------------------------------------------------------------


def _case_shape() -> Callable[[], object]:
    payload = json.dumps({"events": [{"citations": []}] * 4000})
    try:
        SourceContextReview.model_validate_json(payload)
    except ValidationError as caught:
        error = caught
    return lambda: shape_issues(error)


def _case_absence() -> Callable[[], object]:
    return lambda: absence_issues(pack, [("pages 1-10000000 are missing", ("financial",))] * 4)


def _case_gaps() -> Callable[[], object]:
    d = copy.deepcopy(READINESS)
    d["consumers"] = [
        {
            "module_id": "CP-1",
            "readiness": "READY",
            "evidence_demand": "x",
            "source_ids": ["identity"],
            "rationale": "x",
            "citations": [],
            "missing_source": None,
            "limitations": [],
        }
    ] * 6000
    d["gaps"] = [
        {
            "gap_id": f"g{i}",
            "kind": "source",
            "severity": "minor",
            "description": "x",
            "affected_modules": ["CP-1"],
            "remediation": "x",
        }
        for i in range(6000)
    ]
    review = ReadinessReview.model_validate_json(json.dumps(d))
    return lambda: validate_review(pack, review)


def _case_attach() -> Callable[[], object]:
    d = copy.deepcopy(READINESS)
    n = 20000
    d["consumers"] = [
        dict(
            d["consumers"][0],
            source_ids=[f"s{i}" for i in range(n)],
            citations=[dict(fw.IDENTITY, source_id=f"s{n - 1}")] * n,
        )
    ]
    review = ReadinessReview.model_validate_json(json.dumps(d))
    return lambda: validate_review(pack, review)


def _case_refs() -> Callable[[], object]:
    d = copy.deepcopy(CONTEXT)
    scan = d["sources"][1]
    n = 120000
    d["events"] = [_event(0, [EVENT_CITE] * (n // 40))]
    scan["event_scan"] = "events_identified"
    scan["event_ids"] = ["ev0"] * n
    review = SourceContextReview.model_validate_json(json.dumps(d))
    return lambda: validate_source_context(pack, review)


def _case_scans() -> Callable[[], object]:
    d = copy.deepcopy(CONTEXT)
    d["sources"] = [d["sources"][0]] * 1999 + [d["sources"][1]]
    d["events"] = [_event(i, [dict(EVENT_CITE, source_id="zz")]) for i in range(20000)]
    review = SourceContextReview.model_validate_json(json.dumps(d))
    return lambda: validate_source_context(pack, review)


SRC: dict[str, Any] = {
    "source_id": "s",
    "source_class": "issuer",
    "quality": "High",
    "period": None,
    "entity_covered": "x",
    "data_supplied": "x",
    "use": "x",
    "citations": [],
    "limitation": None,
}
CON: dict[str, Any] = {
    "module_id": "m",
    "status": "READY",
    "handoff_item": "x",
    "why_it_matters": "x",
    "gap": "x",
    "required_action": "x",
    "citations": [],
    "flag_topics": [],
}
CFL: dict[str, Any] = {
    "conflict_id": "c",
    "conflict": "x",
    "materiality": "Minor",
    "downstream_impact": "x",
    "citations": [],
}
CTR: dict[str, Any] = {
    "theme": "Key Uncertainties",
    "evidence": "x",
    "risk_mechanic": "x",
    "credit_implication": "x",
    "confidence": "Low",
    "countervailing_conflict_ids": ["c1"],
    "citations": [],
    "limitation": "x",
}
EMPTY: dict[str, list[Any]] = {
    name: []
    for name in (
        "sources",
        "company",
        "business_lines",
        "owners",
        "operating_drivers",
        "transactions",
        "events",
        "governance_and_sponsor",
        "capital_allocation",
        "acquisitions",
        "disclosure_items",
        "credit_translations",
        "conflicts",
        "gaps",
        "consumers",
    )
}
N = 16000


def _cp1a(**rows: list[Any]) -> bc.BusinessContextSubmission:
    return bc.BusinessContextSubmission.model_validate_json(json.dumps({**EMPTY, **rows}))


def _case_cp1a_sources() -> Callable[[], object]:
    s = _cp1a(sources=[dict(SRC, source_id=f"s{i % (N // 2)}") for i in range(N)])
    return lambda: bc._source_issues(pack, s)


def _case_cp1a_consumers() -> Callable[[], object]:
    s = _cp1a(consumers=[dict(CON, module_id=f"m{i % (N // 2)}") for i in range(N)])
    return lambda: bc._consumer_issues(pack, s)


def _case_cp1a_conflicts() -> Callable[[], object]:
    s = _cp1a(conflicts=[dict(CFL, conflict_id=f"c{i % (N // 2)}") for i in range(N)])
    return lambda: bc._shape_issues(s)


def _case_cp1a_translations() -> Callable[[], object]:
    s = _cp1a(
        conflicts=[dict(CFL, conflict_id=f"c{i}") for i in range(N)],
        credit_translations=[CTR] * N,
    )
    return lambda: bc._shape_issues(s)


KNOWN: dict[str, Any] = {}


def _known() -> Any:
    if not KNOWN:
        with tempfile.TemporaryDirectory() as tmp:
            w, p = fw.before_financials(Path(tmp) / "s")
            KNOWN["k"] = known_bindings(w._store, w._binding.ticket_id, "financials")
            KNOWN["p"] = p
    return KNOWN["k"]


def _financials() -> tuple[dict[str, Any], Any]:
    k = _known()
    return copy.deepcopy(fw.financials(KNOWN["p"])), k


def _run_prefill(doc: dict[str, Any], k: Any) -> Callable[[], object]:
    text = json.dumps(doc)
    return lambda: prefill(STEPS["financials"].schema, text, k, PREFILLED["financials"])


def _case_prefill_books() -> Callable[[], object]:
    doc, k = _financials()
    doc["financial"]["books"] = [{"book_id": f"b{i}", "periods": []} for i in range(16000)]
    doc["binding"]["books"] = [{"book_id": f"b{i}", "entity_id": "issuer"} for i in range(16000)]
    return _run_prefill(doc, k)


def _case_prefill_fx() -> Callable[[], object]:
    doc, k = _financials()
    b = doc["financial"]["books"][0]
    b["facilities"] = [{"facility_id": f"x{i}", "period_id": "p"} for i in range(8000)]
    b["facility_fx_conversions"] = [
        {"conversion_id": f"c{i}", "facility_id": f"f{i}", "period_id": "p"} for i in range(8000)
    ]
    return _run_prefill(doc, k)


def _case_prefill_fxrow() -> Callable[[], object]:
    doc, k = _financials()
    b = doc["financial"]["books"][0]
    row = copy.deepcopy(b["facilities"][0])
    row["carrying_value"]["citations"] = row["carrying_value"]["citations"] * 2000
    b["facilities"] = [row]
    b["facility_fx_conversions"] = [
        {
            "conversion_id": f"c{i}",
            "facility_id": row["facility_id"],
            "period_id": row["period_id"],
        }
        for i in range(400)
    ]
    return _run_prefill(doc, k)


def _with_scopes(k: Any, same_end: bool) -> Any:
    ctx = k.context
    fin = next(s for s in ctx.sources if s.classification == "financial")
    scope0 = fin.scopes[0]
    extra = tuple(
        scope0.model_copy(update={"scope_id": f"x{i}", **({} if same_end else {"end_date": None})})
        for i in range(2000 - len(fin.scopes))
    )
    sources = tuple(
        s.model_copy(update={"scopes": (*s.scopes, *extra)}) if s is fin else s for s in ctx.sources
    )
    return type(k)(k.pack_sha256, k.sources, k.step, ctx.model_copy(update={"sources": sources}))


def _case_prefill_scopes() -> Callable[[], object]:
    doc, k = _financials()
    period0 = doc["financial"]["books"][0]["periods"][0]
    short = {key: period0[key] for key in ("period_id", "period_type", "start_date", "end_date")}
    doc["financial"]["books"] = [{"book_id": f"b{i}", "periods": [short]} for i in range(8000)]
    doc["binding"]["books"] = [{"book_id": f"b{i}", "entity_id": "issuer"} for i in range(8000)]
    return _run_prefill(doc, _with_scopes(k, same_end=False))


def _case_prefill_periods() -> Callable[[], object]:
    doc, k = _financials()
    b = doc["financial"]["books"][0]
    period0 = b["periods"][0]
    b["periods"] = [dict(period0, period_id=f"q{i}") for i in range(4000)]
    return _run_prefill(doc, _with_scopes(k, same_end=True))


# The latent sites: CP-3 and CP-4 validators reached once those steps connect to a workflow.
_RUN = Run(
    run_id="r", issuer_id="i", issuer_name="I", as_of=date(2026, 1, 1), case_kind="synthetic"
)
_NO_MODULE = Module(run_id="r", issuer_id="i", as_of=date(2026, 1, 1), module_id="CP-X")
_UPSTREAM = cp3.Upstream((), (), _NO_MODULE, _NO_MODULE, _NO_MODULE, {}, ())
_EVIDENCE = cp3._Evidence({}, {}, ())
_BASIS: dict[str, Any] = {"cp2_refs": [], "quotes": []}


def _instruments(ids: list[str]) -> list[cp3.Instrument]:
    adapter = TypeAdapter(cp3.Instrument)
    return [
        adapter.validate_json(
            json.dumps(
                {
                    "facility_id": i,
                    "fundamental_view": "x",
                    "market_observation": "none",
                    "basis": _BASIS,
                    "limitation": None,
                }
            )
        )
        for i in ids
    ]


def _preference(ordering: list[str]) -> cp3.Preference:
    return TypeAdapter(cp3.Preference).validate_json(
        json.dumps(
            {
                "ordering": ordering,
                "rationale": "x",
                "basis": _BASIS,
                "confidence": "Low",
                "limitation": "x",
            }
        )
    )


def _relative_value(
    ids: list[str], ordering: list[str] | None = None
) -> cp3.RelativeValueSubmission:
    return cp3.RelativeValueSubmission.model_construct(
        instruments=tuple(_instruments(ids)),
        market_evidence=(),
        preference=_preference(ordering if ordering is not None else ids),
        risks=(),
        gaps=(),
    )


def _documents(ids: list[str]) -> cp4.CovenantInterpretationSubmission:
    rows = tuple(cp4.LegalDocument.model_construct(source_id=i) for i in ids)
    return cp4.CovenantInterpretationSubmission.model_construct(documents=rows)


def _case_cp4_documents() -> Callable[[], object]:
    s = _documents([f"d{i % (N // 2)}" for i in range(N)])
    return lambda: cp4._shape_issues(s)


def _case_cp3_instruments() -> Callable[[], object]:
    s = _relative_value([f"f{i % (N // 2)}" for i in range(N)], [])
    return lambda: cp3._instrument_issues(s, _UPSTREAM, _EVIDENCE, {})


def _case_cp3_ordering() -> Callable[[], object]:
    ids = [f"f{i}" for i in range(N // 2)]
    s = _relative_value(ids, ids[::-1] + ids)
    return lambda: cp3._preference_issues(s, _UPSTREAM, _EVIDENCE)


CASES: dict[str, tuple[Callable[[], Callable[[], object]], float]] = {
    "shape": (_case_shape, 0.5),
    "absence": (_case_absence, 0.1),
    "gaps": (_case_gaps, 1.5),
    "attach": (_case_attach, 0.5),
    "refs": (_case_refs, 2.0),
    "scans": (_case_scans, 1.0),
    "cp1a_sources": (_case_cp1a_sources, 0.2),
    "cp1a_consumers": (_case_cp1a_consumers, 0.2),
    "cp1a_conflicts": (_case_cp1a_conflicts, 0.2),
    "cp1a_translations": (_case_cp1a_translations, 0.2),
    "prefill_books": (_case_prefill_books, 2.5),
    "prefill_fx": (_case_prefill_fx, 1.5),
    "prefill_fxrow": (_case_prefill_fxrow, 1.0),
    "prefill_scopes": (_case_prefill_scopes, 2.0),
    "prefill_periods": (_case_prefill_periods, 1.5),
    "cp4_documents": (_case_cp4_documents, 0.2),
    "cp3_instruments": (_case_cp3_instruments, 0.2),
    "cp3_ordering": (_case_cp3_ordering, 0.2),
}


@pytest.mark.parametrize("case", list(CASES))
def test_post_binding_work_is_linear(case: str) -> None:
    build, bound = CASES[case]
    call = build()
    start = time.perf_counter()
    call()
    elapsed = time.perf_counter() - start
    assert elapsed <= bound, f"{case}: {elapsed:.3f}s over the {bound}s bound"


# --- end to end, through the workflow -------------------------------------------------------


def test_invalid_context_submit_is_linear_end_to_end(tmp_path: Path) -> None:
    w, _ = fw.start(tmp_path / "c")
    fw.read_sources(w)
    assert w.submit_review(fw.readiness(pack))["status"] == "valid"
    for source_id in ("identity", "financial"):
        w.invoke("read_pages", {"source_id": source_id, "first_page": 1, "last_page": 1})
    w.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})
    payload = json.dumps({"events": [{"citations": []}] * 4000}, separators=(",", ":"))
    start = time.perf_counter()
    out = w.submit_review(payload)
    elapsed = time.perf_counter() - start
    assert out["status"] != "valid"
    assert elapsed <= 2.0, f"{elapsed:.2f}s"


def test_absence_claim_submit_is_fast_end_to_end(tmp_path: Path) -> None:
    w, _ = fw.start(tmp_path / "c")
    fw.read_sources(w)
    d = json.loads(fw.readiness(pack))
    d["sources"][1]["limitations"] = [fw.LIMIT] + [
        f"pages {j + 1}-10000000 are missing" for j in range(8)
    ]
    start = time.perf_counter()
    w.submit_review(json.dumps(d))
    elapsed = time.perf_counter() - start
    assert elapsed <= 1.0, f"{elapsed:.2f}s"


# --- guards: the output is exactly what the pairwise code gave ----------------------------


def _pairwise_shape(error: ValidationError) -> tuple[str, ...]:
    """The pairwise rule: a container min-length error is dropped when another error sits
    inside that container."""
    errors = error.errors(include_url=False, include_input=False, include_context=False)

    def echoes(item: Any) -> bool:
        return (
            item["type"] == "too_short"
            and item["msg"].startswith(("Tuple should have at least", "List should have at least"))
            and any(
                len(other["loc"]) > len(item["loc"])
                and other["loc"][: len(item["loc"])] == item["loc"]
                for other in errors
            )
        )

    return tuple(
        f"{'.'.join(str(part) for part in item['loc']) or '(root)'}: {item['msg']}"
        for item in errors
        if not echoes(item)
    )


_KEYS: list[int | str] = ["a", "b", "events", "citations", "0", "1", "10", 0, 1, 10, 2]


def _loc(rng: random.Random) -> tuple[int | str, ...]:
    return tuple(rng.choice(_KEYS) for _ in range(rng.choice([0, 0, 1, 1, 2, 2, 3, 3, 4, 5, 6])))


def _synthetic_line(rng: random.Random, pool: list[tuple[int | str, ...]]) -> dict[str, Any]:
    r = rng.random()
    where = rng.choice(pool) if pool and rng.random() < 0.7 else _loc(rng)
    if r < 0.45:
        field_type = rng.choice(["Tuple", "List", "List", "Tuple", "Value", "Set", "Dictionary"])
        return {
            "type": "too_short",
            "loc": where,
            "input": None,
            "ctx": {
                "field_type": field_type,
                "min_length": rng.choice([1, 2, 4]),
                "actual_length": 0,
            },
        }
    if r < 0.75:
        ext = where + tuple(rng.choice(_KEYS) for _ in range(rng.choice([0, 1, 1, 2])))
        return {"type": "missing", "loc": ext, "input": None}
    inner = where + ((rng.choice(_KEYS),) if rng.random() < 0.5 else ())
    if rng.random() < 0.5:
        return {"type": "string_type", "loc": inner, "input": 1}
    return {"type": "string_too_long", "loc": inner, "input": "x", "ctx": {"max_length": 1}}


def test_shape_issues_equals_the_pairwise_reference() -> None:
    from pydantic import BaseModel, Field

    for seed in range(2000):
        rng = random.Random(seed)
        pool = [_loc(rng) for _ in range(rng.choice([1, 2, 3, 5]))]
        lines = [_synthetic_line(rng, pool) for _ in range(rng.choice([1, 2, 3, 4, 6, 9, 14]))]
        error = ValidationError.from_exception_data("T", lines)  # type: ignore[arg-type]
        assert shape_issues(error) == _pairwise_shape(error), seed

    class Inner(BaseModel):
        xs: Annotated[tuple[int, ...], Field(min_length=1)]
        ys: Annotated[list[str], Field(min_length=2)]

    class Outer(BaseModel):
        items: Annotated[tuple[Inner, ...], Field(min_length=1)]
        grid: Annotated[list[Annotated[list[int], Field(min_length=1)]], Field(min_length=1)]
        pairs: Annotated[
            tuple[Annotated[tuple[Inner, ...], Field(min_length=1)], ...], Field(min_length=1)
        ]

    crafted = [
        (
            TypeAdapter(Outer),
            '{"items":[{"xs":[1],"ys":[1]}],"grid":[["a"]],"pairs":[[{"xs":["a"],"ys":[1]}]]}',
        ),
        (TypeAdapter(Outer), '{"items":[{"xs":[],"ys":[]}],"grid":[[]],"pairs":[[]]}'),
        (
            TypeAdapter(Outer),
            '{"items":[{"xs":[1],"ys":["a"]},{"xs":[],"ys":[1,2]}],"grid":[[1],[]],"pairs":[[{"xs":[],"ys":[]}],[]]}',
        ),
        (TypeAdapter(Outer), '{"items":[],"grid":[],"pairs":[]}'),
    ]
    for adapter, text in crafted:
        try:
            adapter.validate_json(text)
        except ValidationError as error:
            assert shape_issues(error) == _pairwise_shape(error), text

    two = TypeAdapter(Annotated[tuple[int, ...], Field(min_length=2)])
    with pytest.raises(ValidationError) as caught:
        two.validate_json('["a"]')
    assert shape_issues(caught.value) == (
        "0: Input should be a valid integer, unable to parse string as an integer",
    )
    with pytest.raises(ValidationError) as caught:
        two.validate_json("[]")
    assert shape_issues(caught.value) == (
        "(root): Tuple should have at least 2 items after validation, not 0",
    )


@given(
    pages=st.sets(st.integers(min_value=-5, max_value=40), max_size=30),
    first=st.integers(min_value=-5, max_value=40),
    width=st.integers(min_value=0, max_value=60),
)
def test_retains_is_set_inclusion(pages: set[int], first: int, width: int) -> None:
    from deploy_vii.readiness import _retains

    last = first + width
    assert _retains(pages, first, last) == set(range(first, last + 1)).issubset(pages)


def _digest(parts: list[str]) -> str:
    return hashlib.sha256("".join(parts).encode()).hexdigest()


def _absence_outputs() -> list[str]:
    parts = []
    for seed in range(3000):
        rng = random.Random(seed)
        first = rng.choice([1, 2, 3, 5, 10])
        last = first + rng.choice([0, 1, 2, 3, 5, 8, 40])
        scope = rng.choice(
            [("financial",), ("identity",), (), ("financial", "identity"), ("nope",)]
        )
        out = absence_issues(
            pack,
            [
                (f"pages {first}-{last} are absent", scope),
                (f"page {first} to {last} not present", scope),
            ],
        )
        parts.append(repr(out))
    return parts


def _source_context_outputs() -> list[str]:
    parts = []
    for seed in range(300):
        rng = random.Random(seed)
        d = copy.deepcopy(CONTEXT)
        scan = d["sources"][rng.choice([0, 1])]
        d["events"] = [
            _event(rng.choice(range(6)), [EVENT_CITE] * rng.choice([1, 2]))
            for _ in range(rng.choice([0, 1, 3, 6]))
        ]
        for e in d["events"]:
            if rng.random() < 0.3:
                e["citations"] = [dict(EVENT_CITE, source_id="identity")]
        scan["event_scan"] = rng.choice(["events_identified", "no_events_identified"])
        scan["event_ids"] = [f"ev{rng.choice(range(7))}" for _ in range(rng.choice([0, 1, 2, 5]))]
        if rng.random() < 0.3:
            d["sources"].append(copy.deepcopy(d["sources"][1]))
        review = SourceContextReview.model_validate_json(json.dumps(d))
        issues = validate_source_context(pack, review)
        parts.append(repr(issues))
        if not issues:
            parts.append(source_context(pack, review).model_dump_json())
    return parts


def _validate_review_outputs() -> list[str]:
    parts = []
    c0 = READINESS["consumers"][0]
    mods = ["CP-1", "CP-1A", "CP-2", "CP-0", "X"]
    for seed in range(400):
        rng = random.Random(seed)
        d = copy.deepcopy(READINESS)
        d["consumers"] = [
            dict(
                c0,
                module_id=rng.choice(mods),
                readiness=r,
                limitations=[] if r == "READY" else [fw.LIMIT],
                source_ids=rng.sample(["identity", "financial", "zz"], rng.choice([0, 1, 2, 3])),
                missing_source="m" if r == "CONDITIONAL" else None,
            )
            for r in [
                rng.choice(["READY", "READY_WITH_LIMITATIONS", "CONDITIONAL"])
                for _ in range(rng.choice([0, 1, 2, 4]))
            ]
        ]
        d["gaps"] = [
            {
                "gap_id": f"g{rng.choice(range(4))}",
                "kind": "source",
                "severity": "minor",
                "description": "x",
                "affected_modules": rng.sample(mods, rng.choice([0, 1, 2, 3])),
                "remediation": "x",
            }
            for _ in range(rng.choice([0, 1, 3, 5]))
        ]
        parts.append(
            repr(validate_review(pack, ReadinessReview.model_validate_json(json.dumps(d))))
        )
    return parts


def _bare_pack() -> PreparedPack:
    return PreparedPack(run=_RUN, sources=())


def _business_context_outputs() -> list[str]:
    parts = []
    bare = _bare_pack()
    for name in ("sources", "consumers", "conflicts", "translate"):
        for seed in range(40):
            rng = random.Random(seed)
            n = rng.choice([0, 1, 2, 5, 30])
            ids = [rng.choice(["a", "b", "c1", "zz", "s0", "q"]) for _ in range(n)]
            empty: dict[str, Any] = {key: () for key in EMPTY}
            if name == "sources":
                rows = tuple(
                    bc.SourceUse.model_validate_json(json.dumps(dict(SRC, source_id=i)))
                    for i in ids
                )
                sub = bc.BusinessContextSubmission.model_construct(**{**empty, "sources": rows})
                parts.append(repr(bc._source_issues(bare, sub)))
            elif name == "consumers":
                rows_c = tuple(
                    bc.Consumer.model_validate_json(json.dumps(dict(CON, module_id=i))) for i in ids
                )
                sub = bc.BusinessContextSubmission.model_construct(**{**empty, "consumers": rows_c})
                parts.append(repr(bc._consumer_issues(bare, sub)))
            elif name == "conflicts":
                rows_f = tuple(
                    bc.Conflict.model_validate_json(json.dumps(dict(CFL, conflict_id=i)))
                    for i in ids
                )
                sub = bc.BusinessContextSubmission.model_construct(**{**empty, "conflicts": rows_f})
                parts.append(repr(bc._shape_issues(sub)))
            else:
                conflicts = tuple(
                    bc.Conflict.model_validate_json(json.dumps(dict(CFL, conflict_id=f"c{k}")))
                    for k in range(n)
                )
                ctr = bc.CreditTranslation.model_validate_json(
                    json.dumps(dict(CTR, countervailing_conflict_ids=["c1", "zz"]))
                )
                sub = bc.BusinessContextSubmission.model_construct(
                    **{**empty, "conflicts": conflicts, "credit_translations": (ctr,) * n}
                )
                parts.append(repr(bc._shape_issues(sub)))
    return parts


def _cp4_outputs() -> list[str]:
    parts = []
    for seed in range(60):
        rng = random.Random(seed)
        ids = [rng.choice(["a", "b", "c", "d1", "z"]) for _ in range(rng.choice([0, 1, 2, 5, 30]))]
        parts.append(repr(cp4._shape_issues(_documents(ids))))
    return parts


def _cp3_outputs() -> list[str]:
    parts = []
    for seed in range(60):
        rng = random.Random(seed)
        pool = ["a", "b", "c", "d", "e"]
        ids = [rng.choice(pool) for _ in range(rng.choice([0, 1, 2, 5, 12]))]
        ordering = [rng.choice(pool + ["q"]) for _ in range(rng.choice([0, 1, 2, 5, 12]))]
        s = _relative_value(ids, ordering)
        parts.append(repr(cp3._instrument_issues(s, _UPSTREAM, _EVIDENCE, {})))
        parts.append(repr(cp3._preference_issues(s, _UPSTREAM, _EVIDENCE)))
    return parts


OUTPUTS: dict[str, tuple[Callable[[], list[str]], str]] = {
    "absence": (
        _absence_outputs,
        "f5a31f1460a63e9ae4b708bb0c045c5f0894ddf79c66ca975bb6b1035ee25e07",
    ),
    "source_context": (
        _source_context_outputs,
        "a039f8b2c29ba2c3378857b7bfa335e03436282a9a0f03b891aa2ca31db05434",
    ),
    "validate_review": (
        _validate_review_outputs,
        "73f05ff2bf97ebc36d0846f43718ba8cba142570c2783d6cb481f3510adb518d",
    ),
    "business_context": (
        _business_context_outputs,
        "3eb2ca18a2e73b4b1f79d507b9f387effc9c197cab2292e8e32b37d0d470d883",
    ),
    "cp4_legal": (_cp4_outputs, "4bd238645003a5eeb3432805805cb536cdd2dde8d42b0c08db597f41108b34dd"),
    "cp3_relative_value": (
        _cp3_outputs,
        "7fa8bc3ceea617ee0d4663ab1e4b65587befee6c79efe8a134fbcc08646b4213",
    ),
}


@pytest.mark.parametrize("name", list(OUTPUTS))
def test_validator_outputs_are_pinned(name: str) -> None:
    produce, digest = OUTPUTS[name]
    assert _digest(produce()) == digest


def _prefill_outputs(seeds: int) -> list[str]:
    parts = []
    known = _known()
    base = fw.financials(KNOWN["p"])
    ctx = known.context
    fin = next(s for s in ctx.sources if s.classification == "financial")
    scope0 = fin.scopes[0]
    ids: list[Any] = ["term-loan", "f2", 1, 1.0, True, [1], {"a": 1}, None, "opening-2024", "p"]
    for seed in range(seeds):
        rng = random.Random(seed)
        doc = copy.deepcopy(base)
        k = known
        books = doc["financial"]["books"]
        b0 = books[0]
        for i in range(rng.choice([0, 0, 1, 2, 3])):
            if rng.random() < 0.5:
                nb = copy.deepcopy(b0)
            else:
                nb = {
                    "book_id": f"b{i}",
                    "periods": copy.deepcopy(b0["periods"][: rng.choice([0, 1, 3])]),
                }
            nb["book_id"] = rng.choice([f"b{i}", "consolidated", 7, None, f"b{i}"])
            books.append(nb)
        rows = doc["binding"]["books"]
        for book in books[1:]:
            r = rng.random()
            if r < 0.6:
                rows.append(
                    {
                        "book_id": book.get("book_id"),
                        "entity_id": rng.choice(["issuer", "issuer", "ghost", 3]),
                    }
                )
            elif r < 0.7:
                rows.append({"book_id": book.get("book_id"), "entity_id": "issuer"})
                rows.append({"book_id": book.get("book_id"), "entity_id": "issuer"})
            elif r < 0.8:
                rows.append("not a row")
        if rng.random() < 0.05:
            doc["binding"]["books"] = {"x": 1}
        for book in books:
            for p in book.get("periods", []):
                r = rng.random()
                if r < 0.15:
                    p["end_date"] = rng.choice(["2025-03-31", "2023-01-01", None, "bad"])
                elif r < 0.3:
                    p["start_date"] = rng.choice(["2025-01-01", None, "2024-01-01"])
                elif r < 0.4:
                    p["period_type"] = rng.choice(["PERIOD_END", "FY", "QUARTER", 5])
        if rng.random() < 0.6:
            fac = b0.setdefault("facilities", [])
            real = [(r["facility_id"], r["period_id"]) for r in fac]
            for _ in range(rng.choice([1, 2, 4])):
                if fac and rng.random() < 0.7:
                    row = copy.deepcopy(rng.choice(fac))
                else:
                    row = {"facility_id": None, "period_id": None}
                if rng.random() < 0.5:  # a later row with a real key and other content
                    row["facility_name"] = f"later {rng.random()}"
                else:
                    row["facility_id"] = rng.choice(ids)
                    row["period_id"] = rng.choice(ids)
                fac.append(row)
            b0["facility_fx_conversions"] = [
                {
                    "conversion_id": rng.choice(["c1", "c2", 9]),
                    **dict(
                        zip(
                            ("facility_id", "period_id"),
                            rng.choice(real)
                            if rng.random() < 0.6
                            else (rng.choice(ids), rng.choice(ids)),
                            strict=True,
                        )
                    ),
                }
                for _ in range(rng.choice([1, 2, 5]))
            ]
        if rng.random() < 0.6:
            add = []
            for i in range(rng.choice([1, 3, 6])):
                add.append(
                    scope0.model_copy(
                        update={
                            "scope_id": f"x{i}",
                            "period_kind": rng.choice(
                                ["historical_duration", "period_end", "forecast", "unspecified"]
                            ),
                            "start_date": rng.choice(
                                [scope0.start_date, None, rng.choice(fin.scopes).start_date]
                            ),
                            "end_date": rng.choice(
                                [scope0.end_date, None, rng.choice(fin.scopes).end_date]
                            ),
                            "currency": rng.choice([scope0.currency, "EUR"]),
                            "entity_perimeter": rng.choice([scope0.entity_perimeter, None]),
                            "entity_id": rng.choice([scope0.entity_id, scope0.entity_id, "other"]),
                        }
                    )
                )
            sources = tuple(
                s.model_copy(update={"scopes": (*s.scopes, *add)}) if s is fin else s
                for s in ctx.sources
            )
            k = type(known)(
                known.pack_sha256,
                known.sources,
                known.step,
                ctx.model_copy(update={"sources": sources}),
            )
        out = prefill(STEPS["financials"].schema, json.dumps(doc), k, PREFILLED["financials"])
        parts.append(repr((out.payload, out.paths, out.kinds, out.unbound, out.unset)))
    return parts


def test_prefill_outputs_are_pinned() -> None:
    assert _digest(_prefill_outputs(120)) == PREFILL_DIGEST


PREFILL_DIGEST = "91022018872a7c6b4fed63bd39f543510d8b0c2c6d3a05b17f8fc02cd9f86e1e"
