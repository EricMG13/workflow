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
from typing import Any, Literal

import pytest

from deploy_vii import prose
from deploy_vii.contracts import Citation, Fact, Source, Span
from deploy_workflow.owners import cp1c

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp1c-owner"
CASES = ("positive", "gap", "no_peers")
# CP-1's own calculation id is bound at run time; the oracle writes this placeholder for it.
CP1_PLACEHOLDER = "{{CP1_CALCULATION_ID}}"
# Oracle pins: docs/CP1C-OWNER-LEASE.md:3, the serialised methodology re-pin (LEAD 2026-10-28).
PINS = {
    "cases/cp1c-owner/manifest.json": (
        "0b4d4f046a085fc9be91c6ef051d5db3dd1ea46335bfea71ea851b188cb62db3"
    ),
    "cases/cp1c-owner/submissions.json": (
        "13be79735066cd58bdcc4cfa7eebddc0eedbe0abb784153a2950ee38455a8912"
    ),
    "cases/cp1c-owner/expected.json": (
        "e786acb384007d8a4111a7d572b50744cbcd70ee44954a3730b8703f6752fded"
    ),
    "cases/cp1c-owner/builder/build.py": (
        "6c7018dcb31ca1d8abd6e324e7d9048fcfc20ab27501cfb4b4b239dd65fca8b0"
    ),
}


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
    want = [f["fact_id"] for f in expected()["cases"][case]["facts"]]
    assert [i.fact.fact_id for i in result(case).facts] == want


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
    for want in expected()["cases"][case]["facts"]:
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
    present = summary["peers_in_source"] is not None
    if present:
        assert facts["T1C.8.total.sheet"].amount == summary["peers_in_source"]
        assert facts["T1C.8.total.included"].amount == summary["included"]
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
    ]
    assert got == expected()["cases"][case]["tables"]


@pytest.mark.parametrize("case", CASES)
def test_fp03_cells_match_the_tables(case: str) -> None:
    """The FP03 tabs' cell states and shown text are what the tables' facts spell."""
    facts = {item.fact.fact_id: item.fact for item in result(case).facts}
    tables = {t.table_id: t for t in result(case).tables}
    state = {"known": "known", "missing": "gap", "not_applicable": "not_meaningful"}
    for tab in expected()["cases"][case]["FP03"]["blocks"]["peer-positioning"]["tabs"]:
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
    ]
    want = [dict(c, evidence=c.get("evidence", [])) for c in expected()["cases"][case]["claims"]]
    assert got == want


@pytest.mark.parametrize("case", CASES)
def test_claims_resolve_against_the_module_facts(case: str) -> None:
    bound = prose.bind(item.fact for item in result(case).facts)
    issuer = manifest()["cases"][case]["run"]["issuer_name"]
    for claim in result(case).claims:
        assert prose.issues(claim.text, bound, names=(issuer,)) == (), claim.claim_id


@pytest.mark.parametrize("case", CASES)
def test_own_limitations(case: str) -> None:
    assert list(result(case).limitations) == expected()["cases"][case]["own_limitations"]


@pytest.mark.parametrize("case", CASES)
def test_valid_payloads_raise_no_issue(case: str) -> None:
    assert cp1c.calculation_issues(inputs(case)) == ()


@pytest.mark.parametrize("path", PINS)
def test_oracle_pins(path: str) -> None:
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == PINS[path]


def test_policy_constants() -> None:
    policy = expected()["policy_constants"]
    assert cp1c.MIN_INCLUDED_PEERS == policy["minimum_included_peers"]
    assert cp1c.MIXED_PERIOD in policy["period_of_derived_facts"]


# --- refusals (calculation-level content rules) ------------------------------------------------------


def _matches(issue: str, want: str) -> bool:
    return issue.startswith(want) if want.endswith("(") else issue == want


@pytest.mark.parametrize("refusal", expected()["refusals"], ids=lambda r: r["id"])
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


# --- fix round 1: rulings 1C1-1C5 (docs/rulings/2026-10-28-stage1.md) and review findings --------------
# Inputs below are the oracle's own pages with one line edited; the peers source keeps its pinned
# sha so the payload's citations still bind (only page text the test names changes).


def _edited(case: str, page: int, old: str, new: str) -> tuple[Source, ...]:
    *frozen, peers = sources(case)
    texts = [span.text for span in peers.spans]
    assert old in texts[page - 1], old
    texts[page - 1] = texts[page - 1].replace(old, new, 1)
    spans = tuple(Span(locator=s.locator, text=t) for s, t in zip(peers.spans, texts, strict=True))
    return (*frozen, peers.model_copy(update={"spans": spans}))


def _with_sources(
    case: str, edited: tuple[Source, ...], payload: Any = None, cp1: dict[str, Fact] | None = None
) -> Any:
    base = inputs(case, payload=payload, cp1=cp1)
    return cp1c.PeerBenchmarkInputs(
        issuer_name=base.issuer_name,
        sources=edited,
        cp1_metrics=base.cp1_metrics,
        submission=base.submission,
    )


def _facts(found: cp1c.PeerBenchmarkResult) -> dict[str, Fact]:
    return {item.fact.fact_id: item.fact for item in found.facts}


