"""Re-cut the frozen S1 / CP-3 / CP-5 / CP-6 portfolio_decision oracle to a `prepare`d pack.

    PYTHONPATH=src .venv/bin/python cases/o2-synthetic/builder/build.py [--out DIR]

Writes (default DIR = cases/o2-synthetic): identity.txt, financial.txt, business.txt, market.txt,
context.json, submissions.json, manifest.json. Everything is derived from the pinned source
oracles; the only generated values are locators (`page:N` -> `line:N`), source hashes (page-joined
-> file bytes), the pack hash, run_id, and the added rows named in `manifest.json`.
Deterministic: two runs write byte-identical files.
"""

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from deploy_vii.business_context import cp1a_consumers
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare
from deploy_vii.quotes import quoted
from deploy_vii.readiness import (
    ReadinessReview,
    validate_review,
)
from deploy_vii.source_context import SourceContextReview, validate_source_context
from deploy_workflow.context import load_context, preparation_request

CASE = ROOT / "cases" / "o2-synthetic"
RUN_ID = "o2-synthetic-portfolio-decision"
PATHWAY = "portfolio_decision"
PLACEHOLDER_PREFIX = "<<PACK_SHA256"
SOURCE_ORDER = ("identity", "financial", "business", "market")
S1_FILES = ("manifest", "submissions", "expected")


def load(rel: str) -> Any:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def source_pages() -> dict[str, dict[str, Any]]:
    """The frozen page text of each source and its page-joined hash, checked against the oracle."""
    financial = load("cases/financial/manifest.json")
    snapshot = load("cases/snapshot/manifest.json")
    market = load("cases/cp3-cp6-owner/manifest.json")["market_source"]
    business = snapshot["business_source"]["positive"]
    pages: dict[str, dict[str, Any]] = {
        s["source_id"]: {"pages": s["pages"], "sha256": s["sha256"]} for s in financial["sources"]
    }
    pages["business"] = {"pages": business["pages"], "sha256": business["sha256"]}
    pages["market"] = {"pages": market["pages"], "sha256": market["sha256"]}
    for source_id, item in pages.items():
        joined = "\f".join(p["text"] for p in item["pages"])
        if sha(joined.encode()) != item["sha256"]:
            raise RuntimeError(f"{source_id}: page hash drift")
        for number, page in enumerate(item["pages"], 1):
            if page["locator"] != f"page:{number}":
                raise RuntimeError(f"{source_id}: page order")
            if page["text"].splitlines() != page["text"].split("\n"):
                raise RuntimeError(f"{source_id} page:{number}: splitlines differs from split")
    return pages


def source_text(item: dict[str, Any]) -> str:
    """Pages joined with a newline (each page break is a line); no terminal newline."""
    return "\n".join(p["text"] for p in item["pages"])


def page_line_ranges(item: dict[str, Any]) -> dict[str, tuple[int, int]]:
    ranges, start = {}, 1
    for page in item["pages"]:
        count = len(page["text"].split("\n"))
        ranges[page["locator"]] = (start, start + count - 1)
        start += count
    return ranges


def context_document() -> dict[str, Any]:
    document: dict[str, Any] = load("cases/context/research-minimal.json")
    document["run"].update({"pathway": PATHWAY, "case_kind": "synthetic", "as_of": "2026-01-10"})
    document["identity"].update(
        {"issuer_name": "Northbridge Synthetic Group", "issuer_id": "northbridge-synthetic"}
    )
    return document


