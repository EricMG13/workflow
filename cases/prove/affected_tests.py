"""Select the test files a change can affect (stdlib only).

    python3 -I cases/prove/affected_tests.py --tier fast  BASE HEAD
    python3 -I cases/prove/affected_tests.py --tier heavy BASE HEAD

Run from the repository root. Prints the selected test files (tests/**/test_*.py), one
repository-relative path per line, sorted; empty output means none. A summary (changed path ->
number of tests it selects) goes to stderr. A git failure or an unparsable .py file exits 2.

Changed paths come from `git diff --name-only --no-renames -z BASE...HEAD` (NUL-split, decoded
utf-8 with surrogateescape). P is a changed path, B its basename, A(P) its directory names
except the first component, D(P) its directory names (the first included), L(F) the string
literals of a .py file F under src/, tests/ or cases/.
- ALL (every test): pyproject.toml, uv.lock, .python-version, any conftest.py, anything under
  .github/, or this script.
- Seeds(P), for every other P whatever its type:
  0. P under docs/, work/ or .claude/: only this rule applies (1-5 do not). Seeds are every F with
     a code literal containing P, or whose code literals, split on "/", hold every name in D(P)
     as a whole segment, plus B when P sits directly in its top directory (docs/X.md). Code
     literals are L(F) without docstrings (the leading string statement of a module, class or
     function body). Empty seeds select nothing.
  1. P is .py under src/, tests/ or cases/: P itself, plus every F with a literal equal to a
     module name of P (dotted name; bare stem for files under tests/).
  2. Every F with a literal containing P, or a literal containing B together with a literal
     (same F) containing a name in D(P), every directory of P, the first included.
  3. P non-.py under src/<dir>/...: every .py directly in P's directory.
  4. Seeds still empty and P non-.py: every F with a literal containing a name in A(P).
  5. Seeds still empty: nothing when P is under docs/, work/, .claude/ or ends in .md; else ALL.
- Tests are the test files reached from the seeds through the reverse import graph (ast, all
  nodes; importlib.import_module with a literal counts); a seed that is a test counts.
The graph and the literals are read from the working tree, which must be HEAD.
HEAVY files are printed only by --tier heavy; every other selected test only by --tier fast.
"""

import argparse
import ast
import fnmatch
import functools
import io
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
SELF = "cases/prove/affected_tests.py"


class GitError(Exception):
    pass


def git(root: pathlib.Path, *args: str) -> str:
    try:
        done = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    except OSError as exc:
        raise GitError(f"git {' '.join(args)}: {exc}") from exc
    if done.returncode != 0:
        stderr = done.stderr.decode("utf-8", "surrogateescape").strip()
        raise GitError(f"git {' '.join(args)}: {stderr}")
    return done.stdout.decode("utf-8", "surrogateescape")


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
            target = arg.value if isinstance(arg, ast.Constant) else None
            if name == "import_module" and isinstance(target, str) and target:
                found |= prefixes(target)
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


@functools.cache
def literals(source: str, docstrings: bool = True) -> tuple[str, ...]:
    """String constants of a module, including the constant parts of f-strings.

    With docstrings=False the leading string statement of a module, class or function body is
    skipped.
    """
    tree = ast.parse(source)
    skip: set[int] = set()
    if not docstrings:
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                first = node.body[0] if node.body else None
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                    skip.add(id(first.value))
    return tuple(
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip
    )


def seeds_for(path: str, py_files: dict[str, str]) -> set[str]:
    """Files a changed path can affect directly: rules 0-4 of the module docstring."""
    base = path.rsplit("/", 1)[-1]
    top_dirs = [d for d in path.split("/")[:-1] if d]  # D(P): every directory, first included
    dirs = top_dirs[1:]  # A(P): without the first component
    seeds: set[str] = set()
    if path.startswith(IGNORED_PREFIXES):
        need = set(top_dirs) if dirs else {*top_dirs, base}
        for f, src in py_files.items():
            ls = literals(src, docstrings=False)
            if any(path in lit for lit in ls) or need <= {s for lit in ls for s in lit.split("/")}:
                seeds.add(f)
        return seeds
    lits = {f: literals(src) for f, src in py_files.items()}
    is_py = path.endswith(".py")
    if is_py and path.startswith(PY_ROOTS):
        mods = {n.removeprefix("bare:") for n in module_names(path)}
        seeds.add(path)
        seeds |= {f for f, ls in lits.items() if mods.intersection(ls)}
    for f, ls in lits.items():
        named = any(path in lit for lit in ls)
        split = any(base in lit for lit in ls) and any(d in lit for lit in ls for d in top_dirs)
        if named or split:
            seeds.add(f)
    if not is_py and path.startswith("src/") and path.count("/") >= 2:
        parent = path.rsplit("/", 1)[0]
        seeds |= {f for f in py_files if f.rsplit("/", 1)[0] == parent}
    if not seeds and not is_py:
        seeds |= {f for f, ls in lits.items() if any(d in lit for lit in ls for d in dirs)}
    return seeds


def selection_for(
    path: str,
    py_files: dict[str, str],
    names: dict[str, set[str]],
    deps: dict[str, set[str]],
) -> set[str]:
    """Tests selected by one changed path; every test when no rule covers it."""
    tests = select_all(list(py_files))
    if (
        path in ALL_NAMES
        or path.rsplit("/", 1)[-1] == "conftest.py"
        or path.startswith(".github/")
        or path == SELF
    ):
        return tests
    seeds = seeds_for(path, py_files)
    if not seeds:
        return set() if path.startswith(IGNORED_PREFIXES) or path.endswith(".md") else tests
    return {t for t in reach(seeds, names, deps) if t in tests}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="select affected test files")
    parser.add_argument("--tier", choices=("fast", "heavy"), required=True)
    parser.add_argument("base")
    parser.add_argument("head")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="surrogateescape")
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
