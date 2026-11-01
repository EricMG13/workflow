# For each cp8 _text caller in the positive fixture, with the new null check disabled
# (base behaviour), does "None"/"null" render? Prints accepted-and-renders vs render-refused.
import copy, sys
import test_method_cp8 as m
import test_connect_cp8 as c
from deploy_workflow.owners import cp8
from deploy_vii.contracts import ModuleView, View
from deploy_vii import render

def setp(d, path, v):
    for k in path[:-1]:
        d = d[k]
    d[path[-1]] = v

paths = [
    ("synthesis", "text"),
    ("decision", "posture", "absence", "reason"),
    ("decision", "posture", "absence", "follow_up"),
    ("thesis", "expected_spread_return", "absence", "reason"),
]
saved = cp8._FORBIDDEN_TEXT
for disabled in (True, False):
    cp8._FORBIDDEN_TEXT = set() if disabled else saved
    for path in paths:
        for value in ("None", "null"):
            p = copy.deepcopy(m.SUBMISSIONS["positive"])
            setp(p, path, value)
            sub = m.submission(p)
            iss = cp8.validate_ledger(submission=sub, upstream=m.upstream("positive"), pack=m.pack("positive"))
            if iss:
                print("disabled" if disabled else "tip", ".".join(path), value, "REFUSED", iss); continue
            try:
                r = cp8.decision_ledger(pack=m.pack("positive"), submission=sub, upstream=m.upstream("positive"))
                mod = ModuleView(module_id="CP-8", title="CP-8", aliases=(), status="restricted", artifact_sha256="b"*64,
                                 facts=r.facts, tables=r.tables, claims=r.claims, limitations=r.limitations)
                render.render(View(run=c._run("positive"), mode="accepted", modules=(mod,)))
                print("disabled" if disabled else "tip", ".".join(path), value, "RENDERS")
            except ValueError as e:
                print("disabled" if disabled else "tip", ".".join(path), value, "RENDER-REFUSED", str(e)[:120])
