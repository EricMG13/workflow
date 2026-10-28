# CP-DR Stage 1 report

- Branch `claude/cpdr-stage1`, cut from the lane tip `f2cd61f`. That tip contains 4822066 (the brief), e8ee084 and 70ec120. My original worktree `agent-a3c578c73e0bfdae5` had been removed by the time the controller authorised the fast-forward. I therefore created a new worktree at `.claude/worktrees/cpdr-stage1` from `f2cd61f`, which reaches the same state the authorised fast-forward would have.
- Commit: see `git log -1` on the branch (SHA is in the returned report).
- Files:
  - `src/deploy_workflow/owners/__init__.py` (empty)
  - `src/deploy_workflow/owners/cpdr.py`
  - `tests/test_method_cpdr.py`
  - this report

## What Stage 1 provides (pure, no I/O)

- **Submission schema:** `ResearchQuestion`, `GapResearch` and `ResearchSubmission`, exactly as in the lease's Public API.
- **Agenda:** `parse_agenda(facts)` turns CP-0 T5 facts into `tuple[AgendaGap, ...]` (Method 1).
  - Gap kind/severity, description, named consumers and remediation are parsed by the lease rule.
  - `T5.review.gaps` gives the empty agenda.
  - No T5 agenda fact, both kinds at once, or an unexpected T5 fact raises `ValueError`.
- **Validation:** `validate_research(*, submission, agenda, sources)` applies content rules 1-7. It calls `readiness.citation_issues` for rule 6 and de-duplicates with `dict.fromkeys`.
- **Bookkeeping:** `bookkeeping(*, submission)` gives integer counts, statuses and Decimal shares (4 dp, ROUND_HALF_UP). With no question the share is `None`.
- **Composition:** `compose(CpdrInputs)` returns `CpdrResult`:
  - facts behind every cell, built as product `contracts.Fact`;
  - TDR.1-TDR.3 as product `ReportTable`;
  - claims as product `Claim`;
  - own limitations;
  - the consumption fact list.

## Input fields

