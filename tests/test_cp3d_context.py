"""Phase 3 Task 2 (Design 9): CP-3D offers the context file's quotes as Python-built observations.

Every expected string comes from the frozen oracle `cases/cp3-context-owner/expected.json#cp3d`
(and `cases/cp3d-owner` for the rest of the submission). The packs are the cp3d-owner positive
sources plus a `context` source built by `preparation.prepare_source`, under the
cp3-context-owner manifest `run` (`credit_snapshot`, `ctx3-<case>-v1`, P3-P10).
"""

import copy
import hashlib
import importlib
import json
from datetime import date
from pathlib import Path
from typing import Any, cast

import pytest

from deploy_vii.contracts import Fact, Run, Source, Span
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow.owners import cp3d

base: Any = importlib.import_module("test_method_cp3d")
conn: Any = importlib.import_module("test_connect_cp3d")

ROOT = Path(__file__).parents[1]
CASE = ROOT / "cases/cp3-context-owner"
EXP: dict[str, Any] = json.loads((CASE / "expected.json").read_text())["cp3d"]
MAN: dict[str, Any] = json.loads((CASE / "manifest.json").read_text())
OFFERED: dict[str, list[dict[str, Any]]] = EXP["offered_observations"]
REFUSALS: dict[str, dict[str, Any]] = {r["id"]: r for r in EXP["refusals"]}
SEVEN = ("row", "kind", "source_id", "locator", "quote", "level_text", "as_of_text")
POSITIVE = base.SUBMISSIONS["positive"]
SINGLE_OLD = (
    "Single dealer quotation; the sheet reports no trade in the period to the quotation date"
)
SINGLE_NEW = (
    "Single dealer quotation from the context file (user-supplied); trading activity is not read"
)
UNREADABLE = "context source unreadable: "
BY_PYTHON = "context market evidence is built by Python; cite it by row id"
PAIR = (
    "observations[{i}] and observations[{j}]: a context bid or offer must pair with the other "
    "side of the same context quote row"
)
TALK_LABEL = "Indicative talk from the context file (user-supplied)."
SINGLE_ONE_SIDE = (
    "Single dealer quotation from the context file (user-supplied) with only the {side} "
    "observed; trading activity is not read"
)
BOM_ISSUE = "not valid JSON (Unexpected UTF-8 BOM (decode using utf-8-sig) at line 1)"

# The frozen CP-3D positive at HEAD before this change (N1: a no-context submission and its report
# keep their hashes).
POSITIVE_SUBMISSION_SHA256 = "7058435598fee14056bf912e9b5ea8f68f43115a7c8e86d5792346c7b11b9c42"
POSITIVE_REPORT_SHA256 = "1e6ec16d1add4397dd298de52a5b2b67266a6edba462ab5e30e7675492d30a1e"


def context_pack(name: str, raw: bytes | None = None) -> PreparedPack:
    path = f"cases/cp3-context-owner/contexts/{name}.json"
    request = SourceRequest(source_id="context", path=path, media_type="text/plain")
    data = (CASE / "contexts" / f"{name}.json").read_bytes() if raw is None else raw
    plain = conn._pack("positive")
    fields = {k: v for k, v in MAN["run"].items() if k in Run.model_fields and k != "run_id"}
    run = Run.model_validate_json(json.dumps({**fields, "run_id": f"ctx3-{name}-v1"}))
    return PreparedPack(run=run, sources=(*plain.sources, prepare_source(request, data)))


def upstream(name: str) -> cp3d.Upstream:
    return cp3d.upstream_of(pack=context_pack(name), cp0=conn._cp0("positive"))


def submission(observations: list[dict[str, Any]]) -> cp3d.MarketImpliedSubmission:
    return cast(
        cp3d.MarketImpliedSubmission,
        base._submission(base._edited(POSITIVE, [["observations", observations]])),
    )


def by_row(*rows: str, case: str = "observed-and-talk") -> list[dict[str, Any]]:
    """The submitted form (M2): kind and row id, every other field empty."""
    listed = {o["row"]: o for o in OFFERED[case]}
    return [
        {
            "kind": listed[row]["kind"],
            "source_id": "",
            "locator": "",
            "quote": "",
            "level_text": "",
            "as_of_text": None,
            "context_row": row,
        }
        for row in rows
    ]


