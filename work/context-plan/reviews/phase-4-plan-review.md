# Phase 4 (ratings) plan: controller rulings and review, 2026-10-31

Plan: `docs/superpowers/plans/2026-10-31-phase-4-ratings.md` (draft, mx-feature, 229 lines).

## Controller rulings on the draft's open questions (applied recommendations)
- **Q1** `scope` unused, no instrument field: instrument reads "Not stated" (phases-2-8 Phase 4 item 3);
  `scope` is recorded in a limitation.
- **Q2** two context ratings rows from one agency: refused (no instrument field to tell them apart).
- **Q3** trigger terms read only from the attached source's page 3, as today (cp2h.py:157-163).
- **Q4** empty outlook reads "Not stated".
- **Q5** `context` joins CP-2H's read scope in `host.py` (CP-2H row only).

## Review (mx-autonomous, read-only), 2026-10-31: verdict fix (6 Medium)
Probes in `scratchpad/p4probe/`: `probe_minified_context.py` (exit 0), `probe_task1_red.py` (exit 0),
`probe_static_sites.py` (exit 0). The Stage 8 Low fix is right (REDs 1 and 3 fail at HEAD, pass with it).
- **M1** (:147) `compute` re-parses with `parse_ratings` (cp2h.py:1904) beside `validate` :1683 and
  `_parsed_source` :2175: one shared source-selection helper at all three sites; add `compute`.
- **M2** (:171) appending limitations keeps false fixed lines (cp2h.py:1801-1802 synthetic agencies, :1826
  source's combined scale): on context runs replace out[0] and out[6] in place (as out[7], :1869); pin texts.
- **M3** `Moody's` breaks possessive f-strings (cp2h.py:953, :1264, :1877 → "Moody's's"): possessive helper
  adding nothing after a trailing `'s` (frozen texts unchanged); pin the oracle text.
- **M4** (:75) scale table lacks `D` for S&P and Fitch: add row 23 `D`; reviewer checks.
- **M5** (:164) the line walker raises `ValueError` on a valid file with another layout (minified context =
  one `line:1` span): object-anchored citations (Phase 3's design) or a named validation issue, never a raise.
- **M6** oracle texts ambiguous (:80 T2R.8 period, :81 "Rating date not stated", :80 vs :166 value_class of
  position): pin each string, field and `value_class` in Task 0 and Task 3 together.
- Lows: RED 2 passes at HEAD (guard); `test_pack_without_context_unchanged` must compare against frozen
  `expected.json`; :126 branch on `source` not `r.scale_line is None` (:951), `line` stored as `str(i)`, state
  register-vs-terms refusal order; `tests/test_host_h1.py` shared with O7 (:557-561, exact-set :350-359), real
  CP-2H rows `_LEASED_ROWS` :460, :496-498, update `host.py:102`, `cp2h.py:1939`, `docs/CP2H-OWNER-LEASE.md:46`,
  `cases/PINS.json` shared with O7's re-pin; Task 4 `methods/cp2h.md` is not in the manifest's `files[]`
  (not imported) and its :33-34 go stale; line cites (UNRATED :164, texts :154/:156, context.py:733-770,
  mismatch :764, out[7] :1869, host row :103); Task 1 reviewer `mx-precise`.

## Controller rulings (2026-10-31)
- All findings accepted as proposed. M5: object-anchored citations shared with Phase 3 (one helper in
  `src/deploy_workflow`, built by whichever phase builds first; the other reuses it).
- **Task 4 / D12:** `post_import_patches` records only patches to files in the manifest's `files[]`.
  `methods/cp2h.md` is repo-authored, so it gets no D12 record; its hash change runs through the re-pin of
  every file that pins it (`cases/PINS.json`, leases), by the oracle process (separate preparer,
  independent `mx-precise` review, `cases/pins.py --check`). The same rule holds for every repo-authored
  `src/deploy_vii` file in later phases.

## Re-review of rev 2 (mx-autonomous): fix (M5 open)
- M1 (:164-166), M2 (:184-190), M3 (:139), M4 (:78; rows 22 SD/RD, 23 D for S&P and Fitch; Moody's stops at
  21 C), M6 (:83-85, :96), D12 (:27-31, :208) fixed. Residue: :182 files "Rating date not stated" under
  T2R.8; it is the T2R.2 position period.
- **M5 open** (:171-177): Phase 3's scanner sits in `src/deploy_vii/cp3_relative_value.py`, which may not
  import `deploy_workflow`.
- Lows: `uncitable_row` (:93) must state the key layout; no file pins `9e809987` (cp2h.md), so Task 4's re-pin
  does nothing; :156 cite `:350-356, :391`.

### Controller rulings
- **M5:** Phase 3 (rev 3) builds `src/deploy_workflow/context_cites.py` for CP-3D and keeps
  `cp3_relative_value.py`'s own `_value_offsets`, tied by a parity test. Phase 4 imports that helper (Phase 3
  builds first); if Phase 4 is ever built first, Phase 4 builds the helper to Phase 3's contract.
- **D12 (supersedes the earlier ruling here):** per B14, Task 4 writes a D12 record for `methods/cp2h.md`
  (repo-authored shape); no re-pin is needed because no file pins its hash (Task 4 says so).
- Residue and Lows accepted.

## Re-review of rev 3: approve
- M5 (:169-177), B14 (:28, :215-217), residue (:181) fixed; two Lows (:153 "extend", :154 cites) applied by
  the controller. **Phase 4 plan approved.**
