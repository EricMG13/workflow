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
7. B22a: turn on the `line:N` citation check in `unread_citation_issues`, and re-cut the frozen payloads that cite context lines (owner table below). This must land before any live call.

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
| B22's citation check is not done. `unread_citation_issues` stays page-only, so on a text or HTML run a model can cite a `line:N` it never read; the quote must still match the line exactly (O2 Task 7 R1; phase review p03). Tightening it re-cuts the frozen o2 CP-0 payload, the context-citing payloads of `context-attachments-owner`, `cp2h-context-owner`, o2 CP-1A/CP-3 and the owner cores cp1d, cp2e, cp3d, cpdr and cp8. | `live/tools.py:1261-1267` | user B22a: before the first live run (readiness item 7) |
| `MAX_LINES_PER_EXTRACT` is 200, but a real filing's last statement unit runs to the end of the source, so CP-1 financials fails closed on real HTML (O2 Task 7 R2). | `live/tools.py` | fails closed |
| The extracted-coverage floor (`_cell_coverage`) counts only `page:N` citations, so it never judges a line source (B22 review I1). Nothing in the repo turns the floor on. | `live/tools.py:919-924` | floor off |
| `STATEMENT_HEADING` is case-sensitive and must match the whole line. All 22 golden HTML sources title-case their statement headings ("Consolidated Balance Sheets"), so CP-1 financials on a real HTML source finds no statement unit and refuses by name (phase review p01). This predates O2. | `financial_workflow.py:88` | refuses by name after the O2 phase fix |
| `live/prompts.py` still says "page" (`CITATION_RULE` :78, `PAGE_SPAN_RULE` :109, `QUOTE_PAGE_RULE` :173, :183-188, :896). B22 does not cover prompts.py (O2 Task 7 R3). | `live/prompts.py` | before O6 live runs |
| For the goldens owner: 83 golden quotes and 2 `printed` values do not fit one converted line under the no-div rule (`cases/goldens/line-exceptions.json`). Re-cut them to one line, or rule a span-joining citation (a `readiness.py` change, the user's). | `cases/goldens/` | fixed exception list, shrink-only |
| `context.py:343-346`: a ValidationError chain shows an extra key's value in the traceback (O2 Task 2 adversary). | `context.py` | — |
| `run_pathway`'s public default composer has no prompt for `source_readiness`, so a public `run_pathway` stops `NoPrompt` at CP-0 until O6. The O2 walk proves orchestration through `_run_pathway` with a labelled test composer. | `run_pathway.py` | O6 |
| `_retainable` keeps the old rule: any blocked head anywhere makes a blocked-edge error retainable. Now that the walk continues, that rule covers every later module. `write_receipt`'s settled-xor-refused check still rejects a skipped upstream (O3 T1 review). | `owner_workflow.py` `_retainable` | predates G3 |
| A receipt written before G3 that holds a refusal no longer verifies, because `missing_*` is recomputed and is never empty. No such receipt is persisted (O3 T1 adversary L3). | `owner_workflow.py` `_verify_walk` | document, or accept empty fields as legacy |
| The verifier does not bind the order of `receipt.refusals` (`_verify_audit` compares sets). The renderer takes the earliest refusal by plan position, so a reordered list renders the same (O3 T1 re-review L2). | `owner_workflow.py` `_verify_walk` | renderer pinned by test |
| The cpos `s1a_refused_cp1a` oracle has no structured `refused_begins`, so `tests/test_owner_s1a.py:898` follows its prose (B23 C/D review). | `cases/cpos-owner/expected.json` | slow test; CI |
| After a begin defect propagates (not retainable), `_advance` leaves the old binding active, and `state()` shows a settled module as active (O3 T2 adversary L1). | `owner_workflow.py` `_advance` | predates |
| `state()` takes `_operation` without blocking (P17), so a polling reader makes mutators fail with `not_permitted` (O3 T2 adversary I1). | `owner_workflow.py` `state` | callers must not poll while driving |
| The context form's JS rules (dp order, increase check, parse guard) have no behavioural test. A test that runs a JS runtime (node) would be a new CI dependency and needs a decision record (Phase 6 T1 review f01-f04). | `docs/templates/context-form.html` | literals compared with the reader table |
| `PROMPT_SET_SHA256` is not in run.json, because `tests/test_run_pathway.py:261` pins the key set (O6 Q3). | `run_pathway.py` | constant plus golden test |
| `read_pages`' tool description and the `CITATION_RULE` example in `live/prompts.py` still say "page". O6 adds a line-source rule in the composer instead (O6-P9). | `src/deploy_vii/live/` | O6 rule `compose.O5` |
| When another writer stales the journal heads (for example `replace_pack` at the CP-MODEL stop), `state()` raises `identity_mismatch` from `_settled` instead of answering with `stale` True. This contradicts its docstring (O3 T2 re-review I2; probe f5b). | `owner_workflow.py` `state` / `_settled` | predates Task 2 |
| CP-2D parses JSON numbers through float (`MinimumCash.amount`), so `9.99999999999999999999` becomes `Decimal('10')`. The figure still equals the pin; only the payload text differs (Phase 6 T2 adversary p07). | `owners/cp2d.py:91` | predates |
| Fences refuse `<<<` after NFKD with Cf/Mn/Me and the Hangul fillers removed (O6 fix round 2, F3). Visible lookalikes such as U+2039 `‹`, U+02C2 `˂` and U+1438 `ᐸ` still pass. Rule on a confusables check before untrusted evidence (O7b) fills the fenced block (O6 T2 re-review). | `prompts/fence.py` | before O7b |
| CP-2A `DECLINE_PATTERN` (`cp2a.py:79`, `:93-94`) uses `\d`, which pydantic's Rust regex reads as Unicode, so `0.٢` passes the shape check and composes as 0.2 when no pin is set. With a pin it is refused as typed (Phase 6 T3 adversary L3). | `owners/cp2a.py` | predates; `[0-9]` |
| The `pins-context-owner` oracle keeps "Scenario shock sizes are analyst assumptions without a source citation." beside the new pinned line that calls them user-supplied, and the T2B.1 shock facts stay `analyst_judgment` (Phase 6 T3 adversary Info 2). Should both sentences stand? | `cases/pins-context-owner/expected.json` | oracle owner |
| `cp2d._inputs(store, attempt, submission)` (`cp2d.py:2203-2208`) has no caller in src, and its docstring says `submit`, `probe` and `view` use it. It does not carry the pinned flag. Delete it or correct the docstring (Phase 6 T4 precise Info 4). | `owners/cp2d.py` | predates |
| On the live path, after a validator crash, a different payload makes `submit_review` raise a bare `ValueError` ("Ticket already retains a different response"), not a `WorkflowError` (O3 T3a reviews; predates). After R5, `open()` resubmits the retained payload, so a resume never reaches it. | `owner_workflow.py` `submit_review` | predates |
| A huge minimum-cash amount with no context (`1E+999999999` and similar) makes the CP-2D validator raise `Overflow` or `ValueError: Number is too large to display exactly`, and `execution.py:794` leaves the step pending (Phase 6 T4 adversary; predates T4; `probe_huge_exponent.py`). | `owners/cp2d.py` / `execution.py` | predates |
| Add to the CP-2D float item: `10.000000000000001` is refused as `submitted 10.000000000000002`, a value nobody typed. Pydantic also reads `"+10"`, `" 10"`, `"1_0"` and non-ASCII digits as `Decimal(10)`, while CP-2A refuses non-ASCII spellings, so the two modules differ (Phase 6 T4 adversary I1/I2). | `owners/cp2d.py` | predates |
| The `pins-context-owner` oracle keeps CP-2D T2E.7 "Minimum cash is an analyst assumption, not a source figure." beside the pinned line, the same pattern as the CP-2A item (Phase 6 T4 adversary I6). | `cases/pins-context-owner/expected.json` | oracle owner |
| `cp4_legal._shape_issues` (`deploy_vii/cp4_legal.py:593`) refuses "documents: X is registered more than once", but no `legal_covenants` line in `STEP_CONTRACTS` says documents are registered once, so the model is not told. It is listed in O6 `OWNER_GAPS` (O6-P19; O6 T3 review M1). Other existing-step checks with no contract line join this item as O6 T3 fix round 1 classifies them. | `deploy_vii/live/prompts.py` STEP_CONTRACTS | vii edit; owner |
| Two CP-3 mutants survive the CP-3 tests both at 13d18091 and after Phase 3 T1: N08 (a model `market_evidence` row of kind `none` that quotes something passes) and N10 (the "Unavailable or changed source" issue can be removed). The code was moved in T1 but its behaviour is unchanged (Phase 3 T1 re-review; `p3t1-adversary/mutants_parent_legacy.py`). | `deploy_vii/cp3_relative_value.py` tests | predates |