ALDER = "Alder Ridge Holdings  2025-12-31  200.0  52.0  104.0  8.0  41.6"
ISSUER_LINE = "Northbridge Synthetic Group  2025-12-31  120.0  30.0  50.0  5.0  21.0"
BASIS = "Basis: twelve months to the period end shown; USD; amounts in millions; unaudited desk summaries."


def test_1c1_included_peer_with_a_not_meaningful_ratio_settles_not_applicable() -> None:
    """Probe P1: Alder (Comparable) with adjusted EBITDA -52.0; leverage keeps three peers."""
    edited = _edited("positive", 1, ALDER, ALDER.replace("  52.0  ", "  -52.0  "))
    case = _with_sources("positive", edited)
    assert cp1c.calculation_issues(case) == ()
    facts = _facts(cp1c.compute(case))
    assert facts["T1C.3.p01.total_leverage_adjusted"].status == "not_applicable"
    assert facts["T1C.4.total_leverage_adjusted.median"].status == "known"
    reason = "Not meaningful: the peer's own ratio is not meaningful"
    for name in ("deviation", "flag"):
        fact = facts[f"T1C.5.p01.total_leverage_adjusted_{name}"]
        assert (fact.status, fact.limitation) == ("not_applicable", reason)
    got = next(
        i
        for i in cp1c.compute(case).facts
        if i.fact.fact_id.endswith("leverage_adjusted.outlier_count")
    )
    assert "T1C.5.p01.total_leverage_adjusted_flag" not in got.derives_from
    assert got.derives_from == tuple(
        f"T1C.5.{r}.total_leverage_adjusted_flag" for r in ("p02", "p03", "p04")
    )


@pytest.mark.parametrize(
    ("old", "new", "metric", "status", "reason"),
    [
        (
            "  5.0  21.0",
            "  Not stated  21.0",
            "interest_coverage_adjusted",
            "missing",
            "Not calculable: interest expense is not stated on the issuer line of the peer source",
        ),
        (
            "  120.0  30.0  ",
            "  120.0  0.0  ",
            "total_leverage_adjusted",
            "not_applicable",
            "Not meaningful: adjusted ebitda is not positive",
        ),
    ],
)
def test_1c2_issuer_line_that_cannot_be_recomputed_is_not_compared(
    old: str, new: str, metric: str, status: str, reason: str
) -> None:
    """Probe P2: the issuer line's interest expense Not stated (and a zero EBITDA)."""
    edited = _edited("positive", 1, ISSUER_LINE, ISSUER_LINE.replace(old, new))
    case = _with_sources("positive", edited)
    assert cp1c.calculation_issues(case) == ()
    facts = _facts(cp1c.compute(case))
    # round 4 (d): the ruled cells, field by field
    sheet = facts[f"T1C.6.{metric}.sheet"]
    assert (sheet.status, sheet.limitation, sheet.unit, sheet.period, sheet.value_class) == (
        status,
        reason,
        "MULTIPLE",
        "Twelve months to 2025-12-31",
        None,
    )
    difference = facts[f"T1C.6.{metric}.difference"]
    assert (
        difference.status,
        difference.limitation,
        difference.unit,
        difference.period,
        difference.value_class,
    ) == ("missing", "Not compared: one side is not available", "MULTIPLE", None, None)
    result_fact = facts[f"T1C.6.{metric}.result"]
    assert (
        result_fact.status,
        result_fact.text,
        result_fact.value_class,
        result_fact.calculation_id,
    ) == ("known", "Not compared", None, None)
    assert facts[f"T1C.6.{metric}.cp1"].status == "known"


def test_1c2_percent_metric_difference_is_in_percentage_points() -> None:
    edited = _edited("positive", 1, ISSUER_LINE, ISSUER_LINE.replace("  120.0  ", "  Not stated  "))
    facts = _facts(cp1c.compute(_with_sources("positive", edited)))
    sheet = facts["T1C.6.adjusted_ebitda_margin.sheet"]
    assert (sheet.status, sheet.unit, sheet.limitation) == (
        "missing",
        "PERCENT",
        "Not calculable: revenue is not stated on the issuer line of the peer source",
    )
    difference = facts["T1C.6.adjusted_ebitda_margin.difference"]
    assert (difference.status, difference.unit, difference.period) == ("missing", "pp", None)


def test_tie_out_differs_when_the_issuer_line_disagrees() -> None:
    edited = _edited("positive", 1, ISSUER_LINE, ISSUER_LINE.replace("120.0", "125.0"))
    facts = _facts(cp1c.compute(_with_sources("positive", edited)))
    assert facts["T1C.6.adjusted_ebitda_margin.result"].text == "Differs"
    assert facts["T1C.6.adjusted_ebitda_margin.difference"].amount != 0
    assert facts["T1C.6.total_leverage_adjusted.result"].text == "Reconciled"


def test_negative_denominator_is_not_meaningful_with_its_reason() -> None:
    """An excluded peer (Ellsworth) with negative EBITDA: the T1C.3 cell is not_applicable."""
    line = "Ellsworth Park Limited  2025-12-31  500.0  150.0  75.0  7.5  60.0"
    edited = _edited("positive", 1, line, line.replace("  150.0  ", "  -150.0  "))
    facts = _facts(cp1c.compute(_with_sources("positive", edited)))
    leverage = facts["T1C.3.p05.total_leverage_adjusted"]
    assert (leverage.status, leverage.limitation) == (
        "not_applicable",
        "Not meaningful: adjusted ebitda is not positive",
    )
    assert facts["T1C.3.p05.adjusted_ebitda_margin"].amount == Decimal("-0.3")


