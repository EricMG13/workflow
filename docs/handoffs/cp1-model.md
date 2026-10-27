# CP1 financial workflow and deterministic Model handoff

## Reviewed implementation

C1 owns exactly `src/deploy_workflow/financial_workflow.py`,
`tests/test_financial_workflow.py` and this handoff on `codex/cp1-financial-impl`,
based on `4cc75da077c49e173f4599211b22d63a6ed6d188`.
The imported financial core, source host and original source-only workflow are
unchanged. PR MANAGER alone integrates the LEAD-admitted commit.

The producer implementation and its 20 component cases passed. This does not
qualify the actual analytical actor, renderer or native browser. Those remain the
next admitted runs. The C2 helper below is ready for use after integration.
Paid/provider/live work remains paused; no product model/effort setting changed.
LEAD explicitly selected Sol/high for this lease. Separate sensitive/tournament
reviewers were configured as `gpt-6.1-sol` / `high`; this records dispatch and
review responses, not inaccessible provider telemetry.

Frozen authority and inputs:

| File/input | SHA256 |
| --- | --- |
| docs/CP1-MODEL-SLICE.md | 0bd7d5d9e5fdffb4f8b3016fb913105dbd1f2d19b8b263827de9120f0bf08250 |
| cases/financial/manifest.json | 6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432 |
| Financial source | 82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429 |
| Identity source | 74fe2ad422266bc01a43af025fed0aca5fdb5aa952c60c013efbbef0ba816ec4 |
| financial_workflow.py tested bytes | 4f513165d4229c853dd7723cb3b9bbdb838b614cbb11a9ae5f818635a947da56 |
| test_financial_workflow.py tested bytes | 771af9a706f0883008b327e12e3e47ed17e90a8b6a8544ca7d18b784acd4621b |

The independently frozen V4 source has opening PERIOD_END2024 balances, four
reported 2025 quarters and independently reported FY2025. All 82 extracted rows,
columns, coordinates and decimals are covered. There is no FY2024 income statement
or prior-year growth qualification. Quarter-only historical LTM lacked the adopted
FY/PYTD anchor; actual reported FY2025 resolves that source gap without changing
core calculation or promotion gates. COGS 15, gross profit 15 and function-only
OPEX 8.75 per quarter remain distinct from total operating costs 23.75. All 26
flow metrics have source-supported quarter/FY values, including actual zeros.
CFO/NCF identities and complete equity bridges are explicit, without residual plugs.

## Public API and C2 seam

Leaf import: `deploy_workflow.financial_workflow`; no shared initializer changes.

```python
FinancialWorkflow.create(directory: Path, pack: PreparedPack, *, model_directory: Path)
workflow.invoke(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]
workflow.read_inputs() -> dict[str, Any]
workflow.submit_review(payload: str) -> dict[str, Any]
workflow.publish_model() -> dict[str, Any]
workflow.write_receipt(destination: Path) -> FinancialSliceReceipt
verify_financial_slice_receipt(
    store: Execution, receipt: FinancialSliceReceipt,
    *, model_directory: Path | None = None,
) -> None
serve_json_lines(workflow, reader, writer, *, destination: Path, participant: str) -> None
```

Trusted setup owns paths and the prepared pack. CLI entry:

```text
python -m deploy_workflow.financial_workflow --directory STORE --pack PACK.json \
  --model-directory MODEL --receipt RECEIPT.json --participant NAME
```

Each JSON line selects one fixed operation. Invoke has `tool` and `arguments`;
submit_review has raw JSON string `payload`; other operations have no arguments.
The five operations are invoke, read_inputs, submit_review, publish_model and
write_receipt. No message grants filesystem/Execution constructors, final Module
submission, arbitrary code, or new paths. Transport permits 128 messages, at most
4*1024*1024 characters per line, and rejects non-finite JSON. Raw review UTF8 is
bounded to 4*1024*1024 bytes. Calls/reads/submissions each permit 16 per ticket/stage;
core stage/module repair budgets remain unchanged; publisher permits two calls.

