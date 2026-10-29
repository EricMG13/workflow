# CP-OS (Report navigation) owner lease — FROZEN by LEAD 2026-10-28 (draft rev 3), owner-preparation task `cpos-owner`

Amended by Modules 2026-10-29 (Stage 2 close release W1, merge of `lead/0d-d` 0daac2c onto `lead/cp6-freeze` 562a3bc; `work/build/stage2/release-plan.md`): pin hashes only, re-pinned against the merged tip: `src/deploy_vii/report_view.py` 51a6853e… → 5c71a311… (lane drift from the CP-2H and CP-4C connections). No oracle value moves. Own files, old → new sha256: `manifest.json` f775812f180e2c18105381579ca363915cb49b59a2cb21d8af540758b9cd44f7 → 560af9d91df597adbdb79c804cdd47cbc744d99b7cd4cc7b1590439369cf041f; `submissions.json` unchanged; `expected.json` unchanged; `builder/build.py` d5e33ab6fc010ca9a84f6ef65cff083b9dcea912276ce83682159ed2af54e22e → a21cd26cb8c856358a0fb1ff66cfe2f6ac4bef33cf1b9fd8bd69787dacd87907.

Amended by LEAD 2026-10-28 (CP-6 freeze re-pin, `work/lead/cp6-freeze/report.md`): `src/deploy_vii/methodology.json` registers `T6-FINAL` under CP-6 `table_ids` (ruling Q7), 1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6 → 0932d9fbcd9272d62bcb7681e1dd16d9bc944319c64716b41dc79715699796e8; this module's builder re-pins it and its manifest records the new hash. Only pin hashes move: no other leaf of this module's oracle changes. Own files, old → new sha256: `manifest.json` 722f7d2714a9509b035336b8fd4a8ea6ad0c2f31de5dee770e5eaed2498e23e9 → f775812f180e2c18105381579ca363915cb49b59a2cb21d8af540758b9cd44f7; `submissions.json` unchanged; `expected.json` unchanged; `builder/build.py` 851f81935e641b4fc10894d5e6dd54d3edf6f6a6b74ff55395f7ab2192bbc234 → d5e33ab6fc010ca9a84f6ef65cff083b9dcea912276ce83682159ed2af54e22e.

Pin consumers: none (no other builder pins or reads this module's files). Every builder except cp2d and cp4 also pins `src/deploy_vii/methodology.json`, which this batch does not change. (Stage 1 release batch, LEAD 2026-10-28; none of this module's files changed.)

Re-pinned by LEAD 2026-10-28 in the serialised `methodology.json` change (branch `lead/methodology-serialised`; `work/lead/methodology-serialised/review.md` COMMIT): `methodology.json` 348fbc4b… → 1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6 (CP-L10 required + CP-1 and TL10.5; CP-1C T1C.1-T1C.8; CP-1D drops T1E.*; CP-2A drops T5.*); two scratch rebuilds identical. builder 6b4b0628… → 851f81935e641b4fc10894d5e6dd54d3edf6f6a6b74ff55395f7ab2192bbc234; manifest 0ca64d19… → 722f7d2714a9509b035336b8fd4a8ea6ad0c2f31de5dee770e5eaed2498e23e9; expected unchanged; submissions unchanged. Pins elsewhere in this file are superseded where they differ.

Frozen after `review-precise-3.md` (FREEZE) with its L-1, L-2, L-3 applied as LEAD wording amendments (lease only; no oracle change); Info-1 (`app.js destOf` → `app.js render, :793` in build.py:120 and expected `rules.shell_skip_link`) deferred to the build, as it changes the expected hash. Pins: manifest 68c15d6ea865e3b66c6834283b479d2eb59755fccdb7fa94bf12b01994ba7c65, submissions cfbcdd4d5e294e81fb3bf52f9109f2469496ffb392e6e7884d267151a2fa636e, expected e087ed49ead974f5fab1137d3c91c139eee313d66fab71900715381e6b3263d3, builder 50a4477424f15de994662faf9518b8b05d918070a8de8a3a84ced4174e00757e.

