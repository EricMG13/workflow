# Task H1b: the five leased owner-only source rows (round 10 item 6), plus the H1 fix 2 riding Lows

This is Stage 2 (connections) work, so it is routed under AGENTS.md 423a06e:
- **Implementer:** `mx-feature`.
- **Reviewer:** `mx-adversary`. Source-capability gating is security-sensitive.

## Worktree
Work only in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/h1b` (branch `claude/h1b`), cut from the lane at ebc8294.
1. Before you edit, run `git -C <worktree> rev-parse HEAD`. It must equal `git -C <worktree> rev-parse claude/module-dev-status-review-0981b6`. If they differ, stop and report.
2. Use absolute paths, and run git from the worktree root.

## Inputs
| File | Section | Why |
|---|---|---|
| `docs/rulings/2026-10-28-stage1.md` | `# Round 10`, section 6 | The five rows and their scopes |
| `docs/CP1C-OWNER-LEASE.md` :31 | | CP-1C `peer_benchmark`: identity, financial, peers |
| `docs/CP2E-OWNER-LEASE.md` :40 | | CP-2E `macro_fx`: financial |
| `docs/CP2H-OWNER-LEASE.md` :36 | | CP-2H `rating_triggers`: identity, financial, ratings |
| `docs/CP4C-OWNER-LEASE.md` :46, :85 | | CP-4C `restructuring_fulcrum`: financial, legal-covenants |
| `docs/CP8-OWNER-LEASE.md` :35 | | CP-8 `decision_ledger`: prior_case, update, market_update |
| `cases/<cp>-owner/` | manifest and submissions | Check each source id against the module's cases |
| `src/deploy_workflow/host.py` | `_SOURCE_STEPS` (:50), `_OWNER_SCOPES`, `_held` | The code to change |
| `tests/test_host_h1.py` | the existing row tests | The pattern to follow |
| `work/build/h1/fix2-review.md` | L1, L2, L3 and their probes in `<S>/h1-fix2-review/` | The riding Lows |

## Build (test-first: write each test and watch it fail before the code)
1. **The five rows.** For each, add a `_SOURCE_STEPS` entry and an `_OWNER_SCOPES` `_held(...)` entry, with the scope exactly as its lease pins it, in pack order. Write one test per row: the scope is the leased sources in pack order, a held source that is not ready answers `unavailable`, and a source outside the scope answers `not_permitted`.
   - If a lease line disagrees with the module's cases on a source id, stop and report. Do not guess.
   - Update the `_SOURCE_STEPS` comment to list the owner-only modules.
2. **L1.** Add a test that pins `_submission_schema` before the tail checks. A producer with no schema source and a CP-1B-shaped two-input tail must answer `not_permitted`, not `identity_mismatch`. It must kill mutant R4 in `<S>/h1-fix2-review/mutate_review.py`.
3. **L2.** Add a test that pins the exact owner tail id, so that prefix and suffix variants are refused. It must kill R2 and R3.
4. **L3.** Add a CP-DR scope test with an `unreadable` held source. It must kill R1.
5. **Docstring.** Fix the stale `CPDR-OWNER-LEASE.md:31` reference in the test module docstring (D-B is now at :33).

## Rules
- **Files:** `src/deploy_workflow/host.py` and `tests/test_host_h1.py` only. Do not touch `owner_workflow.py`, leases, `cases/` or `src/deploy_vii`.
- No stub, fake value or catch-all. A fake core is allowed only in tests.
- **Gates (all exit 0):**
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_host_h1.py tests/test_owner_g1x.py`
  - `ruff check` and `ruff format --check` on both files
  - `MYPYPATH=src mypy --strict src`

  Use the binaries in `/Users/ericguei/Documents/Deploy Workflow/.venv/bin/`.
- **Mutants:** run them only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`. Show that each new row's removal and each riding mutant (R1–R4) is killed.
- **Commit** on `claude/h1b`. End the message with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Put probes under `<S>/h1b/`.

## Report (as text)
- the commit;
- each row with its lease line, its case-checked source ids and its test;
- L1–L3 and their tests;
- mutant exit codes;
- the gates;
- a `Not verified:` line (the deferred source-tools, source-workflow, G1 and S1a suites);
- the ledger line `agent=mx-feature fix-rounds=0 gates-first-pass=<y|n>`.
