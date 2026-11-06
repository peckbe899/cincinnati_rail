try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 34: select several at once (Shift, Ctrl or Cmd click; drag a box with one held) and merge plots or streets.
# Run after patch_page.py (which writes deckpage/index.html from index_v32.html and engine.js).
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new, n=1):
    global src
    c = src.count(old)
    if c != n: sys.exit('count %d != %d for: %s' % (c, n, old[:100]))
    src = src.replace(old, new)

# ---- state
rep("colorBy: 'use', plots0: null, pl: null, ptool: null,", "colorBy: 'use', plots0: null, pl: null, ptool: null, multi: null,")
# ---- streets merged into another are gone from the plan
rep("const feats = layer => S.deck.features.filter(f => f.properties.layer === layer && (S.layers.we || !isWE(f)));",
    "const stGone = f => { const e = S.edits.streets[f.properties.id]; return !!(e && e.del); };\nconst feats = layer => S.deck.features.filter(f => f.properties.layer === layer && (S.layers.we || !isWE(f)) && !(layer === 'street' && stGone(f)));")
rep("  return S.deck.features.filter(f => f.properties.layer !== 'block').map(f => {",
    "  return S.deck.features.filter(f => f.properties.layer !== 'block' && !(f.properties.layer === 'street' && stGone(f))).map(f => {")
rep("kv('Area', fmt(f.area) + ' m²'); const sf = p.street && S.streetById.get(p.street); if (sf) kv('Fronts', sf.properties.name);",
    "kv('Area', fmt(f.area) + ' m²'); const sf = liveStreet(p.street); if (sf) kv('Fronts', sf.properties.name);")
# ---- selection drawing: one or several
OLD_DS = src[src.index("function drawSelection() {"):src.index("function drawLock() {")]
NEW_DS = r'''function drawSelection() {
  const ml = multiList();
  if (ml) for (const f of ml) drawSelOne(f, true, f === ml[0]); else if (S.sel) drawSelOne(S.sel.f, false, true);
  const d = S.drag; ctx.save(); ctx.strokeStyle = C.accent;
  if (d && d.mode === 'cut') { const a = W2S(d.p0[0], d.p0[1]), b = W2S(d.p1[0], d.p1[1]); ctx.setLineDash([6, 4]); ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); }
  if (d && d.mode === 'box') { const x = Math.min(d.a[0], d.b[0]), y = Math.min(d.a[1], d.b[1]), w = Math.abs(d.b[0] - d.a[0]), h = Math.abs(d.b[1] - d.a[1]); ctx.fillStyle = C.accent; ctx.globalAlpha = 0.08; ctx.fillRect(x, y, w, h); ctx.globalAlpha = 1; ctx.setLineDash([5, 4]); ctx.lineWidth = 1.5; ctx.strokeRect(x, y, w, h); }
  ctx.restore();
}
function drawSelOne(f, many, first) {
  const v = S.view; ctx.save(); ctx.strokeStyle = C.accent; ctx.lineWidth = many && !first ? 2.2 : 3;
  const L = f.properties.layer;
  if (L === 'street' || L === 'transit') {
    const c = lineCoords(f), wpx = L === 'street' ? streetWidth(f) * v.s + 4 : (f.properties.sys === 'rer' ? 9 : 10) * v.s + 4;
    ctx.globalAlpha = 0.35; ctx.lineWidth = Math.max(4, wpx); ctx.beginPath(); pathLine(c); ctx.stroke();
    if (L === 'transit' || many) { ctx.globalAlpha = 1; ctx.lineWidth = 1.6; ctx.beginPath(); pathLine(c); ctx.stroke(); }
    if (!many && S.tool === 'edit') { drawHandles(f); drawLock(); }
    if (!many && v.s >= 0.2) { ctx.save(); ctx.setLineDash([]); ctx.globalAlpha = 1; ctx.font = '600 11px ' + css('--font-ui');
      for (const g of curveGroups(f)) { if (g.R >= 20000) continue; const [x, y] = W2S(g.mid[0], g.mid[1]), t = 'R ' + fmt(g.R) + ' m'; ctx.lineWidth = 3; ctx.strokeStyle = C.panel; ctx.strokeText(t, x + 8, y - 8); ctx.fillStyle = C.accent; ctx.fillText(t, x + 8, y - 8); }
      ctx.restore(); }
  } else if (L === 'station') {
    const [x, y] = W2S(...f.geometry.coordinates); ctx.globalAlpha = 1; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(x, y, 10, 0, 7); ctx.stroke();
    ctx.lineWidth = 2.5; for (const sp of f.properties.stops) { for (const r of stopRings(sp)) { ctx.beginPath(); pathLine(r); ctx.closePath(); ctx.stroke(); }
      if (!many && sp.pid && S.tool === 'edit' && !stDeleted(f)) { const [s0, , g] = stopFrame(sp), q = frameAt(g.c, g.cs, s0), [a, b] = W2S(q[0], q[1]); ctx.lineWidth = 1.5; ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(a, b); ctx.lineTo(x, y); ctx.stroke(); ctx.setLineDash([]);
        const n = 12 / Math.max(S.view.s, 0.05); ctx.lineWidth = 2.5; ctx.beginPath(); pathLine([[q[0] - q[3] * n, q[1] + q[2] * n], [q[0] + q[3] * n, q[1] - q[2] * n]]); ctx.stroke(); } }
  } else { if (many) { ctx.globalAlpha = 0.18; ctx.fillStyle = C.accent; ctx.beginPath(); pathPoly(f.geometry); ctx.fill('evenodd'); ctx.globalAlpha = 1; } ctx.beginPath(); pathPoly(f.geometry); ctx.stroke(); }
  ctx.restore();
}
'''
src = src.replace(OLD_DS, NEW_DS)
# ---- single selection clears the multi-selection; handles only for one line
rep("function select(f) { S.sel = f ? { f } : null;", "function select(f) { S.sel = f ? { f } : null; S.multi = null;")
rep("function lineSel() { const s = S.sel; return s && S.tool === 'edit'", "function lineSel() { const s = S.sel; return s && !multiList() && S.tool === 'edit'")
rep("  const s = S.sel; if (!s || S.tool !== 'edit' || s.f.properties.layer !== 'station' || stDeleted(s.f)) return null; const q = S2W(px, py);",
    "  const s = S.sel; if (!s || multiList() || S.tool !== 'edit' || s.f.properties.layer !== 'station' || stDeleted(s.f)) return null; const q = S2W(px, py);")
