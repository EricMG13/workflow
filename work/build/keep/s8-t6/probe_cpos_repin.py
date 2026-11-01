"""T6/F2 probe: rerun cases/cpos-owner/builder/build.py of <repo> with every stale pin replaced by
the file's current sha256 and OUT redirected to <out>; compare each written file with the committed
one. Prints the stale pins and per-file identical/DIFFERS. Exit 1 if any file other than
manifest.json differs, or the builder's own text checks fail.
Usage: python3 -I probe_cpos_repin.py <repo> <out dir>"""
import hashlib, re, sys
from pathlib import Path
repo, out = Path(sys.argv[1]), Path(sys.argv[2])
src = repo / "cases/cpos-owner/builder/build.py"
text = src.read_text(encoding="utf-8")
for rel, pin in re.findall(r'"([^"]+)": "([0-9a-f]{64})"', text.split("def sha_file")[0]):
    now = hashlib.sha256((repo / rel).read_bytes()).hexdigest()
    if now != pin:
        print("stale", rel, pin[:8], "->", now[:8])
        text = text.replace(pin, now)
text = text.replace('OUT = ROOT / "cases" / "cpos-owner"', f"OUT = __import__('pathlib').Path({str(out)!r})")
out.mkdir(parents=True, exist_ok=True)
try:
    exec(compile(text, str(src), "exec"), {"__name__": "__main__", "__file__": str(src)})
except AssertionError as e:
    print("BUILDER CHECK FAILED:", e); sys.exit(1)
bad = 0
for name in ("manifest.json", "submissions.json", "expected.json"):
    same = (out / name).read_bytes() == (repo / "cases/cpos-owner" / name).read_bytes()
    print(name, "identical" if same else "DIFFERS")
    bad += (not same) and name != "manifest.json"
sys.exit(1 if bad else 0)
