# Context File Consumption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the workflow read the context form's `context.json` (schema `context/1`):
Phase 1 builds the shared foundation (validated reader, pack entry, frozen-pack reader); Phases
2-8 connect the modules that use it, each under its own lease.

**Architecture:** `context.json` enters the prepared pack as an ordinary `text/plain` source
with id `context`, so it is hashed and frozen like every other source. A new
`deploy_workflow.context` module validates it with the form's exact rules, builds the
`PreparationRequest` (mapping onto existing `Run` fields only), and gives owners a typed
`RunContext` read from the frozen pack, never from the user's live file. Python reads every
figure by field; no model quotes a context figure.

**Tech Stack:** Python 3.13.15, pydantic `Contract` (`deploy_vii.contracts`), pytest,
hypothesis, ruff, mypy strict. No new dependency.

**Spec:** `docs/CONTEXT-FILE-PROPOSAL.md` and the form `docs/templates/context-form.html`
(its `build()` function, lines ~720-806, is the normative rule set for `context/1`).

## Global Constraints

- No change to `src/deploy_vii` in Phase 1. Shared interfaces and `src/deploy_vii` changes are
  the user's (AGENTS.md); later phases that need one say so in their decision line.
- Closed stages stay closed: module behaviour changes (Phases 2-8) enter
  `work/build/stage<next>-backlog.md` and run under a lease, questions file, frozen oracle and
  `mx-precise` review per AGENTS.md "How work moves". The Modules controller owns them.
- Live/paid/provider calls stay paused; nothing in this plan makes a network call.
- Exact `Decimal` arithmetic; empty string means "not supplied", never zero.
- Every task brief carries: no stub or fake value standing in for real behaviour; no catch-all
  that hides a failure; report ends with a `Not verified:` line.
- Test commands: `PYTHONPATH=src .venv/bin/python -m pytest <path> -q`. Gates per task:
  `ruff check`, `ruff format --check`, `mypy` on changed files. Test runs follow the deferral
  policy in force (AGENTS.md: deferred tests are recorded `gates-first-pass=n/a`).

## Decisions (recommended defaults; the plan proceeds on these unless the user changes them)

| # | Decision | Recommended | Alternative |
|---|---|---|---|
| D1 | How the file enters a run | `text/plain` source, id `context` (no new media type) | add `application/json` to `SourceRequest` (`src/deploy_vii`) |
| D2 | CP-0 authority of the context source | `unknown`, as CP-8's `prior_case`; consuming modules label figures "user-supplied" | new `user` authority value (`src/deploy_vii`) |
| D3 | Run mapping | existing `Run` fields only; run type, periods, currency stay in the context source | add fields to `Run` (`src/deploy_vii`) |
| D4 | Pinned assumptions (Phase 6) | the owner refuses a submission whose value differs from the pinned one (fail closed; the submission stays the record) | the owner substitutes the pinned value |
| D5 | CP-DR web peer sourcing (Phase 7) | stays Planned while provider calls are paused; `cp_dr_public` gives Insufficient Information with the reason, users pick `user_list`/`user_comps` | unpause a provider for CP-DR only |

## Review Focus

- **Hand-edited files the form would refuse** (talk low > high, a quote dated after the run
  as-of, `issuer_trading` on an unlisted issuer): the reader re-applies every form rule and
  refuses with the field path. Pinned by Task 1's invalid-case table.
- **Duplicate JSON keys** (`{"as_of": "2026-01-01", "as_of": "2027-01-01"}`): Python's default
  keeps the last silently; the reader refuses. Pinned in Task 1.
- **Form and reader drift** (a key renamed, a number rule loosened in the form): fixtures saved
  from the real form must load, and the form's regex literals must equal the reader's. Task 2.
- **The context file edited after the pack was prepared**: owners read the frozen pack source,
  and a context whose issuer, as-of, pathway or case kind differs from `pack.run` is refused.
  Task 4.
- **Empty versus zero**: `""` reads as `None`, never `Decimal(0)`, in every numeric field. Task 1.

---

## Phase 1: Foundation (detailed)

### Task 1: `RunContext` model and `load_context`

