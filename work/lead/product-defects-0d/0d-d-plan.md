# 0d-d plan: make the work after the binding write linear, starting from `readiness._echoes_item_error`

**Root fix.** `_echoes_item_error` scanned every Pydantic error once per container error. Replacing that with one pass over each error's proper loc prefixes fixes it. The same class turned up at 12 more reachable sites: 13 in all, in 4 LEAD files, all under `src/deploy_vii`. Every fix gives byte-identical output, in the same order. Modules needs no change.

**How it was checked.** All the fixes were applied to a scratch copy of HEAD, `0d-d-plan/fix/`, built by `d90_make_fix_tree.py` (exit 0, 25 edits). There:
- every site's RED probe passes;
- every differential reports 0 mismatches against HEAD;
- the pinned cases do not move;
- `mypy --strict` on the 4 files exits 0.

**Versions.**
- LEAD: HEAD 32566e3, with pristine copies in `0d-d-plan/base/` and `0d-d-plan/fix/` (`git archive`).
- Every probe is in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-review-wip-worktrees-0145fe/d412fa37-e0cf-4abc-a174-1970a42cd5dc/scratchpad/0d-d-plan/`.
- Each probe takes a tree root as argv[1]. The differentials (d02, d08, d09) take `<base root> <fix root>`.

## 1. Root and class

### Root: confirmed

`readiness.py:90-113`:
- `shape_issues` calls `_echoes_item_error(item, errors)` for every error.
- Every `too_short` error with a "Tuple/List should have at least" message then runs `any(...)` over all errors.
- The cost is O(E·T), where E is the number of errors and T the number of container errors. In the reported shape T ≈ E/8, so the cost is O(E²).

Measured on HEAD (`d01_shape_issues_root.py`, exit 1):
- Direct call: 1.83 s at 38 KB, 7.48 s at 76 KB, 31.54 s at 152 KB.
- `FinancialWorkflow.submit_review` at source_context: 7.77 s at 76 KB.
- Both the submit (d12, N=4,000) and the step replay that verifiers repeat take 7.6–7.8 s at 68 KB.
- At MAX_LINE (4 MiB) this extrapolates to about 8 h per pass.

It is reachable from every step validator that parses a payload:
- `cp0_workflow:15`
- `cp1_workflow:128, :160, :414`
- `business_context:741, :1806`
- `cp2_synthesis:472, :915`
- the cp3–cp6 modules
- `live/submission:433, :446, :1258`

On the simulated fix the direct call takes 0.019 / 0.045 / 0.085 s, and the submit 0.10 / 0.18 s.

Note: Pydantic 2.14 emits the echoed container error only for tuples. The List branch is reachable only through synthetic errors (`d02` Part A).

### What counts as "after the binding write"

- **Financial workflow**: everything after the `_retain(bindings)` call at `financial_workflow.py:632`. That is `_filled` (normalise and prefill), `_evidence_issues` (ToolRules), `submit_model_payload` (normalise and prefill again, then the journal validator, plus `_validate_prefilled`, which runs prefill a third time), and the canonical parse.
- **Owner workflow**: the same functions at `:745-775`.
- **Verifiers**: every verifier replays these functions.

### Class inventory: reachable sites, all LEAD (`src/deploy_vii`)

| # | file:line | What grows | Complexity | HEAD measured | Reachable |
|---|---|---|---|---|---|
| S1 | readiness.py:90-113 | errors × container errors | O(E²) | see Root | every parsing validator |
| S2 | readiness.py:275-277 | `set(range(first, last+1))` per absence claim | O(the range the claim writes), independent of payload size | 3,066 B valid CP-0 payload with 8 claims "pages j-10000000 are missing": submit 8.56 s (d16). Direct: 0.25 s per 10⁷ pages (d03). 10¹⁰ pages would be a MemoryError (not run) | CP-0 `coverage_issues`; CP-1 `validate_source_context:329`; CP-1A `validate_business_context:763`; recomputed by `submit_cp0_review` and the verifiers |
| S3a | readiness.py:391-397 | every gap against every consumer | O(G·C·A) | 1.35 s at 2.6 MB (3,000×3,000, d06); 5.32 s at 6,000×6,000 (d20); end to end 0.51 s at 1.3 MB (d16) | CP-0 |
| S3b | readiness.py:385 | `in consumer.source_ids` per citation | O(K·S) | 0.22 s at 1.3 MB (d06); 2.41 s at 20,000 (d20) | stored-shape CP-0: financial :643, owner :762, source workflow :152. The compose path limits source_ids to the pack |
| S4a | source_context.py:287-289 | the event's citation set rebuilt per reference | O(R·C) | 1.09–1.36 s at 2.2 MB (d04); 3.58 s at 0.82 MiB (d14), about 83 s at 4 MiB extrapolated; end to end 3.15 s at 1.1 MB (d17) | CP-1 source_context; re-run by `validate_financial_context` (context_binding:48), later stage recomputes and verifiers |
| S4b | source_context.py:314-327 | `next()` and `any()` over `review.sources` and `event_ids`, per event and cited source | O(E·(S+R)), capped at S ≤ 2,000 and E ≤ 20,000 | 0.56–0.68 s at 3.7 MB (d04); 2.13 s at E=20,000 × S=2,000 (d20) | same as S4a |
| S5 | business_context.py:662, :678, :711 (`.count` per row) and :718 (`set(ids)` per row) | rows | O(n²) | 0.50 / 0.50 / 0.51 / 1.80 s at N=8,000 (d07); 2.1 / 2.1 / 2.1 / 6.9 s at 16,000 (d20) | owner CP-1A: `owner_workflow:765` → `submit_model_payload` → `submit_cp1a_step` → `_validate_step:1808`. Call chain read, not run end to end |
| S6a | live/submission.py:714-731 `_bound_entity` | all binding rows scanned per book | O(B·R) on the raw document (contract caps not applied yet) | 11.4–12.3 s at 1.3 MB, 16,000 books (d05/d20); financials submit end to end 11.96 s at 512 KB (d15) | prefill ×2–3 per submit, plus verifiers |
| S6b | submission.py:777-787 `_facility` | facility rows scanned per FX conversion | O(X·F) | 5.24 s at 1.2 MB (d05) | same |
| S6c | submission.py:787 | the matched row re-parsed per conversion | O(X·row bytes) | 4.65 s at 769 KB: 400 conversions, one row of 2,000 citations (d05) | same |
| S6d | submission.py:673-681, :728 `_dimensions` | `classes`, the entity scope list and the entity set rebuilt per book | O(B·S_ctx), S_ctx ≤ 2,000 per financial source | 5.14 s at 8,000 books (d20) | same |
| S6e | submission.py:575-596 `_period_scopes` | every entity scope scanned per period | O(P·S_ctx) | 0.90 s at 800 periods; 4.32 s at 4,000 (d20) | same |

### Checked and outside the class (no change)

**Capped by contract limits:**
- `source_context()` at :519-524 (entities × scopes) is capped at 2,000 × 4,000. At the caps it takes 0.38–0.43 s on HEAD (d04 "report").
- `context_binding.py:87-105` (evidence pairs × scopes) and `statement_output._cells:103-129` (3 × periods ≤ 200 × lines) are capped products. They are reached only once the financial review validates. Not measured.

**Linear:**
- `readiness.citation_issues:131` scans spans per citation. That is linear in payload × pack spans.
- `live/tools` ToolRules (0d-c c06/a08).
- `live/schema` normalise, `marked_fields` and `payload_document` (d11 profile, linear).
- `execution.submit_step`, `settle`, `bounded_issues` and `malformed_issues`.
- `cp2_synthesis.validate_credit_synthesis` (mappings and sets).
- downstream_readiness, narrative, quality and canonical_* were only statically triaged (d00, exit 0); their in-loop membership tests are on sets or dicts.

### Latent, same class (controller to rule; not in the task, no RED measured)

None of these is driven by a HEAD workflow. They are reachable only through `submit_model_payload` with a CP-3 or CP-4 ticket.
- **L1** `cp4_legal.py:596`: `seen.count(s)` per row.
- **L2** `cp3_relative_value.py:609`: `seen.count(f)` per row.
- **L3** `cp3_relative_value.py:637-645`: `not in instruments` (a list), `row.ordering.count`, and `not in row.ordering`, all per element.

The fix for each is the S5 pattern (`Counter`, plus a set built once).

### Modules-owned (`src/deploy_workflow`): no super-linear site

The verifiers call the same `deploy_vii` functions, so they inherit the fix. Two notes for Modules only:
- `financial_workflow.py:366-411` and `earnings_workflow.py:1127-1155` are linear in payload, but they scale with the number of pack lines, and each comparison re-normalises the label with `" ".join(label.split())`.
- The verifier call scans (`financial_workflow:969, :991, :1019`; earnings `_verify_transcripts:3328-3360`) are O(calls²), but the calls are bounded by MAX_CALLS.

### Owner notes, outside the class (found while probing)

- **O-a.** `absent_page_ranges` (`readiness.py:249-252`) calls `int()` on a page number of more than 4,300 digits, which raises ValueError (CPython's digit limit). A 5 KB CP-0 payload makes `FinancialWorkflow.submit_review` raise after the binding write, and the CP-0 step is left pending, so every resume raises again (`d18_page_digits_raise.py`). The 0d-b scope excludes raises in validators, so this goes to the owner.
- **O-b.** On the fix, the root shape at MAX_LINE still peaks at 3,329 MiB RSS. That is R1 (Pydantic error materialisation), which the owner already holds out of scope.

## 2. Fix (load-bearing code)

`d90_make_fix_tree.py` is the executable reference. It applies exact one-match replacements to HEAD. Write the docstrings in neutral words, without "HEAD".

### F1. readiness.py: replace `_echoes_item_error`

```python
    errors = error.errors(include_url=False, include_input=False, include_context=False)
    echoed = _echoed(errors)
    return tuple(
        f"{'.'.join(str(part) for part in item['loc']) or '(root)'}: {item['msg']}"
        for item in errors
        if not (_container_too_short(item) and item["loc"] in echoed)
    )

