from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from deploy_vii.contracts import Citation, Fact, Module
from deploy_workflow.model_testing.cases import GoldenCase, checker
from deploy_workflow.model_testing.mapping import Locator, Mapping, MappingEntry, Unmapped
from deploy_workflow.model_testing.scoring import (
    JUDGMENT_MODULES,
    ModuleScore,
    score_module,
)

GOLDENS = Path(__file__).resolve().parents[1] / "cases" / "goldens"
SHA = "a" * 40
H = "b" * 64

IHRT_BILLIONS = "CP-2.debt_stack_pre_exchange.DebtMarketValue.market_value.2024-09-30"
IHRT_PCT = "CP-4.exchange_total.Participation.participation_pct_of_principal.2024-12-20"
LTH_THOUSANDS = (
    "CP-2.debt_stack.total_debt_principal_sum_of_components_excluding_fair_value_adjustment"
    ".principal_total.2025-06-30"
)
LTH_GUARANTOR = "CP-2.obligors.subsidiary_guarantor_ltf_club_operations_company_inc.name"
NATL_TERM_B = "CP-2.debt_stack.term_b.principal_outstanding.2025-09-30"
LTH_CONFLICT = "CP-4.amendment_13.13th_amendment.incremental_commitments_split"


def _golden(case_id: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (GOLDENS / case_id / "module_golden.json").read_text(encoding="utf-8")
    )
    return data


def _case(case_id: str, *fact_ids: str) -> GoldenCase:
    golden = _golden(case_id)
    by_id = {f["fact_id"]: f for f in golden["facts"]}
    return GoldenCase(
        case_id=case_id,
        pathway=golden["pathway"],
        case_dir=GOLDENS / case_id,
        context_path=GOLDENS / case_id / "context.json",
        golden=MappingProxyType({}),
        facts=MappingProxyType({fid: by_id[fid] for fid in fact_ids}),
        out_of_plan=MappingProxyType({}),
        financial_gold_path=Path("g.json"),
        financial_gold_sha256="0" * 64,
    )


def _entry(fid: str, module: str, **kw: Any) -> MappingEntry:
    return MappingEntry(
        fact_id=fid,
        module=module,
        locator=Locator(
            table_id="t", row_id=fid.replace(".", "_")[:60], field="f", period="2025-06-30"
        ),
        **kw,
    )


def _mapping(
    case: GoldenCase,
    entries: list[MappingEntry],
    unmapped: list[Unmapped] | None = None,
    modules: tuple[str, ...] = ("CP-2",),
) -> Mapping:
    return Mapping(
        schema_version="golden-mapping/1",
        case_id=case.case_id,
        preparer="alice",
        reviewer="bob",
        module_commits={m: SHA for m in modules},
        entries=tuple(entries),
        unmapped=tuple(unmapped or ()),
    )


def _cite() -> tuple[Citation, ...]:
    return (Citation(source_id="s", source_sha256=H, locator="p1", quote="q"),)


def _fact(entry: MappingEntry, *, traced: bool = True, **kw: Any) -> Fact:
    loc = entry.locator
    base: dict[str, Any] = {
        "fact_id": "f-" + loc.row_id,
        "label": "x",
        "table_id": loc.table_id,
        "row_id": loc.row_id,
        "field": loc.field,
        "period": loc.period,
    }
    if traced:
        base["citations"] = _cite()
    if kw.get("amount") is not None:
        base["unit"] = "USD"
    if kw.get("status", "known") != "known":
        base["limitation"] = "not available"
    base.update(kw)
    return Fact(**base)


def _module(facts: list[Fact], module_id: str = "CP-2", **kw: Any) -> Module:
    return Module(
        run_id="r",
        issuer_id="i",
        as_of=date(2025, 1, 1),
        module_id=module_id,
        facts=tuple(facts),
        **kw,
    )


def _score(
    module: Module | None,
    case: GoldenCase,
    mapping: Mapping,
    head: str = "accepted",
    upstream: frozenset[str] = frozenset(),
    refusal: tuple[str, ...] = (),
    module_id: str = "CP-2",
) -> ModuleScore:
    return score_module(module, module_id, head, case, mapping, upstream, refusal)


def _one(fid: str, case_id: str, **fact_kw: Any) -> tuple[ModuleScore, GoldenCase, MappingEntry]:
    case = _case(case_id, fid)
    entry = _entry(fid, "CP-2")
    module = _module([_fact(entry, **fact_kw)])
    return _score(module, case, _mapping(case, [entry])), case, entry


