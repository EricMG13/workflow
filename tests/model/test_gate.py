"""R2 live-pause gate: a tripwire on a user-lifted ruling file. No network, no real env."""

import hashlib
import os
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import NoReturn, cast

import pytest

from deploy_workflow.model import adapter as adapter_module
from deploy_workflow.model.adapter import (
    LiveAdapter,
    LivePauseInForce,
    RecordedAdapter,
    check_live_gate,
    live_adapter,
)
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.transport import Request, Response
from deploy_workflow.model.turn import (
    CONFIG_MODELS,
    CONFIG_PROVIDERS,
    Message,
    ModelSpec,
    Provider,
    TurnRequest,
)

REPO = Path(__file__).resolve().parents[2]
GOOD = (
    "# Ruling\nlifts: live-provider-pause\nby: user\ndate: 2026-11-01\n"
    "configs: sol-medium deepseek-max\n"
)


def spec_for(config_id: str) -> ModelSpec:
    model = CONFIG_MODELS[config_id]
    provider = cast(Provider, CONFIG_PROVIDERS[config_id])
    return ModelSpec(config_id, provider, model, config_id.rsplit("-", 1)[1])


def sol_high() -> ModelSpec:
    return ModelSpec("sol-high", "openai", "gpt-6.1-sol", "high")


def ruling(tmp_path: Path, text: str = GOOD) -> tuple[Path, Path]:
    root = tmp_path / "rulings"
    root.mkdir(exist_ok=True)
    path = root / "lift.md"
    path.write_text(text, encoding="utf-8")
    return root, path


def test_gate_passes_for_listed_config(tmp_path: Path) -> None:
    root, path = ruling(tmp_path)
    result = check_live_gate(spec_for("sol-medium"), path, rulings_root=root)
    assert result.path == path.resolve()
    assert len(result.sha256) == 64
    assert str(result.date) == "2026-11-01"


@pytest.mark.parametrize(
    "text",
    [
        GOOD.replace("by: user\n", ""),
        GOOD.replace("by: user", "by: codex"),
        GOOD.replace("2026-11-01", "2026-13-40"),
        GOOD.replace("2026-11-01", "20261101"),
        GOOD.replace("date: 2026-11-01\n", ""),
        GOOD.replace("lifts: live-provider-pause\n", ""),
        GOOD.replace("configs: sol-medium deepseek-max", "configs: sol-medium-2"),
        GOOD.replace("by: user\n", "by: user\nby: codex\n"),
        "",
    ],
)
def test_gate_refuses_bad_ruling(tmp_path: Path, text: str) -> None:
    root, path = ruling(tmp_path, text)
    with pytest.raises(LivePauseInForce):
        check_live_gate(spec_for("sol-medium"), path, rulings_root=root)


def test_gate_refuses_unlisted_config(tmp_path: Path) -> None:
    root, path = ruling(tmp_path)
    with pytest.raises(LivePauseInForce):
        check_live_gate(sol_high(), path, rulings_root=root)


def test_gate_accepts_comma_separated_configs(tmp_path: Path) -> None:
    root, path = ruling(tmp_path, GOOD.replace("sol-medium deepseek-max", "sol-high,sol-medium"))
    check_live_gate(spec_for("sol-medium"), path, rulings_root=root)


