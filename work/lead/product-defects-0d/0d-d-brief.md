# 0d-d brief: make the work after the binding write linear (owner-approved "fix at root", LEAD lane; held for the Stage 2 close release)

Worktree: `/Users/ericguei/Documents/Deploy Workflow Sessions/lead-0d-d`, branch `lead/0d-d`, cut from LEAD `2258d471d9f7a7e09f2cc6d8a5380ab970659bfb`. Work only here.

**First step:** run `git rev-parse HEAD`. If it is not that sha, stop and report BLOCKED.

## Inputs
| Layer | File | Section | Why |
|---|---|---|---|
| L4 | `work/lead/product-defects-0d/0d-d-plan.md` | §1 class inventory and "Latent", §2 F1-F6, §3 constraints, §5 files, §6 RED tests, §7 probes and task order | The plan you execute. |
| L4 | `src/deploy_vii/readiness.py`, `source_context.py`, `business_context.py`, `live/submission.py`, `cp4_legal.py`, `cp3_relative_value.py` | as the plan cites | The code to change. |
| L4 | `docs/reuse/manifest.json` | `files`, `post_import_patches` | Entry shape for the patch records. |

Plan scratch: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-review-wip-worktrees-0145fe/d412fa37-e0cf-4abc-a174-1970a42cd5dc/scratchpad/0d-d-plan/`. It holds the probes (d01-d20), the four `fix_*.diff` references, `d90_make_fix_tree.py` (the executable reference), and `d20_red_tests_sim.py` (the exact test bodies). Each probe takes the tree root as argv[1]; d02, d08 and d09 take `<base root> <fix root>`, with the base being `0d-d-plan/base/`. Run with `"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -E -s <probe> <args>`. `-E` ignores `PYTHONPATH`, so any runner script you write puts this worktree's `src` and `tests` on `sys.path` itself.

**Base drift (checked by LEAD).** The plan's line numbers are against 32566e3. Since then, the only changes to these files are the b10 one-line edits: `business_context.py` `_blank` and `_populated` (:576-581), `cp3_relative_value.py:688` and `cp4_legal.py:649`. None of them overlaps a site, and line counts are unchanged. `fix_business_context.diff` also carries the b10 `_blank`/`_populated` hunk, which is already at this HEAD, so skip that hunk.

## Scope (LEAD rulings on the plan)
- **S1-S6e (13 sites), exactly as F1-F6.**
- **Latent L1-L3 are in scope.** They become live when CP-3 and CP-4 connect in Stage 2. Use the S5 pattern (`Counter`, and a set built once) at `cp4_legal.py:596`, `cp3_relative_value.py:609` and `cp3_relative_value.py:637-645`. Keep the issue text and order byte-identical. Each one gets:
  - a case in `test_post_binding_work_is_linear`, calling the validator directly at a size where HEAD exceeds the bound you set (measure HEAD first, and report the HEAD time and the fix time);
  - a digest guard pinned on HEAD before editing, as G3.
- **Out of scope:**
  - plan owner note O-a (the page-number `int()` raise). It waits for an owner decision; do not touch it.
  - O-b, and the Modules notes.

## Process (plan §7 task order, as amended here)
1. **RED, on unedited HEAD.**
   - Write `tests/test_readiness_linear.py` from `d20_red_tests_sim.py`'s bodies, plus the L1-L3 cases.
   - Pin the G3 and G4 digests, and the L1-L3 digest guards, by running HEAD's code.
   - Call every RED directly from a script, each run in under 60 s. Show that each fails on the unedited source for its stated cause (timing over the bound, not an error).
   - Run `d20_red_tests_sim.py` on this worktree: it should exit 1.
   - G2 fails on HEAD only by ImportError, and does not count as a RED.
2. **Edits.** F1-F3 in readiness.py; F4 in source_context.py; F5 in business_context.py; F6 in live/submission.py; then L1-L3. Write docstrings in neutral words, with no "HEAD". F6 is financial prefill: keep the "last row wins" facility rule and the row order exactly as the plan states.
3. **GREEN.**
   - Call every test in the new file directly.
   - Run d01, d03, d04, d05, d06, d07, d16, d17 and d20 on this worktree.
   - Run d02, d08 and d09 as `<0d-d-plan/base> <this worktree>`.
   - Report each exit code against plan §7's "Fix" column.
   - Do not run d10 or d13 here; they are over 60 s.
4. **Gates,** with the venv binaries directly, on the six source files and the new test:
   - `"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/ruff" check`
   - `ruff format --check`
   - `mypy --strict`

   `ruff check` already exits 1 on HEAD: ISC004 at source_context.py:578 and :580, and TRY004 in cp4_legal. Report the finding list before and after. Add no new finding, and do not fix the old ones.
5. **Pins (report only).** Run `python3 -I cases/pins.py --check` and report its exit code. Then list every `cases/**` pin of `business_context.py` and `cp4_legal.py` that no longer matches. Known pins are in the cp3c, cp4c and cp4-owner builders and manifests, `cp3c-owner/expected.json`, and `snapshot/builder/build_s1_oracle.py`. Do not edit `cases/`: the re-pin is LEAD's Stage 2 close release task.
6. **Records.** In `docs/reuse/manifest.json` `post_import_patches`:
   - add entries for readiness.py (imported `1038a37a…`) and source_context.py (imported `bef10963…`);
   - update the existing entries for submission.py, business_context.py, cp4_legal.py and cp3_relative_value.py.

   Each entry gets:
   - `imported_sha256`, from its `files` entry or the prior patch entry;
   - `sha256`, the final hash;
   - `project_commit`: "lead/0d-d (uncommitted)";
   - a one-line `reason` covering 0d-d;
   - `review`: "work/lead/product-defects-0d/".

   Keep the existing entry shape.

## Rules
- Write only the files named above, plus your report.
- No stub or fake value standing in for real behaviour. No catch-all that hides a failure, and no new `except`.
- Run no pytest, no `uv run`, `uv sync` or `uvx`, and no `git stash`. Do not commit.
- Save no per-round copies of source or tests; the commit holds them.
- Nothing in `src/deploy_workflow`, `cases/` or other tests changes. If the plan turns out to need such a change, stop and report BLOCKED.
- Every probe and direct test run takes at most 60 s.

## Outputs
`work/lead/product-defects-0d/0d-d-report.md`. It covers:
- the RED and GREEN evidence, with each case's HEAD and fix times;
- every probe's exit code;
- the gate exit codes, with the ruff finding lists before and after;
- the `pins --check` exit code and the list of moved pins;
- the final sha256 of each changed file;
- the deferred pytest command for LEAD's final phase (the new file plus the affected tests listed in plan §7 step 7, plus whichever cp3/cp4 tests exercise L1-L3);
- a final `Not verified:` line listing what no gate or test exercised.
