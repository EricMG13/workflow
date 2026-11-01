"""O6 Task 3: the rule lists and the coverage oracle's extractor.

A rule is ``{"id": "<step>.<n>", "statement": str, "checks": [...]}``. ``statement`` is the
sentence the prompt must carry; ``checks`` name what enforces it, in three kinds (O6-P11):

* ``fn:<module>:<qualname>``: a function that enforces the rule, either an issue site of a
  validator or the prompt builder (``prompts.fence:*``);
* ``oracle:<case>:<id>``: a refusal id of a frozen ``cases/<case>-owner/expected.json``;
* ``code:cp1b:<site>``: one of CP-1B's code-defined refusals (it has no oracle).

The 12 steps that already have a ``STEP_CONTRACTS`` text take their rule ids, ``<step>.<letter>``,
and statements from that text; ``rule_lists/compose.json`` holds the composer's own rules. The 14
new steps get a draft from ``extract_checks``: one candidate rule per oracle refusal group, the
issue-site functions reachable from the step's validator, ``statement`` left empty, and, where the
core states its rules in prose, that prose in ``from_code``.

Nothing here runs a validator or calls a model; it reads source with ``ast`` and the frozen
oracles with ``json``.
"""

import ast
import hashlib
import importlib
import importlib.util
import json
import re
import subprocess
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

__all__ = [
    "COMPOSE",
    "DirtyTree",
    "Rule",
    "check_exists",
    "core_sources",
    "dirty_paths",
    "extract_checks",
    "file_sha256",
    "golden_document",
    "issue_functions",
    "load_rules",
    "module_path",
    "needed_checks",
    "oracle_ids",
    "oracle_path",
    "refresh_sha256",
    "rule_ids",
    "sha256_section",
    "step_ids",
    "write_golden",
]

ROOT = Path(__file__).resolve().parents[3]
RULE_LISTS = Path(__file__).resolve().parent / "rule_lists"
COMPOSE = "compose"
_LETTER_RULE = re.compile(r"^([a-z])\. ", re.MULTILINE)

# Where a validator appends the issue it raises. The receiver must be one of these and the
# argument must carry a string literal, so ``out.append(fact)`` is not a site. A new collector name
# is invisible here; the mutation probe in test_rules.py covers the ones in this set.
_COLLECTORS = frozenset(
    {
        "issues",
        "found",
        "out",
        "problems",
        "errors",
        "chk",
        "miss",
        "self",
        "self.found",
        "self.issues",
    }
)
_ADDERS = frozenset({"append", "extend", "add"})


@dataclass(frozen=True)
class Rule:
    id: str
    statement: str
    checks: tuple[str, ...]
    from_code: str | None = None
    when: str | None = None  # compose rules: "inputs", "line_source" or "pins"


def rule_from(raw: Mapping[str, object]) -> Rule:
    checks = raw["checks"]
    if not isinstance(checks, list):
        raise TypeError(f"rule {raw.get('id')}: checks must be a list, not {type(checks).__name__}")
    return Rule(
        id=str(raw["id"]),
        statement=str(raw["statement"]),
        checks=tuple(str(c) for c in checks),
        from_code=None if raw.get("from_code") is None else str(raw["from_code"]),
        when=None if raw.get("when") is None else str(raw["when"]),
    )


def load_rules(name: str) -> tuple[Rule, ...]:
    """The committed rules of a step (or ``compose``), in file order."""
    document = json.loads((RULE_LISTS / f"{name}.json").read_text(encoding="utf-8"))
    return tuple(rule_from(raw) for raw in document["rules"])


def step_ids() -> tuple[str, ...]:
    """The step ids that have a rule-list file (``compose`` is not a step)."""
    return tuple(sorted(p.stem for p in RULE_LISTS.glob("*.json") if p.stem != COMPOSE))


def rule_ids() -> dict[str, list[str]]:
    return {name: [r.id for r in load_rules(name)] for name in (COMPOSE, *step_ids())}


def contract_rules(contract: str, step_id: str) -> tuple[tuple[str, str], ...]:
    """``(<step>.<letter>, statement)`` for every lettered rule of a ``STEP_CONTRACTS`` text; the
    statement is the whole rule, continuation lines included, up to the next lettered rule."""
    starts = list(_LETTER_RULE.finditer(contract))
    out = []
    for n, match in enumerate(starts):
        end = starts[n + 1].start() if n + 1 < len(starts) else len(contract)
        out.append((f"{step_id}.{match.group(1)}", contract[match.start() : end].strip()))
    return tuple(out)


