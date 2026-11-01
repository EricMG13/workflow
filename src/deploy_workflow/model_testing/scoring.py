"""Module scorer: compares one module result with its golden facts through the mapping
(spec 7.4, 9a, 10.3). Python owns the arithmetic; every comparison is ``Decimal``."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Context, Decimal, InvalidOperation
from typing import Any, Literal, cast, get_args

from pydantic import Field

from deploy_vii.contracts import Contract, Fact, Module
from deploy_vii.cp5_integrity import UNIT_SCALE
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
# Fact.unit semantics (display.py "percent takes a decimal fraction"; cp5_integrity.UNIT_SCALE):
# fractions hold 0.922 for 92.2 percent; decimal_percent holds points; basis_points holds bps.
_FRACTION_UNITS = frozenset({"PERCENT", "decimal_fraction"})
_POINT_UNITS = frozenset({"decimal_percent", "pp"})
_BPS_UNITS = frozenset({"basis_points"})
_RATIO_UNITS = _FRACTION_UNITS | _POINT_UNITS | _BPS_UNITS
_PRINTED_NUMBER = re.compile(r"\d[\d,]*(\.\d+)?")
_SCALE_WORD = re.compile(r"\s*(thousand|million|billion)s?\b", re.IGNORECASE)
_SCALE_WORD_EXP = {"thousand": 3, "million": 6, "billion": 9}
_DATE_FORMATS = ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y")


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


def _nonblank(items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(x for x in items if x.strip())


def _parse_date(text: str) -> date | None:
    cleaned = str(checker().normalise(text))
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _is_numeric(golden: Any) -> bool:
    return bool(golden["value_type"] in checker().NUMERIC_TYPES)


def _golden_decimal(golden: Any) -> Decimal:
    return Decimal(golden["value"])


def _golden_units(golden: Any) -> Decimal:
    """Golden value in units; percent points and bps as stored."""
    value = _golden_decimal(golden)
    if golden["value_type"] in _PERCENT_TYPES:
        return value
    return value.scaleb(checker().SCALE_EXP[golden["scale"]], _CTX)


def _unit_problem(fact: Fact, golden: Any) -> str | None:
    """Why the fact's unit cannot be compared with the golden, or None."""
    unit = fact.unit or ""
    expected_scale = UNIT_SCALE.get(unit)
    if fact.amount is not None and expected_scale is not None and fact.scale != expected_scale:
        return f"unit {unit} expects scale {expected_scale}, fact has scale {fact.scale}"
    vtype = golden["value_type"]
    if vtype == "percent":
        ok = unit in _FRACTION_UNITS | _POINT_UNITS
    elif vtype == "bps":
        ok = unit in _BPS_UNITS
    elif golden.get("unit") is None and vtype == "decimal":
        ok = unit not in _POINT_UNITS | _BPS_UNITS  # a unitless ratio may be a fraction unit
    else:
        ok = unit not in _RATIO_UNITS
    if not ok:
        return f"unit {unit or 'none'} is not a {vtype} unit"
    return None


def _module_units(fact: Fact, golden: Any) -> Decimal | None:
    """Module value in the golden's terms: units, percent points or bps."""
    if fact.amount is None:
        return None
    value = _CTX.multiply(fact.amount, fact.scale)
    if fact.unit in _FRACTION_UNITS and golden["value_type"] == "percent":
        value = _CTX.multiply(value, Decimal(100))
    return value


def _numbers_equal(golden: Any, module_units: Decimal) -> bool:
    """Exact equality; a golden with fewer decimal places quantises the module value first."""
    gold = _golden_decimal(golden)
    exp = 0 if golden["value_type"] in _PERCENT_TYPES else checker().SCALE_EXP[golden["scale"]]
    in_golden_scale = module_units.scaleb(-exp, _CTX)
    gold_exp = gold.as_tuple().exponent
    if not isinstance(gold_exp, int):
        return False
    try:
        quantised = in_golden_scale.quantize(Decimal(1).scaleb(min(gold_exp, 0)), context=_CTX)
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
        return None if units is None else format(units.normalize(_CTX), "f")
    return fact.text


def _locate(module: Module | None, entry: MappingEntry) -> list[Fact]:
    if module is None:
        return []
    loc = entry.locator
    key = (loc.table_id, loc.row_id, loc.field, loc.period)
    return [f for f in module.facts if (f.table_id, f.row_id, f.field, f.period) == key]


def _has_value(fact: Fact | None) -> bool:
    return fact is not None and fact.status == "known"


def _equal(fact: Fact, golden: Any, entry: MappingEntry) -> bool:
    vtype = golden["value_type"]
    if _is_numeric(golden):
        units = _module_units(fact, golden)
        return units is not None and _numbers_equal(golden, units)
    if fact.text is None:
        return False
    if vtype == "date":
        expected = _parse_date(str(golden["value"]))
        observed = _parse_date(fact.text)
        return expected is not None and observed == expected
    accepted = [str(golden["value"])]
    if vtype == "text":
        accepted.extend(entry.subject_aliases)
    return _text(fact.text) in {_text(x) for x in accepted}


def _printed_number(printed: str) -> Decimal | None:
    match = _PRINTED_NUMBER.search(printed)
    if match is None:
        return None
    value = Decimal(match.group().replace(",", ""))
    stripped = printed.strip()
    if (stripped.startswith("(") and stripped.endswith(")")) or stripped.startswith("-"):
        value = -value
    word = _SCALE_WORD.match(printed, match.end())
    if word is not None:
        value = value.scaleb(_SCALE_WORD_EXP[word.group(1).lower()], _CTX)
    return value


