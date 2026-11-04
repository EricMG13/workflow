# PR5 CI scheduling class R2 handoff

The selector marks six additional genuine CP1 promotion suites heavy and both checkpoint schedules consume the same list. PR fast uses eight sorted file shards; PR heavy runs each selected affected file separately and keeps sibling jobs from cancelling one another. `-v` exposes active-node diagnostics; durations remain 25.

Focused scheduler tests pass 28/28 (exit 0), including direct routes for all six additions, empty/unaffected behavior, invalid refs, shard allocation and workflow structure. Final collection with `PYTHONPATH=tests` passes (17,071 nodes; five added test nodes against the protected 17,066 baseline); the protected prior inventory was 17,066, so the three new tests are additive. The independent static probe verified 241 test files, 25 unique existing heavy files, 216 fast files, matching checkpoint lists, six direct heavy routes, eight pairwise-disjoint shard slices whose union equals fast, timeout/event/label/concurrency/action/setup/marker invariants. `git diff --check` passed. No heavy test bodies, provider calls, workflow executions or promotion tests ran.

The initial collection without `PYTHONPATH=tests` failed (exit 2; 16,154 collected, three import errors) because research test imports require that path; the corrected collection succeeds.
