"""Sum pytest --durations=0 phases per test from run logs: python -I durations.py <log>... -> TSV."""

import re
import sys
from collections import defaultdict

LINE = re.compile(r"^([0-9.]+)s (setup|call|teardown)\s+(\S+)")
totals: dict[str, float] = defaultdict(float)
for path in sys.argv[1:]:
    for line in open(path, encoding="utf-8"):
        if m := LINE.match(line):
            totals[m.group(3)] += float(m.group(1))
for test, seconds in sorted(totals.items(), key=lambda kv: -kv[1]):
    print(f"{seconds:.2f}\t{test}")
