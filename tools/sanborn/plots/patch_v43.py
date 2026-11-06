try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 43 (Ben, 17 October): pick two points on a street or a Metro/RER/CVG Express line and change the stretch between them: a street's
# width for that stretch (widths per segment, e.wv), or one constant-radius curve between the two points (tangent to the line on both sides);
# filled blocks (side 'fill'). Chain: ... patch_v42.py && patch_v43.py
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new, n=1):
    global src
    c = src.count(old)
    if c != n: sys.exit('count %d != %d for: %s' % (c, n, old[:110]))
    src = src.replace(old, new)

# ---- picks
rep("function select(f) { S.sel = f ? { f } : null;", "function select(f) { if (!f || !S.rng || S.rng.id !== f.properties.id) S.rng = null; S.sel = f ? { f } : null;")
rep("    const vi = vertexAt(px, py); if (vi >= 0) { S.drag = { mode: 'v', vi, p0: vertsOf(S.sel.f)[vi].slice(), axes: lockAxes(S.sel.f, vi), lock: null };",
    "    const vi = vertexAt(px, py); if (vi >= 0) { S.drag = { mode: 'v', vi, p0: vertsOf(S.sel.f)[vi].slice(), axes: lockAxes(S.sel.f, vi), lock: null, px0: px, py0: py, moved: false };")
rep("    if (d.mode === 'v') { const f = S.sel.f, v = vertsOf(f).map(q => q.slice()); let w = [wx, wy];",
    "    if (d.mode === 'v' && !d.moved && Math.hypot(px - d.px0, py - d.py0) < 4) return;   // a click on a point picks it (two picks make a stretch)\n"
    "    if (d.mode === 'v') { d.moved = true; const f = S.sel.f, v = vertsOf(f).map(q => q.slice()); let w = [wx, wy];")
rep("  if (S.drag) { S.drag = null; cv.classList.remove('dragging'); changed(); renderSel(); return; }",
    "  if (S.drag && S.drag.mode === 'v' && !S.drag.moved) { const vi = S.drag.vi; S.drag = null; cv.classList.remove('dragging'); if (S.sel) rangePick(S.sel.f, vi); down = null; return; }\n"
    "  if (S.drag) { S.drag = null; cv.classList.remove('dragging'); changed(); renderSel(); return; }")
