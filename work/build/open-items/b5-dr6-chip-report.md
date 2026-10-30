# B5 report: DR.6 "Not computable" chip (OI-13)

Branch claude/oi-b5-dr6-chip, based on 9661c9d.

Commits:
- 2eba590 RED: tripwire marker removed, per-case (positive, gap) and negative cases.
- 2d12ea5 fix: `Figure.status_chip` (report_view.py), `DR6_CHIP` set in `rating_trigger_figures` (distressed_figures.py), `renderBlock` appends `chip("na", ...)` after the state chip (app.js).
- manifest commit: two `post_import_patches` records (report_view.py, app.js), project_commit 2d12ea5. distressed_figures.py is not a reused file, so it has no record.

Field on `Figure`: the producer already returns `Figure` and sets `reason` beside it; `Block` is not touched.

Dumps moved: none. Greps of `model_dump` and `render-expected` find only `View`/module dumps; no test or oracle compares a full `Figure` or `Block` dump. No `cases/**` file changed.

Not verified: tests, gates, native DOM check, genuine deferred cp2h cases (controller runs these).
