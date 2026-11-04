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
    "tests/test_earnings_workflow.py": "from pkg import mid\n",
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
        "tests/test_earnings_workflow.py",
        "tests/test_owner_rendering.py",
    ]


def test_bad_ref_exits_2(repo: pathlib.Path) -> None:
    done = run_script(repo, "fast", "nosuch")
    assert done.returncode == 2
    assert done.stdout == ""


def test_empty_diff_selects_no_files(repo: pathlib.Path) -> None:
    for tier in ("fast", "heavy"):
        done = run_script(repo, tier, "HEAD")
        assert done.returncode == 0, done.stderr
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


def test_checkpoint_lists_equal_heavy() -> None:
    import importlib.util

    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("affected_tests_heavy", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    heavy = list(module.HEAVY)
    lines = (root / ".github" / "workflows" / "checkpoint.yml").read_text().splitlines()
    matrix = [
        line.strip()[2:]
        for line in lines
        if line.startswith("          - tests/") and line.strip().endswith(".py")
    ]
    grep = [
        line.strip()[len("-e ") :].rstrip(" \\")
        for line in lines
        if line.strip().startswith("-e tests/")
    ]
    assert matrix == heavy
    assert grep == heavy


def test_fast_heavy_partition_preserves_shared_change_union(repo: pathlib.Path) -> None:
    write(repo, {"src/pkg/core.py": "X = 2\n"})
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", "shared source change")
    fast = run_script(repo, "fast", "base")
    heavy = run_script(repo, "heavy", "base")
    assert fast.returncode == 0, fast.stderr
    assert heavy.returncode == 0, heavy.stderr
    fast_files = set(fast.stdout.split())
    heavy_files = set(heavy.stdout.split())
    assert fast_files.isdisjoint(heavy_files)
    assert "tests/test_earnings_workflow.py" in heavy_files
    assert "tests/test_earnings_workflow.py" not in fast_files
    assert fast_files | heavy_files == {
        "tests/test_a.py",
        "tests/test_owner_rendering.py",
        "tests/test_earnings_workflow.py",
    }


def test_direct_earnings_change_selects_heavy_only(repo: pathlib.Path) -> None:
    write(repo, {"tests/test_earnings_workflow.py": "from pkg import other\n"})
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", "earnings test change")
    fast = run_script(repo, "fast", "base")
    heavy = run_script(repo, "heavy", "base")
    assert fast.returncode == 0, fast.stderr
    assert heavy.returncode == 0, heavy.stderr
    assert fast.stdout.split() == []
    assert heavy.stdout.split() == ["tests/test_earnings_workflow.py"]


def test_heavy_cp1_routes_exist_and_heavy_matrix_is_per_file() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    names = {
        "tests/test_owner_cp1d.py",
        "tests/test_owner_cp2a.py",
        "tests/test_owner_cp2g.py",
        "tests/test_owner_cp2h.py",
        "tests/test_owner_cpl10.py",
        "tests/test_model_testing_pathway.py",
    }
    spec = __import__("importlib.util", fromlist=["spec_from_file_location"])
    loaded = spec.spec_from_file_location("affected_tests_routes", SCRIPT)
    assert loaded is not None and loaded.loader is not None
    module = spec.module_from_spec(loaded)
    loaded.loader.exec_module(module)
    assert names <= set(module.HEAVY)
    assert all((root / name).is_file() for name in names)
    workflow = (root / ".github/workflows/pr-heavy.yml").read_text()
    assert "for file in" not in workflow
    assert 'pytest -v "$TEST_FILE" -m "not live" --durations=25' in workflow
    assert workflow.index("concurrency:") < workflow.index("jobs:")
    assert "cancel-in-progress: true" in workflow


def test_each_new_cp1_promotion_file_routes_directly_to_heavy(repo: pathlib.Path) -> None:
    paths = (
        "tests/test_owner_cp1d.py",
        "tests/test_owner_cp2a.py",
        "tests/test_owner_cp2g.py",
        "tests/test_owner_cp2h.py",
        "tests/test_owner_cpl10.py",
        "tests/test_model_testing_pathway.py",
    )
    for path in paths:
        write(repo, {path: "def test_direct_route():\n    assert True\n"})
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", "add CP1 promotion routes")
    fast = run_script(repo, "fast", "base")
    heavy = run_script(repo, "heavy", "base")
    assert fast.returncode == 0, fast.stderr
    assert heavy.returncode == 0, heavy.stderr
    assert fast.stdout.split() == []
    assert set(heavy.stdout.split()) == set(paths)


def test_fast_shard_allocation_is_disjoint_and_complete() -> None:
    files = sorted(f"tests/test_{i}.py" for i in range(241))
    shards = [files[i::8] for i in range(8)]
    assert len({path for shard in shards for path in shard}) == len(files)
    assert set().union(*(set(shard) for shard in shards)) == set(files)
    assert all(set(shards[i]).isdisjoint(shards[j]) for i in range(8) for j in range(i + 1, 8))


def test_workflow_gates_keep_timeout_events_and_checked_selector() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    fast = (root / ".github/workflows/pr.yml").read_text()
    heavy = (root / ".github/workflows/pr-heavy.yml").read_text()
    assert "timeout-minutes: 30" in fast
    assert "types: [labeled, synchronize, reopened]" in heavy
    assert "heavy-tests" in heavy
    assert (
        'files=$(uv run --frozen python -I cases/prove/affected_tests.py --tier fast "$BASE" HEAD)'
        in fast
    )
    assert (
        'files=$(uv run --frozen python -I cases/prove/affected_tests.py --tier heavy "$BASE" HEAD)'
        in heavy
    )
    assert "set -euo pipefail" in fast and "set -euo pipefail" in heavy


def _workflow_run(name: str) -> str:
    root = pathlib.Path(__file__).resolve().parents[1]
    lines = (root / ".github" / "workflows" / name).read_text().splitlines()
    step = "Affected heavy tests" if name == "pr-heavy.yml" else "Affected fast tests"
    start = lines.index(f"      - name: {step}")
    run = lines.index("        run: |", start)
    body: list[str] = []
    for line in lines[run + 1 :]:
        if line and not line.startswith("          "):
            break
        body.append(line[10:] if line else "")
    assert body
    return "\n".join(body) + "\n"


def _run_workflow(
    tmp_path: pathlib.Path,
    name: str,
    env: dict[str, str],
    *,
    sort_failure: str = "",
    awk_failure: str = "",
    grep_failure: str = "",
) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    log = tmp_path / "calls.log"
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/bin/bash\n"
        'if [[ "$*" == *affected_tests.py* ]]; then\n'
        "  printf '%s' \"${SELECTOR_OUTPUT-}\"\n"
        '  exit "${SELECTOR_STATUS:-0}"\n'
        "fi\n"
        "if [[ \" $* \" == *' pytest '* ]]; then\n"
        "  shift 3\n"
        f"  printf 'CALL\\n' >> {str(log)!r}\n"
        f"  printf '<%s>\\n' \"$@\" >> {str(log)!r}\n"
        '  exit "${PYTEST_STATUS:-0}"\n'
        "fi\n"
        'echo "unexpected uv invocation: $*" >&2\n'
        "exit 97\n",
        encoding="utf-8",
    )
    uv.chmod(0o755)
    if sort_failure:
        sort = bin_dir / "sort"
        sort.write_text(
            f"#!/bin/bash\nprintf '%s\\n' tests/test_partial.py\nexit {int(sort_failure)}\n",
            encoding="utf-8",
        )
        sort.chmod(0o755)
    if awk_failure:
        awk = bin_dir / "awk"
        awk.write_text(
            f"#!/bin/bash\nprintf '%s\\n' tests/test_partial.py\nexit {int(awk_failure)}\n",
            encoding="utf-8",
        )
        awk.chmod(0o755)
    if grep_failure:
        grep = bin_dir / "grep"
        grep.write_text(f"#!/bin/bash\nexit {int(grep_failure)}\n", encoding="utf-8")
        grep.chmod(0o755)
    proc_env = {
        **os.environ,
        **env,
        "BASE": "origin/main",
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "CALL_LOG": str(log),
    }
    done = subprocess.run(
        ["bash", "-c", _workflow_run(name)],
        cwd=pathlib.Path(__file__).resolve().parents[1],
        env=proc_env,
        capture_output=True,
        text=True,
        check=False,
    )
    calls: list[list[str]] = []
    if log.exists():
        for block in log.read_text(encoding="utf-8").split("CALL\n")[1:]:
            calls.append([line[1:-1] for line in block.splitlines() if line])
    return done, calls