# ---- helpers: picks, widths per segment, one curve between two points
rep("function setStreet(id, patch) {", r"""function rngOf(f) { const r = S.rng; return r && f && r.id === f.properties.id && r.n === vertsOf(f).length ? r : null; }
function rangePick(f, vi) {
  const r = rngOf(f), n = vertsOf(f).length;
  if (!r || r.b !== null) S.rng = { id: f.properties.id, n, a: vi, b: null }; else if (vi === r.a) S.rng = null; else r.b = vi;
  renderSel(); redraw();
}
function subLine(f, i, j) { const v = vertsOf(f), K = ctrlOf(f) || {}, sk = {}; for (let s = i; s < j; s++) if (K[s]) sk[s - i] = K[s]; return curveCoords(v.slice(i, j + 1), sk); }
function remapWv(ov, oK, wv, nv, nK) {   // widths follow the line when points are added, removed or refitted: each new segment takes the old one under its middle
  const oc = []; for (let s = 0; s < ov.length - 1; s++) oc.push(oK[s] ? curveCoords([ov[s], ov[s + 1]], { 0: oK[s] }) : [ov[s], ov[s + 1]]);
  const out = []; for (let s = 0; s < nv.length - 1; s++) { const m = midHandle(nv, nK, s); let best = 0, bd = 1e18; oc.forEach((c, k) => { const d = lineDist(m, c); if (d < bd) { bd = d; best = k; } }); out.push(wv[best] || null); }
  return out.some(x => x) ? out : undefined;
}
function setWidthRange(f, i, j, w) {
  const n = vertsOf(f).length - 1, e = S.edits.streets[f.properties.id], base = streetWidth(f), wv = e && e.wv && e.wv.length === n ? e.wv.slice() : new Array(n).fill(null);
  for (let s = i; s < j; s++) wv[s] = Math.abs(w - base) < 0.01 ? null : w;
  setEdit(f, { wv: wv.some(x => x) ? wv : undefined });
}
function filletRange(f, i, j, Rq) {   // one constant-radius curve between points i and j, tangent to the line before i and after j
  const v = vertsOf(f).map(q => q.slice()), K = Object.assign({}, ctrlOf(f) || {}), n = v.length, A = v[i], B = v[j];
  const unit = (x, y) => { const L = Math.hypot(x, y); return L > 1e-9 ? [x / L, y / L] : null; };
  const pA = i > 0 ? (K[i - 1] || v[i - 1]) : null, nA = K[i] || v[i + 1], tA = pA ? unit(A[0] - pA[0], A[1] - pA[1]) : unit(nA[0] - A[0], nA[1] - A[1]);
  const nB = j < n - 1 ? (K[j] || v[j + 1]) : null, pB = K[j - 1] || v[j - 1], tB = nB ? unit(nB[0] - B[0], nB[1] - B[1]) : unit(B[0] - pB[0], B[1] - pB[1]);
  if (!tA || !tB) return { msg: 'Those points sit on top of each other.' };
  const cr = tA[0] * tB[1] - tA[1] * tB[0], th = Math.atan2(cr, tA[0] * tB[0] + tA[1] * tB[1]), dx = B[0] - A[0], dy = B[1] - A[1];
  const put = L => { const nk = {}; for (const [a, k] of Object.entries(K)) { const s = +a; if (s < i) nk[s] = k; else if (s >= j) nk[s + (L.v.length - 1) - (j - i)] = k; } for (const [a, k] of Object.entries(L.k)) nk[i + +a] = k;
    setEdit(f, { c: v.slice(0, i).concat(L.v, v.slice(j + 1)).map(q => [r1(q[0]), r1(q[1])]), k: Object.keys(nk).length ? nk : undefined }); };
  if (Math.abs(th) < Math.PI / 360) { put({ v: [A, B], k: {} }); return { msg: 'The line runs straight here: the stretch is now one straight.' }; }
  const s = (dx * tB[1] - dy * tB[0]) / cr, t = (tA[0] * dy - tA[1] * dx) / cr;
  if (!(s > 0.3 && t > 0.3) || Math.abs(th) > Math.PI * 0.97) return { msg: 'The line turns both ways between these points, or doubles back, so one curve cannot join them. Pick two points on one bend.' };
  const half = Math.abs(th) / 2, Rmax = Math.min(s, t) / Math.tan(half), R = Rq > 0 ? Math.min(Rq, Rmax) : Rmax, T = R * Math.tan(half);
  const V = [A[0] + tA[0] * s, A[1] + tA[1] * s], p1 = [V[0] - tA[0] * T, V[1] - tA[1] * T], p2 = [V[0] + tB[0] * T, V[1] + tB[1] * T];
  const nrm = th > 0 ? [-tA[1], tA[0]] : [tA[1], -tA[0]], cen = [p1[0] + nrm[0] * R, p1[1] + nrm[1] * R], a1 = Math.atan2(p1[1] - cen[1], p1[0] - cen[0]);
  const m = Math.max(1, Math.ceil(Math.abs(th) * 180 / Math.PI / 10)), ph = th / m, L = { v: [A], k: {} };
  if (s - T > 0.3) L.v.push(p1);
  for (let q = 1; q <= m; q++) { const am = a1 + ph * (q - 0.5), aq = a1 + ph * q, rc = R / Math.cos(ph / 2); L.k[L.v.length - 1] = [r1(cen[0] + rc * Math.cos(am)), r1(cen[1] + rc * Math.sin(am))]; L.v.push([cen[0] + R * Math.cos(aq), cen[1] + R * Math.sin(aq)]); }
  if (t - T > 0.3) L.v.push(B); else L.v[L.v.length - 1] = B;
  put(L);
  return { R, msg: 'One curve of ' + fmt(R) + ' m radius' + (Rq > 0 && Rq > Rmax + 0.5 ? ' (the largest that fits between these points; ' + fmt(Rq) + ' m does not)' : Rq > 0 ? '' : ' (the largest that fits between these points)') + ', turning ' + fmt(Math.abs(th) * 180 / Math.PI, 1) + '°.' };
}
function rangeBox(f, body) {
  const r = rngOf(f), street = f.properties.layer === 'street', box = document.createElement('div'); box.className = 'stop';
  const hh = document.createElement('p'); hh.className = 'stop-h'; hh.textContent = 'Between two points'; box.append(hh);
  const n = document.createElement('p'); n.className = 'notes'; box.append(n); body.append(box);
  if (!r || r.b === null) { n.textContent = S.tool !== 'edit' ? 'In Edit mode, click a point and then another to pick the stretch between them: ' + (street ? 'give it its own width, or ' : '') + 'make it one constant-radius curve.' : r ? 'Point ' + (r.a + 1) + ' picked. Click another point to pick the stretch between them (click the same point again to drop it).' : 'Click a point, then another point, to pick the stretch between them.'; return; }
  const i = Math.min(r.a, r.b), j = Math.max(r.a, r.b); n.textContent = 'Points ' + (i + 1) + ' to ' + (j + 1) + ', ' + fmt(lenOf(subLine(f, i, j))) + ' m along the line.';
  const mk = (lab, id, val, ph) => { const row = document.createElement('div'); row.className = 'row'; const l = document.createElement('label'); l.htmlFor = id; l.textContent = lab; const inp = document.createElement('input'); inp.type = 'number'; inp.id = id; inp.step = '0.5'; inp.style.width = '80px'; inp.disabled = !S.canWrite; if (val !== null) inp.value = val; if (ph) inp.placeholder = ph; row.append(l, inp); box.append(row); return [row, inp]; };
  const res = document.createElement('p'); res.className = 'notes'; res.style.marginTop = '6px';
  if (street) { const wv = streetWv(f), w0 = (wv && wv[i]) || streetWidth(f), [row, inp] = mk('Width (m)', 'rgW', w0.toFixed(1)); inp.min = '2'; inp.max = '80';
    const b = document.createElement('button'); b.className = 'btn'; b.textContent = 'Set for this stretch'; b.disabled = !S.canWrite; b.addEventListener('click', () => { const w = parseFloat(inp.value); if (!(w >= 2 && w <= 80)) return; setWidthRange(f, i, j, w); renderSel(); }); row.append(b); }
  const [row2, inR] = mk('Radius (m)', 'rgR', null, 'largest'); inR.min = '10';
  const bc = document.createElement('button'); bc.className = 'btn'; bc.textContent = 'One curve between them'; bc.disabled = !S.canWrite || j - i < 1;
  bc.addEventListener('click', () => { const out = filletRange(f, i, j, parseFloat(inR.value) || 0); S.rngMsg = out.msg; if (out.R !== undefined) S.rng = null; renderSel(); });
  row2.append(bc);
  const row3 = document.createElement('div'); row3.className = 'row'; const bx = document.createElement('button'); bx.className = 'btn'; bx.textContent = 'Drop the picks'; bx.addEventListener('click', () => { S.rng = null; renderSel(); redraw(); }); row3.append(bx); box.append(row3, res);
  const nn = document.createElement('p'); nn.className = 'notes'; nn.textContent = 'The curve keeps both points and the line’s direction on either side: it is the largest circle that fits unless you give a smaller radius, with straight runs to it where needed. Points between them are replaced.'; box.append(nn);
}
function setStreet(id, patch) {""")
rep("function setEdit(f, patch) {\n  const kind = editKind(f), id = f.properties.id; if (!kind) return;",
    "function setEdit(f, patch) {\n  const kind = editKind(f), id = f.properties.id; if (!kind) return;\n"
    "  { const old = S.edits[kind][id]; if (kind === 'streets' && old && old.wv && patch.c && !('wv' in patch) && patch.c.length !== vertsOf(f).length) patch = Object.assign({}, patch, { wv: remapWv(vertsOf(f), ctrlOf(f) || {}, old.wv, patch.c, patch.k || {}) }); }")
