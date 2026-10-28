# Module-builder lane: resume point (2026-10-28, session 3)

Lane `claude/module-dev-status-review-0981b6` at 7fdddbf or later (rounds 9 and 10 on it). Fast tests 1982 passed, 2 skipped, 1 xfailed (fast set now includes tests/test_schema_normalise_escapes.py). History is in `work/build/ledger.md`; the plan is `docs/superpowers/plans/2026-10-28-verified-module-builds.md`.

## Merged into the lane
- **Stage 1 modules:** CP-2E, CP-DR, CP-3D, CP-4, CP-1C, CP-2D, CP-L10, CP-2A, CP-1D, CP-3, CP-2G, CP-8, CP-5, CP-4C, CP-2H, CP-3C.
- **Rounds since:** CP-L10 r5 (6e63383); CP-1D r5b + 1D1 (7e29075); G1-X fix 1 (29c0819; G1/S1a suites deferred, so built, not done); CP-3D 6b (f72a8bf) and 6e/6g (fc8c505); CP-DR r5 (5b25007) and 6e (e4de446); CP-1C r6 + fix 1 (e4a0a4d); CP-2E r5-6 (40a3dc6), CP-2A r5-6 + fix 1 (7276630), CP-2D r5/6/6f (b09c33d); CP-1D raw-quote fix (7c88a98); CP-2E 6i (aed93b3); CP-1C 6h (0ef2dc8); CP-3D quote fix + 6h (0b0835f); CP-2D r9 (e3e1277); H1 + fix 1 (278f0aa; F1 fails closed); CP-2A r9 (aa4ab01); CP-3D r10 (a1de97d); G1-X fix 2 + LEAD 0d (857081c; G1/S1a deferred); CP-1D r10 (b7cd02e); CP-2G Stage 1 + fixes 1-2 + r9 (947a57d); CP-2E r10 + fix 1 (a1b50c8); CP-3 re-pin (6c6ea02), CP-8 through r10 (dae85ed), CP-5 + fix 1 (81e8c0b), with LEAD 2682310; H1 fix 2 (38f0f46; deferred suites pending); CP-4C + r8 + fix 1 (3b9c3dc); CP-2H + r7 + fix 1 (f843772; B7 strict xfail); CP-3C through fix 2; library (defect-classes); H1b; CP-1C, CP-2D, CP-8, CP-3D, CP-2G, CP-2E, CP-DR, CP-1D, CP-L10 class rounds (all nine done); CP-4C r11. Fast tests 3600+ passed (see ledger), 2 skipped, 1 xfailed (fast set adds tests/test_defect_classes_selfcheck.py).
- **Layer reviews:** A (6b20407), B (no commit), C (bb79483); reports `stage1/review-{A,B,C}.md`.
- **LEAD docs:** 8483de4 (E6), 3674158 (round 6 oracle batch), rulings rounds 1–6g, the owner ruling, the CP-2H/4C freeze (658a489), G1-X protocol amendments.

## Held (lane stays green)
| Commit | Lands with |
|---|---|
| LEAD 40e529c (B1 integration) | Stage 2 |

## In flight (resume an agent by SendMessage to its id; worktree `.claude/worktrees/agent-<impl id>` unless noted). Opus cap 6 (LEAD AGENTS.md proposal); ruling-text diffs reviewed by mx-feature.
| Work | Base | Agent | Next |
|---|---|---|---|


## Next when a slot frees
- G1-side guards (round 10 item 6 follow-ups) ride with the next G1-X change.
- Ride with the next change: CP-2D pre-D0 gap (round 11); CP-2G I1 explicit raise (round 11); per-module quote-edge (B1) and wrap (B3) fixes and blank-text fixes from the defect-class inventory.