Source permissions remain CP0/source_readiness and CP1/source_context/financials.
Financials must actually extract all statement pages in that epoch and read located
definitions, facilities and disclosures. Earlier source-context reads do not count.
The adapter reconstructs Seen from authentic call receipts and uses public
`seen_tables(PackTools(admitted_pack), seen, context)`, checking every actual printed
column/period, label, locator/quote and exact amount. Standalone empty statement
captions refuse; prose mentioning an absent FY statement is not a statement table.

Later `read_inputs` returns a current FinancialBinding, sequence, full typed input
hash and projected string body. Narrative uses `live.context.narrative_evidence`;
readiness uses `live.context.readiness_inputs`; quality uses authentic QualityInputs
JSON only. Nested raw citations/quotes and catalogue record_json are not exposed.
Historical `prompts.quality_scope` is forbidden. A read of the current source-free
inputs is required before submission. Refused raw-source calls are retained with
no body; supplied arguments are detached from subsequent caller mutations.

The core owns all calculations, validations, candidate Modules and settlement.
CP0 uses actual submit_cp0_review. Ordered CP1 uses the public normalization/prefill
adapter and submit_model_payload, then actual promote_cp1. Raw/stored payload bytes,
canonical review hash, prefill paths/kinds, step/output and candidate/settled
identities stay distinct. Model calls actual publish_cp_model and its verifier.
Owned failed/partial output is quarantined; failed interruption or partial-file
hashing cannot prevent the independent cleanup/audit path. Existing destinations
are preserved. Successful publication precedes the final receipt seal.

Strict final schema `cp1-model-slice-receipt/1`:

- Frozen C2 consumer fields: `run: Run`, `pack_sha256`, final exact-current
  `snapshot_sha256`; optional `cp1` with ticket_id/result_sha256/status
  accepted|restricted; optional `model` with ticket_id/result_sha256/
  cp1_result_sha256 and exact three-file raw SHA map; optional fixed
  `refusal=cp1_not_authorized`.
- Additional typed fields: participant, transport (`python-api` or
  `bounded-json-lines/1`), promoted cp0 record, calls, input_reads, numbered
  submissions, refused_begin and publications.
- Each binding retains run/issuer/as_of/method/pack/snapshot/module/step/ticket/
  attempt/current inputs. Calls retain actual request, status/body/error and
  evidence. Input reads retain actual body/full-input hash. Submissions retain
  raw/stored/canonical identities, prefill mappings, disposition/issues,
  before/after state and actual step/output hashes. Publications retain every
  actual attempt or non-begin refusal with before/after snapshots and file hashes.

Content-addressed audit collections are under `financial-slice-audit/{calls,
input-reads,submissions,bindings,payloads,publications,refused-begin}`. The terminal
`receipt.sha256` seals the exact final receipt. No absolute path grants authority.

Public verification is read-only with respect to Execution. It checks exact current
identity and complete head metadata/qualifications, all retained journal steps and
repairs, snapshot ancestry, exact audit sets, genuine source-call replay, actual
projection bodies, raw-to-stored prefill and numbered occurrence histories. Public
promotion and publication APIs use non-writing probes to rederive whole candidates
and pure settlements. Canonical envelope export/read and Model verification are
repeated. Model file hashes are raw bytes. A portable copy verifies without its
original directory. Any forged/foreign/stale/incomplete receipt raises ValueError.

C2 component helper, with no injected final Modules:

```python
from tests.test_financial_workflow import completed_financial_case
completed_financial_case(root: Path, *, gap: bool = False) -> tuple[Path, Path, Path | None]
# (execution_directory, receipt_path, model_directory_or_none)
```

The positive actual component has Model readiness READY, actual QA Restricted and
restricted promoted CP1/Model heads. Qualifications are implementation-only;
analytical/render/native remain unrun. Restricted QA is promotable; no score-60 or
readiness-only publication gate was introduced. The missing-financial-source case
actually settles CP0 CONDITIONAL/DO NOT RUN, refuses CP1 begin and calls the actual
publisher, which refuses absent promoted basis before any Model attempt/files.

## Test and runtime evidence

Every heavy job was separately LEAD-admitted; source/tests/cases stayed frozen
through each actual exit. No quiet job was killed or restarted. Logs are local
`work/` evidence and are not included in this three-file implementation commit.

