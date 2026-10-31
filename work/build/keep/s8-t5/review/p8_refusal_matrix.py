"""T5 round-3 re-review probe 8: name x argument refusal matrix, financial direct API,
end to end (write_receipt + verify_financial_slice_receipt), as in p6. Each case makes one
call before the normal gap run. Prints the first receipt and the seal result. Exit 1 if any
case cannot be sealed+verified."""
import sys, tempfile
from pathlib import Path
from test_financial_workflow import start, read_sources, readiness
from deploy_vii.execution import Execution
from deploy_workflow.financial_workflow import verify_financial_slice_receipt
from deploy_workflow.workflow import WorkflowError


def deep(n):
    v = []
    for _ in range(n):
        v = [v]
    return v


class S(str):
    pass


NAMES = {"search_pack": "search_pack", "read_pages": "read_pages",
         "extract_statements": "extract_statements", "empty": "", "unknown": "foo",
         "int": 5, "none": None, "surrogate": "\ud800", "str_subclass": S("search_pack")}
ARGS = {"good": {"query": "x"}, "depth101": {"query": "x", "extra": deep(105)},
        "surrogate_val": {"query": "\ud800"}, "non_dict": [1], "empty": {}}


def case(name, args):
    p = Path(tempfile.mkdtemp(prefix="t5m-"))
    w, pack = start(p, gap=True)
    w._participant, w._transport = "t5", "python-api"
    r = w.invoke(name, args)
    first = (r["tool"], r["arguments"] if len(repr(r["arguments"])) < 40 else "<big>",
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
for nk, n in NAMES.items():
    for ak, a in ARGS.items():
        first, result = case(n, a)
        flag = "" if result == "SEALED+VERIFIED" else "  <-- DESYNC"
        bad |= bool(flag)
        print(f"{nk:18} {ak:14} {first} {result}{flag}")
sys.exit(bad)
