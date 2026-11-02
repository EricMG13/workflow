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
| More existing-step checks that no contract line states, added to O6 `OWNER_GAPS` by O6 T3 fix round 1: `source_context._blank_limitations`, and `cp1_workflow._validate_stage` (it binds the retained step and the source gate). Same remedy as the `cp4_legal._shape_issues` item. | `deploy_vii/live/prompts.py` STEP_CONTRACTS | vii edit; owner |
| The `cp1_workflow._validate_stage` OWNER_GAPS entry holds two refusals. "CP-1 source gate blocked: no usable assessed financial source" (`:119-122`) belongs to source_context, not financials. "Financial extraction does not bind the retained source step" (`:130-132`) is non-content if Python fills `context_step_sha256`. Rule each one separately (O6 T3 re-review I2). | `cp1_workflow.py` | owner |
| `cp4_legal.prohibited_issues_cp4` also refuses a peer ranking, which the `legal_covenants.g` contract line does not name (O6 T3 re-review I3; predates). | `deploy_vii/live/prompts.py` STEP_CONTRACTS | vii edit; owner |
| CP-2E `_Check.shocks` (`cp2e.py:730-734`) adds one issue per invalid shock with no cap, so 200,000 junk items give 200,001 issue lines (Phase 6 T5 adversary I2; predates). | `owners/cp2e.py` | predates; cap or collapse |
| O5 records, all predating the change (O5 follow-up adversary, Info). (1) No upper bound on money size: `settled_usd = 1E+9999999` gives a 10 MB `calls.jsonl` line, reachable from a tampered file through `export_recording`. (2) Loose money strings are accepted: `" 1"`, `"+1"`, and `"1_0"` read as 10. (3) Keys glued to a letter or digit, after a `\n` escape in repr text, or after double encoding (`%252F`) are not redacted. (4) `export_recording` lets ValueError (an int over 4300 digits) and RecursionError escape instead of `RecordInvalid`. | `model/record.py`, `model/redact.py` | predates |
| O3 `open()`: an injected `input-reads` record at the open epoch (same body, sequence+1) is adopted, because a submission binding lists `call_ids` but no read ids, and an open-epoch read has no submission yet (O3 T3a re-review p9; ruling R11). It can only add a read. With audit write access, it could also mark inputs read before a real read. | `owner_workflow.py` | accepted; journal reads if the threat model includes audit writers |
| CP-3D, predating Phase 3 T2 (adversary P2, P3). (1) Terms quotes can cite the context file, for example a margin of 340 taken from a quote's `spread_bps`. (2) A user line holding `Published <date>.` puts a context line into `published` (`cp3d.py:2174` reads every pack page). (3) U+2028 or a form feed between JSON tokens makes an invalid file readable after the line split (preparation). (4) The engine's `_value_offsets` (vii) accepts trailing commas and trailing text, but JSON parsing runs first, so this is latent. | `owners/cp3d.py`, `deploy_vii/cp3_relative_value.py` | predates |
| CP-2D liquidity_bridge: with no T4.18 schedule, `maturity_date_refs` is empty (`cp2d.py:2137-2147`), so every `maturity_wall` row is refused (O6 M5 review I1; predates). | `owners/cp2d.py` | predates; owner decides whether a maturity_wall row needs a schedule |
| CP-4C restructuring_fulcrum: the core pins a case-dated balance column (`_PINNED_COLUMN`, `cp4c.py:1391`) that the view does not expose; a `balance_column` view key would let the statement name it (O6 M5 review, concern 3). | `owners/cp4c.py` | predates |
| CP-3C: with no context, a payload whose step lines repeat now journals each line once (`_lines` dedupes), where before it journaled twice; old invalid journals replay with the deduped list (Phase 6 T6 adversary I2; by the brief's design). | `owners/cp3c.py` | owner decides only if journals written before 1b042230 must replay byte-equal |
| Pre-existing gate failures, all predating origin bd11a454: `ruff check src` exits 1 (88 errors: src/deploy_vii, and `tools/upstream.py` BLE001 at :438/:498/:617/:622 from 9d789ac8); mypy `no-any-return` at `tests/test_method_cp2g.py:107` (cb66e6ce) and `assignment` at `tests/test_connect_cp2d.py:515` (aad1480a). | several | predates; CI will show them |
| CP-3D: Phase 3's labels `TALK_FROM_CONTEXT` and `SINGLE_DEALER_CONTEXT` can be forged by a model-written `technicals[i].limitation` in a run with no context file (Phase 6 T7 adversary I3; `probe_forge_phase3_predates.py` exits 1 on b152c014). Phase 6 T7 refuses the pinned label the same way; the same one-line check would cover these. | `owners/cp3d.py` | predates (Phase 3 T2) |
| CP-3D `_RECOVERY` (`cp3d.py:225`, `.match` at :1047): `$` accepts a trailing newline, so `"70\n"` settles as 0.7 with no pin, and under pin 70 is refused fail-closed (Phase 6 T7 adversary I2). Use `\Z` or `fullmatch`. | `owners/cp3d.py` | predates |
| Pre-existing mypy `arg-type` at `tests/test_codex_render_fixes.py:56` (fbcf4be9; ModuleView vs Module). | tests | predates origin |
| Every pinned module: CP-0's review `sources[i].limitations`, `consumers[i].limitations` and `gaps[i].description` are copied verbatim into CP-0's limitations (`deploy_vii/readiness.py:553-557`) and inherited downstream, so a model-written CP-0 limitation equal to a module's `pinned_line` puts a false 'user-supplied, pinned' claim in that module's inherited limitations when nothing is pinned (Phase 6 T7 re-review N-L2; `probe_inherited_forge.py` exits 1). Under a pin the store dedupes it against the module's own label. | `src/deploy_vii/readiness.py` (user's) | predates; needs a vii ruling |

