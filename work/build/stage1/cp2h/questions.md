# CP-2H questions (AGENTS.md: one file per module)

## Decided by the controller (module-only; recorded in the ledger)
- **Q1 (review F1, threshold form).** The frozen manifest `parse_rule` pins `'N.NNx'` (multiple) and `'N.N%'` (percent). Round 7 item 8 refuses any other form with `Trigger terms not found`. The ruling's "N.Nx" is shorthand, because the frozen `2.75x` is N.NNx. The grammar is therefore `[0-9]+\.[0-9]{2}x` or `[0-9]+\.[0-9]%`. This supersedes the earlier "4x is accepted" note sent to LEAD. The builder's looser `\d+(\.\d+)?(x|%)` is a builder sync for LEAD (B1). No frozen value moves; the reviewer's spec_fix_safety.py keeps all 154 tests green.
- **Q2 (review F3).** A percent threshold is stored as a fraction by an exact exponent shift, with no rounding context. The builder's 28-digit `scaleb` is a builder sync (B1).

## For LEAD (one batch)
- **B1.** Builder sync for Q1 and Q2 (build.py `_THRESHOLD` and :237).
- **B2.** The item 8 block rule ("ends at the first short line") silently drops published terms when a middle row is malformed. With a figure-free payload, 3 of 5 terms vanish and "Triggers tested" reads 2, with no issue. The reviewer proposes:
  - a line with one field ends the block;
  - a line with two or more fields that is not the block's width refuses.

  This keeps all tests green. Probes: cp2h-adversary/p05_block_truncation.py and spec_block_safety.py.
- **B3.** An empty or blank limitation passes (d) and reaches `Claim.limitation`. CP-3C has the same case (its item 4).
- **B4.** A known FY2026 first-year result lists a later missing CP-2G fact in `derives_from`. Lease D3 (c) asks for all three rows. Is that intended (p11)?
- **B5 (Stage 2).** The T2R.1 `u_cp1` and `u_cp2g` statuses come from fields that are not checked against the bound Inputs.
- **B6 (Stage 2).** Untested stale-issue order, the `absent` wording, and the `str` current path.

## Ruled by LEAD round 11 (d60035b)
See `docs/rulings/2026-10-28-stage1.md` `# Round 11`, `## CP-2H`. Modules-decides items are recorded in the ledger (2026-10-28 round 11 line).
