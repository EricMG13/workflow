"""Map each CZR BLOCK gap (narrative read body) to its reconciliation check type and the
explanation that produced it; print the type x explanation table and present/absent sides.
Usage: python3 -I classify.py <read-1-narrative.txt>"""
import json,sys,collections,hashlib
lines=open(sys.argv[1]).read().splitlines()
kind=None; sc={}; gaps=[]
for ln in lines:
  if ln.startswith("kind="): kind=ln.split()[0][5:]; continue
  if not ln.startswith("["): continue
  r=json.loads(ln)
  if kind=="source_check":
    cid="recon:"+hashlib.sha256(json.dumps((r[3],r[1],r[2]),separators=(",",":")).encode()).hexdigest()
    sc[cid]=r
  elif kind=="gap": gaps.append(r)
t=collections.Counter(); unmatched=0
for g in gaps:
  if g[1]!="BLOCK": continue
  if g[2]!="source_audit": t[(g[2],"-",g[5][:70])]+=1; continue
  r=sc.get(g[3])
  if r is None: unmatched+=1; continue
  sides=("rep" if r[5] is not None else "-")+"/"+("calc" if r[6] is not None else "-")
  d=g[5]
  key=d.split(";")[0][:75]
  t[(r[1],sides,key)]+=1
for k,v in sorted(t.items()): print(v,k)
print("unmatched",unmatched,"total",sum(t.values()))
