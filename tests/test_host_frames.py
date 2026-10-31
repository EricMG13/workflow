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
        "surrogate_tool": json.dumps(
            {
                "operation": "invoke",
                "tool": "\ud800",
                "arguments": {"query": "x"},
            }
        ),
        "surrogate_tool_bad_args": json.dumps(
            {"operation": "invoke", "tool": "\ud800", "arguments": [1]}
        ),
        "non_str_tool_bad_args": json.dumps({"operation": "invoke", "tool": 5, "arguments": [1]}),
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


# An unrepresentable tool name is refused not_permitted with "" and {}: exactly what
# receipt verification produces when it replays invoke(call.tool, call.arguments).
UNREPRESENTABLE_TOOL = {"surrogate_tool", "surrogate_tool_bad_args", "non_str_tool_bad_args"}


@pytest.mark.parametrize("kind", ["owner", "financial"])
@pytest.mark.parametrize(
    "name",
    [
        "surrogate_query",
        "surrogate_key",
        "surrogate_tool",
        "surrogate_tool_bad_args",
        "non_str_tool_bad_args",
        "deep_args",
    ],
)
def test_bad_frame_then_good_frame_stays_in_sequence(kind, name, tmp_path):
    replies = _run(kind, tmp_path, [_bad_frames()[name], GOOD])
    code = "not_permitted" if name in UNREPRESENTABLE_TOOL else "bad_arguments"
    assert _states(replies) == [("refused", code), ("ok", None)]
    assert replies[0]["arguments"] == {}
    if name in UNREPRESENTABLE_TOOL:
        assert replies[0]["tool"] == ""


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


def test_surrogate_tool_run_can_still_be_sealed_and_verified(tmp_path):
    """Financial gap run (as in the financial workflow tests): a refused surrogate-tool
    call must replay during receipt verification. Owner has no equivalent helper here;
    its replay is covered by the verification loop over `_verify_calls_reads`."""
    from test_financial_workflow import read_sources, readiness, start

    from deploy_vii.execution import Execution
    from deploy_workflow.financial_workflow import verify_financial_slice_receipt

    workflow, pack = start(tmp_path, gap=True)
    workflow._participant, workflow._transport = "h05", "python-api"
    refused = workflow.invoke("\ud800", {"query": "x"})
    assert (refused["status"], refused["error_code"]) == ("refused", "not_permitted")
    read_sources(workflow, gap=True)
    assert workflow.submit_review(readiness(pack, gap=True))["status"] == "valid"
    workflow.publish_model()
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    verify_financial_slice_receipt(Execution(tmp_path / "store"), receipt, model_directory=None)


def _deep(depth):
    value = []
    for _ in range(depth):
        value = [value]
    return value


def _seal_and_verify(workflow, pack, tmp_path):
    from test_financial_workflow import read_sources, readiness

    from deploy_vii.execution import Execution
    from deploy_workflow.financial_workflow import verify_financial_slice_receipt

    read_sources(workflow, gap=True)
    assert workflow.submit_review(readiness(pack, gap=True))["status"] == "valid"
    workflow.publish_model()
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    verify_financial_slice_receipt(Execution(tmp_path / "store"), receipt, model_directory=None)


_REFUSED_ARGUMENTS = {
    "deep": lambda: {"query": "x", "extra": _deep(105)},
    "surrogate_value": lambda: {"query": "\ud800"},
    "non_dict": lambda: [1],
}


@pytest.mark.parametrize("name", ["search_pack", "", "foo", "extract_statements"])
@pytest.mark.parametrize("kind", ["deep", "surrogate_value", "non_dict", "unencodable_name"])
def test_refused_arguments_replay_to_the_same_receipt(tmp_path, name, kind):
    """Replay re-runs invoke(name, {}); a refused-arguments receipt must carry the code
    stage(name, {}) gives: bad_arguments if the name is offered, else not_permitted."""
    from test_financial_workflow import start

    workflow, pack = start(tmp_path, gap=True)
    workflow._participant, workflow._transport = "t5", "python-api"
    if kind == "unencodable_name":
        reply = workflow.invoke(name + "\ud800", {"query": "x"})
        expected = ("", {}, "refused", "not_permitted")
    else:
        reply = workflow.invoke(name, _REFUSED_ARGUMENTS[kind]())
        code = "bad_arguments" if name == "search_pack" else "not_permitted"
        expected = (name, {}, "refused", code)
    assert (reply["tool"], reply["arguments"], reply["status"], reply["error_code"]) == expected
    _seal_and_verify(workflow, pack, tmp_path)


class _Hostile:
    __hash__ = None

    def __eq__(self, other):
        raise RuntimeError("caller code ran")

    def __ne__(self, other):
        raise RuntimeError("caller code ran")


class _LooksEmpty:
    __hash__ = None

    def __eq__(self, other):
        return other == ""


@pytest.mark.parametrize("make_name", [_Hostile, _LooksEmpty])
def test_non_str_tool_name_with_deep_arguments_is_refused_and_seals(tmp_path, make_name):
    from test_financial_workflow import start

    workflow, pack = start(tmp_path, gap=True)
    workflow._participant, workflow._transport = "t5", "python-api"
    reply = workflow.invoke(make_name(), _deep(105))
    assert (reply["tool"], reply["arguments"], reply["error_code"]) == ("", {}, "not_permitted")
    _seal_and_verify(workflow, pack, tmp_path)
