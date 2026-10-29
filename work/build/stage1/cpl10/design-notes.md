CP-L10 Stage 1 design notes (draft, not run). Use as input for the re-dispatched implementer.

Inputs: Upstream(issuer_name, as_of: date, cp0_status, cp0_result_sha256, cp1_status, cp1_result_sha256,
cp1_facts: Mapping[label -> deploy_vii.contracts.Fact]) where label = '<column> · <metric>' (28 T4.10 operands;
a missing key -> ValueError "unbound CP-1 operand"). Submission = raw JSON/Mapping, parsed with
ChangeScreenSubmission.model_validate_json (Contract is strict: lists only become tuples in JSON mode);
shape issues via deploy_vii.readiness.shape_issues (gives "comparison.from_period: Field required").

Arithmetic: change = Fraction(close) - Fraction(start), quantised once to Decimal in Context(prec=38, ROUND_HALF_EVEN);
change_pct = exact change / |start| (signed Fraction), quantised the same way; materiality on the exact Fractions:
|d|*10 >= |a| Material, |d|*20 >= |a| Watch; start == 0 -> Stable/Material with change_pct not_applicable.
Rank key: (class Material/Watch/Not assessed/Stable, zero-base Material first, -|pct|, register index).

Shown text: report_view.fact_spelling(fact, "G1") with "G1" mapped back to the oracle's "G#" (display._gap_id rejects "G#").
Copied cells: Fact(**{**dict(cp1_fact), fact_id/table_id/row_id/field/label, decimals=2 if known MILLIONS else None}).
Target titles: deploy_vii.registry.modules() titles of CP-1D/CP-2A/CP-2D.
Prohibited words: recommend, recovery, covenant -> "<path>: prohibited conclusion: <word>".
Text checks: prose.check(text, refs=prose.bind(python facts).keys(), gaps=(), names=(issuer,)) prefixed "<path>: ",
then prohibited, then "<path>: empty" for whitespace-only. Fields: assessments[i].assessment, .credit_transmission,
overall.rationale. Confidence other than Medium/Low -> "<path>.confidence: <v> is not allowed in a screen".

Findings to raise with LEAD:
F1 ReportTable incompatibility: TL10.2 `total` row (4 facts: material/watch/stable/not_assessed) and TL10.3 `overall`
   row (2 facts) do not match their tables' columns; contracts.validate_tables raises "Report row does not match its
   columns", so a product Module with the oracle's tables cannot be built (Stage 2 blocker).
F2 Lease view key tree lists values {period, status, shown, limitation}; expected.cases.*.view_topics also carries
   amount_exact, and the lease says the view "equals expected.cases.positive.view_topics".
F3 TL10.1 scope_status / source_ref are "bound at run time" in the oracle with no spelling fixed.
F4 Validation order steps (5) overall and (6) gaps name no rule beyond confidence; overall.limitation and gap texts
   have no stated content checks. Confidence "Insufficient Information": lease says "Medium or Low", wording unpinned.
F5 Claim citations are not pinned (Claim.citations is required; () assumed).