IHRT = "ihrt-distressed-restructuring"
LTH = "lth-covenant-refinancing"
NATL = "natl-portfolio-decision"


def test_millions_vs_units_match() -> None:
    # golden IHRT 3.9 billions; module amount 3900000000 at scale 1
    score, _, _ = _one(IHRT_BILLIONS, IHRT, amount=Decimal(3900000000))
    fs = score.facts[0]
    assert fs.outcome == "match"
    assert fs.expected == "3900000000"
    assert fs.observed == "3900000000"
    assert score.passed


def test_thousands_vs_scale_match() -> None:
    # golden LTH 1534149 thousands; module 1534.149 at scale 1000000 (amount x scale, as
    # cp5_integrity.py:371 and the Fact contract define it)
    score, _, _ = _one(LTH_THOUSANDS, LTH, amount=Decimal("1534.149"), scale=Decimal(1000000))
    assert score.facts[0].outcome == "match"
    assert score.facts[0].expected == "1534149000"
    assert score.passed


def test_scale_mismatch_is_a_mismatch() -> None:
    score, _, _ = _one(LTH_THOUSANDS, LTH, amount=Decimal("1534.149"), scale=Decimal(1000))
    assert score.facts[0].outcome == "mismatch"
    assert not score.passed


def test_fewer_golden_decimals() -> None:
    # golden 92.2 percent; module 92.21 -> half-up to one place is 92.2
    score, _, _ = _one(IHRT_PCT, IHRT, amount=Decimal("0.9221"), unit="PERCENT")
    assert score.facts[0].outcome == "match"
    score, _, _ = _one(IHRT_PCT, IHRT, amount=Decimal("0.9225"), unit="PERCENT")
    assert score.facts[0].outcome == "mismatch"  # 92.25 rounds half-up to 92.3
    score, _, _ = _one(IHRT_PCT, IHRT, amount=Decimal("0.9215"), unit="PERCENT")
    assert score.facts[0].outcome == "match"  # half-up, not banker's: 92.15 -> 92.2


def test_entity_case_insensitive() -> None:
    score, _, _ = _one(LTH_GUARANTOR, LTH, text="LTF CLUB OPERATIONS COMPANY, INC.")
    assert score.facts[0].outcome == "match"
    score, _, _ = _one(LTH_GUARANTOR, LTH, text="  LTF Club   Operations Company, Inc. ")
    assert score.facts[0].outcome == "match"
    score, _, _ = _one(LTH_GUARANTOR, LTH, text="Someone Else")
    assert score.facts[0].outcome == "mismatch"


def test_subject_alias_matches() -> None:
    case = _case(LTH, LTH_GUARANTOR)
    entry = _entry(LTH_GUARANTOR, "CP-2", subject_aliases=("LTF Club Ops",))
    module = _module([_fact(entry, text="ltf club ops")])
    assert _score(module, case, _mapping(case, [entry])).facts[0].outcome == "match"


def test_invented_against_missing() -> None:
    # NATL term_b principal is golden-missing; a known 320 is invented
    score, _, _ = _one(NATL_TERM_B, NATL, amount=Decimal(320), scale=Decimal(1000000))
    assert score.facts[0].outcome == "invented"
    assert score.facts[0].expected is None
    assert score.facts[0].observed == "320000000"
    assert score.passed is False


def test_missing_gap_ok_when_absent_or_not_known() -> None:
    case = _case(NATL, NATL_TERM_B)
    entry = _entry(NATL_TERM_B, "CP-2")
    mapping = _mapping(case, [entry])
    absent = _score(_module([]), case, mapping)
    assert absent.facts[0].outcome == "gap_ok"
    assert absent.passed
    gap = _score(_module([_fact(entry, status="missing")]), case, mapping)
    assert gap.facts[0].outcome == "gap_ok"


def test_conflict_ok() -> None:
    case = _case(LTH, LTH_CONFLICT)
    entry = _entry(LTH_CONFLICT, "CP-2")
    mapping = _mapping(case, [entry])
    conflicting = _score(_module([_fact(entry, status="conflicting")]), case, mapping)
    assert conflicting.facts[0].outcome == "conflict_ok"
    # known with one of the evidenced values ($277,500,000.00) and a limitation
    ok = _module([_fact(entry, amount=Decimal(277500000), limitation="two values")])
    assert _score(ok, case, mapping).facts[0].outcome == "conflict_ok"
    no_limit = _module([_fact(entry, amount=Decimal(277500000))])
    assert _score(no_limit, case, mapping).facts[0].outcome == "mismatch"
    other = _module([_fact(entry, amount=Decimal(5), limitation="two values")])
    assert _score(other, case, mapping).facts[0].outcome == "mismatch"