class Recut:
    def __init__(
        self, pages: dict[str, dict[str, Any]], pack: PreparedPack, hashes: dict[str, str]
    ) -> None:
        self.pages, self.hashes = pages, hashes
        self.ranges = {k: page_line_ranges(v) for k, v in pages.items()}
        self.lines = {s.source_id: {sp.locator: sp.text for sp in s.spans} for s in pack.sources}
        self.pack_hash = pack.content_hash()
        self.citations = 0
        self.ambiguous: list[str] = []
        self.map: list[dict[str, Any]] = []

    def citation(self, node: dict[str, Any]) -> None:
        source_id, old = node["source_id"], node["locator"]
        first, last = self.ranges[source_id][old]
        found = [
            n
            for n in range(first, last + 1)
            if quoted(node["quote"], self.lines[source_id][f"line:{n}"])
        ]
        if not found:
            raise RuntimeError(f"{source_id} {old}: quote on no single line: {node['quote']!r}")
        if len(found) > 1:
            self.ambiguous.append(f"{source_id} {old} -> lines {found}")
        node["locator"] = f"line:{found[0]}"
        if "source_sha256" in node:
            if node["source_sha256"] != self.pages[source_id]["sha256"]:
                raise RuntimeError(f"{source_id}: citation hash is not the oracle's")
            node["source_sha256"] = self.hashes[source_id]
        self.citations += 1
        self.map.append({"source_id": source_id, "from": old, "to": node["locator"]})

    def walk(self, node: Any) -> Any:
        if isinstance(node, dict):
            if {"source_id", "locator", "quote"} <= node.keys() and node["source_id"] in self.pages:
                self.citation(node)
            for key, value in list(node.items()):
                node[key] = self.walk(value)
        elif isinstance(node, list):
            return [self.walk(item) for item in node]
        elif isinstance(node, str):
            if node.startswith(PLACEHOLDER_PREFIX):
                return self.pack_hash
            for source_id, item in self.pages.items():
                if node == item["sha256"]:
                    return self.hashes[source_id]
        return node


def compose(
    pack: PreparedPack, pages: dict[str, dict[str, Any]], hashes: dict[str, str]
) -> tuple[dict[str, Any], "Recut"]:
    s1 = load("cases/snapshot/submissions.json")["positive"]
    c36 = load("cases/cp3-cp6-owner/submissions.json")
    cp5 = load("cases/cp5-owner/submissions.json")["positive"]
    cp8 = load("cases/cp8-owner/submissions.json")["readiness_review"]["no_record"]
    p36 = c36["positive"]

    readiness = copy.deepcopy(p36["readiness_review"]["R6"])
    business = copy.deepcopy(s1["business_context"])
    spec = p36["business_context"]
    business["sources"] = [*business["sources"], *copy.deepcopy(spec["sources_append"])]
    business["consumers"] = copy.deepcopy(spec["consumers"]["R6"])
    out = {
        "readiness_review": readiness,
        "cp1_source_context": copy.deepcopy(p36["cp1_source_context"]),
        "business_context": business,
        "credit_synthesis": copy.deepcopy(s1["credit_synthesis"]),
        "relative_value": copy.deepcopy(p36["relative_value"]),
        "committee_challenge": copy.deepcopy(p36["committee_challenge"]),
        "integrity_review": copy.deepcopy(cp5),
    }
    # CP-8 is in the portfolio_decision plan, so CP-0 must assess it. The CP-8 oracle ran on
    # other run fields and sources; its own "no Prior Case record" row and gap are the one CP-8
    # fact that holds here (the pack has no Prior Case record), minus its outcome-source
    # attachments and its rationale about outcome sources, which are not in this pack.
    row = copy.deepcopy(next(c for c in cp8["consumers"] if c["module_id"] == "CP-8"))
    row["source_ids"], row["citations"] = [], []
    row["rationale"] = (
        "The pack holds no prior decision record and no outcome source, and the CP-8 oracle was "
        "frozen on other run fields (as_of 2026-04-30), so CP-8 is not covered by this case."
    )
    gap = copy.deepcopy(cp8["gaps"][0])
    readiness["consumers"].append(row)
    readiness["gaps"].append(gap)
    # P5T3-R7: the context declares executed legal_documents and the pack holds no legal source.
    # Gap copied from cases/context-attachments-owner/submissions.json (legal-exec-missing-gap).
    # The portfolio_decision plan has no legal module and validate_review admits only selected
    # modules or CP-0, so affected_modules is CP-0 (P5T3-R9).
    readiness["gaps"].append(
        {
            "gap_id": "legal-documents-missing",
            "kind": "source",
            "severity": "material",
            "description": "The run context declares executed legal_documents but the pack holds no executed or filed source",
            "affected_modules": ["CP-0"],
            "remediation": "Supply the executed legal documents",
            "citations": [],
        }
    )

    recut = Recut(pages, pack, hashes)
    out = {name: recut.walk(value) for name, value in out.items()}

    # CP-0 assesses the context file as a source (it is a prepared source); its own cited line.
    context_lines = {
        s.locator: s.text for s in next(s for s in pack.sources if s.source_id == "context").spans
    }
    quote = '"issuer_name": "Northbridge Synthetic Group"'
    line = next(k for k, v in context_lines.items() if quote in v)
    out["readiness_review"]["sources"].append(
        {
            "source_id": "context",
            "document_family": "Run context file",
            "authority": "unknown",
            "entity": "Northbridge Synthetic Group",
            "period": "As of January 10, 2026",
            "version_relationship": "Run settings supplied with the pack; not issuer evidence",
            "fidelity": "verified",
            "citations": [
                {
                    "source_id": "context",
                    "source_sha256": hashes["context"],
                    "locator": line,
                    "quote": quote,
                }
            ],
            "limitations": ["Run settings supplied by the analyst; not issuer evidence."],
        }
    )
    # CP-1's source-context review must assess every prepared source once, context included.
    out["cp1_source_context"]["sources"].append(
        {
            "source_id": "context",
            "classification": "nonfinancial",
            "document_type": "Run context file",
            "published_on": "2026-01-10",
            "evidence_class": "internal",
            "evidence_rationale": "Run settings only",
            "analytical_use": "Run settings",
            "citations": [
                {
                    "source_id": "context",
                    "source_sha256": hashes["context"],
                    "locator": line,
                    "quote": quote,
                }
            ],
            "event_scan": "unassessed",
            "event_scan_explanation": "Run settings are not event evidence",
        }
    )
    return out, recut


