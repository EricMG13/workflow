# Triage results (controller summary of the three read-only triage reports, HEAD 559ba54)

## T2 (mx-autonomous, module owners)
| Item | State at HEAD | Disposition |
|---|---|---|
| CP-1D L1 ordinal window | fixed 545e28a (`cp1d.py:644-648`; test `test_method_cp1d.py:1336-1339`) | closed by 545e28a |
| CP-1D L2 mutants | fixed acdaee7 (`test_connect_cp1d.py:727,744,767`) | closed by acdaee7 |
| CP-1D L3 tamper spy | fixed acdaee7 (`test_owner_cp1d.py:361-381`) | closed by acdaee7; owner run deferred |
| CP-1D L5 type: ignore | fixed acdaee7 (none left in cp1d tests; totals noqa 13, type: ignore 5) | closed by acdaee7 |
| CP-1D L6 note vs core | note aligned to the core 545e28a (`cp1d.py:2379-2383`; ruling B3; test `test_connect_cp1d.py:1111`) | closed by 545e28a |
| CP-1D I1 docstring | fixed c824206 (`cp1d.py:2319-2323`) | closed by c824206 |
| CP-2G `next(...)` | fixed 545e28a (`cp2g.py:3182-3184`; test `test_connect_cp2g.py:740`) | closed by 545e28a |
| CP-2D / CP-1D §6 | fixed 545e28a (`_parsed` helper) | closed by 545e28a |
| CP-3D §6 | fixed 30a1f7a (`cp3d.py:2126-2138`) | closed by 30a1f7a |
| CP-3D unresolved reference | open (`cp3d.py:1966-1984`); 0 of 4 frozen summaries carry a reference | fix (mirror eb7e517), batch B2 |
| CP-DR order docstring (item 73 Info) | open (`cpdr.py:289-292`) | fix (docs), batch B2 |
| CP-1 blank scope/source limitation | open; fix belongs in `src/deploy_vii/source_context.py` `validate_source_context` | needs-user |
| (found) CP-2A `_validate_step` raw `model_validate_json` (`cp2a.py:1628`) | open, same §6 class, not on the list | fix with B2 (ruling OI-2) |

## T1 (mx-autonomous, owner core and tests)
| Item | State at HEAD | Disposition |
|---|---|---|
| G1-X guard test gap (`==`→`<=`) | fixed 0e4fd3f (`test_owner_g1x.py:604-614`, guard `owner_workflow.py:939`) | closed by 0e4fd3f |
| G1-X long docstring lines | cited lines reflowed 0e4fd3f; `:12`, `:211`, `:259` still >100 but E501 is not selected (`ruff check` exit 0) | closed by 0e4fd3f; the three remaining lines ride with B3 (same file) |
| CP-2E (a) stale docstring | fixed 0e4fd3f (`test_owner_cp2e.py:5-9`) | closed by 0e4fd3f |
| CP-2E (b) `Cite`/`Cites` copy/asdict | open, latent: nothing copies or `asdict`s them | decided (ruling OI-3) |
| CP-2E (c) empty summary two issues | open (`cp2e.py:819-820`) | fix, batch B2 |
| CP-2A lease text | fixed a70ee52 (`CP2A-OWNER-LEASE.md:69`) | closed by a70ee52 |
| CP-2A forged `Upstream` | open by design (lease v17 builds it by hand) | decided (ruling OI-4) |
| Shared defect test Info | fixed acdaee7 (`test_defect_classes_selfcheck.py:543-554`) | closed by acdaee7 |
| CP-8 L-a | fixed acdaee7 (`test_owner_cp8.py:214-217`) | closed by acdaee7 |
| CP-8 L-b | fixed acdaee7 + lease a70ee52 (`test_owner_cp8.py:220-259`; `CP8-OWNER-LEASE.md:87`) | closed by acdaee7 |
| `_verify_publications` failed CP-MODEL (Stage 4 Info 1) | open (`owner_workflow.py:1795-1801`); store guarantees `issues == ("Interrupted: <interruption>",)` | fix, batch B3, mx-adversary (ruling OI-5) |
| Item 55 rewrite-tournament patches | apply cleanly at HEAD; T1/T2 are the receipt verifier | needs-user (apply vs leave) |
| `drive_cp1` literal/duplication | fixed 0e4fd3f (`s1a_runs.py:282-324`; thin wrappers in cp3c/cp4 runs) | closed by 0e4fd3f |
| `defect_classes.py:858,863` mypy lambda | open, 2 errors at HEAD | fix (functools.partial), batch B1 |

## T3 (mx-autonomous, render, tests, manifest, ruff)
| Item | State at HEAD | Disposition |
|---|---|---|
| D12 `bindings/shipped.py` sha | last record is 8cd0dbc9 = file since 5977ae4; 5c71a311 is the next (report_view) record; strict probe chain=ok | closed by 5977ae4 (W1 finding was a false positive) |
| D12 eleven LEAD records + report_view 3e5b537/24f879a/8aef58d | open: strict probe flags 15 records (cffdf9f ×9, 1a1a140, bb4553b ×2, 3 report_view) | fix, batch B4 (ruling OI-6) |
| ruff `statement_extract.py` TRY004, `report_view.py` SIM102 | open, `src/deploy_vii` | needs-user (recommend leave) |
| ruff `financial_workflow.py:439,446` SIM114 | fixed 3d93a4c | closed by 3d93a4c |
| ruff `financial_workflow.py:914` RUF100 (was :768) | open, CZR file | decided: CZR-blocked (ruling OI-11) |
| ruff `test_legal_render.py:220` C408; `test_cp1_chart_render.py` FURB157 ×4, C408 :433 | open (ruff default rules, no config select) | fix, batch B1 |
| placeholders cp4c/cp4/cp2h "blocked on G2" | open, always skipped | fix (remove; comment names G2 cases), batch B1 (ruling OI-8) |
| `test_shell_css.py:9` first-block parser | open | fix, batch B1 (ruling OI-9) |
| CP-1 chart oracle `cases/charts/expected.json` unpinned | open; PINS 86 paths | fix, batch B4 (ruling OI-7) |
| G2 R2.5 secondary pointers + `cites` normaliser (item 28) | built 3090359, 778fbb3, 715f5a4; genuine reruns green (item 50) | closed by 715f5a4 |
| 11 CP-3C promotion tests | gated on `CP3C_STORE_RUNS=1`; ran green in 5.1 s5 (62 passed) | closed (ran in 5.1 s5); stale docstring `test_owner_cp3c.py:11` rides with B1 |
| cp2d plain-string `tabs` (item 35) | latent; cp2d not in `DEFERRED` | decided (ruling OI-10) |
| DR.6 chip xfail (items 12, 19) | open; oracle already carries `status_chip` | needs-user (recommend draw the chip) |