# --- the cores -----------------------------------------------------------------------------

OWNERS = "deploy_workflow.owners."
VII = "deploy_vii."

# step -> (entry validators as "module:qualname", the oracle cases that cover it). The entry is
# what ``ENTRY_VALIDATOR`` is for an owner core; CP-0 and CP-1 have none, so theirs are the
# functions their submit paths call (``cp1_workflow._validate_stage`` is the CP-1 entry).
ENTRIES: Mapping[str, tuple[str, ...]] = {
    "source_readiness": (
        VII + "readiness:validate_review",
        "deploy_workflow.financial_workflow:_evidence_issues",
    ),
    "source_context": (
        VII + "source_context:validate_source_context",
        "deploy_workflow.financial_workflow:_evidence_issues",
    ),
    "financials": (
        VII + "cp1_workflow:_validate_stage",
        VII + "context_binding:validate_financial_context",
        VII + "financial_validation:validate_financial_review",
        VII + "statement_validation:statement_issues",
        VII + "canonical_audit:validate_definition_review",
        "deploy_workflow.financial_workflow:_evidence_issues",
    ),
    "narrative": (VII + "narrative:validate_narrative_review",),
    "readiness": (VII + "downstream_readiness:validate_downstream_review",),
    "quality": (VII + "quality:validate_quality_review",),
    "business_context": (VII + "business_context:_validate_step",),
    "credit_synthesis": (VII + "cp2_synthesis:_validate_step",),
    "relative_value": (VII + "cp3_relative_value:_validate_step",),
    "integrity_review": (VII + "cp5_integrity:_validate_step", OWNERS + "cp5:_entry_validator"),
    "legal_covenants": (VII + "cp4_legal:_validate_step", OWNERS + "cp4:semantic_issues"),
    "committee_challenge": (VII + "cp6_committee:_validate_step",),
    "research": (OWNERS + "cpdr:ENTRY_VALIDATOR",),
    "market_implied": (OWNERS + "cp3d:_validate_step",),
    "macro_fx": (OWNERS + "cp2e:_validate_step",),
    "decision_ledger": (OWNERS + "cp8:_validate_step",),
    "downside_pathway": (OWNERS + "cp2a:_validate_step",),
    "liquidity_bridge": (OWNERS + "cp2d:_validate_step",),
    "change_screen": (OWNERS + "cpl10:_validate_step",),
    "earnings_quality": (OWNERS + "cp1d:_validate_step",),
    "forward_credit_model": (OWNERS + "cp2g:_validate_step",),
    "peer_benchmark": (OWNERS + "cp1c:_validate_step",),
    "refinancing_risk": (OWNERS + "cp3c:_validate_step",),
    "rating_triggers": (OWNERS + "cp2h:_validate_step",),
    "restructuring_fulcrum": (OWNERS + "cp4c:_validate_step",),
    "earnings_delta": (OWNERS + "cp1b:_validate_step",),
}

# The owner module whose ``ENTRY_VALIDATOR`` is the step's entry (checked against ENTRIES).
OWNER_MODULE: Mapping[str, str] = {
    "business_context": OWNERS + "cp1a",
    "credit_synthesis": OWNERS + "cp2",
    "relative_value": OWNERS + "cp3",
    "integrity_review": OWNERS + "cp5",
    "legal_covenants": OWNERS + "cp4",
    "committee_challenge": OWNERS + "cp6",
    "research": OWNERS + "cpdr",
    "market_implied": OWNERS + "cp3d",
    "macro_fx": OWNERS + "cp2e",
    "decision_ledger": OWNERS + "cp8",
    "downside_pathway": OWNERS + "cp2a",
    "liquidity_bridge": OWNERS + "cp2d",
    "change_screen": OWNERS + "cpl10",
    "earnings_quality": OWNERS + "cp1d",
    "forward_credit_model": OWNERS + "cp2g",
    "peer_benchmark": OWNERS + "cp1c",
    "refinancing_risk": OWNERS + "cp3c",
    "rating_triggers": OWNERS + "cp2h",
    "restructuring_fulcrum": OWNERS + "cp4c",
    "earnings_delta": OWNERS + "cp1b",
}


@dataclass(frozen=True)
class OracleSpec:
    """One frozen oracle a step reads: ``case`` is the ``cases/<case>-owner`` directory, ``prefix``
    keeps only the ids that begin with it (cp3-cp6 serves two steps), ``part`` reads the containers
    of ``document[part]`` instead of the top level (cp3-context's ``cp3d``)."""

    case: str
    prefix: str = ""
    part: str = ""  # a key of the document whose own refusal containers are read (cp3-context)


