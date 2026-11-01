"""T5 round-3 re-review probe 9.
(a) New at af9ceea1: invoke now evaluates `tool_name != ""` on a non-str name, running the
    caller object's __ne__/__bool__ outside any try. A raising __ne__ escapes invoke after the
    sequence was taken; the next good call then fails the workflow's sequence check.
(b) Pre-existing: the SourceSession lock refusal (name, copied, not_permitted) does not replay
    on a fresh session (unreachable via the workflows, whose own lock serialises calls).
Exit 1 if (a) escapes or desyncs."""
import sys, tempfile
from pathlib import Path
from test_financial_workflow import start
from deploy_workflow.host import SourceSession
from deploy_workflow.workflow import WorkflowError


class Hostile:
    def __ne__(self, other):
        raise RuntimeError("caller code ran inside invoke")


p = Path(tempfile.mkdtemp(prefix="t5n-"))
w, pack = start(p, gap=True)
w._participant, w._transport = "t5", "python-api"
bad = 0
try:
    r = w.invoke(Hostile(), {"query": "x"})
    print("(a) hostile name ->", r["tool"], r["status"], r["error_code"])
except Exception as e:  # reported, not hidden
    bad = 1
    print("(a) hostile name ESCAPED invoke:", type(e).__name__, e)
try:
    r = w.invoke("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1})
    print("(a) next good call ->", r["status"], r["error_code"])
except WorkflowError as e:
    bad = 1
    print("(a) next good call REFUSED", e.code, " <-- DESYNC")

# (b) lock path, direct SourceSession use
s = w._session
s._operation.acquire()
try:
    rec = s.invoke("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1})
finally:
    s._operation.release()
fresh = SourceSession.from_execution(w._store, s._ticket_id, s._step_id)
rep = fresh.invoke(rec["tool"], rec["arguments"])
print("(b) lock receipt", (rec["status"], rec["error_code"]), "replays as",
      (rep["status"], rep["error_code"]), "MATCH" if (rec["status"], rec["error_code"]) == (rep["status"], rep["error_code"]) else "MISMATCH (pre-existing)")
sys.exit(bad)
