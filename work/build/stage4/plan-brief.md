# Stage 4 class-level plan (stage contract; Fable, plan only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). The code base is the integrated Stage 3 tip `c43b681`. Read files there with `git show c43b681:<path>`, or read the lane, which holds the Stage 2 release. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

You write one class-level plan and no code. `mx-feature` implements it, and `mx-adversary` attacks it.

## Inputs
| Item | File |
|---|---|
| Stage 4 scope | `L/docs/superpowers/plans/2026-10-28-verified-module-builds.md:144-163` |
| S1a adversary findings HIGH 1, MEDIUM 1, LOW 1 (RED tests included) | `/Users/ericguei/Documents/Deploy Workflow Sessions/s1a-build/work/s1a/review-adversary-4.md`; `L/docs/reviews/s1a-owner-run.md` |
| G1-X adversary review | `L/work/build/g1x/review-adversary.md` |
| Verifier | `L/src/deploy_workflow/owner_workflow.py` (`_verify_begins` :1007-1024, `_verify_attempts` :1427-1429, the :1632 exemption, `Execution.begin` in `execution.py`) |
| Per-module tamper / refusals / tool_use oracle sections | `L/cases/*-owner/expected.json` (search keys `tamper`, `refusals`, `tool_use`) |
| 0d product defect | `L/live/schema.py` `normalise`; LEAD branch `lead/0d-normalise` (read with `git show`) |
| CP-8 rails item | plan :162 |
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` item 17. Modules, acting for LEAD, accepts the 2026-10-28 deferral, so Stage 4 owns these items. |

## The plan must give
1. **The verification principle, applied per class.** The verifier replays the producer's rules on `before`, within the threat model's limits. State the threat model: what an attacker controls (receipt bytes, store files, publication directory) and what is out of scope.
2. **One section per hardening class:**
   - replay of `Execution.begin`, covering HIGH 1's six rules and MEDIUM 1's input binding (LOW 1 falls out);
   - the module `tamper`, `refusals` and `tool_use` oracle sections, grouped by shared mechanism, not by module;
   - the 0d `normalise` TypeError/RecursionError escape, and the later removal of G1-X's `_fill` mapping;
   - the refused-record known gap: say whether it is in scope and why;
   - the CP-8 rails binding to `T7.3.window.realized_value`.
3. **For each class:**
   - the files and functions to change;
   - the RED tests, named or taken from the adversary reports;
   - which existing tests or oracles must not move, and which may move under which ruling;
   - the attack cases `mx-adversary` must try.
4. **Order and batching.**
   - Batch into the fewest `mx-feature` dispatches that do not touch the same files at once (no per-module tasks).
   - Name the gates and the deferred genuine runs for each batch.
5. **Decisions for the user, kept separate:** any change to shared interfaces, to `src/deploy_vii`, or outside the plan.

Write the plan to `<S>/stage4/plan.md`, at most about 4k tokens. Return a summary of at most 600 tokens: its path, the batches, the user decisions, and a `Not verified:` line.

Rules: the plan requires no stub or fake value standing in for real behaviour, and no catch-all that hides a failure unless it is documented and logged.
