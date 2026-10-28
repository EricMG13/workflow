"""Self-check of the shared defect-class library (`tests/defect_classes.py`); no owner is used.

Each case is well-formed (its quote is on its page under `quotes.quoted`, ids are unique, a refused
case names an accepted twin with the same value), and each refused case really differs from that
twin under `quotes.quoted`: the twin's quote is not on the refused page, or the two values differ
once normalised. A refused case is also a trap: its value is a substring of its normalised quote,
so a plain substring check would accept it. A rule W case (round 12) holds its sign one space from
the figure in the plain reading, so round 10's "directly before" alone does not read it signed,
and every reading of it is signed. A blank value is whitespace or `Cf` only (round 12 B10).
"""

import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any, Literal

import pytest
from defect_classes import (
    BLANK_CASES,
    BLANK_VALUES,
    BOM,
    FIGURE_CASES,
    FIGURES,
    HOSTILE_JSON,
    LABEL_TEMPLATES,
    MINUS,
    MODEL_TEXT_HOSTILE,
    NBSP,
    R12_B10,
    R12_W,
    SOFT_HYPHEN,
    TEXT_CASES,
    ZWSP,
    Adapter,
    BlankCase,
    QuoteCase,
    ReviewRun,
    assert_hostile_refused,
    blank_failure,
    case,
    free_text_paths,
    hostile_inputs,
    label_cases,
    model_text_failures,
    path_matches,
    quote_failure,
    with_text,
)
from pydantic import BaseModel, TypeAdapter, ValidationError

from deploy_vii.contracts import Identifier, RunText, Text
from deploy_vii.quotes import hyphen_wrapped, normalise, quoted, reading

LABELLED = tuple(label_cases("bid", f) for f in FIGURES)
ALL: tuple[QuoteCase, ...] = (*FIGURE_CASES, *TEXT_CASES, *(c for g in LABELLED for c in g))
GROUPS: tuple[tuple[QuoteCase, ...], ...] = (FIGURE_CASES, TEXT_CASES, *LABELLED)
REFUSED = [c for c in ALL if not c.accepted]


def _group(c: QuoteCase) -> tuple[QuoteCase, ...]:
    return next(g for g in GROUPS if c in g)


def test_case_ids_are_unique() -> None:
    for group in GROUPS:
        ids = [c.case_id for c in group]
        assert len(ids) == len(set(ids)), ids


@pytest.mark.parametrize("c", ALL, ids=lambda c: c.case_id)
def test_case_is_well_formed(c: QuoteCase) -> None:
    assert c.page and c.quote and c.value and c.ruling
    assert quoted(c.quote, c.page), "the quote is on its page"
    assert (c.twin is None) == c.accepted, "a refused case, and only one, names a twin"
    assert c.kind == ("figure" if c in FIGURE_CASES else "text" if c in TEXT_CASES else "label")
    if c.kind != "text":
        assert any(ch.isdigit() for ch in c.value) and c.value == c.value.strip()


def _same(a: str, b: str) -> bool:
    """Equal under `quotes.quoted`: each is a contiguous normalised substring of the other."""
    return quoted(a, b) and quoted(b, a)


@pytest.mark.parametrize("c", REFUSED, ids=lambda c: c.case_id)
def test_refused_case_differs_from_its_accepted_twin(c: QuoteCase) -> None:
    """Proves only that the refused case is not a normalisation-equal spelling of an accepted
    case (refusing it does not contradict its twin under `quotes.quoted`). It does not prove the
    expected outcome itself: a case wrongly marked refused can still differ from its twin."""
    assert c.twin is not None
    twin = case(c.twin, _group(c))
    assert twin.accepted and twin.twin is None and twin.kind == c.kind
    assert quoted(twin.quote, twin.page)
    assert not (
        _same(c.page, twin.page) and _same(c.quote, twin.quote) and _same(c.value, twin.value)
    )
    assert (c.value == twin.value) == (c.defect != "wrap"), "a twin keeps the value, except B3's"


