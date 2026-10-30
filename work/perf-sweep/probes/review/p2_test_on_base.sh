#!/bin/zsh
# P2 probe: tests/test_validate_tables.py (from 2ded26c) passes on b0ac40c src and 2ded26c src.
# Arg 1 = scratch dir.
PY="/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python"
S="$1"
for rev in b0ac40c 2ded26c; do
  rm -rf "$S/$rev"; mkdir -p "$S/$rev"
  git archive "$rev" src pyproject.toml | tar -x -C "$S/$rev"
  git archive 2ded26c tests/test_validate_tables.py | tar -x -C "$S/$rev"
  echo "== src at $rev"
  (cd "$S/$rev" && "$PY" -m pytest -q -p no:cacheprovider tests/test_validate_tables.py 2>&1 | tail -3)
done
