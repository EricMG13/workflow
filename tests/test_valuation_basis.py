"""Phase 7 Task 2: the EV/EBITDA arithmetic of `owners/valuation_basis.py`.

The inputs below are written from the frozen oracle `cases/valuation-context-owner/expected.json`
(rules, hand_derived, cases.*.cp1c.selection) and the plan's Task 0 tables, not from the module.
"""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal as D
from random import Random
from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from deploy_workflow.context import IssuerMarket, UserMultiple
from deploy_workflow.owners import cp1c
from deploy_workflow.owners import valuation_basis as vb

AS_OF = date(2026, 1, 10)


def peer(
    name: str, ev: str, ebitda: str, when: date | None = date(2025, 11, 30), kind: str = "peer"
) -> vb.AdmittedRecord:
    return vb.AdmittedRecord("user_comps", kind, name, when, "src", D(ev), D(ebitda))


def mult_peers(
    *multiples: str, kind: str = "peer", when: date | None = date(2025, 11, 30)
) -> list[vb.AdmittedRecord]:
    return [peer(f"P{i}", m, "1", when, kind) for i, m in enumerate(multiples)]


def admitted(*multiples: str) -> tuple[vb.Admission, ...]:
    return vb.admit(mult_peers(*multiples), AS_OF, 12)


def issuer(cap: str = "200", debt: str = "70", ev: str = "", basis: Any = "LTM") -> IssuerMarket:
    return IssuerMarket(
        market_cap_m=cap,
        net_debt_m=debt,
        ev_m=ev,
        ebitda_basis=basis,
        as_of="2026-01-05",
        source="s",
    )


def user(
    value: str = "8.50", basis: Any = "LTM", rationale: str = "Mid-point of sector LBO range"
) -> UserMultiple:
    return UserMultiple(value=value, basis=basis, rationale=rationale)


def select(
    requested: str,
    public: Sequence[vb.Admission] = (),
    precedents: Sequence[vb.Admission] = (),
    iss: IssuerMarket | None = None,
    usr: UserMultiple | None = None,
    ebitda: str | None = "30.0",
) -> vb.Selection:
    e = None if ebitda is None else D(ebitda)
    return vb.select_basis(requested, public, precedents, iss, usr, e)


# --- window -------------------------------------------------------------------------------------


def test_window_start_table() -> None:
    assert vb.window_start(date(2026, 1, 10), 12) == date(2025, 1, 10)
    assert vb.window_start(date(2026, 1, 10), 36) == date(2023, 1, 10)
    assert vb.window_start(date(2024, 2, 29), 12) == date(2023, 2, 28)
    assert vb.window_start(date(2026, 3, 31), 1) == date(2026, 2, 28)


def test_admit_boundary_day_inclusive() -> None:
    rows = [peer("in", "9", "1", date(2025, 1, 10)), peer("out", "9", "1", date(2025, 1, 9))]
    inc, out = vb.admit(rows, AS_OF, 12)
    assert inc.included and inc.reason == "Included"
    assert not out.included
    assert out.reason == "Excluded: figures dated 2025-01-09 are before 2025-01-10 (12-month limit)"


def test_admit_reasons() -> None:
    ev0, eb0, ebneg, stale = vb.admit(
        [
            peer("a", "0", "5"),
            peer("b", "9", "0"),
            peer("c", "9", "-2"),
            peer("d", "8", "1", date(2024, 12, 31)),
        ],
        AS_OF,
        12,
    )
    assert ev0.reason == "Excluded: enterprise value is zero" and ev0.multiple is None
    assert eb0.reason == "Excluded: EBITDA is not above zero" and eb0.multiple is None
    assert ebneg.reason == "Excluded: EBITDA is not above zero"
    assert stale.reason == (
        "Excluded: figures dated 2024-12-31 are before 2025-01-10 (12-month limit)"
    )
    assert stale.multiple == D(8)  # shown, but not admitted (oracle e04 multiple_exact 8)


