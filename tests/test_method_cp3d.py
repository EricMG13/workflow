"""CP-3D Stage 1: the market-implied calculation against the frozen oracle.

Every expected value is read from `cases/cp3d-owner/expected.json`; every input is built from the
oracle's own literals (`submissions.json`), pinned pages (`manifest.json`,
`cases/financial/manifest.json`) and fixtures. Nothing here derives an expected value.
"""

import copy
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow.owners import cp3d

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp3d-owner"
EXPECTED: dict[str, Any] = json.loads((CASE / "expected.json").read_text(encoding="utf-8"))
SUBMISSIONS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text(encoding="utf-8"))
MANIFEST: dict[str, Any] = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
FINANCIAL: dict[str, Any] = json.loads(
    (ROOT / "cases" / "financial" / "manifest.json").read_text(encoding="utf-8")
)

CASES = ("positive", "gap_no_recovery", "gap_no_market")
FIXTURES = tuple(EXPECTED["fixtures"])


def _all_pages() -> dict[str, dict[str, str]]:
    pages = {
        s["source_id"]: {p["locator"]: p["text"] for p in s["pages"]} for s in FINANCIAL["sources"]
    }
    market = MANIFEST["market_source_pin"]
    pages[market["source_id"]] = {p["locator"]: p["text"] for p in market["pages"]}
    return pages


def _manifest_case(case: str) -> dict[str, Any]:
    return next(c for c in MANIFEST["cases"] if c["case_id"] == case)


def _third_party(case: str) -> frozenset[str]:
    """CP-0 T3 authority of the case's CP-0 oracle: the sources whose authority is third_party."""
    return frozenset(
        f["fact_id"].split(".")[1]
        for f in EXPECTED["cp0"][case]["facts"]
        if f["fact_id"].startswith("T3.")
        and f["fact_id"].endswith(".authority")
        and f["text"] == "third_party"
    )


def _context(case: str) -> cp3d.MarketContext:
    meta = _manifest_case(case)
    everything = _all_pages()
    ids = [s["source_id"] for s in meta["pack_sources"]]
    pages = {sid: everything[sid] for sid in ids}
    return cp3d.MarketContext(
        pages=pages,
        names={s["source_id"]: s["name"] for s in meta["pack_sources"]},
        third_party=_third_party(case),
        published=cp3d.publication_dates(pages),
        run_as_of=date.fromisoformat(meta["run"]["as_of"]),
    )


def _submission(raw: dict[str, Any]) -> cp3d.MarketImpliedSubmission:
    return cp3d.MarketImpliedSubmission.model_validate_json(json.dumps(raw))


