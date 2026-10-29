# methods/cp2h.md: CP-2H Rating triggers, recorded LEAD adaptation (D12)

Written at Stage 2 from the lease's "Adaptation record" (`docs/CP2H-OWNER-LEASE.md`). The r14 CP-2H SKILL.md is not in this repository, so the titles, columns and claim wording of `T2R.1`-`T2R.10` are composed from the methodology purpose and the architecture row: a recorded adaptation, not a transcription (as CP-2G ruling 1). Oracle: `cases/cp2h-owner/` (builder `builder/build.py`).

## Purpose and mapping

`methodology.json` purpose: "Maps rating migration risk, trigger headroom and agency divergence". Architecture row: "trigger headroom on CP-2G; ratings, thresholds, migration view; FP05 rating-triggers". Required CP-0, CP-1, CP-2G (edge `block`); optional CP-1D (never read by this version). The ten registered ids map one to one to the tables composed here: T2R.1 upstream register, T2R.2 agency rating register, T2R.3 published trigger terms, T2R.4 current trigger headroom, T2R.5 forward trigger headroom, T2R.6 trigger timing, T2R.7 migration assessment, T2R.8 agency divergence, T2R.9 trigger summary, T2R.10 gaps ledger. Python owns all arithmetic. Ratings, scale positions, outlooks and thresholds are parsed from the agency source (`ratings`) and are never analyst input; the analyst gives, per agency, an enumerated migration view, a confidence, a rationale of references only and located citations, then an overall assessment and gaps (D11).

## Method

- Metrics: a trigger's source label maps to one CP-2G ratio ("Total debt to EBITDA" `total_leverage`, "Net debt to EBITDA" `net_leverage`, "EBITDA to cash interest" `interest_coverage`, "Free cash flow to total debt" `fcf_to_debt`). Thresholds "N.NNx" are multiples, "N.N%" fractions, "Not stated" missing.
- Headroom: `threshold - metric` ("Above") or `metric - threshold` ("Below"), one subtraction in the 38-digit half-even context; a percent metric gives percentage points.
- Reached: strict (equal is not reached and shows zero headroom). First year: the first of FY2026-FY2028 the trigger is reached; a year not calculable before it makes the answer missing with its root reason; none reached and all calculable is "Not reached by FY2028".
- T2R.4 FY2025 `actual` is an own copy of CP-2G `T2H.6.a25.<field>`; `check` compares it with the CP-1 reported ratio exactly.
- Notches: the absolute difference of the combined-scale positions; a withdrawn or unrated agency has no position.
- Zero, missing and not applicable stay distinct everywhere; a missing CP-2G ratio keeps CP-2G's own limitation.

## Left out of the method (each is a stated limitation or a follow-up)

Agency-adjusted metric definitions; sustained-period breach conditions; outlook weighting; any numeric probability (forbidden); market-implied ratings (CP-3D); a rating-change history; the DR.6 chart (the design's n/a frame stays idle wording).

## Guard limits (Stage 2)

- **B8 known limit (parse rule).** Fields split on two or more spaces, so a malformed last row of a block written with single tabs or single spaces cannot be told from a one-field note: it ends the block and is dropped (4 of 5 terms in the pinned probe, `test_malformed_last_row_is_the_known_limit`). Any later line on that page with two or more fields makes the source invalid ("any later line", not only the page's last: `terms_row_then_trailing_note`). Closing the limit would move the frozen `parse_rule`.
- **Blank quote.** A citation quote that is blank (whitespace, zero-width or soft-hyphen only) gets `<path>: empty text` at the citation step, before the page check.

## Connection notes (Stage 2)

- **One adapter.** Submit, the entry validator, probe and view reach the core only through `cp2h._adapted`: the host-scope sources (identity, financial, ratings) in pack order, the issuer name, the bound and current inputs, the CP-1 head's four reported ratios (`select_cp1`, in the head's order) and the 28 CP-2G `T2H.6` facts selected by literal id from `owners.cp2g.cp2g_reader` over the bound CP-2G blob (rulings stage2 Q6). CP-2H declares no reader of its own.
- **Parse.** The retained payload is read only through `json_object`; the schema validates the document's exact re-serialisation. Text `json_object` refuses keeps Pydantic's own shape issue (the frozen r06 frame).
- **Issue lines.** Every line that quotes the analyst or the pack (agency, prose, citation, rating, metric, stale text) is cut at 600 characters (`execution.clipped`); a raised composition lists at most 20 lines and a count. A rationale becomes `Claim.text`, so when `prose.issues` passes it, it is also checked as `RunText` (the type's message, never the input).
- **Staleness.** A changed bound upstream is reported alone, before any content check; through the workflow a changed head refuses `stale_binding` first.
- **Figures (Q-SQ).** Every figure is Python's: from the agency source's page rows or from the bound upstream facts. Prose carries references only (`{T2R.x.y.z|token}` own facts, CP-1 figures bound at run time); no free-text field is stored verbatim, so every hostile model text is an issue.
- **Citations.** A source fact cites the agency-source quote it states. A calculated fact has one `Citation` per (source, page), quoting the first of its own inputs' quotes on that page, in input order (rulings stage2 round 3 item 3; the frozen oracle was re-pinned to this rule at the Stage 2 close release, round 5 item 17). The citations of the `cp1:` and `cp2g:` facts a fact derives from are appended at run time after its own by the same rule: one Citation per (source, page) not already cited, the first upstream quote on that page in `derives_from` order. No quote is invented.
- **View tree.** The `read_inputs` view is the lease's draft tree (`manifest.json tool_use.view_tree_draft`): `upstream`, `register`, `triggers` (terms, no quotes; each threshold as the fact a reference may name), `cp2g` (the 28 ratios as `{ref, shown, status, limitation}`), `cp1_facts`, `inherited_limitations`. No `quote`, `citations` or `record_json` key at any depth. An absent agency source gives `register.state` "absent"; a source the parse rule refuses gives "present" with nothing parsed. The key tree is committed in `cases/cp2h-owner/cp2h-view-tree.json` (shape only, per case), checked by the connect test against the view over a real store and by the owner test against the genuine run's body.
- **Settled form.** The reference tables carry the upstream facts verbatim under their own ids; only the table, row and field coordinates change. The step output is `RatingTriggersReport` (the lease's `TriggerReport`; Stage 1 keeps that name for the pure composer's result); the settled tail is `rating-triggers-submission`.
