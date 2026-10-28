**Verdict: APPROVE.** Spec: pass. Quality: pass, with one Low and one Info.

**Spec verdict: pass.**
- `src/deploy_workflow/owner_workflow.py:595-598` matches ruling item 2 exactly: `type(raw) is not tuple or not all(type(i) is str for i in raw)` raises `WorkflowError("not_permitted")`. It sits where the old `sequence = tuple(getattr(core, "STEP_IDS", ()))` line was. An empty tuple gets past it and is still refused by the existing nonempty check at :602.
- `src/deploy_workflow/owner_workflow.py:614` adds ruling item 1 verbatim to the owner-only `served` conjunction. Refusal still goes through the existing frame at :619-628.
- Nothing else in `_check_steps` changed apart from the docstring (:563-566).
- The diff is 71 insertions and 4 deletions in the two named files, so it is under the ceiling.
- Reading `host._OWNER_SCOPES` as a module attribute is safe:
  - `owner_workflow` already imported `deploy_workflow.host` (`from deploy_workflow.host import SourceSession`, :95), and host imports owner_workflow only lazily, inside functions (host.py:604, :803). So the import at :70 adds no cycle.
  - The value is looked up on each call, so there is no stale copy, and a monkeypatch on the module is seen.
- The fixture restores the scope table:
  - `monkeypatch.setattr(host, "_OWNER_SCOPES", …)` (tests/test_owner_g1x.py:349) is undone when each test ends.
  - The per-case patches run inside `pytest.MonkeyPatch.context()` (:472).
  - In the gate session `test_host_h1.py:346`, which asserts the exact set of scope rows, passed after the g1x tests ran.
- Every registered module still passes. CP-0, CP-1, CP-1A and CP-2 pass `_check_steps`. CP-MODEL is refused by `_check_steps`, but it is deterministic and `_check_specs` skips it at :657-663 (`continue`), so the call is never made for it.
- Scope rows (H1/H1b): `host.py:88-113` has a row for each of the 8 owner-only sourced steps (CP-1D, CP-3D, CP-DR, CP-1C, CP-2E, CP-2H, CP-4C, CP-8). Each matches its `_SOURCE_STEPS` entry. None of those cores is registered at 3d25683, so for now each row has no spec using it.
- Leases: no lease gives sources to a step that `_OWNER_SCOPES` lacks. CP-2A, CP-2D, CP-2G, CP-3C and CP-L10 are `sources=False` or submit-only. CP-3, CP-4, CP-5 and CP-1B are live chains. CP-OS has no spec. Each Stage 2 sourced owner-only step will need its own row.

**Quality findings**

- **Low:** tests/test_owner_g1x.py:542-546. The case labelled "scope row without sources" actually tests the same direction as the first case: it sets `viewed.sources=True` when VIEWED has no row. No test covers a row being present while the step has `sources=False`.
  - Input: change the clause at owner_workflow.py:614 from `==` to `<=`, so it only checks that sources imply a row. Then add a `(MODULE, VIEWED)` row with the spec unchanged.
  - Wrong output: create is accepted, and all 24 tests in test_owner_g1x.py still pass on this mutant.
  - The shipped `==` code is correct; only the test is missing. Probe: `<S>/s2-g1x-review/p_one_direction.sh` exits 0 while the gap exists. It should exit 1 once a test patches in a `(MODULE, VIEWED)` row and expects refusal.
- **Info:** the new docstring lines at owner_workflow.py:563, :565 and :566 are 109, 125 and 131 characters long, against `line-length = 100`. E501 is not selected, so ruff does not flag them.

**Exit codes** (in an archive copy of 3d25683, with PYTHONDONTWRITEBYTECODE=1)
- Gate pytest (4 files): 0, 236 passed. Output is in `<S>/s2-g1x-review/gate.txt`.
- Ruff and mypy on the changed files:
  - `ruff check` (both files): 0
  - `ruff format --check` (both files): 0
  - `MYPYPATH=src mypy --strict owner_workflow.py`: 0
- Ruff on the whole repo: `ruff check` exits 1 (287 errors) and `ruff format --check` exits 1 (33 files). This is outside the diff; the two changed files are clean. I did not compare against the 6e51653 base.
- `<S>/s2-g1x-review/mutants.sh` re-runs `s2-g1x/mutate.py` on fresh archive copies, and both mutants are killed (scopes: pytest rc 1; tuple: pytest rc 1). The script exits 0.
- `<S>/s2-g1x-review/p_registered.py` exits 1. The 1 comes only from CP-MODEL, which create never sends to `_check_steps`. It also confirms there is no sourced owner step without a row.

All probes are saved under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s2-g1x-review/`.

Not verified: the full pytest suite. Whether whole-repo ruff fails the same way at base. Any real Stage 1 owner core with these guards: none is registered on this branch, so the 8 scope rows were checked against specs only by reading the leases. The "a row is present, sources False" refusal is correct by reading the code; no test or probe runs it against the shipped code.