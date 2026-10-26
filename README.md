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

## Layout

- `src/deploy_workflow/`: new supported host/tools/workflow interfaces.
- `src/deploy_vii/`: selected unchanged Claude implementations and their actual
  local dependencies, retaining the package name to avoid a broad rename.
- `cases/`: independent representative sources and expected outcomes.
- `tests/`: focused checks for new behavior and relevant reused behavior.
- `docs/`: one plan, one module matrix, a queue and concise evidence references.
- `artifacts/` and `runs/`: ignored local outputs, never imported credentials.

The bootstrap contains reusable functions, not an implemented new CLI or accepted
all-module workflow. LEAD/C1/C2 begin with the source host and frozen lookup tools.
The imported core excludes the old network/provider drivers, spend ledgers,
launchers, CI apparatus and unrelated test/planning history. Import provenance and
known defects are explicit. No paid call, enterprise deployment or production claim
is authorized by this scaffold.

Python 3.13.15, uv 0.12.5 and the pinned dependencies in pyproject.toml are the
starting stack. Local validation may reuse an already installed matching runtime
with this repository's src explicitly first on the import path. Do not sync or
mutate another project's environment. No shared-runtime path is a product dependency.

## Local setup

Dependencies are locked in uv.lock. Run `uv sync --locked --offline` when the
cached Python 3.13.15/runtime packages are available; the bootstrap installed a
separate .venv without changing the old project environment. Source imports use
`PYTHONPATH=src`. No new command-line entry point is claimed yet.

The four chats use independent local clones recorded in docs/TEAM.json. PR MANAGER
owns this checkout for integration. These are local repositories; no GitHub remote,
publication or production activation was created.
