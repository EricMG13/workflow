# T5 root-cause plan (mx-autonomous a14a5b86; written by the controller from the planner's text report)

Line numbers are from af9ceea1. The probes are in `work/build/keep/s8-t5/root-cause/`: `rc_fix.py` (`proposed_invoke`), `rc1_*`, `rc2_source_tools_pins.py` and `rc3_owner_replay.py`.

1. **Root cause.** `invoke` validates the arguments before it asks whether the tool is offered. `SourceTools.stage` (`tools/source.py:38-39`) checks in the opposite order: offered first, then arguments. Replay re-runs `invoke(name, {})` (`financial_workflow.py:1131`, `owner_workflow.py:~2325`, earnings `:2181`), so a refused-arguments receipt must carry the code `stage(name, {})` would give.
   - Record `""` and `{}` for a name that cannot be represented (not an exact `str`, or not UTF-8 encodable).
   - Record the name and `{}` for arguments the host refused. The code is `not_permitted` if the session does not offer the name, and `bad_arguments` if it does.
   - Record the name and the copied arguments for everything after the arguments are accepted.
2. **Fix, in `SourceSession.invoke`.** The check order is: sequence, name, arguments, lock, `_assert_current`, stage.
   - **a. Name.**
     - Old (`:1066-1073`): `name = ""` and so on, then `if not name and tool_name != "": return …not_permitted`.
     - New: `if type(tool_name) is not str:` return `("", {}, refused, not_permitted)`. Then `tool_name.encode("utf-8")` inside `try/except UnicodeEncodeError`, returning the same receipt. Then `name = tool_name`.
     - No caller-object `==` or `!=` runs, which fixes the p9 (a) and p10 Lows.
   - **b. Arguments.**
     - Old (`:1076-1077`): the `bad_arguments` refusal.
     - New: `code = "bad_arguments" if self._tools.offers(name) else "not_permitted"`, then return `(name, {}, refused, code)`.
     - Add a one-line public `SourceTools.offers(name: str) -> bool` in `tools/source.py`, which the controller allows as a second file, in place of reaching into the private `_names`.
   - **c.** Do not move the "offered" check before the arguments check: that would change `test_source_tools.py:1475` (`stale_binding`).
   - **d.** The p9 (b) lock-path Low goes to the owner list, not here.
3. **RED tests (`tests/test_host_frames.py`).** Follow the pattern of `test_surrogate_tool_run_can_still_be_sealed_and_verified`.
   - Parametrise names {`"search_pack"`, `""`, `"foo"`, `"extract_statements"`} × refusals {deep(105) arguments, `{"query": "\ud800"}`, `[1]`, an unencodable name (name + `"\ud800"` with `{"query": "x"}`)}.
   - Expected replies:
     - `search_pack` × an argument refusal gives `(search_pack, {}, refused, bad_arguments)`;
     - the other names × an argument refusal give `(name, {}, refused, not_permitted)`;
     - the unencodable column gives `("", {}, refused, not_permitted)`.
   - Every case must seal and verify (the financial gap run).
   - Add two python-api cases, each with deep(105) arguments. Each expects `("", {}, not_permitted)`, nothing escaping, and the run sealing:
     - a `Hostile` name whose `__ne__` and `__eq__` raise;
     - p10's `LooksEmpty`.
   - Expected results: today 12 cells fail and `Hostile` escapes (`rc1_current.out`); with the change 44/44 (`rc1_proposed.out`); owner replay 9 FAIL now and 0 with the change (`rc3`).
4. **Existing pins.**
   - `tests/test_source_tools.py:514-526` (`test_deep_json_arguments_cannot_escape_sanitized_refusal`) already fails at af9ceea1, because cd85de8c made it `bad_arguments` with `{}`. With the change it gives `not_permitted` with `{}`, so `:526` becomes `result["arguments"] == {}`.
   - `:1474`, `invoke("shell", {"x": nan})`, pins `bad_arguments` and becomes `not_permitted`.
   - Unaffected: `:670` (either code), `:1475`, `:1563-1571`, `test_host_frames.py:111-131`.

Not verified (planner): no pytest; the earnings replay; `extract_statements` inside `financials` with bad arguments; ruff and mypy on the change.