ORACLES: Mapping[str, tuple[OracleSpec, ...]] = {
    "relative_value": (OracleSpec("cp3-cp6", "cp3-"), OracleSpec("cp3-context")),
    "committee_challenge": (OracleSpec("cp3-cp6", "cp6-"),),
    "integrity_review": (OracleSpec("cp5"),),
    "research": (OracleSpec("cpdr"),),
    "market_implied": (OracleSpec("cp3d"), OracleSpec("cp3-context", part="cp3d")),
    "macro_fx": (OracleSpec("cp2e"),),
    "decision_ledger": (OracleSpec("cp8"),),
    "downside_pathway": (OracleSpec("cp2a"),),
    "liquidity_bridge": (OracleSpec("cp2d"),),
    "change_screen": (OracleSpec("cpl10"),),
    "earnings_quality": (OracleSpec("cp1d"),),
    "forward_credit_model": (OracleSpec("cp2g"),),
    "peer_benchmark": (OracleSpec("cp1c"),),
    "refinancing_risk": (OracleSpec("cp3c"),),
    "rating_triggers": (OracleSpec("cp2h"),),
    "restructuring_fulcrum": (OracleSpec("cp4c"),),
}

# Oracles read nowhere above, and why (a case may name a part: ``<case>#<part>``).
ORACLE_EXCLUSIONS: Mapping[str, str] = {
    "cp2h-context": "refusals are composer_only: Python builds that context, no model writes it",
    "cp4": "its semantic_gate lists markers and provenance, not refusal ids; the check source "
    "is cp4_legal and owners.cp4.semantic_issues (ast)",
    "context-attachments": "refusals of the attachment context loader, not of a step submission",
    "valuation-context": "refusal_ids of the valuation context loader, not of a step submission",
    "pins-context": "pinned lines are covered by compose.O6 (_pin_lines), not by oracle ids",
}

# Containers of an oracle's ``expected.json`` that list content refusals. ``tamper_refusals`` and
# the blocked cases test the journal, not what a model wrote, so they are not content refusals.
_REFUSAL_KEYS = (
    "refusals",
    "tool_refusals",
    "tool_use_refusals",
    "hand_built_page_refusals",
    "validator_refusals",
    "model_side_refusals",
)

CP1B_STEP = "earnings_delta"


def oracle_path(case: str) -> Path:
    return ROOT / "cases" / f"{case}-owner" / "expected.json"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _list_ids(key: str, items: list[Any]) -> tuple[str, ...]:
    """The ids of a refusal list; an item with no id is an error, never dropped."""
    ids = []
    for item in items:
        if not isinstance(item, dict):
            raise TypeError(f"oracle container {key}: an item is not an object: {item!r}")
        ident = item.get("id")
        if ident is None:
            raise ValueError(f"oracle container {key}: an item has no id: {item!r}")
        if not isinstance(ident, str):
            raise TypeError(f"oracle container {key}: id {ident!r} is not a string")
        ids.append(ident)
    return tuple(ids)


def _nested_lists(node: Mapping[str, Any]) -> dict[str, list[Any]]:
    return {k: v for k, v in node.items() if k in _REFUSAL_KEYS and isinstance(v, list)}


def _dict_form(
    key: str, node: Mapping[str, Any], document: Mapping[str, Any]
) -> dict[str, tuple[str, ...]]:
    """A dict container: nested refusal lists (cp5, cp3-cp6), else the dict keyed by name."""
    inner = _nested_lists(node)
    if not inner:
        return {key: tuple(node)}
    twice = sorted(set(inner) & {k for k in document if isinstance(document[k], list)})
    if twice:
        raise ValueError(f"oracle container {twice} is both nested in {key} and top-level")
    return {sub: _list_ids(sub, items) for sub, items in inner.items()}


