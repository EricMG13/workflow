"""Writes cases/cpdr-web-retrieval/{manifest,expected}.json (stdlib only, imports nothing from src/).

Frozen key for O7b-2 web retrieval (D1-D8): synthetic hosts, canned responses, a fixed clock, an injected cap of
600. The builder carries a small independent model of the fetch rules (the plan's D3-D8) and derives every
expected value and every hash from the embedded manifest bytes. Nothing dials any address.

Text forms copied from existing code are cited in `_source` notes; every other refusal text is written here.
Run: python3 -I cases/cpdr-web-retrieval/builder/build.py [OUT_DIR]   (from the repository root)
"""

import hashlib
import ipaddress
import json
import re
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "cases" / "cpdr-web-retrieval"


def dump(obj):
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


def pretty(obj, depth=0, width=110):
    """Key-file layout: a container whose one-line JSON fits the width stays on one line (compact, deterministic)."""
    flat = json.dumps(obj, ensure_ascii=False)
    if not isinstance(obj, (dict, list)) or not obj or len(flat) + depth <= width:
        return flat
    pad, inner = " " * (depth + 1), depth + 1
    if isinstance(obj, dict):
        body = [f"{pad}{json.dumps(k)}: {pretty(v, inner, width)}" for k, v in obj.items()]
        return "{\n" + ",\n".join(body) + "\n" + " " * depth + "}"
    return "[\n" + ",\n".join(pad + pretty(v, inner, width) for v in obj) + "\n" + " " * depth + "]"


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def unwrap(addr):
    ip = ipaddress.ip_address(addr)
    return ip.ipv4_mapped if getattr(ip, "ipv4_mapped", None) else ip


def public(addr):
    """The key's rule (O7-R48 M1): is_global after unwrapping ::ffff:a.b.c.d, and not multicast, reserved or site-local."""
    ip = unwrap(addr)
    return ip.is_global and not (
        ip.is_multicast or ip.is_reserved or getattr(ip, "is_site_local", False)
    )


def klass(addr):
    ip = unwrap(addr)
    for name in (
        "is_loopback",
        "is_link_local",
        "is_multicast",
        "is_unspecified",
        "is_reserved",
        "is_private",
    ):
        if getattr(ip, name):
            return name[3:].replace("_", "-")
    return "public" if ip.is_global else "not-global"


CAP, CLOCK, AS_OF, TODAY = 600, "2026-11-02T05:40:00Z", "2026-01-10", "2026-11-02"
MAX_REDIRECTS = 3
UNDATED = f"undated evidence item refused: as_of {AS_OF} is before today"
SYNTH = "This invented case is test data, not evidence about real issuers."
PUB = "93.184.216"  # ordinary allocated space: ipaddress reports is_global; used only through the injected resolver


