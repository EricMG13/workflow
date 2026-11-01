"""Add the `context` source row to the steps of the o2-synthetic walk that assess every source (O2 Task 4c).

    PYTHONPATH=src .venv/bin/python cases/o2-synthetic/builder/context_rows.py [--out DIR]

Run after `build.py` and `cp1_financials.py`; it reads `submissions.json` and `manifest.json` from
DIR (default cases/o2-synthetic) and rewrites them. Idempotent: an existing `context` row is
replaced, so two runs write byte-identical files.

Rule search (validators the walk reaches that need each prepared source assessed once):
- readiness.py:344 (CP-0)            row added by build.py (Task 4)
- source_context.py:188 (CP-1)       row added by build.py (Task 4)
- business_context.py:665 (CP-1A)    row added here
No such rule: CP-2 credit_synthesis, CP-3 relative_value, CP-5 integrity_review, CP-6
committee_challenge (they only list pack sources in their views; no validator compares the set).

The CP-1A row has the CP-0 `context` row's shape: authority unknown -> source_class unknown;
the run settings are not issuer evidence -> quality Low; same entity, period and limitation
wording; its own cited line (the quote must match exactly one line of context.json).
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT / "cases" / "o2-synthetic"
QUOTE = '"issuer_name": "Northbridge Synthetic Group"'
ADDED = (
    "business_context: added source row for `context` (own cited line), required by "
    "validate_business_context (every prepared source assessed once; business_context.py:665)"
)
STATUS_SUFFIX = "; business_context `context` source row (O2 Task 4c): CP-1A context row reviewed (mx-precise accca4ec) and frozen"
BASE_STATUS = (
    "S1, CP-3, CP-5, CP-6 submissions, sources and context frozen (9de132e7, cases/PINS.json); "
    "cp1-financials.json reviewed (mx-precise a0d99f61) and frozen"
)


def write(path: Path, document: Any) -> None:
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=CASE)
    out = parser.parse_args().out
    lines = (out / "context.json").read_text(encoding="utf-8").split("\n")
    found = [n for n, text in enumerate(lines, 1) if QUOTE in text]
    if len(found) != 1:
        raise RuntimeError(f"quote matches lines {found}, exactly one required")
    submissions = json.loads((out / "submissions.json").read_text(encoding="utf-8"))
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    context_sha = hashlib.sha256((out / "context.json").read_bytes()).hexdigest()
    if context_sha != manifest["files"]["context.json"]:
        raise RuntimeError("context.json is not the manifest's")
    sources = submissions["positive"]["business_context"]["sources"]
    sources[:] = [s for s in sources if s["source_id"] != "context"]
    sources.append(
        {
            "source_id": "context",
            "source_class": "unknown",
            "quality": "Low",
            "period": "As of January 10, 2026",
            "entity_covered": "Northbridge Synthetic Group",
            "data_supplied": "Run settings: pathway, case kind, as-of date and issuer identity",
            "use": "Run settings supplied with the pack; not issuer evidence",
            "citations": [{"source_id": "context", "locator": f"line:{found[0]}", "quote": QUOTE}],
            "limitation": "Run settings supplied by the analyst; not issuer evidence.",
        }
    )
    write(out / "submissions.json", submissions)
    changes = [c for c in manifest["changes_from_source_oracles"] if c != ADDED]
    # keep the added row right after the cp1_source_context one
    at = next(i for i, c in enumerate(changes) if c.startswith("cp1_source_context:")) + 1
    changes.insert(at, ADDED)
    manifest["changes_from_source_oracles"] = changes
    manifest["status"] = BASE_STATUS + STATUS_SUFFIX
    manifest["files"]["submissions.json"] = hashlib.sha256(
        (out / "submissions.json").read_bytes()
    ).hexdigest()
    write(out / "manifest.json", manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
