# Independent CP4 FP04 pre-code binding contract review

Result: **PASS for the exact component contract/oracle freeze**:

- docs/CP4-FP04-BINDING-LEASE.md SHA256 a13cacb71a9e403b8fdc504db6ad4bd7ade7821d87e41f6b1c9cf433900b03fc.
- cases/legal/render-expected.json SHA256 5200b47e9986bc715da9f1d2a342ca40a4d3d2d77c3afdc1179fde35f28edb4d.

This reviewer is independent of C2's future implementation. No code, source-owner,
CP5, selected-run receipt or native acceptance follows. LEAD may commit/integrate
these exact files and issue the exact two-file implementation/base/resource lease.
No new financial audit or approval chain was introduced.

## Authority and source pins

C2 original proposal433d422a667e385791ee1c1230b5fd2ac2c340193f3deb7535f374fbb2dd3c01
and JSON440f60888b8c13a297639fcae1c811d0b2fa5a9c24b1d9c994f67d42f06ae18d
were read and left immutable. Reused legal manifest
d6a8ec15285dbe16a6e2ff3f167c26a295b675decfb4df7231901b0243305168,
source contract80f21f1e73063655e799496c3484a51576ff5e9649f03383b341ed7ff2aa453a,
and independent review f6b816587587d5eca6db808c5f8b3a2c4c60cea27bcbe1dba5d0769ddae6013a.
All source strings and original numerical/status expectations remain unchanged.
No recomputation of the financial engine/legal threshold/headroom occurred.

Accepted reference4e2bce9df0e010f0795c392e8254db12fce5fcfe and current inspected
main9a527d4d8b4624a2d7e189223805abcf6324ad5d have the same relevant source bytes:

| Source | SHA256 |
| --- | --- |
| cp4_legal.py | 1b2246ff9b0c0797c25d259c3e408436dfcc874b48be4cf1b2f77566c2bc4128 |
| bindings/cp4.py | 484448f5fbbc81995efa9e8f3e5f1b636c01bbc9d16234a5be44107b6baa7f97 |
| bindings/shipped.py | 4ef3f9ffdc9a6e10461dbe722e8222c8803ccba1ab49f42b9cd9db07bf9d4fec |
| report_view.py | 21dc5c341c85eeb22a372f3c3a97e48b28f0dd37b7f9a62be1d5851e4785808b |
| contracts.py | ee1b27f912804ab81887401a99177f99068247e8c4ba53c000b0d3fde0205e74 |
| display.py | efdcd5d60400e47c1210442ed165e0642bcb3770aaaebf526dfcb7b750588398 |

The code-start revision must still be LEAD's subsequent admitted exact integrated
base. No moving branch/source pointer is treated as a completed check.

## Contracts and counts checked independently

Static AST parsing of literal _register calls (not importing/executing the module)
reproduced all31 ordered table titles/columns/field spellings/header rules and
matched every schema in the proposed oracle. Literal _bind calls reproduced all
31 existing binding objects exactly. All slots/table IDs unique; CP4 ships once.
No new map/file/shipped change is needed or allowed.

Placement:7 front bindings across6 typed dense sections;19 Evidence;5 Limitations.
Six exact specs map T4.9,T4.10,T4.11,T4.13,T4C.6 and T4.2+T4C.12. The last is
Document register primary/Facility coverage tab, with all columns intact. Global
_spec_of gains one immutable mapping with no collision with another adopted
pathway's block IDs. Eleven-section FP04 order and its other5 fallback sections
stay unchanged. Their CP2D/CP3C/CP4C responsibilities remain unimplemented here;
no CP4 liquidity/funding/refinancing/LME answer is invented.

Oracle contains31 complete seeded rows/102 unique facts for the positive and a
separate gap append row/106 facts,6 specs,13 success checks and32 structural/
binding refusal cases. These seeded row/fact counts are not production invariants.
Production row IDs/labels/count/order and source precision remain variable.

Public API unchanged: build(View,Pathway,Iterable[BindingMap])->ReportView.
Only new private CP4 guard and immutable FP04 spec metadata inside report_view.py;
future C2 owns only that file and new tests/test_legal_render.py. No wrapper,
source/upstream/engine/receipt/asset change or new legal parser is granted.

## Ranked doubts and resolved pre-code corrections

1. **Full-analysis stale output hidden by front filtering.** Existing _block
   hides nonshown modules, but render's HTML payload serializes supplied blocked/
   stale Fact arrays. A valid-shaped prior fixture carried into a stale view
   could therefore remain in Full analysis. Freeze now explicitly rejects
   output-bearing nonshown CP4 at its scoped guard. Actual Execution.view already
   clears nonshown facts/tables/claims, so valid current views are unaffected.
   Empty blocked/stale states remain honest; no generic renderer or asset change.

2. **Legitimate copied CP1 IDs/header/labels accidentally rejected.** Current
   _referenced_table preserves each original CP1 fact ID and all fields except
   placement, with refNN rows/header CP-1 figure. Empty reference set emits a
   canonical none/not_applicable row/header None. Normal CP4 facts use generated
   table.row.field IDs. The guard must preserve both forms and source labels,
   even when a Fact.label differs from its column heading (current numeric facts
   also retain source label). It must not require fixture prefixes, globally
   unique IDs across producers, fixed source row counts or decimals=None.
   The seeded current/copy labels explicitly test Reported net leverage.

