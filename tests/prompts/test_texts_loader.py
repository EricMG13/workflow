"""O6 Task 4 batch 0: the text loader (prompts/texts) and the CP-3D context rows (O6-P24)."""

import hashlib
import importlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
from prompt_support import CONTRACT_STEPS, EXISTING, request_for, steps_with_text

from deploy_vii.live.prompts import STEP_CONTRACTS, PromptError
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owners import cp3d
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
# gives the old message.
def test_the_twelve_existing_steps_compose_byte_identically(pack: PreparedPack) -> None:
    got = {}
    for step in sorted(STEP_CONTRACTS):
        messages = compose(request_for(step, pack))
        body = json.dumps([[m.role, m.text] for m in messages])
        got[step] = hashlib.sha256(body.encode()).hexdigest()
    assert got == FROZEN


FROZEN: dict[str, str] = {
    "business_context": ("82190163b19dd9c5f12985744fce16f94e0a94ef088115295a958829007b71e1"),
    "committee_challenge": ("59ae66e95c779b7a4461705bf9e6e5a6e0755c9f0f639cd2f190bc0152f38896"),
    "credit_synthesis": ("209914c5b5b6662bd897f2b92d9dc3ae90286be0f30153aa5f54ec235fa2320c"),
    "financials": ("985eafab692bb87012ef143cabaee6d868895d532f05bc9d242e9a2acd683e4a"),
    "integrity_review": ("1b71ce3d77e672011f2234c363def35ecd38e3f7a0bf2322a6ec38c876b2ffcf"),
    "legal_covenants": ("d274462457744ea7fbc7b91bcd8ad38e9f3b2310671f8b39090daa8680477a44"),
    "narrative": ("d4677ff1aa1cbb825ca73c54ecd6743ed53164f8d072764bba0a7ff2035499a0"),
    "quality": ("8a4d88522e09bdc0d58afc6e484e32455621e37d31c6abb07d6294586e6afb56"),
    "readiness": ("83baf9fa4a883bb73c92231802f52323129620bd8a9e0c81c0a215cd6fc5a492"),
    "relative_value": ("b8693476b0f4e65871ddb987d1288c2a2f24641ee24a68eb90b4fa1c13454f52"),
    "source_context": ("6a57450bfd58fef779cc44b2da69e81f76ce150219ab26efb17e337f1807efee"),
    "source_readiness": ("2c2f595691b8cd8e7e31dd2b7f447fc50d9b0e4ecb409907c9115bef1d644ea0"),
}


def context_text(name: str) -> str:
    return compose(request_for(NEW, ctx.context_pack(name), context=None))[1].text


def rows_block(message: str) -> list[dict[str, str]]:
    start = message.index("<<<CONTEXT id=context-rows")
    body = message[message.index(">>>", start) + 3 : message.index("<<<END>>>", start)]
    return json.loads(body)  # type: ignore[no-any-return]


@pytest.mark.parametrize("name", ["observed-and-talk", "stale", "unmatched"])
def test_the_block_lists_the_offered_rows_in_order(texts: Path, name: str) -> None:
    (texts / f"{NEW}.md").write_text(TEXT, encoding="utf-8")
    offers = cp3d.context_offers(ctx.context_pack(name))
    expected = [
        {
            "row": row,
            "kind": o.kind,
            "facility_id": offers.facilities[row],
            "as_of": offers.dates[row].isoformat(),
        }
        for row, o in offers.observations.items()
    ]
    assert expected
    assert rows_block(context_text(name)) == expected


@pytest.mark.parametrize("name", ["observed-and-talk", "stale", "unmatched"])
def test_the_block_holds_no_figure(texts: Path, name: str) -> None:
    (texts / f"{NEW}.md").write_text(TEXT, encoding="utf-8")
    message = context_text(name)
    levels = {
        o.level_text for o in cp3d.context_offers(ctx.context_pack(name)).observations.values()
    }
    assert levels
    for level in levels:
        assert level not in message


def test_no_context_source_no_block(texts: Path, pack: PreparedPack) -> None:
    (texts / f"{NEW}.md").write_text(TEXT, encoding="utf-8")
    assert "context-rows" not in compose(request_for(NEW, pack))[1].text


def test_offer_errors_no_block(texts: Path) -> None:
    (texts / f"{NEW}.md").write_text(TEXT, encoding="utf-8")
    assert cp3d.context_offers(ctx.context_pack("bad-bytes")).errors
    assert "context-rows" not in context_text("bad-bytes")


def test_contract_steps_ignore_a_loaded_text(texts: Path) -> None:
    """A step whose text is a file is not a STEP_CONTRACTS step: a test that reads
    ``STEP_CONTRACTS[step]`` is parametrized over CONTRACT_STEPS, which a texts file never joins."""
    (texts / f"{NEW}.md").write_text(TEXT, encoding="utf-8")
    assert NEW in steps_with_text(texts)
    assert NEW not in CONTRACT_STEPS
    assert all(step in STEP_CONTRACTS for step in CONTRACT_STEPS)
