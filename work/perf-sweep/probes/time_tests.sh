#!/bin/zsh
# Usage: time_tests.sh <label> <targets-file>   (run from the repo root)
# Runs each pytest target (one per line) in its own process, one at a time, and writes
# work/perf-sweep/runs/<label>/<n>.log plus a summary line per target to summary.tsv:
# target, exit, wall seconds, load average before, load average after, HEAD.
label=$1; targets=$2
py="/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python"
out=work/perf-sweep/runs/$label; mkdir -p $out
base=${TMPDIR:-/tmp}/perf-sweep-$label; rm -rf $base; mkdir -p $base
head=$(git rev-parse --short HEAD); n=0
while IFS= read -r target; do
  [[ -z $target || $target == \#* ]] && continue
  n=$((n+1)); before=$(sysctl -n vm.loadavg | tr -d '{}' | xargs)
  start=$(date +%s)
  "$py" -m pytest -q -p no:cacheprovider --durations=0 --basetemp=$base/$n ${(z)target} > $out/$n.log 2>&1
  code=$?
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$target" $code $(( $(date +%s) - start )) "$before" \
    "$(sysctl -n vm.loadavg | tr -d '{}' | xargs)" $head >> $out/summary.tsv
  rm -rf $base/$n
done < $targets
