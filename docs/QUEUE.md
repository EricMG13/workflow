# Work queue

Bootstrap committed at df26ea82249fc062a8beb8dba3d51f1caf5fdf23. Four role chats are dispatched; no analytical module is accepted.

| Owner | First bounded work | Files | State |
| --- | --- | --- | --- |
| LEAD | Task0 source/upstream interface and independently expected cases | docs/TOOL-CONTRACT.md, cases/*/manifest.json, matrix/queue | Dispatched: Task0 |
| C1 | Source-tool reuse/known-risk analysis, Task1 lease proposal | Own clone; source/host files only after Task0 | Dispatched: preparation |
| C2 | Frozen projection/verification reuse analysis, Task2 lease proposal | Own clone; upstream leaf files only after Task0 | Dispatched: preparation |
| PR MANAGER | Verify bootstrap/import identities; hold integration | Main repository; docs/INTEGRATION.md receipt | Dispatched: integration readiness |

Heavy job: none reserved by this bootstrap. Maximum one; LEAD rechecks actual load
before admission. No implicit dependency on old-project jobs. No provider spend.
Initial review/commit is complete. PR MANAGER owns the main checkout for integration; bootstrap owns final TEAM registration updates. LEAD owns subsequent planning/queue changes through its clone.
