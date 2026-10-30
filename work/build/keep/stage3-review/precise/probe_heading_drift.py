"""Probe: which synthetic case texts does the widened STATEMENT_HEADING locate that the old regex
did not? Walks every JSON string under cases/ (excluding czr-*). Prints each new match.
Usage (from s3-i4): PYTHONPATH=src python -I <this> . Exit 0 always (informational)."""
import json, re, sys
from pathlib import Path

sys.path.insert(0, "src")
from deploy_workflow.financial_workflow import STATEMENT_HEADING as NEW  # noqa: E402

OLD = re.compile(r"^\s*(?:CONSOLIDATED\s+)?(?:INCOME STATEMENT|CASH FLOW STATEMENT|BALANCE SHEET)\s*$", re.M)


def strings(v, path):
    if isinstance(v, str):
        yield path, v
    elif isinstance(v, dict):
        for k, x in v.items():
            yield from strings(x, f"{path}/{k}")
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from strings(x, f"{path}/{i}")


for f in sorted(Path("cases").rglob("*.json")):
    if "czr-" in str(f):
        continue
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:  # report, never hide
        print("UNREADABLE", f, e)
        continue
    for p, s in strings(data, ""):
        if bool(NEW.search(s)) != bool(OLD.search(s)):
            print(f, p, [m.group().strip() for m in NEW.finditer(s)])
