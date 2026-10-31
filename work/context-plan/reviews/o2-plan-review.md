# O2 plan review (mx-autonomous, read-only), 2026-10-31: verdict fix (1 High, 7 Medium, 6 Low)

Target: `docs/superpowers/plans/2026-10-31-part-b-o2.md` draft (363 lines).

- **H1** (plan :253-272). Frozen oracles cannot drive a `prepare`d pack: `preparation_request` appends a
  `context` source (context.py:726-729); CP-0 `validate_review` requires every prepared source assessed
  once (readiness.py:341-344); no frozen oracle has a `context` row (grep of cases/*/submissions.json,
  manifest.json: 0); every oracle uses `page:` locators (only cases/upstream/manifest.json has two
  `line:`); research-minimal.json's run fields differ from the oracle run (cases/cp3-cp6-owner/manifest.json
  R3: northbridge-synthetic, 2026-01-10, synthetic); synthetic sources are supplied page text hashed as
  pages joined with `\f` (tests/cp3_cp6_runs.py:87). The rebase derives the locator from the quote, so a
  wrong-page or deliberate gap-case citation would pass; page checks (`absence_issues`
  readiness.py:276-299, `page_numbers`) stop applying; the round-trip guard proves nothing
  (`literal()` substitutes at run time, cp3_cp6_runs.py:108-112). Fix: drop the rebase; commission a new
  synthetic oracle under B2 (preparer ≠ `mx-precise` reviewer ≠ builder) frozen against the pack
  `prepare` produces (text sources, a context.json with the oracle's run fields, CP-0 row for `context`).
- **M2** (:229). `Run.requested_modules` defaults to the full preset (contracts.py:92-95) and
  `preparation_request` never sets it (context.py:711-718): no one-module walk through `run_pathway`.
  Fix: `_finish_run(workflow, …)` (receipt, render, verify, run.json) tested on the one-module fixture
  (tests/test_owner_workflow.py `fw.make_pack` + `publish`).
- **M3** (:141, :273). `isinstance` admits subclasses (`AuthoringAdapter(RecordedAdapter)` answers by
  default). Fix: exact-type check; author recordings by driving O5's `ToolLoop` directly, replay through
  `run_pathway` with a plain `recorded_adapter`.
- **M4** (:140, :161, :191-192). A lost `mkdir(exist_ok=False)` race goes to Stop and writes into another's
  directory. Fix: `FileExistsError` at mkdir raises `RunDirExists`; nothing written.
- **M5** (:154). `S1`/`s1` collide on case-insensitive APFS (contracts.py:14). Fix: refuse ids colliding
  after `casefold()` as `DuplicateSource` before any write.
- **M6** (:152). FIFO blocks `open("rb")`; stat-then-open TOCTOU. Fix: `os.open(O_RDONLY|O_NONBLOCK|O_CLOEXEC)`,
  `fstat` + `S_ISREG` on the fd, capped read from the same fd.
- **M7** (:207, :226-227, :287, :350). After O1, a step fault after publish leaves `publication/`;
  `_outcome_rules` refuses any run with a `BLOCKED_EDGE` refusal or an unsettled head
  (owner_rendering.py:662-665), so blocked O1 end states become `stopped: render: owner_render_blocked`;
  a verify failure after the rename keeps `delivery/` (owner_rendering.py:960-961, 985). Fix: Q4's
  amendment lists `publication/` (after a publish), `delivery/` (after a verify failure following the
  rename) and `owner_render_blocked` for blocked walks; send it to the testing session as a contract change.
- **M8** (:144, :175, :240-241). Live gate checked twice; `run_pathway` re-checks against the default root
  and could refuse a ruling the adapter accepted. Fix: read the `GateResult` from an exact-typed
  `LiveAdapter` (O5 plan :128).
- **L9** (:304-307). Excepted quotes skip the `printed` check. Fix: still require `printed` in some single
  line of that source; report excluded PDF quotes; the exception list review is a departure to rule.
- **L10** (:140). Use `os.path.lexists` (dangling symlink).
- **L11**. No hash check after `prepare` (it turns FileNotFoundError into an unreadable source,
  preparation.py:389-390). Fix: each pack `Source.sha256` equals the staged bytes' hash.
- **L12**. Q5 `context` entry `media_type` `text/plain` (context.py:728).
- **L13**. Charsets: allow only utf-8, windows-1252, iso-8859-1, ascii.
- **L14**. O1 Q5 keeps `EarningsWorkflow` "until O2"; O2 must say keep or remove.
- Answers: Q1 sound only with a length ceiling tied to O4's `read_inputs` cap, ruled after Task 1 measures
  line lengths; Q2 not a stub, but use a private `_run_pathway(..., prompt_for)` (O5's `ToolLoop` takes
  `prompt_for`, O5 plan :169), and Task 4 proves orchestration with a test composer, not the prompts;
  Q3 after H1; Q4 as M7; Q5 consistent (Tasks 8 and 11 do not read `sources`); Q6 fine.

## Controller rulings (2026-10-31)

- All findings accepted as proposed, with these specifics:
- **H1:** O2 adds a task (before the end-to-end task) that commissions a new synthetic oracle case,
  `cases/o2-synthetic/`, under B2: a preparer agent (not O2's builder) writes text sources (the existing
  synthetic page text of the chosen preset's sources, one `.txt` per source), a `context.json` with that
  oracle's run fields, and every module submission for the preset re-cut to the `line:N` locators and
  file hashes `prepare` actually yields, plus a CP-0 row for `context`; an independent `mx-precise`
  review checks that each citation's quote sits on its cited line of the prepared pack, that every gap
  or absence case of the source oracle stays a gap, and that no value differs from the source oracle;
  frozen before the end-to-end task is built. Preset: the one O1 Task 5's end-state table shows
  settling through CP-5 on frozen submissions (expected portfolio_decision). The plan's tasks name the
  preparer and reviewer roles; the controller dispatches them.
- **Q1:** Task 1 records per-rule miss counts and line-length statistics (max, p99) on the 22 golden HTML
  sources; the controller rules the line rule from them before Task 2; the length ceiling is set with
  O4's byte cap.
- **Q4/M7:** the stopped-file-set amendment goes to the testing session (Plan B list in
  `work/context-plan/part-b-review-2026-10-31.md`).
- **L9:** the exception list is reviewed by `mx-precise` before O2's golden-quote task is built.
- **L14:** O2 keeps `EarningsWorkflow` and its three-run-id gate: its frozen E-* cases depend on it; new
  runs take the owner path. Cost: two CP-1B paths remain until a later cleanup.