def _edited(base: dict[str, Any], edits: list[list[Any]]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for path, value in edits:
        keys: list[Any] = [int(k) if k.isdigit() else k for k in path.split(".")]
        cur: Any = out
        for key in keys[:-1]:
            cur = cur[key]
        cur[keys[-1]] = value
    return out


def _cell_dict(cell: cp3d.Cell) -> dict[str, Any]:
    return {
        "fact_id": cell.fact_id,
        "column": cell.column,
        "period": cell.period,
        "amount": None if cell.amount is None else format(cell.amount, "f"),
        "unit": cell.unit,
        "decimals": cell.decimals,
        "text": cell.text,
        "shown": cell.shown,
        "status": cell.status,
        "cites": [list(c) for c in cell.cites],
        "value_class": cell.value_class,
        "calculation_id": cell.calculation_id,
        "formula": cell.formula,
        "limitation": cell.limitation,
    }


def _table_dict(table: cp3d.Table) -> dict[str, Any]:
    return {
        "table_id": table.table_id,
        "title": table.title,
        "row_header": table.row_header,
        "columns": [{"field": f, "label": label} for f, label in table.columns],
        "rows": [
            {"row_id": r.row_id, "label": r.label, "facts": [_cell_dict(c) for c in r.facts]}
            for r in table.rows
        ],
    }


def _result(case: str) -> cp3d.MarketImpliedResult:
    sub = _submission(SUBMISSIONS[case])
    ctx = _context(case)
    assert cp3d.submission_issues(submission=sub, context=ctx) == ()
    return cp3d.market_implied_result(submission=sub, context=ctx)


# --- the composer over each pack case ----------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_derived_values(case: str) -> None:
    inputs = cp3d.inputs_from_submission(_submission(SUBMISSIONS[case]))
    assert cp3d.compose(inputs=inputs).stored() == EXPECTED["cases"][case]["derived"]


@pytest.mark.parametrize("case", CASES)
def test_tables_equal_the_oracle(case: str) -> None:
    got = [_table_dict(t) for t in _result(case).tables]
    expected = EXPECTED["cases"][case]["tables"]
    assert [t["table_id"] for t in got] == [t["table_id"] for t in expected]
    for g, e in zip(got, expected, strict=True):
        assert g == e, g["table_id"]


@pytest.mark.parametrize("case", CASES)
def test_missing_is_never_zero(case: str) -> None:
    cells = {c.fact_id: c for t in _result(case).tables for r in t.rows for c in r.facts}
    missing = sorted(fid for fid, c in cells.items() if c.status == "missing")
    assert missing == sorted(EXPECTED["cases"][case]["missing_not_zero"])
    for fid in missing:
        assert cells[fid].amount is None and cells[fid].text is None


@pytest.mark.parametrize("case", CASES)
def test_claims_equal_the_oracle(case: str) -> None:
    got = [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "refs": list(c.refs),
            "cites": [list(x) for x in c.cites],
        }
        for c in _result(case).claims
    ]
    assert got == EXPECTED["cases"][case]["claims"]


@pytest.mark.parametrize("case", CASES)
def test_own_and_inherited_limitations(case: str) -> None:
    result = _result(case)
    assert list(result.own_limitations) == EXPECTED["cases"][case]["own_limitations"]
    inherited = cp3d.inherited_limitations(
        own=result.own_limitations, upstream=tuple(EXPECTED["cp0"][case]["limitations"])
    )
    assert list(inherited) == EXPECTED["cases"][case]["inherited_limitations"]


def test_consumption_values_pinned_for_cp3c() -> None:
    inputs = cp3d.inputs_from_submission(_submission(SUBMISSIONS["positive"]))
    stored = cp3d.compose(inputs=inputs).stored()
    pinned = EXPECTED["consumption"]["reader_pinned_for_cp3c"]["positive_values"]
    assert {k: stored[k] for k in pinned} == pinned


# --- composer-only fixtures --------------------------------------------------------------------


def _fixture_inputs(raw: dict[str, Any]) -> cp3d.MarketInputs:
    def dec(key: str) -> Decimal | None:
        value = raw.get(key)
        return None if value is None else Decimal(value)

    return cp3d.MarketInputs(
        bid=dec("bid"),
        offer=dec("offer"),
        talk=dec("talk"),
        quotation_date=date.fromisoformat(raw["asof"]) if raw.get("asof") else None,
        maturity=date.fromisoformat(raw["maturity"]) if raw.get("maturity") else None,
        margin_bp=dec("margin_bp"),
        amortisation_zero=raw.get("amort_zero"),
        recovery=dec("recovery"),
        reference_rate_level=dec("ref_level"),
    )


@pytest.mark.parametrize("fixture", FIXTURES)
def test_fixture_stored_values(fixture: str) -> None:
    entry = EXPECTED["fixtures"][fixture]
    assert cp3d.compose(inputs=_fixture_inputs(entry["inputs"])).stored() == entry["stored"]


# --- calculation-level refusals (validator) ----------------------------------------------------


MUTATIONS = SUBMISSIONS["refusal_mutations"]