def groups_of(document: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    """``{container: ids}`` for the content-refusal containers of one oracle document."""
    groups: dict[str, tuple[str, ...]] = {}
    for key in _REFUSAL_KEYS:
        node = document.get(key)
        if isinstance(node, list):
            groups[key] = _list_ids(key, node)
        elif isinstance(node, dict):
            groups.update(_dict_form(key, node, document))
    return groups


@cache
def _oracle_groups(case: str, part: str = "") -> dict[str, tuple[str, ...]]:
    document = json.loads(oracle_path(case).read_text(encoding="utf-8"))
    return groups_of(document[part] if part else document)


def oracle_ids(step_id: str) -> dict[str, tuple[str, ...]]:
    """``{container: (oracle:<case>:<id>, ...)}`` for the step's oracles, prefix-filtered."""
    out: dict[str, tuple[str, ...]] = {}
    for spec in ORACLES.get(step_id, ()):
        for container, ids in _oracle_groups(spec.case, spec.part).items():
            kept = tuple(f"oracle:{spec.case}:{i}" for i in ids if i.startswith(spec.prefix))
            if kept:
                out[f"{spec.case}{'#' + spec.part if spec.part else ''}/{container}"] = kept
    return out


# O6-P18: checks the model cannot repair. An upstream-binding check (a stale or blocked bound input,
# a module that is not the bound one) is cured by a rerun, and the function takes no submission
# (a test proves it); a "limitations" function writes Python's own limitation text and refuses
# nothing is moved to NOT_ISSUE_SITES. Subtracted from what a rule must carry. {check: reason}.
UPSTREAM = "upstream binding: stale or blocked bound input; the remedy is a rerun, not a rewrite"
OWN_TEXT = "Python's own limitation text, not a refusal of anything the model wrote"
UNREADABLE = "source unreadable; the remedy is a new pack"
CLAIM_TEXT = "builds Python's claim text"
NON_CONTENT: Mapping[str, str] = {
    "fn:deploy_vii.cp2_synthesis:_provenance_issues": UPSTREAM,
    "fn:deploy_vii.cp2_synthesis:_stale_issues": UPSTREAM,
    "fn:deploy_vii.cp3_relative_value:_provenance_issues": UPSTREAM,
    "fn:deploy_vii.cp3_relative_value:_stale_issues": UPSTREAM,
    "fn:deploy_vii.cp4_legal:stale_issues": UPSTREAM,
    "fn:deploy_vii.cp6_committee:_provenance_issues": UPSTREAM,
    "fn:deploy_vii.cp6_committee:_stale_issues": UPSTREAM,
    "fn:deploy_workflow.owners.cp1c:_provenance_issues": UPSTREAM,
    "fn:deploy_workflow.owners.cp1c:_stale_issues": UPSTREAM,
    "fn:deploy_workflow.owners.cp1d:_provenance_issues": UPSTREAM,
    "fn:deploy_workflow.owners.cp1d:_stale_issues": UPSTREAM,
    "fn:deploy_workflow.owners.cp2a:_stale_issues": UPSTREAM,
    "fn:deploy_workflow.owners.cp2d:_provenance_issues": UPSTREAM,
    "fn:deploy_workflow.owners.cp2d:_stale_issues": UPSTREAM,
    "fn:deploy_workflow.owners.cp2g:stale_issues": UPSTREAM,
    "fn:deploy_workflow.owners.cp2h:stale_issues": UPSTREAM,
    "fn:deploy_workflow.owners.cp3c:_provenance_issues": UPSTREAM,
    "fn:deploy_workflow.owners.cp4c:stale_issues": UPSTREAM,
    # oracle ids (O6-P18a): a stale input, and a source the validator cannot read
    **{f"oracle:cp2a:{i}": UPSTREAM for i in ("v17",)},
    **{f"oracle:cp2g:{i}": UPSTREAM for i in ("v18", "v19", "v20")},
    **{f"oracle:cp2h:{i}": UPSTREAM for i in ("v17", "v18")},
    **{f"oracle:cp4c:{i}": UPSTREAM for i in ("v24", "v25", "v26", "v27")},
    "oracle:cp1d:r14": UNREADABLE,
    "oracle:cp1c:r11": UNREADABLE,
    "oracle:cp2h:s01": UNREADABLE,
    "oracle:cp2h:s02": UNREADABLE,
    "oracle:cp3-context:context-unreadable": UNREADABLE,
}

# Functions the site scan reaches that refuse nothing: Python's own limitation text, a truncation of
# an issue list, bound reference names. They are not content checks and not upstream binding, so
# the no-submission test does not apply. {check: reason}; the list may only shrink.
NOT_ISSUE_SITES: Mapping[str, str] = {
    "fn:deploy_vii.cp3_relative_value:Upstream.limits": OWN_TEXT,
    "fn:deploy_vii.cp3_relative_value:_evidence_limitations": OWN_TEXT,
    "fn:deploy_workflow.owners.cp1c:_bounded": "truncates an issue list (listed_issues)",
    "fn:deploy_workflow.owners.cp1d:_bounded": "truncates an issue list (listed_issues)",
    "fn:deploy_workflow.owners.cp3c:_names": "builds bound reference names",
    "fn:deploy_workflow.owners.cp3d:_single_dealer": OWN_TEXT,
    "fn:deploy_workflow.owners.cp8:_Composer._limitations": OWN_TEXT,
    "fn:deploy_workflow.owners.cp2g:_own_limitations": OWN_TEXT,
    "fn:deploy_workflow.owners.cp2d:_limitations": OWN_TEXT,
    "fn:deploy_workflow.owners.cp2d:_facility_limitations": OWN_TEXT,
    "fn:deploy_workflow.owners.cp3d:own_limitations": OWN_TEXT,
    "fn:deploy_workflow.owners.cp1c:_limitations": OWN_TEXT,
    "fn:deploy_workflow.owners.cp2h:_own_limitations": OWN_TEXT,
    "fn:deploy_workflow.owners.cp4c:_own_limitations": OWN_TEXT,
    "fn:deploy_workflow.owners.cp2e:own_limitations": "builds the step's own limitations text",
    **{
        f"fn:deploy_workflow.owners.{c}": CLAIM_TEXT
        for c in (
            "cp2d:_claims",
            "cp2e:_fx_claim",
            "cp2e:_hedge_claim",
            "cp2e:_rate_claims",
            "cp2g:_claims",
            "cp2h:_claims",
            "cp4c:_claims",
            "cpl10:_claims",
        )
    },
    "fn:deploy_workflow.owners.cpl10:_item_rows": "builds table rows",
    "fn:deploy_workflow.owners.cp3d:_Composer.missing_inputs": "builds the missing-inputs table",
    "fn:deploy_workflow.owners.cp2h:_with_upstream_citations": "builds derived-fact citations "
    "(a fail-closed invariant, no validator issue)",
    "fn:deploy_workflow.owners.cp8:_Composer._resolved": "spells resolved run text",
    "fn:deploy_workflow.owners.cp2d:check_cp1_totals": "builds a settled limitation, not a "
    "refusal (ruling 2D-d)",
    "fn:deploy_vii.readiness:absent_page_ranges": "derives absent page ranges from coverage text; "
    "refuses nothing (the citation check that uses them is the refusal)",
    "fn:deploy_workflow.owners.cp4c:_Book.cells": "settles lineage citations (a fail-closed "
    "invariant, no validator issue)",
}

# --- ast: issue sites reachable from the entry -----------------------------------------------


def module_path(module: str) -> Path:
    spec = importlib.util.find_spec(module)
    if spec is None or spec.origin is None:
        raise LookupError(f"module {module} not found")
    return Path(spec.origin)


def _source(module: str) -> tuple[str, ast.Module]:
    text = module_path(module).read_text(encoding="utf-8")
    return text, ast.parse(text)


def function_node(module: str, qualname: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """The definition of ``qualname`` (``f`` or ``Class.method``) in ``module``."""
    defs = _defs(_source(module)[1])
    if qualname not in defs:
        raise LookupError(f"{module}:{qualname} is not a function")
    return defs[qualname]


def core_sources(step_id: str) -> tuple[Path, ...]:
    """The source files of every module the step's entries live in."""
    return tuple(module_path(m) for m in sorted({e.split(":")[0] for e in ENTRIES[step_id]}))


def _defs(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every function by qualname: module level and methods (nested functions belong to their
    outermost function, so their sites count for it)."""
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    found[f"{node.name}.{item.name}"] = item
    return found


def _has_text(node: ast.AST) -> bool:
    return any(
        isinstance(n, ast.JoinedStr) or (isinstance(n, ast.Constant) and isinstance(n.value, str))
        for n in ast.walk(node)
    )


_SEQ = (ast.List, ast.Tuple, ast.ListComp, ast.GeneratorExp, ast.JoinedStr)
_STR_SEQUENCE = re.compile(
    r"^(tuple\[str, \.\.\.\]|list\[str\]|(Iterator|Iterable|Sequence|Generator)\[str.*\])$"
)
type _Function = ast.FunctionDef | ast.AsyncFunctionDef


def _has_prose(node: ast.AST) -> bool:
    """A sentence: an f-string or a string constant of two or more words (not a code or a key)."""
    return any(
        isinstance(n, ast.JoinedStr)
        or (isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value.split()) > 1)
        for n in ast.walk(node)
    )


def _named_issues(function: _Function) -> bool:
    return function.name.endswith(("_issues", "_problems"))


def _issue_like(function: _Function) -> bool:
    """A function that returns issues: named ``*_issues`` or ``*_problems``, or annotated to
    return a sequence or iterator of ``str``. A composer of other text is left out."""
    note = ast.unparse(function.returns) if function.returns else ""
    return _named_issues(function) or bool(_STR_SEQUENCE.match(note))


def _is_str(value: ast.AST | None) -> bool:
    """A string literal, an f-string or a ``+`` of them (adjacent literals are one constant)."""
    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
        return _is_str(value.left) and _is_str(value.right)
    return isinstance(value, ast.JoinedStr) or (
        isinstance(value, ast.Constant) and isinstance(value.value, str)
    )


def string_constants(tree: ast.Module) -> frozenset[str]:
    """Names assigned a string once at module level (plain or annotated, ``Final`` included).
    A compiled pattern, a tuple or a call result is not text."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and _is_str(node.value):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and _is_str(node.value)
        ):
            names.add(node.target.id)
    return frozenset(names)


def _texty(node: ast.AST, consts: frozenset[str]) -> bool:
    """Text: a literal anywhere in it, a bare module string constant, or ``CONST.format(...)``."""
    if _has_text(node):
        return True
    if isinstance(node, ast.Name):
        return node.id in consts
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in consts
    )


def _added(node: ast.AST, consts: frozenset[str] = frozenset()) -> bool:
    """An append, extend, add or ``+=`` of text to a collector."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return (
            node.func.attr in _ADDERS
            and ast.unparse(node.func.value) in _COLLECTORS
            and any(_texty(a, consts) for a in node.args)
        )
    return (
        isinstance(node, ast.AugAssign)
        and isinstance(node.op, ast.Add)
        and ast.unparse(node.target) in _COLLECTORS
        and _texty(node.value, consts)
    )


def _non_empty(node: ast.AST) -> bool:
    """A sequence or comprehension that holds something."""
    if isinstance(node, (ast.List, ast.Tuple)):
        return bool(node.elts)
    return isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.JoinedStr))


def _returned(node: ast.AST, *, prose: bool) -> bool:
    """A ``return`` or ``yield`` of a non-empty sequence; in a function not named for issues it
    must also hold a sentence."""
    if not isinstance(node, (ast.Return, ast.Yield)) or node.value is None:
        return False
    return any(
        isinstance(n, _SEQ) and _non_empty(n) and (not prose or _has_prose(n))
        for n in ast.walk(node.value)
    )


def _validation(node: ast.AST) -> bool:
    """``StepValidation(issues=<a literal sentence>)``."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "StepValidation"
        and any(k.arg == "issues" and _has_prose(k.value) for k in node.keywords)
    )