def issues_of(sub: cp3d.MarketImpliedSubmission, up: cp3d.Upstream) -> list[str]:
    return list(cp3d.submission_issues(submission=sub, context=up.context))


# --- the offered observations ------------------------------------------------------------------


@pytest.mark.parametrize("case", sorted(OFFERED))
def test_offered_observations_equal_oracle(case: str) -> None:
    up = upstream(case)
    data = cp3d.context_observations_data(up)
    want = OFFERED[case]
    assert [{k: d[k] for k in SEVEN} for d in data] == [{k: w[k] for k in SEVEN} for w in want]
    assert [d["facility_id"] for d in data] == [w["facility_id"] for w in want]
    assert all(set(d) == {*SEVEN, "facility_id"} for d in data)
    assert list(up.context.context_observations) == [w["row"] for w in want]
    assert [
        (o.kind, o.source_id, o.locator, o.quote, o.level_text, o.as_of_text, o.context_row)
        for o in up.context.context_observations.values()
    ] == [
        (w["kind"], "context", w["locator"], w["quote"], w["level_text"], w["as_of_text"], w["row"])
        for w in want
    ]
    assert dict(up.context.context_facilities) == {w["row"]: w["facility_id"] for w in want}
    assert dict(up.context.context_dates) == {
        w["row"]: date.fromisoformat(w["quote_as_of"]) for w in want
    }
    assert up.context.context_errors == ()


def test_context_observations_data() -> None:
    """The pure function the prompt will embed: ids, kinds, dates, level texts (and the facility)."""
    data = cp3d.context_observations_data(upstream("observed-and-talk"))
    assert data == [
        {
            "row": "o01",
            "kind": "bid",
            "source_id": "context",
            "locator": "line:30",
            "quote": '"bid": "98.50"',
            "level_text": "98.50",
            "as_of_text": "January 9, 2026",
            "facility_id": "term-loan",
        },
        {
            "row": "o02",
            "kind": "offer",
            "source_id": "context",
            "locator": "line:31",
            "quote": '"ask": "99.00"',
            "level_text": "99.00",
            "as_of_text": "January 9, 2026",
            "facility_id": "term-loan",
        },
        {
            "row": "o03",
            "kind": "indicative_talk",
            "source_id": "context",
            "locator": "line:43",
            "quote": '"price": "99.25"',
            "level_text": "99.25",
            "as_of_text": "January 10, 2026",
            "facility_id": "term-loan",
        },
    ]
    assert [list(d) for d in data] == [[*SEVEN, "facility_id"]] * 3


def test_no_context_data_is_empty() -> None:
    up = cp3d.upstream_of(pack=conn._pack("positive"), cp0=conn._cp0("positive"))
    assert cp3d.context_observations_data(up) == []


def test_a_context_without_quotes_offers_nothing() -> None:
    up = upstream("no-quotes")
    assert cp3d.context_observations_data(up) == []
    assert up.context.context_errors == ()


def test_talk_only_offers_the_talk_price_only() -> None:
    data = cp3d.context_observations_data(upstream("talk-only"))
    assert [(d["kind"], d["level_text"]) for d in data] == [("indicative_talk", "99.25")]


def test_a_quote_with_an_uncitable_figure_is_not_offered() -> None:
    """P3-P14 (B20a): every colliding row is dropped, none is guessed. Two identical minified rows."""
    raw = (CASE / "contexts/minified.json").read_bytes()
    row = b'{"facility_id":"term-loan","kind":"observed","bid":"98.50","ask":"99.00","price":"98.75","yield_pct":"8.25","spread_bps":"340","as_of":"2026-01-09","provider":"Dealer A"}'
    assert row in raw
    twice = raw.replace(row, row + b"," + row, 1)
    assert twice != raw
    up = cp3d.upstream_of(pack=context_pack("minified", twice), cp0=conn._cp0("positive"))
    data = cp3d.context_observations_data(up)
    assert [(d["kind"], d["level_text"]) for d in data] == [("indicative_talk", "99.25")]
    quote = data[0]["quote"] or ""
    assert quote.startswith('{"facility_id":"term-loan","kind":"indicative_talk"')
    assert quote.endswith('"price":"99.25"')


# --- expansion and composition -----------------------------------------------------------------


