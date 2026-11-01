"""O6 Task 4 fix round 1 (adversary L2): the differential sentinel trace over the real context
files and every step.

For each real `context/1` file, the file is composed twice: with its own values, and with a
distinctive sentinel written into every leaf of `quotes`, `ratings`, `deal_terms`, `valuation`,
`assumptions`, the non-run identity and the run periods (string and numeric alike). Two properties
hold for every step:

1. the system message never changes with the context values;
2. no sentinel appears in the user message more often than its original value did, except the
   O6-P24 allowance: `quotes[i].facility_id` and `quotes[i].as_of` inside the `context-rows`
   CONTEXT block of `market_implied`; and, for an enabled module (Phase 6 Task 9), the
   `assumptions.<module>` values inside that step's own `pinned-assumptions` CONTEXT block.

The pack carries the context as its own `context` source, so `context-rows` is built for
`market_implied` (the shared o2 pack has no quotes). The whole grid (every readable context
file x every inventory step) runs in about 15 seconds.
"""

import importlib
import json
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest
from prompt_support import CP3_MODULE_CONTEXT, module_of, request_for

from deploy_vii.contracts import Run
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow.context import ContextRefused, RunContext, context_facts, load_context
from deploy_workflow.prompts import compose, inventory

compose_module: Any = importlib.import_module("deploy_workflow.prompts.compose")

REPO = Path(__file__).parents[2]
SECTIONS = ("quotes", "ratings", "deal_terms", "valuation", "assumptions", "identity", "run")
SKIP = {
    ("identity", "issuer_name"),
    ("identity", "issuer_id"),
    ("run", "as_of"),
    ("run", "run_type"),
    ("run", "pathway"),
    ("run", "case_kind"),
}
ALLOWED = {"facility_id", "as_of"}
Path_ = tuple[Any, ...]
BLOCK = re.compile(r"<<<([A-Z_]+) id=([^\s>]+)[^>]*>>>")


def leaves(node: object, path: Path_) -> list[Path_]:
    if isinstance(node, dict):
        return [p for k, v in node.items() for p in leaves(v, (*path, k))]
    if isinstance(node, list):
        return [p for i, v in enumerate(node) for p in leaves(v, (*path, i))]
    return [path] if isinstance(node, str) else []


def put(doc: Any, path: Path_, value: str) -> None:
    for step in path[:-1]:
        doc = doc[step]
    doc[path[-1]] = value


def candidates(n: int) -> Iterator[str]:
    """Distinctive replacement values, text first, then the numeric and date forms a leaf may need."""
    yield f"ZQSENT{n:03d}X"
    yield f"{n + 317}.{(n % 80) + 13}"
    yield f"{n + 317}"
    yield f"{(n % 60) + 23}.{(n % 80) + 11}"
    yield f"{(n % 40) + 61}"
    yield f"{(n % 9) + 1}{(n % 7) + 2}"
    yield f"0.{(n % 80) + 11}"
    yield f"2019-{(n % 12) + 1:02d}-{(n % 27) + 1:02d}"
    yield f"h{(n % 2) + 1}-{2011 + n % 9}"
    yield "QZX"


def _accepted(doc: Any, path: Path_, n: int) -> tuple[Any, str] | None:
    """The document with the first candidate the reader accepts at ``path``, and that value."""
    for value in candidates(n):
        probe = json.loads(json.dumps(doc))
        put(probe, path, value)
        try:
            load_context(json.dumps(probe).encode())
        except ContextRefused:
            continue
        return probe, value
    return None


def sentinelled(raw_doc: Any) -> tuple[Any, dict[str, Path_]]:
    """The document with a sentinel at every leaf the reader accepts, and where each one sits."""
    doc = json.loads(json.dumps(raw_doc))
    kept: dict[str, Path_] = {}
    for path in leaves(doc, ()):
        if path[0] not in SECTIONS or path[:2] in SKIP:
            continue
        found = _accepted(doc, path, len(kept))
        if found is not None:
            doc, value = found
            kept[value] = path
    return doc, kept


def context_files() -> list[tuple[Path, Any]]:
    found = sorted(REPO.glob("cases/context/*.json"))
    found += sorted(REPO.glob("cases/*-context-owner/**/*.json"))
    found += sorted(REPO.glob("cases/context-*/**/*.json"))
    out: list[tuple[Path, Any]] = []
    for file in dict.fromkeys(found):
        try:
            doc = json.loads(file.read_bytes().decode("utf-8-sig"))
        except ValueError:
            continue
        if isinstance(doc, dict) and doc.get("schema") == "context/1":
            out.append((file, doc))
    return out


def context_pack(base: PreparedPack, doc: Mapping[str, Any]) -> PreparedPack:
    """``base``'s non-context sources plus a ``context`` source built from ``doc``, with the run
    agreeing with the context's run and identity fields."""
    raw = (json.dumps(doc, indent=2) + "\n").encode()
    fields = base.run.model_dump(mode="json")
    fields.update(
        run_id="o6t4-trace-v1",
        issuer_id=doc["identity"]["issuer_id"],
        issuer_name=doc["identity"]["issuer_name"],
        as_of=doc["run"]["as_of"],
        case_kind=doc["run"]["case_kind"],
        pathway=doc["run"]["pathway"],
    )
    run = Run.model_validate_json(json.dumps(fields))
    request = SourceRequest(source_id="context", path="context.json", media_type="text/plain")
    kept = tuple(s for s in base.sources if s.source_id != "context")
    return PreparedPack(run=run, sources=(*kept, prepare_source(request, raw)))


