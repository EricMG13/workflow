"""Build lenient copies of the tip's src for the High 1 non-vacuity runs (scratch only)."""
import shutil
import sys
from pathlib import Path

base = Path(sys.argv[1])  # <D>
tip = base / "tip" / "src"
PUB = ("        if (attempt.module_id, attempt.inputs, attempt.number) != (\n",
       "        if False and (attempt.module_id, attempt.inputs, attempt.number) != (\n")
PUB_REPAIR = ("        ) or (attempt.repair_of, attempt.repair_issues) != (\n",
              "        ) or False and (attempt.repair_of, attempt.repair_issues) != (\n")
HEAD = ("        if bound != _result_attempt(snapshot, head).inputs:\n",
        "        if False and bound != _result_attempt(snapshot, head).inputs:\n")
for name, edits in {"mut-pub": [PUB, PUB_REPAIR], "mut-both": [PUB, PUB_REPAIR, HEAD], "mut-head": [HEAD]}.items():
    dst = base / name / "src"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(tip, dst, ignore=shutil.ignore_patterns("__pycache__"))
    path = dst / "deploy_workflow" / "owner_workflow.py"
    text = path.read_text()
    for old, new in edits:
        assert text.count(old) == 1, (name, old)
        text = text.replace(old, new)
    path.write_text(text)
    print("built", name)
