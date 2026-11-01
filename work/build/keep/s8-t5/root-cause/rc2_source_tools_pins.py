"""T5 root-cause probe 2: the existing test_source_tools.py pins at :514-526
(test_deep_json_arguments_cannot_escape_sanitized_refusal) and :1474 (the "shell" + NaN
call), run outside pytest against the current invoke (argv[1] == "current") or the proposed
one (argv[1] == "proposed"). Prints each pin's outcome; exit 1 if any pin as written fails."""
import json, sys, tempfile
from pathlib import Path
import test_source_tools as t
from deploy_workflow import host
from rc_fix import proposed_invoke

if sys.argv[1:] == ["proposed"]:
    host.SourceSession.invoke = proposed_invoke
host._CP1_VERIFIED.clear() if hasattr(host, "_CP1_VERIFIED") else None
pack = t.pack.__wrapped__()
bad = 0
# :514-526
h, _, _ = t.session(Path(tempfile.mkdtemp(prefix="t5p-")), pack)
nested = None
for _ in range(600):
    nested = {"x": nested}
r = h.invoke("shell", {"nested": nested})
ok = (r["status"], r["error_code"], r["body"]) == ("refused", "not_permitted", None) and \
    json.dumps(r["arguments"]) == json.dumps({"nested": nested})
bad |= not ok
print(":514-526", r["status"], r["error_code"], "args kept" if r["arguments"] else "args {}",
      "PASS" if ok else "FAIL")
# :1474 shape on a current (not stale) session: unoffered name + refused arguments
h, _, _ = t.session(Path(tempfile.mkdtemp(prefix="t5p-")), pack)
r = h.invoke("shell", {"x": float("nan")})
ok = r["error_code"] == "bad_arguments"
bad |= not ok
print(":1474 shape", r["status"], r["error_code"], "PASS" if ok else "FAIL")
r = h.invoke("shell", {})
print(":1475 shape (not stale here)", r["status"], r["error_code"])
sys.exit(bad)
