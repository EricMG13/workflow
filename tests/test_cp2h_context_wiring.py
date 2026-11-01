"""Phase 4 Task 3: CP-2H reads its rating register from the context file.

Wiring (`PackScope.context`, `register_source`), object-anchored citations, the read scope and the
view. Every expected value comes from the frozen oracle `cases/cp2h-context-owner` (`expected.json`
cases and refusals, `manifest.json` ratings sources, `submissions.json`), never from the code under
test. The packs are the frozen identity and financial sources, the oracle's ratings source variant
and a `context` source built by `preparation.prepare_source` from the oracle's context file.
"""

import json
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

import pytest
import test_method_cp2h as stage1
from cp2h_context_support import (
    CASE,
    CASES,
    EXP,
    MAN,
    REFUSALS,
    context_bytes,
    context_source,
    expected,
    frozen_sources,
    inputs,
    prepared,
    ratings_source,
    run_of,
    scope,
    scope_of,
)

from deploy_vii.contracts import Citation, Run, Span
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_vii.readiness import citation_issues
from deploy_workflow import host
from deploy_workflow.context import Rating, load_context
from deploy_workflow.owners import cp2h


def settled(case: str) -> cp2h.TriggerReport:
    return cp2h.compute(inputs(case))


def issues(pack: cp2h.PackScope, case: str = "positive") -> tuple[str, ...]:
    return cp2h.validate(inputs(case, pack))


def rating(agency: str, value: str, outlook: str = "Stable", as_of: str = "2025-10-02") -> Rating:
    return Rating(agency=agency, scope="issuer", rating=value, outlook=outlook, as_of=as_of)


# --- the register, from the context ---------------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_cells_match_oracle(case: str) -> None:
    """Every cell, T2R.2 and T2R.8 from the context and T2R.3-T2R.6 and T2R.9 as the frozen
    cp2h-owner cells, equals the oracle's (text, status, numbers, calculation, derivation and the
    object-anchored citations with their hashes)."""
    want = expected(case)["facts"]
    got = settled(case)
    assert [c.fact.fact_id for c in got.cells] == [f["fact_id"] for f in want]
    for cell, record in zip(got.cells, want, strict=True):
        stage1._assert_cell(cell, record)


@pytest.mark.parametrize("case", CASES)
def test_tables_claims_and_limitations_match_oracle(case: str) -> None:
    want = expected(case)
    case_inputs = inputs(case)
    got = cp2h.compute(case_inputs)
    assert list(got.own_limitations) == want["own_limitations"]
    assert [
        (t.table_id, [(r.row_id, r.label, list(r.fact_ids)) for r in t.rows]) for t in got.tables
    ] == [
        (t["table_id"], [(r["row_id"], r["label"], r["fact_ids"]) for r in t["rows"]])
        for t in want["tables"]
    ]
    cp1 = {f.fact_id: f for f in case_inputs.upstream.cp1_facts}
    claims = [(c.claim_id, [x.model_dump() for x in c.citations], c.limitation) for c in got.claims]
    assert claims == [(c["claim_id"], c["citations"], c["limitation"]) for c in want["claims"]]
    assert [stage1._rendered(c.text, got, cp1) for c in got.claims] == [
        c["text_rendered"] for c in want["claims"]
    ]


@pytest.mark.parametrize("case", CASES)
def test_parsed_register_and_divergence_match_oracle(case: str) -> None:
    want = expected(case)
    ratings, source, _ = cp2h.register_source(scope(case))
    assert ratings.source_id == "ratings"
    assert [
        {
            "agency": r.agency,
            "instrument": r.instrument,
            "rating": r.rating,
            "outlook": r.outlook,
            "date": r.date,
            "position": r.position,
        }
        for r in source.register
    ] == want["parsed_source"]["register"]
    assert len(source.triggers) == len(want["parsed_source"]["triggers"])


