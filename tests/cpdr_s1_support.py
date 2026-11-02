"""O7b-1c S1 test support: the cp_dr=False run record, and the research case materialised on disk.

``off_run_record`` runs the same inputs ``tests/fixtures/cpdr_off_run_5d4710b1.json`` was made from
(by this function, run on the 5d4710b1 code before any S1 edit) and returns the comparable record.
Names and files the run makes differently every time (call ids, snapshot hashes, timestamps) are
normalised to ``*`` and carry no hash; every other file is pinned by sha256.
"""

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from deploy_workflow.model.adapter import recorded_adapter
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.run_inputs import CaseSource
from deploy_workflow.run_pathway import run_pathway

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "cpdr_off_run_5d4710b1.json"
MODEL = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")
HTML = b"<html><body><table><tr><td>Revenue</td><td>1,234</td></tr></table></body></html>"
_VOLATILE = (
    re.compile(r"^(calls\.jsonl|execution/current)$"),
    re.compile(r"^execution/snapshots/[0-9a-f]{64}\.json$"),
    re.compile(r"^execution/owner-run-audit/begins/[0-9a-f]{64}$"),
    re.compile(r"^execution/owner-run-audit/reservations/call-[0-9a-f]{32}(\.settled)?$"),
)


def _normal(name: str) -> tuple[str, bool]:
    for pattern in _VOLATILE:
        if pattern.match(name):
            return re.sub(r"[0-9a-f]{32,64}", "*", name), True
    return name, False


def tree_record(run_dir: Path) -> list[list[str | None]]:
    """Every file under ``run_dir`` except ``run.json`` (pinned as text, since it names the input
    paths): ``[name, sha256]``, with a ``*`` name and no hash where the run varies it every time."""
    record: list[list[str | None]] = []
    for path in sorted(run_dir.rglob("*")):
        relative = str(path.relative_to(run_dir))
        if path.is_file() and relative != "run.json":
            name, volatile = _normal(relative)
            record.append(
                [name, None if volatile else hashlib.sha256(path.read_bytes()).hexdigest()]
            )
    return sorted(record, key=lambda row: str(row[0]))


def off_run_record(base: Path) -> dict[str, Any]:
    """Run the pinned cp_dr=False scenario under ``base`` and return its comparable record."""
    inputs = base / "in"
    inputs.mkdir(parents=True)
    (inputs / "a.html").write_bytes(HTML)
    (inputs / "b.txt").write_bytes(b"plain text\n")
    recordings = base / "recordings"
    recordings.mkdir()
    run_pathway(
        case_id="case-1",
        sources=[
            CaseSource("s1", inputs / "a.html", "text/html"),
            CaseSource("s2", inputs / "b.txt", "text/plain"),
        ],
        context=ROOT / "cases/context/research-minimal.json",
        pathway="credit_snapshot",
        model=MODEL,
        adapter=recorded_adapter(MODEL, recordings),
        cap_usd=Decimal(1),
        run_dir=base / "run",
        run_id="run-1",
    )
    run_json = (base / "run" / "run.json").read_text(encoding="utf-8")
    run_json = run_json.replace(str(inputs), "{IN}").replace(str(ROOT), "{ROOT}")
    return {"run_json": run_json, "tree": tree_record(base / "run")}


KEY = ROOT / "cases" / "cpdr-research-owner"


def key_file(name: str) -> dict[str, Any]:
    """A frozen file of ``cases/cpdr-research-owner`` (read at test time, never edited)."""
    loaded: dict[str, Any] = json.loads((KEY / name).read_text(encoding="utf-8"))
    return loaded


class ResearchCase:
    """The key's research case materialised under ``base``: the manifest and the evidence files it
    names (from ``manifest.json#evidence``, byte for byte), a context file carrying the run's issuer,
    as-of and research questions, and two small case sources (``identity``, ``financial``)."""

    def __init__(self, base: Path, rows: list[dict[str, Any]] | None = None) -> None:
        manifest = key_file("manifest.json")
        self.key = manifest
        inputs = base / "research-in"
        inputs.mkdir(parents=True)
        for entry in [*manifest["evidence"], manifest["fence_terminator_item"]]:
            target = inputs / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(entry["pages"][0]["text"], encoding="utf-8", newline="")
        self.manifest_path = inputs / manifest["research_manifest"]["file"]
        if rows is None:
            self.manifest_path.write_bytes(
                manifest["research_manifest"]["file_bytes"].encode("utf-8")
            )
        else:
            self.manifest_path.write_text(json.dumps(rows), encoding="utf-8")
        context = json.loads((ROOT / "cases/context/research-minimal.json").read_text("utf-8"))
        context["run"]["as_of"] = manifest["run"]["as_of"]
        context["identity"]["issuer_id"] = manifest["run"]["issuer_id"]
        context["identity"]["issuer_name"] = manifest["run"]["issuer_name"]
        context["research_questions"] = manifest["context"]["research_questions"]
        self.context_path = inputs / "context.json"
        self.context_path.write_text(json.dumps(context), encoding="utf-8")
        self.sources = []
        for name in ("identity", "financial"):
            path = inputs / f"{name}.txt"
            path.write_text(f"{name} of Northbridge Synthetic Group\n", encoding="utf-8")
            self.sources.append(CaseSource(name, path, "text/plain"))
        self.inputs = inputs

    def arguments(self, base: Path, **over: Any) -> dict[str, Any]:
        """The ``run_pathway`` keywords of a cp_dr run over this case (a recorded adapter with
        no recordings: the run stops at its first model call, after staging)."""
        recordings = base / "recordings"
        recordings.mkdir(exist_ok=True)
        args: dict[str, Any] = {
            "case_id": "cpdr-research-owner",
            "sources": self.sources,
            "context": self.context_path,
            "pathway": "credit_snapshot",
            "model": MODEL,
            "adapter": recorded_adapter(MODEL, recordings),
            "cap_usd": Decimal(1),
            "run_dir": base / "run",
            "run_id": self.key["run"]["run_id"],
            "cp_dr": True,
            "research_manifest": self.manifest_path,
        }
        return {**args, **over}