@pytest.mark.parametrize("entry", MUTATIONS["entries"], ids=lambda e: e["id"])
def test_refusal_mutation_yields_exactly_its_issue(entry: dict[str, Any]) -> None:
    raw = _edited(SUBMISSIONS[MUTATIONS["base"]], entry["edits"])
    ctx = _context(MUTATIONS["base"])
    issues = cp3d.submission_issues(submission=_submission(raw), context=ctx)
    assert list(issues) == entry["all_issues"] == [entry["issue"]]


def test_refusal_list_matches_the_mutations() -> None:
    assert [(r["id"], r["issue"]) for r in EXPECTED["refusals"]] == [
        (m["id"], m["issue"]) for m in MUTATIONS["entries"]
    ]


@pytest.mark.parametrize("attempt", ("attempt_0", "attempt_1"))
def test_blocked_case_attempt_issues(attempt: str) -> None:
    spec = SUBMISSIONS["blocked"][attempt]
    raw = _edited(SUBMISSIONS["positive"], spec["edits"])
    issues = cp3d.submission_issues(submission=_submission(raw), context=_context("positive"))
    assert list(issues) == [spec["issue"]]
    assert spec["issue"] == EXPECTED["negative_cases"]["blocked_cp3d"][f"{attempt}_issue"]


def test_bid_exceeding_offer_is_refused_on_a_synthetic_page() -> None:
    """The retired `crossed_quote` rule (lease open question 14): a synthetic page, no oracle literal."""
    page = "Dealer quotation on January 9, 2026: bid 99.50 and offer 99.25."
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    for obs, level in ((raw["observations"][0], "99.50"), (raw["observations"][1], "99.25")):
        obs.update(locator="page:9", quote=page, level_text=level)
    ctx = _with_page(_context("positive"), "market", "page:9", page)
    assert cp3d.submission_issues(submission=_submission(raw), context=ctx) == (
        "observations: bid exceeds offer",
    )


def _with_page(
    base: cp3d.MarketContext, source_id: str, locator: str, text: str
) -> cp3d.MarketContext:
    pages = {sid: dict(p) for sid, p in base.pages.items()}
    pages[source_id][locator] = text
    return cp3d.MarketContext(
        pages=pages,
        names=base.names,
        third_party=base.third_party,
        published=cp3d.publication_dates(pages),
        run_as_of=base.run_as_of,
    )


def test_quoted_reference_rate_level_reaches_the_yield_cells_and_claim() -> None:
    """No frozen source states a level; a synthetic page carries the fixture's 4.30 percent test
    vector, so the expected yield is `fixture_with_benchmark` (oracle), not derived here."""
    page = "Published January 10, 2026.\nThe SOFR reference rate is 4.30 percent."
    ctx = _with_page(_context("positive"), "financial", "page:9", page)
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    raw["terms"]["reference_rate"]["absence"] = None
    level_quote = {"source_id": "financial", "locator": "page:9", "quote": page.split("\n")[1]}
    raw["terms"]["reference_rate"]["level"] = {"quote": level_quote, "percent_text": "4.30"}
    sub = _submission(raw)
    assert cp3d.submission_issues(submission=sub, context=ctx) == ()
    result = cp3d.market_implied_result(submission=sub, context=ctx)
    cells = {c.fact_id: c for t in result.tables for r in t.rows for c in r.facts}
    stored = EXPECTED["fixtures"]["fixture_with_benchmark"]["stored"]
    for n in ("bid", "mid", "offer"):
        cell = cells[f"T3E.3.r05.{n}"]
        assert cell.status == "known" and format(cell.amount, "f") == stored[f"yield_{n}"]
        assert cell.calculation_id == f"cp3d.yield_{n}" and ("financial", "page:9") in cell.cites
    assert cells["T3E.3.r04.mid"].value_class == "source"
    assert (
        cells["T3E.3.r04.mid"].period
        == "Facility terms in the financial source published 2026-01-10"
    )
    claim = next(c for c in result.claims if c.claim_id == "CP-3D-YLD-01")
    assert claim.refs == ("T3E.3.r05.mid", "T3E.3.r03.mid")
    assert "[" not in claim.text


