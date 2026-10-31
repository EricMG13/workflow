import io,json,tempfile
from pathlib import Path
from test_financial_workflow import make_pack
from deploy_workflow.owner_workflow import OwnerWorkflow,serve_json_lines as serve_owner
from deploy_workflow.financial_workflow import FinancialWorkflow,serve_json_lines as serve_financial
root=Path(tempfile.mkdtemp(prefix='submit-',dir='/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-codex-findings-review-64c673/ee01671b-a922-47ba-ad87-32129314cd1e/scratchpad/v-tools/legacy/tools/probe-data'))
for name,cls,serve in [('owner',OwnerWorkflow,serve_owner),('financial',FinancialWorkflow,serve_financial)]:
 for variant in ['surrogate','syntax_control']:
    p=root/name/variant
    kwargs={'publication_directory':p/'model'} if name=='owner' else {'model_directory':p/'model'}
    w=cls.create(p/'store',make_pack(),**kwargs)
    bad=json.dumps({'operation':'invoke','tool':'search_pack','arguments':{'query':'\ud800'}}) if variant=='surrogate' else '{broken'
    good={'operation':'invoke','tool':'read_pages','arguments':{'source_id':'identity','first_page':1,'last_page':1}}
    submit={'operation':'submit_review','payload':'{}'}
    raw=(bad+'\n'+json.dumps(good)+'\n'+json.dumps(submit)+'\n').encode()
    reader=io.TextIOWrapper(io.BytesIO(raw),encoding='utf-8'); out=io.BytesIO(); writer=io.TextIOWrapper(out,encoding='utf-8')
    serve(w,reader,writer,destination=p/'receipt.json',participant='review-probe')
    writer.flush(); replies=[json.loads(x) for x in out.getvalue().splitlines()]
    states=[(r.get('status'),r.get('error_code'),r.get('disposition')) for r in replies]
    print(name,variant,states,'calls',len(w._calls),'submissions',len(w._submissions))
    if variant=='surrogate':
       assert [r.get('error_code') for r in replies]==['bad_arguments','identity_mismatch','identity_mismatch']
       assert not w._calls and not w._submissions
    else:
       assert replies[1]['status']=='ok'
       assert replies[2].get('error_code')!='identity_mismatch'
       assert len(w._submissions)==1
print('continued-submission and recovery control assertions passed')
