# Shared defect test fix1 re-review (mx-precise)

**Shared defect-class test, fix round 1 (4871569): scoped re-review**

**Verdict: REQUEST CHANGES.** One part of M1 is still open (Medium). L1 and the Info items are closed.

**M1: partly closed. Mutant A is open (Medium).**
- **Sinks: closed.** I read all 11 CP-0 patterns against `readiness.build_readiness` (`src/deploy_vii/readiness.py:408-530`):
  - `objective`, `reporting_period`, `document_family`, `entity`, `period`, `version_relationship`, `evidence_demand` and `rationale` go to `Fact.text: str | None` (`contracts.py:161`).
  - `sources.*.limitations.*` and `consumers.*.limitations.*` go to `Module.limitations: tuple[str, ...]` and the T8 limits `Fact.text`.
  - `analysis.*.limitation` goes to `Claim.limitation: str | None`.
- For CP-1 I checked 7 patterns: `name`, `fiscal_year_end`, `document_type`, `analytical_use`, `period_label`, `limitations.*` and `sources.*.limitations.*`.
  - They are plain `Text` fields on `EntityContext`, `ReportingScope` and `SourceContext` (`source_context.py:49-107`).
  - They end up in the cells built at `canonical_tables.py:163-225` and the `GapPeriod.label` at `canonical_gaps.py:337`.
- `RunText` is used only by `Claim.text` (`contracts.py:203`). `prose_issues` checks only claim text (`prose.py:310-317`). The CP-1 claims come from the narrative findings (`narrative_projection.py:166`). No allowlisted path reaches `RunText`.
- **Stale pattern fails: closed.** `defect_classes.py:764-768` reports it, and `selfcheck.py:529` tests it.
- **Lax fake with the allowlist fails: closed.** `selfcheck.py:513`.
- **Citation `quote`/`locator` refused: closed.** CP-0 has 54 free-text paths, 28 of them under `citations`. No pattern matches any of the 28, so the green CP-0 test asserts all of them journal an issue.
- **Mutant B (`allowed = True`): caught.** The selfcheck exits 1 with 2 failures.
- **Mutant A: open (Medium), `defect_classes.py:771`.**
  - I added `("analysis", "*", "text")` (`Claim.text`, a `RunText`) to `CP0_VERBATIM`. `model_text_failures` returns `[]`.
  - The cause: an allowlisted path is only allowed to be `valid`; it is never required to be. A path that is wrongly listed but refused today passes silently.
  - A later regression that loosens `Claim.text` would then pass. That is the M1 defect class, now one field at a time.
  - Ruling round 5 item 10 limits the set to non-`RunText` sinks, but only the comment checks this.
  - Fix, either of:
    - fail when an allowlisted path refuses every hostile value (the stale-pattern check, extended to outcomes);
    - or assert that the schema leaf of each allowlisted path carries no `valid_syntax` validator.
  - Add a selfcheck case for whichever you choose.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/defect-classes-review/fix1/p5_verbatim_mutants.py` replaces p3. It exits 1 today (mutant A survives) and should exit 0 after the fix.

**L1: closed.** `p1_schema_coverage.py` (same folder) exits 0. The shared set has 33 entries, covering all 12 `STEPS` schemas and every `*Submission` class, and none of the probe's schemas is missing.

**Info: closed.**
- The test is renamed at `selfcheck.py:418`.
- `selfcheck.py:379` now compares the whole `HOSTILE_JSON` dict, values included.

**API: usable as is for an owner core.**
- `ReviewRun` (`defect_classes.py:721`) only needs `submit_review(str) -> Mapping` with `status` and `issues`.
- A module can wrap its core's `submit` in `fresh()` the same way `_Cp1ContextRun` does.
- `free_text_paths` accepts either a str or parsed JSON. `assert_hostile_refused(schema)` needs only the schema.
- One requirement: the core's follow-up after a refusal must be able to return `valid` on the same run, or every case is reported as wedged.

**New findings:** none besides mutant A.

**Gates**
- The three test files: exit 0, 278 passed in 71.9 s, run in parallel with my probes. The CP-1 file alone is about 48 s according to the fix report.
- `git grep noqa -- src tests | wc -l` gives 13. That is within the 13 ceiling.
- `p1`: exit 0. `p5`: exit 1.
- The worktree is still clean.

Not verified: mypy and ruff (I did not re-run them). I read the sinks of only 4 of the 10 CP-1 patterns' fields beyond the 7 listed above was not done; specifically `evidence_rationale`, `event_scan_explanation` and `entities.*.limitations.*` were not traced downstream. I did not check renders beyond the build sink types. I could not exercise an owner core's `submit` seam, because no core is registered. Timings come from one run on a loaded machine.
