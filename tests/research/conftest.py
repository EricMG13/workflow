"""Shared access to the frozen CP-DR research oracle (read at test time; never edited)."""

import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "cases" / "cpdr-research-owner"


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((CASE / name).read_text(encoding="utf-8"))
    return data


@pytest.fixture(scope="session")
def manifest() -> dict[str, Any]:
    return _load("manifest.json")


@pytest.fixture(scope="session")
def submissions() -> dict[str, Any]:
    return _load("submissions.json")


@pytest.fixture(scope="session")
def expected() -> dict[str, Any]:
    return _load("expected.json")
