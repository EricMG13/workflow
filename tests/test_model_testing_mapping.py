from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from deploy_workflow.model_testing.cases import GoldenCase, load_case
from deploy_workflow.model_testing.mapping import MappingError, load_mapping

ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path("/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1")
SHA = "a" * 40


def _fact(fid: str, module: str) -> dict[str, Any]:
    return {"fact_id": fid, "module": module, "field": "f", "period_end": None, "value": "1"}


def _case() -> GoldenCase:
    facts = {
        "a0": _fact("a0", "CP-0"),
        "a1": _fact("a1", "CP-0"),
        "b1": _fact("b1", "CP-1"),
        "b2": _fact("b2", "CP-1"),
        "c1": _fact("c1", "CP-2"),
    }
    return GoldenCase(
        case_id="case-x",
        pathway="earnings_update",
        case_dir=Path("."),
        context_path=Path("context.json"),
        facts=MappingProxyType(facts),
        out_of_plan=MappingProxyType({}),
        financial_gold_path=Path("g.json"),
        financial_gold_sha256="0" * 64,
    )


def _entry(fid: str, module: str, row: str | None = None, **kw: Any) -> dict[str, Any]:
    return {
        "fact_id": fid,
        "module": module,
        "locator": {"table_id": "t", "row_id": row or fid, "field": "f", "period": None},
        **kw,
    }


def _doc(**over: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema_version": "golden-mapping/1",
        "case_id": "case-x",
        "preparer": "alice",
        "reviewer": "bob",
        "module_commits": {"CP-0": SHA},
        "entries": [_entry("a0", "CP-0")],
        "unmapped": [{"fact_id": "a1", "reason": "not produced"}],
    }
    doc.update(over)
    return doc


def _write(tmp_path: Path, doc: Any) -> Path:
    p = tmp_path / "mapping.json"
    p.write_text(doc if isinstance(doc, str) else json.dumps(doc))
    return p


def test_valid_mapping_loads(tmp_path: Path) -> None:
    m = load_mapping(_write(tmp_path, _doc()), _case())
    assert [e.fact_id for e in m.entries] == ["a0"]
    assert m.entries[0].locator.period is None


def test_every_fact_accounted_once(tmp_path: Path) -> None:
    doc = _doc(unmapped=[{"fact_id": "a0", "reason": "x"}, {"fact_id": "a1", "reason": "y"}])
    with pytest.raises(MappingError, match="once"):
        load_mapping(_write(tmp_path, doc), _case())


def test_mapped_module_fully_accounted(tmp_path: Path) -> None:
    doc = _doc(
        module_commits={"CP-0": SHA, "CP-1": SHA},
        entries=[_entry("a0", "CP-0"), _entry("b1", "CP-1")],
    )
    with pytest.raises(MappingError, match="b2"):
        load_mapping(_write(tmp_path, doc), _case())


def test_entry_module_needs_commit(tmp_path: Path) -> None:
    doc = _doc(entries=[_entry("a0", "CP-0"), _entry("c1", "CP-2")])
    with pytest.raises(MappingError, match="module_commits"):
        load_mapping(_write(tmp_path, doc), _case())


def test_unmapped_module_needs_commit(tmp_path: Path) -> None:
    doc = _doc(unmapped=[{"fact_id": "a1", "reason": "x"}, {"fact_id": "c1", "reason": "x"}])
    with pytest.raises(MappingError, match="module_commits"):
        load_mapping(_write(tmp_path, doc), _case())


@pytest.mark.parametrize("bad", ["abc123", "A" * 40, "g" * 40, SHA + "0"])
def test_commit_is_full_sha(tmp_path: Path, bad: str) -> None:
    with pytest.raises(MappingError, match="40-hex"):
        load_mapping(_write(tmp_path, _doc(module_commits={"CP-0": bad})), _case())


def test_pending_lists_unmapped_modules(tmp_path: Path) -> None:
    case = _case()
    m = load_mapping(_write(tmp_path, _doc()), case)
    assert m.pending(case) == {"b1", "b2", "c1"}


def test_unknown_fact_refused(tmp_path: Path) -> None:
    doc = _doc(entries=[_entry("a0", "CP-0"), _entry("zz", "CP-0")])
    with pytest.raises(MappingError, match="zz"):
        load_mapping(_write(tmp_path, doc), _case())


def test_module_must_match_golden(tmp_path: Path) -> None:
    doc = _doc(module_commits={"CP-0": SHA, "CP-4": SHA}, entries=[_entry("a0", "CP-4")])
    with pytest.raises(MappingError, match="CP-4"):
        load_mapping(_write(tmp_path, doc), _case())


def test_locator_unique(tmp_path: Path) -> None:
    doc = _doc(entries=[_entry("a0", "CP-0", row="r"), _entry("a1", "CP-0", row="r")], unmapped=[])
    with pytest.raises(MappingError, match="locator"):
        load_mapping(_write(tmp_path, doc), _case())