# --- fix round 1 (mx-adversary on a80aa23) -----------------------------------------------------


def test_lvl_claim_date_is_the_bid_offer_quotation_date_not_the_talk_date() -> None:
    """Talk listed first, with its own January 10 date: LVL-01 still states the quotation date."""
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    talk = raw["observations"].pop(2)
    talk["quote"] = (
        "Published January 10, 2026.\nDealers describe the indicative fair value of the "
        "Northbridge Term Loan as around 99.75."
    )
    talk["as_of_text"] = "January 10, 2026"
    raw["observations"].insert(0, talk)
    sub, ctx = _submission(raw), _context("positive")
    assert cp3d.submission_issues(submission=sub, context=ctx) == ()
    claims = cp3d.market_implied_result(submission=sub, context=ctx).claims
    lvl = next(c for c in claims if c.claim_id == "CP-3D-LVL-01")
    expected = next(
        c for c in EXPECTED["cases"]["positive"]["claims"] if c["claim_id"] == "CP-3D-LVL-01"
    )
    assert lvl.text == expected["text"]


_DIGIT_EDITS = [
    (
        [["technicals.3.limitation", "No rating agency rated it in 2026"]],
        "technicals[3].limitation: digits are not allowed",
    ),
    (
        [
            [
                "terms.margin",
                {
                    "quote": None,
                    "bps_text": None,
                    "absence": {"reason": "No margin in 2026", "follow_up": "Ask"},
                },
            ]
        ],
        "margin.absence.reason: digits are not allowed",
    ),
    (
        [
            [
                "terms.maturity",
                {
                    "quote": None,
                    "date_text": None,
                    "absence": {"reason": "Not stated", "follow_up": "Ask by 2026"},
                },
            ]
        ],
        "maturity.absence.follow_up: digits are not allowed",
    ),
    (
        [
            [
                "terms.amortisation",
                {
                    "quote": None,
                    "value_text": None,
                    "absence": {"reason": "Not 1 schedule", "follow_up": "Ask"},
                },
            ]
        ],
        "amortisation.absence.reason: digits are not allowed",
    ),
]


@pytest.mark.parametrize(("edits", "issue"), _DIGIT_EDITS, ids=lambda x: str(x)[:40])
def test_limitation_and_term_absence_texts_are_digit_free(
    edits: list[list[Any]], issue: str
) -> None:
    raw = _edited(SUBMISSIONS["positive"], edits)
    issues = cp3d.submission_issues(submission=_submission(raw), context=_context("positive"))
    assert list(issues) == [issue]


def test_every_oracle_literal_still_validates() -> None:
    for case in CASES:
        assert (
            cp3d.submission_issues(
                submission=_submission(SUBMISSIONS[case]), context=_context(case)
            )
            == ()
        )
    for entry in SUBMISSIONS["tool_use_refusals"]:
        raw = _edited(SUBMISSIONS["positive"], entry.get("edits", []))
        assert (
            cp3d.submission_issues(submission=_submission(raw), context=_context("positive")) == ()
        )


def test_stored_values_round_half_up_at_a_tie() -> None:
    # lease-literal: CP3D-OWNER-LEASE.md:71 "Stored to 0.1 bp" and :67 (expected.json#arithmetic
    # decimal_context "stored outputs are quantised ROUND_HALF_UP"); a 365-day year makes
    # (100 - price) / years x 100 exact, so an offer of 99.9995 is a 0.05 bp tie and a bid of
    # 99.995 with a 4 percent level is a 0.04005 yield tie (bid below offer: not crossed).
    inputs = cp3d.MarketInputs(
        bid=Decimal("99.995"),
        offer=Decimal("99.9995"),
        talk=None,
        quotation_date=date(2026, 1, 1),
        maturity=date(2027, 1, 1),
        margin_bp=Decimal(0),
        amortisation_zero=True,
        recovery=Decimal(0),
        reference_rate_level=Decimal("0.04"),
    )
    assert inputs.bid is not None and inputs.offer is not None and inputs.bid < inputs.offer
    stored = cp3d.compose(inputs=inputs).stored()
    assert (stored["disc_offer"], stored["dm_offer"], stored["lam_offer"]) == ("0.1", "0.1", "0.1")
    assert stored["yield_bid"] == "0.0401"