3. **Mixed native units over-restricted by table defaults.** Binding default
   multiple/amount/text is not each cell's unit. Ratio/percentage/pp cells retain
   native scale1/currencyNone; copied/current source units/scale/currency/precision
   survive unchanged. Known headroom can be MULTIPLE or pp; share PERCENT; gap
   Cell unit/period legitimately null. The generic guard is structural, not a
   case-specific legal judgment, threshold parser or arithmetic repair.

4. **Calculated value falsely implies a K passport.** _computed retains formula
   and calculated value_class but assigns no calculation_id. build_index allocates
   K only for IDs. Correct component assertions preserve exact formula/citations
   and inspect Full Fact fields without inventing a K ID. Original copied source
   facts may legitimately have their own calculation ID; those are not stripped.
   Source/gap passports resolve canonical identities even after fact reordering,
   rather than assuming fixed S/G/K numbers or globally deduplicated fact owners.

5. **Seeded data mistaken for genuine upstream authority.** Fixture runs use
   fp04-component-positive/definition-gap, explicitly synthetic/candidate with
   CP0/CP1/CP5 empty unrun and unselected Model/others not_in_pathway. Fixture-only
   descriptor hashes come from explicit literal strings; CP4 descriptor differs
   per case. No foreign genuine CP1 result hash/receipt is borrowed. Two quoted
   text templates and the fixture hash sentinel were concretized from supplied
   literal citation groups/hash seed, without a composer. Source/stated metadata
   in seeds is preservation data, not proof raw statements report the derived1x.

6. **Known zero/unknown capacity or missing definition confused.** Existing
   source/numeric review governs1x comparator/4.00x threshold/3x headroom/.75 share.
   Gap preserves the same supplied known comparator and specific missing Schedule A
   definition reason, null headroom/share, Not calculable/No. Unknown capacity
   remains null with the adopted capacity-not-calculated explanation. Fully drawn
   zero unused commitment has no dedicated current CP4 output cell; nothing is
   inserted into capacity_amount. Artificial0 headroom is presentation-only.
   No90m arithmetic distance is relabelled permission/commitment/capacity/funding.

7. **Display shorthand becomes a source number change.** Read unchanged native
   formatter metadata, then independently used stdlib Decimal/ROUND_HALF_UP
   quantization only:1 ->1.00x,3 ->3.00x,.75 fraction ->75.0%,0 ->0.00x. No product
   formatter/renderer/import, legal engine or financial re-audit ran. Canonical
   exact values and explicitly supplied Decimal representation remain unchanged.

8. **Rail binding is misrepresented as visible rail tables.** Current Evidence
   shows source inventory/source passports; current Limitations shows module
   limitation strings. Bindings cover all31 tables, but do not mount19 evidence
   tables on the rail. Full analysis retains all tables/fields/trace/copies;
   Module.limitations must also carry scope/omitted protections/capacity/
   unaudited/perimeter and gap-specific Schedule A/not-calculable limits. No
   source-only fake visible/native/download pass or asset lease is inferred.

9. **False Same definition accepted as a mechanical-refusal test.** Current core
   trusts that supplied judgment; it does not derive legal equivalence from the
   source. The later semantic acceptance refusal remains frozen by the legal
   source contract. This component guard does not hard-code the case/sourcehash,
   values or judgment string to simulate an automatic refusal. Actual source-to-
   submission semantic review/owner-currentness/receipts remain separate callers.

## Static evidence and limits

All31 schema metadata checks matched source AST; all31 binding objects matched;
fixture row field order matched schema columns;102 seeded positive Fact IDs were
unique.26 copied citation records' hashes/quotes were lexically checked against
the exact selected supplied pages and all matched. This is preservation of
already reviewed literal evidence, not new financial/legal source interpretation.
Original C2 proposal and legal manifest/contract/independent-review hashes were
rechecked unchanged. JSON parse/AST/hash/Decimal literal checks used stdlib only;
no product import/test/validator/composer/engine/provider/browser/heavy job ran.

The remaining concrete caller gaps do not block this component lease: supported
CP4 source epoch plus genuine promoted-CP1 auth/upstream grant; actual current-
epoch legal read/search/submission/validation/settlement and public legal owner
receipt; complete selected CP1+CP4 CP5 participation/final composition compatible
with that legal owner (not relabelled earnings receipt); authenticated legal render/
native proof and the other5 FP04 responsibilities. Existing source contract already
names them. No new fictional API or broad approval chain was invented here.

Only the three assigned LEAD files were written. C2 proposals and source/numerical
oracles remain immutable. Explicit inherited Sol/high independent-role assignment
is route evidence, not hidden telemetry. Docs/expectation data only: later C2 code
must run confidence-review and no-argument changed-function rewrite-tournament,
independent sensitive review and admitted focused tests before completion/commit.

Not verified: future implementation/tests, actual source/legal owner/CP5 execution or semantic acceptance, authenticated selected-run delivery/native visibility or providers.
