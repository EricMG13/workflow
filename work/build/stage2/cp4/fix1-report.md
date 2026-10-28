# CP-4 fix round 1 report (mx-feature)

CP-4 fix round 1: all of M1, M2, L1-L3 and the Info items are addressed. Commit d92ce29 is on top of 3efd33d in /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-cp4 (branch claude/s2-cp4). The fast gates and the reviewer's p2, p4 and p5 probes all exit 0. The new store-run tests are written and type-checked but have never run (Stage 5).

**What changed**
- **M2, probe tamper test:** `tests/test_probe_cp4.py` is new and its own file, because it takes about 80 s on `test_source_tools.legal_history`.
  - The honest head passes.
  - A forged step status, forged output bytes and a forged head module each raise `identity_mismatch`.
  - Forged attempt numbers 0 and 2 are refused.
  - The fixture settles CP-4 on a repaired attempt 1: a first attempt with an unresolved figure is rejected, then the repair settles. A probe that rebuilds with attempt number 0 cannot pass this fixture, which is what kills R2.
- **M1, deferred suite** (`tests/test_owner_cp4.py` and `tests/cp4_runs.py`):
  - Driver: `fail_attempt` fails one CP-4 attempt on the read rule. `settle` takes a promoted state to the sealed receipt. `cp4_closed` takes an optional `template`.
  - A3b: the false-same run is built with `cp4.semantic_issues` patched off and settles valid. With the gate back on, the verifier refuses it with `identity_mismatch`, and the store is unchanged.
  - A4: `stale_binding` after an interrupt. Also an unread page that is invalid then repaired as attempt 1, with a verifying receipt.
  - Blocked case: attempt 1 also fails, CP-4 settles blocked, and the receipt verifies.
  - A5, three tampers each on its own: an edited `read_inputs` body (resealed consistently, so only the view replay can refuse it), an edited step blob, and an edited `SettledHead` (status, then result hash).
  - A3 audit records: the raw and filled payloads, the binding and the submission files under `owner-run-audit/`.
  - `semantic_acceptance` values (headroom 3, share 0.75, the verdict, calculable Yes) never settle in the corrected module.
  - A1/A2 at store level: CP-0 T3 authority, T8 fields, CP-0 limitations and status, `python_values`, and `source_context_only`.
  - A7: reported as a skipped test, "blocked on G2 (Stage 3)".
- **L1:** a test makes the schema parse raise `RuntimeError` inside `precheck` and expects it to propagate. My first version built its input inside the patched region, so it passed against the catch-all mutant too. The fixed version kills P2.
- **L2:** `test_hostile_model_text_is_journaled_and_never_raises` runs the 144 cases from the reviewer's probe.
  - Nothing raises, nothing is accepted unjournaled, and the input is never echoed.
  - The prose fields (rationale, flag, implication, mechanic) journal `Malformed run text`.
  - The reviewer's claim that every free-text field journals that exact message was too strong. Quote fields journal a citation mismatch, and fields like `threshold_text` journal other rules. All 144 still journal something.
  - The controller can switch it to the shared `tests/defect_classes.py` helpers when they merge.
- **L3:** the `promoted` fixture holds two templates (positive and gap), and every run is a fork of one. The false-same case forks the gap template. That is 2 genuine CP-1 promotions instead of 5.
- **Info:** the `owner_workflow.py:11-12` docstring now names CP-4 and `step_context`. The `test_owner_s1a.py:1904` docstring now says CP-4 has a qualification.

**Test-first:** the M2, L1 and L2 tests pass on the unchanged source, because the reviewer found no source defect. The mutants stand in as their failure evidence, since they all survived the earlier suite.

**Exit codes**
- `p5_deferred_coverage.py`: 0, no item missing.
- `p2_model_text_class.py`: 0 (144 journaled, 0 accepted, 0 raised).
- `p4_mutants.py`: exit 0, 17 of 17 killed, no survivors. I ran it as an extended copy, `<S>/cp4-s2/p4_extended.py` (log `p4_extended.log`), which also runs `tests/test_probe_cp4.py`.
  - The original script runs only the two fast files, so R1-R3 survive there. They are killed only through the new probe file, because it runs over 60 s and has to be its own file.
  - P2 is also killed in the fast files alone, by a P2-only run.
- `<S>/cp4-s2/mutants.py`: exit 0, 37 of 37 killed.
- Fast gate pytest over connect, method, g1x, host_h1 and selfcheck: 368 passed.
- `ruff check`, `ruff format --check` and `mypy --strict` on the changed files: clean.

**Deferred commands** (for `work/build/deferred-runs.md`; `PY` is the repo venv python)
```
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PY -o faulthandler_timeout=1800 -m pytest -q -p no:cacheprovider tests/test_owner_cp4.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PY -m pytest -q -p no:cacheprovider tests/test_probe_cp4.py   # about 80 s
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PY -m pytest -q -p no:cacheprovider tests/test_owner_workflow.py tests/test_owner_s1a.py
```

Not verified:
- Nothing in `test_owner_cp4.py` or the store functions of `cp4_runs.py` has run. `p5` and `--collect-only` (38 tests collected) are static only.
- Assumptions in those unrun tests that could fail at Stage 5:
  - The false-same fork of the gap template matches the gap pack's hash.
  - `clone_workflow` works at the CP-4-begun state.
  - `Head.status` strings and the T8 field texts match the oracle.
  - The `"cp1_status":"restricted"` substring in the CP-4 read body.
  - The seal and audit layout used by the A5 consistent forge.
  - A second `fail_attempt` after a repair re-reads cleanly.
  - `write_receipt` works after a blocked CP-4.
- `test_owner_workflow.py` and `test_owner_s1a.py` were not run, and the A7 render is blocked on G2.
- jscpd and complexipy were not run. `drive_cp1` in `cp4_runs.py` still duplicates the one in `s1a_runs.py`.

agent=mx-feature fix-rounds=1 gates-first-pass=y
