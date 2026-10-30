import csv
import io
import sys

path = sys.argv[1]
raw = open(path, newline="").read()
rows = list(csv.reader(io.StringIO(raw)))
hdr = rows[0]
idx = {r[0]: i for i, r in enumerate(rows)}

G2 = "tests/test_owner_rendering.py -k genuine_deferred (51/51 at 23:30; scope delivery rerun on 5cf7f0c 08:13 d1 / 08:33 d0)"
DOM = "native DOM proof of the delivered page (work/build/stage5/dom-proof.md: 25 rows; 6 rails; block links; 31 # links; skip link)"
NAV_OLD = "page not regenerated on the navigator fix 3c90773 (same shell CSS; items 61-62)"
NAV_NEW = "page regenerated on 3c90773: hit test 0 covered; real mouse clicks navigate (items 61-62)"


def render(scope, nav=NAV_OLD):
    return f"verified: G2 genuine deferred {scope} ({G2}) + {DOM}; {nav}"


def owner(suite, ev):
    return (
        f"verified: actual permitted tool calls in the genuine owner run ({suite}; {ev})",
        f"verified: settled head and verified receipt equal the frozen oracle ({suite}; {ev})",
    )


specs = {}
KEYS = [
    "tool_execution",
    "validated_output",
    "downstream_consumption",
    "rendering",
    "case_evidence",
    "unblocking_task",
    "next_evidence",
]


def row(m, tool, val, cons, rend, case, unb, nxt):
    specs[m] = dict(zip(KEYS, [tool, val, cons, rend, case, unb, nxt]))


E_cp4 = "shard cp-4 04:50 on ff9070e: 123 passed 2 skipped with cp2h and cpdr; files and src unchanged to e37b73e"
E_cp3 = "shard cp-3 00:59 on ff9070e: 123 passed 1 skipped with cp2e cpos cp1d; equivalent per the 05:20 note"
E_l3 = "s5-int l3 08:07: 58 passed 1 skipped with test_probe_cp4 and cp2a"
CP2G_T = "tests/test_owner_cp2g.py::test_a6_cp2g_consumes_the_settled_cp2a_and_cp1d_heads"
CP4C_T = "tests/test_owner_cp4c.py::test_a6_cp4c_consumes_the_settled_cp2g_cp2a_and_cp4_heads"

t, v = owner("tests/test_owner_cp1c.py", E_cp4)
row(
    "CP-1C", t, v,
    "open: cp1c_reader pinned facts verified on the genuine head (test_d3_the_reader_exposes_the_pinned_facts_of_the_genuine_head; cp-4 04:50) but no consumer core reads CP-1C",
    render("cp1c-fp03-peers"),
    "cases/cp1c-owner/ (manifest; submissions; expected; cp1c-view-tree.json)",
    "Owner built and run genuinely per docs/CP1C-OWNER-LEASE.md (Stages 2-5); consumption by a named consumer open",
    "A named consumer (CP-3 with CP-1C in READ_OPTIONAL) reads the settled head; CP-5 scope lease; CP-1A/CP-2/CP-5/CP-6 not run",
)

t, v = owner("tests/test_owner_cp1d.py", E_cp3)
row(
    "CP-1D", t, v,
    f"verified: CP-2G reads the settled CP-1D head and binds it as an input (T1D.3.supported.value copied into T2H.2; {CP2G_T}; s4 06:35 56 passed 1 skipped)",
    render("cp1d-fp02-quality (the one-register block fix; all 3 cases pass on I8)"),
    "cases/cp1d-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CP1D-OWNER-LEASE.md (Stages 2-5)",
    "Owner lows L1-L3 L5 L6 I1 (stage2/lows.md); tests/test_owner_cp1d.py::test_downstream_consumption_stays_open_and_no_reader_exists still asserts the own-run open status; CP-5 scope lease",
)

t, v = owner("tests/test_owner_cp2a.py", E_l3)
row(
    "CP-2A", t, v,
    f"verified: CP-2G and CP-4C read the settled CP-2A head (T2B.1 scenario and ebitda_decline; {CP2G_T} s4 06:35; {CP4C_T} s0 07:34)",
    render("cp2a-fp05-downside"),
    "cases/cp2a-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CP2A-OWNER-LEASE.md (Stages 2-5)",
    "Lease narrowing 'every settled operand' and the forged-Upstream Low (stage2/lows.md); CP-5 scope lease",
)