## From the Phase 6 end batch A (2026-11-01)

- **Huge exponents overflow in display (pre-existing).** A no-context CP-2D run with an amount like `1E+999999` fails in `compute` → `display.format_value` with `ValueError: Number is too large to display exactly` or `Overflow`, not a named refusal. Same at the parent commit; not a pins defect. Probe: `scratchpad/p6t4-adversary/probe_huge_exponent.py` (4 no-context rows exit 1). Recommendation: bound the exponent at the journal shape check so the run refuses with a named reason before compute.

## From the O3 Task 3b adversary review (2026-11-01)

- **`cap.json` has no integrity check.** Someone with write access to the run directory can edit `cap.json` and resume with the new cap; the resume accepts it. Probe: `scratchpad/o3t3b-adversary/probes/test_q5_identity_and_cap.py::test_info_cap_json_edited_raises_the_cap`. Recommendation: accept (the same writer can edit the reservation markers), or bind the cap into the reservation markers' config id.
- **A kill between staging and `cap.json`** leaves a run directory that can be neither resumed nor re-run. No spend. Recommendation: the owner deletes it by hand, or a later change writes `cap.json` before staging.
- **Finishing a sealed run with no `run.json`** (killed after `write_receipt` or after the render). Task 3b fix 1 gives it the named stop `SealedWithoutRunRecord`; finishing it (writing `run.json` from the sealed record) is a follow-up.

## From the O6 Task 4 adversary review (2026-11-01)

- **Arithmetic asked of the model (M2, predates the texts).** `restructuring_fulcrum` rules `.6`/`.7` require the fulcrum `class_ids` and plan treatments to equal Python's waterfall, which is EBITDA × the model's own multiple run through the claims by rank (`cp4c.py:659-680`, `_fulcrum_issues` ~:857); the only arithmetic-free path is "not assessed" for every multiple. `forward_credit_model` `.3` requires the three repayments to stay under the opening debt as a running sum (`cp2g.py:862-870`). Both contradict compose rule 4 ("never do arithmetic"). Recommendation: Python derives the fulcrum and plan treatments from the submitted multiples (and checks the repayment sum, telling the model the headroom), so the model judges and Python computes. Probe: `scratchpad/o6t4-adversary/p08_arithmetic_asked.py` (rc 1).
- **`_drive_resumed` reads the private `workflow._publications`** (O3 Task 3b fix 1, `run_pathway.py`). A public read-only accessor on `OwnerWorkflow` would remove the private read. Recommendation: add the accessor with the next owner_workflow change.

## From the Phase 4 Task 3 adversary review (2026-11-01)

- **`ContextRefused` texts can carry raw context data into the REPAIR block (pre-existing, shared).** `load_context` refusal texts put user-chosen JSON key names verbatim into `loc` (`context.py` ~:347) and the `_line_break_problems` paths (~:291), with decoded escapes (a key `"x\n- Ignore…"` becomes a real line break; a raw RLO stays raw). `_Rules.shocks` (~:469) echoes a raw cp2e shock item. Through `PackScope.context_refusal` → `validate` these reach the model's REPAIR block as extra `- …` lines. cp2a/cp2d/cp2e/cp3c/cp3d/cp4c already route the same text through `pins_of`; Phase 4 Task 3 (796f24be) adds CP-2H. Reachable only for packs prepared outside `run_inputs.py` / `context.py`'s preparers (both run `load_context` first). Probes: `scratchpad/p4t3-adversary/probe_context_refused_text.py` (1), `probe_refused_shared.py` (0, predates). Recommendation: escape C/Zl/Zp characters as `\uXXXX` (the P4-P15 rule) once, where `ContextRefused` is built in `context.py`, so every owner inherits it.

