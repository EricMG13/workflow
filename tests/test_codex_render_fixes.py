"""Stage 8 T2: owner text that rendered wrong (Codex findings H06, H07)."""

import copy
import json
import re

import pytest
import test_connect_cp8 as connect8
import test_method_cp2h as m2h
import test_method_cp8 as m8

from deploy_vii import prose, render
from deploy_vii.contracts import Claim, Fact, ModuleView, View
from deploy_workflow.owners import cp2h, cp8

TOKEN = "{T2R.4.t01.headroom|x}"
SPELLED = "Headroom of 1.08x is short."


def _cp2h_with_token_gap() -> tuple[cp2h.TriggerReport, str]:
    payload = copy.deepcopy(m2h.raw_payload("positive"))
    payload["gaps"][0]["gap"] = f"Headroom of {TOKEN} is short."
    inputs = m2h.inputs("positive", payload)
    assert not cp2h.validate(inputs)
    return cp2h.compute(inputs), payload["gaps"][0]["severity"]


def test_h06_gap_limitation_is_the_resolved_text() -> None:
    report, severity = _cp2h_with_token_gap()
    assert f"Gap ({severity}): {SPELLED}" in report.own_limitations
    assert [x for x in report.own_limitations if "{T2R" in x] == []


def test_h06_no_token_reaches_the_rendered_limitations() -> None:
    report, severity = _cp2h_with_token_gap()
    facts = [c.fact for c in report.cells]
    facts += [cp2h._moved(r.fact, cp2h.CP1_REFERENCES[0], r.row_id) for r in report.cp1_references]
    facts += [
        cp2h._moved(r.fact, cp2h.CP2G_REFERENCES[0], r.row_id) for r in report.cp2g_references
    ]
    claims = tuple(
        Claim(claim_id=c.claim_id, text=c.text, citations=c.citations, limitation=c.limitation)
        for c in report.claims
    )
    module = ModuleView(
        module_id="CP-2H",
        title="CP-2H",
        aliases=(),
        status="restricted",
        artifact_sha256="c" * 64,
        facts=tuple(facts),
        tables=report.tables,
        claims=claims,
        limitations=report.own_limitations,
    )
    assert not prose.prose_issues(module)
    html = render.render(View(run=connect8._run("positive"), mode="accepted", modules=(module,)))
    found = re.search(r'<script[^>]*id="report-data"[^>]*>(.*?)</script>', html, re.DOTALL)
    assert found is not None
    data = json.loads(found.group(1))
    limitations = data["modules"][0]["limitations"]
    assert f"Gap ({severity}): {SPELLED}" in limitations
    assert [x for x in limitations if "{T2R" in x] == []


@pytest.mark.parametrize("value", ["None", "none", "null", "nan"])
def test_h07_null_spellings_are_refused(value: str) -> None:
    payload = copy.deepcopy(m8.SUBMISSIONS["positive"])
    payload["synthesis"]["text"] = value
    issues = cp8.validate_ledger(
        submission=m8.submission(payload),
        upstream=m8.upstream("positive"),
        pack=m8.pack("positive"),
    )
    assert issues == ("synthesis.text: text is a null spelling",)


def test_h07_normal_text_is_still_accepted() -> None:
    payload = copy.deepcopy(m8.SUBMISSIONS["positive"])
    payload["synthesis"]["text"] = "No change."
    issues = cp8.validate_ledger(
        submission=m8.submission(payload),
        upstream=m8.upstream("positive"),
        pack=m8.pack("positive"),
    )
    assert issues == ()


def _bound_of(case: str) -> dict[str, Fact]:
    inputs = m2h.inputs(case)
    ratings = cp2h.ratings_source(inputs.pack)
    source = cp2h.parse_ratings(cp2h.source_pages(ratings))
    book, _ = cp2h._compose(ratings, source, inputs.upstream, None)
    return cp2h._bound(book, inputs.upstream)


def test_h06_gap_text_naming_an_unsettled_fact_is_a_validation_issue() -> None:
    ref = next(k for k, f in sorted(_bound_of("gap").items()) if f.status != "known")
    payload = copy.deepcopy(m2h.raw_payload("gap"))
    payload["gaps"][0]["gap"] = f"Coverage is missing for [{ref}]."
    issues = cp2h.validate(m2h.inputs("gap", payload))
    assert issues == (f"gaps[0].gap: reference {ref} names a fact that is not settled",)


def test_h06_gap_limitation_spells_a_chip_naming_a_settled_fact() -> None:
    ref, fact = next(
        (k, f)
        for k, f in sorted(_bound_of("positive").items())
        if f.status == "known" and f.text is not None and f.amount is None
    )
    payload = copy.deepcopy(m2h.raw_payload("positive"))
    payload["gaps"][0]["gap"] = f"Coverage of [{ref}] is noted."
    inputs = m2h.inputs("positive", payload)
    assert cp2h.validate(inputs) == ()
    severity = payload["gaps"][0]["severity"]
    expected = f"Gap ({severity}): Coverage of {fact.text} is noted."
    assert expected in cp2h.compute(inputs).own_limitations


def _gap_validate(text: str) -> tuple[str, ...]:
    payload = copy.deepcopy(m2h.raw_payload("gap"))
    payload["gaps"][0]["gap"] = text
    return cp2h.validate(m2h.inputs("gap", payload))


def _unsettled_ref() -> str:
    return next(k for k, f in sorted(_bound_of("gap").items()) if f.status != "known")


def test_gap_text_reports_an_unsettled_reference_beside_a_prohibited_conclusion() -> None:
    ref = _unsettled_ref()
    issues = _gap_validate(f"Our rating is weak [{ref}].")
    assert issues == (
        'gaps[0].gap: prohibited conclusion (rating call): "our rating"',
        f"gaps[0].gap: reference {ref} names a fact that is not settled",
    )


def test_gap_text_with_an_unterminated_brace_returns_issues_without_raising() -> None:
    # Guard (passes at HEAD): the syntax error is `_prose`'s to report; the settled check must not raise.
    ref = _unsettled_ref()
    issues = _gap_validate(f"Coverage [{ref}] is missing {{")
    assert issues
    assert not any("is not settled" in x for x in issues)


def test_gap_text_reports_an_unsettled_reference_beside_an_unbound_one() -> None:
    ref = _unsettled_ref()
    issues = _gap_validate(f"Coverage is missing [{ref}] and [T2R.2.zz.nope].")
    assert f"gaps[0].gap: reference {ref} names a fact that is not settled" in issues
    assert any("T2R.2.zz.nope" in x for x in issues)
