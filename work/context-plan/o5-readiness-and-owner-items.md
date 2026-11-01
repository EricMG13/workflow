# O5: live readiness and owner items (controller, 2026-11-01)

These come from the O5 phase review (mx-autonomous a692128f) and the O5 SDD ledger, `.superpowers/sdd/2026-10-31-part-b-o5/progress.md`. Live provider calls stay paused. Nothing here was run live.

## Before the first live call

1. A ruling written by the user in `docs/rulings/` with `lifts: live-provider-pause`, `by: user`, a date and `configs:` lines. The R2 gate (`model/adapter.py` `check_live_gate`) refuses every file there today, and the AGENTS.md pause also applies.
2. Re-fetch the provider docs and supply:
   - the sol cache-write rate (until then a charge with cache writes is unknown and the run stops);
   - the sol rates above 272K (until then `ContextTooLong`);
   - per-model max output for OpenAI and Anthropic (until then the global cap is 131072);
   - whether sol accepts `max` effort;
   - whether error replies carry billing fields (ruling M2 ignores non-2xx usage until then);
   - whether OpenRouter returns `usage.cost` on every reply (if not, every deepseek call stops as an unknown charge);
   - whether OpenAI's `input_tokens_details.cache_write_tokens` exists;
   - opus long-context rates (none stated in the provider docs; opus has no `max_input_tokens`).
3. Confirm `ANTHROPIC_VERSION = "2026-10-21"` and Bearer auth (`model/providers.py`). Context7 was the only source for both.
4. Reservation size. `bytes_per_token` is 1 (`model/loop.py`). That is provably safe, but it reserves about 4x on input, and a sol request over about 272 KB is refused. `TOKEN_OVERHEAD = 64` has not been measured against the providers' tool-use prompts. DEPLOY VII's 3.0 was measured on GLM 5.3 Flash, not on these models. Measure both per config before changing them. O2's `run_pathway.MAX_OUTPUT_TOKENS = 32768` (controller choice, under the 131072 global cap) sizes every reservation: the first sol-medium reservation is about $0.36, so a smaller cap stops at `BudgetExhausted`. Set it per config from the re-fetched limits. Measured offline on `cases/o2-synthetic` (O2 Task 5 part 3): the CP-1 narrative request carries about 669 KB, so with `bytes_per_token` 1 it is bounded at 669,447 tokens. On sol that is over 272,000, so the run stops `ContextTooLong` at CP-1 narrative, offline and live. The O2 walk therefore runs on `opus-medium`, which has no listed input limit, and the sol stop is pinned (`tests/test_o2_done_when.py::test_the_default_token_bound_stops_the_walk_at_narrative`).
5. Real-socket TLS is untested; every test injects the connection. Run one supervised local-TLS or real-socket smoke test before the first paid call. Two related gaps: the reply body has no size cap, and `first_byte_at` is always None.
6. O2 `run_pathway` must:
   - refuse adapters that are not of the exact type;
   - map `StepStopped` to `outcome: stopped`;
   - wire `redact_stream` to stderr.

## For the owner to decide

