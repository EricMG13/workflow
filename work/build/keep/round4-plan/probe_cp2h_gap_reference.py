"""Round 4 survey: CP-2H T2R.10 gap fields (gap, why_it_matters, affected_analysis, action) are
validated by prose.issues (cp2h.py:1608-1614) and stored raw (cp2h.py:1413-1424). A reference in
each must render spelled in display/table_display; a "[sic]" in the free `id` field of T2R.10
must render as written. Exit 1 if any run-text field shows a raw token or [sic] fails."""
import json, sys
import test_method_cp2h as m
import test_connect_cp8 as tc
from deploy_workflow.owners import cp2h
from deploy_vii.report_view import ModuleView

payload = json.loads(json.dumps(m.raw_payload("positive")))
tok = "{T2R.4.t01.headroom|x}"
fields = ("gap", "why_it_matters", "affected_analysis", "action")
for f in fields:
    payload["gaps"][0][f] = f"Headroom of {tok} is in the {f.replace('_', ' ')} text."
rep = cp2h.compute(m.inputs("positive", payload))
facts = [c.fact for c in rep.cells]
facts += [cp2h._moved(r.fact, cp2h.CP1_REFERENCES[0], r.row_id) for r in rep.cp1_references]
sic = "CP-2H-GAP-001 [sic]"
NOSIC = "--no-sic" in sys.argv
facts = tuple(facts) if NOSIC else tuple(f.model_copy(update={"text": sic}) if f.fact_id == "T2R.10.g01.id" else f for f in facts)
base = tc._what_changed_view("positive")
view = base.model_copy(update={"modules": (ModuleView(module_id="CP-2H", title="CP-2H", aliases=(),
    status="restricted", artifact_sha256="c" * 64, facts=facts, limitations=()),)})
try:
    shown = tc._payload_facts(view)
except Exception as e:  # report the failure class; the exit code carries it
    print("render raised:", type(e).__name__, str(e)[:200]); sys.exit(1)
bad = 0
for f in fields:
    s = shown[f"T2R.10.g01.{f}"]
    raw = tok in s["display"] or tok in s["table_display"]
    bad |= raw
    print(f, "RAW" if raw else "spelled", "|", s["table_display"][:70])
s = shown["T2R.10.g01.id"]
print("id:", s["display"]); bad |= (not NOSIC) and s["display"] != sic
sys.exit(1 if bad else 0)