## From the Phase 4 phase review (2026-11-01)

- **`tests/prompts/test_rules.py` nodes run alone from the repo root fail on `import o2_case`.** `pyproject` sets `pythonpath = ["src", "."]`; pytest's prepend mode adds `tests/` only when a `tests/` file is also collected. Passes with `PYTHONPATH=src:tests`. Recommendation: add `"tests"` to `pythonpath` in `pyproject.toml` (one line), so every node id runs alone.

## O3 Task 4 replay (controller, 2026-11-01)

- **Replayed `call_ids` are partly bound.** Fix b7060bbd binds them to the calls retained at the binding, which refuses any edit inconsistent with the journal. A forger who deletes the call records and also blanks `call_ids` still passes (probe `o3t4-adversary/probes/test_p1d_consistent_call_removal.py`): replay then re-issues 0 of 2 calls. Recommendation: record the step's call ids in the journal's settled step. Cost if left: a tampered earlier run can misstate a rerun's spend and call count, but not its outputs.
- **The earlier run's flock is not taken.** A rerun can read an earlier run that is still running. Recommendation: `check_replay` refuses when the earlier run's lock is held (non-blocking probe, no new file in the earlier tree).
- **`replays` and `faults` records are outside `_verify_audit`.** The receipt does not seal them. Recommendation: add both kinds to the sealed set when the receipt format next changes.

## Worktree hygiene (controller, 2026-11-01)

- **Stray formatter edit in `src/deploy_vii/methods/cp1d.md`.** An uncommitted whitespace-only change (comment alignment in its Python code blocks) appeared during the O3 Task 4 fix round. It looks like `ruff format` run on a directory. The controller's `git restore` of it was refused by the permission classifier, so it is still in the worktree, unstaged. Every builder is told never to stage it. Recommendation: the user runs `git restore -- src/deploy_vii/methods/cp1d.md`, or allows the controller to.
- **Pre-existing mypy errors:** `tests/test_method_cp2g.py:107` and `tests/test_connect_cp2d.py:515` (identical at 9a0e7193).
- **cp1d.md cause confirmed:** the O3 Task 4 fix builder ran `.venv/bin/ruff format src tests/test_owner_replay.py`. Ruff 0.17.1 formats Python code blocks in Markdown. It restored `earnings.py` and `tools/upstream.py` itself, but its restore of `cp1d.md` was also denied. Every brief now requires ruff to be run with explicit file paths.
- **ruff ISC004 at `src/deploy_vii/live/prompts.py` ~:1191-1198** (implicit string concatenation), reported by Phase 3 Task 4 Part A as predating it (the adversary confirms at f4e1028a^).
- **cp1d.md restored** by the controller with `git restore`, on the user's approval (reply "2", 2026-11-01). `src/deploy_vii` has no uncommitted change. (17:41 UTC)

## Phase 6 phase review (controller, 2026-11-01)

- **Pinned values are shown as JSON strings, but the contracts are strict ints.** The pinned-assumptions block renders integer fields as strings (`"horizon_months": "24"`, `"repricing.bps": "400"`), while compose.O6 says to submit "exactly that value". A model that copies the string gets a shape refusal and a repair round. It fails closed and never yields a wrong figure. Recommendation: compose.O6 says "the same number in the field's JSON type", or `pins.form_from_context` renders ints as ints. Cost if left: extra repair rounds on live runs.

## Phase 3 Task 4 Part B review (controller, 2026-11-01)

