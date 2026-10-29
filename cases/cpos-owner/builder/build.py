"""Writes cases/cpos-owner/{manifest,submissions,expected}.json (stdlib only).

CP-OS (Report navigation) is deterministic: no analyst submission and no source of its own.
The oracle is the navigation the product must render from a verified owner-run receipt of a
closed S1a run. It is an independent transcription of the documented navigator rules
(src/deploy_vii/report_view.py navigator/status_display, assets/app.js renderNavigation and
renderModule, registry.idle_statuses); the product is read for text checks, never imported.
Every input file is checked against a pinned sha256 before use.

Run from the repository root:  python3 -I cases/cpos-owner/builder/build.py
"""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "cases" / "cpos-owner"

PINS = {
    "cases/snapshot/manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    "cases/snapshot/submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    "cases/snapshot/expected.json": "d1aa1af9677cc4bd77b890261f0ceeca664acc72aac77f91da55cf36d7279baa",
    "src/deploy_vii/methodology.json": "0932d9fbcd9272d62bcb7681e1dd16d9bc944319c64716b41dc79715699796e8",
    # Text-checked only (the literal tables below are asserted to appear in them). A changed pin is the
    # prompt to re-run these checks and move the pin in the same commit; D12 registrations touch the first.
    "src/deploy_vii/report_view.py": "c6b5b931ef5ca72c16d41d17463a4e3d7253d63e1046a9b432a155f571ba7483",
    "src/deploy_vii/assets/app.js": "0f0fe30bf97384d46ebfba4d6d09bc1b179918d6c36cba03b7ef8ee149bf7706",
    "src/deploy_vii/render.py": "7bf8d889fb8f5b74d84f0239664c801a1c0fcfbc3a40e32da6ea49f1cd8bf253",
    "src/deploy_vii/assets/shell.html": "c3f441e14855ff5e5a3a2361f5c1d97c1ef1e0db168f2286cbc1615b4ac76792",
    "src/deploy_vii/registry.py": "adf30a0b3f54d2b4d80fa6397507386e49017f7e6ab6d1399a02c393cf33ebbc",
    # Pinned for the credit_snapshot preset (PATHWAY_MODULES), which 0d's module_display reads.
    "src/deploy_vii/contracts.py": "3b33bfc27add489700f101f4672ff5b22fc0c6276d2bc24545ec6a4d2ee4515e",
}


