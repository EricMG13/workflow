# PT-CI-OWNER-SELECT report

Changed only `tests/test_owner_workflow.py::test_tamper_and_foreign_store_refuse` in the leased function. All verifier assertions after the mutation remain present: tamper returns identity_mismatch; restored bytes verify; relabel returns identity_mismatch; foreign store returns stale_binding. Pinned OwnerCall schema declares status Literal[ok, refused, error].

Bounded probe used real OwnerBinding/OwnerCall/SourceEvidence models and all three legal statuses. Compact and pretty JSON each round-tripped to identical canonical serialization (3 each); semantic selection chose successful call after refused/error records; changed JSON altered only status; content-hash address, exact mutation bytes and exact original restoration passed. Exit0: 3 statuses, 3 compact, 3 pretty, one-field mutation, byte-exact restore. Static AST parse and git diff --check exited0.

No owner-workflow/full heavy test bodies were run: the fixture drives long five-stage workflow work. Exact full verifier path is still to be exercised by the applicable remote heavy CI after integration. No Product runtime claim.
