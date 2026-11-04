# Confidence review — PT-CI-OWNER-SELECT

Least confident about (ranked):
1. Could selection still pick a refused/error receipt? The generator now searches `receipt.calls` by typed `status == "ok"` and explicitly asserts a record exists. Bounded real-schema probe placed refused and error first and selected the later ok record. Verdict: CONFIRMED prior fixture defect, fixed.
2. Could stored bytes differ from selected identity or serialized bytes? Path uses `selected.content_hash()`; test checks readback equals selected compact model JSON before mutation. Bounded temp-store probe confirms hash-addressed readback. Verdict: verified.
3. Could serialization rewrite other fields or alter nested data? Test compares parsed changed object to original dict with only top-level status replaced. Real schema probe covered compact and pretty inputs and status set ok/refused/error. Verdict: verified.
4. Could tamper bytes fail to persist or restoration be approximate? Test verifies exact changed-byte readback and exact original-byte restoration before rerunning verifier. Probe checked both and parsed restored model retains ok. Verdict: verified.
5. Does bounded probe establish full OwnerRunReceipt persistence and all later verifier assertions? No; no fixture workflow body or heavy verifier assertion ran locally. Verdict: still open by design; exact applicable remote heavy CI must run after selective integration.

Fixed: semantic successful-call selection and byte-exact, one-field mutation.
Verified fine: OwnerCall allows exactly ok/refused/error; all post-tamper assertions remain in source; diff limited to requested test body; AST and whitespace checks pass.
By-design: no production/verifier source changes, no long fixture body.
Still open: full real owner workflow verifier on remote heavy CI; no green result claimed.
