# O2 line rule measurement (Task 1, Q1)

22 distinct golden HTML files, 843 quotes, `convert_html` (check.py semantics, strict decode, empty lines dropped). Lengths in characters.

| rule | misses | lines | median | p99 | max |
|---|---|---|---|---|---|
| R1 as written (p,div,tr,li,br,h1-h6) | 184 | 40889 | 47 | 1799 | 6168 |
| no div | 83 | 21911 | 48 | 4803 | 108282 |
| tr + p | 81 | 17056 | 42 | 4613 | 961460 |
| tr only | 50 | 12538 | 47 | 6672 | 961460 |
| no break | 0 | 22 | 192374.5 | 1032864 | 1032864 |

Probe (p4_line_policies.py, errors=replace parser): R1 208, no-div 107, tr+p 105, tr 76, flat 27.
Encoding: 22/22 strictly valid UTF-8, 0 BOM, 0 NUL, 0 charset declared in first 4 KB.

## Ruling (controller, Q1)
Line rule = **no div**: new line at p, tr, li, br, h1-h6; other check.py BLOCK tags (div, td, ...) emit a space.
Reason: 83 misses against tr+p's 81, but longest line 108,282 vs 961,460 characters and more lines (21,911 vs 17,056), so locators are finer. The two extra misses go to the goldens owner (cost if wrong: two quotes to re-cut). Lines stay well under O4's `MAX_INPUT_BYTES` (4,194,304). Implemented as `LINE_TAGS` in `src/deploy_workflow/html_text.py`; corpus test pins 83 misses.
