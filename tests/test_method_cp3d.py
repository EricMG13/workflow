"""CP-3D Stage 1: the market-implied calculation against the frozen oracle.

Every expected value is read from `cases/cp3d-owner/expected.json`; every input is built from the
oracle's own literals (`submissions.json`), pinned pages (`manifest.json`,
`cases/financial/manifest.json`) and fixtures. Nothing here derives an expected value.
"""

import copy
import hashlib
import json
import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import defect_classes as dc
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


# Oracle pins: cases/PINS.json, the shared manifest LEAD regenerates (python3 -I cases/pins.py).
PINS: dict[str, str] = json.loads((ROOT / "cases" / "PINS.json").read_text(encoding="utf-8"))
PINNED = ("manifest.json", "submissions.json", "expected.json", "builder/build.py")


def test_oracle_files_are_the_pinned_revision() -> None:
    for name in PINNED:
        digest = hashlib.sha256((CASE / name).read_bytes()).hexdigest()
        assert digest == PINS[f"cases/cp3d-owner/{name}"], name


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


def test_x1_talk_only_with_a_level_and_a_stated_maturity_does_not_blame_the_maturity() -> None:
    """mx-precise M1 on 9b871a7: with no quotation date `days` is missing although the maturity
    is stated; YLD-01 must not say that no source states a final maturity date."""
    page = "Published January 10, 2026.\nThe SOFR reference rate is 4.30 percent."
    ctx = _with_page(_context("positive"), "financial", "page:9", page)
    raw = _without(("bid", "offer"))
    raw["terms"]["reference_rate"]["absence"] = None
    quote = {"source_id": "financial", "locator": "page:9", "quote": page.split("\n")[1]}
    raw["terms"]["reference_rate"]["level"] = {"quote": quote, "percent_text": "4.30"}
    assert raw["terms"]["maturity"]["date_text"]
    assert _claim_texts(raw, ctx)["CP-3D-YLD-01"] == (  # ruling round 4 (g)
        "The all-in yield is not calculated: [T3E.3.r05.mid] needs the simple discount margin at "
        "the mid, which is not calculated: [T3E.3.r03.mid]."
    )


def test_g_bid_only_with_a_level_and_a_stated_maturity() -> None:
    page = "Published January 10, 2026.\nThe SOFR reference rate is 4.30 percent."
    ctx = _with_page(_context("positive"), "financial", "page:9", page)
    raw = _without(("offer",))
    raw["terms"]["reference_rate"]["absence"] = None
    quote = {"source_id": "financial", "locator": "page:9", "quote": page.split("\n")[1]}
    raw["terms"]["reference_rate"]["level"] = {"quote": quote, "percent_text": "4.30"}
    assert _claim_texts(raw, ctx)["CP-3D-YLD-01"] == (  # ruling round 4 (g)
        "The all-in yield is not calculated: [T3E.3.r05.mid] needs the simple discount margin at "
        "the mid, which is not calculated: [T3E.3.r03.mid]."
    )


_NO_MARGIN = [
    [
        "terms.margin",
        {"quote": None, "bps_text": None, "absence": {"reason": "Not stated", "follow_up": "Ask"}},
    ]
]


@pytest.mark.parametrize(
    ("label", "kinds_dropped", "edits", "reason"),
    (  # ruling round 4 (h): first missing cause in formula order (years, mid, margin)
        ("maturity absent", (), _NO_MATURITY, "Needs a quotation date and a final maturity date"),
        ("talk only", ("bid", "offer"), [], "Needs a quotation date and a final maturity date"),
        (
            "talk only, no margin",
            ("bid", "offer"),
            _NO_MARGIN,
            "Needs a quotation date and a final maturity date",
        ),
        ("bid only", ("offer",), [], "Needs both an observed bid and an observed offer"),
        (
            "offer only, no margin",
            ("bid",),
            _NO_MARGIN,
            "Needs both an observed bid and an observed offer",
        ),
        ("no margin", (), _NO_MARGIN, "Needs a contractual margin and stated zero amortisation"),
    ),
    ids=lambda x: x if isinstance(x, str) and not x.startswith("Needs") else "",
)
def test_h_t3e7_discount_margin_row_names_the_first_missing_cause(
    label: str, kinds_dropped: tuple[str, ...], edits: list[list[Any]], reason: str
) -> None:
    raw = _edited(_without(kinds_dropped), edits)
    sub, ctx = _submission(raw), _context("positive")
    assert cp3d.submission_issues(submission=sub, context=ctx) == ()
    t7 = next(
        t
        for t in cp3d.market_implied_result(submission=sub, context=ctx).tables
        if t.table_id == "T3E.7"
    )
    rows = {r.label: [c.text for c in r.facts] for r in t7.rows}
    assert rows["Simple discount margin"] == ["Simple discount margin", reason], label


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


# --- LEAD rulings round 6b (docs/rulings/2026-10-28-stage1.md: C1-C3) --------------------------

_SINGLE_BOTH = (
    "Single dealer quotation; the sheet reports no trade in the period to the quotation date"
)


@pytest.mark.parametrize(
    ("dropped", "expected"),
    (  # ruling 6b C1
        ((), _SINGLE_BOTH),
        (
            ("offer",),
            (
                "Single dealer quotation with only the bid observed; trading activity in the period "
                "to the quotation date is not read"
            ),
        ),
        (
            ("bid",),
            (
                "Single dealer quotation with only the offer observed; trading activity in the period "
                "to the quotation date is not read"
            ),
        ),
        (("bid", "offer"), None),
    ),
    ids=("bid+offer", "bid only", "offer only", "talk only"),
)
def test_c1_single_dealer_limitation_follows_the_observations(
    dropped: tuple[str, ...], expected: str | None
) -> None:
    sub, ctx = _submission(_without(dropped)), _context("positive")
    assert cp3d.submission_issues(submission=sub, context=ctx) == ()
    own = cp3d.market_implied_result(submission=sub, context=ctx).own_limitations
    single = [x for x in own if x.startswith("Single dealer quotation")]
    assert single == ([] if expected is None else [expected])
    if expected is None:
        assert "Indicative dealer talk is shown but is not used in any calculation" in own


