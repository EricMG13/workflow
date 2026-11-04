## Confidence review — PR5-CI-SCHEDULING-CLASS-R2

Least confident about (ranked):
1. Heavy partition completeness — I compared the six named routes, all 25 unique list entries, tracked inventory, checkpoint matrix and exclusions. Result: all six exist and each shared list matches exactly.
2. Eight shard allocation — static set checks verified 216 fast files partition into eight pairwise-disjoint sorted slices with complete union. The shell implements `i=SHARD; i+=8`.
3. Selector failures and no-work handling — workflow command substitutions remain checked under `set -euo pipefail`; focused tests verify invalid refs exit 2, empty diff returns no files and no affected selections return empty output. The workflows preserve the pytest exit-5 deselection branch.
4. Matrix cancellation and diagnostics — PR-heavy concurrency now scopes at workflow level, preventing siblings cancelling each other; event/label conditions and timeout are retained. Fast and checkpoint suite invocations include `-v`, and durations stay 25.
5. Unintended CI changes — diff review confirms timeout, events, labels, permissions, action pins, setup, marker, fixture, assertion and promotion behavior unchanged.

Fixed: six genuine CP1 promotion suite routes, fast eight-way sharding, heavy per-file execution, concurrency scope, verbose fast diagnostics.
Verified fine: 28 focused scheduler tests pass; static inventory reports 241 files, 25 heavy, 216 fast; final collection passes at 17,071 nodes, five new scheduler test nodes over the protected 17,066 baseline.
Still open: CI workflow execution and the six heavy test bodies are deliberately outside this local schedule check.
