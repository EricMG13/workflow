## Adversarial Review: completion plan and session boundary

**Scope:** Full original completion plan, session/worktree audit, AGENTS.md/CLAUDE.md,
live ruling and relevant runner behavior; then both revised plans. Documentation
review, not runtime qualification. Original plan SHA-256:
`dc86dccc7e16abe89346621ea8f69e8e3428ffa878a77b18c43cad2952524d19`.

**Verdict:** Original **BLOCK**; revised plans **CLEAN, with readiness notes**.
Findings below are resolved in the documents. This does not qualify the product or
authorize a provider launch.

Method: one reviewer used the personas sequentially, Saboteur → New Hire → Security
Auditor. These were perspective changes, not three independent reviewers. Duplicate
findings were merged and promoted per the
[adversarial-reviewer skill](/Users/ericguei/.agents/skills/adversarial-reviewer/SKILL.md).

### Critical Findings

**AR-01 — Implementation and acceptance shared an execution lane. Resolved.**

Original locations: Phase 1 lines 109–144; Phase 2 lines 146–185; Phase 3 lines 187–223.
New Hire found no operational boundary between testing and product construction.
Security Auditor found the corresponding trust-boundary gap: the acceptance lane could
change the product and its measure of success in the same flow without a clear handoff.
WARNING → CRITICAL by the skill's promotion rule.

Applied: the existing plan now belongs exclusively to Pre-Testing; a separate plan/
session owns product implementation, product repairs, design and other completion work.
The user's clarification controls the split: **all testing and related work stays in
Pre-Testing**, including keys, fixtures, comparisons, harness/scoring work, RUN-P5 auditor
work, launch gates, CI diagnosis and proof. This corrects the initial split proposal
that would have moved test preparation to the product session. Oracle preparer,
verifier author and builder remain separate agents. Product defects return through
a repair handoff and Pre-Testing independently verifies the fix.

**AR-02 — Revision recording lacked a complete admission and invalidation boundary.
Resolved.**

Original locations: parallel work lines 31–34; provenance line 60; Phase 1 integration;
Phase 5 repairs. Saboteur found no explicit rejection of dirty/changing candidates
while other work continued. Security Auditor found that keys or scoring could change
without an explicit new evidence version and invalidation decision.
WARNING → CRITICAL by promotion.

Applied: T2 freezes product/runtime assets, test instruments, inputs/context/recordings/
keys/mappings, exact scope/argv, reviews and authority before admission. Tests use a
separate clean checkout. Missing prerequisites or version mismatches reject admission.
Changes produce new versions and invalidate affected results; originals remain intact.
Re-scoring is distinguished from rerunning execution. Bounded CP1 and full-workflow
admissions are separate.

### Warnings

**AR-03 — Complete offline recordings had no preparation owner or provenance contract.
Resolved.**

Original location: Phase 4 lines 229–233. New Hire found a prerequisite with no
production task; an executor could wait for future live success or mistake scripted
responses for model-quality evidence.

Applied: T1 assigns recording/fixture preparation to Pre-Testing, records provenance/
hashes and distinguishes scripted offline inputs from retained live transcripts.
Scripted inputs still exercise actual product tools, settlement and consumers.
Incomplete recordings block their cases; injected heads, receipts or scores do not
qualify them. Offline readiness does not depend on future successful live runs.

**AR-04 — Mandatory fresh live passes repeated already valid complete evidence.
Resolved.**

Original location: Phase 5 lines 278–282. Saboteur found that even a complete passing
run on the final candidate had to repeat because the phase ended, consuming budget
needed for unfinished cells.

Applied: T5 allows a complete pilot/repair run on the final qualified release to
satisfy its cell. Relevant changes invalidate affected full pathways; partial replay
never replaces a required complete pass. Every remaining pass is costed against
shared actual exposure. The single USD25 allowance cannot renew through a new thread,
gate, release or retry.

### Notes

- Document checks passed: valid links, 26 unique owner identities, all six pathways
  in both plans, clean whitespace and the required final Answer Key tables.
- Missing keys, comparisons, recordings and product functionality remain preparation
  work. Proposed manifest/run-card paths are not represented as existing tools or passes.
- The runner can exit zero with stopped outcomes. T4 explicitly requires outcome,
  coverage, receipt and comparison checks. Run cards must use supported selectors.
- CI status, worktree heads, current provider capabilities and balances are dated
  evidence or future execution checks, not newly verified facts.
- This review changes documentation only. No product code, credential file, provider
  call, merge or runtime qualification was performed. Code-changing sessions still
  owe confidence-review and rewrite-tournament where applicable.

### Summary

The original plan mixed product construction with validation and left candidate/test
instrument admission underspecified. Both revised plans keep all testing-related work
in Pre-Testing, isolate product work in a separate session and define evidence handoff,
repair, invalidation and spending boundaries. The remaining work is execution and
runtime proof; the documentation verdict does not claim project completion.
