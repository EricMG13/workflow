#!/bin/zsh
# Usage: [TREE=<source tree>] time_tests.sh <label> <targets-file>   (run from the repo root)
# TREE (default .) is the checkout whose src/tests run, e.g. a `git archive` snapshot of a base.
# Runs each pytest target (one per line) in its own process, one at a time, and writes
# work/perf-sweep/runs/<label>/<n>.log plus a summary line per target to summary.tsv:
# target, exit, wall seconds, load average before, load average after, HEAD, peak RSS bytes.
label=$1; targets=$2
py="/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python"
out=$PWD/work/perf-sweep/runs/$label; mkdir -p $out; tree=${TREE:-.}
base=${TMPDIR:-/tmp}/perf-sweep-$label; rm -rf $base; mkdir -p $base
head=${HEAD_LABEL:-$(git -C $tree rev-parse --short HEAD 2>/dev/null || echo snapshot)}; n=0
while IFS= read -r target; do
  [[ -z $target || $target == \#* ]] && continue
  n=$((n+1)); before=$(sysctl -n vm.loadavg | tr -d '{}' | xargs)
  start=$(date +%s)
  (cd $tree && /usr/bin/time -l "$py" -m pytest -q -p no:cacheprovider --durations=0 --basetemp=$base/$n ${(z)target}) > $out/$n.log 2>&1
  code=$?
  rss=$(awk '/maximum resident set size/ {print $1}' $out/$n.log)
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$target" $code $(( $(date +%s) - start )) "$before" \
    "$(sysctl -n vm.loadavg | tr -d '{}' | xargs)" $head "$rss" >> $out/summary.tsv
  rm -rf $base/$n
done < $targets
