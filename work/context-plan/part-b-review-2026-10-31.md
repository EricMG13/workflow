# Part B review, 2026-10-31 (plan lines 341-518, code at codex/checkpoint 7c28060b)

Reviewer: mx-autonomous (Opus 5.5), read-only. Controller re-ran probes p1-p3 (same results), added
p4, and re-checked the citations below. Probes: `work/context-plan/probes/` (run with
`PYTHONPATH=src <venv python> <probe> <repo root> <corpus root>`; p1 takes no arguments).
Verdict: fix. O1 can start; O2+ wait for amendments.

Disposition: all findings applied to Part B at the user's word "Apply amendments" (2026-10-31).
Rulings: M3's leftover quotes go to the goldens owner to re-cut (the adjacent-span citation is
left as a user **vii** option); offline call records are priced from recorded usage and Plan B
counts live runs only (M5); H1 takes the reorder (O5 before O2), not the O2 split.

Re-review of the amendments (mx-feature, scoped): pass; two Low (DeepSeek `provider.ignore` is
absent from `client.py`, so it is added, not kept; read cap cited at `preparation.py:20, 380`) and
one Info (`hybrid_cp1.py:558` starts `tool_choice` at `"any"`; R5 states the port change), all
applied.

Plan B items for the testing session (not yet sent; it is paused until 2026-11-04 07:00 London):
- Task 3 `account_spend` counts records only from runs whose `run.json` `mode` is `live` (M5).
- Task 4/6 goldens: re-cut the quotes O2's plan lists as holding in no converted line (M3).
- R1 no longer claims Task 6 maps against converted text (Info).
- Stopped-run file set (O2 review M7): a stopped run may also hold `publication/` (a fault after
  CP-MODEL published) and `delivery/` (a verify failure after the rename); a blocked walk ends
  `stopped` with `stopped_reason` `render: owner_render_blocked` and keeps `owner-run.json`, so
  Task 8 scores from `receipt.plan` with `rendered=false`.
- `run.json` `sources` includes a `context` entry (`media_type` `text/plain`, `converted_sha256` null).

| Id | Sev | Finding (verified) | Proposed amendment |
|---|---|---|---|
| H1 | High | O2's call shape and Done-when need O5 (`ModelSpec`, adapters, `calls.jsonl`); order is O2→O5. Spec §1a:15: nothing calls a model today | Order O1 → O5 → O2 → O3 → O4 → O6 → O7; O5 depends on O1; move G8 (CP-0 prompt `Run <id>`) to O6 |
| M1 | Med | `prepare` needs one root (`preparation.py:371-377`); goldens, context and converted files have none; `source_id` used in a path before validation; `context` id refused only after writes (`context.py:705`) | Validate ids before any write; copy every source + context into `run_dir/sources/` and use it as root; reuse the CLI's read cap; add `pack/` to the run directory |
| M2 | Med | `pathway` given twice (argument and `context.run.pathway`) | Refuse a mismatch |
| M3 | Med | R1 lines break golden quotes; a citation must sit in one span (`readiness.py:145-172`, spans are lines `preparation.py:78-79`). p2: 341/843 miss (R1 also runs table cells together). p4 (cells spaced, hidden dropped): R1 208, no-div 107, tr+p 105, tr 76, no line breaks 27 (probe parser differs slightly from check.py). p3: R1 keeps 7-23% hidden iXBRL text | R1 adds a space at every check.py BLOCK tag and drops check.py SKIP/HIDDEN; O2's plan picks the line rule by p4 measurement; Done-when gets a fixed ceiling and reviewed list; quotes no rule can hold go to the goldens owner (or a user **vii** decision to let citations join adjacent spans) |
| M4 | Med | Unknown charge stays reserved but run continues; spec §7.2:83 says it stops | "stays reserved and stops the run" |
| M5 | Med | Offline records priced from recorded usage; Plan B `account_spend` sums every record (planB:126) | Plan B counts live runs only; Part B states offline money values |
| M6 | Med | Unmarked vii: existing prompts are `src/deploy_vii/live/prompts.py` (STEP_CONTRACTS :680, SCOPE_BLOCKS :857); O7d/OD12 `src/deploy_vii/methodology.json`, `bindings/cpdr.py`; O1 maybe `bindings/cp6.py`, `cp6_committee.py` | O6 composes rules/scope feed in `src/deploy_workflow` without editing prompts.py, or marks vii; mark O7d and O1 files vii |
| M7 | Med | R4 misses stdlib traps | `ProxyHandler({})`; TLS verified against original host (`server_hostname`, `check_hostname` on) when connecting to the IP; re-resolve and re-check per redirect; unwrap `::ffff:` before the public check |
| M8 | Med | O5 port list incomplete: VII `live/client.py` is OpenRouter-only, no tools | Name spec §8 sources: `hybrid_cp1.py` Anthropic SSE (tool_choice auto, `output_config.effort`), Codex OpenAI preflight + key-reflection guard, DeepSeek `provider.ignore`, 128k max output, runner 402 handling |
| M9 | Med | O1 Done-when runs spec checks only | Add one offline walk per preset passing `verify_owner_run_receipt` |

Low (batch with the amendments): L1 recordings tied to `run_id` via pack hash; O3 replay by retained
submission, add a no-double-spend rerun case. L2 say which failures raise before any write vs write a
stopped `run.json`. L3 R3 names exception chains and stderr; align R3 and Plan B key regexes
(planB:111 `{6,}` vs R3 `{20,}`). L4 accept only O5's adapter classes. L5 O6 needs a machine-readable
validator-rule list. L6 "Committee Ready" exists nowhere in `src` (OD7). L7 O5 Done-when lacks
redaction and budget-refusal tests.

Info: G1 holds (p1: only `distressed_restructuring` passes). `earnings_workflow.py:1655` → :1657;
`cp2h.py` agency names :162. R1's "framework maps against converted text" is wrong: Plan B Task 6
maps to table/row/field. `cp_dr_public` is the form default for every issuer (`context-form.html:492`),
not only private (OD9 wording). Codex branch (efe43725) is still not merged into codex/checkpoint.

Not verified: no pytest; R4 TLS/proxy behaviour not run; provider docs not fetched; Plan B read at
efe43725; O1's CP-6 file edits unknown.
