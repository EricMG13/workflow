amends: 0007 standalone mode
anchors: CP-0, CP-1

# Decision 0007 amendment: CP-DR LOCAL lineage has two anchors

This amends only the standalone-mode clause of decision 0007. The decision itself stays cited where it is (`src/deploy_vii/contracts.py:157`, `src/deploy_vii/cp2_synthesis.py:17`, `src/deploy_vii/cp4_legal.py:17`, `src/deploy_vii/execution.py:241`); none of those cites is repointed.

## Decision

1. The standalone issuer/sector mode, a CP-DR with no CP-0, is withdrawn.
2. CP-DR in this repo has LOCAL lineage and two anchors: a validated, non-Blocked CP-0 and a validated, non-Blocked CP-1. Python checks that the issuer, run and period match and that the hashes match, including that the CP-0 supplied is the CP-0 that CP-1 consumed.
3. An unanchored mode would need its own contract. It is not built.
4. OD10: LOCAL lineage never claims `FULL_CP_OS`; a LOCAL dossier is never `COMMITTEE_READY`, and its ceiling is `RESEARCH_READY`.
5. OD2: the gap-research CP-DR (CP-0 gaps → TDR.1-3) is retired, because this version excludes subject-borrower gap filling; the `cpdr-owner` case and its frozen oracle are replaced through the Modules process (a separate preparer and an independent `mx-precise` review).