Re-pinned by LEAD 2026-10-28 to 0d (41a8fdb) and 0d(c) (b4ae187); Info-1 applied (`work/lead/cpos-owner-preparation/repin-0d.md`, scoped check `repin-0d-review.md`, fix `repin-0d-fix1.md`). Pins now: manifest 0ca64d19987359020bfd7ea5bcadca1286c005f00f6e9b89d155b5b3ce7d7044, submissions cfbcdd4d5e294e81fb3bf52f9109f2469496ffb392e6e7884d267151a2fa636e, expected c0f93ab07e33c933fc5964e25cbac541addc35d830ab77ea3685003c665bfd0b, builder 6b4b062851a21e877cbdde28838a3c699fe09132c8efec87ba6cc32574a4f8c1; `src/deploy_vii/contracts.py` ee1b27f9… newly pinned (credit_snapshot preset). Note: CP-3/4/5/6 (preset closure, not requested) read "Not run" (footer rows, unrun page, footer grouped by word: `tally.footer_groups`, 16 + 4); `#workbench` resolves via routeOf and is inside the dead-link refusal, so the `shell_skip_link` exception and its rendering-closure condition at :63, :68, :76, :112 and A1 (:85, footer "· 20") are superseded by `expected.rules`. The methodology pin remains a known re-pin (the serialised methodology change).

Pre-code. Oracle: `cases/cpos-owner/` (builder `python3 -I cases/cpos-owner/builder/build.py`). Decision D6 (`docs/OWNER-WORKFLOW-LEASE.md:36`): "Render-time navigation proof over a real selected run, with the rendered navigation page hash bound to that run's verified receipt hash. No journal head." This lease designs to those two sentences and nothing wider.

## Why