row(
    "CP-2D",
    "verified: actual permitted tool calls in the genuine owner run with store runs (tests/test_owner_cp2d.py with CP2D_STORE_RUNS=1; s3 06:31 on the final code: 30 passed with cpl10)",
    "verified: settled head and verified receipt equal the frozen oracle on the nine store runs (tests/test_owner_cp2d.py with CP2D_STORE_RUNS=1; s3 06:31)",
    "verified: CP-3C reads the settled CP-2D head through cp2d_reader in an actual run (tests/test_owner_cp3c.py::test_store_run_d3_and_the_reader_on_the_closed_heads with CP3C_STORE_RUNS=1; s5 07:09 62 passed with cp3)",
    "unverified (CP-2D has no G2 delivery scope; item 35)",
    "cases/cp2d-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CP2D-OWNER-LEASE.md (Stages 2-5); no rendering scope",
    "A G2 scope for CP-2D (the liquidity-runway and funding-gap oracles use plain-string tabs and would raise TypeError in assert_block_equals_oracle) then a native DOM proof; raw model_validate_json in _validate_step (stage2/lows.md)",
)

t, v = owner("tests/test_owner_cp2e.py", E_cp3)
row(
    "CP-2E", t, v,
    "open: cp2e_reader pinned values verified on the settled head (tests/test_owner_cp2e.py::test_d3_reader_exposes_the_pinned_values_of_the_settled_head; cp-3 00:59) but no consumer core reads CP-2E",
    render("slice-cp2e-sensitivity"),
    "cases/cp2e-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CP2E-OWNER-LEASE.md (Stages 2-5); consumption open",
    "A consumer reads CP-2E (CP-5 scope lease after S1b); Info lows on the test docstring and the empty-summary double issue (stage2/lows.md)",
)

t, v = owner("tests/test_owner_cp2g.py", "s4 06:35 on the final code: 56 passed 1 skipped")
row(
    "CP-2G", t, v,
    f"verified: CP-2H and CP-4C read the settled CP-2G head (tests/test_owner_cp2h.py::test_a6_cp2h_consumes_the_settled_cp2g_head l2 09:59 47 passed 1 skipped; {CP4C_T} s0 07:34)",
    f"verified: G2 genuine deferred cp2g-fp05-forward and cp2g-fp05-forward-gap ({G2}) + {DOM} for both pages; {NAV_OLD}",
    "cases/cp2g-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CP2G-OWNER-LEASE.md (Stages 2-5)",
    "Info low: next() without a default on T2H.7 (stage2/lows.md); CP-5 scope lease",
)

t, v = owner("tests/test_owner_cp2h.py", "l2 09:59 on the final code: 47 passed 1 skipped (empty placeholder cp2h:640)")
row(
    "CP-2H", t, v,
    "open: no consumer core reads CP-2H (CP-3 CP-3D and CP-5 list it as optional and none reads it)",
    render("cp2h-fp05-ratings"),
    "cases/cp2h-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CP2H-OWNER-LEASE.md (Stages 2-5); consumption open",
    "A consumer reads CP-2H; remove the empty placeholder test_a7_g2_renders_the_rating_triggers_block (cp2h:640) or point it at the G2 cases (stage2/lows.md)",
)

t, v = owner("tests/test_owner_cp3.py", "s5 07:09 on the final code: 62 passed with the cp3c store runs; R3 run only")
row(
    "CP-3", t, v,
    "open: the CP-6 run that proves CP-3 consumption (R6) is not run; tests/test_owner_cp3.py asserts that no CP-5 or CP-6 head exists in the R3 run",
    render("cp3-fp01-relative-value (positive and gap)"),
    "cases/cp3-cp6-owner/ (manifest; submissions; expected)",
    "CP-3 half built and run genuinely per docs/CP3-OWNER-LEASE.md (Stages 2-5); CP-6 half not run",
    "The CP-6/R6 run (with CP-5) proves CP-3 consumption; CP-1C into READ_OPTIONAL",
)

t, v = owner("tests/test_owner_cp3c.py", "s5 07:09 on the final code with CP3C_STORE_RUNS=1: 62 passed with cp3")
row(
    "CP-3C", t, v,
    "open: no consumer core reads CP-3C (CP-4C never reads it); cp3c_reader shipped and checked on the closed heads (test_store_run_d3_and_the_reader_on_the_closed_heads; s5 07:09)",
    render("cp3c-fp04-refinancing"),
    "cases/cp3c-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CP3C-OWNER-LEASE.md (Stages 2-5); consumption open",
    "A consumer (a CP-4C amendment or a CP-5 scope lease) reads CP-3C; CP-1A not run on real data (CZR after Stage 5; item 19)",
)

t, v = owner(
    "tests/test_owner_cp3d.py",
    "shard cp-2 00:41 on ff9070e; equivalent per the 05:20 note; the 12 skips in that shard are not itemised per file",
)
row(
    "CP-3D", t, v,
    "open: no consumer core reads CP-3D (CP-3 and CP-6 never read it)",
    render("cp3d-fp03-market", NAV_NEW),
    "cases/cp3d-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CP3D-OWNER-LEASE.md (Stages 2-5); consumption open",
    "A consumer reads CP-3D; raw model_validate_json in _validate_step; RunText check masked by other issues (stage2/lows.md)",
)

