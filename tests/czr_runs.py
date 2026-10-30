"""CZR 2026 Q2 public real-data case: pack assembly and the closed CP-1 run driver.

The pack holds the three filed documents of `cases/czr-2026q2-earnings-update` as one source
each; `Source.sha256` is the sha256 of the document file (the hash in `qualification.json`
and `manifest.json`), never a hash of the spans.

PAGE RULE (word for word; Workflow Test writes `page:N` locators from it alone)

    Read a document's bytes as UTF-8 and split at every "\\n" (the files have no form feeds
    and no "\\r"); the final empty piece after the last "\\n" is dropped. The pieces are the
    lines, numbered from 1. A page starts at line 1 and at every line that
      (a) directly follows a line matching ^[0-9]{1,3}$ (a printed page number: one to three
          digits and nothing else on the line, so the page-number line ends its page), or
      (b) is itself a statement heading, a line matching
          ^CONSOLIDATED (CONDENSED )?(BALANCE SHEETS|STATEMENTS OF OPERATIONS|STATEMENTS OF CASH FLOWS)$
          (a heading line that already starts a page by (a) or by being line 1 starts no
          extra page).
    Pages are numbered 1, 2, 3, ... in order of their first line, and the locator is
    "page:N". A page's text is its lines joined by "\\n" (no trailing "\\n"). A page spans
    from its first line up to the line before the next page's first line (the last page
    ends at the last line). The rule is applied to each document separately: the same
    locator in two documents names two different pages, told apart by `source_id`.

Source ids and names come from `manifest.json`. `czr_closed` needs the recorded submissions
`cases/czr-2026q2-earnings-update/submissions.json`, which Workflow Test owns; nothing here
asserts expected values or stands in for a missing submission. The run is item 70: CP-0, CP-1,
CP-1A, CP-2, CP-5 (`requested_modules` CP-1, CP-2, CP-5; CP-1B is not run). Its format is one
object `{"stages": [...], "figures": {...}}`, one stage per step of the run in plan order;
`figures` is optional:

    {"step": "<step id>",
     "calls": [{"tool": "read_pages" | "search_pack" | "extract_statements",
                "arguments": {...}}
               | {"tool": "read_inputs"}, ...],
     "submission": <the step's JSON submission>}

    "figures": {"<name>": {"module_id", "table_id", "period", "label", "unit_token", "spelled"}}

The calls run in order. A tool call must return status ok. `{"tool": "read_inputs"}` (no
`arguments`) calls `workflow.read_inputs()`; it has no status and must not raise: the workflow
raises `WorkflowError` when it refuses (a step whose spec declares `inputs` "none", a wrong
phase, a call limit), the driver does not catch it, and the raise ends the run. Its parsed
`body` is the stage's read body: a JSON object, or, when the body is not a JSON object (the
CP-1 `projection` text), no read body. Every step whose spec declares `inputs` other than
"none" must have made this call before its submission, else the run raises naming it.

A `{{FIG:name}}` token in a stage's submission is replaced by `{<fact_id>|<unit_token>}`. The
fact is the one fact of the settled head (accepted or restricted) of the figure's `module_id`
whose `table_id`, `period` and `label` all equal the selector. It must be a `ref` of the stage's
read body (refs are collected from every list of `{ref, unit, shown, ...}` entries of the JSON
object; one ref shown two ways raises) with the selector's `unit_token` and `spelled`. A token
in a stage with no JSON-object read body (every CP-1 step), an unknown name, zero or several
candidates, or a mismatch raises naming the figure; nothing falls back. Then the one run-time
token `PACK_PLACEHOLDER` is replaced by `PreparedPack.content_hash()` and the submission must be
valid.

A stage whose `step` is not the run's current step, a missing or extra stage, or a call or
submission that is refused raises. After the last stage the model is published and the receipt
is sealed at `<root>/owner-receipt.json`.
"""

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from s1a_runs import FIG, PACK_PLACEHOLDER, figure_names, finish, submit_valid