| Job | PID | UTC interval | Actual result |
| --- | --- | --- | --- |
| C1-FIN-RED-1 | tool did not expose PID | initial RED | exit1, missing implementation, 1 failed/0.24s |
| C1-FIN-FOUNDATION-1 | 34225 | Oct26 23:19:01–23:19:02 | exit0, 2 passed/0.54s |
| C1-FIN-COMPONENT-1 | 34681 | Oct26 23:23:42–23:23:44 | exit1, 7 passed/1 failed/1.67s; invalid CFS D&A fixture ID corrected to other: |
| C1-FIN-POSITIVE-1 | 35007 | Oct26 23:29:08–23:29:09 | exit1/0.83s; NCF identity target correctly required total/subtotal |
| C1-FIN-POSITIVE-2 | 35101 | Oct26 23:31:12–23:32:23 | exit1/70.19s; actual QA exposed missing equity bridges and FY anchor; V4 source/oracle revised independently |
| C1-FIN-POSITIVE-3 | 37379 | Oct26 23:47:40–23:47:41 | exit1/0.78s; prose falsely matched statement caption; anchored actual caption matcher |
| C1-FIN-POSITIVE-4 | 37578 | Oct26 23:49:13–23:56:04 | exit0, 1 passed/410.66s, genuine complete positive + portable verification |
| C1-FIN-FINAL-1 | 39717 | Oct27 00:07:40–00:18:46 | exit0, 20 passed/665.23s |

Final exact focused command (also used for parent tournament verification):

```text
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_financial_workflow.py
....................                                                     [100%]
20 passed in 665.23s (0:11:05)
```

Final log `work/cp1-fin-final-1.log` SHA256
`144ad6503186e6b925e0a5aaf18afd3d02e3dd8bc929d833df9a971999a24dd1`.
Positive-4 log SHA256
`72463b2bd984a49faea9a251a8870254189c8a3be1840ce67dcee7afad54a94e`.
Before/after final source/test/manifest hashes match the table above.

The final 20 cases cover actual positive promotion/publication/public and portable
verification; genuine missing-source begin/publisher refusal; preauthorization;
unread/unextracted/omitted/swapped-period evidence; stale snapshots; two identical
invalid reviews through actual core repairs; invalid QA lineage upgrade; partial
write plus unreadable partial file, quarantine and actual publication repair;
double finish/interruption failure; raw tampering of each Model file; coherently
rebound forged head status/inputs/qualification; foreign store; coherently omitted
and renumbered invalid repair records; existing destination; FY/Q4 same-day column
identity/ambiguity/duplicates/header fallback/generator behavior; prose versus
actual empty statement captions; detached refusal arguments; and strict NaN refusal.

The immutable positive fixture was created by the genuine Positive-4 workflow,
then copied for independent tamper cases and authenticated with the current public
verifier. Its raw receipt SHA is
`9e0136214ec27ba1f325a3010e0ab18a015c410e9037a89621f1814a6a120b28`,
final snapshot `3245b68dd7e038515f751afc678a62a444b262bfa509f5e551a130fc357be32c`.
A clean checkout without this optional local archive builds the genuine helper
anew. Quality/publication repair cases use genuinely reached prefixes and fresh
isolated stores/locks; only specific failure operations are monkeypatched.
No mock success or private final candidate construction is used.

Static validation passed on final bytes:

```text
python -m ruff check src/deploy_workflow/financial_workflow.py tests/test_financial_workflow.py --select I,F
All checks passed!
python -m mypy --follow-imports=silent src/deploy_workflow/financial_workflow.py
Success: no issues found in 1 source file
```

Commands use the repository Python shown above. Caller grep, exact file-scope
review and `git diff --check` also pass. No broad imported suite was run.
A broader optional Ruff run reports six style/advisory findings: re.M alias,
two SIM114 branch-combination suggestions, an unused BLE001 noqa, an unused test
score binding and a loop-closure warning. The closure is called immediately in
the same iteration and never escapes; the actual per-period fixture passed.
The branch shape preserves the reviewed explicit period distinctions. These are
not reported as a full-Ruff pass; the agreed I/F check and strict mypy pass.
No post-test cosmetic source rewrite was made.

## Confidence review — final three-file diff

Least confident about, ranked and investigated through real code/callers:

