import importlib, json, re
from unittest.mock import patch
import test_connect_cpdr as dr
import test_connect_cp8 as cp8
r = importlib.import_module('deploy_vii.render')
dr.test_a_question_with_a_bracketed_citation_renders_as_written()
print('baseline CP-DR regression: PASS')
real_display, real_table, real_render = r.display, r.table_display, r.render
pages=[]
def display(fact):
    return 'QUESTION DROPPED BY MUTANT' if fact.text and '[sic]?' in fact.text else real_display(fact)
def table(fact, gap):
    return 'QUESTION DROPPED BY MUTANT' if fact.text and '[sic]?' in fact.text else real_table(fact, gap)
def capture(*args, **kwargs):
    page=real_render(*args, **kwargs)
    pages.append(page)
    return page
with patch.object(r, 'display', display), patch.object(r, 'table_display', table), patch.object(r, 'render', capture):
    dr.test_a_question_with_a_bracketed_citation_renders_as_written()
    print('mutant CP-DR regression: PASS (survived)')
payload=json.loads(re.search(r'<script[^>]*id="report-data"[^>]*>(.*?)</script>', pages[0], re.S)[1])
facts=[f for m in payload['modules'] if m['module_id']=='CP-DR' for f in m['facts'] if f.get('text') and '[sic]?' in f['text']]
assert len(facts)==1
assert facts[0]['display']==facts[0]['table_display']=='QUESTION DROPPED BY MUTANT'
print(json.dumps({k:facts[0][k] for k in ['fact_id','text','display','table_display']},indent=2))
quote='Section 7.11 [Reserved]; see [sic] and [1].'
base=cp8._what_changed_view('positive')
fid=cp8._thesis_fact_id(base)
changed=cp8._what_changed_view('positive',{fid:quote})
a,b=cp8._what_changed_lines(base),cp8._what_changed_lines(changed)
assert a==b and quote not in repr(b)
cp8.test_a_verbatim_quote_holding_brackets_is_shown_as_written_in_block_and_payload()
print('CP-8 block branch: modified',fid,'is absent; what-changed lines byte-equivalent to unmodified fixture')
