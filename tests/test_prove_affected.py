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


def add_base(repo: pathlib.Path, files: dict[str, str]) -> None:
    """Add files to the base commit and move the `base` tag onto it."""
    write(repo, files)
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", "base2")
    run_git(repo, "tag", "-f", "base")


def test_path_loaded_py_under_cases(repo: pathlib.Path) -> None:
    add_base(
        repo,
        {
            "cases/tool/check.py": "A = 1\n",
            "tests/test_loader.py": (
                "import importlib.util\nP = ROOT / 'cases' / 'tool' / 'check.py'\n"
                "S = importlib.util.spec_from_file_location('c', P)\n"
            ),
        },
    )
    assert select(repo, {"cases/tool/check.py": "A = 2\n"}) == ["tests/test_loader.py"]


def test_py_pinned_by_hash_literal(repo: pathlib.Path) -> None:
    add_base(
        repo,
        {
            "cases/y-owner/builder/build.py": "B = 1\n",
            "tests/test_pin.py": "PINNED = {'cases/y-owner/builder/build.py': 'abc'}\n",
        },
    )
    assert select(repo, {"cases/y-owner/builder/build.py": "B = 2\n"}) == ["tests/test_pin.py"]


def test_docs_file_read_by_test(repo: pathlib.Path) -> None:
    add_base(
        repo,
        {"docs/DATA.csv": "a\n", "tests/test_docs.py": "P = ROOT / 'docs/DATA.csv'\n"},
    )
    assert select(repo, {"docs/DATA.csv": "b\n"}) == ["tests/test_docs.py"]


def test_md_under_src_read_via_path_parts(repo: pathlib.Path) -> None:
    add_base(
        repo,
        {
            "src/pkg/methods/m.md": "m\n",
            "tests/test_md.py": "P = ROOT / 'src' / 'pkg' / 'methods' / 'm.md'\n",
        },
    )
    assert select(repo, {"src/pkg/methods/m.md": "n\n"}) == ["tests/test_md.py"]


def test_fixture_md_read_via_path_parts(repo: pathlib.Path) -> None:
    add_base(
        repo,
        {
            "tests/fixtures/rep/expected.md": "e\n",
            "tests/test_fix.py": "P = HERE / 'fixtures' / 'rep' / 'expected.md'\n",
        },
    )
    assert select(repo, {"tests/fixtures/rep/expected.md": "f\n"}) == ["tests/test_fix.py"]


def test_module_named_only_in_string_literal(repo: pathlib.Path) -> None:
    add_base(
        repo,
        {"src/pkg/lazy.py": "Z = 1\n", "tests/test_lazy.py": "MODS = ('pkg.lazy',)\n"},
    )
    assert select(repo, {"src/pkg/lazy.py": "Z = 2\n"}) == ["tests/test_lazy.py"]


def test_split_path_literal_of_one_level_file(repo: pathlib.Path) -> None:
    add_base(
        repo,
        {
            "cases/PINS.json": "{}\n",
            "tests/test_split.py": "P = ROOT / 'cases' / 'PINS.json'\n",
            "tests/test_full.py": "Q = 'cases/PINS.json'\n",
        },
    )
    assert "tests/test_split.py" in select(repo, {"cases/PINS.json": '{"a": 1}\n'})


def test_non_ascii_path_is_not_quoted(repo: pathlib.Path) -> None:
    add_base(
        repo,
        {"docs/é.csv": "a\n", "tests/test_uni.py": "P = ROOT / 'docs/é.csv'\n"},
    )
    assert select(repo, {"docs/é.csv": "b\n"}) == ["tests/test_uni.py"]


def test_work_path_not_selected_by_substring_of_unrelated_literal(repo: pathlib.Path) -> None:
    add_base(repo, {"work/bld/ledger.md": "l\n", "tests/test_bldr.py": "K = 'bldr_targets'\n"})
    assert select(repo, {"work/bld/ledger.md": "m\n"}) == []


def test_docs_path_ignores_literal_naming_only_basename_extension(repo: pathlib.Path) -> None:
    add_base(
        repo,
        {
            "docs/rx/manifest.json": "{}\n",
            "tests/test_man.py": "M = 'cases/fin/manifest.json'\nN = 'docstring'\n",
        },
    )
    assert select(repo, {"docs/rx/manifest.json": '{"a": 1}\n'}) == []


def test_docs_path_named_only_in_docstring_selects_nothing(repo: pathlib.Path) -> None:
    add_base(
        repo,
        {
            "docs/X-LEASE.md": "l\n",
            "src/pkg/noted.py": '"""Implements docs/X-LEASE.md."""\n',
            "tests/test_noted.py": "from pkg import noted\n",
        },
    )
    assert select(repo, {"docs/X-LEASE.md": "m\n"}) == []


def test_docs_path_read_by_glob_or_full_path_literal_selects_readers(repo: pathlib.Path) -> None:
    add_base(
        repo,
        {
            "docs/rl/r.md": "r\n",
            "tests/test_glob.py": "FILES = (ROOT / 'docs' / 'rl').glob('*')\n",
            "tests/test_named.py": "P = 'docs/rl/r.md'\n",
        },
    )
    assert select(repo, {"docs/rl/r.md": "s\n"}) == ["tests/test_glob.py", "tests/test_named.py"]


def test_docs_top_file_read_by_segment_literals_selects_reader(repo: pathlib.Path) -> None:
    add_base(
        repo,
        {
            "docs/L-NOTE.md": "n\n",
            "tests/test_note.py": "P = ROOT / 'docs' / 'L-NOTE.md'\n",
        },
    )
    assert select(repo, {"docs/L-NOTE.md": "o\n"}) == ["tests/test_note.py"]
