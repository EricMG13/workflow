"""Writes cases/cp2h-context-owner/* (stdlib only; deploy_vii and deploy_workflow are never imported).

Phase 4 Task 0 oracle: CP-2H builds its rating register from the context file's `ratings` rows.
Every expected value is hand-derived from three things and never from the code Phase 4 builds:

  1. the Phase 4 plan (docs/superpowers/plans/2026-10-31-phase-4-ratings.md, Task 0 and Task 3),
  2. the rulings it cites (docs/rulings/2026-10-31-context-plan.md; the fixed combined scale), and
  3. the frozen upstream oracle cases/cp2h-owner/*, read here by sha256 (CP-0, CP-1, CP-2A, CP-2G
     literals, every CP-2G metric, every CP-1 ratio, every T2R.3-T2R.6 and T2R.9 cell).

What changes against cases/cp2h-owner: the register (T2R.2) and the divergence (T2R.8) come from the
context rows on a fixed combined scale, the agencies are S&P and Moody's, and the T2R.3 trigger terms
are the cp2h-owner page:3 terms with the two fictional agencies renamed. Everything else is the
frozen value with the agency names renamed and the ratings source hash replaced.

Run: python3 -I cases/cp2h-context-owner/builder/build.py [OUT_DIR]   (from the repository root)
Two runs write byte-identical files.
"""

import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "cases" / "cp2h-context-owner"

# --- 0. pinned inputs ---------------------------------------------------------------------------

PINS = {
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "cases/context/research-minimal.json": "c09646df4743d845f6b972558bb92c288f0335c1d4959ddd0fb2a1bf39bfbcca",
    "cases/cp2h-owner/manifest.json": "ff74170b7e69824be7e323789f244773465b7ad12eadff237aba7c3563877587",
    "cases/cp2h-owner/submissions.json": "bde5785ea2dee72c2f78fbb8f0762655f81b86b9565f541931f8ef033180f54e",
    "cases/cp2h-owner/expected.json": "d0d0310087cfed3bc1ca9c90d1bcd4b54960f0da3b29b449997e80459c14fae6",
    "cases/cp2h-owner/cp2h-view-tree.json": "3fb8cf29e73431ac2be72f168d26f72d830c475d42590032a49d5a466b5e0728",
}
RAW = {}
for rel, digest in PINS.items():
    RAW[rel] = (ROOT / rel).read_bytes()
    assert hashlib.sha256(RAW[rel]).hexdigest() == digest, f"input drift: {rel}"
F_MAN = json.loads(RAW["cases/cp2h-owner/manifest.json"])
F_SUB = json.loads(RAW["cases/cp2h-owner/submissions.json"])
F_EXP = json.loads(RAW["cases/cp2h-owner/expected.json"])
F_TREE = json.loads(RAW["cases/cp2h-owner/cp2h-view-tree.json"])
BASE_CONTEXT = json.loads(RAW["cases/context/research-minimal.json"])


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def page_sha(pages) -> str:
    return sha("\f".join(p["text"] for p in pages).encode("utf-8"))


def dumps(obj) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


# --- 1. names, run, upstream -------------------------------------------------------------------

RENAME = (("Alder Ratings", "S&P"), ("Brook Credit", "Moody's"))
OLD_NAMES = tuple(o for o, _ in RENAME)
ISSUER = ("northbridge-synthetic", "Northbridge Synthetic Group")
AS_OF = "2026-01-10"


def possessive(name: str) -> str:
    return name if name.endswith("'s") else name + "'s"


def rename(text: str) -> str:
    # possessives first: "Brook Credit's rating" -> "Moody's rating", never "Moody's's"
    text = text.replace("Brook Credit's", "Moody's").replace("Alder Ratings's", "S&P's")
    for old, new in RENAME:
        text = text.replace(old, new)
    return text


def walk(node, fn):
    """Rebuild `node` with `fn` applied to every string value (keys untouched)."""
    if isinstance(node, dict):
        return {k: walk(v, fn) for k, v in node.items()}
    if isinstance(node, list):
        return [walk(v, fn) for v in node]
    if isinstance(node, str):
        return fn(node)
    return node


# --- 2. the fixed combined scale (ruling; written here from the agencies' public scales) ---------

SCALE_ROWS = (
    (1, "AAA", "AAA", "Aaa"),
    (2, "AA+", "AA+", "Aa1"),
    (3, "AA", "AA", "Aa2"),
    (4, "AA-", "AA-", "Aa3"),
    (5, "A+", "A+", "A1"),
    (6, "A", "A", "A2"),
    (7, "A-", "A-", "A3"),
    (8, "BBB+", "BBB+", "Baa1"),
    (9, "BBB", "BBB", "Baa2"),
    (10, "BBB-", "BBB-", "Baa3"),
    (11, "BB+", "BB+", "Ba1"),
    (12, "BB", "BB", "Ba2"),
    (13, "BB-", "BB-", "Ba3"),
    (14, "B+", "B+", "B1"),
    (15, "B", "B", "B2"),
    (16, "B-", "B-", "B3"),
    (17, "CCC+", "CCC+", "Caa1"),
    (18, "CCC", "CCC", "Caa2"),
    (19, "CCC-", "CCC-", "Caa3"),
    (20, "CC", "CC", "Ca"),
    (21, "C", "C", "C"),
    (22, "SD", "RD", None),  # S&P selective default, Fitch restricted default; Moody's has none
    (23, "D", "D", None),  # S&P and Fitch only
)
SCALE = {
    "S&P": {sp: pos for pos, sp, _, _ in SCALE_ROWS if sp},
    "Fitch": {fi: pos for pos, _, fi, _ in SCALE_ROWS if fi},
    "Moody's": {mo: pos for pos, _, _, mo in SCALE_ROWS if mo},
}
UNRATED = ("Withdrawn", "Not rated")

# --- 3. the ratings sources (page text; pages 1-2 stay the frozen cp2h-owner pages) --------------

