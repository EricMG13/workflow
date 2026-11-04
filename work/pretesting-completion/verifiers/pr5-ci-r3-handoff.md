# PR5 CI scheduling final-third handoff

Task: `PR5-CI-SCHEDULING-FINAL-R3`, starting commit
`5a8e02ef410ba4cba7057fa2d375c88603d37b2c`, findings CI-SCHED-P1/P2 only.

Implemented one heavy matrix child per exact selector heavy path (25 in current
order) with `fail-fast: false`. Each child verifies exact whole-line membership
and passes exactly its quoted matrix file to pytest. Fast sharding now captures
the `sort | awk` pipeline through checked command substitution, so producer
errors cannot be hidden by process substitution.

The focused tests extract and execute the actual named workflow shell blocks
under Bash. Doubles cover all 25 heavy children, exact and substring membership,
empty/unselected children, pytest statuses 0/5/13, selector failure, sort failure
with partial output, awk failure with partial output, eight fast shards, and
empty results. Unexpected mock `uv` commands fail closed.

Validation:

- Focused: `PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 /Users/ericguei/Documents/Deploy Workflow/.venv/bin/python -B -m pytest tests/test_prove_affected.py -q` — exit 0, 41 passed.
- Ruff check plus format check on `tests/test_prove_affected.py` — exit 0.
- No full test suite, heavy analytical bodies, GitHub Actions run, or provider
  call was performed.

Scope is the two workflow files, `tests/test_prove_affected.py`, and the three
lease-named records. Checkpoint-v low finding remains out of scope. This is the
final third correction; no further correction round is authorized.
