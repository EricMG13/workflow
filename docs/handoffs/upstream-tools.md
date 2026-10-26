# Task2-A bounded upstream tools handoff

Status: adapter implementation complete for the frozen v1 component contract;
no analytical owner, downstream consumer or rendered-section completion claimed.
Branch `codex/upstream-render`; exact code-start base
`b90c51c382b0544be5dac194eb91124470c22943`.
Frozen Task0 contract/upstream manifest:
`d9411401e4797e04a2e030d3741e937d2d210e32` from LEAD's clone.
Selected implementation and independent review route: GPT-6.1 Sol/high.
Selection is recorded; no hidden runtime model telemetry is asserted.

## Exact lease and supported interface

Only these files changed:

- `src/deploy_workflow/tools/upstream.py`: factory, two tools, scoped views,
  identity/current-snapshot guards, sanitized checks and immutable receipts.
- `tests/test_upstream_tools.py`: reviewed literals, real Execution factory calls,
  success/refusal/state/exception cases and saved actual receipt JSON.
- `docs/handoffs/upstream-tools.md`: this evidence/handoff.

Import directly: `from deploy_workflow.tools.upstream import UpstreamTools`.
Public factory `UpstreamTools.from_execution(store, ticket_id, step_id, *, grants)`;
`invoke(tool_name, arguments) -> dict`; detached call history via `receipts`.
Factory refusal raises ValueError containing only a stable category. Invocation
accepts the JSON-compatible argument domain frozen in Task0, returns/retains
`tool-receipt/1` with exact supplied arguments and empty source_evidence. Arbitrary
Python objects are outside that protocol. No C1 host/source/package exports,
imported code, shared contracts/manifests, rendering or source permissions changed.

`lookup_upstream` preserves producer/hash/status, requested row/field order,
canonical fact identity, exact Decimal strings/nulls, granted citation handles
and full-body 8192 UTF8 byte limit. CP2 is upper-bounded by the existing
referencable known cited/calculated numeric facts; its grants must be a subset
of that view. CP5 uses Task0's separate canonical fact/status view including
missing values. No quotes/citations/raw text/formula/source_amount are exposed.
`verify_upstream` delegates citations to readiness.citation_issues and integrity
to CP5 review_scope/python_checks. Integrity requires complete single-producer,
no-claim/no-blocked/current scope with all canonical coordinates and internal
inspection granted. Unexpected finding categories fail closed; no new arithmetic.

Factory/invoke check real selected pending ticket/current executable registry step,
pack/input/head/canonical hashes and run/issuer/as-of/method/status identity. Every
success is staged, then current binding and snapshot are rechecked before release.
Read-only operations change no source credit, producer bytes, journal state or
settlement. Immutable JSON receipt storage avoids deepcopy recursion while
preserving detached public snapshots. Single-writer lock cleanup covers setup,
checks and receipt retention; control exceptions propagate.

## Frozen expectations and actual call/result evidence

Tests embed Task0's canonical artifact bytes verbatim, not a renderer-derived oracle.
Producer CP1 accepted hash:
`f0ac5658a87f2acb971d1b94a2f64638b40c500adc76759f09a1235f31c3b046`.
Source `upstream-note` / `line:1` hash:
`d0c13ba47b0c6703c40aa521def7b28a834f99ac3f810c80103e49406c0d30cf`.
Expected revenue120, scale1000000, MILLIONS/USD/FY2025; operating_profit known0;
impairment missing/null with `Synthetic upstream fact not disclosed` limitation.
No raw/quote permission. These USD facts supersede preparation's proposed GBP case.

The complete actual successful receipts below were saved during the final admitted
pytest run. They retain actual call/ticket/snapshot/pack/input identities and actual
arguments/results. Lookup, citation and integrity checks are three separate genuine
factory sessions over the same independently frozen component producer; do not
claim they are a single settled analytical run. Synthetic heads seed the component
store; Execution.create/begin/current_inputs and hash-checked reads actually execute.
No mock authorization, arbitrary provider loop or injected final rendering is used.

## Runtime admission and exact results

