import json,sys,collections,re
lines=open(sys.argv[1]).read().splitlines()
sc=[];gaps=[]
mode=None
for ln in lines:
    if ln.startswith("kind="):
        mode=ln.split()[0][5:]; continue
    if mode in("source_check","gap") and ln.startswith("["):
        (sc if mode=="source_check" else gaps).append(json.loads(ln))
b=[g for g in gaps if g[1]=="BLOCK"]
print(collections.Counter(g[2] for g in b))
def norm(d): return re.sub(r"-?\d[\d,.]*","N",d)[:200]
c=collections.Counter(norm(g[5]) for g in b)
for k,v in c.most_common(): print(v,k)
print("--- source checks: reported/calculated presence by type")
c2=collections.Counter((r[1], r[5] is None, r[6] is None, r[7] is None) for r in sc)
for k,v in sorted(c2.items()): print(v,k)
