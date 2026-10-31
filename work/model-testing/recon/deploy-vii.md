# Recon: DEPLOY VII live-model infrastructure (2026-10-31, mx-autonomous, read-only)

**A2B** = DEPLOY VII `.claude/worktrees/agent-a2b34b93ed9b7ad1a` (commit 6441553), the source of Deploy Workflow's pinned subset and the most complete live code. DEPLOY VII main (be92508) lacks `loop.py`, `tools.py` and `schema_check.py`.

**Rules:**
- Deploy Workflow `AGENTS.md:122-123` (pause) and `:150-152`: "Do not copy old provider drivers, ledgers, credentials, experimental launchers". Any import needs a named need, the source commit and hash, and a review.
- DEPLOY VII must never be edited.

## Providers
- **OpenRouter client**, A2B `src/deploy_vii/live/client.py` (690 lines):
  - `ChatClient.complete` with an injectable transport (stdlib urllib; https only; no redirects).
  - Every request pins `provider: {allow_fallbacks:false, require_parameters:true}`.
  - Tools go in `tools`/`tool_choice`.
  - Result classes: ok, fallback, truncated, http_error, insufficient_credit, timeout.
  - `parse_usage` returns null with a reason when a field is missing (never zero) and reads `usage.cost` as a Decimal.
  - The key and account id are scrubbed from errors.
  - Timeout: 600 s with a wall-clock deadline via `read1`.
- **Retries:** the one-shot runner never retries. `loop.py` retries a transient failure once and waits out an in-flight 402 once.
- **Budget:**
  - `live/ledger.py`: append-only JSONL with fsync and lock, Decimal money, reserve/settle/adjust. The cap is bound when the file is first opened. An unknown cost stays fully reserved.
  - `runner.reservation_usd`.
  - `catalog.py` pins prices from `/models` at the maximum override.
  - `credit.py` handles 402s and the key endpoint; `reconcile.py` handles the generation endpoint and the usage delta.
- **Anthropic:** only in A2B `devtools/hybrid_cp1.py` (1,993 lines):
  - Messages API, streamed over SSE (`urllib_stream` :413, `assemble` :494).
  - Body (:563-579): `thinking: {type: adaptive}`, `output_config.effort`, top-level `cache_control: ephemeral`, `tool_choice` any falling back to auto.
  - Idle limit of 120 s between stream bytes.
  - List prices: Opus 5.5 at 4 / 5 / 8 / 0.20 / 20 USD per M tokens.
- **Model ids used then:** `openai/gpt-6.1-sol` (via OpenRouter), `deepseek/deepseek-v4.1-flash-1017`, `claude-opus-5-5`.
- **Keys:** `live/credential.py` converts the RTF with textutil and picks the `sk-or-` token; Anthropic takes the `sk-ant-` token from the same file. **Ignore this**: it is credential discovery. Use explicit environment keys.

## Harnesses
- **Replay corpus:** `tests/product/replay/<step>/*.json` (15 entries), `replay_support.py`, transcripts in A2B `tests/product/replay_transcripts/`.
- **Recorded provider failure bodies** in `tests/product/fixtures/live/` (7 files): DeepSeek 504-inside-200, Luna and Sol 400 `invalid_json_schema`, a generation example. Reuse these for offline tests.
- `tests/product/live_support.py` (fake transports) and `tests/devtools/test_loop_differential.py`.
- **Hybrid harnesses** `devtools/hybrid_cp0.py` and `hybrid_cp1.py`: cells are model × provider × effort on a frozen CP-0 journal, each submit judged by the trusted validators. They record completeness and shrinkage, per-provider ledgers, an ignore-provider list, `plan.json` and `batch-summary.json`.
- **Extraction benchmark** (worktree `serene-rubin-4e1c84`, `claude/extraction-benchmark` 5511dd4):
  - `tests/product/extraction_bench.py` builds a synthetic PDF with one failure class per page (two-column, straddle, hyphen, OCR) and scores with `deploy_vii.quotes.quoted`.
  - Result: pypdf-layout adds about 60% whitespace tokens and fails the column cases; pdftotext fixes columns but breaks hyphen wrap.
  - The live arms were never concluded.