@pytest.mark.parametrize(
    ("page", "old", "new"),
    [
        (1, ALDER, ALDER.replace("  8.0", "")),  # a line that is not 7 fields
        (1, ALDER, ALDER.replace("2025-12-31", "2025-13-45")),  # not a real date
        (1, ALDER, ALDER.replace("2025-12-31", "20251231")),  # not the YYYY-MM-DD shape
        (1, ALDER, ALDER.replace("200.0", "٢00.0")),  # a non-ASCII digit
        (1, ALDER, ALDER.replace("200.0", "²00.0")),
        (1, ALDER, ALDER.replace("200.0", "1e3")),  # not a plain decimal
        (1, ALDER, ALDER.replace("200.0", "5.")),
        (1, ALDER, ALDER + "\n" + ALDER),  # a duplicate label
        (1, ISSUER_LINE + "\n", ""),  # no issuer line
        (1, ISSUER_LINE, ISSUER_LINE + "\n" + ISSUER_LINE),  # two issuer lines
        (1, ALDER, ALDER + "\n"),  # a blank line inside the table
        # round 4 (a): a duplicate page:2 label
        (
            2,
            "Alder Ridge Holdings  IFRS  1  December 31",
            "Alder Ridge Holdings  IFRS  1  December 31\nAlder Ridge Holdings  US GAAP  9  June 30",
        ),
    ],
)
def test_1c4_every_table_rule_breach_is_peer_table_not_found_alone(
    page: int, old: str, new: str
) -> None:
    case = _with_sources("positive", _edited("positive", page, old, new))
    assert cp1c.calculation_issues(case) == ("Peer table not found",)
    with pytest.raises(ValueError, match="Peer table not found"):
        cp1c.compute(case)


def _not_ready(status: Literal["missing", "unreadable"]) -> tuple[Source, ...]:
    *frozen, peers = sources("positive")
    stale = Source(source_id=peers.source_id, name=peers.name, status=status, limitation="Not read")
    return (*frozen, stale)


@pytest.mark.parametrize("status", ["missing", "unreadable"])
def test_round4_b_peer_source_not_ready_composes_the_no_peers_design(
    status: Literal["missing", "unreadable"],
) -> None:
    case = _with_sources("no_peers", _not_ready(status))
    assert cp1c.calculation_issues(case) == ()
    found = cp1c.compute(case)
    ready = "No ready peer source is in the pack"
    frozen = {f["fact_id"]: f for f in expected()["cases"]["no_peers"]["facts"]}
    got = {i.fact.fact_id: i.fact for i in found.facts}
    assert list(got) == list(frozen)  # the no-peers design, fact for fact
    for fact_id, want in frozen.items():
        if want.get("limitation") == "No peer source is in the pack":
            assert got[fact_id].limitation == ready, fact_id
        else:
            assert got[fact_id].limitation == want.get("limitation"), fact_id
    universe = next(c for c in found.claims if c.claim_id == "T1C.1.universe")
    assert universe.text == f"{ready}, so no universe is formed [T1C.8.total.sheet]."
    assert all(ready not in c.text for c in found.claims if c.claim_id != "T1C.1.universe")


def test_round4_b_assessment_with_a_peer_source_not_ready_is_the_r10_class() -> None:
    issues = cp1c.calculation_issues(_with_sources("positive", _not_ready("missing")))
    peers = [a["peer"] for a in submissions()["positive"]["peer_benchmark"]["assessments"]]
    for peer in peers:
        assert f"Assessment given without a peer source in the pack: {peer}" in issues
    assert "Peer table not found" not in issues
    assert not any(i.startswith(("Unknown peer", "Assess each", "Confidence")) for i in issues)


def test_round4_b_frozen_no_peers_keeps_its_wording() -> None:
    universe = next(c for c in result("no_peers").claims if c.claim_id == "T1C.1.universe")
    assert universe.text.startswith("No peer source is in the pack, so")


# Rides with round 4 (reviewer Low): the 1C1 check order where two conditions coincide.
# Composed case: Brookmere, Calder and Dunmore adjusted EBITDA 0.0 (margins 0, so the margin
# median over three included peers is zero; leverage is not_applicable for them, so the
# leverage median has one peer and is missing) and Alder revenue 0.0 (its margin is
# not_applicable). Ellsworth stays excluded.


