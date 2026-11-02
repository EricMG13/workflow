# PF1 review: pilot fixes (gpt-6.1-sol cache-write rate, prompt_cache_options, read_pages line-source window)

- **Range:** e8e364ea..b6b3889a on `claude/pilot-fixes`.
- **Reviewer:** mx-adversary, one seat (B33) covering money, the provider request, and the src/deploy_vii tool bound (B31a, PF-R7/PF-R9).
- **This file:** written by the controller from the reviewer's returned text.
- **Rulings:** PF-R1 to PF-R9 in the lane ledger.

**Verdict: APPROVE** (H0 M0 L2 I4).

## Findings
- **L1. Stale comment.** `src/deploy_workflow/model/pricing.py:107-108` says the 30m tier applies because "the request never sets it". Since 206f75a7 the OpenAI body sends `prompt_cache_options` (`providers.py:234`). The rate is right; the stated reason is not.
  - Fix: cite `providers.OPENAI_PROMPT_CACHE_OPTIONS` (PF-R6).
  - Probe: `p07_stale_sol_comment.sh`, exit 1.
- **L2. Three boundary mutants of read_pages survive `tests/test_line_locators.py`.**
  - A: `>=` at `tools.py:447`.
  - C: `>=` at `:454`.
  - E: `len(span.text)` instead of UTF-8 bytes at `:450`.

  The code is correct (p02). The key's `#measure` and the exact limits lack a runnable comparison.
  - Fix: three key-reading tests: 200 lines within the byte bound are allowed; more than 5 lines totalling exactly 8192 bytes are allowed; characters ≤ 8192 < bytes is refused.
  - Probe: `p03_boundary_mutants.py`, exit 1 (A, C and E survive).
- **I1. The 12h split is ignored when pricing.** A reply with `ttl_12h_tokens` > 0 would be priced at 2.50 (p06, exit 1). This is unreachable while the request pins `ttl: "30m"`, which is tied to `#sol/write_tier_priced` by test (d). Confidence is about 85-90%; the residual risk is provider behaviour. Optional hardening: make the charge unknown on `ttl_12h_tokens` > 0.
- **I2. Scope range.** The brief's claim that `scope --role builder c69b0052 b6b3889a` passes does not hold: that range includes the oracle commit 5aca9093. The two builder ranges pass, and so does per-commit (p08).
- **I3. Test (n) can hang rather than fail** if the unbounded loop returns. There is no pytest-timeout, so only the CI job timeout would catch it.
- **I4. Existing behaviour.**
  - A read of 5 or fewer lines is unbounded in bytes (five 1 MB lines return about 5 MB).
  - A 200-short-line read returns about 33 KB including framing.

## Checks that hold
- **Money.**
  - 2.50 equals 1.25 × 2.00 for ≤ 272K.
  - The formula counts writes once. The pilot charges recompute to 0.0151735 and 0.015241.
  - The reservation is ≥ the charge over 3000 hypothesis mixes (equal at 272K all-write).
  - Unlisted rates, and over 272K, are unknown (p05).
- **Request.**
  - The field is on sol bodies only and is copied per body from a `MappingProxyType`.
  - A 400 is `SENT_CHARGE_KNOWN`.
  - The invocation digest is independent of the body (p04).
- **Tool bound.**
  - Huge `last` values, 201-line ranges, bad types and reversed ranges are refused at once.
  - Page sources are unchanged.
  - A mixed source takes the page path.
  - Refusals record nothing.
  - Output is at most 200 blocks and at most 8192 bytes of line text (p02).
- **Keys.** Tests (a)-(n) read the keys at test time. The PF-R8 edit still asserts the line-source refusal. The prompts and golden are byte-identical to e8e364ea.
- **D12.** Every sha recomputes, and the nine tools.py records chain (p01).
- **Quality.** No new except, suppression, stub or catch-all.

## Probes
Folder: `scratchpad/pf1-review/probes/`.

| Probe | Exit |
|---|---|
| p01_d12_chain | 0 |
| p02_read_window_bounds | 0 |
| p03_boundary_mutants | 1 (L2) |
| p04_cache_option_request | 0 |
| p05_sol_money | 0 |
| p06_sol_12h_split | 1 (I1) |
| p07_stale_sol_comment | 1 (L1) |
| p08_scope_ranges | 0 |

## Tests the reviewer ran
- pricing, providers and line_locators: 143 passed.
- prompts/test_tools, model/test_adapter and model/test_record: 256 passed.

## Not verified
- Live acceptance of `prompt_cache_options`, and whether the 12h split can be reached.
- ruff, format and mypy (the controller ran them: 0).
- The controller's broader GREEN set.
- The offline replay gate (model-testing ran it: pass).