def _container_too_short(item: ErrorDetails) -> bool:
    return item["type"] == "too_short" and item["msg"].startswith(
        ("Tuple should have at least", "List should have at least"))

def _echoed(errors: list[ErrorDetails]) -> set[tuple[int | str, ...]]:
    containers = {item["loc"] for item in errors if _container_too_short(item)}
    if not containers:
        return set()
    return {item["loc"][:end] for item in errors for end in range(len(item["loc"]))
            if item["loc"][:end] in containers}
```

### F2. readiness.py `absence_issues`

Replace `pages = set(range(...)); if all(pages <= paged[item] ...)` with `if all(_retains(paged[item], first, last) for item in targets):`, using:

```python
def _retains(pages: set[int], first: int, last: int) -> bool:
    return last - first < len(pages) and all(page in pages for page in range(first, last + 1))
```

### F3. readiness.py `validate_review`

Before the consumer loop:

```python
ready_rank: dict[str, int] = {}
for position, consumer in enumerate(review.consumers):
    if consumer.readiness == "READY":
        ready_rank.setdefault(consumer.module_id, position)
```

At :385:

```python
attached = set(consumer.source_ids)
if any(citation.source_id not in attached ...)
```

At :395-397:

```python
omitted = sorted((m for m in dict.fromkeys(gap.affected_modules) if m in ready_rank),
                 key=ready_rank.__getitem__)