def sha_file(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def read_pinned(rel):
    assert sha_file(rel) == PINS[rel], f"{rel}: sha256 differs from the pin"
    return (ROOT / rel).read_text(encoding="utf-8")


S1M = json.loads(read_pinned("cases/snapshot/manifest.json"))
S1E = json.loads(read_pinned("cases/snapshot/expected.json"))
read_pinned("cases/snapshot/submissions.json")
METHOD = json.loads(read_pinned("src/deploy_vii/methodology.json"))
RV = read_pinned("src/deploy_vii/report_view.py")
APP = read_pinned("src/deploy_vii/assets/app.js")
RENDER = read_pinned("src/deploy_vii/render.py")
REG = read_pinned("src/deploy_vii/registry.py")
CONTRACTS = read_pinned("src/deploy_vii/contracts.py")

# --- Documented tables, transcribed (decision 0004 section 6; shell.js FAMC/FAMILY) -----------------
# status -> (glyph key the shell draws, word). report_view._STATUS_WORDS plus _GLYPH_OF_ICON.
STATUS_WORDS = {
    "accepted": ("pass", "Pass"),
    "restricted": ("lim", "With limitations"),
    "blocked": ("blocked", "Blocked"),
    "unrun": ("unrun", "Not run"),
    "not_in_pathway": ("na", "Not in this Pathway"),
}
for status, (glyph, word) in STATUS_WORDS.items():
    icon = "not_in_pathway" if status == "not_in_pathway" else glyph
    assert f'"{status}": ("{icon}", "{word}")' in RV, status
assert '_GLYPH_OF_ICON = {"not_in_pathway": "na"}' in RV
# 0d(c) (b4ae187): a preset module (or required producer of the preset) that the run's requested_modules
# override left out reads "Not run" (glyph unrun) in the navigator and the module payload; its navigator
# row stays a footer row (in_pathway and the number follow the status, not the word).
for text in (
    "def module_display(view: View) -> Callable[[ModuleView], tuple[str, str]]:",
    "preset = dependencies(PATHWAY_MODULES[view.run.pathway])",
    'not_requested = module.status == "not_in_pathway" and module.module_id in preset',
    'return status_display("unrun" if not_requested else module.status)',
    '        in_pathway = module.status != "not_in_pathway"\n        if in_pathway:\n            number += 1\n'
    "        glyph, word = display(module)",
    "number=number if in_pathway else None,",
):
    assert text in RV, text
assert "module_status = module_display(view)" in RENDER
assert 'module_payload["status_glyph"], module_payload["status_word"] = module_status(module)' in RENDER

FAMILY_COLORS = {
    "sources": "#9AA0B4", "financials": "#0017E5", "business": "#2B8FD6", "earnings": "#C4410C",
    "synthesis": "#000533", "liquidity": "#0E7A46", "covenants": "#8A5300", "market": "#7A3DB8",
    "recovery": "#B3261E", "evidence": "#9AA0B4", "portfolio": "#000533",
}
MODULE_FAMILY = {
    "CP-0": "sources", "CP-1": "financials", "CP-1A": "business", "CP-1B": "earnings",
    "CP-1C": "market", "CP-1D": "earnings", "CP-2": "synthesis", "CP-2A": "synthesis",
    "CP-2D": "liquidity", "CP-2E": "synthesis", "CP-2G": "liquidity", "CP-2H": "market",
    "CP-3": "market", "CP-3C": "liquidity", "CP-3D": "market", "CP-4": "covenants",
    "CP-4C": "recovery", "CP-5": "evidence", "CP-6": "portfolio",
}
NEUTRAL = "#9AA0B4"
for family, color in FAMILY_COLORS.items():
    assert f'"{family}": "{color}"' in RV, family
for module, family in MODULE_FAMILY.items():
    assert f'"{module}": "{family}"' in RV, module
assert '_NEUTRAL_FAMILY_COLOR = "#9AA0B4"' in RV

# Shell facts the navigation proof relies on (app.js / render.py), asserted present.
for text in (
    'link.href = "#" + row.module_id',                     # module row link
    "report.nav.filter(row => row.in_pathway)",            # numbered list vs footer
    # 0d(c): the navigator footer groups outside rows by word (app.js renderNavigation).
    "[...new Set(outside.map(row => row.word))].forEach(word => {",
    "const group = outside.filter(row => row.word === word);",
    'details.append(node("summary", `${word} · ${group.length}`));',
    'const unrun = inPathway.filter(row => row.glyph === "unrun");',
    # 0d: the skip link focuses #workbench without routing; routeOf maps #workbench to front.
    'const route = location.hash.slice(1) || "front"; return route === "overview" || route === "workbench" ? "front" : route;',
    'document.querySelector("a.skip")?.addEventListener("click", event => {',
    "    event.preventDefault();\n    $(\"workbench\").focus();",
    'moduleFor = (route) => report.modules.find(item => item.module_id === route',
    '["front", "Front Page", "#front"]', '["analysis", "Analysis", "#analysis"]',
    '["model", "Model", "#CP-1"]', '["fit", "Portfolio Fit", "#FIT"]',
    '["evidence", "Evidence", "#evidence"]', '["limits", "Limitations", "#limitations"]',
    'module.status_glyph === "na"',
    "is not part of the ${front.pathway.title} Pathway, so it is not run.",
    "No validated output is available for this module.",
    '"Analysis · " + inPathway.length',
    "if (module.limitations.length)",
    'link = node("a", path); link.href = path',            # the one non-hash link: calculation.json
    # Every other hash href on the page (L5): Front Page block link, coverage table, CP-MODEL links.
    'link.href = "#" + block.full_analysis_route',
    'link.href = "#" + module.module_id;',                 # coverage table
    'anchor.href = "#CP-MODEL"',
    'link.href = "#CP-MODEL"',
    'const path = fact("model-destination", "calculation-json", "path")',
    'model.artifact_sha256 && path && /^[A-Za-z0-9._-]+$/.test(path) && cp1 && pack',
    "front.unplaced.length > 0",                           # the rail Limitations dot also reads this
):
    assert text in APP, text
assert 'payload["nav"] = [row.model_dump(mode="json") for row in navigator(view)]' in RENDER
assert "if module.status == \"rejected\":\n            continue" in RENDER
assert '_NOT_CP5_FAN_IN = frozenset({"CP-5", "CP-6", "CP-8", "CP-MEMO", "CP-OS"})' in REG
assert 'else "not_in_pathway" for m in modules()' in REG

SHELL = read_pinned("src/deploy_vii/assets/shell.html")
assert '<script id="report-data" type="application/json">' in SHELL
# Skip link (0d, 41a8fdb): shell.html carries it, app.js render handles its click (no routing) and routeOf maps
# #workbench to the front route, so it resolves (it was the recorded exception shell_skip_link before 0d).
assert '<a class="skip" href="#workbench">Skip to analysis</a>' in SHELL
assert '<main id="workbench" class="workbench" tabindex="-1">' in SHELL
assert '|| "Unknown destination"' in APP  # app.js render: an unresolved route still draws "Unknown destination"
assert '.replace(\n        "<", "\\\\u003c"\n    )' in RENDER  # report-data escapes "<" as \u003c (render.py:191-193)
assert 'route = spec.producers[0] if spec.producers else None' in RV
assert '"full_analysis_route": route' in RV
# The honest-state Block (no binding filled the block, report_view.py:1712) sets no route and no label: only
# a populated block carries the link. Asserted so the oracle states the superset truthfully.
assert "state=words_state,\n        kind=kind,\n        note=note,\n        width=spec.width,\n    )" in RV

# Front Page blocks of the credit_snapshot Pathway (the pathway of every S1a run): block id ->
# (producers[0], route_label). report_view._CREDIT_SNAPSHOT / _PRESETS, transcribed and text-checked
# below; app.js:428 draws "<route_label or 'Full analysis'> ->" linking "#" + producers[0].
BLOCK_ROUTES = [
    ("key-findings", "CP-2", None), ("company-operating-model", "CP-1A", None),
    ("model-chart-strip", "CP-1", "Open in Model"), ("capital-structure", "CP-1", None),
    ("financials-credit-metrics", "CP-1", "Open in Model"), ("strengths-weaknesses", "CP-2", None),
    ("relative-value", "CP-3", None), ("company-profile", "CP-1A", None),
    ("transaction-summary", None, None), ("portfolio-fit", None, None),
    ("committee-challenge", "CP-6", None), ("what-changed", "CP-8", None),
]
_CS_PRESET = re.search(r'"credit_snapshot": \(\s*\*\(([^)]*)\),\s*\)', CONTRACTS)
assert _CS_PRESET, "credit_snapshot preset not found in contracts.py"
CREDIT_SNAPSHOT_PRESET = re.findall(r'"(CP-[0-9A-Z]+)"', _CS_PRESET.group(1))
assert CREDIT_SNAPSHOT_PRESET == ["CP-0", "CP-1", "CP-MODEL", "CP-1A", "CP-2", "CP-4", "CP-3", "CP-5", "CP-6"]
_PRESET = RV[RV.index('"credit_snapshot",\n        "Credit Snapshot"'):RV.index('"earnings_update",\n        "Earnings Update"')]
assert re.findall(r'"([a-z-]+)",', _PRESET.split("(\n", 1)[1])[:12] == [b[0] for b in BLOCK_ROUTES]
for _bid, _route, _label in BLOCK_ROUTES:
    _start = RV.index(f'"{_bid}": _Spec(')
    _chunk = re.split(r'\n        "[a-z-]+": _Spec\(|\n    \}\n\)', RV[_start + 1:])[0]
    assert (f'("{_route}"' if _route else " (),") in _chunk, _bid
    assert (f'route_label="{_label}"' in _chunk) == bool(_label), _bid

# --- Registry (methodology.json file order is registry order) ---------------------------------------
REGISTRY = [
    {"module_id": m["module_id"], "title": m["title"], "aliases": list(m["aliases"])} for m in METHOD
]
REQUIRED = {m["module_id"]: list(m["required"]) for m in METHOD}
assert len(REGISTRY) == 25 and len({r["module_id"] for r in REGISTRY}) == 25
CPOS = next(m for m in METHOD if m["module_id"] == "CP-OS")
assert CPOS["required"] == [] and CPOS["optional"] == [] and CPOS["table_ids"] == []
assert CPOS["title"] == "Report navigation"
assert CPOS["purpose"] == "Read-only navigation and routing across analytical artifacts; no new analytical handoff."


def scope_of(requested):
    """registry.dependencies, required edges only (optional edges constrain order, not scope)."""
    selected, pending = set(), list(requested)
    while pending:
        item = pending.pop()
        if item in selected:
            continue
        selected.add(item)
        pending.extend(REQUIRED[item])
    return selected


PRESET_CLOSURE = scope_of(CREDIT_SNAPSHOT_PRESET)  # registry.dependencies(PATHWAY_MODULES["credit_snapshot"])


def run_of(case_id):
    return next(c for c in S1M["cases"] if c["case_id"] == case_id)["run"]


POS_RUN = run_of("snapshot-positive")
GAP_RUN = run_of("snapshot-gap-business-without-ownership-transaction")
assert POS_RUN["requested_modules"] == ["CP-1", "CP-MODEL", "CP-1A", "CP-2"] == GAP_RUN["requested_modules"]
assert S1E["execution"]["plan_order"] == ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL"]
assert scope_of(POS_RUN["requested_modules"]) == set(S1E["execution"]["plan_order"])
assert POS_RUN["pathway"] == GAP_RUN["pathway"] == "credit_snapshot"
assert set(S1E["execution"]["plan_order"]) <= PRESET_CLOSURE
S1A_STATUS = S1E["execution"]["statuses_S1a"]
for module in S1E["execution"]["plan_order"]:
    assert S1A_STATUS[module].startswith("restricted"), module


def row_for(entry, status, number, shown=None):
    """status: the view module status. shown: the status the shell displays; it differs only for an
    override-excluded preset module (status not_in_pathway, shown unrun; 0d(c) module_display)."""
    shown = shown or status
    glyph, word = STATUS_WORDS[shown]
    in_pathway = status != "not_in_pathway"  # follows the status, never the displayed word
    module_id = entry["module_id"]
    return {
        "module_id": module_id,
        "title": entry["title"],
        "aliases": entry["aliases"],
        "number": number if in_pathway else None,
        "in_pathway": in_pathway,
        "color": FAMILY_COLORS[MODULE_FAMILY[module_id]] if module_id in MODULE_FAMILY else NEUTRAL,
        "glyph": glyph,
        "word": word,
        "href": "#" + module_id,
        "group": "numbered" if in_pathway else "footer",
        "target": target_for(entry, shown),
    }


def target_for(entry, status):
    """What the page behind the link shows (app.js renderModule); a link never promises more."""
    output = status in ("accepted", "restricted")  # ModuleView carries facts/claims only for these
    if output:
        message = None
    elif status == "not_in_pathway":
        message = "not_part_of_pathway"
    else:
        message = "no_validated_output"
    return {
        "page_title": f"{entry['module_id']} · {entry['title']}",
        "status_chip_word": STATUS_WORDS[status][1],
        "has_output": output,
        "empty_state": message,
        # renderModule shows the "Scope and limitations" panel when the view module carries limitations:
        # a head (restricted or blocked) always does; an idle module has none.
        "limitations_panel": status in ("restricted", "blocked"),
    }


def search_probes(rows):
    probes = []
    for needle in ("business", "limitations", "cp-parse", "not in this pathway", "not run", "zzz"):
        haystack = lambda r: " ".join([r["module_id"], r["title"], r["word"], *r["aliases"]]).lower()
        hits = [r["module_id"] for r in rows if needle in haystack(r)]
        probes.append({
            "filter": needle,
            "numbered_matches": [m for m in hits if next(r for r in rows if r["module_id"] == m)["in_pathway"]],
            "footer_matches": [m for m in hits if not next(r for r in rows if r["module_id"] == m)["in_pathway"]],
        })
    return probes


def footer_groups(footer):
    words = list(dict.fromkeys(r["word"] for r in footer))
    return [{"summary": f"{w} \u00b7 {sum(1 for r in footer if r['word'] == w)}",
             "word": w, "module_ids": [r["module_id"] for r in footer if r["word"] == w]} for w in words]


def build_case(run, heads, description, oracle_status):
    in_scope = scope_of(run["requested_modules"])
    assert set(heads) <= in_scope, "a head outside the run's scope"
    rows, number = [], 0
    for entry in REGISTRY:
        module_id = entry["module_id"]
        if module_id in heads:
            status = heads[module_id]
        elif module_id in in_scope:
            status = "unrun"
        else:
            status = "not_in_pathway"
        if status != "not_in_pathway":
            number += 1
        not_requested = status == "not_in_pathway" and module_id in PRESET_CLOSURE
        rows.append(row_for(entry, status, number, "unrun" if not_requested else None))
    numbered = [r for r in rows if r["in_pathway"]]
    footer = [r for r in rows if not r["in_pathway"]]
    assert [r["number"] for r in numbered] == list(range(1, len(numbered) + 1))
    count = lambda glyph: sum(1 for r in numbered if r["glyph"] == glyph)
    chips = ["All", f"{count('lim')} lim", f"{count('pass')} pass"]
    if count("blocked"):
        chips.append(f"{count('blocked')} blocked")
    unrun = [r for r in numbered if r["glyph"] == "unrun"]
    has_limitations = any(h in ("restricted", "blocked") for h in heads.values())
    return {
        "description": description,
        "oracle_status": oracle_status,
        "run": run,
        "heads": heads,
        "rows": rows,
        "tally": {
            "label": f"Analysis · {len(numbered)}",
            "chips": chips,
            "numbered": len(numbered),
            "footer": len(footer),
            "unrun_line": f"Not run · {len(unrun)}" if unrun else None,
            # app.js renderNavigation: one <details> per distinct word of the outside rows, in row order.
            "footer_groups": footer_groups(footer),
        },
        "rejected_rows": 0,
        "destinations": destinations(run, has_limitations),
        "external_links": external_links(heads),
        "block_links": block_links(rows),
        "hash_links": hash_links(rows, destinations(run, has_limitations)),
        "search_probes": search_probes(rows),
    }


ROUTE_OF = {"overview": "front", "workbench": "front"}  # app.js:672 routeOf, asserted present above
FIXED_ROUTES = {"front", "analysis", "FIT", "evidence", "limitations"}


def resolves(route, rows):
    """app.js routeOf, then moduleFor / render: a route is a module id or alias of report.modules, or a fixed route."""
    route = ROUTE_OF.get(route, route)
    return route in FIXED_ROUTES or any(route == r["module_id"] or route in r["aliases"] for r in rows)


def block_links(rows):
    """Front Page 'Full analysis ->' / 'Open in Model ->' links (app.js:428) and the page each lands on.
    Only a populated block carries full_analysis_route (an honest-state block, report_view.py:1712, has none)
    and absent table-kind blocks are hidden (app.js renderFront); which blocks are populated needs the real
    store. The set below is every link the Pathway can draw, so the rendered set must be a subset."""
    out = []
    for block_id, route, label in BLOCK_ROUTES:
        if route is None:
            out.append({"block_id": block_id, "full_analysis_route": None, "link": None})
            continue
        row = next(r for r in rows if r["module_id"] == route)
        assert resolves(route, rows), (block_id, route)
        out.append({
            "block_id": block_id,
            "full_analysis_route": route,
            "link": {"text": (label or "Full analysis") + " \u2192", "href": "#" + route,
                     "page_title": row["target"]["page_title"], "status_chip_word": row["word"]},
        })
    return out


def hash_links(rows, dests):
    """Every '#' href the rendered page can carry and the route each must resolve to (L5)."""
    sources = {
        "navigator_and_footer_rows": sorted({r["href"] for r in rows}),
        "rail_destinations": sorted({d["href"] for d in dests}),
        "front_page_block_links": sorted({"#" + b[1] for b in BLOCK_ROUTES if b[1]}),
        "analysis_coverage_table": sorted({"#" + r["module_id"] for r in rows}),
        "model_destination_links": ["#CP-MODEL"],
    }
    for name, hrefs in sources.items():
        for href in hrefs:
            assert href.startswith("#") and resolves(href[1:], rows), (name, href)
    # The shell skip link (shell.html) resolves since 0d: the shipped handler focuses #workbench without
    # routing (asserted present above) and routeOf maps #workbench to front, a fixed destination.
    assert resolves("workbench", rows)
    sources["shell_skip_link"] = ["#workbench"]
    return sources


def destinations(run, has_limitations):
    """Rail destinations (app.js DEST); each resolves to a page that exists."""
    return [
        {"key": "front", "label": "Front Page", "href": "#front", "page_title": run["issuer_name"]},
        {"key": "analysis", "label": "Analysis", "href": "#analysis", "page_title": "Analysis"},
        {"key": "model", "label": "Model", "href": "#CP-1", "page_title": "CP-1 · Canonical data foundation"},
        {"key": "fit", "label": "Portfolio Fit", "href": "#FIT", "page_title": "Portfolio Fit",
         "page_text": "Portfolio Fit · not run: No portfolio constraints or exposures have been evaluated."},
        {"key": "evidence", "label": "Evidence", "href": "#evidence", "page_title": "Evidence"},
        {"key": "limits",
         "label": "Limitations" + (" · with limitations" if has_limitations else ""),
         "href": "#limitations", "page_title": "Limitations"},
    ]


def external_links(heads):
    """The one non-hash link (renderModelArtifact, app.js:600-603): the page's CP-MODEL fact
    model-destination/calculation-json/path. 'Linked' means that fact is on the page AND the path
    (calculation.json, cp_model_workflow.CALCULATION) is a key of receipt.model.files."""
    published = heads.get("CP-MODEL") in ("accepted", "restricted")
    return {
        "calculation.json": {
            "rendered": published,
            "page_fact": "CP-MODEL fact table model-destination, row calculation-json, field path",
            "page_gates": "module.artifact_sha256, path matches ^[A-Za-z0-9._-]+$, model-provenance cp1-head and pack sha256",
            "requires": "receipt.model.files has the key calculation.json (cp_model_workflow.CALCULATION)",
            "href_is_relative": "resolves only beside the published model files (app.js:603)",
        }
    }


CASES = {
    "s1a_positive": build_case(
        POS_RUN,
        {m: "restricted" for m in S1E["execution"]["plan_order"]},
        "Closed S1a positive run (CP-0, CP-1, CP-1A, CP-2 restricted; CP-MODEL published over CP-1).",
        "oracle: cases/snapshot/expected.json execution.statuses_S1a",
    ),
    "s1a_gap": build_case(
        GAP_RUN,
        {m: "restricted" for m in S1E["execution"]["plan_order"]},
        "Closed S1a gap run (no ownership or transaction facts). Statuses equal the positive case: "
        "navigation shows status, never content, so a content gap changes no row.",
        "oracle: cases/snapshot/expected.json execution.statuses_S1a and gap_case_authorization",
    ),
    "s1a_blocked_cp1a": build_case(
        POS_RUN,
        {"CP-0": "restricted", "CP-1": "restricted", "CP-1A": "blocked", "CP-2": "restricted",
         "CP-MODEL": "restricted"},
        "S1a acceptance A3b receipt: CP-1A attempts 0 and 1 invalid, CP-1A head blocked; CP-2 begins over "
        "the blocked CP-1A (restricted edge) and settles restricted; CP-MODEL publishes.",
        "derived from docs/S1A-OWNER-RUN-LEASE.md rev 1 H1 and execution.current_inputs (restricted edge "
        "binds a blocked head); CP-2 status restricted is not pinned by the S1 oracle",
    ),
    "s1a_refused_cp1a": build_case(
        POS_RUN,
        {"CP-0": "restricted", "CP-1": "restricted", "CP-MODEL": "restricted"},
        "S1a acceptance A3c receipt: CP-0 does not command CP-1A, so CP-1A is refused at begin (no head) "
        "and the walk stops (S1a Q3 b); CP-2 never begins; CP-MODEL publishes.",
        "derived from docs/S1A-OWNER-RUN-LEASE.md rev 3 R3-1 and Q3(b); CP-2 unrun rests on the "
        "stop-after-refusal rule and on execution.current_inputs refusing an unrun required upstream",
    ),
}

assert [r["module_id"] for r in CASES["s1a_positive"]["rows"] if r["in_pathway"]] == [
    "CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL"
]

EXPECTED = {
    "schema_version": "cpos-owner-expected/1",
    "derivation": (
        "Rows: registry order (methodology.json file order); status of a module = its settled head status, "
        "else 'unrun' if the module is in the run's scope (required-edge closure of requested_modules), else "
        "'not_in_pathway' (registry.idle_statuses). Numbered 1..N in registry order over in-scope modules "
        "(report_view.navigator); footer rows are not numbered. Glyph and word from the status table; colour "
        "from the family table, neutral grey when the registry module has no family. A rejected attempt has "
        "no row. Counts are exact integers. A link target is the module page '<id> · <title>'; only "
        "accepted and restricted heads carry output, so every other row lands on an honest status page. "
        "A not_in_pathway module inside the dependency closure of the Pathway preset reads 'Not run' (see rules."
        "override_excluded_preset_modules)."
    ),
    "status_words": {k: {"glyph": v[0], "word": v[1]} for k, v in STATUS_WORDS.items()},
    "family_colors": FAMILY_COLORS,
    "module_family": MODULE_FAMILY,
    "neutral_color": NEUTRAL,
    "registry": REGISTRY,
    "rules": {
        "never_link_to_missing_content": (
            "Every href in the navigator and rail resolves to a page the shell draws: module routes through "
            "report.modules (all registry modules except rejected attempts), the five fixed destinations, and "
            "calculation.json only when CP-MODEL published (receipt.model.files). An unrun, blocked or "
            "not-in-pathway module links to its status page and promises no findings: has_output false, the "
            "empty-state message shown, the status word in the chip."
        ),
        "verifier": "deploy_workflow.owner_workflow.verify_owner_run_receipt, called before anything is read",
        "no_journal_head": "CP-OS has no attempt, head, ticket or journal entry; the store and receipt are unchanged",
        "binding": (
            "proof.receipt_content_sha256 == OwnerRunReceipt.content_hash() of the verified receipt; "
            "proof.page_sha256 == sha256 of the rendered page bytes; proof.snapshot_sha256 == receipt.snapshot_sha256. "
            "Neither hash is a literal here: both are run-time values asserted by relation."
        ),
        "rail_limits_dot": (
            "Limitations destination reads 'with limitations' when any report module carries limitations or "
            "front.unplaced.length > 0 (app.js:680). The oracle values derive from the heads alone (a restricted or "
            "blocked head carries limitations); an unplaced binding would also light it and needs the real store."
        ),
        "hash_links_all_resolve": (
            "Every '#' href on the rendered page resolves to a page (the shell skip link included since 0d, rule shell_skip_link): navigator and footer rows, the six rail "
            "destinations, Front Page block links (blocks[].full_analysis_route, app.js:428), the Analysis coverage "
            "table (app.js:630) and the CP-MODEL links (app.js:604, :613). A route resolves when, after app.js routeOf "
            "(overview and workbench map to front), it is a module id or alias in report.modules, or front, analysis, "
            "FIT, evidence, limitations (app.js routeOf/moduleFor/render). "
            "cases[*].block_links and cases[*].hash_links list them per case."
        ),
        "shell_skip_link": (
            "Resolves since 0d (41a8fdb), text-checked: every page carries <a class=\"skip\" href=\"#workbench\">Skip to "
            "analysis</a> and <main id=\"workbench\" tabindex=\"-1\"> (shell.html); app.js attaches a click handler that calls "
            "preventDefault and focuses #workbench without routing, and routeOf maps the hash 'workbench' to the front "
            "route, so a page loaded at #workbench shows the Front Page. It is listed in cases[*].hash_links.shell_skip_link "
            "and is inside the dead-link refusal like every other hash link. The CP-OS rendering criterion ('visible "
            "working links') now rests on the native DOM step alone."
        ),
        "override_excluded_preset_modules": (
            "0d(c) (b4ae187): a module with view status not_in_pathway that is in registry.dependencies of the Pathway's "
            "preset (PATHWAY_MODULES[run.pathway], here credit_snapshot) but outside the run's requested_modules scope "
            "reads glyph 'unrun', word 'Not run' in the navigator (report_view.module_display) and in the module payload "
            "(render.py). Its navigator row stays a footer row (in_pathway false, no number: both follow the status). "
            "The navigator footer groups outside rows by word, one <details> per distinct word in row order "
            "(app.js renderNavigation): cases[*].tally.footer_groups. The module page is the unrun page: chip 'Not run', "
            "'No validated output is available…' (the 'not part of the Pathway' message is for glyph 'na' only). "
            "Modules outside the preset closure keep 'Not in this Pathway'."
        ),
        "hash_links_not_derivable_without_a_real_store": (
            "Which Front Page blocks are populated: only a populated block carries full_analysis_route (an honest-state "
            "block, report_view.py:1712, has none) and absent table-kind blocks are hidden (app.js renderFront); "
            "block state words, whether the Model destination shows the calculation link or the fallback text, and the "
            "unplaced list. The oracle gives the superset of links the credit_snapshot Pathway can draw; the test "
            "asserts the links actually drawn are a subset of it and every one resolves. 'Full analysis' on "
            "relative-value and committee-challenge leads to a CP-3, CP-6 'Not run' status page (in the preset, not "
            "requested); what-changed to a CP-8 'Not in this Pathway' page: resolves and promises nothing, but the "
            "label overstates it (LEAD to note)."
        ),
        "report_data_extraction": (
            "The page embeds <script id=\"report-data\" type=\"application/json\">DATA</script> (shell.html); DATA is "
            "json.dumps(ensure_ascii=True, separators=(',',':')) with every '<' replaced by \\u003c "
            "(render.py:191-193), so the first '</script>' after the opening tag ends it and json.loads of the "
            "text between is exact. No tag, no closing tag or invalid JSON: cpos_target_missing (never a bare "
            "JSONDecodeError or AttributeError). Blocks live at report-data report.blocks[], modules at modules[], "
            "rows at nav[]."
        ),
        "target_fields_inferred": (
            "target.has_output and target.limitations_panel are inferred here from status (accepted and restricted "
            "carry facts or claims; restricted and blocked carry limitations) because the oracle has no real View. "
            "The test asserts them against the real heads' module views (facts/claims/tables non-empty; "
            "limitations non-empty). A disagreement is returned to LEAD for a ruling, never edited in the oracle."
        ),
        "limitation_calculation_json_link": (
            "The calculation.json href is relative: it resolves only when the page is opened from a directory "
            "holding the receipt's model files. A page opened elsewhere shows a link that cannot open; CP-OS proves "
            "the link is drawn from the page fact and present in receipt.model.files, not that the file is beside the page."
        ),
    },
    "cases": CASES,
    "dom_expectation": (
        "Native DOM acceptance (separate from component tests; closes rendering): open the page from a directory "
        "holding the receipt's model files (calculation.json beside it); click each numbered row and each footer "
        "row: h1 == target.page_title and the status chip word; the six rail destinations show their page_title; "
        "each Front Page block link in cases[*].block_links that is drawn lands on its page_title; the "
        "calculation.json link opens the file."
    ),
}

SUBMISSIONS = {
    "schema_version": "cpos-owner-submissions/1",
    "note": (
        "CP-OS takes no analyst submission and no source. Nothing here is a submit payload: these are the "
        "input recipes of the refusal tests, each applied to a clone of the named closed run."
    ),
    "receipts": {
        "s1a_positive": "receipt of the closed S1a positive run (acceptance A1) and its publication directory",
        "s1a_gap": "receipt of the closed S1a gap run (A2)",
        "s1a_blocked_cp1a": "receipt of the A3b clone of the positive run",
        "s1a_refused_cp1a": "receipt of the A3c clone of the positive run",
    },
    "verifier_refusals": [
        {
            "id": "seal_edit",
            "on": "s1a_positive",
            "recipe": "receipt copy with only 'participant' changed to a different string; store and audit unchanged",
            "targets": "owner_workflow._verify sealed check: audit/receipt.sha256 != receipt.content_hash()",
            "raises": "WorkflowError", "code": "identity_mismatch",
        },
        {
            "id": "head_status_forged",
            "on": "s1a_positive",
            "recipe": (
                "receipt copy with the CP-1A SettledHead status 'restricted' -> 'accepted', and audit/receipt.sha256 "
                "rewritten to the forged receipt's content hash so the seal agrees"
            ),
            "targets": "owner_workflow._verify head check: _settled(store, module) not in receipt.heads",
            "raises": "WorkflowError", "code": "identity_mismatch",
        },
        {
            "id": "foreign_store",
            "on": "s1a_positive receipt, s1a_gap store",
            "recipe": "present the positive receipt with the gap run's store",
            "targets": "owner_workflow._verify first check: run, pack and snapshot hash differ",
            "raises": "WorkflowError", "code": "stale_binding",
        },
    ],
    "cpos_refusals": [
        {
            "id": "proof_of_other_receipt",
            "on": "s1a_positive page and proof, s1a_gap receipt and store",
            "recipe": (
                "verify_navigation with a proof built for the positive receipt against the gap receipt (both verify). "
                "Differs in run, pack, snapshot, heads and receipt hash at once, on purpose; receipt_hash_only isolates the hash"
            ),
            "raises": "ValueError", "prefix": "cpos_binding",
        },
        {
            "id": "dangling_target",
            "on": "s1a_positive",
            "recipe": (
                "page with the CP-2 entry removed from report-data modules (nav untouched), page_sha256 in the "
                "proof rewritten to the forged page's hash"
            ),
            "raises": "ValueError", "prefix": "cpos_target_missing",
        },
        {
            "id": "forged_row",
            "on": "s1a_positive",
            "recipe": (
                "page whose report-data nav CP-1A row reads glyph 'pass', word 'Pass' (modules untouched), "
                "page_sha256 rewritten consistently"
            ),
            "raises": "ValueError", "prefix": "cpos_rows",
        },
        {
            "id": "page_bytes_edited",
            "on": "s1a_positive",
            "recipe": "page with a trailing newline appended (rows and targets intact), page_sha256 rewritten",
            "raises": "ValueError", "prefix": "cpos_page",
        },
        {
            "id": "receipt_hash_only",
            "on": "s1a_positive",
            "recipe": (
                "the valid s1a_positive proof with only proof.receipt_content_sha256 replaced by "
                "content_hash() of the seal_edit receipt copy; page, store and the verified receipt unchanged"
            ),
            "raises": "ValueError", "prefix": "cpos_binding",
        },
        {
            "id": "forged_proof_row",
            "on": "s1a_blocked_cp1a",
            "recipe": (
                "the valid s1a_blocked_cp1a proof with only the CP-1A NavigationRow has_output changed false -> true; "
                "page unmodified, page_sha256 genuine"
            ),
            "raises": "ValueError", "prefix": "cpos_rows",
        },
        {
            "id": "forged_proof_destination",
            "on": "s1a_positive",
            "recipe": (
                "the valid s1a_positive proof with only the Model destination href '#CP-1' changed to '#CP-MODEL' "
                "(a route that exists, so no dead link); page unmodified, page_sha256 genuine"
            ),
            "raises": "ValueError", "prefix": "cpos_rows",
        },
        {
            "id": "forged_external_link",
            "on": "s1a_positive",
            "recipe": (
                "the valid s1a_positive proof with only proof.external_links changed from ('calculation.json',) "
                "to ('evil.json',); page unmodified, page_sha256 genuine. Replayed variant: external_links = ()"
            ),
            "raises": "ValueError", "prefix": "cpos_proof",
        },
        {
            "id": "unverifiable_page_hash",
            "on": "s1a_positive",
            "recipe": "unmodified page, proof.page_sha256 replaced by 64 zeros",
            "raises": "ValueError", "prefix": "cpos_binding",
        },
    ],
    "order_of_cpos_checks": ["cpos_binding", "cpos_target_missing", "cpos_rows", "cpos_page", "cpos_proof"],
    "full_proof_equality": (
        "After the four prefixed diagnostics, verify_navigation requires proof == derived_proof in full (every "
        "field); any remaining difference raises cpos_proof. Proof forgeries below leave the page unmodified "
        "and its page_sha256 genuine."
    ),
}

MANIFEST = {
    "schema_version": "cpos-owner-cases/1",
    "scope": (
        "CP-OS Report navigation over verified S1a owner-run receipts (positive, gap, blocked CP-1A, refused CP-1A). "
        "No source pack of its own: the runs, packs and receipts are those of docs/S1A-OWNER-RUN-LEASE.md."
    ),
    "status": "DRAFT by owner-preparation task cpos-owner, 2026-10-28; not executed",
    "pins": PINS,
    "reuse": {
        "runs": "cases/snapshot/manifest.json cases[*].run, bytes unchanged",
        "statuses": "cases/snapshot/expected.json execution.statuses_S1a",
        "registry": "src/deploy_vii/methodology.json, data only",
    },
    "source_bytes": "none added; no synthetic source is needed (navigation reads status and registry, not content)",
    "cases": [
        {"case_id": k, "run_id": v["run"]["run_id"], "receipt_from": SUBMISSIONS["receipts"][k]}
        for k, v in CASES.items()
    ],
}


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    write("manifest.json", MANIFEST)
    write("submissions.json", SUBMISSIONS)
    write("expected.json", EXPECTED)
    print("wrote", OUT)
