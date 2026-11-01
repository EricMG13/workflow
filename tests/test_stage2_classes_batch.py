"""The Stage 2 defect classes over the batch modules (CP-1D, CP-2G, CP-1C, CP-3C, CP-2H, CP-4C).

The second half of `test_stage2_classes.py`, which holds the scope, the method, the store run and
the modules connected before the batch. Together the two files cover every registered core.
"""

import importlib
import json
from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from pathlib import Path
from typing import Any

import defect_classes as dc
import pytest
import test_connect_cp1c as tc_cp1c
import test_connect_cp1d as tc_cp1d
import test_connect_cp2g as tc_cp2g
import test_connect_cp2h as tc_cp2h
import test_connect_cp3c as tc_cp3c
import test_connect_cp4c as tc_cp4c
import test_owner_cp1b as to_cp1b
from test_stage2_classes import RETAINED, STORE_CASES, Built, Case, model_text_case, params

from deploy_vii.contracts import Fact
from deploy_vii.execution import Execution
from deploy_workflow import owner_workflow as ow
from deploy_workflow.owners import cp1b

earnings_host: Any = importlib.import_module("test_earnings_workflow")

# --- the stores and positive payloads, each from the module's own connect test --------------------


def _cp1b(root: Path) -> Built:
    """CP-0 (commanding CP-1B) and CP-1 (the earnings register of `test_owner_cp1b._producer`)
    settled through `begin`/`finish`, then CP-1B begun; the payload is the flat quarter pair."""
    pack = earnings_host.pack_for("E-QOQ-FLAT")  # the literal sources the register cites
    store = Execution.create(root / "store", pack)
    producer = to_cp1b._producer(opening=True)
    commands = tuple(
        Fact(
            fact_id=f"t8-{row.lower()}",
            label="Command",
            table_id="T8",
            row_id=row,
            field="exact_command",
            text=f"Run {row}",
        )
        for row in ("CP-1", "CP-1B")
    )
    register = producer.facts
    for module_id, facts in (("CP-0", commands), ("CP-1", register)):
        ticket = store.begin(module_id)
        module = producer.model_copy(
            update={
                "module_id": module_id,
                "run_id": pack.run.run_id,
                "issuer_id": pack.run.issuer_id,
                "as_of": pack.run.as_of,
                "status": "candidate",
                "inputs": ticket.inputs,
                "facts": facts,
                "limitations": producer.limitations if module_id == "CP-1" else (),
            }
        )
        store.finish(ticket.ticket_id, module.model_dump_json(), lambda _m: ())
    store.begin("CP-1B")
    payload = to_cp1b.review("q3-2025", "q4-2025")
    return store.directory, payload.model_dump_json()


def _cp1d(root: Path) -> Built:
    store, _ = tc_cp1d._settled_store(root, "positive")
    return store.directory, tc_cp1d._payload(store, "positive")


def _cp2g(root: Path) -> Built:
    store, _, _ = tc_cp2g.seed(root)
    return store.directory, json.dumps(tc_cp2g._payload())


def _cp1c(root: Path) -> Built:
    store, _ = tc_cp1c._settled_store(root, "positive")
    return store.directory, json.dumps(tc_cp1c._payload())


def _cp3c(root: Path) -> Built:
    store, _, attempt = tc_cp3c.seed(root)
    return store.directory, tc_cp3c.literal(store, attempt)


def _cp2h(root: Path) -> Built:
    store, _, _ = tc_cp2h.seed(root)
    return store.directory, tc_cp2h._submission(store).model_dump_json()


def _cp4c(root: Path) -> Built:
    store, _, _ = tc_cp4c.seed(root)
    return store.directory, json.dumps(tc_cp4c._payload())


# --- the verbatim sets (round 5 item 10), each pattern with its sink ------------------------------

_GAP_ROW = "Fact.text"
_GAP_LIMIT = "Fact.text; Module.limitations 'Gap (<severity>): <gap>'"

