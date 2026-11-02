# Ruling 2026-11-02: model-testing live provider calls

The user's words, verbatim, relayed by the MANAGER session (local_06d37a3a-90ff-4543-9723-12df2e8aeaa0):
"approve offline and live testing"

This ruling lifts the live-provider pause for the model-testing framework (Plan B), for the four configurations of
spec §7.1 (`docs/superpowers/specs/2026-10-31-model-testing-design.md`).

lifts: live-provider-pause
by: user
date: 2026-11-02
configs: sol-medium sol-high opus-medium deepseek-max

Scope and budget, as relayed by MANAGER under spec §7.2:
- The pilot comes first: earnings_update on all four configurations. After it, re-estimate from the
  measured per-module cost and report the actual spend per account to MANAGER.
- The repair pass, then the comparison pass, run in spec order. Each pass runs only while its
  re-estimate fits the usable caps: OpenAI 117, Anthropic 135, OpenRouter 18 USD.
- If a re-estimate shows a pass exceeding its cap, stop that pass and report. The scope is not
  trimmed.
- distressed_restructuring runs on opus-medium only if the measured cost allows.
- Keys come only from OPENAI_API_KEY, ANTHROPIC_API_KEY and OPENROUTER_API_KEY in the environment.
  No key file is read, and no credential is searched for. If a variable is missing, stop and report
  its name.
- An offline pilot on the recorded adapter runs before the first live call.
