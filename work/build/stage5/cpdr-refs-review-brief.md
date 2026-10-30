# CP-DR reference refusal: review (stage contract; mx-precise, read-only)

Change: `claude/s5-cpdr-refs` `e5ecf6d..eb7e517` in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a4a62637d498b45c2`. RED is 44f2649 (the controller ran it: 3 failed, 171 passed) and the fix is eb7e517. On the controller's gates, the CP-DR connect, method and owner suites gave 297 passed; ruff, format and mypy exit 0; suppressions 13 and 5. Logs: lane `work/build/keep/cpdr-refs-red.log` and `cpdr-refs-gates.log`. Brief: lane `work/build/stage5/cpdr-refs-brief.md`, ruling item 73.

Write probes only under lane `work/build/keep/cpdr-refs-review/`. Run Python as one plain command from the change's worktree root (`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "<lane>/.venv/bin/python" -I <probe>`). If it is refused, stop and report it; do not work around it. Run no full suite.

## Check
1. **Parity with CP-2E.** The rule matches `cp2e.run_text`, including the token kinds that count as a reference. A malformed answer gives only the RunText issue (the new `continue`).
2. **Only changes behaviour where intended.** No frozen CP-DR text or pinned refusal moves. Probe this against the pre-fix code: every frozen submission's `check()` and every pinned refusal is identical before and after.
3. **No wedge.** An answer with a reference never reaches `compose` or settle after a valid step.
4. **Docstrings** state the order truthfully.
5. **Policy.** No stub, no catch-all; the issue text does not echo the input.

## Output (text, under 500 tokens)
- verdict (APPROVE or REVISE);
- findings ranked High, Medium, Low, each with the probe path and exit code;
- a `Not verified:` line.
