"""T5 re-review probe q4 (PREDATES T5: host.py:955 `type(value) in (str, ...)` is from
1668904f). A python-api argument value whose class has a metaclass with a raising __eq__
runs caller code inside _json_arguments; the RuntimeError is not in the caught tuple, so it
escapes invoke after the sequence is taken, and the next good call desyncs.
Exit 1 if it escapes or desyncs."""
import sys, tempfile
from pathlib import Path
from test_financial_workflow import start
from deploy_workflow.workflow import WorkflowError


class Meta(type):
    def __eq__(cls, other):
        raise RuntimeError("caller code ran in _json_arguments")

    __hash__ = type.__hash__


class X(metaclass=Meta):
    pass


w, pack = start(Path(tempfile.mkdtemp(prefix="t5q4-")), gap=True)
w._participant, w._transport = "t5", "python-api"
bad = 0
try:
    r = w.invoke("search_pack", {"query": X()})
    print("refused as", r["tool"], r["arguments"], r["error_code"])
except Exception as e:  # reported, not hidden
    bad = 1
    print("ESCAPED invoke:", type(e).__name__, e)
try:
    r = w.invoke("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1})
    print("next good call", r["status"], r["error_code"])
except WorkflowError as e:
    bad = 1
    print("next good call REFUSED", e.code, " <-- DESYNC")
sys.exit(bad)