def test_inherited_excluded() -> None:
    case = _case(LTH, LTH_THOUSANDS)
    entry = _entry(LTH_THOUSANDS, "CP-2", depends_on=("up.1",))
    module = _module([_fact(entry, amount=Decimal(1))])
    mapping = _mapping(case, [entry])
    inherited = _score(module, case, mapping, upstream=frozenset({"up.1"}))
    assert inherited.facts[0].outcome == "inherited"
    assert inherited.passed is True
    plain = _score(module, case, mapping, upstream=frozenset({"other"}))
    assert plain.facts[0].outcome == "mismatch"
    assert plain.passed is False


def test_untraced_fails() -> None:
    score, _, entry = _one(IHRT_BILLIONS, IHRT, amount=Decimal(3900000000), traced=False)
    assert score.facts[0].outcome == "match"
    assert score.untraced == ("f-" + entry.locator.row_id,)
    assert score.passed is False
    # a calculation id counts as a trace
    ok, _, _ = _one(
        IHRT_BILLIONS, IHRT, amount=Decimal(3900000000), traced=False, calculation_id="c1"
    )
    assert ok.untraced == ()
    assert ok.passed


def test_unscored_counts_traced_unmapped_amount_facts() -> None:
    case = _case(IHRT, IHRT_BILLIONS)
    entry = _entry(IHRT_BILLIONS, "CP-2")
    extra = Fact(
        fact_id="extra",
        label="x",
        table_id="o",
        row_id="o",
        field="v",
        amount=Decimal(1),
        unit="USD",
        period="2025-06-30",
        citations=_cite(),
    )
    extra_untraced = Fact(
        fact_id="extra2",
        label="x",
        table_id="o",
        row_id="o2",
        field="v",
        amount=Decimal(1),
        unit="USD",
        period="2025-06-30",
    )
    module = _module([_fact(entry, amount=Decimal(3900000000)), extra, extra_untraced])
    score = _score(module, case, _mapping(case, [entry]))
    assert score.unscored == 1
    assert score.untraced == ("extra2",)


def test_honest_gap_passes() -> None:
    case = _case(IHRT, IHRT_BILLIONS)
    entry = _entry(IHRT_BILLIONS, "CP-2")
    mapping = _mapping(case, [entry])
    blocked = _module([], limitations=("source not provided",))
    score = _score(blocked, case, mapping, head="blocked")
    assert score.facts[0].outcome == "missing_in_output"
    assert score.passed is True
    # an accepted head gets no honest-gap pass (A-I1, spec 7.4)
    gap = _module([_fact(entry, status="missing")], limitations=("not stated",))
    lazy = _score(gap, case, mapping)
    assert lazy.facts[0].outcome == "missing_in_output"
    assert lazy.passed is False
    # no limitation: fails
    assert (
        _score(
            _module(
                [],
            ),
            case,
            mapping,
            head="blocked",
        ).passed
        is False
    )
    assert _score(_module([_fact(entry, status="missing")]), case, mapping).passed is False
    # restricted with a limitation
    assert _score(blocked, case, mapping, head="restricted").passed is True


def test_honest_gap_fails_when_invented() -> None:
    case = _case(NATL, NATL_TERM_B)
    entry = _entry(NATL_TERM_B, "CP-2")
    module = _module([_fact(entry, amount=Decimal(320))], limitations=("note",))
    score = _score(module, case, _mapping(case, [entry]), head="restricted")
    assert score.passed is False


def test_unmapped_reported_not_missing() -> None:
    case = _case(IHRT, IHRT_BILLIONS, IHRT_PCT)
    entry = _entry(IHRT_BILLIONS, "CP-2")
    # IHRT_PCT is CP-4: ask for module CP-4 with the fact listed as unmapped
    other = _case(IHRT, IHRT_BILLIONS, IHRT_PCT)
    mapping = _mapping(
        other,
        [entry],
        unmapped=[Unmapped(fact_id=IHRT_PCT, reason="not produced")],
        modules=("CP-2", "CP-4"),
    )
    module = _module([], module_id="CP-4")
    score = _score(module, case, mapping, module_id="CP-4")
    assert [(f.fact_id, f.outcome) for f in score.facts] == [(IHRT_PCT, "unmapped")]
    assert score.passed is True


