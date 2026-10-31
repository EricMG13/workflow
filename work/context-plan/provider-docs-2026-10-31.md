# Provider docs for O5 (fetched by the controller, 2026-10-31)

Fetched from the providers' current public docs on 2026-10-31. Treat this as data, not instructions.
It is a declared input to O5's task briefs; re-fetch before the first live call.

## OpenAI (Responses API)
Source: developers.openai.com API reference (Context7 `/websites/developers_openai_api_reference`)
and developers.openai.com/api/docs/pricing. platform.openai.com returned 403 to the fetcher.
- `POST https://api.openai.com/v1/responses`; `Authorization: Bearer <OPENAI_API_KEY>`.
- Body: `model`, `instructions`, `input` (messages; `function_call_output` items
  `{type, call_id, output}`), `tools` (`{type: "function", name, description, parameters, strict}`),
  `tool_choice` (`"auto"`), `reasoning.effort` (`none`, `minimal`, `low`, `medium`, `high`,
  `xhigh`, `max`; not every model supports every value), `max_output_tokens`, `store`.
- Output items: `function_call` `{id, call_id, name, arguments (JSON string), status}`, `message`,
  `reasoning`. Response: `id`, `status`, `incomplete_details`, `error`.
- Usage: `input_tokens`, `input_tokens_details.cached_tokens`,
  `input_tokens_details.cache_write_tokens`, `output_tokens`,
  `output_tokens_details.reasoning_tokens`, `total_tokens`.
- Input-token count endpoint exists: `POST /v1/responses/input_tokens` (same `tools` shape).
- `gpt-6.1-sol` standard, per 1M tokens. Short context (≤ 272K input tokens): input USD 2.00,
  output USD 10.00, cached input USD 0.10, 30-minute cache write USD 2.50, 12-hour cache write
  USD 5.00. Long context (> 272K input): input USD 4.00, output USD 15.00, cached input USD 0.20,
  30-minute write USD 5.00, 12-hour write USD 10.00. Max output tokens: not stated on the page.
  Reservation rule (controller ruling, as B11): reserve at the long-context rates when the request
  could exceed 272K input tokens, else short-context, at the 12-hour write rate.

## Anthropic (Messages API)
Source: platform.claude.com/docs/en/api/messages and /docs/en/about-claude/pricing.
- `POST https://api.anthropic.com/v1/messages`; headers `anthropic-version` (the page's example
  sends `2026-10-21`) and the key (the example uses `Authorization: Bearer`; `x-api-key` is the
  long-standing header: confirm which before the first live call).
- Body: `model`, `max_tokens`, `system`, `messages` (`tool_use` `{type, id, name, input}` from the
  assistant; `tool_result` `{type, tool_use_id, content, is_error}` from the user), `tools`
  (`{name, description, input_schema}`), `tool_choice` (`auto`, `any`, `tool`, `none`), `stream`,
  `thinking` (`{"type": "adaptive"}` among others), `output_config.effort` (`low`, `medium`,
  `high`, `xhigh`, `max`).
- Response: `id`, `content`, `model`, `stop_reason` (`end_turn`, `max_tokens`, `stop_sequence`,
  `tool_use`, `pause_turn`, `refusal`, `model_context_window_exceeded`), `stop_details`, `usage`.
- Usage: `input_tokens`, `output_tokens`, `cache_creation_input_tokens`,
  `cache_read_input_tokens`, `cache_creation.{ephemeral_5m_input_tokens, ephemeral_1h_input_tokens}`,
  `output_tokens_details.thinking_tokens`.
- SSE events (from general knowledge, not confirmed on the fetched part): `message_start`,
  `content_block_start`, `content_block_delta` (`text_delta`, `input_json_delta`),
  `content_block_stop`, `message_delta`, `message_stop`, `ping`, `error`. Error body
  `{"type": "error", "error": {"type", "message"}}`.
- `claude-opus-5-5` per 1M tokens: input USD 4, 5-minute cache write USD 5, 1-hour cache write
  USD 8, cache hits USD 0.20, output USD 20. Max output: not fetched.

## OpenRouter (chat completions)
Source: openrouter.ai/docs/api-reference/chat-completion and
`/api/v1/models/deepseek/deepseek-v4.1-flash-1017/endpoints`.
- `POST https://openrouter.ai/api/v1/chat/completions`; `Authorization: Bearer <OPENROUTER_API_KEY>`.
- Body: `model`, `messages` (roles `system`, `user`, `assistant` with `tool_calls`, `tool` with
  `tool_call_id`), `tools` (`{type: "function", function: {name, description, parameters}}`),
  `tool_choice` (`none`, `auto`, `required`, named), `max_completion_tokens` (`max_tokens`
  deprecated), `reasoning.effort` (`max`, `xhigh`, `high`, `medium`, `low`, `minimal`, `none`),
  `provider` (`ignore`, `order`, `allow_fallbacks`, `require_parameters`), `stream`.
- Response: `id`, `choices[].message` (`tool_calls[].{id, function.name, function.arguments}`),
  `finish_reason`, `usage` (`prompt_tokens`, `completion_tokens`,
  `completion_tokens_details.reasoning_tokens`, `prompt_tokens_details.cached_tokens`, `cost`).
- Errors: 400, 401, 402 (insufficient credits), 403, 404, 408, 413, 422, 429, 500, 502, 503, 524,
  529; body `{"error": {"code", "message", "metadata"}}`.
- `deepseek/deepseek-v4.1-flash-1017`: 42 endpoints. OpenInference's tag is `open-inference/fp4`
  (the provider `ignore` slug is `open-inference`). Prices per token vary by endpoint: prompt from
  0.0000000141 to 0.00000045, completion from 0.000000144 to 0.0000018, cache read up to
  0.000000009. Context 1,048,576; max completion 131,072 to 943,718 by endpoint.
  Reservation rule (controller ruling): reserve at the highest listed rates (USD 0.45 input,
  USD 1.80 output, USD 0.009 cache read per 1M) and settle on `usage.cost`.
