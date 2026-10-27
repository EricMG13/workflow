# Task4-A1 — paired-period earnings core handoff

The bounded pure core is implemented and component-verified. It does not complete
CP1B: actual owner/access/settlement, complete selected CP5 consumption and FP02
render/native evidence remain separately leased dependencies.

## Ownership and route

Branch `codex/cp1b-core-a1`; exact base
`f1b3c5c880a616a422ddf87136f56c87f20ccb10`. Preparation branch/commit
`07cf6dee33006d629cee3aab2702cbc590eb5030` preserved. Exactly three owned files:
`src/deploy_workflow/earnings.py`, `tests/test_earnings.py`, this handoff.
All132 baseline source/test/case files matched LEAD's before inventory before
writes and remained unchanged. No shared registry/access/renderer/workflow edits.
Supporting logs/review notes in untracked `work/cp1b-core-a1` are preserved.

LEAD admission `C3-CP1B-CORE-A1-IMPLEMENTATION-1` authorized writes/static checks;
each runtime job below had separate admission. One heavy slot, uncapped disjoint
implementation, paid/provider/live pause and PM-only integration were preserved.
Financial implementation was explicitly dispatched to GPT-6.1 Sol/high agent
`cp1b_core_implementation`; independent sensitive review to Sol/high
`cp1b_sensitive_review`. Distinct Sol/high incumbent/speed/memory/readability/
blind-arbiter agents performed the required tournament. These are actual selected
route records, not hidden model telemetry or changed product settings.

## Contract and final files

| Input / output | SHA256 |
| --- | --- |
| CP1B-CORE-LEASE.md | b32b91f8fdf562d101e3c37cd14336a640f1baeac6d4ced93111fc6bc21d767d |
| cases/earnings/expected.json | 041e2e05cec282658e28a9f99f1c2e93e6f6d8c2ab17d790aad760676a6c2599 |
| Independent pre-code contract review | 526ce2f5e6d0b6104d1c116e2782236b8c2f3c246955a8a8802cf9a31391b3b0 |
| Final earnings.py | 73fa14c1a5ab42be29fd54ce7d9507a0f986e6f7486cec2f5f4bfd4789750896 |
| Final test_earnings.py | c8a2de1b0ba66abe8e2b409f854cbd349ad2ee40e8bb69a1180ec2de75d5d310 |
| Pinned Python runtime | 7c72112b685250b1aec69081696d8fc04040ccefc34505ca56ac48ace7da8d5b |

Only public callable: `build_earnings_delta(ModuleView, prior_period_id,
current_period_id) -> EarningsDeltaReport`, with the exact frozen/slotted records.
It selects actual T4.14 period identities and T4.10 historical Q/FY basis facts,
retaining primary/companion fact IDs and original values. It performs only delta/
permitted growth arithmetic, not CP1 accounting or ratio recomputation. No I/O,
source access, Execution mutation, caller-supplied answers or invented citations.

Q3→Q4 own92-day quarters retain known zero earnings changes and cash/debt+1.25
USDm; net debt remains30. Q3 leverage stays missing, so its change stays missing.
Absent FY2024 retains known FY2025 values and missing prior/delta/applicable growth.
Same/reverse/incompatible and selected PERIOD_END comparisons refuse; unselected
opening PERIOD_END rows remain valid in the full input. Zero prior allows a known
delta but missing growth. Margin changes are percentage points. Arithmetic uses
fresh Context38/HALF_EVEN and restores caller traps/flags, including refusals.

## Actual admitted component checks

Exact focused argv in the C3 clone, with `PYTHONPATH=src` and
`PYTHONDONTWRITEBYTECODE=1`:

`/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python -m pytest -q tests/test_earnings.py`

| Admission | PID | UTC on2026-10-27 | Actual result |
| --- | --- | --- | --- |
| C3-CP1B-A1-RED-1 | 77852 | 08:55:15.292646–08:55:16.343577 | exit1;68 missing-feature assertions |
| C3-CP1B-A1-CAUSAL-1 | 79896 | 09:11:52.917983–09:11:53.262869 | exit1;68 pass/1 opening-row failure |
| C3-CP1B-A1-GREEN-1 | 81475 | 09:17:53.779623–09:17:54.136792 | exit0;71 pass in0.21s |
| C3-CP1B-A1-GREEN-2, LEAD central | 85829 | 09:36:31.872732–09:36:32.216069 | exit0;71 pass in0.19s |

Processes exited naturally; each heavy slot was released after exit. Full logs,
exact argv/runtime/source/test/case before-after pins, PID/UTC/exit are retained in
`work/cp1b-core-a1/{red-1,causal-1,green-1,lead-green-2}.{json,log}`.
All admitted-job input hashes stayed unchanged. Log SHA256 respectively:
`9ea320715e5a598e3aa6ff65edfcb20354bbafe4ea4ebf2001a814a4bccf2dce`,
`414d2d1557cf6e0122d2fbc28892bb158479cfee35a1371836be0ba1dfd2eec8`,
`dcccfc15c6f22e46c20d766f7138bdb5770cdeb9319d03d312014b2ba31a1645`,
`c6f151eaaa200cba9ad4f9d0c498b3f25a9fbc1ae9dced9af675c900f114c65e`.
RED1 proves missing implementation only, not an arithmetic defect.

### Genuine full stored-CP1 projection

