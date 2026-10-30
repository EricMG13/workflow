# B7 report: CP-1 refuses a blank event_scan_explanation (OI-20)

Branch claude/oi-b7-event-scan, from f0fce11.

Commits:
- b6f3469 RED: tests in tests/test_source_context_blank.py (6 failed, 27 passed, run by the controller)
- 4b2fcc2 fix: src/deploy_vii/source_context.py
- 236260e D12 record in post_import_patches (prior d50e1bad -> bcdcec41, review docs/rulings/2026-10-30-open-items.md)
- the commit that adds this report

Rule: a blank `event_scan_explanation` (whitespace, U+200B, U+2800 and the like, via `prose.is_blank`) gives one issue per source, `Empty event scan explanation: <source_id>`, whatever the scan state. The text is not echoed. Nothing else changes.

Parity: 50 `event_scan_explanation` values under cases/**/*.json (stdlib scan), none blank. The parity test asserts it.

Gates (controller, at 236260e):
- the 4 test files, 77 passed
- ruff check: only the 2 ISC004 hits in source_context.py that predate B6 (now at :597/:599)
- ruff format and mypy exit 0
- pins 87 ok
- D12 strict exit 0
- suppressions 13/5
- the B6 reviewer's probe_event_scan_blank.py exits 0

Not verified: the deferred files (earnings, source tools, financial workflow, owner s1a, CZR CP-1) were not run. No project Python was run by me.

agent=mx-feature fix-rounds=0 gates-first-pass=y