# ---- panel for several
rep("  empty.hidden = true; body.hidden = false; body.textContent = '';\n", "  empty.hidden = true; body.hidden = false; body.textContent = '';\n  if (multiList()) { renderMulti(body); return; }\n")
# ---- merged streets: unmerge, and reset puts the others back
rep("    const bR = document.createElement('button'); bR.className = 'btn'; bR.textContent = 'Reset this street'; bR.disabled = !e || !S.canWrite; bR.addEventListener('click', () => { delete S.edits.streets[p.id]; changed(); renderSel(); });\n    row2.append(bE, bR); body.append(row2); curveRow(f, body); alsoHere(f, body);",
    "    const bR = document.createElement('button'); bR.className = 'btn'; bR.textContent = 'Reset this street'; bR.disabled = !e || !S.canWrite; bR.addEventListener('click', () => { if (e && e.mg) for (const [id, x] of Object.entries(e.mg.pre)) { if (id === p.id) continue; if (x) S.edits.streets[id] = x; else delete S.edits.streets[id]; } delete S.edits.streets[p.id]; changed(); renderSel(); });\n    row2.append(bE, bR); body.append(row2);\n    if (e && e.mg) { const n = document.createElement('p'); n.className = 'notes'; n.style.marginTop = '8px'; n.textContent = 'Merged from ' + [p.id].concat(e.mg.ids).map(id => { const g = S.streetById.get(id); return (g ? g.properties.name : id) + ' (' + id + ')'; }).join(', ') + '.'; const r3 = document.createElement('div'); r3.className = 'row'; const bU = document.createElement('button'); bU.className = 'btn'; bU.textContent = 'Unmerge'; bU.disabled = !S.canWrite; bU.title = 'Put the streets back as they were before the merge'; bU.addEventListener('click', () => unmerge(f)); r3.append(bU); body.append(n, r3); }\n    curveRow(f, body); alsoHere(f, body);")
