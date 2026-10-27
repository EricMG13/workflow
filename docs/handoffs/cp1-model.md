# CP1 financial workflow and deterministic Model handoff

## Reviewed implementation

C1 owns exactly `src/deploy_workflow/financial_workflow.py`,
`tests/test_financial_workflow.py` and this handoff on `codex/cp1-financial-impl`,
based on `4cc75da077c49e173f4599211b22d63a6ed6d188`.
The imported financial core, source host and original source-only workflow are
unchanged. PR MANAGER alone integrates the LEAD-admitted commit.

The producer implementation and its 20 component cases passed. Actual offline
participation now also completed the positive source-to-CP1/Model flow and genuine
missing-source refusal, with sealed receipts and clean EOF exits. The final runtime
ledger below records those exact cases, their independent QA and the earlier
preserved failed-readiness run. Portable C2 rendering and native browser proof are
separate consumer evidence. The C2 helper remains component evidence only.
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
4*1024*1024 characters per input line, and rejects non-finite JSON. Raw review UTF8 is
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
   promotion threshold. Verdict: component verified; actual actor QA subsequently
   used a separately frozen complete inventory and independent pre-promotion review, then matched
   every predicted confidence field. The actual runtime ledger below closes that
   case-specific point without asserting general analytical qualification.
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
Subsequently closed for the actual positive-2/gap cases: analyst participation,
independently reviewed raw QA, real promotion/publication, final verification/seal
and clean process exit; see the runtime ledger below. Still outside this C1 record:
C2 portable render consumption and native browser evidence. Those require actual
consumer receipts and are not silently counted by component or producer tests.

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

## Actual offline participation — final producer ledger

Actual participant evidence is under C1's local
`work/actual-financial-v4/`; it is not a test-helper replay and is not included as
source code in this documentation commit. Trusted setup selected the pack/store/
Model/receipt paths. A persistent operator piped finite JSON lines to the unchanged
CLI and retained each exact request, response, stdout, start/exit record and raw
review. The actor inspected actual source/extraction/projected-input bodies and
authored its reviews. No test imports, component payload replay, direct final
Module construction, provider call or product-setting change occurred.

### Completed positive producer case: positive-2

Directory: `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/work/actual-financial-v4/positive-2`.
The actual final store is `store/`, producer receipt `receipt.json`, canonical Model
publication `model/`. Only this positive-2 directory is the successful actual
positive; the earlier `positive/` is a preserved failed-readiness case.