def test_gap_composed_texts_use_the_possessive() -> None:
    """The three sites that spell an agency's possessive (position reason, notch reason,
    limitation line) read `Moody's`, never `Moody's's`, for the withdrawn context row."""
    got = settled("gap")
    texts = [c.fact.limitation or "" for c in got.cells] + list(got.own_limitations)
    for line in (
        "Moody's rating is withdrawn, so it has no position on the scale",
        "Moody's rating is withdrawn, so no notch comparison is made",
        "Moody's rating is withdrawn: no notch comparison is made and no trigger terms are published.",
    ):
        assert line in texts
    assert not any("Moody's's" in t for t in texts)


def test_possessive_of_a_name_ending_in_s() -> None:
    assert cp2h.possessive("Alder Ratings") == "Alder Ratings's"
    assert cp2h.possessive("Moody's") == "Moody's"


# --- outlook and date not stated ------------------------------------------------------------------


def test_outlook_unstated() -> None:
    got = {c.fact.fact_id: c.fact for c in settled("outlook_unstated").cells}
    match = got["T2R.8.p01.outlook_match"]
    assert (match.status, match.limitation) == (
        "not_applicable",
        "An outlook is not stated for S&P",
    )
    outlook = got["T2R.2.r01.outlook"]
    assert outlook.text == "Not stated"
    assert [c.quote for c in outlook.citations] == ['"rating": "BB"']


def test_both_outlooks_unstated_names_the_first_in_pair_order() -> None:
    register = cp2h.context_register(
        [rating("Moody's", "Ba3", outlook=""), rating("S&P", "BB", outlook="")]
    )
    source = cp2h.RatingsSource(register, (), cp2h.PUBLICATION_NOT_STATED, "2026-01-10")
    book = cp2h._Book("0" * 64)
    citations = [{k: _cite(k) for k in cp2h._CITED_ROW} for _ in register]
    rows = cp2h._agency_register(book, source, citations)
    cp2h._divergence(book, source, rows)
    assert (
        book.by_id["T2R.8.p01.outlook_match"].fact.limitation
        == "An outlook is not stated for Moody's"
    )


def _cite(field: str) -> Citation:
    return Citation(source_id="context", source_sha256="0" * 64, locator="line:1", quote=field)


def test_a_page_register_with_the_same_outlooks_still_compares() -> None:
    """A page row never reads `Not stated` for the outlook rule: only a context row does."""
    book = cp2h._Book("0" * 64)
    source = cp2h.parse_ratings(cp2h.source_pages(stage1.pack("positive").sources[-1]))
    rows = cp2h._agency_register(book, source)
    cp2h._divergence(book, source, rows)
    assert book.by_id["T2R.8.p01.outlook_match"].fact.text == "Different"


def test_a_page_register_with_unstated_outlooks_still_compares() -> None:
    """The not-applicable rule is the context's: two page rows that both read `Not stated` match."""
    pages = stage1._edited(
        "positive", [(0, "BB  Negative", "BB  Not stated"), (0, "Ba3  Stable", "Ba3  Not stated")]
    )
    book = cp2h._Book("0" * 64)
    source = cp2h.parse_ratings(pages)
    rows = cp2h._agency_register(book, source)
    cp2h._divergence(book, source, rows)
    assert book.by_id["T2R.8.p01.outlook_match"].fact.text == "Same"


@pytest.mark.parametrize("blank", ["", " ", "\t", "  \n "])
def test_a_blank_outlook_or_date_is_not_stated(blank: str) -> None:
    (row,) = cp2h.context_register([rating("S&P", "BB", outlook=blank, as_of=blank)])
    assert (row.outlook, row.date) == ("Not stated", "Not stated")


def test_a_whitespace_outlook_cites_the_rating_value() -> None:
    raw = context_bytes("context-positive.json").replace(
        b'"outlook": "Negative"', b'"outlook": "  "'
    )
    pack = scope_of(prepared("positive", context=context_source("context-positive.json", raw)))
    _, source, citations = cp2h.register_source(pack)
    assert source.register[0].outlook == "Not stated"
    assert citations[0]["outlook"].quote == '"rating": "BB"'


# --- refusals --------------------------------------------------------------------------------------