# ---- pointer: box select and modifier clicks
rep("    const sp = stopAt(px, py); if (sp) { const [, , g] = stopFrame(sp); S.drag = { mode: 'slide', sp, s0: projectOn(g.c, g.cs, S2W(px, py))[0], o0: stopOff(sp), g }; down = null; cv.classList.add('dragging'); return; }\n  }\n  down = { px, py, cx: S.view.cx, cy: S.view.cy, moved: false };",
    "    const sp = stopAt(px, py); if (sp) { const [, , g] = stopFrame(sp); S.drag = { mode: 'slide', sp, s0: projectOn(g.c, g.cs, S2W(px, py))[0], o0: stopOff(sp), g }; down = null; cv.classList.add('dragging'); return; }\n  }\n  if (e.shiftKey || e.ctrlKey || e.metaKey) { S.drag = { mode: 'box', a: [px, py], b: [px, py] }; down = null; return; }   // with Shift, Ctrl or Cmd: a click adds or removes, a drag draws a box\n  down = { px, py, cx: S.view.cx, cy: S.view.cy, moved: false };")
rep("  const d = S.drag;\n  if (d && S.sel) {", "  const d = S.drag;\n  if (d && d.mode === 'box') { d.b = [px, py]; redraw(); return; }\n  if (d && S.sel) {")
rep("  if (S.drag && S.drag.mode === 'cut') { const d = S.drag; S.drag = null; finishCut(d); return; }",
    "  if (S.drag && S.drag.mode === 'box') { const d = S.drag; S.drag = null; finishBox(d); return; }\n  if (S.drag && S.drag.mode === 'cut') { const d = S.drag; S.drag = null; finishCut(d); return; }")
rep("  if (e.key === 'Escape') { if (S.ptool) { S.ptool = null; S.drag = null; setTool(S.tool); return; } if (S.sel) select(null); }",
    "  if (e.key === 'Escape') { if (S.ptool) { S.ptool = null; S.drag = null; setTool(S.tool); return; } if (S.drag && S.drag.mode === 'box') { S.drag = null; redraw(); return; } if (S.sel) select(null); }")
rep("'Drag to pan, scroll or pinch to zoom. Click a street, line, station, block or plot to see it; click again to step through what is under it.'",
    "'Drag to pan, scroll or pinch to zoom. Click a street, line, station, block or plot to see it; click again to step through what is under it. Shift, Ctrl or Cmd click to select several; drag with one held to box-select plots.'")
# ---- reselect keeps a multi-selection across a rebuild
rep("function reselect() {   // keep the selection across a rebuild\n",
    "function reselect() {   // keep the selection across a rebuild\n  if (S.multi) { const again = f => { const L = f.properties.layer, id = f.properties.id; return L === 'plot' ? S.pl.byId.get(id) || null : L === 'open' ? S.pl.open.find(o => o.properties.id === id) || null : L === 'block' ? S.pl.blockById.get(id) || S.pl.blockList.find(b => b.properties.id === id) || null : f; };\n    const m = S.multi.map(again).filter(Boolean); S.multi = m.length > 1 ? m : null; S.sel = m.length ? { f: m[0] } : null; if (S.multi) { renderSel(); return; } }\n")