## Queued
- Owner items (end review R3): L3, 30 `assert`s on invariant narrowing in product paths (cp2e, cp2d, cpl10, cp2a, cp2g, cp4c); I3, jscpd is not wired (estimated ~5% exact-run duplication in the cp4c/cp2g/cp2h scaffolding). Shared quote-reader helper under owners/ at Stage 2, once M3, M4 and L1 are ruled.
- Riding Lows from the class rounds (see ledger 2026-10-28 class reviews): CP-2D EUR+pre-D0 precedence; CP-8 L1 overlap, L2 exit_trigger blank; CP-3D L2 B3 accept side; CP-2E L2, L3; CP-4C r11 L1, L2. Owner items: CP-2E fx absence digit paths; H1 CP-3D row widening.
- H1b A (shared `outside` universe for row tests, p07) and B (L3 unreadable source with bytes, p10) plus Info comments (host.py:48, test :340), with the next H1 change; owner item: CP-3D row test widening (h1b-review p11); CP-2H fix 1 N1 (`Below  10.00x` unit case), N2 (`.75x`, `.5%`, `-10.0%`); CP-4C N1/N2 (in round 11); H1b none yet; CP-8 r10 (lowercase guard; close-only parenthesis); CP-2E r10 L1 (in fix 1); CP-3D r10 L1 (parenthesis tested at match start, `(-425)`); CP-1D r10 (1D7-before-≤0 unpinned; `(` side untested); CP-3D name wrap-join (quote-6h-review Low 1; needs a public joined-reading helper in deploy_vii.quotes, with LEAD); CP-2D L1-L6 test gaps (stage1/cp2d/round5-6-review.md).
- Whole-branch review: B4 conventions; CP-L10 not_applicable value_class; CP-8 and CP-3C size; earlier surviving-mutant counts.
- Stage 4: refused-record known gap; 0d `normalise` root fix (then remove the G1-X `_fill` mapping); CP-8 `∅ G#` binding.

## LEAD questions
Open questions live in `work/build/stage1/<cp>/questions.md` (cp2h, cp3c, cp4c, cp5) and `stage1/quote-sign-questions.md`. One pointer to LEAD every 20 minutes at most.

## Stage 2 notes collected
- Round 12 (LEAD c27760e): record the rule W guard limit (a spaced range or a dash bullet before a figure is refused; no range exemption) in methods/cp1d, cp3d, cp8, cp2e; record the B8 malformed-last-row limit in methods/cp2h. The methods files live in src/deploy_vii/methods/ (Stage 2 boundary). After the Stage 1 release merge, CP-2H B7: turn test_frozen_composer_only_cp2g_status into a plain test; switch pin tests to cases/PINS.json.
- Protocol §5 (LEAD d637afc): cores read model payload only through `json_object`/`payload_document`. Rewire cp2g:840, cp4c:953, cpl10:926 and cp2h:1623 (`model_validate_json` on raw text; host.py:675 parses raw too, check if §5 covers it) at their Stage 2 seams.
- On the Stage 1 release merge of codex/checkpoint (carries 0d-b): run test_schema_normalise_escapes.py, test_owner_workflow.py::test_equivalence_gap_verifier_replays_unrepresentable_submits and LEAD probe b04.
In the plan and review files: CP-1D B3; the CP-2D Facility binding; CP-2A L6; the `methods/<cp>.md` entries from round 5; the T4.18 currency/name reader (A5, CP-2D and CP-3C; a row with no currency fails closed); A4 floor-not-stated if the schema allows a missing floor; round 10 sign rule in methods/cp1d, cp3d, cp8, cp2e; unsigned-grammar limitation in methods/cp8 and cp3d; CP-3C facility ids as prose names at MC-2; CP-8 item 2 guard-limit note.

## Routing (user, 2026-10-28)
- Round 13 work uses Sonnet implementers (`mx-feature`), not Opus. Reviews unchanged.