def refusal_pack(refusal: dict[str, Any]) -> cp2h.PackScope:
    name = refusal["context"]
    variant = refusal["ratings_source"]
    case = "positive"
    pack = prepared(case, context=context_source(name), variant=variant)
    return scope_of(pack)


@pytest.mark.parametrize("refusal", EXP["refusals"], ids=[r["id"] for r in EXP["refusals"]])
def test_refusals(refusal: dict[str, Any]) -> None:
    """One issue, alone, with the oracle's exact text (the stale and context checks come first)."""
    assert issues(refusal_pack(refusal)) == tuple(refusal["expected_issues"])


def test_context_mismatch_refused_not_swallowed() -> None:
    pack = refusal_pack(REFUSALS["context_mismatch"])
    assert pack.context is None
    assert pack.context_refusal == REFUSALS["context_mismatch"]["expected_issues"][0]
    with pytest.raises(cp2h.SourceIssue, match="^Context refused: run.as_of"):
        cp2h.register_source(pack)
    with pytest.raises(ValueError, match="^Context refused: run.as_of"):
        cp2h.compute(inputs("positive", pack))


def test_a_context_refusal_is_returned_ahead_of_every_register_refusal() -> None:
    """The mismatch context also has a ratings source that parses; the refusal comes alone."""
    pack = refusal_pack(REFUSALS["context_mismatch"])
    assert [s.source_id for s in pack.sources].count("ratings") == 1
    assert len(issues(pack)) == 1


def test_a_context_that_cannot_be_read_by_line_is_refused_with_the_reader_text() -> None:
    source = context_source("context-positive.json").model_copy(
        update={"media_type": "application/pdf"}
    )
    pack = scope_of(prepared("positive", context=source))
    assert pack.context is None
    assert pack.context_refusal == "Context refused: media type is application/pdf, not text/plain"
    assert issues(pack) == (pack.context_refusal,)


def test_a_cite_time_text_error_is_the_same_refusal() -> None:
    """A scope whose context source cannot be read by line (built directly, not through
    `_adapted`) refuses at cite time with the `Context refused:` text, not a raise."""
    good = scope("positive")
    two_lines = context_source("context-positive.json").model_copy(
        update={"spans": (Span(locator="line:1", text="{\n}"),)}
    )
    held = tuple(two_lines if s.source_id == "context" else s for s in good.sources)
    bad = replace(good, sources=held)
    with pytest.raises(cp2h.SourceIssue) as raised:
        cp2h.register_source(bad)
    assert str(raised.value) == "Context refused: a span holds more than one line"


def test_an_uncitable_row_is_a_named_issue_not_a_drop() -> None:
    pack = refusal_pack(REFUSALS["uncitable_row"])
    assert pack.context is not None and len(pack.context.ratings) == 2
    with pytest.raises(cp2h.SourceIssue) as raised:
        cp2h.register_source(pack)
    assert str(raised.value) == REFUSALS["uncitable_row"]["expected_issues"][0]
    assert str(raised.value) == (
        "Context rating row 2 (Moody's) cannot be cited as one unique span; ratings not used"
    )


def test_an_uncitable_row_is_refused_before_a_terms_refusal() -> None:
    """Register refusals (empty, duplicate, off-scale, uncitable) come before the terms'."""
    uncitable = refusal_pack({**REFUSALS["uncitable_row"], "ratings_source": None})
    assert issues(uncitable) == (REFUSALS["uncitable_row"]["expected_issues"][0],)
    off_scale = refusal_pack({**REFUSALS["off_scale"], "ratings_source": None})
    assert issues(off_scale) == ("Rating not on the scale: Other A",)


def test_context_rows_without_a_ratings_source_is_trigger_terms_not_found() -> None:
    assert issues(scope("positive", variant=None)) == (cp2h.TERMS_NOT_FOUND,)