def test_context_row_expands_and_composes() -> None:
    up = upstream("observed-and-talk")
    sub = submission(by_row("o01", "o02", "o03"))
    assert issues_of(sub, up) == []
    expanded = cp3d.expand_context_rows(sub, up.context)
    assert expanded.observations == tuple(up.context.context_observations.values())
    assert [o.context_row for o in expanded.observations] == EXP["positive_observed_and_talk"][
        "expanded_equals_offered"
    ]
    result = cp3d.market_implied_result(submission=sub, context=up.context)
    periods = {cell.period for table in result.tables for row in table.rows for cell in row.facts}
    assert EXP["positive_observed_and_talk"]["talk_period"] in periods
    assert "Commentary published 2026-01-10" in periods
    assert EXP["positive_observed_and_talk"]["quotation_period"] in periods
    report = cp3d.market_implied(
        pack=context_pack("observed-and-talk"), submission=sub, upstream=up
    )
    assert report.submission_sha256 == sub.content_hash()  # before expansion (P3-P12)
    assert report.submission_sha256 != expanded.content_hash()
    own = EXP["positive_observed_and_talk"]["own_limitations"]
    plain = base.EXPECTED["cases"]["positive"]["own_limitations"]
    assert plain[0] == own["replaces"]
    assert list(result.own_limitations) == [own["with"], *plain[1:]]
    assert report.limitations == result.own_limitations


def test_a_submission_without_context_rows_is_not_expanded() -> None:
    up = upstream("observed-and-talk")
    sub = base._submission(POSITIVE)
    assert cp3d.expand_context_rows(sub, up.context) is sub


def test_the_talk_period_reads_the_row_date_not_the_page() -> None:
    """P3-P9: `published` keyed by (source, locator) is never fed context lines."""
    up = upstream("observed-and-talk")
    assert up.context.published == base._context("positive").published
    oracle = EXP["positive_observed_and_talk"]["context_dates"]
    assert up.context.context_dates["o03"] == date.fromisoformat(oracle["o03"])


@pytest.mark.parametrize("case", ["cp3d-filled-context-row", "cp3d-unknown-context-row"])
def test_filled_and_unknown_context_row_refused(case: str) -> None:
    entry = REFUSALS[case]
    up = upstream(Path(entry["context"]).stem)
    assert issues_of(submission(entry["observations"]), up) == entry["issues"]


def test_filled_context_row_refused() -> None:
    entry = REFUSALS["cp3d-filled-context-row"]
    up = upstream("observed-and-talk")
    assert issues_of(submission(entry["observations"]), up) == [
        "observations[0]: context_row must stand alone and name a listed row"
    ]
    for field, value in (
        ("source_id", "context"),
        ("locator", "line:30"),
        ("quote", '"bid": "98.50"'),
        ("level_text", "98.50"),
        ("as_of_text", "January 9, 2026"),
    ):
        filled = by_row("o01", "o02", "o03")
        filled[0][field] = value
        assert issues_of(submission(filled), up) == [
            "observations[0]: context_row must stand alone and name a listed row"
        ], field


def test_unknown_context_row_refused() -> None:
    entry = REFUSALS["cp3d-unknown-context-row"]
    up = upstream("observed-and-talk")
    assert issues_of(submission(entry["observations"]), up) == [
        "observations[0]: context_row must stand alone and name a listed row"
    ]
    wrong_kind = by_row("o01", "o02", "o03")
    wrong_kind[0]["kind"] = "offer"
    assert issues_of(submission(wrong_kind), up) == [
        "observations: kind offer appears more than once",
        "observations[0]: context_row must stand alone and name a listed row",
    ]


def test_a_context_row_with_no_context_in_the_pack_is_unknown() -> None:
    up = cp3d.upstream_of(pack=conn._pack("positive"), cp0=conn._cp0("positive"))
    assert issues_of(submission(by_row("o01", "o02", "o03")), up) == [
        f"observations[{i}]: context_row must stand alone and name a listed row" for i in range(3)
    ]


def test_mixed_facilities_refused() -> None:
    entry = REFUSALS["cp3d-mixed-facilities"]
    up = upstream("unmatched")
    assert issues_of(submission(entry["observations"]), up) == entry["issues"]
    same = by_row("o01", "o02")
    assert issues_of(submission(same), up) == []


