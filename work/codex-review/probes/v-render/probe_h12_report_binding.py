# Desired: render(view_B, report_A) built from a different run must refuse, or the page must
# carry only B's content (rebuilt from B). Exit 1 if A's populated blocks appear under B's run.
import json, re
from deploy_vii.contracts import Run
from deploy_vii.render import render, empty_view
from deploy_vii.report_view import build, pathways
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.registry import modules
from test_chart_render_s5 import _view
from test_financial_series import fixture

view = _view(fixture())
run = Run.model_validate({**view.run.model_dump(), 'requested_modules': tuple(m.module_id for m in modules())})
view = view.model_copy(update={'run': run})
report_a = build(view, next(p for p in pathways() if p.id == run.pathway), SHIPPED_MAPS)
other = empty_view(Run.model_validate({**run.model_dump(), 'run_id': 'other', 'issuer_name': 'Different Issuer'}), candidate=False)
own = json.loads(re.search(r'<script id="report-data" type="application/json">(.*?)</script>', render(other), re.S)[1])
own_populated = sum(b['state'] == 'populated' for b in own['report']['blocks'])
try:
    mixed = render(other, report_a)
except ValueError as e:
    print('REFUSED', e)
    raise SystemExit(0)
d = json.loads(re.search(r'<script id="report-data" type="application/json">(.*?)</script>', mixed, re.S)[1])
populated = sum(b['state'] == 'populated' for b in d['report']['blocks'])
summary = {'issuer': d['run']['issuer_name'], 'run_id': d['run']['run_id'], 'module_facts': sum(len(m['facts']) for m in d['modules']),
           'populated_blocks_mixed': populated, 'populated_blocks_own_render': own_populated}
print(json.dumps(summary))
assert populated == own_populated, 'H12: foreign report blocks rendered under a different run'
print('H12 desired behaviour holds')