def filler(n):
    unit = "Synthetic at-cap filler note. " + SYNTH + "\n"
    return (unit * (n // len(unit) + 1))[:n]


def plain(*lines):
    return "\n".join(lines)


HOSTS = {
    "sector-desk.example": [f"{PUB}.34"],
    "trade-press.example": [f"{PUB}.35", "10.0.0.5"],
    "loop.example": ["127.0.0.1"],
    "metadata.example": ["169.254.169.254"],
    "six-loop.example": ["::1"],
    "mapped.example": ["::ffff:10.0.0.1"],
    "link.example": ["fe80::1"],
    "redirect-a.example": [f"{PUB}.40"],
    "redirect-b.example": [f"{PUB}.41"],
    "redirect-c.example": [f"{PUB}.42"],
    "redirect-d.example": [f"{PUB}.43"],
    "outside.example": [f"{PUB}.50"],
}
HOST_LABEL = {
    h: h in {"sector-desk.example", "outside.example"} or h.startswith("redirect-") for h in HOSTS
}
for _h, _addrs in HOSTS.items():
    for (
        _a
    ) in _addrs:  # public label means is_global; private label means not global after unwrapping
        assert unwrap(_a).is_global == (
            HOST_LABEL[_h] or (_h == "trade-press.example" and _a.startswith(PUB))
        ), (_h, _a)
HOSTS_NOTE = (
    "Public addresses are 93.184.216.x, which ipaddress reports is_global (the documentation ranges 203.0.113.0/24 and "
    "198.51.100.0/24 are not global, so they are not used for public hosts); build.py asserts is_global for every address "
    "labelled public and not-global (after unwrapping ::ffff:a.b.c.d) for every address labelled private (O7-R46). "
    "Nothing dials these addresses. A host is public only when every address it resolves to is public. Host probes use "
    "https://<host>/probe fetched with manifest_hosts = #manifest_hosts plus the probe host."
)

H, T = "text/html; charset=utf-8", "text/plain; charset=utf-8"
HTML = (
    "<html><head><title>Hidden</title></head><body><p>Synthetic sector desk note.</p>"
    "<p>Supply of industrial products is concentrated.</p><p>" + SYNTH + "</p></body></html>"
)
SD = "https://sector-desk.example/notes/"
RA, RB, RC, RD = (f"https://redirect-{x}.example/" for x in "abcd")
W1 = SD + "supply-costs?edition=2&lang=en"
RESPONSES = {
    W1: (200, {"Content-Type": H}, HTML),
    SD + "header-dated": (
        200,
        {"Content-Type": T, "Last-Modified": "Mon, 15 Dec 2025 08:00:00 GMT"},
        plain("Synthetic header-dated note.", SYNTH),
    ),
    SD + "body-dated": (
        200,
        {"Content-Type": T},
        plain("Published: 2025-12-22", "Synthetic body-dated note.", SYNTH),
    ),
    SD + "body-late": (
        200,
        {"Content-Type": T},
        plain("Published: 2026-02-03", "Synthetic late-dated note.", SYNTH),
    ),
    SD + "no-date": (
        200,
        {"Content-Type": T},
        plain("Synthetic note with no publication date.", SYNTH),
    ),
    SD + "located-only": (
        200,
        {"Content-Type": T},
        plain("Published: 2025-12-21", "Synthetic note dated only in its body.", SYNTH),
    ),
    SD + "at-cap": (200, {"Content-Type": T}, filler(CAP)),
    SD + "over-cap": (200, {"Content-Type": T}, filler(CAP + 1)),
    SD + "server-error": (500, {"Content-Type": T}, "error"),
    SD + "report.pdf": (200, {"Content-Type": "application/pdf"}, "%PDF-1.4 synthetic"),
    RA + "three-hops": (302, {"Location": RB + "three-1"}, ""),
    RB + "three-1": (302, {"Location": RC + "three-2"}, ""),
    RC + "three-2": (302, {"Location": RD + "three-3"}, ""),
    RD + "three-3": (
        200,
        {"Content-Type": T},
        plain("Synthetic note reached after three redirects.", SYNTH),
    ),
    RA + "four-hops": (302, {"Location": RB + "four-1"}, ""),
    RB + "four-1": (302, {"Location": RC + "four-2"}, ""),
    RC + "four-2": (302, {"Location": RD + "four-3"}, ""),
    RD + "four-3": (302, {"Location": RA + "four-4"}, ""),
    RA + "to-http": (302, {"Location": "http://redirect-b.example/plain"}, ""),
    RA + "to-outside": (302, {"Location": "https://outside.example/page"}, ""),
    RA + "to-private": (302, {"Location": "https://trade-press.example/target"}, ""),
    RB + "anchor": (200, {"Content-Type": T}, plain("Synthetic anchor note b.", SYNTH)),
    RC + "anchor": (200, {"Content-Type": T}, plain("Synthetic anchor note c.", SYNTH)),
    RD + "anchor": (200, {"Content-Type": T}, plain("Synthetic anchor note d.", SYNTH)),
    "https://trade-press.example/anchor": (
        200,
        {"Content-Type": T},
        "never read: the host is refused first",
    ),
}
LOCAL_PATH = "evidence/local-note.txt"
LOCAL_TEXT = plain("Synthetic local registry note.", SYNTH)

# key, source, family, published, tag. Order is manifest order; the locator of a url row is its url.
SPEC = [
    ("local", LOCAL_PATH, "registry-filings", "2025-12-16"),
    ("html", W1, "sector-desk-notes", "2025-12-18"),
    ("header", SD + "header-dated", "sector-desk-notes", "2025-12-20"),
    ("body", SD + "body-dated", "sector-desk-notes", "2025-12-28"),
    ("late", SD + "body-late", "sector-desk-notes", "2026-01-05"),
    ("neither", SD + "no-date", "sector-desk-notes", None),
    ("located_only", SD + "located-only", "sector-desk-notes", None),
    ("at_cap", SD + "at-cap", "sector-desk-notes", "2025-12-10"),
    ("over_cap", SD + "over-cap", "sector-desk-notes", "2025-12-11"),
    ("status_500", SD + "server-error", "sector-desk-notes", "2025-12-12"),
    ("pdf", SD + "report.pdf", "sector-desk-notes", "2025-12-13"),
    ("r_three", RA + "three-hops", "redirect-notes", "2025-12-14"),
    ("r_four", RA + "four-hops", "redirect-notes", "2025-12-14"),
    ("r_http", RA + "to-http", "redirect-notes", "2025-12-14"),
    ("r_outside", RA + "to-outside", "redirect-notes", "2025-12-14"),
    ("r_private", RA + "to-private", "redirect-notes", "2025-12-14"),
    ("anchor_b", RB + "anchor", "redirect-notes", "2025-12-17"),
    ("anchor_c", RC + "anchor", "redirect-notes", "2025-12-17"),
    ("anchor_d", RD + "anchor", "redirect-notes", "2025-12-17"),
    ("mixed", "https://trade-press.example/anchor", "trade-press-archive", "2025-12-17"),
]
LOCATOR = {
    W1: "https://sector-desk.example/notes/supply-costs"
}  # O7-R48 H2: fence-safe, distinct from the url
ROWS = []
for _key, _src, _fam, _pub in SPEC:
    _row = {("path" if _key == "local" else "url"): _src, "family": _fam}
    if _pub:
        _row["published"] = _pub
    _row["locator"] = LOCATOR.get(_src, _src)
    _row["tag"] = "research"
    ROWS.append(_row)

RULING = ["lifts: live-provider-pause", "by: user", "date: 2026-11-02"]
RULING_TEXTS = {
    "good": "\n".join(RULING + ["configs: web-retrieval"]) + "\n",
    "configs_missing": "\n".join(RULING + ["configs: sol-medium sol-high opus-medium deepseek-max"])
    + "\n",
    "lifts_missing": "\n".join(RULING[1:] + ["configs: web-retrieval"]) + "\n",
}
URL_CHECKS = {
    "http": "http://sector-desk.example/x",
    "file": "file:///etc/passwd",
    "ftp": "ftp://sector-desk.example/x",
    "data": "data:text/plain,hi",
    "userinfo": "https://user:pw@sector-desk.example/x",
    "empty_host": "https:///x",
}
# O7 S3 I-3: a manifest row locator that would break a dossier cell, refused when the rows are parsed (argument time)
LOCATOR_CHECKS = {
    "pipe": "https://sector-desk.example/notes|x",
    "line_feed": "https://sector-desk.example/notes\nx",
    "carriage_return": "https://sector-desk.example/notes\rx",
    "block_opener": "https://sector-desk.example/notes<<<x",
}
LOCATOR_CELL = "manifest row locator contains a pipe character, a line feed or a carriage return, which a dossier table cell cannot hold"
LOCATOR_BLOCK = "manifest row locator contains <<<, which a dossier block cannot show"
# O7-R69: a manifest row family that would break a dossier cell (shown in the dossier and TDR.2), refused at argument time
FAMILY_CHECKS = {
    "pipe": "filing|annual",
    "line_feed": "filing\nannual",
    "carriage_return": "filing\rannual",
    "block_opener": "filing <<<x",
}
FAMILY_CELL = "manifest row family contains a pipe character, a line feed or a carriage return, which a dossier table cell cannot hold"
FAMILY_BLOCK = "manifest row family contains <<<, which a dossier block cannot show"
MANIFEST = {
    "schema_version": "cpdr-web-retrieval-cases/1",
    "scope": "Key for web retrieval behind the live pause (O7b-2 D1-D8). SYNTHETIC: every host is an .example name resolved only by an injected resolver; every body says so.",
    "status": "frozen",
    "hosts": HOSTS,
    "research_manifest": {
        "file": "research-manifest.json",
        "rows": ROWS,
        "files": {LOCAL_PATH: LOCAL_TEXT},
    },
    "manifest_hosts": sorted({urlsplit(r["url"]).hostname for r in ROWS if "url" in r}),
    "responses": {u: {"status": s, "headers": h, "body": b} for u, (s, h, b) in RESPONSES.items()},
    "cap": CAP,
    "timeouts": {"connect_seconds": 10, "total_seconds": 30},
    "slow_connector_seconds": 31,
    "clock": CLOCK,
    "as_of": AS_OF,
    "today": TODAY,
    "ruling_texts": RULING_TEXTS,
    "url_checks": URL_CHECKS,
    "locator_checks": LOCATOR_CHECKS,
    "family_checks": FAMILY_CHECKS,
    "probes": {
        "timeout": W1,
        "request": W1,
        "connection": SD + "header-dated",
    },
}
MANIFEST_BYTES = pretty(MANIFEST) + "\n"

# ---- everything below reads the manifest as written -----------------------------------------------------
M = json.loads(MANIFEST_BYTES)
cap, as_of = M["cap"], M["as_of"]
resp = {
    u: (r["status"], r["headers"], r["body"].encode("utf-8")) for u, r in M["responses"].items()
}
mhosts = set(M["manifest_hosts"])
assert (
    all(b for _, _, b in [resp[W1]])
    and len(resp[SD + "at-cap"][2]) == cap
    and len(resp[SD + "over-cap"][2]) == cap + 1
)


class Refused(Exception):
    pass


def fetch(url, hosts, trace=None):
    """Independent model of D3-D8: returns (record, body, media_type); record['reason'] is set when refused."""
    rec = {
        "url": url,
        "resolved_ip": None,
        "status": None,
        "bytes": None,
        "sha256": None,
        "published_located": None,
        "published_source": None,
        "hops": 0,
        "item_id": None,
        "reason": None,
    }
    cur, hops = url, 0
    try:
        while True:
            host = urlsplit(cur).hostname
            if trace is not None:
                trace.append(host)
            for a in M["hosts"][host]:
                if not public(a):
                    raise Refused(f"host {host} resolves to {a}, which is not a public address")
            rec["resolved_ip"] = M["hosts"][host][0]
            status, headers, body = resp[cur]
            rec["status"] = status
            if status in (301, 302):
                loc = headers["Location"]
                if hops == MAX_REDIRECTS:
                    raise Refused(f"{url} redirected more than {MAX_REDIRECTS} times")
                if not loc.startswith("https://"):
                    raise Refused(f"redirect to {loc} refused: the scheme must be https")
                if urlsplit(loc).hostname not in hosts:
                    raise Refused(
                        f"redirect to host {urlsplit(loc).hostname} refused: not a host named in the manifest"
                    )
                hops += 1
                rec["hops"] = hops
                cur = loc
                continue
            if status != 200:
                raise Refused(f"{url} answered status {status}")
            if len(body) > cap:
                raise Refused(f"{url} body is larger than the {cap}-byte cap")
            rec["bytes"], rec["sha256"] = len(body), sha(body)
            located = locate(headers, body)
            rec["published_located"], rec["published_source"] = located
            return rec, body, headers["Content-Type"]
    except Refused as why:
        rec["reason"] = str(why)
        return rec, None, None


def locate(headers, body):
    if "Last-Modified" in headers:
        return parsedate_to_datetime(
            headers["Last-Modified"]
        ).date().isoformat(), "header:last-modified"
    found = re.search(r"^Published:\s*(\d{4}-\d{2}-\d{2})", body.decode("utf-8"), re.MULTILINE)
    return (found.group(1), "body:published-line") if found else (None, None)


def convert_paragraphs(html):
    """The R1 rule for this key's HTML (tests/test_html_text.py): head dropped, one line per <p>; text.rstrip('\\n') is the item text."""
    body = re.sub(r"<head>.*?</head>", "", html)
    assert set(re.findall(r"</?(\w+)", body)) <= {"html", "body", "p"}
    return "\n".join(re.findall(r"<p>(.*?)</p>", body))


# ---- intake over the rows (the row's own date first, before any fetch; then fetch, media, located date) ------
accepted, refused, fetches, evidence, texts = [], [], [], [], {}
for (key, *_), row in zip(SPEC, M["research_manifest"]["rows"]):
    pub = row.get("published")
    loc = row["locator"]
    if "path" in row:
        rec, text = None, M["research_manifest"]["files"][row["path"]]
    else:
        why = (
            UNDATED
            if pub is None
            else (f"evidence item {loc} is after the cutoff" if pub > as_of else None)
        )
        if why:  # O7-R48 L3: the row's own date refuses before any fetch; no record, no resolver or connector call
            refused.append(
                {
                    "key": key,
                    "family": row["family"],
                    "published": pub,
                    "locator": loc,
                    "reason": why,
                }
            )
            continue
        rec, body, media = fetch(row["url"], mhosts)
        text, why = None, rec["reason"]
        if why is None:
            base = media.split(";")[0]
            if base == "text/html":
                text = convert_paragraphs(body.decode("utf-8"))
            elif base == "text/plain" and media.split(";")[1].strip() == "charset=utf-8":
                text = body.decode("utf-8-sig")
            else:
                why = f"{row['url']} returned unsupported media type {base}"
        if why is None and rec["published_located"] and rec["published_located"] > as_of:
            why = f"evidence item {loc} has a located publication date {rec['published_located']} after the cutoff {as_of}"
        if why:
            rec["reason"], text = why, None
    if rec is not None and rec["reason"]:
        refused.append(
            {
                "key": key,
                "family": row["family"],
                "published": pub,
                "locator": loc,
                "reason": rec["reason"],
            }
        )
    else:
        item_id = f"ev-{len(accepted) + 1}"
        if rec:
            rec["item_id"] = item_id
        accepted.append(item_id)
        texts[key] = text
        evidence.append(
            {
                "item_id": item_id,
                "family": row["family"],
                "published": pub,
                "locator": loc,
                "sha256": sha(text),
                "path": row.get("path"),
                "retrieved": CLOCK,
                "origin": "supplied" if "path" in row else "web",
                "url": row.get("url"),
            }
        )
    if rec is not None:
        fetches.append(rec)
assert accepted == [f"ev-{i}" for i in range(1, 10)], accepted

entries = sorted(
    ({k: r[k] for k in ("locator", "family", "published", "reason")} for r in refused),
    key=lambda e: e["locator"],
)
FETCHES_BYTES, REJECTED_BYTES = dump(fetches), dump(entries)
by_url = {f["url"]: f for f in fetches}


def redirect_case(path):
    resolved = []
    rec, _, _ = fetch(RA + path, mhosts, resolved)
    return {
        "url": rec["url"],
        "hops": rec["hops"],
        "status": rec["status"],
        "reason": rec["reason"],
        "resolved_hosts": resolved,
    }


REDIRECTS = {
    "three_hops_ok": redirect_case("three-hops"),
    "fourth_hop": redirect_case("four-hops"),
    "to_http": redirect_case("to-http"),
    "to_non_manifest_host": redirect_case("to-outside"),
    "to_private": redirect_case("to-private"),
}
assert REDIRECTS["three_hops_ok"]["status"] == 200 and REDIRECTS["three_hops_ok"]["reason"] is None
assert REDIRECTS["to_http"]["resolved_hosts"] == ["redirect-a.example"]
assert (
    len(REDIRECTS["three_hops_ok"]["resolved_hosts"]) == 4
    and len(REDIRECTS["fourth_hop"]["resolved_hosts"]) == 4
)
assert REDIRECTS["fourth_hop"]["hops"] == 3 and REDIRECTS["fourth_hop"]["reason"]
# a host the probe names is a manifest host for its own probe
HOST_CASES = {}
for h, addrs in M["hosts"].items():
    first_bad = next((a for a in addrs if not public(a)), None)
    HOST_CASES[h] = {
        "addresses": addrs,
        "public": first_bad is None,
        "class": klass(first_bad) if first_bad else "public",
        "reason": f"host {h} resolves to {first_bad}, which is not a public address"
        if first_bad
        else None,
    }
assert HOST_CASES["mapped.example"]["class"] == "private" and HOST_CASES["trade-press.example"][
    "reason"
].endswith("10.0.0.5, which is not a public address")

VECTORS = [
    ("127.0.0.1", False),
    ("10.0.0.5", False),
    ("169.254.169.254", False),
    ("100.64.0.1", False),
    ("224.0.0.1", False),
    ("0.0.0.0", False),
    ("240.0.0.1", False),
    ("203.0.113.10", False),
    ("8.8.8.8", True),
    (f"{PUB}.34", True),
    ("::1", False),
    ("::", False),
    ("fe80::1", False),
    ("ff02::1", False),
    ("::ffff:10.0.0.1", False),
    ("::ffff:8.8.8.8", True),
    ("2001:db8::1", False),
    ("2606:4700::1111", True),
    ("4000::1", False),
    ("fec0::1", False),
]
for a, label in VECTORS:
    assert public(a) == label, (a, label)

url_reasons = {
    "http": "the scheme must be https",
    "file": "the scheme must be https",
    "ftp": "the scheme must be https",
    "data": "the scheme must be https",
    "userinfo": "a user name or password is not allowed",
    "empty_host": "the host is missing",
}
for name, u in M[
    "url_checks"
].items():  # check each static case against the model's reading of the URL
    parts = urlsplit(u)
    expect = (
        "the scheme must be https"
        if parts.scheme != "https"
        else "a user name or password is not allowed"
        if parts.username or parts.password
        else "the host is missing"
    )
    assert url_reasons[name] == expect, name

good = RULING_TEXTS["good"]
good_date = next(line.split(": ")[1] for line in good.splitlines() if line.startswith("date:"))
html_text = texts["html"]
EXPECTED = {
    "schema_version": "cpdr-web-retrieval-expected/1",
    "derivation_note": "Built by cases/cpdr-web-retrieval/builder/build.py from manifest.json; every hash from embedded bytes. Reasons not marked _source are written here by the oracle preparer; they name no code path.",
    "gate": {
        "no_ruling": {
            "exception": "EvidenceFetchRefused",
            "text": "url rows need web retrieval, which is paused: give research_ruling, a user ruling under docs/rulings with lifts: live-provider-pause, by: user, date: and a configs: line naming web-retrieval",
        },
        "configs_missing": {
            "exception": "LivePauseInForce",
            "text": "the ruling does not list 'web-retrieval'",
            "_source": "src/deploy_workflow/model/adapter.py:192 (the configs: token test, with config_id 'web-retrieval')",
        },
        "lifts_missing": {
            "exception": "LivePauseInForce",
            "text": "the ruling needs exactly one lifts: line",
            "_source": "src/deploy_workflow/model/adapter.py:179 (with key 'lifts')",
        },
        "good": {"config_id": "web-retrieval", "date": good_date, "sha256": sha(good)},
        "resolver_calls_before_gate": 0,
        "unused_ruling": {
            "exception": "ResearchRulingUnused",
            "text": "a research_ruling is only read when the research manifest has a url row",
            "_note": "mirrors src/deploy_workflow/run_inputs.py:349 (ResearchManifestUnused)",
        },
    },
    "url_checks": {
        n: {"url": u, "reason": f"url {u}: {url_reasons[n]}"} for n, u in M["url_checks"].items()
    },
    "locator_checks": {
        n: {
            "locator": u,
            "reason": LOCATOR_BLOCK if "<<<" in u else LOCATOR_CELL,
            "_source": "preparer text in the form of intake.parse_rows's IntakeError texts ('manifest row needs a non-empty locator'); the rule is research/dossier.breaks_a_table_cell and the <<< check of dossier._cell; the reason names no locator text",
        }
        for n, u in M["locator_checks"].items()
    },
    "family_checks": {
        n: {
            "family": f,
            "reason": FAMILY_BLOCK if "<<<" in f else FAMILY_CELL,
            "_source": "preparer text, same form as locator_checks; the rule is research/dossier.breaks_a_table_cell and the <<< check of dossier._cell; the reason names no family text",
        }
        for n, f in M["family_checks"].items()
    },
    "is_public": {
        "vectors": [{"addr": a, "public": p} for a, p in VECTORS],
        "rule": "ipaddress is_global after unwrapping ::ffff:a.b.c.d, and not multicast, reserved or site-local",
        "_note": "ipaddress reports is_global True for the multicast vectors 224.0.0.1 and ff02::1 and for the unallocated 4000::1 and the site-local fec0::1 (Python 3.14.6); none is public. For every other address public == ipaddress is_global of the unwrapped address, so a property test compares with this rule (is_global and not multicast, reserved or site-local), not with is_global alone (O7-R48 M1).",
        "ipaddress_is_global": {a: unwrap(a).is_global for a, _ in VECTORS},
    },
    "hosts": {"_note": HOSTS_NOTE, **HOST_CASES},
    "redirects": {
        **REDIRECTS,
        "_note": "hops = redirects that passed the scheme, manifest-host and hop-limit checks, counted before the new host is resolved; the limit is 3, a fourth redirect is refused. status is the last response read; resolved_hosts are the hosts the resolver was asked about, in order.",
    },
    "request": {
        "method": "GET",
        "path": urlsplit(M["probes"]["request"]).path
        + "?"
        + urlsplit(M["probes"]["request"]).query,
        "headers": {
            "Host": "sector-desk.example",
            "User-Agent": "deploy-workflow-cpdr",
            "Accept": "text/html, text/plain",
        },
        "verbatim_url": M["probes"]["request"],
    },
    "connection": {
        "host": "sector-desk.example",
        "ip": M["hosts"]["sector-desk.example"][0],
        "port": 443,
        "server_hostname": "sector-desk.example",
        "check_hostname": True,
        "verify_mode": "CERT_REQUIRED",
        "resolver_calls_per_hop": 1,
        "probe_url": M["probes"]["connection"],
    },
    "proxy": {
        "env": {"HTTPS_PROXY": "http://127.0.0.1:9", "https_proxy": "http://127.0.0.1:9"},
        "ip_received": M["hosts"]["sector-desk.example"][0],
    },
    "timeout": {
        "total_seconds": M["timeouts"]["total_seconds"],
        "url": M["probes"]["timeout"],
        "reason": f"{M['probes']['timeout']} took longer than {M['timeouts']['total_seconds']} seconds",
    },
    "cap": {
        "cap": cap,
        "at_cap_sha256": sha(resp[SD + "at-cap"][2]),
        "over_cap_reason": f"{SD}over-cap body is larger than the {cap}-byte cap",
        "max_read_request": cap + 1,
    },
    "published": {
        "header_case": {
            "url": SD + "header-dated",
            **{
                k: by_url[SD + "header-dated"][k] for k in ("published_located", "published_source")
            },
            "disposition": "accepted",
            "reason": None,
        },
        "body_case": {
            "url": SD + "body-dated",
            **{k: by_url[SD + "body-dated"][k] for k in ("published_located", "published_source")},
            "disposition": "accepted",
            "reason": None,
        },
        "located_after_cutoff": {
            "url": SD + "body-late",
            **{k: by_url[SD + "body-late"][k] for k in ("published_located", "published_source")},
            "disposition": "refused",
            "reason": by_url[SD + "body-late"]["reason"],
        },
        "neither": {
            "url": SD + "no-date",
            "disposition": "refused_before_fetch",
            "fetched": False,
            "resolver_calls": 0,
            "connector_calls": 0,
            "reason": UNDATED,
            **dict(
                zip(
                    ("published_located", "published_source"),
                    locate(resp[SD + "no-date"][1], resp[SD + "no-date"][2]),
                )
            ),
            "_note": "the row's own date refuses it (O7-R48 L3): no fetch, no record; the located fields describe the response if it were fetched directly",
        },
        "located_cannot_admit": {
            "url": SD + "located-only",
            "disposition": "refused_before_fetch",
            "fetched": False,
            "resolver_calls": 0,
            "connector_calls": 0,
            "reason": UNDATED,
            **dict(
                zip(
                    ("published_located", "published_source"),
                    locate(resp[SD + "located-only"][1], resp[SD + "located-only"][2]),
                )
            ),
            "_note": "the row's own date refuses it (O7-R48 L3): no fetch, no record; the located fields describe the response if it were fetched directly",
        },
        "_source": "the undated reason is src/deploy_workflow/research/intake.py:130 (holds for any run date after as_of); located_after_cutoff is written here",
    },
    "text": {
        "html_case": {
            "url": W1,
            "converted_text": html_text,
            "converted_sha256": sha(html_text),
            "rule": "head dropped, one line per <p>, trailing newline stripped (tests/test_html_text.py; tests/research/test_intake.py:214)",
        },
        "plain_case": {"url": SD + "header-dated", "sha256": sha(resp[SD + "header-dated"][2])},
        "unsupported_media_reason": by_url[SD + "report.pdf"]["reason"],
    },
    "records": {
        "_note": "locator rule (O7-R48 H2): a url row's locator must pass the fence header rule (prompts/fence.py:36, [A-Za-z0-9][A-Za-z0-9._:+/-]*), so it cannot hold ?, =, & or %; the row's locator, not its url, goes in the header. Row 2 carries a distinct locator for that reason; every other url row's locator is its url. Attempted fetches only: a row refused by its own date is never fetched and has no record (O7-R48 L3).",
        "fetches_json": {
            "file_bytes": FETCHES_BYTES,
            "file_sha256": sha(FETCHES_BYTES),
            "shape": "one record per attempted fetch (every url row not refused by its own row date), in manifest order: url, resolved_ip (last connection made), status (last response read), bytes and sha256 (raw body, set exactly when a 200 body was read within the cap), published_located, published_source, hops (redirects that passed the scheme, manifest-host and hop-limit checks), item_id (set iff accepted), reason (set iff the item was refused after a fetch was attempted); json.dumps indent 1 plus a newline",
        },
        "evidence_json": {"rows": evidence},
        "rejected_json": {
            "entries": entries,
            "file_bytes": REJECTED_BYTES,
            "file_sha256": sha(REJECTED_BYTES),
        },
        "pack_sources": ["identity", "financial"] + accepted,
    },
    "run_json": {
        "keys": ["research_ruling_path", "research_ruling_sha256", "research_ruling_date"],
        "absent_without_ruling": True,
        "ruling_date": good_date,
        "ruling_sha256": sha(good),
    },
    "method": {
        "sentences": [
            "An item dated after the cutoff is refused. The cutoff is the earlier of the as-of date and the context's `run.cutoff`; with no `run.cutoff` it is the as-of date.",
            "A URL row is fetched only when the run names a user ruling that lifts the live-provider pause for `web-retrieval` (`research_ruling`); without one every URL row is refused before anything is written, and the refusal names the ruling the run needs. A fetched item is `https` only, from the user's manifest, with every address public, at most three redirects, the same byte cap, and a recorded url, address, status, size and hash in `research/fetches.json`; a publication date found in the response can refuse an item, never admit one.",
            "No provider or credential is used; the web is used only to fetch the user's URL rows under the ruling Intake names, and the readiness ceiling is `RESEARCH_READY`.",
            "Each research item names a file or an `https` url, a family, a publication date, a locator and the tag `research`.",
        ],
        "_source": "entries 1-2: docs/superpowers/plans (O7b-2 plan) section S5 Text, verbatim; entries 3-4: O7-R56 (cpdr.md lines 3 and 26), verbatim",
    },
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "manifest.json").write_bytes(MANIFEST_BYTES.encode("utf-8"))
(OUT / "expected.json").write_bytes((pretty(EXPECTED) + "\n").encode("utf-8"))
print(f"wrote {OUT}")
