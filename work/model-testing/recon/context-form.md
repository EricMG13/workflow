# Recon: the context form (2026-10-31)

Source: the session "Context file for workflow modules" (`local_8803e348`), worktree `project-goals-overview-6dc197`, branch `claude/workflow-context-file-db27f3`.

## Commits
- `5325c20` is on `codex/checkpoint`. It added:
  - `docs/CONTEXT-FILE-PROPOSAL.md`, the spec;
  - `docs/templates/context-form.html`, an offline step-by-step form that writes `context.json` (schema `context/1`);
  - `docs/templates/portfolio.template.xlsx`.
- `4fd966f` and `0a284ff` hold the consumption plan `docs/superpowers/plans/2026-10-31-context-file-consumption.md` and the PLAN.md "Outstanding" entry. The PR manager is waiting on the user's own word before merging them.

## What context.json supplies
What the filings cannot:
- run settings: run type (primary, secondary, research, earnings), pathway (one of six), case_kind, as_of, current and prior period, currency;
- identity: names, guarantors, ticker, sector, sponsor;
- deal terms;
- quotes;
- ratings;
- valuation: peer source, basis, issuer market data, peers, precedents, user multiple;
- optional pinned assumptions for CP-2A, CP-2D, CP-2E, CP-3C, CP-3D and CP-4C;
- attachments: portfolio workbook, prior case, management bridge, legal documents;
- research questions.

Rules:
- Numbers are plain decimal strings; empty means not supplied, never zero.
- The file enters the pack as a hashed `text/plain` source with id `context`. Owners read it from the frozen pack.
- The filings confirm and the context supplies: a conflict becomes an issue, never an override.

## Status
- Nothing reads `context.json` yet.
- The plan is approved (D1–D5 as recommended) but **not started**:
  - Phase 1 is the foundation: the `deploy_workflow.context` reader, pack preparation, the frozen-pack reader, and CP-0 accepting the context source.
  - Phases 2–8 are the module consumers, each under its own lease, owned by Modules. They include: CP-1B periods; CP-1C EV/EBITDA; CP-DR web peers (stays Planned while provider calls are paused); pinned assumptions; CP-4 drafts; non-USD currency; real agency names in CP-2H; quotes replacing `rv_quotes`.

## Bearing on model testing
- The user requires every test run to be driven through the context form: one `context.json` per issuer and pathway.
- Phase 1 is a hard prerequisite.
- Each module tested needs its phase merged, or the context fields it reads are ignored.
- The six pathways in the context form match the six Codex issuer pathways.
