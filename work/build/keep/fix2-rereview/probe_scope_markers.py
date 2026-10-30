"""Item 45 scope: do oracle {{...}} markers, or any settled known text fact in the cp5/cpl10
fast fixtures, reach _carries_reference? Exit 1 if a rendered known text fact carries one."""
import sys
from deploy_vii import prose
from deploy_vii.report_view import _carries_reference

lits = ["{{PACK_SHA256}}", "{{STATUS:CP-0}}", "{{SHA256:CP-1A}}", "{{TRACE:CP-1 leverage}}",
        "CP-0:{{CP0_RESULT_SHA256}}", "{{CP0_STATUS_WORD}}"]
for s in lits:
    m = prose._TOKEN.search(s)
    print("literal", repr(s), "->", m.group(0) if m else None)

hits = []
import test_method_cp5 as m5
from deploy_workflow.owners.cp5 import candidate, compute
for case in m5.CASES:
    fx = m5.make_fixture(case)
    inputs = m5.make_inputs(case)
    result = compute(inputs)
    mods = list(fx.heads.values()) + [candidate(result, inputs, attempt=1)]
    n = 0
    for mod in mods:
        for f in mod.facts:
            if f.status == "known" and f.text is not None:
                n += 1
                if _carries_reference(f.text):
                    hits.append(("cp5", case, mod.module_id, f.fact_id, f.text[:80]))
    print("cp5", case, "known text facts", n)

import test_method_cpl10 as m10
from deploy_workflow.owners import cpl10
for name in ("positive", "limited"):
    res = cpl10.change_screen(submission=m10._payload(name), upstream=m10.UPSTREAM)
    n = 0
    for cell in res.cells:
        f = cell.fact
        if f.status == "known" and f.text is not None:
            n += 1
            if _carries_reference(f.text):
                hits.append(("cpl10", name, f.fact_id, f.text[:80]))
    for f in m10.UPSTREAM.cp1_facts.values():
        if f.status == "known" and f.text is not None and _carries_reference(f.text):
            hits.append(("cpl10-cp1", f.fact_id, f.text[:80]))
    print("cpl10", name, "known text facts", n)
for h in hits:
    print("HIT", h)
sys.exit(1 if hits else 0)
