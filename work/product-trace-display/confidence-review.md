## Confidence review — TRACE correction 1

Scope: current `app.js` correction from source commit `08ea888540f9ea140ab849829446bb03941cc4ef`; shared ordinary fix round 1 for TRACE-SRC-01/02 and related Low.

Least confident about (ranked):

1. Removing the fact.module_id predicate could weaken cross-module identity and compact a fact from another module.
   investigated → The frozen payload shape places `module_id` on the containing module, while serialized facts carry `table_id`, `row_id`, `fact_id`, `field`, `status`, and `unit`; a pinned CP-1 TRACE fact has `module_id: null`. The helper still requires exactly one matching parent module for the coordinate's module_id and exactly one fact in that module matching coordinate table/row/fact, then requires expected field, known status, and native `%`.
   adversarial case → If two modules share an otherwise identical fact, only the coordinate's uniquely selected module's facts are inspected; duplicate matching facts within that module fail closed. A fact with mismatched table/row/fact fails closed.
   verdict → CONFIRMED bug in prior predicate; this correction removes only the nonexistent child identity test and retains the actual parent/fact identity chain.
   patch → removed `fact.module_id === coord.module_id`.

2. A coherent foreign table coordinate could pass the identity and unit checks.
   investigated → Product behavior is specifically TRACE; exact fact matching alone accepts any coordinate table. The coordinate now must have `table_id === "trace"` before module lookup; fact table must still match coordinate.
   adversarial case → a coordinate and fact both labeled `other-table`, with matching row/fact/field/status/unit, return original text. A TRACE table coordinate continues only through exact matching.
   verdict → CONFIRMED bug in prior guard.
   patch → require literal TRACE table ID.

3. The regex `$` might accept a valid decimal followed by a final line terminator, violating strict ASCII decimal grammar.
   investigated → Independent review cites ECMAScript CompileAssertion semantics; without multiline mode `$` asserts actual input end. The grammar already requires ASCII digits/dot and is unchanged in this correction.
   adversarial case → a final newline cannot satisfy the assertion under this regex mode.
   verdict → fine; do not change grammar.
   patch → n/a.

4. Cell copy, route opt-in, or passport binding may be affected by the guard correction.
   investigated → The change remains inside the identity helper. The helper's return is still used only in a copied display cell. `renderBlock` still opts in only for Relative Value `instrument-levels`; twin/Inspector/Model call sites omit opt-in.
   adversarial case → every non-TRACE route and non-front caller sees the default false; identity ambiguity continues to return the original text.
   verdict → fine by caller tracing; DOM behavior remains unverified.
   patch → n/a.

Fixed: TRACE-SRC-01 / TA-01 phantom child module predicate; TRACE-SRC-02 foreign-table acceptance.
Verified fine: exact parent module uniqueness plus actual serialized fact identity; strict TRACE table requirement; decimal grammar; copied-cell/display-only boundary.
By-design: any missing, duplicate, ambiguous or inconsistent identity preserves the original text.
Still open: scoped independent re-review; Pre-Testing comparator/guard execution and native browser/runtime acceptance. No runtime observations are claimed.

Checks: `git diff --check` passed; `node --check src/deploy_vii/assets/app.js` exited 0 (syntax only). No tests, probes, comparator, compiler, browser or workflow gate was run.
