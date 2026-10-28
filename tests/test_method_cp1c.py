"""CP-1C Stage 1: the peer benchmark calculation against the frozen oracle.

Every expectation comes from cases/cp1c-owner/expected.json; every input comes from the oracle's
own manifests and submissions (the frozen financial pack, the synthetic peer source, the CP-1
probe recorded in the manifest and the literal analyst payloads).
"""

import hashlib
import json
import re
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any

import pytest

from deploy_vii import prose
from deploy_vii.contracts import Citation, Fact, Source, Span
from deploy_workflow.owners import cp1c

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp1c-owner"
CASES = ("positive", "gap", "no_peers")
# CP-1's own calculation id is bound at run time; the oracle writes this placeholder for it.
CP1_PLACEHOLDER = "{{CP1_CALCULATION_ID}}"
# Oracle amendment 1 (LEAD 2026-10-28, not yet re-frozen) moves the T1C.1 totals row to a new
# table T1C.8. Until the re-freeze only T1C.2-T1C.7 and refusals r01-r12 are asserted; T1C.1,
# T1C.8 and the universe claim that names the totals are pending amendment 1.
ASSERTED_TABLES = ("T1C.2", "T1C.3", "T1C.4", "T1C.5", "T1C.6", "T1C.7")
PENDING_CLAIMS = ("T1C.1.universe",)
ASSERTED_REFUSALS = tuple(f"r{n:02d}" for n in range(1, 13))


def _asserted(facts: Any) -> list[Any]:
    return [f for f in facts if f["table_id"] in ASSERTED_TABLES]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@cache
def expected() -> Any:
    return _load(CASE / "expected.json")


@cache
def manifest() -> Any:
    return _load(CASE / "manifest.json")


@cache
def submissions() -> Any:
    return _load(CASE / "submissions.json")


@cache
def financial() -> Any:
    return _load(ROOT / "cases" / "financial" / "manifest.json")


def _page_sha(texts: list[str]) -> str:
    return hashlib.sha256("\f".join(texts).encode("utf-8")).hexdigest()


def _source(
    raw: dict[str, Any], *, source_id: str, name: str, limitation: str | None = None
) -> Source:
    texts = [page["text"] for page in raw["pages"]]
    assert _page_sha(texts) == raw["sha256"]  # the pinned pages are the ones read here
    return Source(
        source_id=source_id,
        name=name,
        status="ready",
        sha256=raw["sha256"],
        spans=tuple(Span(locator=page["locator"], text=page["text"]) for page in raw["pages"]),
        limitation=limitation,
        extraction_status="complete",
    )


@cache
def sources(pack: str) -> tuple[Source, ...]:
    """The host-scoped sources of a case: identity, financial and (when present) peers."""
    frozen = tuple(
        _source(raw, source_id=raw["source_id"], name=raw["name"])
        for raw in financial()["sources"]
        if raw["source_id"] in ("identity", "financial")
    )
    if pack == "no_peers":
        return frozen
    synthetic = manifest()["synthetic_source"]
    raw = (
        synthetic["fixtures"]["peer_table_not_found"] if pack == "unparseable" else synthetic[pack]
    )
    peers = _source(
        raw,
        source_id=synthetic["source_id"],
        name=synthetic["name"],
        limitation=synthetic["pack_limitation"],
    )
    return (*frozen, peers)


def cp1_metrics(citations: tuple[Citation, ...] = ()) -> dict[str, Fact]:
    """CP-1's T4.10 LTM facts as the manifest records the probe of the real promoted head."""
    rule = manifest()["cp1_fact_selection_rule"]
    column = re.search(r"with column '([^']+)'", rule["predicate"])
    assert column is not None
    probed = re.findall(r"(\w+) (PERCENT|MULTIPLE) ([0-9.]+) (calculated)", rule["probe"])
    assert {key for key, *_ in probed} == set(rule["metrics"])
    return {
        key: Fact(
            fact_id=f"T4.10.ltm.{key}",
            label=f"{column.group(1)} · {key}",
            table_id="T4.10",
            amount=Decimal(amount),
            unit=unit,
            period=rule["period"],
            value_class="calculated",
            calculation_id=f"cp1-calc-{key}",
            citations=citations,
        )
        for key, unit, amount, _ in probed
    }


