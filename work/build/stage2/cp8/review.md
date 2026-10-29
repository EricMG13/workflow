# CP-8 Stage 2 review (mx-adversary)

**CP-8 Stage 2 review (8fab26b on 43d4e78): REQUEST CHANGES.** There are two Medium findings. Both are in the deferred test layer and the reader's limitations claim. The core, the adapter and the registrations hold.

I re-ran the gates myself. The gate set gives 1224 passed, exit 0. ruff check, ruff format --check and mypy --strict on the 7 changed `.py` files all exit 0. The three render suites that build with `SHIPPED_MAPS` give 202 passed (`p5_shipped_blast_radius.sh`, exit 0).

Probe directory: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-s2-review/`

## Medium

**M1. The real head's "own" limitations include the synthetic line, so the deferred test will fail.** Probe `p2_synth_own_limitations.py`, exit 1.
- **Where:** `tests/test_owner_cp8.py:35` asserts `module.limitations == own_limitations`.
- **Why it fails:** the run is `case_kind: synthetic`. The product's `settle` (`execution.py:474-479`) adds `"Synthetic case; not real issuer qualification"` to the module's own limitations.
- **Probe result:** I ran `settle` directly, with no store. It gives 7 own limitations against the oracle's 6, and 3 inherited against the oracle's 4.
- **Effect:**
  - The deferred test will fail at Stage 5.
  - `cp8_reader.limitations` will return the synthetic line on every real head. Its docstring says "CP-8's own, not the inherited set", and the oracle files that line under inherited.
- **Why the fast test passes:** `_head_module` builds a head by hand with exactly `own_limitations` and no inherited set. My mutant R1 (`(*module.limitations, *module.inherited_limitations)`) survives because of this.
- **Predates:** the oracle convention that own limitations exclude the synthetic line holds in every `cases/*/expected.json`. That part is for the owner. The new test and the reader claim are this change's.
- **Fix:** LEAD rules which side is right. Then either the reader and test strip the run-level line, or the test compares against own plus that line. Pin it with a head built by `settle`.

**M2. The deferred store tests leave out lease acceptance items 3, 5 (run level) and 6.** Probe `p4_review_mutants.py`, exit 1 (S1 and S2 survive).
- **Why they are due now:** `test_method_cp8.py:5-6` hands the G1-level, blocked and refused cases, tamper and store runs to Stages 2-4. Brief §7 says to write the store runs now.
- **What `tests/test_owner_cp8.py` has:** only the closed run, receipt plus probe, and D3.
- **What it is missing:**
  - **Acceptance 3, no_record.** CP-0 says DO NOT RUN, there is one `RefusedBegin` with the NotAuthorized text, and no attempt or head.
  - **Acceptance 5 at run level:**
    - the journaled tuple `issues` = validator issues + `RULES` issues, through `submit`/`_with_rules`, with r42 pinned twice and not de-duplicated;
    - t01-t03;
    - blocked (attempt 0 r23, then attempt 1 r03);
    - `not_permitted` and `stale_binding`.
  - **Acceptance 6, tamper.** The lease recipe, ending in `probe` raising `identity_mismatch`.
- **`submit` is never tested:** no test at any stage, as written, exercises it. Two mutants survive:
  - S1: always wrapping the rules, which de-duplicates r42;
  - S2: skipping the trusted re-validation.
- **Answer to your question:** yes, the lease requires no_record now (acceptance 3 and the Refusals section). It needs a driver variant and a test, not core code: `execution.begin` raises `NotAuthorized` (`:259-266`).

## Low (ride with the fix)

**L1. Test-strength gaps.** Same probe, `p4_review_mutants.py`. These mutants survive:
- **R2:** `_count` returns 0 for a missing amount. The never-0 invariant is not pinned.
- **R3:** the overall-attribution guard is removed.
- **R4:** `status` is made a constant.
- **U1/U2:** `RULES` counts an absence on a required decision or thesis field. The core does match the oracle's `absence_paths`, but nothing pins it.
- **B1/B2:** the blank check moves ahead of the scope or pack check. The ordering is unpinned.
- **P1:** `NOT_AN_OBJECT` becomes `()`. The new deviation has no test at all.

## Info

- The report names commit da84f8d; the review target is 8fab26b.
- "18 quote sites" are 18 kinds of site. The positive literal has 25 concrete sites, which gives 200 blank tests.
- The `cp8_upstream` docstring says the reader uses it. It does not.
- `NOT_AN_OBJECT` also fires for objects that `json_object` rejects (NaN or Infinity, a lone surrogate, too deep, a 200k-digit int). It fails closed, but the wording is imprecise.
- The report does not give a status for the hostile-text row (Q5). The set has not landed in `tests/defect_classes.py`.
- The T7.2 binding label "Thesis register" differs from the table title "Thesis and expectation register". Labels are not pinned.

## Checks that pass

1. **Adapter.**
   - On both cases it gives exactly the Stage 1 `Upstream`.
   - A missing CP-0 raises.
   - A CP-6 that is bound but unsettled raises (`settled_call`). My fail-open mutant A2 is killed.
   - With CP-6 absent the value is None, the missing cell.
   - In Stage 2, CP-6 cannot be bound. It is unregistered, so `_check_specs` refuses create, and both edges are `block` (`p6_cp6_reachability.py`, exit 0).
2. **Reader and D3.**
   - The reader exposes the 8 items in `expected.consumption`. A missing cell reads None.
   - D3 is recorded OPEN, and no test claims consumption.
3. **Registrations.**
   - Rows are appended only.
   - The spec equals the lease, and `_check_steps` passes, including the `_OWNER_SCOPES` row.
   - There is no `_VIEWS` or `_PRECHECKS` row.
   - `SHIPPED_MAPS` ends with CP8.
   - The bindings equal lease D7 and `expected.render.rails`.
   - `what-changed` keeps `collapsed=False`.
4. **Deviations.**
   - **`LedgerOutput`:** admissible. CP-2 uses the same pattern, the keyword names match, and the `LedgerReport` dataclass cannot be retained as step output. Record it as lease text for LEAD.
   - **`NOT_AN_OBJECT`:** a new constant that protocol §6 forces. No frozen refusal moves (r00 unchanged). LEAD should accept the wording.
   - **`json_object` then `exact_json`:** on 74 literals (plus duplicate-key, escaped and pretty variants) it gives the same model and the same tail digest as the raw parse (`p3_parse_and_digest.py`, exit 0). Neither `RULES` nor `_validate_step` raises on the hostile set.
5. **Blank-quote fix.**
   - It covers all 7 `_cite` call sites, which make up the 18 site kinds (`p1_quote_sites.py`).
   - The position meets addendum 3 ("before the page-occurrence check"). CP-4C checks blank first, but the ruling does not fix the order against scope.
   - The wording is `<path of the blank text>: empty text`, which matches CP-4C.
6. **methods/cp8.md.**
   - The notes match the code (`p7_methods_note_claims.py`, exit 0).
   - The 28 rows are verbatim. Against the draft, only the header changes and a section is appended.
7. **Library boundary:** clean (`p8_boundary.sh`, exit 0).
8. **Mutants:** 19 of mine, 8 killed and 11 survivors (listed above).

Not verified: no store run, deferred test, tamper, receipt or render run was executed (Stage 5 policy). M1 rests on calling `settle` directly, not on a real run. `validate_ledger` and `decision_ledger` were not fuzzed for raises on valid but odd payloads (that is Stage 1 code). The `docs/reuse/manifest.json` sha values were not checked.