| Field | Type | Stage 2 source |
|---|---|---|
| `CpdrInputs.agenda` | `tuple[AgendaGap, ...]` | CP-0 head T5 facts (`T5.<gap_id>.gap` or `T5.review.gaps`); `manifest.upstream_facts_read`; `cpdr_upstream(store, attempt)` |
| `CpdrInputs.submission` | `ResearchSubmission` | judgment (the analyst's `research` step payload) |
| `CpdrInputs.as_of` | `date` | `Run.as_of` (manifest `run.as_of`, 2026-01-10); fact period |
| `validate_research(sources=...)` | `tuple[Source, ...]` | the ready prepared pack (`manifest.sources`) |

## Tests

`PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cpdr.py` gave **27 passed in 0.24 s**. I watched it fail first (ModuleNotFoundError) before implementing.

## Gates

| Gate | First run | Rerun |
|---|---|---|
| `ruff check` (owners + test) | 0 | 0 |
| `ruff format --check` | 1 (two lines in cpdr.py) | 0 after `ruff format` |
| `MYPYPATH=src mypy --strict` cpdr.py | 1 (list invariance annotation) | 0 |

## Oracle sections covered

Each item compares against `expected.json`:

- **`cp0_upstream` and `cp0_upstream_empty_agenda`:** agenda parse, cross-checked against `manifest.view_tree_draft`.
- **`cases.{partial,unresolved,empty_agenda}`:**
  - `bookkeeping`;
  - every fact, as product `Fact` objects in order;
  - tables: ids, titles, row headers, row order, column fields, and every cell's fact id, state and `shown` (spelled by the product's `report_view.fact_spelling`, with G# bound to G1), plus value class, unit and amount/text;
  - `contracts.validate_tables`;
  - claims: id, text, citations, `spelled` via `prose.tokenize` with `fact_spelling`, and `prose.issues` empty;
  - `own_limitations`;
  - `consumption_facts`.
- **`fixtures.*`:** payloads are the partial questions Q1-Q3 as build.py:741-742 assembles them.
- **`refusals.*` (all 18):** the validator part of `step_issues`. RULES-prefixed issues are filtered out; they are Stage 2.
- **`blocked.attempt_0/1`:** issues.

## Left to Stage 2/4

- **RULES (tool-use):** the absence issue in `searched_source_not_in_pack` and `searched_source_not_searched`, and the unread-page issue in `cited_page_not_read` and `citation_outside_pack`. For the two classes that are pure RULES, the test asserts the validator returns `()`.
- **Store, attempt and seam work:**
  - `settled_limitations` and `inherited_limitations` (execution.py:345-366, 441-457);
  - `module_status`;
  - the blocked module status, attempt consumption and the rejected result;
  - `attempt_inputs`;
  - `cpdr_upstream`, `view` and `context_block`, `probe`, `submit`, `cpdr_reader`, and `STEP_IDS`/`SCHEMAS`/`QUALIFICATION`.
- **Other sections:** `tool_use`/`tool_calls`, `rendering`, `tamper`, `consumption` (OPEN) and the rails.

## Engine/oracle disagreements

None. `readiness.citation_issues` produces the pinned strings for `quote_not_verbatim`, `citation_outside_pack` and blocked attempt 0 exactly.

## Choices the oracle does not pin (for the controller)

1. **`bookkeeping` signature.** It is `bookkeeping(*, submission)`, not the lease's `(*, submission, upstream)`. The counts read the submission only, and `fixture_two_gaps` counts a gap (`second-gap`) that is in no agenda. Agenda data enters through `compose`.
2. **Validator issue order.** Rules 3-7 run per question: all checks for one question, then the next. This follows the builder's reference `oracle_issues`. The lease's numbered list could also be read as rule-by-rule across all questions. No pinned tuple tells the two readings apart.
3. **Unpinned table details.**
   - TDR.3 column labels are the field with `_` replaced by a space.
   - TDR.1 and TDR.2 column labels follow `docs/methods-drafts/cpdr.md`.
   - Row labels equal row ids, and `row_kind` is the default `row` (TDR.3 `total` is not marked `row_kind="total"`).
4. **Validator inputs.** `validate_research` takes `agenda` and `sources`, where the lease names `upstream` and `pack`. Stage 2 adapts.

## Confidence-review findings

- **Mutation probe.** I made one-at-a-time edits to cpdr.py and restored from a backup after each:

  | Edit | Result |
  |---|---|
  | rounding mode changed | killed |
  | evidence de-duplication removed | killed |
  | status rule changed | killed |
  | issue truncation to the first issue | survived |
  | agenda parse `rfind("; affects ")` → `find("; ")` | survived |

  Both survivors are oracle-limited. No pinned tuple has two content issues, and no pinned gap description contains "; ". I did not invent expected values to cover them.
- **`compose` assumes a validated submission.** It raises on a gap outside the agenda, an answered question without an answer, or a not_found question without a limitation. A duplicated gap would give duplicate fact ids; `validate_tables` in Stage 2 would refuse them. There are no catch-alls.
- **No stub values.** Missing stays `missing` and not-applicable stays `not_applicable`; neither is ever 0.

## Rewrite-tournament (no-argument mode)

I ran it inline on `validate_research`/`_question_issues` and `compose`/`_Builder`. The impact set is the test file only (a new module). Incumbent holds:

- the two passes in rule 1-2 are required by the order;
- sizes are tiny, so speed and memory are moot;
- no shorter version keeps the per-column fact order.

## Ledger

AGENTS.md asks for a line in `work/<lane>/ledger.md` after each run. The brief limits my writable files, so I did not write it. Line for the controller:

`2026-10-28 cpdr-stage1 pytest tests/test_method_cpdr.py exit 0, 27 passed 0 failed, agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n`

Not verified:
- RULES/tool use, store and attempt behaviour, settled and inherited limitations, module status, blocked status, rendering and tamper (Stages 2-4).
- The two surviving mutants (multi-issue order; a "; " inside a gap description).
- Empty-agenda CP-0 facts are taken from the oracle's pinned text; I did not run `build_readiness`.
- Fixture payloads are re-assembled from the partial literal per build.py; they are not stored in submissions.json.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n

## Fix round 1 (mx-adversary CHANGES REQUIRED on 59aea17)

I wrote the tests first and watched them fail (36 failed, 8 passed) before changing any code.

1. **Surviving mutants.** I added lease-literal tests, each labelled `# lease-literal: <line>`. The expected strings come verbatim from the lease (:46, :47, :112, :114, :115, :117). The payloads are the oracle's literal questions with one stated edit each. The new tests cover:
   - accepted gaps with 1 and with 4 questions;
   - an answered question with no category;
   - a not_found question carrying a valid citation;
   - several content issues on one question, in order: rule 4, then the digit rule, then prohibited words;
   - a digit, and then a prohibited word, in the question text;
   - each prohibited word in mixed case;
   - a pack source that is not ready (status `missing`);
   - a gap description containing "; ", with two consumers;
   - the HALF_UP tie 1/32 = 0.0313, over 8 gaps with 4 questions each.
2. **Empty consumers.** `named_consumers` is now `()` when "affects ; " is empty. Tested.
3. **Strict facts.** `strict=False` is removed; every oracle fact validates strict.
4. **Signatures.**
   - `validate_research(*, submission, upstream, pack)`, with semantics unchanged.
   - `bookkeeping(*, submission)` is kept pending LEAD's ruling.
5. **compose fails closed.** It raises when an agenda gap is missing from the submission, when a submitted gap is outside the agenda, and when a gap is repeated. TDR.1/TDR.2 emission and the empty-agenda line are now decided from the agenda. A test covers each of the three refusals.

**Test.** 45 passed in 0.24 s.

**Gates.** All exit 0 after one `ruff format` of the test file plus one ISC004 rewrite:
- ruff check
- ruff format --check
- mypy --strict

**Mutation probe.** I ran `scratchpad/cpdr/mutate_r1.py`, a copy of `mutate.py`. The `ready_filter_removed` anchor is updated for the `sources` → `pack` rename, and three mutants are added: empty consumers, compose missing gap, compose extra gap. All 14 mutants are killed. A manual mutant that removes the compose repeat check is also killed.

Not verified:
- RULES/tool use, store and attempt behaviour, settled and inherited limitations, module status, blocked status, rendering and tamper (Stages 2-4).
- The lease-literal cases rest on my reading of lease lines :46, :47 and :112-:117. The description-with-"; " and empty-consumer cases also rest on the T5 text form at readiness.py:500. None of these values is in expected.json.

`2026-10-28 cpdr-stage1-fix1 pytest tests/test_method_cpdr.py exit 0, 45 passed 0 failed, agent=general-purpose(opus) fix-rounds=1 gates-first-pass=n`
