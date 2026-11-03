## Confidence review — TRACE front display

Scope: `src/deploy_vii/assets/app.js` diff from `51590329c06aaa09853bb41ed514702d12683875`.

Least confident about (ranked):

1. A passport alias could resolve to the wrong fact, causing unrelated front text to be compacted.
   investigated → `compactTracePercent` searches only `front.index.facts[].ref_ids`, requires exactly one matching entry, requires the coordinate row to equal the visible row, then requires exactly one module and one fact matching module/table/row/fact IDs and the selected `period_0` or `period_3` field. The fact must also be `known` and native `%`. No visible value or label participates in lookup.
   adversarial case → duplicate index hits, coordinate for another row, duplicate module/fact, wrong field, absent coordinates, or another unit each returns the original text.
   verdict → fine by fail-closed guards; runtime cases remain Pre-Testing-owned and unexecuted here.
   patch → n/a.

2. The lexical trim could change non-decimal spellings, sign, or significant digits.
   investigated → the regex accepts only ASCII `-?[0-9]+\\.[0-9]+`; only trailing fractional zeroes and a resulting final period are removed. It does not parse, round, scale, or normalize negative zero.
   adversarial case → `-0.000` becomes `-0`; `7.000000` becomes `7`; integer `7`, `+7.00`, `(7.00)`, `7e0`, `.50`, `7.`, Unicode digits, and text are unchanged by the guard.
   verdict → fine by code inspection; independent comparator owns executable expectations.
   patch → n/a.

3. Canonical source/cell identity or Inspector text could be mutated while preparing the shortened display.
   investigated → the only altered value is a shallow display copy with a new `text` property. Existing renderer receives the original `owner` block; source/passport lookup remains bound to the unchanged `ref_id`. `twinPanel`, chart twins, and tab panels omit the opt-in. `renderBlock` opts in only for `front.pathway.id === "relative_value"` and `block.block_id === "instrument-levels"`.
   adversarial case → calls from Inspector and chart twin use the default `false`; all Front Page column headings and visible accessibility labels also use the opt-in-derived labels, while other headings use original labels.
   verdict → fine by caller tracing; browser behavior is unverified.
   patch → n/a.

4. Malformed index/module entries might throw instead of preserving the canonical spelling.
   investigated → null/non-object entries are filtered before property access; absent/non-array index, modules, or facts return the original cell. The JSON payload itself is parsed by existing startup code and remains outside this patch.
   adversarial case → null index entries, null module entries and null fact entries cannot be selected as matches; missing arrays fail closed.
   verdict → fine within this helper; malformed top-level report JSON remains existing behavior and is outside scope.
   patch → added object guards at each indexed collection boundary.

5. Selected heading and cell accessible name could disagree.
   investigated → the same `columnLabel` function supplies both the table header and `cellNode` label; override is limited to indices 0 and 3 when opted in.
   verdict → fine by call-path inspection; screen-reader verification remains unperformed.
   patch → n/a.

Fixed: object guards for malformed coordinate collections.
Verified fine: identity/unit/field guards, lexical-only shortening, non-mutating cell copy, narrow render opt-in, and shared visible/accessibility column labels as traced above.
By-design: source display does not infer facts from values; any ambiguity preserves the raw front cell text.
Still open: independent Pre-Testing comparator/guard execution and native browser observation/acceptance; independent product review. Those remain with their designated owners.

Checks: `git diff --check` passed; `node --check src/deploy_vii/assets/app.js` exited 0 (syntax only). No product tests, fixtures, comparators, compiler, browser, or workflow gates were run. Workflow gates are deferred to Pre-Testing.
