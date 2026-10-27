# A4 fixture-reference addendum — numeric zero figures and missing chips

Same A4 expected-result review continuation, not a new financial gate. Immutable A4 contract cf562507e8bb5322eb67e7c3338afa52867ff59b7807f95d9dcf30359b589ade and independent review ba27cc9db6d2aeb4cf28c8643a1a15a14b4b7dc3bd15ce95e3dd4ae8933b392d remain unchanged. Original integrity oracle raw SHA256 `a23517e8bcd3b344496ca982e735e4882065a4b27345f5a0e770e922ba25bd8f` is preserved byte-for-byte at work/cp1b-preparation/integrity-expected-pre-reference-fix.json. Corrected active cases/integrity/expected.json SHA256 `90871a0027bf5fd616ef09495e92399735f22a2dafad76d2488134a892733c13`.

## Confirmed source rule and exact correction

Adopted prose.py254–276 checks numeric presence with amount is not None; zero is numeric. [fin.rev] and [earn.delta] therefore produce claim_figure findings rather than the intended clean baseline. Use EXACT baseline Claim.text strings:

- Revenue observation {fin.rev|MILLIONS}.
- Delta observation {earn.delta|MILLIONS}.

MILLIONS is the facts' own declared native unit and therefore accepted by _fact_issues regardless of shown US-dollar scale label. No amount, scale, citation, financial value or zero status changes. A scale mutation still yields only scale_unit: figure syntax tests the declared unit, while CP5 independently checks unit/scale.

For unsettled_unlimited and unsettled_limited, after fin.rev becomes missing amount null, explicitly switch its Claim.text back to EXACT 'Revenue observation [fin.rev].'. The adopted tokenizer treats that chip as a gap reference; no numeric figure is asserted. Leaving the figure syntax would correctly create an additional claim_figure, contrary to the intended isolated unsettled_fact counts. The unlimited variant still has no claim limitation and one unsettled_fact; the limited variant retains its explicit limitation, one structured unsettled record, and zero mechanical findings.

Two scope-mutation declarations are made explicit without changing categories/counts: blocked omits the non-evaluated CP1B ClaimReview and retains the unchanged CP1 review; empty uses empty claim_reviews/contradictions/gaps. Otherwise the unchanged baseline raw reviews would be invalid references to non-evaluated modules, so their declared restricted valid report status would be conditional/ambiguous. No blocked claim is silently evaluated. This is exact fixture setup, not relaxed production claim coverage.

All other strings, values, categories/counts, wire schemas, transport/page/call caps, APIs, source grants, actual financial/math/source/B1 authorities and A4 lineage decomposition remain unchanged. No C1 source/test or B1/delivery-author file was edited. Tests must consume these corrected literals under their existing admission; source-only derivation here does not claim runtime results.

## Exact active-oracle JSON-pointer diff

- `/literal_component_fixture/producers/0/claims/0/text`
  - Before: `Revenue observation [fin.rev].`
  - After: `Revenue observation {fin.rev|MILLIONS}.`
- `/literal_component_fixture/producers/1/claims/0/text`
  - Before: `Delta observation [earn.delta].`
  - After: `Delta observation {earn.delta|MILLIONS}.`
- `/literal_component_fixture/causal_mutations/4/mutation`
  - Before: `Only fin.rev becomes amount=null/status=missing/limitation=Not supplied; summary limitation remains null`
  - After: `Only fin.rev becomes amount=null/status=missing/limitation=Not supplied; CP1 summary.text='Revenue observation [fin.rev].'; summary.limitation remains null`
- `/literal_component_fixture/causal_mutations/5/mutation`
  - Before: `Previous missing fin.rev plus summary.limitation=Observation is unavailable within this scope.`
  - After: `Previous missing fin.rev with CP1 summary.text='Revenue observation [fin.rev].'; summary.limitation=Observation is unavailable within this scope.`
- `/literal_component_fixture/causal_mutations/7/mutation`
  - Before: `Component ReviewScope includes current CP1B input/head status blocked, classified blocked, CP1 remains evaluated`
  - After: `Component ReviewScope includes current CP1B input/head status blocked, classified blocked, CP1 remains evaluated; raw_review.claim_reviews contains only the unchanged CP-1 summary review (omit non-evaluated CP1B review)`
- `/literal_component_fixture/causal_mutations/8/mutation`
  - Before: `Component ReviewScope evaluated heads empty, blocked empty`
  - After: `Component ReviewScope evaluated heads empty, blocked empty; raw_review.claim_reviews=[], contradictions=[], gaps=[] (no evaluated claims)`

## Eleven mutation trace

