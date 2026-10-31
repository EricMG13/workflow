"""Controller probe: golden quotes not inside one converted line, per block-tag policy
(check.py hidden rules; check.py BLOCK tags outside the policy add a space). Exit 0 always; prints counts."""
import importlib.util, json, pathlib, sys
repo, corpus = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("p2", pathlib.Path(__file__).with_name("p2_r1_conversion.py"))
src = spec.loader.get_source("p2").split("variants = {")[0].replace("repo, corpus = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])", "")
ns = {"repo": repo, "corpus": corpus}; exec(src, ns)
chk = ns["chk"]; Base = ns["Lines"]
class Sp(Base):
    def handle_starttag(self, tag, attrs):
        if tag in chk.BLOCK and tag not in self.block: self.parts.append(" ")
        super().handle_starttag(tag, attrs)
    def handle_startendtag(self, tag, attrs):
        if tag in chk.BLOCK and tag not in self.block: self.parts.append(" ")
        super().handle_startendtag(tag, attrs)
    def handle_endtag(self, tag):
        if tag in chk.BLOCK and tag not in self.block: self.parts.append(" ")
        super().handle_endtag(tag)
def lines(raw, block):
    p = Sp(block, chk.SKIP, True); p.feed(raw); p.close()
    return [l for l in (chk.normalise(x) for x in "".join(p.parts).split("\n")) if l]
H = {"h1", "h2", "h3", "h4", "h5", "h6"}
policies = {"R1": ns["R1_BLOCK"], "no-div": {"p", "tr", "li", "br"} | H, "tr+p": {"tr", "p"}, "tr": {"tr"}, "flat": set()}
total = 0; miss = dict.fromkeys(policies, 0)
for case in sorted((repo / "cases/goldens").iterdir()):
    g = case / "module_golden.json"
    if not g.is_file(): continue
    data = json.loads(g.read_text()); texts = {}
    for s in data["sources"]:
        p = corpus / s["file"]
        if p.suffix.lower() == ".pdf" or not p.is_file(): continue
        raw = p.read_text(encoding="utf-8", errors="replace")
        texts[s["source_id"]] = {k: lines(raw, b) for k, b in policies.items()}
    for f in data["facts"]:
        for ev in f["evidence"]:
            if ev["source_id"] not in texts: continue
            total += 1; q = chk.normalise(ev["quote"])
            for k in policies:
                if not any(q in l for l in texts[ev["source_id"]][k]): miss[k] += 1
print("quotes", total, miss)
