"""Phase 3 Task 1 (B6, B6a): CP-3 builds market evidence from the context file's quotes and deal
talk. Every expected string and cell is read from the frozen oracle
`cases/cp3-context-owner/expected.json`; the engine (`deploy_vii.cp3_relative_value`) is called
through `deploy_workflow.owners.cp3`, as `tests/test_method_cp3.py` does.

Packs are the R3 pack (or the S1 pack for `context-only`) plus a `context` source built by
`preparation.prepare_source` from the context file's bytes.
"""

import copy
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import test_method_cp3 as m3
from hypothesis import given, settings
from hypothesis import strategies as st

from deploy_vii import cp3_relative_value as engine
from deploy_vii.contracts import Fact, Input, Run, Source
from deploy_vii.cp3_relative_value import RelativeValueSubmission
from deploy_vii.cp6_committee import cp3_catalogue
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow.context import NUM, load_context
from deploy_workflow.owners.cp3 import CP3Inputs, CP3Result, candidate, compute, context

ROOT = Path(__file__).parents[1]
CASE = ROOT / "cases/cp3-context-owner"
EXP: dict[str, Any] = json.loads((CASE / "expected.json").read_text())
SUBS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text())
MAN: dict[str, Any] = json.loads((CASE / "manifest.json").read_text())
CP3: dict[str, Any] = EXP["cp3"]
CASES = [c["case_id"] for c in MAN["cases"] if c["case_id"] != "bad-bytes"]
CONTEXT_OF = {c["case_id"]: c["context"] for c in MAN["cases"]}
PACK_OF = {c["case_id"]: c["pack"] for c in MAN["cases"]}
RUN_OF = {c["case_id"]: c["run_id"] for c in MAN["cases"]}

# The R3 positive CP-3 values at HEAD (the commit before this change): the guard for packs
# without a context source (N1: the empty `context_rows` is omitted from the dump).
R3_SUBMISSION_HASH = "957823e77dd2dbf2513b97ce762eebc6ab72017562e53511adb0620f839cfc4c"
R3_REPORT_SHA256 = "94bd529ce7fba48fdfd197232014e33dda4affed153dc04dbeb3587a2a9331fc"
R3_HEAD_HASH = "814def80dce87dc9e3678c35859c7fcc31359c3c9629015d9f8f0488b8e9afbd"


# --- packs and inputs ----------------------------------------------------------------------------


def context_bytes(name: str) -> bytes:
    return (CASE / "contexts" / f"{name}.json").read_bytes()


def context_source(name: str, raw: bytes | None = None) -> Source:
    path = f"cases/cp3-context-owner/contexts/{name}.json"
    request = SourceRequest(source_id="context", path=path, media_type="text/plain")
    return prepare_source(request, context_bytes(name) if raw is None else raw)


def pack_for(case: str, source: Source | None = None, *, keep_market: bool = True) -> PreparedPack:
    base = m3.make_pack("positive")
    run = base.run.model_copy(update={"run_id": RUN_OF.get(case, f"ctx3-{case}-v1")})
    sources = tuple(s for s in base.sources if keep_market or s.source_id != "market")
    if source is not None:
        sources = (*sources, source)
    return PreparedPack(run=run, sources=sources)


def inputs_for(
    case: str, pack: PreparedPack, literal: Any = None, *, keep_market: bool = True
) -> CP3Inputs:
    cp0 = m3.make_cp0(pack, "positive")
    facts = tuple(f for f in cp0.facts if keep_market or f.row_id != "market")
    if any(s.source_id == "context" for s in pack.sources):
        facts += (
            Fact(
                fact_id="T3.context.authority",
                label="Authority",
                table_id="T3",
                row_id="context",
                field="authority",
                text="unknown",
            ),
        )
    heads = {
        "CP-0": cp0.model_copy(update={"facts": facts}),
        "CP-1": m3.make_cp1(pack),
        "CP-1A": m3.make_cp1a(pack, "positive", blocked=False),
        "CP-2": m3.make_cp2(pack),
    }
    bound = (
        Input(input_id="prepared-pack", sha256=pack.content_hash(), status="accepted"),
        *(
            Input(input_id=k, sha256=head.content_hash(), status="restricted")
            for k, head in heads.items()
        ),
    )
    if literal is None:
        literal = SUBS["cases"][case]
    return CP3Inputs(
        pack=pack,
        submission=RelativeValueSubmission.model_validate_json(m3._instantiate(literal)),
        bound=bound,
        current=bound,
        cp0=heads["CP-0"],
        cp1=heads["CP-1"],
        cp2=heads["CP-2"],
        optional={"CP-1A": heads["CP-1A"]},
        inherited=(),
    )


