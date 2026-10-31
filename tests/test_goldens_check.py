"""Tests for cases/goldens/check.py using tiny fixtures written to tmp_path."""

import copy
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "cases" / "goldens" / "check.py"
_spec = importlib.util.spec_from_file_location("goldens_check", SCRIPT)
chk = importlib.util.module_from_spec(_spec)
sys.modules["goldens_check"] = chk
_spec.loader.exec_module(chk)

HTML = (
    "<html><head><title>Hidden title</title><style>.x{}</style></head><body>"
    '<div style="display:none">Secret</div><ix:header>Header text</ix:header>'
    "<script>var a=1;</script>"
    "<table><tr><td>Term loan</td><td>$</td><td>1,000</td><td>$</td><td>900</td></tr>"
    "<tr><td>Net</td><td><span>(</span>1,234<span>)</span></td></tr></table>"
    "<p>Rate&nbsp;of  4.75%\n  fixed&amp;firm</p></body></html>"
)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def ev(quote="Term loan $ 1,000 $ 900", printed="1,000"):
    return {"source_id": "s1", "locator": "table", "quote": quote, "printed": printed}


def fact(fid, value, **kw):
    f = {
        "fact_id": fid,
        "module": "CP-2",
        "topic": "t",
        "subject": "s",
        "field": "f",
        "period_end": "2025-12-31",
        "status": "known",
        "value": value,
        "value_type": "decimal",
        "unit": "USD",
        "scale": "millions",
        "evidence": [ev()],
        "derivation": None,
        "gap_reason": None,
    }
    f.update(kw)
    return f


def derived(fid, value, op, operands):
    return fact(
        fid,
        value,
        evidence=[],
        derivation={"op": op, "operands": operands, "script": "derive.py"},
    )


def valid_context():
    return {
        "schema": "context/1",
        "run": {
            "run_type": "research",
            "pathway": "credit_snapshot",
            "case_kind": "public",
            "as_of": "2026-10-31",
            "current_period": "q3-2026",
            "prior_period": "q2-2026",
            "reporting_currency": "USD",
        },
        "identity": {
            "issuer_name": "Acme",
            "issuer_id": "acme",
            "borrower_name": "",
            "parent_name": "",
            "guarantors": [],
            "aliases": [],
            "listed_equity": True,
            "ticker": "ACME",
            "sector": "",
            "country": "",
            "sponsor": "",
        },
        "deal_terms": [],
        "quotes": [
            {
                "facility_id": "",
                "kind": "observed",
                "bid": "99.5",
                "ask": "",
                "price": "",
                "yield_pct": "",
                "spread_bps": "",
                "as_of": "2026-10-30",
                "provider": "x",
            }
        ],
        "ratings": [],
        "valuation": {
            "peer_source": "none",
            "basis": "auto",
            "issuer_market": {
                "market_cap_m": "",
                "net_debt_m": "-5.5",
                "ev_m": "",
                "ebitda_basis": "LTM",
                "as_of": "",
                "source": "",
            },
            "peers": [],
            "precedents": [],
            "user_multiple": {"value": "", "basis": "LTM", "rationale": ""},
        },
        "assumptions": {
            "cp2a": None,
            "cp2d": None,
            "cp2e": {
                "rate_shocks_bps": ["100", "200"],
                "fx_shocks_pct": ["5"],
                "hedge_ratio_pct": "",
                "rationale": "r",
            },
            "cp3c": None,
            "cp3d": None,
            "cp4c": None,
        },
        "attachments": {
            "portfolio_workbook": False,
            "prior_case": False,
            "management_bridge": False,
            "legal_documents": "executed",
        },
        "research_questions": [],
    }