1. **Complete head/candidate authenticity.** Independent review confirmed that a
   core publication subset check alone did not authenticate whole head metadata or
   settlement. Patched exact head_of comparisons with adopted qualifications and
   public non-writing candidate/settlement probes. Adversarial tests coherently
   rebind audit coordinates and the seal before changing head status, inputs or
   qualification, so ancestry alone cannot cause the expected refusal. Verdict:
   confirmed bugs fixed; final causal cases pass.
2. **Repair/audit completeness and repeated payloads.** Confirmed invalid repair
   entries and failed earlier Model attempts could disappear; hash-only selection
   also stranded two identical invalid reviews. Patched all-retained Counter
   equality, numbered submissions, actual latest step/repair selection and complete
   ordered publication-attempt history. Coherent omission/renumber/reseal and real
   repeated-invalid/core-repair cases pass. Verdict: confirmed bugs fixed.
3. **Partial publication and cleanup failures.** Confirmed finish errors outside
   CpModelRefused, failed interruption and unreadable partial-file hashing could
   escape cleanup. Outer finalization handles actual exceptions; interruption,
   per-file hashes and quarantine are independent best effort. Tests inject actual
   write/read/finish/interrupt failures, require quarantined output/audit and deny
   a final success receipt; actual subsequent repair publishes. Existing destination
   is preserved. Verdict: confirmed bugs fixed, causal checks pass.
4. **Financial provenance, periods and arithmetic.** Traced actual extraction,
   per-column identity, statement coverage, core financial/readiness/LTM paths and
   independent V4 literal oracle. Fixed canonical fixture ID/identity classification
   errors, absent equity structures/FY anchor and false prose-caption detection.
   No core arithmetic or gate changed. Positive has four actual complete quarters,
   known zero distinctions and readiness READY; all extracted rows are checked.
   Verdict: source/fixture defects resolved; evidence refusals and positive pass.
5. **Source-free disclosure and raw/stored trust seams.** Traced actual projection
   helpers, source epoch permissions, raw/stored prefill and verifier replay. Quality
   uses only QualityInputs, with no historical quality_scope. Deep detachment and
   non-finite rejection close actual mutable/JSON boundaries. Actual body/no-quote/
   no-record_json assertions, refused raw-source calls and strict transport tests
   pass. Verdict: verified fine after boundary fixes.
6. **Independent QA versus self-fulfilling expectations.** The component helper
   freezes raw claims/materiality/lineage and a Fraction-based expectation from the
   adopted formula before submitting quality. Actual retained score/status matches;
   lineage upgrades fail promotion. No analyst-supplied score/status or invented
   promotion threshold. Verdict: component verified; actual actor QA still requires
   its separate frozen inventory and LEAD review before promotion.
7. **Currentness, portability and operation ordering.** Traced nonblocking instance
   lock, exact snapshot checks, activation/repair order, trusted paths, final seal
   and read-only verifier. Actual stale/foreign/portable/file-tamper tests pass.
   Full inputs remain internal; projection hashes bind them. Verdict: verified fine
   under the documented exclusive-writer/new-destination setup.
8. **Boundaries and failure contracts.** Inspected empty source/table, zero/missing,
   duplicate/ambiguous periods, exhausted repairs, NaN, per-stage/message budgets,
   sealed state and publication retry branches. Focused causal cases above pass;
   finite limits and final-state denial are explicit in the implementation.
   Verdict: verified within the bounded offline contract.

Fixed: concrete root causes in items 1–5. Verified fine: final currentness,
raw/stored identities, actual stage order, independent component QA, source coverage,
portable verification and failure refusal, with actual 20-case evidence above.
By design: trusted exclusive local writer/new destinations; no cross-process atomic
no-replace claim; supplied-page synthetic data without OCR/PDF/provider/production
qualification; implementation qualification only; no CLI resume feature claimed.
Still open: actual analyst participation and independently reviewed raw QA, C2
render consumption and native browser evidence. These are scheduled slice phases,
not silently counted by component tests.

Independent `financial_sensitive_review` closed the scoped final delta: partial
hash-read failures now permit quarantine/audit; forged-head tests coherently rebind
publication records/seal; no residual found. Its final confirmation was static;
the final runtime batch above verifies the corresponding causal cases.

## Rewrite tournament — no-argument post-edit mode

