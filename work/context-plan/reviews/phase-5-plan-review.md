# Phase 5 (attachments and modes) plan: controller rulings and review, 2026-10-31

Plan: `docs/superpowers/plans/2026-10-31-phase-5-attachments-modes.md` (draft, mx-feature, ~190 lines).

## Controller rulings on the draft's open questions
- **Q1** (`methods/cp4.md`, `live/prompts.py:547`, `live/context.py:33` still say "executed or filed"):
  these are `src/deploy_vii` edits outside B7 and B9, so they go to the user (final report). Until the
  user rules, they stay unchanged: the live model is told to cite only executed or filed documents, so a
  draft-only CP-4 fails closed in a live run; offline tests drive recorded submissions. The plan states
  this limit in its Done-when.
- **Q2** the frozen refusal wording at `cp4_legal.py:476` is kept.
- **Q3** no CP-3 confidence cap for draft-only legal inputs: B6 approves CP-3 changes only for
  Python-built market evidence. The draft limitation on CP-4 carries the caveat; a downstream cap goes to
  the user (final report).
- **Q4** draft sources are admitted beside executed ones.
- **Q5** an absent declared attachment is a `source` gap whose description names the missing id as a
  whole word (no new gap field; that would be a contract change).

## Review (mx-autonomous, read-only), 2026-10-31: verdict fix (1 High, 2 Medium)
Probes in `scratchpad/p5probe/`: `authority_leak.sh`, `walk_preset.sh`, `pins_context.sh` (exit 0 each).
- **H1** (:98; readiness.py:28-30) adding `draft` to the shared `Authority` literal widens CP-1A
  `SourceUse.source_class` (business_context.py:53, 141) and the live CP-0 `SourceJudgment`
  (live/submission.py:121, 163) with no context check. Fix: `Authority` unchanged; only
  `SourceAssessment.authority: Authority | Literal["draft"]`; RED: CP-1A `source_class: "draft"` refused,
  `SourceJudgment` authority values unchanged.
- **M1** (:61-62, :154) `credit_snapshot` is CP-0, CP-1, CP-MODEL, CP-1A, CP-2, CP-4, … (contracts.py:49-51)
  and the walk is sequential: Task 0 builds packs through `prepare` with `Run(requested_modules=("CP-4",))`
  and the context repeating the pathway; say `preparation_request` is not used.
- **M2** (:57-58, :84) `cases/pins.py:20-30` PATTERNS miss `context-*.json`: record each context file's
  sha256 in the case `manifest.json` (as `cp4-owner` `frozen_inputs`) and test it.
- Lows: L1 a `draft` assessment of the `context` source itself makes it citable (cp4_legal.py:229-234): add
  a readiness issue (the same with `executed` predates this phase: owner); L2 oracle says which path each
  expected line belongs to (`submit_review` precheck refuses `draft-wrong-context` first); L3 monkeypatch
  `cp0_attachments.precheck` to `()` during verification and assert it fails; L4 1(e), 2(b) second half,
  2(d), `none-declared` are guards; L5 exact regex `(?<![A-Za-z0-9_])id(?![A-Za-z0-9_])`; L6 cites
  readiness loop :356-376, ow:1248, `cp4.precheck` :135-149.
- Sound: lazy import no cycle (context.py:23-30); vii→workflow lazy imports exist only in rendering
  (distressed_figures.py:62, report_view.py:1888): acceptable in a validator if lazy and the D12 reason says so.

## Controller rulings (2026-10-31)
- All findings accepted as proposed. L1's pre-existing `executed`-on-`context` case goes to the user
  (final report).

## Re-review of rev 2 (mx-autonomous): approve
- H1 (:104-105), M1 (:62-64), M2 (:90-91) fixed; cites :356-376, ow:1248 spot-checked. Two Lows (L2
  `draft-wrong-context` needs a `source` gap naming `legal_documents` to reach `V`; :56 pin wording) applied
  by the controller. **Phase 5 plan approved.**
