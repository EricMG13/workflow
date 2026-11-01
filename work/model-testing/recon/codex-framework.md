# Recon: Codex evaluation framework (2026-10-31, mx-autonomous, read-only)

Source tree: `/Users/ericguei/.codex/worktrees/deliverable-design/Deploy Workflow` (branch `codex/deliverable-design`, on 05c3b27). Two commits add `native_runner.py`. Every other evaluation module is untracked, and the tree is still being edited.

## Headline
- It has never run the real workflow end to end with a model. All 432 cells are `research_only` and none is runnable.
- The furthest a live model got is CP-0 `source_readiness`.
- OpenAI was only tested with a protocol smoke (USD 0.00117).
- There is no Anthropic or OpenRouter adapter.

## Architecture
`broker.py` is an allowlist gate over `OwnerWorkflow`: invoke, read_inputs, submit_review, publish, write_receipt, with time and request limits and 2 repairs.

Three modes (`native_runner.py:73`):
- `analytical_api`: `ResponsesProvider` plus `run_api_workflow`. The model returns one JSON `{operation, arguments}` per turn, with no native tool calling.
- `supervised_coding_agent`: Codex `collaboration.spawn_agent` only.
- `offline_synthetic_native_control`.

Each run is a spawned child process with a 1800 s deadline.

`journal.py` writes an append-only, hash-linked JSONL journal with SHA-256 blobs and refuses credential headers. It re-reads under flock, which is O(n²).

A cell is case × variant × parser × effort × rep × mode, 432 in all.

## Module verdicts (24.5k src lines, 18.1k test lines, 659 tests)
- **Reuse as-is:**
  - `journal` (124)
  - `scoring` (57; Decimal cost; 30/25/15/15/10/5 rubric)
  - `corpus` (339)
  - `readiness` (415; 4Q+FY)
  - `fault_registry` (543)
- **Reuse with changes:**
  - `contracts` (337; TokenUsage assumes OpenAI's cached-subset rule)
  - `broker` (568)
  - `campaign` (90)
  - `native_context` / `native_admission` (536 / 415; CP-0 only)
  - `parsing` / `dpp` / `units` (the current arm is PDF only)
  - `reporting` (1294)
  - `judgments` / `review_packets` / `native_packets` (heavy; CP-1 only)
  - `input_catalog` / `quality_projection` / `input_discovery`: paged QualityInputs, the start of the 21 MB fix. **Not imported anywhere.**
  - `collection_cli`
- **Rewrite:**
  - `providers` (1259; OpenAI-only, hard-coded endpoint, model and prices; salvage the token-count preflight, budget reservation, no-redirect HTTPS and key-reflection guard)
  - `pairing` (875)
  - `native_runner` (3741)
  - `execution_manifest` (2095)
  - `campaign_budget` (small)
- **Drop:**
  - `codex_cli_provider`
  - `agent_session`, `session_host`, `instruction_transport`, `transport_profiles`
  - `public_attempts` (coupled to an uncommitted `owner_workflow` CP-6 edit that imports the evaluation package)

## Observability
- **Per call:** request and response ids, HTTP status, requested vs observed model and effort, TokenUsage (input, cached, cache_write, output, reasoning), count/request/generation/total durations, `reserved_usd`, `cost_estimate_usd`. Billed cost is always null.
- **Cost:** a `/v1/responses/input_tokens` preflight, then a reservation of input × max rate + max_output × output rate. Any error sets `_unknown_charge` and stops further calls.
- **Faults:** `fault-registry.json` holds 40 entries.

## OpenAI request shape (providers.py:498-507)
- `model: "gpt-6.1-sol"`, `reasoning.effort` medium or high, `instructions` (step context JSON).
- `input` is the full accumulated conversation with tool results inlined.
- `max_output_tokens` ≤ 16384, `store: false`, `service_tier: "default"`, `text.format = json_object`.
- **Limits:** a 1,000,000-byte request cap and < 272,000 input tokens. The 45 s per-call timeout (60 s maximum) is likely too short for high effort.
- **Failure handling:** no retries. 401, 429 and 5xx stop the run.
- **Key:** `OPENAI_API_KEY` only.

## Corpus (cases/public_evaluation/sources/manifest.csv)
- 38 rows, about 71 MB, from SEC EDGAR:
  - 26 10-Q/10-K HTML filings, 4Q+FY each for TDG, SHC, BGS, LTH, IHRT and NATL (NATL FY2024 is a 10-K/A from 2025-11-05);
  - 1 TDG FY2024 annual-report PDF (160 pages);
  - 10 legal/event HTML documents;
  - 1 failure (SHC IR page, HTTP 403; the SEC copy was used instead).
- Six history reviews are approved.
- **Not usable today:** preparation accepts txt, PDF and xlsx only (`src/deploy_vii/preparation.py:29-32`). There are no packs and no financial oracles. An untracked `public_preparation/core.py` (1165 lines, `prepare_html`) is unreviewed.

## Parser artefacts worth keeping
- `parser-comparison.md`, `final-frozen-parser-speed.*`, `fullannual-parser-trial-record.json`
- the Docling requirements and model artefacts
- `cases/public_evaluation/gold/tdg-annual-smoke/` (15-cell gold)
- `dpp-contract/`
- 160-page PDF results:

| Parser | Time | Numbers matched | Exact printed text |
|---|---|---|---|
| Current | 2.42 s | 15/15 | 6/15 |
| Docling | 177.8 s | 15/15 | 15/15 |
| DPP | not timed | 15/15 | 15/15, provisional |

## Blockers
- **21 MB quality read vs the 1 MiB result cap**, and on the API path vs the 1 MB request and 272k-token limits. The fix is paged reads (`input_catalog`), which are built but not wired.
- Large native artefacts were fixed by 100 MiB streaming.
- Missing JSON-mode instruction → HTTP 400.
- An observer serializer failure lost one response, so its cost is unknown.
- Disk full.
- HTML is not supported by preparation.

## Gates and coupling
- **Gates:** the last full run (06:43Z) had 774 passed, with ruff and mypy clean. Since then 6 modules were added and 12 changed, so the current full status is unknown.
- **Coupling:** it imports private product symbols (`owner_workflow._hist`, `financial_workflow._snapshot` and `._evidence_issues`, `live.prompts._context_body`). All still exist at Claude HEAD; their signatures were not checked.

## Not verified
- The suite on the current tree.
- Module quality beyond structure, imports and test counts.
- The signatures of those private symbols.
- `public_preparation/core.py`.
- The Anthropic and OpenRouter shapes.
- SEC reuse terms.
