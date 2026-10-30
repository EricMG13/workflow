# Stage 5.2: native DOM proof (2026-10-30)

## How it was run
- **Browser:** the built-in browser (Chromium) opened each delivered `report.html` from its own delivery folder, so calculation.json and the model files sat beside it. A local static server (`python3 -m http.server`, 127.0.0.1:8765) served the deliveries.
- **Checker** (`work/build/keep/s52/check.js`): evaluated in the page, with expectations from `work/build/keep/s52/expect.py`. The expectations come from each delivery's own `owner-run.json`; words and titles come from the CP-OS oracle's status and registry tables. On every page the checker:
  - clicks each navigator row (numbered and footer) and reads the h1, the module's own status chip and the empty state;
  - checks numbering against the run's plan in registry order;
  - clicks the six rail destinations;
  - clicks each drawn Front Page block link;
  - resolves every other `#` link and checks the skip-link focus;
  - checks the delivery-scope banner;
  - checks the calculation.json link on the Model destination (CP-1 page).
- **The S1a positive run** is also compared with the CP-OS oracle case `s1a_positive`: rows, destinations, and drawn block links as a subset of the oracle (rule `hash_links_not_derivable_without_a_real_store`).
- **Pointer hit test:** run at 1440x900. From every route visited, each numbered row's centre must hit-test to the row itself.
- **Probes:**
  - A perturbation probe (wrong head word, wrong title, wrong issuer) was caught 3/3.
  - Real mouse clicks were made with the browser's pointer.
- **Slow pages:** the CP-2G and CP-8 refused pages take about 2 s per route, so they were run in parts (localStorage `phase`).

## Deliveries checked (code `claude/s4-int3` 5cf7f0c, shards d0/d1)
| Delivery (scope) | Rows | Rails | Block links | `#` links | calculation.json | Result |
|---|---|---|---|---|---|---|
| s1a-credit-snapshot positive | 25 | 6 | 7 | 31 | drawn, opened by mouse, sha matches receipt | pass, also against the oracle |
| cp3-fp01-relative-value positive | 25 | 6 | 8 | 31 | drawn | pass |
| cp1c-fp03-peers positive | 25 | 6 | 2 | 31 | none (no Model) | pass |
| cp3d-fp03-market positive | 25 | 6 | 1 | 31 | none | pass |
| cp1d-fp02-quality positive | 25 | 6 | 4 | 31 | none | pass |
| cp2a-fp05-downside positive | 25 | 6 | 2 | 31 | none | pass |
| cp2g-fp05-forward positive | 25 | 6 | 4 | 31 | none | pass |
| cp2g-fp05-forward-gap gap | 25 | 6 | 4 | 31 | none | pass |
| cp8-fp01-what-changed no_record (refused) | 25 | 6 | 0 | 31 | none | pass |
| cp2h-fp05-ratings positive | 25 | 6 | 5 | 31 | none | pass |
| cp4c-fp05-recovery positive | 25 | 6 | 6 | 31 | none | pass |
| cp3c-fp04-refinancing positive | 25 | 6 | 5 | 31 | none | pass |
| cp4-fp04-covenants positive | 25 | 6 | 7 | 31 | none | pass |
| cp8-fp01-what-changed positive | 25 | 6 | 1 | 31 | none | pass |
| slice-cp2e-sensitivity positive | 25 | 6 | 0 | 31 | none | pass |
| slice-cpdr-research partial | 25 | 6 | 0 | 31 | none | pass |
| slice-cpl10-screen positive | 25 | 6 | 3 | 31 | none | pass |
| cp1-model (owner slice) | 25 | 6 | 3 | 31 | drawn | pass |
| historical-financials (CP-1/Model slice page) | 25 | 6 | 3 | 31 | drawn | pass |

"Pass" means every check above, except the pointer hit test. The hit test failed on every page whose module pages carry a long outline, which is the defect below.

## Defect found and fixed (rulings items 61, 62)
- **Defect:** on module pages and Limitations, `.module-list` (`src/deploy_vii/assets/app.css:72`, `min-height:0`, since df26ea8) shrank to 0px under the "On this page" outline. A real mouse click on a numbered row landed on an outline button and did not navigate.
  - Reproduced by mouse: on S1a, CP-1 to CP-2; on CP-L10, Limitations to CP-L10.
  - Script `click()` routed anyway, which is why the script-only pass missed it.
- **Fix:** `claude/s5-navfix` 3c90773 adds `flex-shrink:0` (user approved directly; mx-feature build; mx-precise APPROVE).

## Recheck on the fixed code (`claude/s5-int2` 3c90773; deliveries regenerated, 4 passed in 45m53s)
| Delivery | Hit test before | Hit test after | All other checks | Real mouse click |
|---|---|---|---|---|
| cp3d-fp03-market positive | 2 covered | 0 | pass | from CP-3D (27 outline items), the CP-0 row opens CP-0 |
| slice-cpl10-screen positive | rows covered on CP-1, CP-L10, Limitations | 0 | pass | from Limitations (55 items), the CP-L10 row opens CP-L10 (failed before the fix); narrow drawer (407 px): from Limitations, CP-0 opens CP-0 |
| s1a-credit-snapshot positive | 20 covered | 0 | pass, also against the oracle; calculation.json drawn | from CP-1 (56 items), the CP-2 row opens CP-2 (failed before the fix) |

The fix is in the shared shell CSS, which every page inlines byte for byte, so the other 16 deliveries share it.

Not verified:
- The other 16 deliveries were not regenerated on the fixed code. Their shell CSS is the same file.
- Browsers other than the built-in Chromium.
- Viewports other than 1440x900 and the 407 px pane.
- Footer rows were not hit-tested (they sit in collapsed `details` and were not affected).
