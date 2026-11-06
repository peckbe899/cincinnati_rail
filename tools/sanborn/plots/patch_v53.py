try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 53 (Ben, 17 October): not a stretch moved to a side, but a slider at the point where a narrower street meets a wider one
# (e.g. point 106 of Central Parkway): the narrower side's end can sit anywhere across the wider side's end, edge to edge, and only the
# narrower side's last segment follows it. edits.streets[id].jo = {vertex index: offset m, + to the left looking along the line}.
# The v51/v52 stretch controls (Sits on, sideways slider) are taken out of the panel. Chain: ... patch_v52.py && patch_v53.py (also engine.js).
import sys, re
SP = _ws.DATA
def patch(path, reps):
    src = open(path).read()
    for old, new in reps:
        c = src.count(old)
        if c != 1: sys.exit('%s: count %d for: %s' % (path, c, old[:100]))
        src = src.replace(old, new)
    open(path, 'w').write(src)
OLD = """function streetRuns(f) {   // runs of one width (and sideways offset) along a street with widths or offsets set between points (17 October): [{c, w, o, oc}], or null
  const wv = streetWv(f), ov = streetOv(f); if (!wv && !ov) return null; const v = vertsOf(f), K = ctrlOf(f) || {}, w0 = streetWidth(f), out = [];
  for (let i = 0; i < v.length - 1; i++) { const w = (wv && wv[i]) || w0, o = (ov && ov[i]) || 0, seg = K[i] ? curveCoords([v[i], v[i + 1]], { 0: K[i] }) : [v[i], v[i + 1]], last = out[out.length - 1];
    if (last && Math.abs(last.w - w) < 0.01 && Math.abs(last.o - o) < 0.01) last.c.push(...seg.slice(1)); else out.push({ c: seg.slice(), w, o }); }
  for (const r of out) r.oc = offLine(r.c, r.o);
  return out.length > 1 || Math.abs(out[0].w - w0) > 0.01 || Math.abs(out[0].o) > 0.01 ? out : null;
}"""
NEW = """function streetJo(f) {   // where a narrower side meets a wider one: {vertex: offset}, with a live preview while the slider moves
  const e = S.edits.streets[f.properties.id], jo = Object.assign({}, (e && e.jo) || {}), p = S.joPrev;
  if (p && p.id === f.properties.id) jo[p.k] = p.o; return Object.keys(jo).length ? jo : null;
}
function joInfo(f, k) {   // the two segments meeting at point k: which is narrower, how far it may move, and the wider one's left normal
  const v = vertsOf(f), n = v.length - 1; if (k <= 0 || k >= n) return null; const wv = streetWv(f), w0 = streetWidth(f), wa = (wv && wv[k - 1]) || w0, wb = (wv && wv[k]) || w0;
  if (Math.abs(wa - wb) < 0.05) return null; const narrowBefore = wa < wb, wide = narrowBefore ? k : k - 1, p0 = v[wide], p1 = v[wide + 1], L = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) || 1;
  return { narrowBefore, room: Math.abs(wa - wb) / 2, nrm: [-(p1[1] - p0[1]) / L, (p1[0] - p0[0]) / L], wn: Math.min(wa, wb), ww: Math.max(wa, wb) };
}
function streetRuns(f) {   // runs of one width (sideways offset, shifted joints) along a street with widths set between points (17 October): [{c, w, o, oc}], or null
  const wv = streetWv(f), ov = streetOv(f), jo = streetJo(f); if (!wv && !ov && !jo) return null; const v = vertsOf(f), K = ctrlOf(f) || {}, w0 = streetWidth(f), out = [];
  // a shifted joint turns the narrower side's last straight about its far end, so the straight stays straight (no kink at points on it)
  const sh = {}, jv = {};
  for (const [ks, o0] of Object.entries(jo || {})) { const k = +ks, J = joInfo(f, k); if (!J || !o0) continue; const o = Math.max(-J.room, Math.min(J.room, o0)), dir = J.narrowBefore ? -1 : 1; jv[k] = J.narrowBefore ? k - 1 : k;
    const t0 = Math.atan2(v[k][1] - v[k + dir][1], v[k][0] - v[k + dir][0]);
    let m = k + dir; while (m + dir >= 0 && m + dir <= v.length - 1 && !K[Math.min(m, m + dir)] && !K[Math.min(k, k + dir)]) { const a = v[m + dir], b = v[m], t1 = Math.atan2(b[1] - a[1], b[0] - a[0]); if (Math.abs(Math.atan2(Math.sin(t1 - t0), Math.cos(t1 - t0))) > 0.05) break; m += dir; }
    const D = Math.hypot(v[k][0] - v[m][0], v[k][1] - v[m][1]) || 1;
    for (let t = m; t !== k - dir; t -= dir) { if (t === m) continue; const fr = Math.hypot(v[t][0] - v[m][0], v[t][1] - v[m][1]) / D; sh[t] = [J.nrm[0] * o * fr, J.nrm[1] * o * fr]; } }
  const end = (i, k) => { const d = sh[k]; if (!d) return v[k]; if (k in jv && jv[k] !== i) return v[k]; return [v[k][0] + d[0], v[k][1] + d[1]]; };
  for (let i = 0; i < v.length - 1; i++) { const w = (wv && wv[i]) || w0, o = (ov && ov[i]) || 0, a = end(i, i), b = end(i, i + 1), moved = a !== v[i] || b !== v[i + 1];
    const seg = K[i] && !moved ? curveCoords([v[i], v[i + 1]], { 0: K[i] }) : K[i] ? curveCoords([a, b], { 0: [K[i][0] + (a[0] - v[i][0] + b[0] - v[i + 1][0]) / 2, K[i][1] + (a[1] - v[i][1] + b[1] - v[i + 1][1]) / 2] }) : [a, b], last = out[out.length - 1];
    const join = last && Math.abs(last.w - w) < 0.01 && Math.abs(last.o - o) < 0.01 && Math.hypot(last.c[last.c.length - 1][0] - seg[0][0], last.c[last.c.length - 1][1] - seg[0][1]) < 0.01;
    if (join) last.c.push(...seg.slice(1)); else out.push({ c: seg.slice(), w, o }); }
  for (const r of out) r.oc = offLine(r.c, r.o);
  return out.length > 1 || Math.abs(out[0].w - w0) > 0.01 || Math.abs(out[0].o) > 0.01 ? out : null;
}"""
OLD_KEY = "(runs ? ':' + runs.map(r => r.w + '/' + (r.o || 0) + '/' + r.c.length).join(',') : '')"
NEW_KEY = "(runs ? ':' + runs.map(r => r.w + '/' + (r.o || 0) + '/' + r.c.length + '/' + r.c[0][0].toFixed(2) + ',' + r.c[0][1].toFixed(2) + '/' + r.c[r.c.length - 1][0].toFixed(2)).join(',') : '')"
for path in (SP + 'deckpage/index.html', _ws.CODE + 'plots/engine.js'):
    src = open(path).read(); reps = [(OLD, NEW)]
    if OLD_KEY in src: reps.append((OLD_KEY, NEW_KEY))
    patch(path, reps)
