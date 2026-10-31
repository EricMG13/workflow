"""T6 review probe: D12 records, chain, imported shas, pins vs file shas. Usage: probe <W> <rev>."""
import hashlib, json, subprocess, sys
W, REV = sys.argv[1], sys.argv[2]
def show(rev, path):
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=W, capture_output=True, check=True).stdout
def h(b): return hashlib.sha256(b).hexdigest()
bad = 0
m = json.loads(show(REV, "docs/reuse/manifest.json"))
files = {f["destination"]: f["sha256"] for f in m["files"]}
recs = m["post_import_patches"]
new = [r for r in recs if r.get("review") == "docs/rulings/2026-10-29-stage3.md item 86"]
for r in new:
    c, p = r["project_commit"], r["destination"]
    prior, cur = h(show(c + "^1", p)), h(show(c, p))
    idx = recs.index(r)
    last = [x for x in recs[:idx] if x["destination"] == p]
    ok = (prior == r["prior_project_sha256"] and cur == r["sha256"]
          and r["imported_sha256"] == files[p] and last and last[-1]["sha256"] == prior
          and list(r) == list(recs[idx - 1 if idx == len(recs) - 3 else idx - 1]))
    print(c[:8], p, ok, prior[:8], cur[:8]); bad |= not ok
for p in ("src/deploy_vii/contracts.py", "src/deploy_vii/execution.py"):
    tip = h(show(REV, p)); chain = [x for x in recs if x["destination"] == p][-1]["sha256"]
    print("tip", p, tip == chain); bad |= tip != chain
b = show(REV, "cases/cpos-owner/builder/build.py").decode()
man = json.loads(show(REV, "cases/cpos-owner/manifest.json"))
pins = json.loads(show(REV, "cases/PINS.json"))
for p in ("src/deploy_vii/report_view.py", "src/deploy_vii/assets/app.js", "src/deploy_vii/render.py", "src/deploy_vii/contracts.py"):
    cur = h(show(REV, p)); ok = f'"{p}": "{cur}"' in b and cur in json.dumps(man)
    print("pin", p, ok); bad |= not ok
for p in ("cases/cpos-owner/builder/build.py", "cases/cpos-owner/manifest.json", "cases/cpos-owner/expected.json", "cases/cpos-owner/submissions.json"):
    ok = pins[p] == h(show(REV, p)); print("PINS", p, ok); bad |= not ok
sys.exit(bad)
