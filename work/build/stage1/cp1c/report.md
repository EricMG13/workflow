# CP-1C Stage 1 report (agent text; written by the controller because the host refused the agent's write)

- Branch `worktree-cp1c-stage1`, commit `d1103da`, base 509f7db. Files: `owners/__init__.py`, `owners/cp1c.py`, `tests/test_method_cp1c.py`.
- Surface: compute -> PeerBenchmarkResult, calculation_issues, parse_peer_source, peer_metrics, ratio, median, peer_median (None below 3), position, outlier (None at a zero median), difference, shown; schema PeerBenchmarkSubmission/PeerAssessment/Overall/Gap.
- Inputs: run issuer_name; pack sources in the H1 scope (identity, financial, peers); CP-1 T4.10 LTM Q4 25 metrics (exactly one each); judgment.
- Test: 61 passed in 0.38 s. Gates 0. gates-first-pass=n. The RED run was not observed: the hook refused the first write.
- Covered: positive/gap/no_peers restricted to T1C.2–T1C.7 (every fact, rows, FP03 tabs, operands_summary); claims except universe; own limitations; policy_constants; r01–r12; every fixture; a run-time lineage test.
- Pending amendment 1: implemented per the ruling (T1C.8 "Peer universe totals"), not asserted. A scratch probe with renamed ids matched T1C.1, the universe claim and r13/r14. Open: where T1C.8 sits in fact and table order.
- Left to Stage 2/4: tool_refusals, tamper, execution, blocked, settled limitations, cp1_readiness, refused, d8, FP03 rendering, RULES/view.
- Engine/oracle disagreements: none.
- LEAD points:
  1. An included peer with a not_applicable own ratio raises.
  2. An issuer line that can't be recomputed raises.
  3. A missing peer row gets the reason "Not stated in the peer source" (own wording).
  4. Own PeerTableError wordings.
  5. Own path wording `assessments[<n>].rationale`.
  6. Prose references are checked only when the assessment set is consistent.
- Confidence review: non-ASCII digit parsing was patched to ASCII regexes.