from deploy_vii.contracts import Coverage, Fact, Run, Source, Span
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/czr-2026q2-earnings-update"
SUBMISSIONS = CASE / "submissions.json"
RUN_ID = "czr-2026q2-earnings-update-v1"
PAGE_NUMBER = re.compile(r"[0-9]{1,3}")
STATEMENT_HEADING = re.compile(
    r"CONSOLIDATED (?:CONDENSED )?(?:BALANCE SHEETS|STATEMENTS OF OPERATIONS"
    r"|STATEMENTS OF CASH FLOWS)"
)


def manifest() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
    return data


def pages(raw: bytes) -> list[str]:
    """The pages of one document's bytes under the PAGE RULE (module docstring); page N is
    element N-1."""
    lines = raw.decode("utf-8").split("\n")
    if lines[-1] == "":
        lines.pop()
    pages: list[list[str]] = []
    for number, line in enumerate(lines):
        starts = (
            number == 0
            or PAGE_NUMBER.fullmatch(lines[number - 1]) is not None
            or STATEMENT_HEADING.fullmatch(line) is not None
        )
        if starts:
            pages.append([])
        pages[-1].append(line)
    return ["\n".join(page) for page in pages]


def make_pack() -> PreparedPack:
    """The run and the three documents, each paged by `pages`; a document whose bytes differ
    from the manifest hash raises."""
    data = manifest()
    sources = []
    for item in data["documents"]:
        raw = (CASE / item["path"]).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != item["sha256"]:
            raise RuntimeError(f"document hash drift: {item['path']}")
        spans = tuple(Span(locator=f"page:{n}", text=t) for n, t in enumerate(pages(raw), 1))
        sources.append(
            Source(
                source_id=item["source_id"],
                name=item["document_type"],
                status="ready",
                sha256=digest,
                media_type="text/plain",
                spans=spans,
                extractor="filed-text-pages",
                extraction_status="complete",
                coverage=tuple(Coverage(locator=s.locator, status="retained") for s in spans),
            )
        )
    fixed = data["run"]
    run = Run.model_validate_json(
        json.dumps(
            {
                "run_id": RUN_ID,
                "issuer_id": fixed["issuer_id"],
                "issuer_name": fixed["issuer_name"],
                "as_of": fixed["as_of"],
                "case_kind": "public",
                "pathway": "earnings_update",
                "requested_modules": ["CP-1", "CP-2", "CP-5"],
            }
        )
    )
    return PreparedPack(run=run, sources=tuple(sources))


def _read_refs(read_body: Mapping[str, Any]) -> dict[str, tuple[Any, Any]]:
    """ref -> (unit, shown) over every list of `{ref, ...}` entries in the read body."""
    refs: dict[str, tuple[Any, Any]] = {}
    for value in read_body.values():
        if not isinstance(value, list):
            continue
        for entry in value:
            if not isinstance(entry, dict) or "ref" not in entry:
                continue
            shown = (entry.get("unit"), entry.get("shown"))
            if refs.setdefault(entry["ref"], shown) != shown:
                raise RuntimeError(f"read body ref {entry['ref']} is shown two ways")
    return refs


def _figure_fact(facts: tuple[Fact, ...], name: str, selector: Mapping[str, Any]) -> Fact:
    hits = [
        f
        for f in facts
        if (f.table_id, f.period, f.label)
        == (selector["table_id"], selector["period"], selector["label"])
    ]
    if len(hits) != 1:
        raise RuntimeError(f"FIG {name}: {len(hits)} candidate facts, expected exactly one")
    return hits[0]