Separate LEAD admission `C3-CP1B-A1-ACTUAL-CP1-PROBE-1`, PID85986,
09:37:56.534023–09:37:57.888119UTC, exit0. Actual public helper calls projected
stored CP1 `6d41c0a0b6782e4eace1f93d7b028f89041480b3d69721d6b69cfda4afcea8be`.
Twelve positive points passed132 independent oracle field checks; twelve gap
points retain FY revenue120/EBITDA30/cash20/debt50/net debt30 and no invented prior.
FY/Q4 bases remain distinct; full input/blob and caller context stayed unchanged.
This is real-input component proof, not actual CP1B analytical participation.

Retained in LEAD clone `work/cp1b-preparation/`:
`actual-cp1-probe-record.json` SHA256
`b851f982fb8c89ae09df7177d12025448e845565b67edfcb9d16e4893155977a`;
`actual-cp1-probe.log` SHA256
`8472e6a9a4a736db345616e7a3e25a93fbe2bd4178a6ea6a9cece5a51a33d432`;
executed `actual_cp1_probe.py` SHA256
`b39bb6b7cdffe8450ba3d936427d74c76658dd5d603e00726766875c7bcc6b79`.
Root read the actual records/log, rather than inferring success from narration.

## Confidence review and independent closure

Ranked doubts investigated, with full notes in `work/cp1b-core-a1/confidence-review.md`:

1. Full-register fixture coverage: **confirmed defect**. Eager parsing treated the
   canonical opening row's absent start date as invalid before period selection.
   Actual CAUSAL1 reproduced it. Index-first/selected-duration parsing fixes the
   root; three opening guards,71-pass runs and the genuine-input probe verify it.
2. Zero/missing/conflict/applicability and units: **verified fine** by independent
   twelve-point oracle, nine status combinations, zero denominator,5pp guard and
   no FY/rolling substitution. No financial formula/oracle changed to match code.
3. Decimal context/nonfinite/refusals: **verified fine** by explicit caller traps,
   flags, precision/rounding, no pre-rounding, malformed-value and refusal tests.
4. Provenance/authentication and mutation: **by-design structural only**. IDs refer
   to actual selected facts and input serialization is unchanged; ModuleView alone
   cannot authenticate run/issuer/current attempt or grants. No contrary claim.
5. Types, scope and final diff: five optional-value type errors were corrected
   through explicit narrowing, without ignores. Targeted strict mypy, AST and
   whitespace checks pass; only the three leased files are staged for the commit.

Independent Sol/high implementation review found the opening P1; its fix review
closed that finding, and final exact semantic-source7df8 delta review PASS found
no additional material issue. Exact review receipts are retained in
`work/cp1b-core-a1/sensitive-review.md`. Source/value and pre-code contract reviews
are reused.
No owner/permission/settlement/CP5/render review is inferred.

## No-argument post-edit rewrite tournament

Two material targets: `_point` and `build_earnings_delta`. Impact search found only
public test helper→build→_point, no other product caller/reexport or GitNexus index.
Auxiliary validators/parsers remained outside this capped two-symbol pass and were
covered by confidence/sensitive review. Separate role agents proposed full versions.
A first arbiter accidentally saw incumbent code and was discarded before judgment;
a fresh arbiter read only anonymous snippets and header-only invariants.

**Winner: Snippet C**, applied with a backup. Justification:

- Named return fields make all value-to-field mappings inspectable.
- Expanded conditions/comprehensions expose validation and selection stages.
- Signatures, return types, side effects and bounded complexity stay unchanged.

Blind bracket: A>B, C>A, C>D. Root reviewed the actual diff and normalized AST
against the71-pass incumbent: only local names and same-order named constructor
fields differ. Exact winning semantic source7df8/testsf6ce passed central GREEN2;
source-oracle zero/missing/1.25 and5pp cases provide concrete invariant checks.
Actual genuine-data probe also passed those semantic bytes. Full final target code,
role rationale and verification record are in `work/cp1b-core-a1/tournament.md`.

After probe exit/release, deterministic Ruff fixed only four mechanical lint issues:
source/test import ordering and `Decimal("120")`/`Decimal("30")` test literals to
integer literals. Final source73fa has AST equality to verified7df8 when import
alias ordering is normalized; calculation/selection/return functions are identical. Test pre-style backup
`tests-green2-prestyle.py` hashes to the actual GREEN2 f6ce pin; its normalized AST
comparison and Decimal120/30 exact tuple checks confirm equivalent expectations.
Final Ruff, strict targeted mypy, AST and diff-whitespace checks pass. No semantic
change or additional financial behavior was introduced after the final runtime
proof. This import/test-only cleanup is tournament-exempt; no redundant pytest run.

## Remaining scope and later reuse

All A1 implementation findings are closed. Actual CP1B tool use/settlement, source/
upstream permissions, complete selected CP5 review and FP02 real rendering remain
open dependencies, not input gaps. No module status/QA/promotion rule, causal driver,
guidance, prior-year income or broader nonzero earnings qualification is added.

LEAD reported newer old Codex commit `49d93a98db2972e1bb88db1525d098089d67f740`,
`src/deploy_vii/cp1b_earnings_delta.py`, as a later bridge candidate, distinct from
pinned Claude644155 (which lacks CP1B). Its later frozen-producer/sufficiency/
FinancialBook dependencies are absent here. A1 imports none of that candidate;
committed-byte inspection, minimal closure/lease and PM handling remain prerequisites.