def test_admit_precedent_texts() -> None:
    old = peer("p3", "8", "1", date(2022, 12, 31), kind="precedent")
    undated = peer("p6", "7", "1", None, kind="precedent")
    a, b = vb.admit([old, undated], AS_OF, 36)
    assert a.reason == "Excluded: deal dated 2022-12-31 is before 2023-01-10 (36-month limit)"
    assert b.reason == "Excluded: no deal date, the window cannot be checked"
    assert b.multiple == D(7) and not b.included


def test_admit_first_failing_test_gives_reason() -> None:
    (a,) = vb.admit([peer("x", "0", "0", date(2000, 1, 1))], AS_OF, 12)
    assert a.reason == "Excluded: enterprise value is zero"


# --- statistics ---------------------------------------------------------------------------------


def test_stats_peers_a_to_c() -> None:
    rows = vb.admit(
        mult_peers("9", "6", "7") + [peer("D", "8", "1", date(2024, 12, 31)), peer("E", "0", "3")],
        AS_OF,
        12,
    )
    s = vb.stats(rows)
    assert (s.n_total, s.n_admitted) == (5, 3)
    assert (s.minimum, s.median, s.maximum, s.outliers) == (D(6), D(7), D(9), 0)


def test_stats_even_count() -> None:
    s = vb.stats(admitted("6", "9", "10", "12.5"))
    assert s.median == D("9.5")


def test_stats_outlier_flag_counts() -> None:
    # median 7: 12 deviates by 5/7 > 0.5; 10 by 3/7 does not
    s = vb.stats(admitted("6", "7", "7", "10", "12"))
    assert s.outliers == 1


def test_below_minimum_median_missing() -> None:
    s = vb.stats(admitted("6", "9"))
    assert s.n_admitted == 2 and s.median is None and s.outliers is None
    assert (s.minimum, s.maximum) == (D(6), D(9))


def test_stats_empty_set() -> None:
    s = vb.stats(())
    assert (s.n_total, s.n_admitted) == (0, 0)
    assert (s.minimum, s.median, s.maximum, s.outliers) == (None, None, None, None)


# --- selection ----------------------------------------------------------------------------------


def test_select_auto_public() -> None:
    sel = select("auto", admitted("9", "6", "7"))
    assert sel.selected_basis == "public_comps" and sel.multiple == D("7.00")
    assert sel.reason == "auto: public comps, 3 admitted of 3 required (12-month window)"
    assert sel.ebitda_basis == "Not stated by the user"
    assert sel.implied_ev == D("210.0")


def test_select_auto_falls_to_precedents() -> None:
    prec = vb.admit(mult_peers("6", "9", "10", "12.5", kind="precedent"), AS_OF, 36)
    sel = select("auto", admitted("6", "9"), prec)
    assert sel.selected_basis == "precedents" and sel.multiple == D("9.50")


def test_select_auto_insufficient() -> None:
    sel = select(
        "auto", admitted("6", "9"), vb.admit(mult_peers("6", "9", kind="precedent"), AS_OF, 36)
    )
    assert sel.selected_basis == "Insufficient Information"
    assert sel.multiple is None and sel.implied_ev is None
    assert sel.reason == (
        "auto: public comps 2 admitted of 3 required (12-month window); "
        "precedents 2 admitted of 3 required (36-month window); no multiple is selected"
    )


def test_select_auto_never_blends() -> None:
    prec = vb.admit(mult_peers("8", "9", "10", kind="precedent"), AS_OF, 36)
    sel = select("auto", admitted("6", "7", "8"), prec)
    assert sel.selected_basis == "public_comps"


def test_select_explicit_no_fallback() -> None:
    prec = vb.admit(mult_peers("6", "9", "10", "12.5", kind="precedent"), AS_OF, 36)
    sel = select("public_comps", admitted("6", "9"), prec)
    assert sel.selected_basis is None and sel.multiple is None and sel.implied_ev is None
    assert sel.reason == "requested public_comps, 2 admitted of 3 required; no fallback"