- **Six CP-3 context-reader sites are listed as PENDING, not as reader problems.** In `cp3_relative_value.py` ~:555-620, `_strings`, `_figure_problems`, `_date_problems`, `_row_problems`, `_identity_problems` and `_array_rows` are reader problems of the context file, whose remedy is a new pack. Recommendation: move them to the non-content subtraction (`rules.py` ~:334, `UNREADABLE`) instead of PENDING.
- **The CP-3 method text and rules d and e predate `basis.context_rows`.** `src/deploy_vii/methods/cp3.md:31-32`, `CP3_BASIS_RULE` (rule d) and rule e still describe a market basis only as a `basis.quotes` quote, but the validator also accepts `basis.context_rows`. Recommendation: a wording-only `src/deploy_vii` edit naming `basis.context_rows`. It needs a user approval, as B17 item 3 did.
- **Test modules import other test modules** in `tests/prompts/test_factory.py` and `tests/prompts/test_pinned_block.py` (predates; found by the merge-fix check). Recommendation: move the shared helpers into non-test modules, as `merge_strip.py` did.
- **`tests/prompts/test_g8.py` ~:143-160 shells out to `git grep`** at cfe37c23 and 0fc6eb35, so it fails on a tree with no git history (an archive, or a shallow clone). PR CI checks out with `fetch-depth: 0`, so CI is fine. Recommendation: keep it, or skip it with a logged reason when there is no history. (Found by the Phase 3 phase review.)

- **CP-3 market-observation wording (B29 review M1, 2026-11-01).** Rule d's second clause (`live/prompts.py:601-602`), rule e (`:607`) and `methods/cp3.md:31-32` say a market observation or preference "cites a market quote". The validator also accepts a context row (`_cites_market`, `cp3_relative_value.py:1115-1117`, :1150-1153, :1201). A literal reading in a context-only run gives "none" and Insufficient Information, which is weaker than `cases/cp3-context-owner/expected.json#cp3/context-only`. The `Basis` docstring (:191-192) and the refusal messages at :1103, :1153 and :1202 name quotes only. Sent to the user via MANAGER as a proposed B30.
- **cp4_legal.py:411 TRY004 (Phase 5 Task 2 review, I5).** It predates the context plan and makes `ruff check` on that file exit 1.
- **Context form JS has no committed test (Phase 2 Task 1 review, L1).** The `lines` parsers are checked only by the scratch probe `p2t1-review/probe_form_js.js` (node), which the controller runs at the Phase 2 gate. A `cases/prove/` node verifier would need a CI node dependency.
- **CP-4C names its CP-4 input "executed" (Phase 5 Task 2 review, I4).** owners/cp4c.py:1527-1531 ("Executed term loan terms"), pinned by cases/cp4c-owner. A draft or filed CP-4 head passes `_check_cp4_head`. The wording would need an oracle re-key.

## Phase 2 owner items (controller, 2026-11-01)

- **CP-L10 unbound operand shows only `identity_mismatch` (pre-existing).** cpl10.py `view` maps every UpstreamError to `identity_mismatch`. Under ctx-q3, an operator sees that code and never sees the text "unbound CP-1 operand: q4-2024 (no CP-1 T4.14 period)" (Phase 2 Task 3, adversary M1). The same holds for a refused context file: the read refuses `identity_mismatch` before the `CP-L10: Context refused: ...` issue can show (Task 3 re-review, Info).
- **CP-1B leverage-reason substring check (pre-existing).** At owners/cp1b.py:160, a reason that contains "Four complete contiguous quarters" settles as "unavailable" even when it says they are available. It needs a crafted CP-1 limitation to trigger. Probe: `p2t4a-adversary/probes/probe_reason_substring_base_vs_tip.py` (Phase 2 Task 4a, adversary L2).
- **Orphan FY2024 basis (pre-existing).** A gap pair whose fy-2024 values sit in T4.10 with no T4.14 row settles with "Requested FY2024 comparison basis is absent" (Phase 2 Task 4a, adversary I2).
- **Rule compose.O3 does not name `cp0_run_context_block`.** At rule_lists/compose.json:24, the rule's checks name `fence:run_context_block` only. Since Phase 5 Task 6, `cp0_run_context_block` builds CP-0's run-context block. Coverage still passes. This belongs to the O6 rule-list process (Phase 5 Task 6, adversary I3).
- **Pre-existing CP-4 mutants survive.** probe_mutants M4, M6 and M9 survive at both base and tip (Phase 5 Task 6, precise I4). Probe: `p5t2-adversary/probes/probe_mutants.py`.
- **The CP-1B receipt path leaves the step pending on `unsupported_pair` (pre-existing in shape).** `_stage_validation` (earnings_workflow.py ~:2310) lets the composer's `unsupported_pair` ValueError propagate, so the step stays pending instead of returning an issue. The frozen E-* registers compose, so no current case reaches it (Phase 2 Task 4a re-review, I2).
- **The CP-1B literal pair pins stay until Phase 8 (P2T4b-R1).** Phase 8 removes them with keys for other pairs. It must first generalise `supported()`'s opening-row guard to the derived year, and decide `_no_earlier_series`, which refuses any earlier duration row and so would refuse real registers with older history.
- **CP-1B with one context period set (Phase 2 Task 4b, adversary I3).** A research `run_type` on `earnings_update` with only `current_period` set gives O1 behaviour. CP-1B can then settle fy-2024 → fy-2025 while the context names q4-2025. This matches the plan's "both non-empty" rule. Should it refuse instead?
- **CP-1B view offers a pair the validator refuses (pre-existing).** When the register's labels disagree with the pinned ids, the view still offers a pair the validator then refuses. Probe: `p2t4b-adversary/probes/probe_view_offers_refused_pair.py`, exit 1 at base and at tip (Phase 2 Task 4b, adversary I4).
- **Context keys with ESC or newline reach issue text raw (pre-existing).** `context.py` `_path` quotes the key unescaped, and cpl10 is affected too. It is reachable only with a pack whose context never went through the context CLI (Phase 2 Task 4b, adversary L1).
- **Owner transport drain loses the lines after a bad chunk (pre-existing).** When an over-length line with a non-UTF-8 tail is answered, the text decoder drops the rest of that chunk: with no gap both following requests are lost, with a 20 KB gap one is (O3 Task 6, re-review I1). Probe: `o3t6-adversary/probes/test_f5_drain_next_line.py`, exit 1 at the parent and at the tip.
- **No redactor removes a payload quoted inside an exception message.** The loop keeps all of it, in `calls.jsonl` `error` and the stop reason. The owner fault record keeps its first 500 characters. T6-R2's "never a payload" is therefore met nowhere (O3 Task 6, re-review I2).
- **Session-less `invoke` called directly in Python raises on bad shapes (pre-existing).** It raises on a non-str tool, non-object arguments, surrogates and deep arguments. The transport refuses these before they reach it (T6-R12), but the loop path does not (O3 Task 6, re-review f2).
- **For Phase 8, which owns CP-1B periods (Phase 2 phase review I2 and I4).**
  - CP-L10's `_period_register` and `earnings._periods` differ in strictness on non-canonical T4.14 heads, though both fail closed and agree on the real-form register.
  - The CP-1B view offers `pairs: []`, with no reason text, for a resolved context pair outside the two pins.
