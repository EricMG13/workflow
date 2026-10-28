# CP-4 Stage 2 review (mx-adversary)

**CP-4 Stage 2 adversarial review (claude/s2-cp4 @ 3efd33d vs lane 7a39384)**

**Verdict: REQUEST CHANGES.** I found no defect in the source. Two Medium test gaps reopen the work. The Q3/Q4 code is correct on a real store. But no test exercises CP-4's verifier probe, and the deferred suite leaves out most of the lease acceptance items that brief §7 requires.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4-s2-review/`. Each `pN_*.py` has its output beside it as `pN_*.out`.

**M1 (Medium, requirement gap): the deferred tests do not cover the lease acceptance items.**
- Brief §7 says to write a test for every acceptance item that needs a store run. `tests/test_owner_cp4.py` and `tests/cp4_runs.py` have none for:
  - **A3b:** the tamper test that builds the run with `semantic_issues` patched off, then expects the verifier to refuse at the gate replay.
  - **A4:** the `stale_binding` refusal, and "valid attempt 1 still yields a verifying receipt". The repair test stops at `repair_of`.
  - **A5:** all three tampers (edited `read_inputs` body, edited step output, edited `SettledHead`).
  - **Blocked case:** attempt 1 also fails, CP-4 settles blocked, and the receipt still verifies.
  - **A3:** the audit records (`payloads/`, `bindings/`, `submissions/`), and the `semantic_acceptance` values never settling.
  - **A1/A2:** CP-0 T3 authority, the T8 commands and CP-0 limitations; `python_values` and `source_context_only` at store level.
  - **A7 render:** fair to defer, since G2 is Stage 3, but it should be reported as blocked.
- Probe: `p5_deferred_coverage.py` exits 1 and lists all 12 as missing.
- `report2.md` admits only A4 stale and A5, while calling the work "done".

**M2 (Medium, test strength on the G1 verifier seam): `owners.cp4.probe` is never exercised.**
- My mutants R1 (probe is a no-op), R2 (rebuild with attempt number 0) and R3 (body replaced) all survive `test_connect_cp4.py` and `test_method_cp4.py` (`p4_mutants.py`).
- By reading, the deferred file only verifies honest runs, which a no-op probe also passes. So these mutants would survive Stage 5 too.
- The code itself is correct. On a genuine store (`p3_real_store_read_gate.py`, exit 0), `probe` passes on the real head. It refuses a forged step status, forged output bytes and a forged head module with `identity_mismatch`. A forged attempt number raises `ValueError`, which `verify_owner_run_receipt` maps to `identity_mismatch`.
- That probe takes about 90 s using `tests/test_source_tools.legal_history`. So a near-fast probe test is feasible now instead of waiting on the 11–26 minute promotions.

**L1 (Low): the narrow catch in `precheck` is not pinned.**
- Mutant P2 (`except ValidationError` widened to `except Exception`) survives.
- A real catch-all there would silently turn a crashing gate into "no issue".

**L2 (Low): CP-4 is not in any model-text class test.**
- `report.md` says the shared hostile-text set "does not apply to CP-4". Round 3 ruling 2 covers every registered module's positive payload, so it does.
- The behaviour already complies (`p2_model_text_class.py`, exit 0). Every free-text field × `"Rates matter [a lot"`, `"{low"` and `"{}"` (144 cases) journals `<path>: Malformed run text: unbalanced or empty reference`. None raises and none echoes the input.
- When the shared `tests/defect_classes.py` test lands, it must include CP-4. The ruling makes it due before this connection is claimed.

**L3 (Low, cost):** the `closed` fixture runs `promoted()` once per case (3) and the `promoted` fixture runs 2 more. That is 5 genuine CP-1 promotions, against the lease's 2 (the lease has the false-same case clone the gap head). `report2.md` says 2.

