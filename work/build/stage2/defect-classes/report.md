# Shared defect-class test report (mx-feature)

Commit 6e89f6e on claude/s2-defect-classes (cut at 386f53a, tree was clean). Changed files: `tests/defect_classes.py`, `tests/test_defect_classes_selfcheck.py`, and new `tests/test_defect_classes_shared.py`. Nothing in `src`, `cases/` or any module test was touched.

**Helper API** (`import defect_classes as dc`):
- `HOSTILE_JSON: Mapping[str, str]` holds the 8 inputs copied from LEAD's probe.
- `hostile_inputs(schema: type[BaseModel]) -> dict[str, str]` adds, for the first 5 string fields, a `{`-flood and a `{a|b}`-flood.
- `hostile_failures(schema: type[BaseModel]) -> list[str]` returns `"<label>: <ExcClass>"` for every input that raises something other than a `ValueError` subclass.
- `MODEL_TEXT_HOSTILE = ("Rates matter [a lot", "{low", "{}")`.
- `free_text_paths(payload: Any, schema: type[BaseModel]) -> list[tuple[str | int, ...]]`. The payload may be parsed JSON or its text.
  - It walks `schema.model_json_schema()`, so it hard-codes no field names.
  - A free-text field is a string with no pattern, enum, const or format.
- `with_text(payload, path, value) -> Any` returns a deep copy with the string at `path` replaced.
- `class ReviewRun(Protocol)` has `submit_review(payload: str) -> Mapping[str, Any]`, returning an outcome with `status` and `issues`.
- `model_text_failures(schema: type[BaseModel], positive: str, fresh: Callable[[], ReviewRun], *, values=MODEL_TEXT_HOSTILE, require_issue: bool = True) -> list[str]`.
  - For each path and value it builds a `fresh()` run and submits the mutated payload.
  - It asserts no raise, an outcome that is not `valid` and lists an issue, and that a following submit of `positive` is `valid` (no wedge on `stale_binding`).
  - `fresh()` must return a run whose `submit_review` does the module's reads first. A refused attempt re-activates the step on a new binding, so reads are needed again (see `_Cp0Run` and `_Cp1ContextRun` in the shared test).
  - `require_issue=False` is for fields a module legitimately takes verbatim. A `valid` outcome is then skipped, but raise and wedge are still checked.

A module's `test_connect_<cp>` calls `dc.hostile_failures(schema) == []` over its `SCHEMAS`, and `dc.model_text_failures(...) == []` with its own `fresh`.

**Coverage now**
- Q5 hostile text: every `OWNER_SPECS` step schema plus every `owners/*.SCHEMAS` row. That is CP-0, CP-1 (5 steps), CP-1A, CP-2 and `cpl10`. All raise only `ValueError`.
- Model text on a real `OwnerWorkflow` over a real `Execution`, with no fakes:
  - CP-0 `source_readiness`: 54 free-text paths. No raise and no wedge.
  - CP-1 `source_context`: forked from a settled CP-0 with `clone_workflow`. No raise and no wedge.
- No module is registered in `_CORES` at 386f53a, so no owner core exists to cover yet.
- CP-1A and CP-2 are not run through the store. They sit behind CP-1's financial stages, which take 11 to 26 minutes.

**Findings**
- No registered module raises or wedges.
- CP-0 accepts the three hostile strings as `valid` in 25 of its 54 free-text paths, for example `objective`. So its test runs with `require_issue=False`. If LEAD wants CP-0 to journal an issue there, that is a CP-0 change and I did not make it. To reproduce, set `require_issue=True` in `test_cp0_model_text_never_raises_or_wedges_the_run`; 75 "accepted" results come back.

**Selfcheck** (`tests/test_defect_classes_selfcheck.py`):
- `hostile_failures` is shown to catch a `TypeError` schema and a `RecursionError` schema.
- `model_text_failures` is shown to catch:
  - a validator that lets `"Rates matter [a lot"` through to a `RunText` build, which raises `ValidationError` and then wedges the next submit;
  - an outcome with no issue;
  - an accepted hostile value;
  - a wedge after a clean refusal.
- `free_text_paths` and `with_text` have their own tests.

**Gates**
- pytest on the selfcheck file: 236 passed in 0.4 s.
- pytest on the new shared file: 12 passed in 43 to 59 s, which varies with load.
- Both files together: exit 0.
- `ruff check`, `ruff format --check` and `MYPYPATH=src:tests mypy --strict` on the three files: all exit 0.
- Three `# noqa: BLE001` suppressions were added, each at an `except Exception` that only names the exception class. Any suppression-count baseline moves by 3.

Not verified: CP-1A and CP-2 model text through the store (slow driver); CP-1 steps after `source_context`; owner-core modules via a module's own `submit` seam (none registered, so the helper is untested against a real core); the mutated-payload `follow-up valid` check against any module that re-activates a step with different reads; the shared file's runtime budget under heavy load.

agent=mx-feature fix-rounds=0 gates-first-pass=n