for module_id in omitted:
    issues.append(f"Consumer omits relevant gap: {module_id} {gap.gap_id}")
```

This is identical because the final `dict.fromkeys` keeps first occurrences. A module's first occurrence is its first READY consumer.

### F4. source_context.py `validate_source_context`

Before the source loop:

```python
event_sources = {key: {c.source_id for c in event.citations} for key, event in events.items()}
scanned = {(s.source_id, event_id) for s in review.sources for event_id in s.event_ids}
first_review: dict[str, SourceContext] = {}
for item in review.sources:
    first_review.setdefault(item.source_id, item)
```

Then:
- :288-289 becomes `if event_id in events and source.source_id not in event_sources[event_id]:`
- :315 becomes `source_review = first_review.get(source_id)`
- :323-325 becomes `if (source_id, event.event_id) not in scanned:`

### F5. business_context.py

- Add `from collections import Counter`.
- :662, :678 and :711 become `sorted(x for x, n in Counter(seen|judged|ids).items() if n > 1)`.
- At :718, build `known = set(ids)` before the loop and use `- known`.

### F6. live/submission.py `_Resolver`

1. Add `Hashable` to the `collections.abc` import.
2. Add `_Scopes`, a frozen dataclass with `ends: Mapping[date, frozenset[Dimensions]]` and `spans: Mapping[tuple[date, date], frozenset[Dimensions]]`. `_Scopes.of(scopes)` builds both maps by asking `scope_matches_period(scope, "PERIOD_END", start, end)` and `scope_matches_period(scope, "FY", start, end)` at the scope's own dates, skipping a scope with `end_date is None`. The rule stays the one rule.
3. `_period_scopes(period, scopes: _Scopes)` keeps its parse unchanged, then returns:
   - `scopes.ends.get(end, frozenset())` for PERIOD_END;
   - otherwise `scopes.spans.get((end, start), frozenset())`, or `frozenset()` when end or start is None.
4. Add `_frozen(value)`, which freezes JSON values to hashable keys that are equal exactly when the values are `==`. Lists, tuples and dicts are tagged and frozen recursively; scalars pass through.
5. New resolver members:
   - `cached_property bound_rows`: string book_id → list of entity_id values, in row order, or None when there is no row list;
   - `classes` and `entities` as cached properties;
   - `self.scopes[entity]`, holding `_Scopes`;
   - `self.facilities[id(book)]`: `{_frozen((facility_id, period_id)): row}`, where the last row wins;
   - `self.facility_hashes[id(row)]`.
6. `_bound_entity` uses `named = rows.get(book_id, [])`.
7. `_facility` looks the scope up in the index, and parses each matched row once.

All of this is exact because the binding rows and facility rows are not marked: no phase writes them before they are read. Full code: `0d-d-plan/fix_submission.diff`. The other three diffs are `fix_readiness.diff`, `fix_source_context.diff` and `fix_business_context.diff`.

## 3. Constraints (replay is exact; no pinned value moves)

Each differential runs HEAD against the fix:

| Probe | What it compares | Result |
|---|---|---|
| `d02_shape_issues_differential.py <base> <fix>` | Part A: 6,000 synthetic `from_exception_data` errors (Tuple/List/Value too_short, nested containers, a too_short inside a too_short, empty loc and (root), `"0"` vs 0, sibling prefixes, duplicates). Part B: 10,013 real errors from all STEPS schemas, the stored contracts, local tuple/list models, a root TypeAdapter and invalid JSON | 0 mismatches. 3,575 + 140 echoes dropped, covering all 4 kind × empty-loc cases. Exit 0. Mutant control (`mutant/`, prefix range +1): exit 1, 2,951 mismatches |
| `d03_absence_range.py` (3,000 seeds) | digest | f5a31f1460a63e9a on both trees |
| `d04_source_context_products.py` (300 seeds, 737 event-scan lines) | digest | a039f8b2c29ba2c3 on both |
| `d06_validate_review_products.py` (400 seeds, 122 omits-gap and 300 attachment lines) | digest | 73f05ff2bf97ebc3 on both |
| `d07_business_context_counts.py` | digest | 3eb2ca18a2e73b4b on both |
| `d08_prefill_differential.py <base> <fix>` | 300 seeds; every `Prefill` field (payload, paths, kinds, unbound, unset) | 0 mismatches; 239 seeds fill dimension strings, 141 fill facility hashes, 257 have unbound lines. Exit 0. Mutant control (`mutant2/`, first row wins): exit 1, 26 mismatches |
| `d09_pinned_cases_unchanged.py <base> <fix>` | all `cases/**/*.json`: 9,970 nodes, 139,932 outputs | 0 mismatches, exit 0. No pinned string uses any changed wording, except 4 pinned "should have at least" shape lines, which are unchanged |

The verifiers recompute through the same functions, so stored issues and their recomputation are unchanged.

## 4. Bounds for the lease (simulated fix)

| Path | Size | Per submit | Verify side |
|---|---|---|---|
| Root shape through FinancialWorkflow at source_context (d12) | 4,194,286 B | 10.44 s; RSS 3,329 MiB (R1) | step replay 4.15 s |
| Prefill worst case (22,250 books × 2,000 scopes), financials end to end (d15) | 4,163,368 B | 13.95 s | |
| Each site, one pass at about 4 MiB (d13) | ≈ 4 MiB | prefill: 1.78 / 2.38 / 1.13 / 2.66 / 1.85 s; validate_review gaps 0.11 s, attach 0.05 s, absence 0.49 s; source_context refs 0.70 s; cp1a 0.01 s | |
| Source workflow (1 MiB; measured through FinancialWorkflow at that size) | 1,088,012 B | 2.53 s; 923 MiB | replay 1.03 s |

**Verify.** The payload's extra verify cost is one replay of `_filled`, `_evidence_issues` and the step validator, so no more than one submit's time. The full genuine CP-1 verify takes 117–127 s at every N, including N=0 (d10). That is a pre-existing baseline unrelated to payload size, and it is why d10 runs past 60 s.

**Owner and earnings.** Both use the same functions at 4 MiB, but they were not run end to end.

## 5. Files and functions, by owner

**LEAD (one mx-feature):**
1. `src/deploy_vii/readiness.py`: `shape_issues`, `_container_too_short`, `_echoed` (replacing `_echoes_item_error`), `absence_issues`, `_retains`, `validate_review`.
2. `src/deploy_vii/source_context.py`: `validate_source_context`.
3. `src/deploy_vii/business_context.py`: `_source_issues`, `_consumer_issues`, `_shape_issues`.
4. `src/deploy_vii/live/submission.py`: `_Scopes`, `_period_scopes`, `_frozen`, and in `_Resolver`: `__init__`, `bound_rows`, `classes`, `entities`, `_dimensions`, `_bound_entity`, `_facility`.
5. `tests/test_readiness_linear.py` (new).
6. `docs/reuse/manifest.json`, in a separate docs commit after the code commit, as 0d-c did:
   - new `post_import_patches` entries for readiness.py (imported 1038a37a…) and source_context.py (imported bef10963…);
   - update entries 6 (submission) and 22 (business_context): sha256, project_commit, and a 0d-d reason.

**Modules:** none.

## 6. RED tests: `tests/test_readiness_linear.py`

`d20_red_tests_sim.py` holds the exact test bodies. On HEAD it exits 1 (all 15 cases FAIL); on the fix it exits 0. Import helpers with `fw = importlib.import_module("test_financial_workflow")`.

### Shared defect-class test

`test_post_binding_work_is_linear[case]` runs one timed call per case. The table gives the bound, then the HEAD time, then the fix time:

| case | bound | HEAD | fix |
|---|---|---|---|
| shape | 0.5 | 8.31 | 0.046 |
| absence | 0.1 | 0.90 | 0.000 |
| gaps | 1.5 | 5.32 | 0.048 |
| attach | 0.5 | 2.41 | 0.040 |
| refs | 2.0 | 5.28 | 0.22 |
| scans | 1.0 | 2.13 | 0.40 |
| cp1a_sources | 0.2 | 2.17 | 0.007 |
| cp1a_consumers | 0.2 | 2.12 | 0.003 |
| cp1a_conflicts | 0.2 | 2.11 | 0.008 |
| cp1a_translations | 0.2 | 6.93 | 0.011 |
| prefill_books | 2.5 | 12.30 | 0.52 |
| prefill_fx | 1.5 | 5.46 | 0.45 |
| prefill_fxrow | 1.0 | 4.85 | 0.13 |
| prefill_scopes | 2.0 | 5.14 | 0.92 |
| prefill_periods | 1.5 | 4.32 | 0.64 |

All times are in seconds. The HEAD figures come from three probe groups run in parallel.

### End-to-end REDs

- `test_invalid_context_submit_is_linear_end_to_end`: the a07 flow at N=4,000, bound 2.0 s. HEAD 7.77 s, fix 0.18 s.
- `test_absence_claim_submit_is_fast_end_to_end`: d16 "absence", bound 1.0 s. HEAD 8.56 s, fix 0.02 s.

### Guards (pass on HEAD)

- **G1** `test_shape_issues_equals_the_pairwise_reference`: HEAD's algorithm inlined as an oracle, over d02 Part A seeds and the crafted Part B payloads. Also exact literals:
  - `tuple[int,...]` min 2 with `'["a"]'` gives `("0: Input should be a valid integer, unable to parse string as an integer",)`;
  - `'[]'` gives `("(root): Tuple should have at least 2 items after validation, not 0",)`.
- **G2** `test_retains_is_set_inclusion` (hypothesis): fails on HEAD only by ImportError, so it is not counted as a RED.
- **G3** `test_validator_outputs_are_pinned[...]`: the d03/d04/d06/d07 generators, with sha256 digests computed on HEAD before editing. The 16-hex prefixes in §3 are cross-checks.
- **G4** `test_prefill_outputs_are_pinned`: the d08 generator over about 120 seeds, with the digest pinned on HEAD.

## 7. Probes for the reviewer, and task order

**Exit codes, base / fix:**

| Probe | Base | Fix |
|---|---|---|
| d01 | 1 | 0 |
| d03 | 1 | 0 |
| d04 | 1 | 0 |
| d05 | 1 | 0 |
| d06 | 1 | 0 |
| d07 | 1 | 0 |
| d16 | 1 | 0 |
| d17 | 1 | 0 |
| d20 | 1 | 0 |
| d02, d08, d09 (run as `<base> <fix>`) | 0 | |
| d13 | refuses on HEAD (exit 1; would take about 13 h) | 0 |
| d15 | 0 (512 KB) | 0 (4 MiB) |
| d12 | 0 (N=4,000) | 0 (MAX_LINE) |

- Measure-only probes: d00, d11, d14, d18 (exit 0 always).
- d10 is informational. It exits 1 on any tree, because the baseline verify takes more than 60 s.
- **Over the 60 s limit:** d10 (about 200 s per run), and one base run of d13 that I killed.

**Task order (one mx-feature):**
1. On HEAD, write `tests/test_readiness_linear.py` and pin the G3/G4 digests. Show RED with `d20_red_tests_sim.py <tree>`, which should exit 1.
2. F1–F3 in readiness.py.
3. F4 in source_context.py.
4. F5 in business_context.py.
5. F6 in live/submission.py.
6. Run `ruff check`, `ruff format --check` and `mypy --strict` on the 4 files. Note that `ruff check` already exits 1 on HEAD: ruff 0.17.1 reports ISC004 at source_context.py:578 and :580, which predates this task. Then run the probes on the implementation tree.
7. pytest on the new file and the affected tests, under the controller's build-first ruling: test_financial_workflow, test_owner_s1a, test_owner_workflow, test_source_workflow, test_rule_issue_bounds, test_engine_blank_text, test_earnings_workflow, test_source_tools, test_upstream_tools, test_schema_normalise_escapes, test_connected_render, test_earnings_render, test_cp1b_registration.
8. Code commit, then the manifest docs commit.

Not verified: no pytest run, and the test file was not written (only its bodies, simulated by d20). Owner workflow, earnings and CP-1A were not run end to end, and the full verify at MAX_LINE was not measured within 60 s. The capped products (context_binding:87-105, `statement_output._cells`) were not measured, and the downstream engines were only statically triaged. The latent cp3/cp4 sites were not measured. The Modules lane tip was not scanned (only HEAD's `src/deploy_workflow`). GitNexus is not indexed in this worktree. d09 found no parseable ReadinessReview, SourceContextReview or financials nodes in `cases/`, so validator-level identity rests on the seeded differentials. Peak memory was measured with ru_maxrss for the root shape only. I did not check whether the b10-engines fix round in flight touches these files.