## After the class rounds (next steps, 2026-10-28 16:15Z)
1. (done) All class rounds merged.
   Stage 1 release merged (17480de) and follow-up merged (e321357); lane green, 3669 passed. Lane merged into claude/round12 at 128c3ca.
   Round 12 module agents (Opus) from 128c3ca: CP-3D ad7c7f755b86b3954, CP-8 a8adfa642064474bd, CP-2E a047233dbd3d1e26d, CP-2H a3a96fa35d45bd270, CP-4C a4cd80913af819154, CP-2D a0e5edb925476b0a2. Review each per the round12-brief table, merge into claude/round12, and when all six are in, run the fast set on round12 and merge it into the lane.
   Round 12 (claude/round12, worktree round12, at 9eb44e0): Part L, CP-1D and the B10 batch (six modules) approved and merged into claude/round12. CP-3/4/5 B10: LEAD builds lead/b10-engines (deploy_vii.prose.is_blank). When it reaches codex/checkpoint, merge it and make owners/blank.py import is_blank from deploy_vii.prose. Riding-Lows batch merged into the lane. Next, after the release follow-up merges into the lane: merge the lane into claude/round12, then dispatch CP-3D, CP-8, CP-2E, CP-2H, CP-4C, CP-2D per round12-brief.md. End review R1 and R2 saved (stage1/end-review-R1.md, -R2.md); LEAD questions batched in stage1/end-review-questions.md (R1-R3 complete): sent to LEAD ~18:25Z.
   In flight (2026-10-28 ~18:05Z): riding-Lows batch a2564bfd435381686 (worktree stage1-lows, brief stage1/lows-brief.md) then mx-feature review and merge; Stage 1 end review at 87b2a1a, brief stage1/end-review-brief.md: R1 acb9e707a8ed8d839 (mx-autonomous), R2 a8328bdae944bc35d (mx-precise), R3 a76107fc47c365f31 (mx-autonomous). Save each report to stage1/end-review-R<n>.md; findings go to fix rounds. If either review returned while the session was away, read the agent's SubagentHandback in its task .output.
2. (LEAD answered: round 12, c27760e, cherry-picked as 688f185; brief stage1/round12-brief.md, integration branch claude/round12.) Check LEAD's answer to the 16:08Z pointer (quote-sign-questions.md "Open for LEAD"; cp2h B7-B10; cp4c B7). Apply rulings as rulings rounds.
3. Riding Lows batch (ledger, 2026-10-28 class reviews): one test-only round per module, with mx-feature review.
4. Stage 1 end review (Opus, mx-precise or mx-adversary) on the lane, then Stage 2 per AGENTS.md 423a06e.

## Round 13 (LEAD 7ee9c8b, cherry-picked 76d7820; brief work/build/stage1/round13-brief.md)
- Running (mx-feature): CP-1D, CP-3D, CP-2D, CP-3C, CP-L10 in worktrees r13-<cp>, branches claude/r13-<cp> from claude/round12 d2cb626. Reviews: CP-1D mx-adversary; CP-3D, CP-2D, CP-3C mx-precise; CP-L10 mx-feature.
- Queued after their r12 merge: CP-8 (items 7, 8; _labelled narrow join), CP-2E (item 8; label-decimal question still open with LEAD), CP-4C (item 2 + item 5 base_period).
- Riding: CP-2H B8 later-line Low (next CP-2H change); CP-2G item 5 base_period invariant (next CP-2G change).
- Stage 2 notes: item 8 comma guard limits in methods/<cp>.md (CP-1D, CP-3D, CP-8, CP-2E); CP-2D/CP-3C oracle re-pin and removal of the test delta.
- Open for LEAD: CP-8 r12 `_wrap_split` derivation (ignores a W minus before a digit), pending its review.
- Pending LEAD pointer (next, >=20 min after the last): CP-8 controller decision, the _wrap_split exemption is reverted (fail closed, as CP-3D and CP-2E), and the size-level w-minus-wrap cases are satisfied by the B3 span refusal; LEAD may overrule. Possible: CP-1D comma-space list reads one figure (pending adversary); CP-3C missing cash_closing currency (pending review).
- claude/round12 now holds: Part L, CP-1D, B10 batch, CP-2D, CP-3D, CP-2H, CP-2E (r12) + CP-L10 (r13) + lane (checkpoint 2344b17). Waiting: CP-4C r12 review, CP-8 r12 fix1, round 13 CP-1D/CP-3C reviews, CP-2D impl, 0d-c impl; CP-3D r13 blocked on LEAD (date).
- Next LEAD pointer: CP-3C r13 Infos (unsourced currency when cash_closing missing, incl. all-blank currencies; conflicting status words in minimum-cash and T4.18 seniority dependants; _check_value message keeps CP-1 prefix).
- After CP-4C r13: blank support/citation quote batch for every other owner module that takes citations (addendum 3); inventory first.
- Waiting: LEAD signal that codex/checkpoint holds e89b2a2 (b10-repin); then merge it, cp3c pin test should go green.
