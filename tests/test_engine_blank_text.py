"""Round 12 B10 in the reused engines: Cf-only analyst text is `<path>: empty text`.

CP-3, CP-4 and CP-5 check their analyst text only in the reused engines. A text of whitespace and
Unicode format (`Cf`) characters is blank there, as `deploy_vii.prose.is_blank` defines it.
"""

import unicodedata
from datetime import date

from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from deploy_vii import (
    business_context,
    cp2_synthesis,
    cp3_relative_value,
    cp4_legal,
    cp5_integrity,
    cp6_committee,
    narrative,
    quality,
)
from deploy_vii.contracts import Module, Run
from deploy_vii.preparation import PreparedPack

BLANKS = ("\u200b", "\ufeff", "\u00ad", "\u2060", " \u200b\n")
PLAIN = "Leverage is tight."


def _cp3_submission(text: str) -> cp3_relative_value.RelativeValueSubmission:
    return cp3_relative_value.RelativeValueSubmission(
        instruments=(),
        market_evidence=(),
        preference=cp3_relative_value.Preference(
            ordering=(),
            rationale=PLAIN,
            basis=cp3_relative_value.Basis(cp2_refs=(), quotes=()),
            confidence="Low",
            limitation=None,
        ),
        risks=(
            cp3_relative_value.Risk(
                risk=text, mechanic=PLAIN, implication=PLAIN, severity="Minor", cp2_refs=()
            ),
        ),
        gaps=(),
    )


def _cp3(text: str) -> list[str]:
    return cp3_relative_value._text_issues(_cp3_submission(text), {}, ("Acme",))


def _cp3_public(text: str) -> list[str]:
    upstream = cp3_relative_value.Upstream(
        bound=(),
        current=(),
        cp0=_module(cp3_relative_value.CP0),
        cp1=_module(cp3_relative_value.CP1),
        cp2=_module(cp3_relative_value.CP2),
        optional={},
        inherited=(),
    )
    return list(
        cp3_relative_value.validate_relative_value(_pack(), _cp3_submission(text), upstream)
    )


def _cp4(text: str) -> list[str]:
    pack = PreparedPack(
        run=Run(
            run_id="run-1",
            issuer_id="acme",
            issuer_name="Acme",
            as_of=date(2026, 1, 1),
            case_kind="synthetic",
        ),
        sources=(),
    )
    upstream = cp4_legal.Upstream(
        cp0_sha256="0" * 64,
        cp1_sha256="1" * 64,
        cp1_status="blocked",
        authority={},
        legal_sources=(),
        facilities={},
        facts=(),
        rows={},
        cp1_gaps=(),
    )
    submission = cp4_legal.CovenantInterpretationSubmission(
        documents=(),
        covenants=(),
        capacity=(),
        red_flags=(
            cp4_legal.RedFlag(
                flag=text, mechanic=PLAIN, implication=PLAIN, severity="Minor", citations=()
            ),
        ),
        protection_score=cp4_legal.ProtectionScore(
            rating="Weak", rationale=PLAIN, basis=PLAIN, citations=(), limitation=None
        ),
        gaps=(),
    )
    return list(cp4_legal.validate_covenant_interpretation(pack, submission, upstream, ()))


def _cp5(text: str) -> list[str]:
    return cp5_integrity._text_issues("review.rationale", text, ("Acme",))


def _cp5_public(text: str) -> list[str]:
    scope = cp5_integrity.ReviewScope(pack=_pack(), inputs=(), heads=())
    submission = cp5_integrity.IntegritySubmission(
        claim_reviews=(),
        contradictions=(),
        gaps=(
            cp5_integrity.IntegrityGap(
                gap=text, why_it_matters=PLAIN, affected_modules=(), severity="Minor", action=PLAIN
            ),
        ),
    )
    return list(cp5_integrity.validate_integrity(scope, submission))


def _credit_translation_submission(
    evidence: str,
) -> business_context.BusinessContextSubmission:
    return business_context.BusinessContextSubmission(
        sources=(),
        company=(),
        business_lines=(),
        owners=(),
        operating_drivers=(),
        transactions=(),
        events=(),
        governance_and_sponsor=(),
        capital_allocation=(),
        acquisitions=(),
        disclosure_items=(),
        credit_translations=(
            business_context.CreditTranslation(
                theme="Key Uncertainties",
                evidence=evidence,
                risk_mechanic=PLAIN,
                credit_implication=PLAIN,
                confidence="Low",
                countervailing_conflict_ids=(),
                citations=(),
                limitation=PLAIN,
            ),
        ),
        conflicts=(),
        gaps=(),
        consumers=(),
    )