## Observability
- **Per attempt:** `artifacts/model-tests/<exp>/<case>/<model>/<attempt>/` holds `manifest.json`, `request.json`, `response.json`, `output.md`, `events.jsonl`, `metrics.json`, `checks/` and `render/`, plus `tool-calls.jsonl`. The manifest is written last.
- **Per batch:** account usage before and after, a Markdown report, ledgers.
- The layout is documented in `docs/testing-and-telemetry.md:70-98`.
- There is no dashboard.

## Corpus
- One real issuer: Caesars FY2025 10-K (`source-packs/caesars-fy2025-v1`, 195-page PDF, 2.2 MB), prepared pack `artifacts/public-case/czr-fy2025-v2/pack.json`, and execution journals (including a Docling variant).

## Lessons (`live-probe-{2,4,5}-analysis.md`, `docs/development/live-runner.md:1177-1236`, `hybrid-cp1-probe.md`, `hybrid-cp0-candidates.md`)
- **Errors and timeouts:**
  - OpenRouter sends 200 early with whitespace padding, then reports a failure inside it (DeepSeek 504 at about 300 s, or `choices[0].error` with finish_reason "error"). Parse both.
  - The urllib timeout is per socket operation, so padding defeated it (1,029 s against 600 s). Use a wall-clock deadline.
  - A deadline expiry leaves no generation id, so the reservation stays held.
- **Schemas:** OpenAI strict mode needs every property in `required`; pydantic omits defaulted fields, giving 400 `invalid_json_schema`. `live/schema.strict_schema` (pinned) fixes it.
- **Prompt size:**
  - A full 10-K is about 154k tokens at a measured 5.6 bytes per token.
  - A raw 8 MB financials output could not be sent. Bounded projections and pack tools replaced it.
- **Token budgets:**
  - 16k max_tokens truncated Sol and MiMo financials, because reasoning consumes the budget. Use 128k.
  - DeepSeek reports reasoning tokens greater than completion tokens.
- **DeepSeek routing:** through OpenInference it gave 429, 504, 502 and payloads as plain content. With `provider.ignore: ["open-inference"]`, Relace served 4/4 at about US$0.035 per draw.
- **Anthropic:**
  - `tool_choice` any or tool gives 400, so fall back to auto.
  - The 5-minute cache misses after calls longer than 300 s.
  - Sonnet at max spent all 30 calls without submitting.
  - Cost is computed, not billed.
- **Retries:** one transient retry, because a mid-stream 502 lost a draw.
- **Caching:** the first draw cost US$0.42, later draws about US$0.07. Report cached and uncached draws separately.
- **Quality:**
  - Models copied bracketed locators, cited pages off by one, stitched columns together and quoted across page breaks.
  - Sol medium transcribed one fiscal year where Sol high gave three, so acceptance alone does not measure quality.
  - Whether a provider honoured the effort setting cannot be observed.
- **Observed costs on CP-1 (hybrid):** Sol medium US$2.07, Sol high US$2.99, Opus medium US$9.46 (computed). Sol medium on CP-0 about US$0.12.

## Reuse verdicts
| Component | Path | Verdict |
|---|---|---|
| OpenRouter client | A2B `src/deploy_vii/live/client.py` | reuse with changes (client only; needs the pause ruling and an import record) |
| Recorded failure bodies | `tests/product/fixtures/live/` | reuse |
| Anthropic SSE adapter | A2B `devtools/hybrid_cp1.py` :402-850 | reuse with changes (extract; refresh prices from current docs) |
| Key loader | `live/credential.py` | ignore (credential discovery) |
| Ledger / reservation | `live/ledger.py`, `runner.reservation_usd` | reuse with changes |
| Catalog / draw / cohort / credit | `live/*` | ignore; the generation reconcile is useful for OpenRouter only |
| Retention layout | `live/retention.py` | reuse |
| Tool loop | A2B `live/loop.py` | reuse with changes (limits, retry, nudge) |
| Strict schema, projections, prompts | pinned `live/{schema,context,prompts}.py` | already present |
| Replay corpus | `tests/product/replay*` | reuse the pattern |
| Extraction benchmark | `serene-rubin` `extraction_bench.py` | reuse with changes |
| Hybrid cell design | `devtools/hybrid_cp0/1.py` | design only |
| Caesars pack and journals | `source-packs/`, `artifacts/public-case/czr-fy2025-v2` | reuse |

## Not verified
- No tests were run.
- `loop.py`, `runner.py` and `cli.py` were read only through their docstrings and greps.
- Model ids, prices and API parameters are as recorded on 21–24 Oct; fetch current docs before any brief.
