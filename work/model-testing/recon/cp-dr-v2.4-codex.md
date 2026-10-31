# CP-DR v2.4: Codex's change list for Deploy VII (pasted by the user, 2026-10-31)

User: "here is codex suggestion for new cp-dr, which need to be created and function as intended in the context session."

Source: https://chatgpt.com/s/cx_6ae5d71465b48191a213e58ff45b5172 (Codex, read from screenshots of the user's work-side Deploy V v2.4 design; the v2.4 scripts/build are not pinned or validated).

| Area | Change |
|---|---|
| Purpose and scope | Independent research supporting CP-1C and CP-2. Excludes subject-borrower document gap filling. Preserves missing canonical inputs; never manufactures replacements. |
| Prerequisites | Validated, non-Blocked CP-0 and CP-1 for LOCAL runs. Verify issuer, run, reporting period and hashes, incl. that the CP-0 supplied matches the one CP-1 used. Stop on mismatch. (Today: CP-0 only.) |
| Invocation and modes | Default LOCAL, no CP-OS runtime dependency. Explicit invocation, normally after CP-1; not auto-inserted into every pathway. FULL_CP_OS only when explicitly requested and separately supported. |
| Research brief | Locked, versioned brief. Default six questions: competition, metric definitions, valuation context, market demand, industry structure, regulation; tailored from CP-1 issuer context and definition conflicts. User-defined scope, receiving modules, research cutoff, max 32 questions. |
| Research evidence | Supplied/public-source intake with retained content, hashes, locators, dates, evidence-family relationships. Contrary-evidence review, source-independence assessment, explicit uncertainty. Reject evidence after the cutoff. |
| Outputs and validation | One Markdown dossier plus brief JSON. TDR.1 locked questions and recipients; TDR.2 claims and located evidence; TDR.3 answers, contrary evidence, uncertainty, downstream use. Completeness, handoff and research checks. LOCAL dossiers carry `cp_dr_lineage: LOCAL` and cannot be Committee Ready. |
| Consumer integration | Dossier attached to CP-1C/CP-2 as supplied-source context in their source registers; not an analytical upstream dependency. Traceable to the exact dossier version. |
| Optional v2.4 pack | Opt-in TDR.4-6: candidate peers, provisional alignment observations, located peer/transaction figures. CP-1C only; CP-1C verifies and admits independently. |

Ownership stays explicit: CP-1C owns peer admission, AP1-AP11 alignment, normalisation, statistics, outlier interpretation, implied EV. CP-2 owns risk assessments, financial profile, materiality, monitoring triggers, credit conclusions. CP-DR supplies context, never authoritative substitutes.

Deploy VII-specific points (apply to Deploy Workflow's copies):
1. Decision 0007 (:62) standalone CP-DR mode with no CP-0 conflicts with LOCAL's two anchors; update the policy; an unanchored mode needs its own contract.
2. Separate source provenance from module dependencies: a source-attachment mechanism that records the dossier hash and refreshes affected consumers, not CP-DR as an optional dependency of CP-1C/CP-2 (`execution.py:223` input binding).
3. Research capability in the runner: a retrieval stage that retains verifiable evidence before analysis (`live/prompts.py` offers no tools today); existing citation checks reusable.

Sequence: method/version record and contracts → base LOCAL research → CP-2 and CP-1C integration → optional peer pack. Acceptance cases: anchor mismatch, blocked inputs, cutoff violation, missing/contradictory evidence, dossier replacement, LOCAL readiness ceiling.

Caveat (Codex): screenshots establish the design, not that the v2.4 scripts/build pass validation. User ruling 2026-10-31: "there will be no work version set, it need to make its version based on my intend usage and the information provided." This repo builds its own CP-DR version from this description; no parity check.
