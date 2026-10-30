**Verdict: REVISE.** Two Medium findings. The spec is test-only and reads its expectations from the oracles, and the rulings are applied. But two rules can pass without checking anything.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g2-gaps-spec-review/` (shortened to `<R>` below). Each probe ran on a fresh `git archive e37b73e` copy, which I deleted afterwards. No worktree was written; `git status` is clean.

**Preparer's probes (rerun):**
- probe0: exit 0. It must be given the tree root, not the probe directory as the spec's run line says (with the probe directory it exits 1 with FileNotFoundError).
- probe1, probe2, probe3, probe4: exit 0. Every listed perturbation fails as claimed.

**Medium**

1. **`cites` rule, ruling 3: the check covers no real cites for cp8 and only some for cp4.**
   - The spec applies `_page_cites` only to block cells. For cp8, every `cp8.what_changed` fact has `cites == []`.
   - All the non-empty list cites sit in other tables: cp8 positive has 58, no_outcome has 21. cp4 has 35 of its 61 outside the section tables, in the rail tables.
   - So the cp8 cites check would pass while checking no real cite.
   - Fix: apply `_page_cites` to every oracle fact with list `cites` in `#/cases/<c>/tables` (cp3d, cp8) and in `#/<key>/CP-4/tables` (list cites only), keyed by the oracle `fact_id`. Assert a count of non-empty cites checked of at least 1.
   - Probes: `<R>/probe_cites_scope.py` (exit 0, prints the counts) and `<R>/probe_cp8_chip_branches.py` (exit 0).

2. **`_page_cites` ("take the `report.index.facts` entry") does not say what happens when the entry is missing.**
   - The preparer's `common.cites_of` falls back to `or [{"ref_ids": []}]`. That is a catch-all hiding a failure.
   - I removed the index entries of facts whose oracle `cites` is `[]`: 6 entries on cp3d positive, 36 on gap_no_market. The cp3d rule still passed.
   - Gap facts legitimately have no entry, so the spec must say: a known fact has exactly one entry (assert this); a gap fact may have none, and then its cites are `[]`.
   - Probe: `<R>/probe_extra_perturbations.py` (prints "passes (vacuous)"). It exited 1, because its last cp8 step hit StopIteration: no what-changed line carries a C/S chip. That fits finding 1.

**Low**

3. **Ruling 6 (cp3d and cp8 rails) has no rule text or pointers in the spec.**
   - cp3d's oracle has no `render.rails`. Its rails are `render.blocks["evidence rail"]` (T3E.8) and `["limitations rail"]` (T3E.9, T3E.7). Limitations equal `dict.fromkeys(own_limitations + inherited_limitations)`.
   - cp8 uses `render.rails` with `cases/<c>` `own_limitations` and `inherited_limitations`.
   - On the fast pages, cp3d accepts on all 3 cases. The cp8 page was not probed. The spec should name these pointers.
   - Probe: `<R>/probe_rails_cp3d_cp8.py`, exit 0.

4. **Ruling 4 leaves out part of the oracle rule.** The cp4 oracle rule (`#/gap/CP-4/inherited_limitations/rule`) is: CP-1 head `limitations` **then `inherited_limitations`**, de-duplicated, own findings removed. Ruling 4 takes only the CP-1 head's `limitations`. If CP-1's inherited list adds entries not in the CP-0 literal head, the genuine run will disagree. Follow the oracle text.

5. **Ruling 1 contradicts the rule body.** It says the label run "equals the oracle column label, exactly", but the rule and probe3 assert `"<column>:"` (that is, `"Value:"`). State the colon explicitly.

6. **The cp4 field check differs from the spec.** The spec says "same checks as cp3d", meaning `field` equals the oracle column's field. probe2 compares against the `fact_id` suffix instead. Use the column field.

**Info**
- Every cp4 known cell without `text` is covered by `displayed_literals`, so "numeric cells checked only by literals" is not looser than the lease. Probe: `<R>/explore_oracles.py`, exit 0.
- My extra perturbations all failed as they should: cp3d tab label, reversed layout `fact_ids`, known→gap, reversed ref order; cp4 headroom gap→75.0%, gap→n.m., reversed limitations; cp8 swapped lines, K chip→S chip.
- All 10 named genuine ids plus `refused[cp8-fp01-what-changed-no_record]` collect at e37b73e, and all go through `_check_scope_run`. They cover every scope the rules touch.

Not verified: no genuine run (the brief forbids them), so passport numbering on real pages, the store-based CP-1 limitations, and the cp8 rails on a page are unexercised. The finding 2 fix (known facts always have one index entry) was not checked across all scopes.
