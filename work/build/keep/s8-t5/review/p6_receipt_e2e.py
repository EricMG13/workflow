"""T5 fix-2 review probe 6 (end to end, financial gap run as in
test_missing_source_requires_actual_begin_and_publisher_refusal): one bad tool call first, then the
normal run to write_receipt + verify_financial_slice_receipt. Control: int tool / no bad call.
Exit 1 if a surrogate-tool run cannot seal a receipt while the controls can."""
import sys, tempfile
from pathlib import Path
from test_financial_workflow import start, read_sources, readiness
from deploy_vii.execution import Execution
from deploy_workflow.financial_workflow import verify_financial_slice_receipt
from deploy_workflow.workflow import WorkflowError

def case(bad_call):
    p = Path(tempfile.mkdtemp(prefix="t5e-"))
    w, pack = start(p, gap=True)
    w._participant, w._transport = "t5", "python-api"
    if bad_call:
        r = w.invoke(*bad_call); first = (r["tool"], r["status"], r["error_code"])
    else:
        first = None
    read_sources(w, gap=True)
    assert w.submit_review(readiness(pack, gap=True))["status"] == "valid"
    w.publish_model()
    try:
        rec = w.write_receipt(p / "receipt.json")
        verify_financial_slice_receipt(Execution(p / "store"), rec, model_directory=None)
        return first, "SEALED+VERIFIED"
    except WorkflowError as e:  # probe reports the refusal code, it does not hide it
        return first, "write_receipt refused " + e.code

results = {
    "none": case(None),
    "int_tool": case((5, {"query": "x"})),
    "surrogate_tool": case(("\ud800", {"query": "x"})),
}
for k, v in results.items():
    print(k, v)
sys.exit(0 if all(v[1] == "SEALED+VERIFIED" for v in results.values()) else 1)
