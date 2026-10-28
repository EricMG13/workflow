# G1-X fix round 2: remove the `_fill` TypeError mapping (LEAD 0d integrated)

Implementer: a fresh Opus agent. Review afterwards: a scoped mx-adversary review.

## Background
G1-X fix 1 (controller ruling, `fix1-brief.md`) mapped a `TypeError` from `_fill` on a recorded payload to `identity_mismatch` at a single call site: `owner_workflow.py` near :1651, with the docstring near :1995. That was a stand-in until LEAD fixed the root cause in `deploy_vii/live/schema.py`. LEAD has now integrated 0d (31aeee0, merged as 144659f):
- a non-str discriminator tag is treated as "not determined";
- `schema.too_deep` (MAX_NESTING 64) bounds `json_object`, `tools._document` and `submission.compose_payload` before `json.loads`;
- `normalise` leaves a payload with a lone surrogate unchanged, so Pydantic refuses it as `invalid`.

## Step 0
1. `EnterWorktree(path="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/g1x-fill")`. Branch `claude/g1x-fill`, cut from the lane.
2. `git cherry-pick 31aeee0`. This brings LEAD's 0d fix and `tests/test_schema_normalise_escapes.py`. Never edit what it brings.

## Fix (test-first)
1. Write the test first. A recorded payload whose discriminator tag is not a str makes the verifier report `invalid` (the 0d behaviour); nothing raises, and the mapping is not reached. Watch the test fail with the mapping in place: the result today is `identity_mismatch`.
2. Remove the `except TypeError` mapping and its comment.
3. Correct the `verify_owner_run_receipt` docstring so it no longer names that mapped call. Leave the catch at about :2050 unchanged unless it existed only for this case; if you think it did, report that and don't change it.
4. Confirm by reading the code that no other `_fill` call site relies on the mapping.

Not in scope: the lone-surrogate defect. A lone surrogate quoted by an evidence rule's `source_id` or `locator` still crashes `submit_review` after the binding write. It predates 0d and is with the user. Don't build around it.

## Rules
- Files you may write: `src/deploy_workflow/owner_workflow.py` and `tests/test_owner_g1x.py`. Don't edit `src/deploy_vii` beyond the cherry-pick, the owner cores or the cases.
- No stub, fake value or catch-all.
- Tests: run only `tests/test_owner_g1x.py` and `tests/test_schema_normalise_escapes.py`, if it runs in under 60 s. Leave the G1 (`tests/test_owner_workflow.py`) and S1a (`tests/test_owner_s1a.py`) suites deferred and list them.
- Gates on the touched files: `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict src`. Use `/Users/ericguei/Documents/Deploy Workflow/.venv/bin/`.
- Run mutants only from a full temporary copy. Show that restoring the mapping, and dropping the new test's assertion, are each caught.
- Probes go under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g1x-fix2/`.

## Report (as text)
- the commits;
- the test name, and the red you saw;
- each mutant's exit code;
- the gates;
- a `Not verified:` line, which lists the deferred suites;
- the ledger line `agent=general-purpose(opus) fix-rounds=2 gates-first-pass=<y|n>`.