**Files:**
- Create: `src/deploy_workflow/context.py`
- Test: `tests/product/test_context.py`

**Interfaces:**
- Produces:
  - `SCHEMA = "context/1"`; `NUM = r"^\d+(\.\d+)?$"`; `SNUM = r"^-?\d+(\.\d+)?$"`;
    `PERIOD = r"^(q[1-4]|h[12]|fy)-(\d{4})$"` (same literals as the form, line ~651 and ~675);
    `SLUG = r"^[a-z0-9][a-z0-9-]*$"` (Task 2 brings the form to this).
  - `class ContextRefused(ValueError)` with `problems: tuple[str, ...]` (each `"<json.path>: <message>"`).
  - `class RunContext(Contract)` and its nested contracts, field-for-field the `context/1`
    shape in the proposal: `RunSettings`, `Identity`, `DealTerm`, `Quote`, `Rating`,
    `IssuerMarket`, `PeerRow`, `Precedent`, `UserMultiple`, `Valuation`, `Cp2aScenario`,
    `Cp2aPins`, `Cp2dPins`, `Cp2ePins`, `Cp3cPins`, `Cp3dPins`, `Cp4cPins`, `Assumptions`
    (each pin field `X | None`), `Attachments`, `ResearchQuestion`. Numeric fields stay `str`.
    The top-level `schema` key is checked and stripped by `load_context`, not modelled
    (a pydantic field named `schema` shadows `BaseModel.schema`).
  - `def load_context(raw: bytes) -> RunContext` — raises `ContextRefused` listing every problem.
  - `def amount(text: str) -> Decimal | None` — `""` → `None`, else `Decimal(text)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_minimal_research_context_loads():
    ctx = load_context(json.dumps(MINIMAL).encode())   # MINIMAL: research run, issuer + as_of only
    assert ctx.run.run_type == "research" and ctx.run.pathway == "credit_snapshot"
    assert ctx.assumptions.cp2d is None and ctx.deal_terms == ()

def test_empty_amount_is_none_not_zero():
    assert amount("") is None and amount("0") == Decimal("0")

def test_duplicate_keys_refused():
    raw = b'{"schema": "context/1", "schema": "context/1"}'
    with pytest.raises(ContextRefused, match="duplicate key"):
        load_context(raw)

@pytest.mark.parametrize(("path", "value", "message"), INVALID_CASES)
def test_form_rules_refused(path, value, message):
    with pytest.raises(ContextRefused) as caught:
        load_context(json.dumps(set_path(MINIMAL, path, value)).encode())
    assert any(p.startswith(path) and message in p for p in caught.value.problems)
```

`INVALID_CASES` holds one row per rule of the form's `build()` (copy each rule's bound from
there): schema other than `context/1`; unknown key at any level; `run.run_type` outside
{primary, secondary, research, earnings}; `run.pathway` outside the six `PathwayId`s;
`run.as_of` not a real ISO date; periods missing on an earnings run; prior not earlier than
current (same kind); currency not three uppercase letters; empty `issuer_name`; `issuer_id`
outside `^[a-z0-9][a-z0-9-]*$` (a leading hyphen passes the form today but fails `Run`'s
`Identifier`); ticker set while unlisted; deal rows on a non-primary run; no deal row
on a primary run; spread or OID talk low > high; `1,250` in any number; a quote or rating or
peer or issuer-market as-of after `run.as_of`; quote without provider; bid > ask;
`issuer_trading` on an unlisted issuer; peers present for `peer_source` `none` or
`cp_dr_public`; user-comps EBITDA `0`; user multiple `0` and `100`; cp2a with 0 and 5
scenarios; cp2d horizon `0`, `61`, `12.5`; cp2e with 4 rate shocks or a shock of `1001`;
cp3d recovery `100`; cp4c multiple `0`; a pin without rationale; `legal_documents` outside
{executed, draft, none}; 11 research questions; row counts above the form's `ROW` `max`.

