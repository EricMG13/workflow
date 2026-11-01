"""O6 Task 4 batch 0: the text loader (prompts/texts) and the CP-3D context rows (O6-P24)."""

import hashlib
import importlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
from b29_strip import B29_SPANS, undo_b29
from b30_strip import B30_SPANS, undo_b30
from b34_strip import B34_SPANS, undo_b34
from merge_strip import undo_merged_contract
from p5_strip import undo_p5
from p5t6_strip import undo_p5t6_context, undo_p5t6_wording
from prompt_support import CONTRACT_STEPS, EXISTING, request_for, steps_with_text

from deploy_vii.live.prompts import STEP_CONTRACTS, PromptError
from deploy_vii.preparation import PreparedPack
from deploy_workflow.prompts import NoPrompt, compose

compose_module: Any = importlib.import_module("deploy_workflow.prompts.compose")
ctx: Any = importlib.import_module("test_cp3d_context")
NEW = "market_implied"
TEXT = "The market_implied test text.\n"
CASE = Path(ctx.CASE)


@pytest.fixture
def texts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "texts"
    directory.mkdir()
    monkeypatch.setattr(compose_module, "TEXTS_DIR", directory)
    return directory


def system_of(pack: PreparedPack, step: str = NEW) -> str:
    return compose(request_for(step, pack))[0].text


def test_a_found_text_is_the_step_contract(texts: Path, pack: PreparedPack) -> None:
    (texts / f"{NEW}.md").write_text(TEXT, encoding="utf-8")
    assert TEXT.strip() in system_of(pack)
    assert compose_module.has_prompt(NEW)


LETTERED = "Method.\nStep rules:\na. [market_implied.1] First.\nb. [market_implied.2] Second.\n"


def test_a_loaded_text_gets_no_letter_index(texts: Path, pack: PreparedPack) -> None:
    """The M2 letter index serves STEP_CONTRACTS steps only; a loaded text has real tags."""
    (texts / f"{NEW}.md").write_text(LETTERED, encoding="utf-8")
    system = system_of(pack)
    assert "[market_implied.1]" in system
    assert not re.search(rf"\[{NEW}\.[a-z]\]", system)


def test_a_contract_step_keeps_its_letter_index(pack: PreparedPack) -> None:
    step = CONTRACT_STEPS[0]
    system = compose(request_for(step, pack))[0].text
    assert re.search(rf"\[{step}\.a\]=a", system)


def test_a_text_is_read_as_utf8(texts: Path, pack: PreparedPack) -> None:
    (texts / f"{NEW}.md").write_bytes("Crédit — text\n".encode())
    assert "Crédit — text" in system_of(pack)


def test_a_missing_text_is_no_prompt(texts: Path, pack: PreparedPack) -> None:
    with pytest.raises(NoPrompt) as caught:
        system_of(pack)
    assert caught.value.step_id == NEW
    assert not compose_module.has_prompt(NEW)


@pytest.mark.parametrize("body", ["", "  \n\t\n"])
def test_an_empty_text_is_refused(texts: Path, pack: PreparedPack, body: str) -> None:
    (texts / f"{NEW}.md").write_text(body, encoding="utf-8")
    with pytest.raises(PromptError, match="empty"):
        system_of(pack)


def test_a_file_for_a_step_that_has_a_contract_is_refused(texts: Path, pack: PreparedPack) -> None:
    (texts / "narrative.md").write_text(TEXT, encoding="utf-8")
    with pytest.raises(PromptError, match="narrative"):
        system_of(pack, "narrative")