def _coinciding(cp1: dict[str, Fact] | None = None) -> cp1c.PeerBenchmarkResult:
    edited = sources("positive")
    for old, new in (
        (
            "Alder Ridge Holdings  2025-12-31  200.0  52.0",
            "Alder Ridge Holdings  2025-12-31  0.0  52.0",
        ),
        (
            "Brookmere Industries  2025-12-31  150.0  33.0",
            "Brookmere Industries  2025-12-31  150.0  0.0",
        ),
        ("Calder Vale Group  2025-12-31  90.0  27.0", "Calder Vale Group  2025-12-31  90.0  0.0"),
        (
            "Dunmore Cross Corporation  2025-09-30  300.0  48.0",
            "Dunmore Cross Corporation  2025-09-30  300.0  0.0",
        ),
    ):
        *frozen, peers = edited
        texts = [span.text for span in peers.spans]
        assert old in texts[0], old
        texts[0] = texts[0].replace(old, new, 1)
        spans = tuple(
            Span(locator=s.locator, text=t) for s, t in zip(peers.spans, texts, strict=True)
        )
        edited = (*frozen, peers.model_copy(update={"spans": spans}))
    body = json.loads(json.dumps(submissions()["positive"]["peer_benchmark"]))
    body["overall"]["rationale"] = "The peer set is described in the tables."
    return cp1c.compute(_with_sources("positive", edited, payload=body, cp1=cp1))


def test_1c1_value_not_meaningful_comes_before_a_zero_median() -> None:
    facts = _facts(_coinciding())
    assert facts["T1C.4.adjusted_ebitda_margin.median"].amount == 0
    flag = facts["T1C.5.p01.adjusted_ebitda_margin_flag"]
    assert (flag.status, flag.limitation) == (
        "not_applicable",
        "Not meaningful: the peer's own ratio is not meaningful",
    )
    zero = facts["T1C.5.p02.adjusted_ebitda_margin_flag"]
    assert (zero.status, zero.limitation) == (
        "not_applicable",
        "Not meaningful: the peer median is zero",
    )


def test_1c1_median_missing_comes_before_a_not_meaningful_value() -> None:
    facts = _facts(_coinciding())
    assert facts["T1C.4.total_leverage_adjusted.median"].status == "missing"
    flag = facts["T1C.5.p02.total_leverage_adjusted_flag"]
    assert (flag.status, flag.limitation) == ("missing", cp1c.NO_MEDIAN)


def test_1c1_excluded_comes_before_a_missing_median() -> None:
    facts = _facts(_coinciding())
    flag = facts["T1C.5.p05.total_leverage_adjusted_flag"]
    assert (flag.status, flag.limitation) == ("not_applicable", cp1c.EXCLUDED)


def test_1c3_missing_page2_table_reads_not_stated() -> None:
    edited = _edited("positive", 2, cp1c.P2_HEADER, "Peer  Basis  Segments  Year end")
    facts = _facts(cp1c.compute(_with_sources("positive", edited)))
    for row in ("p01", "p05"):
        for name in ("reporting_basis", "segments", "fiscal_year_end"):
            fact = facts[f"T1C.1.{row}.{name}"]
            assert (fact.status, fact.limitation) == ("missing", "Not stated in the peer source")


def test_page2_table_ends_at_the_first_line_that_is_not_four_fields() -> None:
    old = "Calder Vale Group  IFRS  1  December 31"
    edited = _edited("positive", 2, old, "A note line.\n" + old)
    facts = _facts(cp1c.compute(_with_sources("positive", edited)))
    assert facts["T1C.1.p02.reporting_basis"].text == "IFRS"
    assert facts["T1C.1.p03.reporting_basis"].status == "missing"


# Round 2 C3: page:1 must carry the "USD; amounts in millions" clause of its Basis line.


@pytest.mark.parametrize(
    "basis",
    [
        BASIS.replace("USD; amounts in millions", "EUR; amounts in thousands"),
        BASIS.replace("USD; amounts in millions", "USD; amounts in thousands"),
        "Note: twelve months to the period end shown; USD; amounts in millions.",  # no Basis line
    ],
)
def test_c3_basis_line_without_the_usd_millions_clause_is_peer_table_not_found(basis: str) -> None:
    case = _with_sources("positive", _edited("positive", 1, BASIS, basis))
    assert cp1c.calculation_issues(case) == ("Peer table not found",)


# Round 3 ruling 1C-x: an amount with more than one decimal place breaches the table rule.


def test_1c_x_amount_more_precise_than_one_decimal_place_is_peer_table_not_found() -> None:
    finer = _edited("positive", 1, ALDER, ALDER.replace("200.0", "200.04"))
    assert cp1c.calculation_issues(_with_sources("positive", finer)) == ("Peer table not found",)
    whole = _edited("positive", 1, ALDER, ALDER.replace("200.0", "200"))
    assert cp1c.calculation_issues(_with_sources("positive", whole)) == ()


def test_source_amounts_take_the_basis_line_currency_and_scale() -> None:
    fact = _facts(result("positive"))["T1C.2.p01.revenue"]
    assert (fact.currency, fact.unit, fact.scale, fact.decimals) == (
        "USD",
        "MILLIONS",
        Decimal(1_000_000),
        1,
    )


# Confidence rule as the lease states it (refusal_rules.confidence).


def test_high_confidence_is_refused_with_a_peer_source() -> None:
    body = json.loads(json.dumps(submissions()["positive"]["peer_benchmark"]))
    body["overall"]["confidence"] = "High"
    issues = cp1c.calculation_issues(inputs("positive", payload=body))
    assert issues == (
        "Confidence cannot be High: the peer figures are desk-supplied and unaudited",
    )


def test_high_confidence_rule_does_not_apply_without_a_peer_source() -> None:
    body = json.loads(json.dumps(submissions()["no_peers"]["peer_benchmark"]))
    body["overall"]["confidence"] = "High"
    assert cp1c.calculation_issues(inputs("no_peers", payload=body)) == ()


