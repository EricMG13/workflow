# Fix round 1: docs/templates/context-form.html

Same rules as brief.md. Edit only docs/templates/context-form.html. Do not commit.
Probes live in /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-project-goals-overview-6dc197/8636ed04-09eb-46c0-b2dc-59b1d24948f9/scratchpad/probes/

- **F1 (Medium):** gate every module-named consequence on the current module list
  (`has()`): peer sourcing and the auto/blend/precedents basis items on CP-1C; draft-document
  mode on CP-4; real agency names on CP-2H; non-USD on CP-2D; CP-1B period pair on CP-1B. Count
  only pinned assumptions whose module (cp2a→CP-2A, cp2d→CP-2D, cp2e→CP-2E, cp3c→CP-3C,
  cp3d→CP-3D, cp4c→CP-4C) is in the list. Probe `p2_planned_gating.sh <html>` must exit 0.
- **F2 (Low):** loading must not use loaded keys in CSS selectors: iterate known keys from the
  spec (or compare `el.dataset.k === k`). Validate the whole file before `resetAll()`, so a bad
  file changes nothing and shows its error.
- **F3 (Low):** the CP-2A "add 1 to 4 scenarios" error names "CP-2A scenarios", not "undefined".
- **F4 (Low):** rating scope cards get one line each: Issuer "Rating applies to the issuer";
  Facility "Rating applies to one facility".
- **F5 (Low):** loading an empty `run.as_of` loads it empty (it then shows its required error).
- **F6 (Info):** update `#status` text only when the error count changes; remove aria-live from
  the panel's consequence list.
- **Design hook:** `.tag` (line ~145) and `.panel .sig li b` (line ~169) use
  `var(--rb-fs-micro)` (10.5px). Use `var(--rb-fs-label)` (11px). Leave the token block as copied.
- **F7:** no change (fixed keys are kept, confirmed).

Report as text: what changed per finding, the exit codes of `p1_syntax_network.sh <html>` and
`p2_planned_gating.sh <html>`, and a final `Not verified:` line.
