# T2 scoped re-review (mx-precise; saved by the controller)

Verdict: CHANGES REQUIRED. H1 not fixed for newline paths: scope.py:45-47 `_regex` compiles `**` -> `.*` without re.DOTALL, so `.github/workflows/a\nb.yml`, `cases/a\nb.json`, `docs/superpowers/plans/a\nb.md` classify NEUTRAL (02084968 fnmatch classified them ORACLE). Probes: scratchpad/t2-rereview/probe_quoted_rereview.sh (exit 1, 2 newline checks), probe_classify_rereview.py (exit 1, 3 newline paths).
Fixed: Info 2 (probe_nonutf8.sh 0), L1, L2, L3.
Out of scope: `rev-list -z` needs a recent git (fails closed, exit 2); UnicodeEncodeError on a non-UTF-8 stdout locale.
