"""T5 round-3 re-review probe 10: a non-str name whose __eq__ says it equals "" passes the
`tool_name != ""` test at host.py:1072, so with bad arguments it is still refused
("", {}, bad_arguments), the receipt the item-88 ruling says must not exist for a non-str
name. End to end as p6. Exit 1 if the run cannot be sealed+verified."""
import sys, tempfile
from pathlib import Path
from test_financial_workflow import start, read_sources, readiness
from deploy_vii.execution import Execution
from deploy_workflow.financial_workflow import verify_financial_slice_receipt
from deploy_workflow.workflow import WorkflowError


class LooksEmpty:
    def __eq__(self, other):
        return other == ""
    __hash__ = None


p = Path(tempfile.mkdtemp(prefix="t5q-"))
w, pack = start(p, gap=True)
w._participant, w._transport = "t5", "python-api"
r = w.invoke(LooksEmpty(), [1])
print("first:", (r["tool"], r["arguments"], r["status"], r["error_code"]))
read_sources(w, gap=True)
assert w.submit_review(readiness(pack, gap=True))["status"] == "valid"
w.publish_model()
try:
    rec = w.write_receipt(p / "receipt.json")
    verify_financial_slice_receipt(Execution(p / "store"), rec, model_directory=None)
    print("SEALED+VERIFIED")
    sys.exit(0)
except WorkflowError as e:  # reported, not hidden
    print("REFUSED", e.code, " <-- DESYNC")
    sys.exit(1)
