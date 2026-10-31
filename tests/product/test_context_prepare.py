"""Pack preparation from a context file: request builder and the ``prepare`` CLI."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import deploy_workflow.context as context_module
from deploy_vii.contracts import PATHWAY_MODULES
from deploy_vii.preparation import SourceRequest, load_pack
from deploy_workflow.context import (
    CONTEXT_SOURCE_ID,
    ContextRefused,
    load_context,
    preparation_request,
)

CASES = Path(__file__).resolve().parents[2] / "cases" / "context"
FIX_MINIMAL = (CASES / "research-minimal.json").read_bytes()
SRC = Path(__file__).resolve().parents[2] / "src"


def test_run_fields_come_from_context() -> None:
    req = preparation_request(
        load_context(FIX_MINIMAL), run_id="ctx-run-1", context_path="context.json", sources=()
    )
    run = req.run
    assert (run.issuer_name, run.issuer_id, str(run.as_of), run.pathway) == (
        "Northbridge Group",
        "northbridge-group",
        "2026-10-31",
        "credit_snapshot",
    )
    assert run.requested_modules == PATHWAY_MODULES["credit_snapshot"]
    assert req.sources[-1] == SourceRequest(
        source_id="context", path="context.json", media_type="text/plain"
    )
    assert CONTEXT_SOURCE_ID == "context"


def test_context_id_collision_refused() -> None:
    clash = SourceRequest(source_id="context", path="x.txt", media_type="text/plain")
    with pytest.raises(ContextRefused):
        preparation_request(
            load_context(FIX_MINIMAL), run_id="r", context_path="context.json", sources=(clash,)
        )


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    return subprocess.run(
        [sys.executable, "-m", "deploy_workflow.context", "prepare", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _setup(tmp_path: Path, raw: bytes = FIX_MINIMAL) -> Path:
    root = tmp_path / "root"
    root.mkdir()
    (root / "context.json").write_bytes(raw)
    (root / "filing.txt").write_text("Revenue was 100.", encoding="utf-8")
    return root


def _args(root: Path, dest: Path, *extra: str, context: str = "context.json") -> list[str]:
    return [
        "--context",
        str(root / context),
        "--root",
        str(root),
        "--run-id",
        "ctx-run-1",
        "--destination",
        str(dest),
        *extra,
    ]


def test_cli_refuses_invalid_context_before_writing(tmp_path: Path) -> None:
    root = _setup(tmp_path, b'{"schema": "context/1"}')
    dest = tmp_path / "pack"
    done = _cli(*_args(root, dest, "--source", "filing=filing.txt:text"))
    assert done.returncode == 2
    with pytest.raises(ContextRefused) as refused:
        load_context(b'{"schema": "context/1"}')
    expected = list(refused.value.problems)
    assert len(expected) > 1
    assert done.stderr.splitlines() == expected
    assert "Traceback" not in done.stderr
    assert not dest.exists()


def test_cli_refuses_huge_integer_without_traceback(tmp_path: Path) -> None:
    root = _setup(tmp_path, b'{"schema": "context/1", "x": ' + b"1" * 5000 + b"}")
    dest = tmp_path / "pack"
    done = _cli(*_args(root, dest, "--source", "filing=filing.txt:text"))
    assert done.returncode == 2
    assert "Traceback" not in done.stderr
    assert done.stderr.splitlines() == ["$: not valid JSON (ValueError)"]
    assert not dest.exists()


def test_cli_refuses_oversize_context_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _setup(tmp_path, b" " * 65)
    dest = tmp_path / "pack"
    monkeypatch.setattr(context_module, "MAX_BYTES", 64)
    args = argparse.Namespace(
        context=str(root / "context.json"),
        root=str(root),
        run_id="ctx-run-1",
        source=[],
        destination=str(dest),
    )
    with pytest.raises(ContextRefused, match="larger than 64 bytes"):
        context_module._run_prepare(args)
    assert not dest.exists()


def test_run_field_errors_use_context_paths() -> None:
    raw = json.loads(FIX_MINIMAL)
    raw["identity"]["issuer_id"] = "a" * 161
    with pytest.raises(ContextRefused) as refused:
        preparation_request(
            load_context(json.dumps(raw).encode()),
            run_id="ok-run",
            context_path="context.json",
            sources=(),
        )
    assert refused.value.problems[0].startswith("identity.issuer_id:")


def test_cli_prepares_pack(tmp_path: Path) -> None:
    root = _setup(tmp_path)
    dest = tmp_path / "pack"
    done = _cli(*_args(root, dest, "--source", "filing=filing.txt:text"))
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == str(dest)
    pack = json.loads((dest / "pack.json").read_text(encoding="utf-8"))
    assert [(s["source_id"], s["status"]) for s in pack["sources"]] == [
        ("filing", "ready"),
        ("context", "ready"),
    ]
    assert load_pack(dest).run.issuer_id == "northbridge-group"


@pytest.mark.parametrize(
    ("extra", "context", "needle"),
    [
        (("--source", "nocolon"), "context.json", "--source"),
        (("--source", "Bad Id=filing.txt:text"), "context.json", "Bad Id"),
        (("--source", "a=filing.txt:docx"), "context.json", "docx"),
        (("--source", "a=filing.txt:text", "--source", "a=filing.txt:text"), "context.json", "a"),
        (("--source", "context=filing.txt:text"), "context.json", "context"),
        ((), "missing.json", "missing.json"),
        ((), "../outside.json", "outside"),
    ],
)
def test_cli_refuses_bad_arguments_before_writing(
    tmp_path: Path, extra: tuple[str, ...], context: str, needle: str
) -> None:
    root = _setup(tmp_path)
    (tmp_path / "outside.json").write_bytes(FIX_MINIMAL)
    dest = tmp_path / "pack"
    done = _cli(*_args(root, dest, *extra, context=context))
    assert done.returncode == 2
    assert needle in done.stderr
    assert "Traceback" not in done.stderr
    assert not dest.exists()


def test_cli_refuses_bad_run_id_before_writing(tmp_path: Path) -> None:
    root = _setup(tmp_path)
    dest = tmp_path / "pack"
    args = _args(root, dest)
    args[args.index("--run-id") + 1] = "Bad Run"
    done = _cli(*args)
    assert done.returncode == 2
    assert "run_id" in done.stderr
    assert "Traceback" not in done.stderr
    assert not dest.exists()