# ---- the multi-selection code, after the plot engine
rep("function lotCount(g, u) {", r'''// ---------------------------------------------------------------- several at once (15 October)
// Shift, Ctrl or Cmd click adds a thing to the selection or takes it out; dragging with one of them held draws a box that adds every
// plot whose middle is inside it. Two or more plots that make one connected piece can be merged (one plot step, the first selected
// keeping its id, use and name); two or more streets merge into the first selected: the others join it end to end, an overlap where
// one was drawn over another is dropped, a gap is bridged with a straight piece, and the others are kept as merged into it
// (edits.streets[id] = {del, into}), with the state before the merge on the merged street (mg.pre) for Unmerge.
function multiList() { return S.multi && S.multi.length > 1 ? S.multi : null; }
function setMulti(cur) { S.multi = cur.length > 1 ? cur : null; S.sel = cur.length ? { f: cur[0] } : null; if (S.ptool) { S.ptool = null; setTool(S.tool); } renderSel(); redraw(); }
function toggleMulti(f) { const cur = S.multi ? S.multi.slice() : (S.sel ? [S.sel.f] : []), i = cur.indexOf(f); if (i >= 0) cur.splice(i, 1); else cur.push(f); setMulti(cur); }
function addMulti(fs) { const cur = S.multi ? S.multi.slice() : (S.sel ? [S.sel.f] : []); for (const f of fs) if (!cur.includes(f)) cur.push(f); setMulti(cur); }
function plotMid(pf) { if (pf._m) return pf._m; const r = pf.geometry.coordinates[0]; let a = 0, cx = 0, cy = 0; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const w = r[j][0] * r[i][1] - r[i][0] * r[j][1]; a += w; cx += (r[j][0] + r[i][0]) * w; cy += (r[j][1] + r[i][1]) * w; } pf._m = Math.abs(a) > 1e-9 ? [cx / (3 * a), cy / (3 * a)] : r[0]; return pf._m; }
function plotsInBox(x0, y0, x1, y1) {
  if (!S.pl || !S.layers.plt || !S.layers.blk || S.view.s < PZ) return [];
  const out = [], seen = new Set();
  for (let gx = Math.floor(x0 / 100); gx <= Math.floor(x1 / 100); gx++) for (let gy = Math.floor(y0 / 100); gy <= Math.floor(y1 / 100); gy++) for (const pf of (S.pl.grid.get(gx + ',' + gy) || [])) {
    if (seen.has(pf)) continue; seen.add(pf); if (pf.properties.layer !== 'plot' || (!S.layers.we && pf.properties.we)) continue;
    const c = plotMid(pf); if (c[0] >= x0 && c[0] <= x1 && c[1] >= y0 && c[1] <= y1) out.push(pf); }
  return out;
}
function finishBox(d) {
  if (Math.hypot(d.b[0] - d.a[0], d.b[1] - d.a[1]) < 5) { const list = pickAll(...S2W(d.a[0], d.a[1])); if (list[0]) toggleMulti(list[0]); else redraw(); return; }
  const [x0, y1] = S2W(Math.min(d.a[0], d.b[0]), Math.min(d.a[1], d.b[1])), [x1, y0] = S2W(Math.max(d.a[0], d.b[0]), Math.max(d.a[1], d.b[1])), ps = plotsInBox(x0, y0, x1, y1);
  if (!ps.length) { $('hint').textContent = S.view.s < PZ ? 'Zoom in until the plots show (about 1 pixel per metre) to box-select them.' : 'No plot has its middle inside that box.'; redraw(); return; }
  addMulti(ps);
}
function connectedPlots(ps) { const n = ps.length, seen = new Set([0]), st = [0]; while (st.length) { const i = st.pop(); for (let j = 0; j < n; j++) if (!seen.has(j) && touching(ps[i], ps[j])) { seen.add(j); st.push(j); } } return seen.size === n; }
function setPlotUseQuiet(pf, code) { setPlotField(pf, 'u', undefined); pf._uv = -1; const inh = plotUse(pf)[0] || ''; setPlotField(pf, 'u', inh === code ? undefined : code); pf._uv = -1; }
function streetPiece(f) { return { v: vertsOf(f).map(q => q.slice()), k: Object.assign({}, ctrlOf(f) || {}) }; }
function revPiece(p) { const n = p.v.length, k = {}; for (const [i, c] of Object.entries(p.k)) k[n - 2 - +i] = c; return { v: p.v.slice().reverse(), k }; }
function appendPiece(ch, p, tol) {   // p joined onto the end of ch; p's leading points that lie on ch (drawn over it) are dropped
  let d = 0; while (d < p.v.length && lineDist(p.v[d], ch.v) < tol) d++;
  if (d >= p.v.length) return { v: ch.v, k: ch.k, gap: 0 };
  const n = ch.v.length, end = ch.v[n - 1], k = Object.assign({}, ch.k);
  if (d > 0 && Math.hypot(p.v[d - 1][0] - end[0], p.v[d - 1][1] - end[1]) < 0.5 && p.k[d - 1]) k[n - 1] = p.k[d - 1];   // they meet end to end: p's first piece keeps its curve
  for (const [i, c] of Object.entries(p.k)) { const j = +i; if (j >= d) k[n + j - d] = c; }
  return { v: ch.v.concat(p.v.slice(d)), k, gap: lineDist(end, p.v) };
}
function planMerge(fs) {
  let ch = streetPiece(fs[0]), maxGap = 0; const rest = fs.slice(1), tol = Math.max(2, streetWidth(fs[0]) / 2);
  while (rest.length) {
    let best = null;
    for (const f of rest) { let p = streetPiece(f); if (lineDist(p.v[p.v.length - 1], ch.v) < lineDist(p.v[0], ch.v)) p = revPiece(p);   // the end nearer the chain goes first
      const e = ch.v[ch.v.length - 1], s = ch.v[0], de = lineDist(e, p.v), ds = lineDist(s, p.v);
      if (!best || Math.min(de, ds) < best.d) best = { f, p, d: Math.min(de, ds), atEnd: de <= ds }; }
    rest.splice(rest.indexOf(best.f), 1);
    if (best.atEnd) ch = appendPiece(ch, best.p, tol);
    else { const r = appendPiece(revPiece(ch), best.p, tol), back = revPiece(r); back.gap = r.gap; ch = back; }
    maxGap = Math.max(maxGap, ch.gap || 0);
  }
  return { v: ch.v.map(q => [r1(q[0]), r1(q[1])]), k: Object.fromEntries(Object.entries(ch.k).map(([i, c]) => [i, [r1(c[0]), r1(c[1])]])), maxGap };
}
function mergeStreets(fs) {
  const prim = fs[0], plan = planMerge(fs), pre = {};
  for (const f of fs) { const e = S.edits.streets[f.properties.id]; pre[f.properties.id] = e ? JSON.parse(JSON.stringify(e)) : null; }
  const ne = Object.assign({}, S.edits.streets[prim.properties.id] || {}, { c: plan.v, k: plan.k, mg: { ids: fs.slice(1).map(f => f.properties.id), pre } });
  if (!Object.keys(ne.k).length) delete ne.k;
  S.edits.streets[prim.properties.id] = ne;
  for (const f of fs.slice(1)) S.edits.streets[f.properties.id] = { del: true, into: prim.properties.id };
  S.multi = null; S.sel = { f: prim }; changed(); renderSel();
}
function unmerge(f) { const e = S.edits.streets[f.properties.id]; if (!e || !e.mg) return; for (const [id, x] of Object.entries(e.mg.pre)) { if (x) S.edits.streets[id] = x; else delete S.edits.streets[id]; } changed(); renderSel(); }
function renderMulti(body) {
  const ml = multiList(), plots = ml.filter(f => f.properties.layer === 'plot'), streets = ml.filter(f => f.properties.layer === 'street'), other = ml.filter(f => !plots.includes(f) && !streets.includes(f));
  const P = (cls, t) => { const e = document.createElement('p'); e.className = cls; e.textContent = t; return e; };
  const words = [[plots.length, 'plot'], [streets.length, 'street'], [other.length, 'other thing']].filter(x => x[0]).map(([n, w]) => n + ' ' + w + (n === 1 ? '' : 's'));
  body.append(P('sel-name', ml.length + ' selected'), P('sel-sub', words.join(', ')));
  if (plots.length >= 2) {
    const box = document.createElement('div'); box.className = 'stop'; box.append(P('stop-h', 'Plots'));
    const dl = document.createElement('dl'); dl.className = 'kv'; const kv = (k, val) => { const dt = document.createElement('dt'); dt.textContent = k; const dd = document.createElement('dd'); dd.textContent = val; dl.append(dt, dd); };
    kv('Area together', fmt(plots.reduce((a, q) => a + q.area, 0)) + ' m²'); const mix = new Map(); for (const q of plots) { const u = plotUse(q)[0] || ''; mix.set(u, (mix.get(u) || 0) + 1); } kv('Uses', [...mix].map(([u, n]) => UNAME[u] + ' ' + n).join(' · ')); box.append(dl);
    const ok = jready() && connectedPlots(plots), row = document.createElement('div'); row.className = 'row';
    const bM = document.createElement('button'); bM.className = 'btn'; bM.textContent = 'Merge into ' + featLabel(plots[0]); bM.disabled = !S.canWrite || !ok;
    bM.addEventListener('click', () => { S.pendingSel = { layer: 'plot', id: plots[0].properties.id }; S.multi = null; pushOp({ t: 'm', ids: plots.map(q => q.properties.id) }); });
    row.append(bM); box.append(row);
    box.append(Object.assign(P('notes', ok ? 'One plot from all of them; the first selected keeps its id, use and name.' : jready() ? 'They do not make one piece: add the plots between them, or take out the ones apart from the rest.' : 'The geometry library is still loading.'), { style: 'margin-top:8px' }));
    box.append(Object.assign(P('stop-h', 'Use for all ' + plots.length), { style: 'margin-top:10px' }));
    const seg = document.createElement('div'); seg.className = 'seg';
    for (const [k, lab] of USES.concat([['', 'Not set']])) { const b = document.createElement('button'); b.className = 'btn use'; b.disabled = !S.canWrite; const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = useCol(k); b.append(sw, document.createTextNode(lab)); b.setAttribute('aria-pressed', String(mix.size === 1 && mix.has(k)));
      b.addEventListener('click', () => { for (const q of plots) setPlotUseQuiet(q, k); changed(); renderSel(); }); seg.append(b); }
    box.append(seg); body.append(box);
  }
  if (streets.length >= 2) {
    const plan = planMerge(streets), box = document.createElement('div'); box.className = 'stop'; box.append(P('stop-h', 'Streets'));
    const dl = document.createElement('dl'); dl.className = 'kv'; const kv = (k, val) => { const dt = document.createElement('dt'); dt.textContent = k; const dd = document.createElement('dd'); dd.textContent = val; dl.append(dt, dd); };
    kv('Length joined', fmt(lenOf(Object.keys(plan.k).length ? curveCoords(plan.v, plan.k) : plan.v)) + ' m'); kv('Widest gap bridged', fmt(plan.maxGap, 1) + ' m'); box.append(dl);
    const row = document.createElement('div'); row.className = 'row'; const bM = document.createElement('button'); bM.className = 'btn'; bM.textContent = 'Merge into ' + streets[0].properties.name; bM.disabled = !S.canWrite;
    bM.addEventListener('click', () => mergeStreets(streets)); row.append(bM); box.append(row);
    box.append(Object.assign(P('notes', 'The first street selected (' + streets[0].properties.id + ') keeps its name, width and kind. The others join it end to end: where one was drawn over another the overlap is dropped, and a gap is bridged with a straight piece.' + (plan.maxGap > 30 ? ' One join bridges ' + fmt(plan.maxGap) + ' m; check that these pieces belong together.' : '') + ' Unmerge on the merged street puts them back.'), { style: 'margin-top:8px' }));
    body.append(box);
  }
  const lst = document.createElement('div'); lst.className = 'also'; lst.append(document.createTextNode('Selected:'));
  for (const f of ml.slice(0, 40)) { const b = document.createElement('button'); b.className = 'btn'; b.textContent = featLabel(f); b.addEventListener('click', () => select(f)); lst.append(b); }
  if (ml.length > 40) lst.append(document.createTextNode('and ' + (ml.length - 40) + ' more'));
  const row = document.createElement('div'); row.className = 'row'; const bC = document.createElement('button'); bC.className = 'btn'; bC.textContent = 'Clear selection'; bC.addEventListener('click', () => select(null)); row.append(bC);
  body.append(lst, row, Object.assign(P('notes', 'Shift, Ctrl or Cmd click adds a thing or takes it out. Drag with one of them held to add every plot whose middle is inside the box. Esc clears.'), { style: 'margin-top:8px' }));
}
function lotCount(g, u) {''')
rep("Plots can be split along a line, merged with a neighbour, divided into lots, and given a use and a name, one by one or a whole block at a time.</p>",
    "Plots can be split along a line, merged with a neighbour, divided into lots, and given a use and a name, one by one or a whole block at a time. Since 15 October several things can be selected at once (Shift, Ctrl or Cmd click, or a box dragged with one of them held): selected plots that make one piece merge into one plot, and street pieces merge into one street (the first selected keeps its name and width; Unmerge puts them back).</p>")
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v34', len(src))
