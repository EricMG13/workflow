"""Phase 5 Task 2: CP-4 cites draft legal sources and states the fixed draft limitation (B7).

The answer key is the frozen oracle `cases/context-attachments-owner/expected.json` (packs, CP-0
reviews and covenant submissions come from its manifest and submissions; nothing here derives an
expected value) and, for the executed-only guard, `cases/cp4-owner/expected.json`.
"""

import dataclasses
import importlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from deploy_vii import cp4_legal
from deploy_vii.contracts import Input, Module
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import build_readiness

ROOT = Path(__file__).resolve().parents[1]
rd: Any = importlib.import_module("test_readiness_draft")
tm: Any = importlib.import_module("test_method_cp4")
KEY = rd.EXPECTED
CASES = KEY["cases"]
DRAFT_LIMITATION = KEY["draft_limitation"]
NOT_LEGAL = KEY["texts"]["not_legal_source (frozen, cp4_legal.py:476-478)"]


def _cp0(pack: PreparedPack, case_id: str, *, also_draft: str | None = None) -> Module:
    review = rd.make_review(case_id, pack)
    if also_draft is not None:
        review = rd.reassess(review, also_draft, "draft")
    return build_readiness(pack, review)


def _cp1(pack: PreparedPack) -> Module:
    run = pack.run
    return Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id="CP-1",
        status="accepted",
        facts=(tm.cp1_fact(),),
    )


def _t4d1(case_id: str) -> dict[str, dict[str, str]]:
    """The oracle's T4D.1 rows; `draft-cited-other` shares `draft-ok`'s CP-0 head."""
    key = "draft-ok" if case_id == "draft-cited-other" else case_id
    rows: dict[str, dict[str, str]] = {
        k: v for k, v in CASES[key]["M"]["CP-4"]["T4D.1"].items() if isinstance(v, dict)
    }
    return rows


def _upstream(case_id: str) -> tuple[PreparedPack, cp4_legal.Upstream]:
    """The oracle's pack and the CP-4 view of its real CP-0 head (`cp4_upstream`), with the
    facilities and CP-1 figures of the executed-case stand-in (Stage 1 of the CP-4 tests)."""
    pack = rd.make_pack(case_id)
    real = cp4_legal.cp4_upstream(pack, _cp0(pack, case_id), _cp1(pack))
    base = tm.make_upstream("positive")
    expected = _t4d1(case_id)
    assert all(real.authority[k] == v["CP-0 authority"] for k, v in expected.items())
    assert set(real.legal_sources) == {
        k for k, v in expected.items() if v["Eligible for CP-4 citation"] == "Yes"
    }
    upstream = dataclasses.replace(base, authority=real.authority, legal_sources=real.legal_sources)
    return pack, upstream


def _submission(
    case_id: str, pack: PreparedPack, upstream: cp4_legal.Upstream
) -> cp4_legal.CovenantInterpretationSubmission:
    raw = json.dumps(rd.SUBMISSIONS["cases"][case_id]["cp4_legal_covenants"])
    text = raw.replace(tm.FIG, tm.select_metric(pack, upstream))
    return cp4_legal.CovenantInterpretationSubmission.model_validate_json(text)


def _inputs(pack: PreparedPack) -> Sequence[Input]:
    inputs: Sequence[Input] = tm.make_inputs("positive", pack)
    return inputs


def _issues(case_id: str) -> tuple[str, ...]:
    pack, upstream = _upstream(case_id)
    submission = _submission(case_id, pack, upstream)
    return tuple(
        cp4_legal.validate_covenant_interpretation(pack, submission, upstream, _inputs(pack))
    )


def _report(case_id: str) -> cp4_legal.CovenantInterpretationReport:
    pack, upstream = _upstream(case_id)
    submission = _submission(case_id, pack, upstream)
    return cp4_legal.covenant_interpretation(pack, submission, upstream, _inputs(pack))


# --- (a): the draft source is a CP-4 legal source -----------------------------------------------


def test_cp4_upstream_lists_the_draft_source() -> None:
    pack = rd.make_pack("draft-ok")
    upstream = cp4_legal.cp4_upstream(pack, _cp0(pack, "draft-ok"), _cp1(pack))
    assert upstream.authority["legal-draft"] == "draft"
    assert upstream.legal_sources == tuple(
        k for k, v in _t4d1("draft-ok").items() if v["Eligible for CP-4 citation"] == "Yes"
    )


def test_a_non_legal_source_assessed_draft_is_also_a_legal_source() -> None:
    """P5T2-R2 (P5T1-R8): no "legal sources only" rule; `draft` is citable as `filed` is today."""
    pack = rd.make_pack("draft-ok")
    cp0 = _cp0(pack, "draft-ok", also_draft="financial")
    upstream = cp4_legal.cp4_upstream(pack, cp0, _cp1(pack))
    assert upstream.legal_sources == ("financial", "legal-draft")


def test_the_authority_set_is_executed_filed_draft() -> None:
    assert cp4_legal.LEGAL_AUTHORITIES == frozenset({"executed", "filed", "draft"})
    assert cp4_legal.DRAFT_LIMITATION == DRAFT_LIMITATION


# --- (b): the covenant quoting the draft source validates; the Q2 text is frozen -----------------


def test_a_covenant_quoting_the_draft_source_validates() -> None:
    assert _issues("draft-ok") == ()


def test_a_quote_of_an_issuer_source_keeps_the_frozen_refusal_text() -> None:
    issues = _issues("draft-cited-other")
    want = NOT_LEGAL.format(path="capacity[3]", source_id="identity", authority="issuer")
    assert want in issues
    assert not any("legal-draft" in line for line in issues)
    assert "draft source" not in want


def test_the_frozen_q2_wording_is_byte_identical_in_the_source() -> None:
    text = Path(cp4_legal.__file__).read_text(encoding="utf-8")
    assert (
        '                f"{path}: {source_id} is not an executed or filed source (CP-0 authority "\n'
        "                f\"{upstream.authority.get(source_id, 'none')}, or the source is not ready)\"\n"
    ) in text
    assert (
        '            issues.append(f"{path}: {row.source_id} is not an executed or filed source")\n'
    ) in text


# --- (c), (d), (e): the limitation, the executed-only guard and the T4D.1 row -------------------


@pytest.mark.parametrize("case_id", ["draft-ok", "draft-uncited"])
def test_the_limitation_is_in_the_module_once_and_in_oracle_order(case_id: str) -> None:
    want = CASES[case_id]["M"]["CP-4"]["own_limitations"]
    limitations = _report(case_id).limitations
    assert list(limitations) == want["exact_order"]
    assert limitations.count(want["contains_once"]) == 1
    assert want["contains_once"] == DRAFT_LIMITATION
    assert len(limitations) == want["total_count"]


def test_executed_only_sources_add_no_limitation() -> None:
    inputs = tm.make_inputs_object("positive")
    report = cp4_legal.covenant_interpretation(
        inputs.pack, inputs.submission, inputs.upstream, inputs.inputs
    )
    assert list(report.limitations) == tm.EXPECTED["positive"]["CP-4"]["own_limitations"]
    assert DRAFT_LIMITATION not in report.limitations


def test_t4d1_row_of_the_draft_source_reads_draft_and_eligible() -> None:
    report = _report("draft-ok")
    table = next(t for t in report.tables if t.table_id == "T4D.1")
    text = {f.fact_id: f.text for f in report.facts}
    want = _t4d1("draft-ok")
    got = {row.label: [text[f] for f in row.fact_ids[:3]] for row in table.rows}
    assert got == {label: list(cells.values()) for label, cells in want.items()}