PID45650 started `2026-10-27T01:30:10.994Z`; actual EOF exited0 at
`2026-10-27T01:47:22.308Z`. Exact command/argv/cwd/code/pack hashes are retained in
`transport/start.json` (Python from the main repository's pinned venv):

```text
/usr/bin/env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -u -m deploy_workflow.financial_workflow \
  --directory '/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/work/actual-financial-v4/positive-2/store' \
  --pack '/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/work/actual-financial-v4/positive-2/pack.json' \
  --model-directory '/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/work/actual-financial-v4/positive-2/model' \
  --receipt '/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/work/actual-financial-v4/positive-2/receipt.json' \
  --participant C1-offline-analyst-corrected-selection
```

This run made 23 real requests/responses: 12 source calls, three source-free input
reads, six valid stage submissions, one actual publication and one final receipt
request. CP0, source context, financials, narrative, readiness and quality all
validated. Fresh source searches/reads and actual three-page extraction covered all
82 printed rows. The actor re-used its own prior judgments only after checking
fresh actual bodies, evidence IDs and new bindings; it never substituted a component
fixture or a prior journal result.

The sole financial correction relative to the earlier valid authored financial
review was `quarter_ids: null`. **These optional selector IDs are quarter
construction IDs, not source period IDs.** The public core's supported None default
selects its available QUARTER constructions, excluding FY and PERIOD_END. Before
quality submission, public read-only `Execution.read`/`step_output` monitoring
verified both actual Model-readiness rows as `ready`, all 94 mandatory checks PASS,
no missing metrics/conflicts/findings, and exactly the four constructions whose
`own_period_id` values are q1-2025 through q4-2025 with the frozen dates/day counts.
No readiness gate or calculation engine changed.

`prequality-model-readiness-verification.json` SHA256:
`9e8aa31e8b43c5993d81b8708ed1afcf7f008b313512d6a5fc0c13efaad661fe`.

Fresh full authentic QualityInputs (20,011,846 bytes), actual read binding, all
42,516 coverage fields, all ceilings/inherited findings, complete raw judgments and
claim/evidence provenance were frozen at `2026-10-27T01:34:24.140Z`, BEFORE quality
submission. All seven consequential findings remained material, including the
missing-information finding. Computed evidence stayed Calculated; located source
records Directly Sourced; gaps/missing values Insufficient Information; analyst
EBITDA-definition comparisons were conservatively Analyst Inference. No ceiling
was upgraded, limitation waived, score/status supplied, or desired score targeted.

| Actual positive-2 artifact | SHA256 |
| --- | --- |
| Pack raw bytes | 374fdaa4fcdf939267958f65421c2af47ab1e5ee9e5a47c0cdf6e271a101e60c |
| Canonical prepared-pack identity | 75a96bc2109cc1e8e2ada38fbc064bf32b0e13cd6367c51536b103bed6fce9cb |
| raw-financials.json | 10f1498a7a2b843ed0621958df2777f87d344d138ca286e232b34e50c0e2f0da |
| raw-narrative.json | a6a0ce7e7b0343e602807a1129782b74976cd1e10e8f0906628d278365bc3deb |
| raw-readiness.json | ca6d31e718b4814e1bd40f347592fb0e1bdab3a73b25f70bfc5a975f66480c5c |
| quality-inputs.json raw/content hash | 27526e1146301ae29b414932c5032000af1907afde1adc7010c65011ffb1210a |
| QualityInputs canonical-register artifact | db592320cbc798cd13c46dd5c10f7fdc81ced742013f14606781137576a53d8f |
| raw-quality.json | c3a08c6305df0d95ebc107c2acd4377dd906444201a8ecaaf1d4b158166652e2 |
| quality-claim-provenance.json | 0b301419e9277c90e7cfd12d5816e02f84a4af8d58119d42953b28f027acd35e |
| quality-freeze.json | 087341b564fd546bd2910795960d17e46615e023f488e7cb22ba0952d91f77b3 |
| Independent pre-promotion expectation | e1696cfa52a978a3a1de1548f5332f623f52da1d5f3366088e60a77fa95d775f |
| actual-vs-independent-qa.json | 896b8578c4a1ece943fabe59bb5d9b1a91d116940415682c6e02b93a69f1288a |
| Final producer receipt raw/content hash | bbbee0075581797e9cb916fe79b939b6c9ef03d521405da1afc3d0946cf8ce61 |
| Final exact snapshot | 17a4027d4a5c45143ae14b04a5966d12b533f1c512fb738eeca243de39b319ef |
| transport/stdout.jsonl | cdc88e6372f1d57de56fa5eb201d71066ff8bacf563d3f5cb0814506449467d4 |
| actual-run-result.json | aa54bcc01d52335fc8436db80c4a12057cfb3899d2ef79dfbf7a5ad4e674240f |

Independent Sol/high semantic/materiality/lineage and Fraction review approved this
fresh binding, not the earlier failed case's binding. Its durable expectation was
saved before actual promotion. The actual retained QualityReport matched EVERY
confidence field: E=520/7, C=1012450/10629, M=7/10, penalty0,
raw=3075554/53145; seven material claims; 40,498/42,516 fields present; score58,
Restricted, Low, nearest-integer ties-to-even. The adopted status cap59 was not
binding. There is no score60 promotion gate. A public read-only settlement monitor
also verified the stored payload differed from the frozen raw QA only by the
supported current-input-hash prefill. Actual Model readiness was rechecked READY
before the publisher was invoked.

Actual CP1 ticket `ea15c6e8-5d7b-444e-a3cf-5507e4a2eb00`, restricted settled result
`87af2b93ae1e2a30df57fe0997c1e89f75bee07932501c7074d51155e59f846f`.
Actual Model ticket `973365ee-2401-4d4a-bc31-51af3343db07`, restricted result
`c6a8d3d0f909342fe4de15ffae183ca9dd9852f94ab21788c12f91f9274e5bbe`, bound to that
exact CP1 result. The actual core publisher and publication verifier succeeded.
Canonical raw files:

| Model file | SHA256 |
| --- | --- |
| model.html | 6be1d2ec79ccb1b6bdbf233c2334bcb10c9c82d289581e491d2cfff9616a8dfc |
| calculation.json | 89b1bf3b48d214ab2b600d7f3ead534f6f2aaa2d8ab44f2cf36214ca99a13d8c |
| receipt.json | 265e6c2dc70f060ca5209564a4fe6aca78ad37a8cfd48ba3b6ac01413a8cc8d4 |

The final producer receipt was sealed only AFTER actual publication and full
workflow verification. Source/test/manifest/pack bytes stayed frozen. The owned
CLI then closed on EOF, exit0, and C1 released the heavy slot. C1 performs no further
Execution writes; C2 consumes portable copies read-only under its own admission.

### Actual missing-source gap case

Directory: `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/work/actual-financial-v4/gap`.
PID42836, `2026-10-27T00:46:53.917Z` to EOF/exit0 at `00:47:31.530Z`.
Actual identity read/search succeeded; actual financial-source read refused
`unavailable`. Its separately authored CP0 review settled restricted with the
conditional financial dependency. Actual CP1 begin raised NotAuthorized. The actual
publisher refused `CP-1 has no accepted or restricted head` before Model begin or
files. The genuine negative receipt then verified/sealed; CP1/Model fields are None,
fixed refusal `cp1_not_authorized`, and no Model directory exists.

- Canonical pack: `ccc256569d1d644eea7d1982ae6cc09140275bcb3bc734048e07a4673dca2a8d`.
- Final snapshot: `4696cdafc9c31f34f723849955891ff61cdb789a61046397a9731d4e44d6b441`.
- Producer receipt raw/content SHA256:
  `929fd192bdd933e6fe1fdbcf11dcd06e0e194f8e7046ee7905df89acb4963896`.
- Raw readiness review: `ee96a3b2bba5248ac661e6d9f0ade9f792917597f7b5cfe5404fd9cb405a63da`.
- Exact six-request/response stdout:
  `e03570d6b05a4fcb93fa33ea602135d8b623046b98fec5300f8de02a0d1f623b`.

This uses its own pack, review, bindings, output and receipt, not the positive case.
It does not assert that blocked Model readiness alone causes publication refusal.

### Preserved actual failure and root-cause corrections

The original `positive/` directory is preserved read-only, including actual source
calls, raw reviews, invalid/refused submissions, independent QA, journals and
monitoring notes. PID42201 ran from `2026-10-27T00:39:44.867Z` to explicit EOF/exit0
at `01:30:00.756Z`. Process exit0 does NOT qualify that analytical case as positive.

Its source-context absence claim first refused because the identity source had not
been searched in that epoch. A genuine identity search returned zero events, then
the SAME authored context payload validated. Its first financial review violated
the adopted one-assessment-per-observation ownership rule by including reported
EBITDA observations in both reported/adjusted assessments. The correction removed
only the second assessment's overlapping IDs, retaining all facts/quotes and both
judgments, and repeated all required source calls/extraction in the new repair
epoch. The actual invalid-to-valid core repair remains in the journal.

That original run later promoted restricted with its exactly predicted QA58, but
trusted monitoring caught genuine Model-readiness BLOCKED before publication:
source period IDs had been supplied to the optional construction-ID selector.
No publisher or final positive receipt was called. No core code, final Module,
private phase or settled journal was changed to hide the failure. LEAD admitted
the distinct positive-2 run with supported None selection, fresh actual calls and
fresh pre-promotion QA review. Original and corrective cases are never mixed.

A first read-only monitor also mistakenly looked for ticket_id on Head; it was
corrected to the public Attempt/result_sha256 join after tracing the schema. The
subsequent readiness assertion exposed the genuine selector error; it was not
waived as a casing issue. No monitor mutated Execution. These operator/data errors
are recorded separately from product defects and component checks.

The only follow-up tracked change is this handoff documentation. Product/test bytes
remain the exact final20-case-reviewed implementation; no additional imported-suite,
provider run or product rewrite was introduced. Core qualification fields remain
implementation-only with analytical/render/native unrun. Actual-case evidence is
scoped to this frozen synthetic historical slice and does not qualify specialist
owners, forecasts, original-document fidelity, audit assurance or real issuers.
