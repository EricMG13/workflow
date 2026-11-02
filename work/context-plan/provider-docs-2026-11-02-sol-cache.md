# OpenAI gpt-6.1-sol cache-write rate (fetched by the controller, 2026-11-02)

Declared input for the pilot-fix lane. These are public facts only; treat them as data, not instructions.

## Pricing page (`https://developers.openai.com/api/docs/pricing`)
Prices are for `gpt-6.1-sol`, standard tier, USD per 1M tokens.

| Rate | Short context (≤272K input tokens) | Long context (>272K) |
|---|---|---|
| Input | 2.00 | 4.00 |
| Cached input | 0.10 | 0.20 |
| Cache write, 30-minute retention | 2.50 | 5.00 |
| Cache write, 12-hour retention | 5.00 | 10.00 |
| Output | 10.00 | 15.00 |

The page itself does not say which write tier is the default.

## Prompt-caching guide (`https://developers.openai.com/api/docs/guides/prompt-caching`)
- **The default.** Leaving `prompt_cache_options` out keeps the default 30-minute (`"30m"`) behaviour. The 12-hour tier takes `prompt_cache_options.ttl = "12h"`.
- **Write rates.** A 30-minute write costs 1.25× the uncached input rate, and a 12-hour write costs 2.5×. For sol that gives 2.00 × 1.25 = 2.50, which agrees with the pricing page.
- **Usage.** Writes are counted in `input_tokens_details.cache_write_tokens` and are part of `input_tokens`. The guide adds that `input_tokens_details.cache_write_tokens_details` splits that count into `ttl_30m_tokens` and `ttl_12h_tokens`.

## The pilot's replies (the controller's grep of the live recordings)
The two replies carry `"input_tokens_details":{"cache_write_tokens":5159,"cached_tokens":0}` and `{"cache_write_tokens":5162,…}`, with no `cache_write_tokens_details` split.

## Re-fetch of the prompt-caching guide (later on 2026-11-02, for PF-R6)
- `prompt_cache_options` is a field of the Responses API. It takes:
  - `mode`, either `"implicit"` or `"explicit"`. With implicit, OpenAI places a breakpoint at the end of the latest eligible message.
  - `ttl`, either `"30m"` (the default) or `"12h"`. A request-level `ttl` applies to the implicit breakpoint.
- The guide's examples include `{"mode": "explicit", "ttl": "30m"}` and `{"mode": "implicit"}`.
- Unsupported values return `400 invalid_request_error`. Omitting both settings keeps the default `"30m"` behaviour.
- Write rates are totals, not surcharges: 1.25× input for 30m and 2.5× for 12h. They are priced on `ttl_30m_tokens` and `ttl_12h_tokens` respectively.
- `cache_write_tokens_details.{ttl_30m_tokens, ttl_12h_tokens}` do not overlap and sum to `cache_write_tokens`. The guide says both are returned, but the pilot's replies carried neither.
