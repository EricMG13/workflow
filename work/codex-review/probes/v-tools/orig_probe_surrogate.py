import io,json,tempfile
from pathlib import Path
from test_financial_workflow import make_pack
from deploy_workflow.owner_workflow import OwnerWorkflow, serve_json_lines as serve_owner
from deploy_workflow.financial_workflow import FinancialWorkflow, serve_json_lines as serve_financial
root=Path(tempfile.mkdtemp(prefix='surrogate-',dir='/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-codex-findings-review-64c673/ee01671b-a922-47ba-ad87-32129314cd1e/scratchpad/v-tools/legacy/tools/probe-data'))
for name, cls, serve in [('owner',OwnerWorkflow,serve_owner),('financial',FinancialWorkflow,serve_financial)]:
    kwargs={'publication_directory':root/name/'model'} if name=='owner' else {'model_directory':root/name/'model'}
    workflow=cls.create(root/name/'store',make_pack(),**kwargs)
    bad={'operation':'invoke','tool':'search_pack','arguments':{'query':'\ud800'}}
    good={'operation':'invoke','tool':'read_pages','arguments':{'source_id':'identity','first_page':1,'last_page':1}}
    raw=('\n'.join(json.dumps(r) for r in [bad,good,good])+'\n').encode()
    reader=io.TextIOWrapper(io.BytesIO(raw),encoding='utf-8')
    out=io.BytesIO(); writer=io.TextIOWrapper(out,encoding='utf-8')
    serve(workflow,reader,writer,destination=root/name/'receipt.json',participant='review-probe')
    writer.flush()
    replies=[json.loads(s) for s in out.getvalue().decode().splitlines()]
    print(name,[(r.get('status'),r.get('error_code')) for r in replies], 'retained_calls',len(workflow._calls))
    assert [r.get('error_code') for r in replies]==['bad_arguments','identity_mismatch','identity_mismatch']
print('CONFIRMED: malformed escaped surrogate permanently desynchronizes public workflow source-call sequence')
