# PR Manager integration receipt

Reviewed 26 October 2026. This receipt records the initial integration checkout
and bootstrap evidence; it does not admit analytical work or qualify modules.

## Checkout and provenance

- Integration repository: `/Users/ericguei/Documents/Deploy Workflow`
- Branch and starting HEAD: `codex/checkpoint` at
  `df26ea82249fc062a8beb8dba3d51f1caf5fdf23`.
- `git status` was clean before this receipt. No Git remote is configured.
- The selected source snapshot is Claude worktree commit
  `6441553936086c834be885e2f3d7cd7f0959aa5c`.
- `docs/reuse/manifest.json` records 108 source/resource entries and SHA256
  values; `docs/BOOTSTRAP-REVIEW.md` reports that all 108 destination bytes
  matched the pinned source blobs and their manifest hashes. The selected 85
  Python modules imported from this repository in its own `.venv`; offline
  dependency setup also succeeded. These are provenance/setup checks, not
  functional or module-completion evidence.
- The import is selective and has no copied Git history. Provider clients,
  credentials, ledgers, runners, private packs, run artifacts and bulk legacy
  tests/plans were excluded. The known historical failed-render evidence risk,
  incomplete bindings, and missing owners remain open as listed in
  `docs/reuse/README.md`.

## Clean clone integration process

1. Clone or copy this local repository into an independent integration checkout;
   confirm the base commit, branch, clean status and absence/presence of remotes.
   Team clone paths and identities belong in `docs/TEAM.json` under LEAD's
   ownership.
2. Accept a candidate only after LEAD records its specific commit and exclusive
   task/file lease in `docs/QUEUE.md`. Preserve the coordinator's checkout and
   evidence; do not bulk-import old history or merge unadmitted work.
3. Verify the candidate's exact parent/base, changed paths, manifest impact and
   diff. Require a concrete handoff with commands/results, actual supported tool
   invocation and submission/settlement lineage where applicable, independently
   fixed expected results, and an independent Sol/high review for sensitive
   semantics. Check that applicable focused tests and required code-review
   workflows have completed before integration.
4. Integrate only the admitted commit or patch after the evidence is reviewable.
   Record commit identity, files, checks, review evidence and remaining limits
   here or in a linked receipt. Keep this integration branch local unless the
   user later authorizes a remote action.

## Handoff and review requirements

Each handoff must identify the starting commit, exact owned files and behavior,
independent positive and refusal/gap expectations, implementation model/effort
route, candidate commit, and the actual verification evidence. Sensitive
financial/state/provenance expectations need independent Sol/high review.
Before any later integration commit, follow `AGENTS.md`: run confidence-review
after code changes, enumerate and resolve least-confident points, and run
rewrite-tournament in no-argument post-edit mode on changed non-trivial
functions. Do not make module-completion claims from imports, mocks, review files
or direct composers alone.

## Current checks and limits

- Bootstrap evidence was reviewed in `docs/BOOTSTRAP-REVIEW.md`; no heavy checks
  were rerun for this receipt.
- The initial receipt preceded team registration. Bootstrap subsequently
  registered all four chat IDs and independent clone paths in `docs/TEAM.json`
  and dispatched Task0, C1/C2 preparation and this integration receipt.
  `docs/QUEUE.md` records those handoffs; no heavy job was reserved by bootstrap.
- No analytical module is accepted. Actual host tool execution, validated and
  settled output, downstream consumption, rendered sections and case-level
  evidence remain outstanding.
- No external GitHub remote is configured. No PR URL, push, publication,
  credential setup or production activation exists.
- Live/paid/provider testing remains paused. Preserve the one-heavy-job and
  two-disjoint-lane limits; LEAD must admit resource use after checking actual
  processes. No heavy job was started for this review.

## Task0 integration receipt

Integrated LEAD's admitted Task0 commit
`d9411401e4797e04a2e030d3741e937d2d210e32` from
`/Users/ericguei/Documents/Deploy Workflow Sessions/lead` (`codex/lead`) by
local fetch and cherry-pick. The resulting integration commit is
`c4ca5680d557fae5a9327db6d344c48b51728b75` on `codex/checkpoint`.

The six admitted files are `PLAN.md`, `docs/MODULES.csv`, `docs/QUEUE.md`,
`docs/TOOL-CONTRACT.md`, `cases/source/manifest.json`, and
`cases/upstream/manifest.json`. The queue-file conflict was resolved in favor of
LEAD's reviewed Task0 queue, which supersedes the bootstrap queue; bootstrap
`docs/TEAM.json` registration and this integration receipt were preserved.
Reviewed SHA-256 values match the Task0 queue receipt:

- `docs/TOOL-CONTRACT.md`: `fa6d2ef20a4d8cf4b4e9f065f96b29f1552feaa5a12195a53c3db88b489fee88`
- `cases/source/manifest.json`: `dfb9cbaa2db94934c2d322009e7a070d0a39ed67898d92bd9fb2c1fdbf3a03c8`
- `cases/upstream/manifest.json`: `c63e87c92d49ecf7427dbcc39925dfa04844b7c52566e745f22086eb66aacbea`

