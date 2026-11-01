"""Borrower-name check (Phase 2): the context's borrower against the CP-1 T4.2 entities.

``entities`` are the T4.2 ``(Entity Name, Entity Role)`` cells. A role cell joins several roles
with ``"; "``, so each role is split on it. The check compares and reports; it never raises on
a mismatch and never alters identity.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from deploy_workflow.context import RunContext

GAP_CODE = "borrower_name_mismatch"


@dataclass(frozen=True, slots=True)
class IdentityCheck:
    outcome: Literal["match", "mismatch", "not_supplied"]
    gaps: tuple[str, ...]
    context_borrower: str
    found: tuple[str, ...]


def _fold(name: str) -> str:
    return "".join(c for c in name.casefold() if c.isalnum())


def _is_borrower(roles: Sequence[str]) -> bool:
    return any(part == "borrower" for role in roles for part in role.split("; "))


def compare(context: RunContext, entities: Sequence[tuple[str, tuple[str, ...]]]) -> IdentityCheck:
    """Compare ``context.identity.borrower_name`` with the borrower-role T4.2 entities."""
    named = context.identity.borrower_name
    found = tuple(dict.fromkeys(name for name, roles in entities if _is_borrower(roles)))
    if not named or not found:
        return IdentityCheck("not_supplied", (), named, found)
    if _fold(named) in {_fold(name) for name in found}:
        return IdentityCheck("match", (), named, found)
    gap = f'{GAP_CODE}: context names "{named}", CP-1 locates "{"; ".join(found)}"'
    return IdentityCheck("mismatch", (gap,), named, found)