# --- LEAD rulings (docs/rulings/2026-10-28-stage1.md: CP-3D D1-D3, Round 2 X1) -----------------


def _claim_texts(raw: dict[str, Any], ctx: cp3d.MarketContext | None = None) -> dict[str, str]:
    ctx = ctx or _context("positive")
    sub = _submission(raw)
    assert cp3d.submission_issues(submission=sub, context=ctx) == ()
    result = cp3d.market_implied_result(submission=sub, context=ctx)
    return {c.claim_id: c.text for c in result.claims}


def _without(kinds: tuple[str, ...]) -> dict[str, Any]:
    raw: dict[str, Any] = copy.deepcopy(SUBMISSIONS["positive"])
    raw["observations"] = [o for o in raw["observations"] if o["kind"] not in kinds]
    return raw


_POSITIVE_CLAIMS = {c["claim_id"]: c["text"] for c in EXPECTED["cases"]["positive"]["claims"]}
_NO_MARKET_CLAIMS = {c["claim_id"]: c["text"] for c in EXPECTED["cases"]["gap_no_market"]["claims"]}


def test_d1_period_without_a_published_line_is_stated_not_refused() -> None:
    # ruling D1: "Without that line, do not fail closed: use `…, publication date not stated`"
    base = _context("positive")
    dropped = {("financial", "page:5"), ("market", "page:2")}
    ctx = cp3d.MarketContext(
        pages=base.pages,
        names=base.names,
        third_party=base.third_party,
        published={k: v for k, v in base.published.items() if k not in dropped},
        run_as_of=base.run_as_of,
    )
    result = cp3d.market_implied_result(
        submission=_submission(SUBMISSIONS["positive"]), context=ctx
    )
    cells = {c.fact_id: c for t in result.tables for r in t.rows for c in r.facts}
    terms = "Facility terms in the financial source, publication date not stated"
    assert cells["T3E.3.r02.mid"].period == terms
    assert cells["T3E.1.r03.level"].period == "Commentary, publication date not stated"
    assert cells["T3E.2.r04.value"].period == (
        "Commentary, publication date not stated and quotation of 2026-01-09"
    )


def test_d1_published_line_needs_its_full_stop() -> None:
    # ruling D1: the cited page's `Published <Month D, YYYY>.` line
    pages = {
        "market": {
            "page:1": "Published January 10, 2026 by the desk",
            "page:2": "Published January 10, 2026.",
        }
    }
    assert cp3d.publication_dates(pages) == {("market", "page:2"): date(2026, 1, 10)}


def test_x1_i_bid_only() -> None:
    texts = _claim_texts(_without(("offer",)))
    assert texts["CP-3D-LVL-01"] == (  # ruling X1 (i)
        "On January 9, 2026 the dealer quotation was {T3E.1.r01.level|%} bid; no offer was "
        "submitted, so the mid is not calculated: [T3E.2.r01.value]."
    )
    assert texts["CP-3D-DM-01"] == _NO_MARKET_CLAIMS["CP-3D-DM-01"]
    assert texts["CP-3D-YLD-01"] == _POSITIVE_CLAIMS["CP-3D-YLD-01"]
    assert texts["CP-3D-PD-01"] == _NO_MARKET_CLAIMS["CP-3D-PD-01"]


