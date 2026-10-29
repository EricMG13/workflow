# Shared defect test fix round 1 report (mx-feature)

Fix round 1 is committed as 4871569 on top of 8c5bf8b. M1, L1 and both Info items are done.

I wrote the selfcheck tests alongside the code and ran them together once; I did not run them red first.

**Final API** (changes only; other names are as before):
- `model_text_failures(schema: type[BaseModel], positive: str, fresh: Callable[[], ReviewRun], *, values: Sequence[str] = MODEL_TEXT_HOSTILE, verbatim: frozenset[tuple[str | int, ...]] = frozenset()) -> list[str]`. `require_issue` is gone.
  - `verbatim` is the only place a `valid` outcome is allowed.
  - Every other free-text path must journal an issue, and the follow-up must be `valid`.
  - A `verbatim` pattern that matches no path in the payload is itself a failure, so the set cannot go stale.
  - Raises still propagate.
- New `path_matches(pattern, path) -> bool`. `"*"` in a pattern stands for any list index.

**Verbatim sets.** Both are `Mapping[pattern, sink]`, passed as `frozenset(...)`.
- **CP-0** (`CP0_VERBATIM` in `tests/test_defect_classes_shared.py`): all 25 accepted paths. I read `readiness.build_readiness` for each sink.
  - `objective` and `reporting_period` go to `Fact.text`.
  - `sources.*.{document_family, entity, period, version_relationship}` go to `Fact.text`.
  - `sources.*.limitations.*` and `consumers.*.limitations.*` go to `Module.limitations` (`str`) and `Fact.text` (T8 limits).
  - `consumers.*.{evidence_demand, rationale}` go to `Fact.text`.
  - `analysis.*.limitation` goes to `Claim.limitation` (`str | None`, not `Claim.text`).
- **CP-1 source_context** (`CP1_CONTEXT_VERBATIM` in the new `tests/test_defect_classes_cp1.py`): all 23 accepted paths, as 10 patterns.
  - `entities.*.{name, fiscal_year_end}` and `entities.*.limitations.*` are plain `Text` fields on `EntityContext`.
  - `limitations.*` goes to `SourceContextReport.limitations` (`Text`).
  - `sources.*.{document_type, evidence_rationale, analytical_use, event_scan_explanation}` and `sources.*.limitations.*` are plain `Text` fields on `SourceContext`.
  - `sources.*.scopes.*.period_label` is `ReportingScope.period_label` (`Text`).
  - These feed the canonical table cells (`str`) and the `canonical_gaps` label (`Text`).
- No accepted path in either module reaches `RunText` or `Claim.text`, so there is no defect to report. I checked that CP-1's claims are built from the narrative step, not this one.
- Citation `quote` and `locator` paths are in neither set, so the tests now assert they are refused.

**L1.** `SCHEMAS` in the shared file now also holds every live `STEPS` schema and every `*Submission` class in `deploy_workflow.owners`. The Q5 set runs over all of them.

**Info items.** The per-field-floods test is renamed to `test_hostile_inputs_add_the_per_field_floods_of_the_first_string_fields`. `test_hostile_set_is_the_probes` now compares the full `HOSTILE_JSON` dict, values included.

**Selfcheck.**
- A fully lax fake fails even when the verbatim set is passed.
- A fake that accepts only the allowlisted path passes.
- The same fake fails when the path is not listed.
- A stale pattern is reported.
- A verbatim path does not excuse a build that raises.

**Runtime.** I split CP-1 into its own file, so each file stays under 60 s.
- Selfcheck: 0.4 s.
- Shared: 17.6 s.
- CP-1: about 48 s.

**Gates.**
- All three test files together: 277 tests, exit 0.
- `ruff check` and `ruff format --check`: exit 0 on 4 files.
- `mypy --strict`: exit 0 on 4 files.
- `git grep noqa -- src tests`: 13, unchanged.
- `p1_schema_coverage.py`: exit 0.
- `p4_hostile_on_uncovered.py`: exit 0.
- `p3_require_issue_scope.py` can no longer run, because it passes the removed `require_issue` argument. Its job is now done by the tests.

Not verified: L2 (null or empty free-text fields, backlog per the ruling). CP-1A and CP-2 model text through the store. CP-1 steps after `source_context`. Downstream rendering of the verbatim text beyond the build and sink types read in the source. Owner-core `submit` seams (no core registered). Runtime under heavy load.

agent=mx-feature fix-rounds=1 gates-first-pass=n