# show the last curve message once
rep("function rangeBox(f, body) {\n", "function rangeBox(f, body) {\n  if (S.rngMsg) { const m = document.createElement('p'); m.className = 'notes'; m.style.fontWeight = '600'; m.textContent = S.rngMsg; body.append(m); S.rngMsg = null; }\n")
# ---- panels
rep("    curveRow(f, body); alsoHere(f, body);\n  } else if (L === 'block') {", "    curveRow(f, body); rangeBox(f, body); alsoHere(f, body);\n  } else if (L === 'block') {")
rep("    row2.append(bE, bR); body.append(row2); curveRow(f, body);\n    const n = document.createElement('p'); n.className = 'notes'; n.style.marginTop = '8px'; n.textContent = 'Once edited, the tracks",
    "    row2.append(bE, bR); body.append(row2); curveRow(f, body); rangeBox(f, body);\n    const n = document.createElement('p'); n.className = 'notes'; n.style.marginTop = '8px'; n.textContent = 'Once edited, the tracks")
rep("    kv('Width', fmt(streetWidth(f), 1) + ' m (' + fmt(streetWidth(f) / 0.3048) + ' ft)' + (p.width_src === 'default' ? ', not printed' : ''));",
    "    { const rr = streetRuns(f); kv('Width', fmt(streetWidth(f), 1) + ' m (' + fmt(streetWidth(f) / 0.3048) + ' ft)' + (p.width_src === 'default' ? ', not printed' : '') + (rr ? '; between points: ' + rr.map(x => fmt(x.w, 1)).join(', ') + ' m along it' : '')); }")
