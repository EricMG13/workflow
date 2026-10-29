"""The committed `read_inputs` view key trees (`cases/<cp>-owner/<cp>-view-tree.json`).

A tree is shape only: dict keys in order, scalar type names, and for a list its distinct element
shapes. `check` compares the body a module's `view` serves with the committed tree of one case;
`render` writes the file text (used to regenerate a tree after a lease change).
"""

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def shape(value: Any) -> Any:
    """Key tree with scalar type names; a list keeps its distinct element shapes."""
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    if isinstance(value, list):
        shapes: list[Any] = []
        for item in value:
            if (s := shape(item)) not in shapes:
                shapes.append(s)
        return shapes
    return type(value).__name__


def path(slug: str) -> Path:
    return ROOT / "cases" / f"{slug}-owner" / f"{slug}-view-tree.json"


def load(slug: str) -> dict[str, Any]:
    tree: dict[str, Any] = json.loads(path(slug).read_text(encoding="utf-8"))
    return tree


def entry(body: str) -> dict[str, Any]:
    """The committed form of one view body: its top-level keys in order and its shape."""
    parsed = json.loads(body)
    return {"top_level_keys": list(parsed), "tree": shape(parsed)}


def render(note: str, bodies: dict[str, str]) -> str:
    return json.dumps({"_note": note, **{c: entry(b) for c, b in bodies.items()}}, indent=1) + "\n"


def check(slug: str, case: str, body: str) -> None:
    """Assert the body's keys and shape equal the committed tree of the case."""
    frozen = load(slug)[case]
    assert entry(body) == frozen, f"{slug} {case}: the view no longer matches {path(slug).name}"
