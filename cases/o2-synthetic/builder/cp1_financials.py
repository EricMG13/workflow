"""Re-cut the CP-1 tool-loop financials stage of the financial slice to the o2-synthetic pack (B22).

    PYTHONPATH=src:tests .venv/bin/python cases/o2-synthetic/builder/cp1_financials.py [--out DIR]

Writes (default DIR = cases/o2-synthetic; the inputs are always read from there) `cp1-financials.json` and adds the `cp1_tool_loop` entry
and `status` to `manifest.json` (every other manifest field is left as it is; `build.py` is not
run and the frozen files are not rewritten). Deterministic: two runs write byte-identical files.

- `tool_calls`: the o2 image of `tests/test_financial_workflow.py` `financial_reads`: one
  `extract_statements` call over the statement units `_statement_units` derives from the pack's
  `line:N` spans, the `read_pages` calls over the lines of the source pages 1 and 5 (the pages that
  call reads, in runs of at most `MAX_PAGES_PER_READ`) and the same `search_pack` call.
- `submission`: `financials(pack)` of that file called on the o2 pack, each citation's `page:N`
  replaced by its own `line:K` (an exact `quoted` match of the quote inside the lines of the old
  page) and each source hash by the pack's. Nothing else is changed. A quote that matches no line
  or more than one line inside its old page stops the build (nothing is written).

Narrative, readiness and quality are not re-cut: they are functions of the run's read inputs.
"""

import argparse
import hashlib
import importlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests"), str(HERE)]

import build

from deploy_vii.live.tools import MAX_PAGES_PER_READ
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare
from deploy_vii.quotes import quoted
from deploy_workflow.context import load_context, preparation_request
from deploy_workflow.financial_workflow import _statement_units

CASE = build.CASE
SOURCE_FUNCTION = (
    "tests/test_financial_workflow.py financials(pack); reads: financial_reads(workflow)"
)
MAPPING_RULE = (
    "financials(o2 pack) with each citation's page:N replaced by the line:K of the prepared pack "
    "whose span holds the quote (quotes.quoted), searched only inside the lines of that page of the "
    "frozen source (cases/financial/manifest.json), exactly one match required; source_sha256 "
    "replaced by the pack's file-bytes hash; no value, id, status or number changed"
)
READ_PAGES = (1, 5)  # the source pages financial_reads reads
SEARCH = {"query": "not disclosed", "source_id": "financial"}


def load_pack_of_case() -> tuple[PreparedPack, dict[str, str]]:
    context_raw = (CASE / "context.json").read_bytes()
    request = preparation_request(
        load_context(context_raw),
        run_id=build.RUN_ID,
        context_path="context.json",
        sources=[
            SourceRequest(source_id=k, path=f"{k}.txt", media_type="text/plain")
            for k in build.SOURCE_ORDER
        ],
    )
    with tempfile.TemporaryDirectory() as scratch:
        pack = prepare(request, CASE, Path(scratch) / "pack")
    manifest = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
    if pack.content_hash() != manifest["run"]["pack_sha256"]:
        raise RuntimeError("the prepared pack is not the manifest's pack")
    return pack, {s.source_id: s.sha256 or "" for s in pack.sources}