SS = F_MAN["synthetic_source"]
POS_PAGES = deepcopy(SS["positive"]["pages"])
GAP_PAGES = deepcopy(SS["gap"]["pages"])
assert page_sha(POS_PAGES) == SS["positive"]["sha256"]
assert page_sha(GAP_PAGES) == SS["gap"]["sha256"]
OLD_SHA = {"positive": SS["positive"]["sha256"], "gap": SS["gap"]["sha256"]}


def with_terms(pages, terms_text):
    return [pages[0], pages[1], {"locator": "page:3", "text": terms_text}]


POS_TERMS = rename(POS_PAGES[2]["text"])
GAP_TERMS = rename(GAP_PAGES[2]["text"])
# terms_agency_unrated: the S&P rows and one Fitch row (no Moody's rows, so the Fitch rule is the only breach)
fitch_lines = [ln for ln in POS_TERMS.split("\n") if not ln.startswith("Moody's  ")]
fitch_lines.append("Fitch  Downgrade  Net debt to EBITDA  Above  2.25x")
FITCH_TERMS = "\n".join(fitch_lines)
RATINGS = {
    "positive": {"pages": with_terms(POS_PAGES, POS_TERMS)},
    "gap": {"pages": with_terms(GAP_PAGES, GAP_TERMS)},
    "fitch_terms": {"pages": with_terms(POS_PAGES, FITCH_TERMS)},
}
for key, item in RATINGS.items():
    item["sha256"] = page_sha(item["pages"])
NEW_SHA = {"positive": RATINGS["positive"]["sha256"], "gap": RATINGS["gap"]["sha256"]}
assert len({v["sha256"] for v in RATINGS.values()} | set(OLD_SHA.values())) == 5

# --- 4. the context files ----------------------------------------------------------------------


def row(agency, scope, rating, outlook, as_of):
    return {"agency": agency, "scope": scope, "rating": rating, "outlook": outlook, "as_of": as_of}


ROWS = {
    "positive": [
        row("S&P", "issuer", "BB", "Negative", "2025-11-14"),
        row("Moody's", "issuer", "Ba3", "Stable", "2025-10-02"),
    ],
    "gap": [
        row("S&P", "issuer", "BB", "Negative", ""),
        row("Moody's", "issuer", "Withdrawn", "Stable", "2025-10-02"),
    ],
    "outlook_unstated": [
        row("S&P", "issuer", "BB", "", "2025-11-14"),
        row("Moody's", "issuer", "Ba3", "Stable", "2025-10-02"),
    ],
    "no_ratings": [],
    "off_scale": [row("Other", "issuer", "A", "Stable", "2025-11-14")],
    "duplicate_agency": [
        row("S&P", "issuer", "BB", "Negative", "2025-11-14"),
        row("S&P", "facility", "BB-", "Negative", "2025-11-14"),
    ],
    "terms_agency_unrated": [row("S&P", "issuer", "BB", "Negative", "2025-11-14")],
}


def context_doc(rows, as_of=AS_OF):
    doc = deepcopy(BASE_CONTEXT)
    doc["run"].update({"pathway": "distressed_restructuring", "case_kind": "synthetic", "as_of": as_of})
    doc["identity"].update({"issuer_name": ISSUER[1], "issuer_id": ISSUER[0]})
    doc["ratings"] = deepcopy(rows)
    return doc


def pretty(doc) -> str:  # JSON.stringify(o, null, 2) of the form, plus the form's trailing LF
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def minified(doc) -> str:  # JSON.stringify(o): no spaces, one line
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=False) + "\n"


def uncitable(doc) -> str:
    """The positive file with row 2 (Moody's) written with its key and value on separate lines
    (valid JSON, not the form's layout): neither the key/value line nor a one-line object holds
    its `rating` or `outlook` value."""
    text = pretty(doc)
    start = text.index('"agency": "Moody\'s"')
    head, tail = text[:start], text[start:]
    for key, value in (("rating", "Ba3"), ("outlook", "Stable")):
        old = f'"{key}": "{value}"'
        assert tail.count(old) == 1
        tail = tail.replace(old, f'"{key}":\n        "{value}"')
    return head + tail


CONTEXT_FILES = {}  # file name -> (text, case ids using it)


def put(name, text):
    assert name not in CONTEXT_FILES
    CONTEXT_FILES[name] = text


put("context-positive.json", pretty(context_doc(ROWS["positive"])))
put("context-gap.json", pretty(context_doc(ROWS["gap"])))
put("context-outlook-unstated.json", pretty(context_doc(ROWS["outlook_unstated"])))
put("context-no-ratings.json", pretty(context_doc(ROWS["no_ratings"])))
put("context-off-scale.json", pretty(context_doc(ROWS["off_scale"])))
put("context-duplicate-agency.json", pretty(context_doc(ROWS["duplicate_agency"])))
put("context-terms-agency-unrated.json", pretty(context_doc(ROWS["terms_agency_unrated"])))
put("context-mismatch.json", pretty(context_doc(ROWS["positive"], as_of="2026-01-11")))
put("context-minified.json", minified(context_doc(ROWS["positive"])))
put("context-uncitable.json", uncitable(context_doc(ROWS["positive"])))
CTX_SHA = {n: sha(t.encode("utf-8")) for n, t in CONTEXT_FILES.items()}

# --- 5. object-anchored citations into a context file (Phase 3 contract, Phase 4 Task 3 item 3) ---

FIELDS = ("agency", "scope", "rating", "outlook", "as_of")
_VALUE = r'"{key}"\s*:\s*("(?:[^"\\]|\\.)*")'


def line_no(text, offset):
    return text.count("\n", 0, offset) + 1