BATCH_CASES: Mapping[str, Case] = {
    # The CP-1B submission is two period ids and three literals: no model-written text, so no
    # verbatim path (`cp1b.EarningsDeltaOwnerReview`; the CP-2H case is empty likewise).
    "CP-1B": Case(_cp1b, {}),
    "CP-1D": Case(
        _cp1d,
        {
            ("assessments", "*", "limitation"): "Claim.limitation of T1D.2.<row>",
            ("overall", "limitation"): "Claim.limitation of T1D.1.assessment",
            ("gaps", "*", "gap"): f"T1D.7 {_GAP_LIMIT}",
            ("gaps", "*", "why_it_matters"): f"T1D.7 {_GAP_ROW}",
            ("gaps", "*", "affected_analysis"): f"T1D.7 {_GAP_ROW}",
            ("gaps", "*", "action"): f"T1D.7 {_GAP_ROW}",
        },
    ),
    "CP-2G": Case(
        _cp2g,
        {
            ("base_drivers", "revenue_growth", "limitation"): (
                "Claim.limitation of T2H.3.revenue_growth"
            ),
            ("base_drivers", "ebitda_margin", "limitation"): (
                "Claim.limitation of T2H.3.ebitda_margin"
            ),
            ("base_drivers", "dividends", "limitation"): "Claim.limitation of T2H.3.dividends",
            ("downside", "limitation"): "Claim.limitation of T2H.3.downside",
            ("assessment", "limitation"): "Claim.limitation of T2H.3.assessment",
        },
    ),
    "CP-1C": Case(
        _cp1c,
        {
            ("assessments", "*", "limitation"): (
                "Claim.limitation of T1C.1.<row>; Module.limitations 'Partly comparable peer "
                "included: <label>: <limitation>'"
            ),
            ("overall", "limitation"): "Claim.limitation of T1C.1.assessment",
            ("gaps", "*", "gap"): f"T1C.7 {_GAP_LIMIT}",
            ("gaps", "*", "why_it_matters"): f"T1C.7 {_GAP_ROW}",
            ("gaps", "*", "affected_analysis"): f"T1C.7 {_GAP_ROW}",
            ("gaps", "*", "action"): f"T1C.7 {_GAP_ROW}",
        },
    ),
    # The positive payload states `repricing`, so `repricing_absence.*` (also retained only) has
    # no path here.
    "CP-3C": Case(
        _cp3c,
        {
            ("repricing", "rationale"): RETAINED,
            ("paths", "*", "text"): "T3D.6 Fact.text",
            ("paths", "*", "credit_implication"): "T3D.6 Fact.text",
            ("paths", "*", "limitation"): "Module.limitations (own; a T3D.8 row)",
        },
    ),
    "CP-2H": Case(_cp2h, {}),
    "CP-4C": Case(
        _cp4c,
        {
            ("claims", "*", "limitation"): "Claim.limitation of its analyst claim",
            ("valuation", "*", "limitation"): "Claim.limitation of its analyst claim",
            ("fulcrum", "*", "limitation"): "Claim.limitation of its analyst claim",
            ("plan", "*", "limitation"): "Claim.limitation of its analyst claim",
            ("assessment", "limitation"): "Claim.limitation of the assessment claim",
            ("gaps", "*", "gap"): f"T4E.10 {_GAP_LIMIT}",
            ("gaps", "*", "why_it_matters"): f"T4E.10 {_GAP_ROW}",
            ("gaps", "*", "affected_analysis"): f"T4E.10 {_GAP_ROW}",
            ("gaps", "*", "action"): f"T4E.10 {_GAP_ROW}",
        },
    ),
}


def test_the_two_files_cover_every_registered_core_once() -> None:
    assert not set(STORE_CASES) & set(BATCH_CASES)
    assert set(STORE_CASES) | set(BATCH_CASES) == set(ow._CORES)
    assert set(ow._CORES) <= set(ow.OWNER_SPECS)


@pytest.mark.parametrize(
    ("module_id", "listed"),
    [
        ("CP-1C", tc_cp1c.CP1C_VERBATIM),
        ("CP-2G", tc_cp2g.CP2G_VERBATIM),
        ("CP-2H", tc_cp2h.CP2H_VERBATIM),
        ("CP-4C", tc_cp4c.CP4C_VERBATIM),
        ("CP-3C", {p for p in tc_cp3c.CP3C_VERBATIM if p[0] != "repricing_absence"}),
    ],
)
def test_a_set_equals_the_one_its_connect_test_states(
    module_id: str, listed: AbstractSet[dc.TextPath]
) -> None:
    assert set(BATCH_CASES[module_id].verbatim) == set(listed)


def test_cp1b_has_no_model_text_and_its_store_settles_the_flat_pair(tmp_path: Path) -> None:
    """CP-1B's submission is two period ids and three literals, so the model-text class has no
    path to check (`free_text_paths` is empty and `model_text_case` would refuse the case); what
    the case proves is that the store is real: the core settles the flat pair on it."""
    directory, payload = BATCH_CASES["CP-1B"].build(tmp_path)
    schema = ow._CORES["CP-1B"].SCHEMAS["earnings_delta"]
    assert dc.free_text_paths(payload, schema) == []
    store = Execution(directory)
    ticket = next(a.ticket_id for a in store.read().attempts if a.status == "pending")
    submitted = cp1b.submit(store, ticket, "earnings_delta", payload, None)
    assert submitted.journal.status == "finished" and not submitted.journal.issues


@pytest.mark.parametrize(
    "module_id", params({m: c for m, c in BATCH_CASES.items() if m != "CP-1B"}, {})
)
def test_model_text_is_journaled_except_on_the_verbatim_paths(
    module_id: str, tmp_path: Path
) -> None:
    assert model_text_case(module_id, BATCH_CASES[module_id], tmp_path) == []
