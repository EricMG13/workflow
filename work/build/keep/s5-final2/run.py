"""Deferred long runs for the open-items merge (f25f62d) on ../s5-final2: at most 6 concurrent
processes (the test-speed session's budget alongside its timing pair). One log per job."""
import subprocess, time, os, pathlib, datetime
W = "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s5-final2"
L = "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6"
P, O = f"{L}/.venv/bin/python", pathlib.Path(f"{L}/work/build/keep/s5-final2")
PY = [P, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rfE"]
EA = "test_real_retained_owner_submission_resumes_exact_session_and_finishes_once"
EB = "test_real_refused_session or test_actual_composed_new_money or test_unresolved_empty_session"
fast = (pathlib.Path(L) / "work/build/keep/fast-set.txt").read_text().split()
CZR = "cases/czr-2026q2-earnings-update"
(O / "czr-root").mkdir(exist_ok=True)
JOBS = [
    ("j00-fast", PY + fast + ["tests/test_shell_css.py"]),
    ("j01-czr-partial", [P, f"{CZR}/partial-builder/run.py", str(O / "czr-root"), f"{CZR}/submissions-partial.json"]),
    ("j02-cp2h", PY + ["tests/test_owner_cp2h.py"]),
    ("j03-cp4c", PY + ["tests/test_owner_cp4c.py", "-k", "not never_wedges"]),
    ("j04-s1a-workflow", PY + ["tests/test_owner_s1a.py", "tests/test_owner_workflow.py"]),
    ("j05-earn-a", PY + ["tests/test_earnings_workflow.py", "-k", EA]),
    ("j06-earn-c", PY + ["tests/test_earnings_workflow.py", "-k", f"not ({EA} or {EB})"]),
    ("j07-g2-cp2h-cp3d", PY + ["tests/test_owner_rendering.py", "-k", "cp2h or cp3d"]),
    ("j08-cp4-cp2a", PY + ["tests/test_owner_cp4.py", "tests/test_owner_cp2a.py"]),
    ("j09-earn-b", PY + ["tests/test_earnings_workflow.py", "-k", EB]),
    ("j10-cpos-tools-fin", PY + ["tests/test_owner_cpos.py", "tests/test_source_tools.py", "tests/test_financial_workflow.py"]),
    ("j11-cp3d-cp2e", PY + ["tests/test_owner_cp3d.py", "tests/test_owner_cp2e.py"]),
]
env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": "src:tests"}
now = lambda: datetime.datetime.now().strftime("%H:%M")
running, queue = {}, list(JOBS)
while queue or running:
    while queue and len(running) < 6:
        name, cmd = queue.pop(0)
        log = open(O / f"{name}.log", "w")
        log.write(f"start {now()}\n"); log.flush()
        running[name] = (subprocess.Popen(cmd, cwd=W, env=env, stdout=log, stderr=subprocess.STDOUT), log)
        print(f"{now()} start {name}", flush=True)
    for name, (proc, log) in list(running.items()):
        if proc.poll() is not None:
            log.write(f"exit={proc.returncode} end {now()}\n"); log.close()
            print(f"{now()} {name} exit={proc.returncode}", flush=True)
            del running[name]
    time.sleep(20)