@pytest.fixture
def env(tmp_path):
    corpus = tmp_path / "corpus"
    (corpus / "ACME").mkdir(parents=True)
    html = corpus / "ACME" / "a.htm"
    html.write_bytes(HTML.encode())
    pdf = corpus / "ACME" / "b.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    gold = tmp_path / "financial_gold.json"
    gold.write_bytes(b"{}")
    case = tmp_path / "case"
    case.mkdir()
    (case / "derive.py").write_text("print('ok')\n")
    golden = {
        "schema_version": "module-golden/1",
        "case_id": "acme",
        "issuer_id": "acme",
        "pathway": "credit_snapshot",
        "cutoff": "2026-10-31",
        "context_file": "context.json",
        "financial_gold": {"path": str(gold), "sha256": sha(b"{}")},
        "sources": [
            {
                "source_id": "s1",
                "file": "ACME/a.htm",
                "sha256": sha(html.read_bytes()),
                "url": "",
                "form": "10-K",
                "period_end": "2025-12-31",
                "filed": "2026-02-01",
            }
        ],
        "facts": [
            fact("CP-2.t.a", "1000"),
            fact("CP-2.t.b", "900", evidence=[ev(printed="900")]),
            derived("CP-2.t.sum", "1900", "sum", ["CP-2.t.a", "CP-2.t.b"]),
        ],
        "not_golden": [{"module": "CP-5", "why": "judgment"}],
        "needs_user_input": [{"context_path": "$.ratings", "modules": ["CP-2H"], "why": "w"}],
        "limitations": [],
        "preparer": "t",
    }
    return {
        "case": case,
        "corpus": corpus,
        "golden": golden,
        "html": html,
        "gold": gold,
        "pdf": pdf,
    }


def write(env, golden=None, context=None):
    env["case"].joinpath("module_golden.json").write_text(json.dumps(golden or env["golden"]))
    env["case"].joinpath("context.json").write_text(json.dumps(context or valid_context()))


def run(env, golden=None, context=None):
    write(env, golden, context)
    return chk.check_case(env["case"], env["corpus"])


def mutated(env, fn):
    g = copy.deepcopy(env["golden"])
    fn(g)
    return g


def problems(out):
    return "\n".join(out.problems)


# ---- visible text


def test_visible_text_normalisation():
    t = chk.visible_text(HTML)
    assert "Term loan $ 1,000 $ 900" in t
    assert "Net (1,234)" in t
    assert "Rate of 4.75% fixed&firm" in t
    for hidden in ("Secret", "Header text", "var a", "Hidden title"):
        assert hidden not in t


def test_visible_text_unclosed_head_ends_at_body():
    assert chk.visible_text("<head><title>T</title><body><p>Shown</p>") == "Shown"


# ---- module_golden.json: shape and status rules


def test_valid_case_passes(env):
    out = run(env)
    assert out.problems == []


def test_missing_key_and_unknown_keys_refused(env):
    g = mutated(
        env, lambda g: (g.pop("preparer"), g.update(extra=1), g["facts"][0].update(bogus=1))
    )
    text = problems(run(env, g))
    assert "$.preparer: missing key" in text
    assert "$.extra: unknown key" in text
    assert "$.facts[0].bogus: unknown key" in text


def test_wrong_type_refused(env):
    g = mutated(env, lambda g: g.update(limitations="nope"))
    assert "$.limitations: expected a list of strings" in problems(run(env, g))


def test_duplicate_fact_id(env):
    g = mutated(env, lambda g: g["facts"].append(copy.deepcopy(g["facts"][0])))
    assert "duplicate fact_id" in problems(run(env, g))


def test_bad_status_and_value_type(env):
    def f(g):
        g["facts"][0]["status"] = "maybe"
        g["facts"][1]["value_type"] = "float"

    text = problems(run(env, mutated(env, f)))
    assert "$.facts[0].status: must be one of" in text
    assert "$.facts[1].value_type: must be one of" in text


def test_scale_thousands_accepted(env):
    g = mutated(env, lambda g: g["facts"][0].update(scale="thousands"))
    g["facts"] = g["facts"][:1]
    assert run(env, g).problems == []


def test_scale_billions_accepted(env):
    g = mutated(env, lambda g: g["facts"][0].update(scale="billions"))
    g["facts"] = g["facts"][:1]
    assert run(env, g).problems == []