| Mutation | Independent source-derived mechanical result | Review/status implication |
|---|---|---|
| bad_fact_quote | fact_citation1, all other mechanical0 | supported review invalid via flagged fact; figure remains syntactically numeric/cited |
| bad_claim_quote | claim_citation1, others0 | supported review invalid via claim marks |
| bad_scale | scale_unit1, others0, amount remains0 | supported invalid via flagged fact; MILLIONS still valid declared figure unit |
| unresolved_claim | claim_figure1, others0 | unresolved chip names no known/missing fact; supported invalid |
| unsettled_unlimited | unsettled_fact1, others0; unsettled record limited=false | missing chip is valid prose; no claim limitation causes the sole finding |
| unsettled_limited | all mechanical0; unsettled record limited=true | missing chip plus explicit limitation; no zero substitution or invented numeric figure |
| identity_twice | figure_identity2, others0; two groups differ in value | same Fact ID and same coordinate group each compare0 versus1; original CP1 ref flagged |
| blocked | blocked_upstream1, others0; only CP1 claim evaluated | valid reduced evaluated-set review yields restricted report |
| empty | empty_evaluated_set1, others0 | empty review matches empty evaluated claims and yields restricted report |
| unsupported | mechanical all0; unsupported_claim1 | labels-only rationale + unsupported verdict with empty refs accepted structurally; restricted report |
| partly_supported | mechanical all0; partly_supported_claim1 | existing own reference retained; restricted report |

The separate contradiction fixture remains literal opposed qualitative disclosures with source-matching citations; no numeric chips are present. Its two own policy#c1 references resolve by producer, exactly one analyst contradiction and no mechanical finding remain expected. This is not semantic approval for an arbitrary unsupported contradiction.

No product import/validator/engine/test/provider/job ran. The same sensitive-review lineage applies; no accounting/count relaxation or extra approval chain. Selected Sol/high independent expectation role is evidenced by LEAD's assignment, not hidden telemetry.

## Separate known B1 claim dependency

The original fixture PASS did NOT approve the then-frozen B1 numeric-chip claim for actual settlement or imply clean CP5; the exact separate source correction is now reviewed below. LEAD independently confirmed the B1 exact positive/no-YoY texts contain chips for known numeric facts, and Execution.candidate_issues unconditionally invokes prose_issues. The original owner author must freeze the separate native-figure/gap-chip override before actual B1 progression. A4's owner-authority references and source-grounded first-case claim-catalog byte proof must then explicitly bind that correction; the original proof/history remains retained as transport-only evidence. No B1/source/product/delivery file is changed by this erratum, and no old raw candidate result is promoted by wording.

## Same-review B1 override and coherent A4 proof update

Root-authored docs/CP1B-CLAIM-REFERENCE-ADDENDUM.md SHA3341de531ec2d20ebac3c30bb3a753c2fc00e60b2fdaa95ef065e6c774160bcf overrides only known monetary reference grammar. Current owner oracle is a37dc25f8f756364ae88726cdec3f2de1bbf4c20892ca910d22e9646186efd9d; original e66 B1 lease and c8 oracle remain unchanged historical authority outside that override. E-QOQ-FLAT uses six same-ID MILLIONS figures; E-NO-YOY uses two known same-ID MILLIONS figures and retains the three nonknown gap chips. valid_own_fact_references_only replaces chips_only. No number, unit, period, lineage, citation union, limitation,44/12/one-claim count or wire/API changes. Independent owner-claim-reference-review.md records that source-grounded PASS; grammar validity alone is not analytical support or actual settlement.

The exact intermediate integrity oracle ef5e0e17541b9ad86e1c1dd80090ca9c8bd6e16bb16cd2c818e7b0dabe299fdb is preserved in work/cp1b-preparation/integrity-expected-pre-owner-reference-update.json. The coherent active oracle additionally changes ONLY four scalar leaves: top owner_oracle_sha256 and static proof owner_oracle_sha256 to a37dc25f; claims second-page BODY977->1031 bytes; claim catalog digest67396429a142851a745090d65f90a89424a86382866e9b01af1ae267ee23f304->5b4b95fc79cfe552df2c66452b7d147bf780b1da62f64e175adb2b666de77428. Required refs/counts/all other catalog hashes/page sizes unchanged. The previous proof remains in exact archived oracles and original review source.

A stdlib-only full15-section reconstruction, scanning every1..20 prefix/terminal wrapper, parsed both numeric figures and missing chips by ID. It reconfirmed all12lineages/24operands/252companions/35operand-cites/44owner identities and75+6required facts,65tools/70messages, manifest3459 and largest page8088 within8192. The known figure grammar adds54UTF-8bytes to the one-record terminal claim page, not a new point, financial value or scope. No product/core/engine/validator/test/provider ran. Actual B1/CP5/render participation remains separately unverified.
