"""Scope check separating builder and oracle paths (stdlib only).

    python3 -I cases/prove/scope.py BASE HEAD
        exit 1 when a non-merge commit in BASE..HEAD touches both a PRODUCT and an ORACLE path
    python3 -I cases/prove/scope.py --role builder BASE HEAD
        exit 1 when BASE...HEAD touches an ORACLE or PLAN path
    python3 -I cases/prove/scope.py --role oracle BASE HEAD
        exit 1 when BASE...HEAD touches a PRODUCT path

Run from the repository root. A git failure exits 2 with git's stderr; it never passes.

Bound: per-commit mode stops a careless mix only. Merge commits are skipped and a builder can
split a mix across commits; the `--role builder` check over the whole range is the boundary.
In patterns, `*` matches within one path segment and `**` matches any depth.
"""

import re
import subprocess
import sys

ORACLE = (
    "cases/**",
    "src/deploy_vii/methodology.json",
    ".claude/skills/**",
    ".github/**",
    "tests/test_goldens_*.py",
    "tests/test_prove_*.py",
)
PLAN = (
    "docs/superpowers/plans/**",
    "docs/superpowers/specs/**",
    "docs/*-LEASE.md",
    "docs/*-ADDENDUM.md",
)
USAGE = "usage: scope.py [--role builder|oracle] BASE HEAD"


class GitError(Exception):
    pass


def _regex(pattern: str) -> re.Pattern[str]:
    parts = re.split(r"(\*\*|\*)", pattern)
    body = "".join(
        ".*" if part == "**" else "[^/]*" if part == "*" else re.escape(part) for part in parts
    )
    return re.compile(body, re.DOTALL)


def _match(path: str, patterns: tuple[str, ...]) -> bool:
    return any(_regex(pattern).fullmatch(path) for pattern in patterns)


def classify(path: str) -> str:
    if _match(path, ORACLE):
        return "ORACLE"
    if _match(path, PLAN):
        return "PLAN"
    if path.startswith(("src/", "tests/")):
        return "PRODUCT"
    return "NEUTRAL"


def git(*args: str) -> list[str]:
    """Run git; return its NUL-separated output decoded as utf-8 with surrogateescape."""
    try:
        done = subprocess.run(["git", *args], capture_output=True, check=False)
    except OSError as exc:
        raise GitError(f"git {' '.join(args)}: {exc}") from exc
    if done.returncode != 0:
        message = done.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(message or f"git {' '.join(args)} exited {done.returncode}")
    return [
        item.decode("utf-8", errors="surrogateescape") for item in done.stdout.split(b"\0") if item
    ]


def printable(text: str) -> str:
    """Escape undecodable bytes so printing a path can never raise."""
    return text.encode("utf-8", errors="backslashreplace").decode("utf-8")


def per_commit(base: str, head: str) -> tuple[int, list[str]]:
    shas = git("rev-list", "--no-merges", "-z", f"{base}..{head}")
    violations: list[str] = []
    for sha in shas:
        paths = git(
            "diff-tree", "--root", "-z", "--no-commit-id", "-r", "--name-only", "--no-renames", sha
        )
        classes = {path: classify(path) for path in paths}
        if "PRODUCT" in classes.values() and "ORACLE" in classes.values():
            violations += [
                f"{sha} {printable(path)}: {kind} in per-commit"
                for path, kind in classes.items()
                if kind in ("PRODUCT", "ORACLE")
            ]
    return len(shas), violations


def per_role(role: str, base: str, head: str) -> tuple[int, list[str]]:
    forbidden = {"builder": ("ORACLE", "PLAN"), "oracle": ("PRODUCT",)}[role]
    paths = git("diff", "-z", "--name-only", "--no-renames", f"{base}...{head}")
    violations = [
        f"{base}...{head} {printable(path)}: {classify(path)} in --role {role}"
        for path in paths
        if classify(path) in forbidden
    ]
    return len(paths), violations


def main(argv: list[str]) -> int:
    role = ""
    if argv[:1] == ["--role"] and len(argv) == 4 and argv[1] in ("builder", "oracle"):
        role, argv = argv[1], argv[2:]
    if len(argv) != 2 or argv[0].startswith("-"):
        print(USAGE, file=sys.stderr)
        return 2
    base, head = argv
    try:
        checked, violations = per_role(role, base, head) if role else per_commit(base, head)
    except GitError as exc:
        print(f"scope: git failed: {printable(str(exc))}", file=sys.stderr)
        return 2
    for line in violations:
        print(line)
    if violations:
        return 1
    unit = "paths" if role else "commits"
    print(f"scope: {checked} {unit} checked, 0 violations")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