def case_inputs(case: str, literal: Any = None) -> CP3Inputs:
    keep = PACK_OF[case] != "S1+context"
    pack = pack_for(case, context_source(CONTEXT_OF[case]), keep_market=keep)
    return inputs_for(case, pack, literal, keep_market=keep)


def run_case(case: str) -> tuple[CP3Inputs, CP3Result]:
    inputs = case_inputs(case)
    return inputs, compute(inputs)


def facts_of(result: CP3Result) -> dict[str, Fact]:
    assert result.report is not None
    return {f.fact_id: f for f in result.report.facts}


def apply_edits(literal: Any, edits: list[list[Any]]) -> Any:
    out = copy.deepcopy(literal)
    for op, path, value in edits:
        assert op == "set"
        *parents, last = re.findall(r"[^.\[\]]+|\[\d+\]", path)
        node = out
        for part in parents:
            node = node[int(part[1:-1])] if part.startswith("[") else node[part]
        if last.startswith("["):
            node[int(last[1:-1])] = value
        else:
            node[last] = value
    return out


# --- oracle comparison ---------------------------------------------------------------------------


def check_rows(case: str, result: CP3Result) -> None:
    exp = CP3[case]
    facts = facts_of(result)
    assert result.report is not None
    table = next(t for t in result.report.tables if t.table_id == "T3.3")
    order = [r.row_id for r in table.rows]
    assert order == (exp["t33_row_order"] or ["none"])
    for row in exp.get("t33_rows", []):
        for cell in row["facts"]:
            fact = facts[cell["fact_id"]]
            assert fact.text == cell["text"], cell["fact_id"]
            assert fact.status == cell["status"], cell["fact_id"]
            assert fact.value_class == cell["value_class"], cell["fact_id"]
            assert fact.limitation == cell["limitation"], cell["fact_id"]
            assert [[c.source_id, c.locator] for c in fact.citations] == cell["cites"]
            if "cite_quotes" in cell:
                assert [c.quote for c in fact.citations] == cell["cite_quotes"]


def own_members(case: str) -> list[str]:
    exp = CP3[case]
    if "own_limitations" in exp:
        return list(exp["own_limitations"]["members"])
    return list(exp["report_equals_r3_positive"]["own_limitations"])


def check_cells(case: str, result: CP3Result) -> None:
    exp = CP3[case]
    facts = facts_of(result)
    for group in ("t31_i01_changed_cells", "t34_changed_cells"):
        for fact_id, text in exp.get(group, {}).items():
            if fact_id != "other_cells":
                assert facts[fact_id].text == m3._bound_text(text), fact_id
    assert result.report is not None
    claims = {
        c.claim_id: [[x.source_id, x.locator] for x in c.citations] for c in result.report.claims
    }
    for claim in exp.get("claims", []):
        assert claims[claim["claim_id"]] == claim["cites"], claim["claim_id"]


@pytest.mark.parametrize("case", CASES)
def test_case_equals_oracle(case: str) -> None:
    _, result = run_case(case)
    assert result.issues == ()
    assert result.report is not None
    check_rows(case, result)
    check_cells(case, result)
    members = own_members(case)
    assert sorted(result.report.limitations) == sorted(members)
    if "own_limitations_count" in CP3[case]:
        assert len(result.report.limitations) == CP3[case]["own_limitations_count"]
    user_label = "Market evidence rows from the context file are user-supplied figures"
    expected_label = CP3[case].get("user_supplied_limitation_present", False)
    assert (user_label in result.report.limitations) == expected_label


# --- named plan tests ----------------------------------------------------------------------------


