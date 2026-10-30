"""Weaken each G2 rule on the archive copy; each listed fast test must then fail.
Usage: python probe_weaken_rules.py <tree root> <venv python>. Exit 0 iff every weakening is caught."""
import os, subprocess, sys
from pathlib import Path
tree, py = Path(sys.argv[1]), sys.argv[2]
src = (tree / "tests/test_owner_rendering.py").read_text()
MUTS = {
    "page_cites_no_count": (
        "    assert len(entries) == (1 if required else 0), (fact_id, len(entries), required)\n",
        "    assert len(entries) <= 1\n",
        "test_fast_cp3d_tables_rule_on_real_pages"),
    "rails_without_synth_middle": (
        "            *((_SYNTHETIC_LIMITATION,) if synthetic else ()),\n", "",
        "test_fast_rails_rule_on_real_cp8_pages"),
    "cp4_no_cp1_inherited": (
        "[*literal, *cp1.limitations, *cp1.inherited_limitations]", "[*literal, *cp1.limitations]",
        "test_fast_cp4_pointer_rule_on_real_pages"),
    "cp8_no_pen_check": (
        "    assert all(r[\"kind\"] in allowed for r in body), body\n", "",
        "test_fast_cp8_lines_rule_on_real_pages"),
}
caught = True
for name, (old, new, test) in MUTS.items():
    assert src.count(old) == 1, name
    f = tree / "tests" / f"test_mut_{name}.py"
    f.write_text(src.replace(old, new))
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": "src:tests"}
    r = subprocess.run([py, "-m", "pytest", "-p", "no:cacheprovider", "-q", str(f), "-k", test],
                       cwd=tree, env=env, capture_output=True, text=True)
    f.unlink()
    print(name, "pytest exit", r.returncode, r.stdout.strip().splitlines()[-1])
    caught &= r.returncode == 1
sys.exit(0 if caught else 1)