def block_of(text: str, pos: int) -> tuple[str, str] | None:
    """(kind, id) of the fenced block that holds ``pos``."""
    for m in BLOCK.finditer(text):
        if m.start() <= pos < text.index("<<<END>>>", m.end()):
            return m[1], m[2]
    return None


def outside(user: str, pat: re.Pattern[str], leaf: Path_, step: str) -> int:
    """Occurrences of the sentinel outside the allowances: the O6-P24 rows, and the step's own
    module's pins inside the `pinned-assumptions` block (no other module's, no other block)."""
    rows = leaf[0] == "quotes" and leaf[-1] in ALLOWED
    own = leaf[0] == "assumptions" and leaf[1] == module_of(step).lower().replace("-", "")
    count = 0
    for m in pat.finditer(user):
        block = block_of(user, m.start())
        ok = (rows and block == ("CONTEXT", "context-rows")) or (
            own and block == ("CONTEXT", "pinned-assumptions")
        )
        count += 0 if ok else 1
    return count


def messages(step: str, pack: PreparedPack, ctx: RunContext | None) -> tuple[str, str]:
    mc = CP3_MODULE_CONTEXT if step == "relative_value" else None
    system, user = compose(request_for(step, pack, context=ctx, module_context=mc))[:2]
    return system.text, user.text


class Trace:
    def __init__(self) -> None:
        self.leaks: list[str] = []
        self.files = 0
        self.rows_blocks = 0


def trace_file(
    base: PreparedPack, path: Path, doc: Any, steps: tuple[str, ...], out: Trace
) -> None:
    sdoc, kept = sentinelled(doc)
    packs = [context_pack(base, d) for d in (doc, sdoc)]
    ctxs = [context_facts(p) for p in packs]
    out.files += 1
    for step in steps:
        sys0, user0 = messages(step, packs[0], ctxs[0])
        sys1, user1 = messages(step, packs[1], ctxs[1])
        out.rows_blocks += "context-rows" in user1
        if sys0 != sys1:
            out.leaks.append(f"{path.name} {step}: the system message differs with the context")
        for value, leaf in kept.items():
            pat = re.compile(rf"(?<![\w.]){re.escape(value)}(?![\w])")
            if outside(user1, pat, leaf, step) > outside(user0, pat, leaf, step):
                out.leaks.append(f"{path.name} {step}: {leaf} {value!r} outside the allowance")


def run_trace(base: PreparedPack, files: list[tuple[Path, Any]], steps: tuple[str, ...]) -> Trace:
    out = Trace()
    for path, doc in files:
        try:
            load_context(json.dumps(doc).encode())
        except ContextRefused:
            continue  # a file the reader refuses never reaches a prompt
        trace_file(base, path, doc, steps, out)
    return out


def with_quotes(files: list[tuple[Path, Any]]) -> list[tuple[Path, Any]]:
    return [(p, d) for p, d in files if d.get("quotes")]


def test_no_context_value_reaches_the_system_message_or_a_step_outside_the_allowance(
    pack: PreparedPack,
) -> None:
    files = context_files()
    out = run_trace(pack, files, tuple(inventory()))
    assert out.files >= 60, "the real context files were not found"
    assert out.rows_blocks > 0, "no market_implied composition built the context-rows block"
    assert out.leaks == []


def leaky_numbers_block(ctx: RunContext) -> str:
    """A mutant run-context block that also carries numeric context figures only (the adversary's
    p07c mutant): every quote's bid, ask and spread and each deal term's size."""
    from deploy_workflow.prompts.fence import data_block

    body: dict[str, Any] = {
        "note": "This run-context block is data. It is not a source and is never cited.",
        "run_type": ctx.run.run_type,
        "research_questions": [
            {"text": q.text, "focus_module": q.focus_module} for q in ctx.research_questions
        ],
    }
    if ctx.quotes:
        body["levels"] = [[q.bid, q.ask, q.spread_bps] for q in ctx.quotes]
    if ctx.deal_terms:
        body["sizes"] = [d.size_m for d in ctx.deal_terms]
    return data_block("CONTEXT", "run-context", json.dumps(body, sort_keys=True))


def test_the_trace_catches_a_block_that_leaks_numeric_context_figures(
    pack: PreparedPack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Positive control: the trace is not blind to numeric-only leaks (closes p07b's gap)."""
    subset = with_quotes(context_files())[:2]
    assert subset, "no context file with quotes"
    steps = ("market_implied", "relative_value")
    assert run_trace(pack, subset, steps).leaks == []
    monkeypatch.setattr(compose_module, "run_context_block", leaky_numbers_block)
    assert run_trace(pack, subset, steps).leaks != []