def test_heavy_workflow_executes_one_exact_matrix_file_per_child(tmp_path: pathlib.Path) -> None:
    import importlib.util

    root = pathlib.Path(__file__).resolve().parents[1]
    loaded = importlib.util.spec_from_file_location("affected_tests_matrix", SCRIPT)
    assert loaded is not None and loaded.loader is not None
    module = importlib.util.module_from_spec(loaded)
    loaded.loader.exec_module(module)
    workflow = (root / ".github" / "workflows" / "pr-heavy.yml").read_text()
    expected = list(module.HEAVY)
    matrix = [
        line.strip()[2:] for line in workflow.splitlines() if line.startswith("          - tests/")
    ]
    assert matrix == expected and len(matrix) == 25 and len(set(matrix)) == 25
    assert "fail-fast: false" in workflow
    assert "TEST_FILE: ${{ matrix.file }}" in workflow
    assert "cancel-in-progress: true" in workflow
    calls: list[list[str]] = []
    for file in matrix:
        done, child_calls = _run_workflow(
            tmp_path / file.replace("/", "_"),
            "pr-heavy.yml",
            {"TEST_FILE": file, "SELECTOR_OUTPUT": "\n".join(matrix)},
        )
        assert done.returncode == 0, done.stderr
        assert child_calls == [["-v", file, "-m", "not live", "--durations=25"]]
        calls.extend(child_calls)
    assert len(calls) == 25
    assert [call[1] for call in calls] == matrix


