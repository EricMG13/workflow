# A4 fixture-reference correction review


PASS for the exact bounded fixture correction. Original A4 contract/review cf56/ba27 remain unchanged; original oracle a23517e8 is preserved exactly in integrity-expected-pre-reference-fix.json. Active oracle SHA256 `90871a0027bf5fd616ef09495e92399735f22a2dafad76d2488134a892733c13`; addendum SHA256 `92c2851b4bfc01354929e374c45f58d9292db98ec935f88f0bbb35b841367173`; archive SHA256 `a23517e8bcd3b344496ca982e735e4882065a4b27345f5a0e770e922ba25bd8f`. This review is the same independent Sol/high expected-result role, distinct from C1 implementation; no hidden telemetry claim.

Root cause: prose._fact_issues at prose.py254–276 rejects any numeric chip when amount is not None, including Decimal zero. Native-unit figures over cited known0 are valid. prose.issues282–300 classifies missing chip IDs as gap runs, avoiding a numeric figure over missing; _Checker.claim at cp5_integrity.py510–541 still records the referenced missing fact and emits unsettled_fact only when Claim.limitation is absent. Every original numeric amount/status/unit/scale/citation stays unchanged.

All eleven mutations were traced from source, not adapter/candidate output. The addendum table records exact expected counts and implications. readiness.citation_issues116–155 gives one issue per invalid citation; _Checker.facts/claim separates fact/claim citation and scale/prose categories; identity_groups355–434 yields two differing groups for the appended same-ID/same-coordinate value; _review_issues610–690 rejects supported over marked refs and excludes non-evaluated reviews; _review_findings822–850 adds the unchanged analyst kinds; integrity_review1188–1231 makes own findings/gaps restricted. No confirmed count/category mismatch remains once blocked/empty valid-review declarations are explicit.

Exactly six scalar JSON leaves changed: two baseline Claim.texts, two missing-fact mutation declarations, and blocked/empty scope review declarations. Diff logic independently asserted identical key sets/list lengths and unchanged remaining data. No financial values/counts/categories/wire/caps/API/source/permission changes. No product/test/B1/delivery-author edits or runtime imports/engines/jobs/providers. Adjacent B1 exact numeric-chip claim issue was reported to LEAD for separate owner-author amendment, not edited or silently accepted here.

Read source hashes: prose33f4de8945127d4e2af005949c4d560a1b3d6d20629be8c42ce86e684784a74f; CP5 core84fbe447ab9f1c8598030cf44533072dccdd114d3d34c6c5bb0d20a8d5c3225c; readiness1038a37a8227f426e4d6e1e79985e986e23e77f9e7cdee763a884477162ccffa; report_viewc934d50152c06d52d2646031ce76bf961d7e19fbb460f4880ca4bde69392fa98; Execution752ae7c74774f4410db0a24bb49c443d777dac7c8e3e6c8f8a11e088a3c9bff3.

Known separate dependency: actual B1 owner settlement remains unqualified until its original author freezes the confirmed numeric-figure/gap-chip correction. Root confirmed the same prose guard at candidate_issues. A4 current owner authority and static first-case claim catalog may need a source-grounded pin/byte update after that override; no product engine or count relaxation is authorized. Original A4 static proof is retained as byte-feasibility evidence, not proof the erroneous numeric-chip owner claim can settle or be CP5 clean.


## Same review continuation: B1 grammar dependency closed

Independent review of root-authored B1 claim override3341de53/current owner oracle a37dc25f is recorded in owner-claim-reference-review.md. Six positive and two known no-YoY native monetary figures retain the same fact IDs; three missing no-YoY chips remain. No actual settlement/CP5clean claim follows from grammar validity. The previously recorded dependency is now closed for the exact source expectation only.