Resolved targets from actual `git diff HEAD --stat`; cap of two material symbols
per pass. Parent read each target and caller before the bracket. No GitNexus graph
was available; repository-wide reference grep plus strict mypy supplied the impact
check. Separate incumbent/speed/memory/readability/anonymous-arbiter roles ran as
configured Sol/high, at most three concurrently. Parent applied and verified winners.

### Pass 1

**Winner:** anonymous Snippet C, replacing `_column_periods`, final lines 420–468
in `src/deploy_workflow/financial_workflow.py`. Blind bracket B vs C → C;
C vs D → C; C vs A → C. A incumbent, B speed, C memory, D readability.

**Justification:**

- Count matching periods and retain only the single ID instead of allocating a
  list for every column; matching retained space falls from O(periods) to O(1).
- Preserve full per-cell iteration, header fallback order, all period-type/date
  distinctions, ambiguity/duplicate rejection and one-shot iterator behavior.
- Keep mapping local and explicit without changing signature, return type, callers
  or any evidence/submission side effect.

Impact: `_evidence_issues` → submit_review and public receipt verification; focused
column cases also call it directly. Backup before applying:
`work/rewrite-column/financial_workflow.before.py`. Parent invariant spot-check:
actual Q4 and FY ending 2025-12-31 map to separate IDs; duplicated candidates and
repeated FY columns refuse. Final exact focused pytest command above passes all
20 cases, including those invariants. Strict mypy/caller grep pass; parent inspected
the actual diff and applied only the selected function.

### Pass 2

**Winner:** anonymous Snippet B, replacing `FinancialWorkflow.submit_review`
(final lines 599–734) and `_publication_history` (1198–1256). Blind bracket
B vs C → B; B vs D → B; B vs A → B. A incumbent, B speed, C memory,
D readability (incumbent retained as its candidate).

**Justification:**

- Cache immutable raw/stored encoded bytes and the frozen after-snapshot hash,
  making repeated audit identities consistent without removing core recomputation.
- Build prior ticket IDs once per history transition, reducing discovery from
  O(before*after) to expected O(before+after) with the same asymptotic peak space.
- Preserve audit-before-submission order, occurrence multiplicity, prior-attempt
  equality, repair activation, publication refusal and response contracts.

Impact: serve_json_lines and focused workflow/helper callers → submit_review;
write_receipt/public verifier → _verify → _publication_history. Backup before
applying: `work/rewrite-state/financial_workflow.before.py`. Parent accepts the
bounded encoded-buffer lifetime tradeoff (raw review cap four MiB) for explicit
identity reuse. Spot-check: two identical invalid reviews use genuine core repairs;
failed publication then real retry requires both attempt records, and coherent
omission refuses. Final exact focused pytest command above passes all 20 cases;
strict mypy/caller grep pass. Parent inspected actual diff, signature and side
effects after application. No candidate was applied beneath a running check.

Other material symbols skipped under the per-pass cap: _evidence_issues, _verify,
_projection, _historical, _verify_cp0, _verify_promotion, _verify_model_settlement,
publish_model, write_receipt, invoke, read_inputs, transport and activation. These
remain covered by sensitive/confidence review and causal checks, without claiming
a whole-branch rewrite sweep. Mechanical schemas, trivial helpers, test/doc changes
and the branchless non-finite rejection are exempt.

**Final code:** the exact three selected functions follow. This is the verified
in-tree implementation, not an untested challenger proposal.

```python
def _column_periods(headers: tuple[str, ...], periods: Any) -> tuple[str, ...] | None:
    """Map explicit quarter, FY and date headings; no inferred periods or arithmetic."""
    for header in headers:
        cells = re.split(r"\s{2,}", header.strip())[1:]
        if not cells:
            continue
        found = []
        for cell in cells:
            quarter = re.fullmatch(r"Q([1-4]) (\d{4})", cell)
            annual = re.fullmatch(r"FY (\d{4})", cell)
            dated = re.fullmatch(r"(Opening|Q[1-4]|FY) (\d{4}-\d{2}-\d{2})", cell)
            match_count = 0
            for period in periods:
                if (
                    quarter
                    and period.period_type == "QUARTER"
                    and period.fiscal_quarter == int(quarter[1])
                    and re.findall(r"\d{4}", period.fiscal_year) == [quarter[2]]
                ):
                    match_id = period.period_id
                elif (
                    annual
                    and period.period_type == "FY"
                    and re.findall(r"\d{4}", period.fiscal_year) == [annual[1]]
                ):
                    match_id = period.period_id
                elif (
                    dated
                    and str(period.end_date) == dated[2]
                    and (
                        (dated[1] == "Opening" and period.period_type == "PERIOD_END")
                        or (dated[1] == "FY" and period.period_type == "FY")
                        or (
                            dated[1].startswith("Q")
                            and period.period_type == "QUARTER"
                            and period.fiscal_quarter == int(dated[1][1])
                        )
                    )
                ):
                    match_id = period.period_id
                else:
                    continue
                match_count += 1
            if match_count != 1:
                break
            found.append(match_id)
        if len(found) == len(cells) and len(set(found)) == len(found):
            return tuple(found)
    return None
```