def test_observed_and_talk_rows() -> None:
    _, result = run_case("observed-and-talk")
    facts = facts_of(result)
    assert facts["T3.3.c01.kind"].text == "Observed"
    assert facts["T3.3.c02.kind"].text == "Indicative talk"
    assert len(facts["T3.3.c01.quote"].citations) == 5
    assert len(facts["T3.3.c02.quote"].citations) == 2
    assert facts["T3.3.c01.quote"].value_class == "source"
    assert facts["T3.3.c01.source"].value_class is None


def test_talk_only_issue_string() -> None:
    refusal = next(r for r in EXP["model_side_refusals"] if r["id"] == "ctx-talk-only-high")
    literal = apply_edits(SUBS["cases"]["talk-only"], refusal["edits"])
    result = compute(case_inputs("talk-only", literal))
    assert list(result.issues) == refusal["issues"]


def test_stale_31_days_limits_and_30_does_not() -> None:
    _, result = run_case("stale")
    facts = facts_of(result)
    assert "Stale quote" not in (facts["T3.3.c01.limitation"].text or "")
    assert "31 days before the run as-of 2026-01-10 (limit 30)" in (
        facts["T3.3.c02.limitation"].text or ""
    )


def test_unmatched_and_empty_quote_are_named_gaps() -> None:
    _, result = run_case("unmatched")
    assert result.report is not None
    for text in (
        "Gap (Medium): context quote for facility revolver-x matches no CP-1 facility (T4.18); not used",
        "Gap (Medium): context quote for facility term-loan carries no figure; not used",
    ):
        assert text in result.report.limitations


def test_deal_talk_one_range_row_no_midpoint() -> None:
    _, result = run_case("deal-talk")
    facts = facts_of(result)
    assert facts["T3.3.c01.quote"].text == "term-loan: spread talk 325-350 bps; OID talk 99.0-99.5"
    assert facts["T3.3.c01.kind"].text == "Indicative talk"
    assert not any(f.fact_id.startswith("T3.3.c02") for f in facts.values())


def test_lone_bound_is_omitted_and_named() -> None:
    _, result = run_case("deal-lone-bound")
    facts = facts_of(result)
    assert facts["T3.3.c01.quote"].text == CP3["deal-lone-bound"]["lone_bound"]["row_quote_cell"]
    assert facts["T3.3.c01.limitation"].text == CP3["deal-lone-bound"]["lone_bound"]["limitation"]
    assert all("325" not in (c.quote or "") for c in facts["T3.3.c01.quote"].citations)


def test_with_market_row_order_m_then_c() -> None:
    _, result = run_case("with-market-row")
    assert result.report is not None
    table = next(t for t in result.report.tables if t.table_id == "T3.3")
    assert [r.row_id for r in table.rows] == ["m01", "m02", "c01", "c02"]


def test_model_context_row_refused() -> None:
    check_refusal("context-row-submitted")


def test_basis_quoting_context_refused() -> None:
    check_refusal("context-quote-cited")


def test_unknown_context_row_refused() -> None:
    check_refusal("unknown-context-row")


def check_refusal(refusal_id: str) -> None:
    refusal = next(r for r in EXP["model_side_refusals"] if r["id"] == refusal_id)
    literal = apply_edits(SUBS["cases"][refusal["case"]], refusal["edits"])
    result = compute(case_inputs(refusal["case"], literal))
    assert result.report is None
    assert sorted(result.issues) == sorted(refusal["issues"])


@pytest.mark.parametrize("refusal_id", [r["id"] for r in EXP["model_side_refusals"]])
def test_model_side_refusals(refusal_id: str) -> None:
    check_refusal(refusal_id)


def test_unreadable_and_bad_bytes_are_issues() -> None:
    expected = CP3["bad-bytes"]["validator_issues"]
    pack = pack_for("bad-bytes", context_source("bad-bytes"))
    inputs = inputs_for("bad-bytes", pack, SUBS["cases"]["bad-bytes"])
    result = compute(inputs)
    assert result.report is None
    wanted = {*expected["exact"], *(f["proposed_exact"] for f in expected["fragments"])}
    assert set(result.issues) == wanted
    assert len(result.issues) == expected["count"]
    for fragment in expected["fragments"]:
        assert any(all(p in issue for p in fragment["must_contain"]) for issue in result.issues)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema": "context/1", "quotes": [',  # not JSON
        b'{"schema": "context/1", "quotes": [], "quotes": []}',  # duplicate key
        b"[1, 2]",  # not an object
        b'{"schema": "context/1", "identity": {}, "quotes": [], "deal_terms": []}',  # bad shape
    ],
)
def test_unreadable_context_text_is_an_issue(raw: bytes) -> None:
    pack = pack_for("x", context_source("observed-and-talk", raw))
    result = compute(inputs_for("x", pack, SUBS["cases"]["no-quotes"]))
    assert result.report is None
    assert result.issues
    assert all(i.startswith("context source unreadable: ") for i in result.issues)


