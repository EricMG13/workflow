"""Source-level mutant of `host._SOURCE_STEPS` for the Info re-check (scratch copy only):
CP-1 loses its `financials` source step. The owner spec keeps `sources=True` on it."""
import shutil
import sys
from pathlib import Path

base = Path(sys.argv[1])
dst = base / "mut-info" / "src"
if dst.exists():
    shutil.rmtree(dst)
shutil.copytree(base / "tip" / "src", dst, ignore=shutil.ignore_patterns("__pycache__"))
path = dst / "deploy_workflow" / "host.py"
old = '    "CP-1": ("source_context", "financials"),\n'
new = '    "CP-1": ("source_context",),\n'
text = path.read_text()
assert text.count(old) == 1
path.write_text(text.replace(old, new))
print("built mut-info")
