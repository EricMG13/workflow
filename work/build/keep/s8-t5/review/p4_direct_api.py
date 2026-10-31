"""T5 review probe 4: python-api callers (no JSON parse in front of the host): a cyclic dict,
nan/inf floats, a tuple, a str subclass, a 5000-digit int, then a good call. Reports whether the
host raised (RecursionError etc.) or refused, and whether the session stays in sequence. Exit 1 on desync."""
import sys, tempfile
from pathlib import Path
from test_financial_workflow import make_pack
from deploy_workflow.owner_workflow import OwnerWorkflow
from deploy_workflow.financial_workflow import FinancialWorkflow

class S(str):
    pass

def cases():
    cyc = {"query": "x"}; cyc["self"] = cyc
    yield "cyclic", cyc
    yield "nan", {"query": "x", "n": float("nan")}
    yield "inf", {"query": "x", "n": float("inf")}
    yield "tuple", {"query": "x", "n": (1,)}
    yield "str_subclass", {"query": S("x")}
    yield "int_5000", {"query": "x", "n": 10 ** 5000}

GOOD = ("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1})
bad = 0
for kind, cls, kw in (("owner", OwnerWorkflow, "publication_directory"), ("financial", FinancialWorkflow, "model_directory")):
    for name, args in cases():
        p = Path(tempfile.mkdtemp(prefix="t5d-"))
        w = cls.create(p / "store", make_pack(), **{kw: p / "model"})
        w._participant, w._transport = "t5", "python-api"
        try:
            r = w.invoke("search_pack", args); first = (r["status"], r["error_code"], r["arguments"] == {})
        except BaseException as e:  # probe reports the exception type, it does not hide it
            first = ("raised", type(e).__name__)
        r2 = w.invoke(*GOOD)
        ok = (r2["status"], r2["error_code"]) == ("ok", None)
        bad |= not ok
        print(kind, name, first, (r2["status"], r2["error_code"]), "OK" if ok else "DESYNC")
sys.exit(1 if bad else 0)
