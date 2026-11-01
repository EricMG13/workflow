"""Tests for cases/prove/affected_tests.py on temporary git repositories."""

import os
import pathlib
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "cases" / "prove" / "affected_tests.py"
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}

BASE_FILES = {
    "src/pkg/__init__.py": "",
    "src/pkg/core.py": "X = 1\n",
    "src/pkg/mid.py": "from pkg import core\n",
    "src/pkg/other.py": "Y = 1\n",
    "tests/test_a.py": "from pkg import mid\n",
    "tests/test_b.py": "def test_b():\n    from pkg import other\n",
    "tests/test_owner_rendering.py": "from pkg import core\n",
    "cases/x-owner/expected.json": "{}\n",
    "tests/test_x.py": 'NAME = "x-owner"\n',
    "docs/a.md": "a\n",
}


def run_git(repo: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, env=ENV, capture_output=True, check=True)


def write(repo: pathlib.Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def run_script(repo: pathlib.Path, tier: str, base: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--tier", tier, base, "HEAD"],
        cwd=repo,
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    run_git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, BASE_FILES)
    run_git(tmp_path, "add", "-A")
    run_git(tmp_path, "commit", "-q", "-m", "base")
    run_git(tmp_path, "tag", "base")
    return tmp_path


def select(repo: pathlib.Path, files: dict[str, str], tier: str = "fast") -> list[str]:
    write(repo, files)
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", "change")
    done = run_script(repo, tier, "base")
    assert done.returncode == 0, done.stderr
    return done.stdout.split()


def test_transitive_importer_selected_unrelated_not(repo: pathlib.Path) -> None:
    assert select(repo, {"src/pkg/core.py": "X = 2\n"}) == ["tests/test_a.py"]


def test_function_level_import_counts(repo: pathlib.Path) -> None:
    assert select(repo, {"src/pkg/other.py": "Y = 2\n"}) == ["tests/test_b.py"]


def test_data_file_selects_test_naming_the_case(repo: pathlib.Path) -> None:
    assert select(repo, {"cases/x-owner/expected.json": '{"a": 1}\n'}) == ["tests/test_x.py"]


def test_pyproject_selects_all(repo: pathlib.Path) -> None:
    assert select(repo, {"pyproject.toml": "[project]\n"}) == [
        "tests/test_a.py",
        "tests/test_b.py",
        "tests/test_x.py",
    ]


def test_docs_only_selects_none(repo: pathlib.Path) -> None:
    assert select(repo, {"docs/a.md": "b\n"}) == []


def test_heavy_file_only_in_heavy_tier(repo: pathlib.Path) -> None:
    assert select(repo, {"src/pkg/core.py": "X = 3\n"}, "heavy") == [
        "tests/test_owner_rendering.py"
    ]


def test_bad_ref_exits_2(repo: pathlib.Path) -> None:
    done = run_script(repo, "fast", "nosuch")
    assert done.returncode == 2
    assert done.stdout == ""