_C2_PAGE = (
    "Published January 10, 2026.\nDealer quotation on January 9, 2026: bid 98.50 and offer "
    "99.25, expressed as a percentage of par.\nFacility margin is 1250 basis points.\n"
    "The SOFR reference rate is 1234.5 percent.\nA later sheet shows bid 98.123456 and offer 250.50."
)


def _c2_context() -> cp3d.MarketContext:
    base = _with_page(_context("positive"), "financial", "page:9", _C2_PAGE)
    return _with_page(base, "market", "page:9", _C2_PAGE)


def _c2_quote(source_id: str, line: int) -> dict[str, str]:
    return {"source_id": source_id, "locator": "page:9", "quote": _C2_PAGE.split("\n")[line]}


def test_c2_margin_token_that_occurs_gets_the_shape_issue() -> None:
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    raw["terms"]["margin"] = {
        "quote": _c2_quote("financial", 2),
        "bps_text": "1250",
        "absence": None,
    }
    issues = cp3d.submission_issues(submission=_submission(raw), context=_c2_context())
    assert list(issues) == [  # ruling 6b C2
        "margin: bps_text 1250 must have at most three integer digits and four decimal places"
    ]


def test_c2_reference_rate_token_that_occurs_gets_the_shape_issue() -> None:
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    raw["terms"]["reference_rate"]["absence"] = None
    raw["terms"]["reference_rate"]["level"] = {
        "quote": _c2_quote("financial", 3),
        "percent_text": "1234.5",
    }
    issues = cp3d.submission_issues(submission=_submission(raw), context=_c2_context())
    assert list(issues) == [  # ruling 6b C2
        (
            "reference_rate: level percent_text 1234.5 must have at most three integer digits and "
            "four decimal places"
        )
    ]


@pytest.mark.parametrize(
    ("kind", "level", "issue"),
    (  # ruling 6b C2: the level keeps its pinned bound issue; decimals get their own
        (
            "bid",
            "98.123456",
            "observations[0]: level_text 98.123456 must have at most four decimal places",
        ),
        ("offer", "250.50", "observations[1]: level must be above 0 and at most 200"),
    ),
)
def test_c2_level_token_that_occurs_gets_the_shape_or_bound_issue(
    kind: str, level: str, issue: str
) -> None:
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    obs = next(o for o in raw["observations"] if o["kind"] == kind)
    # The later sheet line states no date, so a dateless bid or offer also gets its as_of_text
    # issue; only the first (level) issue is under test.
    obs.update(locator="page:9", quote=_C2_PAGE.split("\n")[4], level_text=level, as_of_text=None)
    issues = cp3d.submission_issues(submission=_submission(raw), context=_c2_context())
    assert issues[0] == issue


@pytest.mark.parametrize(
    ("edits", "issue"),
    (  # ruling 6b C3, frame `<path>: text carries a prohibited conclusion`
        ([["recovery.rationale", "Buy the loan at this convention"]], "recovery.rationale"),
        (
            [["technicals.3.limitation", "We recommend waiting for a rating"]],
            "technicals[3].limitation",
        ),
        ([["instrument.name", "Cheap Northbridge Term Loan"]], "instrument.name"),
        (
            [
                ["recovery", None],
                ["recovery_absence", {"reason": "Not assessed", "follow_up": "Sell first"}],
            ],
            "recovery_absence.follow_up",
        ),
        (
            [
                ["recovery", None],
                ["recovery_absence", {"reason": "An attractive level", "follow_up": "Ask"}],
            ],
            "recovery_absence.reason",
        ),
    ),
    ids=("rationale", "limitation", "instrument", "recovery_follow_up", "recovery_reason"),
)
def test_c3_prohibited_conclusions_in_the_widened_fields(
    edits: list[list[Any]], issue: str
) -> None:
    raw = _edited(SUBMISSIONS["positive"], edits)
    issues = cp3d.submission_issues(submission=_submission(raw), context=_context("positive"))
    assert f"{issue}: text carries a prohibited conclusion" in issues


def test_c3_market_absence_is_checked_and_comes_first() -> None:
    raw = copy.deepcopy(SUBMISSIONS["gap_no_market"])
    raw["market_absence"] = {"reason": "No quotation; overweight on talk", "follow_up": "Ask"}
    raw["summary"]["text"] = "The loan is attractive."
    issues = cp3d.submission_issues(submission=_submission(raw), context=_context("gap_no_market"))
    assert list(issues) == [
        "market_absence.reason: text carries a prohibited conclusion",
        "summary.text: text carries a prohibited conclusion",
    ]


def test_c3_quotes_are_never_checked() -> None:
    page = "Published January 10, 2026.\nThe dealer would buy at around 99.75."
    ctx = _with_page(_context("positive"), "market", "page:9", page)
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    talk = next(o for o in raw["observations"] if o["kind"] == "indicative_talk")
    talk.update(locator="page:9", quote=page.split("\n")[1])
    assert cp3d.submission_issues(submission=_submission(raw), context=ctx) == ()


def test_c3_only_the_pinned_summary_refusal_hits_among_frozen_literals() -> None:
    hits = []
    for entry in MUTATIONS["entries"]:
        raw = _edited(SUBMISSIONS[MUTATIONS["base"]], entry["edits"])
        issues = cp3d.submission_issues(submission=_submission(raw), context=_context("positive"))
        if any("prohibited conclusion" in i for i in issues):
            hits.append(entry["id"])
    assert hits == ["prohibited_conclusion"] == [MUTATIONS["entries"][14]["id"]]


# --- LEAD rulings round 6e (CP-3D item 3) and the 6b reviewer's Lows ----------------------------

_PROHIBITED_FRAME = "text carries a prohibited conclusion"