def test_context_not_third_party_ok_only_when_listed() -> None:
    up = upstream("observed-and-talk")
    assert "context" not in up.context.third_party
    listed = submission(by_row("o01", "o02", "o03"))
    assert issues_of(listed, up) == []
    written_out = [
        {**o.model_dump(), "context_row": None} for o in up.context.context_observations.values()
    ]
    refused = issues_of(submission(written_out), up)
    assert refused == [f"observations[{i}]: {BY_PYTHON}" for i in range(3)]


def test_other_sources_keep_third_party_rule() -> None:
    """The existing refusals [0..18] of cases/cp3d-owner/expected.json still hold, word for word,
    on a pack that also carries a context file."""
    up = upstream("observed-and-talk")
    listed = base.EXPECTED["refusals"]
    assert len(listed) == 19
    for entry in base.MUTATIONS["entries"]:
        raw = base._edited(POSITIVE, entry["edits"])
        issues = list(cp3d.submission_issues(submission=base._submission(raw), context=up.context))
        assert issues == [entry["issue"]], entry["id"]
    assert [e["issue"] for e in listed] == [e["issue"] for e in base.MUTATIONS["entries"]]


def test_unreadable_context_is_an_issue_not_an_exception() -> None:
    entry = REFUSALS["context-unreadable"]
    up = upstream("bad-bytes")  # no exception escapes upstream_of
    assert up.context.context_observations == {}
    assert list(up.context.context_errors) == entry["issues"]
    assert all(e.startswith(UNREADABLE) for e in up.context.context_errors)
    problems = entry["reader_problems_in_order"]
    assert [e.removeprefix(UNREADABLE) for e in up.context.context_errors] == problems
    for observations in (POSITIVE["observations"], by_row("o01", "o02", "o03")):
        assert issues_of(submission(observations), up) == entry["issues"]
    report_issues = cp3d.validate_market_implied(submission=submission(by_row("o01")), upstream=up)
    assert list(report_issues) == entry["issues"]


def test_non_text_and_multi_line_context_sources_are_unreadable() -> None:
    plain = context_pack("observed-and-talk")
    context = next(s for s in plain.sources if s.source_id == "context")
    others = tuple(s for s in plain.sources if s.source_id != "context")
    cp0 = conn._cp0("positive")

    def refused(source: Source) -> tuple[str, ...]:
        pack = PreparedPack(run=plain.run, sources=(*others, source))
        return cp3d.upstream_of(pack=pack, cp0=cp0).context.context_errors

    assert refused(context.model_copy(update={"media_type": "application/pdf"})) == (
        UNREADABLE + "media type is application/pdf, not text/plain",
    )
    folded = (
        Span(locator="line:1", text="\n".join(s.text for s in context.spans[:2])),
        *context.spans[2:],
    )
    assert refused(context.model_copy(update={"spans": folded})) == (
        UNREADABLE + "a span holds more than one line",
    )
    unavailable = context.model_copy(
        update={
            "status": "unreadable",
            "spans": (),
            "sha256": None,
            "limitation": "no bytes",
            "extraction_status": "blocked",
            "coverage": (),
        }
    )
    assert refused(unavailable) == (UNREADABLE + "sources.context: status is unreadable: no bytes",)


@pytest.mark.parametrize("name", ["no-quotes", "observed-and-talk"])
@pytest.mark.parametrize("json_spans", [True, False])
def test_a_non_text_context_is_refused_on_its_media_type_alone(name: str, json_spans: bool) -> None:
    plain = context_pack(name)
    context = next(s for s in plain.sources if s.source_id == "context")
    others = tuple(s for s in plain.sources if s.source_id != "context")
    spans = (
        context.spans
        if json_spans
        else tuple(s.model_copy(update={"text": "%PDF " + s.text}) for s in context.spans)
    )
    pdf = context.model_copy(update={"media_type": "application/pdf", "spans": spans})
    pack = PreparedPack(run=plain.run, sources=(*others, pdf))
    errors = cp3d.upstream_of(pack=pack, cp0=conn._cp0("positive")).context.context_errors
    assert errors == (UNREADABLE + "media type is application/pdf, not text/plain",)


