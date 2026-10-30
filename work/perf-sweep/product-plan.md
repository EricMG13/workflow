# Product-change plan

Status: **approved by the user in the sweep session (2026-10-30: "Yes, apply P1–P3").**
P2 and P3 edit `src/deploy_vii`; P1 edits
`src/deploy_workflow/earnings_workflow.py`, a module-lane file. Nothing here changes a hash, a byte output, an error or a public API.

Evidence: `work/perf-sweep/profiles/prof3.out` (E-NO-YOY, 2bbf633, 1727 s profiled / 1277 s
plain) and the scratch micro-trial `work/perf-sweep/probes/micro_trial.py` on a real settled
CP-1 Module blob (43,868,524 bytes, 44,044 facts, 27 tables; sha 7278c637…; copied from an
earnings owner store of a Stage 5 test run). Micro-trial ran at load average ≈ 11 on 10 cores,
min of 3; the ratios are the evidence, the absolute seconds are loaded-machine figures.

| Micro-trial (one call on the CP-1 blob) | min s | max s |
|---|---|---|
| `Module.model_validate_json(raw)` | 0.692 | 0.784 |
| `module.content_hash()` | 0.169 | 0.187 |
| `validate_tables` (current) | 0.212 | 0.227 |
| `validate_tables` (P2 grouped) | 0.032 | 0.036 |

## P1 — hash the CP-1 producer once per `_operands` call

- Where: `src/deploy_workflow/earnings_workflow.py:1685` `_reference(producer, fact)` computes
  `producer.content_hash()` for every operand and companion; `_operands` (:1696) calls it
  1,440 times over 10 calls in E-NO-YOY: 237.3 s profiled.
- Change: in `_operands`, compute `producer_sha256 = producer.content_hash()` once and pass it
  to `_reference` (signature `_reference(producer_sha256: str, fact: Fact)`; its only callers are
  inside `_operands`, lines 1704 and 1725).
- Same output: `producer` is one `Module` object bound for the whole `_operands` call and never
  rebound; `Module` is `frozen=True` (`contracts.py:76`), its fields are tuples of frozen
  contracts, `str`, `date`, `Decimal`; no `object.__setattr__` or `__dict__` write exists in
  `src/` (grep). So every one of the 1,440 calls returns the same string.
- Expected saving: ≈ 1,430 × 0.17 s ≈ 240 s per fresh earnings settle (E-NO-YOY and
  E-QOQ-FLAT each; also every fixture/test that reaches `_operands` via `submit_review`).
- Guard: unit test counting `Module.content_hash` calls during one `_operands` call
  (≤ 1 on the producer), written first against current code (fails: 1,440-style count).
- Risk 1 (leaf function, pure). Confidence 2 (profile + micro-trial per-call cost).

## P2 — group canonical fact ids by table once in `validate_tables`

- Where: `src/deploy_vii/contracts.py:290`, inside the per-table loop:
  `{fact.fact_id for fact in facts if fact.table_id == table.table_id}` rescans every fact for
  every table (O(tables × facts)). 144.2 s self time over 5,281 calls in E-NO-YOY; it runs on
  every `Module` (`distinct_records`, :311) and `ModuleView` (`output_identity`, :343)
  construction, including each `model_validate_json`.
- Change: before the table loop, build `ids_by_table: dict[str, set[str]]` in one pass over
  `facts`; compare with `ids_by_table.get(table.table_id, set())`. Exact candidate text:
  `validate_tables_grouped` in `work/perf-sweep/probes/micro_trial.py`.
- Same output: the new pass raises nothing; every check runs in the same order with the same
  messages. Micro-trial compared current vs. grouped on the real tables and 8 failure inputs
  (drop/extra/duplicate fact, duplicate table, duplicate row, short row, omitted rows, no
  tables): all 9 identical (exit 0).
- Expected saving: ≈ 0.18 s per call on a full CP-1 Module (0.21 → 0.03); proportionally less
  on smaller modules. Upper bound in E-NO-YOY: the 144 s self time.
