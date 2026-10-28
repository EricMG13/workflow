# Deploy Workflow agent instructions

## Goal and authority

The user authorized this separate project, selective reuse of relevant Claude code,
and initially four sessions: LEAD, COORDINATOR 1, COORDINATOR 2 and PR MANAGER.
On2026-10-27 the user added COORDINATOR 3 for Task4 earnings modules and explicitly
authorized uncapped active implementation. This repository
is independent of DEPLOY VII. Old sessions, plans, hooks, provider defaults and
release gates are references, not inherited authority. Never edit the old project
or depend on its mutable staged work. Read README.md, docs/SPEC.md and PLAN.md.

Every intended analytical module completes only after actual permitted tool use,
validated/settled output, actual downstream consumption and assigned rendered
sections. Review files, mocks, registered tool names and direct composers alone
are intermediate evidence. CP-MODEL and CP-OS are deterministic exceptions.

## Model routing

Claude Code took over from Codex on 2026-10-27 (user decision). The former
GPT-6.1 Sol/high route maps to `mx-feature`, GPT-6 Luna/medium to `mx-scaffold`;
historical records keep their original route names.

- `mx-feature` implements financial semantics, provenance/permissions, state,
  persistence, recovery and consequential parser behavior, and fixes in them.
- `mx-scaffold` handles fully specified mechanical changes and PR mechanics.
- Two Sonnet fix rounds per task. For a third, `mx-autonomous` writes a root-cause
  fix plan and a fresh `mx-feature` executes it; no Fable (user, 2026-10-28). There
  is no fourth: LEAD takes the open findings to the user. Only rounds that fix a
  High or Medium finding count (global §1 stop rule). Findings from any review of
  the same task share its two-round budget; a later review's findings never start a
  new one (user, 2026-10-28).
- `mx-precise` reviews each task and independently reviews financial/stateful
  expected results; `mx-adversary` also reviews diffs touching financial,
  ordering/concurrency or security code, and re-reviews only fixes of its own
  High or Medium findings. Opus/architect agents never write code.
- A re-review brief lists the finding IDs it checks, and the review checks only
  those. Anything else it notices goes under "Out of scope", never changes the
  verdict, and LEAD takes it to the user. When only Low or Info findings remain,
  the verdict is PASS with notes (user, 2026-10-28).
- When a second round hits the same defect class (for example crash residue
  between writes, a forgery path through a verifier, refusal mapping), stop
  patching sites. `mx-autonomous` writes one plan for the whole class (one atomic
  commit point, verify by replaying the producer's rules), and the lease states the
  threat model's bounds (which crash points, which forger) that reviews hold to
  (user, 2026-10-28).
- A fix round leaves a brief, a report and a commit. Do not save copies of the
  source or tests per round; the commit holds them. LEAD moves closed entries
  from docs/QUEUE.md to docs/QUEUE-ARCHIVE.md (user, 2026-10-28).
- Coordinator sessions plan and dispatch; they do not write product code.
- User instructions require confidence-review after any code change, before
  declaring completion or committing. Enumerate doubts, trace causes, refute
  suspects, patch confirmed defects and report remaining limits.
- After non-trivial code changes, run rewrite-tournament in no-argument post-edit
  mode on changed functions before declaring completion or committing. Renames,
  comments, docs, config, tests and generated files are exempt.

## Small tasks and independent expectations

One task owns one named behavior/invariant, a starting commit, exclusive files,
independent success/failure expectations and a concrete handoff. Define expected
values, units, periods, citations, statuses and downstream effects before evaluating
candidate output. Do not derive an oracle from the renderer or code under test.
An independent `mx-precise` review checks sensitive expectations. The global 800-line
PR cap does not apply to lane integrations (user, 2026-10-27). Reuse existing
reviews rather than add approval chains. Stop inventing policy at unclear semantics:
name the exact requirement and have LEAD resolve it from the adopted source.
LEAD's rulings are applied to a draft before its first independent review.

Module builds (user, 2026-10-28):
- An oracle or lease preparer runs the product's table, claim and render
  validators and a scratch double rebuild before handback, and reports their exit
  codes. Reviews after the first check only the diff. LEAD accepts the reviewer's
  rebuild exit code and does not rebuild again itself.
- Each module keeps one questions file (`work/<lane>/<module>/questions.md`). A
  module's first task lists its open semantic questions there (signs, bases,
  fail-closed cases). No build is dispatched until LEAD has ruled on all of them
  in one batch, frozen the oracle and marked the lease closed. Later questions go
  to the same file; Modules sends LEAD one message pointing at the files at most
  every 20 minutes, which also keeps both sessions under the app's message cap.
