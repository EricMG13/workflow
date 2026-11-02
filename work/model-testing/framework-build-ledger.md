# SDD ledger — plan: docs/superpowers/plans/2026-10-31-model-testing-framework.md

Branch claude/agitated-meitner-5f25bb (reset to efe43725, merged codex/checkpoint 2e7709cc as 0e317b2a; claude/codex-findings-review-64c673 is checked out in another worktree).
Spec: docs/superpowers/specs/2026-10-31-model-testing-design.md. Routing: AGENTS.md + ~/.claude/CLAUDE.md (mx-*; 2 Sonnet fix rounds, 3rd = mx-autonomous plan + fresh mx-feature).
Scope: Tasks 1-5, 7-10. Deferred: Task 6 (W3, phases 2-8 change layouts), Task 11 (until O3/O4/O6 merged).

## Pre-flight scan (after amendments)
| Pair / task | Produces → consumes | Finding |
|---|---|---|
| T1→T2 | CONFIGS → config/provider check | ok |
| T1→T3 | ACCOUNTS, CONFIGS → cap_for | ok |
| T1→T4 | CASES → load_case loop | ok |
| T2→T3 | RunMeta, CallRecord (Runs) → account_spend live-only | ok |
| T2→T8 | read_run → score_run | ok |
| T2→T10 | RunMeta, CallRecord (call_index, error_class) → retries, account section | ok |
| T3→T10 | account_spend(runs) → spend vs cap | ok |
| T4→T5 | GoldenCase.facts (in-plan only) → unknown-fact refusal | ok: out-of-plan facts refused as unknown, consistent with W1 |
| T4→T7 | checker() normalise, SCALE_EXP → compare | ok |
| T5→T7 | entries, depends_on, pending → outcomes | ok |
| T7→T8 | score_module(head_status incl. refused, refusal_missing) | ok |
| T8→T10 | PathwayScore (mode, outcome, stopped_reason) → cells | ok |
| T9→T10 | FaultRecord → faults by class | ok |
| T1 self | test imports private `_PRESETS` | Ruling: use public PATHWAY_MODULES — same mapping, public name — none if wrong |
| T4 self | context-refusal test mutation ("-tdg") may be refused by check.py first | Ruling: implementer picks a mutation check.py accepts and load_context refuses, records it — test still proves N2 — none |
| T7 self | units rule amount×scale | consistent with display.py:44 (multiply before rounding) |
| T8 self | fixture from tests/o2_case.py | non-golden synthetic case; GoldenCase/Mapping built in test — ok |
| T2,3,5,7,8,9,10 | each test list vs interfaces | consistent |