All runtime checks used the matching new-project Python 3.13.15 environment without modifying it,
with this clone's src first; no environment was synced or changed. Every check was
freshly admitted by LEAD, source/test frozen beneath it, then slot released immediately.
No broad suite/provider/live/paid test or unrelated process stop was performed.

Common command prefix:
`PYTHONPATH=src '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q`.

| Admission | Target after prefix | PID / UTC start -> finish | Actual result |
| --- | --- | --- | --- |
| C2-RED-1 | `tests/test_upstream_tools.py::test_factory_lookup_preserves_fixed_facts` | 12077 / 21:22:01.350640 -> 21:22:02.787517 | exit1;1failed/1.06s; hashes and real fixture passed, explicit missing-adapter assertion failed |
| C2-GREEN-1 | `tests/test_upstream_tools.py` | 14078 / 21:26:23.889476 -> 21:26:24.529684 | exit0;48passed/0.48s |
| C2-RED-2 | `'tests/test_upstream_tools.py::test_exception_categories_never_turn_failure_into_clean_success[control]'` | 14458 / 21:28:00.789714 -> 21:28:01.192964 | exit1;1failed/0.24s; retained refused versus required error |
| C2-RED-3 | `tests/test_upstream_tools.py::test_interrupted_receipt_bookkeeping_never_strands_writer_lock tests/test_upstream_tools.py::test_deep_json_arguments_return_and_retain_complete_refusal` | 16759 / 21:30:59.143965 -> 21:31:01.063748 | exit1;3failed/1.74s; two stranded-lock recovery failures plus deep JSON RecursionError |
| C2-GREEN-2-REVISED | `tests/test_upstream_tools.py` | 17078 / 21:32:29.767127 -> 21:32:30.366575 | exit0;53passed/0.44s |
| C2-TOURNAMENT-GREEN | `tests/test_upstream_tools.py` | 17950 / 21:34:00.231076 -> 21:34:00.833357 | exit0;53passed/0.45s; final winner/callers/invariants verified |

Dates are 2026-10-26 UTC (Europe/London GMT that date). Full local logs, excluding
initial RED's native tool output, are under ignored `artifacts/c2-*.log`.
The superseded early GREEN2 and older one-node RED3 admissions were never run.
New causal test assertions preceded the confirmed root fixes; additional independent
review probes strengthen the original tests-first suite rather than mirror output.

Final product SHA256:
`4854ec219bcd646e72b1ec367573df898bafad4d48a1f6e18285c90043b0eebe`.
Final tests SHA256:
`40887e513da2bf079b3032bc661d980362da4128c205f653b3bd3344a6474425`.
Final source-set SHA256:
`d0548c04f58625351658b1bd39889506b066ee85cf1a2ff507f0c29a6eaaa1a5`.
Rule: SHA256 of path UTF8 + NUL + exact file bytes + NUL, concatenated in product,
then tests order. Source unchanged after final admitted 53-pass run.
Scoped `ruff check --no-cache` and `ruff format --check` on both files passed;
AST parsing and git diff whitespace/file-scope checks passed.

## Confidence review — Task2-A

Least confident about (ranked):
1. **Hash ownership versus identity.** Traced _context through real current_inputs,
   head_module/result/pack. Runtime rejects foreign run/issuer/as-of, malformed
   method bytes, wrong producer hash/status, stale inputs/selection/ticket/head
   and tampered artifact. Verified fine; no valid-hash ownership shortcut.
2. **Raw/hidden disclosure.** Traced projected-key and canonical-coordinate grants,
   CP2 view bounds, explicit citation-handle mapping and sanitized diagnostic
   categories. Runtime rejects raw tools/quotes/citations/hidden targets whole;
   no partial body or raw marker appears. Verified fine for admitted v1 views.
3. **CP2 missing eligibility.** Original row-denial test was causally weak because
   grants independently denied impairment. Added factory-refusal test with original
   missing-row grants: now it tests the referencable upper bound itself. Verified
   by final focused run; missing remains outside CP2 even though CP5 can inspect it.
