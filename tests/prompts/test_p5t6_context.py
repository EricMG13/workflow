"""Phase 5 Task 6 (P5T1-R9): CP-0's run-context block also shows `attachments.legal_documents`.

The answer key is the frozen context oracle: `cases/context-attachments-owner/context-*.json`
declare the mode, and the block must show exactly what the file declares. Only CP-0 gets the key.
"""

import json
from pathlib import Path

import pytest
from prompt_support import request_for

from deploy_vii.preparation import PreparedPack
from deploy_workflow.context import load_context
from deploy_workflow.prompts.compose import compose
from deploy_workflow.prompts.fence import cp0_run_context_block, run_context_block

CASE = Path(__file__).resolve().parents[2] / "cases" / "context-attachments-owner"
MODES = {
    "context-draft.json": "draft",
    "context-executed.json": "executed",
    "context-none.json": "none",
}


def body_of(rendered: str) -> dict[str, object]:
    loaded: dict[str, object] = json.loads(
        rendered.split(">>>\n", 1)[1].rsplit("\n<<<END>>>", 1)[0]
    )
    return loaded


@pytest.mark.parametrize("name", sorted(MODES))
def test_the_cp0_block_shows_the_declared_legal_documents_mode(name: str) -> None:
    raw = json.loads((CASE / name).read_text(encoding="utf-8"))
    assert raw["attachments"]["legal_documents"] == MODES[name]
    ctx = load_context((CASE / name).read_bytes())
    assert body_of(cp0_run_context_block(ctx))["attachments"] == {"legal_documents": MODES[name]}


def test_the_plain_block_never_carries_attachments() -> None:
    ctx = load_context((CASE / "context-draft.json").read_bytes())
    assert "attachments" not in body_of(run_context_block(ctx))
    cp0 = body_of(cp0_run_context_block(ctx))
    assert {k: v for k, v in cp0.items() if k != "attachments"} == body_of(run_context_block(ctx))


def test_the_mode_is_a_fenced_json_value_never_a_line() -> None:
    ctx = load_context((CASE / "context-draft.json").read_bytes())
    rendered = cp0_run_context_block(ctx)
    assert '"legal_documents": "draft"' in rendered
    assert "legal_documents" not in [line.strip() for line in rendered.splitlines()]


def test_only_the_cp0_message_carries_the_mode(pack: PreparedPack) -> None:
    for step in ("source_readiness", "source_context", "legal_covenants", "readiness"):
        user = compose(request_for(step, pack))[1].text
        assert ('"attachments"' in user) == (step == "source_readiness"), step