- Guard: existing contract tests for each `ValueError` message, plus the micro-trial cases as
  a parametrized test that compares against a frozen copy of today's function.
- Risk 2 (shared validator on every contract load). Confidence 2 (profile + identity trial).

## P3 — memoise the parsed settled Module per verified blob hash

- Where: `src/deploy_vii/execution.py:607` `Execution.result(sha256)`: 372 calls in E-NO-YOY,
  122.1 s in `model_validate_json` + 29.6 s in `content_hash`, re-parsing the same
  content-addressed blobs (0.7 s per CP-1 parse in the micro-trial).
- Change: keep `self._load(sha256)` on every call (file read + sha256 check, so the
  missing/corrupt-blob errors at :591-596 stay exactly as now, tested by
  `test_known_core_blob_integrity_failures_map_identity_and_never_recreate_bytes`); move the
  parse and the canonical check into a module-level `functools.lru_cache(maxsize=4)` function
  keyed by the verified `sha256` string, which parses the verified bytes and raises the same
  "not the canonical module" `ValueError`. Exceptions are not cached by `lru_cache`, so a
  failing blob fails the same way every time.
- Same output: equal sha256 ⇒ equal verified bytes ⇒ the same deterministic parse. Callers
  receive one shared frozen `Module`; `head_module` (:627) already derives the stale variant
  with `model_copy`, which returns a new object and never mutates the cached one.
- Cost to watch: memory, ≤ 4 parsed Modules (≈ 233 MiB RSS per parsed 44 MB CP-1 blob, probe;
  measure RSS before/after in the same run).
- Risk 3 (cache on a store read path). Confidence 2.

## P4 — instance cache on `Contract.content_hash`: not recommended

The proposal's item 1 asked whether models are "frozen or never mutated after hashing".
`Contract` is `frozen=True` (`contracts.py:76`), so attribute assignment raises. But a cache
stored on the instance is unsafe here:

- pydantic 2.14.1 `BaseModel.__copy__` (`.venv/.../pydantic/main.py:1034`) copies `__dict__`
  and `__pydantic_private__` wholesale, and `model_copy(update=...)` (:410, :466) then writes
  only the updated fields into the copy. A cached hash (in `__dict__` via `cached_property`
  or in a `PrivateAttr`) would be carried into a copy whose content differs, giving a wrong
  hash. `src/` has 96 `model_copy(` call sites, e.g. `execution.py:304, 486, 493, 627`.
- Private attributes also take part in `BaseModel.__eq__` (`main.py:1227`), so a
  `PrivateAttr` cache would make equal models compare unequal depending on whether they had
  been hashed.
- A value-keyed external cache is also wrong: pydantic equality treats `Decimal("1.0")` and
  `Decimal("1.00")` as equal while their JSON (and hash) differ.

A safe instance cache would need `__copy__`, `__deepcopy__` and `model_copy` overrides on
`Contract`. P1 and P3 remove the measured repeats (≈ 270 of the 415 profiled seconds) at their
call sites without that.

## Deferred

- P5 `financial_validation.py:42` `records`: 47.7 M recursive calls, 126 s. Candidate:
  per-class tuple of model-bearing field names, preserving field order. Needs its own trial.
- P6 `live/submission.py:488/499` `quality_inputs`/`known_bindings` and
  `cp1_workflow.py:256` `_stage_registers` (≈ 460–610 s, overlapping): memoising them skips
  the "every stage recomputed" re-verification the docstrings promise
  (`cp1_workflow.py:257-260`, `submission.py:489-491`). That is a verification-policy change,
  not an optimisation; it needs an owner ruling first.
- `pytest-xdist`: new dependency; needs a decision record and the user's word.

## Apply order (after the user's word)

1. Write each guard test first and record it failing (P1 call count) or passing-identical
   (P2/P3 behaviour) on current code.
2. Apply P2, then P1, then P3, one commit each, `mx-feature` implementer, `mx-precise`
   review; `mx-adversary` for P3 (store read path).
3. Per change: rerun the same heavy-test set with the same harness; accept only gains
   > 2 × noise; `python3 -I cases/pins.py --check`; affected tests green.