4. **Final freshness rather than early refusal.** Original hook mutated during
   initial result load. Added hook after real citation checking: complete staged
   result refuses stale_binding/null body/empty evidence when the journal changes.
   Final focused run passes. Conservative equality, not durable concurrency, is claimed.
5. **Interrupted receipt validity.** Independent review identified BaseException
   bypassing the Exception handler, leaving refused/error_code=None in finally.
   RED2 reproduced; root fix records error/internal_error then rethrows. Final
   tests verify propagation, stable retained failure and subsequent real lookup.
6. **Writer cleanup across initialization/retention.** Review traced successful
   lock acquisition before cleanup region, plus retention before release. RED3
   reproduced permanent refusal after each injected interruption. An outer finally
   now owns the entire acquired-lock lifetime. Both recovery cases are green.
7. **Deep JSON receipts.** LEAD shared a causal C1 finding; this lane independently
   reproduced 600-level JSON refused receipt deepcopy RecursionError in RED3.
   Immutable JSON-string retention and decoded snapshots preserve exact supplied
   JSON/detachment without that recursive copy path. Return/history/recovery tests pass.
8. **Reentrancy and mutation.** Separate writer/receipt locks, unique ordered
   sequences and detached history traced. Runtime tests mutate input/returned
   binding/body/history, refuse reentrant work and retain independent successful
   calls; no journal or source-credit delta. Verified fine.
9. **Financial and scope meaning.** Literal USD120, scale1000000, known0/missingnull,
   multibyte output bound, complete integrity scope/partial/subset/multi/claim
   refusals and sanitized scale/citation findings pass. Existing Python owns math;
   clean mechanical verification is never labeled material-support acceptance.
10. **Tournament changes.** Lazy match uniqueness preserves zero/one/multiple-match
    decisions over immutable Attempt tuples; dropping the temporary encoded string
    changes no supplied argument. Final exact focused command checks all callers
    and concrete financial/permission/state invariants after applying the winner.

Fixed: malformed interrupted receipt, stranded writer lock, deep-JSON receipt copying;
causal test gaps. Verified fine: named identity, scope/disclosure, JSON/Decimal/null,
byte bounds, stale-output refusal, mutation and reentrancy behavior. By design:
JSON-compatible input domain; in-process receipts only, no crash durability; no
source permission or material-support/settlement/render acceptance manufactured.
Still open: downstream analytical settlement/consumption/render evidence below.
No confirmed implementation defect remains within this bounded v1 contract.

## Independent sensitive review

Independent Sol/high agent `upstream_sensitive_review` reviewed frozen Task0 contract,
manifest, first product dd2001.../tests 4b6f85..., and concrete trust/state/financial
boundaries. It identified interrupted receipt and the two causal test gaps, then
confirmed the initialization/retention lock flaw. Its narrow final inspection of
product a1040004.../tests 40887e... confirmed all root fixes resolved, no public
schema drift/new disclosure/caller break and no remaining findings. No reviewer
runtime was run; the 53-pass evidence belongs to this lane's admitted run. The final
allocation-only tournament change was independently adjudicated and then verified
by the actual final 53-pass run; it changes no sensitive oracle or public contract.

## No-argument post-edit rewrite tournament

Scope resolved from this session's new nontrivial functions: `_context` and
`UpstreamTools.invoke`, the two most material trust/publication symbols.
Other helpers/factory/projection/checks are outside this pass's two-symbol cap;
they received confidence and independent review plus the focused suite.
No GitNexus was available. rg impact set: __init__/_current -> _context;
from_execution -> constructor; invoke calls only in test_upstream_tools.py today,
with the frozen future host as downstream consumer. No shared export was changed.

Separate Sol/high agents: Incumbent, Speed, Memory, Readability, then blind Arbiter.
Full candidates used the same mandatory correctness fixes before comparison.
Bracket: A versus B -> A; A versus C -> A (C disqualified for an altered snapshot
attribute); A versus D -> A. A=Memory; B=Speed; C=Readability; D=Incumbent.
No disqualified candidate was applied. Backup retained before winner application.