def test_select_precedents_explicit() -> None:
    prec = vb.admit(mult_peers("6", "9", "10", "12.5", kind="precedent"), AS_OF, 36)
    sel = select("precedents", (), prec)
    assert sel.multiple == D("9.50") and sel.implied_ev == D("285.0")
    assert sel.reason == "precedents: median of 4 admitted precedents (36-month window)"
    thin = select("precedents", admitted("6", "7", "8"), vb.admit(mult_peers("6"), AS_OF, 36))
    assert thin.multiple is None
    assert thin.reason == "requested precedents, 1 admitted of 3 required; no fallback"


def test_blend_average() -> None:
    prec = vb.admit(mult_peers("6", "9", "10", "12.5", kind="precedent"), AS_OF, 36)
    sel = select("blend", admitted("9", "6", "7"), prec)
    assert sel.selected_basis == "blend" and sel.multiple == D("8.25")
    assert sel.implied_ev == D("247.5")
    assert (
        sel.reason
        == "blend: plain average of the public comps median 7.00 and the precedents median 9.50"
    )
    thin = select(
        "blend",
        admitted("9", "6", "7"),
        vb.admit(mult_peers("6", "9", kind="precedent"), AS_OF, 36),
    )
    assert thin.multiple is None and thin.implied_ev is None
    assert thin.reason == "requested blend, precedents 2 admitted of 3 required; no fallback"


def test_round_half_even_2dp() -> None:
    assert select("public_comps", admitted("7.125", "7.125", "7.125")).multiple == D("7.12")
    assert select("public_comps", admitted("7.135", "7.135", "7.135")).multiple == D("7.14")


def test_over_99_99_is_gap() -> None:
    sel = select("public_comps", admitted("100", "100", "100"))
    assert sel.multiple is None and sel.implied_ev is None
    assert "99.99" in sel.reason and "100.00" in sel.reason
    ok = select("public_comps", admitted("99.99", "99.99", "99.99"))
    assert ok.multiple == D("99.99")


def test_issuer_trading() -> None:
    sel = select("issuer_trading", iss=issuer())
    assert sel.selected_basis == "issuer_trading" and sel.multiple == D("9.00")
    assert sel.implied_ev == D("270.0") and sel.ebitda_basis == "LTM"
    assert sel.reason == (
        "issuer_trading: enterprise value 270.0 (market cap 200 plus net debt 70, as of 2026-01-05) "
        "over CP-1 LTM adjusted EBITDA 30.0"
    )


def test_issuer_trading_ev_wins() -> None:
    sel = select("issuer_trading", iss=issuer(cap="1", debt="1", ev="150"))
    assert sel.multiple == D("5.00")


def test_issuer_trading_ntm_gap() -> None:
    sel = select("issuer_trading", iss=issuer(basis="NTM"))
    assert sel.multiple is None and sel.implied_ev is None and sel.ebitda_basis == "NTM"
    assert sel.reason == "NTM needs a forecast EBITDA that CP-1C does not read"


def test_issuer_trading_ebitda_gaps() -> None:
    for e in (None, "0", "-3"):
        sel = select("issuer_trading", iss=issuer(), ebitda=e)
        assert sel.multiple is None and sel.implied_ev is None, e
        assert "CP-1 LTM adjusted EBITDA" in sel.reason


def test_issuer_trading_ev_not_positive_gap() -> None:
    sel = select("issuer_trading", iss=issuer(cap="10", debt="-10"))
    assert sel.multiple is None and sel.implied_ev is None
    assert "enterprise value" in sel.reason
    assert select("issuer_trading", iss=None).multiple is None


