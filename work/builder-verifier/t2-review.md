# T2 review (mx-precise; saved by the controller)

Spec: CHANGES REQUIRED. Quality: PASS with notes.
- H1 scope.py:66 - paths git quotes (non-ASCII, `"`, `\`, control chars) read as `"..."` and classify neutral; a builder can add new ORACLE files and pass every mode. Fix: `-z`, NUL split; non-UTF-8 handled (Info 2). Probe: scratchpad/t2-review/probe_quoted_paths.sh.
- L1 scope.py:1-11,70 - per-commit mode skips merge commits (evil merge); --role builder catches it; document the bound. Probe: probe_merge_root.sh (a).
- L2 scope.py:73 - root commit in range lists no paths; add `--root`. Probe: probe_root_commit.sh.
- L3 scope.py:22-23,44 - fnmatch `*` crosses `/` (fails closed). Probe: probe_classify.py.
- Info 1 empty range passes with "0 commits checked"; Info 2 non-UTF-8 output would traceback (exit 1, not 2).
Not verified (reviewer): subdirectory runs, user git config such as diff.relative, GitHub behaviour on non-ASCII workflow names.