def test_gate_refuses_file_outside_root(tmp_path: Path) -> None:
    root, _ = ruling(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text(GOOD, encoding="utf-8")
    with pytest.raises(LivePauseInForce):
        check_live_gate(spec_for("sol-medium"), outside, rulings_root=root)


def test_gate_refuses_dotdot_out_of_root(tmp_path: Path) -> None:
    root, _ = ruling(tmp_path)
    (tmp_path / "outside.md").write_text(GOOD, encoding="utf-8")
    with pytest.raises(LivePauseInForce):
        check_live_gate(spec_for("sol-medium"), root / ".." / "outside.md", rulings_root=root)


def test_gate_refuses_symlink_out_of_root(tmp_path: Path) -> None:
    root, _ = ruling(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text(GOOD, encoding="utf-8")
    link = root / "link.md"
    link.symlink_to(outside)
    with pytest.raises(LivePauseInForce):
        check_live_gate(spec_for("sol-medium"), link, rulings_root=root)


def test_gate_refuses_missing_file(tmp_path: Path) -> None:
    root, _ = ruling(tmp_path)
    with pytest.raises(LivePauseInForce):
        check_live_gate(spec_for("sol-medium"), root / "nope.md", rulings_root=root)


def test_gate_refuses_a_directory(tmp_path: Path) -> None:
    root, _ = ruling(tmp_path)
    with pytest.raises(LivePauseInForce):
        check_live_gate(spec_for("sol-medium"), root, rulings_root=root)


def test_every_real_ruling_refuses_every_config() -> None:
    files = sorted((REPO / "docs" / "rulings").rglob("*"))
    assert files, "the real docs/rulings must exist"
    for path in files:
        if not path.is_file():
            continue
        for config_id in CONFIG_MODELS:
            with pytest.raises(LivePauseInForce):
                check_live_gate(spec_for(config_id), path)


# ------------------------------------------------------------------ F11 trap


class TrapMapping(Mapping[str, str]):
    """Any read raises; touches are also recorded."""

    def __init__(self) -> None:
        self.touched: list[str] = []

    def _trip(self, what: str) -> NoReturn:
        self.touched.append(what)
        raise AssertionError(f"environment touched: {what}")

    def __getitem__(self, key: str) -> str:
        self._trip("__getitem__")

    def __iter__(self) -> Iterator[str]:
        self._trip("__iter__")

    def __len__(self) -> int:
        self.touched.append("__len__")
        raise AssertionError("environment touched: __len__")

    def __contains__(self, key: object) -> bool:
        self._trip("__contains__")

    def get(self, key: str, default: object = None) -> NoReturn:
        self._trip("get")


class Spy:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, environ: Mapping[str, str]) -> Redactor:
        self.calls += 1
        return Redactor()


def test_bad_ruling_touches_no_environment_and_builds_no_redactor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, path = ruling(tmp_path, GOOD.replace("by: user", "by: codex"))
    trap, os_trap, spy = TrapMapping(), TrapMapping(), Spy()
    monkeypatch.setattr(Redactor, "from_environ", spy)
    monkeypatch.setattr(adapter_module, "LIVE_RULINGS_ROOT", root)
    with monkeypatch.context() as scoped:  # pytest itself reads os.environ outside the test body
        scoped.setattr(os, "environ", os_trap)
        for env in (trap, None):
            with pytest.raises(LivePauseInForce):
                live_adapter(spec_for("sol-medium"), path, environ=env)
    assert trap.touched == [] and os_trap.touched == [] and spy.calls == 0


def fake_ok(request: Request) -> Response:
    body = (
        b'{"id":"r1","model":"gpt-6.1-sol","status":"completed","output":[{"type":"message",'
        b'"content":[{"type":"output_text","text":"hi"}]}],'
        b'"usage":{"input_tokens":5,"output_tokens":3}}'
    )
    return Response(200, body, {})


def turn_request() -> TurnRequest:
    return TurnRequest((Message("user", "hi"),), (), 100, "medium")


def test_good_ruling_construction_touches_nothing_and_complete_reads_the_three_key_variables_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, path = ruling(tmp_path)
    monkeypatch.setattr(adapter_module, "LIVE_RULINGS_ROOT", root)
    reads: list[str] = []

    class Counting(Mapping[str, str]):
        def __getitem__(self, key: str) -> str:
            reads.append(key)
            return f"sk-test-fake-{key.lower()}-0123456789"

        def __iter__(self) -> Iterator[str]:
            raise AssertionError("iterated")

        def __len__(self) -> int:
            raise AssertionError("sized")

        def __contains__(self, key: object) -> bool:
            raise AssertionError("contains")

    os_trap = TrapMapping()
    with monkeypatch.context() as scoped:
        scoped.setattr(os, "environ", os_trap)
        adapter = live_adapter(spec_for("sol-medium"), path, transport=fake_ok, environ=Counting())
        assert isinstance(adapter, LiveAdapter) and adapter.ruling == path
        assert adapter.gate.sha256 and reads == []
        reply = adapter.complete(
            turn_request(), invocation_digest="d" * 64, call_index=0, reservation_id="r"
        )
        assert reply.kind == "ok"
        assert set(reads) == {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"}
        before = list(reads)
        adapter.complete(
            turn_request(), invocation_digest="d" * 64, call_index=1, reservation_id="r"
        )
        assert reads == before  # a second complete reads no variable
    assert os_trap.touched == []


def test_classes_are_distinct_and_exported() -> None:
    assert not issubclass(LiveAdapter, RecordedAdapter)
    assert not issubclass(RecordedAdapter, LiveAdapter)


# ------------------------------------------------------------------ fix round 1


def test_gate_sha_is_of_the_file_bytes(tmp_path: Path) -> None:
    root, path = ruling(tmp_path)
    result = check_live_gate(spec_for("sol-medium"), path, rulings_root=root)
    assert result.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "old,new",
    [
        ("by: user", "by: username"),
        ("lifts: live-provider-pause", "lifts: live-provider-pause-x"),
        ("2026-11-01", "2026-1-1"),
    ],
)
def test_gate_is_exact_about_values(tmp_path: Path, old: str, new: str) -> None:
    root, path = ruling(tmp_path, GOOD.replace(old, new))
    with pytest.raises(LivePauseInForce):
        check_live_gate(spec_for("sol-medium"), path, rulings_root=root)


def test_gate_refuses_a_swap_to_a_symlink_after_resolve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, path = ruling(tmp_path, GOOD.replace("by: user", "by: codex"))
    outside = tmp_path / "outside.md"
    outside.write_text(GOOD, encoding="utf-8")
    real_open = os.open
    swapped: list[bool] = []

    def racing_open(target: str | Path, flags: int, mode: int = 0o777) -> int:
        if Path(target) == path.resolve() and not swapped:
            path.unlink()
            path.symlink_to(outside)
            swapped.append(True)
        return real_open(target, flags, mode)

    monkeypatch.setattr(os, "open", racing_open)
    with pytest.raises(LivePauseInForce):
        check_live_gate(spec_for("sol-medium"), path, rulings_root=root)