def _sites(function: _Function, consts: frozenset[str] = frozenset()) -> int:
    """Issue sites in one function. Coverage is per function: a new check inside a function a rule
    already carries is not seen here, only by the sha256 pins of the golden file (L2)."""
    returns, named = _issue_like(function), _named_issues(function)
    return sum(
        _added(n, consts) or _validation(n) or (returns and _returned(n, prose=not named))
        for n in ast.walk(function)
    )


def _name_edges(
    node: ast.Name, defs: Mapping[str, _Function], classes: frozenset[str]
) -> Iterator[str]:
    if node.id in defs:
        yield node.id
    elif node.id in classes:
        yield from (q for q in defs if q.startswith(node.id + "."))


def _attribute_edges(
    node: ast.Attribute, owner: str | None, defs: Mapping[str, _Function], classes: frozenset[str]
) -> Iterator[str]:
    if not isinstance(node.value, ast.Name):
        return
    holder = owner if node.value.id in ("self", "cls") else node.value.id
    if holder in classes and f"{holder}.{node.attr}" in defs:
        yield f"{holder}.{node.attr}"


def _edges(
    qualname: str,
    function: _Function,
    defs: Mapping[str, _Function],
    classes: frozenset[str],
) -> Iterator[str]:
    owner = qualname.split(".")[0] if "." in qualname else None
    for node in ast.walk(function):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            yield from _name_edges(node, defs, classes)
        elif isinstance(node, ast.Attribute):
            yield from _attribute_edges(node, owner, defs, classes)