def test_x1_ii_offer_only() -> None:
    texts = _claim_texts(_without(("bid",)))
    assert texts["CP-3D-LVL-01"] == (  # ruling X1 (ii)
        "On January 9, 2026 the dealer quotation was {T3E.1.r02.level|%} offer; no bid was "
        "submitted, so the mid is not calculated: [T3E.2.r01.value]."
    )
    assert texts["CP-3D-DM-01"] == _NO_MARKET_CLAIMS["CP-3D-DM-01"]
    assert texts["CP-3D-PD-01"] == _NO_MARKET_CLAIMS["CP-3D-PD-01"]


@pytest.mark.parametrize("dated", (False, True), ids=("undated", "dated"))
def test_x1_iii_talk_only_never_uses_the_talk_date(dated: bool) -> None:
    raw = _without(("bid", "offer"))
    if dated:
        raw["observations"][0]["quote"] = (
            "Published January 10, 2026.\nDealers describe the indicative fair value of the "
            "Northbridge Term Loan as around 99.75."
        )
        raw["observations"][0]["as_of_text"] = "January 10, 2026"
    texts = _claim_texts(raw)
    assert texts["CP-3D-LVL-01"] == (  # ruling X1 (iii)
        "No dealer quotation was submitted: [T3E.1.r01.level] and [T3E.1.r02.level] are not stated; "
        "indicative talk of {T3E.1.r03.level|%} of par is shown as context only."
    )


def test_d2_lvl_date_is_the_bid_as_of_text_verbatim() -> None:
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    talk = raw["observations"].pop(2)
    talk["quote"] = (
        "Published January 10, 2026.\nDealers describe the indicative fair value of the "
        "Northbridge Term Loan as around 99.75."
    )
    talk["as_of_text"] = "January 10, 2026"
    raw["observations"].insert(0, talk)
    assert _claim_texts(raw)["CP-3D-LVL-01"] == _POSITIVE_CLAIMS["CP-3D-LVL-01"]


def test_x1_iv_mid_above_par() -> None:
    page = (
        "Published January 10, 2026.\nDealer quotation on January 9, 2026: bid 100.50 and "
        "offer 101.00, expressed as a percentage of par."
    )
    ctx = _with_page(_context("positive"), "market", "page:9", page)
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    for obs, level in ((raw["observations"][0], "100.50"), (raw["observations"][1], "101.00")):
        obs.update(locator="page:9", quote=page.split("\n")[1], level_text=level)
    sub = _submission(raw)
    assert cp3d.submission_issues(submission=sub, context=ctx) == ()
    result = cp3d.market_implied_result(submission=sub, context=ctx)
    texts = {c.claim_id: c.text for c in result.claims}
    assert texts["CP-3D-DM-01"] == _POSITIVE_CLAIMS["CP-3D-DM-01"]  # known form, negative margin
    assert texts["CP-3D-PD-01"] == (  # ruling X1 (iv)
        "The market-implied default probability is not meaningful: [T3E.5.r01.mid] and "
        "[T3E.5.r02.mid] need a positive simple discount margin, and at the mid the margin is "
        "{T3E.3.r03.mid|bp}."
    )
    cells = {c.fact_id: c for t in result.tables for r in t.rows for c in r.facts}
    dm = cells["T3E.3.r03.mid"]
    assert dm.status == "known" and dm.amount is not None and dm.amount < 0
    assert format(dm.amount, "f") == EXPECTED["fixtures"]["fixture_above_par"]["stored"]["dm_mid"]
    assert (
        cells["T3E.5.r01.mid"].limitation
        == "Not meaningful: the simple discount margin is not positive"
    )


_NO_MATURITY = [
    [
        "terms.maturity",
        {"quote": None, "date_text": None, "absence": {"reason": "Not stated", "follow_up": "Ask"}},
    ]
]


