#!/bin/zsh
# P1 probe: run the 17e07ba test test_operands_hash_the_producer_once against b0ac40c src and
# against 17e07ba src, in throwaway trees (arg 1 = scratch dir). Expect base: fails `assert 4 == 1`
# only; head: passes.
set -u
PY="/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python"
S="$1"
for label in base head; do
  rm -rf "$S/$label"; mkdir -p "$S/$label"
  rev=b0ac40c; [[ $label == head ]] && rev=17e07ba
  git archive "$rev" src pyproject.toml | tar -x -C "$S/$label"
  git archive 17e07ba tests cases | tar -x -C "$S/$label"
  echo "== $label (src at $rev, tests at 17e07ba)"
  (cd "$S/$label" && "$PY" -m pytest -q -p no:cacheprovider tests/test_earnings_workflow.py -k operands_hash_the_producer_once 2>&1 | tail -15)
  echo "exit=$pipestatus[1]"
done
