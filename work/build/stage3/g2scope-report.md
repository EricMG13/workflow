# G2 scope-table preparer report (mx-feature ac60d03f, claude/s3-g2scope dbd4c7c)

G2 delivery-scope lease amendment (rev 2) is committed. Nothing was rendered or run through G2, which doesn't exist yet, so the banners are drafts.

**Tip SHA:** `dbd4c7c` on `claude/s3-g2scope`, one commit on `ab9777f`. `git diff --stat` touches only `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-g2scope/docs/OWNER-RENDERING-LEASE.md` (+149 lines). The commit message ends with the Co-Authored-By line.

**Rows:** 19 triples in total. Two exist already (`cp1-model`, `s1a-credit-snapshot`) and 17 are new. Of the new rows, 15 are ready and 2 are gated.
- **Gated:** `cp6-fp01-committee` and `cp3c-fp04-refinancing`.
- **Covered:** the section has all of these for every row.
  - The scope table.
  - Banner literals for each supported outcome (21 new texts).
  - Oracle path with JSON pointers.
  - Run fixture and its return shape.
  - The per-scope acceptance additions.
  - The list of modules with no row.
- **Checks:** a script built each driver case's `Run` and compared it with its row, and checked section order against `_PRESETS` and against the oracle block keys. It covered the 16 driver rows and passed. The other three triples were compared by eye.
- **Triples:** all distinct. CP-2G needs two rows because its positive run requests `("CP-2G","CP-1D")` and its gap run requests `("CP-2G",)`.

**Disagreements and my choices:**
- **D1, CP-2D `maturity-wall`:** the lease puts it in the scope. The oracle pins only its owner (MODEL, `stage3_pending`) and Q-C1 made it Model-owned. I dropped it from the sections and added it later, after the S.4 wiring.
- **D2, CP-3C `T3D.1`:** the oracle binds it to `refinancing-paths`, but Q-C2 draws it in `funding-gap`. The row follows the ruling, with `funding-gap` first. It is gated until the binding moves and the oracle is re-pinned.
- **D3, CP-2E:** the lease says "module page and rails" but G2 proves only sections and rails. I set `sections=()` and put the module-page check in the scope's acceptance. This also makes an empty `sections` valid for rails-only rows.
- **D4, CP-3 and CP-6:** the CP-3 lease says `cp6_closed` exists, but `tests/cp3_cp6_runs.py:6` says it doesn't, and there is no CP-6 core. So the CP-6 row is gated. CP-5 has no run of its own, so it shares that row.
- **D5, CP-DR:** the lease gives it a rails-only scope entry, so it gets `slice-cpdr-research`. The brief said "none per Q1", but I found no "Q1" text in the CP-DR lease.
- **D6, CP-4:** section order follows the pathway, not the oracle dict order.
- **D7, drivers:** return shapes differ (two paths, three, or a workflow for `cp8_closed`). I recorded each shape per row and left the drivers unchanged.
- **D8, refused outcome:** rev 1 M1 now needs a pinned refused run and a driver that can produce it. CP-1D, CP-8 and CP-L10 have the oracle pin but no driver case, so their refused outcome is deferred.
- **D9, case_kind:** it is `synthetic` for every row, taken from the packs.

**Questions for Modules:**
- **Q-S1:** confirm CP-DR gets a row, against the brief's "none per Q1".
- **Q-S2:** confirm both gated rows ship only after the Q-C2 wiring and the CP-6 core. The alternative is to ship `cp3c-fp04-refinancing` now without `funding-gap`, which leaves `T3D.1` unasserted.

Not verified: no rendering or G2 code ran, so the oracle block trees were compared only for section order and key sets, not against product output. The CP-3 core was not run. The refused-run pins were read from oracle text, and the refused drivers for CP-1C, CP-2A, CP-2G, CP-2H and CP-4C were checked only to list the case. Banner wording and the "five-field" block check (title, owner, kind, state, tabs) are my own drafting.
