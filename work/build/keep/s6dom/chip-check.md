# DR.6 "Not computable" chip: native DOM check (2026-10-30 21:51)

- **Pages:** regenerated on `../s5-final2` (310a49c) with `tests/test_owner_rendering.py` G2 genuine deferred cp2h (positive and gap): 2 passed in 38m11s, exit 0 (`regen.log`).
- **How:** the built-in Chromium at 1440x900, served by `python3 -m http.server` on 127.0.0.1:8765. On each page a real mouse click on the Front Page rail link, then an in-page script.
- **Where the chip lives:** the page data has exactly one `status_chip` (`report.blocks[10].figures[0]`: DR.6, "Not computable"). That is block `rating-triggers`, drawn on the Front Page by `renderBlock` (`src/deploy_vii/assets/app.js:421`). The CP-2H module page draws no chip. That is expected, since the chip belongs to the block head.

| Page | Chips in `#block-rating-triggers` head | "Not computable" chips elsewhere | Hit test at the chip's centre | Screenshot |
|---|---|---|---|---|
| cp2h-fp05-ratings positive | 1: `chip st-na` "Not computable", visible, beside the DR.6 note | 0 | the chip itself | `positive-chip.png` |
| cp2h-fp05-ratings gap | 1: `chip st-na` "Not computable", visible | 0 | the chip itself | `gap-chip.png` |

Result: pass on both pages.

Not verified:
- Other browsers and viewports.
- No automated test reads the drawn chip. The G2 `_figure_equals` does not compare `status_chip`.