def test_every_text_file_ends_with_exactly_one_newline() -> None:
    for path in sorted(compose_module.TEXTS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n") and not text.endswith("\n\n"), path.name


def test_existing_is_the_contracts_plus_the_text_stems() -> None:
    stems = {p.stem for p in compose_module.TEXTS_DIR.glob("*.md")}
    assert set(EXISTING) == set(STEP_CONTRACTS) | stems


# Frozen at HEAD (before the loader): sha256 of the JSON of each STEP_CONTRACTS step's composed
# messages on the o2 pack. Re-frozen by O6 Task 5 (T5-D) for the [compose.<id>] tokens and CP-0's
# G8 block; tests/prompts/test_g8.py keeps the old digests and shows that removing exactly those
# gives the old message. relative_value was re-frozen by Phase 3 Task 4 (the CP3_EVIDENCE_RULE
# reword, B17 item 3); tests/prompts/test_context_evidence.py keeps its old digest and shows that
# putting back the old rule text and removing the evidence block gives the old message.
# relative_value was re-frozen again by B29 (the method text and rule d name `basis.context_rows`);
# test_the_b29_wording_is_the_only_change_to_the_frozen_message keeps the previous digest.
# And again by B30 (the market-observation and preference rules, the method text and the Basis
# schema text name `basis.context_rows`); test_the_b30_wording_is_the_only_change_to_the_frozen_
# message keeps the digest after B29. And again by B34 (the preference line under "What to return"
# names `basis.context_rows`); test_the_b34_wording_is_the_only_change_to_the_frozen_message keeps
# the digest after B30.
# financials and narrative were re-frozen by the O6 merge integration (ruling M-R1: the merged
# restricted-cash change in their contract text and schema); test_the_merged_restricted_cash_change_
# is_the_only_change keeps their old digests and shows that undoing exactly it gives the old message.
def test_the_twelve_existing_steps_compose_byte_identically(pack: PreparedPack) -> None:
    got = {}
    for step in sorted(STEP_CONTRACTS):
        messages = compose(request_for(step, pack))
        body = json.dumps([[m.role, m.text] for m in messages])
        got[step] = hashlib.sha256(body.encode()).hexdigest()
    assert got == FROZEN


# The answer key (M-R1): the digests of these two steps before the merged restricted-cash ids.
# Never edited.
PRE_MERGE_FROZEN: dict[str, str] = {
    "financials": "985eafab692bb87012ef143cabaee6d868895d532f05bc9d242e9a2acd683e4a",
    "narrative": "d4677ff1aa1cbb825ca73c54ecd6743ed53164f8d072764bba0a7ff2035499a0",
}


@pytest.mark.parametrize("step", sorted(PRE_MERGE_FROZEN))
def test_the_merged_restricted_cash_change_is_the_only_change_to_the_frozen_message(
    pack: PreparedPack, step: str
) -> None:
    messages = compose(request_for(step, pack))
    system, user = messages[0], messages[1]
    body = json.dumps(
        [[system.role, undo_merged_contract(step, system.text)], [user.role, user.text]]
    )
    assert hashlib.sha256(body.encode()).hexdigest() == PRE_MERGE_FROZEN[step]


# The answer key (B29): relative_value's digest before the CP-3 method text and rule d named
# `basis.context_rows` (the FROZEN value from the O3 release cut e1d8b5a2). Never edited.
PRE_B29_FROZEN: dict[str, str] = {
    "relative_value": "dc90b63a7ee77bd4482fdadba8b6e25a5492951897753e2e4a828af3ea9dd729",
}


@pytest.mark.parametrize("step", sorted(PRE_B29_FROZEN))
def test_the_b29_wording_is_the_only_change_to_the_frozen_message(
    pack: PreparedPack, step: str
) -> None:
    messages = compose(request_for(step, pack))
    system, user = messages[0], messages[1]
    text = undo_b29(step, undo_b30(step, undo_b34(step, system.text)))
    body = json.dumps([[system.role, text], [user.role, user.text]])
    assert hashlib.sha256(body.encode()).hexdigest() == PRE_B29_FROZEN[step]


def test_the_b29_strip_removes_only_spans_the_message_holds(pack: PreparedPack) -> None:
    for step, spans in B29_SPANS.items():
        system = undo_b30(step, undo_b34(step, compose(request_for(step, pack))[0].text))
        assert all(system.count(span) == count for span, count, _ in spans)


# The answer key (B30): relative_value's digest before the market-observation and preference rules,
# the method text and the `Basis` schema text named `basis.context_rows` (the FROZEN value after
# B29, e7d2c02b). Never edited.
PRE_B30_FROZEN: dict[str, str] = {
    "relative_value": "fe12a09cfc3b8c3b37a9f27961b7feb192f4fb3a59a1a1653ba952b9cc399b0b",
}


@pytest.mark.parametrize("step", sorted(PRE_B30_FROZEN))
def test_the_b30_wording_is_the_only_change_to_the_frozen_message(
    pack: PreparedPack, step: str
) -> None:
    messages = compose(request_for(step, pack))
    system, user = messages[0], messages[1]
    body = json.dumps(
        [[system.role, undo_b30(step, undo_b34(step, system.text))], [user.role, user.text]]
    )
    assert hashlib.sha256(body.encode()).hexdigest() == PRE_B30_FROZEN[step]


def test_the_b30_strip_removes_only_spans_the_message_holds(pack: PreparedPack) -> None:
    for step, spans in B30_SPANS.items():
        system = undo_b34(step, compose(request_for(step, pack))[0].text)
        assert all(system.count(span) == count for span, count, _ in spans)


# The answer key (B34): relative_value's digest before the preference line named
# `basis.context_rows` (the FROZEN value after B30, f3b1aba5). Never edited.
PRE_B34_FROZEN: dict[str, str] = {
    "relative_value": "f3b1aba5daffca2ebeebe195f6bb4daab5115994007ab6561cba2629928b1c30",
}


@pytest.mark.parametrize("step", sorted(PRE_B34_FROZEN))
def test_the_b34_wording_is_the_only_change_to_the_frozen_message(
    pack: PreparedPack, step: str
) -> None:
    messages = compose(request_for(step, pack))
    system, user = messages[0], messages[1]
    body = json.dumps([[system.role, undo_b34(step, system.text)], [user.role, user.text]])
    assert hashlib.sha256(body.encode()).hexdigest() == PRE_B34_FROZEN[step]


def test_the_b34_strip_removes_only_spans_the_message_holds(pack: PreparedPack) -> None:
    for step, spans in B34_SPANS.items():
        system = compose(request_for(step, pack))[0].text
        assert all(system.count(span) == count for span, count, _ in spans)


# The answer key (Phase 5 Task 1, P5T1-R6): source_readiness's digest before the draft and context
# authority line `[source_readiness.p5]` joined the CP-0 message (the FROZEN value after B30).
# Never edited.
PRE_P5T1_FROZEN: dict[str, str] = {
    "source_readiness": "f79002b0b6dba89b493fdd93f8baf1c8aa914bd71102370c1d0a6e6fca62f2b6",
}


@pytest.mark.parametrize("step", sorted(PRE_P5T1_FROZEN))
def test_the_p5_line_is_the_only_change_to_the_frozen_message(
    pack: PreparedPack, step: str
) -> None:
    messages = compose(request_for(step, pack))
    system, user = messages[0], messages[1]
    # Phase 5 Task 6 (P5T6-R3): undo CP-0's `attachments` key first, then the P5 line.
    user_text = undo_p5t6_context(step, user.text)
    body = json.dumps([[system.role, undo_p5(step, system.text)], [user.role, user_text]])
    assert hashlib.sha256(body.encode()).hexdigest() == PRE_P5T1_FROZEN[step]


# The answer key (Phase 5 Task 6, P5T6-R1 and R3): the digests of these two steps before CP-0's
# run-context block gained `attachments` and CP-4's method text named draft sources (the FROZEN
# values after Phase 5 Task 1 for source_readiness and after B30 for legal_covenants). Never edited.
PRE_P5T6_FROZEN: dict[str, str] = {
    "legal_covenants": "d274462457744ea7fbc7b91bcd8ad38e9f3b2310671f8b39090daa8680477a44",
    "source_readiness": "cf819db26dab80a34951dde352cb95f10bb38fb1ce01684e293bd856d3ccb743",
}


@pytest.mark.parametrize("step", sorted(PRE_P5T6_FROZEN))
def test_the_p5t6_changes_are_the_only_change_to_the_frozen_message(
    pack: PreparedPack, step: str
) -> None:
    messages = compose(request_for(step, pack))
    system, user = messages[0], messages[1]
    body = json.dumps(
        [
            [system.role, undo_p5t6_wording(step, system.text)],
            [user.role, undo_p5t6_context(step, user.text)],
        ]
    )
    assert hashlib.sha256(body.encode()).hexdigest() == PRE_P5T6_FROZEN[step]


# source_readiness and legal_covenants were re-frozen by Phase 5 Task 6 (CP-0's run-context block
# shows `attachments`; CP-4's method text names draft sources); PRE_P5T6_FROZEN keeps the digests
# before, and test_the_p5t6_changes_are_the_only_change_to_the_frozen_message undoes exactly them.
FROZEN: dict[str, str] = {
    "business_context": ("82190163b19dd9c5f12985744fce16f94e0a94ef088115295a958829007b71e1"),
    "committee_challenge": ("59ae66e95c779b7a4461705bf9e6e5a6e0755c9f0f639cd2f190bc0152f38896"),
    "credit_synthesis": ("209914c5b5b6662bd897f2b92d9dc3ae90286be0f30153aa5f54ec235fa2320c"),
    "financials": ("8d196274b78c7f5444f3a9e130618be05b74d5d800a703654abbc445926dd315"),
    "integrity_review": ("1b71ce3d77e672011f2234c363def35ecd38e3f7a0bf2322a6ec38c876b2ffcf"),
    "legal_covenants": ("22e7630bb28415fcd27aa005767f5767060fcfecff5dc1cde036a5e4401c7d39"),
    "narrative": ("3e8d87b8f6e5085f539e94e7184db2e89feb7cc45b4e03e897925dca24d819f7"),
    "quality": ("8a4d88522e09bdc0d58afc6e484e32455621e37d31c6abb07d6294586e6afb56"),
    "readiness": ("83baf9fa4a883bb73c92231802f52323129620bd8a9e0c81c0a215cd6fc5a492"),
    "relative_value": ("d9202926890f8f011bcbf97fc40334e2b576fd57959f460d75c27b204262cba0"),
    "source_context": ("6a57450bfd58fef779cc44b2da69e81f76ce150219ab26efb17e337f1807efee"),
    "source_readiness": ("bc8cd4d8611fe907bfad6bd8754b458730d1551cca98aec8822277f440d4658b"),
}


# The CP-3D rows block (O6-P24 ``context-rows``: id, kind, facility, date only) became Python's
# one fenced ``context-evidence`` block in Phase 3 Task 4 (it now carries the quote and level text
# too, for the model to refer to by row id); tests/prompts/test_context_evidence.py checks it.


def test_contract_steps_ignore_a_loaded_text(texts: Path) -> None:
    """A step whose text is a file is not a STEP_CONTRACTS step: a test that reads
    ``STEP_CONTRACTS[step]`` is parametrized over CONTRACT_STEPS, which a texts file never joins."""
    (texts / f"{NEW}.md").write_text(TEXT, encoding="utf-8")
    assert NEW in steps_with_text(texts)
    assert NEW not in CONTRACT_STEPS
    assert all(step in STEP_CONTRACTS for step in CONTRACT_STEPS)
