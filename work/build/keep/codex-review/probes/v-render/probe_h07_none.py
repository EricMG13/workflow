# Desired: every value cp8 accepts (validate_ledger -> no issues) must render; a forbidden
# spelling must be refused by validate_ledger. Exit 1 if accepted-but-unrenderable.
import copy
import test_method_cp8 as m
import test_connect_cp8 as c
from deploy_workflow.owners import cp8
from deploy_vii.contracts import ModuleView, View
from deploy_vii import render, prose

bad = []
for value in ('No change.', 'None', 'none', 'null', 'nan'):
    payload = copy.deepcopy(m.SUBMISSIONS['positive'])
    payload['synthesis']['text'] = value
    submission = m.submission(payload)
    issues = cp8.validate_ledger(submission=submission, upstream=m.upstream('positive'), pack=m.pack('positive'))
    print('value', repr(value), 'producer issues', issues)
    if issues:
        continue
    report = cp8.decision_ledger(pack=m.pack('positive'), submission=submission, upstream=m.upstream('positive'))
    module = ModuleView(module_id='CP-8', title='CP-8', aliases=(), status='restricted', artifact_sha256='b'*64, facts=report.facts, tables=report.tables, claims=report.claims, limitations=report.limitations)
    view = View(run=c._run('positive'), mode='accepted', modules=(module,))
    pi = prose.prose_issues(module)
    print('  claim issues', pi)
    try:
        render.render(view)
    except ValueError as e:
        print('  ACCEPTED BUT RENDER REFUSED', type(e).__name__, str(e)[:200])
        bad.append(value)
    else:
        print('  RENDER OK')
print('accepted-but-unrenderable:', bad)
assert not bad