t, v = owner("tests/test_owner_cp4.py", E_l3)
row(
    "CP-4", t, v,
    f"verified: CP-4C reads the settled CP-4 head ({CP4C_T}; s0 07:34); CP-4's own run still records consumption open (test_d3_cp4_consumption_stays_open)",
    render("cp4-fp04-covenants"),
    "cases/cp4-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CP4-OWNER-LEASE.md (Stages 2-5)",
    "Remove or replace the empty placeholder test_a7_render_of_the_six_sections_and_two_rails (cp4:497); CP-5 scope lease",
)

t, v = owner(
    "tests/test_owner_cp4c.py",
    "s0 07:34 on the final code: 57 passed 1 skipped; the never-wedges test test_a3_model_text_is_refused_or_verbatim_and_never_wedges (s1) had not finished at 09:59",
)
row(
    "CP-4C", t, v,
    "open: no consumer core reads CP-4C",
    render("cp4c-fp05-recovery"),
    "cases/cp4c-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CP4C-OWNER-LEASE.md (Stages 2-5); one owner test unfinished",
    "Finish s1 (the never-wedges test); empty placeholder test_a7_g2_renders_the_two_recovery_blocks (cp4c:615); a consumer reads CP-4C",
)

t, v = owner(
    "tests/test_owner_cp8.py",
    "s4-int3 05:05: 86 passed; s5-int q 07:21 on the final code: 136 passed with owner cpos and G2 cp8 cpdr",
)
row(
    "CP-8", t, v,
    "open: no consumer core reads CP-8; cp8_reader shipped (tests/test_owner_cp8.py::test_d3_the_reader_exposes_the_pinned_head_and_claims_no_consumption; 05:05)",
    f"verified: G2 genuine deferred cp8-fp01-what-changed positive and no_outcome and refused no_record ({G2}; G2 cp8 x3 at 05:05 and 07:21) + {DOM} incl. the refused page; {NAV_OLD}",
    "cases/cp8-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CP8-OWNER-LEASE.md (Stages 2-5); consumption open",
    "A consumer reads CP-8; lows L-a L-b and the _verify_publications replay of failed publications (stage2/lows.md)",
)

t, v = owner("tests/test_owner_cpdr.py", E_cp4)
row(
    "CP-DR", t, v,
    "open: no consumer core reads CP-DR (CP-5 has no scope lease for it); cpdr_reader shipped",
    render("slice-cpdr-research (partial case)"),
    "cases/cpdr-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CPDR-OWNER-LEASE.md (Stages 2-5); consumption open",
    "A consumer reads CP-DR (CP-5 scope lease); owner lows: long question_id and gap id wedges; RunText check masked; L2b and L2f untested (stage2/lows.md)",
)

t, v = owner(
    "tests/test_owner_cpl10.py",
    "s3 06:31: 30 passed with cp2d; l1 08:15 on the final code: 14 passed with G2 cpl10 and cp2h",
)
row(
    "CP-L10", t, v,
    "open: no consumer core reads CP-L10; cpl10_reader shipped",
    render("slice-cpl10-screen", NAV_NEW),
    "cases/cpl10-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CPL10-OWNER-LEASE.md (Stages 2-5); consumption open",
    "A consumer reads CP-L10; CP-1 accepts a blank scope limitation (predates; stage2/lows.md)",
)

row(
    "CP-OS",
    "n/a: deterministic exception",
    "verified: real verify_owner_run_receipt call on real receipts with the navigation proof (cpos-navigation/1) and the refusal cases (tests/test_owner_cpos.py; cp-3 00:59 on ff9070e; s5-int q 07:21 on the final code: 136 passed)",
    "n/a: deterministic exception",
    "verified: native DOM click acceptance on all 19 delivered pages (work/build/stage5/dom-proof.md: rows; rails; block links; 31 # links; skip link focus; calculation.json; S1a also against the CP-OS oracle case s1a_positive; hit test and real mouse clicks pass on 3c90773 for s1a cp3d cpl10; items 61-63)",
    "cases/cpos-owner/ (manifest; submissions; expected)",
    "Owner built and run genuinely per docs/CPOS-OWNER-LEASE.md (Stages 2-5)",
    "No ledger line records a separate source fix for the shell_skip_link exception (the skip-link focus check passes in the DOM proof); 16 deliveries not regenerated on 3c90773; test_shell_css parser Low (stage2/lows.md)",
)

for m, d in specs.items():
    r = rows[idx[m]]
    for k, val in d.items():
        assert "," not in val and '"' not in val, (m, k, val)
        r[hdr.index(k)] = val

out = io.StringIO()
csv.writer(out, lineterminator="\n").writerows(rows)
open(path, "w", newline="").write(out.getvalue())
print(len(specs), "rows updated")