def test_user_multiple_label() -> None:
    sel = select("user_multiple", usr=user())
    assert sel.selected_basis == "user_multiple" and sel.multiple == D("8.50")
    assert sel.reason == "user-supplied (LTM basis); rationale: Mid-point of sector LBO range"
    assert sel.ebitda_basis == "LTM" and sel.implied_ev == D("255.0")


def test_user_multiple_ntm_carried_without_implied_ev() -> None:
    sel = select("user_multiple", usr=user(basis="NTM"))
    assert sel.multiple == D("8.50") and sel.ebitda_basis == "NTM"
    assert sel.implied_ev is None
    assert sel.reason.startswith("user-supplied (NTM basis)")


def test_user_multiple_missing_is_gap() -> None:
    for u in (None, user(value="")):
        sel = select("user_multiple", usr=u)
        assert sel.multiple is None and sel.implied_ev is None


def test_implied_ev() -> None:
    assert select("public_comps", admitted("7", "7", "7")).implied_ev == D("210.0")
    prec = vb.admit(mult_peers("6", "9", "10", "12.5", kind="precedent"), AS_OF, 36)
    assert select("blend", admitted("7", "7", "7"), prec).implied_ev == D("247.5")


def test_zero_never_substituted() -> None:
    thin = admitted("6", "9")
    gaps = [
        select("auto", thin),
        select("public_comps", thin),
        select("precedents", thin),
        select("blend", thin),
        select("issuer_trading", iss=issuer(basis="NTM")),
        select("issuer_trading", iss=None),
        select("user_multiple", usr=None),
        select("public_comps", admitted("100", "100", "100")),
    ]
    for g in gaps:
        assert g.multiple is None and g.implied_ev is None, g.reason
        assert g.reason


def test_implied_ev_gap_when_ebitda_unknown_keeps_multiple() -> None:
    sel = select("public_comps", admitted("7", "7", "7"), ebitda=None)
    assert sel.multiple == D("7.00") and sel.implied_ev is None
    assert "implied EV" in sel.reason


# --- properties ---------------------------------------------------------------------------------

cents = st.integers(min_value=1, max_value=999_999).map(lambda n: D(n) / 100)
multiples = st.lists(cents, min_size=3, max_size=12)


def records(ms: Sequence[D], kind: str = "peer") -> list[vb.AdmittedRecord]:
    return [
        vb.AdmittedRecord("user_comps", kind, f"P{i}", date(2025, 11, 30), "s", m, D(1))
        for i, m in enumerate(ms)
    ]


@given(multiples)
def test_property_min_median_max(ms: list[D]) -> None:
    s = vb.stats(vb.admit(records(ms), AS_OF, 12))
    assert s.minimum is not None and s.median is not None and s.maximum is not None
    assert s.minimum <= s.median <= s.maximum
    assert s.n_admitted == len(ms)


in_range = st.integers(min_value=1, max_value=9999).map(lambda n: D(n) / 100)
some = st.lists(in_range, min_size=0, max_size=6)


@given(some, some, st.sampled_from(["auto", "public_comps", "precedents", "blend"]))
def test_property_no_multiple_below_three(
    pub_ms: list[D], prec_ms: list[D], requested: str
) -> None:
    pub = vb.admit(records(pub_ms), AS_OF, 12)
    prec = vb.admit(records(prec_ms, "precedent"), AS_OF, 36)
    sel = vb.select_basis(requested, pub, prec, None, None, D(30))
    enough = {
        "auto": len(pub_ms) >= 3 or len(prec_ms) >= 3,
        "public_comps": len(pub_ms) >= 3,
        "precedents": len(prec_ms) >= 3,
        "blend": len(pub_ms) >= 3 and len(prec_ms) >= 3,
    }[requested]
    # a multiple is returned exactly when the chosen set (both sets for blend) has >= 3 admitted
    assert (sel.multiple is not None) is enough
    assert (sel.implied_ev is not None) is enough
    if requested == "auto" and len(pub_ms) < 3 <= len(prec_ms):
        assert sel.selected_basis == "precedents"


