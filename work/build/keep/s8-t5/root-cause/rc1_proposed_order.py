"""T5 root-cause probe 1. Runs the p8-style matrix (financial direct API, end to end:
write_receipt + verify_financial_slice_receipt) plus p9(a) and p10, against either the
current SourceSession.invoke (argv[1] == "current") or the proposed check order patched in
(argv[1] == "proposed"). Exit 1 if any case cannot seal+verify or a caller object escapes."""
import sys, tempfile
from pathlib import Path
from test_financial_workflow import start, read_sources, readiness
from deploy_vii.execution import Execution
from deploy_vii.live.prompts import PromptError
from deploy_workflow import host
from deploy_workflow.host import SourceSession, _json_arguments
from deploy_workflow.tools.source import SourceError
from deploy_workflow.financial_workflow import verify_financial_slice_receipt
from deploy_workflow.workflow import WorkflowError
from rc_fix import proposed_invoke


if sys.argv[1:] == ["proposed"]:
    SourceSession.invoke = proposed_invoke


def deep(n):
    v = []
    for _ in range(n):
        v = [v]
    return v


class S(str):
    pass


class LooksEmpty:
    def __eq__(self, other):
        return other == ""
    __hash__ = None


class Hostile:
    def __ne__(self, other):
        raise RuntimeError("caller code ran")
    def __eq__(self, other):
        raise RuntimeError("caller code ran")
    __hash__ = None


NAMES = {"offered": "search_pack", "empty": "", "unknown": "foo",
         "offered_not_here": "extract_statements", "int": 5, "str_subclass": S("search_pack"),
         "looks_empty": LooksEmpty(), "hostile": Hostile()}
ARGS = {"good": {"query": "x"}, "depth": {"query": "x", "extra": deep(105)},
        "surrogate_val": {"query": "\ud800"}, "non_dict": [1], "empty": {}}


def case(name, args):
    p = Path(tempfile.mkdtemp(prefix="t5rc-"))
    w, pack = start(p, gap=True)
    w._participant, w._transport = "t5", "python-api"
    try:
        r = w.invoke(name, args)
    except Exception as e:  # reported as a failure, not hidden
        return ("ESCAPED", type(e).__name__), "FAIL"
    first = (r["tool"], r["arguments"] if len(repr(r["arguments"])) < 30 else "<big>",
             r["status"], r["error_code"])
    read_sources(w, gap=True)
    assert w.submit_review(readiness(pack, gap=True))["status"] == "valid"
    w.publish_model()
    try:
        rec = w.write_receipt(p / "receipt.json")
        verify_financial_slice_receipt(Execution(p / "store"), rec, model_directory=None)
        return first, "SEALED+VERIFIED"
    except WorkflowError as e:  # reported, not hidden
        return first, "REFUSED " + e.code


bad = 0
cases = [(nk, n, ak, a) for nk, n in NAMES.items() for ak, a in ARGS.items()]
# unencodable-name column: each str name with a lone surrogate appended
for nk, n in NAMES.items():
    if type(n) is str:
        cases.append((nk, n + "\ud800", "unencodable_name", {"query": "x"}))
for nk, n, ak, a in cases:
    first, result = case(n, a)
    flag = "" if result == "SEALED+VERIFIED" else "  <-- FAIL"
    bad |= bool(flag)
    print(f"{nk:17} {ak:16} {first} {result}{flag}")
sys.exit(bad)