def test_edge_cut_twins_are_the_nearest_accepted_edge_case() -> None:
    for c in REFUSED:
        if c.defect != "edge_cut":
            continue
        twin = case(str(c.twin), FIGURE_CASES)
        assert twin.defect == "edge_cut" and twin.case_id.startswith(("edge-start-", "edge-end-"))
        starts = normalise(c.quote).startswith(c.value)
        assert twin.case_id.startswith("edge-start-" if starts else "edge-end-"), c.case_id
    only_page = ("edge-prefix-25", "edge-minus-1.25", "edge-10", "edge-minus-0.25")
    for cid in (*only_page, *(f"w-edge-minus-space-{f}" for f in FIGURES)):
        c = case(cid, FIGURE_CASES)
        twin = case(str(c.twin), FIGURE_CASES)
        assert c.quote == twin.quote and not _same(c.page, twin.page), "only the page differs"


@pytest.mark.parametrize("c", REFUSED, ids=lambda c: c.case_id)
def test_refused_case_is_a_substring_trap(c: QuoteCase) -> None:
    assert quoted(c.value, c.quote)


def test_figure_twins_are_whole_unsigned_figures() -> None:
    for c in REFUSED:
        if c.kind == "figure":
            twin = case(str(c.twin), FIGURE_CASES)
            assert f" {twin.value} " in f" {normalise(twin.page)} "


def test_wrap_cases_follow_b3() -> None:
    split = case("wrap-split", TEXT_CASES)
    joined = case("wrap-joined", TEXT_CASES)
    assert hyphen_wrapped(split.quote) and "- " in normalise(split.value)
    assert not hyphen_wrapped(joined.quote) and "- " not in normalise(joined.value)
    assert split.page == joined.page and hyphen_wrapped(split.page)


def test_round_13_wrap_cases_follow_the_w_exemption() -> None:
    """Round 13 addendum: W's minus before a digit is no B3 wrap split; `A-\\n25` and `a - b` are."""
    signed = case("w-minus-wrap-text", TEXT_CASES)
    assert signed.accepted and "- 1.25" in normalise(signed.value) and hyphen_wrapped(signed.quote)
    for cid, twin in (
        ("b3-letter-wrap-text", "b3-letter-joined-text"),
        ("b3-no-digit-wrap-text", "b3-no-digit-joined-text"),
        ("b3-index-0-letter-wrap-text", "b3-index-0-letter-joined-text"),
        ("b3-index-0-digit-wrap-text", "b3-index-0-digit-joined-text"),
    ):
        c = case(cid, TEXT_CASES)
        assert not c.accepted and c.twin == twin and "- " in normalise(c.value)
        assert hyphen_wrapped(c.quote) and not hyphen_wrapped(case(twin, TEXT_CASES).quote)


def test_class_characters_are_present() -> None:
    by_defect = {d: [c for c in ALL if c.defect == d] for d in {c.defect for c in ALL}}
    assert all(SOFT_HYPHEN in c.page for c in by_defect["soft_hyphen"])
    assert all(NBSP in c.page for c in by_defect["nbsp"])
    assert all(any(ch in c.page for ch in "–—−") for c in by_defect["dashes"])
    assert {c.kind for c in by_defect["soft_hyphen"]} == {"figure", "label", "text"}
    assert {c.kind for c in by_defect["nbsp"]} == {"figure", "label", "text"}
    signs = {c.case_id for c in by_defect["signs"]}
    for f in FIGURES:
        assert {f"sign-{s}-{f}" for s in ("minus", "ascii", "en", "parens")} <= signs
        assert MINUS in case(f"sign-minus-{f}", FIGURE_CASES).page
    assert {"sign-1-december", "sign-2024-2025", "sign-95-96", "sign-s-350"} <= signs
    edges = {c.case_id for c in by_defect["edge_cut"] if not c.accepted}
    assert {"edge-prefix-25", "edge-10", "edge-minus-0.25"} <= edges
    assert {"edge-close-paren-25", "edge-open-paren-25"} <= edges


_W_REFUSED = ("minus-space", "minus-wrap", "minus-nbsp", "parens-wrap", "edge-minus-space")
_W_ACCEPTED = ("break", "letter-wrap")