def test_x1_v_maturity_absent_without_a_level() -> None:
    texts = _claim_texts(_edited(SUBMISSIONS["positive"], _NO_MATURITY))
    assert texts["CP-3D-DM-01"] == (  # ruling X1 (v)
        "The simple discount margin is not calculated: [T3E.3.r03.mid] is not available."
    )
    assert texts["CP-3D-YLD-01"] == _POSITIVE_CLAIMS["CP-3D-YLD-01"]
    assert texts["CP-3D-PD-01"] == _NO_MARKET_CLAIMS["CP-3D-PD-01"]


def test_x1_v_maturity_absent_with_a_quoted_level() -> None:
    page = "Published January 10, 2026.\nThe SOFR reference rate is 4.30 percent."
    ctx = _with_page(_context("positive"), "financial", "page:9", page)
    raw = _edited(SUBMISSIONS["positive"], _NO_MATURITY)
    raw["terms"]["reference_rate"]["absence"] = None
    quote = {"source_id": "financial", "locator": "page:9", "quote": page.split("\n")[1]}
    raw["terms"]["reference_rate"]["level"] = {"quote": quote, "percent_text": "4.30"}
    assert _claim_texts(raw, ctx)["CP-3D-YLD-01"] == (  # ruling X1 (v)
        "The all-in yield is not calculated: [T3E.3.r05.mid] needs a final maturity date, which no "
        "source in the pack states."
    )


def _variants() -> list[tuple[str, dict[str, Any], bool]]:
    """Every combination of observed kinds, recovery, maturity, margin and a quoted level."""
    out = []
    kinds = ("bid", "offer", "indicative_talk")
    for mask in range(1, 8):
        keep = tuple(k for i, k in enumerate(kinds) if mask >> i & 1)
        for recovery in (True, False):
            for maturity in (True, False):
                for margin in (True, False):
                    for level in (True, False):
                        raw = _without(tuple(k for k in kinds if k not in keep))
                        if not recovery:
                            raw["recovery"] = None
                            raw["recovery_absence"] = {"reason": "Not assessed", "follow_up": "Ask"}
                        if not maturity:
                            raw = _edited(raw, _NO_MATURITY)
                        if not margin:
                            absent = {"reason": "Not stated", "follow_up": "Ask"}
                            raw["terms"]["margin"] = {
                                "quote": None,
                                "bps_text": None,
                                "absence": absent,
                            }
                        if level:
                            raw["terms"]["reference_rate"]["absence"] = None
                            q = {
                                "source_id": "financial",
                                "locator": "page:9",
                                "quote": "The SOFR reference rate is 4.30 percent.",
                            }
                            raw["terms"]["reference_rate"]["level"] = {
                                "quote": q,
                                "percent_text": "4.30",
                            }
                        label = f"{'+'.join(keep)}|rec={recovery}|mat={maturity}|mg={margin}|lvl={level}"
                        out.append((label, raw, level))
    return out


@pytest.mark.parametrize(
    ("label", "raw", "level"), _variants(), ids=lambda x: x if isinstance(x, str) else ""
)
def test_x1_nothing_that_validates_raises(label: str, raw: dict[str, Any], level: bool) -> None:
    page = "Published January 10, 2026.\nThe SOFR reference rate is 4.30 percent."
    ctx = _with_page(_context("positive"), "financial", "page:9", page)
    sub = _submission(raw)
    assert cp3d.submission_issues(submission=sub, context=ctx) == (), label
    result = cp3d.market_implied_result(submission=sub, context=ctx)
    cells = {c.fact_id: c for t in result.tables for r in t.rows for c in r.facts}
    for claim in result.claims:
        for ref in re.findall(r"\{([^|{}]+)\|", claim.text):
            assert cells[ref].status == "known", (label, claim.claim_id, ref)
        for ref in re.findall(r"\[([^\[\]]+)\]", claim.text):
            assert cells[ref].amount is None, (label, claim.claim_id, ref)  # chip names no figure
