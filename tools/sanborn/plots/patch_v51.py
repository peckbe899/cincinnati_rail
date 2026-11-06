try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 51 (Ben, 17 October): a stretch of street narrower than the road either side can sit anywhere within the wider road's width
# (shifted sideways, no S-bend or kink): edits.streets[id].ov, one sideways offset per segment (m, + to the left looking along the line).
# Chain: ... patch_v48.py && patch_v51.py. Also applied to plots/engine.js.
import sys
SP = _ws.DATA
def patch(path, reps):
    src = open(path).read()
    for old, new in reps:
        c = src.count(old)
        if c != 1: sys.exit('%s: count %d for: %s' % (path, c, old[:100]))
        src = src.replace(old, new)
    open(path, 'w').write(src)
OLD_RUNS = """function streetRuns(f) {   // runs of one width along a street with widths set between points (17 October): [{c, w}], or null
  const wv = streetWv(f); if (!wv) return null; const v = vertsOf(f), K = ctrlOf(f) || {}, w0 = streetWidth(f), out = [];
  for (let i = 0; i < v.length - 1; i++) { const w = wv[i] || w0, seg = K[i] ? curveCoords([v[i], v[i + 1]], { 0: K[i] }) : [v[i], v[i + 1]], last = out[out.length - 1];
    if (last && Math.abs(last.w - w) < 0.01) last.c.push(...seg.slice(1)); else out.push({ c: seg.slice(), w }); }
  return out.length > 1 || Math.abs(out[0].w - w0) > 0.01 ? out : null;
}"""
NEW_RUNS = """function streetOv(f) { const e = S.edits.streets[f.properties.id]; if (!e || !e.ov) return null; return e.ov.length === vertsOf(f).length - 1 && e.ov.some(x => x) ? e.ov : null; }
function offLine(c, o) {   // the line moved o metres sideways (+ to the left), mitred at the bends
  if (!o || c.length < 2) return c; const n = c.length, nr = [];
  for (let i = 0; i < n - 1; i++) { const dx = c[i + 1][0] - c[i][0], dy = c[i + 1][1] - c[i][1], L = Math.hypot(dx, dy) || 1; nr.push([-dy / L, dx / L]); }
  return c.map((q, i) => { const a = nr[Math.max(0, i - 1)], b = nr[Math.min(n - 2, i)], mx = a[0] + b[0], my = a[1] + b[1], L = Math.hypot(mx, my) || 1, m = [mx / L, my / L], k = Math.max(0.3, m[0] * a[0] + m[1] * a[1]);
    return [q[0] + m[0] * o / k, q[1] + m[1] * o / k]; });
}
function streetRuns(f) {   // runs of one width (and sideways offset) along a street with widths or offsets set between points (17 October): [{c, w, o, oc}], or null
  const wv = streetWv(f), ov = streetOv(f); if (!wv && !ov) return null; const v = vertsOf(f), K = ctrlOf(f) || {}, w0 = streetWidth(f), out = [];
  for (let i = 0; i < v.length - 1; i++) { const w = (wv && wv[i]) || w0, o = (ov && ov[i]) || 0, seg = K[i] ? curveCoords([v[i], v[i + 1]], { 0: K[i] }) : [v[i], v[i + 1]], last = out[out.length - 1];
    if (last && Math.abs(last.w - w) < 0.01 && Math.abs(last.o - o) < 0.01) last.c.push(...seg.slice(1)); else out.push({ c: seg.slice(), w, o }); }
  for (const r of out) r.oc = offLine(r.c, r.o);
  return out.length > 1 || Math.abs(out[0].w - w0) > 0.01 || Math.abs(out[0].o) > 0.01 ? out : null;
}
function runJoint(a, b) { return a.w <= b.w ? a.oc[a.oc.length - 1] : b.oc[0]; }   // where two runs meet: the narrower one's end (it lies inside the wider one)"""
OLD_CR = """  const gs = runs.map(r => corridor(r.c, r.w, basin));
  for (let i = 1; i < runs.length; i++) { const q = runs[i].c[0]; gs.push(jline([q, [q[0] + 0.01, q[1]]]).buffer(Math.min(runs[i - 1].w, runs[i].w) / 2, 8)); }"""
