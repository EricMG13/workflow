"""Byte-compare two kept pytest tmp trees: python -I compare_trees.py <a> <b>.

Prints the file count, every path present in only one tree, and every path whose bytes differ.
Exit 0 only when both trees hold the same paths with identical bytes.
"""

import hashlib
import pathlib
import sys


def digests(root: pathlib.Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


a, b = (digests(pathlib.Path(arg)) for arg in sys.argv[1:3])
only = sorted(a.keys() ^ b.keys())
differ = sorted(k for k in a.keys() & b.keys() if a[k] != b[k])
print(f"files {len(a)} vs {len(b)}; only-in-one {len(only)}; differ {len(differ)}")
for path in only[:20]:
    print(f"  only: {path}")
for path in differ[:20]:
    print(f"  differ: {path}")
sys.exit(1 if only or differ else 0)