def inputs(
    case: str,
    *,
    pack: str | None = None,
    payload: Any = None,
    cp1: dict[str, Fact] | None = None,
) -> cp1c.PeerBenchmarkInputs:
    body = submissions()[case]["peer_benchmark"] if payload is None else payload
    return cp1c.PeerBenchmarkInputs(
        issuer_name=manifest()["cases"][case]["run"]["issuer_name"],
        sources=sources(pack or case),
        cp1_metrics=cp1_metrics() if cp1 is None else cp1,
        submission=cp1c.PeerBenchmarkSubmission.model_validate_json(json.dumps(body)),
    )


@cache
def result(case: str) -> cp1c.PeerBenchmarkResult:
    return cp1c.compute(inputs(case))


def _exact(amount: Decimal | None) -> str | None:
    """The oracle's canonical exact decimal: fixed point, no trailing zeros."""
    if amount is None:
        return None
    text = format(amount, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _cites(items: Any) -> list[tuple[str, str, str]]:
    return [(c["source_id"], c["locator"], c["quote"]) for c in items]


# --- the facts ------------------------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_fact_ids_and_order(case: str) -> None:
    want = [f["fact_id"] for f in _asserted(expected()["cases"][case]["facts"])]
    got = [i.fact.fact_id for i in result(case).facts if i.fact.table_id in ASSERTED_TABLES]
    assert got == want


def _assert_fact(item: cp1c.PeerFact, want: dict[str, Any], peer_sha: str | None) -> None:
    fact, where = item.fact, want["fact_id"]
    assert (fact.table_id, fact.row_id, fact.field) == (
        want["table_id"],
        want["row_id"],
        want["field"],
    ), where
    assert fact.label == want["label"], where
    assert fact.status == want["status"], where
    assert fact.text == want.get("text"), where
    assert fact.unit == want.get("unit"), where
    assert fact.period == want.get("period"), where
    assert _exact(fact.amount) == want.get("amount_exact"), where
    assert fact.currency == want.get("currency"), where
    assert fact.scale == Decimal(want.get("scale", "1")), where
    assert fact.decimals == want.get("decimals"), where
    assert fact.value_class == want.get("value_class"), where
    assert fact.formula == want.get("formula"), where
    assert fact.limitation == want.get("limitation"), where
    assert list(item.derives_from) == want.get("derives_from", []), where
    assert item.copied_from_cp1 == want.get("copied_from_cp1"), where
    if want.get("copied_from_cp1"):
        source = next(f for f in cp1_metrics().values() if f.label == want["copied_from_cp1"])
        assert want["calculation_id"] == CP1_PLACEHOLDER, where
        assert fact.calculation_id == source.calculation_id, where
        assert fact.citations == source.citations, where
    else:
        assert fact.calculation_id == want.get("calculation_id"), where
        got = _cites(c.model_dump() for c in fact.citations)
        assert got == _cites(want.get("citations", [])), where
        assert all(c.source_sha256 == peer_sha for c in fact.citations), where
    assert cp1c.shown(fact) == want["shown"], where


@pytest.mark.parametrize("case", CASES)
def test_every_fact_equals_the_oracle(case: str) -> None:
    got = {item.fact.fact_id: item for item in result(case).facts}
    peer_sha = {s.source_id: s.sha256 for s in sources(case)}.get("peers")
    for want in _asserted(expected()["cases"][case]["facts"]):
        _assert_fact(got[want["fact_id"]], want, peer_sha)


@pytest.mark.parametrize("case", CASES)
def test_operands_summary(case: str) -> None:
    summary = expected()["cases"][case]["operands_summary"]
    facts = {item.fact.fact_id: item.fact for item in result(case).facts}
    for ref, value in summary["peer_metrics"].items():
        row, key = ref.split(".")
        fact = facts[f"T1C.3.{row}.{key}"]
        # the summary writes a missing ratio as null and a not-meaningful one as "na"
        got = {"known": _exact(fact.amount), "missing": None, "not_applicable": "na"}
        assert got[fact.status] == value, ref
    present = summary["peers_in_source"] is not None  # the totals themselves: amendment 1
    for key, stat in summary["stats"].items():
        if stat is None:
            assert not present
            continue
        assert facts[f"T1C.4.{key}.n"].amount == stat["n"], key
        assert _exact(facts[f"T1C.4.{key}.median"].amount) == stat["median"], key
        if stat["median"] is None:
            continue
        assert _exact(facts[f"T1C.4.{key}.difference"].amount) == stat["difference"], key
        assert facts[f"T1C.4.{key}.position"].amount == stat["position"], key
        assert facts[f"T1C.4.{key}.of"].amount == stat["of"], key
        flagged = [
            fact.row_id
            for fact in facts.values()
            if fact.table_id == "T1C.5"
            and fact.field == f"{key}_flag"
            and fact.row_id != "issuer"
            and fact.text == "Outlier"
        ]
        assert flagged == stat["outliers"], key
        assert facts[f"T1C.4.{key}.outlier_count"].amount == len(stat["outliers"]), key


def test_copied_cell_citations_follow_cp1_at_run_time() -> None:
    """Lineage rule: a copied CP-1 cell keeps CP-1's citations; a fact that derives from it
    carries them at that cell's place in derives_from order (the oracle's literal list omits them)."""
    peers = next(s for s in sources("positive") if s.source_id == "peers")
    cp1_cite = Citation(
        source_id="financial",
        source_sha256=next(s.sha256 for s in sources("positive") if s.source_id == "financial")
        or "",
        locator="page:2",
        quote="Adjusted EBITDA  7.5  7.5  7.5  7.5  30.0",
    )
    got = cp1c.compute(inputs("positive", cp1=cp1_metrics((cp1_cite,))))
    facts = {item.fact.fact_id: item.fact for item in got.facts}
    assert facts["T1C.3.issuer.total_leverage_adjusted"].citations == (cp1_cite,)
    difference = facts["T1C.4.total_leverage_adjusted.difference"].citations
    literal = next(
        f
        for f in expected()["cases"]["positive"]["facts"]
        if f["fact_id"] == "T1C.4.total_leverage_adjusted.difference"
    )
    assert difference[0] == cp1_cite
    assert _cites(c.model_dump() for c in difference[1:]) == _cites(literal["citations"])
    assert all(c.source_sha256 == peers.sha256 for c in difference[1:])


# --- tables, claims, limitations --------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_tables(case: str) -> None:
    got = [
        {
            "table_id": t.table_id,
            "title": t.title,
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)} for r in t.rows
            ],
        }
        for t in result(case).tables
        if t.table_id in ASSERTED_TABLES
    ]
    want = [t for t in expected()["cases"][case]["tables"] if t["table_id"] in ASSERTED_TABLES]
    assert got == want


