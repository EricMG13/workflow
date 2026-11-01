"""Select the test files a change can affect (stdlib only).

    python3 -I cases/prove/affected_tests.py --tier fast  BASE HEAD
    python3 -I cases/prove/affected_tests.py --tier heavy BASE HEAD

Run from the repository root. Prints the selected test files (tests/**/test_*.py), one
repository-relative path per line, sorted; empty output means none. A summary (changed path ->
number of tests it selects) goes to stderr. A git failure or an unparsable .py file exits 2.

Changed paths come from `git diff --name-only --no-renames BASE...HEAD`. Selection:
- every test when pyproject.toml, uv.lock, .python-version, a conftest.py, anything under
  .github/, this script, or a path no rule below covers (outside docs/, work/, .claude/, *.md)
  changes;
- a changed .py under src/, tests/ or cases/ selects the tests that reach it through the import
  graph (all ast nodes; importlib.import_module with a literal counts) and itself if a test;
- a changed non-.py file under src/<dir>/ counts as a change to every .py under that dir;
- a changed non-.py file under cases/<name>/, tests/fixtures/<name>/ or directly under tests/
  selects, through the graph, every .py under tests/ or cases/ whose source contains <name>
  (the file name for a file directly under tests/).
HEAVY files are printed only by --tier heavy; every other selected test only by --tier fast.
"""

import argparse
import ast
import fnmatch
import pathlib
import subprocess
import sys

HEAVY = (
    "tests/test_owner_rendering.py",
    "tests/test_owner_workflow.py",
    "tests/test_owner_s1a.py",
    "tests/test_financial_workflow.py",
    "tests/test_financial_render.py",
)
ALL_NAMES = ("pyproject.toml", "uv.lock", ".python-version")
IGNORED_PREFIXES = ("docs/", "work/", ".claude/")
PY_ROOTS = ("src/", "tests/", "cases/")


class GitError(Exception):
    pass


def git(root: pathlib.Path, *args: str) -> str:
    try:
        done = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=False
        )
    except OSError as exc:
        raise GitError(f"git {' '.join(args)}: {exc}") from exc
    if done.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout


def module_names(path: str) -> set[str]:
    """Names a .py file can be imported by (bare:<stem> for tests importing each other)."""
    parts = path[:-3].split("/")
    names: set[str] = set()
    if parts[0] == "src":
        parts = parts[1:]
    elif parts[0] == "tests":
        names.add("bare:" + parts[-1])
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if parts:
        names.add(".".join(parts))
    return names


def prefixes(dotted: str) -> set[str]:
    bits = dotted.split(".")
    return {".".join(bits[: i + 1]) for i in range(len(bits))}


def package_of(path: str) -> list[str]:
    parts = path[:-3].split("/")
    if parts[0] == "src":
        parts = parts[1:]
    return parts[:-1]


def imports_of(path: str, source: str) -> set[str]:
    tree = ast.parse(source, filename=path)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found |= prefixes(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                pkg = package_of(path)
                if node.level - 1 > len(pkg):
                    continue
                base = pkg[: len(pkg) - (node.level - 1)]
                module = ".".join([*base, *(node.module.split(".") if node.module else [])])
            else:
                module = node.module or ""
            if module:
                found |= prefixes(module)
            for alias in node.names:
                if alias.name != "*" and module:
                    found.add(f"{module}.{alias.name}")
                elif alias.name != "*":
                    found.add(alias.name)
        elif isinstance(node, ast.Call) and node.args:
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            arg = node.args[0]
            if name == "import_module" and isinstance(arg, ast.Constant):
                if isinstance(arg.value, str) and arg.value:
                    found |= prefixes(arg.value)
    if path.startswith("tests/"):
        found |= {"bare:" + n for n in found if "." not in n}
    return found


def is_test(path: str) -> bool:
    return path.startswith("tests/") and fnmatch.fnmatch(path.rsplit("/", 1)[-1], "test_*.py")


def select_all(files: list[str]) -> set[str]:
    return {f for f in files if is_test(f)}


def reach(seeds: set[str], names: dict[str, set[str]], deps: dict[str, set[str]]) -> set[str]:
    """Files that depend, transitively, on any seed (seeds themselves included)."""
    seen = set(seeds)
    queue = list(seeds)
    while queue:
        path = queue.pop()
        targets = names[path] if path in names else module_names(path)
        for other, imported in deps.items():
            if other not in seen and imported & targets:
                seen.add(other)
                queue.append(other)
    return seen


def selection_for(
    path: str,
    py_files: dict[str, str],
    names: dict[str, set[str]],
    deps: dict[str, set[str]],
) -> set[str]:
    """Tests selected by one changed path; every test when no rule covers it."""
    tests = select_all(list(py_files))
    base = path.rsplit("/", 1)[-1]
    if path in ALL_NAMES or base == "conftest.py" or path.startswith(".github/"):
        return tests
    if path == "cases/prove/affected_tests.py":
        return tests
    if path.startswith(IGNORED_PREFIXES) or path.endswith(".md"):
        return set()
    if path.endswith(".py") and path.startswith(PY_ROOTS):
        return {t for t in reach({path}, names, deps) if t in tests}
    parts = path.split("/")
    if parts[0] == "src" and len(parts) > 2:
        prefix = "/".join(parts[:2]) + "/"
        seeds = {p for p in py_files if p.startswith(prefix)}
        return {t for t in reach(seeds, names, deps) if t in tests}
    needle = ""
    if parts[0] == "cases" and len(parts) > 2:
        needle = parts[1]
    elif parts[:2] == ["tests", "fixtures"] and len(parts) > 3:
        needle = parts[2]
    elif parts[0] == "tests" and len(parts) == 2:
        needle = parts[1]
    if not needle:
        return tests
    seeds = {p for p, src in py_files.items() if needle in src}
    return {t for t in reach(seeds, names, deps) if t in tests}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="select affected test files")
    parser.add_argument("--tier", choices=("fast", "heavy"), required=True)
    parser.add_argument("base")
    parser.add_argument("head")
    args = parser.parse_args(argv)
    try:
        root = pathlib.Path(git(pathlib.Path.cwd(), "rev-parse", "--show-toplevel").strip())
        diff = git(root, "diff", "--name-only", "--no-renames", "-z", f"{args.base}...{args.head}")
        listed = git(root, "ls-files", "-z", "--", *PY_ROOTS).split("\0")
        py_files: dict[str, str] = {}
        for path in sorted(p for p in listed if p.endswith(".py")):
            py_files[path] = (root / path).read_text(encoding="utf-8")
        names = {p: module_names(p) for p in py_files}
        deps = {p: imports_of(p, src) for p, src in py_files.items()}
    except (GitError, OSError, SyntaxError, UnicodeDecodeError) as exc:
        print(f"affected_tests: {exc}", file=sys.stderr)
        return 2
    selected: set[str] = set()
    for path in sorted(p for p in diff.split("\0") if p):
        hit = selection_for(path, py_files, names, deps)
        print(f"affected_tests: {path} -> {len(hit)}", file=sys.stderr)
        selected |= hit
    heavy = set(HEAVY)
    chosen = selected & heavy if args.tier == "heavy" else selected - heavy
    for path in sorted(chosen):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
