# Phase 5: attachments and the CP-4 draft mode Implementation Plan

**Status:** draft 2026-10-31 on `claude/context-plan-build` (28ad7934); not started. Phase row:
`docs/superpowers/plans/2026-10-31-context-file-consumption.md:329`; questions and rulings:
`work/context-plan/reviews/phases-2-8-questions.md:77-88`; user ruling B7 (`docs/rulings/2026-10-31-context-plan.md:27-29`).
Item 4 of the questions (CP-DR `research_questions`) is dropped: superseded by Part B O7.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** (1) A CP-0 review for a pack whose context declares an attachment (`portfolio_workbook`, `prior_case`,
`management_bridge`) or legal documents (`executed`, `draft`) that the pack does not hold is refused unless it
carries a `source` gap naming what is missing. (2) With `legal_documents: draft`, CP-0 may classify a source
`draft` and CP-4 may cite it, with a fixed draft limitation on the CP-4 module. A pack without a `context` source
behaves exactly as today.

**Architecture:** `context_facts(pack)` (`context.py:733`) gives `RunContext.attachments` (`context.py:222-226`).
Declared-but-absent is a CP-0 `_PRECHECKS` row (`owner_workflow.py:597-599`, the hook
`_gate` runs at submit and in replay, `:800-818`) over the filled `ReadinessReview`, in a new module
`owners/cp0_attachments.py` shaped like `owners/cp4.py:135-149` (bounded `json_object` parse, model validate, a
bad shape gives no issue here because the step validator refuses it). Draft authority is two `src/deploy_vii`
edits: `readiness.py` admits the value (on `SourceAssessment.authority` only, H1) for a draft context only; `cp4_legal.py` counts it as citable and
states the limitation.

## Global Constraints

- No stub or fake value standing in for real behaviour; no catch-all that hides a failure (a `ContextRefused`
  becomes an explicit issue line, never `None`); no network call; no key read.
- `src/deploy_vii`: only `readiness.py` and `cp4_legal.py` (B7). Each gets a D12 `post_import_patches` entry in
  `docs/reuse/manifest.json` (array shape as the `cp4_legal.py` entries at `:1345-1362`): `project_commit` is the
  code commit, `sha256` the file's hash there (`git show <commit>:<path> | shasum -a 256`), landed in the commit
  after the code commit. Review: `mx-adversary` on both diffs (B7 names D12 and the adversary).
  Not edited (no ruling): `methods/cp4.md:15,119`, `live/prompts.py:547`, `live/context.py:33,128` (see Q1).
- A pack without a `context` source, or with `legal_documents: none`/all attachments `false`, behaves exactly as
  today: every frozen case, `PINS.json` entry and oracle stays green and unchanged.
- Context figures need no label here (no figure is read). The draft limitation is Python's fixed text, not model text.
- Reports end `Not verified:` and list table, row and field changes (R7): this phase changes CP-0 T3 `authority`
  values (new `draft`), CP-4 T4.2 col 3 and T4D.1 cols 2-3 for a draft source, and CP-4 `limitations`, context packs only.
- Tests: `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest <paths> -q`.
  Gates on changed files: `ruff check`, `ruff format --check`, `mypy`; full suite once before hand-off (B3).

## Overlap with Part B (read at HEAD 28ad7934)

- `owner_workflow.py` (Part B O1 is editing it; the worktree copy already adds CP-6 imports, `OwnerSpec`, qualification,
  probe and entry-validator rows): this phase touches two places only: the import block (`:101-`, one name) and the
  `_PRECHECKS` dict (`:597-599`, one row `"CP-0": cp0_attachments.precheck`). O1's plan
  (`2026-10-31-part-b-o1.md`) never names `_PRECHECKS`; the comment at `:594-596` says module tasks add their rows.
  Build Task 3 after O1's branch lands, or rebase on it; the conflict is limited to adjacent lines. `_gate`
  (`:800-818`) is unchanged by this phase and must stay unchanged by O1 (check at rebase).
