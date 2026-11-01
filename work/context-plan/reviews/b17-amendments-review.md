# B17 plan amendments review (mx-autonomous aa2f06f2, 2026-11-01)

Plans: phase-3-market-evidence, phase-5-attachments-modes, phase-7-valuation, phase-8-periods-currency
(uncommitted B17 amendments). Probes: scratchpad/b17probe/ (context_authority.py 0, pin_consumers.py 0,
cp1b_dimension.py 1 — the USD literal at report_view.py:2298).

Verdicts: Phase 3 approve · Phase 5 approve (Low notes) · Phase 7 approve · Phase 8 fix.

## Findings and rulings

1. **High, Phase 8 Task 6b (:307-314), R3 (:123).** `report_view.py:2298` `_cp1b_fact_shape` hard-codes
   `("MILLIONS","USD",Decimal(1000000))` for every CP-1B money fact; RED (b) cannot pass and R3 cannot settle
   in EUR. **Ruling B18 (applied recommendation):** :2298 is inside B17 item 9 (same CP-1B layout validator,
   called at :2385; the run's money unit; USD byte-identical; `mx-adversary`). C = currency of
   `revenue:current`, required non-None; every money fact on all 9 rows, prior/current/delta, must be
   `("MILLIONS", C, 1e6)`. Drop the "gaps with no currency → US$ m" fallback (today a None currency raises;
   the fallback would weaken the check). Add REDs: a row in a different currency than C refuses; a None
   currency refuses. USD byte-identical (`scale_label("MILLIONS","USD")` = `US$ m`).
2. **High, Phase 8 re-pins (:319).** Remove `cases/legal/manifest.json:294,338` from the re-pin list (old
   report_view hashes `571ee44…`, `c934d50…`, provenance, unenforced; re-pinning ripples into cp2d/cp4/cp4c
   builders and manifests, render-expected, source-host-expected). Add `cases/cpos-owner/builder/build.py:28`
   (`read_pinned` asserts it) and the `cases/PINS.json:84,86` entries that follow. Re-pins go through a
   separate preparer + `mx-precise` (oracle process).
3. **Medium, Phase 8 :307 and R3 (:123-126).** Nine money labels, not eight: add `Net debt (US$ m)` at
   `bindings/cp1b.py:49`; otherwise a `US$` token survives and Done-when 7 fails.
4. **Low, Phase 8 :317.** Last report_view D12 record is `docs/reuse/manifest.json:1795`, sha `5dc981…`
   (not :1228).
5. **Low, Phase 5 :112.** "RED (i)" → "(h)"; state the context refusal once.
6. **Low, Phase 5 :179, :184.** Two D12 entries, not three (prompts.py has no "executed" literal). The phrase
   wraps across `cp4.md:15-16`; the test matches with whitespace normalised; drop "two lines".

Confirmed by the reviewer: D12 shapes (prompts/context/cp4/report_view in files[]; cp1c.md, cp4c.md,
cp1b.py not); no hash pins for cp1c.md or cp4c.md; no frozen case assesses `context` as executed, filed or
draft (12 hits, all `unknown`).

Not verified (reviewer): no tests run; pins added after HEAD by O6 or other phases; `docs/handoffs` sha
lists (taken as historical); CP-1B claim/limit text for EUR (Task 7).
