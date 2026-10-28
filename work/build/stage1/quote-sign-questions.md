# Shared quote-reader questions (CP-1D, CP-3D, CP-8, CP-2E)

## For LEAD (one batch)
- B1 (CP-2E round 10 review I1). The sign is read on the quote only. A quote that starts at the digit (`25 percent` cut from the page's `−25 percent`, or `25)` from `(25)`) is a contiguous substring, `quoted` accepts it, and the unsigned text validates. Applies to all four readers. A fix is a rule change (read the page character before the quote's match).
- B2 (CP-3D round 10 review L1, decided locally as a riding Low): the parenthesis exclusion applies only when the match starts with a digit, so `(-425)` with `-425` keeps today's shape refusal.
- B3. A public joined-reading helper in `deploy_vii.quotes` (normalise does not join quote-side hyphen wraps; CP-8 L-1, CP-3D Low 1; the CP-2E fix 1 review notes the same gap for `-\n`).
- AGENTS.md rule 3: this class (raw read after a normalised match, and sign reading) should become one shared test every quote-reading module runs. Proposed as a Modules task once LEAD confirms B1.

## Ruled by LEAD round 11 (d60035b)
B1: a figure at a quote edge is read on the page. B2: Modules decides (CP-3D keeps the shape refusal for `(-425)`). B3: no helper; a name or text value with `- ` on a hyphen-wrapped quote does not occur. The shared class test is a Modules task (stage1/defect-classes-brief.md).
