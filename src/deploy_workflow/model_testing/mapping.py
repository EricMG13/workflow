"""Golden mapping: ties each golden fact to one fact in a module result (spec 9a.1).

A mapping is made against one commit of each module's code (``module_commits``) and covers one
module at a time; facts of modules without a commit are *pending*, not unmapped by mistake.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from deploy_vii.contracts import Contract
from deploy_workflow.model_testing.cases import GoldenCase

_COMMIT = re.compile(r"[0-9a-f]{40}")


class MappingError(ValueError):
    """A golden mapping cannot be used for scoring."""


def _norm(text: str) -> str:
    from deploy_workflow.model_testing.scoring import _text  # scoring imports this module

    return _text(text)


class RowKey(Contract):
    """Finds a register row by the text of its key cell instead of a fixed row id (register
    modules number rows in model submission order). ``aliases`` only help find the row."""

    field: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _aliases_nonblank(self) -> RowKey:
        if any(not _norm(a) for a in self.aliases):
            raise ValueError("row_key aliases must be non-blank")
        return self


class PeriodRef(Contract):
    """Names a locator's period by a register row (e.g. T4.14) instead of a literal string:
    the row whose ``match`` cells all equal gives its ``id_field`` cell text as the period."""

    table_id: str = Field(min_length=1)
    id_field: str = Field(min_length=1)
    match: dict[str, str] = Field(min_length=1)

    @model_validator(mode="after")
    def _match_nonblank(self) -> PeriodRef:
        if any(not _norm(k) or not _norm(v) for k, v in self.match.items()):
            raise ValueError("period_ref match keys and values must be non-blank")
        return self


class Locator(Contract):
    table_id: str = Field(min_length=1)
    row_id: str | None = Field(default=None, min_length=1)
    row_key: RowKey | None = None
    field: str = Field(min_length=1)
    period: str | None
    period_ref: PeriodRef | None = None

    @model_validator(mode="after")
    def _one_row_locator(self) -> Locator:
        if (self.row_id is None) == (self.row_key is None):
            raise ValueError("locator needs exactly one of row_id or row_key")
        if self.period_ref is not None and self.period is not None:
            raise ValueError("locator sets both period and period_ref; use only one")
        return self


class MappingEntry(Contract):
    fact_id: str = Field(min_length=1)
    module: str = Field(min_length=1)
    locator: Locator
    subject_aliases: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()


class Unmapped(Contract):
    fact_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class Mapping(Contract):
    schema_version: Literal["golden-mapping/1"]
    case_id: str = Field(min_length=1)
    preparer: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    module_commits: dict[str, str]
    entries: tuple[MappingEntry, ...]
    unmapped: tuple[Unmapped, ...]

    @model_validator(mode="after")
    def _self_consistent(self) -> Mapping:
        if self.preparer == self.reviewer:
            raise ValueError("reviewer must differ from preparer")
        for module, commit in self.module_commits.items():
            if not _COMMIT.fullmatch(commit):
                raise ValueError(f"module_commits[{module!r}] is not a 40-hex lowercase commit")
        seen: set[tuple[str, str, str, str, str | None]] = set()
        for e in self.entries:
            loc = e.locator
            if loc.row_id is None or loc.period_ref is not None:
                continue  # row-key and period_ref entries are checked in load_mapping
            key = (e.module, loc.table_id, loc.row_id, loc.field, loc.period)
            if key in seen:
                raise ValueError(
                    f"locator used twice in module {e.module}: "
                    f"{loc.table_id}/{loc.row_id}/{loc.field}/{loc.period}"
                )
            seen.add(key)
        return self

    def pending(self, case: GoldenCase) -> frozenset[str]:
        return frozenset(
            fid for fid, fact in case.facts.items() if fact["module"] not in self.module_commits
        )


def _no_dups(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate key")
        out[k] = v
    return out


def _check_row_key_collisions(m: Mapping, case: GoldenCase, name: str) -> None:
    seen: list[tuple[tuple[Any, ...], set[str], str]] = []
    for e in m.entries:
        loc = e.locator
        rk = loc.row_key
        ref = loc.period_ref
        if rk is None and ref is None:
            continue
        if rk is not None:
            texts = {_norm(str(case.facts[e.fact_id].get("subject", "")))}
            texts.update(_norm(a) for a in rk.aliases)
            row_part: tuple[Any, ...] = ("key", rk.field)
        else:
            texts = {str(loc.row_id)}
            row_part = ("id",)
        ref_part: tuple[Any, ...] | None = None
        if ref is not None:
            items = sorted((_norm(k), _norm(v)) for k, v in ref.match.items())
            ref_part = (ref.table_id, ref.id_field, tuple(items))
        ident = (e.module, loc.table_id, loc.field, loc.period, row_part, ref_part)
        for other_ident, other_texts, other_id in seen:
            if other_ident == ident and texts & other_texts:
                raise MappingError(
                    f"{name}: locators of {other_id} and {e.fact_id} collide in module "
                    f"{e.module}: {loc.table_id}/{loc.field}/{loc.period}"
                )
        seen.append((ident, texts, e.fact_id))


def _check_against_case(m: Mapping, case: GoldenCase, name: str) -> None:
    if m.case_id != case.case_id:
        raise MappingError(f"{name}: case_id {m.case_id!r} is not {case.case_id!r}")
    for e in m.entries:
        fact = case.facts.get(e.fact_id)
        if fact is None:
            raise MappingError(f"{name}: entry fact {e.fact_id} is not in the case's in-plan facts")
        if e.module != fact["module"]:
            raise MappingError(
                f"{name}: entry {e.fact_id} names module {e.module}, golden says {fact['module']}"
            )
        if e.module not in m.module_commits:
            raise MappingError(f"{name}: entry {e.fact_id}: {e.module} has no module_commits entry")
        for dep in e.depends_on:
            if dep not in case.facts:
                raise MappingError(f"{name}: entry {e.fact_id} depends_on unknown fact {dep}")
    for u in m.unmapped:
        fact = case.facts.get(u.fact_id)
        if fact is None:
            raise MappingError(f"{name}: unmapped fact {u.fact_id} is not in the case's facts")
        if fact["module"] not in m.module_commits:
            raise MappingError(
                f"{name}: unmapped {u.fact_id}: {fact['module']} has no module_commits entry"
            )
    _check_row_key_collisions(m, case, name)
    counts = Counter([e.fact_id for e in m.entries] + [u.fact_id for u in m.unmapped])
    for fid, n in counts.items():
        if n > 1:
            raise MappingError(f"{name}: fact {fid} must appear exactly once, found {n}")
    for fid, fact in case.facts.items():
        if fact["module"] in m.module_commits and fid not in counts:
            raise MappingError(
                f"{name}: fact {fid} of mapped module {fact['module']} is in neither entries nor unmapped"
            )


def load_mapping(path: Path, case: GoldenCase) -> Mapping:
    name = path.name
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise MappingError(f"{name}: cannot read: {exc.strerror or exc}") from exc
    try:
        json.loads(raw, object_pairs_hook=_no_dups)
        mapping = Mapping.model_validate_json(raw)
    except ValidationError as exc:
        shown = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or '<root>'}: {err['msg']}"
            for err in exc.errors(include_input=False, include_url=False)[:5]
        )
        raise MappingError(f"{name}: invalid mapping: {shown}") from exc
    except ValueError as exc:  # JSONDecodeError, UnicodeDecodeError, duplicate keys
        raise MappingError(f"{name}: not valid JSON (duplicate or malformed key)") from exc
    _check_against_case(mapping, case, name)
    return mapping
