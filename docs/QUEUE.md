# Work queue

Bootstrap is being prepared; no analytical module is accepted.

| Owner | First bounded work | Files | State |
| --- | --- | --- | --- |
| LEAD | Task0 source/upstream interface and independently expected cases | docs/TOOL-CONTRACT.md, cases/*/manifest.json, matrix/queue | Ready after bootstrap handoff |
| C1 | Source-tool reuse/known-risk analysis, Task1 lease proposal | Own clone; source/host files only after Task0 | Preparation permitted |
| C2 | Frozen projection/verification reuse analysis, Task2 lease proposal | Own clone; upstream leaf files only after Task0 | Preparation permitted |
| PR MANAGER | Verify bootstrap/import identities; hold integration | Main repository; docs/INTEGRATION.md receipt | Ready after bootstrap |

Heavy job: none reserved by this bootstrap. Maximum one; LEAD rechecks actual load
before admission. No implicit dependency on old-project jobs. No provider spend.
Only the bootstrap owner writes the main checkout until initial review/commit.
