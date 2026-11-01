"""H05 desired behaviour: after a refused malformed frame, a later valid frame succeeds.
Exits 1 while the defect is present. Also prints where the owner-level exception arises."""
import io, json, sys, tempfile, traceback
from pathlib import Path
from test_financial_workflow import make_pack
from deploy_workflow.owner_workflow import OwnerWorkflow, serve_json_lines as serve_owner
from deploy_workflow.financial_workflow import FinancialWorkflow, serve_json_lines as serve_fin

root = Path(tempfile.mkdtemp(prefix="h05-"))
good = {"operation": "invoke", "tool": "read_pages",
        "arguments": {"source_id": "identity", "first_page": 1, "last_page": 1}}
bads = {
    "surrogate_query": json.dumps({"operation": "invoke", "tool": "search_pack", "arguments": {"query": "\ud800"}}),
    "surrogate_key": json.dumps({"operation": "invoke", "tool": "search_pack", "arguments": {"query": "x", "\ud800": 1}}),
    "deep_args": '{"operation":"invoke","tool":"search_pack","arguments":{"query":"x","extra":' + "[" * 210 + "0" + "]" * 210 + "}}",
}
failures = []
for wname, cls, serve in [("owner", OwnerWorkflow, serve_owner), ("financial", FinancialWorkflow, serve_fin)]:
    for bname, bad in bads.items():
        p = root / wname / bname
        kw = {"publication_directory": p / "model"} if wname == "owner" else {"model_directory": p / "model"}
        w = cls.create(p / "store", make_pack(), **kw)
        reader = io.StringIO(bad + "\n" + json.dumps(good) + "\n")
        writer = io.StringIO()
        serve(w, reader, writer, destination=p / "receipt.json", participant="h05")
        replies = [json.loads(s) for s in writer.getvalue().splitlines()]
        states = [(r.get("status"), r.get("error_code")) for r in replies]
        print(wname, bname, states)
        if states[1] != ("ok", None):
            failures.append((wname, bname, states))

# locate the owner-level raise for the surrogate case (direct call, no transport catch)
p = root / "trace"
w = OwnerWorkflow.create(p / "store", make_pack(), publication_directory=p / "model")
w._participant, w._transport = "h05", "bounded-json-lines/1"
try:
    w.invoke("search_pack", {"query": "\ud800"})
    print("direct invoke returned")
except Exception as e:
    tb = traceback.extract_tb(e.__traceback__)
    print("direct invoke raised", type(e).__name__, "at", [(f.filename.split('/')[-1], f.lineno, f.name) for f in tb][-4:])
print("session sequence", w._session._sequence, "owner epoch calls", len(w._epoch_calls))
if failures:
    print("DEFECT PRESENT:", len(failures), "cases desynchronised")
    sys.exit(1)
print("OK: all later valid calls succeeded")
