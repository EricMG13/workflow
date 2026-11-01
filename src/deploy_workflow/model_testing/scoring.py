"""Module scorer: compares one module result with its golden facts through the mapping
(spec 7.4, 9a, 10.3). Python owns the arithmetic; every comparison is ``Decimal``."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Context, Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import Field

from deploy_vii.contracts import Contract, Fact, Module
from deploy_workflow.model_testing.cases import GoldenCase, checker
from deploy_workflow.model_testing.mapping import Mapping, MappingEntry

Outcome = Literal[
    "match",
    "mismatch",
    "missing_in_output",
    "invented",
    "gap_ok",
    "conflict_ok",
    "unmapped",
    "inherited",
]
HeadStatus = Literal["accepted", "restricted", "blocked", "refused", "absent"]

JUDGMENT_MODULES = frozenset({"CP-5", "CP-6", "CP-MODEL", "CP-2A"})

# Wide enough that scaling and quantising never round before the comparison does.
_CTX = Context(prec=120, rounding=ROUND_HALF_UP)
_PERCENT_TYPES = ("percent", "bps")
_PRINTED_NUMBER = re.compile(r"-?\d[\d,]*(\.\d+)?")
_PRINTED_DATE_FORMATS = ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d")


class FactScore(Contract):
    fact_id: str = Field(min_length=1)
    outcome: Outcome
    expected: str | None
    observed: str | None


class ModuleScore(Contract):
    module_id: str = Field(min_length=1)
    head_status: HeadStatus
    facts: tuple[FactScore, ...]
    untraced: tuple[str, ...]
    unscored: int = Field(ge=0)
    judgment: bool
    passed: bool


def _text(value: str) -> str:
    return str(checker().normalise(value)).casefold()


def _is_numeric(golden: Any) -> bool:
    return bool(golden["value_type"] in checker().NUMERIC_TYPES)


def _golden_decimal(golden: Any) -> Decimal:
    return Decimal(golden["value"])


def _golden_units(golden: Any) -> Decimal:
    """Golden value in units; percent and bps are compared as stored."""
    value = _golden_decimal(golden)
    if golden["value_type"] in _PERCENT_TYPES:
        return value
    return value.scaleb(checker().SCALE_EXP[golden["scale"]], _CTX)


def _module_units(fact: Fact, golden: Any) -> Decimal | None:
    """Module value in the golden's units (``amount x scale``, as ``cp5_integrity`` does)."""
    if fact.amount is None:
        return None
    if golden["value_type"] in _PERCENT_TYPES:
        return fact.amount
    return _CTX.multiply(fact.amount, fact.scale)


def _numbers_equal(golden: Any, module_units: Decimal) -> bool:
    """Exact equality; a golden with fewer decimal places quantises the module value first."""
    gold = _golden_decimal(golden)
    exp = 0 if golden["value_type"] in _PERCENT_TYPES else checker().SCALE_EXP[golden["scale"]]
    in_golden_scale = module_units.scaleb(-exp, _CTX)
    places = max(0, -gold.as_tuple().exponent)  # type: ignore[operator]
    try:
        quantised = in_golden_scale.quantize(Decimal(1).scaleb(-places), context=_CTX)
    except InvalidOperation:
        return False
    return quantised == gold


def _expected_text(golden: Any) -> str | None:
    if golden["value"] is None:
        return None
    if _is_numeric(golden):
        return format(_golden_units(golden), "f")
    return str(golden["value"])


def _observed_text(fact: Fact | None, golden: Any) -> str | None:
    if fact is None:
        return None
    if fact.amount is not None:
        units = _module_units(fact, golden)
        return None if units is None else format(units, "f")
    return fact.text


def _locate(module: Module | None, entry: MappingEntry) -> Fact | None:
    if module is None:
        return None
    loc = entry.locator
    for fact in module.facts:
        if (fact.table_id, fact.row_id, fact.field, fact.period) == (
            loc.table_id,
            loc.row_id,
            loc.field,
            loc.period,
        ):
            return fact
    return None


def _has_value(fact: Fact | None) -> bool:
    return fact is not None and fact.status == "known"


def _equal(fact: Fact, golden: Any, entry: MappingEntry) -> bool:
    if _is_numeric(golden):
        units = _module_units(fact, golden)
        return units is not None and _numbers_equal(golden, units)
    if fact.text is None:
        return False
    observed = _text(fact.text)
    expected = [str(golden["value"]), *entry.subject_aliases]
    return observed in {_text(x) for x in expected}


def _printed_matches(printed: str, fact: Fact, golden: Any) -> bool:
    """Whether a conflicting golden's evidenced ``printed`` value is the module's value."""
    if fact.text is not None:
        observed = _text(fact.text)
        if observed == _text(printed):
            return True
        for fmt in _PRINTED_DATE_FORMATS:
            try:
                return observed == datetime.strptime(printed.strip(), fmt).date().isoformat()
            except ValueError:
                continue
        return False
    units = _module_units(fact, golden)
    match = _PRINTED_NUMBER.search(printed)
    if units is None or match is None:
        return False
    return Decimal(match.group().replace(",", "")) == units


