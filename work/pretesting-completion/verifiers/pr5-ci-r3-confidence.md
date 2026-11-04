# Confidence review — PR5 CI scheduling (CI-SCHED-P1/P2)

## Least confident about (ranked)

1. **Heavy children could still execute more than one test file, or run a file
   selected only by a substring.**
   investigated → The job matrix is taken in exact order from the selector's
   `HEAVY` tuple. Each child gets one `TEST_FILE`; its exact line is checked with
   `grep -Fx`, then pytest receives only the quoted variable. An actual-shell
   test ran every one of the 25 children against a selector containing all 25
   paths and asserted one invocation with exactly one file. Separate cases
   covered a prefix, suffix, unselected child, and empty selection.
   verdict → fine (confirmed with actual workflow shell and mocked `uv`/pytest)
   patch → n/a

2. **A membership-tool error could be mistaken for an ordinary non-match.**
   investigated → With `set -e`, a pipeline inside an `if` is exempt from the
   implicit exit. The workflow now examines the pipeline status: only grep's
   status 1 is treated as an unselected matrix child; other failures exit with
   their status. A mock grep returning 2 confirms pytest is not called and the
   shell exits 2.
   verdict → confirmed risk, corrected at the status branch
   patch → propagated membership pipeline failures

3. **Fast shard allocation could hide a failed producer or allocate partial
   output.**
   investigated → `files=$(printf ... | sort | awk ...)` runs in the parent
   shell under `set -euo pipefail`. Actual workflow-shell controls made sort
   emit a partial path then return 23, and awk emit a partial path then return
   41; both statuses escaped before pytest. The selector's status 2 likewise
   escaped. Eight shard runs over a reversed 18-file input matched the expected
   sorted allocation, covered the union once, and had pairwise-disjoint inputs.
   Empty selection and an empty shard skipped pytest successfully.
   verdict → fine (failure propagation and shard partition exercised)
   patch → n/a

4. **Pytest's special no-tests status could break prior intended behavior.**
   investigated → Actual heavy workflow-shell runs returned success for pytest
   statuses 0 and 5 and propagated 13. Fast invocation arguments remain the
   original `uv run --frozen pytest -v ... -m "not live" --durations=25` path.
   verdict → fine for heavy status handling; the fast workflow's unchanged
   pytest status branch was outside this correction
   patch → n/a

5. **Existing scheduling controls or the matrix's relation to the selector
   might have drifted.**
   investigated → The probe compares all matrix entries to the imported
   selector `HEAVY` tuple and verifies `fail-fast: false`, `TEST_FILE` matrix
   binding, and workflow concurrency. The focused suite also checks the
   existing event, label, timeout, selector, and marker setup.
   verdict → fine (static invariants and focused tests)
   patch → n/a

## Fixed

- CI-SCHED-P1: one independently budgeted heavy job per each selected heavy
  matrix path, fail-fast disabled, exact one-file invocation.
- CI-SCHED-P2: checked fast shard pipeline, with sort and awk failures
  propagating before pytest.
- Added actual-workflow-shell probes for the scheduling and error boundaries.

## Verified fine

- Checkpoint membership and the source `HEAVY` list were left untouched; the
  new workflow matrix equals the current 25-item selector list.
- Workflow-level concurrency, timeout, events, labels, checkout/setup, pytest
  markers, and durations remain present.
- Test doubles reject any unexpected `uv` command, so these probes cannot
  accidentally run dependency installation or real pytest.

## By-design

- A matrix child that is not in the selected heavy-file set exits without
  running pytest; an empty selection and empty shard also exit successfully.
- Pytest status 5 remains a successful all-deselected result, matching the
  prior workflow contract.

## Still open

- GitHub Actions did not execute this workflow; platform scheduling behavior
  was checked through the authored YAML invariants and the actual extracted
  shell with local doubles.
- Heavy analytical test bodies, accepted CI execution, and heavy timing were
  not exercised under this lease.