def test_a_context_that_differs_from_the_run_is_unreadable() -> None:
    plain = context_pack("observed-and-talk")
    other = plain.run.model_copy(update={"issuer_id": "someone-else"})
    pack = PreparedPack(run=other, sources=plain.sources)
    errors = cp3d.upstream_of(pack=pack, cp0=conn._cp0("positive")).context.context_errors
    assert errors == (
        UNREADABLE
        + "identity.issuer_id: context has 'northbridge-synthetic' but the run has 'someone-else'",
    )


# --- staleness and the single-dealer text ------------------------------------------------------


def test_stale_limitation_has_run_as_of() -> None:
    up = upstream("stale")
    exact = EXP["stale"]["cites_exactly_30_days"]
    sub30 = submission(exact["submitted_observations"])
    assert issues_of(sub30, up) == []
    assert [x for x in cp3d.own_limitations(sub30, up.context) if x.startswith("Stale")] == exact[
        "own_limitations_stale"
    ]
    over = EXP["stale"]["cites_31_days"]
    sub31 = submission(over["submitted_observations"])
    assert issues_of(sub31, up) == []
    own = cp3d.own_limitations(sub31, up.context)
    assert [x for x in own if x.startswith("Stale")] == over["own_limitations_stale"]
    assert own.count(over["own_limitations_stale"][0]) == 1  # bid and offer share one line
    assert over["single_dealer"] in own and SINGLE_OLD not in own
    result = cp3d.market_implied_result(submission=sub31, context=up.context)
    assert result.own_limitations == own


def test_only_a_quote_older_than_the_limit_gets_a_stale_line() -> None:
    """Of two bids, 30 and 31 days old, only the older one is named."""
    up = upstream("stale")
    rows = ("o01", "o03")  # bid dated 2025-12-11 (30 days), bid dated 2025-12-10 (31 days)
    sub = submission(by_row(*rows, case="stale"))
    own = cp3d.own_limitations(sub, up.context)
    assert [x for x in own if x.startswith("Stale")] == [
        "Stale quote: term-loan quote dated 2025-12-10 is 31 days before the run as-of 2026-01-10 (limit 30)"
    ]


def test_without_a_context_no_stale_line_is_added() -> None:
    sub = submission(EXP["stale"]["cites_31_days"]["submitted_observations"])
    assert not [x for x in cp3d.own_limitations(sub) if x.startswith("Stale")]
    assert cp3d.own_limitations(sub) == cp3d.own_limitations(sub, None)


def test_single_dealer_text_for_context() -> None:
    up = upstream("observed-and-talk")
    both = cp3d.own_limitations(submission(by_row("o01", "o02", "o03")), up.context)
    assert both[0] == SINGLE_NEW and SINGLE_OLD not in both
    one_side = cp3d.own_limitations(submission(by_row("o01", "o03")), up.context)
    assert one_side[0] == SINGLE_ONE_SIDE.format(side="bid")
    assert SINGLE_NEW not in one_side
    talk_only = cp3d.own_limitations(submission(by_row("o03")), up.context)
    assert SINGLE_NEW not in talk_only and SINGLE_OLD not in talk_only
    sheet = cp3d.own_limitations(base._submission(POSITIVE), up.context)
    assert sheet[0] == SINGLE_OLD and SINGLE_NEW not in sheet


# --- guards: packs without a context are unchanged ---------------------------------------------


def test_no_context_packs_unchanged() -> None:
    sub = base._submission(POSITIVE)
    assert sub.content_hash() == POSITIVE_SUBMISSION_SHA256
    assert "context_row" not in sub.model_dump_json()
    assert "context_row" in submission(by_row("o01")).model_dump_json()
    report = conn._report("positive")
    assert report.submission_sha256 == POSITIVE_SUBMISSION_SHA256
    assert hashlib.sha256(report.model_dump_json().encode()).hexdigest() == POSITIVE_REPORT_SHA256
    up = cp3d.upstream_of(pack=conn._pack("positive"), cp0=conn._cp0("positive"))
    assert up.context == base._context("positive")
    assert up.context.context_observations == {} and up.context.context_errors == ()
    assert cp3d.own_limitations(sub) == tuple(base.EXPECTED["cases"]["positive"]["own_limitations"])