def rating_cites(text):
    """One dict per `ratings[i]` row: field -> (locator, quote) or None.

    Quote rule (hand-stated, the contract of Phase 3/4): the key/value text `"rating": "BB"` when the
    field occupies its own line (the line, stripped, is the key/value text with at most one trailing
    comma) and the text is unique in that line; else the text from the row object's `{` through the
    value when that is one line and unique in it; else None (never a guessed span)."""
    lines = text.splitlines()
    assert text.count('"ratings"') == 1
    pos = text.index("[", text.index('"ratings"')) + 1
    decoder = json.JSONDecoder()
    out = []
    while True:
        while text[pos] in " \n\t\r,":
            pos += 1
        if text[pos] == "]":
            return out
        obj, end = decoder.raw_decode(text, pos)
        cites = {}
        for key in FIELDS:
            m = re.search(_VALUE.format(key=key), text[pos:end])
            assert m is not None, key
            key_at, value_end = pos + m.start(), pos + m.end()
            kv = text[key_at:value_end]
            found = None
            if "\n" not in kv:
                line = lines[line_no(text, key_at) - 1]
                if line.strip().rstrip(",") == kv and line.count(kv) == 1:
                    found = (f"line:{line_no(text, key_at)}", kv)
            if found is None:
                anchored = text[pos:value_end]
                if "\n" not in anchored:
                    line = lines[line_no(text, pos) - 1]
                    if line.count(anchored) == 1:
                        found = (f"line:{line_no(text, pos)}", anchored)
            cites[key] = found
        out.append(cites)
        pos = end


def issuer_name_cite(text):
    """The CP-0 / CP-1 `context` assessment's own cited line (as the Phase 2 oracle)."""
    lines = text.splitlines()
    for quote in ('"issuer_name": "Northbridge Synthetic Group"', '"issuer_name":"Northbridge Synthetic Group"'):
        hits = [n for n, ln in enumerate(lines, 1) if quote in ln]
        if len(hits) == 1 and lines[hits[0] - 1].count(quote) == 1:
            return f"line:{hits[0]}", quote
    raise AssertionError("issuer_name not citable")


# --- 6. T2R.2 / T2R.8 facts, hand-derived from the rows and the fixed scale -----------------------

POSITION_UNIT = "scale position"
NOTCH_UNIT = "notches"
POSITION_FORMULA = "position of the rating on the fixed combined scale"
NOTCH_FORMULA = "absolute difference of the two positions on the combined scale"
UNDATED_PERIOD = "As of the rating register, publication date not stated"  # register_published is "not stated"
NOT_STATED = "Not stated"


