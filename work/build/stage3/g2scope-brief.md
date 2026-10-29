# Stage 3 G2 delivery-scope table, preparer (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). Worktree `../s3-g2scope`, branch `claude/s3-g2scope`, cut at release ab9777f. Python: `L/.venv/bin/python`.

You are the **preparer** of a lease amendment. You edit `docs/OWNER-RENDERING-LEASE.md` only. A separate mx-precise reviewer approves it, and a different agent builds G2. You never edit `src/`, `tests/` or `cases/`.

## Inputs
| Item | File |
|---|---|
| G2 lease (rev 1, frozen) | `docs/OWNER-RENDERING-LEASE.md` (rulings :124-181, banner texts :146-154, rev 1 M1-M3, L1-L4) |
| Rulings for this task | `L/docs/rulings/2026-10-29-stage3.md` item 2 |
| Module scope rows | every `docs/*-OWNER-LEASE.md` (search `DeliveryScope`, `DELIVERY_SCOPES`, `delivery scope`, `G2`): at least CP-1C :48, CP-1D :43, CP-2A :149, CP-2D :127/Rendered sections, CP-2E :78, CP-2G :160, CP-2H :48/:123, CP-3C :193, CP-3D :92, CP-DR :183, CP-L10 :68; check CP-1B, CP-3/CP-6, CP-4, CP-4C, CP-5, CP-8 and any other lease too |
| Each module's run fixtures and render oracle | `tests/<cp>_runs.py`; the render section of `cases/<cp>-owner/expected.json` |
| Q-C1, Q-C2 | `L/work/build/stage3/questions.md` |
| Pathway modules | `src/deploy_vii/contracts.py` (`_PRESETS`, `PATHWAY_MODULES`), `src/deploy_vii/report_view.py` (`_Spec` rows) |

## Process
1. Add a section "## Rev 2 amendments (Modules, 2026-10-29) — override the body and rulings" to the G2 lease, after rev 1.
2. In it, one table row per module run that has an owner oracle, keyed by `scope_id`: `pathway`, the exact `requested_modules` tuple of the run (from `tests/<cp>_runs.py` or the oracle's run, never from the lease alone), `case_kind`, `sections` (block ids, pathway order), `rails`, supported outcomes, the banner literal per supported outcome, the oracle path and JSON pointer that each scope's acceptance asserts against, and the run fixture function.
3. Where a lease's scope row disagrees with the module's frozen oracle, its `_Spec` rows or Q-C1/Q-C2, the oracle and rulings win; list each disagreement and the choice. Where a module has no scope row in its lease (for example CP-DR "none per Q1"), say whether it gets one and why.
4. Scope matching: G2 binds `(pathway, requested_modules, case_kind)` (rulings Q1(b), L2). Show that no two rows share that triple; where two runs share it (positive and gap of one module), they share one scope with both outcomes, or the outcome set says how the gap run is handled.
5. Banner texts: draft one per supported outcome, in the style of the rev 0 texts (`:146-154`): say what the scope covers and that the rest remains unqualified. No numbers.
6. List the acceptance tests G2 needs per scope (the rev 1 test list applies to `cp1-model` and `s1a-credit-snapshot`; say what each new scope adds: the five-field block check against its oracle, rails, limitations, refusals).
7. One commit ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates
- Every row's `requested_modules` and sections cross-checked against the code and oracle you cite (give file:line).
- `git diff --stat` touches only `docs/OWNER-RENDERING-LEASE.md`.

## Outputs (report as text, at most about 1.5k tokens)
- Tip SHA; row count; each disagreement and choice; questions; `Not verified:` line.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged.