def issue_functions(module: str, entry: str, source: str | None = None) -> dict[str, int]:
    """``{qualname: site count}`` for every function of ``module`` reachable from ``entry`` (a
    qualname) that holds at least one issue site. Reachability follows a name load or a ``self``
    attribute that resolves to a function or method of the same module. ``source`` replaces the
    module's text (the mutation probe)."""
    tree = ast.parse(source) if source is not None else _source(module)[1]
    defs = _defs(tree)
    if entry not in defs:
        raise LookupError(f"{module}:{entry} is not a function")
    classes = frozenset(n.name for n in tree.body if isinstance(n, ast.ClassDef))
    seen: set[str] = set()
    todo = [entry]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        todo.extend(_edges(name, defs[name], defs, classes))
    consts = string_constants(tree)
    counted = {name: _sites(defs[name], consts) for name in seen}
    return {name: n for name, n in sorted(counted.items()) if n}


def _composer_checks() -> set[str]:
    """What a ``compose.*`` rule carries (for example the pin lines of ``compose.O6``): a step's
    list does not repeat it."""
    return {c for rule in load_rules(COMPOSE) for c in rule.checks}


def site_checks(step_id: str, sources: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """The ``fn:`` checks the step's validator needs: every reachable function with a site, less
    the ``NON_CONTENT`` and ``NOT_ISSUE_SITES`` ones and what a ``compose.*`` rule carries. ``sources`` maps a module name to replacement text (the mutation probe)."""
    out: list[str] = []
    for entry in ENTRIES[step_id]:
        module, qualname = entry.split(":")
        found = issue_functions(module, qualname, (sources or {}).get(module))
        out.extend(f"fn:{module}:{q}" for q in found)
    excluded = set(NON_CONTENT) | set(NOT_ISSUE_SITES) | _composer_checks()
    return tuple(c for c in dict.fromkeys(out) if c not in excluded)


# --- CP-1B's code-defined refusals (it has no oracle) -----------------------------------------


def cp1b_sites() -> tuple[str, ...]:
    """CP-1B's refusal sites: the shape issue, the pair codes ``build_earnings_delta`` raises as
    ``ValueError`` (``_PERIOD_CODES``), the unsupported pair, the comparison assessment and the
    ``OwnerError`` code of the composer (``cp1b.py`` :176-192, :280-318)."""
    module = importlib.import_module(OWNERS + "cp1b")
    codes = sorted(module._PERIOD_CODES)
    return (
        "code:cp1b:shape",
        *(f"code:cp1b:period:{c}" for c in codes),
        "code:cp1b:unsupported_pair",
        "code:cp1b:comparison_assessment",
        "code:cp1b:owner_error",
    )


def needed_checks(step_id: str, sources: Mapping[str, str] | None = None) -> frozenset[str]:
    """Every check some rule must carry for the step: the issue-site functions reachable from its
    validator, every content refusal id of its oracles and, for CP-1B, its code-defined sites."""
    needed = set(site_checks(step_id, sources))
    for ids in oracle_ids(step_id).values():
        needed.update(i for i in ids if i not in NON_CONTENT)
    if step_id == CP1B_STEP:
        needed.update(cp1b_sites())
    return frozenset(needed)


def check_exists(check: str) -> bool:
    """Whether a check resolves: an AST function, an oracle id or a CP-1B code site."""
    kind, _, rest = check.partition(":")
    if kind == "fn":
        module, _, qualname = rest.rpartition(":")
        try:
            _, tree = _source(module)
        except (LookupError, ModuleNotFoundError):
            return False
        return qualname in _defs(tree)
    if kind == "oracle":
        case, _, ident = rest.partition(":")
        parts = {s.part for specs in ORACLES.values() for s in specs if s.case == case} or {""}
        try:
            return any(
                ident in ids for part in parts for ids in _oracle_groups(case, part).values()
            )
        except FileNotFoundError:
            return False
    if kind == "code":
        return check in cp1b_sites()
    return False


# --- the extractor ---------------------------------------------------------------------------


def _prose(step_id: str) -> str | None:
    """The rules a core states in prose: CP-L10's ``SCREEN_RULES`` and the ``rules`` of CP-1C's
    view (``_RULES_VIEW``)."""
    if step_id == "change_screen":
        return str(importlib.import_module(OWNERS + "cpl10").SCREEN_RULES)
    if step_id == "peer_benchmark":
        view = importlib.import_module(OWNERS + "cp1c")
        return json.dumps(
            {
                "minimum_included_peers": view.MIN_INCLUDED_PEERS,
                "outlier_fraction": str(view.OUTLIER_FRACTION),
                **view._RULES_VIEW,
            },
            sort_keys=True,
        )
    return None


def _fn_modules(names: tuple[str, ...]) -> set[Path]:
    """The source file of every module any ``fn:`` check of these lists names."""
    return {
        module_path(check.split(":")[1])
        for name in names
        for rule in load_rules(name)
        for check in rule.checks
        if check.startswith("fn:")
    }


def _pinned() -> tuple[list[Path], list[Path]]:
    """``(cores, oracles)``: the files the golden pins (a step's entry modules, each owner module,
    each module an ``fn:`` check names; each oracle file the checks read)."""
    names = (COMPOSE, *step_ids())
    cores = (
        {p for step in step_ids() for p in core_sources(step)}
        | {module_path(m) for m in OWNER_MODULE.values()}
        | _fn_modules(names)
    )
    oracles = {oracle_path(o.case) for specs in ORACLES.values() for o in specs}
    return sorted(cores), sorted(oracles)


def sha256_section() -> dict[str, dict[str, str]]:
    """The sha256 of every pinned core and oracle file."""
    cores, oracles = _pinned()
    return {
        "cores": {p.relative_to(ROOT).as_posix(): file_sha256(p) for p in cores},
        "oracles": {p.relative_to(ROOT).as_posix(): file_sha256(p) for p in oracles},
    }


class DirtyTree(RuntimeError):
    """A pinned file has uncommitted changes, so a golden taken now would pin text that no commit
    holds."""


def dirty_paths(paths: list[Path], root: Path = ROOT) -> list[str]:
    """The paths (relative to ``root``) with uncommitted changes against HEAD, staged or not."""
    relative = [p.relative_to(root).as_posix() for p in paths]
    done = subprocess.run(
        ["git", "diff", "HEAD", "--name-only", "--", *relative],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(done.stdout.split())


def _require_clean() -> None:
    cores, oracles = _pinned()
    dirty = dirty_paths([*cores, *oracles])
    if dirty:
        raise DirtyTree(
            "pinned files have uncommitted changes; commit them (or wait for their lane) first: "
            + ", ".join(dirty)
        )


def golden_document() -> dict[str, Any]:
    """The golden file: every rule (id, statement, checks) and the sha256 of every core and oracle
    file the checks read. Written once with ``json.dumps(golden_document(), indent=1)``; a removed
    or edited rule is then an explicit edit the review sees."""
    return {
        "rules": {
            name: [
                {"id": r.id, "statement": r.statement, "checks": list(r.checks)}
                for r in load_rules(name)
            ]
            for name in (COMPOSE, *step_ids())
        },
        "sha256": sha256_section(),
    }


def refresh_sha256(path: Path) -> None:
    """Rewrite only the ``sha256`` section of the golden file at ``path`` (O6-P20). The editing
    lane runs this after it changes a core and re-runs the coverage tests, in its own commit:
    ``python -c "from pathlib import Path; from deploy_workflow.prompts import rules;
    rules.refresh_sha256(Path('tests/prompts/rule_lists.golden.json'))"``. A change to a rule
    is not a refresh; it goes to the rule-list process. It refuses while any pinned file is dirty
    (G4)."""
    _require_clean()
    document = json.loads(path.read_text(encoding="utf-8"))
    document["sha256"] = sha256_section()
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def write_golden(path: Path) -> None:
    """Write the whole golden file (rules and sha256); refuses while any pinned file is dirty."""
    _require_clean()
    document = golden_document()
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def extract_checks(step_id: str) -> dict[str, Any]:
    """The draft ``rule_lists/<step>.json`` of a new step: one candidate rule per oracle refusal
    group, one rule for the issue-site functions (``fn:``), and, where the core states its rules
    in prose, one rule that carries that text as ``from_code``. Every ``statement`` is empty; the
    M5 agent completes them and moves checks between rules."""
    rules: list[dict[str, Any]] = []

    def add(checks: tuple[str, ...], from_code: str | None = None) -> None:
        entry: dict[str, Any] = {
            "id": f"{step_id}.{len(rules) + 1}",
            "statement": "",
            "checks": list(checks),
        }
        if from_code is not None:
            entry["from_code"] = from_code
        rules.append(entry)

    prose = _prose(step_id)
    if prose is not None:
        add((), prose)
    for ids in oracle_ids(step_id).values():
        if kept := tuple(i for i in ids if i not in NON_CONTENT):
            add(kept)
    if step_id == CP1B_STEP:
        add(cp1b_sites())
    fns = site_checks(step_id)
    if fns:
        add(fns)
    return {"step": step_id, "rules": rules}