def test_rule_w_cases_are_present() -> None:
    """Round 12 rule W: a spaced minus, an interior `-\\n`, U+2212 then NBSP, `(\\n` and an
    edge figure after a page `- ` (refused, each figure); the hyphen wraps `A-\\n` and
    `2024-\\n2025`, `95-96` and a line break with no minus (accepted)."""
    w = {c.case_id: c for c in FIGURE_CASES if c.ruling == R12_W}
    for f in FIGURES:
        assert all(not w[f"w-{k}-{f}"].accepted for k in _W_REFUSED)
        assert all(w[f"w-{k}-{f}"].accepted for k in _W_ACCEPTED)
        assert f"-\n{f}" in w[f"w-minus-wrap-{f}"].quote
        assert f"{MINUS}{NBSP}{f}" in w[f"w-minus-nbsp-{f}"].quote
        assert f"(\n{f})" in w[f"w-parens-wrap-{f}"].quote
        assert f"A-\n{f}" in w[f"w-letter-wrap-{f}"].quote
    assert w["w-2024-2025-wrap"].accepted and "2024-\n2025" in w["w-2024-2025-wrap"].quote
    assert case("sign-95-96", FIGURE_CASES).accepted


_DIRECT_MINUS = re.compile(r"(?<![A-Za-z0-9])-\Z")
_SPACED_MINUS = re.compile(r"(?<![A-Za-z0-9])- \Z")


def _signs(text: str, value: str) -> set[str]:
    """How each whole occurrence of `value` in a normalised text is signed: `r10` (a minus or
    accounting parentheses directly at the figure), `w` (only one space away) or `none`."""
    kinds: set[str] = set()
    for m in re.finditer(rf"(?<![0-9.]){re.escape(value)}(?![0-9]|\.[0-9])", text):
        before, after = text[: m.start()], text[m.end() :]
        if _DIRECT_MINUS.search(before) or (before.endswith("(") and after.startswith(")")):
            kinds.add("r10")
        elif _SPACED_MINUS.search(before) or (
            before.endswith(("(", "( ")) and after.startswith((")", " )"))
        ):
            kinds.add("w")
        else:
            kinds.add("none")
    return kinds


def _readings(raw: str) -> tuple[str, ...]:
    joined = reading(raw, join_wraps=True).text
    return (normalise(raw), joined) if hyphen_wrapped(raw) else (normalise(raw),)


@pytest.mark.parametrize(
    "c", [c for c in FIGURE_CASES if c.ruling == R12_W], ids=lambda c: c.case_id
)
def test_rule_w_case_is_signed_only_under_w(c: QuoteCase) -> None:
    """A refused W case is signed one space away in the plain reading (round 10 alone misses it)
    and signed in every reading; an accepted control is unsigned in every reading. An edge case
    carries its sign on the page, outside its quote."""
    signed = c.page if c.defect == "edge_cut" else c.quote
    if c.accepted:
        assert all(_signs(r, c.value) == {"none"} for r in _readings(c.quote))
        assert all(_signs(r, c.value) == {"none"} for r in _readings(c.page))
        return
    assert _signs(normalise(signed), c.value) == {"w"}
    assert all("none" not in _signs(r, c.value) for r in _readings(signed))
    if c.defect == "edge_cut":
        assert normalise(c.quote).startswith(c.value)
        assert _signs(normalise(c.quote), c.value) == {"none"}


@pytest.mark.parametrize("label", ["bid", "offer", "spread", "balance of"])
@pytest.mark.parametrize("figure", FIGURES)
def test_label_cases_bind_the_label(label: str, figure: str) -> None:
    bound = label_cases(label, figure)
    assert len(bound) == len(LABEL_TEMPLATES)
    for c in bound:
        assert "{" not in c.page + c.quote + c.value and quoted(c.quote, c.page)
        assert label in normalise(c.page) and c.value == figure


def test_label_needs_two_letters_and_a_family_figure() -> None:
    with pytest.raises(ValueError):
        label_cases("x")
    with pytest.raises(ValueError):
        label_cases("bid", "0.25")