## Log
- 13:00 Plan B amendments (C2,C4,W1,W3,W4,W5,W7,W8,W9,N2 + O5 CallRecord reuse, live-only accounts) drafted by controller; mx-feature docs review dispatched.
- Ruling: W1 — NATL CP-4 facts treated as out of plan by the loader, not deleted from the approved golden — no golden reopen, ready if requested_modules is ruled — cost if wrong: one golden edit later.
- Ruling: Task 2 imports O5's CallRecord instead of a second definition — no contract drift — cost if wrong: none (same shape, Plan A says O5 writes exactly it).
- Ruling: spec §7.6 harness line also corrected (adapter/turn loop are orchestrator faults per §1a) beyond W7's prompt line — same staleness — cost if wrong: one line.
- 13:06 user (direct, this session): "yes" to the per-session venv OK — controller may run RED and gate commands (fast node-id pytest, ruff, mypy) with /Users/ericguei/Documents/Deploy Workflow/.venv/bin/python, PYTHONPATH=src.
- 13:08 Task 1 dispatched (mx-scaffold), BASE 0e317b2a
- 13:08 Plan B amendments committed 1af5176e; review mx-feature: fix (M1 W9 wiring owner, L cite :310, L key-material message, I Runs Sequence) → all ADDRESSED, pass. agent=mx-feature fix-rounds=1 gates-first-pass=n/a (docs)
- Ruling: after Task 1, implementers for tasks with disjoint files run in parallel (2, 4, 9; then 3, 5; then 7; 8; 10) — dependency chains allow it and wall time matters — cost if wrong: an index.lock commit race, retried per common.md.
- 13:09 Task 1: complete (commits 1af5176e..10da2fec, review clean; mx-precise pass). agent=mx-scaffold fix-rounds=0 gates-first-pass=y (5 passed; controller re-ran pytest 5 passed)
- Task 1: minor (deferred): L1 test path relative to cwd (anchor to __file__); I1 Account does not validate reserve/credit ranges
- 13:09 Tasks 2, 4, 9 dispatched in parallel (mx-feature)
- 13:11 Task 9 built 175d7956 (mx-feature, 7 passed, no RED observed) → mx-precise review with test-strength probes
- 13:11 Task 2 built 94d54a6a (mx-feature, 20 passed, RED = ModuleNotFoundError) → mx-precise + mx-adversary
- 13:11 Task 4 built f5bf2375 (mx-feature, 7 passed 7.4 s, no RED observed) → mx-precise
- 13:11 Task 3 dispatched (mx-feature); Task 5 dispatched (mx-feature)
- 13:12 Task 2 mx-precise: fix — F1 Medium records.py:61-63 extra_forbidden loc echoes input field name (key) into JournalError (probe task-2-loc-echo.py exit 1). Pre-existing same flaw in O5 record.py:114-116 _invalid → owner (MANAGER handoff). Waiting for mx-adversary before fix round 1.
- 13:12 Task 9 mx-precise: fix — F1 Medium needs_owner double-iterates Iterable (generator → IndexError; probe task-9-generator.py); F2 Low ValidationError text echoes raw line; F3 Low model branch untested (task-9-mutants.py); F4 Info empty ids. Fix round 1 sent to original implementer (HEAD before fix 8376a80a).
- 13:13 Task 4: complete (commit f5bf2375, review clean; mx-precise pass). agent=mx-feature fix-rounds=0 gates-first-pass=y (7 passed 7.4 s; controller re-ran 7 passed)
- Task 4: minor (deferred): F1 Low loader's own gold pin unreachable by tests (check.py refuses first) — add test with stub checker or drop pin (probe task-4-mutants.py C1/C2)
- 13:13 Task 3 mx-precise: pass (I1 unreachable guard, L1 no RED). Waiting on mx-adversary.
- 13:13 Task 5 built 8376a80a (mx-feature, 24 passed, no RED observed) → mx-precise; Task 7 dispatched (mx-feature)
- 13:13 Task 9: fix round 1/2 (4 addressed, 0 open — F1 generator, F2 echo, F3 model branch, F4 empty ids; commits 175d7956..0c9c3d53); re-review mx-feature pass; probes 0/0/0
- 13:13 Task 9: complete (commits 10da2fec..0c9c3d53, review clean). agent=mx-feature fix-rounds=1 gates-first-pass=y (7 passed first; 11 after fix)
- 13:14 Task 5: complete (commit 8376a80a, review clean; mx-precise pass, 9/9 refusal mutants caught by probe task-5-refusals.py). agent=mx-feature fix-rounds=0 gates-first-pass=y (24 passed; controller re-ran 24 passed)
- Task 5: minor (deferred): I-1 module_commits keys not checked against golden modules (typo maps nothing, facts stay pending)
- 13:16 Task 2 mx-adversary: fix — M1 (=precise F1) loc echo; M2 non-UTF-8 UnicodeDecodeError leaks file bytes via repr; M3 RunMeta no key check; L1 calls.jsonl non-file reads as no records; L2 __context__ keeps input; L3 cap_usd unbounded. Info (O5, pre-existing → owner): CallRecord money has no lower bound (negative settled cancels spend); attempt=true accepted; KEY_PATTERN \b misses glued keys; no size cap. Fix round 1 sent to original implementer (HEAD e93de09d).
- 13:16 Task 3 mx-adversary: fix — M1 unknown charge does not stop the configuration (spec §7.2; probe task-3-adv-unknown-stops-config.py); L negative money raises cap above usable; L Decimal context unpinned; L provider/config mismatch not refused (in-memory). Info: crashed live run (calls.jsonl, no run.json) spend uncountable → Task 11 brief must stop on a run folder without run.json.
- Ruling: unknown-charge stop goes in require_budget: a config_id with any live record of that config_id and cost_status unknown raises UnknownCharge(AccountExhausted) naming config and run_id — spec §7.2 says it stops that configuration and Task 11 already stops a config on AccountExhausted — cost if wrong: a config stops until the charge settles; the user can rule otherwise.
- Ruling (for Task 11 brief): driver stops on any run folder lacking run.json (crashed live run, spend uncountable) — cost if wrong: one manual resume.
- 13:16 Task 7 built e93de09d (mx-feature, 22 passed, RED = ModuleNotFoundError; 2 type: ignore) → mx-precise + mx-adversary (financial comparisons). Task 8 dispatched (mx-feature).
- Ruling: RunMeta.cap_usd has no upper bound (finite > 0 only) — no consumer uses it for spend (Task 3 uses usable credit) — cost if wrong: an absurd cap shown in a report
- 13:19 Task 2: fix round 1/2 (6 addressed, 0 open — M1 loc echo, M2 non-UTF-8, M3 RunMeta key, L1 non-file, L2 context, L3 cap; commit ea85ac1d); re-review mx-adversary pass; probes 0 (runmeta-key probe defective, corrected r1 probe exits 0)
- 13:19 Task 2: complete (commits 94d54a6a..ea85ac1d, review clean). agent=mx-feature fix-rounds=1 gates-first-pass=y (20 passed first; 33 after fix)
- Task 2: minor (deferred): records.py imports private O5 _strings (owner: make public); O5 out-of-scope items for owner: CallRecord money no lower bound, attempt=true, KEY_PATTERN \b glued keys (task-2-adv-o5-boundary.py), O5 _invalid loc echo (record.py:114-116), no size cap
- 13:19 Task 7 mx-precise: fix — F1 High absent/refused-without-inputs module can pass (judgment modules; all-golden-missing; all pending) (probe task-7-absent-passes.py); F2 Low refused head with present Module skips invented/untraced; F3/F4 Low type: ignore removable. Waiting for mx-adversary.
- Ruling: module value quantised half-up to the golden's stored places before comparing (3.94bn matches golden 3.9bn) — spec §7.4 says exactly this; the golden's precision is the oracle's — cost if wrong: a coarse golden accepts a slightly off value.
- 13:20 Task 3: fix round 1/2 (4 addressed, 0 open — M1 unknown stops config, L negative, L context, L mismatch; commit 9a8a756f); re-review mx-adversary pass (3 probe exits 1 confirmed probe artefacts; r1 probe task-3-adv-r1-refusals.py 0)
- 13:20 Task 3: complete (commits 9601e870..9a8a756f, review clean). agent=mx-feature fix-rounds=1 gates-first-pass=y (9 passed first; 20 after fix)
- Open for user (via MANAGER): no path settles an unknown charge, so under spec §7.2 a config with one unknown record stays stopped; needs a settlement record (e.g. billing reconciliation) — Task 11 or orchestrator scope.
- 13:24 Task 7 mx-adversary: fix — H1 unit ignored (percent fraction vs points, unit/scale), H2 duplicate locator first-wins, M3 absent passes (=precise F1), M4 blank limitation/refusal counts, L5 printed parse loose, L6 refused+module unchecked (=precise F2); I1-I6 spec ambiguities.
- Ruling: H1 module value converted by unit per display.py/report_view.py/cp5 UNIT_SCALE (PERCENT/decimal_fraction ×100; decimal_percent, basis_points as stored; unit/scale disagreement and class disagreement = mismatch) — product semantics are the oracle — cost if wrong: a unit we do not know is compared as units.
- Ruling: H2 duplicate facts at one locator = mismatch (invented if any carries a value against golden-missing) — never first-wins — cost if wrong: a benign duplicate fails a module (visible in report).
- Ruling: I1 honest gap only for blocked/restricted heads; an accepted head marking known golden facts missing fails — spec §7.4 binding, §10.3 covers declared limits — cost if wrong: a genuinely input-starved accepted module fails (visible, rerun).
- Ruling: I3 aliases only for text facts; I5 known dates compare as dates; I2 inherited kept (§9a.3); I4 rounding kept (§7.4); I6 provenance depth is orchestrator/receipt side — costs: minor scoring strictness changes.
- 13:24 Task 7 fix round 1 sent to original implementer (findings file task-7-findings-r1.md; HEAD 9a8a756f).
- 13:25 Task 8 built 68f7cb33 (mx-feature, 13 passed ~2 s, RED = ModuleNotFoundError). Concern: O2 offline full walk stops at render: owner_render_scope (>5 min, RUN_PROMOTION-gated), so receipt tests use a G1 owner run from test_financial_workflow helpers with a test-written run.json; stopped-run tests use real O2 author/replay. → mx-precise; Task 10 dispatched (mx-feature)
- 13:27 Task 7 fix round 1 done 10e1bbfe (36 passed, 14 RED first; 0 type: ignore; adversary probes 0 except rules.py cases 1/3 and provenance.py per rulings) → scoped re-review mx-adversary. Side effect: 4 Task 8 tests (68f7cb33) fail — they assumed an absent CP-MODEL passes; goes into Task 8 fix round.
- 13:27 Task 8 mx-precise: fix — F1 Medium 4 tests depend on lenient absent-judgment scoring (probe task-8-strict-scoring.py); F2 Info upstream_mismatches untested. Exception types verified (WorkflowError ⊂ ValueError). Fix round 1 sent to original implementer (HEAD 10e1bbfe).
- 13:28 Task 10 built 81013c5b (mx-feature, 10 passed, RED = ModuleNotFoundError; fixture hand-checked by implementer) → mx-precise (independent recompute)
- 13:30 Task 7: fix round 1/2 (10 addressed; new N1 Medium fraction vs decimal golden regression, N2 Low date-text evidence, N3 Low scale word anywhere; commit 10e1bbfe). Re-review mx-adversary: fix.
- Ruling: N1 a decimal golden with unit None accepts fraction units compared raw (no ×100); ×100 only against percent goldens — avoids reopening the approved NATL golden — cost if wrong: a fraction-vs-multiple confusion on a unit-less decimal golden.
- Ruling: N2 date-typed conflicting golden also accepts exact evidenced printed text; N3 scale word must follow the number; pp added to point units — costs: minor.
- 13:30 Task 7 fix round 2/2 sent (task-7-findings-r2.md; HEAD 81013c5b).
- 13:30 Task 10 mx-precise: fix — F1 Medium partial token sums unmarked (task-10-partial-tokens.py); F2 Low unknown pathway counted silently + type: ignore (task-10-unknown-pathway.py); F3 Low offline cost mixed in Totals; F4 Low fault line wording/config. All fixture numbers independently recomputed: match.
- Ruling: partial token sums render as "≥N.Nk tok"; Totals split Cost (live) / Cost (offline, computed); fault lines carry config_id — the report must never present a lower bound or non-money as exact money — cost if wrong: layout churn only.
- 13:30 Task 10 fix round 1 sent (HEAD 81013c5b).
- 13:31 Task 7 fix round 2 done 73cf6399 (40 passed, 4 RED first; probes 0) → scoped re-review mx-adversary
- 13:31 Task 10 fix round 1 done 30fb988f (14 passed; unknown-pathway probe 0; partial-tokens probe 1 = probe artefact, controller confirmed cell renders ≥1.7k tok) → scoped re-review mx-feature
- 13:32 Task 10: fix round 1/2 (4 addressed, 0 open — F1 partial tokens ≥, F2 unknown pathway, F3 split cost, F4 fault line; commit 30fb988f); re-review mx-feature pass
- 13:32 Task 10: complete (commits 81013c5b..30fb988f, review clean). agent=mx-feature fix-rounds=1 gates-first-pass=y (10 passed first; 14 after fix)
- Task 10: minor (deferred): stopped run's unreached modules show "—" not STOPPED (reviewer note)
- 13:32 Task 7: fix round 2/2 (4 addressed, 0 open — N1, N2, N3, pp; commit 73cf6399); re-review mx-adversary pass
- 13:32 Task 7: complete (commits e93de09d..73cf6399, review clean). agent=mx-feature fix-rounds=2 gates-first-pass=y (22 passed first; 40 after round 2)
- Task 7: minor (deferred): R2-L1 a covenant multiple stated with unit PERCENT matches a unit-less decimal golden (N1 consequence; probe task-7-r2-adv-multiple-as-percent.py) — clean fix is tagging fraction goldens (golden change, owner); A-I2 inherited causation, A-I4 rounding window, A-I6 provenance depth recorded as rulings
- 13:40 Task 8: fix round 1/2 done cec53635 (tests only; 14 passed 3 skipped; probe 0). F1 partly open: passed=True path and tamper/stopped isolation only in RUN_PROMOTION-gated good_run tests (good run render/verify >25 min).
- Ruling: fast coverage of score_run composition via a test-only monkeypatched score_module wrapper (real scorer called, passed forced True) on the real G1 gap run; gated good_run tests kept as CI evidence — composition is pathway.py's job, module rules are Task 7's and tested there — cost if wrong: a mismatch between forced and real passing is caught only in CI.
- 13:40 Task 8 fix round 2/2 sent.
- 13:41 Task 8 fix round 2 done 6e798e3d (18 passed 3 skipped; probe 0) → scoped re-review mx-precise
- 13:41 Branch gates (controller): pytest tests/test_model_testing_*.py 172 passed 3 skipped (RUN_PROMOTION-gated good_run) 10 s exit 0; ruff check 0; ruff format --check 0; mypy strict 19 files 0; suppressions 0. GitNexus: repo not indexed (n/a). Diff src+tests 4134 lines vs 0e317b2a (over the global 800 cap; AGENTS.md exempts lane integrations — PR Manager to decide split).
- 13:41 Task 8: fix rounds 1-2/2 (F1 addressed, F2 addressed as far as fast run allows; commits cec53635, 6e798e3d); re-review mx-precise pass
- 13:41 Task 8: complete (commits 68f7cb33..6e798e3d, review clean). agent=mx-feature fix-rounds=2 gates-first-pass=y (13 passed first; 18 passed after) — 3 RUN_PROMOTION good_run tests deferred to CI (built, not run)
- Task 8: minor (deferred): duplicate test test_inherited_upstream_arrives_at_the_downstream_module (:386-400) repeats :302-325 and is misnamed
- 13:47 user (direct): "fable is available" → whole-branch review moved from mx-autonomous (stopped) to mx-architect (Fable), per global §1.
- 13:56 Whole-branch review (mx-architect, Fable): fix — F1 High receipt plan subset scored + receipt identity unchecked; F2 Medium omitted conflicting = mismatch (not forgivable); F3 Medium refusal gaps counted as matched in report; F4 Medium not_applicable scored as known; L1-L3; I1-I5. No ruling overturned. Rewrite of score_module/_score_entry recommended inside the fix.
- Ruling: F1 module list = PATHWAY_MODULES[pathway]; receipt plan outside preset or run_id/pathway mismatch refused (JournalError) — spec §7.4 — cost if wrong: a run with a deliberately narrowed requested_modules is refused (none planned; W1 keeps presets).
- Ruling: F3 refused gap_ok stays in denominator, out of numerator, shown "(N refused)"; PASS/FAIL from ModuleScore.passed — a refusing model must not top accuracy — cost if wrong: layout only.
- Ruling: F2 omitted conflicting = missing_in_output; F4 not_applicable = missing; L1-L3, I1-I4, Task 8 duplicate test fixed in the same wave — costs minor.
- 13:56 Final fix wave dispatched (fresh mx-feature; final-findings.md; HEAD 6e798e3d).
- 14:02 Final fix wave done 6315738e (186 passed 3 skipped; branch + task probes 0; 11 probes exit 1 only from removed GoldenCase.golden kwarg — controller confirmed stripped copies in scratchpad/probes-nogolden exit 0) → scoped re-review mx-architect
- 14:04 Final fix wave: re-review mx-architect pass (all items addressed; Low: RUN_PROMOTION good_run tests now assert passed False, real-scorer passed=True path unexercised at any level → Task 11/owner item). Final gates: pytest tests/test_model_testing_*.py 186 passed 3 skipped exit 0; ruff 0; format 0; mypy strict 19 files 0; suppressions 0; tests/test_run_pathway.py 40 passed; no change outside src/deploy_workflow/model_testing.
- 14:10 MANAGER ruling (under the user's standing "apply your recommendations" rule; user may overrule): Task 11 adds a user-filled settlement record for unknown charges.
- 14:10 MANAGER ruling: one PR; the AGENTS.md lane-integration exemption covers the 800-line cap. MANAGER verified a9996921 (25 files, +4910/-3, all in scope). Merge waits for the user's word; MANAGER passes it to PR Manager.
- 14:07 CONTEXT: fixing the four O5 items as ruling B26; `_strings` becomes public `deploy_workflow.model.record.strings` (alias kept). Follow-up here once its commit lands: switch model_testing/records.py to `strings`.
- 19:04 B26 follow-up: fast-forwarded to codex/checkpoint 9d4a2401 (CONTEXT release 1, contains 7418f074/81c3679b/f1a43026). records.py switched `_strings` → public `strings` (mx-scaffold). The merge broke test_negative_money_refused (3 cases): O5 7418f074 adds `Field(ge=0)` to CallRecord money. Ruling: the test asserts CallRecord's ValidationError and keeps budget.py:49-50's refusal tested via the file's model_copy idiom, per MANAGER — keep asserting the refusal. budget.py:49-50 (negative and non-finite money) is now unreachable through any validated CallRecord; it is kept, explicitly, as defence in depth for records that bypassed validation. Cost if wrong: one dead branch. mx-feature scoped review pass; probe scratchpad/probe_neg.py 0. Info for CONTEXT: record.py:165-166 `_strings` alias now unused, can be dropped.

## Tasks 6 and 11 (2026-11-02, base codex/checkpoint 9c018f76, CONTEXT release 3)
- 08:02 MANAGER: blockers landed (O3 Task 7 + O3/O4 phase gate APPROVE; O6 Task 6 + phase review APPROVE; Phases 5, 7, 8 phase-approved). Fast-forwarded to 9c018f76. SDD workspace was wiped (git-ignored); recovery from this ledger and git log.
- Ruling: Task 6 runs as one batch over every golden module at 9c018f76, one preparer per case (6 in parallel, disjoint outputs), not one batch per phase — Phases 2-8 have all landed, and modules recur across phases (CP-0, CP-1C, CP-3D, CP-4C), so mapping per phase would remap them; CP-2 is changed by no phase. Cost if wrong: a later layout change reopens that module's entries (R7).
- Ruling: a fact whose row id or field the model chooses at run time goes to `unmapped` with the reason, never a guessed locator; a module may exceed the 20% unmapped bound only with the reason in its report (Task 6 Step 4). Cost if wrong: under-scored modules, visible in the report.
- Ruling: preparers do not run the venv (builder venv refusal); the controller runs load_mapping. Stage contract work/model-testing/mapping/CONTEXT.md; briefs work/model-testing/mapping/briefs/<case>.md; Task 5 I-1 carried (every module_commits key is a golden module of the case).
- 08:02 Task 6 preparers dispatched (mx-feature × 6, one per case). Task 11 implementer dispatched (mx-feature) with controller addendum .superpowers/sdd/2026-10-31-model-testing-framework/task-11-controller.md: rulings 1-8 (corpus/cases args, --recordings, crashed-run stop, settlement record charge-settlement/1 in budget.py, I5 refusal names checked in score_run, §7.2 estimates, subcommands, real-scorer passed=True test). Task 11 runs beside Task 6: disjoint files.
- 08:06 Task 6 preparers done (mx-feature: tdg a79120e6, shc a2cd5e1a, bgs a2b3dc4a, lth aa9a2cdf, ihrt aee3a923, natl ad1872af). load_mapping exit 0 on all six (scratchpad/check_maps.py). Entries / in-plan facts: TDG 3/178, SHC 9/97, BGS 1/108, LTH 5/187, IHRT 1/165, NATL 1/81. Causes: register rows r01.. in model submission order; CP-2 is prose + refNN copies of CP-1 (golden CP-2 debt facts belong to CP-1); filing data points no module outputs; CP-1 numbers live in financial_gold.json, pinned but never scored.
- Ruling: out-of-plan facts are not mapped (NATL CP-4; load_mapping refuses them since GoldenCase.facts excludes them); CONTEXT step 5 corrected. Cost if wrong: none — they score nowhere in this pathway.
- 08:06 Sent MANAGER the coverage finding with recommendation: (1) commit the six mappings after mx-precise review; (2) score CP-1 against financial_gold.json; (3) row-key locator for registers; (4) goldens owner re-tags. Proceeding with (1); (2)-(4) wait for MANAGER (they widen the approved spec's scoring). Reviews dispatched: mx-precise afc8b676 (TDG, SHC, BGS), a5f4bba4 (LTH, IHRT, NATL).
- 08:09 User ruling via MANAGER, verbatim: "Steps 2-4". Approved: (1) commit the six mappings after mx-precise; (2) score CP-1 against financial_gold.json; (3) row-key locator; (4) goldens re-tag by a separate oracle-preparer (never the builder of 2-3), reviewed by mx-precise, re-pinned through cases/pins.py, before the step 2-3 preparers re-run. Report post-fix coverage per case.
- Ruling: step 3 runs beside Task 11 (disjoint files: mapping.py, scoring.py and their tests vs run.py, __main__.py, budget.py, pathway.py); step 2 follows step 3 (both touch scoring). Cost if wrong: a rebase of one commit.
- Ruling (step 3 design): RowKey(field, aliases) separate from subject_aliases (keeps ruling I3: aliases compare text values only); key cell matched with scoring's `_text`; 0 rows → missing_in_output, 2+ rows → the existing "N facts at one locator" path. Cost if wrong: model wording that differs from subject + aliases scores missing.
- Ruling (step 2 design): GoldenCase carries financial_gold facts as CP-1 golden facts (unit/scale converted), so CP-1 is mapped and scored through the same mapping.json + scorer; the metric+period → CP-1 locator table is the CP-1 entries of mapping.json, made by the oracle preparers, not the builder. Cost if wrong: one more file format.
- Ruling (step 4 pin): cases/pins.py does not cover cases/goldens/; step 4 adds `cases/goldens/*/module_golden.json` and (after the re-run) `cases/goldens/*/mapping.json` to its PATTERNS and regenerates cases/PINS.json, as MANAGER asked. Cost if wrong: a PINS.json merge conflict with other branches (sorted lines).
- Ruling (step 4 format): not_golden is module-level ({module, why}); a removed fact is one item {module, why: "<fact_id>: <reason>"}; a re-tagged fact gets the new module prefix in fact_id (check.py rule) and every reference (derivation operands, line-exceptions.json) follows. A fact financial_gold already holds goes to not_golden "covered by financial_gold" instead of a re-tag. Cost if wrong: re-tag churn.
- 08:09 Step 3 implementer dispatched (mx-feature a79ccae7), brief .superpowers/sdd/…/step-3-brief.md.
- 08:13 Task 6 review: mx-precise afc8b676 (TDG fix: 2 High; SHC pass + Medium product finding; BGS fix: Medium commits) and a5f4bba4 (LTH fix: High horizon_months; IHRT fix: High missed CP-1A slot; NATL pass; Low CP-0 context.py). Fix round 1 by the same preparers; scoped re-reviews closed all (probes rereview.py, commits.sh, p2, p4, p5 exit 0). load_mapping exit 0 on all six. Entries: TDG 1, SHC 9, BGS 1, LTH 4, IHRT 2, NATL 1.
- Ruling: SHC CP-1B entries stay (locators correct); CP-1B refusing the context's q2→q2 pair (owners/cp1b.py@438317d3:155-163) is a product finding for the owner list, not a mapping defect. LTH horizon_months goes to step 4 as a golden question.
- Ruling: Task 6 Step 4 test `test_all_mappings_load` is written after the step 2-3 re-run (the 20% bound cannot hold on these step-1 keys; the reports state why). Cost if wrong: none; the test lands with the final keys.
- Task 6 step 1: complete (mapping round 0 + fix round 1). agent=mx-feature×6 fix-rounds=1 gates-first-pass=n/a (oracle data; load_mapping exit 0 after fix)
