"""The refused begins of an owner receipt beside the frozen oracle's `refused_begins` (G3, B23).

Test-only. The oracle spells a reason `str(NotAuthorized): <text>` or `str(ValueError): <text>`;
the receipt keeps `<text>`. Both sides become `(module_id, reason, missing_inputs,
missing_commands)`, in order, so a test follows the frozen list field by field."""

from collections.abc import Sequence
from typing import Any


def of_receipt(receipt: Any) -> list[tuple[str, str, list[str], list[str]]]:
    return [
        (r.module_id, r.reason, list(r.missing_inputs), list(r.missing_commands))
        for r in receipt.refusals
    ]


def of_oracle(
    refused_begins: Sequence[dict[str, Any]],
) -> list[tuple[str, str, list[str], list[str]]]:
    def text(reason: str) -> str:
        return reason.removeprefix("str(NotAuthorized): ").removeprefix("str(ValueError): ")

    return [
        (
            w["module_id"],
            text(w["reason"]),
            list(w.get("missing_inputs", [])),
            list(w.get("missing_commands", [])),
        )
        for w in refused_begins
    ]