- O7 edits `owner_workflow.py`, `owners/cpdr.py`, `tools/source.py`, `docs/reuse/manifest.json` (CP-DR rows only):
  the manifest is an append-only array; add this phase's entries after O7's.
- O6 (prompts) reads `methods/cp4.md`; this phase leaves it unchanged. No file overlap with O2/O3/O4.

## Task 0: the oracle `cases/context-attachments-owner/`

Prepared by a **preparer** who is not the builder of Tasks 1-4, reviewed by an independent `mx-precise`, frozen and
pinned before Task 1: `cases/pins.py` PATTERNS (`cases/pins.py:20-30`) do not cover `context-*.json`, so each context file's sha256 is recorded in the case `manifest.json` `frozen_inputs` and a test re-hashes it (M2); before
Task 1. Layout as `cases/cp4-owner/`: `manifest.json`, `submissions.json`, `expected.json`, `builder/build.py` (stdlib
only), plus context files `context-*.json` saved in the form's layout (as `cases/context/primary-full.json`). The
preparer runs the table, claim and render validators and a scratch double rebuild and reports exit codes.

**Run and upstream.** Run `ctxatt-*`, issuer `northbridge-synthetic`, pathway `credit_snapshot`, case kind `synthetic`, as-of 2026-01-10.
Packs are built through `prepare` with `Run(requested_modules=("CP-4",))` and a context repeating the pathway;
`preparation_request` is not used (the `credit_snapshot` preset is CP-0, CP-1, CP-MODEL, CP-1A, CP-2, CP-4, ... `contracts.py:49-51`,
and the walk is sequential, so a preset run would need CP-1A and CP-2 inputs this case does not freeze). Upstream: the CP-4 owner case's frozen financial pack and legal
sources (`cases/cp4-owner/manifest.json` `frozen_inputs`, no source bytes edited), plus the `context` source. Each
context repeats `run.as_of`, issuer and pathway or `context_facts` refuses (`context.py:756-769`). Expected values
come from the rulings below, never from the code under test. Each expected line is tagged with its path: `P` = the
`submit_review` precheck refusal (`owner_workflow` `_gate`, first), `V` = `validate_review` (reached only when the precheck passes),
`M` = module output. `draft-wrong-context` is refused on path `P` first only if the declared-attachment rules fire; with no
other defect the refusal is `V`, and the case states which.