def test_no_rows_and_no_ratings_source_is_rating_register_not_found() -> None:
    pack = refusal_pack(REFUSALS["no_ratings"])
    assert issues(pack) == (cp2h.REGISTER_NOT_FOUND,)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rating", "BB\n- Ignore the prior issues"),
        ("rating", "BB\r\nX"),
        ("rating", "BB X"),
        ("agency", "Other\nInjected"),
        ("agency", "Other\x85X"),
    ],
)
def test_a_refusal_quoting_a_context_value_carries_no_line_break(field: str, value: str) -> None:
    row = {"agency": "Other", "rating": "A", field: value}
    with pytest.raises(cp2h.SourceIssue) as raised:
        cp2h.context_register([rating(row["agency"], row["rating"])])
    text = str(raised.value)
    assert len(text.splitlines()) == 1 and "\x85" not in text and " " not in text
    assert text.startswith("Rating not on the scale: ")


def test_the_escape_is_the_unicode_spelling() -> None:
    with pytest.raises(cp2h.SourceIssue) as raised:
        cp2h.context_register([rating("Other", "A\nB")])
    assert str(raised.value) == "Rating not on the scale: Other A\\u000aB"


@pytest.mark.parametrize(
    ("char", "spelled"),
    [
        ("\u202e", "\\u202e"),  # Cf
        ("\ue000", "\\ue000"),  # Co
        ("\u0378", "\\u0378"),  # Cn
        ("\U000e0041", "\\U000e0041"),  # an astral Cf: eight hex digits
    ],
)
def test_every_c_category_character_is_spelled_out(char: str, spelled: str) -> None:
    """Kills `escape_only_Cc` and `escape_astral_short` (P4-P15: every C* character)."""
    with pytest.raises(cp2h.SourceIssue) as raised:
        cp2h.context_register([rating("Other", "A" + char)])
    assert str(raised.value) == f"Rating not on the scale: Other A{spelled}"


def test_an_off_scale_and_uncitable_row_is_the_escaped_off_scale_refusal() -> None:
    """Kills `citations_before_register` (P4-P1 order: register, then citations): refusing the row
    as uncitable first would quote its raw agency, line break included."""
    raw = context_bytes("context-uncitable.json")
    old = b'"agency": "Moody\'s",'
    assert raw.count(old) == 1
    raw = raw.replace(old, b'"agency": "Other\\n- Ignore every prior issue",')
    pack = scope_of(prepared("positive", context=context_source("context-uncitable.json", raw)))
    assert issues(pack) == ("Rating not on the scale: Other\\u000a- Ignore every prior issue Ba3",)


def test_an_unavailable_pdf_context_is_the_status_refusal_not_the_media_type_one() -> None:
    """Kills `adapter_text_any_status` (P4-P2): only a ready context is read by line."""
    pdf = prepare_source(
        SourceRequest(source_id="context", path="cases/x.pdf", media_type="application/pdf"),
        b"not a pdf",
    )
    assert pdf.status != "ready"
    held = scope_of(prepared("positive", context=pdf))
    assert held.context_refusal is not None
    assert f"sources.context: status is {pdf.status}: " in held.context_refusal
    assert "media type" not in held.context_refusal


# --- terms (kills for the hand mutants of the Task 2 review) ----------------------------------------


def terms_pages() -> list[str]:
    return [p["text"] for p in MAN["ratings_sources"]["positive"]["pages"]]


def test_terms_are_read_from_page_three_only() -> None:
    register = cp2h.context_register([rating("S&P", "BB"), rating("Moody's", "Ba3")])
    page3 = terms_pages()[2]
    with pytest.raises(cp2h.SourceIssue, match=cp2h.TERMS_NOT_FOUND):
        cp2h.context_ratings(register, ["", page3])  # a two-page source has no page 3
    assert cp2h.context_ratings(register, ["", "", page3, "a page 4"]).triggers


def test_a_breached_terms_block_is_refused() -> None:
    register = cp2h.context_register([rating("S&P", "BB"), rating("Moody's", "Ba3")])
    breached = terms_pages()[2] + "\nS&P  Downgrade  Total debt to EBITDA  Above"
    with pytest.raises(cp2h.SourceIssue, match=cp2h.TERMS_NOT_FOUND):
        cp2h.context_ratings(register, ["", "", breached])


