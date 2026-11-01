"""Tests for cases/prove/scope.py on temporary git repositories."""

import importlib.util
import os
import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "cases" / "prove" / "scope.py"
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def git(repo: pathlib.Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=repo, env=ENV, capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def commit(repo: pathlib.Path, *paths: str) -> str:
    count = git(repo, "rev-list", "--all", "--count")
    for rel in paths:
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"{rel}\n{count}\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "c")
    return git(repo, "rev-parse", "HEAD")


def make_repo(tmp_path: pathlib.Path) -> tuple[pathlib.Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "commit", "-q", "--allow-empty", "-m", "root")
    return repo, git(repo, "rev-parse", "HEAD")


def run(repo: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args],
        cwd=repo,
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
    )


def test_mixed_commit_fails_per_commit(tmp_path: pathlib.Path) -> None:
    repo, base = make_repo(tmp_path)
    sha = commit(repo, "src/a.py", "cases/x/expected.json")
    done = run(repo, base, "HEAD")
    assert done.returncode == 1
    assert f"{sha} src/a.py: PRODUCT in per-commit" in done.stdout
    assert f"{sha} cases/x/expected.json: ORACLE in per-commit" in done.stdout


def test_separate_commits_pass_per_commit(tmp_path: pathlib.Path) -> None:
    repo, base = make_repo(tmp_path)
    commit(repo, "src/a.py", "tests/test_a.py")
    commit(repo, "cases/x/expected.json", "tests/test_goldens_x.py")
    done = run(repo, base, "HEAD")
    assert done.returncode == 0, done.stdout
    assert done.stdout.strip() == "scope: 2 commits checked, 0 violations"


def test_builder_range_touching_lease_or_methodology_fails(tmp_path: pathlib.Path) -> None:
    repo, base = make_repo(tmp_path)
    commit(repo, "src/a.py", "docs/X-LEASE.md", "src/deploy_vii/methodology.json")
    done = run(repo, "--role", "builder", base, "HEAD")
    assert done.returncode == 1
    assert "docs/X-LEASE.md: PLAN in --role builder" in done.stdout
    assert "src/deploy_vii/methodology.json: ORACLE in --role builder" in done.stdout
    assert "src/a.py" not in done.stdout


def test_builder_range_with_product_only_passes(tmp_path: pathlib.Path) -> None:
    repo, base = make_repo(tmp_path)
    commit(repo, "src/a.py", "tests/test_a.py", "notes.txt")
    done = run(repo, "--role", "builder", base, "HEAD")
    assert done.returncode == 0, done.stdout
    assert done.stdout.strip() == "scope: 3 paths checked, 0 violations"


def test_oracle_range_touching_src_fails(tmp_path: pathlib.Path) -> None:
    repo, base = make_repo(tmp_path)
    commit(repo, "cases/x/expected.json", "src/a.py")
    done = run(repo, "--role", "oracle", base, "HEAD")
    assert done.returncode == 1
    assert "src/a.py: PRODUCT in --role oracle" in done.stdout
    assert "cases/x" not in done.stdout


def test_bad_ref_exits_2(tmp_path: pathlib.Path) -> None:
    repo, base = make_repo(tmp_path)
    for args in ((base, "nope"), ("--role", "builder", "nope", "HEAD")):
        done = run(repo, *args)
        assert done.returncode == 2
        assert "git failed" in done.stderr
        assert "scope:" not in done.stdout


def test_quoted_path_oracle_in_mixed_commit_fails_per_commit(tmp_path: pathlib.Path) -> None:
    repo, base = make_repo(tmp_path)
    sha = commit(repo, "cases/x/café.json", "src/a.py")
    done = run(repo, base, "HEAD")
    assert done.returncode == 1
    assert f"{sha} cases/x/café.json: ORACLE in per-commit" in done.stdout


def test_quoted_path_workflow_fails_builder_role(tmp_path: pathlib.Path) -> None:
    repo, base = make_repo(tmp_path)
    commit(repo, "src/a.py", ".github/workflows/café.yml")
    done = run(repo, "--role", "builder", base, "HEAD")
    assert done.returncode == 1
    assert ".github/workflows/café.yml: ORACLE in --role builder" in done.stdout


def test_root_commit_in_range_is_checked(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "root"
    repo.mkdir()
    git(repo, "init", "-q")
    commit(repo, "src/a.py", "cases/x/e.json")
    git(repo, "checkout", "-q", "--orphan", "other")
    git(repo, "rm", "-rqf", ".")
    git(repo, "commit", "-q", "--allow-empty", "-m", "other")
    other = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-")
    done = run(repo, other, "HEAD")
    assert done.returncode == 1
    assert "src/a.py: PRODUCT in per-commit" in done.stdout


def test_glob_star_stays_in_one_segment() -> None:
    spec = importlib.util.spec_from_file_location("scope", SCRIPT)
    assert spec is not None and spec.loader is not None
    scope = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scope)
    assert scope.classify("tests/test_goldens_a.py") == "ORACLE"
    assert scope.classify("tests/test_goldens_a/helper.py") == "PRODUCT"
    assert scope.classify("cases/a/b/c.json") == "ORACLE"
    assert scope.classify("docs/sub/X-LEASE.md") == "NEUTRAL"
    assert scope.classify("docs/superpowers/plans/a/b.md") == "PLAN"
