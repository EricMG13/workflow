# Model Testing Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A framework that drives orchestrated pathway runs on four model configurations, scores every module's output against the six issuer goldens, tracks spend per provider account, records faults, and writes a provider comparison report.

**Architecture:** New package `src/deploy_workflow/model_testing/`. It never calls a model: the orchestrator (context plan Part B, O2 `run_pathway` and O5 model connection) does that and writes a run directory. The framework reads run directories (receipt, execution store, call records), scores the settled module results against `cases/goldens/<case>/` through a reviewed mapping table, and reports. Tasks 1–10 build and test offline against fixtures now; Task 11 wires to `run_pathway` once O2 and O5 are merged.

**Tech Stack:** Python 3.13, pydantic (`deploy_vii.contracts.Contract`), `decimal.Decimal`, stdlib only (no new dependency).

**Spec:** `docs/superpowers/specs/2026-10-31-model-testing-design.md` (approved 2026-10-31). Orchestrator side: `docs/superpowers/plans/2026-10-31-context-file-consumption.md` Part B. Gap list: `work/model-testing/recon/orchestration-gaps.md`.

## Global Constraints

- Live provider calls stay paused (`AGENTS.md:122-124`). Nothing in Tasks 1–10 makes a network call; Task 11's live mode refuses to start without a lifting ruling in `docs/rulings/`.
- Keys only from `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, read by the orchestrator, never by the framework. Never read `~/Documents/OP Router.rtf`. No key appears in any record, report or error text.
- New code only in `src/deploy_workflow/model_testing/`, tests in `tests/test_model_testing_*.py`, mapping files in `cases/goldens/<case>/mapping.json`. No change to `src/deploy_vii` or to other `src/deploy_workflow` modules.
- No new dependency. Money, scores and comparisons in `Decimal`; money serialised as strings.
- Configurations (spec §7.1): `sol-medium` openai `gpt-6.1-sol` medium; `sol-high` openai `gpt-6.1-sol` high; `opus-medium` anthropic `claude-opus-5-5` medium; `deepseek-max` openrouter `deepseek/deepseek-v4.1-flash-1017` max.
- Accounts (spec §7.2): openai credit 130, anthropic 150, openrouter 20; reserve 10%; usable 117, 135, 18 (USD).
- Gates per task: `PYTHONPATH=src .venv/bin/python -m pytest <test file> -q -p no:cacheprovider`, `ruff check`, `ruff format --check`, `mypy` (strict) on changed files. Test runs follow the deferral policy in force (deferred tests are recorded `gates-first-pass=n/a`).
- Every task brief carries: no stub or fake value standing in for real behaviour; no catch-all that hides a failure; the report ends with a `Not verified:` line.

## Review Focus

- **Codex gold changed after the pin.** TDG and SHC gold were snapshotted mid-fix (spec §9a.6). A `financial_gold.json` whose sha256 differs from `module_golden.json` → `CaseError` naming the file, never a silent rescore. Task 4.
- **Key material in a call record.** A provider error echoed into a record's `error` text (e.g. `sk-or-…`, `sk-ant-…`, `sk-proj-…`) → `JournalError`; the record is never accepted or reported. Task 2.
- **Unknown charge.** A record with `cost_status: "unknown"` counts its full `reserved_usd` against the account until settled, and `cap_for` returns 0 once usable credit is exhausted. Task 3.
- **Scale mismatch.** A module fact in units (or with `scale` 1000000) against a golden stored in millions or thousands must compare equal when the values are equal in units. Task 7.
- **Retries and reruns.** Several attempts for one module: cost counts every call record; accuracy uses only the settled head named in the receipt. Task 8.

---

### Task 1: Configurations and accounts

**Files:**
- Create: `src/deploy_workflow/model_testing/__init__.py` (empty), `src/deploy_workflow/model_testing/configs.py`
- Test: `tests/test_model_testing_configs.py`

**Interfaces:**
- Produces:
  - `Provider = Literal["openai", "anthropic", "openrouter"]`, `Role = Literal["repair", "comparison"]`
  - `@dataclass(frozen=True) class ModelConfig: config_id: str; provider: Provider; model: str; effort: str; roles: frozenset[Role]`
  - `CONFIGS: Mapping[str, ModelConfig]` (the four in Global Constraints; roles: `sol-medium` and `deepseek-max` both roles, `sol-high` and `opus-medium` comparison only)
  - `@dataclass(frozen=True) class Account: account_id: Provider; credit: Decimal; reserve: Decimal = Decimal("0.10")` with property `usable -> Decimal` (= credit × (1 − reserve), exact)
  - `ACCOUNTS: Mapping[Provider, Account]`
  - `CASES: Mapping[PathwayId, str]` (pathway → case dir name, spec §7.3 table); `PILOT_PATHWAY = "earnings_update"`
  - `OPUS_PATHWAYS: tuple[PathwayId, ...] = ("earnings_update", "portfolio_decision", "credit_snapshot", "covenant_refinancing", "relative_value")`

- [ ] **Step 1: Write the failing tests**

```python
def test_usable_caps():
    assert {a: ACCOUNTS[a].usable for a in ACCOUNTS} == {
        "openai": Decimal("117.00"), "anthropic": Decimal("135.00"), "openrouter": Decimal("18.00")}