def test_same_locator_in_other_module_allowed(tmp_path: Path) -> None:
    doc = _doc(
        module_commits={"CP-0": SHA, "CP-1": SHA},
        entries=[
            _entry("a0", "CP-0", row="r"),
            _entry("b1", "CP-1", row="r"),
        ],
        unmapped=[
            {"fact_id": "a1", "reason": "x"},
            {"fact_id": "b2", "reason": "x"},
        ],
    )
    assert len(load_mapping(_write(tmp_path, doc), _case()).entries) == 2


def test_depends_on_known(tmp_path: Path) -> None:
    doc = _doc(entries=[_entry("a0", "CP-0", depends_on=["nope"])])
    with pytest.raises(MappingError, match="nope"):
        load_mapping(_write(tmp_path, doc), _case())


def test_depends_on_known_fact_accepted(tmp_path: Path) -> None:
    doc = _doc(entries=[_entry("a0", "CP-0", depends_on=["b1"])])
    assert load_mapping(_write(tmp_path, doc), _case()).entries[0].depends_on == ("b1",)


def test_preparer_differs_from_reviewer(tmp_path: Path) -> None:
    with pytest.raises(MappingError, match="reviewer"):
        load_mapping(_write(tmp_path, _doc(reviewer="alice")), _case())


def test_empty_reason_refused(tmp_path: Path) -> None:
    doc = _doc(unmapped=[{"fact_id": "a1", "reason": ""}])
    with pytest.raises(MappingError, match="reason"):
        load_mapping(_write(tmp_path, doc), _case())


def test_case_id_must_match(tmp_path: Path) -> None:
    with pytest.raises(MappingError, match="case_id"):
        load_mapping(_write(tmp_path, _doc(case_id="other")), _case())


def test_duplicate_json_key_refused(tmp_path: Path) -> None:
    text = json.dumps(_doc())[:-1] + ', "preparer": "carol"}'
    with pytest.raises(MappingError, match=r"not valid JSON \(duplicate or malformed key\)") as ei:
        load_mapping(_write(tmp_path, text), _case())
    assert "preparer" not in str(ei.value)  # no key name echoed


def test_unknown_key_and_bad_json_refused(tmp_path: Path) -> None:
    with pytest.raises(MappingError, match="surprise"):
        load_mapping(_write(tmp_path, _doc(surprise=1)), _case())
    with pytest.raises(MappingError, match="JSON"):
        load_mapping(_write(tmp_path, "{not json"), _case())


def test_missing_file_refused(tmp_path: Path) -> None:
    with pytest.raises(MappingError, match="cannot read"):
        load_mapping(tmp_path / "absent.json", _case())


def test_error_does_not_echo_document(tmp_path: Path) -> None:
    doc = _doc(preparer="SECRET-NAME-123", reviewer=5)
    with pytest.raises(MappingError) as ei:
        load_mapping(_write(tmp_path, doc), _case())
    assert "SECRET-NAME-123" not in str(ei.value)


@pytest.mark.skipif(not CORPUS.is_dir(), reason="public corpus v1 is not on this machine")
def test_real_case_two_modules(tmp_path: Path) -> None:
    case = load_case(ROOT / "cases" / "goldens" / "shc-earnings-update", CORPUS)
    mods = ["CP-0", "CP-1D"]
    entries = []
    unmapped = []
    for i, (fid, f) in enumerate(case.facts.items()):
        if f["module"] not in mods:
            continue
        if i % 2:
            entries.append(_entry(fid, f["module"], row=f"row{i}"))
        else:
            unmapped.append({"fact_id": fid, "reason": "no matching module fact"})
    doc = _doc(
        case_id=case.case_id,
        module_commits={m: SHA for m in mods},
        entries=entries,
        unmapped=unmapped,
    )
    m = load_mapping(_write(tmp_path, doc), case)
    pending = m.pending(case)
    assert pending and all(case.facts[f]["module"] in {"CP-1", "CP-1B"} for f in pending)
    assert any(case.facts[f]["module"] == "CP-1" for f in pending)  # financial_gold facts
    assert len(m.entries) + len(m.unmapped) + len(pending) == len(case.facts)


def _rk_entry(fid: str, module: str = "CP-0", **rk: Any) -> dict[str, Any]:
    return {
        "fact_id": fid,
        "module": module,
        "locator": {
            "table_id": "t",
            "row_key": {"field": "name", **rk},
            "field": "f",
            "period": None,
        },
    }


def _rk_case(subject_a: str, subject_b: str) -> GoldenCase:
    case = _case()
    facts = dict(case.facts)
    facts["a0"] = {**facts["a0"], "subject": subject_a}
    facts["a1"] = {**facts["a1"], "subject": subject_b}
    return GoldenCase(
        case_id=case.case_id,
        pathway=case.pathway,
        case_dir=case.case_dir,
        context_path=case.context_path,
        facts=MappingProxyType(facts),
        out_of_plan=case.out_of_plan,
        financial_gold_path=case.financial_gold_path,
        financial_gold_sha256=case.financial_gold_sha256,
    )


