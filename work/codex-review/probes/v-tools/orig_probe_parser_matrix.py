import io,json,tempfile
from pathlib import Path
from test_financial_workflow import make_pack
from deploy_workflow.owner_workflow import OwnerWorkflow,serve_json_lines
from deploy_workflow.earnings_workflow import _classify_frame
root=Path(tempfile.mkdtemp(prefix='parser-',dir='/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-codex-findings-review-64c673/ee01671b-a922-47ba-ad87-32129314cd1e/scratchpad/v-tools/legacy/tools/probe-data'))
valid={'operation':'invoke','tool':'read_pages','arguments':{'source_id':'identity','first_page':1,'last_page':1}}
variants={
 'surrogate_query':json.dumps({'operation':'invoke','tool':'search_pack','arguments':{'query':'\ud800'}}),
 'surrogate_key':json.dumps({'operation':'invoke','tool':'search_pack','arguments':{'query':'x','\ud800':1}}),
 'surrogate_tool':json.dumps({'operation':'invoke','tool':'\ud800','arguments':{}}),
 'deep_args':'{"operation":"invoke","tool":"search_pack","arguments":{"query":"x","extra":'+ '['*210+'0'+']'*210+'}}',
 'nonfinite':'{"operation":"invoke","tool":"search_pack","arguments":{"query":NaN}}',
 'overflow':'{"operation":"invoke","tool":"search_pack","arguments":{"query":1e9999}}',
 'syntax':'{broken',
 'duplicate_query':'{"operation":"invoke","tool":"search_pack","arguments":{"query":"x","query":"Northbridge"}}',
}
for name,bad in variants.items():
    w=OwnerWorkflow.create(root/name/'store',make_pack(),publication_directory=root/name/'model')
    reader=io.StringIO(bad+'\n'+json.dumps(valid)+'\n')
    writer=io.StringIO()
    serve_json_lines(w,reader,writer,destination=root/name/'receipt.json',participant='parser-review')
    replies=[json.loads(s) for s in writer.getvalue().splitlines()]
    states=[(r.get('status'),r.get('error_code')) for r in replies]
    earnings_frame=bad.replace('"operation"','"op"').encode()+b'\n'
    op,req,error=_classify_frame(earnings_frame)
    print(name,states,'earnings classify',(op,error))
    if name.startswith('surrogate') or name=='deep_args':
        assert states==[('refused','bad_arguments'),('refused','identity_mismatch')]
        assert error=='bad_arguments'
    else:
        assert states[1]==('ok',None)
print('all parser boundary assertions passed')
