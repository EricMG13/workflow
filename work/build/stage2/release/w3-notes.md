# W3 integration notes (collected from W2 reports)

- **B a70ee52.** The CP-2D `run_rate_annual` question is ruled: no reader or oracle change in this release. CP-3C reads `T2E.3.r01` from the bound head, and the lease text records that (YAGNI: no consumer needs it on `Cp2dHead`). Record it as round 5 item 20 at W3.
- **B's TOOL-CONTRACT rows** cite `cases/<cp>-owner/<cp>-view-tree.json` for CP-1C, 1D, 2G, 2H, 3C and 4C. After the merge, check that all six files exist.
- **Stale comment at `cp3c.py:2368`.** It says the oracle consumption block names the run-rate pin; it does not. Fix it at W3 if A1 has not; it is comment-only.
