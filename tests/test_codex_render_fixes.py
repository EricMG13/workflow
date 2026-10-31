"""Stage 8 T2: owner text that rendered wrong (Codex findings H06, H07)."""

import copy
import json
import re

import pytest
import test_connect_cp8 as connect8
import test_method_cp2h as m2h
import test_method_cp8 as m8

from deploy_vii import prose, render
from deploy_vii.contracts import Claim, ModuleView, View
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
    found = re.search(r'<script[^>]*id="report-data"[^>]*>(.*?)</script>', html, re.S)
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