- **The cpos-owner report_view.py pin is stale (pre-existing, Phase 8 pre-flight P8-P3).** `cases/cpos-owner/manifest.json:10` and `builder/build.py:28` still name `5dc981…`, two records behind `dbf8de07…`. No test calls `read_pinned`, so only a cpos-owner rebuild would fail. The oracle preparer re-pins it.
- **The CP-4C prompt and CP-1C's selected multiple (Phase 7 pre-flight P7-P12). Closed by ruling P7-R13 (2026-11-02).** The Phase 7 Task 4 review (p07) found that CP-4C's prompt is `src/deploy_workflow/prompts/texts/restructuring_fulcrum.md`, not a `STEP_CONTRACTS` entry, so the sentence needs no `src/deploy_vii` edit. It lands as rule `restructuring_fulcrum.11` in Task 4's fix round, and the golden is refreshed at the Release 3 cut.

## Phase 8 Task 1 owner items (2026-11-01)
- `context_periods.resolve` reads a two-year spelling (`FY2025/26`, `2025-26`) as its first year, while vii's `fiscal_year_number` reads the second. PeriodBasis now refuses the mismatch (P8T1-R2), so such a register is falsely refused at `fy-2026`. `resolve` is shared with cpl10 `context_quarters` and `earnings_workflow._column_periods`; aligning it with vii is an owner decision.
- PeriodBasis refuses stub fiscal years, anything outside 364-371 days (P8T1-R3). A transition-year pack needs an owner rule for its LTM label.

## Phase 7 Task 2 owner item (2026-11-01)
- Duplicate peer rows each count toward CP-1C's minimum of 3 admitted (adversary I-3). No dedup rule exists; one is an owner decision.

## Phase 8 Task 4 owner item (2026-11-01)
- A context with a blank run.current_period takes the default FY2025 basis when its currency is USD (P8-R3, which keeps the frozen Phase 6 pins-context cases). A 2026 run with a blank base therefore refuses at selection instead of inferring its year. Whether a blank base should derive its year from CP-1 is an owner decision.