@given(multiples, st.randoms())
def test_property_admit_order_independent(ms: list[D], rnd: Random) -> None:
    recs = records(ms)
    shuffled = list(recs)
    rnd.shuffle(shuffled)
    a = {x.record.name: x for x in vb.admit(recs, AS_OF, 12)}
    b = {x.record.name: x for x in vb.admit(shuffled, AS_OF, 12)}
    assert a == b
    assert vb.stats(list(a.values())) == vb.stats(list(b.values()))


@given(multiples)
def test_property_outlier_count_matches_flags(ms: list[D]) -> None:
    s = vb.stats(vb.admit(records(ms), AS_OF, 12))
    med = cp1c.median(ms)
    flags = [cp1c.outlier(m, med) for m in ms]
    assert s.outliers == sum(1 for f in flags if f is not None and f[1] == "Outlier")


# --- fix round 1: tests that kill the review mutants ----------------------------------------------


def test_negative_ev_is_refused_with_its_own_reason() -> None:
    (a,) = vb.admit([peer("n", "-5", "2")], AS_OF, 12)
    assert not a.included and a.multiple is None
    assert a.reason == "Excluded: enterprise value is negative"


def test_stats_min_max_cover_admitted_records_only() -> None:
    rows = vb.admit(
        mult_peers("6", "7", "9")
        + [peer("old", "1", "1", date(2024, 1, 1)), peer("big", "50", "1", date(2024, 1, 1))],
        AS_OF,
        12,
    )
    s = vb.stats(rows)
    assert (s.n_total, s.n_admitted) == (5, 3)
    assert (s.minimum, s.maximum) == (
        D(6),
        D(9),
    )  # stale 1x and 50x are shown in the table, not in the range


def test_implied_ev_zero_or_negative_ebitda_is_gap() -> None:
    for e in ("0", "-1"):
        sel = select("public_comps", admitted("7", "7", "7"), ebitda=e)
        assert sel.multiple == D("7.00") and sel.implied_ev is None
        assert sel.reason.endswith(
            "implied EV not calculable: CP-1 LTM adjusted EBITDA is not a known positive amount"
        )


def test_user_multiple_zero_negative_and_rounding() -> None:
    for v in ("0", "0.00", "-8.5"):
        sel = select("user_multiple", usr=user(value=v))
        assert sel.multiple is None and sel.implied_ev is None, v
        assert sel.reason == "the user multiple is not above zero"
    assert select("user_multiple", usr=user(value="8.505")).multiple == D("8.50")  # half-even
    assert select("user_multiple", usr=user(value="8.515")).multiple == D("8.52")


def test_implied_ev_uses_the_rounded_multiple() -> None:
    sel = select("public_comps", admitted("7.125", "7.125", "7.125"))
    assert sel.multiple == D("7.12") and sel.implied_ev == D("213.60")  # not 7.125 x 30.0 = 213.75


def test_blend_averages_exact_medians_not_rounded_ones() -> None:
    pub = vb.admit(mult_peers("7.004", "7.004", "7.004"), AS_OF, 12)
    prec = vb.admit(mult_peers("7.007", "7.007", "7.007", kind="precedent"), AS_OF, 36)
    sel = select("blend", pub, prec)
    assert sel.multiple == D(
        "7.01"
    )  # (7.004 + 7.007) / 2 = 7.0055; the rounded 7.00 + 7.01 would give 7.00


def test_blend_reason_states_medians_half_up() -> None:
    pub = admitted("6", "7.125", "8.25")
    prec = vb.admit(mult_peers("9", "9.5", "10", kind="precedent"), AS_OF, 36)
    sel = select("blend", pub, prec)
    assert sel.multiple == D("8.31")  # (7.125 + 9.5) / 2 = 8.3125
    assert sel.reason == (
        "blend: plain average of the public comps median 7.13 and the precedents median 9.50"
    )


