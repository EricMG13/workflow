# Release review lane A (mx-adversary)

## Lane A review: product source (0d-d and W2-C), release tree at 5a6a746

**Verdict: APPROVE.** I found no High or Medium finding in the release diff. One Medium-class finding predates the release and goes to the owner. Two Lows and two Infos can ride with the fix batch.

All probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-A/probes/` (written `<P>/` below). The scratch trees beside it are `base` = 0daac2c^ (2258d47), `fix` = 0daac2c and `tip` = 5a6a746, all made with `git archive`. Nothing was changed in the release tree.

### 0d-d (first review): verified
- **Same issues as the old code.**
  - All 7 pinned digests (absence, source_context, validate_review, business_context, cp4_legal, cp3_relative_value, prefill with 120 seeds) match when run on the old code and also on the tip. So they really were pinned on the old code, and the tip reproduces them. Probe `<P>/a01_digests.py`: exit 0 on base, exit 0 on tip.
  - I added my own edge-case differential (1,500 readiness reviews and 800 source contexts), covering duplicate READY consumers, duplicate `affected_modules`, duplicate gap ids, duplicate source rows with different `published_on`/`event_ids`, and duplicate events. Output is byte-identical between base and 0daac2c (`<P>/a03_edge_outputs.py`, `cmp` exit 0).
  - By reading the code:
    - `_echoed` is the same check as the old pairwise rule.
    - `_retains` is the same as `set(range) <= pages` given first ≤ last.
    - The new `ready_rank` order plus the final `dict.fromkeys` keeps exactly the old first occurrences.
    - The `_Scopes` lookup matches `scope_matches_period` exactly.
    - The `_frozen` keys equal each other exactly when the values are `==` (`json_object` parses floats as Decimal and rejects NaN).
    - "Last row wins" for facilities is kept.
    - The cached `bound_rows`, `classes`, `entities` and facility rows hold values that no phase writes.
  - No refusal moved.
- **The timing bounds are real.**
  - Every one of the 18 cases is over its bound on base: 2.0–100x, e.g. shape 7.38 s against 0.5 s, prefill_books 11.3 s against 2.5 s.
  - Every case passes on the tip.
  - Both end-to-end tests fail on base (7.70 s and 8.13 s) and pass on the tip.
  - Probes: `<P>/a02_timing.py` (base exit 1, tip exit 0) and `<P>/a08_e2e.py` (base exit 1, tip exit 0).
- The reuse-manifest sha256 records match the tip for all 9 reused files, and the legal pin on `readiness.py` is at the tip sha.

### W2-C: verified
- **`is_blank`** adds exactly the round 13 addendum 3 set. The test of neighbouring code points shows the ranges are exact.
- **Blank citation quote:** refused after the source and locator checks and before the match. No frozen line used the old wording for a blank quote.
- **CP-DR `question_id`:** QUESTION_ID_MAX = 160 − 15 = 145. The tightness test passes, and probe `rr2` exits 0.
- **Unconditional RunText in CP-DR and CP-3D:** the tests would fail if the check were made conditional again. Probe `rr4` exits 0.
- **CP-3D `_parsed`:** same as the CP-2D and CP-1D versions.
- **G1-X guard:** the new test kills the `==` → `<=` mutant (`<P>/a06_g1x_mutant.sh`: clean=0, mutant=1, exit 0).
- **Shared `drive_cp1`:**
  - The cp3c and cp4 options match their old driver steps: business search, the narrative tool check and the readiness callback.
  - cp3c's old `cp2g_runs._quality_review` is identical to the new default `_credit_quality_review`.
- **Schema-driven fill:** it finds real paths. CP-0 gets `consumers.*.missing_source` and `sources.*.limitations.0`; CP-1 gets `sources.*.limitations.0` and `sources.*.scopes.*.limitations.0` (`<P>/a07_absent_paths.py`).
- **Verbatim sinks, the W3 question:** yes, a text check covers `sources.*.scopes.*.limitations.*`.
  - CP-1's own absence rule reaches it through `_prose_scopes` → `_prose(assessment)`, which walks into the scopes (`source_context.py:333, 374-398`). A scope limitation saying "pages 1-1 are missing" is refused.
  - The W3 note looked at `readiness._texts`, which is CP-0's list, not CP-1's.
  - Hostile run text lands in `ContextGap.description: Text`, not RunText, so it cannot raise. The verbatim entry is sound.

### Findings
**Medium-class, predates (owner): CP-DR composition raises on a long CP-0 gap id.**
- Where: `src/deploy_workflow/owners/cpdr.py:481` (`fact_id = f"{table}.{row}.{field}"`) for the TDR.1 rows. The gap-id checks at `cpdr.py:292-305` do not bound the length.
- What happens:
  - CP-0 accepts and builds a gap id of up to 153 characters (`T5.<gap>.gap` fits in 160).
  - CP-DR's `ENTRY_VALIDATOR` then passes a matching submission cleanly.
  - `compose` raises a `Fact` error on `TDR.1.<gap>.named_consumers` or `.description` when the gap id is 139–153 characters long.
  - This is the gap-id sibling of the `question_id` owner item that W2-C fixed, on the same post-write compose path.
- Probes:
  - `<P>/a04_cpdr_long_gap_id.py <n>`: n=138 exits 0; n=139, 145 and 153 exit 1.
  - `<P>/a09_cp0_long_gap_id_builds.py 145`: CP-0 validates and builds the 152-character T5 fact.

**Low (release): the F1 test does not measure the record it is named for.**
- Where: `tests/test_rule_issue_bounds.py:422`, `test_the_real_worst_case_record_bound_holds_for_escaped_characters`.
- It sizes only `json.dumps(ToolRules().issues(...))` and never a stored record.
- The stated bound does hold in practice: through a real submit, the stored record is 126,451 B, within WORST_CASE (160,384 B) and over LIMIT (64 KiB).
- Fix: assert on `_largest(fin._audit(...))` as the sibling tests do, or rename the test.
- Probes: `<P>/a10_f1_record_bound_static.py` (exit 1: no record access) and `<P>/a11_f1_real_record.py` (exit 0).

**Low (release, 0d-d): some timing margins are thin, so the tests may flake.**
- Measured on the tip while the controller's suites were running:
  - prefill_scopes: 2.3x under its bound;
  - scans: 2.6x;
  - prefill_periods: 2.8x.
- On the RED side, base is only 2.0–2.8x over the bound for scans, refs, prefill_scopes and prefill_periods.
- On a runner that is much faster or much slower, one side can flip: a revert slips through, or the test flakes.
- Probe: `<P>/a02_timing.py`.

**Low, predates (owner): CP-1 accepts blank limitations.**
- A scope or source limitation of `" "`, U+200B or U+2800 is accepted and rendered as a blank gap row.
- `source_context` never calls `is_blank`; `Text` only refuses `""`.
- Probe: `<P>/a05_cp1_scope_limitation_sink.py` (exit 1).

**Info:**
- The verbatim note at `tests/test_defect_classes_shared.py:114` says `missing_source` is "checked for prohibited text (`readiness.py`)". `readiness` has no prohibited-text check. The field goes through the absence-claim rule at `readiness.py:321`; the W3 notes repeat the same wording.
- The reflowed docstring at `src/deploy_workflow/owner_workflow.py:893` leaves "the" alone on its own line.

### Gate exit codes (run on the release tree)
| Gate | Scope | Result |
|---|---|---|
| `ruff check` | 28 lane files | exit 1, only the 5 known pre-existing findings: `cp4_legal.py:404` TRY004; `prose.py:114, :127` ISC004; `source_context.py:581, :583` ISC004. No new finding. |
| `ruff format --check` | 28 lane files | exit 0 |
| `mypy --strict` | 13 source files | exit 0 |
| pytest batch 1 | `test_readiness_linear`, `test_citation_blank_quote`, `test_engine_blank_text`, `test_rule_issue_bounds`, `test_owner_g1x` | 101 passed, exit 0 |
| pytest batch 2 | `test_owner_blank`, `test_connect_cpdr`, `test_method_cpdr`, `test_connect_cp3d`, `test_method_cp3d`, `test_defect_classes_selfcheck` | 1815 passed, exit 0 |
| pytest, CP-0 and CP-1 model-text fill | `test_defect_classes_cp1`, `test_defect_classes_shared`, `-k model_text` | 2 passed, exit 0 |
| `rr2`, `rr4` | named W2-C probes | exit 0 each |

Not verified: the full suite, the render suites and genuine `test_owner_<cp>` runs (the controller is running these); the slow real-store `drive_cp1` runs for s1a, cp3c and cp4; the gap-id finding end to end through a real CP-DR workflow (I showed only a clean validator result followed by a compose raise); CP-0's own behaviour for gap ids of 154–160 characters; how the report renderer treats `[` or `{` in CP-1 gap rows; jscpd; the timing bounds on any other machine or under CI parallelism.