def test_configs_match_ruling():
    assert set(CONFIGS) == {"sol-medium", "sol-high", "opus-medium", "deepseek-max"}
    assert CONFIGS["opus-medium"].model == "claude-opus-5-5" and CONFIGS["opus-medium"].effort == "medium"
    assert CONFIGS["deepseek-max"].model == "deepseek/deepseek-v4.1-flash-1017"
    assert {c for c, m in CONFIGS.items() if "repair" in m.roles} == {"sol-medium", "deepseek-max"}

def test_cases_cover_every_preset():
    from deploy_vii.contracts import _PRESETS
    assert set(CASES) == set(_PRESETS)
    assert all((Path("cases/goldens") / d / "module_golden.json").is_file() for d in CASES.values())

def test_opus_pathways_exclude_distressed():
    assert "distressed_restructuring" not in OPUS_PATHWAYS and OPUS_PATHWAYS[0] == PILOT_PATHWAY
```

- [ ] **Step 2: Run, expect FAIL** (`ModuleNotFoundError: deploy_workflow.model_testing`)
- [ ] **Step 3: Implement `configs.py`** as listed. `PathwayId` imported from `deploy_vii.contracts`.
- [ ] **Step 4: Run tests and gates, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): configurations and accounts`

---

### Task 2: Call records and journal reader

The orchestrator (O5) writes one record per model call. This task fixes the record contract the framework consumes; the controller sends it to the context-form session so O5 emits exactly this shape.

**Files:**
- Create: `src/deploy_workflow/model_testing/records.py`
- Test: `tests/test_model_testing_records.py`

**Interfaces:**
- Consumes: `Provider`, `CONFIGS` (Task 1)
- Produces:
  - `class CallRecord(Contract)`: `schema_version: Literal["model-call/1"]`; `run_id`, `case_id`, `pathway`, `module_id`, `step_id: str`; `attempt: int` (0 or 1); `call_index: int` (≥ 0, order within the step); `config_id: str`; `provider: Provider`; `requested_model`, `reported_model: str | None`; `requested_effort: str`; `invocation_digest: str` (64 hex); `request_id: str | None`; `http_status: int | None`; `started_at`, `first_byte_at`, `finished_at: datetime | None`; `input_tokens`, `cached_read_tokens`, `cache_write_tokens`, `output_tokens`, `reasoning_tokens: int | None` (None = not reported, never 0); `reserved_usd: Decimal`; `settled_usd: Decimal | None`; `cost_status: Literal["billed", "computed", "unknown"]`; `tool_calls: tuple[ToolCallRecord, ...]`; `submit_sha256: str | None`; `error_class: str | None`; `error: str | None`
  - `class ToolCallRecord(Contract)`: `name: str`, `arguments_sha256: str`, `result_bytes: int`, `refusal_code: str | None`
  - `class JournalError(ValueError)`
  - `read_journal(path: Path) -> tuple[CallRecord, ...]`

