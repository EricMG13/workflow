"""T5 probe: why does a frame at the depth bound come back refused? Prints, per workflow and depth,
the reply status/error code, the reply keys, and the depth of the arguments the owner layer retained.
Usage (T5 worktree root): PYTHONPATH=src:tests <venv python> <this>"""
import io, json, tempfile
from pathlib import Path
from test_financial_workflow import make_pack
from deploy_workflow.owner_workflow import OwnerWorkflow, serve_json_lines as so
from deploy_workflow.financial_workflow import FinancialWorkflow, serve_json_lines as sf

def depth(v, d=1):
    if isinstance(v, dict): return max([depth(x, d + 1) for x in v.values()] or [d])
    if isinstance(v, list): return max([depth(x, d + 1) for x in v] or [d])
    return d - 1

root = Path(tempfile.mkdtemp(prefix="t5-"))
for name, cls, serve, kw in [("owner", OwnerWorkflow, so, "publication_directory"), ("financial", FinancialWorkflow, sf, "model_directory")]:
    for args in ({"query": "x", "extra": 1}, {"query": "x", "extra": "[" * 99}):
        p = root / name / str(len(json.dumps(args)))
        w = cls.create(p / "store", make_pack(), **{kw: p / "model"})
        frame = json.dumps({"operation": "invoke", "tool": "search_pack", "arguments": args})
        out = io.StringIO()
        serve(w, io.StringIO(frame + "\n"), out, destination=p / "r.json", participant="t5")
        r = json.loads(out.getvalue().splitlines()[0])
        print(name, list(args), r.get("status"), r.get("error_code"), sorted(r)[:8])
    for n in (99, 100):
        args = {"query": "x"}
        p = root / name / f"d{n}"
        w = cls.create(p / "store", make_pack(), **{kw: p / "model"})
        w._participant, w._transport = "t5", "bounded-json-lines/1"
        nested = 0
        for _ in range(n - 1): nested = [nested]
        reply = w.invoke("search_pack", {"query": "x", "extra": nested})
        print(name, "depth", n, reply.get("status"), reply.get("error_code"), "retained depth", depth(w._calls[-1].arguments) if w._calls else None)
