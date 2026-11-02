"""CP-DR anchor check (O7b-1a): the settled CP-0/CP-1 pair a research run stands on.

``check_anchors`` is a pure function over the two settled heads, their modules and the run. The
caller (``begin("CP-DR")``, wired in O7b-1c) runs it before ``current_inputs`` so that the refusal
names the anchor instead of the generic "Required upstream is unrun, stale or blocked" error.
A head carries status, hash and inputs; issuer, ``as_of`` and method version live in the settled
module, so each anchor is a head with the module its ``result_sha256`` names.
"""

from dataclasses import dataclass

from deploy_vii.contracts import Module, Run
from deploy_vii.execution import Head
from deploy_workflow.research.contracts import Anchor, CpDrNotAnchored

_SETTLED = frozenset({"accepted", "restricted"})


@dataclass(frozen=True)
class SettledAnchor:
    head: Head
    module: Module


def _own(slot: str, anchor: SettledAnchor | None) -> SettledAnchor:
    if anchor is None:
        raise CpDrNotAnchored(f"{slot} head is missing")
    if anchor.head.module_id != slot:
        raise CpDrNotAnchored(f"{slot} slot holds module {anchor.head.module_id}")
    if anchor.head.status not in _SETTLED:
        raise CpDrNotAnchored(f"{slot} head is {anchor.head.status}")
    if anchor.module.module_id != slot or anchor.module.content_hash() != anchor.head.result_sha256:
        raise CpDrNotAnchored(f"{slot} head result_sha256 is not the hash of its settled module")
    return anchor


# (label, Module attribute, wording when both heads agree, the run's side).
_IDENTITY = (
    ("issuer", "issuer_id", "CP-0 and CP-1 heads carry issuer {}", "the run's issuer is {}"),
    ("period", "as_of", "the heads carry as_of {}", "the run's as_of is {}"),
    ("method version", "method_version", "the heads carry {}", "the run's method version is {}"),
)


def _identity(cp0: SettledAnchor, cp1: SettledAnchor, run: Run) -> None:
    for label, attr, agree, ours in _IDENTITY:
        theirs, want = (getattr(cp0.module, attr), getattr(cp1.module, attr)), getattr(run, attr)
        if theirs == (want, want):
            continue
        if theirs[0] == theirs[1]:
            raise CpDrNotAnchored(
                f"{label} mismatch: {agree.format(theirs[0])}, {ours.format(want)}"
            )
        raise CpDrNotAnchored(
            f"{label} mismatch: CP-0 head carries {theirs[0]} and CP-1 head carries "
            f"{theirs[1]}, {ours.format(want)}"
        )


def _lineage(cp0: SettledAnchor, cp1: SettledAnchor) -> None:
    consumed = [item for item in cp1.head.inputs if item.input_id == "CP-0"]
    if not consumed:
        raise CpDrNotAnchored("CP-1 head records no CP-0 input")
    if consumed[0].sha256 != cp0.head.result_sha256:
        raise CpDrNotAnchored(
            "CP-1 consumed a different CP-0: CP-1 Input CP-0 hash differs from the CP-0 head "
            "result_sha256"
        )


def check_anchors(cp0: SettledAnchor | None, cp1: SettledAnchor | None, run: Run) -> Anchor:
    """The anchor the brief binds, or ``CpDrNotAnchored`` naming the first miss.

    Order: CP-0 head, CP-1 head (exists, right module, settled ``accepted``/``restricted``, equal
    to its module), then issuer, period, method version, then CP-1's recorded CP-0 input.
    """
    first = _own("CP-0", cp0)
    second = _own("CP-1", cp1)
    _identity(first, second, run)
    _lineage(first, second)
    return Anchor(cp0_sha256=first.head.result_sha256, cp1_sha256=second.head.result_sha256)
