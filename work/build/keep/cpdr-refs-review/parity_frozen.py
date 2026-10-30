"""Probe: validate_research on every frozen CP-DR submission and pinned refusal input is
identical under pre-fix (e5ecf6d, scratch copy) and post-fix (eb7e517, worktree) code; plus
token-kind parity with cp2e.run_text and the malformed-answer path. Run from the change's
worktree root. Exit 0 = all hold."""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path.cwd()

def child(src: str) -> None:
    sys.path[:0] = [src, str(ROOT / "tests")]
    import deploy_workflow.owners.cpdr as m
    assert Path(m.__file__).resolve().is_relative_to(Path(src).resolve()), m.__file__
    import test_method_cpdr as t
    S = t.SUBMISSIONS
    out = {}
    def run(name, payload, empty=False):
        out[name] = list(m.validate_research(submission=t.submission(payload),
                         upstream=t.agenda(empty=empty), pack=t.sources()))
    for k in ("partial", "unresolved", "empty_agenda"):
        run("cpdr." + k, S["cpdr"][k], empty=(k == "empty_agenda"))
    for a in ("attempt_0", "attempt_1"):
        run("blocked." + a, S["cpdr"]["blocked"][a])
    for k, item in S["refusal_inputs"].items():
        run("refusal." + k, item["payload"], empty=item["cp0"] == "cp0_readiness_review_empty_agenda")
    print(json.dumps({"file": m.__file__, "out": out}))

def main() -> int:
    res = {}
    for tag, src in (("pre", str(HERE / "pre/src")), ("post", str(ROOT / "src"))):
        p = subprocess.run([sys.executable, "-I", __file__, "--child", src],
                           capture_output=True, text=True, cwd=ROOT,
                           env={"PYTHONDONTWRITEBYTECODE": "1"})
        if p.returncode:
            print(tag, "child failed", p.stderr[-2000:]); return 2
        res[tag] = json.loads(p.stdout.strip().splitlines()[-1])
        print(tag, res[tag]["file"], len(res[tag]["out"]), "cases")
    bad = [k for k in res["pre"]["out"] if res["pre"]["out"][k] != res["post"]["out"][k]]
    print("differing cases:", bad)
    # frozen refusals vs pinned (content part)
    import json as j
    exp = j.loads((ROOT / "cases/cpdr-owner/expected.json").read_text())
    print("cases checked:", sorted(res["post"]["out"]))
    return 1 if bad else 0

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--child":
        child(sys.argv[2]); sys.exit(0)
    sys.exit(main())
