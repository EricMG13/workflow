"""Mutation probe for tests/test_shell_css.py parser. argv[1] = tree root. Exit 0 iff all expectations hold."""
import re, sys, pathlib
css0 = (pathlib.Path(sys.argv[1]) / "src/deploy_vii/assets/app.css").read_text()
def decl(css, sel):
    m = re.search(re.escape(sel) + r"\s*\{([^}]*)\}", css)
    if not m: return None
    return {k.strip(): v.strip() for k, v in (d.split(":", 1) for d in m.group(1).split(";") if d.strip())}
def passes(css):
    d = decl(css, ".module-list"); return d is not None and d.get("flex-shrink") == "0"
print("occurrences of .module-list:", len(re.findall(r"\.module-list\b", css0)))
fixed = passes(css0)
unfixed = css0.replace(";flex-shrink:0}", "}", 1)
removed = re.sub(r"\.module-list\{[^}]*\}", "", css0)
later_override = css0 + "\n.module-list{flex-shrink:1}\n"
earlier_other = ".x .module-list{flex-shrink:0}\n" + unfixed
res = {"fixed": passes(fixed and css0), "unfixed": passes(unfixed), "removed": passes(removed),
       "later_override(gap)": passes(later_override), "earlier_other_rule(gap)": passes(earlier_other)}
print(res)
ok = res["fixed"] and not res["unfixed"] and not res["removed"]
sys.exit(0 if ok else 1)