rep("    row.append(lab, inp); body.append(row);\n    const row2 = document.createElement('div'); row2.className = 'row';\n    const bE = document.createElement('button'); bE.className = 'btn'; bE.textContent = S.tool === 'edit' ? 'Stop editing' : 'Edit points'; bE.disabled = !S.canWrite; bE.addEventListener('click', () => setTool(S.tool === 'edit' ? 'select' : 'edit'));\n    const bR = document.createElement('button'); bR.className = 'btn'; bR.textContent = 'Reset this street';",
    "    if (streetWv(f)) { const bW = document.createElement('button'); bW.className = 'btn'; bW.textContent = 'One width again'; bW.title = 'Drop the widths set between points'; bW.disabled = !S.canWrite; bW.addEventListener('click', () => { setEdit(f, { wv: undefined }); renderSel(); }); row.append(bW); }\n"
    "    row.append(lab, inp); body.append(row);\n    const row2 = document.createElement('div'); row2.className = 'row';\n    const bE = document.createElement('button'); bE.className = 'btn'; bE.textContent = S.tool === 'edit' ? 'Stop editing' : 'Edit points'; bE.disabled = !S.canWrite; bE.addEventListener('click', () => setTool(S.tool === 'edit' ? 'select' : 'edit'));\n    const bR = document.createElement('button'); bR.className = 'btn'; bR.textContent = 'Reset this street';")
# ---- drawing: streets with widths between points; the picked stretch
rep("function drawHandles(f) {\n  const v = vertsOf(f), K = ctrlOf(f), d = S.drag;\n  ctx.save();",
    "function drawHandles(f) {\n  const v = vertsOf(f), K = ctrlOf(f), d = S.drag, rg = rngOf(f);\n  ctx.save();\n"
    "  if (rg && rg.b !== null) { ctx.globalAlpha = 0.35; ctx.strokeStyle = C.accent; ctx.lineWidth = 10; ctx.lineCap = 'round'; ctx.beginPath(); pathLine(subLine(f, Math.min(rg.a, rg.b), Math.max(rg.a, rg.b))); ctx.stroke(); ctx.globalAlpha = 1; ctx.lineCap = 'butt'; }")
rep("  v.forEach((q, i) => { const [x, y] = W2S(q[0], q[1]); ctx.fillStyle = (d && d.mode === 'v' && d.vi === i) ? C.accent : C.panel;",
    "  v.forEach((q, i) => { const [x, y] = W2S(q[0], q[1]); ctx.fillStyle = (d && d.mode === 'v' && d.vi === i) || (rg && (rg.a === i || rg.b === i)) ? C.accent : C.panel;")