CP-OS is a deterministic exception (AGENTS.md; `methodology.json`: no required or optional upstream, no table ids; purpose "Read-only navigation and routing across analytical artifacts; no new analytical handoff."). It is exempt from the execution chain (`execution.py:259` skips the CP-0 command check; `registry.py:25` keeps it out of CP-5's fan-in) and G1 has no spec for it. The navigation already exists: `report_view.navigator` (`report_view.py:840`) feeds `report.nav` (`render.py:184`) and `app.js` `renderNavigation` draws it. What is missing is the proof that the navigation a page shows is the navigation of a real, verified run, and that every link lands on a page that exists and says what is true.

## Prerequisites

- G1 integrated (`verify_owner_run_receipt`, `OwnerRunReceipt`); S1a integrated (closed S1a runs, `tests/s1a_runs.py` `s1a_closed`), because the receipts under test are S1a receipts.
- Independent of G2. No change to `src/deploy_vii`, `owner_workflow.py`, `host.py`, `app.js`.

## G1 change under `docs/G1X-OWNER-CORE-PROTOCOL.md`: none

CP-OS is not an owner-run step. It has no `OwnerSpec`, `StepSpec`, `_CORES` entry, probe, view, precheck, `STEP_IDS`, `SCHEMAS` or `submit`, so none of the §2 attributes applies, and §1 (live-contract vs owner-only) does not classify it. G1 already refuses it as a requested module (no spec; S1a: "any module without a spec refuse at create"), `registry.plan` never schedules it (no edges), and `OwnerRunReceipt` needs no field for it. A test pins the first fact (A7: `WorkflowError("not_permitted")` from `_check_specs`, `owner_workflow.py:319-320`, before `Execution.create`). No D12 registration (`table_ids` stays `[]`), no `docs/reuse/manifest.json` row beyond the two new files.

## Files

- New `src/deploy_workflow/owners/cpos.py` (about 200 lines). It lives beside the cores for D12 location only; it is not an owner core.
- New `tests/test_owner_cpos.py`.
- Reads, never edits: `deploy_workflow.owner_workflow` (`OwnerRunReceipt`, `verify_owner_run_receipt`), `deploy_vii.execution.Execution.view/read/head_module`, `deploy_vii.render.render`, `deploy_vii.report_view.navigator`, `deploy_vii.registry`.

## Public API (positional, no journal, no files written)

```
class NavigationRow(Contract):      # NavRow fields plus the link proof
    module_id, title, aliases, number, in_pathway, color, glyph, word     # = report_view.NavRow
    href: str                        # "#" + module_id
    group: Literal["numbered", "footer"]
    page_title: str                  # "<module_id> · <title>"
    has_output: bool                 # the view module carries facts, claims or tables
    empty_state: Literal["not_part_of_pathway", "no_validated_output"] | None
    limitations_panel: bool          # the view module carries limitations
class NavigationDestination(Contract): key, label, href, page_title
class NavigationProof(Contract):
    schema_version: Literal["cpos-navigation/1"]
    run: Run; pack_sha256: Hash; snapshot_sha256: Hash
    receipt_content_sha256: Hash     # OwnerRunReceipt.content_hash() of the verified receipt
    page_sha256: Hash                # sha256 of the rendered page bytes
    heads: tuple[SettledHead, ...]   # copied from the verified receipt
    rows: tuple[NavigationRow, ...]; destinations: tuple[NavigationDestination, ...]
    external_links: tuple[str, ...]  # ("calculation.json",) iff the page links it AND receipt.model.files holds it
def navigation(store, receipt, publication_directory) -> tuple[bytes, NavigationProof]
def verify_navigation(store, receipt, publication_directory, page, proof) -> None
```

`publication_directory` is passed to `verify_owner_run_receipt` unchanged (S1a publishes CP-MODEL, so a model-bearing receipt needs it).

## Behaviour

`navigation`:
1. Call `verify_owner_run_receipt(store, receipt, publication_directory=...)` first. A tampered or stale receipt raises `WorkflowError` (`identity_mismatch` or `stale_binding`) and nothing else runs. CP-OS does not catch, relabel or re-implement it. This is its only authentication; it replays no submission.
2. `view = store.view()` (accepted mode). Require `view.run == receipt.run` and each receipt head's view-module status equal to the head's; a module without a head shows its idle status (`registry.idle_statuses`). Read-only: store and receipt bytes unchanged. (The earlier `artifact_sha256` equality check is dropped: `view()` computes that field from the head, `execution.py:917`, so it cannot fail.)
3. `html = render(view)`; `page = html.encode()`. After the render, re-read the store: `store.read().content_hash()` must equal `receipt.snapshot_sha256` (as `owner_workflow.py:1189`); a difference raises `ValueError` `cpos_binding`. Parse the `report-data` JSON: the page embeds `<script id="report-data" type="application/json">DATA</script>` (`shell.html`); DATA is `json.dumps(ensure_ascii=True, separators=(",", ":"))` with every `<` replaced by `\u003c` (`render.py:191-193`), so the first `</script>` after the opening tag ends it and `json.loads` of the text between is exact. A missing tag, missing closing tag or invalid JSON raises `ValueError` `cpos_target_missing` (never a bare `JSONDecodeError` or `AttributeError`). Blocks are `report.blocks[]`, modules `modules[]`, rows `nav[]`.
4. Rows come from `navigator(view)` plus per-row link facts read from the real view module: `has_output` is facts, claims or tables non-empty, `limitations_panel` is limitations non-empty (never from status alone). Destinations are the six fixed `DEST` entries. `external_links` is `("calculation.json",)` iff the page links it and `receipt.model.files` holds that key. "Linked" is one thing: the page's CP-MODEL fact `model-destination` / `calculation-json` / `path` is present with the shell's gates (`artifact_sha256`, path matching `^[A-Za-z0-9._-]+$`, `model-provenance` cp1-head and pack hashes; `app.js:600-603`), and its path is a key of `receipt.model.files`. A page link absent from `files` is `cpos_target_missing`. Limitation: the href is relative (`app.js:603`), so it opens only from a directory holding the receipt's model files; CP-OS proves the link is drawn from the page fact and listed in the receipt, not that the file sits beside the page.
5. Return `(page, NavigationProof(..., receipt_content_sha256=receipt.content_hash(), page_sha256=sha256(page)))`.

`verify_navigation` repeats steps 1-4 on the same store and receipt, then checks in this order, each a `ValueError` whose message starts with the prefix:
- `cpos_binding`: `proof.receipt_content_sha256 != receipt.content_hash()`, `proof.snapshot_sha256 != receipt.snapshot_sha256`, `proof.run`/`pack_sha256`/`heads` differ from the receipt, `sha256(page) != proof.page_sha256`, or the store changed during the render (step 3).
- `cpos_target_missing`: `report-data` cannot be extracted (step 3); a `#` href on the page has no page (except the recorded `shell_skip_link` `#workbench`, below) (every hash href: navigator and footer rows, rail destinations, Front Page block links `blocks[].full_analysis_route` -> `app.js:428`, Analysis coverage table `app.js:630`, CP-MODEL links `app.js:604`, `:613`; resolves when the route is a module id or alias in `report-data` `modules` or one of `front`, `analysis`, `FIT`, `evidence`, `limitations`); or `calculation.json` is linked without being in `receipt.model.files`.
- `cpos_rows`: the page's `nav` differs from the re-derived rows, or `proof.rows`/`destinations` differ from the re-derived ones.
- `cpos_page`: `page != render(view)` byte for byte.
- Then, last: `proof == derived_proof` in full (every field, including `external_links` and any field added later). Any remaining difference raises `cpos_proof` (its own prefix, last in the order). This closes H1: a proof forged in a field the four checks above do not name cannot pass.

Recorded exception `shell_skip_link`: every page carries `<a class="skip" href="#workbench">Skip to analysis</a>` (`shell.html:5`); `#workbench` does not resolve ("Unknown destination", `app.js:793`). It is a product defect outside CP-OS, its own task (shell/app.js, test-first), text-checked in the oracle and excluded from the dead-link refusal. The CP-OS rendering criterion ("visible working links") closes only after that defect is fixed and the native DOM step passes.

Never-a-dead-link rule (all other hrefs): a module row always links `#<module_id>`; the shell resolves it through `report.modules` (every registry module except rejected attempts, which have no row). An unrun, blocked or not-in-pathway module therefore links to its status page, which carries no findings: `has_output` false and the empty-state message (`app.js` `renderModule`: "No validated output is available…" or "…is not part of the … Pathway, so it is not run."), the status word in the chip, and for a blocked head the limitations panel. No row ever claims output the view lacks. A rejected attempt has no row. The only non-hash link, `calculation.json`, renders only from the page fact above and is checked against the receipt. The Front Page "Full analysis →" / "Open in Model →" links (only a populated block carries a route, `report_view.py:1634`, `:1712`) point at `#<producers[0]>`: all land on an existing module page; `relative-value`, `committee-challenge` and `what-changed` land on a CP-3, CP-6, CP-8 "not part of this Pathway" page, so the label overstates what is behind it (LEAD to note; no change proposed).

Deterministic: same store and receipt give the same page and proof bytes; the proof is a `Contract`, so `model_dump_json` bytes are canonical.

## Tool use and consumption

CP-OS has no analyst, no pack tools, no `read_inputs`, no ticket (D2 does not apply). Completion framing (AGENTS.md:16, `docs/MODULES.csv:27`): CP-OS is a deterministic exception; its criterion is "Actual selected run/sections -> direct deterministic navigation -> visible working links". `tool_execution` and `downstream_consumption` are marked "n/a: deterministic exception"; `validated_output` is the verified receipt plus the proof; `rendering` closes only after the native DOM step below and the `shell_skip_link` defect fix (:66). The real work is the actual call of `verify_owner_run_receipt` on a real receipt and the actual render. The `MODULES.csv` CP-OS row update (text only, by LEAD in the closing commit, not here) will read: lane C2, tool_execution "n/a: deterministic exception", validated_output "verified-receipt navigation proof (cpos-navigation/1)", downstream_consumption "n/a: deterministic exception", rendering "closed by native DOM click acceptance and the shell_skip_link defect fix", case_evidence the four cases of `cases/cpos-owner`. The test asserts the call happened (the tampered-receipt cases refuse before any page exists; a spy on the verifier is not needed because the refusal codes are the verifier's own). Consumption (D3) is not a module-to-module edge: the consumer of the proof is the shell, which draws `report.nav`. The proof asserts the page's `nav` equals the rows and every href resolves. That the links work on screen is native DOM acceptance, run with the page opened from a directory holding the receipt's model files (so the `calculation.json` link opens), and it closes rendering, the same split as G2 Q4 and the existing render tests ("Component data assertions supplement, but never replace, native DOM proof").

## Rendered sections and table ids

No block (D7): the assigned rendered section is the navigator aside (`#module-list`, `#nav-foot`, tally) and rail (`#rail-dests`). Table ids: none, so the D8 collision check is vacuous (`methodology.json` CP-OS `table_ids: []`; nothing registered).

## Acceptance (values from `cases/cpos-owner/expected.json` only)

Receipts: closed S1a positive and gap runs (A1, A2) and the A3b and A3c clones of the positive run; fixtures from `tests/s1a_runs.py`.
- A1 `s1a_positive`: 25 rows; numbered 1-5 = CP-0, CP-1, CP-1A, CP-2, CP-MODEL, all `lim`/"With limitations" with their family colour (CP-MODEL neutral `#9AA0B4`); 20 footer rows `na`/"Not in this Pathway" with `number` null, including CP-OS itself; tally "Analysis · 5", chips All/5 lim/0 pass, footer "Not in this Pathway · 20", no unrun line; each numbered row `has_output` true and `limitations_panel` true (the test asserts both against the real heads' module views; the oracle infers them from status, and any disagreement returns to LEAD for a ruling, never a silent oracle edit); footer rows `has_output` false, `empty_state` "not_part_of_pathway", no limitations panel; six destinations with the expected titles and "Limitations · with limitations"; `calculation.json` linked. Search probes equal the oracle. `block_links` and `hash_links` (per case in `expected.json`): every `#` href the page draws is in the oracle superset and every one except `hash_links.shell_skip_link` resolves (the oracle cannot say which blocks are populated without a real store; see the oracle rule `hash_links_not_derivable_without_a_real_store`).
- A2 `s1a_gap`: the same as A1 (content gaps change no row); `run.run_id` is the gap run.
- A3 `s1a_blocked_cp1a`: CP-1A `blocked`/"Blocked" (`has_output` false, `empty_state` "no_validated_output", limitations panel true); chips All/4 lim/0 pass/1 blocked.
- A4 `s1a_refused_cp1a`: CP-1A and CP-2 `unrun`/"Not run" (`has_output` false, `empty_state` "no_validated_output", no limitations panel); unrun line "Not run · 2"; chips All/3 lim/0 pass; `calculation.json` linked.
- A5 verifier refusals (`submissions.json` `verifier_refusals`), each raising the verifier's own error before any page is made: `seal_edit` and `head_status_forged` give `identity_mismatch` (the second forges the seal file too, so only the head check can refuse), `foreign_store` gives `stale_binding`.
- A6 CP-OS refusals (`cpos_refusals`), in the stated order, each by its prefix: `proof_of_other_receipt` (many fields differ on purpose), `receipt_hash_only` (only `proof.receipt_content_sha256`), `unverifiable_page_hash` (`cpos_binding`); `dangling_target` (`cpos_target_missing`); `forged_row`, `forged_proof_row` (blocked case, proof CP-1A `has_output: true`), `forged_proof_destination` (Model `#CP-1` -> `#CP-MODEL`) (`cpos_rows`); `forged_external_link` (`("evil.json",)`, replay with `()`) (`cpos_proof`); `page_bytes_edited` (`cpos_page`). Page forgeries (`dangling_target`, `forged_row`, `page_bytes_edited`) rehash the page and rewrite the proof's `page_sha256` so only the named check can refuse. Proof forgeries leave the page unmodified and genuine, and each differs from a valid input in exactly one thing, so a test replays it as a literal. The named check is the first to refuse; with the targeted comparison removed, the recipe refuses with a different prefix or, for `forged_external_link`, passes. The final `proof == derived_proof` check (`cpos_proof`) is the only check that refuses `forged_external_link`.
- A7 `requested_modules` containing CP-OS refuses at G1 `create` with `WorkflowError("not_permitted")` (no spec; `_check_specs`, `owner_workflow.py:319-320`, before `Execution.create`) and writes nothing.
- A8 read-only: relative paths and bytes of the store, publication directory and receipt are identical before and after `navigation` and after a refused `verify_navigation`. Determinism: a subprocess with another `PYTHONHASHSEED` yields identical page and proof bytes.
- Product-vs-oracle probe already run (see report): `navigator` rows for all four cases equal `expected.json`.

Gates: `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict` on both files.

## Deferred commands (build-first; LEAD final phase, heavy-job lock)

```
PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest tests/test_owner_cpos.py -q
python3 -I cases/cpos-owner/builder/build.py && git diff --exit-code -- cases/cpos-owner
```
The oracle re-run needs the pins unchanged: `report_view.py` and `app.js` are pinned (text-checked), so a D12 registration in `report_view.py` moves that pin in the same commit.

## Open questions for LEAD

1. **Receipts with blocked heads or refusals.** G2 refuses them (G2 rev 1 M1) until an oracle covers them. Recommend CP-OS accepts them: navigation shows honest status, and A3/A4 are the oracle. The blocked case's CP-2 `restricted` and the refused case's CP-2 `unrun` are derived (restricted edge in `execution.current_inputs`; S1a Q3(b) stop rule), not pinned by the S1 oracle; confirm when the A3b/A3c receipts exist.
2. **Page identity.** Recommend the "navigation page" is `render(view)` bytes with no banner (one function, no file). When G2 delivers `report.html`, its verifier may compare the banner-stripped delivery to this page hash; do not make CP-OS depend on G2.
3. **Status-page links.** Recommend keeping the shell's behaviour (an unrun or not-in-pathway row links to an existing status page that promises nothing) over an `app.js` change to render such rows as plain text. Alternative needs a C2 lease.
4. **Portfolio Fit destination** is a static "Portfolio Fit · not run" page (`app.js`, `FIT` route), true while CP-3B/CP-6A portfolio-fit blocks are unimplemented. Recommend recording it as a limitation, not refusing runs with CP-3/CP-6 heads; revisit with CP-3B/CP-6A.
5. **CP-OS's own row** is a footer row "Not in this Pathway" (it is in the registry, never requested). Recommend keeping it: it is the registry's truth and CP-OS has no head.
6. **Native DOM acceptance** of working links (open the page from a directory holding the receipt's model files; click each row, destination, drawn Front Page block link and the `calculation.json` link; `h1` and chip per `expected.json`) is a separate LEAD-run step, as for every render lease; with the `shell_skip_link` defect fix (:66) it closes CP-OS rendering.
7. **Pins.** The oracle pins `report_view.py`, `app.js`, `render.py`, `registry.py` for text checks. Recommend accepting the churn (the builder fails loudly when navigation semantics move).

Not verified: the revision-2 recipes and the full-equality check are text only (no code, no test); no pytest; no real receipt, store or page was produced (the `NavigationProof` API is unwritten); `verify_owner_run_receipt` refusal codes for the three verifier recipes are read from code (`owner_workflow.py:1101-1166`), not executed; S1a/G1 integration state is taken from lease texts; CP-2 status in the blocked case and CP-2 absence in the refused case are derived, not observed.
