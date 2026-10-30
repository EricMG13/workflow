import sys, json, re, hashlib
sys.path[:0] = [__import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "../../..")) + "/tests",
                __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "../../..")) + "/src"]
import czr_runs
from deploy_vii.quotes import normalise

M = czr_runs.manifest()
SHA = {d["source_id"]: d["sha256"] for d in M["documents"]}
PAGES = {d["source_id"]: czr_runs.pages((czr_runs.CASE / d["path"]).read_bytes()) for d in M["documents"]}
K, Q, R = "czr-fy2025-10k", "czr-q2-2026-10q", "czr-q2-2026-release"
PACK = "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>"

def cite(src, page, quote):
    text = PAGES[src][page - 1]
    assert normalise(quote) in normalise(text), (src, page, quote)
    return {"source_id": src, "source_sha256": SHA[src], "locator": f"page:{page}", "quote": quote}

def line_of(src, page, label_start):
    """The one verbatim page line that starts with label_start."""
    hits = [l for l in PAGES[src][page - 1].split("\n") if l.startswith(label_start)]
    assert len(hits) == 1, (src, page, label_start, hits)
    return hits[0]

def cite_line(src, page, label_start):
    return cite(src, page, line_of(src, page, label_start))