## Phase 8 Task 3 owner items (2026-11-01)
- CP-1D's `parse_bridge` never reads the currency or scale on the bridge's basis line ("; EUR; amounts in millions"). A USD or thousands bridge under an EUR run, or an EUR bridge under the USD default, composes, and every T1D.1 amount is stamped in the run's currency, in millions. This predates Phase 8, which widens the exposure (adversary P1; probes `probe_bridge_currency.py` and `probe_bridge_currency_default.py`, both exit 1). The reviewer rates it Medium.
- CP-1D's view raises `ValueError` when CP-1 holds no T4.10 facts for the run's LTM column. Under `read_inputs` that is an `InternalError` fault, not a refusal. This also predates Phase 8; P8-R5 fixes only the context, period and currency refusals.

## Phase 5 Task 3 owner items (2026-11-01)
- Four CP-0 paths call `submit_cp0_review` without the owner workflow's `_PRECHECKS`, so a context pack sent through them gets no attachments or legal gate: `financial_workflow.py:899` (the CLI), `earnings_workflow.py:2680` and `:2835`, `workflow.py:531`, and `deploy_vii/live/submission.py:1102`. The plan scoped Task 3 to the owner workflow (adversary I4).
- The model is never told the attachments rule. No `source_readiness` rule states it, `fence.cp0_run_context_block` shows only `legal_documents`, and the rule-coverage check cannot see a precheck. This is an O6 rule-list item (adversary I5).
- Gaps in the legal rule's matching (adversary I1, I2 and I3):
  - the legal gap is matched by plain substring, so `illegal_documents_x` passes;
  - any ready source assessed `filed` or `executed` satisfies the executed rule, non-legal sources included;
  - the frozen regex is ASCII-only, ruling Q5.
- No test kills the replay-recompute skip mutant in `OwnerWorkflow.open` for any module (`probe_site_mutant_replay_all.py`). This predates Phase 5.

## Phase 8 Task 5 owner items (2026-11-02)
- A non-calendar fiscal year (July-June, April-March, 52/53-week) is refused by CP-2G and CP-2H (P8T5-R1). Deriving forecast windows from `ltm_start`/`ltm_end` + k years needs an owner rule for 52/53-week years and a pinned key.
- CP-2A money break levels are copied into CP-2G in the run's currency with no check (`cp2g.py:2059` `_cp2a_copy`). An EUR run copies a USD 50 level as EUR 50. The parent did the same under USD. This predates Phase 8.

## Phase 8 Task 4 owner item, added (2026-11-02)
- With a blank USD base, CP-2D and CP-3C bind the 2025 figures from a CP-1 whose latest year is 2026 but which also carries 2025 rows. The labels are honest, and the parent behaved the same. Whether vii ever emits such a two-year T4.14 register is unverified (adversary L3, `probe_blank_usd_two_year.py`).

## Phase 8 Task 7 owner item (2026-11-02)
- A plain USD CP-L10 `Upstream` accepts a known operand in another currency (EUR). A frozen `test_method_cpl10` assertion pins this, so the Phase 8 currency check covers non-USD runs only (`RunUpstream`, P8T7-R8). Whether a USD run should refuse a non-USD operand is the owner's call.

## Phase 5 phase review owner items (2026-11-02)
- Under `legal_documents: draft`, a CP-0 review can class the draft source `executed` or `filed` and add a `source` gap naming `legal_documents`. That review passes both gates, and CP-4 then cites the source with no draft limitation. The plan allows the gap route, so this is design latitude (phase review I1, `probe_seam_matrix.py`).
- B17.6 refuses `executed`, `filed` and `draft` authority on the `context` source, but not `third_party`. `live/context.py:35` sends CP-3 the sources CP-0 classes `third_party`, so a context file classed `third_party` would reach CP-3. Not probed (phase review I5).

## P8-R4 rules batch owner items (2026-11-02)
- The rule-coverage scanner (`rules._sites`) cannot see a refusal returned through a helper as a plain string. The batch covered the CP-2A, CP-2E, CP-2G and CP-2H sites. Released helpers at cp1d.py:2151, cp2d.py:2321/2325 and cp3c.py:2588/2592 have the same blind spot. Whether their steps' rules state those refusals was not checked (review I1).
- Under the blank-USD fail-open (P8-R3), the cp2g and cp2h entry validators raise `ValueError` (`select_cp1`, "unexpected unit or period") instead of returning an issue, when the CP-1 register is EUR or incomplete. This fails closed, under the documented guard (review I2).

## Phase 7 Task 1 review owner items (2026-11-02)
- `MYPYPATH=src mypy` fails on `tests/cp3c_runs.py:151` with `[no-untyped-call]`. It fails the same way at the parent, so it predates Task 1 (review I1).
- The frozen prose at `cases/cp1c-owner/expected.json:140` (`execution.consumption.edges`) says "optional for CP-2, CP-3 and CP-5 only". Since Phase 7 Task 1, CP-4C also takes CP-1C as an optional input, so the sentence is false. No test reads it, and it is the oracle preparer's to fix (review I3).