def _frame_issues(issues: tuple[str, ...]) -> list[str]:
    return [i for i in issues if i.endswith((_PROHIBITED_FRAME, "digits are not allowed"))]


def test_c3_prohibited_conclusion_in_a_technical_text() -> None:
    raw = _edited(SUBMISSIONS["positive"], [["technicals.0.text", "The quote is attractive."]])
    issues = cp3d.submission_issues(submission=_submission(raw), context=_context("positive"))
    assert list(issues) == [f"technicals[0].text: {_PROHIBITED_FRAME}"]


@pytest.mark.parametrize(
    ("edits", "path"),
    (  # ruling 6e item 3: the widened C3 fields, each at its digit check
        (
            [["terms.reference_rate.absence.reason", "No curve; buy one"]],
            "reference_rate.absence.reason",
        ),
        (
            [["terms.reference_rate.absence.follow_up", "Recommend a feed"]],
            "reference_rate.absence.follow_up",
        ),
        (
            [
                [
                    "terms.margin",
                    {
                        "quote": None,
                        "bps_text": None,
                        "absence": {"reason": "Cheap", "follow_up": "Ask"},
                    },
                ]
            ],
            "margin.absence.reason",
        ),
        (
            [
                [
                    "terms.maturity",
                    {
                        "quote": None,
                        "date_text": None,
                        "absence": {"reason": "Not stated", "follow_up": "Sell"},
                    },
                ]
            ],
            "maturity.absence.follow_up",
        ),
        (
            [
                [
                    "terms.amortisation",
                    {
                        "quote": None,
                        "value_text": None,
                        "absence": {"reason": "Undervalued", "follow_up": "Ask"},
                    },
                ]
            ],
            "amortisation.absence.reason",
        ),
        ([["terms.reference_rate.name", "Attractive SOFR"]], "reference_rate.name"),
    ),
    ids=("rr_reason", "rr_follow_up", "margin", "maturity", "amortisation", "rr_name"),
)
def test_6e_widened_fields_get_the_prohibited_check(edits: list[list[Any]], path: str) -> None:
    raw = _edited(SUBMISSIONS["positive"], edits)
    issues = cp3d.submission_issues(submission=_submission(raw), context=_context("positive"))
    assert _frame_issues(issues) == [f"{path}: {_PROHIBITED_FRAME}"]


def test_c3_order_across_fields_with_a_recovery_absence() -> None:
    """Order: market_absence, recovery_absence, instrument.name, term absences, reference_rate
    name then absence, technicals text then limitation, summary; within one field the digit
    issue comes first (the order before C3)."""
    raw = _edited(
        SUBMISSIONS["gap_no_market"],
        [
            ["market_absence.reason", "Overweight is not possible without a quote"],
            ["recovery", None],
            ["recovery_absence", {"reason": "Not assessed", "follow_up": "Sell side input needed"}],
            ["instrument.name", "Cheap Northbridge Term Loan"],
            [
                "terms.margin",
                {
                    "quote": None,
                    "bps_text": None,
                    "absence": {"reason": "Recommend asking", "follow_up": "Ask"},
                },
            ],
            ["terms.reference_rate.name", "Attractive SOFR"],
            ["terms.reference_rate.absence.follow_up", "Buy a curve feed"],
            ["technicals.0.text", "No market level is available to assess, so 2 dealers say buy."],
            ["technicals.0.limitation", "Outperform is not assessed"],
            ["summary.text", "Undervalued."],
        ],
    )
    issues = cp3d.submission_issues(submission=_submission(raw), context=_context("gap_no_market"))
    assert _frame_issues(issues) == [
        f"market_absence.reason: {_PROHIBITED_FRAME}",
        f"recovery_absence.follow_up: {_PROHIBITED_FRAME}",
        f"instrument.name: {_PROHIBITED_FRAME}",
        f"margin.absence.reason: {_PROHIBITED_FRAME}",
        f"reference_rate.name: {_PROHIBITED_FRAME}",
        f"reference_rate.absence.follow_up: {_PROHIBITED_FRAME}",
        "technicals[0].text: digits are not allowed",
        f"technicals[0].text: {_PROHIBITED_FRAME}",
        f"technicals[0].limitation: {_PROHIBITED_FRAME}",
        f"summary.text: {_PROHIBITED_FRAME}",
    ]


def test_c3_order_recovery_rationale_after_the_terms_before_the_technicals() -> None:
    raw = _edited(
        SUBMISSIONS["positive"],
        [
            ["terms.reference_rate.absence.reason", "Cheap curve missing"],
            ["recovery.rationale", "An attractive convention"],
            ["technicals.1.text", "The sheet reports no trade, a buy signal."],
        ],
    )
    issues = cp3d.submission_issues(submission=_submission(raw), context=_context("positive"))
    assert _frame_issues(issues) == [
        f"reference_rate.absence.reason: {_PROHIBITED_FRAME}",
        f"recovery.rationale: {_PROHIBITED_FRAME}",
        f"technicals[1].text: {_PROHIBITED_FRAME}",
    ]


# --- LEAD rulings round 6g (CP-3D leading zeros) ------------------------------------------------

_LZ_PAGE = (
    "Published January 10, 2026.\nDealer quotation on January 9, 2026: bid 0098.50 and offer "
    "0200, expressed as a percentage of par.\nFacility margin is 025 basis points.\n"
    "Mandatory annual amortisation is 00.\nThe SOFR reference rate is 04.30 percent.\n"
    "Facility margin is 0.5 basis points."
)


def _lz_context() -> cp3d.MarketContext:
    base = _with_page(_context("positive"), "financial", "page:9", _LZ_PAGE)
    return _with_page(base, "market", "page:9", _LZ_PAGE)


def _lz_quote(source_id: str, line: int) -> dict[str, str]:
    return {"source_id": source_id, "locator": "page:9", "quote": _LZ_PAGE.split("\n")[line]}


def _lz_level(kind: str, level: str) -> list[list[Any]]:
    index = {"bid": 0, "offer": 1}[kind]
    return [
        [f"observations.{index}.locator", "page:9"],
        [f"observations.{index}.quote", _LZ_PAGE.split("\n")[1]],
        [f"observations.{index}.level_text", level],
    ]


