"""Probe (O3 Task 4 / O7 N1): list every model-submitted step schema field that names a run or
hash binding (run_id, issuer_id, as_of, *sha256*) and is NOT pre-filled by Python
(PREFILLED_MARKER), so a replay under a new run_id would resubmit the earlier run's value.
Usage: python -I replay_identity_fields.py <exported HEAD src dir>. Exit 1 if any is found."""
import sys
sys.path.insert(0, sys.argv[1])
from typing import get_args, get_origin
from pydantic import BaseModel
from deploy_vii.live.schema import PREFILLED_MARKER
from deploy_workflow import owner_workflow as ow

NAMES = ("run_id", "issuer_id", "as_of", "sha256")

def walk(model, path, seen, out):
    if model in seen:
        return
    seen = seen | {model}
    for name, f in model.model_fields.items():
        extra = f.json_schema_extra if isinstance(f.json_schema_extra, dict) else {}
        if any(n in name for n in NAMES) and PREFILLED_MARKER not in extra:
            out.append(f"{path}.{name}")
        stack = [f.annotation]
        while stack:
            t = stack.pop()
            if isinstance(t, type) and issubclass(t, BaseModel):
                walk(t, f"{path}.{name}", seen, out)
            stack.extend(get_args(t))

found = {}
for module_id, spec in ow.OWNER_SPECS.items() if hasattr(ow, "OWNER_SPECS") else ow._specs().items():
    for step in spec.steps:
        out = []
        walk(step.schema, step.schema.__name__, frozenset(), out)
        if out:
            found[(module_id, step.step_id)] = out
for key, fields in sorted(found.items()):
    print(key, fields)
sys.exit(1 if found else 0)