class StrictRecut(build.Recut):
    """`build.Recut` that never chooses: a quote with no match or with several inside its old page
    is recorded and the build stops after the walk."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.missing: list[str] = []
        self.pairs: dict[tuple[str, str, str, str], int] = {}

    def citation(self, node: dict[str, Any]) -> None:
        source_id, old, quote = node["source_id"], node["locator"], node["quote"]
        first, last = self.ranges[source_id][old]
        found = [
            n for n in range(first, last + 1) if quoted(quote, self.lines[source_id][f"line:{n}"])
        ]
        if not found:
            self.missing.append(f"{source_id} {old}: {quote!r}")
            return
        if len(found) > 1:
            self.ambiguous.append(f"{source_id} {old} -> lines {found}: {quote!r}")
            return
        node["locator"] = f"line:{found[0]}"
        if node["source_sha256"] != self.pages[source_id]["sha256"]:
            raise RuntimeError(f"{source_id}: citation hash is not the oracle's")
        node["source_sha256"] = self.hashes[source_id]
        self.citations += 1
        key = (source_id, old, node["locator"], quote)
        self.pairs[key] = self.pairs.get(key, 0) + 1


def tool_calls(pack: PreparedPack, ranges: dict[str, tuple[int, int]]) -> list[dict[str, Any]]:
    financial = next(s for s in pack.sources if s.source_id == "financial")
    units = list(_statement_units(financial.spans))
    calls: list[dict[str, Any]] = [
        {
            "tool": "extract_statements",
            "arguments": {"source_id": "financial", "locators": units},
        }
    ]
    for page in READ_PAGES:
        first, last = ranges[f"page:{page}"]
        for start in range(first, last + 1, MAX_PAGES_PER_READ):
            calls.append(
                {
                    "tool": "read_pages",
                    "arguments": {
                        "source_id": "financial",
                        "first_page": start,
                        "last_page": min(start + MAX_PAGES_PER_READ - 1, last),
                    },
                }
            )
    calls.append({"tool": "search_pack", "arguments": dict(SEARCH)})
    return calls


def build_cp1(out_dir: Path) -> None:
    pack, hashes = load_pack_of_case()
    pages = build.source_pages()
    fw = importlib.import_module("test_financial_workflow")
    # the source payload shares citation dicts between rows; unshare them so each is cut once
    submission = json.loads(json.dumps(fw.financials(pack)))
    recut = StrictRecut(pages, pack, hashes)
    submission = recut.walk(submission)
    if recut.missing or recut.ambiguous:
        raise RuntimeError(
            "quote matches not unique, nothing written:\n"
            + "\n".join([*("missing " + m for m in recut.missing), *recut.ambiguous])
        )
    left = json.dumps(submission).count('"page:')
    if left:
        raise RuntimeError(f"{left} page:N locators remain")
    matches = [
        {"source_id": s, "from": old, "to": new, "quote": q, "uses": n}
        for (s, old, new, q), n in sorted(recut.pairs.items())
    ]
    document = {
        "schema_version": "o2-synthetic-cp1-financials/1",
        "note": (
            "CP-1 tool-loop financials stage of the financial slice re-cut to line:N locators and "
            "file hashes of the o2-synthetic pack. Narrative, readiness and quality are not re-cut "
            "(computed from the run's read inputs). Values, ids and statuses are the source "
            "payload's."
        ),
        "run_id": build.RUN_ID,
        "pack_sha256": pack.content_hash(),
        "source_function": SOURCE_FUNCTION,
        "tool_calls": tool_calls(pack, build.page_line_ranges(pages["financial"])),
        "submission": submission,
        "citations_recut": recut.citations,
        "ambiguous_line_matches": [],
        "missing_line_matches": [],
        "matches": matches,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "cp1-financials.json"
    target.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
    manifest["status"] = (
        "S1, CP-3, CP-5, CP-6 submissions, sources and context frozen (9de132e7, cases/PINS.json); "
        "cp1-financials.json reviewed (mx-precise a0d99f61) and frozen"
    )
    manifest["cp1_tool_loop"] = {
        "file": "cp1-financials.json",
        "sha256": digest,
        "source_function": SOURCE_FUNCTION,
        "mapping_rule": MAPPING_RULE,
        "tool_calls": "o2 image of financial_reads: extract_statements over the derived statement "
        "units, read_pages over the lines of source pages 1 and 5, the same search_pack",
        "not_re_cut": "narrative, readiness and quality: computed from the run's read inputs as "
        "tests/s1a_runs.py drive_cp1 does",
        "citations_recut": recut.citations,
        "ambiguous_line_matches": [],
        "script": "cases/o2-synthetic/builder/cp1_financials.py",
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=CASE)
    build_cp1(parser.parse_args().out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
