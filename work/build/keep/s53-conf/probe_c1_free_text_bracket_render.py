"""C1: a CP-DR question text the entry validator accepts, holding a bracketed citation such as
`[sic]`, becomes a known text fact (TDR.2.<row>.question). render.py item 45 sends every known text
fact that prose._TOKEN matches through resolve(), which fails closed, so the whole page raises.
Exit 1 if the accepted submission's page cannot be rendered (the defect); 0 if it renders."""
import copy, json, sys
import test_connect_cpdr as t
from deploy_vii.contracts import ModuleView, View
from deploy_vii.render import empty_view, render
from deploy_workflow.owners import cpdr

def page_for(payload):
    text = json.dumps(payload)
    attempt, store = t.attempt_of(t.cp0_module(empty=False), text)
    outcome = cpdr.ENTRY_VALIDATOR(store, store.pack(), attempt)
    assert outcome.issues == (), outcome.issues
    sub = t.submission(payload)
    inputs = cpdr._inputs(store, attempt, sub)
    module = cpdr.research_module(report=cpdr.compose(inputs), inputs=inputs, attempt=attempt,
                                  run=store.read().run)
    run = store.read().run
    base = empty_view(run, candidate=False)
    mods = tuple(
        ModuleView(module_id=m.module_id, title=m.title, aliases=m.aliases, status="restricted",
                   artifact_sha256=module.content_hash(), facts=module.facts, tables=module.tables,
                   claims=module.claims, limitations=module.limitations)
        if m.module_id == "CP-DR" else m for m in base.modules)
    return render(base.model_copy(update={"modules": mods}))

good = t.SUBMISSIONS["cpdr"]["partial"]
page_for(good)
print("control: oracle 'partial' submission renders")
bad = copy.deepcopy(good)
q = bad["gaps"][0]["questions"][0]
q["text"] = q["text"].rstrip("?") + " [sic]?"
print("question text:", q["text"])
try:
    page_for(bad)
except ValueError as e:
    print("DEFECT: accepted submission, page render raises:", str(e)[:200])
    sys.exit(1)
print("renders")