def test_limit_is_tested_on_the_rounded_multiple() -> None:
    assert select("public_comps", admitted("99.994", "99.994", "99.994")).multiple == D("99.99")
    over = select("public_comps", admitted("99.995", "99.995", "99.995"))  # half-even gives 100.00
    assert over.multiple is None and "100.00" in over.reason


def test_issuer_reason_ev_is_half_up_at_one_dp() -> None:
    sel = select("issuer_trading", iss=issuer(cap="", debt="", ev="270.25"))
    assert "enterprise value 270.3 (stated, as of 2026-01-05)" in sel.reason
    assert sel.multiple == D("9.01")


def test_multiple_below_one_cent_is_gap() -> None:  # P7T2-R1
    sel = select(
        "public_comps", [a for a in vb.admit(mult_peers("0.002", "0.002", "0.002"), AS_OF, 12)]
    )
    assert sel.multiple is None and sel.implied_ev is None
    assert "0.01" in sel.reason and "0.00" in sel.reason
    assert select("user_multiple", usr=user(value="0.004")).multiple is None
    assert (
        select("public_comps", admitted("0.005", "0.005", "0.005")).multiple is None
    )  # half-even 0.00
    assert select("public_comps", admitted("0.015", "0.015", "0.015")).multiple == D("0.02")
    assert select("public_comps", admitted("0.01", "0.01", "0.01")).multiple == D("0.01")


def test_huge_inputs_give_the_over_limit_gap_never_an_exception() -> None:  # P7T2-R2
    huge = "1" + "0" * 36
    sel = select("public_comps", vb.admit([peer(f"h{i}", huge, "1") for i in range(3)], AS_OF, 12))
    assert sel.multiple is None and sel.implied_ev is None and "99.99" in sel.reason
    sel = select("issuer_trading", iss=issuer(cap="", debt="", ev="1" + "0" * 27), ebitda="1")
    assert sel.multiple is None and "99.99" in sel.reason
    sel = select("user_multiple", usr=user(value="1" + "0" * 40))
    assert sel.multiple is None and "99.99" in sel.reason
    big = select(
        "issuer_trading", iss=issuer(cap="", debt="", ev="1" + "0" * 37), ebitda="1" + "0" * 36
    )
    assert big.multiple == D("10.00")  # a huge EV over an equally huge EBITDA is a normal multiple
    pub = vb.admit(mult_peers(huge, huge, huge), AS_OF, 12)
    prec = vb.admit(mult_peers("7", "7", "7", kind="precedent"), AS_OF, 36)
    assert select("blend", pub, prec).multiple is None


def test_non_finite_figures_are_refused() -> None:  # P7T2-R4
    rows = vb.admit(
        [
            vb.AdmittedRecord(
                "user_comps", "peer", "i", date(2025, 11, 30), "s", D("Infinity"), D(1)
            ),
            vb.AdmittedRecord("user_comps", "peer", "n", date(2025, 11, 30), "s", D(5), D("NaN")),
            vb.AdmittedRecord("user_comps", "peer", "q", date(2025, 11, 30), "s", D("NaN"), D(1)),
            vb.AdmittedRecord(
                "user_comps", "peer", "j", date(2025, 11, 30), "s", D(5), D("-Infinity")
            ),
        ],
        AS_OF,
        12,
    )
    for a in rows:
        assert not a.included and a.multiple is None
        assert a.reason == "Excluded: enterprise value or EBITDA is not a finite number"


def test_user_ntm_multiple_gives_an_implied_ev_reason() -> None:  # P7T2-R5
    sel = select("user_multiple", usr=user(basis="NTM"))
    assert sel.multiple == D("8.50") and sel.implied_ev is None
    assert sel.reason == (
        "user-supplied (NTM basis); rationale: Mid-point of sector LBO range; "
        "implied EV not calculable: an NTM multiple is not applied to LTM EBITDA"
    )