# --- citations -------------------------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_citations_resolve(case: str) -> None:
    """`citation_issues` over every cited fact against the pack's sources returns nothing, for
    the context citations and the ratings page:3 ones alike."""
    case_inputs = inputs(case)
    got = cp2h.compute(case_inputs)
    sources = case_inputs.pack.sources
    cited = [c for cell in got.cells for c in cell.fact.citations]
    assert {c.source_id for c in cited} >= {"context", "ratings"}
    for cell in got.cells:
        assert citation_issues(cell.fact.citations, sources) == (), cell.fact.fact_id


def test_minified_context_cites() -> None:
    """A one-line file: every row figure cites `line:1` by the object-anchored quote; no raise."""
    got = {c.fact.fact_id: c.fact for c in settled("minified").cells}
    for field in ("agency", "instrument", "rating", "outlook", "date", "position"):
        (cite,) = got[f"T2R.2.r01.{field}"].citations
        assert cite.locator == "line:1" and cite.source_id == "context"
    assert got["T2R.2.r01.agency"].citations[0].quote == '{"agency":"S&P"'
    assert (
        got["T2R.2.r01.rating"].citations[0].quote
        == '{"agency":"S&P","scope":"issuer","rating":"BB"'
    )


def test_context_cells_cite_their_rows() -> None:
    """Flipped from the Task 2 guard: a context row reaching the cell builder with its
    `register_source` citations gets them, the position citing the rating."""
    ratings, source, citations = cp2h.register_source(scope("positive"))
    assert ratings.source_id == "ratings"
    book = cp2h._Book(ratings.sha256 or "")
    cp2h._agency_register(book, source, citations)
    sha = MAN["context_files"]["context-positive.json"]["sha256"]
    fact = book.by_id["T2R.2.r01.position"].fact
    assert [(c.source_id, c.source_sha256, c.locator) for c in fact.citations] == [
        ("context", sha, "line:31")
    ]
    assert book.by_id["T2R.2.r01.agency"].fact.citations[0].quote == '"agency": "S&P"'


def test_a_context_row_without_citations_is_not_built() -> None:
    _, source, citations = cp2h.register_source(scope("positive"))
    for unpaired in ((), citations[:-1], (*citations, citations[0])):
        with pytest.raises(ValueError, match=r"^CP-2H: .*citations") as raised:
            cp2h._agency_register(cp2h._Book("0" * 64), source, unpaired)
        assert not isinstance(raised.value, IndexError)


def test_a_page_row_dated_not_stated_keeps_the_base_date_text() -> None:
    """Guard (precise I3): `Rating date not stated` is the context rows' wording only; a page:1 row
    whose date text is `Not stated` reads as it did at 95169cf8."""
    row = cp2h.RegisterRow(
        "Alder Ratings", "Senior notes", "BB", "Stable", "Not stated", 12, "l", "s"
    )
    book = cp2h._Book("0" * 64)
    cp2h._position(book, row, "r01", ())
    assert book.by_id["T2R.2.r01.position"].fact.period == "Rating dated Not stated"


# --- the page register is untouched (guards) -------------------------------------------------------


def test_pack_without_context_unchanged() -> None:
    """A PackScope built as before: the page register, no citations, the frozen cp2h-owner cells
    and limitations."""
    for case in stage1.COMPOSED:
        case_inputs = stage1.inputs(case)
        assert case_inputs.pack.context is None and case_inputs.pack.context_refusal is None
        _, source, citations = cp2h.register_source(case_inputs.pack)
        assert citations == () and source.register[0].source == "ratings"
        got = cp2h.compute(case_inputs)
        want = stage1.EXPECTED["cases"][case]
        assert list(got.own_limitations) == want["own_limitations"]
        for cell, record in zip(got.cells, want["facts"], strict=True):
            stage1._assert_cell(cell, record)