## O3 Task 7 owner item (2026-11-02)
- O3's done-when (a) asks for a `distressed_restructuring` walk in which CP-2G and CP-2H settle over a refused CP-4. No pinned case supplies the sources and a CP-0 for the current preset. So the built test (O3T7-R3) walks the o2 sources instead: CP-0 is the test input, CP-1A is granted, and CP-4, CP-4C and CP-5 are refused. Showing CP-2G and CP-2H settle after a refusal needs a new oracle with settled distressed file sources. Until one exists, that row is built but not done.

## Phase 7 Task 3 review owner items (2026-11-02)
- With `cp_dr_public` and `blend` plus precedents, T1C.11 reads "public comps 0 admitted of 3 required" but never names the O7d gap: the public-peer figures await the CP-DR peer pack. The frozen oracle builder models `blend` the same way (`cases/valuation-context-owner/builder/build.py:466,618`). Changing it is an owner decision (review L2).
- A user multiple with more than 2 dp, for example 8.555, is carried as a `source` fact holding 8.56, with the formula "user-supplied multiple". The frozen key pins `value_class source` and that formula, so a change needs the oracle preparer first (review L4).
- T1C.10 rounds the exact median half-up for display. T1C.11 selects the 2-dp multiple half-even (Design 6). A median of 5.025 therefore shows as 5.03x in T1C.10 and 5.02x in T1C.11. This predates Task 3 (review I4).
- The CP-4C prompt does not yet tell the model to use `selected_multiple` when it is present. Closed by ruling P7-R13: rule `restructuring_fulcrum.11`, in `src/deploy_workflow/prompts/`, lands in Phase 7 Task 4's fix round.

## Phase 7 Task 4 review owner items (2026-11-02)
- **Confusable characters in the forgery checks (review L2; predates Task 4).** `cp3d._normalised` folds with NFKC, which does not fold dash variants or Cyrillic look-alikes. Two copies get no issue at all:
  - a model-written gap that copies the CP-1C selection line with U+2011 in "CP-1C" and without the "no alignment" tail;
  - Phase 6's pinned line with U+2011 in "user-supplied", which `pin_label_forged` misses.

  A full copy is still refused. Folding confusables is an owner decision (probe `scratchpad/p7t4-review/probes/p05_forgery.py`).

## O3/O4 phase review owner items (2026-11-02)
These are documentary, for the testing session's framework plan; there is no code change.
- Contract amendment 2 and Task 7 row (a) in `docs/superpowers/plans/2026-10-31-part-b-o3-o4.md` predate ruling B23, the renderer's consequence-refusal rule (review L1).
- Contract amendment 3 under-lists the new `stopped_reason` values (review L2). It omits:
  - `UnrecordedCall` and `SealedWithoutRunRecord`;
  - `ReplayRefused` and `ReplayPackChanged` mid-run;
  - the resumed money-stop forms;
  - the two publish and resume texts.

