"""Undo the Phase 5 Task 6 changes to composed messages (rulings P5T6-R1 and P5T6-R3).

`undo_p5t6_context` (CP-0, `source_readiness`, the user message): the run-context block gained the
key `attachments` (`legal_documents`), so its one JSON line and its `sha256` header changed; the
strip removes that key and rewrites the header hash of what is left.
`undo_p5t6_wording` (CP-4, `legal_covenants`, the system message): CP-4's method text named
`executed, filed or, on a draft-documents run, draft` where it said `executed or filed`.
Removing exactly these gives the message the digests pinned before Task 6.
"""

import hashlib
import json
import re

_BLOCK = re.compile(r"<<<CONTEXT id=run-context sha256=([0-9a-f]{64})>>>\n(.*)\n<<<END>>>")
WORDING_NEW = "(CP-0 classes them executed,\nfiled or, on a draft-documents run, draft);"
WORDING_OLD = "(CP-0 classes them executed\nor filed);"


def undo_p5t6_context(step_id: str, text: str) -> str:
    """Remove `attachments` from the run-context block of a CP-0 user message."""
    if step_id != "source_readiness":
        return text
    found = _BLOCK.findall(text)
    assert len(found) == 1, step_id
    digest, line = found[0]
    assert hashlib.sha256(line.encode()).hexdigest() == digest
    body = json.loads(line)
    assert set(body["attachments"]) == {"legal_documents"}
    del body["attachments"]
    old = json.dumps(body, sort_keys=True)
    old_block = (
        f"<<<CONTEXT id=run-context sha256={hashlib.sha256(old.encode()).hexdigest()}>>>\n"
        f"{old}\n<<<END>>>"
    )
    return _BLOCK.sub(lambda _: old_block, text)


def undo_p5t6_wording(step_id: str, text: str) -> str:
    """Put CP-4's old `executed or filed` method wording back (`legal_covenants` only)."""
    if step_id != "legal_covenants":
        return text
    assert text.count(WORDING_NEW) == 1
    return text.replace(WORDING_NEW, WORDING_OLD)
