"""RED probe: the old `next(CP-1 record)` picks by hash order, the new one by step id."""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

from deploy_workflow import replay
from deploy_workflow.owner_workflow import OWNER_SPECS

STEPS = [s.step_id for s in OWNER_SPECS["CP-1"].steps]


def h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def build(salt: int) -> list[replay.ReplayRecord]:
    return [
        replay.ReplayRecord(
            earlier_run_id="earlier-run",
            module_id="CP-1",
            step_id=step,
            earlier_payload_sha256=h(f"e{salt}{step}"),
            payload_sha256=h(f"p{salt}{step}"),
            snapshot_sha256=h(f"s{salt}{step}"),
            rebound=(
                (replay.Rebound(path="financial.run_id", old="earlier-run", new="rerun"),)
                if step == "financials"
                else ()
            ),
        )
        for step in STEPS
    ]


def read_back(execution: Path) -> list[replay.ReplayRecord]:
    folder = execution / replay.AUDIT / "replays"
    return [
        replay.ReplayRecord.model_validate_json(p.read_bytes())
        for p in sorted(folder.iterdir())
        if json.loads(p.read_bytes())["schema_version"] == "replay/1"
    ]


for salt in range(1000):  # a salt whose hash order does not put financials first
    with tempfile.TemporaryDirectory() as tmp:
        for record in build(salt):
            replay._write_record(Path(tmp), "replays", record)
        records = read_back(Path(tmp))
    if records[0].step_id != "financials":
        break
else:
    sys.exit("no salt found")

old = next(r for r in records if r.module_id == "CP-1")
by_step = {r.step_id: r for r in records if r.module_id == "CP-1"}
new = by_step["financials"]
print("old picks", old.step_id, "rebound", old.rebound)
print("new picks", new.step_id, "rebound", new.rebound)
if old.rebound != ():
    sys.exit(1)  # old expression picked financials: probe not discriminating
assert set(by_step) == set(STEPS)
assert [(b.path, b.old, b.new) for b in new.rebound] == [("financial.run_id", "earlier-run", "rerun")]