def _blank(text: str) -> bool:
    """Round 12 B10, written here from the ruling (no owner is imported)."""
    return all(ch.isspace() or unicodedata.category(ch) == "Cf" for ch in text)


def test_blank_cases_split_empty_from_whitespace_only() -> None:
    assert [c.value for c in BLANK_CASES] == list(BLANK_VALUES)
    for c in BLANK_CASES:
        assert _blank(c.value) and quoted(c.quote, c.page)
        assert c.whitespace_only == (c.value != "")
    assert [c.value for c in BLANK_CASES if not c.whitespace_only] == [""]


def test_blank_values_hold_format_characters() -> None:
    """B10: the four `Cf` values, which `str.strip()` keeps, carry the round 12 ruling."""
    kept = [c for c in BLANK_CASES if c.value.strip()]
    assert [c.value for c in kept] == [ZWSP, BOM, SOFT_HYPHEN, f" {ZWSP}\n"]
    assert all(c.ruling == R12_B10 for c in kept)
    assert all(c.ruling != R12_B10 for c in BLANK_CASES if c not in kept)


# --- the assertion helpers, against plain readers written here (no owner) ----------------------


def _naive(page: str, quote: str, value: str) -> Sequence[str]:
    """A raw substring reader: the defect class itself."""
    return () if quoted(quote, page) and value in quote else ("value does not occur in the quote",)


def _empty_frame(page: str, quote: str, value: str) -> Sequence[str]:
    return ("text: empty text",) if _blank(value) else ()


def test_quote_failure_reports_a_wrong_outcome() -> None:
    refusal = "value does not occur in the quote"
    trap = case("sign-ascii-25", FIGURE_CASES)
    message = quote_failure(trap, _naive, refusal)
    assert message is not None and message.startswith("sign-ascii-25: expected")
    assert quote_failure(case("genuine-25", FIGURE_CASES), _naive, refusal) is None
    shy = case("shy-name", TEXT_CASES)
    assert quote_failure(shy, _naive, refusal) == f"shy-name: expected accepted, got {[refusal]}"


def _schema_refuses_empty(page: str, quote: str, value: str) -> Sequence[str]:
    """A `Text` field: pydantic's min_length refusal of "" stands; whitespace gets the frame."""
    if value == "":
        raise ValidationError.from_exception_data(
            "Text",
            [
                {
                    "type": "string_too_short",
                    "loc": ("text",),
                    "input": value,
                    "ctx": {"min_length": 1},
                }
            ],
        )
    return ("text: empty text",) if _blank(value) else ()


def _issue_refuses_empty(page: str, quote: str, value: str) -> Sequence[str]:
    """A validator that reports the schema refusal of "" as an issue (CP-L10's shape step)."""
    if value == "":
        return ("text: String should have at least 1 character",)
    return _empty_frame(page, quote, value)


def test_blank_failure_needs_the_frame() -> None:
    blank: BlankCase = BLANK_CASES[1]
    assert blank_failure(blank, _empty_frame, "text: empty text") is None
    message = blank_failure(blank, _naive, "text: empty text")
    assert message is not None and "expected 'text: empty text'" in message


def test_a_strip_reader_fails_exactly_the_format_cases() -> None:
    """The B10 class: a `not value.strip()` reader passes every case but the `Cf` ones."""

    def strip_frame(page: str, quote: str, value: str) -> Sequence[str]:
        return ("text: empty text",) if not value.strip() else ()

    failed = [c.value for c in BLANK_CASES if blank_failure(c, strip_frame, "text: empty text")]
    assert failed == [c.value for c in BLANK_CASES if c.ruling == R12_B10]


@pytest.mark.parametrize("adapter", [_schema_refuses_empty, _issue_refuses_empty, _empty_frame])
def test_empty_text_may_keep_an_existing_refusal(adapter: Adapter) -> None:
    """Controller decision (library fix 1): "" passes with any refusal; whitespace needs the frame."""
    for c in BLANK_CASES:
        assert blank_failure(c, adapter, "text: empty text") is None, c.case_id


