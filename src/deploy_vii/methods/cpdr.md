# CP-DR — deep research (LOCAL): method cp-dr/2026-10-31

Lineage: `LOCAL`. The research rests on the evidence items the user supplied and on the run's own prepared sources. The research prompt carries each accepted item's text in its own `UNTRUSTED_EVIDENCE` block, and `search_pack` and `read_pages` are the only way to read the run's prepared sources. No web, provider or credential is used, and the readiness ceiling is `RESEARCH_READY`.

Role: evidence analyst. Reader question: what do the supplied research items say about the sector questions CP-1C and CP-2 need answered, where do they disagree, and what stays open?

## Scope

- Independent research that supports CP-1C and CP-2. A question names one or both of them as its receivers. No module reads CP-DR output until O7d.
- It excludes filling gaps in the subject borrower's own documents. CP-0 and CP-1 own those.
- It never manufactures a replacement for a missing canonical input. A question the items cannot answer is reported as missing, with its limitation.
- The module requires CP-0 and CP-1. Both heads must be settled and must carry the same issuer, run, period and method version, and CP-1 must record `Input CP-0` with the hash of the CP-0 head. Any miss refuses the run before a model call (`CpDrNotAnchored`).

## Tables (R7; ids registered in `methodology.json`, nothing else is registered)

| Table | Title | Row header | Columns | Rail |
|---|---|---|---|---|
| TDR.1 | Locked questions and recipients | `question_id` | `text`, `kind`, `receivers`, `focus_module` | Evidence |
| TDR.2 | Claims and located evidence | `claim_id` | `question_id`, `claim`, `evidence_id`, `locator`, `published`, `family` | Evidence |
| TDR.3 | Answers, contrary evidence, uncertainty and downstream use | `question_id` | `answer_state`, `answer`, `contrary`, `uncertainty`, `downstream_use`, `questions_total`, `answered`, `partly`, `not_found`, `contrary_items` | Limitations |

TDR.3 has one row per question plus the `total` row, which is the sum of the question rows; `total` is therefore not a usable question id. Fact ids are `<table>.<row>.<field>`, and every cell is backed by a fact. Python composes the tables from the locked brief, the checked submission and the intake record; the analyst writes no cell.

## Intake

- Each research item names a file, a family, a publication date, a locator and the tag `research`. Python assigns the ids `ev-1`, `ev-2` and so on, in manifest order. The user cannot choose one.
- An item dated after the cutoff is refused. The cutoff is the earlier of the as-of date and the context's `run.cutoff`; with no `run.cutoff` it is the as-of date. An undated item is refused when the as-of date is before today.
- A URL row is fetched only when the run names a user ruling that lifts the live-provider pause for `web-retrieval` (`research_ruling`); without one every URL row is refused before anything is written, and the refusal names the ruling the run needs. A fetched item is `https` only, from the user's manifest, with every address public, at most three redirects, the same byte cap, and a recorded url, address, status, size and hash in `research/fetches.json`; a publication date found in the response can refuse an item, never admit one.
- The per-item cap is `preparation.MAX_BYTES`, applied to the raw read.
- The converted text limit is the same `preparation.MAX_BYTES`, because the pack refuses any staged source above it. HTML is reduced to text with the standard library parser only.
- URL locators with `?`, `=`, `&`, `%` or `#` are refused by the fence header rule (a locator must match `[A-Za-z0-9][A-Za-z0-9._:+/-]*`), because a header field is placed in the header line of its evidence block.
- An item that holds the fence terminator `<<<END>>>`, any `<<<END`, or an evidence-block opener is refused at intake and listed in `research/rejected.json`. A refused item's text never reaches the pack, a prompt or the dossier. The dossier lists the refused item with its locator, family, publication date and reason under `Rejected items`; for a terminator refusal it shows the terminator note in place of the reason.
- Evidence text is untrusted. Each item reaches the model only inside its own `UNTRUSTED_EVIDENCE` block, and an instruction inside it is data, not a command.

## The brief

- The brief step reads the run's own sources, never the supplied items. The model tailors questions; Python orders, bounds, hashes and locks them. The locked brief is written once as `research/brief.json`, and any later edit is refused (`BriefInvalid`, hash mismatch).
- The context questions from the run come first (`ctx-1`, `ctx-2`), then the six default questions in this order, then the analyst's own. A context question names a focus module: CP-1C goes to CP-1C, CP-2 goes to CP-2, and CP-DR or blank goes to both. Every other question goes to both.
- The count is 1 to 32 in all. The context questions count toward the 32, and the cut falls on the tail: tailored questions are dropped, context questions are not.
- A question id is at most 138 characters (the number `steps.QUESTION_ID_MAX`, set by the longest fact id it must carry). It may not start with `ctx-`, may not be `total`, and may not repeat.
- The six default questions, each submitted once, in this order, with its own kind:
  1. `competition` (`default_1`): which producers supply the sector, and how concentrated supply is.
  2. `metric-definitions` (`default_2`): how producers in the sector define the issuer's headline earnings metric.
  3. `valuation-context` (`default_3`): what trading level or spread the supplied items state for the sector.
  4. `market-demand` (`default_4`): how customer orders and shipments in the sector have moved over the latest year.
  5. `industry-structure` (`default_5`): how producers are structured by size and product focus.
  6. `regulation` (`default_6`): which licensing or other regulatory rules bear on producers.

## Rules

- Every question gets an answer state: `answered`, `partly` or `not_found`. Python decides whether the submission holds; the model's judgment is not accepted on its own word.
- Citations go through tools. A cited span must be located verbatim in a source the run holds, and a cited `page:N`, or a cited `line:N` of an `ev-*` item, must have been returned by `read_pages` in the step.
- An answered claim carries at least one citation, contrary evidence or a recorded none-found, and an uncertainty. A cited contrary item makes the question `contrary`.
- Families: two items of one family never count as independent. A claim lists its independent items, and they must be cited by the claim and drawn from different families.
- `not_found` is a missing result, not an answer. It carries no claim, states its limitation and names the items searched, and each searched item needs a recorded `search_pack` over it.
- The digit rule: analyst text (claims, uncertainty, limitations, question text) holds no digit character of any script. A figure reaches the reader only as a quoted source span or as Python's own count.
- `recommend` is banned in analyst text. `covenant`, `recovery` and `refinanc` are allowed here.
- Python owns every count (questions, answered, partly, not found, contrary items) and the downstream-use text of each question.
- Readiness comes from the claim states, one per brief question: empty, or any blocked, gives BLOCKED; any contrary or missing gives `RESEARCH_READY_WITH_LIMITATIONS`; otherwise `RESEARCH_READY`. It is never above `RESEARCH_READY`, because the lineage is `LOCAL`.
- The module always carries the LOCAL limitation, and a pack source carries no publication date or family, which is also stated as a limitation.
- Consumers: CP-1C and CP-2 are the named receivers of a question. No module reads CP-DR output until O7d. The dossier (`cp-dr-dossier`) is the rendered form of the settled tables.

## Guard limits (accepted costs)

- **Locator characters.** A locator with `?`, `=`, `&`, `%` or `#` cannot be supplied, so a source whose only address carries a query or fragment needs a plain locator from the user.
- **No digits in prose.** A year, an ordinal written in digits and a non-ASCII digit are all refused in analyst text.
- **Bounds.** Both byte limits are `MAX_BYTES`; a longer item is refused, not truncated.
- **Issue lines are bounded.** Lines that quote the payload are cut, and a long list keeps its first lines and a count of the rest.