def _score_entry(
    entry: MappingEntry,
    fact: Fact | None,
    golden: Any,
    module: Module,
    upstream: frozenset[str],
) -> FactScore:
    fid = entry.fact_id
    expected = _expected_text(golden)
    observed = _observed_text(fact, golden)
    status = golden["status"]

    def out(outcome: Outcome) -> FactScore:
        return FactScore(fact_id=fid, outcome=outcome, expected=expected, observed=observed)

    if status == "missing":
        return out("invented" if _has_value(fact) else "gap_ok")
    if status == "conflicting":
        if fact is not None and fact.status == "conflicting":
            return out("conflict_ok")
        if (
            fact is not None
            and _has_value(fact)
            and (fact.limitation or module.limitations)
            and any(
                _printed_matches(str(ev.get("printed", "")), fact, golden)
                for ev in golden.get("evidence") or ()
            )
        ):
            return out("conflict_ok")
        return out("mismatch")
    if not _has_value(fact):
        return out("missing_in_output")
    assert fact is not None
    if _equal(fact, golden, entry):
        return out("match")
    if set(entry.depends_on) & upstream:
        return out("inherited")
    return out("mismatch")


def _traced(fact: Fact) -> bool:
    return bool(fact.citations) or fact.calculation_id is not None


def score_module(
    module: Module | None,
    module_id: str,
    head_status: str,
    case: GoldenCase,
    mapping: Mapping,
    upstream_mismatches: frozenset[str],
    refusal_missing: tuple[str, ...] = (),
) -> ModuleScore:
    entries = [e for e in mapping.entries if e.module == module_id]
    pending = mapping.pending(case)
    scores: list[FactScore] = []
    judgment = module_id in JUDGMENT_MODULES

    def unmapped(fid: str) -> FactScore:
        golden = case.facts[fid]
        return FactScore(
            fact_id=fid, outcome="unmapped", expected=_expected_text(golden), observed=None
        )

    refused_honestly = head_status == "refused" and bool(refusal_missing)
    untraced: list[str] = []
    unscored = 0

    if module is not None and not refused_honestly:
        mapped_locators = {
            (e.locator.table_id, e.locator.row_id, e.locator.field, e.locator.period)
            for e in entries
        }
        for fact in module.facts:
            if fact.status != "known" or fact.amount is None:
                continue
            if not _traced(fact):
                untraced.append(fact.fact_id)
            elif (fact.table_id, fact.row_id, fact.field, fact.period) not in mapped_locators:
                unscored += 1

    for entry in entries:
        golden = case.facts[entry.fact_id]
        if refused_honestly:
            scores.append(
                FactScore(
                    fact_id=entry.fact_id,
                    outcome="gap_ok",
                    expected=_expected_text(golden),
                    observed="refused: " + ", ".join(refusal_missing),
                )
            )
            continue
        if module is None or head_status in ("absent", "refused"):
            outcome: Outcome = "gap_ok" if golden["status"] == "missing" else "missing_in_output"
            scores.append(
                FactScore(
                    fact_id=entry.fact_id,
                    outcome=outcome,
                    expected=_expected_text(golden),
                    observed=None,
                )
            )
            continue
        scores.append(
            _score_entry(entry, _locate(module, entry), golden, module, upstream_mismatches)
        )

    listed = {e.fact_id for e in entries}
    for u in mapping.unmapped:
        if u.fact_id in case.facts and case.facts[u.fact_id]["module"] == module_id:
            scores.append(unmapped(u.fact_id))
            listed.add(u.fact_id)
    for fid in sorted(pending):
        if case.facts[fid]["module"] == module_id and fid not in listed:
            scores.append(unmapped(fid))

    outcomes = {s.outcome for s in scores}
    bad = "invented" in outcomes or bool(untraced)
    if judgment:
        passed = not bad  # no value facts required
    elif refused_honestly:
        passed = True  # the module named what it lacked and invented nothing
    else:
        all_non_known = (
            module is not None
            and bool(entries)
            and all(not _has_value(_locate(module, e)) for e in entries)
        )
        honest_gap = (
            module is not None
            and (head_status in ("blocked", "restricted") or all_non_known)
            and bool(module.limitations)
        )
        passed = (
            not bad
            and "mismatch" not in outcomes
            and ("missing_in_output" not in outcomes or honest_gap)
        )
    return ModuleScore(
        module_id=module_id,
        head_status=head_status,  # type: ignore[arg-type]
        facts=tuple(scores),
        untraced=tuple(untraced),
        unscored=unscored,
        judgment=judgment,
        passed=passed,
    )
