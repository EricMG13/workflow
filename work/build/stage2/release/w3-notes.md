# W3 integration notes (collected from W2 reports)

- **B a70ee52.** The CP-2D `run_rate_annual` question is ruled: no reader or oracle change in this release. CP-3C reads `T2E.3.r01` from the bound head, and the lease text records that (YAGNI: no consumer needs it on `Cp2dHead`). Record it as round 5 item 20 at W3.
- **B's TOOL-CONTRACT rows** cite `cases/<cp>-owner/<cp>-view-tree.json` for CP-1C, 1D, 2G, 2H, 3C and 4C. After the merge, check that all six files exist.
- **Stale comment at `cp3c.py:2368`.** It says the oracle consumption block names the run-rate pin; it does not. Fix it at W3 if A1 has not; it is comment-only.
- **D 291fa8e.** The owner cores are not reused files: the reuse manifest has no `owners/` or `methods/` records, so they need no D12 records.
- **D duplication.** Each of the four cores (cp1c, cp2g, cp2h, cp4c) has its own `_one_per_page` copy. Run jscpd at W3; if it flags them, hoist one shared helper.
- **D v08 interpretation, for the release review.** v08 gains a separate `unread_issues` key, with `refusal_rules.journal` reworded. `expected_issues` keeps the validator's single line. Check this against the close-release text "limitations equal the issues".
- **D cross-lane pins.** The cp2h and cp4c builders pin CP-2G files. W3 must run the full chain.
- **C c8b708b.** Its `readiness.py` change moves the pin at `cases/legal/manifest.json:290` (119058ff… → 01616654…). The W3 chain must re-pin it; `PINS.json` does not list this file, so `pins.py --check` misses it.
- **C, new known ruff finding.** `prose.py:114` and `:127` ISC004 predate the change and are unchanged.
- **C, method notes.** `methods/cp1d.md`, `cp2e.md` and `cp1c.md` still say blank means "whitespace and Cf only". Fix the text at W3 to match the new `is_blank`.
- **C, the verbatim sinks: the release review must check them.** C listed three paths as verbatim, not fixed: `consumers.*.missing_source`, `sources.*.scopes.*.limitations.*` and `sources.*.limitations.*` (CP-1).
  - `missing_source` goes through the readiness text check (`readiness.py:321`) and is rendered nowhere else.
  - `scopes.*.limitations` becomes a rendered gap row (`source_context.py:496-497`). It is **not** in `readiness` `_texts` (:314-326), so check whether any text check covers it. If none does, that is a predating CP-1 owner finding, not a release fix.