# Round 2 C1: the prohibited-conclusion check over every analyst text field, in the ruled order;
# round 4 (c): gap fields gap by gap (pinned by test_c1_prohibited_fields_in_the_ruled_order).


def test_prohibited_conclusions_in_limitations_and_gaps_are_refused() -> None:
    """Reviewer probe: a gap action and the overall limitation state an instrument view."""
    body = json.loads(json.dumps(submissions()["positive"]["peer_benchmark"]))
    body["gaps"][0]["action"] = "Overweight the bonds; leverage is 1.67x versus 2.50x."
    body["overall"]["limitation"] = "We recommend an overweight position at 6.00x coverage."
    issues = cp1c.calculation_issues(inputs("positive", payload=body))
    assert issues, issues
    assert all(
        issue.startswith(
            ("gaps[0].action: prohibited conclusion", "overall.limitation: prohibited")
        )
        for issue in issues
    ), issues
    assert any(issue.startswith("gaps[0].action: ") for issue in issues)
    assert any(issue.startswith("overall.limitation: ") for issue in issues)
    # the bare-figure rule stays on the rationales only (no 'Bare figure' issue here)
    assert not any("Bare figure" in issue for issue in issues)


def test_prohibited_check_reaches_the_assessment_limitation() -> None:
    body = json.loads(json.dumps(submissions()["positive"]["peer_benchmark"]))
    body["assessments"][3]["limitation"] = "Overweight it despite the period."
    issues = cp1c.calculation_issues(inputs("positive", payload=body))
    assert issues and all(i.startswith("assessments[3].limitation: prohibited") for i in issues)


def test_c1_prohibited_fields_in_the_ruled_order() -> None:
    body = json.loads(json.dumps(submissions()["positive"]["peer_benchmark"]))
    second = json.loads(json.dumps(body["gaps"][0]))
    body["gaps"].append(second)
    for gap in body["gaps"]:
        for name in ("gap", "why_it_matters", "affected_analysis", "action"):
            gap[name] = "Overweight it."
    body["assessments"][0]["rationale"] = "Overweight it."
    body["assessments"][0]["limitation"] = "Overweight it."
    body["assessments"][1]["rationale"] = "Overweight it."
    body["overall"]["rationale"] = "Overweight it."
    body["overall"]["limitation"] = "Overweight it."
    issues = cp1c.calculation_issues(inputs("positive", payload=body))
    paths = [issue.split(": prohibited conclusion")[0] for issue in issues]
    gaps = [f"gaps[{i}].{f}" for i in (0, 1) for f in ("gap", "why_it_matters",
            "affected_analysis", "action")]  # fmt: skip
    assert paths == [
        "assessments[0].rationale",
        "assessments[0].limitation",
        "assessments[1].rationale",
        "overall.rationale",
        "overall.limitation",
        *gaps,
    ], issues
    assert all('(instrument recommendation): "overweight"' in issue for issue in issues)


# Round 2 C2 (rules against the builder): a zero peer median. Reviewer probe: FFO of Alder,
# Brookmere and Calder set to 0.0, so the FFO-to-debt median over four included peers is zero.


def test_c2_zero_peer_median() -> None:
    edited = sources("positive")
    for line in (
        ALDER,
        "Brookmere Industries  2025-12-31  150.0  33.0  99.0  11.0  30.0",
        "Calder Vale Group  2025-12-31  90.0  27.0  40.5  4.5  18.9",
    ):
        *frozen, peers = edited
        texts = [span.text for span in peers.spans]
        zero = line.rsplit("  ", 1)[0] + "  0.0"
        texts[0] = texts[0].replace(line, zero, 1)
        spans = tuple(
            Span(locator=s.locator, text=t) for s, t in zip(peers.spans, texts, strict=True)
        )
        edited = (*frozen, peers.model_copy(update={"spans": spans}))
    found = cp1c.compute(_with_sources("positive", edited))
    facts = _facts(found)
    assert facts["T1C.4.ffo_to_debt.median"].amount == 0
    count = facts["T1C.4.ffo_to_debt.outlier_count"]
    assert (count.status, count.unit, count.limitation) == (
        "not_applicable",
        "peers",
        "Not meaningful: the peer median is zero",
    )
    flag = facts["T1C.5.issuer.ffo_to_debt_flag"]
    assert (flag.status, flag.limitation) == (
        "not_applicable",
        "Not meaningful: the peer median is zero",
    )
    claim = next(c for c in found.claims if c.claim_id == "T1C.4.ffo_to_debt")
    assert claim.text.endswith(
        "{T1C.4.ffo_to_debt.median|%} across {T1C.4.ffo_to_debt.n|peers}. The outlier test does "
        "not apply to this metric because the peer median is zero."
    )
    assert "not flagged" not in claim.text
    other = next(c for c in found.claims if c.claim_id == "T1C.4.total_leverage_adjusted")
    assert other.text.endswith(" The issuer is not flagged an outlier on this metric.")


# --- round 5 P1 and round 6 B1 (docs/rulings/2026-10-28-stage1.md) ------------------------------------