- [ ] **Step 1: Write the failing tests**

```python
def test_reads_valid_journal(tmp_path): ...  # two records written with model_dump_json, read back equal, order kept
def test_refuses_duplicate_call(tmp_path):    # same (run_id, module_id, step_id, attempt, call_index) twice
    with pytest.raises(JournalError, match="duplicate call"): read_journal(p)
def test_refuses_key_material(tmp_path):      # error="401 invalid key sk-or-v1-abc123"
    with pytest.raises(JournalError, match="key material"): read_journal(p)
def test_refuses_unknown_config(tmp_path):    # config_id="opus-high"
    with pytest.raises(JournalError, match="opus-high"): read_journal(p)
def test_settled_requires_known_cost(tmp_path):  # cost_status="unknown" with settled_usd set
    with pytest.raises(JournalError): read_journal(p)
def test_missing_tokens_stay_none(tmp_path):  # record without reasoning_tokens → None, not 0
```

- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement.** One JSON object per line; a blank or unparsable line is a `JournalError` with its line number. Key-material check: regex `\b(sk-(or|ant|proj)-[A-Za-z0-9_-]{6,}|sk-[A-Za-z0-9]{20,})` over every string field. `cost_status != "unknown"` requires `settled_usd`; `"unknown"` requires `settled_usd is None`. `provider` must equal `CONFIGS[config_id].provider`.
- [ ] **Step 4: Run tests and gates, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): call record contract and journal reader`

---

### Task 3: Account spend and run caps

**Files:**
- Create: `src/deploy_workflow/model_testing/budget.py`
- Test: `tests/test_model_testing_budget.py`

**Interfaces:**
- Consumes: `ACCOUNTS`, `CONFIGS` (Task 1); `CallRecord` (Task 2)
- Produces:
  - `account_spend(records: Iterable[CallRecord], account_id: Provider) -> Decimal`: sum of `settled_usd`, plus `reserved_usd` for `cost_status == "unknown"`
  - `cap_for(config_id: str, records: Iterable[CallRecord]) -> Decimal`: `max(Decimal(0), usable − account_spend)` for the config's account
  - `class BudgetExhausted(RuntimeError)`; `require_budget(config_id, records, needed: Decimal) -> Decimal` raises when `cap_for < needed`

- [ ] **Step 1: Write the failing tests**

```python
def test_spend_sums_settled_and_unknown():  # openai: settled 10.50 + unknown reserved 3.25 + anthropic 9.00
    assert account_spend(rs, "openai") == Decimal("13.75")
def test_shared_account():                  # sol-medium and sol-high both draw on openai
    assert cap_for("sol-high", rs) == Decimal("117.00") - Decimal("13.75")
def test_cap_floor_zero():                  # openrouter spend 18.40
    assert cap_for("deepseek-max", rs) == Decimal(0)
def test_require_budget_raises():
    with pytest.raises(BudgetExhausted, match="deepseek-max"): require_budget("deepseek-max", rs, Decimal("0.01"))
```

- [ ] **Step 2: Run, expect FAIL** · **Step 3: Implement** · **Step 4: Run tests and gates, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): account spend and caps`

---

### Task 4: Golden case loader

**Files:**
- Create: `src/deploy_workflow/model_testing/cases.py`
- Test: `tests/test_model_testing_cases.py`

**Interfaces:**
- Consumes: `CASES` (Task 1); `cases/goldens/check.py` (`check_case(case_dir, corpus)`, `normalise`, `SCALE_EXP`)
- Produces:
  - `@dataclass(frozen=True) class GoldenCase: case_id: str; pathway: PathwayId; case_dir: Path; context_path: Path; golden: Mapping[str, Any]; facts: Mapping[str, Mapping[str, Any]]` (by `fact_id`)`; financial_gold_path: Path; financial_gold_sha256: str`
  - `class CaseError(ValueError)`
  - `load_case(case_dir: Path, corpus: Path) -> GoldenCase`
  - `checker() -> ModuleType`: loads `cases/goldens/check.py` once via `importlib.util.spec_from_file_location` (ponytail: the checker stays a standalone stdlib script; this is its only importer)