## Phase 8 end batch 1 and Task 2 owner items (2026-11-02)
- **The liquidity axis currency (end batch 1, item F).** An all-unsettled CR.2/CR.3 frame takes its axis currency from the module's other MILLIONS facts, because `ModuleView` carries no run currency. A module that states no currency on any fact still shows `US$ m`. Carrying the run currency into `ModuleView` is an owner decision.
- **A Basis line with two currency clauses (Phase 8 Task 2 review I5; predates the task).** CP-1C reads a peers page whose Basis line holds two currency clauses as the run's currency under either run. Before Phase 8 it was read as USD (probe `scratchpad/p8t2-review/probes/probe_basis_clause.py`, INFO row).
- **An explicit valuation basis with no records leaves no trace (Phase 7 Task 3 review L1; ruling P7-R11's fallback).** The cases are `peer_source none` with `public_comps`, `blend` with no precedents, and `precedents` with no precedents. Each composes no EV table and no limitation, although Design 5 calls it a stated gap. No key in `cases/valuation-context-owner/expected.json` gives the row, the cell or the gap text. Showing the gap needs an oracle amendment first (probe `scratchpad/p7t3-review/probes/probe_silent_basis.py`, exit 1).

## Methods batch, O6 Task 6 and Phase 8 done-when owner items (2026-11-02)
- **The `auto` basis never reaches precedents (methods review Low-1; predates the batch).**
  - `valuation_basis._auto` falls back to precedents, but `load_context` refuses precedents unless the basis is `precedents` or `blend` (`context.py:601-602`). The context form hides them too (`context-form.html:1132`).
  - So an `auto` run with `user_list` or `cp_dr_public` always ends at "Insufficient Information" (probe `scratchpad/methods-review/probes/p02_auto_precedents_unreachable.py`, exit 0).
  - The owner decides between two options: allow precedents under `auto`, or have RUN-GUIDE.md:158-164 and `methods/cp1c.md` say that `auto` reads public comps only.
- **A stale docstring (methods review Low-2, code half).** `owners/cp1c.py:3144-3146` still says no consumer reads the EV reader. CP-4C has called `cp1c_reader` since Phase 7 Task 4 (`cp4c.py:2910`). The method text is fixed in methods fix 1; the docstring is code and is not in any open task.
- **The tool loop does not check the step's offer (O6 Task 6 review I1; predates the task).**
  - `ToolLoop._kind` and `_call` (`model/loop.py:824-843`) dispatch on the tool name alone. A tool the step was not offered is refused one layer down, by the workflow (`not_permitted`).
  - Six such calls were each refused, recorded, and did not stop the run (probe `scratchpad/o6t6-review/probes/p04_unoffered_tool_calls.py`, exit 0).
  - Only the `read_inputs` case has a fast test.
  - Refusing at the loop is an owner decision.
- **mypy over the test modules.** A plain `mypy tests/test_periods_currency_oracle.py` follows its imports and reports 5 earlier errors:
  - `tests/test_method_cp2g.py:107` (no-any-return);
  - `tests/test_periods_currency_misc.py:36` and `tests/test_connect_cp1d.py:605-607` (attr-defined: implicit re-exports).

  PR CI runs mypy only over `src/deploy_workflow/` and `cases/prove/`, with `--follow-imports=silent`, so CI does not see them.

## Phase 8 phase review owner items (2026-11-02)
- **CP-2G and CP-2H match the CP-1 label alone (review L1; predates the phase).** `select_cp1` in cp2g and cp2h matches a T4.10 fact by its label only. The other five owners also require the run's period. A twin label from another period is therefore picked by CP-2G and CP-2H but refused elsewhere (probe `scratchpad/p8-phase-review/probes/p02*`, exit 1).
- **CP-1B and the earnings path bypass the blank-base rule (review L2).** `currency_basis` is read directly, so these paths skip P8-R3's blank-base rule. The output stays honest (probe `p06*`, exit 1). Routing them through `run_basis` is an owner decision.

## O7b-1b review owner items (2026-11-02)
- **The O6 fence lets NFKD-unfolded lookalikes through (review I-3; predates O7).** `‹`, `〈` and `⟨` pass the fence and stay inside it. Probe: `scratchpad/o7b1b-review/probes/p01*`, exit 0, for what the fence does refuse. Widening the fold is an owner decision.
- **A delimiter in a pack span raises out of `stage()` (review I-4; predates O7).** `PackTools` raises `PromptError` from `stage()` when a span holds a delimiter. Intake makes this unreachable for `ev-*`, but not for pack sources.

## Release 3 owner items (2026-11-02)
- **The budget test's refusal regex is shared (R3-B1 review Low; predates Release 3).**
  - `tests/test_model_testing_budget.py:195,197` match only the location prefix that `budget.py`'s three guards share (`:45`, `:47`, `:50`). A rewritten money-guard message passes. Probe: `scratchpad/r3b1-review/probes/mutants.sh`, `m_msg`.
  - Suggested fix: match `.*not negative`.
  - The comment at `:218` names `model_construct`, but the code uses `model_copy`.
- **The budget's negative-money guard is defence in depth.** `budget.py:49` cannot be reached from any `src` path, because every `CallRecord` constructor validates `ge=0`. Keeping or removing it is an owner decision.
- **Slow owner tests run only in CI (R3-G1).** These time out as whole files at 290 s locally, so the controller's union gate leaves them to PR CI, under the user's "slow tests left to CI":
  - `test_owner_cp1c`, `cp1d`, `cp2a`, `cp2g`, `cp2h`, `cp3`, `cp4` (also `cp4c`);
  - `test_earnings_workflow`.

  Each test_owner_cp1c/cp4c node takes about 275 s of module-fixture setup. CI does not run `RUN_PROMOTION` at all, so promotion-gated nodes run nowhere automatically.
- **The cp4c builder cannot run in place (R3-L3(b); since 9f32bbd3).** Its cp3c-manifest pin is stale. It is restored in O7b-1c S3.
