# B1 claim reference grammar correction

This is a narrow pre-code correction of the two exact comparison claim strings.
The original B1 lease e66aa2df765ff76c2fe9644ba2f5c003dc65572ad6060246538265171bc54071
and original owner oracle c8af02d3760f0ac24a8ecd2e2e6d2f3be38f260c706d200995b12c0f3d37456d
remain historical authorities for every unchanged rule. The original oracle is
archived byte-for-byte in LEAD work/cp1b-preparation/owner-expected-pre-reference-fix.json.
This addendum overrides only the known numeric reference syntax and the oracle's
old misleading chips-only declaration. The current owner oracle hash is a37dc25f8f756364ae88726cdec3f2de1bbf4c20892ca910d22e9646186efd9d.

## Source rule and confirmed defect

Execution.candidate_issues unconditionally applies prose_issues to a candidate.
The adopted prose._fact_issues requires a numeric figure reference whenever
Fact.amount is not None, including known zero. A text chip for such a fact fails
settlement. A figure reference over a nonknown fact also fails. This rule already
exists; no CP1B exception or later CP5 waiver is allowed.

Use {own-fact-id|MILLIONS} for the six known monetary references in E-QOQ-FLAT
and the two known current monetary references in E-NO-YOY. MILLIONS is the
unchanged native Fact.unit; the token is an expectation, not an inline copied
numeric answer or a display conversion. Keep the three nonknown no-YoY
prior/delta/growth references as existing [own-fact-id] chips.

## Exact claims

Claim ID remains cp1b-comparison. E-QOQ-FLAT text is exactly:

Flat sequential earnings comparison: {cp1b:T1B.1:revenue:delta|MILLIONS} {cp1b:T1B.1:ebitda:delta|MILLIONS} {cp1b:T1B.1:adjusted_ebitda:delta|MILLIONS}. Current balance observations: {cp1b:T1B.2:cash_closing:current|MILLIONS} {cp1b:T1B.2:total_debt:current|MILLIONS} {cp1b:T1B.2:net_debt:current|MILLIONS}.

E-NO-YOY text is exactly:

Current earnings observations: {cp1b:T1B.1:revenue:current|MILLIONS} {cp1b:T1B.1:ebitda:current|MILLIONS}. Requested prior income comparison is unavailable [cp1b:T1B.1:revenue:prior] [cp1b:T1B.1:revenue:delta] [cp1b:T1B.1:revenue:growth].

The oracle now declares valid_own_fact_references_only=true, replacing the
old valid_own_fact_chips_only key. Only the same own-module fact IDs qualify.
Claim citations retain the original first-occurrence union from those exact
referenced facts, and both claim limitations remain byte-identical.

## Compatibility and verification

No value, unit, period, basis, source/citation, status, fact/reference ID, table,
44-fact/12-lineage/one-claim count, financial calculation, actor review, wire
record, public API, grant, raw/setup/session policy, budget or receipt field
changes. Original A1, A2, A3, financial/source and case descriptor pins remain
unchanged. Actual OwnerPins and OwnerSetup must commit the current owner oracle
bytes before a fresh run; old temporary/component evidence retains its original
version and is not relabelled. No existing qualified owner run is migrated.

A4 continues to import the actual B1 typed receipt/public verifier. Its current
owner-oracle pin and static first-case claim catalog proof must reflect these
strings; old proof artifacts are preserved. Qualified fact references and
required evidence membership do not change. Other actual CP5 findings remain
honest; valid grammar does not assert semantic support or a clean report.

Later causal verification must show the old numeric-chip candidate rejects under
the adopted settlement/prose guard, the new known numeric figure references pass
that guard, gap chips remain nonnumeric/limited, and actual fresh owner settlement
still satisfies every original source/participation/core requirement. Those
product checks and actual owner/CP5/render qualification are not established by
this source-only correction. Paid/provider tests remain paused.