class Register:
    """The register and divergence facts of one context file, in the order the frozen builder emits them."""

    def __init__(self, rows, text, ctx_name):
        self.rows, self.sha = rows, CTX_SHA[ctx_name]
        self.cites = rating_cites(text)
        assert len(self.cites) == len(rows)
        self.facts, self.by_id, self.fact_cites = [], {}, {}
        self.parsed, self.positions = [], []
        self.build()

    def cite(self, i, field):
        loc_quote = self.cites[i][field]
        assert loc_quote is not None, (i, field)
        return {
            "source_id": "context",
            "source_sha256": self.sha,
            "locator": loc_quote[0],
            "quote": loc_quote[1],
        }

    def add(self, rec, cites):
        self.facts.append(rec)
        self.by_id[rec["fact_id"]] = rec
        self.fact_cites[rec["fact_id"]] = cites
        return rec

    def lineage(self, derives, own=()):
        out = list(own)
        for d in derives:
            assert self.by_id[d]["status"] == "known", d
            out += self.fact_cites[d]
        out = [c for k, c in enumerate(out) if c not in out[:k]]
        if not derives:
            return out
        first = {}  # one citation per (source, locator), the first of the inputs on it, in input order
        for c in out:
            first.setdefault((c["source_id"], c["locator"]), c)
        return list(first.values())

    def text_fact(self, table, row_id, field, label, value, value_class, derives=(), own=()):
        rec = {
            "fact_id": f"{table}.{row_id}.{field}",
            "table_id": table,
            "row_id": row_id,
            "field": field,
            "label": label,
            "status": "known",
            "text": value,
            "shown": value,
            "value_class": value_class,
        }
        if derives:
            rec["derives_from"] = list(derives)
        cites = self.lineage(derives, own)
        if cites:
            rec["citations"] = cites
        return self.add(rec, cites)

    def number_fact(self, table, row_id, field, label, value, unit, period, formula, derives):
        cites = self.lineage(derives)
        rec = {
            "fact_id": f"{table}.{row_id}.{field}",
            "table_id": table,
            "row_id": row_id,
            "field": field,
            "label": label,
            "status": "known",
            "unit": unit,
            "period": period,
            "amount_exact": str(value),
            "shown": f"{value} {unit}",
            "decimals": None,
            "value_class": "calculated",
            "formula": formula,
            "calculation_id": f"calc:{table}.{row_id}.{field}",
            "derives_from": list(derives),
        }
        if cites:
            rec["citations"] = cites
        return self.add(rec, cites)

    def unsettled(self, table, row_id, field, label, unit, reason, period=None):
        rec = {
            "fact_id": f"{table}.{row_id}.{field}",
            "table_id": table,
            "row_id": row_id,
            "field": field,
            "label": label,
            "status": "not_applicable",
            "unit": unit,
            "period": period,
            "amount_exact": None,
            "shown": None,
            "limitation": reason,
        }
        return self.add(rec, [])

    def missing_text(self, table, row_id, field, label, reason):
        rec = {
            "fact_id": f"{table}.{row_id}.{field}",
            "table_id": table,
            "row_id": row_id,
            "field": field,
            "label": label,
            "status": "not_applicable",
            "text": None,
            "shown": None,
            "limitation": reason,
        }
        return self.add(rec, [])

    def build(self):
        for i, r in enumerate(self.rows):
            rid = f"r{i + 1:02d}"
            rating_cite, agency_cite = [self.cite(i, "rating")], [self.cite(i, "agency")]
            outlook = r["outlook"] or NOT_STATED
            dated = r["as_of"] or NOT_STATED
            self.text_fact("T2R.2", rid, "agency", "Agency", r["agency"], "source", own=agency_cite)
            self.text_fact("T2R.2", rid, "instrument", "Instrument", NOT_STATED, "source", own=rating_cite)
            self.text_fact("T2R.2", rid, "rating", "Rating", r["rating"], "source", own=rating_cite)
            self.text_fact(
                "T2R.2", rid, "outlook", "Outlook", outlook, "source",
                own=[self.cite(i, "outlook")] if r["outlook"] else rating_cite,
            )
            self.text_fact(
                "T2R.2", rid, "date", "Rating date", dated, "source",
                own=[self.cite(i, "as_of")] if r["as_of"] else rating_cite,
            )
            period = f"Rating dated {r['as_of']}" if r["as_of"] else "Rating date not stated"
            position = None if r["rating"] in UNRATED else SCALE[r["agency"]][r["rating"]]
            if position is None:
                reason = f"{possessive(r['agency'])} rating is {r['rating'].lower()}, so it has no position on the scale"
                self.unsettled("T2R.2", rid, "position", "Position on the combined scale", POSITION_UNIT, reason, period)
            else:
                self.number_fact(
                    "T2R.2", rid, "position", "Position on the combined scale", position, POSITION_UNIT,
                    period, POSITION_FORMULA, (f"T2R.2.{rid}.rating",),
                )
            self.positions.append(position)
            self.parsed.append(
                {
                    "agency": r["agency"],
                    "instrument": NOT_STATED,
                    "rating": r["rating"],
                    "outlook": outlook,
                    "date": dated,
                    "position": position,
                }
            )
        assert len(self.rows) == 2
        ra, rb = self.parsed
        pa, pb = self.positions
        at = ("T2R.8", "p01")
        self.text_fact(*at, "first_agency", "First agency", ra["agency"], None, derives=("T2R.2.r01.agency",))
        self.text_fact(*at, "second_agency", "Second agency", rb["agency"], None, derives=("T2R.2.r02.agency",))
        self.divergence = {"row": "p01", "notches": None, "lower": None, "outlooks": None}
        if pa is None or pb is None:
            who = ra if pa is None else rb
            why = f"{possessive(who['agency'])} rating is {who['rating'].lower()}, so no notch comparison is made"
            self.unsettled(*at, "notches", "Notches apart", NOTCH_UNIT, why, UNDATED_PERIOD)
            self.missing_text(*at, "lower_rated", "Lower rated", why)
            self.missing_text(*at, "outlook_match", "Outlooks", why)
            return
        positions = ("T2R.2.r01.position", "T2R.2.r02.position")
        notches = abs(pa - pb)
        self.number_fact(*at, "notches", "Notches apart", notches, NOTCH_UNIT, UNDATED_PERIOD, NOTCH_FORMULA, positions)
        lower = "Same rating" if pa == pb else (ra["agency"] if pa > pb else rb["agency"])
        self.text_fact(
            *at, "lower_rated", "Lower rated", lower, None,
            derives=(*positions, "T2R.2.r01.agency", "T2R.2.r02.agency"),
        )
        self.divergence.update(notches=notches, lower=lower)
        if NOT_STATED in (ra["outlook"], rb["outlook"]):
            who = ra if ra["outlook"] == NOT_STATED else rb
            self.missing_text(*at, "outlook_match", "Outlooks", f"An outlook is not stated for {who['agency']}")
        else:
            same = "Same" if ra["outlook"] == rb["outlook"] else "Different"
            self.text_fact(
                *at, "outlook_match", "Outlooks", same, None,
                derives=("T2R.2.r01.outlook", "T2R.2.r02.outlook"),
            )
            self.divergence["outlooks"] = same

    def own_lines(self):
        """The context-run additions to the own limitations (plan Task 3 item 5, in the plan's order)."""
        out = [
            "Scale positions come from a fixed combined-scale table in the module, not from an agency source."
        ]
        out += [f"The rating date is not stated for {r['agency']}." for r in self.rows if not r["as_of"]]
        out += [f"Rating scope: {r['scope']} ({r['agency']})." for r in self.rows]
        return out


LIM0 = (
    "Agency ratings and outlooks are user-supplied in the context file; trigger terms are read from "
    "the attached agency source."
)
LIM6 = (
    "The notch difference is measured on the module's fixed combined scale; outlook weighting and "
    "sub-notch differences are not modelled."
)

# --- 7. expected cases --------------------------------------------------------------------------

REG_TABLE = "T2R.2"
DIV_TABLE = "T2R.8"


def check_pages(node, pages):
    """Every ratings citation quote is a line of the new source's page it names."""
    if isinstance(node, dict):
        if node.get("source_id") == "ratings" and "quote" in node:
            n = int(node["locator"].split(":")[1])
            assert node["quote"] in pages[n - 1]["text"], node
        for v in node.values():
            check_pages(v, pages)
    elif isinstance(node, list):
        for v in node:
            check_pages(v, pages)


def retarget(node, variant):
    """Frozen subtree -> this case's: agency names renamed, the ratings source hash replaced."""

    def fn(s):
        return NEW_SHA[variant] if s == OLD_SHA[variant] else rename(s)

    return walk(node, fn)


def payload_for(variant, reg):
    """The frozen rating_triggers submission, renamed, with the register-line evidence re-cut to the context row."""
    sub = retarget(F_SUB["cases"][variant]["rating_triggers"], variant)
    for i, view in enumerate(sub["views"]):
        keep = [c for c in view["evidence"] if c["locator"] == "page:3"]
        row_cite = reg.cite(i, "rating")
        if variant == "gap" and i == 0:
            view["evidence"] = keep  # the frozen gap view cites terms only
        else:
            view["evidence"] = keep + [row_cite]
    return sub


def agency_view_facts(case, reg):
    """The T2R.7.aNN.agency facts of `case` with the citation their source fact carries (updated in place)."""
    out = []
    for n in (1, 2):
        fact = next(f for f in case["facts"] if f["fact_id"] == f"T2R.7.a{n:02d}.agency")
        assert fact["derives_from"] == [f"T2R.2.r{n:02d}.agency"], fact
        fact["citations"] = deepcopy(reg.fact_cites[f"T2R.2.r{n:02d}.agency"])
        out.append(fact)
    return out