- [ ] **Step 1: Write the failing tests**

```python
def test_loads_every_golden():
    for d in CASES.values():
        c = load_case(Path("cases/goldens") / d, CORPUS)
        assert c.facts and c.context_path.name == "context.json"
def test_refuses_changed_financial_gold(tmp_path):  # copy shc case + gold, append a byte to the gold copy
    with pytest.raises(CaseError, match="financial_gold.*sha256"): load_case(case, CORPUS)
def test_refuses_failing_checker(tmp_path):         # copy a case, change one quote
    with pytest.raises(CaseError, match="check.py"): load_case(case, CORPUS)
```

`CORPUS = Path("/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1")`; tests needing it are skipped with a reason when it is absent (the corpus is gitignored).

- [ ] **Step 2: Run, expect FAIL** · **Step 3: Implement** (`check_case` findings non-empty → `CaseError` listing the first five) · **Step 4: Run, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): golden case loader with gold pin`

---

### Task 5: Mapping contract and loader

The goldens are not keyed to module outputs (spec §9a.1). A mapping entry ties one golden fact to one fact in a module result (`deploy_vii.contracts.Module.facts`, located by `table_id`, `row_id`, `field`, `period`).

**Files:**
- Create: `src/deploy_workflow/model_testing/mapping.py`
- Test: `tests/test_model_testing_mapping.py`

**Interfaces:**
- Consumes: `GoldenCase` (Task 4)
- Produces:
  - `class Locator(Contract)`: `table_id: str`, `row_id: str`, `field: str`, `period: str | None`
  - `class MappingEntry(Contract)`: `fact_id: str`, `module: str`, `locator: Locator`, `subject_aliases: tuple[str, ...] = ()`, `depends_on: tuple[str, ...] = ()` (golden fact_ids whose upstream value this fact uses)
  - `class Unmapped(Contract)`: `fact_id: str`, `reason: str` (non-empty)
  - `class Mapping(Contract)`: `schema_version: Literal["golden-mapping/1"]`, `case_id: str`, `preparer: str`, `reviewer: str`, `entries: tuple[MappingEntry, ...]`, `unmapped: tuple[Unmapped, ...]`
  - `class MappingError(ValueError)`; `load_mapping(path: Path, case: GoldenCase) -> Mapping`

- [ ] **Step 1: Write the failing tests**

```python
def test_every_fact_accounted_once(tmp_path):   # a fact in entries and unmapped
    with pytest.raises(MappingError, match="once"): load_mapping(p, case)
def test_unknown_fact_refused(tmp_path):        # entry fact_id not in case.facts
def test_module_must_match_golden(tmp_path):    # entry.module "CP-4" for a CP-2 golden fact
def test_locator_unique(tmp_path):              # two entries with one locator in one module
def test_depends_on_known(tmp_path):            # depends_on names an absent fact
def test_preparer_differs_from_reviewer(tmp_path):
    with pytest.raises(MappingError, match="reviewer"): load_mapping(p, case)
```

- [ ] **Step 2: Run, expect FAIL** · **Step 3: Implement** · **Step 4: Run, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): golden mapping contract`

---

### Task 6: Mapping oracle stage (six `mapping.json` files)

Oracle work, not code (spec §9a.1): preparer ≠ reviewer ≠ scorer builder (Task 7), ids in the ledger. One ICM stage like `work/model-testing/goldens/`.

**Files:**
- Create: `work/model-testing/mapping/CONTEXT.md` (stage contract), `work/model-testing/mapping/briefs/<case>.md`, `cases/goldens/<case>/mapping.json` × 6
- Test: Task 5's `load_mapping` on all six

**Stage contract inputs:** the case's `module_golden.json`; the module's owner core and its `methodology.json` table ids (which `table_id`/`row_id`/`field` each module writes); the module's synthetic owner oracle `cases/<module>-owner/expected.json` and the replay in `tests/*_runs.py` for real result layouts; Task 5's contract.

