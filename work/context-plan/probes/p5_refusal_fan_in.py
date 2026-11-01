"""Probe (O3+O4 Task 1, F2): for each preset, list the modules planned before CP-5 that are not in
CP-5's required set. Only the deterministic CP-MODEL should appear (registry.py:24-25), so no
refusal can leave an analytical module before CP-5 unconsumed. Prints; exits 0.
Usage: PYTHONPATH=src python work/context-plan/probes/p5_refusal_fan_in.py"""

from deploy_vii.contracts import PATHWAY_MODULES
from deploy_vii.registry import dependencies, plan

for pathway, requested in PATHWAY_MODULES.items():
    order = plan(requested)
    if "CP-5" not in order:
        print(f"{pathway}: no CP-5")
        continue
    required = dependencies(requested)["CP-5"]
    outside = [m for m in order[: order.index("CP-5")] if m not in required]
    print(f"{pathway}: before CP-5 and outside its required set: {outside}")
