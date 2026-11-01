# O5 plan review (mx-autonomous, read-only), 2026-10-31: verdict fix (2 High, 9 Medium)

Target: `docs/superpowers/plans/2026-10-31-part-b-o5.md` draft at 3451eec5.

- **F1 High** (plan :73-74, :121, :168, :171). Retry and 402 resend inside `adapter.complete` send up
  to three requests on one reservation and one record (breaks Part B "one record per provider
  request" and the cap). :171 releases a failed sent call's reservation; Codex `providers.py:516-535,
  551-552` treats every non-2xx and timeout as an unknown charge (spec §7.2, §4). Fix: `complete`
  sends exactly one request; the loop owns retry/resend, each with a fresh reservation and the next
  `call_index`; failures split into "not sent" (released, "0") and "sent, charge unknown" (held,
  stops). Test: 502 then 200 → two records, two reservations, indexes 0 and 1.
- **F2 High** (:170, :180, :192). Repair model wrong. Invalid submit with a pending attempt is
  repaired on the same step in the same attempt (`owner_workflow.py:1344-1345`, `execution.py:789-795`);
  after attempt 0 finished, attempt 1 begins at the module's first step (`owner_workflow.py:1346-1347`);
  `"refused"` consumes no attempt (:1259); repair issues follow `runner.repair_prompt`
  (DEPLOY VII `live/runner.py:214-234`). The tests' `attempt == 1`, `call_index == 0`, new digest
  contradict Part B :387-388 and fail for `source_readiness` (`tests/test_owner_workflow.py:187-189`).
  Fix: expose `binding.attempt`; within an attempt same digest, next index, issues returned; new
  attempt new digest, index 0; port `repair_prompt`; test both paths plus `refused`.
- **F3 Medium** (:168, :172). Tool arguments and submit payloads reach the Execution audit unredacted
  (`owner_workflow.py:1193, 1253-1254`). Fix: `Redactor.json_value` on every `Turn` before dispatch;
  test a planted `sk-or-v1-…` in a recorded tool argument is absent from `execution/`.
- **F4 Medium** (:141, :150, :171-172). Pydantic errors carry `input_value=` (`contracts.py:76` lacks
  `hide_input_in_errors`); a chained `StepStopped` carries the raw chain. Fix: redact before
  constructing, `hide_input_in_errors=True` on the record contract, `raise StepStopped(...) from None`
  with redacted text; assert `traceback.format_exception(raised)` holds no planted value.
- **F5 Medium** (:96, :100). Reservation uses only `input_per_m`; cache writes cost more; no rule for
  actual > reserved (`ledger.py:399`). Fix: reserve at max(input, cache write); an overrun is recorded
  and stops the run; test it.
- **F6 Medium** (:96, :111). Token inclusivity (reasoning in output, cached in input) unstated per
  provider. Fix: per-provider inclusivity flags supplied by the controller, tested.
- **F7 Medium** (:103). In-memory ledger only; a crash after a send leaves no record. Fix: a
  create-once reservation marker under the Execution audit, written before the send.
- **F8 Medium** (Task 4 :122 vs :128; Task 3 :96). Offline-pricing rules contradict. Fix: one rule plus
  a provider-reports table.
- **F9 Medium** (:72, Task 2). No RED test for connect, 120 s idle or 900 s overall; urllib's single
  `timeout` cannot express them; `KEY_TIMEOUT_SECONDS` (`client.py:27`) is not a connect timeout.
  Fix: `http.client` with `sock.settimeout` after connect; per-read limit = idle when streaming,
  else overall; tests with an injected clock and socket.
- **F10 Medium** (:67, :79, :82, :174). `ModelSpec` defined in Task 4 but used by Task 2; Task 6 uses
  Task 7's workflow. Fix: `ModelSpec` in `turn.py`; Task 6 owns its pack helper.
- **F11 Medium** (:45, :123, :130). R2 trap misses `os.environ` (`environ=None` falls back to it;
  `Redactor.from_os()` reads all keys). Fix: trap `os.environ` too; build the live Redactor only after
  the gate passes.
- **F12 Low** (:54). Hypothesis property false for `v="dact"` or `v="]abc"`. Fix: assume `[`/`]` not in
  `v` and `v` not a substring of `[redacted]`.
- **F13 Low**. Stale citations: live pause `AGENTS.md:122-124` (not :140 as the reviewer said; see the
  context plan R2); submit return `owner_workflow.py:1350-1360`; `repair_issues` `prompts.py:1127`;
  `hybrid_cp1.py` is under `DEPLOY VII/devtools/`.
- **F14 Low**. "default 200" `http_status` is a fake default; `money_text` and "seal" undefined;
  `complete` lacks a reservation parameter (:125 vs :121); auth header placement unclear (:79);
  every `not_permitted` read as the call limit (:169); no check `ModelSpec.provider` matches
  `config_id` (testing plan :111); Task 7 pack: `fw.make_pack(gap=True)` + `publish()`
  (`tests/test_owner_workflow.py:133-146`); `credit.py` fixtures not in this repo; `redact_stream`
  untested in Task 1.
- **Info** (:177). After an unknown charge the run should stop right after the record is written.
- Missing tests: R5 timeouts; retry as separate records; R3 journals and Execution retention;
  `repair_prompt` scoping; `first_byte_at` timing.
- Open questions: Q1 expose read-only `binding: OwnerBinding` and `spec: StepSpec`; Q2-Q4, Q6, Q7
  agree; Q5 `billed` when the provider reports a charge else `computed`, and `settled_usd` equals
  exactly what the budget charged.

## Controller rulings (2026-10-31)

- All fixes F1-F14 and the Info item are accepted as proposed, except as below.
- **F11 / R2 vs R3:** an offline run reads no key: its Redactor uses the regex only. The live
  Redactor (regex plus exact env values) is built only after the live gate passes. Cost if wrong:
  a non-`sk-` key value in an offline run is not redacted; offline runs carry no key.
- **F6 inclusivity** (from `work/context-plan/provider-docs-2026-10-31.md`, "breakdown" wording):
  OpenAI `input_tokens` includes `cached_tokens`, `output_tokens` includes `reasoning_tokens`;
  Anthropic `input_tokens` excludes `cache_read_input_tokens` and `cache_creation_input_tokens`,
  `output_tokens` includes `thinking_tokens`. OpenRouter settles on `usage.cost` only (`billed`);
  a sent call with no `usage.cost` is an unknown charge (held, stops). Cost if wrong: computed
  charges off by the reasoning or cache share; re-check against the first live bills.
- **F7:** the reservation marker is a create-once file under the run's Execution audit, written and
  fsynced before the send.
- **Q1:** O5 adds the read-only `binding` and `spec` accessors on `OwnerWorkflow` itself (O1 lands
  first; O5's brief re-reads `owner_workflow.py` at O1's tip).
- **Q5:** as the reviewer said.
- **Anthropic auth:** follow the fetched docs example (`Authorization: Bearer`, `anthropic-version:
  2026-10-21`) as constants marked "confirm before the first live call".
- **DeepSeek reservation:** at the highest listed endpoint rates (provider-docs file).