**Rules:** one entry per golden fact the module writes; a golden fact no module output can hold goes to `unmapped` with the reason (never guessed); `depends_on` lists golden operands from upstream modules; subject aliases only for names the module would print differently (e.g. "Term Loan B" vs "Term B Loans").

- [ ] **Step 1:** Controller writes `CONTEXT.md` and six briefs (no code).
- [ ] **Step 2:** Six preparer dispatches (`mx-feature`), one per case; each runs `load_mapping` and reports exit 0.
- [ ] **Step 3:** Six reviews (`mx-precise`), sampling ≥ 30 entries per case against the module code; fix round per case if a High/Medium finding.
- [ ] **Step 4:** Test `test_all_mappings_load` in `tests/test_model_testing_mapping.py`: every case in `CASES` loads, and `unmapped` ≤ 20% of known facts per case (else the stage reports why).
- [ ] **Step 5: Commit** `goldens: mapping tables (six cases)`

---

### Task 7: Module scorer

**Files:**
- Create: `src/deploy_workflow/model_testing/scoring.py`
- Test: `tests/test_model_testing_scoring.py`

**Interfaces:**
- Consumes: `GoldenCase`, `checker()` (Task 4); `Mapping` (Task 5); `deploy_vii.contracts.Module`, `Fact`
- Produces:
  - `Outcome = Literal["match", "mismatch", "missing_in_output", "invented", "gap_ok", "conflict_ok", "unmapped", "inherited"]`
  - `class FactScore(Contract)`: `fact_id`, `outcome: Outcome`, `expected: str | None`, `observed: str | None`
  - `class ModuleScore(Contract)`: `module_id`, `head_status: Literal["accepted", "restricted", "blocked", "absent"]`, `facts: tuple[FactScore, ...]`, `untraced: tuple[str, ...]` (module fact ids), `unscored: int`, `judgment: bool`, `passed: bool`
  - `JUDGMENT_MODULES = frozenset({"CP-5", "CP-6", "CP-MODEL", "CP-2A"})`
  - `score_module(module: Module | None, module_id: str, head_status: str, case: GoldenCase, mapping: Mapping, upstream_mismatches: frozenset[str]) -> ModuleScore`

**Rules (spec §7.4, §9a, §10.3):**
- Numeric: compare in units. Golden units = `Decimal(value).scaleb(SCALE_EXP[scale])`; module units = `amount × fact.scale` (Step 3 confirms this against `deploy_vii/display.py`); percent and bps compare as stored. Exact equality, except when the golden has fewer decimal places: quantise the module value half-up to the golden's places first.
- Text: `normalise(x).casefold()` equal, or equal to a `subject_aliases` entry.
- Golden `missing`: `gap_ok` when the module fact is absent or not `known`; `invented` when it carries a value.
- Golden `conflicting`: `conflict_ok` when the module fact is `conflicting`, or known with one of the evidenced values and a limitation; else `mismatch`.
- `inherited`: a `mismatch` whose entry `depends_on` intersects `upstream_mismatches`; excluded from `passed`.
- Provenance: every `known` module fact with an `amount` needs `citations` or `calculation_id`; others go to `untraced` and fail the module.
- Honest gap: `head_status` blocked/restricted, or every mapped fact non-known, passes only when each non-known fact has a limitation and nothing is invented or untraced.
- Judgment modules: no value facts required; pass on provenance and no `invented`.
- `passed`: no `mismatch`, `missing_in_output`, `invented`, no `untraced`.

- [ ] **Step 1: Write the failing tests** (fixtures built as `Module(...)` objects, values from the real goldens)

```python
def test_millions_vs_units_match():   # golden IHRT 3.9 billions; module amount 3900000000 scale 1
def test_thousands_vs_scale_match():  # golden LTH 1,534,149 thousands; module amount 1534.149 scale 1000000
def test_fewer_golden_decimals():     # golden 92.2 percent; module 92.21 → match after half-up quantise
def test_entity_case_insensitive():   # golden "LTF Club Operations Company, Inc."; module "LTF CLUB OPERATIONS COMPANY, INC."
def test_invented_against_missing():  # NATL term_b principal golden missing; module known 320 → invented, passed False
def test_inherited_excluded():        # mismatch with depends_on in upstream_mismatches → inherited, passed True
def test_untraced_fails():            # known amount, no citations, no calculation_id
def test_honest_gap_passes():         # head blocked, facts missing with limitations → passed True
def test_unmapped_reported_not_missing():
```

- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement.** First read `deploy_vii/display.py` scale handling and pin the units rule with `test_thousands_vs_scale_match`; if `scale` means something else, stop and report BLOCKED with the evidence.
- [ ] **Step 4: Run tests and gates, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): module scorer`

---

### Task 8: Pathway score from a run directory

**Run directory contract** (what O2 `run_pathway` must write; the controller sends it to the context-form session with Task 2's record contract): `<run_dir>/execution/` (the `Execution` store), `<run_dir>/owner-run.json` (`OwnerRunReceipt`), `<run_dir>/publication/` (or absent), `<run_dir>/delivery/` (rendered slice), `<run_dir>/calls.jsonl` (Task 2 records), `<run_dir>/run.json` (`case_id`, `pathway`, `config_id`, `run_id`).

**Files:**
- Create: `src/deploy_workflow/model_testing/pathway.py`
- Test: `tests/test_model_testing_pathway.py`

**Interfaces:**
- Consumes: Tasks 2, 4, 5, 7; `deploy_workflow.owner_workflow.OwnerRunReceipt`, `verify_owner_run_receipt`; `deploy_workflow.owner_rendering.verify_owner_rendered_slice`; `deploy_vii.execution.Execution.result`
- Produces:
  - `class PathwayScore(Contract)`: `run_id`, `case_id`, `pathway`, `config_id`, `modules: tuple[ModuleScore, ...]` (plan order), `rendered: bool`, `passed: bool`
  - `score_run(run_dir: Path, case: GoldenCase, mapping: Mapping) -> PathwayScore`

**Rules:** walk `receipt.plan` in order; each module's result is `Execution.result(head.result_sha256)` for its settled head (no head → `absent`); `upstream_mismatches` accumulates mismatched fact_ids of earlier modules; `rendered` = receipt verifies and `verify_owner_rendered_slice` raises nothing; `passed` = every module passed and `rendered`.

- [ ] **Step 1: Write the failing tests** using a run directory produced offline from an existing replay (`tests/s1a_runs.py` or `tests/czr_runs.py` helpers) with a test mapping: `test_scores_plan_order`, `test_retry_uses_settled_head_only` (two attempts in the store, one head), `test_tampered_delivery_not_rendered` (flip a byte in `delivery/report.html` → `rendered False`, `passed False`), `test_absent_module_fails`.
- [ ] **Step 2: Run, expect FAIL** · **Step 3: Implement** · **Step 4: Run, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): pathway score from run directory`

---

### Task 9: Fault records

**Files:**
- Create: `src/deploy_workflow/model_testing/faults.py`
- Test: `tests/test_model_testing_faults.py`

**Interfaces:**
- Produces:
  - `FaultClass = Literal["product", "prompt", "harness", "model"]`
  - `class FaultRecord(Contract)`: `schema_version: Literal["fault/1"]`, `fault_id`, `run_id`, `case_id`, `pathway`, `module_id`, `step_id`, `config_id`, `fault_class: FaultClass`, `assigned_by: str` (agent id), `confirmed_by: str` (controller), `evidence: tuple[str, ...]` (call `invocation_digest`s and fact_ids, ≥ 1), `fix_ref: str | None`, `rerun_run_id: str | None`, `rerun_passed: bool | None`
  - `append_fault(path: Path, record: FaultRecord) -> None` (append-only JSONL, fsync; duplicate `fault_id` refused)
  - `read_faults(path: Path) -> tuple[FaultRecord, ...]`
  - `MAX_FIX_ROUNDS = 2`; `fix_rounds(faults, case_id, module_id, fault_class) -> int` (records with `fix_ref`); `needs_owner(faults, case_id, module_id, fault_class) -> bool` (≥ `MAX_FIX_ROUNDS` and last rerun not passed)

