"""Survey side check: does the CP-2H T2R.10 reference reach the page HTML raw outside the
report-data payload (block table cells use fact_spelling, report_view.py:1460-1469)?
Prints where the raw token occurs; exit 1 if it appears outside the payload script."""
import json, re, sys
import test_method_cp2h as m
import test_connect_cp8 as tc
from deploy_workflow.owners import cp2h
from deploy_vii import render as core_render
from deploy_vii.report_view import ModuleView

payload = json.loads(json.dumps(m.raw_payload("positive")))
tok = "{T2R.4.t01.headroom|x}"
payload["gaps"][0]["gap"] = f"Headroom of {tok} is short."
rep = cp2h.compute(m.inputs("positive", payload))
facts = [c.fact for c in rep.cells]
facts += [cp2h._moved(r.fact, cp2h.CP1_REFERENCES[0], r.row_id) for r in rep.cp1_references]
base = tc._what_changed_view("positive")
view = base.model_copy(update={"modules": (ModuleView(module_id="CP-2H", title="CP-2H", aliases=(),
    status="restricted", artifact_sha256="c" * 64, facts=tuple(facts), limitations=()),)})
page = core_render.render(view)
outside = re.sub(r'<script[^>]*id="report-data"[^>]*>.*?</script>', "", page, flags=re.DOTALL)
esc = tok.replace("|", "&#124;")
hits = [h for h in (tok, esc) if h in outside]
print("raw token outside payload:", hits, "| 'Headroom of' occurrences outside:", outside.count("Headroom of"))
sys.exit(1 if hits else 0)
