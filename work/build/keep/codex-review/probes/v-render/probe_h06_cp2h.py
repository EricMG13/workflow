import copy, json, re
import test_method_cp2h as m
import test_connect_cp8 as c8
from deploy_workflow.owners import cp2h
from deploy_vii import render, prose
from deploy_vii.contracts import ModuleView, View, Claim
payload=copy.deepcopy(m.raw_payload('positive'))
token='{T2R.4.t01.headroom|x}'
payload['gaps'][0]['gap']=f'Headroom of {token} is short.'
inputs=m.inputs('positive',payload)
print('VALIDATION', cp2h.validate(inputs))
assert not cp2h.validate(inputs)
rep=cp2h.compute(inputs)
facts=[c.fact for c in rep.cells]
facts += [cp2h._moved(r.fact,cp2h.CP1_REFERENCES[0],r.row_id) for r in rep.cp1_references]
facts += [cp2h._moved(r.fact,cp2h.CP2G_REFERENCES[0],r.row_id) for r in rep.cp2g_references]
claims=tuple(Claim(claim_id=c.claim_id,text=c.text,citations=c.citations,limitation=c.limitation) for c in rep.claims)
module=ModuleView(module_id='CP-2H',title='CP-2H',aliases=(),status='restricted',artifact_sha256='c'*64,facts=tuple(facts),tables=rep.tables,claims=claims,limitations=rep.own_limitations)
view=View(run=c8._run('positive'),mode='accepted',modules=(module,))
assert not prose.prose_issues(module)
html=render.render(view)
data=json.loads(re.search(r'<script[^>]*id="report-data"[^>]*>(.*?)</script>',html,re.S).group(1))
f=next(f for f in data['modules'][0]['facts'] if f['fact_id']=='T2R.10.g01.gap')
print('TABLE DISPLAY',f['table_display'])
assert f['table_display']=='Headroom of 1.08x is short.'
limits=[v for v in data['modules'][0]['limitations'] if token in v]
print('VISIBLE LIMITATIONS',limits)
assert not limits, ("H06 raw token in limitations", limits)
print('H06 desired behaviour holds')
assert any('Headroom of 1.08x is short.' in v for v in data['modules'][0]['limitations'])
