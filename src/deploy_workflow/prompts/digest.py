"""``PROMPT_SET_SHA256`` (O6 ruling Q3): one digest over the whole prompt set.

The set is every ``texts/*.md`` and every ``rule_lists/*.json`` (``compose.json`` holds the
orchestrator rules O1-O6). An edit to any byte of any of them moves the digest, so a text change
that keeps every rule statement still shows as a golden diff. It is a constant plus a golden
(``tests/prompts/prompt_set.golden.json``); it is not written to ``run.json``. Stdlib only, so the
module is a leaf.
"""

import hashlib
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_PARTS = (("texts", "*.md"), ("rule_lists", "*.json"))


def prompt_set_files() -> tuple[Path, ...]:
    """The pinned files in sorted path order (posix path relative to ``prompts/``)."""
    found = (p for folder, pattern in _PARTS for p in (_ROOT / folder).glob(pattern))
    return tuple(sorted(found, key=lambda p: p.relative_to(_ROOT).as_posix()))


def compute_prompt_set_sha256() -> str:
    """sha256 over, for each file in sorted order: its relative path, a NUL, the byte length in
    decimal, a NUL and the bytes. The length and NULs keep two sets of files from colliding."""
    digest = hashlib.sha256()
    for path in prompt_set_files():
        data = path.read_bytes()
        digest.update(f"{path.relative_to(_ROOT).as_posix()}\0{len(data)}\0".encode())
        digest.update(data)
    return digest.hexdigest()


PROMPT_SET_SHA256 = compute_prompt_set_sha256()
