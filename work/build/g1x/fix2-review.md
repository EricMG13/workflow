**Verdict: APPROVE.** I found nothing at High, Medium or Low. With the mapping gone, no forged or hostile recorded payload I tried makes the verifier raise anything except `WorkflowError`. Every raw raise my probes hit came from either the test-only fake precheck or the out-of-scope lone-surrogate defect.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g1x-fix2-review/`. Run them from the target root with `PYTHONPATH="src:tests:<that dir>"`; `run_all.sh` in that folder runs all of them, and every one should exit 0.

**Check 1: can stored data make the verifier raise?**
- **Where the unions are** (`r01_discriminators.py`, exit 0): the only discriminated unions are in CP-1 `narrative` (5 unions, tag `kind`) and the fake `ViewedSubmission.parts`. `_CORES` and `_PRECHECKS` are empty in product.
- **Forged receipts** (`r02_forged_recorded.py`, exit 0): 354 forged, resealed receipts. That is 177 hostile texts on the CP-0, CP-3D sourced and CP-3D viewed submissions, each tried two ways: the recorded payload alone, and the recorded and stored payloads together. The texts cover:
  - non-str tags: list, dict, int, float, bool, null, nested, deep, empty, unknown, surrogate;
  - wrong JSON types at the union and around it;
  - nesting at depths 63, 64, 65, 200, 1000 and 100000, plus scanner edge cases (unbalanced brackets, brackets inside strings, escaped quotes);
  - lone surrogates in values, tags and keys, with and without null-fill;
  - NaN, Infinity, huge numbers and duplicate keys.

  Result: 348 answered `identity_mismatch`. The other 6 raised `RecursionError`, all from the test double (see Info 1).
- **Hostile payloads in genuine runs** (`r04_runtime_hostile.py`, exit 0): in 165 runs the model sent one hostile payload at one step, then each run was sealed and verified. Every one verified `accepted`. That covers 120 viewed, 14 sourced and 31 CP-0 steps journaled `invalid` and replayed through `_gate`, `_entry_outcome`, the validators and `_verify_invalid_step`.
- **CP-1 fill** (`r06_cp1_fill_fuzz.py`, exit 0): the fix-1 mapping also used to cover `financial_workflow._filled`. I fed 10,344 mutated payloads through `normalise` then `prefill`, with a `Known` built the way `known_bindings` builds it, over all five CP-1 steps (all 61 narrative paths). Nothing raised outside `ValueError`/`OSError`. `r06b_resolver_active.py` (exit 0) confirms the resolver actually ran, filling `scope-dimension` and `financial-review`.
- **Raw payload bytes** (`r08_forged_bytes.py`, exit 0): bytes of a UTF-8-encoded lone surrogate, invalid UTF-8, BOM, NUL, a raw control character, a CESU pair and overlong encodings all give `identity_mismatch`.
- **Pydantic and surrogates** (`r05_surrogate_semantics.py`, exit 0): `normalise` never raises on these inputs, and Pydantic refuses every lone surrogate.
- **Programming errors still propagate** (`r09_typeerror_site.py`, exit 0): a patched `normalise` `TypeError` reaches the caller through `_verify_submissions:1649` → `_fill:456`, with nothing relabelling it.

**Check 2: the new test fails for the right reason** (`r07_mapping_restored_reason.py`, exit 0; each mutant runs in a full temporary copy):
- K1: with `owner_workflow.py` exactly as at abdf53e (mapping restored), the earlier assertions pass. The test then fails at the final `pytest.raises(TypeError)` with `WorkflowError: identity_mismatch`, raised from the mapping at `owner_workflow.py:1656`.
- K2: with the 0d guard removed, it fails at its first assertion, `normalise(ViewedSubmission, raw) == (raw, ())`, with `unhashable type`. So it pins 0d.
- K3 (mapping moved inside `_fill`) and K4 (`TypeError` added to the outer catch) are also caught.
- The implementer's `mutants.py` exits 0: M0=0, M1=1, M2=0, M3=1, each as expected.

**Check 3:** the `serve_json_lines` catch at `owner_workflow.py:2041`, and the catch-all at :2043, both came in with e331a87 (G1 integration), before d36b5ab and 29c0819. They are the transport's sanitising catches and unrelated to this change.

**Check 4:** `_fill` is called in two places. Runtime `submit_review` at :899 was never mapped; the verifier at :1649 was the mapped call. The test uses at `tests/test_owner_g1x.py:665` and :770 call or wrap `_fill` directly. No other module imports it.

**Check 5:** the diff only removes code, rewrites the docstring and replaces a test. It adds no stub, fake value or catch-all. The new docstring at :1984-1988 is accurate.

**Info (none affects the verdict)**
1. **The test-only fake precheck can raise `RecursionError`.** `tests/test_owner_g1x.py:211-215` `_precheck` calls `json.loads` with no depth bound.
   - A payload nested 100000 deep makes it raise at runtime (`submit_review:904` → `_gate:488`, after the binding write) and in the verifier (`_verify_submissions:1668` → `_gate:488`).
   - Probes: `r03_recursion_origin.py` (exit 0) shows the frames and gets `identity_mismatch` once the fake precheck is unregistered; `r02` and `r04` tag these raises `[test-double _precheck]`.
   - No product precheck exists on this branch. But G1-X §4 hands each registered precheck the filled, forgeable payload, and the protocol names `owners.cp4.precheck`. Module tasks should parse through `json_object` or `too_deep`.
2. **Out-of-scope defect, hit by `r04`:** case `g1x_sourced src-surrogate`. A lone-surrogate `source_id` quoted by the evidence rule makes `submit_review:923` raise a Pydantic `ValidationError` (`StepValidation issues.1`) after the binding write. This is the known pre-existing defect that is with the user. Its forged equivalent in the verifier answers `identity_mismatch` (`r02`).
3. **Stale ruling note:** `docs/rulings/2026-10-28-stage1.md:856` still describes the mapping as tracked by LEAD. The implementer flagged it too; docs were outside their write scope.
4. **The old review's probes have changed exits, as expected:**
   - `g1x-review/p03_r44_forged_payload_typeerror.py` now exits 1. Parts 1 and 2 show no error and `identity_mismatch`. Part 3's assertion assumed the old runtime crash.
   - `p12_recursion_preexisting.py` exits 0 and now prints "no error".
5. **No test forges a payload any more:** the replaced test forged a recorded payload; the new one uses a genuine run. That case stays pinned indirectly through the `normalise` assertion and the genuine invalid replay, and `r02` exercises it directly.

**Gates** (run from the target root; all exit 0):
- `pytest -q -p no:cacheprovider tests/test_owner_g1x.py tests/test_schema_normalise_escapes.py`: 33 passed.
- `ruff check` on both touched files.
- `ruff format --check` on both touched files.
- `MYPYPATH=src mypy --strict src`: 111 files.
- The target worktree is clean at 857081c.

Not verified: no end-to-end CP-1 run, so neither a forged nor a hostile narrative replay went through `_entry_outcome` and `validate_cp1_stage` (function-level fuzz only, because a CP-1 promotion takes 11-26 minutes); the financials fuzz sampled 600 of 11,186 paths; CP-1A and CP-2 entry validators and probes on hostile stored payloads; forged snapshots (a forged rather than model-sent payload reaching the validators); real owner cores and prechecks on the module lanes; the deferred G1 (`tests/test_owner_workflow.py`) and S1a (`tests/test_owner_s1a.py`) suites; ruff across all of `src`; GitNexus `detect_changes`.
