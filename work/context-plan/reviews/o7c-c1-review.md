# O7c C1 review (mx-adversary aef899a9), 7b632b58..244e38de

Probes are in `scratchpad/o7c-c1-review/probes/` (session 9d206924), each with a `.out` file. Rulings: O7-R54.

## Round 0: spec FIX, quality FIX
**What holds:**
- Ordering and state (p04): a pending consumer blocks `begin("CP-DR")`; `invalidate` stales CP-1C and CP-2 only; restricted, blocked and absent CP-DR behave as designed; `_edges` is right.
- The D12 chain (p05).
- Every preset orders CP-DR before its consumers (p03).
- Scope (p06).

**Findings:**
- **H-1.** `host._producer_inputs` admits only one-step heads, so a settled CP-DR head is never authenticated. CP-1C's session and prompt then refuse with `identity_mismatch` in every `cp_dr=True` run where CP-1C follows CP-DR (p02 exits 1; p02b attributes it to C1). Plan row 6's test never opened a session.
- **M-1.** `cp1c.RULES` uses `unread_citation_issues`, which checks only `page:N`, so an unread `ev-*` `line:N` cite is accepted (p01 exits 1). The feat commit deleted the RED leg.
- **L-1.** The CP-2 no-citation check is top-level only.
- **Infos:**
  - I-1: the `execution.py` comment;
  - I-2: helper name `_held_with_research`;
  - I-3: 244e38de pinned S1's `cpdr.py`;
  - I-4: the two-store test is sound;
  - I-5: CP-DR cannot re-settle in-store.

Not verified (reviewer):
- a full `run_pathway(relative_value, cp_dr=True)` reaching CP-1C;
- the receipt verifier over a sealed bound run;
- CP-2's live prompt over a real head;
- whether option (a) passes the verifier;
- mutation testing.

## Round 1 (86b83bad, 0eddf772, 84017b23): APPROVE
- **H-1 fixed.**
  - p02 exits 0, along with p02b-p04 and p06.
  - The fast nodes pass, and the row-6 node compares at `host.session_sources`.
  - The receipt verifier's replay reaches the CP-DR branch over the pinned snapshot (p08).
- **M-1 fixed.**
  - p01 exits 0.
  - The leg is restored and isolated, with parity against `research_rules`.
  - cp1c-owner behaviour is unchanged: p10 gives 172 equal cases.
- **L-1 fixed.** p11.

**Lows, which ride:**
- **L-a.** `TablesInvalid` (a `ResearchError`) escapes `_cpdr_producer_inputs` on an edited `evidence.json`: p07's V3 and V8c. The session still refuses, but not as `identity_mismatch`. The same escape predates C1 at `verify_owner_run_receipt`. Smallest single fix: `cpdr.probe` maps `ResearchError` to `WorkflowError("identity_mismatch")`. Goes to C3, which owns `owners/cpdr.py`.
- **L-b.** The CP-DR memo duplicates the submission memo (p09). Goes to the end batch: share one memo with a `check` callable.

**Infos:**
- On a memo hit, `evidence.json` edits are not re-checked; that belongs to O7-R49 L-2.
- The row-6 node takes about 4 minutes; whether it moves to `HEAVY` is the owner's call.

Not verified (reviewer): a sealed receipt over a model-recorded CP-1C walk; `run_pathway` reaching CP-1C with `cp_dr=True`; mutation testing.

**C1 is complete.** The tracked copy `work/context-plan/reviews/o7c-c1-review.md`, which the D12 record cites, goes in the end batch.
