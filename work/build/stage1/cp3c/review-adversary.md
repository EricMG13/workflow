## Verdict: CHANGES REQUIRED

There are two Medium defects and one Medium test-strength gap. The arithmetic matches the Method in every frozen and ruled state I probed, and all 44 ruled strings occur byte for byte in composed output. The problems are at the edges: states that pass validation but that no ruling settles, and ruled behaviour that no test pins.

Target: `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa5a4817fa00cd287` at adf826a. A three-dot diff against the lane names only `cp3c.py` and its test. The two-dot diff also names `work/build/ledger.md` and `round8-report.md`, but only because the lane has moved past the target (Info). The lane now also carries round 9 rulings (4c35a25). Their only CP-3C content is in D-1: they confirm `Facility currency (<id>)` as a Gap and restate "an unstated term is a Gap".

Probes and runners are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-adversary/`. Probes import from `probe_root/` and mutants run on `copy/`; both are full copies of the target. The shared helper is `plib.py`. A probe exits 1 while its defect is present.

## Findings that count toward the verdict

**M1 (Medium). A facility whose maturity is before D0 gives wrong figures instead of raising.**
- Where: `cp3c.py:511-515`, `:569-577`, `:591`, `:799-803`.
- Scenario: the Q4 2025 register lists a facility maturing 2025-06-30 (overdue, which is plausible "during distress").
  - Months come out as -6, so `amort × months / 12` and `F × months / 12` both flip sign.
  - With a cash burn of F = -6 a year, resources at that maturity rise to 13, above the base of 10.
  - With amortisation of 12 a year, "amortisation before maturity" is -6 and the balloon is 56, above the principal of 50.
- No guard exists upstream: CP-1's `FacilityRecord` (`financial_contracts.py:250-269`) and CP-2D do not refuse it, and grep found no maturity-date check in `deploy_vii`.
- No lease or ruling covers the state (grep of both leases and the rulings found nothing). The module docstring (`:12`) says such a state raises "rather than invent one", but it does not.
- Fix: LEAD rules the behaviour (a raise, or a ruled gap). Until then, fail closed.
- Probe: `probe_past_maturity.py`, exit 1.

**M2 (Medium). A facility id containing a digit makes `compute` raise on a valid submission in a ruled state.**
- Where: `cp3c.py:1628-1632`. `prose.check` is called without `names`, while the claim causes at `:1651-1661`, `:1693` and `:1755` embed the id, as rulings C-3 and 8-B6 require.
- Scenario: `contracts.Identifier` (`contracts.py:14`) allows digits.
  - Id `tl2` with no wall principal raises `CP-3C CP-3C-NEED-01: Bare figure: tl2`.
  - Id `tla1` with seniority not stated raises in LME-01.
  - `notes-2029` passes only because a year label happens to cover the digits.
- No ruling keeps this raise. CP-2D dropped ids from its claims for the same reason (L5).
- Fix options: pass the facility ids as `prose.check(names=…)` (the parameter exists for literal names), with the same names at Stage 2 MC-2; or LEAD rules id-free causes.
- Probe: `probe_digit_id.py`, exit 1.

**M3 (Medium, test strength). Four mutants of ruled or confirmed behaviour survive.**
Each mutant's state is correct in today's code (`probe_survivor_states.py`, exit 0), so these are missing tests, not defects.
- A13 (`:863`): cash interest sign. `copy_negate()` → `abs()` survives, because no test feeds a positive CP-1 cash interest. This is the sign class you asked about.
- A18 (`:802`): the inside-horizon test in `_facility`, `<=` → `<`. The A1 sweep only exercises `wall_position`. Frozen maturity 2027-12-31 with H = 24 sits exactly on this boundary.
- A25 (`:1481-1490`): the controller-confirmed own-line order (currency, maturity date, principal) is not pinned.
- A39 (`:1656`): the 8-B2 cause frame matching on the reason. The collision of a USD facility with no principal and a EUR facility is untested.

**L1 (Low). The T3D.5 Base column takes the last rank's claims, not the largest.**
- Where: `cp3c.py:644-645`. The lease (`:76`), `method_rules.lme_capacity`, the builder's `max(...)` and the cell's own formula text at `:1292` all say "largest".
- They differ only when a principal is negative, which is the B6-ruled negative-total state. Secured 50 plus unsecured -10 gives Base 40, where the largest is 50.
- CP-1 refuses negative principals (`financial_contracts.py:255-257`), so this is reachable only through that ruled state.
- Probe: `probe_negative_principal.py`, exit 1.

**L2 (Low). The precision comment is wrong, and stored amounts do not conserve principal.**
- `cp3c.py:62-65` says the builder runs in Python's default context. It does not: `build.py:19` sets `prec = 60`, while the code uses 28.
- Amortisation 5 a year over 7 months gives stored amortisation plus payable that misses the principal of 100 by 3E-27. The 60-digit value also differs from the stored one.
- The lease says "amounts are exact", which no fixed precision can achieve for /12. No frozen value moves.
- Probe: `probe_precision.py`, exit 1.

## Pre-existing or unruled, for LEAD (not counted)
1. **8-B3 scope.** No own line is written for an unstated annual amortisation or ranking term (`:1474-1497`). CP-2D's term loop (`cp2d.py:722-744`) writes one for amortisation, round 9 D-1 restates "an unstated term is a Gap", and the controller did not confirm this choice. If 8-B3 covers every unstated term, this is a Medium omission. Probe: `probe_unstated_term_lines.py`, exit 1.
2. **Empty register versus unmatched.** An empty CP-1 register with a non-empty CP-2D wall gives "is not in the CP-1 debt register", not C-6's `NO_FACILITY` and its own line (`:669`, `:1477`). The test at `:1029-1034` pins this reading. The 8-B5 rule "an empty register overrides everything" may read the other way. It needs inconsistent heads. Probe: `probe_empty_register.py`, exit 1.
3. **BURDEN-01 collision.** With EBITDA at or below 0 and the payable also missing, the ratio returns the numerator's gap first (`:413-417`), so C-3's "because adjusted EBITDA is zero or negative" is dropped (`:1720`). The output is true but omits the cause; the precedence is unruled. Probe: `probe_burden_collision.py`, exit 1.
4. **Blank limitation.** A whitespace-only or newline limitation passes "states its limitation" and becomes a row in the gaps table (T3D.8). The lease types the field as `str | None`, not `Text`. Probe: `probe_blank_limitation.py`, exit 1.
5. **Negative principal or amortisation.** `min(amort × m / 12, principal)` turns a negative principal into negative amortisation, which adds 10 to every facility's resources (`:577`). A negative amortisation gives a balloon above the principal. CP-1 refuses both, so they are reachable only through the B6 state. The Method formula itself, and the builder, do the same. Probes: `probe_negative_principal.py` and `probe_negative_amort_months.py`, both exit 1.
6. **Info.** An unknown seniority flag is not checked when the secured status is NOT_STATED (`:538-546`). It is unreachable, because CP-1's Literal closes the vocabulary. Probe: `probe_rank_flag_hidden.py`, exit 1.

## Checks that came back clean
- **Ruled strings and precedence.** All 44 ruled strings from C-1 to C-6 and 8-B2/B3/B6 are reachable byte for byte (`probe_ruled_strings.py`, exit 0). The C-4 order, the 8-B5 points and the confirmed choices are implemented.
- **Fail-closed states.** The only raises are invariants, the C-6 unknown-flag raise and the M2 prose raise. There is no `except` anywhere.
- **Quotes, I/O, names.** No quote is read (item 5 does not apply), there is no I/O or store, host, session or render import, and no G1-X §2 name is defined (`probe_static.py`, exit 0).
- **Guard.** The core-local guard copies the product's `_word`/`_near` whitespace handling exactly.
- **Validator.** It skips the repricing texts when both repricing and absence are given, exactly as the builder's `check_payload` does.

## Mutants

The implementer's `cp3c-r6h-8/mutate.py`, run on `copy/`: exit 0, 29 of 29 killed, source restored by sha.

My `mutants.py`, run on `copy/` (output in `mutants.out`): 45 mutants, 30 killed, 15 survived, exit 1, restored (sha c90a63e0…, equal to the original).

| Result | Mutants |
|---|---|
| Killed | A01 half-even rounding · A02 3 dp · A03, A04 denominator rule · A05 no max(0) · A06 no earlier paid · A07 max in place of min · A08 no amortisation cap · A09 flow not prorated · A10 /1000 · A11 pro forma omits added · A12 cover inverted · A14 secured rank swapped · A15 strict claims · A16 rows[0] junior · A17 `wall_position` strict · A20 nearest takes last · A21 zero balloon meaningful · A22 after-horizon keeps inside rows · A23 and in place of or · A24 "leaves" form dropped · A26 facility lines after paths · A27 Gap kind becomes Limitation · A28 negative reason for zero · A29 gap cells lose currency · A30 trace keeps whole period · A31 basis "" · A32 II path must cite · A38 empty-register reading · A43 burden cause on any gap |
| Survived, Medium (M3) | A13 · A18 · A25 · A39 |
| Survived, Low | A33 absence-reason text unchecked · A34 limitation text unchecked · A40 three-word window · A35 unit, A36 whole months, A37 flag, A41 period, A42 duplicate id, A45 prose (untested invariant raises) |
| Survived, Info | A19 leap-400 rule (equivalent for 1901-2099) · A44 order of two wall lines (unruled) |

## Gates (target root)
- pytest: exit 0, 141 passed.
- `ruff check`: exit 0.
- `ruff format --check`: exit 0.
- `MYPYPATH=src mypy --strict`: exit 0.

Not verified: Stage 2 bindings and MC-2 `prose_issues` with citations and names; that no upstream layer outside the files I grepped refuses a pre-D0 maturity (grep only, and a short rtk result proves nothing); real packs with digit-bearing facility ids; cp3c against the current lane tip with round 9 merged; the builder (read, not run); mutmut (all mutants were hand-written); the full suite. Some probes encode my expected behaviour for unruled states (M1, LEAD items 1-5), so a LEAD ruling may change what they should check.
