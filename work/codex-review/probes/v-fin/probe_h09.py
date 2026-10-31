"""H09 desired behaviour at HEAD: blank/Cf-only accounting_basis and entity_perimeter on a
financial historical scope are refused at the source-context boundary; visible control passes
end to end. Exit 1 while the defect is present. argv[1] = output dir."""
import copy, json, sys, tempfile
from pathlib import Path
import test_financial_workflow as f
from deploy_vii.execution import Execution
from deploy_vii.source_context import SourceContextReview, validate_source_context

OUT = Path(sys.argv[1])
failures, results = [], {}
pack = f.make_pack()
base = json.loads(f.context(pack))
cases = [('visible', 'IFRS', False), ('none', None, True), ('space', ' ', True),
         ('zwsp', '​', True), ('basis_only_zwsp', '​', False)]
for name, value, both in cases:
    raw = copy.deepcopy(base)
    for scope in raw['sources'][1]['scopes']:
        scope['accounting_basis'] = value
        if both:
            scope['entity_perimeter'] = value
    issues = validate_source_context(pack, SourceContextReview.model_validate_json(json.dumps(raw)))
    results[name] = list(issues)
    print('validator', name, len(issues), issues[:2])
    if name == 'visible' and issues:
        failures.append(f'control visible refused: {issues}')
    if name != 'visible' and not issues:
        failures.append(f'{name}: validator returned no issue')

def full_run(case, value):
    root = Path(tempfile.mkdtemp(prefix=case + '-', dir=OUT))
    wf, pk = f.start(root)
    f.read_sources(wf)
    assert wf.submit_review(f.readiness(pk))['status'] == 'valid'
    wf.invoke('read_pages', {'source_id': 'identity', 'first_page': 1, 'last_page': 1})
    wf.invoke('read_pages', {'source_id': 'financial', 'first_page': 1, 'last_page': 1})
    wf.invoke('search_pack', {'query': 'subsequent', 'source_id': 'financial'})
    raw = json.loads(f.context(pk))
    if value is not None:
        for scope in raw['sources'][1]['scopes']:
            scope['accounting_basis'] = value
            scope['entity_perimeter'] = value
    outcome = wf.submit_review(json.dumps(raw))
    print(case, 'source-context submit', outcome.get('status'), str(outcome)[:300])
    if outcome['status'] != 'valid':
        return {'context_status': outcome['status']}
    f.financial_reads(wf)
    fin = wf.submit_review(json.dumps(f.financials(pk)))
    assert fin['status'] == 'valid', fin
    read = wf.read_inputs()
    kpi = {r['evidence_id'] for r in f.parsed_evidence(read['body']) if r['kind'] == 'kpi'}
    assert wf.submit_review(json.dumps(f.narrative(read)))['status'] == 'valid'
    wf.read_inputs()
    assert wf.submit_review(json.dumps({'consumers': []}))['status'] == 'valid'
    qa = json.loads(wf.read_inputs()['body'])
    payload = {'claims': [{'claim_id': c['claim_id'], 'material': True,
        'evidence': [{'evidence_id': e, 'lineage_class': 'Calculated' if e in kpi else 'Directly Sourced',
                      'rationale': 'Python calculation' if e in kpi else 'Located source balance-sheet observation'}
                     for e in c['evidence_ids']],
        'rationale': 'Material historical credit consideration'} for c in qa['claims']]}
    assert wf.submit_review(json.dumps(payload))['status'] == 'valid'
    store = Execution(root / 'store')
    snap = store.read()
    head = next((h for h in snap.heads if h.module_id == 'CP-1'), None)
    dims = []
    if head is not None:
        mod = store.head_module(head)
        dims = [(x.field, x.status, repr(x.text)) for x in mod.facts
                if x.table_id == 'T4.14' and x.field in ('accounting_basis', 'entity_perimeter')]
    pub = wf.publish_model()
    print(case, 'CP-1 promoted', head is not None, 'T4.14 dims', len(dims), dims[:2], 'publish', pub)
    return {'context_status': 'valid', 'cp1_promoted': head is not None, 'dims': dims,
            'publication': pub, 'model_exists': (root / 'model').exists()}

vis = full_run('visible', None)
if vis.get('publication', {}).get('status') != 'ok':
    failures.append(f'control visible did not publish: {vis}')
blank = full_run('zwsp', '​')
if blank['context_status'] == 'valid':
    failures.append(f"zwsp source context accepted; cp1_promoted={blank.get('cp1_promoted')} "
                    f"publication={blank.get('publication')}")
print('FAILURES', failures)
sys.exit(1 if failures else 0)
