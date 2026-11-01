# L: end-of-branch Low batch (stage contract; mx-scaffold)

Rules: `W/work/build/stage8-vii/common.md` (read first), except: step 0 is `git checkout -b claude/s8-vii-lows 2c43a6c5` (the integration tip after all three merges). One commit `style: stage 8-vii Low batch`. Mechanical edits only; no behaviour change. Edit only the files below.

1. `tests/test_report_view_tl10_4.py`: inside the loop, after the `"{" not in` assert, add `assert impact[key] == "A move of 3.75 US$ m reaches the credit view."` (controller confirmed this exact string for both `display` and `table_display`). Keep the other asserts.
2. `tests/test_source_context_blank.py`: replace each literal U+200B character inside a string (two places, in the H09 tests near :141-166) with the escape `​` (ruff PLE2515). Find them with `grep -n $'​'`.
3. Rewrap to the file's 100-column wrap, words unchanged:
   - `src/deploy_vii/report_view.py` the comment block above `_RUN_TEXT_FIELDS` (the line starting `#: :1413-1424). CP-L10's TL10.4` is 159 columns); keep the `#: ` prefix on every line.
   - `src/deploy_vii/source_context.py` the `_lacks` docstring line (~:355, 116 columns) and the `_disagreements` docstring line (~:369, 101 columns).
4. `tests/test_cash_scope.py`: two spots so `ruff format --check` passes: wrap `MISSING_2024 = "..."` as `MISSING_2024 = (\n    "..."\n)`; put `def scope_of(items: tuple[Item, ...] = BOTH, citations: tuple[Citation, ...] = ()) -> CashScope:` on one line (it fits in 100 columns).

Report as text (under 200 tokens): SHA, files touched, `Not verified:`.
