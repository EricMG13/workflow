# Deploy Workflow

A focused project for analytical tools, executable modules and rendered deliverables.
The checkpoint is actual analytical tool use → validated output → downstream
consumption → rendered section. Production rollout is a later project phase.

## Start here

1. [Agent instructions](AGENTS.md)
2. [Scope and success criteria](docs/SPEC.md)
3. [Execution plan](PLAN.md)
4. [All-module coverage matrix](docs/MODULES.csv)
5. [Current assignments and resource queue](docs/QUEUE.md)
6. [Team](docs/TEAM.json) and [role instructions](docs/roles/LEAD.md)
7. [Reuse selection and known risks](docs/reuse/README.md)
8. [Current offline run guide](docs/RUN-GUIDE.md) and [separate production backlog](docs/PRODUCTION-BACKLOG.md)

## Layout

- `src/deploy_workflow/`: new supported host/tools/workflow interfaces.
- `src/deploy_vii/`: selected Claude baseline and reviewed local patches, with
  original hashes and patch history retained in `docs/reuse/manifest.json`.
- `cases/`: independent representative sources and expected outcomes.
- `tests/`: focused checks for new behavior and relevant reused behavior.
- `docs/`: one plan, one module matrix, a queue and concise evidence references.
- `artifacts/` and `runs/`: ignored local outputs, never imported credentials.

The bounded source/CP1/Model and CP1 chart slices have actual offline execution,
publication and rendered/native evidence. See docs/CP1-CHART-ACCEPTANCE.md for
the qualified synthetic cases and exact revisions. Component implementation or
registered metadata does not qualify other owners: docs/MODULES.csv remains the
actual tool/output/consumer/render record. The full 26-owner/six-pathway plan is
open. CP1B's projection and owner work is separately leased.

The imported core excludes the old network/provider drivers, spend ledgers,
launchers, CI apparatus and unrelated planning history. Paid/provider/live tests
remain paused. Source integration/push is separate from Model publication and
production deployment.

Python 3.13.15, uv 0.12.5 and the pinned dependencies in pyproject.toml are the
starting stack. Local validation may reuse an already installed matching runtime
with this repository's src explicitly first on the import path. Do not sync or
mutate another project's environment. No shared-runtime path is a product dependency.

## Local setup

Dependencies are locked in uv.lock. Run `uv sync --locked --offline` when the
cached Python 3.13.15/runtime packages are available; the bootstrap installed a
separate .venv without changing the old project environment. Source imports use
`PYTHONPATH=src`. The bounded offline financial JSON-lines entry point is
`python -m deploy_workflow.financial_workflow`; it requires an exact prepared
pack and actual stage participation. See the run guide before starting it.

The five chats use independent local clones recorded in docs/TEAM.json. PR MANAGER
owns the integration checkout. Its source remote is
[EricMG13/workflow](https://github.com/EricMG13/workflow); source commits are pushed
under the existing authorization. No production deployment or provider activation
follows from a push. The deterministic CP-MODEL publication is a verified local
artifact, described separately in the slice acceptance records.
