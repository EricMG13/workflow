"""CP-OS report navigation proof: the navigation a page shows is that of a real, verified run.

`docs/CPOS-OWNER-LEASE.md` (D6: render-time navigation proof over a real selected run, with the
rendered page hash bound to that run's verified receipt hash; no journal head). CP-OS is not an
owner-run step: it has no `OwnerSpec`, core, probe or submit, and it writes nothing. It lives
beside the cores for D12 location only.

`navigation` authenticates the receipt with G1's `verify_owner_run_receipt` (its only
authentication; CP-OS neither catches nor relabels its refusals), renders the accepted view with
`deploy_vii.render.render`, and returns the page bytes with a `NavigationProof` of the navigator
rows, the six rail destinations and the one external link, every `#` href checked against the
pages the shell draws. `verify_navigation` repeats the derivation and refuses, in this order,
`cpos_binding`, `cpos_target_missing`, `cpos_rows`, `cpos_page`, `cpos_proof` (a `ValueError`
whose message starts with the prefix).
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from deploy_vii.contracts import Contract, Hash, Identifier, Run, Text, View
from deploy_vii.execution import Execution
from deploy_vii.registry import idle_statuses
from deploy_vii.render import render
from deploy_vii.report_view import navigator
from deploy_workflow.owner_workflow import (
    OwnerRunReceipt,
    SettledHead,
    verify_owner_run_receipt,
)

SCHEMA = "cpos-navigation/1"
OPEN_TAG = '<script id="report-data" type="application/json">'
CLOSE_TAG = "</script>"
# Routes the shell draws besides modules (app.js routeOf / render).
FIXED_ROUTES = frozenset({"front", "analysis", "FIT", "evidence", "limitations"})
# The recorded shell defect outside CP-OS (lease, `shell_skip_link`): excluded from the refusal.
SKIP_LINK = "workbench"
# The path charset the shell accepts for the model link (app.js renderModelArtifact).
LINK_PATH = re.compile(r"[A-Za-z0-9._-]+")
HASH_HREF = re.compile(r'href="#([^"]*)"')
# (key, label, href) as the shell's DEST (app.js).
DEST = (
    ("front", "Front Page", "#front"),
    ("analysis", "Analysis", "#analysis"),
    ("model", "Model", "#CP-1"),
    ("fit", "Portfolio Fit", "#FIT"),
    ("evidence", "Evidence", "#evidence"),
    ("limits", "Limitations", "#limitations"),
)
DEST_TITLES = {
    "analysis": "Analysis",
    "fit": "Portfolio Fit",
    "evidence": "Evidence",
    "limits": "Limitations",
}


class NavigationRow(Contract):
    """`report_view.NavRow` plus the proof that its link lands on a page that says what is true."""

    module_id: Identifier
    title: Text
    aliases: tuple[str, ...]
    number: int | None
    in_pathway: bool
    color: str
    glyph: str
    word: Text
    href: str
    group: Literal["numbered", "footer"]
    page_title: str
    has_output: bool
    empty_state: Literal["not_part_of_pathway", "no_validated_output"] | None
    limitations_panel: bool


class NavigationDestination(Contract):
    key: str
    label: str
    href: str
    page_title: str


class NavigationProof(Contract):
    schema_version: Literal["cpos-navigation/1"] = "cpos-navigation/1"
    run: Run
    pack_sha256: Hash
    snapshot_sha256: Hash
    receipt_content_sha256: Hash
    page_sha256: Hash
    heads: tuple[SettledHead, ...]
    rows: tuple[NavigationRow, ...]
    destinations: tuple[NavigationDestination, ...]
    external_links: tuple[str, ...]


def _refuse(prefix: str, detail: str) -> ValueError:
    return ValueError(f"{prefix}: {detail}")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extract(page: bytes) -> dict[str, Any]:
    """The `report-data` JSON of a page. The first closing script tag ends it (render.py escapes
    every `<` in DATA), so the text between is exact. Anything else is `cpos_target_missing`."""
    try:
        text = page.decode()
    except UnicodeDecodeError:
        raise _refuse("cpos_target_missing", "page is not UTF-8") from None
    start = text.find(OPEN_TAG)
    if start < 0:
        raise _refuse("cpos_target_missing", "no report-data tag")
    start += len(OPEN_TAG)
    end = text.find(CLOSE_TAG, start)
    if end < 0:
        raise _refuse("cpos_target_missing", "report-data tag is not closed")
    try:
        data = json.loads(text[start:end])
    except ValueError:
        raise _refuse("cpos_target_missing", "report-data is not JSON") from None
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("modules"), list)
        or not isinstance(data.get("nav"), list)
        or not isinstance(data.get("report"), dict)
        or not isinstance(data["report"].get("blocks"), list)
    ):
        raise _refuse("cpos_target_missing", "report-data lacks modules, nav or report blocks")
    result: dict[str, Any] = data
    return result


def _model_link(data: dict[str, Any]) -> str | None:
    """The calculation link path iff the shell draws it: the CP-MODEL fact `model-destination` /
    `calculation-json` / `path` with the shell's gates (app.js renderModelArtifact)."""
    model = next((m for m in data["modules"] if m.get("module_id") == "CP-MODEL"), None)
    if model is None or not model.get("artifact_sha256"):
        return None

    def fact(table: str, row: str, field: str) -> str | None:
        for item in model.get("facts", ()):
            if (item.get("table_id"), item.get("row_id"), item.get("field")) == (table, row, field):
                text = item.get("text")
                return text if isinstance(text, str) and text else None
        return None

    path = fact("model-destination", "calculation-json", "path")
    if (
        path is None
        or LINK_PATH.fullmatch(path) is None
        or not fact("model-provenance", "cp1-head", "sha256")
        or not fact("model-provenance", "pack", "sha256")
    ):
        return None
    return path


