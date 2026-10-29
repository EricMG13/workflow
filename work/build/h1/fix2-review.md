## H1 fix round 2 re-review (mx-adversary, by finding id): target 38f0f46, diff `1371d49..38f0f46`

**Verdict: APPROVE.** F1 (item 2), item 5, I1 and I2 all hold, and the F2 and fix-1 regression probes all exit 0. There are no High or Medium findings, so nothing goes to the owner from this round. Three new Low findings are test gaps only; the code is correct and fails closed in each case. They ride with the end batch.

I edited nothing in the target. It is still clean at 38f0f46; the ignored `__pycache__` folders there predate this review. Every probe and mutant ran on full copies with `PYTHONDONTWRITEBYTECODE=1`. Probe directory: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/h1-fix2-review/` (called `<P>/` below). Each probe's output is saved beside it as `.out`.

### Findings by id

**F1 (item 2): holds.** Evidence: `<P>/p10_f1_forgery.py` exit 0, `<P>/p12_passthrough.py` exit 0, `<P>/p14_cores_registry.py` exit 0.
- **Owner-only forgeries are refused.** Every forged head is a self-consistent journal: written through the public `Execution` API with a bypass validator, and the replay reproduces it. So only the new rule can refuse it.
  - The genuine CP-3D head passes, and only passes are cached in the memo.
  - Each of these is refused, with nothing cached:
    - a forged digest;
    - the id `market-implied`;
    - the ids `research-submission`, `market_implied-submission`, `Market-implied-submission`, `x-market-implied-submission`, `market-implied-submission-submission` and `earnings-quality-submission`;
    - two tails, in either order;
    - no tail.
  - A duplicated tail cannot be built at all: `Module` refuses a duplicate input identity.
- **Every case without a schema source raises `SourceError not_permitted` with 0 payload reads and an empty memo.** The cases:
  - CP-3D claiming `research` or `business_context`;
  - the core unregistered after settlement;
  - `STEP_IDS` as a list, a str, two steps, empty or missing;
  - `SCHEMAS` as a list, an instance, `dict`, or missing the step;
  - CP-1A claiming `credit_synthesis` or `market_implied`;
  - CP-1B `earnings_delta`, with or without a registered core (its step chain succeeds, so it takes the live branch);
  - an unknown module.
- **Schema before the tails.** With no schema source and a failing tail (a CP-1B-shaped two-input tail, no tail, or a non-`-submission` tail), the answer is still `not_permitted`.
- **Live path unchanged.** CP-1A `business_context` still resolves to `BusinessContextSubmission` and still passes. `p06_live_path_equivalence.py` also exits 0.
- **Pass-through, end to end.** p12 has a real CP-DR `SourceSession` bind a settled owner-only CP-3D head. The probe patches the registry to add the CP-DR to CP-3D edge, because no real cheap edge exists.
  - With the core: the session opens.
  - Core unregistered: both `from_execution` and a live `invoke` refuse `not_permitted` through `except SourceError: raise` (host.py:934-935), and the memo stays empty.
  - Forged tail digest: the session refuses `identity_mismatch`.
  - G1's `_activate` (owner_workflow.py:747-756) lets the SourceError propagate, so there is no fall-back to a session-less mode.
- **`_CORES` cannot be changed by a caller.** An AST scan of `src/` finds only the binding at owner_workflow.py:105. `_CORES` is empty at import. `OwnerWorkflow.create` with a caller spec for an owner-only module that has no core is refused `not_permitted`, and `_CORES` keeps the same object and contents.
- **Info (shapes only registered core code could have; not caller input):**
  - A `STEP_IDS` that is a tuple subclass, or an object equal to anything, passes the ruled `STEP_IDS == (step_id,)`. `_owner_sequence` uses `type(...) is tuple` instead. Round 10's G1-side guard (`_check_steps` requires `type(core.STEP_IDS) is tuple`) closes this at create time.
  - An ABC-registered virtual `Contract` is refused (pydantic disables virtual subclasses in `issubclass`).
  - `Contract` itself as the schema raises a ValidationError, which maps to `identity_mismatch`: it fails closed.

**Item 5: holds.** Evidence: `<P>/p11_cpdr_held_session.py` exit 0, `<P>/p13_scope_rows.py` exit 0.
- **Real CP-DR session.** The pack holds a `missing` source and an `unreadable` source carrying marker spans.
  - The scope is every held source, in pack order.
  - `read_pages` and scoped `search_pack` on both answer `unavailable`, with no body.
  - An unscoped search never returns the marker bytes and never surfaces either source.
  - An unknown source answers `not_permitted`.
  - The run seals `accepted`.
- **Rows compared, base against target, over 74,110 packs** (ready, missing and unreadable sources):
  - the row keys and `_SOURCE_STEPS` are unchanged;
  - CP-1D and CP-3D give identical scopes;
  - CP-DR is every held source (it was ready-only);
  - there is no CP-3 or other live-contract owner row.
- CP-3's registry scope does filter to ready sources (context.py:118-122), so the new comment is accurate. `_ready_pack` has no remaining references.

**I1 and I2: hold.** Evidence: `<P>/p_i1_i2_prose.py` exit 0.
- The item-4 prose appears word for word in `work/build/h1/q6-source.md`, and the old "keeps today's acceptance" sentence is gone.
- The round gives no word-for-word docstring text for I1. The docstring states the boundary as item 3 and protocol §5 do: provenance only, with composition checked at the receipt verifier, where `_verify_settlements` runs `_PROBES[m]`.

**F2 and fix-1 regression: holds.** p02_producer_forgery 0, p01_scope 0, p03_memo 0, run from `<S>/h1-review/`. LEAD's `p_f1_schema_source.py` also exits 0, but it tests its own copy of the rule, not host.py, so it does not count as host evidence.

### New findings (Low, test gaps in this diff; each survives the suite and is killed by a probe)
- **L1** (host.py:648, tests/test_host_h1.py:898): moving `_submission_schema` after the tail checks (R4) survives. The test uses the genuine tail. Under R4, a producer with no schema source and a failing tail (CP-1B's real two-input tail) would answer `identity_mismatch` instead of the ruled `not_permitted`. Killed by p10 B15-B18.
- **L2** (host.py:656, tests/test_host_h1.py:826-847): replacing the exact owner tail id with a prefix match (R2) or a suffix match (R3) survives. Killed by p10 A4d and A4e.
- **L3** (host.py:72, tests/test_host_h1.py:384 and :924): a CP-DR scope that drops `unreadable` sources (R1) survives, because the tests use only a `missing` source. Killed by p11 and p13.

Runner: `<P>/mutate_review.py`, output in `<P>/mutate_review.out`.

Outside the diff, for the owner (Info): the CPDR lease body still says "the whole ready pack" at :33 and :212; LEAD amended only its header. The test module docstring cites `CPDR-OWNER-LEASE.md:31`, but D-B is now at :33.

### Mutants and gates
- `<S>/h1-fix2/mutate_fix2.py` on a fresh copy: exit 0, 11 of 11 killed.
- `pytest -q -p no:cacheprovider tests/test_host_h1.py tests/test_owner_g1x.py`: exit 0, 48 passed.
- `ruff check` (host.py, tests/test_host_h1.py): exit 0.
- `ruff format --check` (same files): exit 0.
- `MYPYPATH=src mypy --strict src` (cache in `<P>/mypycache`): exit 0, 111 files.
- No stub, fake value or catch-all in the diff. The fake core is test-only, and the new `except ValueError` around `step_chain` is narrow.

Not verified: no real Stage 1 owner core was used (test fake cores only). No real CP-1B head went through the host; I checked it as a unit and with a CP-1B-shaped tail on a fake head. The consumer-to-owner-producer edge exists only in a probe-patched registry; real CP-3 and CP-4 consumers need a promoted CP-1. The receipt verifier was not run on a head with forged content (I1 rests on reading owner_workflow.py:1738-1799). The deferred suites were not run: test_source_tools, test_source_workflow, test_owner_workflow, test_owner_s1a. The reviewer's 40-mutant mutate_h1.py was not rerun.
