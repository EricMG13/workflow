# CP-3 Stage 2 review (mx-precise)

**CP-3 Stage 2 review (8704e1f on adeb8c9): REQUEST CHANGES.** Two Medium findings, one under each verdict; the rest is Low or Info.

I re-ran the gates in `s2-cp3`. The 5-file pytest set gave 393 passed. `ruff check`, `ruff format --check` and `mypy --strict` (with `MYPYPATH=src:tests`) on the 6 changed files all exited 0.

Scratch directory: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3-s2-review/`
- `mutants.py` exits 1: 3 of my 8 mutants are killed and 5 survive.
- `p_create_refusals.py` exits 0.

**Spec verdict: REQUEST CHANGES**

- **M1 (Medium): the lease acceptance store tests are missing.**
  - Where: `tests/test_owner_cp3.py:11-12` (the docstring says "Not written here") and `report.md:64`.
  - Timing: the §7 amendment (72cc6de, 19:40) is later than 8704e1f (19:35). Even so, the lease Acceptance list (`docs/CP3-OWNER-LEASE.md:204-229`) required these tests under the old §7 as well.
  - Required now (all on R3, none needs R6):
    - The A4 tamper refusals (a), (b) and (c): the `refusals.tamper_refusals` entries, run on clones of the closed positive run.
    - The blocked-CP-1A variant: `positive.CP-3.blocked_cp1a_variant`, with the receipt and the re-derived head.
    - `cp3-stale-snapshot`, which is a CP-3 positive tool-use refusal, not a CP-6 one.
    - The CONTEXT block: `CP-3.context_block_checks`, including the check that the four optional ids are absent from the body (lease :164-167).
    - Other acceptance items with no test: the upstream equalities (CP-0 R3, CP-1A deltas and `catalogue_size`, CP-2 equal to S1), the CP-2 read-body register counts (M4, lease :155-158), the `inherited_limitations` order, the `CP-3.render` blocks and rails, and the upstream-chain `read_pages market page:1` counts.
  - Fast, so they must run now in `test_connect_cp3` (amended §7: "a fast one is run, not deferred"): the create-time refusals. These are the spec override, CP-4C, CP-3D, CP-2D or CP-3C in a CP-3 run, a plan with CP-5 but no CP-5 spec, and the aliases.
    - On this branch the pinned R3 pack already refuses for the CP-MODEL ordering reason. These tests therefore need a control selection without CP-MODEL that `create` accepts, so a refusal for the wrong reason cannot pass. Alternatively, land them after `claude/s2-g1x-order`.
  - Blocked on the CP-6 freeze: only the D3 test (the CP-6 head cells, R6; lease :179-180). The report should mark it with exactly those words.

- **M2 (Medium): CP-3B now passes `create`, against lease :138-139.**
  - Lease :138-139 says an alias in `requested_modules` refuses at `create` and writes nothing. With CP-3 registered, `canonical("CP-3B")` gives CP-3, and a CP-MODEL-free CP-3B selection is created (`p_create_refusals.py`: "alias CP-3B … -> created").
  - Before this change it refused, because CP-3 had no spec. The guard at `owner_workflow.py:668-684` has no alias check (that guard predates this change).
  - The lease contradicts itself: Q11 (:276-278) recommends canonicalising instead, and asserting that the receipts and `MODULES.csv` count no completion for the alias.
  - This needs a LEAD ruling, and then the matching test. It should not be closed silently.

- **Registrations: correct.**
  - All rows are appended at the end. `OwnerSpec["CP-3"]` equals lease :80-83 and sits after CP-MODEL. `_ENTRY_VALIDATORS` is present (protocol §2; it is tested at `test_connect_cp3.py:121`).
  - There is no `_CORES`, `_VIEWS` or `_PRECHECKS` row and no reader, which agrees with lease :147 and :264. Nothing for CP-6 is touched.

- **Library boundary: clean.** The diff touches nothing under `cases/`, `methodology.json`, TOOL-CONTRACT or `src/deploy_vii`.

- **Backlog rows: agreed.**
  - Blank quotes: all 54 variants fail closed, and the wording is the engine's. Info is the right level; the wording item goes to LEAD.
  - Hostile-text stand-in (`test_connect_cp3.py:251-272`): admissible until the shared set lands (brief §6, ruling Q5). Swap it for the shared set then.

- **Diff size: Info.** The diff is 935 changed lines, 927 of them added, most of it tests. The brief states no ceiling. Global §3's 800-line cap applies per PR.

**Quality verdict: PASS with Lows**

- **`probe` (`owners/cp3.py:109-115`): sound.**
  - It is the same shape as CP-2's: `probe_one_step` with `_validate_step`, and `_candidate` built the same way as `submit_cp3_step` (`cp3_relative_value.py:1216-1217`).
  - The seam is positional (`owner_workflow.py:1818`).
  - A forged head, a mutated payload, zero or doubled steps, a no-op probe and a validator that skips validation are all refused or killed. I found no way for a forged result to pass.
- **L1 (Low): the attempt number is never checked by the fast tests.** The mutant `cp3_module(report, attempt.inputs, 0)` survives (`mutants.py`), because every fixture settles attempt 0. In a real run it fails closed on attempt 1. Fix: add a fixture that settles attempt 1.
- **R3 driver (`tests/cp3_cp6_runs.py`).**
  - It exports `cp3_closed` only.
  - The composition matches `submissions.json`: the positive base for both cases, `sources` plus `sources_append`, the R3 consumers, `change: none`, and the R3 readiness document.
  - `{{FIG:}}` is bound through `s1.figure_fact` (exactly one match), and an unknown name stays unbound and fails closed.
  - The order (CP-3, then `finish`) agrees with Round 2's rule that publication stays terminal.
  - `drive_cp1(context=)` (`s1a_runs.py:253-260`) is backward compatible: existing callers pass no `context`, so behaviour is unchanged.
- **L2 (Low): four driver mutants survive the fast gate**, because the driver never runs in Stage 2. They are: `drive_cp1` ignoring `context=`, `cp1_bindings` taking the first match instead of exactly one, the market `extractor` dropped, and `drive_cp3` skipping the reads. Only the Stage 5 run can kill them; record that in the deferred list.

No stub, fake value or undocumented catch-all is in `src`.

Not verified: the store suite, `cp3_closed` and the deferred runs (they need a real CP-1 promotion, and R3 `create` refuses on this branch until `s2-g1x-order` lands); the Round 2 ordering change itself; the CP-3B receipt and `MODULES.csv` counting behaviour; and GitNexus, jscpd, complexipy and bandit, none of which I ran.
