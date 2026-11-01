"""R1 as written: html.parser, one line per p/div/tr/li/br/h1-h6, script+style dropped,
normalise() within a line. Count golden quotes not found inside a single converted line.
Variant B adds check.py's other block tags (td, th, table, ...) and its hidden rules.
Exit 0 when R1-as-written finds every quote; 1 otherwise. Args: repo root, corpus root."""
import html.parser, importlib.util, json, pathlib, sys
repo, corpus = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("chk", repo / "cases/goldens/check.py")
chk = importlib.util.module_from_spec(spec); spec.loader.exec_module(chk)
R1_BLOCK = {"p", "div", "tr", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6"}

class Lines(html.parser.HTMLParser):
    def __init__(self, block, skip, hidden):
        super().__init__(convert_charrefs=True)
        self.block, self.skip, self.hidden = block, skip, hidden
        self.parts, self.stack, self.skipping = [], [], 0
    def handle_starttag(self, tag, attrs):
        if tag in self.block: self.parts.append("\n")
        if tag in chk.VOID: return
        h = tag in self.skip or (self.hidden and any(k == "style" and chk.HIDDEN.search(v or "") for k, v in attrs))
        self.stack.append((tag, h)); self.skipping += h
    def handle_startendtag(self, tag, attrs):
        if tag in self.block: self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in self.block: self.parts.append("\n")
        if tag in chk.VOID: return
        names = [t for t, _ in self.stack]
        if tag not in names: return
        keep = len(names) - 1 - names[::-1].index(tag)
        while len(self.stack) > keep:
            _, h = self.stack.pop(); self.skipping -= h
    def handle_data(self, data):
        if not self.skipping: self.parts.append(data)

def lines(raw, block, skip, hidden):
    p = Lines(block, skip, hidden); p.feed(raw); p.close()
    return [l for l in (chk.normalise(x) for x in "".join(p.parts).split("\n")) if l]

variants = {"R1": (R1_BLOCK, {"script", "style"}, False), "checkpy": (chk.BLOCK | R1_BLOCK, chk.SKIP, True)}
total = 0; miss = {k: 0 for k in variants}; adj = {k: 0 for k in variants}; examples = {k: [] for k in variants}
for case in sorted((repo / "cases/goldens").iterdir()):
    g = case / "module_golden.json"
    if not g.is_file(): continue
    data = json.loads(g.read_text())
    texts = {}
    for s in data["sources"]:
        p = corpus / s["file"]
        if p.suffix.lower() == ".pdf" or not p.is_file(): continue
        raw = p.read_text(encoding="utf-8", errors="replace")
        texts[s["source_id"]] = {k: lines(raw, *v) for k, v in variants.items()}
    for f in data["facts"]:
        for ev in f["evidence"]:
            if ev["source_id"] not in texts: continue
            total += 1
            q = chk.normalise(ev["quote"])
            for k in variants:
                L = texts[ev["source_id"]][k]
                if not any(q in l for l in L):
                    miss[k] += 1
                    if any(q in L[i] + " " + L[i + 1] for i in range(len(L) - 1)): adj[k] += 1
                    elif len(examples[k]) < 3: examples[k].append((case.name, f["fact_id"], q[:90]))
print("quotes checked:", total)
for k in variants:
    print(f"{k}: not in one line {miss[k]}; of which found across two adjacent lines {adj[k]}; examples {examples[k]}")
sys.exit(0 if miss["R1"] == 0 else 1)