def test_a_context_pack_leaves_the_sheet_report_unchanged_but_for_the_context_page() -> None:
    """A submission citing only the sheet gives the same tables and claims with or without the
    context file in the pack."""
    up = upstream("observed-and-talk")
    sub = base._submission(copy.deepcopy(POSITIVE))
    with_context = cp3d.market_implied_result(submission=sub, context=up.context)
    without = cp3d.market_implied_result(submission=sub, context=base._context("positive"))
    assert with_context.tables == without.tables
    assert with_context.claims == without.claims
    assert with_context.own_limitations == without.own_limitations


# --- fix round 1 -------------------------------------------------------------------------------


def third_party_context_upstream(name: str = "observed-and-talk") -> cp3d.Upstream:
    """CP-0 classes the `context` source third_party (the F3 bypass)."""
    fact = Fact(fact_id="T3.context.authority", label="T3.context.authority", text="third_party")
    cp0 = conn._cp0("positive")
    cp0 = cp0.model_copy(update={"facts": (*cp0.facts, fact)})
    return cp3d.upstream_of(pack=context_pack(name), cp0=cp0)


def test_a_model_written_context_observation_is_refused_whatever_cp0_says() -> None:
    up = third_party_context_upstream()
    assert "context" in up.context.third_party
    sheet = POSITIVE["observations"]
    by_hand = {
        "kind": "indicative_talk",
        "source_id": "context",
        "locator": "line:33",
        "quote": '"yield_pct": "8.25"',
        "level_text": "8.25",
        "as_of_text": None,
        "context_row": None,
    }
    assert issues_of(submission([sheet[0], sheet[1], by_hand]), up) == [
        f"observations[2]: {BY_PYTHON}"
    ]
    copied = {**up.context.context_observations["o03"].model_dump(), "context_row": None}
    assert issues_of(submission([sheet[0], sheet[1], copied]), up) == [
        f"observations[2]: {BY_PYTHON}"
    ]
    assert issues_of(submission(by_row("o01", "o02", "o03")), up) == []
    # the refused hand-written bid is not also reported as an unpaired side
    hand_bid = {
        **by_row("o01")[0],
        "context_row": None,
        "source_id": "context",
        "locator": "line:30",
    }
    assert issues_of(submission([hand_bid, by_row("o02")[0]]), up) == [
        f"observations[0]: {BY_PYTHON}"
    ]


def test_a_context_bid_and_offer_must_come_from_one_quote_row() -> None:
    up = upstream("observed-and-talk")
    sheet = POSITIVE["observations"]
    assert issues_of(submission([by_row("o01")[0], sheet[1]]), up) == [PAIR.format(i=0, j=1)]
    assert issues_of(submission([sheet[0], by_row("o02")[0]]), up) == [PAIR.format(i=0, j=1)]
    assert issues_of(submission([by_row("o02")[0], by_row("o01")[0]]), up) == []
    sheet_pair_with_talk = [sheet[0], sheet[1], by_row("o03")[0]]
    assert issues_of(submission(sheet_pair_with_talk), up) == []


def test_two_context_rows_never_pair() -> None:
    d = json.loads((CASE / "contexts/observed-and-talk.json").read_text())
    d["quotes"].append({**d["quotes"][0], "bid": "98.40", "ask": "98.90", "provider": "Dealer C"})
    up = cp3d.upstream_of(
        pack=context_pack("observed-and-talk", json.dumps(d, indent=2).encode()),
        cp0=conn._cp0("positive"),
    )
    ids = {(o.kind, o.level_text): r for r, o in up.context.context_observations.items()}
    bid, offer = ids[("bid", "98.50")], ids[("offer", "98.90")]
    assert issues_of(submission(by_row_in(up, bid, offer)), up) == [PAIR.format(i=0, j=1)]
    own, other = ids[("bid", "98.40")], ids[("offer", "98.90")]
    assert issues_of(submission(by_row_in(up, own, other)), up) == []


def by_row_in(up: cp3d.Upstream, *rows: str) -> list[dict[str, Any]]:
    return [
        {
            "kind": up.context.context_observations[r].kind,
            "source_id": "",
            "locator": "",
            "quote": "",
            "level_text": "",
            "as_of_text": None,
            "context_row": r,
        }
        for r in rows
    ]


def test_a_cross_row_pair_in_two_facilities_is_only_a_facility_issue() -> None:
    up = upstream("unmatched")
    assert issues_of(submission(REFUSALS["cp3d-mixed-facilities"]["observations"]), up) == [
        "observations mix context facilities"
    ]


