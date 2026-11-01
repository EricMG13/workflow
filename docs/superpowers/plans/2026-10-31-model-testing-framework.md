# Model Testing Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A framework that drives orchestrated pathway runs on four model configurations, scores every module's output against the six issuer goldens, tracks spend per provider account, records faults, and writes a provider comparison report.

**Architecture:** New package `src/deploy_workflow/model_testing/`. It never calls a model: the orchestrator (context plan Part B, O2 `run_pathway` and O5 model connection) does that and writes a run directory. The framework reads run directories (receipt, execution store, call records), scores the settled module results against `cases/goldens/<case>/` through a reviewed mapping table, and reports. Tasks 1–5 and 7–10 build and test offline now. O2 (`src/deploy_workflow/run_pathway.py`) and O5 (`src/deploy_workflow/model/`) are merged; Task 11 starts after O3, O4 and O6 are merged too (W4). Task 6 runs per module after that module's context-plan phase lands (W3).

**Amendments (2026-11-01, cross-plan review `work/context-plan/cross-plan-review-2026-10-31.md`, rows owned by B or both; cites re-checked against `codex/checkpoint` @ 2e7709cc):** C2 → Task 11; C4 → Tasks 2, 8, 11; W1 → Task 4; W3 → Tasks 5, 6; W4 → Task 11, Architecture; W5 → Task 2 (O5's `KEY_PATTERN`, `model/redact.py:19`, already is the widened pattern; Task 2 imports it); W7 → spec §7.6 and §10.2; W8 → Task 10; W9 → Tasks 7, 8; N2 → Task 4. Also from the merged tip: Task 2 consumes O5's `CallRecord` (`model/record.py:148`) instead of defining a second one, and adds the `run.json` reader; Task 3 counts only `mode: live` runs toward an account (the rule Plan A's record contract assigns to this plan).

**Tech Stack:** Python 3.13, pydantic (`deploy_vii.contracts.Contract`), `decimal.Decimal`, stdlib only (no new dependency).

**Spec:** `docs/superpowers/specs/2026-10-31-model-testing-design.md` (approved 2026-10-31). Orchestrator side: `docs/superpowers/plans/2026-10-31-context-file-consumption.md` Part B. Gap list: `work/model-testing/recon/orchestration-gaps.md`.

## Global Constraints

- Live provider calls stay paused (`AGENTS.md:122-124`). Nothing in Tasks 1–10 makes a network call. The live gate is O5's `live_adapter` (`model/adapter.py:447`, R2); Task 11 passes it the ruling and only pre-checks the path (C2).
- Keys only from `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, read by the orchestrator, never by the framework. Never read `~/Documents/OP Router.rtf`. No key appears in any record, report or error text.
- New code only in `src/deploy_workflow/model_testing/`, tests in `tests/test_model_testing_*.py`, fixtures in `tests/fixtures/model_testing/`, mapping files in `cases/goldens/<case>/mapping.json`. No change to `src/deploy_vii` or to other `src/deploy_workflow` modules (importing them is fine).
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

def test_configs_agree_with_orchestrator():  # O5 refuses a ModelSpec whose config/provider differ
    from deploy_workflow.model.turn import CONFIG_PROVIDERS, ModelSpec
    assert {c: m.provider for c, m in CONFIGS.items()} == dict(CONFIG_PROVIDERS)
    for m in CONFIGS.values():
        ModelSpec(m.config_id, m.provider, m.model, m.effort)

def test_cases_cover_every_preset():
    from deploy_vii.contracts import PATHWAY_MODULES
    assert set(CASES) == set(PATHWAY_MODULES)
    assert all((Path("cases/goldens") / d / "module_golden.json").is_file() for d in CASES.values())

def test_opus_pathways_exclude_distressed():
    assert "distressed_restructuring" not in OPUS_PATHWAYS and OPUS_PATHWAYS[0] == PILOT_PATHWAY
```

- [ ] **Step 2: Run, expect FAIL** (`ModuleNotFoundError: deploy_workflow.model_testing`)
- [ ] **Step 3: Implement `configs.py`** as listed. `PathwayId` imported from `deploy_vii.contracts`.
- [ ] **Step 4: Run tests and gates, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): configurations and accounts`

---

### Task 2: Run directory reader (`run.json` and call records)

The orchestrator writes `run.json` (O2, `run_pathway.py:161-185`, sole writer) and one `model-call/1` record per provider request in `calls.jsonl` (O5, `model/record.py:148` `CallRecord`). This task reads both; it defines neither record shape (C4). The record contract is O5's class, imported, so the two can never drift.

**Files:**
- Create: `src/deploy_workflow/model_testing/records.py`
- Test: `tests/test_model_testing_records.py`

**Interfaces:**
- Consumes: `CONFIGS` (Task 1); `deploy_workflow.model.record.CallRecord`, `ToolCallRecord`; `deploy_workflow.model.redact.KEY_PATTERN` (`redact.py:19`, `\b(sk-(or|ant|proj)-[A-Za-z0-9_-]{6,}|sk-[A-Za-z0-9_-]{20,})`, the widened pattern of W5)
- Produces:
  - `class RunSource(Contract)`: `source_id`, `path`, `sha256: str`, `media_type: str`, `converted_sha256: str | None`
  - `class RunMeta(Contract)`: the `run.json` fields as `_write_run_json` writes them: `case_id`, `pathway: PathwayId`, `config_id`, `run_id: str`; `mode: Literal["offline", "live"]`; `cap_usd: Decimal`; `sources: tuple[RunSource, ...]`; `cp_dr_invoked: bool`; `replayed_from_run: str | None`; `outcome: Literal["settled", "stopped"]`; `stopped_reason: str | None`; `ruling_path`, `ruling_sha256`, `ruling_date: str | None = None`. Validator: the three ruling fields are set exactly when `mode == "live"`; `stopped_reason` is set exactly when `outcome == "stopped"`.
  - `class JournalError(ValueError)`
  - `read_journal(path: Path) -> tuple[CallRecord, ...]`
  - `read_run(run_dir: Path) -> tuple[RunMeta, tuple[CallRecord, ...]]` (`run.json` absent → `JournalError` "no run.json": the run was refused or crashed, nothing to score; `calls.jsonl` absent → no records)

- [ ] **Step 1: Write the failing tests** (records built with `CallRecord(...)` and written with `model_dump_json`)

```python
def test_reads_valid_journal(tmp_path): ...    # two records read back equal, order kept
def test_refuses_duplicate_call(tmp_path):     # same (run_id, module_id, step_id, attempt, call_index) twice
    with pytest.raises(JournalError, match="duplicate call"): read_journal(p)
def test_refuses_key_material(tmp_path):       # line hand-written with error="401 invalid key sk-proj-abcdef123456"
    with pytest.raises(JournalError, match="key material") as e: read_journal(p)
    assert "abcdef123456" not in str(e.value)  # the value never echoes
def test_refuses_long_bare_key(tmp_path):      # error holds "sk-" + 24 chars with "-" and "_" (W5)
def test_refuses_unknown_config(tmp_path):     # config_id="opus-high"
    with pytest.raises(JournalError, match="opus-high"): read_journal(p)
def test_settled_requires_known_cost(tmp_path):  # cost_status="unknown" with settled_usd set
def test_null_tokens_stay_none(tmp_path):      # reasoning_tokens null → None, not 0
def test_reads_run_json(tmp_path):             # offline settled run.json → RunMeta; records' run_id/case_id/pathway/config_id must equal it
def test_live_run_needs_ruling_fields(tmp_path):
def test_record_from_other_run_refused(tmp_path):  # a record whose run_id differs from run.json
```

- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement.** One JSON object per line; a blank or unparsable line is a `JournalError` with its line number. Each line is validated as O5's `CallRecord` (its validator already refuses key material and an unknown/settled mismatch); a `ValidationError` becomes `JournalError` with the line number and each error's location and message, never the input (`errors(include_input=False)`, as `model/record.py:115` `_invalid` does); O5's validator message "a record field holds key material" survives that, so the key-material refusal says "key material" while the value never appears. `config_id` must be in `CONFIGS` and `provider` must equal `CONFIGS[config_id].provider`. `read_run` checks every record's identity fields against `run.json`.
- [ ] **Step 4: Run tests and gates, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): run directory reader`

---

### Task 3: Account spend and run caps

**Files:**
- Create: `src/deploy_workflow/model_testing/budget.py`
- Test: `tests/test_model_testing_budget.py`

**Interfaces:**
- Consumes: `ACCOUNTS`, `CONFIGS` (Task 1); `RunMeta`, `CallRecord` (Task 2)
- Produces (`Runs = Sequence[tuple[RunMeta, Sequence[CallRecord]]]`, read more than once so never a generator, what `read_run` returns per run directory):
  - `account_spend(runs: Runs, account_id: Provider) -> Decimal`: over runs whose `RunMeta.mode == "live"` only (an offline run's computed cost is not money: Plan A record contract), sum of `settled_usd`, plus `reserved_usd` for `cost_status == "unknown"`
  - `cap_for(config_id: str, runs: Runs) -> Decimal`: `max(Decimal(0), usable − account_spend)` for the config's account
  - `class AccountExhausted(RuntimeError)` (named apart from O5's per-run `BudgetExhausted` error class); `require_budget(config_id, runs, needed: Decimal) -> Decimal` raises when `cap_for < needed`

- [ ] **Step 1: Write the failing tests**

```python
def test_spend_sums_settled_and_unknown():  # openai: settled 10.50 + unknown reserved 3.25 + anthropic 9.00
    assert account_spend(rs, "openai") == Decimal("13.75")
def test_shared_account():                  # sol-medium and sol-high both draw on openai
    assert cap_for("sol-high", rs) == Decimal("117.00") - Decimal("13.75")
def test_cap_floor_zero():                  # openrouter spend 18.40
    assert cap_for("deepseek-max", rs) == Decimal(0)
def test_require_budget_raises():
    with pytest.raises(AccountExhausted, match="deepseek-max"): require_budget("deepseek-max", rs, Decimal("0.01"))
def test_offline_runs_not_counted():        # an offline run with computed 50.00 adds nothing to openai
    assert account_spend(rs + [offline_run], "openai") == Decimal("13.75")
```

- [ ] **Step 2: Run, expect FAIL** · **Step 3: Implement** · **Step 4: Run tests and gates, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): account spend and caps`

---

### Task 4: Golden case loader

**Files:**
- Create: `src/deploy_workflow/model_testing/cases.py`
- Test: `tests/test_model_testing_cases.py`

**Interfaces:**
- Consumes: `CASES` (Task 1); `cases/goldens/check.py` (`check_case(case_dir, corpus)` :724, `normalise` :161, `SCALE_EXP` :60); `deploy_workflow.context.load_context(raw: bytes)` (`context.py:315`, raises `ContextRefused`); `deploy_vii.contracts.PATHWAY_MODULES`
- Produces:
  - `@dataclass(frozen=True) class GoldenCase: case_id: str; pathway: PathwayId; case_dir: Path; context_path: Path; golden: Mapping[str, Any]; facts: Mapping[str, Mapping[str, Any]]` (by `fact_id`, only facts whose `module` is in `PATHWAY_MODULES[pathway]`)`; out_of_plan: Mapping[str, int]` (module → count of golden facts for modules the pathway's plan does not run; never scored, shown in the report)`; financial_gold_path: Path; financial_gold_sha256: str`
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
def test_refuses_context_the_product_refuses(tmp_path):  # N2: copy a case, set context issuer_id "-tdg"
    with pytest.raises(CaseError, match="context.json"): load_case(case, CORPUS)  # check.py's SLUG accepts it, load_context does not
def test_natl_cp4_out_of_plan():                    # W1: portfolio_decision does not run CP-4
    c = load_case(Path("cases/goldens/natl-portfolio-decision"), CORPUS)
    assert c.out_of_plan == {"CP-4": 51} and not any(f["module"] == "CP-4" for f in c.facts.values())
```

W1 ruling (controller, 2026-11-01): NATL's 51 CP-4 facts are treated as not golden by the loader, not deleted from the approved golden. Measured on the merged tip, NATL is the only case with facts outside its plan. Keeping them costs nothing and keeps them ready if `requested_modules` is ever ruled to add CP-4 for that case; deleting them would reopen an approved golden.

`CORPUS = Path("/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1")`; tests needing it are skipped with a reason when it is absent (the corpus is gitignored).

- [ ] **Step 2: Run, expect FAIL** · **Step 3: Implement** (`check_case` findings non-empty → `CaseError` listing the first five; then `load_context(context_path.read_bytes())`, `ContextRefused` → `CaseError` naming `context.json` and its problems, so a context `check.py` accepts but the product refuses (its `SLUG` differs from `context.py:37`) fails here, not mid-run) · **Step 4: Run, expect PASS**
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
  - `class Mapping(Contract)`: `schema_version: Literal["golden-mapping/1"]`, `case_id: str`, `preparer: str`, `reviewer: str`, `module_commits: dict[str, str]` (module id → the 40-hex commit of the module code the mapping was made against; W3), `entries: tuple[MappingEntry, ...]`, `unmapped: tuple[Unmapped, ...]`
  - `Mapping.pending(case) -> frozenset[str]`: fact_ids of golden facts whose module has no `module_commits` entry yet (Task 6 maps one module at a time; the scorer reports these `unmapped` with reason "module not yet mapped")
  - `class MappingError(ValueError)`; `load_mapping(path: Path, case: GoldenCase) -> Mapping`

- [ ] **Step 1: Write the failing tests**

```python
def test_every_fact_accounted_once(tmp_path):   # a fact in entries and unmapped
    with pytest.raises(MappingError, match="once"): load_mapping(p, case)
def test_mapped_module_fully_accounted(tmp_path):  # CP-1 in module_commits, one CP-1 fact in neither list
    with pytest.raises(MappingError, match="CP-1"): load_mapping(p, case)
def test_entry_module_needs_commit(tmp_path):   # entry for CP-2, no "CP-2" in module_commits
    with pytest.raises(MappingError, match="module_commits"): load_mapping(p, case)
def test_commit_is_full_sha(tmp_path):          # "abc123" refused
def test_pending_lists_unmapped_modules(tmp_path):  # only CP-0 mapped → pending = every other module's fact_ids
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

**When (W3, deferred 2026-11-01):** context-plan Phases 2–8 and O1 still change module `table_id`/`row_id`/`field` layouts (Plan A R7: each phase report lists its layout changes). A module is mapped only after the phase that changes it is merged, so this stage runs once per landed phase, mapping the modules that phase changed across every case in one batch. Each run writes the module's commit (`git log -1 --format=%H -- <module's owner core and binding files>` at the merged tip) into `module_commits`; a later layout change to that module reopens its entries (the report diff of R7 names them). Until a module is mapped its facts are `pending` (Task 5), not failures.

**Files:**
- Create: `work/model-testing/mapping/CONTEXT.md` (stage contract), `work/model-testing/mapping/briefs/<case>.md`, `cases/goldens/<case>/mapping.json` × 6
- Test: Task 5's `load_mapping` on all six

**Stage contract inputs:** the case's `module_golden.json`; the module's owner core and its `methodology.json` table ids (which `table_id`/`row_id`/`field` each module writes); the module's synthetic owner oracle `cases/<module>-owner/expected.json` and the replay in `tests/*_runs.py` for real result layouts; Task 5's contract.

**Rules:** one entry per golden fact the module writes; a golden fact no module output can hold goes to `unmapped` with the reason (never guessed); `depends_on` lists golden operands from upstream modules; subject aliases only for names the module would print differently (e.g. "Term Loan B" vs "Term B Loans").

- [ ] **Step 1:** Controller writes `CONTEXT.md` once, and per landed phase one brief naming the modules it changed and their commits (no code).
- [ ] **Step 2:** One preparer dispatch (`mx-feature`) per landed phase, covering those modules in every case; it runs `load_mapping` on each case and reports exit 0.
- [ ] **Step 3:** One review (`mx-precise`) per batch, sampling ≥ 30 entries per mapped module and case against the module code at its recorded commit; one fix round if a High/Medium finding.
- [ ] **Step 4:** Test `test_all_mappings_load` in `tests/test_model_testing_mapping.py`: every case in `CASES` loads, and for each mapped module `unmapped` ≤ 20% of its known facts (else the stage reports why).
- [ ] **Step 5: Commit** per batch `goldens: mapping tables (<modules>)`

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
  - `class ModuleScore(Contract)`: `module_id`, `head_status: Literal["accepted", "restricted", "blocked", "refused", "absent"]`, `facts: tuple[FactScore, ...]`, `untraced: tuple[str, ...]` (module fact ids), `unscored: int`, `judgment: bool`, `passed: bool`
  - `JUDGMENT_MODULES = frozenset({"CP-5", "CP-6", "CP-MODEL", "CP-2A"})`
  - `score_module(module: Module | None, module_id: str, head_status: str, case: GoldenCase, mapping: Mapping, upstream_mismatches: frozenset[str], refusal_missing: tuple[str, ...] = ()) -> ModuleScore` (`refusal_missing`: the inputs a recorded refused `begin` names, W9)

**Rules (spec §7.4, §9a, §10.3):**
- Numeric: compare in units. Golden units = `Decimal(value).scaleb(SCALE_EXP[scale])`; module units = `amount × fact.scale` (Step 3 confirms this against `deploy_vii/display.py`); percent and bps compare as stored. Exact equality, except when the golden has fewer decimal places: quantise the module value half-up to the golden's places first.
- Text: `normalise(x).casefold()` equal, or equal to a `subject_aliases` entry.
- Golden `missing`: `gap_ok` when the module fact is absent or not `known`; `invented` when it carries a value.
- Golden `conflicting`: `conflict_ok` when the module fact is `conflicting`, or known with one of the evidenced values and a limitation; else `mismatch`.
- `inherited`: a `mismatch` whose entry `depends_on` intersects `upstream_mismatches`; excluded from `passed`.
- Provenance: every `known` module fact with an `amount` needs `citations` or `calculation_id`; others go to `untraced` and fail the module.
- Honest gap: `head_status` blocked/restricted, or every mapped fact non-known, passes only when the module carries a limitation (`Module.limitations`, `contracts.py:310`; limitations are module-level) and nothing is invented or untraced.
- Recorded refusal (W9): `head_status == "refused"` with a non-empty `refusal_missing` scores every mapped golden fact `gap_ok` (`observed` = `"refused: " + ", ".join(refusal_missing)`) and passes: the module honestly named what it lacked and invented nothing. A refusal naming no input, and `absent`, score each mapped known fact `missing_in_output` and fail.
- Pending module facts (`mapping.pending(case)`, Task 5) score `unmapped`, never `missing_in_output`.
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
def test_refusal_naming_input_is_honest_gap():  # head "refused", refusal_missing ("portfolio_workbook",) → gap_ok, passed True
def test_refusal_naming_nothing_fails():        # head "refused", refusal_missing () → missing_in_output, passed False
def test_pending_module_scored_unmapped():
```

- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement.** First read `deploy_vii/display.py` scale handling and pin the units rule with `test_thousands_vs_scale_match`; if `scale` means something else, stop and report BLOCKED with the evidence.
- [ ] **Step 4: Run tests and gates, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): module scorer`

---

### Task 8: Pathway score from a run directory

**Run directory contract** (O2, merged; Plan A "Interface contracts"): `sources/`, `pack/`, `execution/` (the `Execution` store), `owner-run.json` (`OwnerRunReceipt`, `owner_workflow.py:696`), `publication/` (or absent), `delivery/` (rendered slice), `calls.jsonl`, `raw/`, `run.json` (Task 2 `RunMeta`). A stopped run has `sources/`, `pack/` (when prepared), `execution/`, `calls.jsonl`, `raw/` and `run.json` only. The framework reads these and writes none of them (C4).

**Files:**
- Create: `src/deploy_workflow/model_testing/pathway.py`
- Test: `tests/test_model_testing_pathway.py`

**Interfaces:**
- Consumes: Tasks 2 (`read_run`), 4, 5, 7; `deploy_workflow.owner_workflow.OwnerRunReceipt`, `verify_owner_run_receipt(store, receipt, *, publication_directory)` (:2501); `deploy_workflow.owner_rendering.verify_owner_rendered_slice(execution_directory, receipt_path, publication_directory, delivery_directory)` (:939); `deploy_vii.execution.Execution.result(sha256)` (:623); `deploy_vii.contracts.PATHWAY_MODULES`
- Produces:
  - `class PathwayScore(Contract)`: `run_id`, `case_id`, `pathway`, `config_id`, `mode: Literal["offline", "live"]`, `outcome: Literal["settled", "stopped"]`, `stopped_reason: str | None`, `ruling_sha256: str | None`, `modules: tuple[ModuleScore, ...]` (plan order), `rendered: bool`, `passed: bool` (run identity, `mode`, `outcome`, `stopped_reason` and the ruling field are copied from `run.json`, never inferred)
  - `score_run(run_dir: Path, case: GoldenCase, mapping: Mapping) -> PathwayScore`

**Rules:** `read_run(run_dir)` first; `run.json`'s `case_id` and `pathway` must equal the `GoldenCase`'s (else `CaseError`). With `owner-run.json`: walk `receipt.plan` in order; each module's result is `Execution.result(head.result_sha256)` for its settled head; a module with a `receipt.refusals` entry and no head → `refused` (`refusal_missing=()` until O3 adds the named missing inputs to the recorded refusal, Plan A O3; Task 11 wires them through an optional `refusals` argument once O3 is merged); otherwise no head → `absent`. `upstream_mismatches` accumulates mismatched fact_ids of earlier modules; `rendered` = receipt verifies and `verify_owner_rendered_slice` raises nothing; `passed` = `outcome == "settled"`, every module passed and `rendered`. Without `owner-run.json` (a stopped run, C4): the module list is `PATHWAY_MODULES[pathway]`, each module scored `absent`, `rendered` false, `passed` false.

- [ ] **Step 1: Write the failing tests** on real run directories written by O2's offline path: `tests/o2_case.py` (`author` then `replay`, the O2 synthetic `portfolio_decision` case through `_run_pathway` with O5's recorded adapter), with a `GoldenCase` and `Mapping` built in the test for that synthetic case: `test_scores_plan_order`, `test_retry_uses_settled_head_only` (two attempts in the store, one head), `test_tampered_delivery_not_rendered` (flip a byte in `delivery/report.html` → `rendered False`, `passed False`), `test_absent_module_fails`, `test_reads_outcome_and_mode_from_run_json` (fields copied; offline run has `ruling_sha256` None), `test_stopped_run_without_receipt` (replay with a recordings file missing one call → `RecordingMissing` stops the run; no `owner-run.json`; every `PATHWAY_MODULES["portfolio_decision"]` module `absent`, `rendered` False, `passed` False), `test_case_mismatch_refused`. If one replay takes over the fast-test budget, the brief records the slow tests as deferred to CI (`gates-first-pass=n/a`).
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
- Consumes: `PathwayScore` (8), `RunMeta`, `CallRecord` (2), `FaultRecord` (9), `account_spend`, `ACCOUNTS` (3, 1)
- Produces: `render_report(scores: Sequence[PathwayScore], runs: Sequence[tuple[RunMeta, Sequence[CallRecord]]], faults: Sequence[FaultRecord]) -> str` (`runs` as `read_run` returns them, so the account section counts live runs only, Task 3)

**Layout (spec §7.8):** per pathway, a table: rows modules in plan order, columns configs; cell `PASS 41/41 · $1.23 · 18.4k tok · 52 s` or `FAIL 37/41 (2 inherited)`. Then a totals table per config (accuracy = matched / scored known facts, inherited excluded; cost; tokens; median wall time; retries, W8: a record counts as a retry when it is the first call (lowest `call_index`) of `attempt == 1`, or when the record with the same `(run_id, module_id, step_id, attempt)` and `call_index − 1` has `error_class` set; ordinary tool-loop turns, whose predecessor succeeded, are not retries). A stopped run's cell shows `STOPPED (<stopped_reason>)`. When any run is `mode: offline` the report opens with one line saying its costs are computed from recordings, not money. Then faults by class. Then spend vs usable cap per account. Costs from records, `Decimal` quantised to cents half-up; tokens with `None` shown as `n/r`, never 0.

- [ ] **Step 1: Write the failing test** `test_report_matches_fixture`: two configs × one pathway fixture → byte-equal to `report_expected.md` (the controller reviews the fixture as the spec of the layout); `test_unknown_cost_flagged` (an unknown-cost call shows `reserved` beside the total); `test_retries_from_call_index_and_error_class` (W8: step with calls 0 ok, 1 ok, 2 error, 3 ok, plus attempt 1 call 0 → 2 retries); `test_offline_runs_not_charged` (offline run's computed cost absent from the account section).
- [ ] **Step 2: Run, expect FAIL** · **Step 3: Implement** · **Step 4: Run, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): comparison report`

---

### Task 11: Run driver (starts after context plan Part B O3, O4 and O6 are merged; O2 and O5 already are; W4)

**Files:**
- Create: `src/deploy_workflow/model_testing/run.py`, `src/deploy_workflow/model_testing/__main__.py`
- Test: `tests/test_model_testing_run.py`

**Interfaces:**
- Consumes: everything above; O2 `run_pathway(*, case_id, sources: Sequence[CaseSource], context: Path, pathway, model: ModelSpec, adapter: ModelAdapter, cap_usd: Decimal, run_dir: Path, run_id: str, cp_dr: bool = False) -> RunOutcome` (`run_pathway.py:378`; `CaseSource`, `RunOutcome` in `run_inputs.py:106-121`); O5 `ModelSpec` (`model/turn.py:110`), `recorded_adapter(model, recordings)` (`model/adapter.py:295`), `live_adapter(model, ruling)` (:447). The brief re-reads these at the merged tip of O3/O4/O6 and records any change.
- Produces:
  - `plan_runs(stage: Literal["pilot", "repair", "comparison"]) -> tuple[tuple[str, PathwayId, str], ...]` (case_id, pathway, config_id): pilot = `PILOT_PATHWAY` × four configs; repair = six pathways × repair configs; comparison = six pathways × `sol-high` plus `OPUS_PATHWAYS` × `opus-medium`
  - `main(argv) -> int`: `python -m deploy_workflow.model_testing {pilot|repair|comparison|score|report} [--live --ruling docs/rulings/<file>.md] --out artifacts/model-testing/<run_id>/`

**Rules (C4):** per planned run, build `ModelSpec(config_id, provider, model, effort)` from Task 1's `ModelConfig`, the case's `CaseSource` list from `module_golden.json` `sources` and the corpus, and call `run_pathway` with a fresh `run_dir` under `--out` and a new `run_id`; the framework never writes or edits `run.json` and scores with `score_run` (Task 8). Offline by default (`recorded_adapter`). **Live (C2):** `--live --ruling <path>` passes the ruling to `live_adapter(model, ruling)`, which owns the gate (R2: the `lifts`/`by`/`date`/`configs` lines) and raises `LivePauseInForce`; the driver's own check (the file exists under `docs/rulings/`) is a pre-check for a clear CLI message only, never the gate. `run_pathway` records the ruling's path, sha256 and date in `run.json`. **Refusals (W9):** once O3 is merged, the driver reads each refused module's named missing inputs from O3's interface (Plan A O3: recorded with the refusal and readable through `state()`; the brief records the exact field or call at the merged tip) and passes them to `score_run`, which forwards them to `score_module(refusal_missing=…)` (Task 8 gains an optional `refusals: Mapping[str, tuple[str, ...]]` argument, default empty, in this task). Before each run, `require_budget` with the config's estimated cost from the pilot (or the spec §7.2 estimate before the pilot); an `AccountExhausted` stops that config and the report says so. `distressed_restructuring` on `opus-medium` runs only when `cap_for("opus-medium", …)` ≥ its measured estimate after the five Opus pathways.

- [ ] **Step 1: Write the failing tests:** `test_plan_counts` (pilot 4, repair 12, comparison 11), `test_live_refused_without_ruling`, `test_live_ruling_reaches_live_adapter` (a ruling file that passes the pre-check but lacks R2's lines → `LivePauseInForce` from O5, and no run directory exists), `test_driver_never_writes_run_json` (only `run_pathway` creates it), `test_refusal_names_reach_scorer` (a run with a refused module whose O3 record names an input → that module `refused`, its mapped facts `gap_ok`, passed True), `test_budget_exhausted_skips_config`, `test_offline_pilot_scores` (the offline pilot on the recorded adapter writes four run dirs, each scored, and one report).
- [ ] **Step 2: Run, expect FAIL** · **Step 3: Implement** · **Step 4: Run tests and gates, expect PASS**
- [ ] **Step 5: Commit** `feat(model-testing): run driver`

---

## After the plan

- The first live call (the pilot) happens only after the user's lifting ruling, with the prerequisites in spec §6 met.
- Re-estimate the budget from the pilot's records (Task 3 sums) before the repair pass.
- Whole-branch review per global rules (`mx-architect`; `confidence-review` and `rewrite-tournament` once on the branch diff).