@pytest.mark.parametrize(
    ("edits", "issue"),
    (  # ruling 6g: `<path>: <field> <x> must have no leading zero`
        (
            _lz_level("bid", "0098.50"),
            "observations[0]: level_text 0098.50 must have no leading zero",
        ),
        (_lz_level("offer", "0200"), "observations[1]: level_text 0200 must have no leading zero"),
        (
            [
                [
                    "terms.margin",
                    {"quote": _lz_quote("financial", 2), "bps_text": "025", "absence": None},
                ]
            ],
            "margin: bps_text 025 must have no leading zero",
        ),
        (
            [
                [
                    "terms.amortisation",
                    {"quote": _lz_quote("financial", 3), "value_text": "00", "absence": None},
                ]
            ],
            "amortisation: value_text 00 must have no leading zero",
        ),
        (
            [
                ["terms.reference_rate.absence", None],
                [
                    "terms.reference_rate.level",
                    {"quote": _lz_quote("financial", 4), "percent_text": "04.30"},
                ],
            ],
            "reference_rate: level percent_text 04.30 must have no leading zero",
        ),
    ),
    ids=("bid", "offer", "margin", "amortisation", "reference_rate"),
)
def test_6g_leading_zero_is_refused(edits: list[list[Any]], issue: str) -> None:
    raw = _edited(SUBMISSIONS["positive"], edits)
    issues = cp3d.submission_issues(submission=_submission(raw), context=_lz_context())
    assert issues[0] == issue
    assert not any(
        "decimal places" in i or "at most 200" in i or "integer digits" in i for i in issues
    )


def test_6g_a_single_zero_integer_part_is_fine() -> None:
    raw = _edited(
        SUBMISSIONS["positive"],
        [
            [
                "terms.margin",
                {"quote": _lz_quote("financial", 5), "bps_text": "0.5", "absence": None},
            ]
        ],
    )
    assert cp3d.submission_issues(submission=_submission(raw), context=_lz_context()) == ()


def test_6g_leading_zero_comes_after_occurrence() -> None:
    raw = _edited(
        SUBMISSIONS["positive"],
        [
            [
                "terms.margin",
                {"quote": _lz_quote("financial", 2), "bps_text": "0025", "absence": None},
            ]
        ],
    )
    issues = cp3d.submission_issues(submission=_submission(raw), context=_lz_context())
    assert list(issues) == ["margin: bps_text 0025 does not occur in the quote"]


# --- reads after a normalised quote match (CP-8 adversary M1 class) ----------------------------

_SH = "­"  # soft hyphen: `quotes.normalise` deletes it, so the locator check accepts it
_POSITIVE: dict[str, Any] = SUBMISSIONS["positive"]
_BID_LINE: str = _POSITIVE["observations"][0]["quote"]
_INSTRUMENT_LINE: str = _POSITIVE["instrument"]["quote"]["quote"]
_SH_LINES = (
    "Dealer quotation on January 9, 2026: bid 98.503 and offer 98.50.",
    "Facility margin is 425 basis points.",
    "Mandatory annual amortisation is 10 percent.",
    "The SOFR reference rate is 4.30 percent.",
)


def _soft(text: str, word: str, at: int) -> str:
    """`text` with a soft hyphen `at` characters into its one occurrence of `word`."""
    assert text.count(word) == 1, word
    return text.replace(word, word[:at] + _SH + word[at:])


def _sh_context() -> cp3d.MarketContext:
    page = "\n".join(_SH_LINES)
    return _with_page(
        _with_page(_context("positive"), "financial", "page:9", page), "market", "page:9", page
    )


def _sh_ref(line: int, word: str, at: int) -> dict[str, str]:
    return {
        "source_id": "financial",
        "locator": "page:9",
        "quote": _soft(_SH_LINES[line], word, at),
    }


@pytest.mark.parametrize(
    ("edits", "issue"),
    (
        (  # the CP-8 M1 shape: the page states 98.50, the raw quote holds a token 98
            [
                ["observations.0.quote", _soft(_BID_LINE, "98.50", 2)],
                ["observations.0.level_text", "98"],
            ],
            "observations[0]: level_text 98 does not occur in the quote",
        ),
        (
            [
                ["observations.0.quote", _soft(_BID_LINE, "98.50", 1)],
                ["observations.0.level_text", "8.50"],
            ],
            "observations[0]: level_text 8.50 does not occur in the quote",
        ),
        (  # the page's bid is 98.503; 98.50 is its offer
            [
                ["observations.0.locator", "page:9"],
                [
                    "observations.0.quote",
                    _soft(_soft(_SH_LINES[0], "98.503", 5), "offer 98.50", 9),
                ],
            ],
            "observations[0]: bid level_text 98.50 is not labelled bid in the quote",
        ),
        (  # talk at the page's bid level, with the bid label split
            [
                ["observations.2.locator", "page:1"],
                ["observations.2.quote", _soft(_BID_LINE, "bid", 1)],
                ["observations.2.level_text", "98.50"],
            ],
            "observations[2]: indicative_talk level_text 98.50 is a bid or offer level in the quote",
        ),
        (
            [["terms.margin", {"quote": _sh_ref(1, "425", 1), "bps_text": "25", "absence": None}]],
            "margin: bps_text 25 does not occur in the quote",
        ),
        (  # the page states 10 percent; a zero would select the simple margin convention
            [
                [
                    "terms.amortisation",
                    {"quote": _sh_ref(2, "10", 1), "value_text": "0", "absence": None},
                ]
            ],
            "amortisation: value_text 0 does not occur in the quote",
        ),
        (
            [
                ["terms.reference_rate.absence", None],
                [
                    "terms.reference_rate.level",
                    {"quote": _sh_ref(3, "4.30", 1), "percent_text": "4"},
                ],
            ],
            "reference_rate: level percent_text 4 does not occur in the quote",
        ),
        (  # a name the page does not state (it holds the soft hyphen)
            [
                ["terms.reference_rate.name", _soft("SOFR", "SOFR", 2)],
                ["terms.reference_rate.quote.quote", _soft("SOFR reference rate", "SOFR", 2)],
            ],
            "reference_rate: name does not occur in the quote",
        ),
        (
            [
                ["instrument.name", _soft("Northbridge Term Loan", "Northbridge", 5)],
                ["instrument.quote.quote", _soft(_INSTRUMENT_LINE, "Northbridge Term Loan", 5)],
            ],
            "instrument: name does not occur in the quote",
        ),
    ),
    ids=(
        "level-split",
        "level-cp8-shape",
        "bid-label",
        "talk-label",
        "margin",
        "amortisation",
        "reference-rate-level",
        "reference-rate-name",
        "instrument-name",
    ),
)
def test_reads_refuse_what_the_normalised_quote_does_not_state(
    edits: list[list[Any]], issue: str
) -> None:
    raw = _edited(_POSITIVE, edits)
    issues = cp3d.submission_issues(submission=_submission(raw), context=_sh_context())
    assert list(issues) == [issue]


