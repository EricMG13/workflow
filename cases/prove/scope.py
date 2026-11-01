"""Scope check separating builder and oracle paths (stdlib only).

    python3 -I cases/prove/scope.py BASE HEAD
        exit 1 when a non-merge commit in BASE..HEAD touches both a PRODUCT and an ORACLE path
    python3 -I cases/prove/scope.py --role builder BASE HEAD
        exit 1 when BASE...HEAD touches an ORACLE or PLAN path
    python3 -I cases/prove/scope.py --role oracle BASE HEAD
        exit 1 when BASE...HEAD touches a PRODUCT path

Run from the repository root. A git failure exits 2 with git's stderr; it never passes.
"""

import fnmatch
import subprocess
import sys

ORACLE = (
    "cases/*",
    "src/deploy_vii/methodology.json",
    ".claude/skills/*",
    ".github/*",
    "tests/test_goldens_*.py",
    "tests/test_prove_*.py",
)
PLAN = (
    "docs/superpowers/plans/*",
    "docs/superpowers/specs/*",
    "docs/*-LEASE.md",
    "docs/*-ADDENDUM.md",
)
USAGE = "usage: scope.py [--role builder|oracle] BASE HEAD"


class GitError(Exception):
    pass


def _match(path: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        if pattern.startswith("docs/*-"):
            # single-level glob: the file sits directly under docs/
            if path.count("/") == 1 and fnmatch.fnmatchcase(path, pattern):
                return True
        elif fnmatch.fnmatchcase(path, pattern):
            return True
    return False


def classify(path: str) -> str:
    if _match(path, ORACLE):
        return "ORACLE"
    if _match(path, PLAN):
        return "PLAN"
    if path.startswith(("src/", "tests/")):
        return "PRODUCT"
    return "NEUTRAL"


def git(*args: str) -> list[str]:
    try:
        done = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except OSError as exc:
        raise GitError(f"git {' '.join(args)}: {exc}") from exc
    if done.returncode != 0:
        raise GitError(done.stderr.strip() or f"git {' '.join(args)} exited {done.returncode}")
    return [line for line in done.stdout.splitlines() if line]


def per_commit(base: str, head: str) -> tuple[int, list[str]]:
    shas = git("rev-list", "--no-merges", f"{base}..{head}")
    violations: list[str] = []
    for sha in shas:
        paths = git("diff-tree", "--no-commit-id", "-r", "--name-only", "--no-renames", sha)
        classes = {path: classify(path) for path in paths}
        if "PRODUCT" in classes.values() and "ORACLE" in classes.values():
            violations += [
                f"{sha} {path}: {kind} in per-commit"
                for path, kind in classes.items()
                if kind in ("PRODUCT", "ORACLE")
            ]
    return len(shas), violations


def per_role(role: str, base: str, head: str) -> tuple[int, list[str]]:
    forbidden = {"builder": ("ORACLE", "PLAN"), "oracle": ("PRODUCT",)}[role]
    paths = git("diff", "--name-only", "--no-renames", f"{base}...{head}")
    violations = [
        f"{base}...{head} {path}: {classify(path)} in --role {role}"
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
        print(f"scope: git failed: {exc}", file=sys.stderr)
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
