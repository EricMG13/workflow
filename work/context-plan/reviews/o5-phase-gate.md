# O5 phase gate results

Model layer src/deploy_workflow/model + tests/model, plus owner_workflow accessors (eb47e0dc). Venv python. Fast tests only (B16), no RUN_PROMOTION, no whole-suite run. Run 2026-11-01. Nothing changed; gates only.

## Static, tests, pins
| Gate | Exit | Result |
| :-- | :-- | :-- |
| ruff check (model, tests/model, owner_workflow.py) | 0 | clean |
| ruff format --check (same paths) | 0 | clean |
| MYPYPATH=src mypy (same paths) | 0 | no issues in 23 source files |
| pytest -q tests/model | 0 | 445 passed |
| tests/test_owner_workflow.py::test_binding_and_spec_accessors_mirror_the_private_fields (only function eb47e0dc added) | 0 | 1 passed |
| python3 -I cases/pins.py --check | 0 | matches 176 paths |

## Leftovers
`git status --short`: only untracked work/context-plan/plan-amendments-2026-11-01-brief.md. Nothing uncommitted under src/ or tests/.

## Reviewer probes (`.venv/bin/python <probe>`, PYTHONPATH=src:<probe dir>)
| Set | Result |
| :-- | :-- |
| o5t4 expected 0 (p01, p02, p03, p04-p08, p09-p09h, p10-p13, p15) | all 0 except **p09i = 1 (UNEXPECTED)**; prints only "ProviderRejected" |
| o5t4 accepted at 1: p03b, p14 | both 1 |
| o5t6 expected 0 (p01-p04, p06-p09, p11-p14) | all 0 |
| o5t6 accepted at 1: p05, p10 | both 1 |
| o5t6 p13 verdicts | no BROKE line; final "HELD: export relaxation admits no forgery (broke=[])"; two "[pre-existing]/[design]" lines exported as noted |
| o5t5 expected 0 (r01-r05, p01, p03-p05, p08-p10, p12-p14) | all 0 |
| o5t5 accepted at 1: p06, p07, p11, p15, r06, r07 | all 1 |
| o5t5 not in either list | p02 = 1 (prints "BROKEN: export kind differs from the live classification", sent_unknown ProviderRejected exported as sent_usage); r08 = 0 |
| o5t3 expected 0 (p01-p08, p10-p13, plus p02b, p03b, p06b, p12b, p12c) | all 0 |
| o5t3 accepted at 1: p09 | 1 |

## Size
- `git diff --shortstat a40986ec~1 HEAD -- src/deploy_workflow/model tests/model`: 22 files changed, 10511 insertions(+)
- `git show --shortstat eb47e0dc`: 2 files changed, 34 insertions(+)