def _quality_rationale(text: str) -> object:
    return quality.ClaimAssessment(claim_id="c1", material=True, evidence=(), rationale=text)


def _pack() -> PreparedPack:
    return PreparedPack(
        run=Run(
            run_id="run-1",
            issuer_id="acme",
            issuer_name="Acme",
            as_of=date(2026, 1, 1),
            case_kind="synthetic",
        ),
        sources=(),
    )


def _module(module_id: str) -> Module:
    return Module(run_id="run-1", issuer_id="acme", as_of=date(2026, 1, 1), module_id=module_id)


def _cp2(text: str) -> list[str]:
    submission = cp2_synthesis.CreditSynthesisSubmission(
        assessment=cp2_synthesis.Assessment(
            rationale=PLAIN,
            category="Insufficient Information",
            confidence="Low",
            cp1a_refs=(),
            limitation=PLAIN,
        ),
        thesis=cp2_synthesis.Thesis(
            text=PLAIN, category="Insufficient Information", cp1a_refs=(), limitation=PLAIN
        ),
        strengths=(),
        weaknesses=(),
        key_findings=(cp2_synthesis.Finding(text=text, cp1a_refs=()),),
        risks=(),
        gaps=(),
    )
    upstream = cp2_synthesis.Upstream(
        bound=(),
        current=(),
        cp1=_module(cp2_synthesis.CP1),
        cp1a=_module(cp2_synthesis.CP1A),
        inherited=(),
    )
    return list(cp2_synthesis.validate_credit_synthesis(_pack(), submission, upstream))


def _cp6_submission(text: str) -> cp6_committee.CommitteeSubmission:
    basis = cp6_committee.Basis(cp2_refs=(), cp3_refs=(), cp5_refs=())
    return cp6_committee.CommitteeSubmission(
        recommendation=cp6_committee.Recommendation(
            action_bias="Neutral",
            rationale=PLAIN,
            conditions=PLAIN,
            confidence="Low",
            limitation=None,
            basis=basis,
        ),
        thesis_challenges=(),
        recovery_view=(),
        risks=(
            cp6_committee.Risk(
                risk=text, mechanic=PLAIN, implication=PLAIN, severity="Minor", basis=basis
            ),
        ),
        gaps=(),
    )


def _cp6(text: str) -> list[str]:
    return cp6_committee._text_issues(_cp6_submission(text), {}, ("Acme",))


def _cp6_public(text: str) -> list[str]:
    upstream = cp6_committee.Upstream(
        bound=(),
        current=(),
        cp0=_module("CP-0"),
        cp1=_module("CP-1"),
        cp2=_module("CP-2"),
        cp3=_module("CP-3"),
        cp5=_module("CP-5"),
        optional={},
        blocked=frozenset(),
        inherited=(),
    )
    return list(cp6_committee.validate_committee(_pack(), _cp6_submission(text), upstream))


def _business_context(text: str) -> list[str]:
    submission = business_context.BusinessContextSubmission(
        sources=(),
        company=(
            business_context.CompanyFact(
                aspect="sector",
                text=text,
                category="Insufficient Information",
                citations=(),
                limitation=PLAIN,
            ),
        ),
        business_lines=(),
        owners=(),
        operating_drivers=(),
        transactions=(),
        events=(),
        governance_and_sponsor=(),
        capital_allocation=(),
        acquisitions=(),
        disclosure_items=(),
        credit_translations=(),
        conflicts=(),
        gaps=(),
        consumers=(),
    )
    return list(business_context.validate_business_context(_pack(), submission))


def _where(issues: list[str], where: str) -> list[str]:
    return [issue for issue in issues if issue.startswith(where)]


def test_cp3_cf_only_text_is_empty_text():
    for text in BLANKS:
        assert _where(_cp3(text), "risks[0].risk") == ["risks[0].risk: empty text"], repr(text)


def test_cp4_cf_only_text_is_empty_text():
    for text in BLANKS:
        got = _where(_cp4(text), "red_flags[0].flag")
        assert got == ["red_flags[0].flag: empty text"], repr(text)


