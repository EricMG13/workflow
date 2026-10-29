# Stage 1 rulings round 5: brief (CP-8, CP-2G, CP-3C)

Implementer: the module's original implementer, resumed (opus). Review: a first mx-adversary review of the module after this round.

## Step 0
- From your worktree root, run `git merge <lane tip named in your dispatch>`. merge-tree shows it is clean against your commit.
- The lane tip carries the methodology change (a48990d), so re-pin any `manifest.frozen_inputs` or methodology sha your test asserts. The CP-1C precedent is 2524eb4: change the pin to the new sha and its value only, with no oracle edits.

## Inputs
| File | Section | Why |
|---|---|---|
| `docs/rulings/2026-10-28-stage1.md` | `# Round 5`: your module's section, then "LEAD notes and additions" (these take precedence) | The rulings to apply |
| Your report `work/build/stage1/<cp>/report.md` | "Rulings needed" and the choices to confirm | The cases each ruling answers |
| `docs/<CP>-OWNER-LEASE.md`, `cases/<cp>-owner/` | | Lease and frozen oracle; a ruling beats the lease |

## Process
1. Apply every ruling for your module test-first. Write the test, watch it fail for the cited raise or the old wording, then fix.
2. Each ruling cites a raise site at your reviewed commit. After the round, none of those `ValueError`s remain unless the ruling keeps it as an invariant (8-8, 8-12, C-6 unknown ranking flag); reword those without `_unpinned`.
3. Run every new string through `prose.issues` and `bare_figures`. Report any hit to LEAD; don't reword it.
4. Optional builder syncs (8-14, D-6 and others) are not yours; list them for LEAD.
5. Stage 2 notes (the `methods/<cp>.md` entries named in rulings 8-15, 8-16, C-4, C-5) are not written now; list them in the report.
6. Frozen literals stay as pinned. CP-8 `∅ G#` is for Stage 4.

## Rules
- No stub or fake value standing in for real behaviour.
- No catch-all that hides a failure.
- Never rewrite oracle payloads; a frozen-oracle disagreement is a strict xfail plus a live test of the ruled behaviour.
- Don't invent wording beyond the rulings; where none is pinned, fail closed and list it for LEAD.
- Files you may write: `src/deploy_workflow/owners/<cp>.py` and `tests/test_method_<cp>.py`.
- Tests: `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_<cp>.py` only.
- Gates on both files, exit 0: `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict`.
- Save probes as scripts in your scratchpad folder and report each one's exit code.

## Output
Return the report as text. It contains:
- the commit SHA;
- each ruling id, then its test name;
- the probes and their exit codes;
- the gates;
- prose and bare-figure hits;
- the Stage 2 notes;
- a `Not verified:` line;
- the ledger line `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=<y|n>`.