@pytest.mark.parametrize("case", CASES)
def test_fp03_cells_match_the_tables(case: str) -> None:
    """The FP03 tabs' cell states and shown text are what the tables' facts spell."""
    facts = {item.fact.fact_id: item.fact for item in result(case).facts}
    tables = {t.table_id: t for t in result(case).tables}
    state = {"known": "known", "missing": "gap", "not_applicable": "not_meaningful"}
    for tab in expected()["cases"][case]["FP03"]["blocks"]["peer-positioning"]["tabs"]:
        if tab["table_id"] not in ASSERTED_TABLES:
            continue
        got = [
            {
                "row_id": r.row_id,
                "label": r.label,
                "cells": [
                    {
                        "fact_id": f,
                        "field": facts[f].field,
                        "shown": cp1c.shown(facts[f]),
                        "state": state[facts[f].status],
                    }
                    for f in r.fact_ids
                ],
            }
            for r in tables[tab["table_id"]].rows
        ]
        assert got == tab["rows"], tab["table_id"]


@pytest.mark.parametrize("case", CASES)
def test_claims(case: str) -> None:
    got = [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "limitation": c.limitation,
            "evidence": [x.model_dump() for x in c.citations],
        }
        for c in result(case).claims
        if c.claim_id not in PENDING_CLAIMS
    ]
    want = [
        dict(c, evidence=c.get("evidence", []))
        for c in expected()["cases"][case]["claims"]
        if c["claim_id"] not in PENDING_CLAIMS
    ]
    assert got == want


