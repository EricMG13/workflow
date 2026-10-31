# Review brief: one public-issuer golden (mx-precise, read-only)

You review one case directory, `cases/goldens/<case_id>/`, prepared under `work/model-testing/goldens/CONTEXT.md` and `briefs/<issuer>.md`. You did not prepare it. Never edit the case files or the repo. Put probes in your scratch directory.

The golden will judge whether live models populated the deliverable accurately. A wrong golden fact means a model is marked wrong for being right, so be exact.

## Check
1. **Facts vs source.** Sample at least 30 known facts, or all of them if there are fewer, weighted to the brief's core modules. For each, re-find the value in the primary source yourself (write a stdlib script; use `cases/goldens/check.py`'s `visible_text` if helpful) and confirm:
   - the value, sign, unit, scale, period end and subject;
   - the right instrument, entity and column (borrower vs parent, principal vs carrying, commitment vs funded, fair value vs quote).
2. **Completeness against the brief.** List anything in the brief's scope that the filings print but the golden omits, or marks `missing` while it is printed.
3. **Derivations.** Run `derive.py`; check that the operands and operation are right, not merely that the arithmetic recomputes.
4. **`context.json`.**
   - Check it against the form rules (`git show 5325c209:docs/templates/context-form.html`, `build()` :721-806) and the proposal (`git show 5325c209:docs/CONTEXT-FILE-PROPOSAL.md`).
   - Values must be supported by the filings.
   - Nothing may be invented (market data, peers, ratings).
   - Defaults are used where the user has supplied nothing.
5. **Judgment calls** in `prepare-report.md`: agree or disagree, each with a reason.
6. **Spot-check against Codex's financial gold** (path in `module_golden.json` `financial_gold`): where a module fact overlaps a Codex metric (for example cash or total debt at the same date), the two must agree or the difference must be explained.
7. Run `python3 -I cases/goldens/check.py cases/goldens/<case_id>` and report its exit code.

Do not re-report these known controller findings: G-1 scale (thousands are stored as printed; fix pending), G-2 zero-width characters, G-3 BGS peer_source, G-4 SHC dash as zero.

## Report (≤ 1.5k tokens)
- Verdict: APPROVE / REVISE.
- Findings, each with:
  - an id `<CASE>-R<n>` and severity (High = a wrong value or wrong subject; Medium = a missing in-scope fact or a context.json rule breach; Low or Info);
  - the fact_id or path;
  - what the source shows, with the source file, locator and quote;
  - the probe script path and its exit code.
- End with a `Not verified:` line.