- [ ] **Step 2: Run to verify they fail**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/product/test_context.py -q`
Expected: FAIL (`ModuleNotFoundError: deploy_workflow.context`).

- [ ] **Step 3: Implement `load_context(raw: bytes) -> RunContext`**

Parse with `json.loads(raw.decode("utf-8-sig"), object_pairs_hook=...)` refusing duplicate
keys; validate shape with the contracts (`extra="forbid"` comes from `Contract`); then apply
the cross-field rules above in one pass that collects every problem before raising. Compare
numbers as `Decimal`, never `float`.

- [ ] **Step 4: Run to verify they pass**

Same command. Expected: PASS. Also `ruff check src/deploy_workflow/context.py tests/product/test_context.py`, `ruff format --check` on both, `mypy src/deploy_workflow/context.py`: exit 0.

- [ ] **Step 5: Commit**

```bash
git add src/deploy_workflow/context.py tests/product/test_context.py
git commit -m "feat: context/1 reader with the context form's rules"
```

### Task 2: Form drift guard

**Files:**
- Create: `cases/context/research-minimal.json`, `cases/context/primary-full.json`,
  `cases/context/README.md` (two lines: produced by the form's Download, how)
- Test: `tests/product/test_context.py` (append)

**Interfaces:**
- Consumes: `load_context`, `NUM`, `SNUM`, `PERIOD` from Task 1.
- Declared input: the two fixtures are produced by the controller in the browser with the form
  before dispatch (the implementer has no browser). `research-minimal.json`: Research run,
  issuer "Northbridge Group" (id `northbridge-group`), as-of 2026-10-31, everything else default.
  `primary-full.json` fills every step:
  two facilities, one quote, one rating, `user_comps` with three peers, basis `blend` with two
  precedents, all six pins, two research questions. Values are fictional.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("name", ["research-minimal.json", "primary-full.json"])
def test_form_output_loads(name):
    raw = (CASES / name).read_bytes()
    assert {"schema": SCHEMA, **load_context(raw).model_dump(mode="json")} == json.loads(raw)

def test_form_regexes_match_reader():
    html = FORM.read_text()
    assert f"const NUM = /{NUM}/, SNUM = /{SNUM}/;" in html
    assert f"/{PERIOD}/.exec(p)" in html
    assert f"/{SLUG}/.test(v)" in html   # SLUG = r"^[a-z0-9][a-z0-9-]*$", exported by Task 1
```

- [ ] **Step 2: Run to verify they fail** — Expected: FAIL (fixtures absent).
- [ ] **Step 3: Add the fixtures** (from the declared input) and change the form's slug test
  (`fld`, `r.t === 'slug'`) from `/^[a-z0-9-]+$/` to `/^[a-z0-9][a-z0-9-]*$/` so form and reader
  agree.
- [ ] **Step 4: Run to verify they pass** — Expected: PASS.
- [ ] **Step 5: Commit** `git add cases/context tests/product/test_context.py docs/templates/context-form.html` —
  `"test: context form fixtures and drift guard"`.

### Task 3: Pack preparation from a context file

**Files:**
- Modify: `src/deploy_workflow/context.py`
- Test: `tests/product/test_context_prepare.py`

**Interfaces:**
- Consumes: `RunContext`, `load_context`.
- Produces:
  - `CONTEXT_SOURCE_ID = "context"`
  - `def preparation_request(context: RunContext, *, run_id: str, context_path: str, sources: Sequence[SourceRequest]) -> PreparationRequest`
    — `Run(run_id=run_id, issuer_id=identity.issuer_id, issuer_name=identity.issuer_name,
    as_of=date.fromisoformat(run.as_of), case_kind=run.case_kind, pathway=run.pathway)`
    (`requested_modules` left to the preset); appends
    `SourceRequest(source_id="context", path=context_path, media_type="text/plain")`.
    Raises `ContextRefused` if any `sources` item already uses id `context`.
  - CLI: `python -m deploy_workflow.context prepare --context PATH --root DIR --run-id ID
    --source ID=RELPATH:MEDIA [--source ...] --destination DIR` → loads the file, builds the
    request (context path relative to `--root`), calls `deploy_vii.preparation.prepare`, prints
    the pack path. `MEDIA` is one of `text`, `pdf`, `xlsx`.

