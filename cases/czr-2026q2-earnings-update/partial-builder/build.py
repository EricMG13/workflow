import sys, json, importlib
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
names = sys.argv[2:]
stages = [importlib.import_module(n).stage() for n in names]
figs = {}
for n in names:
    m = importlib.import_module(n)
    figs.update(getattr(m, "FIGURES", {}))
out = {"stages": stages}
if figs: out["figures"] = figs
open(sys.argv[1], "w").write(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
print("wrote", sys.argv[1], len(stages), "stages")