def test_unreadable_source_status_is_an_issue() -> None:
    source = context_source("observed-and-talk", b"\xff\xfe\x00bad")
    assert source.status != "ready"
    result = compute(inputs_for("x", pack_for("x", source), SUBS["cases"]["no-quotes"]))
    assert result.report is None
    assert any(i.startswith("context source unreadable: ") for i in result.issues)


def test_unciteable_quote_is_a_gap() -> None:
    _, result = run_case("unciteable")
    assert result.report is not None
    for text in CP3["unciteable"]["gap_limitations"]:
        assert text in result.report.limitations
    assert not any(f.fact_id.startswith("T3.3.c") for f in result.report.facts)


def test_unciteable_deal_terms_is_a_gap() -> None:
    _, result = run_case("unciteable-deal")
    assert result.report is not None
    for text in CP3["unciteable-deal"]["gap_limitations"]:
        assert text in result.report.limitations
    assert not any(f.fact_id.startswith("T3.3.c") for f in result.report.facts)


def test_minified_context_cites_one_line() -> None:
    _, result = run_case("minified")
    facts = facts_of(result)
    cites = [*facts["T3.3.c01.quote"].citations, *facts["T3.3.c02.quote"].citations]
    assert len(cites) == 7
    assert {c.locator for c in cites} == {"line:1"}
    assert cites[0].quote.startswith('{"facility_id":"term-loan"')


def test_context_only_pack_rows_and_note() -> None:
    inputs, result = run_case("context-only")
    assert result.issues == ()
    block = context(inputs)
    exp = CP3["context-only"]["context_block"]
    assert block["market_evidence_note"] == exp["market_evidence_note"]
    assert block["market_evidence_sources"] == []
    assert block["context_market_evidence"] == exp["context_market_evidence"]


@pytest.mark.parametrize("case", CASES)
def test_context_block_lists_rows_and_caps_and_note(case: str) -> None:
    inputs = case_inputs(case)
    block = context(inputs)
    exp = CP3[case].get("context_block")
    if exp is None:  # no-quotes: no rows, nothing added
        assert block["context_market_evidence"] == []
        return
    assert block["context_market_evidence"] == exp["context_market_evidence"]
    assert block["confidence_caps"] == exp["confidence_caps"]
    if "market_evidence_note" in exp:
        assert block["market_evidence_note"] == exp["market_evidence_note"]
        assert block["market_evidence_sources"] == exp["market_evidence_sources"]
    if "pack_sources_context_entry" in exp:
        sources: Any = block["pack_sources"]
        entries = [s for s in sources if s["source_id"] == "context"]
        assert entries == [exp["pack_sources_context_entry"]]


def test_cp6_catalogue_lists_context_rows() -> None:
    for case in ("observed-and-talk", "with-market-row", "talk-only"):
        inputs, result = run_case(case)
        catalogue = cp3_catalogue(candidate(result, inputs, attempt=0))
        got = {ref: row.label for ref, row in catalogue.items() if ref.startswith("T3.3.")}
        assert got == CP3[case]["cp6_catalogue_t33"]


# --- offsets and the reader -----------------------------------------------------------------------

_text = st.text(
    alphabet=st.characters(exclude_categories=["Cs"], exclude_characters="\x00"), max_size=12
)
_scalar = st.one_of(_text, st.integers(), st.booleans(), st.none())
_row = st.dictionaries(st.text(alphabet="abcdef_", min_size=1, max_size=5), _scalar, max_size=5)
_doc = st.fixed_dictionaries(
    {"quotes": st.lists(_row, max_size=4), "deal_terms": st.lists(_row, max_size=4)},
    optional={"other": st.lists(_row, max_size=3), "n": st.integers()},
)