def test_round5_p1_not_ready_peer_source_own_line() -> None:
    found = cp1c.compute(_with_sources("no_peers", _not_ready("unreadable")))
    assert found.limitations[0] == (
        "No ready peer source is in the pack: no peer universe, median, position or outlier flag "
        "can be formed."
    )
    assert (
        result("no_peers").limitations[0] == expected()["cases"]["no_peers"]["own_limitations"][0]
    )


# B1: a CP-1 T4.10 ratio that is not known. The reviewer's probe makes interest coverage
# not_applicable (cash interest zero); a second case makes the margin missing with unit None.
COVERAGE_NA = "Not meaningful: cash interest is zero (ZERO_OR_NEGATIVE_DENOMINATOR)"
MARGIN_MISSING = "Not calculable: revenue is not stated"
NOT_COMPARED = "Not compared: one side is not available"


def _cp1_not_known() -> dict[str, Fact]:
    metrics = cp1_metrics()
    coverage = metrics["interest_coverage_adjusted"]
    metrics["interest_coverage_adjusted"] = coverage.model_copy(
        update={
            "amount": None,
            "status": "not_applicable",
            "limitation": COVERAGE_NA,
            "unit": "PERCENT",
            "currency": "USD",
            "scale": Decimal(1_000_000),
            "decimals": 2,
        }
    )
    margin = metrics["adjusted_ebitda_margin"]
    metrics["adjusted_ebitda_margin"] = margin.model_copy(
        update={"amount": None, "status": "missing", "limitation": MARGIN_MISSING, "unit": None}
    )
    return metrics


def _plain(case: str) -> Any:
    body = json.loads(json.dumps(submissions()[case]["peer_benchmark"]))
    body["overall"]["rationale"] = "The peer set is described in the tables."
    return body


def _b1(case: str) -> cp1c.PeerBenchmarkResult:
    found = inputs(case, payload=_plain(case), cp1=_cp1_not_known())
    assert cp1c.calculation_issues(found) == ()
    return cp1c.compute(found)


def test_b1_probe_payload_is_refused_not_raised() -> None:
    """Probe B1: the positive payload cites the issuer's coverage as a figure; with CP-1's ratio
    not known that is an issue, never a ValueError out of validation."""
    issues = cp1c.calculation_issues(inputs("positive", cp1=_cp1_not_known()))
    assert "Figure reference names a gap: T1C.3.issuer.interest_coverage_adjusted" in issues


@pytest.mark.parametrize(
    ("metric", "status", "reason", "unit"),
    [
        ("interest_coverage_adjusted", "not_applicable", COVERAGE_NA, "MULTIPLE"),
        ("adjusted_ebitda_margin", "missing", MARGIN_MISSING, "PERCENT"),
    ],
)
def test_b1_copies_carry_cp1_status_and_limitation(
    metric: str, status: str, reason: str, unit: str
) -> None:
    facts = _facts(_b1("positive"))
    source = _cp1_not_known()[metric]
    for fact_id in (f"T1C.3.issuer.{metric}", f"T1C.6.{metric}.cp1"):
        fact = facts[fact_id]
        # round 6g: an unsettled copy takes the metric's unit, currency and scale (a ratio has
        # no currency and scale 1, as T1C.3's own ratios); every other key stays verbatim
        assert (fact.status, fact.limitation, fact.amount) == (status, reason, None)
        assert (fact.unit, fact.currency, fact.scale) == (unit, None, Decimal(1)), fact_id
        assert (
            fact.period,
            fact.citations,
            fact.calculation_id,
            fact.value_class,
            fact.decimals,
        ) == (
            source.period,
            source.citations,
            source.calculation_id,
            source.value_class,
            source.decimals,
        ), fact_id


@pytest.mark.parametrize("metric", ["interest_coverage_adjusted", "adjusted_ebitda_margin"])
def test_b1_peer_statistics_unchanged_and_issuer_cells_not_compared(metric: str) -> None:
    facts = _facts(_b1("positive"))
    frozen = {f["fact_id"]: f for f in expected()["cases"]["positive"]["facts"]}
    for name in ("n", "median", "outlier_count"):
        fact_id = f"T1C.4.{metric}.{name}"
        assert _exact(facts[fact_id].amount) == frozen[fact_id]["amount_exact"], fact_id
    units = {"difference": {m.key: m for m in cp1c.METRICS}[metric].difference_unit, "position": "rank",
             "of": "entities"}  # fmt: skip
    for name, unit in units.items():
        fact = facts[f"T1C.4.{metric}.{name}"]
        assert (fact.status, fact.limitation, fact.unit, fact.period, fact.value_class) == (
            "missing",
            NOT_COMPARED,
            unit,
            cp1c.MIXED_PERIOD,
            None,
        ), name


@pytest.mark.parametrize(
    ("metric", "status", "reason"),
    [
        ("interest_coverage_adjusted", "not_applicable",
         "Not meaningful: the issuer's CP-1 ratio is not meaningful"),
        ("adjusted_ebitda_margin", "missing", "Not calculable: the issuer's CP-1 value is missing"),
    ],
)  # fmt: skip
def test_b1_issuer_outlier_cells_use_the_issuer_wording(
    metric: str, status: str, reason: str
) -> None:
    facts = _facts(_b1("positive"))
    for name, unit in (("deviation", "PERCENT"), ("flag", None)):
        fact = facts[f"T1C.5.issuer.{metric}_{name}"]
        assert (fact.status, fact.limitation, fact.unit, fact.period, fact.value_class) == (
            status,
            reason,
            unit,
            cp1c.MIXED_PERIOD,
            None,
        ), name
    # peers keep their own flags
    assert facts[f"T1C.5.p01.{metric}_flag"].status == "known"