def test_context_labels_name_the_user_supplied_file() -> None:
    up = upstream("observed-and-talk")
    sheet = POSITIVE["observations"]
    one_bid = cp3d.own_limitations(submission(by_row("o01")), up.context)
    assert one_bid[0] == SINGLE_ONE_SIDE.format(side="bid")
    one_offer = cp3d.own_limitations(submission(by_row("o02")), up.context)
    assert one_offer[0] == SINGLE_ONE_SIDE.format(side="offer")
    talk_only = cp3d.own_limitations(submission(by_row("o03")), up.context)
    assert TALK_LABEL in talk_only
    with_sheet = cp3d.own_limitations(
        submission([sheet[0], sheet[1], by_row("o03")[0]]), up.context
    )
    assert with_sheet[0] == SINGLE_OLD and TALK_LABEL in with_sheet
    full = cp3d.own_limitations(submission(by_row("o01", "o02", "o03")), up.context)
    assert TALK_LABEL not in full  # the context pair line already says it
    bid_and_talk = cp3d.own_limitations(submission(by_row("o01", "o03")), up.context)
    assert bid_and_talk[0] == SINGLE_ONE_SIDE.format(side="bid") and TALK_LABEL not in bid_and_talk
    sheet_talk = cp3d.own_limitations(base._submission(POSITIVE), up.context)
    assert TALK_LABEL not in sheet_talk


def test_a_double_bom_context_is_a_named_issue() -> None:
    raw = b"\xef\xbb\xbf" + (CASE / "contexts/observed-and-talk.json").read_bytes()
    one = cp3d.upstream_of(pack=context_pack("observed-and-talk", raw), cp0=conn._cp0("positive"))
    assert one.context.context_errors == ()  # preparation strips one BOM
    two_raw = b"\xef\xbb\xbf" + raw
    two = cp3d.upstream_of(
        pack=context_pack("observed-and-talk", two_raw), cp0=conn._cp0("positive")
    )
    assert two.context.context_errors == (UNREADABLE + BOM_ISSUE,)
    assert two.context.context_observations == {}
    assert issues_of(submission(by_row("o01")), two) == [UNREADABLE + BOM_ISSUE]


def test_a_file_the_walk_refuses_is_a_named_issue(monkeypatch: pytest.MonkeyPatch) -> None:
    """The walk's own failures are the named `ContextTextError`, caught where the offers are built."""
    from deploy_workflow import context_cites

    def refuse(*_: object) -> None:
        raise context_cites.ContextTextError("expected ',' or ']' at offset 7")

    monkeypatch.setattr(cp3d, "cite_all", refuse)
    up = upstream("observed-and-talk")
    assert up.context.context_errors == (UNREADABLE + "expected ',' or ']' at offset 7",)


# --- properties the first round left unpinned (mutants D04, D19, D29, D29b, D36, D39, D56) ----


def test_a_row_with_an_uncitable_unoffered_figure_is_not_offered() -> None:
    """D04: B20a covers yield and spread, which are never offered."""
    good = (CASE / "contexts/observed-and-talk.json").read_bytes()
    bad = good.replace(
        b'"yield_pct": "8.25",\n      "spread_bps": "340",',
        b'"yield_pct": "8.25", "spread_bps": "340",',
    )
    assert bad != good
    data = cp3d.context_observations_data(
        cp3d.upstream_of(pack=context_pack("observed-and-talk", bad), cp0=conn._cp0("positive"))
    )
    assert [(d["row"], d["kind"]) for d in data] == [("o01", "indicative_talk")]
    shared_empty = good.replace(
        b'"yield_pct": "",\n      "spread_bps": "335",', b'"yield_pct": "", "spread_bps": "335",'
    )
    assert shared_empty != good
    data = cp3d.context_observations_data(
        cp3d.upstream_of(
            pack=context_pack("observed-and-talk", shared_empty), cp0=conn._cp0("positive")
        )
    )
    assert [d["kind"] for d in data] == ["bid", "offer"]  # the talk row's spread cannot cite