The exact ef5 intermediate integrity oracle is archived at integrity-expected-pre-owner-reference-update.json. Active integrity oracle 90871a0027bf5fd616ef09495e92399735f22a2dafad76d2488134a892733c13 differs from ef5 ONLY at four scalar leaves: owner oracle hash at top/proof, terminal claim page977->1031 and ordered claim catalog digest67396429...->5b4b95fc79cfe552df2c66452b7d147bf780b1da62f64e175adb2b666de77428. Full source-only15catalog/maximal-prefix rederivation confirms unchanged65tools/70messages/manifest3459/maxBODY8088, all refs/counts/values/wire/caps unchanged. The old proof source remains untouched and archived. Current addendum SHA256 92c2851b4bfc01354929e374c45f58d9292db98ec935f88f0bbb35b841367173. Original A4cf56/ba27 and B1e66 remain immutable.


## Current read-only proof reproduction source

This current source handles both adopted figure and chip IDs, preserves full identifiers and scans every permitted prefix. It prints proof JSON and writes no file. The original proof source/history remains untouched.

```python
from pathlib import Path
import json,hashlib,re
r=Path('/Users/ericguei/Documents/Deploy Workflow Sessions/lead');p=r/'cases/integrity/expected.json';o=json.loads(p.read_text())
before_update=json.loads(json.dumps(o));oldproof=o['static_first_case_transport_proof'];o['owner_oracle_sha256']=hashlib.sha256((r/'cases/earnings/owner-expected.json').read_bytes()).hexdigest();assert o['owner_oracle_sha256']=='a37dc25f8f756364ae88726cdec3f2de1bbf4c20892ca910d22e9646186efd9d'
C=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
H=lambda x:hashlib.sha256(x.encode()).hexdigest()
K=lambda x:H(C(x));hh='f'*64
blob=Path('/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/work/actual-cp1-charts-1/positive/store/blobs/6d41c0a0b6782e4eace1f93d7b028f89041480b3d69721d6b69cfda4afcea8be')
raw=blob.read_bytes();mh=hashlib.sha256(raw).hexdigest();m=json.loads(raw);fs={f['fact_id']:f for f in m['facts']}
owner=json.loads((r/'cases/earnings/owner-expected.json').read_text());rend=json.loads((r/'cases/earnings/render-expected.json').read_text());run=next(c['run'] for c in owner['manifest']['cases'] if c['case_id']=='E-QOQ-FLAT')
pr={'module_id':'CP-1','sha256':mh,'status':'restricted'};pb={'module_id':'CP-1B','sha256':'b'*64,'status':'restricted'}
def coord(f):return {k:f[k] for k in ['fact_id','table_id','row_id','field']}
def fr(f):return {'producer_module_id':'CP-1','producer_sha256':mh,**coord(f)}
def qr(pro,f,kind='fact'):return {'producer_module_id':pro['module_id'],'producer_sha256':pro['sha256'],'kind':kind,'ref':f}
def handles(f):return [{k:c[k] for k in ['source_id','source_sha256','locator']} for c in f.get('citations',[])]
def fh(f):return H(json.dumps(f,ensure_ascii=False,separators=(',',':')))
def unioncs(facts):
 found=[];seen=set()
 for f in facts:
  for c in f.get('citations',[]):
   k=C(c)
   if k not in seen:seen.add(k);found.append(c)
 return found
periods={};metrics={}
for f in m['facts']:
 if f['table_id']=='T4.14':periods.setdefault(f['row_id'],{})[f['field']]=f
 if f['table_id']=='T4.10':metrics.setdefault(f['row_id'],{})[f['field']]=f
periods={x['period_id']['text']:x for x in periods.values()};metrics={x['field_1']['text']:x for x in metrics.values()}
def basis(pid):return 'model-basis:'+H(''.join(str(len(x))+':'+x for x in ['historical','Q:'+pid]))
bases={pid:basis(pid) for pid in ['q3-2025','q4-2025']};measures=owner['lineage']['measure_order'];pf=['period_id','period_type','fiscal_year','fiscal_quarter','start_date','end_date','currency','unit','accounting_basis','entity_perimeter']
lineages=[];sourceids=set();selected={}
for measure in measures:
 row=metrics[measure];primary={pid:row[bases[pid]] for pid in bases};selected[measure]=primary
 companions=[row['field_1'],*[periods[pid][k] for pid in bases for k in pf]]
 d={'measure_id':measure,'prior':None,'current':None,'companions':[fr(f) for f in companions]}
 for role,pid in [('prior','q3-2025'),('current','q4-2025')]:
  f=primary[pid];d[role]={'fact':fr(f),'period_id':pid,'basis_id':bases[pid],'source_period':f['period'],'source_basis':f['basis'],'fact_sha256':fh(f),'citation_handles':handles(f)}
 lineages.append(d);sourceids.update(f['fact_id'] for f in list(primary.values())+companions)
bundletext=C({'producer_module_id':'CP-1','producer_sha256':mh,'prior_period_id':'q3-2025','current_period_id':'q4-2025','prior_basis_id':bases['q3-2025'],'current_basis_id':bases['q4-2025'],'operands':lineages});eid='cp1b:T1B.3:evidence.inputs:assessment';bid='lineage-bundle:'+K({'producer_sha256':pb['sha256'],'fact_id':eid,'raw_sha256':H(bundletext)})
heads=[];ops=[];comps=[];cites=[];payloads={};rawsizes=[]
for n,d in enumerate(lineages):
 rawline=C(d);lid='lineage:'+K({'producer_sha256':pb['sha256'],'measure_id':d['measure_id'],'raw_sha256':H(rawline)});rawsizes.append(len(rawline.encode()));payloads[d['measure_id']]={'schema_version':'cp5-protected-payload/1','kind':'cp1b_operand_lineage','raw_sha256':H(rawline),'raw_bytes':len(rawline.encode()),'handle':lid,'projection':'bounded_lineage_catalog/1'};ids={}
 for role in ['prior','current']:
  x=d[role];oid='lineage-operand:'+K({'lineage_id':lid,'role':role});ids[role]=oid
  cc=[{'lineage_id':lid,'operand_id':oid,'ordinal':i,'citation':c} for i,c in enumerate(x['citation_handles'])];cites+=cc
  ops.append({'operand_id':oid,'lineage_id':lid,'role':role,'fact':x['fact'],'period_id':x['period_id'],'basis_id':x['basis_id'],'source_period':x['source_period'],'source_basis_sha256':H(x['source_basis']),'source_basis_bytes':len(x['source_basis'].encode()),'fact_sha256':x['fact_sha256'],'citation_count':len(cc),'citations_sha256':K(cc)})
 cc=[{'lineage_id':lid,'ordinal':i,'fact':f} for i,f in enumerate(d['companions'])];comps+=cc
 heads.append({'lineage_id':lid,'bundle_id':bid,'ordinal':n,'measure_id':d['measure_id'],'raw_sha256':H(rawline),'raw_bytes':len(rawline.encode()),'prior_operand_id':ids['prior'],'current_operand_id':ids['current'],'companion_count':len(cc),'companions_sha256':K(cc)})
bf={};allcs=unioncs([fs[i] for i in sorted(sourceids)])
for tab in rend['positive']['tables']:
 for row in tab['rows']:
  for cell in row['cells']:
   measure=row['row_id'];field=cell['field'];primary=selected[measure];src=primary.get(cell['period'])
   cs=src['citations'] if src else unioncs([primary['q3-2025'],primary['q4-2025']])
   b={'fact_id':cell['fact_id'],'label':'L'*160,'table_id':tab['table_id'],'row_id':measure,'field':field,'amount':cell['value'],'text':None,'status':cell['status'],'unit':cell['unit'],'currency':cell['currency'],'scale':cell['scale'],'period':cell['period'],'basis':src['basis'] if src else payloads[measure],'denominator':src.get('denominator') if src else None,'limitation':'L'*512,'calculation_id':None if src else 'cp1b-calc:q3-2025:q4-2025:'+measure+':'+field,'value_class':src.get('value_class') if src else 'calculated','calculation_status':cell['status'],'citations':cs};bf[b['fact_id']]=b
for a in owner['assessments']['E-QOQ-FLAT']:
 fid='cp1b:T1B.3:'+a['row_id']+':assessment';text=('A'*512) if a.get('text') is not None else None
 if a['row_id']=='evidence.inputs':text={'schema_version':'cp5-protected-payload/1','kind':'cp1b_evidence_bundle','raw_sha256':H(bundletext),'raw_bytes':len(bundletext.encode()),'handle':bid,'projection':'bounded_lineage_catalog/1'}
 b={'fact_id':fid,'label':'L'*160,'table_id':'T1B.3','row_id':a['row_id'],'field':'assessment','amount':None,'text':text,'status':a['status'],'unit':None,'currency':None,'scale':'1','period':'q3-2025->q4-2025','basis':None,'denominator':None,'limitation':a.get('limitation'),'calculation_id':None,'value_class':a['value_class'],'calculation_status':None,'citations':allcs if a['citations_policy']!='none' else []};bf[fid]=b
assert len(bf)==44
claimids=set()
for c in m['claims']:
 for a,b in re.findall(r'\[([A-Za-z0-9_.:-]+)\]|\{([A-Za-z0-9_.:-]+)\|[^}]+\}',c['text']):claimids.add(a or b)
req=sourceids|claimids;ctxt=owner['claim']['texts']['E-QOQ-FLAT'];breq={a or b for a,b in re.findall(r'\[([A-Za-z0-9_.:-]+)\]|\{([A-Za-z0-9_.:-]+)\|[^}]+\}',ctxt)}
def cref(pro,f):
 hs=handles(f);return {'projection':'fact_citation_catalog/1','handle':'fact-citations:'+K({'producer_sha256':pro['sha256'],'fact_id':f['fact_id'],'fact_sha256':fh(f),'handles_sha256':K(hs)}),'count':len(hs),'sha256':K(hs)}
def safe(pro,f):
 keys=['fact_id','label','table_id','row_id','field','amount','text','status','unit','currency','scale','period','basis','denominator','limitation','calculation_id','value_class','calculation_status'];z={k:f.get(k) for k in keys};z['fact_sha256']=fh(f);z['citation_handles']=cref(pro,f);return z
fc=[]
for pro,facts in [(pr,[fs[i] for i in sorted(req)]),(pb,list(bf.values()))]:
 for f in facts:fc.extend({'owner_fact':qr(pro,f['fact_id']),'ordinal':n,'citation':c} for n,c in enumerate(handles(f)))
owners=[{'owner':pb,'coordinate':coord(f),'fact_sha256':fh(f),'citation_set':cref(pb,f),'basis_commitment':f['basis'] if isinstance(f['basis'],dict) else None,'text_commitment':f['text'] if isinstance(f['text'],dict) else None} for f in bf.values()]
bundle={'bundle_id':bid,'owner':pb,'owner_fact':qr(pb,eid),'raw_sha256':H(bundletext),'raw_bytes':len(bundletext.encode()),'source_producer':pr,'prior_period_id':'q3-2025','current_period_id':'q4-2025','prior_basis_id':bases['q3-2025'],'current_basis_id':bases['q4-2025'],'lineage_count':12,'lineages_sha256':K([x['lineage_id'] for x in heads]),'owner_fact_count':44,'owner_facts_sha256':K(owners)}
sections={s:[] for s in o['required_sections']+['fact_index']};sections.update({'lineage_bundles':[bundle],'lineage_headers':heads,'lineage_operands':ops,'lineage_companions':comps,'lineage_citations':cites,'lineage_owner_facts':owners,'fact_citations':fc})
sections['required_evidence']=[{'producer':pr,'fact':safe(pr,fs[i]),'reasons':['claim_reference','lineage_primary','lineage_companion'],'claim_ids':['claim-id-padding'*4]} for i in sorted(req)]+[{'producer':pb,'fact':safe(pb,bf[i]),'reasons':['claim_reference'],'claim_ids':['cp1b-comparison']} for i in sorted(breq)]
for c in m['claims']:
 sections['claims'].append({'producer':pr,'claim_id':c['claim_id'],'text':c['text'],'limitation':c.get('limitation'),'citation_count':len(c['citations']),'touching_kinds':[]})
 sections['claim_citations'].extend({'producer':pr,'claim_id':c['claim_id'],'ref':c['claim_id']+'#c'+str(n+1),'citation':{k:x[k] for k in ['source_id','source_sha256','locator']},'flagged':False} for n,x in enumerate(c['citations']))
bcs=unioncs([bf[i] for i in sorted(breq)]);sections['claims'].append({'producer':pb,'claim_id':'cp1b-comparison','text':ctxt,'limitation':owner['claim']['limitations']['E-QOQ-FLAT'],'citation_count':len(bcs),'touching_kinds':[]})
sections['claim_citations'].extend({'producer':pb,'claim_id':'cp1b-comparison','ref':'cp1b-comparison#c'+str(n+1),'citation':{k:x[k] for k in ['source_id','source_sha256','locator']},'flagged':False} for n,x in enumerate(bcs))
sections['producers']=[{'producer':pr,'role':'evaluated','fact_count':len(fs),'claim_count':len(m['claims']),'claim_citation_count':sum(len(c['citations']) for c in m['claims'])},{'producer':pb,'role':'evaluated','fact_count':44,'claim_count':1,'claim_citation_count':len(bcs)}]
for pro,vals in [(pr,m['limitations']),(pb,owner['own_limitations']['E-QOQ-FLAT'])]:
 for n,v in enumerate(vals):
  for origin in ['upstream_module','inherited']:sections['limitations'].append({'producer':pro,'origin':origin,'ordinal':n,'text_sha256':H(v),'label':'Upstream restriction retained'})
S='a'*64;G='b'*64;M='c'*64;cursor='integrity-cursor:'+'d'*64
def body(sec,off,entries,done):return {'scope_sha256':S,'grant_sha256':G,'manifest_sha256':M,'section':sec,'total':len(sections[sec]),'offset':off,'entries':entries,'next_cursor':None if done else cursor,'complete':done}
proof={};calls=1
for sec in o['required_sections']:
 records=sections[sec];off=0;sizes=[];lengths=[]
 if not records:sizes=[len(C(body(sec,0,[],True)).encode())];lengths=[0]
 while off<len(records):
  nfit=0
  for n in range(1,min(20,len(records)-off)+1):
   if len(C(body(sec,off,records[off:off+n],off+n==len(records))).encode())<=8192:nfit=n
   else:pass
  if not nfit:raise RuntimeError(('indivisible',sec,off,len(C(body(sec,off,[records[off]],off+1==len(records))).encode())))
  sizes.append(len(C(body(sec,off,records[off:off+nfit],off+nfit==len(records))).encode()));lengths.append(nfit);off+=nfit
 single=max([len(C(body(sec,n,[x],n+1==len(records))).encode()) for n,x in enumerate(records)] or [0])
 proof[sec]={'entries':len(records),'pages':len(sizes),'page_entries':lengths,'body_bytes':sizes,'max_body_bytes':max(sizes),'max_indivisible_body_bytes':single,'ordered_entries_sha256':K(records)};calls+=len(sizes)
binding={'run_id':run['run_id'],'issuer_id':run['issuer_id'],'as_of':run['as_of'],'method_version':'deploy-v-r14','pack_sha256':hh,'snapshot_sha256':hh,'module_id':'CP-5','step_id':'integrity_review','ticket_id':'11111111-1111-4111-8111-111111111111','attempt':0,'inputs':[{'input_id':i,'sha256':hh,'status':'accepted' if i=='prepared-pack' else 'restricted'} for i in ['prepared-pack','CP-0','CP-1','CP-1B']]}
manifest={'schema_version':'cp5-integrity-manifest/1','binding':binding,'session_id':'integrity-session:'+'1'*64,'grant_sha256':G,'scope_sha256':S,'manifest_sha256':M,'producer_count':2,'evaluated_count':2,'blocked_count':0,'fact_count':len(fs)+44,'claim_count':len(sections['claims']),'claim_citation_count':len(sections['claim_citations']),'sections':[{'section':s,'count':len(sections[s]),'sha256':K(sections[s])} for s in sections],'limits':{k:v for k,v in o['limits'].items() if k!='grant_coordinate_total'}}
pm={'kind':'independent-stdlib-static-transport-envelope/1','qualification':'Transport bytes/counts only; genuine retained historical full CP1 IDs/metadata/citations and frozen B1/A3 literal amounts. Not actual fresh B1 execution or a new financial oracle. B1 full Fact hashes use 64hex proof placeholders after protected projection, not asserted raw candidate hashes.','reference_cp1_file':str(blob),'reference_cp1_sha256_before':mh,'reference_cp1_sha256_after':hashlib.sha256(blob.read_bytes()).hexdigest(),'owner_contract_sha256':o['owner_contract_sha256'],'owner_oracle_sha256':o['owner_oracle_sha256'],'case_id':'E-QOQ-FLAT','cp1_claims':len(m['claims']),'cp1_claim_named_facts':len(claimids),'lineage_point_count':12,'lineage_companion_count_each':[len(x['companions']) for x in lineages],'total_lineage_companions':len(comps),'total_lineage_operands':len(ops),'total_lineage_citations':len(cites),'unique_lineage_cp1_facts':len(sourceids),'cp1_required_evidence_count':len(req),'cp1b_required_evidence_count':len(breq),'cp1b_fact_identity_count':44,'full_raw_lineage_min_bytes':min(rawsizes),'full_raw_lineage_max_bytes':max(rawsizes),'full_raw_bundle_bytes':len(bundletext.encode()),'b1_metadata_padding':'B1 labels160chars, numeric limitations512chars, other nonprotected known assessment text512chars bound fixed first-case metadata. Raw amounts are fixed oracle strings; full real source IDs/row IDs/fields/citation ordinals and full64hex handles/cursors/36char ticket retain escaping overhead.','sections':proof,'manifest_body_bytes':len(C(manifest).encode()),'required_page_calls':calls-1,'whole_scope_verify_calls':1,'minimum_tool_calls':calls,'planned_message_count_with_setup_read_submission_two_seals':calls+5,'tool_cap':1024,'message_cap':2048,'max_page_bytes':max(x['max_body_bytes'] for x in proof.values()),'body_cap':8192,'all_pages_fit':all(x['max_body_bytes']<=8192 for x in proof.values()),'all_indivisible_records_fit':all(x['max_indivisible_body_bytes']<=8192 for x in proof.values()),'no_product_imports_or_execution':True}
assert pm['reference_cp1_sha256_before']==pm['reference_cp1_sha256_after'];assert pm['manifest_body_bytes']<=8192;assert calls<=1024
pm['proof_authority']=oldproof['proof_authority'];print('REPRODUCED_PROOF_JSON='+C(pm))
print(json.dumps({k:pm[k] for k in ['lineage_point_count','total_lineage_companions','total_lineage_operands','total_lineage_citations','cp1_required_evidence_count','cp1b_required_evidence_count','full_raw_lineage_min_bytes','full_raw_lineage_max_bytes','full_raw_bundle_bytes','manifest_body_bytes','minimum_tool_calls','planned_message_count_with_setup_read_submission_two_seals','max_page_bytes','all_pages_fit','all_indivisible_records_fit']},indent=2))
print([(s,x['entries'],x['pages'],x['max_body_bytes']) for s,x in proof.items()])

```