def test_scale_trillions_refused(env):
    g = mutated(env, lambda g: g["facts"][0].update(scale="trillions"))
    assert "$.facts[0].scale: must be one of" in problems(run(env, g))


def test_known_needs_value_and_no_gap(env):
    def f(g):
        g["facts"][0]["value"] = None
        g["facts"][1]["gap_reason"] = "why"

    text = problems(run(env, mutated(env, f)))
    assert "$.facts[0].value: known fact needs a non-null value" in text
    assert "$.facts[1].gap_reason: known fact needs gap_reason null" in text


def test_missing_rules(env):
    env["golden"]["facts"].pop()  # the derived sum reads fact 0
    ok = mutated(
        env,
        lambda g: g["facts"][0].update(
            status="missing", value=None, evidence=[], gap_reason="absent"
        ),
    )
    assert run(env, ok).problems == []

    def bad(g):
        g["facts"][0].update(status="missing", value="1", gap_reason=None)

    assert "missing fact needs a non-empty gap_reason" in problems(run(env, mutated(env, bad)))
    assert "missing fact needs a null value" in problems(run(env, mutated(env, bad)))


def test_conflicting_rules(env):
    env["golden"]["facts"].pop()  # the derived sum reads fact 0

    def ok(g):
        g["facts"][0].update(status="conflicting", value=None, evidence=[ev(), ev()])

    assert run(env, mutated(env, ok)).problems == []

    def bad(g):
        g["facts"][0].update(status="conflicting", value=None, evidence=[ev()])

    assert "needs at least 2 evidence" in problems(run(env, mutated(env, bad)))


def test_decimal_value_format(env):
    for v in ("1,000", "1e3", "+5", "", 1000):
        g = mutated(env, lambda g, v=v: g["facts"][0].update(value=v))
        assert "decimal value must be a string" in problems(run(env, g)), v
    g = mutated(env, lambda g: g["facts"][0].update(value="-1000.50"))
    assert "decimal value" not in problems(run(env, g))


def test_date_value(env):
    def f(g, v):
        g["facts"][0].update(value=v, value_type="date")

    assert "date value must be a real ISO date" in problems(
        run(env, mutated(env, lambda g: f(g, "2025-02-30")))
    )
    assert "date value" not in problems(run(env, mutated(env, lambda g: f(g, "2025-02-28"))))


def test_known_non_derived_needs_evidence(env):
    g = mutated(env, lambda g: g["facts"][0].update(evidence=[]))
    assert "needs at least one evidence" in problems(run(env, g))


# ---- sources


def test_source_missing_file_and_bad_hash(env):
    def f(g):
        g["sources"][0]["file"] = "ACME/nope.htm"

    assert "not found under the corpus" in problems(run(env, mutated(env, f)))
    g = mutated(env, lambda g: g["sources"][0].update(sha256="0" * 64))
    assert "$.sources[0].sha256: does not match" in problems(run(env, g))


def test_source_path_escape_refused(env):
    g = mutated(env, lambda g: g["sources"][0].update(file="../financial_gold.json"))
    assert "relative path inside the corpus" in problems(run(env, g))


def test_source_filed_after_cutoff(env):
    g = mutated(env, lambda g: g["sources"][0].update(filed="2026-11-01"))
    assert "is after the cutoff" in problems(run(env, g))


def test_evidence_source_must_be_listed(env):
    g = mutated(env, lambda g: g["facts"][0]["evidence"][0].update(source_id="zz"))
    assert "'zz' is not a listed source" in problems(run(env, g))


# ---- quotes


