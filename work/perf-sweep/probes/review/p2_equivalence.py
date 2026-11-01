"""P2 probe: old (b0ac40c) vs new validate_tables give the same outcome on random real inputs.

Run from the worktree root: python .superpowers/sdd/product-plan/probes/p2_equivalence.py
Exit 0 when every outcome (None or exact ValueError message) matches.
"""
import random
import subprocess
import sys

sys.path.insert(0, "src")
import deploy_vii.contracts as c  # noqa: E402

old_src = subprocess.run(
    ["git", "show", "b0ac40c:src/deploy_vii/contracts.py"], capture_output=True, text=True, check=True
).stdout
start = old_src.index("def validate_tables(")
end = old_src.index("\nclass Module(", start)
ns = dict(vars(c))
exec(old_src[start:end], ns)
old = ns["validate_tables"]
new = c.validate_tables
assert old is not new


def outcome(fn, tables, facts):
    try:
        fn(tables, facts)
    except ValueError as e:
        return str(e)
    return None


rng = random.Random(1)
T, R, F = ["ta", "tb", "tc"], ["r1", "r2"], ["value", "other"]
compared, seen = 0, set()
for _ in range(60000):
    facts = tuple(
        c.Fact(fact_id=rng.choice("abcdefg"), label="l", table_id=rng.choice(T),
               row_id=rng.choice(R), field=rng.choice(F), text="x")
        for _ in range(rng.randint(0, 5))
    )
    fact_ids = [f.fact_id for f in facts] + ["zz"]
    tables = []
    for _ in range(rng.randint(0, 3)):
        fields = tuple(rng.choice(F) for _ in range(rng.randint(1, 2)))
        try:
            tables.append(c.ReportTable(
                table_id=rng.choice(T), title="t",
                columns=tuple(c.TableColumn(field=f, label=f if rng.random() < 0.9 else "X") for f in fields),
                rows=tuple(
                    c.TableRow(row_id=rng.choice(R), label="r",
                               fact_ids=tuple(rng.choice(fact_ids) for _ in range(rng.choice([len(fields), len(fields), 1]))))
                    for _ in range(rng.randint(0, 2))
                ),
                interface_id=rng.choice([None, None, "i1", "i2"]),
            ))
        except Exception:
            continue  # generator only: skip inputs the contract itself refuses
    tables = tuple(tables)
    a, b = outcome(old, tables, facts), outcome(new, tables, facts)
    if a != b:
        print("MISMATCH", a, b, tables, facts)
        sys.exit(1)
    compared += 1
    seen.add(a)
print("compared", compared, "outcomes seen:", len(seen))
for s in sorted(seen, key=str):
    print("  ", s)
