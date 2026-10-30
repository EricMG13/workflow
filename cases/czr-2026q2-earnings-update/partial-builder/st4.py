from common import *
def stage():
    return {"step": "readiness", "calls": [{"tool": "read_inputs"}], "submission": {"consumers": []}}
