"""B23 freeze probe (stdlib only; run from the repository root: python3 -I work/context-plan/probes/b23_freeze_digests.py).

1. For every file under cases/ changed since the parent (the HEAD before the freeze commit), every added or
   removed line of `git diff` must be a digest line (it holds a 64-hex literal).
2. Every digest literal in the changed builders, chart oracles, manifests and expected files that names a file
   (a "cases/..." or "src/..." key, a "path"/"file" sibling of "sha256", or a files_sha256 key relative to the
   case directory) must equal the sha256 of that file. Added literals that name no file fail.
Default reads the working tree (before the commit); `--head` reads blobs at HEAD and diffs parent..HEAD.
Exit 0 when held, 1 otherwise.
"""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PARENT = "9d3902056af288e6b66e4cecfc1b4e84d02741ff"
ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
HEAD = "--head" in sys.argv
HEX = re.compile(r"[0-9a-f]{64}")
# known stale pin, an owner item (ruling B23a item 3): the cp4c builder still pins the old cp3c manifest
KNOWN_STALE = {
    ("cases/cp4c-owner/builder/build.py", "cases/cp3c-owner/manifest.json"),
    ("cases/cp4c-owner/manifest.json", "cases/cp3c-owner/manifest.json"),
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def read(rel):
    if HEAD:
        return subprocess.check_output(["git", "show", f"HEAD:{rel}"], cwd=ROOT)
    return (ROOT / rel).read_bytes()


def sha(rel):
    return hashlib.sha256(read(rel)).hexdigest()


diff_args = [PARENT, "HEAD"] if HEAD else [PARENT]
changed = [f for f in git("diff", "--name-only", *diff_args, "--", "cases").split("\n") if f]
fails = []
checked = 0
added = set()
for line in git("diff", "-U0", *diff_args, "--", "cases").split("\n"):
    if line.startswith("+") and not line.startswith("+++"):
        added.update(HEX.findall(line))
mapped_added = set()

# 1. every changed line is a digest line
for f in changed:
    for line in git("diff", "-U0", *diff_args, "--", f).split("\n"):
        if line[:1] in ("+", "-") and not line.startswith(("+++", "---")) and not HEX.search(line):
            fails.append(f"non-digest changed line in {f}: {line[:120]}")


def walk(node, parent_key=None, siblings=None):
    """Yield (key, value, siblings) for each 64-hex string value in a JSON tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and HEX.fullmatch(v):
                yield k, v, node
            else:
                yield from walk(v, k, node)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v, parent_key, siblings)


def target(f, key, sib):
    """The file a digest literal names, or None when it is not a file digest (e.g. a source page digest)."""
    case_dir = str(Path(f).parent)
    if key.startswith(("cases/", "src/")):
        return key
    if key == "sha256":
        if isinstance(sib.get("path"), str) and "schema_version" in sib:  # chart oracle modules entry
            return sib["path"]
        if isinstance(sib.get("file"), str):
            fl = sib["file"]
            if fl.startswith(("cases/", "src/")):
                return fl
            return f"{case_dir}/{fl}" if (ROOT / case_dir / fl).is_file() else None  # else an external doc digest
        return None
    if key.endswith(".json") and "/" not in key:  # files_sha256 entries, relative to the case directory
        return f"{case_dir}/{key}"
    if "/" in key:
        return f"{case_dir}/{key}"
    return None


# 2. every named digest equals the file's sha256
for f in changed:
    if not f.endswith((".json", ".py")):
        continue
    text = read(f).decode("utf-8")
    if f.endswith(".py"):
        for m in re.finditer(r'"((?:cases|src)/[^"]+)":\s*"([0-9a-f]{64})"', text):
            rel, lit = m.groups()
            if (f, rel) in KNOWN_STALE:
                print(f"known stale (owner item, B23a 3): {f} pins {rel}")
                continue
            checked += 1
            mapped_added.add(lit)
            if sha(rel) != lit:
                fails.append(f"{f}: {rel} pinned {lit} but is {sha(rel)}")
        continue
    for key, lit, sib in walk(json.loads(text)):
        rel = target(f, key, sib)
        if rel is None:
            continue
        if (f, rel) in KNOWN_STALE:
            print(f"known stale (owner item, B23a 3): {f} pins {rel}")
            continue
        try:
            actual = sha(rel)
        except (subprocess.CalledProcessError, FileNotFoundError):
            fails.append(f"{f}: {key} names missing file {rel}")
            continue
        checked += 1
        mapped_added.add(lit)
        if actual != lit:
            fails.append(f"{f}: {rel} pinned {lit} but is {actual}")

for lit in sorted(added - mapped_added):
    # PINS.json is checked by cases/pins.py --check; every other added literal must name a file
    fails.append(f"added digest literal not tied to a file digest check: {lit}")

print(f"changed files under cases/: {len(changed)}; digest literals checked: {checked}")
for x in fails:
    print("FAIL", x)
sys.exit(1 if fails else 0)