- [ ] **Step 1: Write the failing tests**

```python
def test_run_fields_come_from_context():
    req = preparation_request(load_context(FIX_MINIMAL), run_id="ctx-run-1", context_path="context.json", sources=())
    assert (req.run.issuer_name, req.run.issuer_id, str(req.run.as_of), req.run.pathway) == ("Northbridge Group", "northbridge-group", "2026-10-31", "credit_snapshot")
    assert req.run.requested_modules == PATHWAY_MODULES["credit_snapshot"]
    assert req.sources[-1] == SourceRequest(source_id="context", path="context.json", media_type="text/plain")

def test_context_id_collision_refused(): ...   # a source named "context" → ContextRefused

def test_cli_refuses_invalid_context_before_writing(tmp_path):
    # invalid context → exit code 2, problems on stderr, destination directory not created

def test_cli_prepares_pack(tmp_path):
    # research-minimal fixture + one text filing → pack.json has sources (filing, context), both ready
```

- [ ] **Step 2: Run to verify they fail** — `pytest tests/product/test_context_prepare.py -q`: FAIL.
- [ ] **Step 3: Implement `preparation_request` and the `prepare` CLI** (`argparse`; exit 2 on
  `ContextRefused` with one problem per stderr line; no write before validation).
- [ ] **Step 4: Run to verify they pass** — PASS; ruff/format/mypy exit 0.
- [ ] **Step 5: Commit** — `"feat: prepare a pack from a context file"`.

### Task 4: Typed context from a frozen pack

**Files:**
- Modify: `src/deploy_workflow/context.py`
- Test: `tests/product/test_context_pack.py`

**Interfaces:**
- Consumes: `load_context`, `CONTEXT_SOURCE_ID`, Task 3's CLI (to build test packs).
- Produces: `def context_facts(pack: PreparedPack) -> RunContext | None` — `None` when the pack
  holds no `context` source (every existing case pack); otherwise rebuilds the bytes as
  `"\n".join(span.text for span in source.spans)` and calls `load_context`. Raises
  `ContextRefused` when the source is not `ready`, or when the context's issuer name, issuer id,
  as-of, case kind or pathway differ from `pack.run`.

- [ ] **Step 1: Write the failing tests**

```python
def test_pack_without_context_gives_none(): assert context_facts(existing_case_pack) is None
def test_frozen_context_read_back(): assert context_facts(pack_from_fixture("primary-full.json")) == load_context(FIX_FULL)
def test_crlf_and_bom_file_reads_the_same(): ...   # same context saved with BOM + CRLF → equal RunContext
def test_context_not_matching_run_refused(): ...   # pack.run.as_of changed via model_copy → ContextRefused naming "as_of"
def test_unready_context_refused(): ...            # source status "missing" → ContextRefused
```

- [ ] **Step 2: Run to verify they fail** — FAIL.
- [ ] **Step 3: Implement `context_facts`.**
- [ ] **Step 4: Run to verify they pass** — PASS; ruff/format/mypy exit 0.
- [ ] **Step 5: Commit** — `"feat: read the run context from a frozen pack"`.

### Task 5: CP-0 accepts a pack holding the context source; run guide

**Files:**
- Test: `tests/product/test_context_readiness.py`
- Modify: `docs/RUN-GUIDE.md` (new section "Start from the context form")

**Interfaces:**
- Consumes: Task 3's CLI; `deploy_vii.readiness.build_readiness`; the CP-0 review pattern in
  `tests/test_source_workflow.py` (copy its review construction; add one `SourceAssessment`
  for `context` with authority `unknown` per D2).

- [ ] **Step 1: Write the failing test** `test_readiness_accepts_context_source`: a pack from
  the research fixture plus one synthetic filing; `build_readiness` returns a module whose P3
  facts include the `context` row and whose T1 `issuer` equals the context's issuer name; a
  review that omits the `context` assessment is refused (existing behaviour, asserted).
