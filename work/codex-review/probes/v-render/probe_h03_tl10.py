import json, re
import test_connect_cpl10 as c
import test_connect_cp8 as c8
from deploy_workflow.owners import cpl10
from deploy_vii import render, prose
from deploy_vii.contracts import ModuleView, View
sub, topic, facts = c._tl10_3_facts()
issues = cpl10.validate_screen(submission=sub, upstream=c.UPSTREAM) if hasattr(cpl10, 'validate_screen') else None
print('validation', issues)
# change_screen invokes its real validator; no fact edits are used.
result = cpl10.screen_report(submission=json.dumps(sub), upstream=c.UPSTREAM, run=c8._run('positive'), pack_sha256='a'*64)
facts = result.facts
module = ModuleView(module_id='CP-L10', title='CP-L10', aliases=(), status='restricted', artifact_sha256='c'*64, facts=facts, tables=result.tables, claims=result.claims, limitations=result.limitations)
view = View(run=c8._run('positive'), mode='accepted', modules=(module,))
assert not prose.prose_issues(module)
html = render.render(view)
payload = json.loads(re.search(r'<script[^>]*id="report-data"[^>]*>(.*?)</script>', html, re.S).group(1))
by_id = {f['fact_id']: f for f in payload['modules'][0]['facts']}
for table, field in [('TL10.3','credit_transmission'),('TL10.4','decision_impact')]:
    fact_id=f'{table}.{topic}.{field}'
    f=by_id[fact_id]
    print(fact_id, 'display=',f['display'],'table_display=',f['table_display'])
    table_data=next(t for t in payload['modules'][0]['tables'] if t['table_id']==table)
    assert any(fact_id in row['fact_ids'] for row in table_data['rows'])
resolved=by_id[f'TL10.3.{topic}.credit_transmission']['table_display']
trigger=by_id[f'TL10.4.{topic}.decision_impact']['table_display']
print('EQUAL',resolved == trigger)
assert '3.75 US$ m' in resolved
print('RAW_TRIGGER', '{TL10.2.' in trigger)
# Desired behaviour: TL10.4 decision_impact resolves to the same quantity, both display and table_display.
d = by_id[f'TL10.4.{topic}.decision_impact']
assert '{' not in d['display'] and '{' not in d['table_display'], ('H03 raw token displayed', d['display'], d['table_display'])
assert '3.75 US$ m' in d['display'] and '3.75 US$ m' in d['table_display'], d
print('H03 desired behaviour holds')