**Winner: Snippet A (Memory).** Replaces `_context`131-196 and invoke398-474
in `src/deploy_workflow/tools/upstream.py` (final line coordinates).

Justification:

- Lazy ticket matching retains O(1) matching state and stops after a duplicate.
- Releasing encoded JSON sooner reduces retained argument-buffer memory.
- Exact guards, signatures, failure ordering, receipts and mandatory fixes remain.

Verification: exact final focused pytest command above, **53passed in0.45s**;
all current callers and USD120/known0/missingnull/citation/state/refusal checks pass;
ruff check/format-check and final source diff inspected by C2. No speed benchmark
or broad platform certification is claimed. Final winning target code:

```python
def _context(
    store: Execution, ticket_id: str, step_id: str
) -> tuple[ExecutionSnapshot, Attempt, PreparedPack, dict[str, Module]]:
    snapshot = store.read()
    matches = (item for item in snapshot.attempts if item.ticket_id == ticket_id)
    attempt = next(matches, None)
    if attempt is None or next(matches, None) is not None:
        raise _Refusal("stale_binding")
    if attempt.module_id not in _VIEWS or _VIEWS[attempt.module_id] != step_id:
        raise _Refusal("not_permitted")
    chain = step_chain(attempt.module_id)
    # Both admitted v1 consumers have one settling step, with no in-attempt
    # repair. A retained pending/invalid/valid output cannot admit new tool use.
    if (
        chain.steps != (step_id,)
        or attempt.status != "pending"
        or attempt.steps
        or attempt.step_repairs
        or attempt.payload_sha256 is not None
    ):
        raise _Refusal("stale_binding")
    pack = store.pack(snapshot)
    current = current_inputs(snapshot, attempt.module_id)
    if current != attempt.inputs:
        old = {item.input_id: item for item in attempt.inputs}
        if any(
            item.input_id in old
            and old[item.input_id].sha256 == item.sha256
            and old[item.input_id].status != item.status
            for item in current
        ):
            raise _Refusal("identity_mismatch")
        raise _Refusal("stale_binding")
    selected = dependencies(snapshot.run.requested_modules)
    heads = {head.module_id: head for head in snapshot.heads}
    if len(heads) != len(snapshot.heads) or len({i.input_id for i in attempt.inputs}) != len(
        attempt.inputs
    ):
        raise _Refusal("identity_mismatch")
    modules = {}
    for item in attempt.inputs:
        if item.input_id == "prepared-pack":
            if item.sha256 != pack.content_hash() or item.status != "accepted":
                raise _Refusal("identity_mismatch")
            continue
        if item.input_id not in selected:
            raise _Refusal("not_permitted")
        head = heads.get(item.input_id)
        if head is None or head.status == "stale" or head.result_sha256 != item.sha256:
            raise _Refusal("stale_binding")
        if head.status != item.status:
            raise _Refusal("identity_mismatch")
        module = store.head_module(head)
        run = snapshot.run
        if (
            (module.run_id, module.issuer_id, module.as_of, module.method_version)
            != (run.run_id, run.issuer_id, run.as_of, run.method_version)
            or module.module_id != item.input_id
            or module.status != item.status
            or module.content_hash() != item.sha256
        ):
            raise _Refusal("identity_mismatch")
        modules[item.input_id] = module
    if "CP-1" not in modules:
        raise _Refusal("not_permitted")
    return snapshot, attempt, pack, modules

def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Return and retain one atomic receipt; a failed call has no partial body."""
    # Only JSON-compatible arguments are in the public protocol. Validate
    # before copying so non-JSON objects cannot invoke deepcopy hooks.
    try:
        encoded = json.dumps(arguments, ensure_ascii=False, allow_nan=False)
        supplied = json.loads(encoded)
        del encoded
    except (TypeError, ValueError, RecursionError):
        raise ValueError("bad_arguments") from None
    acquired = self._lock.acquire(blocking=False)
    try:
        with self._receipt_lock:
            self._sequence += 1
            sequence = self._sequence
        receipt: dict[str, Any] = {
            "schema_version": "tool-receipt/1",
            "call_id": str(uuid4()),
            "sequence": sequence,
            "binding": copy.deepcopy(self._binding),
            "tool": tool_name,
            "arguments": supplied,
            "status": "refused",
            "body": None,
            "error_code": None,
            "source_evidence": {"read": [], "extracted": [], "surfaced": [], "searched": []},
        }
        try:
            if not acquired:
                raise _Refusal("not_permitted")
            expected = {"lookup_upstream": _LOOKUP_KEYS, "verify_upstream": _VERIFY_KEYS}
            if tool_name not in expected:
                raise _Refusal("not_permitted")
            if type(supplied) is not dict or set(supplied) != expected[tool_name]:
                raise _Refusal("bad_arguments")
            pack, modules = self._current()
            producer = self._producer(supplied, modules)
            data = (
                self._lookup(supplied, producer)
                if tool_name == "lookup_upstream"
                else self._verify(supplied, producer, pack)
            )
            body = {
                "producer": {
                    "module_id": producer.module_id,
                    "sha256": producer.content_hash(),
                    "status": producer.status,
                },
                **data,
            }
            if len(json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()) > 8192:
                raise _Refusal("bad_arguments")
            # Recheck bytes and authorization, not just a mutable current pointer.
            self._current()
            if self._store.read().content_hash() != self._snapshot_sha256:
                raise _Refusal("stale_binding")
            receipt.update(status="ok", body=body)
        except _Refusal as refusal:
            receipt["error_code"] = str(refusal)
        except Exception:  # noqa: BLE001 -- sanitize unexpected errors at receipt boundary
            receipt.update(status="error", error_code="internal_error")
        except BaseException:
            # Preserve interruption semantics while retaining a valid failed
            # attempt receipt; never report process control as a tool success.
            receipt.update(status="error", error_code="internal_error")
            raise
        finally:
            with self._receipt_lock:
                self._receipts.append(
                    json.dumps(
                        receipt, ensure_ascii=False, allow_nan=False, separators=(",", ":")
                    )
                )
        return receipt
    finally:
        if acquired:
            self._lock.release()
```