def test_refusal_naming_input_is_honest_gap() -> None:
    case = _case(IHRT, IHRT_BILLIONS)
    entry = _entry(IHRT_BILLIONS, "CP-2")
    score = _score(
        None, case, _mapping(case, [entry]), head="refused", refusal=("portfolio_workbook",)
    )
    assert score.facts[0].outcome == "gap_ok"
    assert score.facts[0].observed == "refused: portfolio_workbook"
    assert score.facts[0].expected == "3900000000"
    assert score.passed is True
    assert score.head_status == "refused"


def test_refusal_naming_nothing_fails() -> None:
    case = _case(IHRT, IHRT_BILLIONS)
    entry = _entry(IHRT_BILLIONS, "CP-2")
    mapping = _mapping(case, [entry])
    score = _score(None, case, mapping, head="refused", refusal=())
    assert score.facts[0].outcome == "missing_in_output"
    assert score.passed is False
    absent = _score(None, case, mapping, head="absent")
    assert absent.facts[0].outcome == "missing_in_output"
    assert absent.passed is False


def test_pending_module_scored_unmapped() -> None:
    case = _case(IHRT, IHRT_BILLIONS, IHRT_PCT)
    entry = _entry(IHRT_BILLIONS, "CP-2")
    mapping = _mapping(case, [entry])  # CP-4 has no commit: pending
    assert IHRT_PCT in mapping.pending(case)
    score = _score(None, case, mapping, head="absent", module_id="CP-4")
    assert [(f.fact_id, f.outcome) for f in score.facts] == [(IHRT_PCT, "unmapped")]


def test_judgment_module_needs_no_values() -> None:
    assert JUDGMENT_MODULES == frozenset({"CP-5", "CP-6", "CP-MODEL", "CP-2A"})
    case = _case(IHRT, IHRT_BILLIONS)
    entry = _entry(IHRT_BILLIONS, "CP-5")
    mapping = _mapping(case, [entry], modules=("CP-5",))
    score = _score(_module([], module_id="CP-5"), case, mapping, module_id="CP-5")
    assert score.judgment is True
    assert score.passed is True
    wrong = _module([_fact(entry, amount=Decimal(1))], module_id="CP-5")
    assert _score(wrong, case, mapping, module_id="CP-5").passed is True
    assert (
        _score(
            _module(
                [],
            ),
            case,
            _mapping(case, [_entry(IHRT_BILLIONS, "CP-2")]),
        ).judgment
        is False
    )


def test_judgment_module_invented_fails() -> None:
    case = _case(NATL, NATL_TERM_B)
    entry = _entry(NATL_TERM_B, "CP-6")
    module = _module([_fact(entry, amount=Decimal(320))], module_id="CP-6")
    score = _score(module, case, _mapping(case, [entry], modules=("CP-6",)), module_id="CP-6")
    assert score.facts[0].outcome == "invented"
    assert score.passed is False


def test_golden_files_use_the_scale_names_the_scorer_knows() -> None:
    exps = checker().SCALE_EXP
    for case_id in (IHRT, LTH, NATL):
        for f in _golden(case_id)["facts"]:
            assert f["scale"] in exps


@given(
    value=st.decimals(min_value=-(10**9), max_value=10**9, places=4, allow_nan=False),
    scale=st.sampled_from(sorted(checker().SCALE_EXP, key=str)),
)
def test_scale_property(value: Decimal, scale: str | None) -> None:
    exp = checker().SCALE_EXP[scale]
    golden = {
        "fact_id": "g1",
        "module": "CP-2",
        "subject": "s",
        "field": "f",
        "period_end": None,
        "status": "known",
        "value": format(value, "f"),
        "value_type": "decimal",
        "unit": "USD",
        "scale": scale,
    }
    case = GoldenCase(
        case_id="c",
        pathway="credit_snapshot",
        case_dir=Path("."),
        context_path=Path("c.json"),
        golden=MappingProxyType({}),
        facts=MappingProxyType({"g1": golden}),
        out_of_plan=MappingProxyType({}),
        financial_gold_path=Path("g.json"),
        financial_gold_sha256="0" * 64,
    )
    entry = _entry("g1", "CP-2")
    mapping = _mapping(case, [entry])
    units = value.scaleb(exp)
    for amount, fscale in ((units, Decimal(1)), (value, Decimal(1).scaleb(exp))):
        module = _module([_fact(entry, amount=amount, scale=fscale)])
        assert _score(module, case, mapping).facts[0].outcome == "match"


