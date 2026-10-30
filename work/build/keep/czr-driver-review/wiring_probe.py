import sys
from pathlib import Path as _P
sys.path[:0] = [str(_P.cwd() / "src"), str(_P.cwd() / "tests")]
"""czr_closed passes the live spec's inputs to figure_body and a FIG token in a non
module_context stage raises naming the figure before any submit (no full run)."""
import json
import tempfile
from pathlib import Path

import czr_runs

seen = []
real = czr_runs.figure_body


def spy(inputs, read_body):
    seen.append((inputs, read_body))
    return real(inputs, read_body)


czr_runs.figure_body = spy
sel = {"module_id": "CP-1", "table_id": "T1", "period": "Q2 26", "label": "Revenue",
       "unit_token": "USD_M", "spelled": "$2,900"}
with tempfile.TemporaryDirectory() as d:
    sub = Path(d) / "s.json"
    sub.write_text(json.dumps({"figures": {"rev": sel}, "stages": [
        {"step": "source_readiness", "calls": [], "submission": {"x": "{{FIG:rev}}"}}]}))
    try:
        czr_runs.czr_closed(Path(d) / "run", sub)
        raise SystemExit("no raise")
    except RuntimeError as e:
        print("raised:", e)
        assert str(e).startswith("FIG rev:") and "module_context" in str(e)
print("figure_body calls:", seen)
assert seen == [("none", None)]
