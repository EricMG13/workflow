import json,sys,collections
lines=open(sys.argv[1]).read().splitlines()
sc=[];gaps=[]
mode=None
for ln in lines:
    if ln.startswith("kind="):
        mode=ln.split()[0][5:]; continue
    if mode in("source_check","gap") and ln.startswith("["):
        (sc if mode=="source_check" else gaps).append(json.loads(ln))
print("source_check",len(sc),collections.Counter((r[1],r[4]) for r in sc))
b=[g for g in gaps if g[1]=="BLOCK"]
print("gaps",len(gaps),"BLOCK",len(b))
print(collections.Counter((g[2],g[3]) for g in b))
seen=collections.defaultdict(set)
for g in b: seen[(g[2],g[3])].add(g[5][:160])
for k,v in seen.items():
    print("==",k)
    for d in sorted(v)[:6]: print("   ",d)
print("source_check by type/status:")
for r in sc[:3]: print(r)
