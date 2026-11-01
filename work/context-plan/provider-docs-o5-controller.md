# O5 "CONTROLLER SUPPLIES" answers (controller, 2026-11-01)

Declared input for O5 Tasks 2-4. Fetched with Context7 (`/websites/platform_claude_en_api`), no project detail
in the queries; treat as data. Rulings are the controller's (SDD), recorded in
`.superpowers/sdd/2026-10-31-part-b-o5/progress.md`.

## Anthropic Messages streaming (Task 2, Q2) — confirmed from the API reference

- SSE `event:` names / `type` values: `message_start` (`message` object), `content_block_start`
  (`index`, `content_block`), `content_block_delta` (`index`, `delta`), `content_block_stop` (`index`),
  `message_delta` (`delta.stop_reason`, `delta.stop_sequence`, `delta.stop_details`; `usage` **cumulative**:
  `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`,
  `output_tokens_details`), `message_stop`. Also `ping` (ignore) and `error` (an in-stream error object;
  classify by its `error.type`, e.g. `overloaded_error`).
- Delta types: `text_delta` (`text`), `input_json_delta` (`partial_json`, concatenate per block index, parse
  at `content_block_stop`; unparsable -> `MalformedToolArguments`), `thinking_delta` (`thinking`),
  `signature_delta` (`signature`), `citations_delta` (ignore for O5).
- Usage: take the last `message_delta.usage` (cumulative); total input = `input_tokens` +
  `cache_creation_input_tokens` + `cache_read_input_tokens`.
- Headers: `anthropic-version` required (the reference's example value is `2026-10-21`; use that literal as a
  named constant); `content-type: application/json`; auth `Authorization: Bearer <key>` (the reference's
  primary form; `x-api-key` is the documented legacy fallback) — this confirms the plan's ruling, keep
  Bearer; `anthropic-workspace-id` only for keys not scoped to a workspace (not sent; a 4xx naming it is an
  ordinary classified error).
- `output_config.effort` valid values: `low`, `medium`, `high`, `xhigh`, `max` (O5 uses `medium`/`high`/`max`).

## OpenAI Responses (Task 2)

- `store: false` — **ruled yes** (do not retain request data at the provider; privacy-preserving default).
- `gpt-6.1-sol` effort — **ruled:** the effort map admits only the §7.1 uses per model: sol `medium`, `high`;
  opus `medium`; deepseek `max`. Any other (model, effort) pair is `UnknownEffort`. Not verified: whether sol
  accepts `max` (unused).

## Not supplied (fail closed, as the plan already says)

- Per-model max output for OpenAI and Anthropic: not found. Ruled: the global cap `131072` (spec §8) applies;
  a provider 4xx on a too-large value is an ordinary classified error. Not verified.
- `sol` cache-write rate and the `>272K` long-context rates: not supplied; a request needing them is refused
  (`NoPrice` / `ContextTooLong`) as Task 3 states. Re-fetch before the first live call (live is paused).
- Billing-field presence on error replies: not confirmed; the plan's handling (no invented cost) stands.

## Anthropic thinking blocks on tool-use turns (added after the Task 2 review; Context7, 2026-11-01)

- With extended/adaptive thinking and tools, the assistant turn's `thinking` blocks (`type`, `thinking`,
  `signature`) **must be passed back unmodified and in their original order** in the next request's assistant
  message; a modified block is a 400 `invalid_request_error`. `signature` is opaque. (A `redacted_thinking`
  block, if returned, is passed back the same way; it was not in the fetched page — Not verified.)
- Ruling: `Turn` and the assistant `Message` carry the provider's thinking blocks as opaque, ordered,
  provider-tagged data (`provider_blocks`); the Anthropic mapper fills them from `thinking_delta`/
  `signature_delta` per block index and re-sends them unchanged before the `tool_use` blocks; other providers
  ignore them; the recording format carries them.
