// Stage 5.2 native DOM check, evaluated in the delivered page (see README in this folder).
// Clicks every navigator and footer row, the six rail destinations, each drawn Front Page
// block link and every other '#' link, and reads the h1 and status chip the page shows.
(async () => {
  const E = JSON.parse(localStorage.getItem("expect"))[location.pathname];
  if (!E) return { error: "no expectation for " + location.pathname };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const root = document.getElementById("view-root");
  const view = () => ({
    h1: root.querySelector("h1")?.textContent.trim() ?? null,
    // The module's own chip and empty state; on CP-1 the Model destination section above it has its own.
    chip: root.querySelector(":scope > div > .chip")?.textContent.trim() ?? null,
    empty: !!root.querySelector(":scope > div .empty-state"),
    unknown: /Unknown destination/.test(root.textContent),
  });
  const settle = async want => { for (let i = 0; i < 60; i++) { await sleep(50); if (want === undefined || view().h1 === want) break; } return view(); };
  const click = async (a, want) => { a.click(); return settle(want); };
  const rail = href => document.querySelector(`a.rail-btn[href="${href}"]`);
  const bad = [], visited = new Set(), res = { page: location.pathname, scope: E.scope };
  // Optional part for slow pages (localStorage "phase"): {rows:[a,b]} | {part:"rails"|"blocks"|"calc"} | {part:"hashes", known:[...]}.
  const P = JSON.parse(localStorage.getItem("phase") || "null");
  const on = part => !P || P.part === part || (part === "rows" && !!P.rows);
  if (P) res.phase = P;
  const wordOf = id => E.heads[id];
  const banner = document.getElementById("delivery-scope-banner")?.dataset.deliveryScope;
  if (banner !== E.scope) bad.push({ what: "delivery scope banner", banner, scope: E.scope });

  // Navigator (numbered) and footer rows.
  const nav = document.getElementById("navigator");
  const rows = [...nav.querySelectorAll("a.module-link")].map(a => ({ a, group: "numbered", num: a.querySelector(".n")?.textContent.trim(), word: a.querySelector(".sr-only")?.textContent.replace(/^\s*·\s*/, "").trim() }))
    .concat([...nav.querySelectorAll(".nav-foot a[href^='#']")].map(a => ({ a, group: "footer", num: null, word: a.closest("details")?.querySelector("summary")?.textContent.replace(/\s*·\s*\d+\s*$/, "").trim() })));
  const numbered = rows.filter(r => r.group === "numbered").map(r => r.a.getAttribute("href").slice(1));
  if (JSON.stringify(numbered) !== JSON.stringify(E.plan)) bad.push({ what: "numbered rows != plan", numbered, plan: E.plan });
  rows.filter(r => r.group === "numbered").forEach((r, i) => { if (r.num !== String(i + 1)) bad.push({ what: "numbering", id: r.a.getAttribute("href"), num: r.num }); });
  const ids = rows.map(r => r.a.getAttribute("href").slice(1));
  if (ids.length !== Object.keys(E.titles).length || new Set(ids).size !== ids.length) bad.push({ what: "row count", n: ids.length });
  // A real pointer reaches the row: from each route visited, every numbered row's centre hit-tests to the row.
  const covered = [];
  // Run at a desktop viewport (1440x900): below 1350px the navigator is a closed drawer and cannot be hit-tested.
  if (getComputedStyle(nav).display === "none") bad.push({ what: "navigator hidden; run at 1440x900", vw: innerWidth });
  const hitTest = () => { nav.scrollTop = 0; for (const n of nav.querySelectorAll("a.module-link")) { n.scrollIntoView({ block: "nearest" }); const b = n.getBoundingClientRect(), t = document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2); if (!n.contains(t)) covered.push(`${location.hash || "#front"}>${n.getAttribute("href")}`); } };
  for (const r of on("rows") ? (P?.rows ? rows.slice(...P.rows) : rows) : []) {
    const id = r.a.getAttribute("href").slice(1), want = E.titles[id];
    hitTest();
    const v = await click(r.a, want); visited.add("#" + id);
    const head = wordOf(id);
    const wantWord = head ?? (r.group === "numbered" ? "Not run" : r.word);
    // Only accepted and restricted heads carry output; every other row lands on an empty status page.
    const carries = head === "Pass" || head === "With limitations";
    const ok = v.h1 === want && v.chip === r.word && v.chip === wantWord && v.empty === !carries && !v.unknown
      && (r.group === "numbered" || ["Not in this Pathway", "Not run"].includes(r.word));
    const o = E.oracle?.rows[id];
    const okOracle = !o || (o[0] === r.group && (o[1] === null ? r.num === null : String(o[1]) === r.num) && o[2] === v.h1 && o[3] === v.chip && o[4] === !v.empty);
    if (!ok || !okOracle) bad.push({ what: "row", id, group: r.group, rowWord: r.word, head, ...v, oracle: o });
  }
  res.rows = rows.length;
  if (covered.length) bad.push({ what: "numbered rows covered (a real click misses)", n: covered.length, sample: covered.slice(0, 6) });

  // The six rail destinations.
  const rails = [...document.querySelectorAll("a.rail-btn")];
  if (on("rails")) {
  const fixed = { "#front": E.issuer, "#analysis": "Analysis", "#FIT": "Portfolio Fit", "#evidence": "Evidence", "#limitations": "Limitations" };
  for (const a of rails) {
    const href = a.getAttribute("href"), want = fixed[href] ?? E.titles[href.slice(1)];
    const v = await click(a, want); visited.add(href);
    const okOracle = !E.oracle || E.oracle.destinations[href] === v.h1;
    if (v.h1 !== want || v.unknown || !okOracle) bad.push({ what: "rail", href, want, ...v });
  }
  res.rails = rails.length;
  if (rails.length !== 6) bad.push({ what: "rail count", n: rails.length });
  }

  // Front Page block links (re-found after each return to the front page).
  if (on("blocks")) {
  await click(rail("#front"), E.issuer);
  const blocks = [...root.querySelectorAll("a.full")].map(a => [a.getAttribute("href"), a.textContent.trim()]);
  const seenBlocks = [];
  for (let i = 0; i < blocks.length; i++) {
    await click(rail("#front"), E.issuer);
    const a = [...root.querySelectorAll("a.full")][i], href = a.getAttribute("href"), id = href.slice(1);
    const v = await click(a, E.titles[id]); visited.add(href);
    seenBlocks.push([href, v.h1, v.chip]);
    if (v.h1 !== E.titles[id] || v.chip !== (wordOf(id) ?? v.chip) || v.unknown) bad.push({ what: "block", href, text: blocks[i][1], ...v });
  }
  // The oracle lists the superset the Pathway can draw (rule hash_links_not_derivable_without_a_real_store):
  // every drawn link must be one of them.
  if (E.oracle) for (const s of seenBlocks) if (!E.oracle.blocks.some(b => s[0] === b[0] && s[1] === b[1] && s[2] === b[2])) bad.push({ what: "block link outside the oracle", s });
  res.blocks = blocks.length;
  }

  // Every other '#' link drawn on any page visited so far, then the skip link.
  if (on("hashes")) {
  const all = new Set();
  const collect0 = () => document.querySelectorAll("a[href^='#']").forEach(a => all.add(a.getAttribute("href")));
  if (P?.known) { for (const h of P.known) visited.add(h); location.hash = "#front"; await settle(); collect0(); }
  const collect = () => document.querySelectorAll("a[href^='#']").forEach(a => all.add(a.getAttribute("href")));
  for (const h of P?.known ? [] : [...visited]) { location.hash = h; await settle(); collect(); }
  for (const h of [...all].filter(h => h !== "#workbench" && !visited.has(h))) {
    location.hash = h; const v = await settle(); visited.add(h);
    if (!v.h1 || v.unknown) bad.push({ what: "hash", h, ...v });
  }
  res.hashes = all.size;
  const skip = document.querySelector("a.skip[href='#workbench']");
  if (skip) { skip.click(); await sleep(100); if (document.activeElement?.id !== "workbench") bad.push({ what: "skip link focus", active: document.activeElement?.id }); }
  else bad.push({ what: "no skip link" });
  }

  // calculation.json link on the Model destination (the CP-1 page).
  if (!on("calc")) {} else if (E.calc) {
    await click(document.querySelector("a.module-link[href='#CP-1']"), E.titles["CP-1"]);
    const link = root.querySelector("a[href='calculation.json']");
    if (!link || !E.calc_on_disk) bad.push({ what: "calculation.json link", drawn: !!link, onDisk: E.calc_on_disk });
    res.calc = link?.href ?? null;
  } else if (root.querySelector("a[href='calculation.json']")) bad.push({ what: "calculation.json drawn without a published model" });
  location.hash = "#front";
  res.bad = bad;
  return res;
})()