def build(out_dir: Path) -> None:
    pages = source_pages()
    out_dir.mkdir(parents=True, exist_ok=True)
    texts = {k: source_text(pages[k]).encode("utf-8") for k in SOURCE_ORDER}
    for key, raw in texts.items():
        (out_dir / f"{key}.txt").write_bytes(raw)
    context_raw = (json.dumps(context_document(), indent=2, ensure_ascii=False) + "\n").encode()
    (out_dir / "context.json").write_bytes(context_raw)
    context = load_context(context_raw)
    request = preparation_request(
        context,
        run_id=RUN_ID,
        context_path="context.json",
        sources=[
            SourceRequest(source_id=k, path=f"{k}.txt", media_type="text/plain")
            for k in SOURCE_ORDER
        ],
    )
    with tempfile.TemporaryDirectory() as scratch:
        pack = prepare(request, out_dir, Path(scratch) / "pack")
    hashes = {s.source_id: s.sha256 or "" for s in pack.sources}
    for key, raw in texts.items():
        if hashes[key] != sha(raw):
            raise RuntimeError(f"{key}: pack hash is not the file's")
    submissions, recut = compose(pack, pages, hashes)

    review = ReadinessReview.model_validate_json(json.dumps(submissions["readiness_review"]))
    problems = {
        "readiness_review": list(validate_review(pack, review)),
        "cp1_source_context": list(
            validate_source_context(
                pack,
                SourceContextReview.model_validate_json(
                    json.dumps(submissions["cp1_source_context"])
                ),
            )
        ),
    }
    judged = [item["module_id"] for item in submissions["business_context"]["consumers"]]
    expected_consumers = list(cp1a_consumers(pack))
    if judged != expected_consumers:
        raise RuntimeError(
            f"CP-1A consumers {judged} differ from cp1a_consumers {expected_consumers}"
        )

    document = {
        "schema_version": "o2-synthetic-submissions/1",
        "note": (
            "Frozen-oracle submissions of the portfolio_decision preset re-cut to the line:N "
            "locators and file hashes of the pack `prepare` builds from the .txt files and "
            "context.json here. Values, ids and statuses are the source oracles'. {{FIG:name}} "
            "references stay for run-time binding. pack_sha256 is bound (the pack is built once)."
        ),
        "run_id": RUN_ID,
        "pack_sha256": pack.content_hash(),
        "figures": load("cases/cp3-cp6-owner/submissions.json")["figures"],
        "positive": submissions,
    }
    (out_dir / "submissions.json").write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    files = ["context.json", *(f"{k}.txt" for k in SOURCE_ORDER), "submissions.json"]
    manifest = {
        "schema_version": "o2-synthetic-manifest/1",
        "scope": (
            "Synthetic end-to-end oracle for the portfolio_decision preset: S1 (CP-0, CP-1, "
            "CP-1A, CP-2), CP-3, CP-5 and CP-6 submissions re-cut to a prepared pack"
        ),
        "status": "prepared; not reviewed, not frozen",
        "roles": {
            "preparer": "oracle preparer (this builder script)",
            "reviewer": None,
            "builder": None,
        },
        "run": {
            "run_id": RUN_ID,
            "pathway": PATHWAY,
            "case_kind": "synthetic",
            "as_of": "2026-01-10",
            "issuer_id": "northbridge-synthetic",
            "issuer_name": "Northbridge Synthetic Group",
            "requested_modules": list(pack.run.requested_modules),
            "pack_sha256": pack.content_hash(),
        },
        "pack_sources": [
            {
                "source_id": s.source_id,
                "path": s.name,
                "status": s.status,
                "sha256": s.sha256,
                "lines": len(s.spans),
            }
            for s in pack.sources
        ],
        "source_text_rule": "Existing synthetic page text, pages joined with one newline, no terminal newline; no text invented",
        "source_oracles": {
            "identity,financial": "cases/financial/manifest.json sources",
            "business": "cases/snapshot/manifest.json business_source.positive",
            "market": "cases/cp3-cp6-owner/manifest.json market_source",
            "readiness_review": "cases/cp3-cp6-owner/submissions.json positive.readiness_review.R6",
            "cp1_source_context": "cases/cp3-cp6-owner/submissions.json positive.cp1_source_context",
            "business_context": "cases/snapshot/submissions.json positive.business_context + cp3-cp6 sources_append and consumers.R6",
            "credit_synthesis": "cases/snapshot/submissions.json positive.credit_synthesis (unchanged)",
            "relative_value": "cases/cp3-cp6-owner/submissions.json positive.relative_value",
            "committee_challenge": "cases/cp3-cp6-owner/submissions.json positive.committee_challenge",
            "integrity_review": "cases/cp5-owner/submissions.json positive",
        },
        "changes_from_source_oracles": [
            "locator page:N -> line:N and source_sha256 page-joined -> file-bytes hash, on every citation",
            "pack_sha256 placeholder bound to the pack hash above",
            "readiness_review: added source row for `context` (own cited line)",
            "cp1_source_context: added source row for `context` (own cited line), required by validate_source_context (every prepared source assessed once)",
            "readiness_review: added gap legal-documents-missing (P5T3-R7), copied from cases/context-attachments-owner/submissions.json legal-exec-missing-gap with affected_modules [CP-0] (P5T3-R9; the plan has no legal module and validate_review admits only selected modules or CP-0)",
            "readiness_review: added CP-8 consumer row (BLOCKED) and gap missing-prior-record, copied from cases/cp8-owner/submissions.json readiness_review.no_record with source_ids and citations emptied and the rationale rewritten to what this pack holds: CP-8 is in the portfolio_decision plan so CP-0 must assess it; its sources are not in this pack",
        ],
        "dropped_modules": {
            "CP-8": "oracle frozen on other run fields (cases/cp8-owner/manifest.json, as_of 2026-04-30, a different pack); no CP-8 submission here. The preset still plans CP-8, so the run stops at CP-8 (BLOCKED row above)",
            "CP-MODEL": "no submission exists (Python-built)",
        },
        "inherited_oracle_gaps": [],
        "run_time_bindings_changed_by_recut": [
            "cases/cp5-owner/manifest.json run_time_bindings.RT-3 c1_source_locator names page:N; the first CP-1 citation locator is now line:N of the prepared pack"
        ],
        "not_covered": [
            "gap case (cp3-cp6-gap, no market source) needs a second pack and is not included",
            "refusal_mutations are not copied",
            "expected.json is not re-cut: facts and heads in the source expected files cite page:N",
        ],
        "citations_recut": recut.citations,
        "ambiguous_line_matches": sorted(set(recut.ambiguous)),
        "validators": {"issues_by_module": problems},
        "files": {name: sha((out_dir / name).read_bytes()) for name in files},
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    # the manifest hashes the other files; it is not hashed in itself.


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=CASE)
    args = parser.parse_args()
    build(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