- [ ] **Step 1: Write the failing tests:** `test_append_and_read`, `test_duplicate_fault_refused`, `test_assigner_differs_from_confirmer`, `test_needs_owner_after_two_failed_rounds`, `test_model_fault_needs_no_fix_ref`.
- [ ] **Step 2: Run, expect FAIL** · **Step 3: Implement** · **Step 4: Run, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): fault records`

---

### Task 10: Comparison report

**Files:**
- Create: `src/deploy_workflow/model_testing/report.py`
- Test: `tests/test_model_testing_report.py`, fixture `tests/fixtures/model_testing/report_expected.md`

**Interfaces:**
- Consumes: `PathwayScore` (8), `CallRecord` (2), `FaultRecord` (9), `account_spend`, `ACCOUNTS` (3, 1)
- Produces: `render_report(scores: Sequence[PathwayScore], records: Sequence[CallRecord], faults: Sequence[FaultRecord]) -> str`

**Layout (spec §7.8):** per pathway, a table: rows modules in plan order, columns configs; cell `PASS 41/41 · $1.23 · 18.4k tok · 52 s` or `FAIL 37/41 (2 inherited)`. Then a totals table per config (accuracy = matched / scored known facts, inherited excluded; cost; tokens; median wall time; retries = calls with `attempt == 1`). Then faults by class. Then spend vs usable cap per account. Costs from records, `Decimal` quantised to cents half-up; tokens with `None` shown as `n/r`, never 0.

- [ ] **Step 1: Write the failing test** `test_report_matches_fixture`: two configs × one pathway fixture → byte-equal to `report_expected.md` (the controller reviews the fixture as the spec of the layout); `test_unknown_cost_flagged` (an unknown-cost call shows `reserved` beside the total).
- [ ] **Step 2: Run, expect FAIL** · **Step 3: Implement** · **Step 4: Run, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): comparison report`

---

### Task 11: Run driver (starts after context plan Part B O2 and O5 are merged)

**Files:**
- Create: `src/deploy_workflow/model_testing/run.py`, `src/deploy_workflow/model_testing/__main__.py`
- Test: `tests/test_model_testing_run.py`

**Interfaces:**
- Consumes: everything above; `run_pathway(case, context, pathway, config, cap)` from O2 (its exact signature is read from the merged code; the brief records it)
- Produces:
  - `plan_runs(stage: Literal["pilot", "repair", "comparison"]) -> tuple[tuple[str, PathwayId, str], ...]` (case_id, pathway, config_id): pilot = `PILOT_PATHWAY` × four configs; repair = six pathways × repair configs; comparison = six pathways × `sol-high` plus `OPUS_PATHWAYS` × `opus-medium`
  - `main(argv) -> int`: `python -m deploy_workflow.model_testing {pilot|repair|comparison|score|report} [--live --ruling docs/rulings/<file>.md] --out artifacts/model-testing/<run_id>/`

**Rules:** offline by default (O5's recorded-response adapter); `--live` refuses unless `--ruling` names an existing file under `docs/rulings/`, whose path and sha256 go into `run.json`. Before each run, `require_budget` with the config's estimated cost from the pilot (or the spec §7.2 estimate before the pilot); a `BudgetExhausted` stops that config and the report says so. `distressed_restructuring` on `opus-medium` runs only when `cap_for("opus-medium", …)` ≥ its measured estimate after the five Opus pathways.

- [ ] **Step 1: Write the failing tests:** `test_plan_counts` (pilot 4, repair 12, comparison 11), `test_live_refused_without_ruling`, `test_budget_exhausted_skips_config`, `test_offline_pilot_scores` (the offline pilot on the recorded adapter writes four run dirs, each scored, and one report).
- [ ] **Step 2: Run, expect FAIL** · **Step 3: Implement** · **Step 4: Run tests and gates, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): run driver`

---

## After the plan

- The first live call (the pilot) happens only after the user's lifting ruling, with the prerequisites in spec §6 met.
- Re-estimate the budget from the pilot's records (Task 3 sums) before the repair pass.
- Whole-branch review per global rules (`mx-architect`; `confidence-review` and `rewrite-tournament` once on the branch diff).