def test_empty_text_still_needs_a_refusal() -> None:
    def accepts_empty(page: str, quote: str, value: str) -> Sequence[str]:
        return () if value == "" else _empty_frame(page, quote, value)

    empty = next(c for c in BLANK_CASES if not c.whitespace_only)
    message = blank_failure(empty, accepts_empty, "text: empty text")
    assert message is not None and "expected a refusal" in message


def test_whitespace_only_text_does_not_accept_a_schema_refusal() -> None:
    def schema_everywhere(page: str, quote: str, value: str) -> Sequence[str]:
        return ("text: String should have at least 1 character",) if _blank(value) else ()

    for c in BLANK_CASES:
        failed = blank_failure(c, schema_everywhere, "text: empty text") is not None
        assert failed == c.whitespace_only, c.case_id


# --- hostile text classes (Stage 2 round 1 Q5, round 3 item 2) -------------------------------


class Part(BaseModel):
    ref: Identifier
    note: Text | None = None


class Doc(BaseModel):
    kind: Literal["a", "b"]
    summary: Text
    parts: list[Part]


POSITIVE = json.dumps(
    {"kind": "a", "summary": "Rates matter.", "parts": [{"ref": "p1", "note": "x"}, {"ref": "p2"}]}
)


def test_hostile_set_is_the_probes() -> None:
    assert HOSTILE_JSON == {
        "deep_array": "[" * 200_000,
        "deep_object": '{"a":' * 50_000 + "1" + "}" * 50_000,
        "huge_int": '{"x":1' + "0" * 200_000 + "}",
        "nan": '{"x":NaN}',
        "lone_surrogate": '{"x":"\\ud800"}',
        "not_object": '"text"',
        "dup_keys": '{"x":1,"x":2}',
        "empty": "",
    }
    assert MODEL_TEXT_HOSTILE == ("Rates matter [a lot", "{low", "{}")


def test_assert_hostile_refused_passes_a_pydantic_schema() -> None:
    assert_hostile_refused(Doc)


def test_assert_hostile_refused_propagates_a_type_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: object, **kwargs: object) -> None:
        raise TypeError("not a ValueError")

    monkeypatch.setattr(Doc, "model_validate_json", broken)
    with pytest.raises(TypeError):
        assert_hostile_refused(Doc)


def test_assert_hostile_refused_propagates_a_recursion_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deep(cls: object, text: str, /, **kwargs: object) -> None:
        if text.startswith("["):
            raise RecursionError("too deep")
        raise ValueError("refused")

    monkeypatch.setattr(Doc, "model_validate_json", classmethod(deep))
    with pytest.raises(RecursionError):
        assert_hostile_refused(Doc)


def test_hostile_inputs_add_the_per_field_floods_of_the_first_string_fields() -> None:
    inputs = [label for label in _labels() if label.startswith("field_summary")]
    assert inputs == ["field_summary_brackets", "field_summary_refs"]


def _labels() -> list[str]:
    return list(hostile_inputs(Doc))


def test_free_text_paths_reads_the_schema() -> None:
    paths = free_text_paths(POSITIVE, Doc)
    assert paths == [("summary",), ("parts", 0, "note")]
    assert ("kind",) not in paths and ("parts", 0, "ref") not in paths


def test_with_text_copies() -> None:
    payload = json.loads(POSITIVE)
    changed = with_text(payload, ("parts", 0, "note"), "{}")
    assert changed["parts"][0]["note"] == "{}" and payload["parts"][0]["note"] == "x"