@pytest.mark.parametrize(
    "edits",
    (
        [["observations.1.quote", _soft(_BID_LINE, "offer", 3)]],
        [["observations.0.quote", _soft(_BID_LINE, "2026", 2)]],
        [["terms.maturity.quote.quote", _soft(_INSTRUMENT_LINE, "2029", 2)]],
        [["terms.reference_rate.quote.quote", _soft("SOFR reference rate", "SOFR", 2)]],
        [["instrument.quote.quote", _soft(_INSTRUMENT_LINE, "Northbridge Term Loan", 5)]],
    ),
    ids=("offer-label", "as-of-date", "maturity-date", "reference-rate-name", "instrument-name"),
)
def test_reads_accept_what_the_normalised_quote_states(edits: list[list[Any]]) -> None:
    """A soft hyphen inside the label, date or name: the composition is the positive oracle's."""
    sub, ctx = _submission(_edited(_POSITIVE, edits)), _context("positive")
    assert cp3d.submission_issues(submission=sub, context=ctx) == ()
    result = cp3d.market_implied_result(submission=sub, context=ctx)
    expected = EXPECTED["cases"]["positive"]
    assert [_table_dict(t) for t in result.tables] == expected["tables"]
    assert [c.text for c in result.claims] == [c["text"] for c in expected["claims"]]


# --- round 6h (the CP-3D 6g readings) ----------------------------------------------------------


@pytest.mark.parametrize(
    ("percent", "issues"),
    (
        ("070", ["recovery: percent_text 070 must have no leading zero"]),
        ("0100", ["recovery: percent_text 0100 must have no leading zero"]),  # before the bound
        ("0.5", []),
    ),
)
def test_6h_recovery_percent_text_gets_the_leading_zero_check(
    percent: str, issues: list[str]
) -> None:
    raw = _edited(SUBMISSIONS["positive"], [["recovery.percent_text", percent]])
    got = cp3d.submission_issues(submission=_submission(raw), context=_context("positive"))
    assert list(got) == issues


@pytest.mark.parametrize(
    ("index", "level", "issue"),
    (  # a shape check, so it comes before the label check: neither token is labelled as quoted
        (0, "0200", "observations[0]: level_text 0200 must have no leading zero"),
        (2, "0098.50", "observations[2]: level_text 0098.50 must have no leading zero"),
    ),
    ids=("bid-at-the-offer", "talk-at-the-bid"),
)
def test_6h_leading_zero_comes_before_the_label_check(index: int, level: str, issue: str) -> None:
    raw = _edited(
        SUBMISSIONS["positive"],
        [
            [f"observations.{index}.locator", "page:9"],
            [f"observations.{index}.quote", _LZ_PAGE.split("\n")[1]],
            [f"observations.{index}.level_text", level],
        ],
    )
    issues = cp3d.submission_issues(submission=_submission(raw), context=_lz_context())
    assert list(issues) == [issue]


# --- LEAD round 10, item 1: figure signs in quote readers ---------------------------------------

_SIGNS = {"minus": "−{}", "ascii": "-{}", "en-dash": "–{}", "parentheses": "({})"}


def _sign_lines(form: str) -> tuple[str, ...]:
    """Every reader's line with its figure printed in `form`; the analyst text stays unsigned."""
    s = _SIGNS[form].format
    return (
        f"Dealer quotation on January 9, 2026: bid {s('98.50')} and offer 99.25.",
        f"Dealer quotation on January 9, 2026: bid 98.50 and offer {s('99.25')}.",
        f"Dealers describe the indicative fair value as around {s('99.75')}.",
        f"Facility margin is {s('425')} basis points.",
        f"Mandatory annual amortisation is {s('0')}.",
        f"The SOFR reference rate is {s('4.30')} percent.",
    )


def _sign_context(lines: tuple[str, ...]) -> cp3d.MarketContext:
    page = "\n".join(lines)
    return _with_page(
        _with_page(_context("positive"), "financial", "page:9", page), "market", "page:9", page
    )


def _sign_ref(lines: tuple[str, ...], line: int) -> dict[str, str]:
    return {"source_id": "financial", "locator": "page:9", "quote": lines[line]}


def _sign_edits(lines: tuple[str, ...], reader: str, text: str) -> list[list[Any]]:
    """The positive oracle with one reader's quote moved to `lines` and its text set to `text`."""
    if reader in ("bid", "offer", "talk"):
        i = ("bid", "offer", "talk").index(reader)
        return [
            [f"observations.{i}.locator", "page:9"],
            [f"observations.{i}.quote", lines[i]],
            [f"observations.{i}.level_text", text],
        ]
    if reader == "margin":
        return [["terms.margin", {"quote": _sign_ref(lines, 3), "bps_text": text, "absence": None}]]
    if reader == "amortisation":
        amort = {"quote": _sign_ref(lines, 4), "value_text": text, "absence": None}
        return [["terms.amortisation", amort]]
    level = {"quote": _sign_ref(lines, 5), "percent_text": text}
    return [["terms.reference_rate.absence", None], ["terms.reference_rate.level", level]]