rep("function drawGhost(x, y, col) {", r"""function strokeStreet(f, c, wpx) {   // one width, or each run at its own width with a disc where the width changes
  const r = streetRuns(f);
  if (!r) { ctx.lineWidth = wpx(streetWidth(f)); ctx.beginPath(); pathLine(c); ctx.stroke(); return; }
  for (const x of r) { ctx.lineWidth = wpx(x.w); ctx.beginPath(); pathLine(x.c); ctx.stroke(); }
  const fs = ctx.fillStyle; ctx.fillStyle = ctx.strokeStyle; for (let i = 1; i < r.length; i++) { const q = r[i].c[0], [x, y] = W2S(q[0], q[1]); ctx.beginPath(); ctx.arc(x, y, wpx(Math.min(r[i - 1].w, r[i].w)) / 2, 0, 7); ctx.fill(); } ctx.fillStyle = fs;
}
function drawGhost(x, y, col) {""")
rep("      if (pass === 0) { ctx.strokeStyle = C.ink; ctx.globalAlpha = al ? 0.35 : 0.55; ctx.lineWidth = wb + (al ? 1 : 1.5); }\n      else { ctx.globalAlpha = 1; ctx.strokeStyle = C.bst; ctx.lineWidth = wb; }\n      ctx.beginPath(); pathLine(c); ctx.stroke();",
    "      if (pass === 0) { ctx.strokeStyle = C.ink; ctx.globalAlpha = al ? 0.35 : 0.55; }\n      else { ctx.globalAlpha = 1; ctx.strokeStyle = C.bst; }\n      strokeStreet(f, c, m => Math.max(al ? 0.8 : 1.2, m * v.s) + (pass === 0 ? (al ? 1 : 1.5) : 0)); void wb;")
rep("    ctx.strokeStyle = C.ink; ctx.globalAlpha = 0.55; ctx.lineWidth = w + 1.5; ctx.beginPath(); pathLine(c); ctx.stroke();\n    ctx.globalAlpha = 1; ctx.strokeStyle = (k === 'through' || k === 'radial') ? C.thru : C.tee; ctx.lineWidth = w; ctx.beginPath(); pathLine(c); ctx.stroke();",
    "    ctx.strokeStyle = C.ink; ctx.globalAlpha = 0.55; strokeStreet(f, c, m => Math.max(1.2, m * v.s) + 1.5);\n    ctx.globalAlpha = 1; ctx.strokeStyle = (k === 'through' || k === 'radial') ? C.thru : C.tee; strokeStreet(f, c, m => Math.max(1.2, m * v.s));")
rep("    if (p.layer === 'street') { g = { type: 'LineString', coordinates: streetCoords(f) }; p.width_m = streetWidth(f);",
    "    if (p.layer === 'street') { g = { type: 'LineString', coordinates: streetCoords(f) }; p.width_m = streetWidth(f); if (streetRuns(f)) p.widths_m = streetRuns(f).map(x => x.w);")
# ---- filled blocks
rep("sub.textContent = (isWE(f) ? 'Basin · 1904 Sanborn · ' : p.side === 'WV' ? 'West side of the valley, off the deck · ' : p.side === 'new' ? 'New block on open land · ' : 'On the deck · ')",
    "sub.textContent = (p.side === 'fill' ? 'Filled block (17 October): land between streets that had no block; one lot · ' : isWE(f) ? 'Basin · 1904 Sanborn · ' : p.side === 'WV' ? 'West side of the valley, off the deck · ' : p.side === 'new' ? 'New block on open land · ' : 'On the deck · ')")
rep("    if (p.gen && p.gen !== p.id) kv('Part of', 'Block ' + p.gen + ', cut by a street');",
    "    if (p.gen && p.gen !== p.id) kv('Part of', 'Block ' + p.gen + ', cut by a street');\n"
    "    if (p.joined17 && p.joined17.length) kv('Joined', 'with ' + p.joined17.join(', ') + ' across the deck edge (17 October)');\n"
    "    if (p.extended17) kv('Extended', 'by ' + fmt(p.extended17) + ' m² of land it stopped short of (17 October)');")
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v43', len(src))
