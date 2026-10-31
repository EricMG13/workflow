"""Checker for public-issuer goldens: module-golden/1 and context/1 (stdlib only).

    python3 -I cases/goldens/check.py [--corpus DIR] CASE_DIR...

Each CASE_DIR holds module_golden.json and context.json (and derive.py when anything is derived).
Exit 0 when every case passes, 1 otherwise. Every problem prints as
``<case>/<file>: <json path>: <message>``. PDF sources are not parsed: each prints one
``not checked: pdf`` note (same line shape) that does not fail the run.

module_golden.json: required keys and types, unknown keys refused, unique fact_id, status and
value_type enums, status rules (known / missing / conflicting / not_applicable), decimal and
date values, source files and sha256 under the corpus, evidence source ids, quotes found in the
source's visible text, ``printed`` inside ``quote``, derivations recomputed with Decimal
(sum, difference, negate, product, ratio), the financial_gold path and sha256.

Visible text (CONTEXT.md): html.parser; drop script, style, head, ix:header and any element whose
style has display:none; unescape entities; every whitespace run (NBSP and other Unicode spaces
included) becomes one space; strip. The zero-width characters U+200B, U+200C, U+200D, U+2060 and
U+FEFF are deleted (not turned into spaces), in the text and in the quote searched for it. CONTEXT.md does not say where cells are separated, so a
space is inserted at the start and end of block-level tags (td, th, tr, p, div, br, li, ...);
inline tags add nothing, so ``<span>(</span>1,234<span>)</span>`` reads ``(1,234)``.

context.json: the context/1 shape of docs/CONTEXT-FILE-PROPOSAL.md at 5325c209 with the enums and
formats of build() in docs/templates/context-form.html: exact keys at every level, schema,
run_type, pathway, case_kind (the form allows public, private and synthetic), ISO dates,
period ids, currency, slug, enums, and NUM/SNUM for every non-empty number field. Duplicate JSON
keys are refused.

Out of scope: cross-field rules (period required for earnings, prior before current, low <= high,
min/max bounds, dates after as_of, rules tied to run_type or basis), and whether context values
agree with module_golden.json.
"""

import argparse
import datetime
import decimal
import hashlib
import html.parser
import json
import pathlib
import re
import sys

DEFAULT_CORPUS = pathlib.Path(
    "/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1"
)
PATHWAYS = (
    "credit_snapshot",
    "earnings_update",
    "relative_value",
    "covenant_refinancing",
    "distressed_restructuring",
    "portfolio_decision",
)
RUN_TYPES = ("primary", "secondary", "research", "earnings")
CASE_KINDS = ("public", "private", "synthetic")
STATUSES = ("known", "missing", "conflicting", "not_applicable")
VALUE_TYPES = ("decimal", "text", "date", "percent", "bps")
NUMERIC_TYPES = ("decimal", "percent", "bps")
SCALE_EXP = {None: 0, "units": 0, "thousands": 3, "millions": 6, "billions": 9}
OPS = ("sum", "difference", "negate", "product", "ratio")

NUM = re.compile(r"\d+(\.\d+)?", re.ASCII)
SNUM = re.compile(r"-?\d+(\.\d+)?", re.ASCII)
PERIOD = re.compile(r"(q[1-4]|h[12]|fy)-(\d{4})", re.ASCII)
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
CURRENCY = re.compile(r"[A-Z]{3}", re.ASCII)
SLUG = re.compile(r"[a-z0-9-]+", re.ASCII)

# ---------------------------------------------------------------- visible text

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}
SKIP = {"script", "style", "head", "ix:header"}
BLOCK = {
    "address",
    "blockquote",
    "body",
    "br",
    "caption",
    "center",
    "dd",
    "div",
    "dl",
    "dt",
    "fieldset",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}
HIDDEN = re.compile(r"display\s*:\s*none", re.IGNORECASE)