_UNSIGNED = (  # (reader, the unsigned analyst text, the pinned issue it gets under the rule)
    ("bid", "98.50", "observations[0]: level_text 98.50 does not occur in the quote"),
    ("offer", "99.25", "observations[1]: level_text 99.25 does not occur in the quote"),
    ("talk", "99.75", "observations[2]: level_text 99.75 does not occur in the quote"),
    ("margin", "425", "margin: bps_text 425 does not occur in the quote"),
    ("amortisation", "0", "amortisation: value_text 0 does not occur in the quote"),
    (
        "reference_rate",
        "4.30",
        "reference_rate: level percent_text 4.30 does not occur in the quote",
    ),
)


@pytest.mark.parametrize("form", tuple(_SIGNS))
@pytest.mark.parametrize(("reader", "text", "issue"), _UNSIGNED, ids=[u[0] for u in _UNSIGNED])
def test_r10_unsigned_text_against_a_signed_figure_does_not_occur(
    form: str, reader: str, text: str, issue: str
) -> None:
    """Round 10 item 1 and its Parentheses ruling: the quote prints a negative figure, so the
    unsigned `*_text` does not occur; the pinned issue fires at the occurrence check."""
    lines = _sign_lines(form)
    raw = _edited(_POSITIVE, _sign_edits(lines, reader, text))
    issues = cp3d.submission_issues(submission=_submission(raw), context=_sign_context(lines))
    assert list(issues) == [issue]


@pytest.mark.parametrize(
    ("reader", "line", "text"),
    (  # a `-` after a letter or a digit is not a sign; `+` is ignored; a parenthesis that does
        # not close directly after the digits leaves the figure unsigned
        ("talk", "Dealers describe the indicative fair value as around 95-96.", "96"),
        ("talk", "Dealers describe the indicative fair value as around 95–96.", "96"),
        ("margin", "Facility margin is S-350 basis points.", "350"),
        ("margin", "Facility margin is +425 basis points.", "425"),
        ("margin", "Facility margin (set at 425) is in basis points.", "425"),
        ("reference_rate", "The SOFR reference rate (4.30 percent) applies.", "4.30"),
    ),
    ids=("95-96", "95-en-dash-96", "S-350", "plus", "close-paren-only", "open-paren-only"),
)
def test_r10_non_sign_forms_still_validate(reader: str, line: str, text: str) -> None:
    index = {"talk": 2, "margin": 3, "reference_rate": 5}[reader]
    lines = tuple(line if i == index else x for i, x in enumerate(_sign_lines("ascii")))
    raw = _edited(_POSITIVE, _sign_edits(lines, reader, text))
    ctx = _sign_context(lines)
    assert cp3d.submission_issues(submission=_submission(raw), context=ctx) == ()


def test_r10_a_hyphen_after_a_digit_leaves_the_token_to_its_shape_check() -> None:
    """`2024-2025`: the `-` follows a digit, so `2025` occurs and gets the shape issue."""
    lines = (*_sign_lines("ascii")[:5], "The SOFR reference rate is quoted for 2024-2025.")
    raw = _edited(_POSITIVE, _sign_edits(lines, "reference_rate", "2025"))
    issues = cp3d.submission_issues(submission=_submission(raw), context=_sign_context(lines))
    assert list(issues) == [f"reference_rate: level percent_text 2025 {cp3d._SHAPE}"]


@pytest.mark.parametrize(
    ("reader", "text", "issue"),
    (  # a signed analyst text keeps today's refusal
        ("bid", "-98.50", "observations[0]: level_text -98.50 is not a decimal number"),
        ("margin", "-425", f"margin: bps_text -425 {cp3d._SHAPE}"),
        ("amortisation", "-0", f"amortisation: value_text -0 {cp3d._SHAPE}"),
        ("reference_rate", "-4.30", f"reference_rate: level percent_text -4.30 {cp3d._SHAPE}"),
    ),
    ids=("bid", "margin", "amortisation", "reference_rate"),
)
def test_r10_signed_analyst_text_keeps_its_refusal(reader: str, text: str, issue: str) -> None:
    lines = _sign_lines("ascii")
    raw = _edited(_POSITIVE, _sign_edits(lines, reader, text))
    issues = cp3d.submission_issues(submission=_submission(raw), context=_sign_context(lines))
    assert list(issues) == [issue]


# --- LEAD round 11: the shared defect classes (tests/defect_classes.py; AGENTS.md rules 3, 4) ---

_CLASS_LOC = "page:9"  # a fresh locator of the cited source carries the case page
_CLASS_TAIL = " Quoted on January 9, 2026."  # a bid needs its as_of_text in the quote
_Edits = Callable[[dict[str, str], str], list[list[Any]]]


def _class_adapter(case: str, source_id: str, edits: _Edits) -> dc.Adapter:
    """The frozen `case` submission with one field set to the value against the case quote,
    which sits on the case page at `source_id` `page:9`."""

    def adapter(page: str, quote: str, value: str) -> tuple[str, ...]:
        ref = {"source_id": source_id, "locator": _CLASS_LOC, "quote": quote}
        raw = _edited(SUBMISSIONS[case], edits(ref, value))
        ctx = _with_page(_context(case), source_id, _CLASS_LOC, page)
        return cp3d.submission_issues(submission=_submission(raw), context=ctx)

    return adapter


def _obs_edits(index: int) -> _Edits:
    return lambda ref, value: [
        [f"observations.{index}.locator", ref["locator"]],
        [f"observations.{index}.quote", ref["quote"]],
        [f"observations.{index}.level_text", value],
    ]


