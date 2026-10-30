**Re-review verdict on G2 gaps spec revision 1: APPROVE.** All six earlier findings are fixed, both marked deviations are correct, and no High or Medium finding is left.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g2-gaps-spec-review/` (shortened to `<R>` below). They ran on a fresh `git archive e37b73e` copy, which I deleted afterwards. No worktree was written; `git status` is clean.

**Preparer's probes:** probe0 to probe5 all exit 0, and none reports a perturbation as wrongly accepted. Outputs are in `<R>/out_probe*.txt`.

**Deviation (a): the index-entry rule is right and no longer passes vacuously.**
- `build_index` (`report_view.py:803-869`) creates an entry exactly when a fact has a ref: a G# when its status is not known, a C/S per citation, or a K# for a `calculation_id`.
- The oracle-driven rule matches that, with one branch it does not model: a known fact in (T4.9, threshold) whose text fails the strict parse also gets a G#. In the cp4 oracle the only such fact is `4.00x`, which parses and already needs an entry, so it does no harm here (`<R>/probe_strict_t49.py`, exit 0).
- My earlier vacuous-pass perturbations now fail:
  - cp3d positive: 6 index entries of facts with `cites == []` removed; the check fails.
  - cp3d gap_no_market: 36 such entries removed; the check fails.
  - New, cp8 positive: 29 entries of known facts with `cites == []` removed; the check fails.
- Probe: `<R>/probe_extra_perturbations_rev1.py`, exit 0. I dropped its cp4 part because probe2's helper signature changed. probe2's own cp4 perturbations cover cp4.

**Deviation (b): the limitations order follows the core rule and reads nothing from G2.**
- The core builds `own = dict.fromkeys(candidate + SYNTH)` (`execution.py:476-481`), removes `own` from the inherited list (`:366`), and the view joins own then inherited (`:957`).
- So the page order is oracle own, then SYNTH, then the oracle's inherited list without SYNTH. That is exactly what `dict.fromkeys(own + [SYNTH] + inherited)` gives.
- Its inputs are the oracle lists plus the core's SYNTH literal, and the test asserts the oracle's inherited list contains SYNTH.
- probe5 shows the plain `own + inherited` order is wrong on all 5 settle-built pages, so my earlier probe was too lenient. Probe5 exits 0.

**My six findings:**
- Medium 1 (cites on every table): fixed. Counts are 45/39/7 (cp3d), 58/21 (cp8), 61 (cp4), with a minimum of 1 asserted.
- Medium 2 (missing index entry): fixed, as in (a).
- Low 3 (cp3d/cp8 rails pointers): fixed.
- Low 4 (CP-1 `inherited_limitations`): fixed; the rule now follows the oracle text word for word.
- Low 5 (label run colon): fixed.
- Low 6 (cp4 field check): fixed.

**Low (new)**
- For s1a, each cell's expected fact is `{status: known, cites}` and carries no `calculation_id` (the oracle cells have none). If a real CP-1A known fact has a calculation but no cites, the rule demands no entry while the page has a K# entry. That would show up as a false failure in the genuine s1a cases, not a false pass. Probe4 cannot show this because its rebuilt module has no calculations.

**Info**
- The required-entry rule does not model the strict-parse G# branch. It is harmless for these oracles, but a builder comment should name it.

Not verified: no genuine runs, so real passport numbering, the store's CP-1 head, settle-built limitations on real pages and real CP-1A calculations are unexercised. I did not re-perturb cp4 beyond what probe2 itself does.
