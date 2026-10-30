"""Round 4 survey: CP-L10 TL10.3 run-text fields (assessment on a topic row and on the overall
row, credit_transmission; validated at cpl10.py:1060-1073, stored at :804, :809-811, :826) must
render spelled; a "[sic]" in the free `source_refs` field must render as written; a malformed
token in a registered field must raise "does not resolve". Exit 1 on any miss."""
import json, sys
import test_method_cpl10 as m10
import test_connect_cp8 as tc
from deploy_workflow.owners import cpl10
from deploy_vii.report_view import ModuleView

sub = json.loads(m10._payload("positive"))
a = sub["assessments"][0]
tid = a["topic_id"]
tok = "{TL10.2." + tid + ".change|US$ m}"
a2 = dict(a, assessment=f"The balance moved by {tok} in the quarter.",
          credit_transmission=f"A move of {tok} reaches the credit view.")
s2 = dict(sub, assessments=[a2, *sub["assessments"][1:]],
          overall=dict(sub["overall"], rationale=f"Overall, the balance moved by {tok}."))
res = cpl10.change_screen(submission=s2, upstream=m10.UPSTREAM)
facts = tuple(c.fact for c in res.cells)
run_ids = [f"TL10.3.{tid}.assessment", f"TL10.3.{tid}.credit_transmission", "TL10.3.overall.assessment"]
free_id, sic = f"TL10.3.{tid}.source_refs", "CP-1 Cash [sic]"


def page(edit):
    fs = tuple(f.model_copy(update={"text": edit[f.fact_id]}) if f.fact_id in edit else f for f in facts)
    base = tc._what_changed_view("positive")
    view = base.model_copy(update={"modules": (ModuleView(module_id="CP-L10", title="CP-L10",
        aliases=(), status="restricted", artifact_sha256="c" * 64, facts=fs, limitations=()),)})
    return tc._payload_facts(view)


bad = 0
try:
    shown = page({free_id: sic})
    for fid in run_ids:
        raw = tok in shown[fid]["display"] or tok in shown[fid]["table_display"]
        bad |= raw
        print(fid, "RAW" if raw else "spelled", "|", shown[fid]["table_display"][:60])
    print(free_id, "|", shown[free_id]["display"]); bad |= shown[free_id]["display"] != sic
except ValueError as e:
    print("render raised:", str(e)[:160]); bad = 1
for broken in ("{TL10.2." + tid + ".chang|US$ m}", "{TL10.2." + tid + ".change|US$ m"):
    try:
        page({run_ids[0]: f"Moved by {broken}."}); print("malformed NOT refused:", broken); bad = 1
    except ValueError as e:
        print("malformed refused:", "does not resolve" in str(e))
        bad |= "does not resolve" not in str(e)
sys.exit(1 if bad else 0)