_CLASS_FIGURES: tuple[tuple[str, dc.Adapter, str], ...] = (  # (reader, adapter, pinned refusal)
    (
        "margin",
        _class_adapter(
            "positive",
            "financial",
            lambda r, v: [["terms.margin", {"quote": r, "bps_text": v, "absence": None}]],
        ),
        "margin: bps_text {} does not occur in the quote",
    ),
    (
        "amortisation",
        _class_adapter(
            "positive",
            "financial",
            lambda r, v: [["terms.amortisation", {"quote": r, "value_text": v, "absence": None}]],
        ),
        "amortisation: value_text {} does not occur in the quote",
    ),
    (
        "reference_rate.level",
        _class_adapter(
            "positive",
            "financial",
            lambda r, v: [
                ["terms.reference_rate.absence", None],
                ["terms.reference_rate.level", {"quote": r, "percent_text": v}],
            ],
        ),
        "reference_rate: level percent_text {} does not occur in the quote",
    ),
    (
        "talk",
        _class_adapter("positive", "market", _obs_edits(2)),
        "observations[2]: level_text {} does not occur in the quote",
    ),
)


@pytest.mark.parametrize("c", dc.FIGURE_CASES, ids=[c.case_id for c in dc.FIGURE_CASES])
@pytest.mark.parametrize(
    ("reader", "adapter", "refusal"), _CLASS_FIGURES, ids=[r[0] for r in _CLASS_FIGURES]
)
def test_r11_class_figure_cases(
    reader: str, adapter: dc.Adapter, refusal: str, c: dc.QuoteCase
) -> None:
    """Soft hyphen, dashes, NBSP, signs and parentheses (round 10) and the edge cut (round 11 B1)
    through every unlabelled figure reader (`_token_once`)."""
    assert dc.quote_failure(c, adapter, refusal.format(c.value)) is None


_BID = _class_adapter("positive", "market", _obs_edits(0))


def _bid(page: str, quote: str, value: str) -> tuple[str, ...]:
    return tuple(_BID(page + _CLASS_TAIL, quote + _CLASS_TAIL, value))


_LABEL_CASES = tuple(c for f in dc.FIGURES for c in dc.label_cases("bid", f))


@pytest.mark.parametrize("c", _LABEL_CASES, ids=[f"{c.case_id}-{c.value}" for c in _LABEL_CASES])
def test_r11_class_label_cases(c: dc.QuoteCase) -> None:
    """The bid reader (`_token_once`, then `_labelled`): an accepted case gets neither refusal."""
    labelled = f"observations[0]: bid level_text {c.value} is not labelled bid in the quote"
    assert dc.quote_failure(c, _bid, labelled) is None
    if c.accepted:
        occurs = f"observations[0]: level_text {c.value} does not occur in the quote"
        assert dc.quote_failure(c, _bid, occurs) is None


_CLASS_TEXTS: tuple[tuple[str, dc.Adapter, str], ...] = (
    (
        "instrument.name",
        _class_adapter(
            "positive", "market", lambda r, v: [["instrument", {"name": v, "quote": r}]]
        ),
        "instrument: name does not occur in the quote",
    ),
    (
        "reference_rate.name",
        _class_adapter(
            "positive",
            "financial",
            lambda r, v: [["terms.reference_rate.name", v], ["terms.reference_rate.quote", r]],
        ),
        "reference_rate: name does not occur in the quote",
    ),
)


@pytest.mark.parametrize("c", dc.TEXT_CASES, ids=[c.case_id for c in dc.TEXT_CASES])
@pytest.mark.parametrize(
    ("reader", "adapter", "refusal"), _CLASS_TEXTS, ids=[r[0] for r in _CLASS_TEXTS]
)
def test_r11_class_text_cases(
    reader: str, adapter: dc.Adapter, refusal: str, c: dc.QuoteCase
) -> None:
    """Soft hyphen, NBSP and the wrap refusal (round 11 B3) through both name readers."""
    assert dc.quote_failure(c, adapter, refusal) is None


@pytest.mark.parametrize(
    ("reader", "adapter", "refusal"), _CLASS_TEXTS, ids=[r[0] for r in _CLASS_TEXTS]
)
def test_r11_b3_names_the_wrap_refusal_accepts(
    reader: str, adapter: dc.Adapter, refusal: str
) -> None:
    """Round 11 B3 refuses a name with `- ` only in a wrapped quote. An unwrapped quote that
    prints `- ` keeps the name, and a wrapped quote keeps a name with a plain hyphen (whose
    digit takes its own refusal)."""
    page = "The Acme first- priority Term Loan is quoted."
    assert adapter(page, page, "Acme first- priority Term Loan") == ()
    wrapped = "The Acme Term Loan B-2 first-\npriority tranche is quoted."
    issues = tuple(adapter(wrapped, wrapped, "Acme Term Loan B-2"))
    assert refusal not in issues
    assert issues == (f"{reader}: digits are not allowed",)


def test_r11_b1_an_overlapping_occurrence_is_read() -> None:
    """Every occurrence of the quote on the page is read, one that overlaps the one before it
    included: the second `5 .5` in `x 5 .5 .5` starts inside `.5`, so its figure is cut."""
    assert cp3d._whole_on_page("5", "5 .5", "x 5 .5")
    assert not cp3d._whole_on_page("5", "5 .5", "x 5 .5 .5")


def _blank_adapter(case: str, path: str, absent: str | None = None) -> dc.Adapter:
    """The frozen `case` submission with the text at `path` set to the value (the frozen quotes
    stay); `absent` first records that term as absent instead of quoted."""

    def adapter(page: str, quote: str, value: str) -> tuple[str, ...]:
        edits: list[list[Any]] = []
        if absent is not None:
            absence = {"reason": "Not stated in the pack", "follow_up": "Supply the term"}
            edits.append([f"terms.{absent}", {"quote": None, "absence": absence}])
        raw = _edited(SUBMISSIONS[case], [*edits, [path, value]])
        return cp3d.submission_issues(submission=_submission(raw), context=_context(case))

    return adapter