```python
    def submit_review(self, payload: str) -> dict[str, Any]:
        with self._locked():
            self._current()
            if (
                self._phase != "analytical"
                or type(payload) is not str
                or len(payload.encode()) > MAX_LINE
            ):
                raise WorkflowError("not_permitted")
            key = (self._binding.ticket_id, self._binding.step_id, "submit_review")
            if self._limits[key] >= MAX_CALLS:
                raise WorkflowError("not_permitted")
            self._limits[key] += 1
            if self._session is None and not any(r.binding == self._binding for r in self._reads):
                raise WorkflowError("not_permitted")
            evidence = (
                self._epoch_calls[-1].source_evidence if self._epoch_calls else SourceEvidence()
            )
            payload_bytes = payload.encode()
            binding = FinancialSubmissionBinding(
                binding=self._binding,
                payload_sha256=_hash(payload_bytes),
                call_ids=tuple(c.call_id for c in self._epoch_calls),
                successful_call_ids=tuple(c.call_id for c in self._epoch_calls if c.status == "ok"),
                source_evidence=evidence,
            )
            if (
                self._session is not None
                and _parse(FinancialSubmissionBinding, self._session.bind_submission(payload))
                != binding
            ):
                raise WorkflowError("identity_mismatch")
            _put(_audit(self._store, "payloads", binding.payload_sha256), payload_bytes)
            _retain(self._store, "bindings", binding)
            stored, resolved, paths, kinds = _filled(self._store, self._binding, payload)
            stored_bytes = stored.encode()
            stored_hash = _hash(stored_bytes)
            _put(_audit(self._store, "payloads", stored_hash), stored_bytes)
            issues = _evidence_issues(self._store, self._binding, stored, evidence)
            self._current()
            attempt = None
            disposition: Literal["valid", "invalid", "refused"] = "refused"
            submitted_step = None
            if not issues:
                if self._binding.step_id == "source_readiness":
                    attempt = submit_cp0_review(self._store, self._binding.ticket_id, stored)
                else:
                    submitted = submit_model_payload(
                        self._store, self._binding.ticket_id, self._binding.step_id, payload
                    )
                    if (
                        submitted.payload,
                        submitted.nulls_resolved,
                        submitted.prefilled,
                        submitted.prefilled_kinds,
                    ) != (stored, resolved, paths, kinds):
                        raise WorkflowError("identity_mismatch")
                    attempt = submitted.journal
                candidates = (
                    attempt.steps
                    if attempt.steps and attempt.steps[-1].step_id == self._binding.step_id
                    else attempt.step_repairs
                )
                if (
                    not candidates
                    or candidates[-1].payload_sha256 != stored_hash
                    or candidates[-1].step_id != self._binding.step_id
                ):
                    raise WorkflowError("identity_mismatch")
                submitted_step = candidates[-1]
                disposition = (
                    "valid"
                    if submitted_step.status == "valid" and not attempt.issues
                    else "invalid"
                )
                issues = submitted_step.issues or attempt.issues
            after = self._store.read()
            try:
                canonical = (
                    SCHEMAS[self._binding.step_id].model_validate_json(stored).content_hash()
                )
            except ValueError:
                canonical = None
            after_hash = after.content_hash()
            record = StageSubmission(
                sequence=len(self._submissions) + 1,
                binding=binding,
                stored_payload_sha256=stored_hash,
                canonical_review_sha256=canonical,
                disposition=disposition,
                issues=issues,
                snapshot_after_sha256=after_hash,
                nulls_resolved=resolved,
                prefilled=paths,
                prefilled_kinds=kinds,
                step_sha256=None if submitted_step is None else submitted_step.content_hash(),
                step_output_sha256=None if submitted_step is None else submitted_step.output_sha256,
            )
            _retain(self._store, "submissions", record)
            self._submissions.append(record)
            step_id = self._binding.step_id
            self._current_sha256 = after_hash
            if attempt is not None:
                if disposition == "valid" and step_id == "source_readiness":
                    try:
                        self._activate(self._store.begin("CP-1"), "source_context")
                    except NotAuthorized as error:
                        self._refusal = "cp1_not_authorized"
                        self._refused_begin = RefusedBegin(
                            snapshot_sha256=after_hash, reason=str(error)
                        )
                        _retain(self._store, "refused-begin", self._refused_begin)
                        self._phase = "not_authorized"
                elif disposition == "valid" and step_id == "quality":
                    self._phase = "promoted"
                elif disposition == "valid":
                    self._activate(attempt, CP1_PROMOTION[len(attempt.steps)])
                elif attempt.status == "pending":
                    self._activate(attempt, step_id)
                elif attempt.number == 0:
                    self._activate(
                        self._store.begin(attempt.module_id),
                        "source_readiness" if attempt.module_id == "CP-0" else "source_context",
                    )
                else:
                    self._phase = "failed"
            return {
                "schema_version": "financial-review-outcome/1",
                "status": disposition,
                "issues": list(issues),
                "step_id": step_id,
                "refusal": self._refusal,
                "snapshot_sha256": self._current_sha256,
                "next_step": self._binding.step_id if self._phase == "analytical" else None,
                "stored_payload_sha256": stored_hash,
                "prefilled": list(paths),
            }
```