- LEAD rules only on questions that cross modules or change an oracle. The
  Modules controller decides questions that affect one module only, from its
  lease, and records each decision in the lane ledger.
- Module tests pin oracle and method files through one shared manifest of hashes,
  so an oracle change is one re-pin commit, not an agent round per module. LEAD
  releases oracle and lease changes at fixed points (once per stage), in
  dependency order with product-wording changes first, and each lease lists its
  pin consumers. Modules merges `codex/checkpoint` at each point instead of
  cherry-picking or holding individual LEAD commits.
- A defect class found in one module (for example the CP-8 soft hyphen) becomes a
  shared test every module runs, not a per-module hunt.

Dispatch (user, 2026-10-28):
- An implementer's first step enters a worktree cut from the lane tip and checks
  that `git rev-parse HEAD` equals the tip; stop on mismatch. Before launching a
  cohort, dispatch one agent and confirm it starts on the right commit.
- At most six Opus agents run at once across a session. Checks of a diff that
  only applies LEAD's ruling text go to `mx-feature`, not an Opus reviewer.

## Tool and data rules

- Use fixed supported source search/read/extraction and bounded frozen-upstream
  lookup/verification. Developer-agent tools do not prove analytical tool use.
- Keep declared source/field permissions. Upstream-only roles gain no raw-pack
  access. Python owns arithmetic. No arbitrary model-written code or shell tools.
- Retain case/source/upstream identities, actual tool arguments/results, submission
  and settled artifact identities, consumer references and visible output evidence.
- Preserve exact Decimal arithmetic, zero versus missing, entity/unit/period/
  definition identity, citation locators and honest blocked/gap states.
- Live/paid/provider testing remains paused. Local implementation and offline
  checks are permitted; no credential discovery or provider calls. Product model
  and effort choices remain distinct from coding-agent routes.
- Active implementation has no numerical lane cap, by the user's 2026-10-27
  instruction. Every lane still needs an exact exclusive lease and disjoint
  files/interfaces. The heavy-job lock is removed (user, 2026-10-28): test runs
  need no lock and no per-run LEAD admission record, and may run concurrently.
  After each run append one line to the lane's `work/<lane>/ledger.md`: UTC time,
  run name, command, exit code, pass/fail counts,
  `agent=<name> fix-rounds=<n> gates-first-pass=<y|n|n/a>` (`n/a` when the affected
  tests are deferred; static checks alone never give `y`). While tests are deferred
  (build-first, user 2026-10-28), a fixer runs every reviewer probe named in the
  findings it fixes, under 60 s each, and reports their exit codes. LEAD still
  admits new leases and commits for integration in docs/QUEUE.md. Do not freeze a
  run's source while another writer edits it, restart quiet tests, or kill
  unrelated processes.

## Ownership and reuse

LEAD owns PLAN.md, docs/MODULES.csv, docs/QUEUE.md and shared interface decisions.
C1 owns source tools and module/financial execution; C2 owns frozen lookup/verification
and rendering under exclusive leases. C3 owns the Task4 earnings workstream,
starting with CP1B under a separately reviewed exact lease. PR MANAGER alone
integrates approved commits.
Use docs/roles/*.md and docs/TEAM.json for exact sessions, lanes and starting tasks.

src/deploy_vii is a byte-preserved import of only the selected Claude workflow,
financial/tool/render dependency closure. It is not qualified in this repository.
New public interfaces belong in src/deploy_workflow. Do not copy old provider drivers,
ledgers, credentials, experimental launchers, entire test suites or planning history.
Additional imports need a named checkpoint need, source commit/hash and review.
Keep docs/reuse/manifest.json current; fix the known risks in docs/reuse/README.md
before the affected analytical tool use is counted. Historical evidence is scoped
by its original version/case and is not a new-project pass.

Enterprise identity, deployments, broad platform/provider certification, background
launchers and optional OCR/workbook-export services are deferred unless a named
required tool invocation cannot work without a bounded part. Do not recreate the
old production programme as a checkpoint dependency.