@pytest.mark.parametrize("metric", ["interest_coverage_adjusted", "adjusted_ebitda_margin"])
def test_b1_tie_out_not_compared(metric: str) -> None:
    facts = _facts(_b1("positive"))
    assert facts[f"T1C.6.{metric}.sheet"].status == "known"
    difference = facts[f"T1C.6.{metric}.difference"]
    assert (
        difference.status,
        difference.limitation,
        difference.unit,
        difference.period,
        difference.value_class,
    ) == (
        "missing",
        NOT_COMPARED,
        {m.key: m for m in cp1c.METRICS}[metric].difference_unit,
        None,
        None,
    )
    result_fact = facts[f"T1C.6.{metric}.result"]
    assert (result_fact.text, result_fact.value_class, result_fact.calculation_id) == (
        "Not compared",
        None,
        None,
    )


def test_b1_claims() -> None:
    claims = {c.claim_id: c.text for c in _b1("positive").claims}
    assert claims["T1C.4.interest_coverage_adjusted"] == (
        "Interest coverage (adjusted) of the issuer is [T1C.3.issuer.interest_coverage_adjusted] "
        "against a peer median of {T1C.4.interest_coverage_adjusted.median|x} across "
        "{T1C.4.interest_coverage_adjusted.n|peers}. The outlier test does not apply to the issuer "
        "on this metric because its CP-1 value is not available."
    )
    assert claims["T1C.4.adjusted_ebitda_margin"] == (
        "Adjusted EBITDA margin of the issuer is [T1C.3.issuer.adjusted_ebitda_margin] against a "
        "peer median of {T1C.4.adjusted_ebitda_margin.median|%} across "
        "{T1C.4.adjusted_ebitda_margin.n|peers}. The outlier test does not apply to the issuer on "
        "this metric because its CP-1 value is not available."
    )
    frozen = {c["claim_id"]: c["text"] for c in expected()["cases"]["positive"]["claims"]}
    assert claims["T1C.4.total_leverage_adjusted"] == frozen["T1C.4.total_leverage_adjusted"]


def test_b1_own_lines_follow_the_peer_source_lines_in_metrics_order() -> None:
    limitations = list(_b1("positive").limitations)
    frozen = expected()["cases"]["positive"]["own_limitations"]
    assert limitations[:2] == frozen[:2]
    tail = (
        "so its difference from the peer median, its position and its outlier flag are not "
        "compared."
    )
    assert limitations[2:4] == [
        f"The issuer's adjusted EBITDA margin is not available in CP-1 ({MARGIN_MISSING}), {tail}",
        f"The issuer's interest coverage (adjusted) is not available in CP-1 ({COVERAGE_NA}), {tail}",
    ]
    assert limitations[4:] == frozen[2:]


def test_b1_new_strings_pass_prose_and_bare_figures() -> None:
    found = _b1("positive")
    bound = prose.bind(item.fact for item in found.facts)
    issuer = manifest()["cases"]["positive"]["run"]["issuer_name"]
    for claim in found.claims:
        assert prose.issues(claim.text, bound, names=(issuer,)) == (), claim.claim_id


def test_b1_precedence_no_peer_source_then_median_missing() -> None:
    no_peers = _facts(_b1("no_peers"))
    for name in ("difference", "position", "of"):
        fact = no_peers[f"T1C.4.interest_coverage_adjusted.{name}"]
        assert fact.limitation == "No peer source is in the pack", name
    assert no_peers["T1C.6.interest_coverage_adjusted.difference"].limitation == (
        "No peer source is in the pack"
    )
    gap = _facts(_b1("gap"))
    frozen = {f["fact_id"]: f for f in expected()["cases"]["gap"]["facts"]}
    for name in ("difference", "position", "of"):
        fact_id = f"T1C.4.interest_coverage_adjusted.{name}"
        assert gap[fact_id].limitation == frozen[fact_id]["limitation"], name


def test_b1_known_cp1_fact_with_the_wrong_unit_still_raises() -> None:
    metrics = cp1_metrics()
    metrics["total_leverage_adjusted"] = metrics["total_leverage_adjusted"].model_copy(
        update={"unit": "PERCENT"}
    )
    with pytest.raises(ValueError, match="CP-1 fact unavailable for total_leverage_adjusted"):
        cp1c.calculation_issues(inputs("positive", cp1=metrics))


B1_SENTENCE = (
    " The outlier test does not apply to the issuer on this metric because its CP-1 value is not "
    "available."
)


def test_b1_claim_comes_before_the_zero_median_sentence() -> None:
    """Review M1: the 1C1 order puts the issuer's unknown value ahead of a zero median."""
    found = _coinciding(cp1=_cp1_not_known())
    facts = _facts(found)
    assert facts["T1C.4.adjusted_ebitda_margin.median"].amount == 0
    assert facts["T1C.3.issuer.adjusted_ebitda_margin"].status == "missing"
    text = {c.claim_id: c.text for c in found.claims}["T1C.4.adjusted_ebitda_margin"]
    assert text.endswith(B1_SENTENCE)
    assert "peer median is zero" not in text