@pytest.mark.parametrize("case", CASES)
def test_claims_resolve_against_the_module_facts(case: str) -> None:
    bound = prose.bind(item.fact for item in result(case).facts)
    issuer = manifest()["cases"][case]["run"]["issuer_name"]
    for claim in result(case).claims:
        if claim.claim_id in PENDING_CLAIMS:
            continue
        assert prose.issues(claim.text, bound, names=(issuer,)) == (), claim.claim_id


@pytest.mark.parametrize("case", CASES)
def test_own_limitations(case: str) -> None:
    assert list(result(case).limitations) == expected()["cases"][case]["own_limitations"]


@pytest.mark.parametrize("case", CASES)
def test_valid_payloads_raise_no_issue(case: str) -> None:
    assert cp1c.calculation_issues(inputs(case)) == ()


def test_policy_constants() -> None:
    policy = expected()["policy_constants"]
    assert cp1c.MIN_INCLUDED_PEERS == policy["minimum_included_peers"]
    assert cp1c.MIXED_PERIOD in policy["period_of_derived_facts"]


# --- refusals (calculation-level content rules) ------------------------------------------------------


def _matches(issue: str, want: str) -> bool:
    return issue.startswith(want) if want.endswith("(") else issue == want


@pytest.mark.parametrize(
    "refusal",
    [r for r in expected()["refusals"] if r["id"] in ASSERTED_REFUSALS],
    ids=lambda r: r["id"],
)
def test_refusal(refusal: Any) -> None:
    payload = next(r for r in submissions()["refusals"] if r["id"] == refusal["id"])["payload"]
    case = inputs(refusal["base_case"], pack=refusal["pack"], payload=payload)
    issues = cp1c.calculation_issues(case)
    wants = refusal["expected_issues"]
    assert len(issues) == len(wants), issues
    for want in wants:
        assert any(_matches(issue, want) for issue in issues), (want, issues)
    with pytest.raises(ValueError):
        cp1c.compute(case)


# --- fixtures: the composer rules at their boundaries --------------------------------------------------


@pytest.mark.parametrize("case", expected()["fixtures"]["median"]["cases"])
def test_fixture_median(case: Any) -> None:
    got = cp1c.median([Decimal(v) for v in case["values"]])
    assert _exact(got) == case["median"]


@pytest.mark.parametrize("case", expected()["fixtures"]["outlier_boundary"]["cases"])
def test_fixture_outlier_boundary(case: Any) -> None:
    got = cp1c.outlier(Decimal(case["value"]), Decimal(case["median"]))
    assert got is not None
    deviation, flag = got
    assert (_exact(deviation), flag) == (case["deviation"], case["flag"])


def test_fixture_outlier_zero_median_is_not_meaningful() -> None:
    rule = expected()["fixtures"]["zero_denominators"]["rule"]
    assert "a median of zero: deviation and flag not_applicable" in rule
    assert cp1c.outlier(Decimal(1), Decimal(0)) is None


@pytest.mark.parametrize("case", expected()["fixtures"]["position"]["cases"])
def test_fixture_position(case: Any) -> None:
    higher = case["direction"] == "Higher is better"
    got = cp1c.position(
        Decimal(case["issuer"]), [Decimal(v) for v in case["peers"]], higher_is_better=higher
    )
    assert got == (case["position"], case["of"])


@pytest.mark.parametrize("case", expected()["fixtures"]["minimum_universe"]["cases"])
def test_fixture_minimum_universe(case: Any) -> None:
    values = [Decimal(n + 1) for n in range(case["included_with_value"])]
    got = cp1c.peer_median(values)
    assert ("known" if got is not None else "missing") == case["median"]


@pytest.mark.parametrize("case", expected()["fixtures"]["zero_denominators"]["cases"])
def test_fixture_zero_denominators(case: Any) -> None:
    operands = {"revenue": "100", "ebitda": "20", "debt": "40", "interest": "4", "ffo": "10"}
    (operand,) = operands.keys() & case.keys()
    (metric,) = case.keys() - operands.keys()
    operands[operand] = case[operand]
    key = {"margin": "adjusted_ebitda_margin"}.get(metric, metric)
    row = cp1c.PeerRow(
        label="Fixture",
        period_end="2025-12-31",
        amounts={k: None if v == cp1c.NOT_STATED else Decimal(v) for k, v in operands.items()},
        line="Fixture",
        basis=None,
    )
    assert cp1c.peer_metrics(row)[key].status == case[metric]
