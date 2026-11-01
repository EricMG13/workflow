"""CP-DR contracts: version, readiness ladder, brief, evidence item and named errors (O7a)."""

import hashlib
import json
import re
from collections.abc import Sequence
from datetime import date
from typing import Any, Final, Literal, Self

from pydantic import field_validator, model_validator

from deploy_vii.contracts import Contract, Hash, Identifier, Text

METHOD_VERSION_CPDR: Final = "cp-dr/2026-10-31"

Readiness = Literal[
    "COMMITTEE_READY", "RESEARCH_READY", "RESEARCH_READY_WITH_LIMITATIONS", "BLOCKED"
]
# FULL_CP_OS is not representable (OD10).
Lineage = Literal["LOCAL"]
LOCAL_CEILING: Readiness = "RESEARCH_READY"
ClaimState = Literal["supported", "contrary", "missing", "blocked"]
Receiver = Literal["CP-1C", "CP-2"]
QuestionKind = Literal[
    "default_1",
    "default_2",
    "default_3",
    "default_4",
    "default_5",
    "default_6",
    "context",
    "custom",
]

MIN_QUESTIONS = 1
MAX_QUESTIONS = 32
RESERVED_IDS = frozenset({"cp-dr-dossier", "peers"})
RESERVED_PREFIX = "ev-"
_ITEM_ID = re.compile(r"^ev-[1-9][0-9]*$")
_ALL_RECEIVERS: tuple[Receiver, ...] = ("CP-1C", "CP-2")


class ResearchError(Exception):
    """Base of the CP-DR errors; not a ValueError so pydantic does not wrap it."""


class CpDrNotAnchored(ResearchError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class BriefInvalid(ResearchError):
    pass


class CutoffViolation(ResearchError):
    def __init__(self, item_id: str) -> None:
        super().__init__(f"evidence item {item_id} is after the cutoff")
        self.item_id = item_id


class CommitteeReadyRefused(ResearchError):
    pass


class EvidenceFetchRefused(ResearchError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ReservedSourceId(ResearchError):
    pass


def refuse_reserved(source_id: str) -> None:
    """Refuse a research-manifest source id that CP-DR reserves for itself."""
    if source_id in RESERVED_IDS or source_id.startswith(RESERVED_PREFIX):
        raise ReservedSourceId(f"source id {source_id!r} is reserved by CP-DR")


def assign_readiness(states: Sequence[ClaimState]) -> Readiness:
    """Readiness of a LOCAL dossier; never above LOCAL_CEILING."""
    if not states or "blocked" in states:
        return "BLOCKED"
    if "contrary" in states or "missing" in states:
        return "RESEARCH_READY_WITH_LIMITATIONS"
    return LOCAL_CEILING


class Dossier(Contract):
    """Minimal in O7a; O7b-1 extends it."""

    brief_sha256: Hash
    lineage: Lineage
    readiness: Readiness

    @field_validator("readiness")
    @classmethod
    def _not_committee_ready(cls, value: Readiness) -> Readiness:
        if value == "COMMITTEE_READY":
            raise CommitteeReadyRefused("a LOCAL dossier is never COMMITTEE_READY")
        return value


def receivers_for_focus(focus_module: str) -> tuple[Receiver, ...]:
    """Map a context question's focus_module to its receivers (L8)."""
    focus = focus_module.strip()
    if focus == "CP-1C":
        return ("CP-1C",)
    if focus == "CP-2":
        return ("CP-2",)
    if focus in ("CP-DR", ""):
        return _ALL_RECEIVERS
    raise BriefInvalid(f"focus_module {focus_module!r} is not CP-1C, CP-2, CP-DR or blank")


class ResearchQuestion(Contract):
    question_id: Identifier
    text: Text
    kind: QuestionKind
    receivers: tuple[Receiver, ...]
    focus_module: str | None = None

    @model_validator(mode="after")
    def _receivers_consistent(self) -> Self:
        if not self.receivers:
            raise BriefInvalid(f"question {self.question_id} has no receivers")
        if self.kind == "context":
            if self.focus_module is None:
                raise BriefInvalid(f"context question {self.question_id} has no focus_module")
            if self.receivers != receivers_for_focus(self.focus_module):
                raise BriefInvalid(f"question {self.question_id} receivers do not match focus")
        return self

    @classmethod
    def from_context(cls, question_id: str, text: str, focus_module: str) -> Self:
        return cls(
            question_id=question_id,
            text=text,
            kind="context",
            receivers=receivers_for_focus(focus_module),
            focus_module=focus_module,
        )


class Anchor(Contract):
    cp0_sha256: Hash
    cp1_sha256: Hash


def _canonical_sha256(body: dict[str, Any]) -> str:
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ResearchBrief(Contract):
    version: Literal["cp-dr/2026-10-31"] = METHOD_VERSION_CPDR
    issuer_id: Identifier
    run_id: Identifier
    as_of: date
    cutoff: date
    questions: tuple[ResearchQuestion, ...]
    anchor: Anchor
    peer_pack: bool
    brief_sha256: Hash

    @model_validator(mode="after")
    def _checked(self) -> Self:
        if not MIN_QUESTIONS <= len(self.questions) <= MAX_QUESTIONS:
            raise BriefInvalid(f"a brief holds {MIN_QUESTIONS}-{MAX_QUESTIONS} questions")
        if self.cutoff > self.as_of:
            raise BriefInvalid("cutoff is after as_of")
        if self.brief_sha256 != self.expected_sha256():
            raise BriefInvalid("brief_sha256 does not match the canonical brief")
        return self

    def expected_sha256(self) -> str:
        return _canonical_sha256(self.model_dump(mode="json", exclude={"brief_sha256"}))

    @classmethod
    def build(cls, **fields: Any) -> Self:
        """Construct a brief and compute its hash; all validation runs on the result."""
        draft = cls.model_construct(brief_sha256="0" * 64, **fields)
        digest = _canonical_sha256(draft.model_dump(mode="json", exclude={"brief_sha256"}))
        return cls(**fields, brief_sha256=digest)


class EvidenceItem(Contract):
    item_id: str
    origin: Literal["supplied", "web"]
    sha256: Hash
    locator: Text
    published: date | None
    family: Text

    @field_validator("item_id")
    @classmethod
    def _reserved_form(cls, value: str) -> str:
        if not _ITEM_ID.fullmatch(value):
            raise ValueError("item_id must be ev-<n>, n >= 1, no leading zero")
        return value