def test_empty_figures_sharing_a_line_block_nothing() -> None:
    good = (CASE / "contexts/observed-and-talk.json").read_bytes()
    packed = good.replace(b'"bid": "",\n      "ask": "",', b'"bid": "", "ask": "",')
    assert packed != good
    up = cp3d.upstream_of(pack=context_pack("observed-and-talk", packed), cp0=conn._cp0("positive"))
    assert [d["kind"] for d in cp3d.context_observations_data(up)] == [
        "bid",
        "offer",
        "indicative_talk",
    ]


@pytest.mark.parametrize(
    ("figure", "issue"),
    [
        ("250", "level must be above 0 and at most 200"),
        ("098.50", "level_text 098.50 must have no leading zero"),
        ("98.12345", "level_text 98.12345 must have at most four decimal places"),
    ],
)
def test_the_range_and_shape_checks_still_run_on_a_listed_row(figure: str, issue: str) -> None:
    """D29b: a listed row skips only third_party, label and as_of; the figure rules still run."""
    good = (CASE / "contexts/observed-and-talk.json").read_bytes()
    raw = good.replace(b'"bid": "98.50"', f'"bid": "{figure}"'.encode())
    raw = raw.replace(b'"ask": "99.00"', b'"ask": "999.00"')
    up = cp3d.upstream_of(pack=context_pack("observed-and-talk", raw), cp0=conn._cp0("positive"))
    assert issues_of(submission(by_row("o01")), up) == [f"observations[0]: {issue}"]


def test_a_listed_figure_must_still_occur_once_in_its_quote() -> None:
    """D29 and the stated fail-safe: a minified bid == ask makes the anchored quote hold the
    number twice, and the offered observation is refused, never accepted with a guessed span."""
    d = json.loads((CASE / "contexts/observed-and-talk.json").read_text())
    d["quotes"][0]["ask"] = "98.50"
    raw = json.dumps(d, separators=(",", ":")).encode()
    up = cp3d.upstream_of(pack=context_pack("observed-and-talk", raw), cp0=conn._cp0("positive"))
    assert issues_of(submission(by_row("o01", "o02")), up) == [
        "observations[1]: level_text 98.50 does not occur in the quote"
    ]


def test_a_context_row_after_a_sheet_observation_is_expanded() -> None:
    """D19: expansion tests every observation, not just the first."""
    up = upstream("observed-and-talk")
    sheet = POSITIVE["observations"]
    mixed = submission([sheet[0], by_row("o03")[0]])
    expanded = cp3d.expand_context_rows(mixed, up.context)
    assert expanded.observations[0] == mixed.observations[0]
    assert expanded.observations[1] == up.context.context_observations["o03"]


def test_context_errors_come_first_among_the_issues() -> None:
    """D36."""
    up = upstream("bad-bytes")
    entry = base.MUTATIONS["entries"][0]
    sub = base._submission(base._edited(POSITIVE, entry["edits"]))
    got = list(cp3d.submission_issues(submission=sub, context=up.context))
    assert got[:2] == list(up.context.context_errors) and entry["issue"] in got[2:]


def test_a_sheet_pair_with_a_context_talk_keeps_the_sheet_text() -> None:
    """D39: only a context bid or offer changes the single-dealer text."""
    up = upstream("observed-and-talk")
    sheet = POSITIVE["observations"]
    sub = submission([sheet[0], sheet[1], by_row("o03")[0]])
    assert issues_of(sub, up) == []
    assert cp3d.own_limitations(sub, up.context)[0] == SINGLE_OLD


def test_a_sheet_only_submission_on_a_stale_context_gets_no_stale_line() -> None:
    """D56."""
    d = json.loads((CASE / "contexts/observed-and-talk.json").read_text())
    for q in d["quotes"]:
        q["as_of"] = "2025-11-01"
    up = cp3d.upstream_of(
        pack=context_pack("observed-and-talk", json.dumps(d, indent=2).encode()),
        cp0=conn._cp0("positive"),
    )
    own = cp3d.own_limitations(base._submission(POSITIVE), up.context)
    assert not [x for x in own if x.startswith("Stale")]
    stale = cp3d.own_limitations(submission(by_row("o01", "o02")), up.context)
    want = (
        "Stale quote: term-loan quote dated 2025-11-01 is 70 days before the run as-of "
        "2026-01-10 (limit 30)"
    )
    assert [x for x in stale if x.startswith("Stale")] == [want]