def test_zero_width_characters_deleted(env):
    zw = "\u200b\u200c\u200d\u2060\ufeff"
    assert chk.visible_text(f"<p>1,{zw}234 a{zw} b</p>") == "1,234 a b"
    html = env["html"]
    html.write_bytes(f"<p>Net 1,\u200b234 total</p>{HTML}".encode())
    g = mutated(env, lambda g: g["sources"][0].update(sha256=sha(html.read_bytes())))
    ev0 = g["facts"][0]["evidence"][0]
    ev0.update(quote="Net 1,234 total", printed="1,234")
    assert run(env, g).problems == []
    ev0.update(quote="Net 1,\u200d234 total", printed="Net")
    assert run(env, g).problems == []


def test_zero_width_paragraph_quote_collapses_whitespace(env):
    html = env["html"]
    html.write_bytes(b"<p>A</p><p>&#8203;</p><p>B</p>")
    g = mutated(env, lambda g: g["sources"][0].update(sha256=sha(html.read_bytes())))
    g["facts"][0]["evidence"][0].update(quote="A \u200b B", printed="A \u200b B")
    g["facts"] = g["facts"][:1]
    assert run(env, g).problems == []


def test_quote_found_and_not_found(env):
    g = mutated(
        env,
        lambda g: g["facts"][0]["evidence"][0].update(quote="Term loan $ 1,001", printed="1,001"),
    )
    assert "quote not found" in problems(run(env, g))
    g = mutated(
        env, lambda g: g["facts"][0]["evidence"][0].update(quote="Secret", printed="Secret")
    )
    assert "quote not found" in problems(run(env, g))


def test_printed_must_be_in_quote(env):
    g = mutated(env, lambda g: g["facts"][0]["evidence"][0].update(printed="7,777"))
    assert "printed value is not a substring of quote" in problems(run(env, g))


def test_quote_length_limit(env):
    g = mutated(
        env, lambda g: g["facts"][0]["evidence"][0].update(quote="Term loan " * 40, printed="Term")
    )
    assert "longer than 300" in problems(run(env, g))


def test_pdf_source_is_noted_not_failed(env):
    def f(g):
        g["sources"].append(
            {
                "source_id": "p1",
                "file": "ACME/b.pdf",
                "sha256": sha(b"%PDF-1.4"),
                "url": "",
                "form": "AR",
                "period_end": "",
                "filed": "2026-01-01",
            }
        )
        g["facts"][0]["evidence"] = [
            {"source_id": "p1", "locator": "p3", "quote": "anything", "printed": "any"}
        ]

    out = run(env, mutated(env, f))
    assert out.problems == []
    assert any("not checked: pdf" in n for n in out.notes)


# ---- derivations


@pytest.mark.parametrize(
    ("op", "operands", "value"),
    [
        ("sum", ["CP-2.t.a", "CP-2.t.b"], "1900"),
        ("difference", ["CP-2.t.a", "CP-2.t.b"], "100"),
        ("negate", ["CP-2.t.a"], "-1000"),
        ("product", ["CP-2.t.a", "CP-2.t.b"], "900000000000"),
        ("ratio", ["CP-2.t.a", "CP-2.t.b"], "1.11"),
        ("ratio", ["CP-2.t.b", "CP-2.t.a"], "0.9"),
    ],
)
def test_derivation_passes(env, op, operands, value):
    g = mutated(env, lambda g: g["facts"].append(derived("CP-2.t.d", value, op, operands)))
    assert run(env, g).problems == []


@pytest.mark.parametrize(
    ("op", "operands", "value"),
    [
        ("sum", ["CP-2.t.a", "CP-2.t.b"], "1901"),
        ("difference", ["CP-2.t.b", "CP-2.t.a"], "100"),
        ("negate", ["CP-2.t.a"], "1000"),
        ("product", ["CP-2.t.a", "CP-2.t.b"], "90000"),
        ("ratio", ["CP-2.t.a", "CP-2.t.b"], "1.12"),
        ("ratio", ["CP-2.t.a", "CP-2.t.b"], "1.2"),
    ],
)
def test_derivation_fails(env, op, operands, value):
    g = mutated(env, lambda g: g["facts"].append(derived("CP-2.t.d", value, op, operands)))
    assert "recomputes to" in problems(run(env, g))


