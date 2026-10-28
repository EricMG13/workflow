# CP-DR (Deep research, LOCAL) owner lease — FROZEN by LEAD 2026-10-28 (draft rev 4)

Amended by LEAD 2026-10-28 (rulings round 10 item 5; H1 review-adversary open point 1). D-B's scope "the whole ready pack" becomes "every source the prepared pack holds; one that is not ready answers `unavailable`, never its bytes". This is one convention for every fixed owner row. No frozen CP-DR pack holds a source that is not ready, so nothing moves.

Re-pinned by LEAD 2026-10-28 in the serialised `methodology.json` change (branch `lead/methodology-serialised`; `work/lead/methodology-serialised/review.md` COMMIT): `methodology.json` 348fbc4b… → 1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6 (CP-L10 required + CP-1 and TL10.5; CP-1C T1C.1-T1C.8; CP-1D drops T1E.*; CP-2A drops T5.*); two scratch rebuilds identical. builder 6dc0efbb… → 591da654cfe1eb0e932bffa3b48b7dc362d9d1f3180821bd838e3bdd0f99aae5; manifest c9b3734e… → 44862ca3166a29f7d8ff44e7c1073bbdfa2229201c46d83586a262f5de192066; expected unchanged; submissions unchanged. Pins elsewhere in this file are superseded where they differ.

Frozen after `review-precise-3.md` (FREEZE). Pins: manifest c9b3734e8a426ba60d6f4857aa4abe01ad690a9e35f9ae949ce917fc9169cba7, submissions 4ffb322a4d640bc6208250cfd0697cef389b8d0843f6071340247e31b478b1af, expected 1a3d266d185c7230f36ed31651ce36b58528dcf5ee227a63364dd63ecbe84bab, builder 11fc8db61d68cfe768e42fc2643042b1a5e327ee17d86fa3d652aa2375331ac3. `methods-cpdr-draft.md` is committed as `docs/methods-drafts/cpdr.md`; the build moves it to `src/deploy_vii/methods/cpdr.md`.

LEAD notes at freeze: (1) issue order: the product sorts unread-page issues; sorting absence issues is this core's own rule (as :111 states); where :97 or the oracle's `refusal_note` attribute both sorts to `ToolRules.issues`, read it that way. (2) Two known re-pins, each landing with the change that causes it and amending this header: the builder's `methodology.json` pin (the serialised methodology change for CP-L10 D4 and CP-1C D8; expected and submissions stay byte-identical, the manifest changes only in that pin) and the acceptance 7 render pin, which records today's override-slice wording and is re-derived once the 0d override-wording fix and the call-band fix land (`docs/QUEUE.md`).

