# Legal oracle move preparer report (mx-feature a2f57624, claude/s3-legal 9ac76c6)

Legal oracle move done: one commit, with one brief item (maturity-wall kind) not moved because the rendered value does not change.

Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a2f57624b0b7195e0
Branch `claude/s3-legal`, cut from c43b681 (tip confirmed). Tip: 9ac76c6, with the Co-Authored-By line.

**Moved values** (`cases/legal/render-expected.json`, `other_front_sections.blocks.funding-gap`, hand-edited because no generator exists in `cases/legal/` or `cases/*/builder/`):
- `producers`: `["CP-2D"]` becomes `["CP-2D","CP-3C"]`. Source: ruling item 6.1 and item 13, and `cases/charts/cr3-expected.json` at `render.covenant_refinancing.producers`.
- `note`: "Not run: CP-2D was not requested in this run." becomes "Not run: CP-2D · CP-3C was not requested in this run."
  - No ruling or oracle gives this literal. Ruling item 13 only says the note changes.
  - I took the text from the code's existing producer-join format (" · "), the same text the test workaround builds. Confirm it in review.

**Not moved: `maturity-wall` kind = `chart`.**
- The spec row is now `chart` (`src/deploy_vii/report_view.py:1240`), but the rendered not-run block still has `block.kind == "dense"`. The oracle's `kind` is compared against `block.kind`, so moving it would make the test fail.
- `cases/charts/s4fp04-expected.json` (the legal-render regression item, and the adversarial case) pins that the FP04 fixture keeps owner MODEL and the empty state "Not run: CP-1 has not run." with no figure.
- The oracle holds no spec-kind field. If you want one added, that needs a ruling.

**Figures on populated blocks:** none to move. I found no value in this oracle that the integrated code renders differently beyond funding-gap. Fixture rows and `covenant-tests-headroom` are unchanged, and the test is green with no other edits.

**`cases/PINS.json`:** regenerated with `python3 -I cases/pins.py` (86 paths). The file did not change, so `render-expected.json` is not among the pinned paths.

**Builder targets** for `tests/test_legal_render.py`:
1. Delete `_producers_after_stage3` and `_note_after_stage3` (lines 369-387, both marked `# Stage 3 item 13`).
2. Line 358: change the assertion to `assert report_view._spec_of(block_id).producers == tuple(want["producers"])`.
3. Line 365: change the assertion to `assert block.note == want["note"]`.
4. Drop imports used only by the helpers. `json` and `ROOT` are probably still used elsewhere, so check.

**Gates:**
- `python3 -I cases/pins.py --check`: exit 0.
- Generator double rebuild: not applicable, no generator.
- `PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_legal_render.py`: 77 passed. This is with the moved oracle and the old workaround still in place. The workaround becomes a no-op because the producers now agree.

Not verified: the test after the builder reverts the workaround (targets 1-3); the exact note literal against any ruling (none exists); the full suite or any test beyond `tests/test_legal_render.py`; the `responsibility_context_only` prose, which I left unchanged.