**Info (no action needed):**
- **Missing `_VIEWS` row (your check 1):** it now raises `not_permitted` instead of `KeyError`. The path cannot be reached:
  - `_check_steps` refuses such a spec at create.
  - The verifier only uses `OWNER_SPECS`, and both of its view steps have rows.
  - No receipt and no read counter changes. Only the unreachable transport code differs (`bad_arguments` before, `not_permitted` now).
- **Aliases:** `step_context` and `module_context` are interchangeable for any step with a `_VIEWS` row, as ruling Q4 says. Specs are fixed, so no caller can choose.
- **Stale text:**
  - the `owner_workflow.py:11-12` module docstring;
  - the `test_owner_s1a.py:1904` docstring (CP-4 now has a qualification);
  - protocol §3 "serves projection or module_context", which is LEAD's text.

**Checks that passed:**
1. **Q4.**
   - The literal is in both `StepSpec.inputs` and `step()`.
   - `_inputs` serves `_VIEWS[step](_owner_historical(...), attempt)`, and the verifier recomputes reads through it (`:1473`).
   - On a real store the body is byte-identical to `live.context.module_context(...,"legal_covenants")` and deterministic, with no `quote`, `citations` or `record_json` key.
   - `inputs="none"` gives `not_permitted`. A changed attempt number, another ticket (CP-1), another module's step (CP-2 `credit_synthesis`) and forged inputs each give `identity_mismatch` (p3).
   - My mutants I1–I5 and C1–C3 are all killed.
2. **Registrations.**
   - Every row is appended last.
   - `_ENTRY_VALIDATORS["CP-4"] is cp4_legal._validate_step`, with no adapter, and `_PRECHECKS["CP-4"] is cp4.precheck`.
   - `OWNER_SPECS["CP-4"]` equals the lease literal.
3. **`precheck` fail-through is safe.**
   - Five cases where the bounded `json_object` parse refuses (raw tab, newline or NUL; a BOM; a lone surrogate) are also rejected by pydantic (p1, no bypass).
   - The gate and `_validate_step` parse the same stored text with the same class, so shape errors are journaled as invalid issues (that is the record).
   - It catches `ValidationError` only, which is narrow and documented.
4. **Seams.** `view`, `probe` and `precheck` are positional, and `view` uses compact JSON with a sha256 digest. Mutants V1/V2 (`ensure_ascii`, `sort_keys`) are killed.
5. **Fast tests.** The adapter over `Module` objects has per-field sensitivity. `validate_bindings` returns `()`. `_spec_of` returns the row for the 6 blocks (`_COVENANT_REFINANCING` has exactly those 6). The D3 pin holds.
6. **Library boundary.** `git diff --stat` over `cases`, `src/deploy_vii`, `docs` and `methodology.json` is empty.
7. **Gates (re-run).**
   - pytest gate set: 366 passed, exit 0 (`gate_pytest.out`).
   - ruff check and `ruff format --check`: exit 0 (`gate_ruff.out`).
   - `mypy --strict` on the 5 files: exit 0 (`gate_mypy.out`).
8. **Mutants overall.** 13 of 17 killed; the 4 survivors are behind M2 and L1.

**Ledger:** fixer should add a fast `cp4.probe` tamper test (kills R1–R3), the deferred A3b, A4-stale, A4-repair-verify, A5 ×3 and blocked-case tests, and a non-`ValidationError` propagation test for `precheck` (kills P2). Re-run `p4_mutants.py` and `p5_deferred_coverage.py` and report their exit codes.

Not verified: no store run through `OwnerWorkflow` (`create` with CP-4, `read_inputs` via the transport, the precheck refusal audit, the verifier's gate replay end-to-end); I did not run `test_owner_cp4.py`, `test_owner_workflow.py` or `test_owner_s1a.py` (including the `:1899` CP-4 case); the deferred-suite survival of R1–R3 is by reading, not by run; I tested the five json_object/pydantic asymmetries in p1, not every possible one; A7 render; jscpd and complexipy were not run.
