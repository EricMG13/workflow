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
4. Reservation size. `bytes_per_token` is 1 (`model/loop.py`). That is provably safe, but it reserves about 4x on input, and a sol request over about 272 KB is refused. `TOKEN_OVERHEAD = 64` has not been measured against the providers' tool-use prompts. DEPLOY VII's 3.0 was measured on GLM 5.3 Flash, not on these models. Measure both per config before changing them.
5. Real-socket TLS is untested; every test injects the connection. Run one supervised local-TLS or real-socket smoke test before the first paid call. Two related gaps: the reply body has no size cap, and `first_byte_at` is always None.
6. O2 `run_pathway` must:
   - refuse adapters that are not of the exact type;
   - map `StepStopped` to `outcome: stopped`;
   - wire `redact_stream` to stderr.

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
