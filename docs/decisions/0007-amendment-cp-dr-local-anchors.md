amends: 0007 standalone mode
anchors: CP-0, CP-1

# Decision 0007 amendment: CP-DR LOCAL lineage has two anchors

This amends only the standalone-mode clause of decision 0007. The decision itself stays cited where it is (`contracts.py:157`, `cp2_synthesis.py:17`, `cp4_legal.py:17`, `execution.py:241`); none of those cites is repointed.

## Decision

1. The standalone issuer/sector mode, a CP-DR with no CP-0, is withdrawn.
2. CP-DR in this repo has LOCAL lineage and two anchors: a validated, non-Blocked CP-0 and a validated, non-Blocked CP-1. Python checks that the issuer, run and period match and that the hashes match, including that the CP-0 supplied is the CP-0 that CP-1 consumed.
3. An unanchored mode would need its own contract. It is not built.
4. OD2 and OD10 are recorded. LOCAL lineage never claims `FULL_CP_OS`; a LOCAL dossier is never `COMMITTEE_READY`, and its ceiling is `RESEARCH_READY`.
