"""O6 Task 3: the rule lists and the coverage oracle's extractor.

A rule is ``{"id": "<step>.<n>", "statement": str, "checks": [...]}``. ``statement`` is the
sentence the prompt must carry; ``checks`` name what enforces it, in three kinds (O6-P11):

* ``fn:<module>:<qualname>``: a function of a validator core that holds issue sites;
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
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

__all__ = [
    "COMPOSE",
    "Rule",
    "check_exists",
    "core_sources",
    "extract_checks",
    "file_sha256",
    "golden_document",
    "issue_functions",
    "load_rules",
    "module_path",
    "needed_checks",
    "oracle_ids",
    "oracle_path",
    "rule_ids",
    "step_ids",
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


def _rule(raw: Mapping[str, object]) -> Rule:
    checks = raw["checks"]
    assert isinstance(checks, list)
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
    return tuple(_rule(raw) for raw in document["rules"])


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
    keeps only the ids that begin with it (cp3-cp6 serves two steps)."""

    case: str
    prefix: str = ""


ORACLES: Mapping[str, tuple[OracleSpec, ...]] = {
    "relative_value": (OracleSpec("cp3-cp6", "cp3-"), OracleSpec("cp3-context")),
    "committee_challenge": (OracleSpec("cp3-cp6", "cp6-"),),
    "integrity_review": (OracleSpec("cp5"),),
    "research": (OracleSpec("cpdr"),),
    "market_implied": (OracleSpec("cp3d"),),
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


@cache
def _oracle_groups(case: str) -> dict[str, tuple[str, ...]]:
    """``{container: ids}`` for the content-refusal containers of one oracle, in file order."""
    document = json.loads(oracle_path(case).read_text(encoding="utf-8"))
    groups: dict[str, tuple[str, ...]] = {}
    for key in _REFUSAL_KEYS:
        node = document.get(key)
        if isinstance(node, list):
            groups[key] = tuple(i["id"] for i in node if isinstance(i, dict) and "id" in i)
        elif isinstance(node, dict):
            inner = {k: v for k, v in node.items() if k in _REFUSAL_KEYS and isinstance(v, list)}
            if inner:
                for sub, items in inner.items():
                    groups[sub] = tuple(i["id"] for i in items)
            else:
                groups[key] = tuple(node)
    return groups


def oracle_ids(step_id: str) -> dict[str, tuple[str, ...]]:
    """``{container: (oracle:<case>:<id>, ...)}`` for the step's oracles, prefix-filtered."""
    out: dict[str, tuple[str, ...]] = {}
    for spec in ORACLES.get(step_id, ()):
        for container, ids in _oracle_groups(spec.case).items():
            kept = tuple(f"oracle:{spec.case}:{i}" for i in ids if i.startswith(spec.prefix))
            if kept:
                out[f"{spec.case}/{container}"] = kept
    return out


# --- ast: issue sites reachable from the entry -----------------------------------------------


def module_path(module: str) -> Path:
    spec = importlib.util.find_spec(module)
    if spec is None or spec.origin is None:
        raise LookupError(f"module {module} not found")
    return Path(spec.origin)


def _source(module: str) -> tuple[str, ast.Module]:
    text = module_path(module).read_text(encoding="utf-8")
    return text, ast.parse(text)


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


def _sites(function: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    count = 0
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _ADDERS
            and ast.unparse(node.func.value) in _COLLECTORS
            and any(_has_text(a) for a in node.args)
        ) or (
            isinstance(node, ast.AugAssign)
            and isinstance(node.op, ast.Add)
            and ast.unparse(node.target) in _COLLECTORS
            and _has_text(node.value)
        ):
            count += 1
    return count


def _edges(
    qualname: str,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    defs: Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef],
    classes: frozenset[str],
) -> Iterator[str]:
    owner = qualname.split(".")[0] if "." in qualname else None
    for node in ast.walk(function):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id in defs:
                yield node.id
            elif node.id in classes:
                yield from (q for q in defs if q.startswith(node.id + "."))
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            holder = owner if node.value.id in ("self", "cls") else node.value.id
            if holder in classes and f"{holder}.{node.attr}" in defs:
                yield f"{holder}.{node.attr}"


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
    counted = {name: _sites(defs[name]) for name in seen}
    return {name: n for name, n in sorted(counted.items()) if n}


def site_checks(step_id: str, sources: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """The ``fn:`` checks the step's validator needs: every reachable function with a site.
    ``sources`` maps a module name to replacement text (the mutation probe)."""
    out: list[str] = []
    for entry in ENTRIES[step_id]:
        module, qualname = entry.split(":")
        found = issue_functions(module, qualname, (sources or {}).get(module))
        out.extend(f"fn:{module}:{q}" for q in found)
    return tuple(dict.fromkeys(out))


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
        needed.update(ids)
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
        try:
            groups = _oracle_groups(case)
        except FileNotFoundError:
            return False
        return any(ident in ids for ids in groups.values())
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


def golden_document() -> dict[str, Any]:
    """The golden file: every rule (id, statement, checks) and the sha256 of every core and oracle
    file the checks read. Written once with ``json.dumps(golden_document(), indent=1)`` into
    ``tests/prompts/rule_lists.golden.json``; a removed or edited rule is then an explicit edit."""
    names = (COMPOSE, *step_ids())
    cores = sorted(
        {p for step in step_ids() for p in core_sources(step)}
        | {module_path(OWNER_MODULE[s]) for s in OWNER_MODULE}
    )
    oracles = sorted({oracle_path(o.case) for specs in ORACLES.values() for o in specs})
    return {
        "rules": {
            name: [
                {"id": r.id, "statement": r.statement, "checks": list(r.checks)}
                for r in load_rules(name)
            ]
            for name in names
        },
        "sha256": {
            "cores": {p.relative_to(ROOT).as_posix(): file_sha256(p) for p in cores},
            "oracles": {p.relative_to(ROOT).as_posix(): file_sha256(p) for p in oracles},
        },
    }


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
        add(ids)
    if step_id == CP1B_STEP:
        add(cp1b_sites())
    fns = site_checks(step_id)
    if fns:
        add(fns)
    return {"step": step_id, "rules": rules}