| Case | Context `attachments` | Pack holds | CP-0 review | Expected |
|---|---|---|---|---|
| `abs-refused` | `portfolio_workbook`, `prior_case`, `management_bridge` all true; legal `executed` | financial + legal (executed) + context; no `portfolio`, `prior_case`, `bridge` | no gaps | precheck issues, exactly three, in field order: `attachments.portfolio_workbook: source 'portfolio' is declared but not in the pack; add a source gap naming it`, then `prior_case`, then `bridge` (id and field swapped); no journal step |
| `abs-gap-ok` | as above | as above | three `kind: "source"` gaps whose descriptions name `portfolio`, `prior_case`, `bridge` | no precheck issue; review settles; T3 and gaps as the review states |
| `abs-present` | `management_bridge` true | `bridge` source ready | no gap | no issue |
| `abs-unready` | `management_bridge` true | `bridge` present with status `missing` | no gap | issue naming `bridge` (a source that is not ready is absent) |
| `none-declared` (guard) | all false, `none` | financial + legal | no gaps | no issue (equals today) |
| `legal-exec-missing` | `executed` | financial only | no source assessed `executed` or `filed`, no gap | issue `attachments.legal_documents: 'executed' documents are declared but no source is assessed executed or filed; add a source gap naming legal_documents`; with a `source` gap whose description contains `legal_documents` -> none |
| `draft-ok` | `draft` | financial + the legal source (draft) | legal source assessed authority `draft`; CP-4 documents row cites it | CP-0 T3 authority `draft`; CP-4 admitted; module `limitations` contain `DRAFT_LIMITATION` (text below) once; T4D.1 row: authority `draft`, eligible `Yes` |
| `draft-wrong-context` | `executed` (and a second case: no context source) | legal source | authority `draft`; a `source` gap naming `legal_documents` (so the precheck's executed rule passes and path `V` is reached) | `validate_review` issue `Draft authority needs a context that declares draft legal documents: <source_id>`; for no context the same line |
| `draft-cited-other` | `draft` | an `issuer`-authority source | CP-4 row quotes it | refused as today: `<id> is not an executed, filed or draft source ...` is **not** used; the existing text `is not an executed or filed source (CP-0 authority issuer, ...)` stays (frozen wording, Q2) |
| `draft-uncited` | `draft` | draft source | CP-4 cites only executed/filed ones | limitation still present (eligibility, not citation, triggers it) |
| `mismatch` | context `run.as_of` 2026-01-11 | | | precheck issue `Context refused: run.as_of: context has '2026-01-11' but the run has '2026-01-10'` |

`DRAFT_LIMITATION` (fixed, the preparer writes it in `expected.json`, the reviewer approves wording): `Legal
documents in this run are drafts, not executed or filed instruments; covenant terms may change before signing.`

Pins that change: none (`cases/cp4-owner` and every other pin untouched). New pins: this case's four files and builder.
`cases/pins.py:20-30` PATTERNS do not match `context-*.json` (M2): the case `manifest.json` records each context file's sha256 under
`frozen_inputs` (as `cases/cp4-owner/manifest.json`), and a test re-hashes every file against it.

## Task 1: draft authority in CP-0 (`src/deploy_vii/readiness.py`; sensitive; `mx-adversary`)

**Files:** modify `src/deploy_vii/readiness.py`; test `tests/test_readiness_draft.py`; D12 entry in `docs/reuse/manifest.json`.
Depends on Task 0.

- [ ] **RED** (fail today: `draft` is not an `Authority`, `readiness.py:28-30`): with the Task 0 packs (`draft-ok`,
  `draft-wrong-context`, no-context pack): (a) `validate_review` on `draft-ok` returns `()`; (b) on a context with
  `legal_documents: executed` returns exactly `("Draft authority needs a context that declares draft legal documents: <id>",)`;
  (c) a pack with no `context` source: same line; (d) a pack whose context fails `context_facts` (`mismatch`): the
  line `Draft authority refused, context invalid: <first problem>` (no exception escapes, no silent pass);
  (e) a review with no `draft` assessment never calls `context_facts` (monkeypatch it to raise: still `()`), so every
  existing pack validates as today; (f) `build_readiness` T3 authority fact text is `draft` (`readiness.py:494`); (g) H1: a CP-1A `source_class: "draft"` is still refused and the `SourceJudgment` authority values are unchanged; (h) L1: a `draft` assessment of `context` is refused. Guards (pass today, must stay): (e) and the second half of (g).
- [ ] **Implement:** leave `Authority` (`:28-30`) unchanged (H1: it also types CP-1A `SourceUse.source_class`, `business_context.py:53,141`, and the live `SourceJudgment`, `live/submission.py:121,163`) and set `SourceAssessment.authority: Authority | Literal["draft"]`; in `validate_review`'s source loop (`:356-376`) collect
  `draft = [a.source_id for a in review.sources if a.authority == "draft"]`; if any, import `context_facts`/`ContextRefused`
  lazily inside the function (layering precedent: `distressed_figures.py:62`, `report_view.py:1888`), read
  `context_facts(pack)` once, and append the one issue per draft source unless `legal_documents == "draft"`.
  The `unknown`-authority rule at `:367` is unchanged; `draft` still needs entity and period or a limitation. Also append an issue when a `draft` assessment is for source id `context`
  (`Draft authority cannot classify the context source`; L1: else `cp4_legal.py:229-234` would make the context file citable).
  `executed` on `context` predates this phase and goes to the user.
- [ ] Run `tests/test_readiness_draft.py tests/test_readiness_linear.py tests/test_source_workflow.py -q`; gates.
- [ ] Commit `feat(vii): CP-0 draft authority, admitted only for a draft context (B7)`; then the D12 commit
  `docs(reuse): D12 record for readiness.py draft authority`.

## Task 2: CP-4 cites draft sources and states the limitation (`src/deploy_vii/cp4_legal.py`; sensitive; `mx-adversary`)

**Files:** modify `src/deploy_vii/cp4_legal.py`; test `tests/test_cp4_draft.py`; D12 entry. Depends on Task 1.

- [ ] **RED** (each fails today): using Task 0 `draft-ok`: (a) `cp4_upstream` (`:216-259`) lists the draft source in
  `legal_sources`; (b) `validate_covenant_interpretation` (`:621`) accepts a covenant quoting it, and `_row_issues`
  (`:467-509`) still refuses (second half is a guard) a quote of an `issuer`-authority source with the frozen text at `:476-478`;
  (c) `covenant_interpretation` (`:1429`) `limitations` contain `DRAFT_LIMITATION` exactly once, also when no
  row cites the draft source (`draft-uncited`); (d, a guard) with only executed/filed sources the module hash equals the frozen
  `cases/cp4-owner` module (no limitation added); (e) T4D.1 (`:1209-1222`) row for the draft source reads authority `draft`, eligible `Yes`.
- [ ] **Implement:** `LEGAL_AUTHORITIES = frozenset({"executed","filed","draft"})` (`:89`; a draft source can exist in
  the CP-0 head only when Task 1 admitted it, so cp4_legal needs no context read); constant `DRAFT_LIMITATION`; after the
  gap limitations (`:1442`) append it when any `upstream.legal_sources` entry has `upstream.authority == "draft"`.
  `dict.fromkeys` at `:1476` dedupes.
- [ ] Run `tests/test_cp4_draft.py tests/test_method_cp4.py tests/test_owner_cp4.py tests/test_connect_cp4.py tests/test_probe_cp4.py -q`; gates.
- [ ] Commit `feat(vii): CP-4 cites draft sources and states the draft limitation (B7)`; then the D12 commit.

## Task 3: the CP-0 attachments precheck (sensitive: ordering/state gate; `mx-adversary`)

**Files:** create `src/deploy_workflow/owners/cp0_attachments.py`; modify `src/deploy_workflow/owner_workflow.py`
(import + `_PRECHECKS` row, see Overlap); test `tests/test_owner_cp0_attachments.py`. Depends on Task 0 (not on 1-2).

**Behaviour.** `precheck(store, binding, stored) -> tuple[str, ...]`: parse as `owners/cp4.py:135-149` (non-object or
schema misfit gives `()`); `ctx = context_facts(store.pack())` (`_FrozenExecution.pack()` is the frozen pack, `_gate` `:812`);
`ContextRefused` gives `("Context refused: " + problem, ...)`; `None` gives `()`. Fixed ids: `ATTACHMENT_IDS =
{"portfolio_workbook": "portfolio", "prior_case": "prior_case", "management_bridge": "bridge"}` (`inputs/portfolio.py:604`,
`owners/cp8.py:74`, `owners/cp1d.py:79`). For each declared field, in that order: absent when no pack source has the id with
status `ready`; then an issue unless the review has a gap with `kind == "source"` whose `description` matches the regex `(?<![A-Za-z0-9_])<id>(?![A-Za-z0-9_])` (L5). Legal: `executed` needs a ready source assessed `executed` or `filed`; `draft` needs one assessed `draft`
(a missing one needs a `source` gap whose description contains `legal_documents`); `none` imposes nothing. Issue texts as
the Task 0 table. Bounded: at most 4 issues; no loop over the review longer than its `gaps`/`sources` tuples.

- [ ] **RED** (fail today: CP-0 has no `_PRECHECKS` row, so every review passes): the ten Task 0 cases through
  `owner_workflow` `submit_review` for `abs-refused`, `abs-gap-ok`, `legal-exec-missing`, `mismatch` (the refusal writes no
  journal step and consumes no attempt, `owner_workflow.py:1248`); plus unit tests of `precheck` for `abs-present`,
  `abs-unready`, `none-declared`; and (d) the verifier replay recomputes the same issues: a receipt of an `abs-gap-ok`
  run verifies, and tampering the stored review to drop a gap fails verification; (L3) with `cp0_attachments.precheck`
  monkeypatched to return `()` during verification, the receipt of a run whose review was refused-then-edited, or one
  built without the gap, fails verification (the verifier must run the gate itself).
  Property test (hypothesis): for any subset of declared attachments and any set of ready sources, the number of issues equals
  declared-and-absent-and-ungapped fields.
- [ ] **Implement** as above. A gap naming an id that the pack does hold is allowed (no issue; not this gate's business).
- [ ] Run `tests/test_owner_cp0_attachments.py tests/test_owner_workflow*.py tests/test_host_h1.py -q`; gates.
- [ ] Commit `feat(owner): CP-0 refuses a review that ignores a declared but absent attachment`.

## Task 4: draft run reaches CP-4 end to end

**Files:** test `tests/test_owner_cp4_draft_run.py` (helper from `tests/cp4_runs.py`). Depends on Tasks 1-3.

- [ ] **RED:** a primary-style run on `draft-ok` (context `primary-full` shape with `legal_documents: draft`): CP-0 review with
  the draft assessment settles, CP-1 settles, CP-4 submission quoting the draft source settles; the CP-4 head's `limitations`
  contain `DRAFT_LIMITATION`; `write_receipt` then `verify_owner_run_receipt` exit clean. Same run with the context edited to
  `executed` after preparation: the pack is frozen, so `context_facts` reads the frozen bytes and the run is unchanged
  (the live file is never read, `context.py:736-737`).
- [ ] Run the test, then `tests/test_owner_cp4.py tests/test_connect_cp4.py -q`; gates. No source change expected beyond Tasks 1-3; a
  failure here reopens the task that owns the cause.
- [ ] Commit `test(owner): a draft-document run reaches CP-4 with the draft limitation`.

## Task 5: regression and hand-off

- [ ] `python3 -I cases/pins.py --check` exit 0; `tests/test_method_cp4.py` and every `cases/*-owner` test unchanged and green; the full suite once (B3).
- [ ] Report lists R7 changes above and ends `Not verified:`.

## Done-when as tests

- "A primary run with draft documents reaches CP-4 with a 'draft' limitation": Task 4 and Task 2(c).
- "A declared but absent source is a CP-0 gap": Task 3 `abs-refused` / `abs-gap-ok` / `abs-unready` / `legal-exec-missing`.
- "Draft admitted only when the context's `legal_documents` is `draft`" (B7): Task 1(b)(c)(d).
- Limit (Q1 ruling): draft mode is proven on the owner path only; the live CP-4 prompt and method are unchanged, so a live model run cannot cite draft sources.
- "No context, same behaviour": Task 1(e), Task 2(d), Task 3 `none-declared`, Task 5 pins and frozen cases.

## Ruled decisions (no open questions; `work/context-plan/reviews/phase-5-plan-review.md`)

- **Ruled: Q1 stays unchanged and goes to the user.** `methods/cp4.md:15,119`, `live/prompts.py:547` and `live/context.py:33` keep
  "executed or filed"; B7 does not cover them and B9 names Phases 4, 6, 8. Live-run limit: a live CP-4 model is not told about
  draft sources and so cannot cite them; draft mode works on the owner path only (fails closed). `live/context.py:128` follows
  `legal_sources`, so the CONTEXT block lists draft sources automatically.
- **Ruled: Q2** keep the error wording at `cp4_legal.py:476-478` (frozen texts).
- **Ruled: Q3 stays unchanged and goes to the user.** No CP-3 confidence cap; the CP-4 limitation travels in the module's `limitations`.
- **Ruled: Q4** a draft source beside executed ones is allowed; the limitation applies to the whole module (Task 2(c)).
- **Ruled: Q5** a `source` gap names the missing id in its description, matched by `(?<![A-Za-z0-9_])<id>(?![A-Za-z0-9_])`; no new gap field.
- **Ruled (review H1, M1, M2, L1-L6)** applied above: `Authority` unchanged; packs via `prepare`; context hashes in the manifest;
  `context` draft refusal; path tags; replay probe; guards marked; exact regex; citations corrected. `executed` on the `context` source goes to the user.