def test_locator_needs_row_id_or_row_key(tmp_path: Path) -> None:
    neither = _entry("a0", "CP-0")
    del neither["locator"]["row_id"]
    with pytest.raises(MappingError, match="row_id or row_key"):
        load_mapping(_write(tmp_path, _doc(entries=[neither])), _case())
    both = _rk_entry("a0")
    both["locator"]["row_id"] = "r01"
    with pytest.raises(MappingError, match="row_id or row_key"):
        load_mapping(_write(tmp_path, _doc(entries=[both])), _case())


def test_row_key_entries_collide_on_shared_key_text(tmp_path: Path) -> None:
    case = _rk_case("Term Loan B", "  term LOAN  b ")
    doc = _doc(entries=[_rk_entry("a0"), _rk_entry("a1")], unmapped=[])
    with pytest.raises(MappingError, match="a0.*a1|a1.*a0"):
        load_mapping(_write(tmp_path, doc), case)
    # a shared alias collides too
    case = _rk_case("Term Loan B", "Revolver")
    doc = _doc(entries=[_rk_entry("a0"), _rk_entry("a1", aliases=["TERM loan b"])], unmapped=[])
    with pytest.raises(MappingError, match="collide"):
        load_mapping(_write(tmp_path, doc), case)


def test_row_key_distinct_subjects_ok(tmp_path: Path) -> None:
    case = _rk_case("Term Loan B", "Revolver")
    doc = _doc(entries=[_rk_entry("a0"), _rk_entry("a1")], unmapped=[])
    m = load_mapping(_write(tmp_path, doc), case)
    assert [e.locator.row_key is not None for e in m.entries] == [True, True]
    # a row-id and a row-key entry never collide
    doc = _doc(entries=[_rk_entry("a0"), _entry("a1", "CP-0")], unmapped=[])
    assert len(load_mapping(_write(tmp_path, doc), case).entries) == 2


def test_row_id_mapping_still_loads(tmp_path: Path) -> None:
    m = load_mapping(_write(tmp_path, _doc()), _case())
    loc = m.entries[0].locator
    assert loc.row_id == "a0"
    assert loc.row_key is None


def _ref_entry(
    fid: str, module: str = "CP-0", end: str = "2024-12-28", **ref: Any
) -> dict[str, Any]:
    entry = _rk_entry(fid, module)
    entry["locator"]["period"] = None
    entry["locator"]["period_ref"] = {
        "table_id": "T4.14",
        "id_field": "period_id",
        "match": {"end_date": end, "period_type": "QUARTER"},
        **ref,
    }
    return entry


def test_period_ref_excludes_literal_period(tmp_path: Path) -> None:
    case = _rk_case("Revenue", "Margin")
    entry = _ref_entry("a0")
    entry["locator"]["period"] = "P7"
    with pytest.raises(MappingError, match="period.*period_ref"):
        load_mapping(_write(tmp_path, _doc(entries=[entry], unmapped=[])), case)
    ok = _ref_entry("a0")
    assert (
        load_mapping(_write(tmp_path, _doc(entries=[ok])), case).entries[0].locator.period is None
    )


def test_period_ref_entries_collide_on_same_match(tmp_path: Path) -> None:
    case = _rk_case("Revenue", "Revenue")
    # same row key text, same ref (values normalised): collide
    other = _ref_entry("a1", end="2024-12-28 ")
    doc = _doc(entries=[_ref_entry("a0"), other], unmapped=[])
    with pytest.raises(MappingError, match="collide"):
        load_mapping(_write(tmp_path, doc), case)
    # the same ref on row-id locators collides too
    one, two = _ref_entry("a0"), _ref_entry("a1")
    for e in (one, two):
        del e["locator"]["row_key"]
        e["locator"]["row_id"] = "r01"
    with pytest.raises(MappingError, match="collide"):
        load_mapping(_write(tmp_path, _doc(entries=[one, two], unmapped=[])), case)


def test_period_ref_distinct_match_ok(tmp_path: Path) -> None:
    case = _rk_case("Revenue", "Revenue")
    different = _ref_entry("a1", end="2024-09-28")
    doc = _doc(entries=[_ref_entry("a0"), different], unmapped=[])
    assert len(load_mapping(_write(tmp_path, doc), case).entries) == 2
    # a literal-period entry never collides with a period_ref one
    literal = _rk_entry("a1")
    literal["locator"]["period"] = "P7"
    doc = _doc(entries=[_ref_entry("a0"), literal], unmapped=[])
    assert len(load_mapping(_write(tmp_path, doc), case).entries) == 2


def test_zero_width_alias_and_blank_ref_refused(tmp_path: Path) -> None:
    case = _rk_case("Revenue", "Margin")
    bad_alias = _rk_entry("a0", aliases=["\u200b"])
    with pytest.raises(MappingError, match="non-blank"):
        load_mapping(_write(tmp_path, _doc(entries=[bad_alias], unmapped=[])), case)
    blank_ref = _ref_entry("a0", match={"end_date": "\u200b"})
    with pytest.raises(MappingError, match="non-blank"):
        load_mapping(_write(tmp_path, _doc(entries=[blank_ref], unmapped=[])), case)