def bind_stage_figures(
    text: str,
    figures: Mapping[str, Mapping[str, Any]],
    read_body: Mapping[str, Any] | None,
    facts_of: Callable[[str], tuple[Fact, ...]],
) -> str:
    """Replace each `{{FIG:name}}` in `text` by `{<fact_id>|<unit_token>}` under the figure
    rule in the module docstring; any failure raises naming the figure."""
    bound: dict[str, str] = {}
    refs: dict[str, tuple[Any, Any]] | None = None
    for name in figure_names(text):
        selector = figures.get(name)
        if selector is None:
            raise RuntimeError(f"FIG {name}: not in the submissions figures")
        if read_body is None:
            raise RuntimeError(f"FIG {name}: the stage has no JSON-object read body")
        if refs is None:
            refs = _read_refs(read_body)
        fact = _figure_fact(facts_of(selector["module_id"]), name, selector)
        shown = refs.get(fact.fact_id)
        if shown is None:
            raise RuntimeError(f"FIG {name}: {fact.fact_id} is not a ref of the read body")
        if shown != (selector["unit_token"], selector["spelled"]):
            raise RuntimeError(f"FIG {name}: unit/shown {shown[0]}/{shown[1]}")
        bound[name] = "{" + fact.fact_id + "|" + selector["unit_token"] + "}"
    return FIG.sub(lambda m: bound[m[1]], text)


def require_read(step: str, inputs: str, *, read_made: bool) -> None:
    """A step whose spec declares `inputs` other than "none" must have called read_inputs."""
    if inputs != "none" and not read_made:
        raise RuntimeError(f"step {step!r} declares inputs {inputs!r}: read_inputs not called")


def _settled_facts(workflow: OwnerWorkflow) -> Callable[[str], tuple[Fact, ...]]:
    def facts_of(module_id: str) -> tuple[Fact, ...]:
        store = workflow._store
        heads = [
            h
            for h in store.read().heads
            if h.module_id == module_id and h.status in ("accepted", "restricted")
        ]
        if len(heads) != 1:
            raise RuntimeError(f"{len(heads)} settled heads for {module_id}, expected one")
        return store.head_module(heads[0]).facts

    return facts_of


def _read_body(done: Mapping[str, Any]) -> dict[str, Any] | None:
    """The parsed read body when it is a JSON object, else None (a text-only body)."""
    try:
        body = json.loads(done["body"])
    except json.JSONDecodeError:
        return None
    return body if isinstance(body, dict) else None


def czr_closed(root: Path, submissions_path: Path = SUBMISSIONS) -> tuple[Path, Path, Path]:
    """One closed item 70 run of the CZR pack under `root`: (store, sealed receipt,
    publication). Raises FileNotFoundError naming the submissions file while it is missing."""
    if not submissions_path.is_file():
        raise FileNotFoundError(f"CZR recorded submissions not found: {submissions_path}")
    data = json.loads(submissions_path.read_text(encoding="utf-8"))
    stages = data["stages"]
    figures = data.get("figures", {})
    pack = make_pack()
    workflow = OwnerWorkflow.create(root / "store", pack, publication_directory=root / "model")
    facts_of = _settled_facts(workflow)
    for stage in stages:
        current = workflow._binding.step_id
        if stage["step"] != current:
            raise RuntimeError(f"submissions stage {stage['step']!r} but the run is at {current!r}")
        read_made = False
        read_body: dict[str, Any] | None = None
        for call in stage["calls"]:
            if call["tool"] == "read_inputs":
                read_body = _read_body(workflow.read_inputs())
                read_made = True
                continue
            done = workflow.invoke(call["tool"], call["arguments"])
            if done["status"] != "ok":
                raise RuntimeError(f"{current} {call['tool']}: {done['error_code']}")
        require_read(current, workflow._spec.inputs, read_made=read_made)
        payload = json.dumps(stage["submission"], ensure_ascii=False)
        payload = bind_stage_figures(payload, figures, read_body, facts_of)
        submit_valid(workflow, payload.replace(PACK_PLACEHOLDER, pack.content_hash()))
    finish(workflow, root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json", root / "model"
