CP-4 Stage 1 draft notes (not run). Design for src/deploy_workflow/owners/cp4.py:

MARKERS = ("has the meaning assigned in", "is not supplied with this copy")
_ISSUE = "covenants[{i}]: metric_basis 'Same definition' is refused because the cited source text matches incorporation-by-reference markers: {markers}"

def _norm(text): return re.sub(r"\s+", " ", text).casefold()

def semantic_issues(*, pack: PreparedPack, submission: CovenantInterpretationSubmission) -> tuple[str, ...]:
    for i, covenant in enumerate(submission.covenants):
        if covenant.metric_basis != "Same definition": continue
        scope = [quote texts of covenant.citations] + [span.text of every pack source span whose
                 (source_id, locator) a citation names, each (source_id, locator) once]
        hits = [m for m in MARKERS if any(m in _norm(t) for t in scope)]
        if hits: issue with markers "; ".join(f"'{m}'" for m in hits)

@dataclass(frozen=True) Cp4Inputs(pack, submission, upstream: cp4_legal.Upstream, inputs: tuple[Input, ...])
@dataclass(frozen=True) Cp4Result(issues: tuple[str, ...], report: CovenantInterpretationReport | None)
def compute(inputs) -> Cp4Result: gate first; then cp4_legal.validate_covenant_interpretation; then
    cp4_legal.covenant_interpretation.

Test approach (tests/test_method_cp4.py): build the pack from the manifest pack_sources plus frozen pages
(found by sha256 in cases/financial and cases/legal manifests, raw rule checked); construct
cp4_legal.Upstream directly: authority = expected[case].CP-0.T3_authority, legal_sources =
legal_sources_for_cp4, facilities and cp1_status from cp4_step_view.expected_values, one CP-1 fixture Fact
built from figures.predicate_facts + financial q4_ltm_metric_oracle.net_leverage_reported (amount "1",
unit MULTIPLE), row label "net_leverage_reported" (T4F.2 label prefix), fixture cp1_gaps and head hashes.
Substitute <<FIG:net_leverage_reported>> with the fixture id. Compare all 31 tables generically
(fact_id, column, text, status, cites, value_class, limitation) with explicit handlers for the run-time-bound
cells: T4.9.r01.current/headroom/headroom_share, T4C.8 cp_1_metric/metric_period, T4F.1 *.sha_256,
T4F.2 copy, T4F.3 metric_operand/result, T4F.5 r01..rN template.
