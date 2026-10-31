# T5 (H05): fix rounds so far (written by the controller from the builder's and reviewers' text reports)

Branch `claude/s8-h05` in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-ab34920acb6e018fd`, from 88fbda46.

- **Build** (mx-feature ab34920a), d1d700d5 RED and cd85de8c fix:
  - `_json_arguments` gains `MAX_ARGUMENT_DEPTH = 100` (jiter refuses depth >= 200 in pydantic-core 2.50.1) and a `json.dumps(..., ensure_ascii=False).encode("utf-8")` check.
  - The refusal is `bad_arguments` with `{}`.
- **Round 1** (8de8b999, tests only): a test defect. `search_pack` refuses unknown keys at tool level, so the depth tests now tell a host refusal (`{}`) from a tool refusal (arguments kept). Not counted as a fix round.
- **Review** (mx-adversary aa37107e): REVISE, Medium. A lone-surrogate tool name still desynced the session.
- **Round 2** (6a1da7d5 RED, 7961c63c fix): an unencodable str name becomes `""` and is refused `bad_arguments` with `{}`. e1e03134 is the controller's ruff format.
- **Re-review** (mx-adversary ab6a003c): REVISE, Medium, introduced by round 2.
  - `("", {}, bad_arguments)` does not replay: receipt verification re-runs `invoke(call.tool, call.arguments)` (`owner_workflow.py:~2325`, `financial_workflow.py:~1131`), `invoke("", {})` gives `not_permitted`, and `write_receipt` then refuses `identity_mismatch`.
  - p7 predates T5: a non-str tool with bad arguments did the same.
- **Round 3** (9e2811c0 RED, af9ceea1 fix): an unrepresentable name (non-str, or an unencodable str) is refused `not_permitted` with `""` and `{}` before the arguments check. RED 7 failed; GREEN 18/18; p1-p7 exit 0.
- **Re-review** (mx-adversary af56b98f): APPROVE for the round-2 Medium, but the controller's rerun confirms these remain open:
  - **Medium** (the same invariant; partly introduced by T5's cd85de8c, partly predating it). `p8_refusal_matrix.py` exits 1 on 9 cells. A str name the session does not offer (`""`, `"foo"`, or `extract_statements` outside `financials`) with any argument refusal (depth over 100, a surrogate value, or non-dict arguments) gives `(name, {}, bad_arguments)`. Its replay gives `not_permitted`, so the run cannot seal.
    - Before T5, only the non-dict form existed. The depth and surrogate forms come from cd85de8c.
  - **Low, introduced by af9ceea1** (python-api callers only): `tool_name != ""` runs the caller's `__ne__` outside any try (`host.py:~1072`).
    - `p9_ne_and_lock.py` (a) exits 1: a raising `__ne__` desyncs.
    - `p10_eq_nonstr_bad_args.py` exits 1: a non-str whose `__eq__` matches `""`, with bad arguments, gives `("", {}, bad_arguments)`.
  - **Low, predates T5:** the lock-path receipt `(name, copied, not_permitted)` replays as `ok` (`p9_ne_and_lock.py` (b); direct `SourceSession` use only).
  - **Info:** `(tool, {}, bad_arguments)` replays for `search_pack`/`read_pages`/`extract_statements` only because each requires an argument.

All probes are in `work/build/keep/s8-t5/review/`; run each with `PYTHONPATH=src:tests:<that dir>`.
