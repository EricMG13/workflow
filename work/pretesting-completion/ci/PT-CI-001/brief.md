# PT-CI-001 — TEST-METADATA repair

Starting commit: `a4549ed54d6dc8a00f50188757dbbdfbe09315a8` (verified in isolated worktree).

## Answer key

| User/system action | Surface | Expected observable result | Comparison |
|---|---|---|---|
| Pin the CPL10 owner expected oracle digest in the golden metadata | `tests/prompts/rule_lists.golden.json#/sha256/oracles/cases~1cpl10-owner~1expected.json` | The value equals the independently reviewed and adopted oracle file digest `631f44385947f16cd9d0fa02e263ae5a8ce9eadfe194b0866dbd97febb08f48d`; previous pin was `285915140dbd7722e406ce96bb11c20ab5f5ce370e6649748299f4809695ce45` | `PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q tests/prompts/test_rules.py::test_the_golden_file_pins_the_sha256_of_each_core_and_oracle` compares golden metadata to `rules.golden_document()` and thus the oracle bytes |

Independent basis: `cases/cpl10-owner/expected.json` is the adopted oracle; its recorded digest is `631f44385947f16cd9d0fa02e263ae5a8ce9eadfe194b0866dbd97febb08f48d`. Independent `mx-precise` review is PASS/FREEZE in `work/context-plan/reviews/o7-plan-review.md`. The approved remedy is to change only the stale literal in the golden metadata; no oracle, source, rule text, or other golden field changes.
