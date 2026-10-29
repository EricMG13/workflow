# Stage 2 close release review (stage contract)

This is one review phase for the whole close release. It is also 0d-d's first review (user, 2026-10-28: "Include, one review"). Three Opus reviewers (`mx-adversary`) run in parallel, read-only, one per lane below. One fix batch follows; it takes the High and Medium findings plus the Lows.

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. `R` = `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-release` (read-only), the branch `claude/s2-release` at the tip named in the dispatch. The base is lane f1544a3, so the release diff is `git diff f1544a3..<tip>`.

## Inputs
| Item | File | Why |
|---|---|---|
| Plan | `L/work/build/stage2/release-plan.md`, `L/work/build/stage2/close-release.md` | what the release must do |
| Reports | `L/work/build/stage2/release/w1-report.md`, `w2-{a1,a2,b,c,d}-report.md`, `w3-report.md`, `w3-notes.md` | builders' claims to verify |
| Rulings | `docs/rulings/2026-10-28-stage2.md` rounds 1-5 (items 1-22), `L/work/build/stage2/questions.md` | settled; do not re-raise |
| Known | `L/work/build/stage2/lows.md` (owner items), `L/work/build/stage2-backlog.md` | already recorded; do not re-raise |
| 0d-d | `R/work/lead/product-defects-0d/0d-d-{brief,plan,report}.md`, the 0d-d commit 0daac2c | 0d-d's own contract |
| Spec | `AGENTS.md`, `docs/G1X-OWNER-CORE-PROTOCOL.md`, `docs/<CP>-OWNER-LEASE.md`, `docs/CP1-CHART-SLICE.md` | the spec |

## Lanes
- **A, product source: 0d-d and W2-C.**
  - 0d-d: the linear readiness and prefill paths (`readiness.py`, `live/submission.py`, `source_context.py`, `business_context.py`, `cp3_relative_value.py`, `cp4_legal.py`). Check that each linear rewrite gives the same issues as the old code (the pinned digests), that the timing bounds are real, and that no refusal moved.
  - W2-C: `prose.is_blank`, the `citation_issues` blank quote, the CP-DR `question_id` bound (145 against the 160 cap), the CP-DR and CP-3D unconditional RunText check, the CP-3D `json_object` path, the G1-X guard test, the shared `drive_cp1`, and the schema-driven free-text fill. Also check the three verbatim sinks C declared (W3 notes): does any text check cover `sources.*.scopes.*.limitations.*` before it renders as a gap row?
- **B, oracle re-pins: W1, W2-A1, W2-A2 and the W3 chain.**
  - Every `cases/` change in the release diff must trace to a named close-release item or a pure re-pin. Flag any value that moved without one.
  - The removed deltas (`CP2D_D7_DELTA`, `CP3C_D7_DELTA`, `PERIOD_DELTA`, `GAP_VALUE_CLASS_DELTA`, `PRINCIPAL_PERIOD_DELTA`, `GAP_CURRENCY`, `CP1A_BOUND`, `STAGE2_REFUSAL_DELTA`, the CP-2G blocked xfail and the CP-4C v08 pin): each replacing test must fail if the oracle reverts.
  - The CP-2D drawings precedence (round 5 item 4, wording item 21).
  - Whether CP-2D `T2E.5.r05` and `r06` should carry a currency.
  - The D12 manifest records (round 5 item 19).
  - Double-rebuild determinism (rerun one rebuild if it takes under 2 minutes).
- **C, citations and text: W2-D and W2-B.**
  - The round 3 citation rule in CP-2H, CP-1C, CP-2G and CP-4C (round 5 item 17), and the hoisted `_one_per_page` helper.
  - The CP-4C v08 `unread_issues` reading against close-release "limitations equal the issues".
  - The six view trees and their pins.
  - The lease, protocol and TOOL-CONTRACT text against the code at the tip (spot-check at least 10 file:line cites).
  - `MODULES.csv`.

## Process
For each change in your lane, check four things:
1. it matches its item and ruling;
2. its test would fail on the defect or revert it names (reason through at least two per lane, or run one if under 2 minutes);
3. no frozen value moved outside a named item;
4. no stub, fake value or catch-all that hides a failure (unless documented and logged).

Also:
- Re-run the lane's quick gates.
- Write a probe for each finding, save it under `<S>/release-review-<lane>/`, and name it in the finding.
- Do not edit anything.

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

## Outputs (report as text, at most about 2k tokens)
- A verdict for the lane (APPROVE or REQUEST CHANGES).
- Findings by severity, each with file:line, the failure scenario and its probe. Mark predating findings "predates".
- Gate exit codes.
- `Not verified:`.
