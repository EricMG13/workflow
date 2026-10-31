# Fix batch 2 (Lows from the redesign review): docs/templates/context-form.html

Same rules as before. Edit only docs/templates/context-form.html. No commit.

- **Q1:** `update()` rebuilds the stepper buttons and the `#steperr` links on every call, so a
  click that follows a field blur can land on a replaced element and be lost. Update stepper
  buttons in place (text, class, `aria-*`, disabled state) and rebuild `#steperr` only when its
  error list changes.
- **Q2:** `#steperr` (`role="alert"`) re-announces on every keystroke. Covered by the same
  "rebuild only when the list changes" rule as `#nextlive`.
- **I3:** give `im-as_of` the same date help text as the other date inputs.
- **Layout (controller, browser check):** at desktop width the Issuer step puts four fields in a
  row and truncates the "e.g." placeholders. Use at most two fields per row on desktop (one
  under 600px) so every placeholder shows in full; apply the same to other steps' field grids
  (row tables may stay wider but must not truncate placeholders).
- I1, I2: no change.

Run `p1_syntax_network.sh`, `p2_planned_gating.sh`, `p3_gate_callsites.sh` (probes folder as
before) and your jsdom checks. Report as text with exit codes and a `Not verified:` line.