- [ ] **Step 2: Run to verify it fails** — FAIL until the pack builder exists in the test helper.
- [ ] **Step 3: Write the helper and the RUN-GUIDE section**: fill the form → save
  `context.json` beside the filings → run the Task 3 CLI → start the existing workflow with
  the produced pack. State that no module reads the context yet beyond `Run` (Phases 2-8).
- [ ] **Step 4: Run to verify it passes** — PASS.
- [ ] **Step 5: Commit** — `"test: CP-0 accepts a context source; run guide"`. Then update the
  form's top notice text in `docs/templates/context-form.html` to "The workflow reads the run
  settings and issuer from this file; module features tagged Planned are not built yet."

---

## Phases 2-8: module consumers (one plan each, written after its questions are ruled)

Each phase opens with `work/<lane>/<module>/questions.md`, rulings, a frozen oracle and a
lease (AGENTS.md "How work moves"), then gets its own detailed plan. All read the context
through `context_facts(pack)` (Task 4); a pack without a context source keeps today's
behaviour exactly, so every frozen case stays green.

| Phase | Modules | Change | Open questions | Done when |
|---|---|---|---|---|
| 2 Identity and periods | CP-0, CP-1, CP-1A, CP-1B, CP-L10 | CP-0 shows borrower/aliases beside the issuer gate; CP-1A shows context sector and sponsor as user-supplied beside its cited rows (cited rows still required); CP-1 compares located entity roles with the context names (a mismatch is an issue, never an override); CP-1B takes `current_period`/`prior_period` instead of `_case_parameters` (`earnings_workflow.py:1655`); CP-L10 offers the context periods | Does a borrower-name mismatch block CP-1 or record a gap? Which period kinds can CP-1B compare (q vs fy)? | An earnings run on a non-test `run_id` reaches CP-1B with the context's periods |
| 3 Market evidence | CP-3, CP-3D | `quotes` and `deal_terms` talk become the market evidence (observed / indicative_talk) with the context's dates; quote as-of checked against `Run.as_of`; `rv_quotes` retired | Is price talk one row per bound (low/high) or a range row? Staleness limit? | CP-3 runs on a secondary context with Python-read quotes; talk-only caps confidence |
| 4 Ratings | CP-2H | `ratings` rows feed the rating register; real agency names (S&P, Moody's, Fitch) replace the synthetic headers (`cp2h.py:161`) | Where do trigger terms come from when only a rating is given? | CP-2H states real agency ratings; no ratings → today's "Rating register not found" |
| 5 Attachments and modes | CP-0, CP-4, CP-DR | `attachments` declare expected sources (a declared but absent source is a CP-0 gap); CP-4 draft-document mode for primary runs; CP-DR answers `research_questions` beside gap research | Draft authority value (`src/deploy_vii`: user decision); may a draft-only CP-4 reach High confidence? | A primary run with draft documents reaches CP-4 with a "draft" limitation |
| 6 Pinned assumptions | CP-2A, CP-2D, CP-2E, CP-3C, CP-3D, CP-4C | A pinned value binds the submission (D4); the limitation reads "user-supplied assumption" | D4 confirmation; does a pin also feed the model prompt (live, paused)? | Each module refuses a differing submission and labels a pinned value |
| 7 Valuation | CP-1C, CP-DR, CP-4C, new valuation step | CP-1C adds EV/EBITDA (new `ev` operand) from user comps; issuer trading multiple from `issuer_market`; precedents; basis selection (`auto` thresholds); CP-4C takes the selected multiple; CP-DR web peers per D5 | `auto` thresholds (minimum count, maximum age, blend weights); where valuation lives (CP-1C or a new module); D5 | A private-issuer run with user comps produces a peer EV/EBITDA range and CP-4C uses it |
| 8 Periods and currency | CP-2D, CP-2G, CP-2H, CP-3C, CP-4C | Replace hard-coded LTM Q4 25 / FY2026-28 / q4-2025 / USD with the context's periods and currency | FX source for non-USD; forecast years from the period or the as-of? | One non-2025 context runs these modules without a hard-coded period |

Order: 2 → 3 → 4 → 5 → 6 → 7 → 8. Phase 8 can start after Phase 2 if real-issuer runs are
the priority, since it removes the largest blocker for non-synthetic cases.