_CLASS_BLANKS: tuple[tuple[str, dc.Adapter], ...] = (  # (issue path, adapter): every text field
    ("instrument.name", _blank_adapter("positive", "instrument.name")),
    ("reference_rate.name", _blank_adapter("positive", "terms.reference_rate.name")),
    *(
        (
            f"reference_rate.absence.{f}",
            _blank_adapter("positive", f"terms.reference_rate.absence.{f}"),
        )
        for f in ("reason", "follow_up")
    ),
    *(
        (f"{t}.absence.{f}", _blank_adapter("positive", f"terms.{t}.absence.{f}", t))
        for t in ("maturity", "margin", "amortisation")
        for f in ("reason", "follow_up")
    ),
    ("recovery.rationale", _blank_adapter("positive", "recovery.rationale")),
    *(
        (f"{k}.{f}", _blank_adapter(case, f"{k}.{f}"))
        for k, case in (
            ("recovery_absence", "gap_no_recovery"),
            ("market_absence", "gap_no_market"),
        )
        for f in ("reason", "follow_up")
    ),
    *(
        (f"technicals[{i}].text", _blank_adapter("positive", f"technicals.{i}.text"))
        for i in range(len(SUBMISSIONS["positive"]["technicals"]))
    ),
    ("technicals[3].limitation", _blank_adapter("positive", "technicals.3.limitation")),
    ("summary.text", _blank_adapter("positive", "summary.text")),
)


@pytest.mark.parametrize("c", dc.BLANK_CASES, ids=[c.case_id for c in dc.BLANK_CASES])
@pytest.mark.parametrize(("path", "adapter"), _CLASS_BLANKS, ids=[b[0] for b in _CLASS_BLANKS])
def test_r11_class_blank_text(path: str, adapter: dc.Adapter, c: dc.BlankCase) -> None:
    """Round 11 blank text: CP-3D pins no empty-text frame, so `<path>: empty text`."""
    assert dc.blank_failure(c, adapter, dc.EMPTY_TEXT.format(path=path)) is None


_MARGIN_CLASS = _CLASS_FIGURES[0][1]
_MARGIN_25 = "margin: bps_text 25 does not occur in the quote"
_R11_QUOTE = "25 percent over the reference rate."


@pytest.mark.parametrize(
    ("page", "accepted"),
    (  # round 11 B1 beyond the shared cases: the quote "25 percent ..." at the start edge
        ("Its level moved by -\n25 percent over the reference rate.", False),  # joined reading
        ("Its level moved by\n25 percent over the reference rate.", True),
        (f"The cap is 4{_R11_QUOTE} The level is {_R11_QUOTE}", False),  # one of two is cut
        (f"The cap is {_R11_QUOTE} The level is {_R11_QUOTE}", True),
        ("The level is 0.25 percent over the reference rate.", False),  # `.` before the figure
        ("The level is 0. 25 percent over the reference rate.", True),
    ),
    ids=("wrapped-minus", "wrapped-plain", "one-of-two-cut", "both-whole", "dot", "dot-space"),
)
def test_r11_b1_every_occurrence_in_every_page_reading(page: str, accepted: bool) -> None:
    """The figure occurs only if each occurrence of the quote, in `normalise(page)` and in the
    joined reading of a wrapped page, has the same unsigned whole figure on the page."""
    issues = _MARGIN_CLASS(page, _R11_QUOTE, "25")
    assert (_MARGIN_25 not in issues) is accepted


@pytest.mark.parametrize(("page", "accepted"), (("250", False), ("25", True)), ids=("cut", "whole"))
def test_r11_b1_a_wrapped_quote_is_read_joined_on_the_page(page: str, accepted: bool) -> None:
    """The quote's joined reading (`quotes.reading(quote, join_wraps=True).text`) is a needle too:
    only it is on the page, and the figure at its end edge is checked there."""
    line = f"Margin on the first-priority {page} basis points."
    issues = _MARGIN_CLASS(line, "first-\npriority 25", "25")
    assert (_MARGIN_25 not in issues) is accepted


@pytest.mark.parametrize(
    ("reader", "line", "text", "issue"),
    (  # round 11 B2 (Modules): a signed text inside accounting parentheses keeps the shape issue
        (
            "margin",
            "Facility margin is (-425) basis points.",
            "-425",
            f"margin: bps_text -425 {cp3d._SHAPE}",
        ),
        (
            "margin",
            "Facility margin is (425) basis points.",
            "425",
            "margin: bps_text 425 does not occur in the quote",
        ),
        (
            "reference_rate",
            "The SOFR reference rate is (-4.30) percent.",
            "-4.30",
            f"reference_rate: level percent_text -4.30 {cp3d._SHAPE}",
        ),
        (
            "amortisation",
            "Mandatory annual amortisation is (-0).",
            "-0",
            f"amortisation: value_text -0 {cp3d._SHAPE}",
        ),
    ),
    ids=("margin-signed", "margin-unsigned", "reference_rate-signed", "amortisation-signed"),
)
def test_r11_b2_parentheses_read_only_around_a_digit(
    reader: str, line: str, text: str, issue: str
) -> None:
    index = {"margin": 3, "amortisation": 4, "reference_rate": 5}[reader]
    lines = tuple(line if i == index else x for i, x in enumerate(_sign_lines("ascii")))
    raw = _edited(_POSITIVE, _sign_edits(lines, reader, text))
    issues = cp3d.submission_issues(submission=_submission(raw), context=_sign_context(lines))
    assert list(issues) == [issue]


@pytest.mark.parametrize(
    ("page", "accepted"),
    (("The level is 25.5 percent.", False), ("The level is 25. It holds.", True)),
    ids=("decimal-cut", "full-stop"),
)
def test_r11_b1_a_full_stop_after_the_figure_is_still_its_end_edge(
    page: str, accepted: bool
) -> None:
    """`The level is 25.`: only `.` follows the figure, so the page must not go on with a digit."""
    issues = _MARGIN_CLASS(page, "The level is 25.", "25")
    assert (_MARGIN_25 not in issues) is accepted