NEW_CR = """  const gs = runs.map(r => corridor(r.oc || r.c, r.w, basin));
  for (let i = 1; i < runs.length; i++) { const q = runJoint(runs[i - 1], runs[i]); gs.push(jline([q, [q[0] + 0.01, q[1]]]).buffer(Math.min(runs[i - 1].w, runs[i].w) / 2, 8)); }"""
OLD_KEY = "(runs ? ':' + runs.map(r => r.w + '/' + r.c.length).join(',') : '')"
NEW_KEY = "(runs ? ':' + runs.map(r => r.w + '/' + (r.o || 0) + '/' + r.c.length).join(',') : '')"
for path in (SP + 'deckpage/index.html', _ws.CODE + 'plots/engine.js'):
    src = open(path).read()
    reps = [(OLD_RUNS, NEW_RUNS), (OLD_CR, NEW_CR)]
    if OLD_KEY in src: reps.append((OLD_KEY, NEW_KEY))
    patch(path, reps)
patch(SP + 'deckpage/index.html', [
 ("  for (const x of r) { ctx.lineWidth = wpx(x.w); ctx.beginPath(); pathLine(x.c); ctx.stroke(); }\n  const fs = ctx.fillStyle; ctx.fillStyle = ctx.strokeStyle; for (let i = 1; i < r.length; i++) { const q = r[i].c[0], [x, y] = W2S(q[0], q[1]);",
  "  for (const x of r) { ctx.lineWidth = wpx(x.w); ctx.beginPath(); pathLine(x.oc || x.c); ctx.stroke(); }\n  const fs = ctx.fillStyle; ctx.fillStyle = ctx.strokeStyle; for (let i = 1; i < r.length; i++) { const q = runJoint(r[i - 1], r[i]), [x, y] = W2S(q[0], q[1]);"),
 ("if (kind === 'streets' && old && old.wv && patch.c && !('wv' in patch) && patch.c.length !== vertsOf(f).length) patch = Object.assign({}, patch, { wv: remapWv(vertsOf(f), ctrlOf(f) || {}, old.wv, patch.c, patch.k || {}) }); }",
  "if (kind === 'streets' && old && old.wv && patch.c && !('wv' in patch) && patch.c.length !== vertsOf(f).length) patch = Object.assign({}, patch, { wv: remapWv(vertsOf(f), ctrlOf(f) || {}, old.wv, patch.c, patch.k || {}) });\n    if (kind === 'streets' && old && old.ov && patch.c && !('ov' in patch) && patch.c.length !== vertsOf(f).length) patch = Object.assign({}, patch, { ov: remapWv(vertsOf(f), ctrlOf(f) || {}, old.ov, patch.c, patch.k || {}) }); }"),
 ("function filletRange(f, i, j, Rq) {",
  """function shiftLimits(f, i, j) {   // how far the stretch i-j may move sideways and stay inside the wider road on either side: [lo, hi] or null
  const n = vertsOf(f).length - 1, wv = streetWv(f), ov = streetOv(f), w0 = streetWidth(f), W = s => (wv && wv[s]) || w0, O = s => (ov && ov[s]) || 0, ws = W(i);
  let lo = -1e9, hi = 1e9, any = false;
  for (const s of [i - 1, j]) { if (s < 0 || s >= n) continue; any = true; const room = (W(s) - ws) / 2; if (room < 0.05) return { none: true }; lo = Math.max(lo, O(s) - room); hi = Math.min(hi, O(s) + room); }
  return any && lo <= hi + 1e-6 ? { lo, hi } : { none: true };
}
function setShiftRange(f, i, j, o) {
  const n = vertsOf(f).length - 1, e = S.edits.streets[f.properties.id], ov = e && e.ov && e.ov.length === n ? e.ov.slice() : new Array(n).fill(null);
  for (let s = i; s < j; s++) ov[s] = Math.abs(o) < 0.01 ? null : Math.round(o * 100) / 100;
  setEdit(f, { ov: ov.some(x => x) ? ov : undefined });
}
function filletRange(f, i, j, Rq) {"""),
 ("""    const b = document.createElement('button'); b.className = 'btn'; b.textContent = 'Set for this stretch'; b.disabled = !S.canWrite; b.addEventListener('click', () => { const w = parseFloat(inp.value); if (!(w >= 2 && w <= 80)) return; setWidthRange(f, i, j, w); renderSel(); }); row.append(b); }""",
  """    const b = document.createElement('button'); b.className = 'btn'; b.textContent = 'Set for this stretch'; b.disabled = !S.canWrite; b.addEventListener('click', () => { const w = parseFloat(inp.value); if (!(w >= 2 && w <= 80)) return; setWidthRange(f, i, j, w); renderSel(); }); row.append(b);
    // sideways position inside the wider road on either side
    const lim = shiftLimits(f, i, j), ov = streetOv(f), o0 = (ov && ov[i]) || 0, hs = document.createElement('p'); hs.className = 'notes'; hs.style.marginTop = '8px'; box.append(hs);
    if (lim.none) hs.textContent = 'Sideways position: give this stretch a narrower width than the road next to it, and it can then sit anywhere inside that road\\u2019s width (no S-bend).';
    else { const lo = Math.max(lim.lo, -40), hi = Math.min(lim.hi, 40);
      hs.textContent = 'Sideways position inside the wider road: ' + fmt(lo, 1) + ' to ' + fmt(hi, 1) + ' m from the line (+ is to the left looking from point ' + (i + 1) + ' to point ' + (j + 1) + '). Now ' + fmt(o0, 1) + ' m.';
      const rowS = document.createElement('div'); rowS.className = 'row'; const sl = document.createElement('input'); sl.type = 'range'; sl.min = lo; sl.max = hi; sl.step = '0.1'; sl.value = Math.min(hi, Math.max(lo, o0)); sl.style.flex = '1'; sl.disabled = !S.canWrite;
      const nv = document.createElement('input'); nv.type = 'number'; nv.step = '0.1'; nv.style.width = '70px'; nv.value = (+sl.value).toFixed(1); nv.disabled = !S.canWrite;
      sl.addEventListener('input', () => { nv.value = (+sl.value).toFixed(1); }); sl.addEventListener('change', () => { setShiftRange(f, i, j, +sl.value); renderSel(); });
      nv.addEventListener('change', () => { const o = Math.min(hi, Math.max(lo, parseFloat(nv.value) || 0)); setShiftRange(f, i, j, o); renderSel(); });
      rowS.append(sl, nv); box.append(rowS);
      const rowB = document.createElement('div'); rowB.className = 'row';
      for (const [lab, o] of [['Left edge', hi], ['Centre', Math.min(hi, Math.max(lo, 0))], ['Right edge', lo]]) { const bb = document.createElement('button'); bb.className = 'btn'; bb.textContent = lab; bb.disabled = !S.canWrite; bb.addEventListener('click', () => { setShiftRange(f, i, j, o); renderSel(); }); rowB.append(bb); }
      box.append(rowB); } }"""),
 ("(rr ? '; between points: ' + rr.map(x => fmt(x.w, 1)).join(', ') + ' m along it' : '')",
  "(rr ? '; between points: ' + rr.map(x => fmt(x.w, 1) + (Math.abs(x.o) > 0.01 ? ' (shifted ' + fmt(x.o, 1) + ')' : '')).join(', ') + ' m along it' : '')"),
 ("if (streetRuns(f)) p.widths_m = streetRuns(f).map(x => x.w);", "if (streetRuns(f)) { p.widths_m = streetRuns(f).map(x => x.w); p.offsets_m = streetRuns(f).map(x => x.o); }"),
])
print('ok v51')