def expected_case(variant, reg):
    case = retarget(F_EXP["cases"][variant], variant)
    pages = RATINGS[variant]["pages"]
    # replace the T2R.2 and T2R.8 facts in place
    new = {f["fact_id"]: f for f in reg.facts}
    old_ids = [f["fact_id"] for f in case["facts"] if f["table_id"] in (REG_TABLE, DIV_TABLE)]
    assert sorted(old_ids) == sorted(new), (old_ids, sorted(new))
    case["facts"] = [new.get(f["fact_id"], f) if f["fact_id"] in new else f for f in case["facts"]]
    agency_view_facts(case, reg)  # T2R.7.aNN.agency derives from T2R.2.rNN.agency
    # claims T2R.7.a01/a02 cite the analyst's evidence, in order
    sub = payload_for(variant, reg)
    for n, view in enumerate(sub["views"], 1):
        claim = next(c for c in case["claims"] if c["claim_id"] == f"T2R.7.a{n:02d}")
        claim["citations"] = deepcopy(view["evidence"])
    # parsed source, divergence, limitations
    case["parsed_source"]["register"] = reg.parsed
    case["divergence"] = [reg.divergence]
    lims = case["own_limitations"]
    assert len(lims) >= 8
    lims[0], lims[6] = LIM0, LIM6
    case["own_limitations"] = lims[:8] + reg.own_lines() + lims[8:]
    case["source_variant"] = variant
    case["source_sha256"] = NEW_SHA[variant]
    # nothing of the fictional agencies, no stale hash, and only ratings page:3 or context citations remain
    blob = json.dumps(case, ensure_ascii=False)
    assert not any(n in blob for n in OLD_NAMES), "an old agency name remains"
    assert OLD_SHA[variant] not in blob
    for f in case["facts"] + case["claims"]:
        for c in f.get("citations", []):
            assert c["source_id"] in ("context", "ratings", "financial", "identity"), c
            if c["source_id"] == "ratings":
                assert c["locator"] == "page:3", c
    check_pages(case, pages)
    return case


def fp05_not_meaningful_cell():
    gap = F_EXP["cases"]["gap"]["FP05"]["blocks"]["rating-triggers"]
    tab = next(t for t in gap["tabs"] if t["table_id"] == "T2R.8")
    cell = tab["rows"][0]["cells"][4]
    assert cell["field"] == "outlook_match" and cell["state"] == "not_meaningful"
    return deepcopy(cell)


def delta_case(base, reg, fp05_cell=None):
    """A case that equals `positive` except the listed replacements."""
    sub = payload_for("positive", reg)
    claims = []
    pos = base
    for n, view in enumerate(sub["views"], 1):
        claim = deepcopy(next(c for c in pos["claims"] if c["claim_id"] == f"T2R.7.a{n:02d}"))
        claim["citations"] = deepcopy(view["evidence"])
        claims.append(claim)
    out = {
        "same_as": "positive",
        "replaces": {
            "parsed_source.register": reg.parsed,
            "divergence": [reg.divergence],
            "facts": [*reg.facts, *agency_view_facts(deepcopy(pos), reg)],
            "claims": claims,
        },
    }
    if fp05_cell is not None:
        cell = deepcopy(fp05_cell)
        out["replaces"]["FP05.blocks.rating-triggers.tabs[T2R.8].rows[p01].cells[outlook_match]"] = cell
    return out


# --- 8. refusals --------------------------------------------------------------------------------

SOURCE_REFUSALS = (
    # id, case, context file, ratings source, class, expected issue, derivation
    (
        "no_ratings", "context-no-ratings.json", None, "context ratings empty",
        "Rating register not found",
        "ratings_source finds no ratings source (today's text, cp2h.py:154 REGISTER_NOT_FOUND) and the context holds no row",
    ),
    (
        "no_terms", "context-positive.json", None, "no trigger terms source",
        "Trigger terms not found",
        "rows but no `ratings` source: the terms cannot be read (cp2h.py:156 TERMS_NOT_FOUND)",
    ),
    (
        "off_scale", "context-off-scale.json", "positive", "rating not on the scale",
        "Rating not on the scale: Other A",
        "agency `Other` has no scale; cp2h.py:353 text `Rating not on the scale: <agency> <rating>`",
    ),
    (
        "duplicate_agency", "context-duplicate-agency.json", "positive", "agency twice",
        "Rating register not found",
        "S&P twice (issuer BB, facility BB-): the duplicate-agency rule of cp2h.py:346-348 reads REGISTER_NOT_FOUND",
    ),
    (
        "terms_agency_unrated", "context-terms-agency-unrated.json", "fitch_terms", "terms name an unrated agency",
        "Trigger terms not found",
        "terms name Fitch, which has no rated register row: cp2h.py:430-432 reads TERMS_NOT_FOUND",
    ),
    (
        "context_mismatch", "context-mismatch.json", "positive", "context disagrees with the run",
        "Context refused: run.as_of: context has '2026-01-11' but the run has '2026-01-10'",
        "context.py:764 `{path}: context has {theirs!r} but the run has {ours!r}` behind the `Context refused: ` prefix (plan Task 3 item 1); the only breach is run.as_of",
    ),
    (
        "uncitable_row", "context-uncitable.json", "positive", "context row cannot be cited",
        "Context rating row 2 (Moody's) cannot be cited as one unique span; ratings not used",
        "row 2's rating and outlook values sit on lines apart from their keys and the object spans several lines: no key/value line, no one-line object quote (plan Task 3 item 3); a named issue, not a raise",
    ),
)

# --- 9. main ------------------------------------------------------------------------------------


