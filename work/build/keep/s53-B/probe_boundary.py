"""Lens B step 1: src/deploy_vii changes in <base>..<rev> that are neither a reused file with a
post_import_patches record nor a G1X section-6 admitted new file (bindings/<cp>.py), plus
deploy_vii -> deploy_workflow imports new in the range. Usage: python -I probe_boundary.py <repo> <base> <rev>.
Exit 1 if any change has neither admission."""
import json, re, subprocess, sys
repo, base, rev = sys.argv[1:4]
git = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True).stdout
m = json.loads(git("show", f"{rev}:docs/reuse/manifest.json"))
reused = {f["destination"] for f in m["files"]}
recorded = {r["destination"] for r in m["post_import_patches"]}
reasons = " ".join(r.get("reason", "") for r in m["post_import_patches"])
fail = 0
for line in git("diff", "--name-status", base, rev, "--", "src/deploy_vii").splitlines():
    status, path = line.split("\t")[0], line.split("\t")[-1]
    if path in reused:
        ok = path in recorded or status == "A"  # an import is recorded in files[]
        kind = "reused+record" if path in recorded else ("import" if status == "A" else "NO RECORD")
    elif re.fullmatch(r"src/deploy_vii/bindings/cp[0-9a-z]+\.py", path):
        ok, kind = True, "G1X s6 bindings file" + (" (named in a record)" if path.split("/")[-1] in reasons else "")
    elif path.startswith("src/deploy_vii/methods/") and path.endswith(".md"):
        ok, kind = True, "method note (docs)"
    else:
        ok, kind = False, "NEW deploy_vii file: no manifest record, no G1X s6 admission"
    if not ok:
        fail += 1
    print(("  " if ok else "!!"), status, path, "-", kind)
def imports(commit):
    out = git("grep", "-n", "-E", r"^[[:space:]]*(from|import) deploy_workflow", commit, "--", "src/deploy_vii")
    return {re.sub(r"^[^:]+:[^:]+:\d+:", "", l).strip() + "  @" + l.split(":")[1] for l in out.splitlines()}
new = sorted(imports(rev) - imports(base))
print("deploy_vii -> deploy_workflow imports new in range:", *new, sep="\n  ")
sys.exit(1 if fail else 0)
