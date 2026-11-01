"""Phase 6 Task 9: the pinned-assumptions block reads `owners.pins`, one module at a time.

The expected bodies come from the frozen oracle `cases/pins-context-owner` (context files and
`expected.json`), never from the code under test. `PINS_ENABLED` is the one list of enabled
modules; the guard runs each enabled module's own validator on the oracle's `differs` case.
"""

import hashlib
import importlib
import json
import re
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest
import test_owner_cp2a_pins as p2a
import test_owner_cp2d_pins as p2d
import test_owner_cp2e_pins as p2e
import test_owner_cp3c_pins as p3c
import test_owner_cp3d_pins as p3d
import test_owner_cp4c_pins as p4c
from prompt_support import request_for

from deploy_vii.contracts import Run
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow.context import RunContext, context_facts
from deploy_workflow.model.turn import Message
from deploy_workflow.owners import pins as owner_pins
from deploy_workflow.prompts.compose import O6_PINS, PINS_ID

compose_module = importlib.import_module("deploy_workflow.prompts.compose")

ORACLE = Path(__file__).resolve().parents[2] / "cases" / "pins-context-owner"
SENTINEL = "RATIONALE-SENTINEL-7f3a"
NUM = re.compile(r"^[0-9]+(\.[0-9]+)?$")
STEPS = {
    "CP-2A": "downside_pathway",
    "CP-2D": "liquidity_bridge",
    "CP-2E": "macro_fx",
    "CP-3C": "refinancing_risk",
    "CP-3D": "market_implied",
    "CP-4C": "restructuring_fulcrum",
}
ALL_SIX = frozenset(STEPS)
CONTEXTS = {  # the oracle context that pins each module
    "CP-2A": "context-distressed_restructuring.json",
    "CP-2D": "context-covenant_refinancing.json",
    "CP-2E": "context-credit_snapshot.json",
    "CP-3C": "context-covenant_refinancing.json",
    "CP-3D": "context-relative_value.json",
    "CP-4C": "context-distressed_restructuring.json",
}


def _with_sentinel(raw: bytes) -> bytes:
    """The context with every non-empty `rationale` replaced by the sentinel."""

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "rationale" and value:
                    node[key] = SENTINEL
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    doc = json.loads(raw)
    walk(doc)
    return json.dumps(doc, indent=2).encode()


def context_pack(base: PreparedPack, name: str, *, sentinel: bool = False) -> PreparedPack:
    """`base`'s non-context sources plus the oracle context `name`, the run agreeing with it."""
    raw = (ORACLE / name).read_bytes()
    if sentinel:
        raw = _with_sentinel(raw)
        assert SENTINEL.encode() in raw  # the context does carry rationales
    doc = json.loads(raw)
    fields = base.run.model_dump(mode="json")
    fields.update(
        run_id="t9-pins-v1",
        issuer_id=doc["identity"]["issuer_id"],
        issuer_name=doc["identity"]["issuer_name"],
        as_of=doc["run"]["as_of"],
        case_kind=doc["run"]["case_kind"],
        pathway=doc["run"]["pathway"],
    )
    run = Run.model_validate_json(json.dumps(fields))
    request = SourceRequest(source_id="context", path="context.json", media_type="text/plain")
    kept = tuple(s for s in base.sources if s.source_id != "context")
    return PreparedPack(run=run, sources=(*kept, prepare_source(request, raw)))


def messages(
    pack: PreparedPack, module: str, *, context: RunContext | None | str = "from-pack"
) -> tuple[Message, ...]:
    msgs: tuple[Message, ...] = compose_module.compose(
        request_for(STEPS[module], pack, context=context)
    )
    return msgs


def parts(msgs: tuple[Message, ...]) -> tuple[str, str]:
    return msgs[0].text, msgs[1].text