## Actual final factory/invocation receipts

These are actual saved JSON results from the final admitted component tests, not
handwritten substitutes. The three full bindings show their separate test sessions.

```json
[
  {
    "schema_version": "tool-receipt/1",
    "call_id": "beeafda0-66d9-49c2-81e9-7a3617047fa7",
    "sequence": 1,
    "binding": {
      "run_id": "task0-upstream-run",
      "issuer_id": "synthetic-issuer",
      "as_of": "2025-12-31",
      "method_version": "deploy-v-r14",
      "pack_sha256": "f27fcd100ddf8c114103b5db446e551b88cf4aae9c5c381732a73d128a6cb43b",
      "snapshot_sha256": "1fc8fe3f2b9a5bcfdc4862455dd146db27a2b1a19f3f3954f46b98d964b2bf07",
      "module_id": "CP-5",
      "step_id": "integrity_review",
      "ticket_id": "8be505e7-f2af-4a34-8776-03ed042cb437",
      "attempt": 0,
      "inputs": [
        {
          "input_id": "prepared-pack",
          "sha256": "f27fcd100ddf8c114103b5db446e551b88cf4aae9c5c381732a73d128a6cb43b",
          "status": "accepted"
        },
        {
          "input_id": "CP-0",
          "sha256": "bc00c718274734e4b4a6e38c1da5f198a92e3197d0ef2602dc9ddc280f879c6c",
          "status": "accepted"
        },
        {
          "input_id": "CP-1",
          "sha256": "f0ac5658a87f2acb971d1b94a2f64638b40c500adc76759f09a1235f31c3b046",
          "status": "accepted"
        }
      ]
    },
    "tool": "lookup_upstream",
    "arguments": {
      "producer_module_id": "CP-1",
      "producer_sha256": "f0ac5658a87f2acb971d1b94a2f64638b40c500adc76759f09a1235f31c3b046",
      "table_id": "income",
      "row_ids": [
        "revenue",
        "operating_profit",
        "impairment"
      ],
      "fields": [
        "fact_id",
        "table_id",
        "row_id",
        "field",
        "status",
        "label",
        "amount",
        "scale",
        "unit",
        "currency",
        "period",
        "limitation",
        "citation_handles"
      ]
    },
    "status": "ok",
    "body": {
      "producer": {
        "module_id": "CP-1",
        "sha256": "f0ac5658a87f2acb971d1b94a2f64638b40c500adc76759f09a1235f31c3b046",
        "status": "accepted"
      },
      "table_id": "income",
      "rows": [
        {
          "row_id": "revenue",
          "facts": [
            {
              "fact_id": "revenue",
              "table_id": "income",
              "row_id": "revenue",
              "field": "value",
              "status": "known",
              "label": "Revenue",
              "amount": "120",
              "scale": "1000000",
              "unit": "MILLIONS",
              "currency": "USD",
              "period": "FY2025",
              "limitation": null,
              "citation_handles": [
                {
                  "source_id": "upstream-note",
                  "source_sha256": "d0c13ba47b0c6703c40aa521def7b28a834f99ac3f810c80103e49406c0d30cf",
                  "locator": "line:1"
                }
              ]
            }
          ]
        },
        {
          "row_id": "operating_profit",
          "facts": [
            {
              "fact_id": "operating_profit",
              "table_id": "income",
              "row_id": "operating_profit",
              "field": "value",
              "status": "known",
              "label": "Operating profit",
              "amount": "0",
              "scale": "1000000",
              "unit": "MILLIONS",
              "currency": "USD",
              "period": "FY2025",
              "limitation": null,
              "citation_handles": [
                {
                  "source_id": "upstream-note",
                  "source_sha256": "d0c13ba47b0c6703c40aa521def7b28a834f99ac3f810c80103e49406c0d30cf",
                  "locator": "line:1"
                }
              ]
            }
          ]
        },
        {
          "row_id": "impairment",
          "facts": [
            {
              "fact_id": "impairment",
              "table_id": "income",
              "row_id": "impairment",
              "field": "value",
              "status": "missing",
              "label": "Impairment",
              "amount": null,
              "scale": "1000000",
              "unit": "MILLIONS",
              "currency": "USD",
              "period": "FY2025",
              "limitation": "Synthetic upstream fact not disclosed",
              "citation_handles": []
            }
          ]
        }
      ]
    },
    "error_code": null,
    "source_evidence": {
      "read": [],
      "extracted": [],
      "surfaced": [],
      "searched": []
    }
  },
  {
    "schema_version": "tool-receipt/1",
    "call_id": "90a515ae-2d70-469d-bba5-7a392dbe0858",
    "sequence": 1,
    "binding": {
      "run_id": "task0-upstream-run",
      "issuer_id": "synthetic-issuer",
      "as_of": "2025-12-31",
      "method_version": "deploy-v-r14",
      "pack_sha256": "f27fcd100ddf8c114103b5db446e551b88cf4aae9c5c381732a73d128a6cb43b",
      "snapshot_sha256": "2e156eefdd901c8882857de68e256b04fe945f908486ff1163421e5ee0490113",
      "module_id": "CP-5",
      "step_id": "integrity_review",
      "ticket_id": "279fff6f-af62-447d-8b44-04c9274dc07e",
      "attempt": 0,
      "inputs": [
        {
          "input_id": "prepared-pack",
          "sha256": "f27fcd100ddf8c114103b5db446e551b88cf4aae9c5c381732a73d128a6cb43b",
          "status": "accepted"
        },
        {
          "input_id": "CP-0",
          "sha256": "bc00c718274734e4b4a6e38c1da5f198a92e3197d0ef2602dc9ddc280f879c6c",
          "status": "accepted"
        },
        {
          "input_id": "CP-1",
          "sha256": "f0ac5658a87f2acb971d1b94a2f64638b40c500adc76759f09a1235f31c3b046",
          "status": "accepted"
        }
      ]
    },
    "tool": "verify_upstream",
    "arguments": {
      "producer_module_id": "CP-1",
      "producer_sha256": "f0ac5658a87f2acb971d1b94a2f64638b40c500adc76759f09a1235f31c3b046",
      "kind": "citations",
      "fact_ids": [
        "revenue",
        "operating_profit",
        "impairment"
      ]
    },
    "status": "ok",
    "body": {
      "producer": {
        "module_id": "CP-1",
        "sha256": "f0ac5658a87f2acb971d1b94a2f64638b40c500adc76759f09a1235f31c3b046",
        "status": "accepted"
      },
      "kind": "citations",
      "verdict": "valid",
      "issue_count": 0,
      "issues": []
    },
    "error_code": null,
    "source_evidence": {
      "read": [],
      "extracted": [],
      "surfaced": [],
      "searched": []
    }
  },
  {
    "schema_version": "tool-receipt/1",
    "call_id": "f1ffeb9a-b442-4cf0-9b36-d0706dadf84a",
    "sequence": 1,
    "binding": {
      "run_id": "task0-upstream-run",
      "issuer_id": "synthetic-issuer",
      "as_of": "2025-12-31",
      "method_version": "deploy-v-r14",
      "pack_sha256": "f27fcd100ddf8c114103b5db446e551b88cf4aae9c5c381732a73d128a6cb43b",
      "snapshot_sha256": "99844ed6863c80c63c14611638420bbe7ceffcd80ce0d357908d7fba3ba95b80",
      "module_id": "CP-5",
      "step_id": "integrity_review",
      "ticket_id": "4a68ec8b-1175-4731-8b5a-741e4077a2d6",
      "attempt": 0,
      "inputs": [
        {
          "input_id": "prepared-pack",
          "sha256": "f27fcd100ddf8c114103b5db446e551b88cf4aae9c5c381732a73d128a6cb43b",
          "status": "accepted"
        },
        {
          "input_id": "CP-0",
          "sha256": "bc00c718274734e4b4a6e38c1da5f198a92e3197d0ef2602dc9ddc280f879c6c",
          "status": "accepted"
        },
        {
          "input_id": "CP-1",
          "sha256": "f0ac5658a87f2acb971d1b94a2f64638b40c500adc76759f09a1235f31c3b046",
          "status": "accepted"
        }
      ]
    },
    "tool": "verify_upstream",
    "arguments": {
      "producer_module_id": "CP-1",
      "producer_sha256": "f0ac5658a87f2acb971d1b94a2f64638b40c500adc76759f09a1235f31c3b046",
      "kind": "integrity",
      "fact_ids": [
        "revenue",
        "operating_profit",
        "impairment"
      ]
    },
    "status": "ok",
    "body": {
      "producer": {
        "module_id": "CP-1",
        "sha256": "f0ac5658a87f2acb971d1b94a2f64638b40c500adc76759f09a1235f31c3b046",
        "status": "accepted"
      },
      "kind": "integrity",
      "verdict": "valid",
      "issue_count": 0,
      "issues": []
    },
    "error_code": null,
    "source_evidence": {
      "read": [],
      "extracted": [],
      "surfaced": [],
      "searched": []
    }
  }
]
```

## Consumer connection and remaining rendered evidence

Task2-A unblocks CP2 bounded CP1 consumption and CP5 mechanical integrity, and their
FP01 synthesis/QA/evidence/limitations sections. Adapter completion finishes no owner.
C1/LEAD still must register/import the leaf, retain actual analyst calls in the real
workflow, bind calls to submissions, validate and settle real producers/consumers,
and prove the settled consumer actually used the exact selected returned references.

Synthetic component heads are not a substitute for real CP0/CP1 outputs. Task3's
first leased slice is real CP0 settlement -> actual CP1 source_context consumption
-> selected Evidence/Limitations/CP0 DOM. Financial statements/Model and broader
CP2/CP5 owner settlement remain separate evidence. C2 has no rendering code lease.
Future rendered-cell checks must compare actual selected-run values/status/units/
periods/citation metadata/producer hashes and limitations to independent fixed facts,
not the renderer's own output. Review JSON, registered names, component receipts,
placeholder pages and direct composers alone do not close matrix rows.
