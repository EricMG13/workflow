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
asserts expected values or stands in for a missing submission. Its format is one object
`{"stages": [...]}`, one stage per step of the run in plan order (CP-0 `source_readiness`, then
CP-1 `source_context`, `financials`, `narrative`, `readiness`, `quality`):

    {"step": "<step id>",
     "calls": [{"tool": "read_pages" | "search_pack" | "extract_statements",
                "arguments": {...}}, ...],
     "submission": <the step's JSON submission>}

The calls run in order and each must return status ok; then the submission, with the one
run-time token `PACK_PLACEHOLDER` replaced by `PreparedPack.content_hash()`, must be valid.
A stage whose `step` is not the run's current step, a missing or extra stage, or a call or
submission that is refused raises. After the last stage the model is published and the receipt
is sealed at `<root>/owner-receipt.json`.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from s1a_runs import PACK_PLACEHOLDER, finish, submit_valid

from deploy_vii.contracts import Coverage, Run, Source, Span
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/czr-2026q2-earnings-update"
SUBMISSIONS = CASE / "submissions.json"
RUN_ID = "czr-2026q2-earnings-update-cp1-v1"
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
                "requested_modules": ["CP-1"],
            }
        )
    )
    return PreparedPack(run=run, sources=tuple(sources))


def czr_closed(root: Path) -> tuple[Path, Path, Path]:
    """One closed CP-1 run of the CZR pack under `root`: (store, sealed receipt, publication).
    Raises FileNotFoundError naming `submissions.json` while Workflow Test has not written it."""
    if not SUBMISSIONS.is_file():
        raise FileNotFoundError(f"CZR recorded submissions not found: {SUBMISSIONS}")
    stages = json.loads(SUBMISSIONS.read_text(encoding="utf-8"))["stages"]
    pack = make_pack()
    workflow = OwnerWorkflow.create(root / "store", pack, publication_directory=root / "model")
    for stage in stages:
        current = workflow._binding.step_id
        if stage["step"] != current:
            raise RuntimeError(f"submissions stage {stage['step']!r} but the run is at {current!r}")
        for call in stage["calls"]:
            done = workflow.invoke(call["tool"], call["arguments"])
            if done["status"] != "ok":
                raise RuntimeError(f"{current} {call['tool']}: {done['error_code']}")
        payload = json.dumps(stage["submission"], ensure_ascii=False)
        submit_valid(workflow, payload.replace(PACK_PLACEHOLDER, pack.content_hash()))
    finish(workflow, root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json", root / "model"