class _Visible(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []  # (tag, skipped)
        self.skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.handle_endtag("head")  # an unclosed head ends at body
        if tag in BLOCK:
            self.parts.append(" ")
        if tag in VOID:
            return
        hidden = tag in SKIP or any(k == "style" and HIDDEN.search(v or "") for k, v in attrs)
        self.stack.append((tag, hidden))
        self.skipping += hidden

    def handle_startendtag(self, tag, attrs):
        if tag in BLOCK:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in BLOCK:
            self.parts.append(" ")
        if tag in VOID:
            return
        names = [t for t, _ in self.stack]
        if tag not in names:
            return
        keep = len(names) - 1 - names[::-1].index(tag)
        while len(self.stack) > keep:
            _, hidden = self.stack.pop()
            self.skipping -= hidden

    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(data)


ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"))


def visible_text(raw):
    parser = _Visible()
    parser.feed(raw)
    parser.close()
    return normalise("".join(parser.parts))


def normalise(text):
    """Delete zero-width characters, collapse every whitespace run to one space, strip."""
    return re.sub(r"\s+", " ", text.translate(ZERO_WIDTH)).strip()


# ---------------------------------------------------------------- helpers


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_iso_date(v):
    if not isinstance(v, str) or not ISO_DATE.fullmatch(v):
        return False
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        return False
    return True


def _no_dups(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def load_json(path):
    """Return (data, message); message is None when the file parsed."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"cannot read file: {e.strerror or e}"
    except UnicodeDecodeError as e:
        return None, f"not UTF-8: {e}"
    try:
        return json.loads(text, object_pairs_hook=_no_dups), None
    except ValueError as e:
        return None, f"invalid JSON: {e}"


class Out:
    """Collects problems and notes for one case."""

    def __init__(self, case):
        self.case = case
        self.problems = []
        self.notes = []

    def bad(self, file, path, msg):
        self.problems.append(f"{self.case}/{file}: {path}: {msg}")

    def note(self, file, path, msg):
        self.notes.append(f"{self.case}/{file}: {path}: {msg}")


def check_shape(out, file, value, spec, path):
    """Validate value against spec. spec: dict = object with exactly those keys; [dict] = list of
    such objects; tuple = enum; ("null", spec) = null or spec; str = scalar kind."""
    if spec == "any":
        return
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            out.bad(file, path, "expected an object")
            return
        for k in value:
            if k not in spec:
                out.bad(file, f"{path}.{k}", "unknown key")
        for k, sub in spec.items():
            if k not in value:
                out.bad(file, f"{path}.{k}", "missing key")
            else:
                check_shape(out, file, value[k], sub, f"{path}.{k}")
    elif isinstance(spec, list):
        if not isinstance(value, list):
            out.bad(file, path, "expected a list")
            return
        for i, item in enumerate(value):
            check_shape(out, file, item, spec[0], f"{path}[{i}]")
    elif isinstance(spec, tuple) and spec[0] == "null":
        if value is not None:
            check_shape(out, file, value, spec[1], path)
    elif isinstance(spec, tuple):
        if value not in spec or isinstance(value, (bool, list, dict)):
            out.bad(file, path, f"must be one of {', '.join(spec)}")
    else:
        check_scalar(out, file, value, spec, path)


SCALAR_RULES = {
    "num": (NUM, "enter a plain number such as 1250 or 99.5"),
    "snum": (SNUM, "enter a plain number such as -1250 or 99.5"),
    "period": (PERIOD, "use q1-2026, h2-2026 or fy-2025 (lowercase)"),
    "date": (ISO_DATE, "use a date as YYYY-MM-DD"),
    "cur": (CURRENCY, "use three uppercase letters, such as USD"),
    "slug": (SLUG, "use lowercase letters, digits and hyphens only"),
}


def check_scalar(out, file, value, kind, path):
    if kind == "bool":
        if not isinstance(value, bool):
            out.bad(file, path, "expected true or false")
    elif kind == "strlist":
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            out.bad(file, path, "expected a list of strings")
    elif kind == "numlist":
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            out.bad(file, path, "expected a list of number strings")
        else:
            for i, x in enumerate(value):
                if not NUM.fullmatch(x):
                    out.bad(file, f"{path}[{i}]", SCALAR_RULES["num"][1])
    elif not isinstance(value, str):
        out.bad(file, path, "expected a string")
    elif kind == "str":
        pass
    elif kind == "str!":
        if not value.strip():
            out.bad(file, path, "required")
    else:
        required = kind.endswith("!")  # without "!" an empty string means not supplied
        base = kind.rstrip("!")
        if value == "":
            if required:
                out.bad(file, path, "required")
        elif not SCALAR_RULES[base][0].fullmatch(value):
            out.bad(file, path, SCALAR_RULES[base][1])
        elif base == "date" and not is_iso_date(value):
            out.bad(file, path, "not a real calendar date")


# ---------------------------------------------------------------- context/1

_ROW_DEAL = {
    "facility_id": "str",
    "instrument": "str",
    "currency": "cur",
    "size_m": "num",
    "tenor_years": "num",
    "talk_spread_bps_low": "num",
    "talk_spread_bps_high": "num",
    "talk_oid_low": "num",
    "talk_oid_high": "num",
    "floor_pct": "num",
    "call_protection": "str",
    "use_of_proceeds": "str",
    "as_of": "date",
    "provider": "str",
}
_RATIONALE = {"rationale": "str"}
CONTEXT_SPEC = {
    "schema": ("context/1",),
    "run": {
        "run_type": RUN_TYPES,
        "pathway": PATHWAYS,
        "case_kind": CASE_KINDS,
        "as_of": "date!",
        "current_period": "period",
        "prior_period": "period",
        "reporting_currency": "cur!",
    },
    "identity": {
        "issuer_name": "str!",
        "issuer_id": "slug!",
        "borrower_name": "str",
        "parent_name": "str",
        "guarantors": "strlist",
        "aliases": "strlist",
        "listed_equity": "bool",
        "ticker": "str",
        "sector": "str",
        "country": "str",
        "sponsor": "str",
    },
    "deal_terms": [_ROW_DEAL],
    "quotes": [
        {
            "facility_id": "str",
            "kind": ("observed", "indicative_talk"),
            "bid": "num",
            "ask": "num",
            "price": "num",
            "yield_pct": "num",
            "spread_bps": "num",
            "as_of": "date!",
            "provider": "str!",
        }
    ],
    "ratings": [
        {
            "agency": "str!",
            "scope": ("issuer", "facility"),
            "rating": "str!",
            "outlook": "str",
            "as_of": "date",
        }
    ],
    "valuation": {
        "peer_source": ("cp_dr_public", "user_list", "user_comps", "none"),
        "basis": (
            "auto",
            "public_comps",
            "precedents",
            "blend",
            "issuer_trading",
            "user_multiple",
        ),
        "issuer_market": {
            "market_cap_m": "num",
            "net_debt_m": "snum",
            "ev_m": "num",
            "ebitda_basis": ("LTM", "NTM"),
            "as_of": "date",
            "source": "str",
        },
        "peers": [
            {
                "name": "str",
                "ticker": "str",
                "ev_m": "num",
                "ebitda_m": "num",
                "as_of": "date",
                "source": "str",
            }
        ],
        "precedents": [
            {
                "target": "str",
                "acquirer": "str",
                "date": "date",
                "ev_m": "num",
                "ebitda_m": "num",
                "source": "str",
            }
        ],
        "user_multiple": {"value": "num", "basis": ("LTM", "NTM"), "rationale": "str"},
    },
    "assumptions": {
        "cp2a": (
            "null",
            {
                "scenarios": [{"ebitda_decline_pct": "num", "interest_increase_pct": "num"}],
                **_RATIONALE,
            },
        ),
        "cp2d": ("null", {"horizon_months": "num", "minimum_cash_m": "num", **_RATIONALE}),
        "cp2e": (
            "null",
            {
                "rate_shocks_bps": "numlist",
                "fx_shocks_pct": "numlist",
                "hedge_ratio_pct": "num",
                **_RATIONALE,
            },
        ),
        "cp3c": ("null", {"repricing_bps": "num", **_RATIONALE}),
        "cp3d": ("null", {"recovery_pct": "num", **_RATIONALE}),
        "cp4c": ("null", {"ev_multiple": "num", **_RATIONALE}),
    },
    "attachments": {
        "portfolio_workbook": "bool",
        "prior_case": "bool",
        "management_bridge": "bool",
        "legal_documents": ("executed", "draft", "none"),
    },
    "research_questions": [{"text": "str!", "focus_module": "str"}],
}


def check_context(out, case_dir):
    file = "context.json"
    data, msg = load_json(case_dir / file)
    if msg:
        out.bad(file, "$", msg)
        return
    check_shape(out, file, data, CONTEXT_SPEC, "$")


# ---------------------------------------------------------------- module-golden/1

SOURCE_KEYS = {
    "source_id": "str!",
    "file": "str!",
    "sha256": "str!",
    "url": "str",
    "form": "str",
    "period_end": "date",
    "filed": "date!",
}
EVIDENCE = {"source_id": "str!", "locator": "str!", "quote": "str!", "printed": "str!"}
DERIVATION = {"op": OPS, "operands": "strlist", "script": "str!"}
FACT_SPEC = {
    "fact_id": "str!",
    "module": "str!",
    "topic": "str!",
    "subject": "str!",
    "field": "str!",
    "period_end": ("null", "date!"),
    "status": STATUSES,
    "value": "any",
    "value_type": VALUE_TYPES,
    "unit": ("null", ("USD", "percent", "bps")),
    "scale": ("null", ("millions", "thousands", "billions", "units")),
    "evidence": [EVIDENCE],
    "derivation": ("null", DERIVATION),
    "gap_reason": ("null", "str!"),
}
GOLDEN_SPEC = {
    "schema_version": ("module-golden/1",),
    "case_id": "str!",
    "issuer_id": "str!",
    "pathway": PATHWAYS,
    "cutoff": "date!",
    "context_file": "str!",
    "financial_gold": {"path": "str!", "sha256": "str!"},
    "sources": [SOURCE_KEYS],
    "facts": [FACT_SPEC],
    "not_golden": [{"module": "str!", "why": "str!"}],
    "needs_user_input": [{"context_path": "str!", "modules": "strlist", "why": "str!"}],
    "limitations": "strlist",
    "preparer": "str!",
}


def check_value(out, file, fact, path):
    """Status and value rules for one fact (shape already checked)."""
    status, value, vtype = fact["status"], fact["value"], fact["value_type"]
    ev = fact["evidence"]
    gap = fact["gap_reason"]
    if status == "known":
        if value is None:
            out.bad(file, f"{path}.value", "known fact needs a non-null value")
        if gap is not None:
            out.bad(file, f"{path}.gap_reason", "known fact needs gap_reason null")
    else:
        if value is not None:
            out.bad(file, f"{path}.value", f"{status} fact needs a null value")
    if status == "missing" and not (isinstance(gap, str) and gap.strip()):
        out.bad(file, f"{path}.gap_reason", "missing fact needs a non-empty gap_reason")
    if status == "conflicting" and len(ev) < 2:
        out.bad(file, f"{path}.evidence", "conflicting fact needs at least 2 evidence entries")
    if status == "known" and value is not None:
        if vtype in NUMERIC_TYPES:
            if not (isinstance(value, str) and SNUM.fullmatch(value)):
                out.bad(
                    file,
                    f"{path}.value",
                    "decimal value must be a string matching ^-?\\d+(\\.\\d+)?$",
                )
        elif vtype == "date":
            if not is_iso_date(value):
                out.bad(file, f"{path}.value", "date value must be a real ISO date")
        elif not (isinstance(value, str) and value.strip()):
            out.bad(file, f"{path}.value", "text value must be a non-empty string")
    if status == "known" and fact["derivation"] is None and not ev:
        out.bad(
            file, f"{path}.evidence", "known non-derived fact needs at least one evidence entry"
        )


def recompute(op, vals):
    """Exact Decimal result of op over vals; raises ValueError on a bad operand count or divisor."""
    ctx = decimal.Context(
        prec=200, traps=[decimal.InvalidOperation, decimal.Inexact, decimal.DivisionByZero]
    )
    if op == "negate":
        if len(vals) != 1:
            raise ValueError("negate needs exactly 1 operand")
        return ctx.minus(vals[0])
    if len(vals) < 2:
        raise ValueError(f"{op} needs at least 2 operands")
    if op == "sum":
        total = vals[0]
        for v in vals[1:]:
            total = ctx.add(total, v)
        return total
    if op == "difference":
        total = vals[1]
        for v in vals[2:]:
            total = ctx.add(total, v)
        return ctx.subtract(vals[0], total)
    if op == "product":
        total = vals[0]
        for v in vals[1:]:
            total = ctx.multiply(total, v)
        return total
    if len(vals) != 2:
        raise ValueError("ratio needs exactly 2 operands")
    if vals[1] == 0:
        raise ValueError("ratio divisor is zero")
    # The quotient is rarely finite: compute at 200 digits (rounding allowed here only).
    return decimal.Context(prec=200).divide(vals[0], vals[1])


_CTX = decimal.Context(prec=200)


def check_derivation(out, file, fact, path, by_id, case_dir):
    der = fact["derivation"]
    dpath = f"{path}.derivation"
    if not (case_dir / der["script"]).is_file():
        out.bad(
            file, f"{dpath}.script", f"script {der['script']!r} not found in the case directory"
        )
    if fact["status"] != "known" or fact["value_type"] not in NUMERIC_TYPES:
        out.bad(file, dpath, "a derived fact must be known with a decimal, percent or bps value")
        return
    vals = []
    for i, oid in enumerate(der["operands"]):
        op = by_id.get(oid)
        if op is None:
            out.bad(file, f"{dpath}.operands[{i}]", f"operand {oid!r} is not a fact in this file")
        elif not (
            op["status"] == "known"
            and op["value_type"] in NUMERIC_TYPES
            and isinstance(op["value"], str)
            and SNUM.fullmatch(op["value"])
        ):
            out.bad(file, f"{dpath}.operands[{i}]", f"operand {oid!r} is not a known decimal fact")
        else:
            vals.append(decimal.Decimal(op["value"]).scaleb(SCALE_EXP[op["scale"]], _CTX))
    if len(vals) != len(der["operands"]) or not isinstance(fact["value"], str):
        return
    if not SNUM.fullmatch(fact["value"]):
        return  # already reported by check_value
    stored = decimal.Decimal(fact["value"])
    try:
        result = recompute(der["op"], vals)
    except (ValueError, decimal.DecimalException) as e:
        out.bad(file, dpath, f"cannot recompute: {e}")
        return
    if der["op"] == "ratio":
        if fact["value_type"] == "percent":
            result = result.scaleb(2, _CTX)
    else:
        result = result.scaleb(-SCALE_EXP[fact["scale"]], _CTX)
    places = max(0, -stored.as_tuple().exponent)
    result = result.quantize(
        decimal.Decimal(1).scaleb(-places), rounding=decimal.ROUND_HALF_UP, context=_CTX
    )
    if result != stored:
        out.bad(
            file, f"{path}.value", f"stored {fact['value']} but {der['op']} recomputes to {result}"
        )


def resolve_source(corpus, rel):
    """Path under corpus, or None when rel is absolute or escapes it."""
    root = corpus.resolve()
    p = (root / rel).resolve()
    if pathlib.PurePath(rel).is_absolute() or not p.is_relative_to(root):
        return None
    return p


def check_sources(out, file, data, corpus):
    """Returns {source_id: visible text or None (not checkable)} and the source dicts by id."""
    texts = {}
    by_id = {}
    for i, src in enumerate(data["sources"]):
        path = f"$.sources[{i}]"
        sid = src["source_id"]
        if sid in by_id:
            out.bad(file, f"{path}.source_id", f"duplicate source_id {sid!r}")
        by_id[sid] = src
        texts[sid] = None
        if (
            is_iso_date(src["filed"])
            and is_iso_date(data["cutoff"])
            and src["filed"] > data["cutoff"]
        ):
            out.bad(
                file, f"{path}.filed", f"filed {src['filed']} is after the cutoff {data['cutoff']}"
            )
        p = resolve_source(corpus, src["file"])
        if p is None:
            out.bad(file, f"{path}.file", "must be a relative path inside the corpus")
        elif not p.is_file():
            out.bad(file, f"{path}.file", f"not found under the corpus: {src['file']}")
        elif sha256_of(p) != src["sha256"]:
            out.bad(file, f"{path}.sha256", f"does not match the file (actual {sha256_of(p)})")
        elif p.suffix.lower() == ".pdf":
            out.note(file, f"{path}.file", "not checked: pdf")
            texts[sid] = "pdf"
        else:
            texts[sid] = visible_text(p.read_text(encoding="utf-8", errors="replace"))
    return texts, by_id


def check_evidence(out, file, fact, path, texts, sources):
    for j, ev in enumerate(fact["evidence"]):
        epath = f"{path}.evidence[{j}]"
        sid = ev["source_id"]
        if sid not in sources:
            out.bad(file, f"{epath}.source_id", f"{sid!r} is not a listed source")
            continue
        if len(ev["quote"]) > 300:
            out.bad(file, f"{epath}.quote", "longer than 300 characters")
        quote = normalise(ev["quote"])
        if normalise(ev["printed"]) not in quote:
            out.bad(file, f"{epath}.printed", "printed value is not a substring of quote")
        text = texts[sid]
        if text is None or text == "pdf":
            continue  # source problem or pdf note already reported
        if quote not in text:
            out.bad(file, f"{epath}.quote", "quote not found in the source's visible text")


def check_golden(out, case_dir, corpus):
    file = "module_golden.json"
    data, msg = load_json(case_dir / file)
    if msg:
        out.bad(file, "$", msg)
        return
    before = len(out.problems)
    check_shape(out, file, data, GOLDEN_SPEC, "$")
    if len(out.problems) > before:
        return  # later checks assume the shape
    if not (case_dir / data["context_file"]).is_file():
        out.bad(file, "$.context_file", f"{data['context_file']} not found in the case directory")
    fg = pathlib.Path(data["financial_gold"]["path"])
    if not fg.is_file():
        out.bad(file, "$.financial_gold.path", "file not found")
    elif sha256_of(fg) != data["financial_gold"]["sha256"]:
        out.bad(
            file, "$.financial_gold.sha256", f"does not match the file (actual {sha256_of(fg)})"
        )
    texts, sources = check_sources(out, file, data, corpus)
    by_id = {}
    for i, fact in enumerate(data["facts"]):
        path = f"$.facts[{i}]"
        if fact["fact_id"] in by_id:
            out.bad(file, f"{path}.fact_id", f"duplicate fact_id {fact['fact_id']!r}")
        by_id[fact["fact_id"]] = fact
        if not fact["fact_id"].startswith(fact["module"] + "."):
            out.bad(
                file,
                f"{path}.fact_id",
                f"must start with the module id {fact['module']!r} and a dot",
            )
    for i, fact in enumerate(data["facts"]):
        path = f"$.facts[{i}]"
        check_value(out, file, fact, path)
        check_evidence(out, file, fact, path, texts, sources)
        if fact["derivation"] is not None:
            check_derivation(out, file, fact, path, by_id, case_dir)


def check_case(case_dir, corpus):
    out = Out(str(case_dir))
    check_golden(out, case_dir, corpus)
    check_context(out, case_dir)
    return out


def main(argv):
    ap = argparse.ArgumentParser(description="Check public-issuer golden cases.")
    ap.add_argument("--corpus", type=pathlib.Path, default=DEFAULT_CORPUS)
    ap.add_argument("cases", nargs="+", type=pathlib.Path, metavar="CASE_DIR")
    args = ap.parse_args(argv)
    failed = False
    for case_dir in args.cases:
        out = check_case(case_dir, args.corpus)
        for line in out.notes + out.problems:
            print(line)
        failed = failed or bool(out.problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