def _mixed(env, value, vtype="decimal", ops=("CP-2.t.k", "CP-2.t.m")):
    def f(g):
        g["facts"][0].update(value="500", scale="thousands")
        g["facts"][1].update(value="2", scale="millions", evidence=[ev(printed="900")])
        g["facts"].pop()
        g["facts"].append(derived("CP-2.t.d", value, "sum", ["CP-2.t.a", "CP-2.t.b"]))

    return mutated(env, f)


def test_mixed_scale_sum_passes(env):
    assert run(env, _mixed(env, "2.5")).problems == []


def test_mixed_scale_sum_wrong_value_fails(env):
    assert "recomputes to" in problems(run(env, _mixed(env, "2.6")))


def test_percent_ratio_passes_and_fails(env):
    def f(g, v):
        g["facts"].append(
            derived("CP-2.t.p", v, "ratio", ["CP-2.t.b", "CP-2.t.a"]) | {"value_type": "percent"}
        )

    assert run(env, mutated(env, lambda g: f(g, "90.0"))).problems == []
    assert "recomputes to" in problems(run(env, mutated(env, lambda g: f(g, "0.9"))))


@pytest.mark.parametrize(
    ("vtype", "op"), [("percent", "product"), ("bps", "ratio"), ("percent", "ratio")]
)
def test_percent_or_bps_operand_refused(env, vtype, op):
    def f(g):
        g["facts"][1].update(value_type=vtype, unit=vtype, scale=None, evidence=[ev(printed="900")])
        g["facts"].append(derived("CP-2.t.d", "1", op, ["CP-2.t.a", "CP-2.t.b"]))

    text = problems(run(env, mutated(env, f)))
    assert "operand 'CP-2.t.b'" in text
    assert "percent/bps" in text


def test_derivation_operand_rules(env):
    def f(g):
        g["facts"][1].update(status="missing", value=None, evidence=[], gap_reason="x")
        g["facts"].append(derived("CP-2.t.d", "1", "sum", ["CP-2.t.a", "CP-2.t.b", "CP-2.t.nope"]))

    text = problems(run(env, mutated(env, f)))
    assert "operand 'CP-2.t.b' is not a known decimal fact" in text
    assert "operand 'CP-2.t.nope' is not a fact in this file" in text


def test_derivation_arity_zero_divisor_and_script(env):
    def f(g):
        g["facts"][1].update(value="0", evidence=[ev(quote="900", printed="0")])
        g["facts"].append(derived("CP-2.t.n", "0", "negate", ["CP-2.t.a", "CP-2.t.a"]))
        g["facts"].append(derived("CP-2.t.r", "0", "ratio", ["CP-2.t.a", "CP-2.t.b"]))
        g["facts"][-1]["derivation"]["script"] = "missing.py"

    text = problems(run(env, mutated(env, f)))
    assert "negate needs exactly 1 operand" in text
    assert "ratio divisor is zero" in text
    assert "script 'missing.py' not found" in text


# ---- financial_gold


def test_financial_gold_path_and_hash(env):
    g = mutated(env, lambda g: g["financial_gold"].update(sha256="0" * 64))
    assert "$.financial_gold.sha256: does not match" in problems(run(env, g))
    g = mutated(env, lambda g: g["financial_gold"].update(path="/nonexistent/x.json"))
    assert "$.financial_gold.path: file not found" in problems(run(env, g))


def test_unparseable_and_duplicate_key_json(env):
    write(env)
    env["case"].joinpath("module_golden.json").write_text("{")
    env["case"].joinpath("context.json").write_text(
        '{"schema": "context/1", "schema": "context/1"}'
    )
    out = chk.check_case(env["case"], env["corpus"])
    text = problems(out)
    assert "module_golden.json: $: invalid JSON" in text
    assert "context.json: $: invalid JSON: duplicate key 'schema'" in text


# ---- context.json


def ctx_problems(env, fn):
    c = valid_context()
    fn(c)
    return problems(run(env, context=c))


