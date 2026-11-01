# Recon: Deploy Workflow model seam and harness (2026-10-31, mx-autonomous, read-only, HEAD 3888fe0)

## Model seam
- **No model is wired today.** Runs are Python replays of recorded submissions through the public `OwnerWorkflow` methods (`tests/czr_runs.py:253`, `tests/s1a_runs.py`, `tests/cp*_runs.py`).
- **Owner path** (`owner_workflow.py`): `invoke` :1168, `read_inputs` :1198, `submit_review` :1218, `publish` :1368, `write_receipt` :1459, `serve_json_lines` :2433, `main` :2484.
  - Frames: `{"operation":"invoke","tool","arguments"}`, `read_inputs`, `submit_review` (payload is a raw JSON string), `publish`, `write_receipt`.
  - Refusal codes: not_permitted, bad_arguments, stale_binding, identity_mismatch, unavailable, render_refused, internal_error.
  - 21 plan modules. CP-1B is not in the plan.
- **Financial path:** `financial_workflow.py:1531`, the same protocol plus `publish_model`, for CP-1 and CP-MODEL only.
- **Earnings path (CP-1B):** `earnings_workflow.py:4257`. Frames use the key `"op"` (state, invoke, read_inputs, submit_review, close) and replies are `{"status":"ok","result"}`. There is no CLI.
- **Tools:** `host.SourceSession.invoke` (host.py:1057) offers `search_pack`, `read_pages` and `extract_statements` (financials only). Each returns a `tool-receipt/1` envelope.
- **Specs and prompts:**
  - `deploy_vii/live/tools.py:226` `tool_specs(step_id)` emits OpenAI strict function specs (`live/schema.py`).
  - `live/prompts.py:1120` `build()` assembles prompts, but only for the `STEPS` (`live/submission.py:246`).
  - The 13 owner-only modules have **no prompt**: CP-1C, CP-1D, CP-2A/D/E/G/H, CP-3C/D, CP-4C, CP-8, CP-DR, CP-L10. Their schemas are the `StepSpec.schema` contracts (owner_workflow.py:259).
- **What an adapter must do:**
  - Build a prompt per step and offer the tools (plus `read_inputs` when inputs ≠ none, which must be read before submit) and one submit tool with the step schema.
  - Map tool calls to invoke, read_inputs and submit.
  - Track the step. There is no state operation; the binding module and step come back in replies, and submit returns `next_step`.
  - Handle the two-tries-per-attempt limit (`execution.py:775-782`).
  - Emit the real pack hash and figure bindings that recorded cases fill in as placeholders (`<<PACK_SHA256>>`, `{{FIG:name}}`).

## Limits
- `MAX_LINE` 4 MiB.
- `MAX_CALLS` 16 per (ticket, step, op).
- **`MAX_MESSAGES` 128 per owner/financial JSONL session for the whole run**, which is too few for a multi-module run. Earnings allows 2048.
- Tool caps (`live/tools.py:93-99`): read 5 pages, extract 8 pages, 15 hits, 300-character snippets. Earnings pages are cut at 8 KiB.
- Replies are not size-capped: the CP-1 quality read is 16.9–21 MB. U4 approved `quality_scope`; not implemented.
- H05: a lone-surrogate or deep frame poisons the session (open).

## Provider code and the pause
- **No HTTP client in src.** The DEPLOY VII OpenRouter runner (client, credential, ledger, loop, runner) was deliberately excluded (`docs/reuse/manifest.json` `excluded_python_modules`).
- `live/settings.py` expects a `settings/project.toml` `[model_tests]` section (candidates, effort ladder, spend caps). The file is absent and unused.
- **The live-testing pause is in force:**
  - `AGENTS.md:122-124`: "Live/paid/provider testing remains paused … no credential discovery or provider calls".
  - Also in README, PLAN.md:19/171/192, `docs/RUN-GUIDE.md`, `docs/QUEUE.md:15` and `docs/PRODUCTION-BACKLOG.md:6/14`.
  - The pytest marker `live` is "paused".
  - No ruling lifts it.

## Recording
- **Captured:** the hash-chained `ExecutionSnapshot`, attempts and step outputs, and audit blobs (begins, refused-begin, calls with full receipts, input-reads, bindings, submissions, payloads, publications). `OwnerRunReceipt` is verified by `verify_owner_run_receipt`.
- **Not captured:** timestamps, latency, tokens, model id, cost, raw transcripts. The owner JSONL keeps no raw lines.

## Cases
- 58 synthetic manifests and 1 public case (CZR).
- **Owner oracles:** `cases/*-owner/{manifest,submissions,expected}.json` plus `builder/build.py` (150 KB–2 MB each).
- **CZR:** real filings (about 590 KB) in `cases/czr-2026q2-earnings-update/documents`, with `expected.json` and `qualification.json`. Only `submissions-partial.json` exists, blocked at CP-1 QA 39.
- **Runners:** `tests/czr_runs.py` (`make_pack`, `czr_closed`), `tests/s1a_runs.py` (CP-0→CP-MODEL), `tests/cp*_runs.py`. There is no CLI that builds a pack from a manifest.
- **Delivery:** `owner_rendering.render_owner_slice` :954 and `verify_owner_rendered_slice` :939.

## Gates and rules
- No Makefile, CI or pre-commit.
- **Commands:** `.venv/bin/python -m pytest -q -p no:cacheprovider`, ruff check/format, mypy strict, `python3 -I cases/pins.py --check`.
- **src/deploy_vii** changes need the user's word plus a D12 `post_import_patches` record. New code goes in `src/deploy_workflow`.
- **Dependencies:** pydantic, pypdf, openpyxl only. A new dependency needs a decision record; stdlib urllib avoids that.
- Ledger lines are required (AGENTS.md:126-131).

## Likely blockers for a live run, in order
1. The pause rule: a user ruling and a credential-handling rule are needed.
2. No client, turn loop or settings exist.
3. The 128-message cap and the missing state operation: drive the Python API in-process, or change the transport (shared interface).
4. No prompts or schemas for the 13 owner-only modules.
5. The uncapped quality read (U4).
6. Strict-schema quirks per provider (`live/schema.py` handles OpenAI only).
7. Placeholders and the two-tries limit.
8. CZR QA blocks (U3) and the CP-1 defects (H01/H02/H08, D1–D3): a synthetic baseline is needed.
9. The recording gap: the adapter must journal what the store doesn't keep.
10. H05 poisoning and the 4 MiB request cap.

## Not verified
No code was run. The size figures come from CONSOLIDATED.md. The Codex package was only skimmed.