| Item | Where | Today |
|---|---|---|
| The branch is far over the 800-line PR cap (O5 alone adds 10,511 lines, about 4,360 of them source) | global §3 | PR Manager holds the O1 merge until the O5 gate |
| The R3 `\b` key pattern misses a key joined to a word character (`token_sk-or-…`) | `model/redact.py` KEY_PATTERN (R3 verbatim by ruling) | exact-value pass still covers env keys |
| A short env value (e.g. `"x"`) counts as a secret, so every reply is KeyReflected and the run stops | `model/redact.py:75` (R3 "exact non-empty values") | fails closed |
| model-call/1 has no raw-body hash, so a forged raw body that matches tokens and ids exports | `model/record.py` | — |
| A crash between budget settle and record append goes undetected; no link between marker and record | `budget.py`, `record.py` (schema) | — |
| `_refuse_forged_error` only means something for 2xx records; a status edited to 4xx skips it | `record.py:538` | — |
| A key used as a field name can echo in a validation error (r06); an ok turn with one invalid UTF-8 byte is withheld and can't be exported (r07) | `record.py` | both fail closed |
| Two Budgets over one Execution dir each enforce the cap only in memory | `budget.py` (ponytail comment) | single-process runner |
| A parent directory swapped for a symlink passes the O_NOFOLLOW gate read | `adapter.py` gate | tripwire, not an authenticator |
| Operator procedure for a crash-left reservation marker (settle it with the billed actual) | `budget.py` | the run stays stopped until settled |
| A settled charge above its reservation can take spend past the cap, and the stop reason then reads `NoSubmit`, not an overrun (O2 Task 3 adversary p04: 100.00002 spent on a cap of 1) | `model/loop.py:556-570` | the next reserve refuses; `spent_usd` in run.json shows the true total |
| An exception inside a tool call (for example a TypeError) becomes a stop with run.json through O5's `_caught`, not a propagated crash (p09) | `model/loop.py` `_caught` | run_pathway docstring says so |
| `DELIVERY_SCOPES` has no `portfolio_decision` row, so every portfolio_decision run ends `stopped: render: owner_render_scope` and writes no delivery (O2 Task 5: on o2-synthetic, eight modules settle restricted and the receipt verifies, then render refuses). Adding a scope is a rendering lease. | `owner_rendering.py:101-372` | the O2 done-when pins this end state |
| A RecordedAdapter miss is recorded as `AdapterError`, cost unknown, with the reservation held, so an offline stopped run reports non-zero `spent_usd` (O2 Task 3 C4) | `model/loop.py` | offline spend is not money (Q7); parked for the end-of-plan batch |
| B22's citation check is not done. `unread_citation_issues` stays page-only, so on a text or HTML run a model can cite a `line:N` it never read; the quote must still match the line exactly (O2 Task 7 R1; phase review p03). Tightening it re-cuts the frozen o2 CP-0 payload, the context-citing payloads of `context-attachments-owner`, `cp2h-context-owner`, o2 CP-1A/CP-3 and the owner cores cp1d, cp2e, cp3d, cpdr and cp8. | `live/tools.py:1261-1267` | asked of the user (narrows B22) |
| `MAX_LINES_PER_EXTRACT` is 200, but a real filing's last statement unit runs to the end of the source, so CP-1 financials fails closed on real HTML (O2 Task 7 R2). | `live/tools.py` | fails closed |
| The extracted-coverage floor (`_cell_coverage`) counts only `page:N` citations, so it never judges a line source (B22 review I1). Nothing in the repo turns the floor on. | `live/tools.py:919-924` | floor off |
| `STATEMENT_HEADING` is case-sensitive and must match the whole line. All 22 golden HTML sources title-case their statement headings ("Consolidated Balance Sheets"), so CP-1 financials on a real HTML source finds no statement unit and refuses by name (phase review p01). This predates O2. | `financial_workflow.py:88` | refuses by name after the O2 phase fix |
| `live/prompts.py` still says "page" (`CITATION_RULE` :78, `PAGE_SPAN_RULE` :109, `QUOTE_PAGE_RULE` :173, :183-188, :896). B22 does not cover prompts.py (O2 Task 7 R3). | `live/prompts.py` | before O6 live runs |
| For the goldens owner: 83 golden quotes and 2 `printed` values do not fit one converted line under the no-div rule (`cases/goldens/line-exceptions.json`). Re-cut them to one line, or rule a span-joining citation (a `readiness.py` change, the user's). | `cases/goldens/` | fixed exception list, shrink-only |
| `context.py:343-346`: a ValidationError chain shows an extra key's value in the traceback (O2 Task 2 adversary). | `context.py` | — |
| `run_pathway`'s public default composer has no prompt for `source_readiness`, so a public `run_pathway` stops `NoPrompt` at CP-0 until O6. The O2 walk proves orchestration through `_run_pathway` with a labelled test composer. | `run_pathway.py` | O6 |