# ---- fix round 1 ----------------------------------------------------------------------


def test_percent_unit_is_a_fraction() -> None:
    # A-H1: PERCENT / decimal_fraction hold a decimal fraction (display.py "percent takes a
    # decimal fraction"); decimal_percent holds points.
    ok, _, _ = _one(IHRT_PCT, IHRT, amount=Decimal("0.922"), unit="PERCENT")
    assert ok.facts[0].outcome == "match"
    assert ok.facts[0].expected == "92.2"
    assert ok.facts[0].observed == "92.2"
    bad, _, _ = _one(IHRT_PCT, IHRT, amount=Decimal("92.2"), unit="PERCENT")
    assert bad.facts[0].outcome == "mismatch"
    frac, _, _ = _one(IHRT_PCT, IHRT, amount=Decimal("0.922"), unit="decimal_fraction")
    assert frac.facts[0].outcome == "match"
    pts, _, _ = _one(IHRT_PCT, IHRT, amount=Decimal("92.2"), unit="decimal_percent")
    assert pts.facts[0].outcome == "match"


def test_unit_scale_disagreement_is_mismatch() -> None:
    score, _, _ = _one(IHRT_BILLIONS, IHRT, amount=Decimal(3900000000), unit="MILLIONS")
    assert score.facts[0].outcome == "mismatch"
    assert "MILLIONS" in (score.facts[0].observed or "")
    assert score.passed is False
    agree, _, _ = _one(
        IHRT_BILLIONS, IHRT, amount=Decimal(3900), unit="MILLIONS", scale=Decimal(1000000)
    )
    assert agree.facts[0].outcome == "match"


def test_unit_class_must_agree_with_golden() -> None:
    pct_as_money, _, _ = _one(IHRT_PCT, IHRT, amount=Decimal("92.2"), unit="USD")
    assert pct_as_money.facts[0].outcome == "mismatch"
    money_as_pct, _, _ = _one(IHRT_BILLIONS, IHRT, amount=Decimal(39), unit="PERCENT")
    assert money_as_pct.facts[0].outcome == "mismatch"


def test_duplicate_locator_is_mismatch() -> None:
    case = _case(IHRT, IHRT_BILLIONS)
    entry = _entry(IHRT_BILLIONS, "CP-2")
    good = _fact(entry, amount=Decimal(3900000000))
    wrong = _fact(entry, fact_id="other", amount=Decimal(7100000000))
    score = _score(_module([good, wrong]), case, _mapping(case, [entry]))
    assert score.facts[0].outcome == "mismatch"
    assert score.facts[0].observed == "2 facts at one locator"
    assert score.passed is False


def test_duplicate_locator_with_value_against_missing_is_invented() -> None:
    case = _case(NATL, NATL_TERM_B)
    entry = _entry(NATL_TERM_B, "CP-2")
    gap = _fact(entry, status="missing")
    value = _fact(entry, fact_id="other", amount=Decimal(320), scale=Decimal(1000000))
    score = _score(_module([gap, value]), case, _mapping(case, [entry]))
    assert score.facts[0].outcome == "invented"
    assert score.passed is False


def test_absent_module_never_passes() -> None:
    case = _case(NATL, NATL_TERM_B)
    mapping = _mapping(case, [_entry(NATL_TERM_B, "CP-2")])
    for head in ("absent", "refused"):
        assert _score(None, case, mapping, head=head).passed is False
        assert _score(None, case, mapping, head=head, refusal=("", "  ")).passed is False
    case = _case(IHRT, IHRT_BILLIONS)
    judged = _mapping(case, [_entry(IHRT_BILLIONS, "CP-5")], modules=("CP-5",))
    for head in ("absent", "refused"):
        assert _score(None, case, judged, head=head, module_id="CP-5").passed is False
    # everything pending
    pend = _score(None, case, _mapping(case, []), head="absent", module_id="CP-2")
    assert pend.passed is False