@settings(max_examples=150, deadline=None)
@given(
    doc=_doc,
    indent=st.sampled_from([None, 1, 2, 4]),
    compact=st.booleans(),
    ascii_only=st.booleans(),
)
def test_offsets_agree_with_json_loads(
    doc: dict[str, Any], indent: int | None, compact: bool, ascii_only: bool
) -> None:
    separators = (",", ":") if compact else None
    text = json.dumps(doc, indent=indent, separators=separators, ensure_ascii=ascii_only)
    offsets = engine._value_offsets(text)
    expected = {
        f"{array}[{i}].{key}": value
        for array in ("quotes", "deal_terms")
        for i, row in enumerate(doc[array])
        for key, value in row.items()
        if isinstance(value, str)
    }
    assert set(offsets) == set(expected)
    decoder = json.JSONDecoder()
    for path, offset in offsets.items():
        assert text[offset] == '"'
        value, _ = decoder.raw_decode(text, offset)
        assert value == expected[path]


def test_offset_of_a_known_value() -> None:
    raw = context_bytes("observed-and-talk").decode()
    offsets = engine._value_offsets(raw)
    offset = offsets["quotes[0].price"]
    assert raw.count("\n", 0, offset) + 1 == 32
    assert raw[offset : offset + 7] == '"98.75"'


def test_reader_parity_with_context_module() -> None:
    assert engine.STALE_DAYS == 30
    files = [ROOT / "cases/context" / n for n in ("primary-full.json", "research-minimal.json")]
    files += [ROOT / p for p in EXP["reader_parity"]["files"].values()]
    seen = 0
    for path in files:
        raw = path.read_bytes()
        try:
            loaded = load_context(raw)
        except ValueError:
            assert path.stem == "bad-bytes"
            continue
        run = Run(
            run_id="parity",
            issuer_id=loaded.identity.issuer_id,
            issuer_name=loaded.identity.issuer_name,
            as_of=date.fromisoformat(loaded.run.as_of),
            case_kind=loaded.run.case_kind,
            pathway=loaded.run.pathway,
        )
        source = prepare_source(
            SourceRequest(source_id="context", path=str(path), media_type="text/plain"), raw
        )
        parsed = engine._read_context(source, run)
        assert parsed.issues == (), path
        assert [dict(q) for q in parsed.quotes] == [q.model_dump() for q in loaded.quotes]
        wanted = (
            "facility_id",
            "talk_spread_bps_low",
            "talk_spread_bps_high",
            "talk_oid_low",
            "talk_oid_high",
            "as_of",
            "provider",
        )
        assert [dict(d) for d in parsed.deals] == [
            {k: v for k, v in d.model_dump().items() if k in wanted} for d in loaded.deal_terms
        ]
        seen += 1
    assert seen >= 10
    assert engine.CONTEXT_NUM == NUM


# --- guards (green before and after) --------------------------------------------------------------


def test_no_context_source_is_unchanged() -> None:
    inputs = m3.make_inputs("positive")
    result = compute(inputs)
    assert result.report is not None
    assert inputs.submission.content_hash() == R3_SUBMISSION_HASH
    import hashlib

    assert hashlib.sha256(result.report.model_dump_json().encode()).hexdigest() == R3_REPORT_SHA256
    assert candidate(result, inputs, 1).content_hash() == R3_HEAD_HASH
    assert "context_rows" not in inputs.submission.model_dump_json()
    assert "context_market_evidence" not in context(inputs)


def test_context_source_with_no_rows_changes_only_the_pack_hash() -> None:
    base = m3.make_inputs("positive")
    plain = compute(base)
    _, result = run_case("no-quotes")
    assert plain.report is not None and result.report is not None
    assert result.report.pack_sha256 != plain.report.pack_sha256
    for field in ("tables", "facts", "claims", "limitations", "submission_sha256"):
        assert getattr(result.report, field) == getattr(plain.report, field), field


def test_third_party_basis_quotes_unchanged() -> None:
    base = m3.make_inputs("positive")
    pack = pack_for("x", context_source("observed-and-talk"))
    inputs = inputs_for("x", pack, SUBS["cases"]["no-quotes"])
    result = compute(inputs)
    assert result.issues == ()
    assert result.report is not None
    plain = compute(base)
    assert plain.report is not None
    facts = facts_of(result)
    for cell in ("source", "kind", "quote", "as_of", "limitation"):
        assert facts[f"T3.3.m01.{cell}"] == next(
            f for f in plain.report.facts if f.fact_id == f"T3.3.m01.{cell}"
        )


