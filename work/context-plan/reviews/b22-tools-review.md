# B22 review: `line:N` locators in `src/deploy_vii/live/tools.py` (O2 Task 7)

Range 63a5bbb8..ad4a14a3: code f0cf47c6, D12 record ad4a14a3. Brief: `.superpowers/sdd/2026-10-31-part-b-o2/task-7-brief.md` (gitignored).

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-tool-use-m365-copilot-research-8ff28f/9d206924-1225-454b-b5b4-bbf09f856c4e/scratchpad/`, under `o2t7-adversary/` and `o2t7-review/`. Exit 0 means the property held.

## mx-adversary (a3bbdf4f): approve

- **Page packs unchanged** (`probe_page_packs.py`, 0). BASE and HEAD `tools.py` were run side by side on page, mixed and both-kind sources, with `line:` arguments on a page source. Outputs, recorded evidence and `seen_tables` were byte-identical. The only spec change is the one the brief requires (`extract_statements`), and recording digests hash messages only.
- **Injection** (`probe_injection.py`, 0). 33 malformed requests were refused, and each recorded nothing.
- **Coverage** (`probe_coverage.py`, `probe_e2e_oracle.py`, 0). A wrong `line:K`, a range key, or a same-label row in another unit is left uncovered. Missing, superset or split units are refused. `citation_issues` refuses a range key as a locator.
- **Recorded reads** (`probe_seen.py`, 0). Owner cores still use the page-only check. `earnings_workflow` stays fail-closed on line sources.
- **cp4 slowness predates this change** (`probe_cp4_timing.sh`). HEAD took 94.5 s and 5.57 GB, against 91.6 s and 5.37 GB with BASE `tools.py` and `financial_workflow.py`. The time goes to CP-1 re-verification in `host.py`.
- **D12 record** (`probe_d12.py`, 0): `prior_project_sha256` f03f7d04, `sha256` 40414baa, `project_commit` f0cf47c6.
- **L1.** Two adjacent heading lines make an empty unit that can never be measured, so the step fails closed (`probe_unit_bounds.py`, 1). This is ruled below.
- **I1.** The extracted-coverage floor (`_cell_coverage`, tools.py:919-924) checks only `page:N`. Nothing in the repo reaches it, so it goes on the owner list.

## mx-precise (a925883e): spec pass, quality fix (Lows only)

The stand-in done-when test is an honest unit test of `_evidence_issues` over the real extraction, and it is two-sided. The Lows:
- untested boundaries: exactly 200 lines, 8 ranges, and a valid range followed by a failing range recording nothing;
- mixed-source kind detection unpinned (unreachable today);
- unit text untested;
- an unused `blocker()` and a stale docstring;
- the `extract_statements` docstring not updated, and an overlong `seen_tables` docstring line.

`mutants.py` exits 1 with 8 survivors, 2 of them equivalent.

## Controller rulings

- **L1:** a heading line followed directly by another heading line starts one unit with it, and the unit runs to the line before the next non-adjacent heading. Cost if wrong: two titled tables measured as one.
- The Lows go to one fix dispatch.
- I1 goes on the owner list beside B22's deferred citation check (task-7-brief R1).
