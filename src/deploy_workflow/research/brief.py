"""CP-DR brief lock (O7b-1a): tailored questions to a locked ``research/brief.json``.

The tailoring model call and the owner step are O7b-1c; the tailored list is an input here. Python
orders (context questions first, OD4), bounds (1-32, cut from the tail), hashes and locks.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from deploy_workflow.research.contracts import (
    MAX_QUESTIONS,
    Anchor,
    BriefInvalid,
    QuestionKind,
    ResearchBrief,
    ResearchQuestion,
    receivers_for_focus,
)

CONTEXT_PREFIX = "ctx-"
_ALL_RECEIVERS = receivers_for_focus("")
HASH_MISMATCH = "hash mismatch"


@dataclass(frozen=True)
class TailoredQuestion:
    question_id: str
    text: str
    kind: QuestionKind


def _context(index: int, text: str, focus_module: str) -> ResearchQuestion:
    return ResearchQuestion.from_context(f"{CONTEXT_PREFIX}{index}", text, focus_module)


def _tailored(item: TailoredQuestion) -> ResearchQuestion:
    return ResearchQuestion(
        question_id=item.question_id, text=item.text, kind=item.kind, receivers=_ALL_RECEIVERS
    )


def _check_tailored(tailored: Sequence[TailoredQuestion]) -> None:
    """Refuse a malformed tailored question wherever it sits, not only inside the kept 32."""
    seen: set[str] = set()
    for item in tailored:
        if item.kind == "context":
            raise BriefInvalid(f"tailored question {item.question_id} cannot have kind context")
        if item.question_id.startswith(CONTEXT_PREFIX):
            raise BriefInvalid(f"tailored question id {item.question_id} uses the ctx- prefix")
        if item.question_id in seen:
            raise BriefInvalid(f"a brief repeats the question_id {item.question_id}")
        seen.add(item.question_id)


def merge_questions(
    context_questions: Sequence[tuple[str, str]], tailored: Sequence[TailoredQuestion]
) -> tuple[ResearchQuestion, ...]:
    """Context questions first (``ctx-1``...), then the tailored list, cut to 32 from the tail."""
    if len(context_questions) > MAX_QUESTIONS:
        raise BriefInvalid(f"{len(context_questions)} context questions exceed {MAX_QUESTIONS}")
    _check_tailored(tailored)
    leading = [_context(i, text, focus) for i, (text, focus) in enumerate(context_questions, 1)]
    return (*leading, *(_tailored(item) for item in tailored[: MAX_QUESTIONS - len(leading)]))


def write_locked_brief(path: Path, brief: ResearchBrief) -> None:
    """Write ``brief.json`` once; a lock is never overwritten."""
    if path.exists():
        raise BriefInvalid(f"brief already locked at {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(brief.model_dump(mode="json"), sort_keys=True, indent=1, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )


def lock_brief(
    *,
    issuer_id: str,
    run_id: str,
    as_of: date,
    cutoff: date,
    context_questions: Sequence[tuple[str, str]],
    tailored: Sequence[TailoredQuestion],
    anchor: Anchor,
    path: Path,
    peer_pack: bool = False,
) -> ResearchBrief:
    """Merge, bound, hash and write the brief; the returned ``brief_sha256`` is the lock."""
    brief = ResearchBrief.build(
        issuer_id=issuer_id,
        run_id=run_id,
        as_of=as_of,
        cutoff=cutoff,
        questions=merge_questions(context_questions, tailored),
        anchor=anchor,
        peer_pack=peer_pack,
    )
    write_locked_brief(path, brief)
    return brief


def rebuild_brief(body: dict[str, Any]) -> ResearchBrief:
    """A brief from its JSON body with the hash recomputed; a stored ``brief_sha256`` is ignored.

    The contracts are strict, so JSON strings and lists are converted to dates and tuples here.
    """
    fields = {k: v for k, v in body.items() if k != "brief_sha256"}
    try:
        fields["as_of"] = date.fromisoformat(fields["as_of"])
        fields["cutoff"] = date.fromisoformat(fields["cutoff"])
        fields["questions"] = [
            ResearchQuestion.model_validate(q, strict=False) for q in fields["questions"]
        ]
        return ResearchBrief.build(**fields)
    except (KeyError, TypeError, ValueError) as error:
        raise BriefInvalid(f"brief body is malformed: {error}") from error


def body_sha256(body: dict[str, Any]) -> str:
    """O7-P8: sha256 of the body without ``brief_sha256``, sorted keys, compact separators."""
    hashed = {k: v for k, v in body.items() if k != "brief_sha256"}
    text = json.dumps(hashed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_locked_brief(path: Path, locked_sha256: str) -> ResearchBrief:
    """Read the brief back; any edit since the lock is ``BriefInvalid("hash mismatch")``.

    The raw stored body is hashed first and compared with both the hash stored in the file and
    the one recorded at the lock (``run.json``), so rewriting both in the file is caught too.
    Only a body that passes is validated; an unreadable or non-object file is the same refusal.
    """
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BriefInvalid(HASH_MISMATCH) from error
    if not isinstance(stored, dict):
        raise BriefInvalid(HASH_MISMATCH)
    computed = body_sha256(stored)
    if stored.get("brief_sha256") != computed or computed != locked_sha256:
        raise BriefInvalid(HASH_MISMATCH)
    return rebuild_brief(stored)