# --- edge cases beyond the oracle (no frozen value; the expected text is stated here) -------------


def edited_case(base: str, edit: Any, literal: str = "no-quotes") -> CP3Result:
    """Run the R3 positive submission over `base` context with `edit(dict)` applied first."""
    doc = json.loads(context_bytes(base))
    edit(doc)
    raw = json.dumps(doc, indent=2).encode()
    pack = pack_for("edge", context_source(base, raw))
    return compute(inputs_for("edge", pack, SUBS["cases"][literal]))


def rows_of(result: CP3Result) -> dict[str, str | None]:
    return {f.fact_id: f.text for f in facts_of(result).values() if f.fact_id.startswith("T3.3.c")}


def test_deal_row_without_a_date_is_not_stated_and_never_stale() -> None:
    result = edited_case("deal-talk", lambda d: d["deal_terms"][0].update(as_of=""))
    cells = rows_of(result)
    assert cells["T3.3.c01.as_of"] == "Not stated"
    assert cells["T3.3.c01.limitation"] == (
        "Provider: Lead arranger; user-supplied figure; date not stated"
    )
    assert not any("Stale" in text for text in result.report.limitations)  # type: ignore[union-attr]


def test_deal_row_for_an_unknown_facility_and_lone_bounds_are_named_gaps() -> None:
    def unknown(doc: dict[str, Any]) -> None:
        doc["deal_terms"][0]["facility_id"] = "revolver-x"

    def lone(doc: dict[str, Any]) -> None:
        deal = doc["deal_terms"][0]
        deal.update(
            talk_spread_bps_high="350",
            talk_spread_bps_low="",
            talk_oid_high="",
            talk_oid_low="99.0",
        )

    gap = edited_case("deal-talk", unknown).report
    assert gap is not None
    assert (
        "Gap (Medium): context deal term for facility revolver-x matches no CP-1 facility "
        "(T4.18); not used"
    ) in gap.limitations
    none = edited_case("deal-talk", lone).report
    assert none is not None
    assert (
        "Gap (Medium): context deal terms row 1 for facility term-loan carries no complete talk "
        "range; not used"
    ) in none.limitations
    assert USER_LABEL not in none.limitations


USER_LABEL = "Market evidence rows from the context file are user-supplied figures"


def test_equal_figures_in_two_indented_rows_cite_their_own_lines() -> None:
    def same(doc: dict[str, Any]) -> None:
        doc["quotes"][1].update(bid="98.50", ask="99.00", price="", spread_bps="")

    cells = {
        f.fact_id: [c.locator for c in f.citations]
        for f in facts_of(edited_case("observed-and-talk", same)).values()
        if f.fact_id.endswith(".quote") and f.fact_id.startswith("T3.3.c")
    }
    assert cells["T3.3.c01.quote"][:2] == ["line:30", "line:31"]
    assert cells["T3.3.c02.quote"] == ["line:41", "line:42"]


def test_a_stale_quote_that_is_not_cited_still_caps_confidence() -> None:
    literal = apply_edits(SUBS["cases"]["stale"], [["set", "preference.confidence", "High"]])
    result = compute(case_inputs("stale", literal))
    assert result.issues[0].endswith("a context quote is more than 30 days old")


def test_no_context_source_adds_nothing_to_the_context_block() -> None:
    block = context(m3.make_inputs("positive"))
    assert "context_market_evidence" not in block
    assert block["confidence_caps"] == ["CP-2 is restricted"]


def test_level_wording_is_refused_for_talk_only_context_rows_but_not_observed_ones() -> None:
    words = [["set", "preference.rationale", "The loan trades at par on the quotation."]]
    mixed = compute(
        case_inputs("observed-and-talk", apply_edits(SUBS["cases"]["observed-and-talk"], words))
    )
    assert mixed.issues == ()
    talk = compute(case_inputs("talk-only", apply_edits(SUBS["cases"]["talk-only"], words)))
    assert talk.issues == (
        'preference.rationale: indicative talk worded as a market level: "trades at"',
    )