def _external_links(data: dict[str, Any], receipt: OwnerRunReceipt) -> tuple[str, ...]:
    path = _model_link(data)
    if path is None:
        return ()
    if receipt.model is None or path not in receipt.model.files:
        raise _refuse("cpos_target_missing", f"{path} is linked but not in the receipt's files")
    return (path,)


def _check_links(page: bytes, data: dict[str, Any]) -> None:
    """Every `#` href the page draws lands on a page the shell has (lease, never-a-dead-link)."""
    routes = set(FIXED_ROUTES)
    for module in data["modules"]:
        routes.add(module["module_id"])
        routes.update(module.get("aliases", ()))
    hrefs = [row["module_id"] for row in data["nav"]]
    hrefs += [href[1:] for _, _, href in DEST]
    hrefs += [
        b["full_analysis_route"] for b in data["report"]["blocks"] if b.get("full_analysis_route")
    ]
    hrefs += [module["module_id"] for module in data["modules"]]
    if _model_link(data) is not None:
        hrefs.append("CP-MODEL")
    html = page.decode()
    outside = html[: html.find(OPEN_TAG)] + html[html.find(CLOSE_TAG, html.find(OPEN_TAG)) :]
    hrefs += [match[1] for match in HASH_HREF.finditer(outside)]
    for route in hrefs:
        if route != SKIP_LINK and route not in routes:
            raise _refuse("cpos_target_missing", f"#{route} has no page")


def _rows(view: View) -> tuple[NavigationRow, ...]:
    modules = {m.module_id: m for m in view.modules}
    rows = []
    for row in navigator(view):
        module = modules[row.module_id]
        has_output = bool(module.facts or module.claims or module.tables)
        empty_state: Literal["not_part_of_pathway", "no_validated_output"] | None = None
        if not has_output:
            empty_state = "not_part_of_pathway" if row.glyph == "na" else "no_validated_output"
        rows.append(
            NavigationRow(
                **row.model_dump(),
                href="#" + row.module_id,
                group="numbered" if row.in_pathway else "footer",
                page_title=f"{row.module_id} · {row.title}",
                has_output=has_output,
                empty_state=empty_state,
                limitations_panel=bool(module.limitations),
            )
        )
    return tuple(rows)


