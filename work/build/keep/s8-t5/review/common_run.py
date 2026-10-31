"""Shared runner for the T5 review probes: send frames to owner/financial serve_json_lines."""
import io, json, tempfile
from pathlib import Path
from test_financial_workflow import make_pack
from deploy_workflow.owner_workflow import OwnerWorkflow, serve_json_lines as so
from deploy_workflow.financial_workflow import FinancialWorkflow, serve_json_lines as sf

GOOD = json.dumps({"operation": "invoke", "tool": "read_pages",
                   "arguments": {"source_id": "identity", "first_page": 1, "last_page": 1}})
RECEIPT = json.dumps({"operation": "write_receipt"})


def run(kind, frames):
    root = Path(tempfile.mkdtemp(prefix="t5r-"))
    if kind == "owner":
        w = OwnerWorkflow.create(root / "store", make_pack(), publication_directory=root / "model")
        serve = so
    else:
        w = FinancialWorkflow.create(root / "store", make_pack(), model_directory=root / "model")
        serve = sf
    out = io.StringIO()
    serve(w, io.StringIO("".join(f + "\n" for f in frames)), out,
          destination=root / "receipt.json", participant="t5r")
    replies = [json.loads(l) for l in out.getvalue().splitlines()]
    return [(r.get("status"), r.get("error_code")) for r in replies], replies, w