Re-pinned by LEAD 2026-10-28 (note 2, render half, discharged): acceptance 7 render pin re-derived after 0d (41a8fdb) and 0d(c) (b4ae187) (`work/lead/cpdr-owner-preparation/repin-0d.md`, scoped check `work/lead/cpos-owner-preparation/repin-0d-review.md`, fix `repin-0d-fix1.md`). Pins now: manifest c9b3734e8a426ba60d6f4857aa4abe01ad690a9e35f9ae949ce917fc9169cba7, submissions 4ffb322a4d640bc6208250cfd0697cef389b8d0843f6071340247e31b478b1af, expected 36572c50b663ab4a1f6eaa300d7ee2e668f511cb206dcacfa820105e60b65263, builder 6dc0efbba0ab5433a48bbd24a4ccd4da5dbdcb34c01e58c4692f2b20206cc5fd. Note: 8 blocks `not_run` "Not run: <codes> was not requested in this run.", call band `not_requested`/"Not run", `what-changed` keeps `not_in_pathway` (CP-8 outside the preset closure); acceptance 7 also covers `expected.rendering.navigator_words` (modules outside the run's plan; CP-0 and CP-DR follow their head status, `navigator_words_scope`), and the "Rails-only mode" paragraph (:177) is superseded by `expected.rendering`. The methodology pin remains a known re-pin.

Former draft heading follows.

_CP-DR (Deep research, LOCAL) owner lease: DRAFT rev 4, 2026-10-28 (mx-escalate fix round 3, pre-code)_

Pre-code. Nothing here is frozen. Oracle: `cases/cpdr-owner/` (manifest, submissions, expected, stdlib builder). It writes no code. Every G1 seam is `docs/G1X-OWNER-CORE-PROTOCOL.md` (section 3 as amended 2026-10-28), which supersedes any statement here that differs. Rev 2 applies the LEAD rulings on `report.md` and `review-precise-1.md` (H1, H2, M1-M6, L1-L3); rev 4 those on `review-precise-2.md` (H-1, L-1..L-4, Info). Open points are in the last section.

## Why

CP-DR turns open evidence gaps into either a cited answer from the prepared local sources or an honest "unresolved". Python owns the gap-status bookkeeping (which gaps exist, how many questions each took, how many were answered, status and share); the analyst only writes research questions and, for each, a cited answer or a "not found" with its limitation. No web, provider or credential: the only evidence tools are the pack tools `search_pack` and `read_pages` over the frozen pack. A gap local sources cannot resolve stays open and is shown as unresolved (gap spelling `∅ G#`), never filled, never 0 or N/A. Edges: required CP-0 (`block`); no optional edges; no module lists CP-DR as an input (checked in `methodology.json`). Section: Evidence and Limitations rails only (no Front Page block, no pathway lists CP-DR).

Module kind: `registry.step_chain("CP-DR")` raises "CP-DR has no live step contract". CP-DR is an **owner-only module** (protocol section 1): `entry="owner_core"`, core `src/deploy_workflow/owners/cpdr.py` supplies every section-2 item; no `src/deploy_vii` registry StepChain, **no `precheck`** (every validator issue is a journaled invalid step; ruling Q5).

Scope: gap mode only. The standalone issuer/sector question mode is NOT leased (the Run carries no question field; ruling Q3, deferred).

The r14 CP-DR SKILL.md is not in this repository. Titles and columns of TDR.1-TDR.3 are a LEAD-accepted adaptation (ruling Q7), recorded in `methods-cpdr-draft.md`.

## Prerequisites

1. S1a integrated and G1-X built. Today `SUPPORTED_ANALYTICAL = {CP-0, CP-1}` and `ENTRIES = (cp0_review, model_payload)`.
2. **D-A (admitted, protocol section 3 amended).** An owner-only step may have `sources=True` together with `inputs="module_context"`: CP-DR's one step `research` has the pack tools as evidence and `read_inputs` as the agenda view. No core attribute (`PACK_SOURCE_STEPS` is not used). Its pack scope is the fixed host-side mapping of D-B.
3. **D-B (admitted).** The H1 host task adds the fixed mapping (`_SOURCE_STEPS["CP-DR"]` equivalent and scope = every source the prepared pack holds, a source that is not ready answering `unavailable`; amended by rulings round 10 item 5), never caller-supplied. `host.SourceSession.from_execution` today resolves `_SOURCE_STEPS[module]`, `step_chain(module)` and `declared_sources/readable_sources` from the registry (`host.py:584-587, 662-666`); for CP-DR all three come back empty or raise. `src/deploy_vii` must not import `deploy_workflow`, so the mapping lives in `host.py`.
4. **D-C (admitted, protocol section 6).** `bindings/cpdr.py` (FP block bindings only, rails only, never imports `deploy_workflow`), `bindings/shipped.py` `CPDR` appended to `SHIPPED_MAPS`. No `methodology.json` change (ids already registered). No `report_view.py` change (no block).
5. TOOL-CONTRACT.md matrix row for CP-DR (tool use section).
6. G2 delivery scope (rendering section).

## The run

New run `slice-cpdr-gap`: pathway `credit_snapshot` with `requested_modules = ("CP-DR",)` (the explicit value overrides the preset, `contracts.Run`); `registry.plan` gives `CP-0, CP-DR`. No CP-1 and no CP-MODEL: the run costs one CP-0 settlement. The partial, unresolved and blocked attempts, and **each refusal**, clone that settled store before CP-DR begins (a refusal runs attempt 0 on its own clone). The empty-agenda case has its own CP-0 settlement (below).

Pack: identity and financial sources unchanged from `cases/financial/manifest.json`; business source = `cases/snapshot/manifest.json#business_source.gap` (reduced note: no ownership or transaction content); pack limitation as the snapshot gap case. All sha256 pinned in the manifest and re-verified by the builder.

CP-0 literal = the snapshot gap `readiness_review` with the three-part delta of `manifest.cp0_delta`: consumers become one CP-DR entry copied from the CP-1A entry; the single gap `missing-ownership-transaction` keeps id, kind `scope`, severity `material` and remediation, drops the clause naming CP-1A rows, and names `affected_modules = [CP-DR]`; sources, objective, period and analysis unchanged. The settled gap fact is `T5.missing-ownership-transaction.gap`, text `scope/material: Ownership and transaction content is absent from the business note; affects CP-DR; Supply the ownership and transaction documents`.

**Empty-agenda CP-0 (`submissions.json#cp0_readiness_review_empty_agenda`).** The same review with `gaps = []`. Probed: `validate_review` returns `()`; `build_readiness` emits the single T5 fact `T5.review.gaps` = "No gaps identified by this supplied review" (no `T5.<gap_id>.gap` fact); module limitations and `T8.CP-DR.limits` equal `manifest.upstream_facts_read.{cp0_limitations_empty_agenda, T8.CP-DR.limits_empty_agenda}`.

## Method (Python owns; every number is an integer or a Decimal)

1. **Agenda.** `cpdr_upstream(*, store, attempt)` binds the CP-0 head and parses each `T5.<gap_id>.gap` fact: `kind/severity` = text before the first `": "`; named consumers = between the last `"; affects "` and the next `"; "`; remediation = the rest. `T5.review.gaps` means an empty agenda.
2. **Per gap** (TDR.1 row): `questions` n (1 to 4), `answered` a, `unresolved` n - a, `answered_share` = a / n Decimal quantised to 4 places ROUND_HALF_UP (unit `decimal_fraction`, shown x100 at 1 dp), `status` = Resolved if a = n, Unresolved if a = 0, else Partially resolved.
3. **Totals** (TDR.3 row `total`): gaps total / Resolved / Partially resolved / Unresolved; questions total, answered, unresolved; overall share by the same rule. Units `gaps`, `questions`, `decimal_fraction`; period `as_of` 2026-01-10.
4. **Not found is never filled.** A `not_found` question yields a `missing` answer fact and a `missing` evidence fact (`TDR.2.<qid>.answer`, `.evidence`; `value_class analyst_judgment`; `limitation` = the analyst's), cells spelled `∅ G#`. It counts as unresolved. A known 0 (zero answered) is distinct: the share `0.0%` is a known value.
5. **Empty agenda is a valid settled state (ruling M5).** Zero gaps, zero questions: every `TDR.3.total.*` count is a known 0 (`0 gaps`, `0 questions`); `TDR.3.total.answered_share` is `status not_applicable` (its fact `limitation`: "No research question was submitted, so an answered share has no denominator."), cell `∅ G# n.m.` (state `not_meaningful`), never 0. TDR.1 and TDR.2 have no rows and are not emitted. Own limitation: "No gaps identified by this supplied review; no research question was submitted." The only valid CP-DR submission is `{"gaps": []}`; a non-empty submission is a journaled invalid step (below).
6. **Facts behind every cell (ruling H1).** Every cell of TDR.1-TDR.3 has a fact (`cells.<col>.fact`, id `<table>.<row>.<field>`); the oracle lists all facts. `formula` and `calculation_id` only on calculated facts. Kinds: numeric counts/shares and the `status` text (TDR.1) and `outcome` text (TDR.2) are `calculated`; question, answer and limitation texts are `analyst_judgment` (the answer fact carries the answer's citations); gap, kind/severity, named consumers, description, searched sources and the answered `TDR.2.<qid>.evidence` (the cited locators as text, carrying the answer's citations) are known text with no value class (copied from the CP-0 gap fact or the submission). TDR.3 holds the `total` row only (rev 3, LEAD ruling): a declared `ReportTable` needs one fact per column in every row, so the per-item limitation rows are gone; an unresolved item's limitation lives on the missing `TDR.2.<qid>.answer`/`.evidence` facts and in the module's own limitations ("Unresolved: ..."). The TDR.3 answer column of rev 1 is dropped too: the answer is missing once, in TDR.2.
7. **Claims.** One Python summary claim whose figures are `{TDR.3.total.<k>|<unit>}` references to the module's own facts (empty-agenda variant: questions_total and gaps_total, no share), plus one claim per answered question carrying the analyst's digit-free answer and its citations. Probed with `prose.issues` over the built facts (empty) and `bare_figures` (no hit).
8. **Module status and limitations (ruling L1).** `restricted`. `settled_limitations` = own limitations (base line "Research used the prepared local sources only; nothing outside the pack was searched.", one "Unresolved: <question> <limitation>" per unresolved question, the empty-agenda line when applicable) plus "Synthetic case; not real issuer qualification" (`execution.py:444-447`). `inherited_limitations` = the CP-0 head's limitations, de-duplicated, settled own removed (`execution.py:345-366`). Both pinned per case in `expected.cases.<case>`.

Expected values (all derived in `build.py`):

| Case | Questions | Answered | Unresolved | Share | Gap status |
|---|---|---|---|---|---|
| partial (positive) | 3 | 2 | 1 | 0.6667 shown 66.7% | Partially resolved |
| unresolved (gap) | 2 | 0 | 2 | 0.0000 shown 0.0% (known zero) | Unresolved |
| empty_agenda | 0 | 0 | 0 | not_applicable `∅ G# n.m.`; counts known 0 | no gap row |
| fixture_resolved (composer) | 2 | 2 | 0 | 1.0000 shown 100.0% | Resolved |
| fixture_two_gaps (composer) | 3 | 2 | 1 | 0.6667 shown 66.7%; gaps Resolved 1, Unresolved 1 | per gap |
| blocked | attempts 0 and 1 invalid | | | | module blocked, no tables, no claims |

## Local-source determination (why the cases are honest)

Partial: Q `transactions` and Q `distributions` are answered from financial page:1 and page:3 (verbatim quotes pinned by the builder). Q `owner-identity` is `not_found`: the builder asserts that no prepared page contains "owned by", "Holdings", "Harbour", "shareholder loan" or "distribution policy", and the searches over identity, financial and business surface only unrelated spans (financial page:1 and page:3 dividends paid; financial page:4 "Shareholders equity"; business page:1 title "Business and ownership note"). Unresolved: owner and distribution-policy questions are both `not_found`. All figures in the answers' quotes are source quotes; analyst text is digit-free (builder asserts no `str.isdigit()` character, and no prohibited word, in any literal real text).

## Files

New: `src/deploy_workflow/owners/cpdr.py` (about 300-450 lines); `tests/test_owner_cpdr.py`; `tests/cpdr_runs.py` (`cpdr_closed(case, root)`: pack assembly, literals, tool-call sequence; G2 imports it).
Changed: `owner_workflow.py` (G1-X: `OWNER_SPECS["CP-DR"]`, `_CORES`, `SUPPORTED_ANALYTICAL`, `_QUALIFICATION`, `_PROBES`, `_VIEWS["research"]`), `host.py` (D-B), `bindings/cpdr.py` and `bindings/shipped.py` (D-C), `docs/reuse/manifest.json`, TOOL-CONTRACT.md row.

## Public API

```
owners.cpdr.MODULE_ID = "CP-DR"; STEP_ID = "research"; STEP_IDS = (STEP_ID,); QUALIFICATION
SCHEMAS = {STEP_ID: ResearchSubmission}
class ResearchQuestion(Contract):  question_id: Identifier; text: Text
                                   outcome: Literal["answered","not_found"]
                                   answer: Text | None; category: Literal["Documentary Fact","Management Language","Analyst Interpretation"] | None
                                   citations: tuple[Citation, ...]; searched_sources: tuple[Identifier, ...]; limitation: str | None
class GapResearch(Contract):       gap_id: Identifier; questions: tuple[ResearchQuestion, ...]
class ResearchSubmission(Contract): gaps: tuple[GapResearch, ...]      # empty tuple allowed (empty agenda)
# seams, positional (protocol section 2); no precheck
RULES(text, seen) -> tuple[str, ...]            # tool-use evidence rules (protocol section 2, LEAD amendment 2026-10-28)
probe(store, snapshot, attempt) -> None        # WorkflowError("identity_mismatch") unless attempt and head rebuild exactly
view(historical, attempt) -> tuple[str, str]   # (sha256, body) of the read_inputs view; _VIEWS["research"]
submit(store, ticket_id, step_id, payload, rules) -> Submitted      # rules="journaled": every issue is an invalid step
# internals (keyword arguments only)
cpdr_upstream(*, store, attempt) -> Upstream          # bound CP-0 head, parsed agenda, inherited limitations
bookkeeping(*, submission, upstream) -> Bookkeeping   # pure; ints and Decimal; share None when no question
validate_research(*, submission, upstream, pack) -> tuple[str, ...]   # validator rules 1-7 below (no tool-use evidence)
research_module(*, report, inputs, attempt) -> Module
context_block(*, upstream) -> dict[str, object]       # the exact read_inputs view; view() hashes it
cpdr_reader(store, head) -> CpdrHead                  # the consumer reader (Consumption)
```
Reuse: `readiness.citation_issues(citations, pack.sources)` for verbatim location; `live.tools.unread_citation_issues` and `UNBACKED_ABSENCE` inside `RULES`; `prose` for claim checks. No new arithmetic engine.

## Submission schema (reference and judgment only)

Literal examples: `submissions.json#cpdr.{partial,unresolved,empty_agenda,blocked}`. One `GapResearch` per CP-0 gap, 1 to 4 questions each, `question_id` unique across the submission. `answered`: answer, category and at least one citation, no limitation. `not_found`: no answer, category or citation; a limitation. Every question names `searched_sources` (ready pack sources). Free text is digit-free and carries no prohibited conclusion. Citations are `{source_id, source_sha256, locator, quote}`; `source_sha256` is the prefilled kind `source`.

## Validator rules and RULES (rulings H2, M2, M3; protocol section 2 amendment)

**Which mode checks tool use against `Seen`.** The step has `rules="journaled"`. G1's `ToolRules` path raises for a step that is not a tool-loop step, so the tool-use evidence rules are the core's `RULES(text, seen)`: pure over the payload text and the session's `Seen`, reusing `live/tools.py` `UNBACKED_ABSENCE` (absence backed by a recorded search) and `unread_citation_issues` (cited `page:N` read through `read_pages`), issues in the product's order: absence issues first, then unread-page issues, each sorted (`ToolRules.issues`, tools.py:1216-1219). G1-X calls it in place of `ToolRules().issues` at submit and in the verifier (`_verify_submissions` replay, S1a R3-2). **Dedupe rule (stated once).** The step's `step.issues` is `validate_research` issues followed by `RULES` issues, de-duplicated with `dict.fromkeys` where the journaled rule issues are added to the validator issues (S1a R3-2, `_with_rules`); R4-2's "no dedupe" is the replay of a step with no journaled rules, so the two are consistent. No pinned CP-DR tuple holds a duplicate.

`validate_research` (content rules, in order; each check at most one issue per item):

1. Per submitted gap, in order: `gap_id` not in the CP-0 agenda -> `gap_id is not in the CP-0 agenda: <id>`; `gap_id` already seen -> `gap_id appears twice: <id>` (the first occurrence counts its questions).
2. Per agenda gap, in agenda order: not 1 to 4 questions (absent counts 0) -> `a gap takes 1 to 4 research questions: <id>`.
3. Per question, in submission order: `question_id` already seen -> `question_id appears twice: <id>`.
4. Shape. answered: missing answer, category or citation -> `an answered question needs an answer, a category and at least one citation: <id>`; has a limitation -> `an answered question carries no limitation: <id>`. not_found: has an answer, category or citation -> `a not_found question carries no answer, category or citation: <id>`; no limitation -> `a not_found question states its limitation: <id>`.
5. Searched sources: none -> `searched_sources must name at least one prepared source: <id>`; a source that is not a ready pack source -> `searched source is not a ready prepared source: <id> <source>`.
6. Citations: `readiness.citation_issues` per citation (a source outside the pack gives `Unavailable or changed source: <source>`; a quote not found gives `Quote/locator mismatch: quote not found under <source> <locator> (normalised whitespace, quote marks and dashes): "<quote>"`, the quote shown whole up to 200 characters).
7. Text. **Digit rule:** any character `c` with `c.isdigit()` (Python `str.isdigit()`) in the question `text`, `answer` or `limitation` -> `text must not contain a figure: <id>` (one issue per question; years such as "2025" count, which `prose.bare_figures` does not catch). Prohibited words (case-insensitive substrings "recommend", "refinanc", "covenant", "recovery") in the same fields -> `text carries a prohibited conclusion: <id>`.

`RULES(text, seen)` (tool use; product wording):

a. Absence: for each `not_found` question and each of its `searched_sources` with no recorded `search_pack` covering it (`Seen.searched_source`) -> `Absence claim without a recorded search: <id> not_found for <source>; search_pack that source before claiming it is not found`, sorted. The prefix is the product's `UNBACKED_ABSENCE`; the remainder is the core's wording (the product has no CP-DR line). Answered questions' `searched_sources` are validated for membership only; the absence claim is the not-found.
b. Every cited `page:N` locator of the payload not in `Seen.read`, sorted by (source, locator) -> `Cited page not read through read_pages: <source> <locator>` (`unread_citation_issues`, probed; locators that are not `page:N` are left to validator rule 6).

Order: all of (a), then all of (b), the product's `ToolRules.issues` order (absence then unread). No pinned tuple holds both kinds; the builder's reference validator emits them in this order.

**Membership and one defect.** `RULES` is pure over text and `Seen` and does not know pack membership, so the earlier "membership first, skip" ruling (M2) cannot hold inside it: an out-of-pack citation source or searched source yields its membership issue and its RULES issue. Those two classes are one defect with both consequences: each pins both issues, in this order (the membership issue, then the RULES issue; for `citation_outside_pack` the unread-page issue, for `searched_source_not_in_pack` the absence issue); every other class stays one defect and one issue. RULES stays pure over text and `Seen` (LEAD ruling, rev 2). (Recorded for LEAD: the alternative is a core wrapper that filters non-pack citations before calling `unread_citation_issues`, which G1's `RULES(text, seen)` signature cannot do without the pack.)

The builder carries a stdlib reference implementation of these rules and asserts that every pinned tuple is exactly what it derives from the literal payload and calls; the revision probe compared the `unread_citation_issues` part with the product function over every payload.

## Refusals: journaled invalid steps (`expected.json#refusals`; payloads in `submissions.json#refusal_inputs`)

There is no precheck and no refused-submission disposition for these. Each class is one literal payload (the partial submission with exactly one defect, plus the `calls` it needs) submitted as **attempt 0 of its own clone of the settled CP-0 store**: the step is journaled invalid, the attempt is consumed, the attempt-0 result is `rejected` with limitations equal to the issues, and `step.issues` is the complete tuple below. `_verify_submissions` replays the validator on the historical snapshot and requires `step.issues` to equal the bounded tuple of the dedupe rule above exactly (S1a R3-2). The empty-agenda row runs on the empty-agenda CP-0 clone.

| Class | Defect | Complete `step.issues` |
|---|---|---|
| gap_unaddressed | `{"gaps": []}` | `a gap takes 1 to 4 research questions: missing-ownership-transaction` |
| gap_with_five_questions | five questions `extra-0..4` | the same string |
| unknown_gap | a second gap `invented-gap` (question `invented-owner`) | `gap_id is not in the CP-0 agenda: invented-gap` |
| gap_repeated | the gap copied; its question ids renamed `<id>-repeat` (M1) | `gap_id appears twice: missing-ownership-transaction` |
| question_id_repeated | question 2 renamed `transactions` | `question_id appears twice: transactions` |
| answered_without_citation | citations emptied | `an answered question needs an answer, a category and at least one citation: transactions` |
| not_found_with_answer | answer and category on `owner-identity` | `a not_found question carries no answer, category or citation: owner-identity` |
| not_found_without_limitation | limitation null | `a not_found question states its limitation: owner-identity` |
| answered_with_limitation | limitation on `transactions` | `an answered question carries no limitation: transactions` |
| no_searched_source | `searched_sources = []` | `searched_sources must name at least one prepared source: owner-identity` |
| searched_source_not_in_pack | `["web"]` | `searched source is not a ready prepared source: owner-identity web`; `Absence claim without a recorded search: owner-identity not_found for web; search_pack that source before claiming it is not found` |
| searched_source_not_searched | no business `search_pack` | `Absence claim without a recorded search: owner-identity not_found for business; search_pack that source before claiming it is not found` |
| cited_page_not_read | no `read_pages` of page:3 | `Cited page not read through read_pages: financial page:3` |
| quote_not_verbatim | forged quote under financial page:1 | the full `Quote/locator mismatch ...` string of validator rule 6 with quote "The group completed an acquisition in the third quarter." |
| citation_outside_pack | citation source `web` | `Unavailable or changed source: web`; `Cited page not read through read_pages: web page:1` |
| digit_in_text | answer "Nothing happened in 2025." | `text must not contain a figure: transactions` |
| prohibited_conclusion | limitation "We recommend asking the sponsor." | `text carries a prohibited conclusion: owner-identity` |
| submission_against_empty_agenda | the partial submission against the empty-agenda CP-0 | `gap_id is not in the CP-0 agenda: missing-ownership-transaction` |

`gap_unaddressed` and `gap_with_five_questions` share one issue string (acceptable; the payloads differ).

**Blocked case.** Attempt 0: the forged-quote payload, `step.issues = (<the quote_not_verbatim string>)`; attempt 1 (a new attempt): the figure-in-text payload, `step.issues = ("text must not contain a figure: transactions",)`; the module is `blocked`, no tables, no claims; the receipt verifies and `cpdr_reader` exposes the status only.

**Run-level refusals (G1, not journaled steps).** Any `invoke` of a tool other than `search_pack`/`read_pages` is a refused `not_permitted` receipt; submit without its own `read_inputs` is `not_permitted`; a snapshot change between read and submit is `stale_binding`; `begin` is refused (edge `block`) when CP-0 is blocked or stale.

**Empty agenda.** `{"gaps": []}` against the empty-agenda CP-0 is valid and settles `restricted` (method 5). One `read_inputs`, no search, no read.

## Tamper (acceptance 6; literal recipe in `expected.json#tamper`, ruling M4)

Target: the settled CP-DR result Module of the closed partial run, fact `TDR.1.missing-ownership-transaction.status`, "Partially resolved" -> "Resolved". The status lives only in the result Module (the table cell holds the fact id; the step output holds the submission references). Recipe: copy the store; edit only that fact's text in the Module; serialise as `Execution._store` does and write the blob under the new `Module.content_hash()` R2; write a new snapshot with the CP-DR Attempt and Head `result_sha256` = R2 (status, inputs, commands unchanged; same parent) and rewrite `current`; in the retained receipt set the CP-DR `SettledHead.result_sha256` = R2; set `receipt.snapshot_sha256` and every coordinate that named the old final snapshot (the CP-DR settling `OwnerSubmission.snapshot_after_sha256`, `owner_workflow.py` `_advance` -> `_finish_walk`; the record is retained as `audit/submissions/<content_hash>` by `_retain`) to the new digest; delete `audit/submissions/<old record hash>` and write the edited `OwnerSubmission` as `audit/submissions/<its content_hash>` (`model_dump_json` bytes); rewrite `audit/receipt.sha256` with the forged receipt's `content_hash` (S1a R3-5 and CP-3 A4 pattern). Expect everything upstream of the probe to pass (audit inventory, blob and snapshot hashes, ancestor walk, head equality, calls/reads, journaled-step replay) and `cpdr.probe` to raise `identity_mismatch` because its rebuild reads TDR.1 status "Partially resolved". The test asserts that `_verify_audit` and every check before `_PROBES` pass on the forged copy (as CP-3 A4 (a)), then that `cpdr.probe` raises `identity_mismatch`; asserting `identity_mismatch` alone would not show the probe was reached. An edited step output is caught by the store's blob hash check, not the probe (recorded limitation, S1a R3-5).

## Tool use (TOOL-CONTRACT, D2)

CP-DR is a pack-tool step: `search_pack` and `read_pages` over every source the prepared pack holds, a source that is not ready answering `unavailable` (rulings round 10 item 5; no `extract_statements`; no upstream tools). Matrix row to add: "CP-DR research | exactly the view `owners.cpdr.view(historical, attempt)` registered in `_VIEWS['research']` (gap agenda, source ids and statuses, question limits; no quote, citation or record_json at any depth) | pack search/read over all ready sources". Acceptance: exactly one ok `read_inputs` per attempt before submit; the search and read calls of `submissions.tool_calls.<case>` are ok with `expect_header` / `expect_spans`; `searched_sources` of not-found questions and cited locators are checked against `Seen` by the core's `RULES`. Hit counts follow the documented any-term, case-insensitive substring rule and were compared with `PackTools` headers in the revision probe (all match). A `read_inputs` record counts as tool use only for the view it is; the pack calls are the research tool use.

## Consumption proof (D3): OPEN

No core reads CP-DR. `registry.edge_rule("CP-5","CP-DR") == "restricted"`, but CP-5's review counts as consumption only after a lease extends the CP-5 integrity scope to CP-DR. CP-5 has no owner core yet (S1b after A4). This lease ships `cpdr_reader(store, head)` and pins what a future CP-5 must do (ruling L3): bind the CP-DR head `result_sha256` as an attempt input and cite, in its review, the facts listed per case in `expected.cases.<case>.consumption_facts`: `TDR.1.<gap>.{questions,answered,unresolved,answered_share,status}`, all eight `TDR.3.total.*`, and for each unresolved item the missing `TDR.2.<qid>.answer` fact (its limitation is the unresolved reason). No completion claim covers consumption; do not weaken the rule.

## Rendered sections (D7) and table ids (D8)

Rails only. `bindings/cpdr.py` slots prefixed `cpdr-`: `TDR.1` -> `evidence`, `TDR.2` -> `evidence`, `TDR.3` -> `limitations`. Rendered by G2 `owner_rendering.py` with a new scope entry and sections Evidence and Limitations only.

**Rails-only mode (ruling M6).** No rails-only mode exists; `report_view.build(view, credit_snapshot, SHIPPED_MAPS)` renders the full Front Page for this override slice. Acceptance 7 pins today's product output (`expected.rendering`): call band `outside_pathway`; the 12 block states: `key-findings`, `company-operating-model`, `model-chart-strip`, `capital-structure`, `financials-credit-metrics`, `strengths-weaknesses`, `relative-value`, `company-profile`, `committee-challenge`, `what-changed` are `not_in_pathway` (wording "Not in this Pathway: <CP-x> is not part of Credit Snapshot."); `transaction-summary` and `portfolio-fit` are `absent` ("Absent: No module produces this block yet."). The `not_in_pathway` wording is false for an override slice: a product defect recorded in `docs/QUEUE.md` as its own `report_view` task (test-first). CP-DR does not fix or depend on it; the pin changes only with that task. Probed on a pre-run view; the post-run view of the same slice is not probed.

D8 collision check: `TDR.1`-`TDR.3` appear only in the CP-DR entry of `src/deploy_vii/methodology.json` (builder asserts no other module lists them) and, by `grep -rl "TDR\." src tests docs cases`, in no other file under `src/`, `tests/`, `docs/` besides this oracle. No new registration.

## Acceptance (from `expected.json` only)

1. Positive (`partial`): CP-0 settles restricted with the T5 gap fact; CP-DR settles `restricted` with inputs `prepared-pack, CP-0` hash-equal to the heads plus `research-submission`; tables TDR.1-TDR.3 cell for cell (ids, shown, units, value classes) and **every cell's fact** equal to `cases.partial.facts` (status, text/amount, value class, citations, calculation id, formula only on calculated, limitation on missing); `∅ G#` bound at run time; claims equal (`spelled`); `settled_limitations` and `inherited_limitations` equal; receipt verifies; store bytes unchanged afterwards.
2. Gap (`unresolved`): share `0.0%` known; the TDR.2 answer and evidence facts of both questions missing; gap status Unresolved; module settles restricted.
3. Empty agenda (`empty_agenda`): the empty-agenda CP-0 settles; `{"gaps": []}` is valid; counts known 0, share fact not_applicable with its limitation, cell `∅ G# n.m.`; no TDR.1/TDR.2; limitation pinned.
4. Fixtures: `bookkeeping` over `fixture_resolved` and `fixture_two_gaps` equals `expected.fixtures`.
5. Refusals: each `refusal_inputs` payload, as attempt 0 on its own clone, yields a journaled invalid step whose `step.issues` equals `expected.refusals.<class>.step_issues` exactly; run-level refusals (stale binding, read-before-submit, other tools).
6. Blocked: attempts 0 and 1 invalid with the pinned issues, module blocked, `cpdr_reader` exposes status only.
7. Rendering: the rails are populated with owner CP-DR, and the 12 block states plus call band equal `expected.rendering` (today's product output).
8. Verifier: `cpdr.probe` reruns validation and gets the head back; the tamper recipe refuses with `identity_mismatch` and nothing upstream does.
9. Consumption: recorded OPEN; no test claims it.
10. Claim check: `prose.prose_issues` empty for every expected claim (probed).
11. Gates: ruff check, ruff format --check, mypy strict on changed files.

## Deferred test commands (build-first: not run now; LEAD's final phase)

```
cd "<LEAD worktree>" && PYTHONPATH=src "../../../.venv/bin/python" -m pytest tests/test_owner_cpdr.py -x -q    # heavy lock, one CP-0 settlement plus one empty-agenda CP-0
python3 -I cases/cpdr-owner/builder/build.py && shasum -a 256 cases/cpdr-owner/*.json                         # oracle reproduces byte for byte
```
Plus ruff, `MYPYPATH=src mypy` on changed files, `tests/test_owner_workflow.py` unchanged.

## Rulings and open points (numbering of `report.md`)

1. D-A: admitted without a core attribute (protocol section 3 amended).
2. D-B: admitted (H1 host task, fixed mapping, every held source, not-ready ones `unavailable`; rulings round 10 item 5).
3. Standalone question mode: deferred (empty agenda is a valid settled state, not a free-form question).
4. CP-DR-only run (not `(CP-1A, CP-DR)`).
5. Blocked-case defects journaled vs other refusals in a gate: every validator refusal is a journaled invalid step consuming an attempt; no precheck (applied: H2).
6. Rails-only render with an overridden `requested_modules`: the review checks it (done: no rails-only mode; today's output pinned in acceptance 7, wording defect queued separately; applied: M6).
7. TDR titles/columns: LEAD adaptation, recorded in `methods-cpdr-draft.md`.
8. "1 questions" spelling: cosmetic, accepted.
9. Whether a quote answers its question is analyst judgment; Python checks location and tool use only (`expected.not_verified`).

**Closed in rev 3: TDR.3 shape.** TDR.3 holds the `total` row only (LEAD ruling); `contracts.validate_tables` passes on every table of every case (probe below).

## Probes run (read-only, build-first rule)

`python3 -I cases/cpdr-owner/builder/build.py` twice (identical sha256). Venv python, `PYTHONPATH=src`, scratch copies (`scratchpad/cpdr-rev2/`, `scratchpad/cpdr-rev3/`): `ReadinessReview` + `validate_review` + `build_readiness` for both CP-0 literals (T5 facts, module limitations, `T8.CP-DR.limits` equal the oracle); every fact built as `contracts.Fact` and every cell's `fact_spelling` (with gap id G1) equal to its `shown`; `prose.issues` on every claim of the three cases (empty); `bare_figures` on literal analyst texts (no hit); `readiness.citation_issues` on every citation (none) and on `quote_not_verbatim` / `citation_outside_pack` (equal the pinned strings); `PackTools.search_pack` headers for all three call lists (equal); `report_view.build` on a pre-run view (equals `expected.rendering`); `contracts.validate_tables` over every case's tables with product `Fact`s built from the oracle (zero failures, rev 3). Rev 4 (`scratchpad/cpdr-rev4/`): the same probes rerun on the rebuilt oracle (all equal); the tamper step 5 modelled against `_verify_audit` on a scratch `Execution` store with one retained settling `OwnerSubmission` (the receipt-only rewrite of rev 3 is refused `identity_mismatch`; with the old audit file deleted and the edited record retained under its new hash it passes); the reference validator's RULES order and `page:N` filter checked against `ToolRules.issues` order and `unread_citation_issues` (equal).

Not verified: no product code exists, so no expected value was compared with product output beyond the probes above; the reference validator is the oracle's own; the section-2 seams, host mapping and bindings are design, not built; the tamper recipe follows `owner_workflow.py` and `execution.py` as read, never executed; the empty-agenda CP-DR run and a Module without TDR.1/TDR.2 were not constructed; the rendering pin is a pre-run view; `∅ G#` numbering at run time and "1 questions" follow `display.py` as read.