```python
def _publication_history(store: Execution, receipt: FinancialSliceReceipt) -> None:
    """Every begun Model attempt and non-begin refusal has its retained actual transition."""
    snapshot = store.read()
    attempts = {a.ticket_id: a for a in snapshot.attempts if a.module_id == "CP-MODEL"}
    recorded = Counter(p.ticket_id for p in receipt.publications if p.ticket_id is not None)
    if recorded != Counter(attempts.keys()) or not 1 <= len(receipt.publications) <= 2:
        raise WorkflowError("identity_mismatch")
    previous_after = None
    for index, publication in enumerate(receipt.publications):
        before = _snapshot(store, publication.snapshot_before_sha256)
        after = _snapshot(store, publication.snapshot_after_sha256)
        if previous_after is not None and previous_after != publication.snapshot_before_sha256:
            raise WorkflowError("identity_mismatch")
        previous_after = publication.snapshot_after_sha256
        if publication.status == "refused":
            if (
                before != after
                or publication.ticket_id is not None
                or publication.files
                or not publication.reason
            ):
                raise WorkflowError("identity_mismatch")
            if not receipt.refusal and not (
                publication.reason.startswith("Output ")
                and "already exists; publish into a new directory" in publication.reason
            ):
                raise WorkflowError("identity_mismatch")
            continue
        before_tickets = {a.ticket_id for a in before.attempts}
        added = [a for a in after.attempts if a.ticket_id not in before_tickets]
        if (
            len(added) != 1
            or added[0].module_id != "CP-MODEL"
            or added[0].ticket_id != publication.ticket_id
            or added[0] != attempts.get(publication.ticket_id)
        ):
            raise WorkflowError("identity_mismatch")
        if tuple(
            a for a in after.attempts if a.ticket_id != publication.ticket_id
        ) != before.attempts or set(publication.files) - set(FILES):
            raise WorkflowError("identity_mismatch")
        attempt = added[0]
        if publication.status == "published":
            if (
                index != len(receipt.publications) - 1
                or attempt.status != "finished"
                or attempt.issues
                or publication.reason is not None
                or receipt.model is None
                or publication.files != receipt.model.files
            ):
                raise WorkflowError("identity_mismatch")
        elif (
            attempt.status != "finished"
            or not attempt.issues
            or attempt.interruption is None
            or not publication.reason
        ):
            raise WorkflowError("identity_mismatch")
```