def pinned_body(user: str) -> dict[str, Any] | None:
    """The JSON body of the one pinned-assumptions block, or None when there is none."""
    found = re.findall(
        rf"<<<CONTEXT id={PINS_ID} sha256=[0-9a-f]+>>>\n(.*?)\n<<<END>>>", user, re.DOTALL
    )
    assert len(found) <= 1 and user.count(f"id={PINS_ID}") == len(found)
    if not found:
        return None
    body: dict[str, Any] = json.loads(found[0])
    return body


def digest(msgs: tuple[Message, ...]) -> str:
    return hashlib.sha256("\x00".join(m.text for m in msgs).encode()).hexdigest()


# ---------------------------------------------------------------- the block reads owners.pins


def test_cp3c_prompt_holds_the_one_pinned_block_and_the_rule(
    pack: PreparedPack, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(compose_module, "PINS_ENABLED", frozenset({"CP-3C"}))
    covenant = context_pack(pack, "context-covenant_refinancing.json")
    system, user = parts(messages(covenant, "CP-3C"))
    assert pinned_body(user) == {"repricing.bps": "400"}
    assert O6_PINS in system and "exactly that value" in O6_PINS
    # CP-3D and CP-2A are not enabled: none, whatever the context pins
    assert pinned_body(parts(messages(covenant, "CP-3D"))[1]) is None
    assert pinned_body(parts(messages(covenant, "CP-2A"))[1]) is None


def test_no_pin_or_no_context_gives_no_block_and_no_rule(
    pack: PreparedPack, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(compose_module, "PINS_ENABLED", frozenset({"CP-3C"}))
    no_pin = context_pack(pack, "context-covenant_refinancing-no-cp3c.json")
    for target, context in ((no_pin, "from-pack"), (pack, None)):
        system, user = parts(messages(target, "CP-3C", context=context))
        assert pinned_body(user) is None and O6_PINS not in system


def test_the_cp2a_body_is_submission_paths_and_fractions(
    pack: PreparedPack, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(compose_module, "PINS_ENABLED", frozenset({"CP-2A"}))
    ctx = context_pack(pack, "context-distressed_restructuring.json")
    body = pinned_body(parts(messages(ctx, "CP-2A"))[1])
    assert body is not None and list(body) == ["scenarios"]
    expected = json.loads((ORACLE / "expected.json").read_text())["modules"]["CP-2A"]["pins"]
    want = [
        {"ebitda_decline": decline, "interest_increase": interest}
        for decline, interest in expected["fractions"]
    ]
    assert body["scenarios"] == want


@pytest.mark.parametrize("module", sorted(ALL_SIX))
def test_the_block_holds_no_rationale_and_no_other_modules_pin(
    module: str, pack: PreparedPack, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(compose_module, "PINS_ENABLED", frozenset({module}))
    marked = context_pack(pack, CONTEXTS[module], sentinel=True)
    system, user = parts(messages(marked, module))
    assert SENTINEL not in system and SENTINEL not in user
    ctx = context_facts(marked)
    assert ctx is not None
    body = pinned_body(user)
    assert body == owner_pins.form_from_context(module, ctx)
    assert set(body or {}) <= {
        "scenarios",
        "horizon_months",
        "minimum_cash.amount",
        "rate_shocks_bp",
        "fx_shocks_percent",
        "hedge_ratio.percent_text",
        "repricing.bps",
        "recovery.percent_text",
        "valuation[*].multiple",
    }


def _leaves(node: object) -> Iterable[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for item in node:
            yield from _leaves(item)
    elif isinstance(node, Mapping):
        for item in node.values():
            yield from _leaves(item)


@pytest.mark.parametrize("module", sorted(ALL_SIX))
def test_every_pinned_value_is_a_decimal_string_that_cannot_forge_a_delimiter(
    module: str, pack: PreparedPack
) -> None:
    ctx = context_facts(context_pack(pack, CONTEXTS[module]))
    assert ctx is not None
    form = owner_pins.form_from_context(module, ctx)
    assert form is not None
    leaves = list(_leaves(form))
    assert leaves and all(NUM.fullmatch(leaf) for leaf in leaves)


def test_a_module_not_enabled_has_the_unpinned_prompt(
    pack: PreparedPack, monkeypatch: pytest.MonkeyPatch
) -> None:
    covenant = context_pack(pack, "context-covenant_refinancing.json")
    monkeypatch.setattr(compose_module, "PINS_ENABLED", frozenset())
    unpinned = digest(messages(covenant, "CP-3C"))
    monkeypatch.setattr(compose_module, "PINS_ENABLED", frozenset({"CP-2D"}))
    assert digest(messages(covenant, "CP-3C")) == unpinned
    monkeypatch.setattr(compose_module, "PINS_ENABLED", frozenset({"CP-3C"}))
    assert digest(messages(covenant, "CP-3C")) != unpinned


def test_composing_with_a_pin_leaves_the_environment_alone(
    pack: PreparedPack, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    monkeypatch.setattr(compose_module, "PINS_ENABLED", frozenset({"CP-3C"}))
    before = dict(os.environ)
    messages(context_pack(pack, "context-covenant_refinancing.json", sentinel=True), "CP-3C")
    assert dict(os.environ) == before


# ------------------------------------------------------------------------------ the guard

Runner = Callable[[Path, pytest.MonkeyPatch], list[str]]


def _cp2a(tmp: Path, mp: pytest.MonkeyPatch) -> list[str]:
    return list(p2a._journal(tmp, mp, "differs")[3].issues)


def _cp2d(tmp: Path, mp: pytest.MonkeyPatch) -> list[str]:
    return list(p2d._journal(tmp, mp, "differs")[2].issues)


def _cp2e(tmp: Path, _: pytest.MonkeyPatch) -> list[str]:
    pack = p2e._pack(tmp, p2e.CASES["differs"]["context"])
    return list(p2e._validate(pack, p2e._payload("differs")).issues)


def _cp3c(tmp: Path, mp: pytest.MonkeyPatch) -> list[str]:
    store, _, attempt = p3c._run(tmp, mp, "differs")
    return p3c._issues(store, attempt)


def _cp3d(tmp: Path, _: pytest.MonkeyPatch) -> list[str]:
    spec = p3d.CASES["differs"]
    pack = p3d._pack(tmp, spec["context"], spec["base_case"])
    return list(p3d._validate(pack, p3d._payload("differs"), spec["base_case"]).issues)


def _cp4c(tmp: Path, mp: pytest.MonkeyPatch) -> list[str]:
    store, _, attempt = p4c._run(tmp, mp, "differs")
    return p4c._issues(store, attempt)


OWNER_DIFFERS: dict[str, Runner] = {
    "CP-2A": _cp2a,
    "CP-2D": _cp2d,
    "CP-2E": _cp2e,
    "CP-3C": _cp3c,
    "CP-3D": _cp3d,
    "CP-4C": _cp4c,
}


def enabled_without_a_pin_check(
    enabled: Iterable[str], owners: Mapping[str, Runner], tmp: Path, mp: pytest.MonkeyPatch
) -> list[str]:
    """The enabled module ids whose owner's entry validator, run on the oracle's `differs` case,
    emits no `assumptions.<module>.` line: a prompt would invite a pin the owner does not check."""
    unchecked = []
    for module in sorted(enabled):
        prefix = f"assumptions.{module.lower().replace('-', '')}."
        runner = owners.get(module)
        lines = [] if runner is None else runner(tmp / module, mp)
        if not any(line.startswith(prefix) for line in lines):
            unchecked.append(module)
    return unchecked


def test_enabled_modules_check_their_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert not enabled_without_a_pin_check(
        compose_module.PINS_ENABLED, OWNER_DIFFERS, tmp_path, monkeypatch
    )


def test_a_stub_owner_that_emits_no_pin_line_fails_the_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub: dict[str, Runner] = {"CP-9Z": lambda _t, _m: ["some other issue"]}
    assert enabled_without_a_pin_check(["CP-9Z"], stub, tmp_path, monkeypatch) == ["CP-9Z"]
    assert enabled_without_a_pin_check(["CP-9Y"], stub, tmp_path, monkeypatch) == ["CP-9Y"]