def test_blank_limitations_do_not_count() -> None:
    case = _case(IHRT, IHRT_BILLIONS)
    entry = _entry(IHRT_BILLIONS, "CP-2")
    mapping = _mapping(case, [entry])
    blank = _module([], limitations=("", "   "))
    assert _score(blank, case, mapping, head="blocked").passed is False
    real = _module([], limitations=("", "source missing"))
    assert _score(real, case, mapping, head="blocked").passed is True


def test_blank_fact_limitation_does_not_make_conflict_ok() -> None:
    case = _case(LTH, LTH_CONFLICT)
    entry = _entry(LTH_CONFLICT, "CP-2")
    module = _module([_fact(entry, amount=Decimal(277500000), limitation="  ")])
    assert _score(module, case, _mapping(case, [entry])).facts[0].outcome == "mismatch"


def test_refused_with_module_still_checks_provenance() -> None:
    case = _case(NATL, NATL_TERM_B)
    entry = _entry(NATL_TERM_B, "CP-2")
    mapping = _mapping(case, [entry])
    untraced = _module([_fact(entry, traced=False, amount=Decimal(320), scale=Decimal(1000000))])
    score = _score(untraced, case, mapping, head="refused", refusal=("portfolio_workbook",))
    assert score.facts[0].outcome == "invented"
    assert score.untraced != ()
    assert score.passed is False


def test_refused_with_module_turns_only_missing_into_gap_ok() -> None:
    case = _case(IHRT, IHRT_BILLIONS)
    entry = _entry(IHRT_BILLIONS, "CP-2")
    score = _score(
        _module([]), case, _mapping(case, [entry]), head="refused", refusal=("portfolio_workbook",)
    )
    assert score.facts[0].outcome == "gap_ok"
    assert score.passed is True


def test_conflict_date_never_takes_a_bare_number() -> None:
    case = _case(IHRT, "CP-4.exchange_dates.Exchange.press_release_date")
    entry = _entry("CP-4.exchange_dates.Exchange.press_release_date", "CP-4")
    mapping = _mapping(case, [entry], modules=("CP-4",))
    num = _module([_fact(entry, amount=Decimal(23), unit="x", limitation="two dates")], "CP-4")
    assert _score(num, case, mapping, module_id="CP-4").facts[0].outcome == "mismatch"
    txt = _module([_fact(entry, text="2024-12-23", limitation="two dates")], "CP-4")
    assert _score(txt, case, mapping, module_id="CP-4").facts[0].outcome == "conflict_ok"


def test_printed_number_parsing() -> None:
    from deploy_workflow.model_testing import scoring

    golden = {"value_type": "decimal", "scale": "units"}

    def fact(amount: str) -> Fact:
        return Fact(
            fact_id="x",
            label="x",
            amount=Decimal(amount),
            unit="USD",
            period="2025-06-30",
        )

    assert scoring._printed_matches("(175,000,000)", fact("-175000000"), golden)
    assert not scoring._printed_matches("(175,000,000)", fact("175000000"), golden)
    assert scoring._printed_matches("$175 million", fact("175000000"), golden)
    assert scoring._printed_matches("$1.5 Billion", fact("1500000000"), golden)
    assert not scoring._printed_matches("$175 million", fact("175"), golden)


def test_aliases_never_apply_to_dates_and_dates_compare_as_dates() -> None:
    date_id = "CP-4.exchange_dates.Exchange.press_release_date"
    golden = _golden(IHRT)
    known = next(f for f in golden["facts"] if f["value_type"] == "date" and f["status"] == "known")
    case = _case(IHRT, known["fact_id"])
    iso = known["value"]
    parsed = date.fromisoformat(iso)
    named = f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"
    entry = _entry(known["fact_id"], known["module"], subject_aliases=("Other Date",))
    mapping = _mapping(case, [entry], modules=(known["module"],))
    for text, outcome in (
        (iso, "match"),
        (named, "match"),
        ("Other Date", "mismatch"),
        ("junk", "mismatch"),
    ):
        module = _module([_fact(entry, text=text)], known["module"])
        got = _score(module, case, mapping, module_id=known["module"]).facts[0].outcome
        assert got == outcome, text
    assert date_id  # the conflicting date fact exists in the corpus


def test_unknown_head_status_is_refused() -> None:
    import pytest

    case = _case(IHRT, IHRT_BILLIONS)
    mapping = _mapping(case, [_entry(IHRT_BILLIONS, "CP-2")])
    with pytest.raises(ValueError, match="head_status"):
        _score(None, case, mapping, head="bogus")