def trigger_view(positive_case):
    out = []
    for n, t in enumerate(positive_case["parsed_source"]["triggers"], 1):
        row = f"t{n:02d}"
        fact = next(f for f in positive_case["facts"] if f["fact_id"] == f"T2R.3.{row}.threshold")
        out.append(
            {
                "row": row,
                "agency": t["agency"],
                "direction": t["direction"],
                "metric": t["metric"],
                "comparison": t["comparison"],
                "threshold": {"ref": fact["fact_id"], "shown": fact["shown"], "status": fact["status"]},
            }
        )
    return out


def main():
    files = {}
    for name, text in CONTEXT_FILES.items():
        files[name] = text.encode("utf-8")

    regs = {
        "positive": Register(ROWS["positive"], CONTEXT_FILES["context-positive.json"], "context-positive.json"),
        "gap": Register(ROWS["gap"], CONTEXT_FILES["context-gap.json"], "context-gap.json"),
        "outlook_unstated": Register(
            ROWS["outlook_unstated"], CONTEXT_FILES["context-outlook-unstated.json"], "context-outlook-unstated.json"
        ),
        "minified": Register(ROWS["positive"], CONTEXT_FILES["context-minified.json"], "context-minified.json"),
    }
    # the minified file really is one span
    assert len(CONTEXT_FILES["context-minified.json"].splitlines()) == 1
    assert all(c["locator"] == "line:1" for f in regs["minified"].facts for c in f.get("citations", []))
    # the uncitable file: row 1 citable, row 2 rating/outlook not
    unc = rating_cites(CONTEXT_FILES["context-uncitable.json"])
    assert all(v is not None for v in unc[0].values())
    assert unc[1]["rating"] is None and unc[1]["outlook"] is None
    assert unc[1]["agency"] is not None and unc[1]["as_of"] is not None

    positive = expected_case("positive", regs["positive"])
    gap = expected_case("gap", regs["gap"])
    cell = fp05_not_meaningful_cell()
    outlook_unstated = delta_case(positive, regs["outlook_unstated"], retarget(cell, "positive"))
    minified = delta_case(positive, regs["minified"])

    # case table of the brief, as the oracle's own statement of each case
    context_runs = {
        "positive": {"context": "context-positive.json", "ratings_source": "positive"},
        "gap": {"context": "context-gap.json", "ratings_source": "gap"},
        "outlook_unstated": {"context": "context-outlook-unstated.json", "ratings_source": "positive"},
        "minified": {"context": "context-minified.json", "ratings_source": "positive"},
        "view": {"context": "context-positive.json", "ratings_source": "positive"},
    }
    trig = trigger_view(positive)
    view = {
        "context": "context-positive.json",
        "ratings_source": "positive",
        "tree_file": "cp2h-context-view-tree.json",
        "register": {
            "state": "present",
            "source_id": "context",
            "pages": [],
            "agencies": [
                {"row": f"r{n:02d}", **{k: a[k] for k in ("agency", "rating", "outlook", "date", "position")}}
                for n, a in enumerate(positive["parsed_source"]["register"], 1)
            ],
        },
        "triggers": trig,
        "everything_else": "as the frozen cases/cp2h-owner/cp2h-view-tree.json positive tree: upstream, cp2g, cp1_facts, inherited_limitations",
        "derivation": "register: context-positive rows on the fixed scale (BB 12, Ba3 13), pages [] because a context register has no pages (plan Task 3 item 6); triggers: the frozen positive T2R.3 threshold facts (cases/cp2h-owner/expected.json cases.positive), agencies renamed",
    }

    # the refusals ------------------------------------------------------------------------------
    refusals = []
    for rid, ctx, variant, klass, issue, why in SOURCE_REFUSALS:
        refusals.append(
            {
                "id": rid,
                "class": klass,
                "issue_kind": "context" if rid in ("context_mismatch", "uncitable_row") else "source",
                "context": ctx,
                "context_sha256": CTX_SHA[ctx],
                "ratings_source": variant,
                "payload": "submissions.json cases.positive.rating_triggers",
                "composer_only": True,
                "expected_issues": [issue],
                "derivation": why,
            }
        )

    expected = {
        "schema_version": "cp2h-context-owner-expected/1",
        "derivation": (
            "Hand-derived from the Phase 4 plan Task 0 table and the ruling's fixed combined scale; every number, "
            "text and citation outside T2R.2 / T2R.8 is the frozen cases/cp2h-owner/expected.json value with the "
            "agencies renamed (Alder Ratings -> S&P, Brook Credit -> Moody's) and the ratings source hash replaced; "
            "builder/build.py performs exactly that transcription and asserts it."
        ),
        "frozen_inputs": PINS,
        "agency_rename": {o: n for o, n in RENAME},
        "possessive": {"S&P": "S&P's", "Moody's": "Moody's", "rule": "a name already ending in 's is unchanged, else 's is appended"},
        "combined_scale": {
            "rows": [
                {"position": p, "sp": sp, "fitch": fi, "moodys": mo} for p, sp, fi, mo in SCALE_ROWS
            ],
            "by_agency": SCALE,
            "no_position": list(UNRATED),
            "note": "S&P and Fitch share the letter symbols; position 22 is S&P SD and Fitch RD, 23 is D for S&P and Fitch; Moody's has neither",
        },
        "citation_rules": {
            "span": "the context source `context`, locator `line:N` (splitlines of the file's bytes), source_sha256 = sha256 of the file bytes",
            "key_value_quote": "when the field has its own line (the stripped line is the key/value text, one trailing comma allowed) and the text is unique in that line: `\"rating\": \"BB\"` (form layout)",
            "object_anchored_quote": "else the text from the row object's `{` through the cited value when that is one line and unique in it (a minified file: `{\"agency\":\"S&P\",\"scope\":\"issuer\",\"rating\":\"BB\"`, locator line:1)",
            "none": "else no citation: the named issue `Context rating row <n> (<agency>) cannot be cited as one unique span; ratings not used`",
            "fields": "agency -> agency value; instrument `Not stated`, rating, and a `Not stated` outlook or date -> the rating value; outlook -> outlook value; date -> as_of value",
            "derived": "a derived fact (position, notches, lower_rated, outlook_match, first_agency, second_agency) has one citation per (source, locator): the first of its inputs' citations on it, in input order (cases/cp2h-owner/builder/build.py lineage rule, rulings stage2 round 3 item 3); position derives from its rating fact and has no scale citation",
            "terms": "T2R.3 and everything derived from it cite ratings page:3, as before, with the renamed quotes",
        },
        "own_limitations_rule": (
            "frozen list; [0] and [6] replaced by the context lines; then, directly after the eight fixed lines "
            "and before the frozen threshold-not-stated, withdrawn, not-calculable and Gap lines: the fixed-table "
            "line, one `The rating date is not stated for <agency>.` per empty as_of (row order), one "
            "`Rating scope: <scope> (<agency>).` per row (row order). The order is the preparer's reading of plan "
            "Task 3 item 5 ('replaced in place ... Then it appends'); see the report."
        ),
        "evidence_rule": "the analyst views cite the ratings page:3 term lines they rest on and the row's context `rating` value (a `line:N` citation); read_pages reads only page:3 (read_pages returns page:N spans only)",
        "cases": {
            "positive": positive,
            "gap": gap,
            "outlook_unstated": outlook_unstated,
            "minified": minified,
        },
        "view": view,
        "refusals": refusals,
        "refusal_rules": {
            "order": "validate: stale upstream; then `Context refused: ...` alone; then register refusals (empty, duplicate, off-scale, uncitable row) before terms refusals (plan Task 3 item 2); one issue each, returned alone, composer-only",
            "no_terms": "a context with rows and no `ratings` source; the variant `ratings` source without a page:3 terms header reads the same text (not separately exercised)",
            "ordering_checked": "no case here breaches two rules at once, so the order is stated, not discriminated",
        },
    }

    # submissions -----------------------------------------------------------------------------
    def overlay(ctx_name, text):
        loc, quote = issuer_name_cite(text)
        cite = {"source_id": "context", "source_sha256": CTX_SHA[ctx_name], "locator": loc, "quote": quote}
        return {
            "cp0_readiness_source": {
                "source_id": "context",
                "document_family": "User-supplied run context",
                "authority": "unknown",
                "entity": ISSUER[1],
                "period": AS_OF,
                "version_relationship": "User-supplied form download for this run",
                "fidelity": "verified",
                "citations": [cite],
                "limitations": [
                    "User-supplied run context: its names, periods and figures are the user's statements; CP-0 classifies its authority as unknown and does not verify them against issuer sources."
                ],
            },
            "cp1_source_context_source": {
                "source_id": "context",
                "classification": "nonfinancial",
                "document_type": "User-supplied run context",
                "published_on": AS_OF,
                "evidence_class": "internal",
                "evidence_rationale": "User-supplied settings and names; authority unknown (D2)",
                "analytical_use": "Run settings and user-stated names",
                "citations": [deepcopy(cite)],
                "event_scan": "unassessed",
                "event_scan_explanation": "A user-supplied run context is not event evidence",
            },
        }

    cases_sub = {}
    for case_id in ("positive", "gap", "outlook_unstated", "minified"):
        variant = context_runs[case_id]["ratings_source"]
        ctx_name = context_runs[case_id]["context"]
        reg = regs[case_id]
        frozen = F_SUB["cases"][variant]
        over = overlay(ctx_name, CONTEXT_FILES[ctx_name])
        readiness = retarget(frozen["readiness_review"], variant)
        cp1 = retarget(frozen["cp1_source_context"], variant)
        check_pages(readiness, RATINGS[variant]["pages"])
        check_pages(cp1, RATINGS[variant]["pages"])
        readiness["sources"] = [*readiness["sources"], over["cp0_readiness_source"]]
        cp1["sources"] = [*cp1["sources"], over["cp1_source_context_source"]]
        payload = payload_for(variant, reg)
        check_pages(payload, RATINGS[variant]["pages"])
        cases_sub[case_id] = {
            "context": ctx_name,
            "ratings_source": variant,
            "readiness_review": readiness,
            "cp1_source_context": cp1,
            "cp1_readiness": deepcopy(frozen["cp1_readiness"]),
            "rating_triggers": payload,
            "tool_calls": [
                {"tool": "read_inputs", "arguments": None},
                {
                    "tool": "read_pages",
                    "arguments": {"source_id": "ratings", "first_page": 3, "last_page": 3},
                    "expect_spans": [{"source_id": "ratings", "locator": "page:3"}],
                },
            ],
        }
    for case_id, item in cases_sub.items():
        assert not any(n in json.dumps(item["rating_triggers"]) for n in OLD_NAMES), case_id

    submissions = {
        "schema_version": "cp2h-context-owner-submissions/1",
        "note": (
            "Literal analyst submissions for the rating_triggers step of the context runs, re-cut from "
            "cases/cp2h-owner/submissions.json cases.positive/gap: agencies renamed, every ratings citation "
            "re-pointed to the new ratings source hash, the page:1 register-line evidence replaced by a citation of "
            "the row's context `rating` value, and the `context` source assessed once in the CP-0 review and the CP-1 "
            "source context (authority unknown). {{FIG:name|token}} and {{EVID:..}} placeholders and the pack hash are "
            "bound at run time exactly as in the frozen oracle. upstream_step_literals and figures are the frozen ones."
        ),
        "figures": deepcopy(F_SUB["figures"]),
        "upstream_step_literals": deepcopy(F_SUB["upstream_step_literals"]),
        "cases": cases_sub,
        "refusal_payload": "composer-only refusals use cases.positive.rating_triggers",
    }
    assert "ratings" not in json.dumps(submissions["upstream_step_literals"])

    # view tree -------------------------------------------------------------------------------
    tree = {
        "_note": (
            "Shape of the body `owners.cp2h.view(historical, attempt)` serves for `read_inputs` on a context run "
            "(Phase 4 Task 0, preparer): the frozen cases/cp2h-owner/cp2h-view-tree.json positive tree, with "
            "`register.pages` an empty list (a context register has no pages). Values are in expected.json view."
        ),
        "positive": deepcopy(F_TREE["positive"]),
    }
    tree["positive"]["tree"]["register"]["pages"] = []

    # manifest --------------------------------------------------------------------------------
    sources_fin = {s["source_id"]: s["sha256"] for s in json.loads(RAW["cases/financial/manifest.json"])["sources"]}
    run_base = {
        "issuer_id": ISSUER[0],
        "issuer_name": ISSUER[1],
        "as_of": AS_OF,
        "method_version": "deploy-v-r14",
        "case_kind": "synthetic",
        "pathway": "distressed_restructuring",
        "requested_modules": ["CP-2H"],
    }
    cases_man = {}
    for cid, spec in context_runs.items():
        cases_man[cid] = {
            "run": {"run_id": f"cp2h-context-owner-{cid.replace('_', '-')}", **run_base},
            "context": spec["context"],
            "ratings_source": spec["ratings_source"],
            "pack": ["identity", "financial", "ratings", "context"],
            "execution": "closed run: CP-0, CP-1, CP-2A, CP-2G as cases/cp2h-owner cases.positive/gap (same chain, same figures), CP-2H",
            "submission": "submissions.json cases." + (cid if cid != "view" else "positive"),
            "expected": "expected.json " + (f"cases.{cid}" if cid != "view" else "view"),
        }
    for rid, ctx, variant, klass, issue, why in SOURCE_REFUSALS:
        cases_man[rid] = {
            "run": {"run_id": f"cp2h-context-owner-{rid.replace('_', '-')}", **run_base},
            "context": ctx,
            "ratings_source": variant,
            "pack": ["identity", "financial"] + (["ratings"] if variant else []) + ["context"],
            "execution": "composer only (validate / register build on the pack); no run",
            "expected": f"expected.json refusals[{rid}]",
        }
    manifest = {
        "schema_version": "cp2h-context-owner-cases/1",
        "scope": "Phase 4: CP-2H builds its rating register from the context file's `ratings` rows (S&P, Moody's, Fitch) on a fixed combined scale; trigger terms from an attached `ratings` source",
        "status": "DRAFT 1 prepared by the cp2h-context-owner Task 0 preparer, 2026-11-01; review pending; not frozen, not pinned",
        "roles": {"preparer": "Task 0 preparer (this builder)", "reviewer": None, "builder": None},
        "raw_rule": "ratings pages: literal UTF-8 LF, no terminal LF per page; U+000C joins ordered pages for the source SHA256 (as cases/cp2h-owner). context files: the bytes the form writes (JSON.stringify(o, null, 2) + LF; context-minified.json: JSON.stringify(o) + LF), sha256 of the file bytes, spans line:N via splitlines",
        "inputs_pinned": PINS,
        "financial_baseline": {
            "path": "cases/financial/manifest.json",
            "sources": [
                {"source_id": s, "sha256": sources_fin[s], "reuse": "Every page text and locator stays byte-identical; read by reference, never edited"}
                for s in ("identity", "financial")
            ],
        },
        "upstream": "CP-0, CP-1, CP-2A, CP-2G closed chain as cases/cp2h-owner/manifest.json cases.positive (and gap for the gap case): every CP-2G metric and CP-1 ratio is the already frozen value",
        "ratings_sources": {
            "source_id": "ratings",
            "name": SS["name"],
            "status": SS["status"],
            "media_type": SS["media_type"],
            "extractor": SS["extractor"],
            "extraction_status": SS["extraction_status"],
            "pack_limitation_positive": SS["pack_limitation_positive"],
            "pack_limitation_gap": SS["pack_limitation_gap"],
            "note": "pages 1-2 are the frozen cp2h-owner pages (fictional agencies, fictional scale, scale positions 11/12) and are present and ignored by the context path; page 3 is the frozen page 3 with Alder Ratings -> S&P and Brook Credit -> Moody's (fitch_terms: S&P rows plus one Fitch row)",
            **{k: v for k, v in RATINGS.items()},
        },
        "context_files": {
            name: {"sha256": CTX_SHA[name], "lines": len(text.splitlines()), "bytes": len(text.encode("utf-8"))}
            for name, text in CONTEXT_FILES.items()
        },
        "context_source": {
            "source_id": "context",
            "status": "ready",
            "media_type": "text/plain",
            "spans": "line:N per splitlines of the file",
            "base": "cases/context/research-minimal.json with run.pathway distressed_restructuring, case_kind synthetic, as_of 2026-01-10, identity Northbridge Synthetic Group / northbridge-synthetic and the case's ratings rows",
            "run_type": "research (a primary run requires a deal_terms row)",
        },
        "combined_scale": expected["combined_scale"],
        "cases": cases_man,
        "run_time_bindings": "as cases/cp2h-owner/manifest.json run_time_bindings: pack hash, {{FIG:..}}, {{EVID:..}}, {{INPUTS_SHA256}} and ticket ids are bound at run time",
        "outputs": {},
    }

    # write -----------------------------------------------------------------------------------
    (OUT / "builder").mkdir(parents=True, exist_ok=True)
    for name, raw in files.items():
        (OUT / name).write_bytes(raw)
    out_text = {
        "expected.json": dumps(expected),
        "submissions.json": dumps(submissions),
        "cp2h-context-view-tree.json": dumps(tree),
    }
    for name, text in out_text.items():
        (OUT / name).write_bytes(text.encode("utf-8"))
    manifest["outputs"] = {
        name: sha(text.encode("utf-8")) for name, text in out_text.items()
    }
    (OUT / "manifest.json").write_bytes(dumps(manifest).encode("utf-8"))
    print(f"wrote {len(files) + len(out_text) + 1} files to {OUT}")


if __name__ == "__main__":
    main()
