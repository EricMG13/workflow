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
- Two Sonnet fix rounds per task; the third and later go to a fresh `mx-escalate`.
- `mx-precise` reviews each task and independently reviews financial/stateful
  expected results; `mx-adversary` also reviews diffs touching financial,
  ordering/concurrency or security code. Opus/architect agents never write code.
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
An independent `mx-precise` review checks sensitive expectations. Reuse existing
reviews rather than add approval chains. Stop inventing policy at unclear semantics:
name the exact requirement and have LEAD resolve it from the adopted source.

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
- Use at most one heavy local job. Active implementation has no numerical lane
  cap, by the user's2026-10-27 instruction. Every lane still needs an exact exclusive
  lease and disjoint files/interfaces. Since the 2026-10-27 Claude handover a test
  run needs no per-run LEAD admission record: take the global heavy-job lock
  (`mkdir /tmp/deploy-workflow-heavy-job.lock`; wait while it exists, never delete
  another lane's lock), run, `rmdir` it, then append one line to the lane's
  `work/<lane>/ledger.md`: UTC time, run name, command, exit code, pass/fail counts,
  `agent=<name> fix-rounds=<n> gates-first-pass=<y|n>`. LEAD still admits new leases
  and commits for integration in docs/QUEUE.md. Do not
  freeze a run's source while another writer edits it, restart quiet tests, or kill
  unrelated processes. Static checks (ruff, mypy) need no lock.

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