src = open(SP + 'deckpage/index.html').read()
# panel: the stretch box back to width + curve; the point slider when one point is picked
a = src.index("    const rowA = document.createElement('div'); rowA.className = 'row'; const la = document.createElement('label'); la.htmlFor = 'rgA';")
b = src.index("      box.append(rowB); } }") + len("      box.append(rowB); } }")
src = src[:a] + """    const b = document.createElement('button'); b.className = 'btn'; b.textContent = 'Set for this stretch'; b.disabled = !S.canWrite; b.addEventListener('click', () => { const w = parseFloat(inp.value); if (!(w >= 2 && w <= 80)) return; setWidthRange(f, i, j, w); renderSel(); }); row.append(b); }""" + src[b:]
old_pick = "  if (!r || r.b === null) { n.textContent = S.tool !== 'edit' ? 'In Edit mode, click a point and then another to pick the stretch between them: ' + (street ? 'give it its own width, or ' : '') + 'make it one constant-radius curve.' : r ? 'Point ' + (r.a + 1) + ' picked. Click another point to pick the stretch between them (click the same point again to drop it).' : 'Click a point, then another point, to pick the stretch between them.'; return; }"
assert src.count(old_pick) == 1
src = src.replace(old_pick, old_pick[:-len(' return; }')] + """
    if (r && street) joBox(f, r.a, box);
    return; }""")