@pytest.mark.parametrize("status", [0, 5, 13])
def test_heavy_workflow_propagates_pytest_status(tmp_path: pathlib.Path, status: int) -> None:
    file = "tests/test_owner_cp1d.py"
    done, calls = _run_workflow(
        tmp_path,
        "pr-heavy.yml",
        {
            "TEST_FILE": file,
            "SELECTOR_OUTPUT": "tests/test_owner_cp1d.py\n",
            "PYTEST_STATUS": str(status),
        },
    )
    assert done.returncode == (0 if status in (0, 5) else status), done.stderr
    assert calls == [["-v", file, "-m", "not live", "--durations=25"]]


def test_heavy_workflow_propagates_membership_tool_error(tmp_path: pathlib.Path) -> None:
    done, calls = _run_workflow(
        tmp_path,
        "pr-heavy.yml",
        {
            "TEST_FILE": "tests/test_owner_cp1d.py",
            "SELECTOR_OUTPUT": "tests/test_owner_cp1d.py\n",
        },
        grep_failure="2",
    )
    assert done.returncode == 2
    assert calls == []


@pytest.mark.parametrize(
    ("selector", "matrix_file"),
    [
        ("tests/test_owner_cp1.py\n", "tests/test_owner_cp1d.py"),
        ("tests/test_owner_cp1d.py.extra\n", "tests/test_owner_cp1d.py"),
        ("tests/test_owner_cp1d.py\n", "tests/test_not_heavy.py"),
        ("", "tests/test_owner_cp1d.py"),
    ],
)
def test_heavy_workflow_requires_exact_selected_matrix_member(
    tmp_path: pathlib.Path, selector: str, matrix_file: str
) -> None:
    done, calls = _run_workflow(
        tmp_path,
        "pr-heavy.yml",
        {"TEST_FILE": matrix_file, "SELECTOR_OUTPUT": selector},
    )
    assert done.returncode == 0
    assert calls == []


@pytest.mark.parametrize("failure", ["selector", "sort", "awk"])
def test_fast_workflow_fails_before_pytest_on_selection_pipeline_error(
    tmp_path: pathlib.Path, failure: str
) -> None:
    env = {"SHARD": "0", "SELECTOR_OUTPUT": "tests/test_1.py\ntests/test_2.py\n"}
    if failure == "selector":
        env["SELECTOR_STATUS"] = "2"
    done, calls = _run_workflow(
        tmp_path,
        "pr.yml",
        env,
        sort_failure="23" if failure == "sort" else "",
        awk_failure="41" if failure == "awk" else "",
    )
    assert done.returncode == {"selector": 2, "sort": 23, "awk": 41}[failure]
    assert calls == []


def test_fast_workflow_shards_actual_reverse_file_list_and_empty_results(
    tmp_path: pathlib.Path,
) -> None:
    files = [f"tests/test_{i:02}.py" for i in reversed(range(18))]
    expected = [
        ["tests/test_00.py", "tests/test_08.py", "tests/test_16.py"],
        ["tests/test_01.py", "tests/test_09.py", "tests/test_17.py"],
        ["tests/test_02.py", "tests/test_10.py"],
        ["tests/test_03.py", "tests/test_11.py"],
        ["tests/test_04.py", "tests/test_12.py"],
        ["tests/test_05.py", "tests/test_13.py"],
        ["tests/test_06.py", "tests/test_14.py"],
        ["tests/test_07.py", "tests/test_15.py"],
    ]
    observed: list[list[str]] = []
    for shard, expected_files in enumerate(expected):
        done, calls = _run_workflow(
            tmp_path / f"shard-{shard}",
            "pr.yml",
            {"SHARD": str(shard), "SELECTOR_OUTPUT": "\n".join(files)},
        )
        assert done.returncode == 0, done.stderr
        assert len(calls) == 1
        assert calls[0] == ["-v", *expected_files, "-m", "not live", "--durations=25"]
        observed.append(calls[0][1:-3])
    assert set().union(*(set(shard) for shard in observed)) == set(files)
    assert all(not (set(a) & set(b)) for i, a in enumerate(observed) for b in observed[i + 1 :])
    empty, calls = _run_workflow(
        tmp_path / "empty", "pr.yml", {"SHARD": "0", "SELECTOR_OUTPUT": ""}
    )
    assert empty.returncode == 0 and calls == []
    empty_shard, calls = _run_workflow(
        tmp_path / "empty-shard",
        "pr.yml",
        {"SHARD": "7", "SELECTOR_OUTPUT": "tests/test_0.py\ntests/test_1.py"},
    )
    assert empty_shard.returncode == 0 and calls == []