class _Run:
    """A test-only run: `check` stands for the module's step validator and `build` for the type
    the step builds from the text after the binding write; the binding goes stale when a submit
    raises, so the next submit refuses, like the CP-2E wedge."""

    def __init__(self, check: str, build: bool) -> None:
        self._check = check
        self._build = build
        self._stale = False

    def submit_review(self, payload: str) -> Mapping[str, Any]:
        if self._stale:
            raise RuntimeError("stale_binding")
        self._stale = True  # the binding audit write
        doc = json.loads(payload)
        texts = [doc["summary"], *(p["note"] for p in doc["parts"] if p.get("note"))]
        hostile = [t for t in texts if "[" in t or "{" in t]
        if self._check == "strict_summary":  # a validator that checks only the summary
            hostile = [t for t in hostile if t == doc["summary"]]
        if self._check in {"strict", "strict_summary"} and hostile:
            self._stale = False
            return {"status": "invalid", "issues": [f"summary: bad text {hostile[0]!r}"]}
        if self._check == "silent" and hostile:
            self._stale = False
            return {"status": "invalid", "issues": []}
        if self._build:  # the validator passed it; the build refuses it after the write
            for text in texts:
                TypeAdapter(RunText).validate_python(text)
        self._stale = False
        return {"status": "valid", "issues": []}


def _failures(check: str, build: bool, **options: Any) -> list[str]:
    def fresh() -> ReviewRun:
        return _Run(check, build)

    return model_text_failures(Doc, POSITIVE, fresh, **options)


def test_run_text_refuses_a_bracket() -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(RunText).validate_python("Rates matter [a lot")


def test_model_text_failures_propagates_a_build_that_raises_after_the_write() -> None:
    with pytest.raises(ValidationError):
        _failures("lax", build=True)


def test_model_text_failures_propagates_a_wedge_that_raises() -> None:
    class Once(_Run):
        def submit_review(self, payload: str) -> Mapping[str, Any]:
            try:
                return super().submit_review(payload)
            finally:
                self._stale = True  # the binding stays stale after any submit

    with pytest.raises(RuntimeError, match="stale_binding"):
        model_text_failures(Doc, POSITIVE, lambda: Once("strict", False))


def test_model_text_failures_is_empty_when_the_validator_journals_an_issue() -> None:
    assert _failures("strict", build=True) == []


def test_model_text_failures_catches_an_outcome_with_no_issue() -> None:
    failures = _failures("silent", build=False)
    assert any("summary='{}': invalid with no issue" in f for f in failures)
    assert any("parts.0.note='{}': invalid with no issue" in f for f in failures)


NOTE = ("parts", "*", "note")


def test_a_fully_lax_validator_fails_even_with_a_verbatim_set() -> None:
    failures = _failures("lax", build=False, verbatim=frozenset({NOTE}))
    assert any("summary='{}': accepted" in f for f in failures)
    assert _failures("lax", build=False) != []


def test_a_validator_that_accepts_only_the_verbatim_path_passes() -> None:
    assert _failures("strict_summary", build=False, verbatim=frozenset({NOTE})) == []


def test_a_verbatim_path_is_required_to_be_listed() -> None:
    failures = _failures("strict_summary", build=False)
    assert any("parts.0.note='{}': accepted" in f for f in failures)
    assert not any(f.startswith("summary=") for f in failures)


def test_an_unused_verbatim_pattern_is_a_failure() -> None:
    stale = frozenset({NOTE, ("parts", "*", "gone")})
    failures = _failures("strict_summary", build=False, verbatim=stale)
    assert failures == ["parts.*.gone: verbatim pattern names no path of the payload"]


def test_a_verbatim_path_does_not_excuse_a_build_that_raises() -> None:
    with pytest.raises(ValidationError):
        _failures("strict_summary", build=True, verbatim=frozenset({NOTE}))


def test_path_matches_wildcards_only_list_indices() -> None:
    assert path_matches(("a", "*", "b"), ("a", 3, "b"))
    assert not path_matches(("a", "*"), ("a", "b"))
    assert not path_matches(("a",), ("a", 0))


def test_model_text_failures_reports_a_wedge_that_refuses() -> None:
    class Wedge(_Run):
        def submit_review(self, payload: str) -> Mapping[str, Any]:
            if self._stale:
                return {"status": "refused", "issues": ["stale_binding"]}
            outcome = super().submit_review(payload)
            self._stale = True
            return outcome

    failures = model_text_failures(Doc, POSITIVE, lambda: Wedge("strict", False))
    assert failures and all("wedged, valid payload was refused" in f for f in failures)
