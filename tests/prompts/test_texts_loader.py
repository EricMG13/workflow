"""O6 Task 4 batch 0: the text loader (prompts/texts) and the CP-3D context rows (O6-P24)."""

import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import pytest
from prompt_support import EXISTING, request_for

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


def test_existing_is_the_contracts_plus_the_text_stems() -> None:
    stems = {p.stem for p in compose_module.TEXTS_DIR.glob("*.md")}
    assert set(EXISTING) == set(STEP_CONTRACTS) | stems


# Frozen at HEAD (before the loader): sha256 of the JSON of each STEP_CONTRACTS step's composed
# messages on the o2 pack.
def test_the_twelve_existing_steps_compose_byte_identically(pack: PreparedPack) -> None:
    got = {}
    for step in sorted(STEP_CONTRACTS):
        messages = compose(request_for(step, pack))
        body = json.dumps([[m.role, m.text] for m in messages])
        got[step] = hashlib.sha256(body.encode()).hexdigest()
    assert got == FROZEN


FROZEN: dict[str, str] = {
    "business_context": ("77e144292b8b64791e6a326a9dbfd68de8dd776282549ce823c334c7780f2f93"),
    "committee_challenge": ("20af64f31e55a976174c1f953a6787769b94137307030ef6cadd04fda50e0716"),
    "credit_synthesis": ("ce0a50087423ab9e674d178f243fd0eb54de655ed447651a9b56cc00a14d6702"),
    "financials": ("f42748bd79792c3a1e6e703b36fa2384456eec66ec25f8fe87c95612d9a57022"),
    "integrity_review": ("3bbd8f39400a1ca508f00150c52e3437b55bf9e32a4eead1f839cdfa96925038"),
    "legal_covenants": ("dc57675b1e42b1810ed1a3da99ba2dc70d0698e15aa41af1261c1e108ae6b14f"),
    "narrative": ("2e13063723b8fde9a990002de88f2857155c070c80a4649500d5183e226372fc"),
    "quality": ("007209478b2ffe287277ff755b9d497d101552cf0451eff4bfb854e4b921c058"),
    "readiness": ("8f92e8a5bfe7ea33a91d6112fb28925050b2d3885670fdfbcb968d08e7805fcd"),
    "relative_value": ("e3483e176ff80b2f302311904cdba37d6bfce3e75c2914caf33031d3f1541e22"),
    "source_context": ("1b40c9c60bd152592cf691414ea459416706b842d9e407e166024d382d8d11d8"),
    "source_readiness": ("ea4e4966aee75b656e67c6c07ac46e3cf68b6c8c8d9063ac8316cf111e1d5db6"),
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
