# B4 report: D12 records (OI-6) and the CP-1 chart oracle pin (OI-7)

Branch `claude/oi-b4-manifest`, cut from 559ba54. `post_import_patches`: 73 -> 79 records. All shas computed from git (`sha256(git show <commit>:<path>)`); script and probes are system `python3 -I`, stdlib only.

## D12 records

Rule applied: where the chain lacked a lane first-parent change, that change got a record (lane = `git log --first-parent 559ba54`); a branch record whose own `^1` and result match the chain after those inserts is kept with its prior corrected; the fork record 8aef58d is folded.

| Record | Before | After | Git evidence |
|---|---|---|---|
| cffdf9f x9 (business_context, cp2_synthesis, cp3_relative_value, cp4_legal, cp5_integrity, cp6_committee, narrative, prose, quality) | no prior | prior = sha of `cffdf9f^1:<path>` (equals the imported sha, so the chain links) | `git show cffdf9f^1:<path>` |
| 3e5b537 report_view | no prior | prior c934d501 (imported) | `3e5b537^1` |
| 1a1a140 live/schema.py | no prior, chain from imported c6374419 broken | prior 9854394f; inserted lane record ff7b7b2 (c6374419 -> 9854394f) before it | walk of 559ba54 first-parent: ff7b7b2 c6374419->9854394f, 128c3ca 9854394f->68fb91b0 (same transition 1a1a140 records, so no separate 128c3ca record) |
| bb4553b live/tools.py | no prior | prior 2d607ea2; inserted 1668904 (380c20eb -> d4071e59), ff7b7b2 (-> 3b84b58b), 128c3ca (-> 2d607ea2) | first-parent walk; `bb4553b^1` = 2d607ea2 |
| bb4553b live/submission.py | wrong prior 6656846f (the imported sha) | prior 1d92f7d5; inserted 07a41d6 (6656846f -> a6b8919e), ff7b7b2 (-> 01ea63df), 128c3ca (-> 1d92f7d5) | first-parent walk; `bb4553b^1` = 1d92f7d5 |
| 8aef58d report_view | GAP (prior 51a6853e, result 4edad0a3) | removed; folded into 24f879a, reason labelled "Folded from 8aef58d" with its reason kept | 24f879a^1 = 09ab059d (the chain after b9d937e); item 52 precedent |
| 24f879a report_view | prior 4edad0a3 (BAD) | prior 09ab059d, reason extended | `24f879a^1` |

Inserted records (6) carry `project_commit`, prior/new sha from git, reason = the commit subject plus "reconstructed from git, 2026-10-30", and `review` = `docs/rulings/2026-10-30-open-items.md` (the ruling that orders them; it lands with the open-items merge, not on this base).

Choice vs the triage simulation: the sim used the lead-branch merges 144659f and e04259d as intermediates; the brief says the lane first-parent line wins, so ff7b7b2 and 128c3ca are used. Same 73 -> 79 count. bb4553b and 1a1a140 are kept (they pass item 19 once the chain is filled) rather than folded into 67df6a1 / 128c3ca; no other record changed.

## Gates

- Strict probe `python3 -I work/build/keep/s53-B/probe_d12_strict.py <worktree> df26ea8 HEAD`: exit 0. It prints no summary line; the output has 79 `pip` lines, 0 BAD, 0 GAP, 0 FAIL (grep count 0), saved at the scratchpad `b4/probe.out`. Before: exit 1, 15 flagged.
- Manifest loads (`json.load`): 79 records.
- `python3 -I cases/pins.py --check`: exit 0, "cases/PINS.json matches 87 paths" (86 -> 87).

## OI-7

`PATTERNS` and the docstring gain `cases/charts/expected.json`. `git diff cases/PINS.json`: one added line (sha 2ca2606c...), nothing else. `git log --oneline -- cases/charts/expected.json`: only 44cc41d (freeze); no change since.