Checks: candidate file scope was exactly six files; all three reviewed hashes
matched; `git diff --cached --check` passed before committing. LEAD's queue
records its independent Sol/high review, confidence/static validation and
docs/data-only scope. No heavy suite or provider test was run. The integration
checkout remains local, with no external remote; the working tree was clean
after the integration commit. Task0 freezes contracts, cases and leases only;
no analytical module is accepted. C1 Task1-A and C2 Task2-A are not integrated
and require their own later LEAD admission.

## Task3-A contract and slice ledger integration

Integrated LEAD's exact admitted documentation/data commit
`d055a1f4754513613e58521d4d158105816248fa` from its `codex/lead` clone by
local fetch and cherry-pick. The resulting integration commit is
`4e40ce955f8fa1c7df90dd8b2d669b8b48779b3b` on `codex/checkpoint`.

The four admitted files are `PLAN.md`, `docs/QUEUE.md`,
`docs/SLICE-CONTRACT.md`, and `cases/connected/manifest.json`. The independent
Sol/high review hashes match the committed files:

- `docs/SLICE-CONTRACT.md`: `c1970233fd69aa5c7cf5b0a73156a7323eddcc894bd97a4cd558765c023dfb77`
- `cases/connected/manifest.json`: `30b383bd397ecf1c99f3f49d02674605d8ad9c6868da4b4f205124942d731df1`

The queue records the detailed confidence/static review and runtime ledger.
This change freezes the restricted first connected source slice and its
dispatch/evidence requirements; no product code changed and no module is
accepted. `git cherry-pick` completed without conflict, and the four-file
scope matched LEAD's admission. No tests, heavy jobs or live/paid/provider calls
were run for this docs/data-only integration. The prior TEAM registration and
integration receipts remain in place. Product commits are still held pending
their separate final review and LEAD admission.

## C2 Task2-A upstream tool integration

Integrated C2's exact admitted product commit
`a2eb18025f16dac06c9832ba9a8531e974042335` from
`/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-2`
(`codex/upstream-render`, based on
`b90c51c382b0544be5dac194eb91124470c22943`) by local fetch and cherry-pick.
The resulting integration commit is
`3ebaf4737e6f8c581a53aca09d5aac36bc8a5a4e` on `codex/checkpoint`.

The three admitted files are `src/deploy_workflow/tools/upstream.py`,
`tests/test_upstream_tools.py`, and `docs/handoffs/upstream-tools.md`; no
source/host/shared/export/imported/render file was changed. The final handoff
hashes match the integrated product and tests:

- `src/deploy_workflow/tools/upstream.py`:
  `4854ec219bcd646e72b1ec367573df898bafad4d48a1f6e18285c90043b0eebe`
- `tests/test_upstream_tools.py`:
  `40887e513da2bf079b3032bc661d980362da4128c205f653b3bd3344a6474425`

Integration confidence review: candidate status was clean and the exact commit
scope matched LEAD's admission. Its only product import is from existing
`deploy_vii` primitives; Task0 specifies direct leaf import from
`deploy_workflow.tools.upstream`, so no package export edit is needed or
included. The commit cherry-picked without conflict. Final SHA checks passed.
The handoff records the independent Sol/high sensitive review, ten-point
confidence review, no-argument rewrite tournament, and final focused run of 53
tests passed (PID 17950, exit 0). Those results belong to C2's admitted run;
no combined source/upstream suite was run here. No live, paid, provider,
publication or production activity occurred. This adapter is component evidence
only and does not establish an accepted analytical owner or module.

## C1 Task1-A source tool integration

Integrated C1's exact admitted commit
`8adbd4104918ef7ccaeee1e8d234c0e2d7ae71f9` from
`/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1`
(`codex/source-tools`, based on
`46fdf57ca9c938f1139a61c071dd713740eb06a3`) by local fetch and cherry-pick.
The resulting integration commit is
`1668904ffb211fd8a31864e6e1f8345e03a27ada` on `codex/checkpoint`.

The six admitted files are `src/deploy_workflow/host.py`,
`src/deploy_workflow/tools/source.py`, `src/deploy_workflow/tools/__init__.py`,
`tests/test_source_tools.py`, `src/deploy_vii/live/tools.py`, and
`docs/handoffs/source-tools.md`. The imported-tool change is limited to
`PackTools.read_pages` and `PackTools.search_pack`; the diff contains no other
shared/export/imported/render edits. Final bundle hashes were verified against
C1's handoff, including patched `live/tools.py` SHA256
`d4071e59bde16648ab9175e529cce47a5b5e0f456da3a4692e831d0b346b1e48`.
The source commit and original `files[].sha256` baseline remain unchanged in
the reuse manifest. Its new top-level `post_import_patches` entry records the
patched destination hash, original imported hash, C1 project commit and review
handoff; `hash_interpretation` distinguishes the two.

Integration confidence review: clean candidate and exact six-file admission
were confirmed; the cherry-pick completed without conflict; all five final
bundle hashes matched; the integrated source patch matched its recorded SHA;
manifest JSON parsed; removing the two new provenance keys yields the exact
prior manifest, confirming no baseline fields changed. The handoff records the
independent Sol/high sensitive review, closed confidence review, required
no-argument rewrite tournament, and C1-FINAL-1 results: 58 focused tests,
narrow mypy, and Ruff passed. Those checks were performed in C1's admitted
clone; no combined source/upstream suite was run here. Task1-A is adapter
component evidence only; analytical settlement, downstream consumption and
rendering remain unverified. No live/paid/provider calls or publishing occurred.
