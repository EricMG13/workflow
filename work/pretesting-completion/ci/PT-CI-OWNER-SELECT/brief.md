# PT-CI-OWNER-SELECT — bounded testing-only repair

Base: `71d5728b933aab24ab9b367e170ee2faaa4449eb`; exclusive lease pins this one test plus these three records. Function `test_tamper_and_foreign_store_refuse` has arbitrary `iterdir()` receipt choice and performs literal `"ok"` replacement. An early refused/error record can make the mutation a no-op.

Fix: choose the first `status == "ok"` from `receipt.calls`, fail explicitly if absent, find the file by `selected.content_hash()`, compare raw bytes to the selected compact serialization, construct an error-status model copy, and assert the parsed JSON differs only in top-level status. Write and verify exact bytes; retain exact restoration. All existing verifier identity, relabel, and foreign-store assertions remain. Testing ownership only; no Product verifier repair, no round-budget reset.