def test_context_valid_and_missing_file(env):
    assert run(env).problems == []
    run(env)
    env["case"].joinpath("context.json").unlink()
    out = chk.check_case(env["case"], env["corpus"])
    assert "context.json: $: cannot read file" in problems(out)


def test_context_unknown_and_missing_keys(env):
    def f(c):
        c["extra"] = 1
        c["run"]["nope"] = 1
        del c["identity"]["ticker"]
        c["valuation"]["issuer_market"]["zzz"] = ""

    text = ctx_problems(env, f)
    assert "$.extra: unknown key" in text
    assert "$.run.nope: unknown key" in text
    assert "$.identity.ticker: missing key" in text
    assert "$.valuation.issuer_market.zzz: unknown key" in text


def test_context_schema_and_enums(env):
    def f(c):
        c["schema"] = "context/2"
        c["run"].update(run_type="deal", pathway="other", case_kind="secret")
        c["assumptions"]["cp2e"]["rate_shocks_bps"] = ["1x"]
        c["quotes"][0]["kind"] = "guess"
        c["attachments"]["legal_documents"] = "maybe"

    text = ctx_problems(env, f)
    for path in (
        "$.schema",
        "$.run.run_type",
        "$.run.pathway",
        "$.run.case_kind",
        "$.quotes[0].kind",
        "$.attachments.legal_documents",
    ):
        assert f"{path}: must be one of" in text
    assert "$.assumptions.cp2e.rate_shocks_bps[0]" in text
    for ok in ("primary", "secondary", "research", "earnings"):
        assert ctx_problems(env, lambda c, ok=ok: c["run"].update(run_type=ok)) == ""
    for ok in ("public", "private"):
        assert ctx_problems(env, lambda c, ok=ok: c["run"].update(case_kind=ok)) == ""


def test_context_dates_and_periods(env):
    def f(c):
        c["run"]["as_of"] = "2026-02-30"
        c["run"]["current_period"] = "Q3-2026"
        c["run"]["prior_period"] = "h3-2026"
        c["quotes"][0]["as_of"] = "10/30/2026"

    text = ctx_problems(env, f)
    assert "$.run.as_of: not a real calendar date" in text
    assert "$.run.current_period: use q1-2026" in text
    assert "$.run.prior_period: use q1-2026" in text
    assert "$.quotes[0].as_of: use a date" in text
    assert (
        ctx_problems(env, lambda c: c["run"].update(current_period="fy-2025", prior_period=""))
        == ""
    )
    assert "$.run.as_of: required" in ctx_problems(env, lambda c: c["run"].update(as_of=""))


def test_context_number_fields(env):
    def f(c):
        c["quotes"][0]["bid"] = "1,250"
        c["quotes"][0]["price"] = "-3"
        c["valuation"]["issuer_market"]["market_cap_m"] = "12."
        c["valuation"]["issuer_market"]["net_debt_m"] = "--1"
        c["quotes"][0]["spread_bps"] = 5

    text = ctx_problems(env, f)
    assert "$.quotes[0].bid: enter a plain number" in text
    assert "$.quotes[0].price: enter a plain number" in text
    assert "$.valuation.issuer_market.market_cap_m: enter a plain number" in text
    assert "$.valuation.issuer_market.net_debt_m: enter a plain number" in text
    assert "$.quotes[0].spread_bps: expected a string" in text
    # signed field accepts a negative; empty means not supplied
    assert ctx_problems(env, lambda c: c["quotes"][0].update(ask="")) == ""


# ---- CLI


def test_cli_exit_codes_and_line_format(env):
    write(env)
    cmd = [sys.executable, "-I", str(SCRIPT), "--corpus", str(env["corpus"]), str(env["case"])]
    ok = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert ok.returncode == 0, ok.stdout
    g = mutated(env, lambda g: g["sources"][0].update(sha256="0" * 64))
    write(env, g)
    bad = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert bad.returncode == 1
    assert f"{env['case']}/module_golden.json: $.sources[0].sha256: " in bad.stdout
