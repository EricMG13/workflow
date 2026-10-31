"""H05: a refused malformed frame must not desynchronise the session sequence."""

import io
import json

import pytest
from test_financial_workflow import make_pack

from deploy_workflow.financial_workflow import FinancialWorkflow
from deploy_workflow.financial_workflow import serve_json_lines as serve_financial
from deploy_workflow.owner_workflow import OwnerWorkflow
from deploy_workflow.owner_workflow import serve_json_lines as serve_owner

# Mirrors host.MAX_ARGUMENT_DEPTH.
DEPTH_BOUND = 100

GOOD = json.dumps(
    {
        "operation": "invoke",
        "tool": "read_pages",
        "arguments": {"source_id": "identity", "first_page": 1, "last_page": 1},
    }
)


def _nested(levels: int) -> str:
    return "[" * levels + "0" + "]" * levels


def _search(arguments_json: str) -> str:
    return '{"operation":"invoke","tool":"search_pack","arguments":' + arguments_json + "}"


def _bad_frames() -> dict[str, str]:
    return {
        "surrogate_query": json.dumps(
            {"operation": "invoke", "tool": "search_pack", "arguments": {"query": "\ud800"}}
        ),
        "surrogate_key": json.dumps(
            {
                "operation": "invoke",
                "tool": "search_pack",
                "arguments": {"query": "x", "\ud800": 1},
            }
        ),
        "deep_args": _search('{"query":"x","extra":' + _nested(210) + "}"),
    }


def _deep_frame(total_depth: int) -> str:
    # `arguments` itself is depth 1, so `extra` holds total_depth - 1 list levels.
    return _search('{"query":"x","extra":' + _nested(total_depth - 1) + "}")


def _run(kind: str, tmp_path, frames: list[str]) -> list[dict]:
    if kind == "owner":
        workflow = OwnerWorkflow.create(
            tmp_path / "store", make_pack(), publication_directory=tmp_path / "model"
        )
        serve = serve_owner
    else:
        workflow = FinancialWorkflow.create(
            tmp_path / "store", make_pack(), model_directory=tmp_path / "model"
        )
        serve = serve_financial
    writer = io.StringIO()
    serve(
        workflow,
        io.StringIO("".join(frame + "\n" for frame in frames)),
        writer,
        destination=tmp_path / "receipt.json",
        participant="h05",
    )
    return [json.loads(line) for line in writer.getvalue().splitlines()]


def _states(replies: list[dict]) -> list[tuple[object, object]]:
    return [(reply.get("status"), reply.get("error_code")) for reply in replies]


@pytest.mark.parametrize("kind", ["owner", "financial"])
@pytest.mark.parametrize("name", ["surrogate_query", "surrogate_key", "deep_args"])
def test_bad_frame_then_good_frame_stays_in_sequence(kind, name, tmp_path):
    replies = _run(kind, tmp_path, [_bad_frames()[name], GOOD])
    assert _states(replies) == [("refused", "bad_arguments"), ("ok", None)]
    assert replies[0]["arguments"] == {}


# search_pack refuses any unknown key at tool level, so a deep `extra` is never "ok".
# A host-level refusal returns arguments == {}; a tool-level refusal keeps the arguments.
@pytest.mark.parametrize("kind", ["owner", "financial"])
def test_frame_at_depth_bound_passes_host_and_is_retained(kind, tmp_path):
    frame = _deep_frame(DEPTH_BOUND)
    replies = _run(kind, tmp_path, [frame, GOOD])
    assert _states(replies) == [("refused", "bad_arguments"), ("ok", None)]
    assert replies[0]["arguments"] == json.loads(frame)["arguments"]


@pytest.mark.parametrize("kind", ["owner", "financial"])
def test_frame_one_level_over_depth_bound_is_refused_by_host(kind, tmp_path):
    replies = _run(kind, tmp_path, [_deep_frame(DEPTH_BOUND + 1), GOOD])
    assert _states(replies) == [("refused", "bad_arguments"), ("ok", None)]
    assert replies[0]["arguments"] == {}


def test_bound_matches_host():
    from deploy_workflow.host import MAX_ARGUMENT_DEPTH

    assert MAX_ARGUMENT_DEPTH == DEPTH_BOUND