def test_cp5_cf_only_text_is_empty_text():
    for text in BLANKS:
        assert _cp5(text) == ["review.rationale: empty text"], repr(text)


def test_ordinary_text_is_unchanged():
    assert _where(_cp3(PLAIN), "risks[0].risk") == []
    assert _where(_cp4(PLAIN), "red_flags[0].flag") == []
    assert _cp5(PLAIN) == []
    # An empty or whitespace-only text was empty text before and stays so.
    for text in ("", "  \n\t"):
        assert _where(_cp3(text), "risks[0].risk") == ["risks[0].risk: empty text"]
        assert _where(_cp4(text), "red_flags[0].flag") == ["red_flags[0].flag: empty text"]
        assert _cp5(text) == ["review.rationale: empty text"]


@given(st.text())
def test_is_blank_is_whitespace_controls_format_or_invisible_characters(text):
    from deploy_vii.prose import is_blank

    invisible = (
        {0x034F, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x3164, 0xFFA0, 0x2800}
        | set(range(0x180B, 0x1810))
        | set(range(0xFE00, 0xFE10))
        | set(range(0xE0100, 0xE01F0))
    )
    expected = all(
        c.isspace() or unicodedata.category(c) in {"Cc", "Cf"} or ord(c) in invisible
        for c in text
    )
    assert is_blank(text) is expected
    assert is_blank("") is True


def test_cp2_cf_only_text_is_empty_text():
    for text in BLANKS:
        got = _where(_cp2(text), "key_findings[0].text")
        assert got == ["key_findings[0].text: empty text"], repr(text)
    assert _where(_cp2(PLAIN), "key_findings[0].text") == []


def test_cp6_cf_only_text_is_empty_text():
    for text in BLANKS:
        assert _where(_cp6(text), "risks[0].risk") == ["risks[0].risk: empty text"], repr(text)
    assert _where(_cp6(PLAIN), "risks[0].risk") == []


def test_business_context_cf_only_text_is_empty_text():
    for text in BLANKS:
        got = _where(_business_context(text), "company[0].text")
        assert got == ["company[0].text: empty text"], repr(text)
    assert _where(_business_context(PLAIN), "company[0].text") == []


def test_narrative_cf_only_prose_is_refused():
    for text in BLANKS:
        try:
            narrative.ProsePart(text=text)
        except ValidationError as error:
            assert "Narrative prose must be nonblank" in str(error), repr(text)
        else:
            raise AssertionError(f"Cf-only prose accepted: {text!r}")
    assert narrative.ProsePart(text=PLAIN).text == PLAIN


def test_public_validators_refuse_cf_only_text():
    for text in BLANKS:
        assert _where(_cp3_public(text), "risks[0].risk") == ["risks[0].risk: empty text"]
        assert _where(_cp5_public(text), "gaps[0].gap") == ["gaps[0].gap: empty text"]
        assert _where(_cp6_public(text), "risks[0].risk") == ["risks[0].risk: empty text"]
    assert _where(_cp3_public(PLAIN), "risks[0].risk") == []
    assert _where(_cp5_public(PLAIN), "gaps[0].gap") == []
    assert _where(_cp6_public(PLAIN), "risks[0].risk") == []


def test_quality_cf_only_explanation_is_refused():
    for text in (*BLANKS, "   "):
        try:
            _quality_rationale(text)
        except ValidationError as error:
            assert "QA explanations must be nonblank" in str(error), repr(text)
        else:
            raise AssertionError(f"blank QA explanation accepted: {text!r}")
    assert (
        quality.ClaimAssessment(
            claim_id="c1", material=True, evidence=(), rationale=PLAIN
        ).rationale
        == PLAIN
    )


def test_business_context_cf_only_evidence_is_not_populated():
    rule = "cp1a.credit_translation_has_evidenced_row"
    whitespace = business_context.validate_business_context(
        _pack(), _credit_translation_submission("   ")
    )
    assert any(issue.startswith(rule) for issue in whitespace)
    for text in BLANKS:
        got = business_context.validate_business_context(
            _pack(), _credit_translation_submission(text)
        )
        assert any(issue.startswith(rule) for issue in got), repr(text)
    plain = business_context.validate_business_context(
        _pack(), _credit_translation_submission(PLAIN)
    )
    assert not any(issue.startswith(rule) for issue in plain)