def test_empty_context_ratings_reads_the_ratings_source() -> None:
    """A context file with no ratings rows leaves the register to the agency source's page:1,
    whose cells are the frozen cp2h-owner positive cells."""
    run = Run.model_validate_json(json.dumps(stage1.MANIFEST["cases"]["positive"]["run"]))
    ratings = cp2h.ratings_source(stage1.pack("positive"))
    pack = PreparedPack(
        run=run,
        sources=(*frozen_sources(), ratings, context_source("context-no-ratings.json")),
    )
    held = scope_of(pack)
    assert held.context is not None and held.context.ratings == ()
    case_inputs = replace(stage1.inputs("positive"), pack=held)
    got = cp2h.compute(case_inputs)
    for cell, record in zip(got.cells, stage1.EXPECTED["cases"]["positive"]["facts"], strict=True):
        stage1._assert_cell(cell, record)
    assert list(got.own_limitations) == stage1.EXPECTED["cases"]["positive"]["own_limitations"]


# --- the read scope --------------------------------------------------------------------------------


def test_host_scope_holds_context() -> None:
    row = host._OWNER_SCOPES[("CP-2H", "rating_triggers")]
    with_context = prepared("positive")
    assert row(with_context) == ("identity", "financial", "ratings", "context")
    without = PreparedPack(run=with_context.run, sources=with_context.sources[:-1])
    assert row(without) == ("identity", "financial", "ratings")
    assert cp2h.SCOPE == frozenset({"identity", "financial", "ratings", "context"})


# --- the view --------------------------------------------------------------------------------------


def upstream_of(case: str) -> cp2h.Upstream:
    cp2g_case = expected(case)["cp2g_head"]["case"]
    return cp2h.Upstream(
        bound=stage1.BOUND,
        current=stage1.BOUND,
        cp1=stage1.cp1_facts(cp2g_case),
        cp2g=stage1.cp2g_metrics(cp2g_case),
    )


def block_of(pack: PreparedPack, case: str = "positive") -> dict[str, Any]:
    return cp2h.context_block(pack=pack, upstream=upstream_of(case))


def test_view_register_block() -> None:
    view = EXP["view"]
    block = block_of(prepared("positive"))
    assert block["register"] == view["register"]
    assert block["triggers"] == view["triggers"]
    tree = json.loads((CASE / view["tree_file"]).read_text())["positive"]
    assert list(block) == tree["top_level_keys"]
    plain = block_of(
        PreparedPack(
            run=run_of("positive"), sources=(*frozen_sources(), ratings_source("positive"))
        )
    )
    for key in ("upstream", "cp2g", "cp1_facts", "inherited_limitations"):
        assert block[key] == plain[key]


def test_view_of_a_refused_context_shows_no_register_not_the_page_one() -> None:
    mismatch = REFUSALS["context_mismatch"]
    pack = prepared("positive", context=context_source(mismatch["context"]))
    block = block_of(pack)
    assert block["register"] == {
        "state": "absent",
        "source_id": None,
        "pages": [],
        "agencies": [],
    }
    assert block["triggers"] == []


def test_view_with_rows_and_no_terms_is_present_with_no_agencies() -> None:
    block = block_of(prepared("positive", variant=None))
    assert block["register"] == {
        "state": "present",
        "source_id": "context",
        "pages": [],
        "agencies": [],
    }
    assert block["triggers"] == []


def test_view_of_a_page_register_is_unchanged() -> None:
    plain = PreparedPack(
        run=run_of("positive"), sources=(*frozen_sources(), ratings_source("positive"))
    )
    empty = prepared("positive", context=context_source("context-no-ratings.json"))
    for pack in (plain, empty):
        register = block_of(pack)["register"]
        assert (register["state"], register["source_id"]) == ("present", "ratings")
        assert register["pages"] == ["page:1", "page:2", "page:3"]


def test_the_context_register_is_the_unstated_outlook_in_the_view() -> None:
    pack = prepared("outlook_unstated")
    agencies: Sequence[dict[str, Any]] = block_of(pack)["register"]["agencies"]
    assert agencies[0]["outlook"] == "Not stated" and agencies[1]["outlook"] == "Stable"


def test_the_loaded_context_is_the_files_own() -> None:
    held = scope("positive")
    assert held.context == load_context(context_bytes("context-positive.json"))
