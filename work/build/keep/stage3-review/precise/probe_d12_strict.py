"""Strict D12 probe. For every reused file (manifest `files[].destination`) changed between
<base> and <rev>: (a) a post_import_patches record exists for the change (records only in
local_patch_lineage are reported as MISPLACED); (b) the chain of post_import_patches records links
prior -> sha256 from the imported sha; (c) the LAST post_import_patches record's sha256 equals the
file at <rev>; (d) round 5 item 19: prior_project_sha256 = file in first parent of project_commit,
and the file at project_commit = sha256.
Usage: python -I probe_d12_strict.py <repo> <base> <rev>. Exit 1 on any failure."""
import hashlib, json, subprocess, sys

repo, base, rev = sys.argv[1:4]


def git(*a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, check=False)


def sha_at(commit, path):
    r = git("show", f"{commit}:{path}")
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None


m = json.loads(git("show", f"{rev}:docs/reuse/manifest.json").stdout)
imported = {f["destination"]: f["sha256"] for f in m["files"]}
changed = git("diff", "--name-only", base, rev).stdout.decode().split()
fail = 0
for d in sorted(set(changed) & set(imported)):
    recs = [r for r in m["post_import_patches"] if r["destination"] == d]
    lpl = [r for r in m.get("local_patch_lineage", []) if r["destination"] == d]
    at_rev = sha_at(rev, d)
    print(d, "file@rev", at_rev[:8])
    chain = imported[d]
    for r in recs:
        pc = r["project_commit"]
        fp = sha_at(pc + "^1", d)
        at_pc = sha_at(pc, d)
        okc = r.get("prior_project_sha256") in (chain, None) or r.get("prior_project_sha256") == chain
        ok19 = fp == r.get("prior_project_sha256") and at_pc == r["sha256"]
        print(f"   pip @{pc[:7]} prior={str(r.get('prior_project_sha256'))[:8]} -> {r['sha256'][:8]}"
              f" chain={'ok' if okc else 'GAP'} item19={'ok' if ok19 else f'BAD(fp={str(fp)[:8]},at={str(at_pc)[:8]})'}")
        fail += (not okc) + (not ok19)
        chain = r["sha256"]
    for r in lpl:
        print(f"   lpl @{r['project_commit'][:7]} -> {r['sha256'][:8]}"
              f"{'  MISPLACED (not in post_import_patches)' if r['sha256'] == at_rev and chain != at_rev else ''}")
    if chain != at_rev:
        print(f"   FAIL last post_import_patches sha {chain[:8]} != file@rev {at_rev[:8]}")
        fail += 1
sys.exit(1 if fail else 0)