src = src.replace("function setShiftRange(f, i, j, o) {", """function joBox(f, k, box) {   // the slider at a point where the street changes width
  const J = joInfo(f, k), p = document.createElement('p'); p.className = 'notes'; p.style.marginTop = '6px'; box.append(p);
  if (!J) { p.textContent = 'Where the street changes width at a point, that point gets a slider here: the narrower side can meet the wider side anywhere across its width.'; return; }
  const e = S.edits.streets[f.properties.id], o0 = (e && e.jo && e.jo[k]) || 0, side = J.narrowBefore ? 'before it (points ' + k + ' and back)' : 'after it (points ' + (k + 2) + ' on)';
  p.textContent = 'Where the ' + fmt(J.wn, 1) + ' m street ' + side + ' meets the ' + fmt(J.ww, 1) + ' m street: slide its end across the wider street\\u2019s end, edge to edge. Only its last segment follows; the wider street does not move.';
  const row = document.createElement('div'); row.className = 'row'; const L1 = document.createElement('span'); L1.className = 'notes'; L1.textContent = 'right edge';
  const sl = document.createElement('input'); sl.type = 'range'; sl.min = -J.room; sl.max = J.room; sl.step = '0.1'; sl.value = Math.max(-J.room, Math.min(J.room, o0)); sl.style.flex = '1'; sl.disabled = !S.canWrite;
  const L2 = document.createElement('span'); L2.className = 'notes'; L2.textContent = 'left edge';
  const val = document.createElement('p'); val.className = 'notes'; const show = o => { val.textContent = Math.abs(o) < 0.05 ? 'Centred.' : fmt(Math.abs(o), 1) + ' m to the ' + (o > 0 ? 'left' : 'right') + ' of centre (looking from point 1 toward the end of the street), ' + fmt(J.room - Math.abs(o), 1) + ' m short of the edge.'; };
  show(+sl.value);
  sl.addEventListener('input', () => { S.joPrev = { id: f.properties.id, k, o: +sl.value }; show(+sl.value); redraw(); });
  sl.addEventListener('change', () => { S.joPrev = null; const ed = S.edits.streets[f.properties.id] || {}, jo = Object.assign({}, ed.jo || {}); if (Math.abs(+sl.value) < 0.05) delete jo[k]; else jo[k] = Math.round(+sl.value * 100) / 100; setEdit(f, { jo: Object.keys(jo).length ? jo : undefined }); renderSel(); });
  row.append(L1, sl, L2); box.append(row, val);
  const rb = document.createElement('div'); rb.className = 'row'; for (const [lab, o] of [['Right edge', -J.room], ['Centre', 0], ['Left edge', J.room]]) { const bb = document.createElement('button'); bb.className = 'btn'; bb.textContent = lab; bb.disabled = !S.canWrite; bb.addEventListener('click', () => { sl.value = o; sl.dispatchEvent(new Event('change')); }); rb.append(bb); } box.append(rb);
}
function setShiftRange(f, i, j, o) {""", 1)
# point indices shift when points are added or removed: carry the shifted joints by position
src = src.replace("    if (kind === 'streets' && old && old.ov && patch.c && !('ov' in patch) && patch.c.length !== vertsOf(f).length) patch = Object.assign({}, patch, { ov: remapWv(vertsOf(f), ctrlOf(f) || {}, old.ov, patch.c, patch.k || {}) }); }",
"""    if (kind === 'streets' && old && old.ov && patch.c && !('ov' in patch) && patch.c.length !== vertsOf(f).length) patch = Object.assign({}, patch, { ov: remapWv(vertsOf(f), ctrlOf(f) || {}, old.ov, patch.c, patch.k || {}) });
    if (kind === 'streets' && old && old.jo && patch.c && !('jo' in patch)) { const ovs = vertsOf(f), nj = {}; for (const [k, o] of Object.entries(old.jo)) { const q = ovs[+k]; if (!q) continue; let bi = -1, bd = 3; patch.c.forEach((p, i) => { const d = Math.hypot(p[0] - q[0], p[1] - q[1]); if (d < bd) { bd = d; bi = i; } }); if (bi > 0) nj[bi] = o; } patch = Object.assign({}, patch, { jo: Object.keys(nj).length ? nj : undefined }); } }""", 1)
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v53')
