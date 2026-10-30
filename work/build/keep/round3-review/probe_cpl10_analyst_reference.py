"""Round 3 step 3: CP-L10 analyst assessment text is checked by prose.issues (so it may carry
{TL10.2.<topic>.change|<unit>} references) and is stored verbatim as a TL10.3 known text fact.
Exit 1 if the rendered payload display shows the raw reference token instead of the figure."""
import json, sys
import test_method_cpl10 as m10
import test_connect_cp8 as tc
from deploy_workflow.owners import cpl10
from deploy_vii.report_view import View, ModuleView  # noqa

sub = json.loads(m10._payload("positive"))
a = sub["assessments"][0]
topic = next(t for t in cpl10.TOPICS if t.topic_id == a["topic_id"]) if hasattr(cpl10, "TOPICS") else None
ref = None
res = None
for unit in ([topic.token] if topic else []) + ["US$ m", "x", "%"]:
    cand = "{TL10.2." + a["topic_id"] + ".change|" + unit + "}"
    a2 = dict(a, assessment="The balance moved by " + cand + " over the quarter.")
    s2 = dict(sub, assessments=[a2, *sub["assessments"][1:]])
    try:
        res = cpl10.change_screen(submission=s2, upstream=m10.UPSTREAM); ref = cand; break
    except ValueError as e:
        print("refused", cand, str(e)[:120])
if res is None:
    print("no accepted reference form"); sys.exit(2)
facts = tuple(c.fact for c in res.cells)
fid = f"TL10.3.{a['topic_id']}.assessment"
print("accepted; stored fact", fid, "=", next(f.text for f in facts if f.fact_id == fid))
base = tc._what_changed_view("positive")
view = base.model_copy(update={"modules": (ModuleView(module_id="CP-L10", title="CP-L10", aliases=(),
    status="restricted", artifact_sha256="c" * 64, facts=facts, limitations=()),)})
shown = tc._payload_facts(view)[fid]
print("display:", shown["display"]); print("table_display:", shown["table_display"])
sys.exit(1 if ref in shown["display"] or ref in shown["table_display"] else 0)