def _destinations(view: View, data: dict[str, Any]) -> tuple[NavigationDestination, ...]:
    titles = {m.module_id: m.title for m in view.modules}
    limited = any(m.get("limitations") for m in data["modules"]) or bool(
        data["report"].get("unplaced")
    )
    result = []
    for key, label, href in DEST:
        if key == "front":
            page_title = view.run.issuer_name
        elif key == "model":
            page_title = f"CP-1 · {titles['CP-1']}"
        else:
            page_title = DEST_TITLES[key]
        if key == "limits" and limited:
            label += " · with limitations"
        result.append(NavigationDestination(key=key, label=label, href=href, page_title=page_title))
    return tuple(result)


def _derive(
    store: Execution, receipt: OwnerRunReceipt, publication_directory: Path | None
) -> tuple[View, bytes, dict[str, Any], NavigationProof]:
    """Steps 1-5 of the lease: verify, view, render, re-read, parse, derive."""
    verify_owner_run_receipt(store, receipt, publication_directory=publication_directory)
    view: View = store.view()
    if view.run != receipt.run:
        raise _refuse("cpos_binding", "view run differs from the receipt's run")
    idle = idle_statuses(receipt.run)
    heads = {head.module_id: head.status for head in receipt.heads}
    for module in view.modules:
        if module.status != heads.get(module.module_id, idle[module.module_id]):
            raise _refuse("cpos_binding", f"{module.module_id} status differs from the receipt")
    page = render(view).encode()
    if store.read().content_hash() != receipt.snapshot_sha256:
        raise _refuse("cpos_binding", "the store changed during the render")
    data = _extract(page)
    _check_links(page, data)
    proof = NavigationProof(
        run=receipt.run,
        pack_sha256=receipt.pack_sha256,
        snapshot_sha256=receipt.snapshot_sha256,
        receipt_content_sha256=receipt.content_hash(),
        page_sha256=_sha(page),
        heads=receipt.heads,
        rows=_rows(view),
        destinations=_destinations(view, data),
        external_links=_external_links(data, receipt),
    )
    return view, page, data, proof


def navigation(
    store: Execution, receipt: OwnerRunReceipt, publication_directory: Path | None
) -> tuple[bytes, NavigationProof]:
    """The navigation page of a verified run and its proof. Writes nothing."""
    _, page, _, proof = _derive(store, receipt, publication_directory)
    return page, proof


def verify_navigation(
    store: Execution,
    receipt: OwnerRunReceipt,
    publication_directory: Path | None,
    page: bytes,
    proof: NavigationProof,
) -> None:
    """Refuse a page or proof that is not the derived one, by the first failing check in the
    order binding, target, rows, page, full proof."""
    view, derived_page, _, derived = _derive(store, receipt, publication_directory)
    if (
        proof.receipt_content_sha256 != receipt.content_hash()
        or proof.snapshot_sha256 != receipt.snapshot_sha256
        or proof.run != receipt.run
        or proof.pack_sha256 != receipt.pack_sha256
        or proof.heads != receipt.heads
        or _sha(page) != proof.page_sha256
    ):
        raise _refuse("cpos_binding", "page or proof is not bound to this verified receipt")
    shown = _extract(page)
    _check_links(page, shown)
    _external_links(shown, receipt)
    if shown["nav"] != [row.model_dump(mode="json") for row in navigator(view)]:
        raise _refuse("cpos_rows", "the page's navigator differs from the run's rows")
    if proof.rows != derived.rows or proof.destinations != derived.destinations:
        raise _refuse("cpos_rows", "the proof's rows or destinations differ from the run's")
    if page != derived_page:
        raise _refuse("cpos_page", "page bytes differ from the render of the run's view")
    if proof != derived:
        raise _refuse("cpos_proof", "proof differs from the derived proof")