def _printed_matches(printed: str, fact: Fact, golden: Any) -> bool:
    """Whether a conflicting golden's evidenced ``printed`` value is the module's value,
    read by the golden's value_type."""
    vtype = golden["value_type"]
    if vtype == "date":
        if fact.text is None:
            return False
        if _text(fact.text) == _text(printed):
            return True
        want = _parse_date(printed)
        return want is not None and _parse_date(fact.text) == want
    if vtype not in checker().NUMERIC_TYPES:
        return fact.text is not None and _text(fact.text) == _text(printed)
    if fact.amount is None or _unit_problem(fact, golden) is not None:
        return False
    units = _module_units(fact, golden)
    want_number = _printed_number(printed)
    return units is not None and want_number is not None and want_number == units


def _score_entry(
    entry: MappingEntry,
    facts: list[Fact],
    golden: Any,
    module: Module,
    upstream: frozenset[str],
) -> FactScore:
    fid = entry.fact_id
    expected = _expected_text(golden)
    status = golden["status"]
    fact = facts[0] if facts else None
    observed = _observed_text(fact, golden)

    def out(outcome: Outcome, seen: str | None = None) -> FactScore:
        return FactScore(
            fact_id=fid,
            outcome=outcome,
            expected=expected,
            observed=observed if seen is None else seen,
        )

    if len(facts) > 1:
        seen = f"{len(facts)} facts at one locator"
        if status == "missing" and any(_has_value(f) for f in facts):
            return out("invented", seen)
        return out("mismatch", seen)
    if status == "missing":
        return out("invented" if _has_value(fact) else "gap_ok")
    if status == "conflicting":
        if fact is not None and fact.status == "conflicting":
            return out("conflict_ok")
        limited = fact is not None and bool(
            (fact.limitation or "").strip() or _nonblank(module.limitations)
        )
        if (
            fact is not None
            and _has_value(fact)
            and limited
            and any(
                _printed_matches(str(ev.get("printed", "")), fact, golden)
                for ev in golden.get("evidence") or ()
            )
        ):
            return out("conflict_ok")
        return out("mismatch")
    if fact is None or not _has_value(fact):
        return out("missing_in_output")
    if _is_numeric(golden) and fact.amount is not None:
        problem = _unit_problem(fact, golden)
        if problem is not None:
            return out("mismatch", problem)
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
    if head_status not in get_args(HeadStatus):
        raise ValueError(f"head_status {head_status!r} is not one of {get_args(HeadStatus)}")
    head = cast(HeadStatus, head_status)
    entries = [e for e in mapping.entries if e.module == module_id]
    judgment = module_id in JUDGMENT_MODULES
    refusal = _nonblank(refusal_missing)
    refused_honestly = head == "refused" and bool(refusal)
    # An absent head, or a refusal naming nothing, has no module result to read.
    usable = head != "absent" and (head != "refused" or refused_honestly)
    live = module if usable else None

    def gap(fid: str, golden: Any) -> FactScore:
        return FactScore(
            fact_id=fid,
            outcome="gap_ok",
            expected=_expected_text(golden),
            observed="refused: " + ", ".join(refusal),
        )

    scores: list[FactScore] = []
    untraced: list[str] = []
    unscored = 0
    if live is not None:
        mapped_locators = {
            (e.locator.table_id, e.locator.row_id, e.locator.field, e.locator.period)
            for e in entries
        }
        for fact in live.facts:
            if fact.status != "known" or fact.amount is None:
                continue
            if not _traced(fact):
                untraced.append(fact.fact_id)
            elif (fact.table_id, fact.row_id, fact.field, fact.period) not in mapped_locators:
                unscored += 1

    for entry in entries:
        golden = case.facts[entry.fact_id]
        if live is None:
            if refused_honestly:
                scores.append(gap(entry.fact_id, golden))
                continue
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
        scored = _score_entry(entry, _locate(live, entry), golden, live, upstream_mismatches)
        if refused_honestly and scored.outcome == "missing_in_output":
            scored = gap(entry.fact_id, golden)
        scores.append(scored)

    listed = {e.fact_id for e in entries}
    for u in mapping.unmapped:
        if u.fact_id in case.facts and case.facts[u.fact_id]["module"] == module_id:
            scores.append(_unmapped(case, u.fact_id))
            listed.add(u.fact_id)
    for fid in sorted(mapping.pending(case)):
        if case.facts[fid]["module"] == module_id and fid not in listed:
            scores.append(_unmapped(case, fid))

    outcomes = {s.outcome for s in scores}
    bad = "invented" in outcomes or bool(untraced)
    if refused_honestly:
        # the module named what it lacked: pass only if it invented nothing
        passed = not bad and "mismatch" not in outcomes
    elif module is None or not usable:
        passed = False  # no usable module result never passes
    elif judgment:
        passed = not bad  # no value facts required
    else:
        # The module itself declares the limit (spec 10.3): blocked or restricted only.
        honest_gap = head in ("blocked", "restricted") and bool(_nonblank(module.limitations))
        passed = (
            not bad
            and "mismatch" not in outcomes
            and ("missing_in_output" not in outcomes or honest_gap)
        )
    return ModuleScore(
        module_id=module_id,
        head_status=head,
        facts=tuple(scores),
        untraced=tuple(untraced),
        unscored=unscored,
        judgment=judgment,
        passed=passed,
    )


def _unmapped(case: GoldenCase, fid: str) -> FactScore:
    return FactScore(
        fact_id=fid, outcome="unmapped", expected=_expected_text(case.facts[fid]), observed=None
    )