def test_b1_claim_sentence_skipped_when_the_median_is_missing_or_no_peer_source() -> None:
    """Review L1 / round 6g: the median-missing and no-peer-source reasons come first."""
    for case in ("gap", "no_peers"):
        frozen = {c["claim_id"]: c["text"] for c in expected()["cases"][case]["claims"]}
        claims = {c.claim_id: c.text for c in _b1(case).claims}
        k = "interest_coverage_adjusted"
        want = frozen[f"T1C.4.{k}"].replace(f"{{T1C.3.issuer.{k}|x}}", f"[T1C.3.issuer.{k}]")
        assert claims[f"T1C.4.{k}"] == want, case
        assert B1_SENTENCE not in claims[f"T1C.4.{k}"], case


CONFLICTING = "Conflicting: CP-1's reconciliation does not agree"


ISSUER_CONFLICTING = "Not calculable: the issuer's CP-1 value is conflicting"  # round 6h (a)


def _cp1_conflicting(metric: str = "total_leverage_adjusted") -> dict[str, Fact]:
    metrics = cp1_metrics()
    metrics[metric] = metrics[metric].model_copy(
        update={"amount": None, "status": "conflicting", "limitation": CONFLICTING}
    )
    return metrics


def test_6g_conflicting_cp1_fact_takes_the_b1_path() -> None:
    found = inputs("positive", payload=_plain("positive"), cp1=_cp1_conflicting())
    assert cp1c.calculation_issues(found) == ()
    result_ = cp1c.compute(found)
    facts = _facts(result_)
    k, source = "total_leverage_adjusted", cp1_metrics()["total_leverage_adjusted"]
    for fact_id in (f"T1C.3.issuer.{k}", f"T1C.6.{k}.cp1"):
        fact = facts[fact_id]
        assert (fact.status, fact.limitation, fact.amount, fact.unit) == (
            "conflicting",
            CONFLICTING,
            None,
            "MULTIPLE",
        ), fact_id
        assert (fact.period, fact.calculation_id) == (source.period, source.calculation_id)
    for fact_id in (
        f"T1C.4.{k}.difference",
        f"T1C.4.{k}.position",
        f"T1C.4.{k}.of",
        f"T1C.6.{k}.difference",
    ):
        fact = facts[fact_id]
        assert (fact.status, fact.limitation) == ("missing", NOT_COMPARED), fact_id
    # round 6h (a): the issuer's outlier cells follow the B1 issuer frames, not the 1C2 text
    for name, unit in (("deviation", "PERCENT"), ("flag", None)):
        fact = facts[f"T1C.5.issuer.{k}_{name}"]
        assert (fact.status, fact.limitation, fact.unit, fact.period, fact.value_class) == (
            "missing",
            ISSUER_CONFLICTING,
            unit,
            cp1c.MIXED_PERIOD,
            None,
        ), name
    assert facts[f"T1C.5.p01.{k}_flag"].status == "known"
    assert facts[f"T1C.6.{k}.result"].text == "Not compared"
    frozen = {f["fact_id"]: f for f in expected()["cases"]["positive"]["facts"]}
    for name in ("n", "median", "outlier_count"):
        fact_id = f"T1C.4.{k}.{name}"
        assert _exact(facts[fact_id].amount) == frozen[fact_id]["amount_exact"], fact_id
    claim = {c.claim_id: c.text for c in result_.claims}[f"T1C.4.{k}"]
    assert claim.endswith(B1_SENTENCE)
    tail = (
        "so its difference from the peer median, its position and its outlier flag are not "
        "compared."
    )
    assert result_.limitations[2] == (
        f"The issuer's total leverage (adjusted) is not available in CP-1 ({CONFLICTING}), {tail}"
    )


def test_6h_conflicting_issuer_cells_keep_the_median_missing_reason_first() -> None:
    """Round 6h (a): the conflicting reason sits at the value step of the 1C1 order, so a missing
    median still comes first (the gap case's coverage median is missing)."""
    k = "interest_coverage_adjusted"
    found = inputs("gap", payload=_plain("gap"), cp1=_cp1_conflicting(k))
    assert cp1c.calculation_issues(found) == ()
    facts = _facts(cp1c.compute(found))
    assert facts[f"T1C.3.issuer.{k}"].status == "conflicting"
    frozen = {f["fact_id"]: f for f in expected()["cases"]["gap"]["facts"]}
    for name in ("deviation", "flag"):
        fact_id = f"T1C.5.issuer.{k}_{name}"
        assert (facts[fact_id].status, facts[fact_id].limitation) == (
            "missing",
            frozen[fact_id]["limitation"],
        ), fact_id


def test_6g_absent_cp1_fact_still_raises() -> None:
    metrics = cp1_metrics()
    del metrics["total_leverage_adjusted"]
    with pytest.raises(ValueError, match="CP-1 fact unavailable for total_leverage_adjusted"):
        cp1c.calculation_issues(inputs("positive", cp1=metrics))
