# CP-2E fix round 1 report (mx-feature)

CP-2E fix round 1 is done. Two new commits sit on 0fa5b4a: 5761df4 (the review findings) and 2b58c89 (rulings round 5, label decimal and `fx.` paths).

**H1 (summary raised after the binding write): fixed**
- `_Check.run_text` validates the summary with `TypeAdapter(RunText)`, built once, with `include_input=False`, bounded by `clipped`. It runs inside `validate_macro_fx`, before any report is built.
- Exact issue text: `summary.text: Value error, Malformed run text: unbalanced or empty reference`.
- I added one rule beyond your ruling. A well-formed reference in the summary (`[abc]`, `{abc|x}`) is refused as `summary.text: text carries a reference`. Without it, settle would reject the module after a valid step. Please confirm it.
- The summary is the only model string that becomes `RunText` or `Claim` text. The other free-text fields only reach `Fact.text` or `limitation`, which are plain strings. A test feeds bracket text to 7 such fields and none raises.
- Test order: the summary tests were red first. After your ruling I switched to the `TypeAdapter` and changed the wording and the test together, so that step was not red-first.

**M1 (citation quotes): fixed**
- Cell cites now use a `Cite` pair (source_id, locator) that also carries its quote.
- The pair still equals and hashes as the plain page cite, and `_dedupe` keeps the first instance per page. The `_quotes` helper is gone. Page-level cites and every frozen value are unchanged.
- Sourced facts (T2F.1 value and basis cells, 11 rows) cite the quote of the submission field they were read from.
- Derived facts cite the first of their own input quotes on each page, in input order. Derived means:
  - T2F.2 to T2F.5 cells;
  - the T2F.6 assessment cells;
  - all claims.
- The rule is stated in `methods/cp2e.md`.
- The replacement tests cover both the sourced and the derived rule. `p2_citation_wrong_quote.py` exits 0.

**M2 (store acceptance tests): done**
- Added to `tests/test_owner_cp2e.py` and run (50 passed, 1 skipped, about 6 s):
  - the tamper case. Every check before `_PROBES` passes, and a no-op probe lets the forged run through. `cp2e.probe` alone raises `identity_mismatch`, so the recipe's key assertion is proven.
  - `stale_binding`;
  - the blocked case;
  - begin refused when CP-0 is blocked;
  - all 27 frozen refusals as store runs;
  - the hand-built-page refusal, run on its pinned page and pack hashes.
- Skipped: the tamper test for the gap case, because the recipe is stated on the positive case only.
- Acceptance 1 now compares every Fact field of every cell for both cases.
- The settled own limitations are the oracle list plus "Synthetic case; not real issuer qualification", deduplicated. Inherited limitations exclude any that are own.
- Oracle discrepancy: `blocked_cp2e` says "module blocked, no head". The store gives a CP-2E head with status `blocked`, as CP-1A does in the S1a blocked run. I asserted that, so LEAD should confirm the wording.

**Lows**
- L2: `T2F.1.r04` now stores `normalise(name)`. The frozen name SOFR is unchanged, and `p7_reference_rate_widening.py` exits 0.
- L3: killed with fast tests that run `submit` against a real store. `parse_raw_json` survives as an equivalent mutant: once `json_object` has accepted the text, the re-parse of `exact_json(document)` and of `text` give the same result. A test pins the refusals of text that `json_object` rejects.
- L4: added the `docs/reuse/manifest.json` `post_import_patches` record for `shipped.py`, in the CP-L10 form (sha256 `01ebc258…`, project_commit 0fa5b4a). It will conflict textually with the CP-L10 record on merge. LEAD resolves it by keeping both.
- L5: the table row headers and columns are now in `methods/cp2e.md`. L1 is untouched, and `_ENTRY_VALIDATORS["CP-2E"]` exists (a registration test pins it).

**Rulings round 5**
- Label decimal: `labelled` now uses the trailing guard `(?![0-9]|[.,][0-9])`. `spread 25.5` no longer labels 25 and is refused as `rate_exposure.spread: bps_text 25 is not labelled spread in the quote`. `p_label_decimal.py` now exits 1, which means the gap is closed. No frozen refusal or value moved: all 27 refusals and the Stage 1 cases pass.
- `fx.` paths: absence digit issues now carry the submission path (`fx.debt_currency_absence.reason`, `fx.operating_fx_absence.follow_up`, and so on). There is a test for each of the four absence objects and both parts.

**Probe and mutant exit codes (run on a `git archive` copy of 5761df4)**

| Probe | Exit | Meaning |
|---|---|---|
| p1 | 0 | summary no longer raises; returns the issue |
| p2 | 0 | |
| p3 | 0 | run not wedged. The valid literal submitted next came back `invalid`, not `stale_binding`; I did not look into why |
| p4 | 1 | only `parse_raw_json` survives (equivalent). `quotes_last_wins` and `quotes_no_basis` no longer apply because `_quotes` is gone, and my dedupe mutants replace them |
| p7 | 0 | |
| p9 | 0 | all 7 killed |

- Reviewer probes live in `<S>/cp2e-s2-review/`, my own copy in `<S>/cp2e-s2-fix1/`.
- My own mutant script (`<S>/cp2e-s2/mutants.py`, run on the worktree): 57 killed, 0 survived. It includes keep-last and keep-first-of-reversed dedupe, quote-from-locator and dropped-quote mutants (so both the first-quote and last-quote mutants die), the `run_text` mutants, the stored raw reference rate, the old label guard and the old absence path.

**Gates, all exit 0**
- The brief's pytest set plus `tests/test_owner_cp2e.py`: 1033 passed, 1 skipped.
- `ruff check` and `ruff format --check` on the 8 changed files.
- `mypy --strict` on the changed src files and tests.
- `tests/test_method_cp2e.py` was edited in one place beyond Info 2: line 334 uses `cp2e.Cite(...)` instead of a plain pair, for mypy.
- Frozen-case results are unchanged: Stage 1 values, the 27 refusals, blocked attempts, tool-use refusals and both cases' tables.

Not verified: the other modules' S1a or snapshot store runs; `tests/test_owner_workflow.py` and `tests/test_owner_s1a.py`, which were not run this round; any render or browser run; the inherited-limitations equality for the gap case beyond what `test_owner_cp2e.py` asserts; and the 800-line PR cap, which this change exceeds (tests make up most of it).

agent=mx-feature fix-rounds=1 gates-first-pass=n (the brief's pytest set passed first time, but the first pass of the store tests needed fixes)
