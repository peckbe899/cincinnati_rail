// ---------------------------------------------------------------- plots and land use (15 October)
// Every block is divided into plots (plots.json: lot widths measured on each block face of the 1904 sheets, cuts snapped to the
// sheet's lot lines, the deck at the same density). The plots follow the streets live: a street moved, widened or lengthened since
// the layers were generated cuts the plots under its new corridor (a plot cut in two becomes two), and the land its old corridor
// leaves goes to the plots that front it, out to the old centre line, so blocks stretch and join. Land no plot fronts is left open,
// to be added to a plot, made a plot or divided into lots. Splits, merges, divisions and fills are kept in order in edits.plotOps
// and replayed on top; uses and names sit in edits.plots (by plot id; a piece falls back to its parent, X~a and X.2 to X) and in
// edits.blocks[id].u (every plot of the block). A use is the plot's own, else the block's, else the sheet's label, else the block type's.
const USES = [['r', 'Residential'], ['m', 'Mixed use'], ['c', 'Commercial'], ['i', 'Industrial'], ['w', 'Religious'], ['v', 'Civic'], ['p', 'Parking'], ['o', 'Open or vacant']];
const UNAME = Object.assign(Object.fromEntries(USES), { '': 'Not set' });
const TYPE_USE = { worship: 'w', civic: 'v', school: 'v', hospital: 'v', industrial: 'i', square: 'o', park: 'o', planting: 'o' };
const USRC = { plot: 'set for this plot', parent: 'set before the plot was divided', block: 'set for the whole block', sheet: 'read from the 1904 sheet', type: 'from the block type' };
const PZ = 1.1, TS = 60;   // plots are drawn from 1.1 px per metre; street corridors are cut into 60 m tiles
const OPEN_LAYERS = new Set(['boulevard', 'roundabout', 'forecourt', 'cut_square', 'we_forecourt', 'cut_park', 'cut_precinct', 'palace', 'cut_headhouse', 'cut_building', 'rail_open', 'dive_cut']);
let J = null, GF = null;
function jready() { if (J) return true; if (window.jsts && window.jsts.geom) { J = window.jsts; GF = new J.geom.GeometryFactory(new J.geom.PrecisionModel()); return true; } return false; }
function ov(a, b, kind) {   // overlay with fallbacks: as is, cleaned, then on a 1 mm grid; never throws
  try { return a[kind](b); } catch (e) { /* retry */ }
  try { return a.buffer(0)[kind](b.buffer(0)); } catch (e) { /* retry */ }
  try { const R = J.precision.GeometryPrecisionReducer, pm = new J.geom.PrecisionModel(1000); return R.reduce(a, pm)[kind](R.reduce(b, pm)); } catch (e) { /* retry */ }
  try { return J.precision.EnhancedPrecisionOp[kind](a, b); } catch (e) { console.warn('overlay failed', kind); }
  return kind === 'intersection' ? GF.createGeometryCollection([]) : a;
}
function hit(a, b) { try { return a.intersects(b); } catch (e) { return true; } }
function uunion(gs) { try { return J.operation.union.UnaryUnionOp.union(GF.createGeometryCollection(gs)); } catch (e) { let g = gs[0]; for (const h of gs.slice(1)) g = ov(g, h, 'union'); return g; } }
const jc = q => new J.geom.Coordinate(Math.round(q[0] * 100) / 100, Math.round(q[1] * 100) / 100);
function jring(r) { const cs = r.map(jc), a = cs[0], b = cs[cs.length - 1]; if (a.x !== b.x || a.y !== b.y) cs.push(new J.geom.Coordinate(a.x, a.y)); return GF.createLinearRing(cs); }
function jpoly(rings) { return GF.createPolygon(jring(rings[0]), rings.slice(1).map(jring)); }
function jgeom(g) { const ps = polysOf(g).map(jpoly); return ps.length === 1 ? ps[0] : GF.createMultiPolygon(ps); }
function jOf(pf) { return pf._j || (pf._j = jpoly(pf.geometry.coordinates)); }
function jline(c) { return GF.createLineString(c.map(jc)); }
const jbox = (x0, y0, x1, y1) => GF.toGeometry(new J.geom.Envelope(x0, x1, y0, y1));
function ringC(lr) { const cs = lr.getCoordinates(), out = []; for (let i = 0; i < cs.length - 1; i++) out.push([cs[i].x, cs[i].y]); return out; }
function partsJ(g, minA = 2) {   // polygons of a JSTS result, largest first, slivers and pinholes dropped
  const out = [], walk = h => { const n = h.getNumGeometries(); if (h.getGeometryType() === 'Polygon') { if (!h.isEmpty() && h.getArea() >= minA) out.push(h); return; } for (let i = 0; i < n; i++) walk(h.getGeometryN(i)); };
  walk(g); out.sort((a, b) => b.getArea() - a.getArea());
  return out.map(p => { const rr = [ringC(p.getExteriorRing())]; for (let k = 0; k < p.getNumInteriorRing(); k++) { const r = ringC(p.getInteriorRingN(k)); if (ringArea(r) >= 0.5) rr.push(r); } return { rings: rr, j: rr.length === p.getNumInteriorRing() + 1 ? p : jpoly(rr) }; });
}
function bbOf(r) { let x0 = 1e18, y0 = 1e18, x1 = -1e18, y1 = -1e18; for (const q of r) { if (q[0] < x0) x0 = q[0]; if (q[0] > x1) x1 = q[0]; if (q[1] < y0) y0 = q[1]; if (q[1] > y1) y1 = q[1]; } return [x0, y0, x1, y1]; }
const bbHit = (a, b, m = 0) => a[0] - m <= b[2] && b[0] - m <= a[2] && a[1] - m <= b[3] && b[1] - m <= a[3];
const grow = (b, m) => [b[0] - m, b[1] - m, b[2] + m, b[3] + m];
function nearestOn(c, p) { let best = 1e18, bx = 0, by = 0; for (let i = 1; i < c.length; i++) { const a = c[i - 1], b = c[i], dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy || 1e-12; let t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2; t = t < 0 ? 0 : t > 1 ? 1 : t; const x = a[0] + t * dx, y = a[1] + t * dy, d = Math.hypot(p[0] - x, p[1] - y); if (d < best) { best = d; bx = x; by = y; } } return [bx, by, best]; }
function ringsArea(rr) { let a = ringArea(rr[0]); for (let k = 1; k < rr.length; k++) a -= ringArea(rr[k]); return a; }
function mkPlot(id, block, rings, props, j) {
  const pf = { type: 'Feature', properties: Object.assign({}, props, { layer: 'plot', id, block }), geometry: { type: 'Polygon', coordinates: rings }, bb: bbOf(rings[0]), area: ringsArea(rings), adds: null, st: id };
  if (j) pf._j = j; return pf;
}
const plotProps = p => ({ kind: p.kind, street: p.street, u0: p.u0, lab: p.lab, we: p.we });
function decodePlots(D) {
  const [E0, N0] = D.o, out = [];
  for (const [id, block, kind, street, u0, lab, rings] of D.plots) {
    const R = rings.map(a => { let x = a[0], y = a[1]; const pts = [[E0 + x / 10, N0 + y / 10]]; for (let i = 2; i < a.length; i += 2) { x += a[i]; y += a[i + 1]; pts.push([E0 + x / 10, N0 + y / 10]); } return pts; });
    const bf = S.blkById.get(block);
    out.push(mkPlot(id, block, R, { kind: { l: 'lot', i: 'interior', o: 'open' }[kind] || kind, street, u0, lab: lab.map(i => D.labels[i]), we: bf ? isWE(bf) : false }));
  }
  return out;
}
// ids: a piece cut off by a street is X~a, X~b (the largest piece keeps X); a split or division gives X.1, X.2 ...
const SUF = 'abcdefghijklmnopqrstuvwxyz';
function chainIds(id) { const out = [id]; let s = id; for (;;) { const m = /^(.*)[~.][a-z0-9]+$/.exec(s); if (!m) break; s = m[1]; out.push(s); } return out; }
function liveStreet(id) { let f = id && S.streetById.get(id), n = 0; while (f && n++ < 8) { const e = S.edits.streets[f.properties.id]; if (!e || !e.del || !e.into) break; f = S.streetById.get(e.into) || f; } return f || null; }   // a merged street answers for the pieces merged into it
function genCoords(f) { const k = f.properties.k; return k && Object.keys(k).length ? curveCoords(f.geometry.coordinates, k) : f.geometry.coordinates; }
function sameLine(a, b) { if (a.length !== b.length) return false; for (let i = 0; i < a.length; i++) if (Math.abs(a[i][0] - b[i][0]) > 0.01 || Math.abs(a[i][1] - b[i][1]) > 0.01) return false; return true; }
const isBasinSt = f => f.properties.kind === 'we_street' || f.properties.kind === 'we_alley';
function corridor(c, w, basin) {   // as the layers were built: flat ends; mitred bends in the basin, round on the deck
  const BP = J.operation.buffer.BufferParameters, bp = new BP(6, BP.CAP_FLAT, basin ? BP.JOIN_MITRE : BP.JOIN_ROUND, 3);
  return J.operation.buffer.BufferOp.bufferOp(jline(c), w / 2, bp);
}
function streetWv(f) { const e = S.edits.streets[f.properties.id]; if (!e || !e.wv) return null; return e.wv.length === vertsOf(f).length - 1 && e.wv.some(x => x) ? e.wv : null; }
function streetOv(f) { const e = S.edits.streets[f.properties.id]; if (!e || !e.ov) return null; return e.ov.length === vertsOf(f).length - 1 && e.ov.some(x => x) ? e.ov : null; }
function offLine(c, o) {   // the line moved o metres sideways (+ to the left), mitred at the bends
  if (!o || c.length < 2) return c; const n = c.length, nr = [];
  for (let i = 0; i < n - 1; i++) { const dx = c[i + 1][0] - c[i][0], dy = c[i + 1][1] - c[i][1], L = Math.hypot(dx, dy) || 1; nr.push([-dy / L, dx / L]); }
  return c.map((q, i) => { const a = nr[Math.max(0, i - 1)], b = nr[Math.min(n - 2, i)], mx = a[0] + b[0], my = a[1] + b[1], L = Math.hypot(mx, my) || 1, m = [mx / L, my / L], k = Math.max(0.3, m[0] * a[0] + m[1] * a[1]);
    return [q[0] + m[0] * o / k, q[1] + m[1] * o / k]; });
}
function streetJo(f) {   // where a narrower side meets a wider one: {vertex: offset}, with a live preview while the slider moves
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
}
function runJoint(a, b) { return a.w <= b.w ? a.oc[a.oc.length - 1] : b.oc[0]; }   // where two runs meet: the narrower one's end (it lies inside the wider one)
function streetWmax(f) { const r = streetRuns(f); return r ? Math.max(...r.map(x => x.w)) : streetWidth(f); }
function corridorRuns(runs, basin) {   // each run at its width; a disc at each change of width closes the notch on a bend
  const gs = runs.map(r => corridor(r.oc || r.c, r.w, basin));
  for (let i = 1; i < runs.length; i++) { const q = runJoint(runs[i - 1], runs[i]); gs.push(jline([q, [q[0] + 0.01, q[1]]]).buffer(Math.min(runs[i - 1].w, runs[i].w) / 2, 8)); }
  return uunion(gs);
}
const corrMemo = new Map();
function genCorr(f) { let g = corrMemo.get(f.properties.id); if (!g) { g = corridor(genCoords(f), f.properties.width_m, isBasinSt(f)); corrMemo.set(f.properties.id, g); } return g; }
function changedStreets() {
  const out = [];
  for (const id of Object.keys(S.edits.streets)) {
    const f = S.streetById.get(id); if (!f) continue;
    const gc = genCoords(f), w0 = f.properties.width_m;
    if (S.edits.streets[id].del) { out.push({ id, f, gc, cc: null, w0, w: 0, del: true, basin: isBasinSt(f), key: id + ':gone', bbN: [1e18, 1e18, -1e18, -1e18], bbO: grow(bbOf(gc), w0 / 2 + 1) }); continue; }   // merged into another street: its whole corridor is left
    const cc = streetCoords(f), runs = streetRuns(f), w = runs ? Math.max(...runs.map(r => r.w)) : streetWidth(f);
    if (!runs && Math.abs(w - w0) < 0.01 && sameLine(gc, cc)) continue;
    out.push({ id, f, gc, cc, w0, w, runs, basin: isBasinSt(f), key: id + ':' + w + (runs ? ':' + runs.map(r => r.w + '/' + (r.o || 0) + '/' + r.c.length + '/' + r.c[0][0].toFixed(2) + ',' + r.c[0][1].toFixed(2) + '/' + r.c[r.c.length - 1][0].toFixed(2)).join(',') : '') + ':' + cc.map(q => q[0].toFixed(2) + ',' + q[1].toFixed(2)).join(';'), bbN: grow(bbOf(cc), w / 2 + 1), bbO: grow(bbOf(gc), w0 / 2 + 1) });
  }
  return out;
}
function sig(g) {   // a short fingerprint of a geometry's coordinates (to 1 cm)
  const cs = g.getCoordinates(); let h1 = 0x811c9dc5, h2 = (0x01000193 ^ cs.length) >>> 0;
  for (const c of cs) { const x = Math.round(c.x * 100), y = Math.round(c.y * 100); h1 = Math.imul(h1 ^ x, 16777619) >>> 0; h1 = Math.imul(h1 ^ y, 16777619) >>> 0; h2 = Math.imul(h2 ^ (x * 31 + y), 2246822519) >>> 0; }
  return h1.toString(36) + h2.toString(36) + cs.length;
}
function tilesNear(c, h, g) {   // the parts of g in the 60 m tiles along line c
  const out = []; if (!g || g.isEmpty()) return out; const bb = bbOf(c), r = h + TS * 0.75;
  for (let tx = Math.floor((bb[0] - h) / TS); tx <= Math.floor((bb[2] + h) / TS); tx++) for (let ty = Math.floor((bb[1] - h) / TS); ty <= Math.floor((bb[3] + h) / TS); ty++) {
    if (lineDist([(tx + 0.5) * TS, (ty + 0.5) * TS], c) > r) continue;
    const q = ov(g, jbox(tx * TS, ty * TS, (tx + 1) * TS, (ty + 1) * TS), 'intersection'); if (q.isEmpty() || q.getArea() < 0.01) continue;
    const e = q.getEnvelopeInternal(); out.push({ tk: tx + ',' + ty, g: q, sig: sig(q), bb: [e.getMinX(), e.getMinY(), e.getMaxX(), e.getMaxY()] });
  }
  return out;
}
function sweep(r, j) {   // the strip between a plot's frontage on j's old corridor and its old centre line
  const h = j.w0 / 2, G = j.gc, quads = [], n = r.length, tol = 0.9;
  const cross = (p, q, a, b) => { const d = (x, y, z) => (y[0] - x[0]) * (z[1] - x[1]) - (y[1] - x[1]) * (z[0] - x[0]); return d(p, q, a) * d(p, q, b) < 0 && d(a, b, p) * d(a, b, q) < 0; };
  for (let i = 0; i < n; i++) {
    const a = r[i], b = r[(i + 1) % n], m = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 4));
    for (let k = 0; k < m; k++) {
      const p = [a[0] + (b[0] - a[0]) * k / m, a[1] + (b[1] - a[1]) * k / m], q = [a[0] + (b[0] - a[0]) * (k + 1) / m, a[1] + (b[1] - a[1]) * (k + 1) / m];
      const pp = nearestOn(G, p), qq = nearestOn(G, q); if (Math.abs(pp[2] - h) > tol || Math.abs(qq[2] - h) > tol) continue;
      const P2 = [pp[0], pp[1]], Q2 = [qq[0], qq[1]]; if (cross(q, Q2, P2, p) || ringArea([p, q, Q2, P2]) < 0.01) continue;
      quads.push(jpoly([[p, q, Q2, P2]]));
    }
  }
  if (!quads.length) return null;
  return uunion(quads);
}
function vacated(j, CS) {   // j's old corridor less every corridor and open area now over it
  let V = j.O; const cut = [];
  for (const k of CS) if (bbHit(j.bbO, k.bbN)) cut.push(k.N);
  for (const f of S.streets0) { if (f._chg || !bbHit(j.bbO, f._bb)) continue; const g = genCorr(f); if (hit(g, V)) cut.push(g); }
  for (const f of S.openFeats) if (bbHit(j.bbO, f._bb)) { const g = f._j || (f._j = jgeom(f.geometry)); if (hit(g, V)) cut.push(g); }
  for (const g of cut) { V = ov(V, g, 'difference'); if (V.isEmpty()) break; }
  if (!V.isEmpty()) { try { V = V.buffer(-0.3, 2).buffer(0.3, 2); } catch (e) { /* keep as is */ } }   // strips under 0.6 m (a street redrawn a few cm off) are not land
  return V;
}
const memo1 = new Map(), memoOps = new Map(), memoC = new Map(), distMemo = new Map();
function stage1(pf, hits) {   // cut by new corridors, stretched into vacated ones
  let g = jOf(pf), chg = false; const adds = [], claims = [];
  for (const h of hits) if (h.kind === 'N' && bbHit(pf.bb, h.bb) && hit(g, h.g)) {   // a cut thinner than 0.5 m is a street redrawn a few cm off: ignored
    const d = ov(g, h.g, 'difference'), rem = g.getArea() - d.getArea(); if (rem < 0.5) continue;
    if (rem < 40) { const x = ov(g, h.g, 'intersection'); try { if (x.buffer(-0.25, 2).isEmpty()) continue; } catch (e) { /* cut it */ } }
    g = d; chg = true; }
  const byJ = new Map(); for (const h of hits) if (h.kind === 'V' && bbHit(pf.bb, h.bb, 1)) { if (!byJ.has(h.j)) byJ.set(h.j, []); byJ.get(h.j).push(h); }
  for (const [j, hs] of byJ) { const Q = sweep(pf.geometry.coordinates[0], j); if (!Q) continue;
    for (const h of hs) { if (!hit(Q, h.g)) continue; const e = ov(Q, h.g, 'intersection'); if (e.isEmpty() || e.getArea() < 0.5) continue; adds.push(e); claims.push([h.tk, e]); } }
  if (adds.length) { const n0 = g.getNumGeometries(); for (const e of adds) g = ov(g, e, 'union'); if (g.getNumGeometries() > n0) g = g.buffer(0.03).buffer(-0.03); chg = true; }
  return chg ? { parts: partsJ(g), adds, claims } : null;
}
function frontDir(pf) {   // unit vector along the plot's street front: its street near it, else its longest side
  const r = pf.geometry.coordinates[0], c = r.reduce((a, q) => [a[0] + q[0] / r.length, a[1] + q[1] / r.length], [0, 0]);
  const sf = liveStreet(pf.properties.street);
  if (sf) { const L = streetCoords(sf); let bi = 1, bd = 1e18; for (let i = 1; i < L.length; i++) { const d = segDist(c, L[i - 1], L[i]); if (d < bd) { bd = d; bi = i; } } if (bd < 80) { const dx = L[bi][0] - L[bi - 1][0], dy = L[bi][1] - L[bi - 1][1], n = Math.hypot(dx, dy); if (n > 0.1) return [dx / n, dy / n]; } }
  let best = 0, u = [1, 0]; for (let i = 0; i < r.length; i++) { const a = r[i], b = r[(i + 1) % r.length], L = Math.hypot(b[0] - a[0], b[1] - a[1]); if (L > best) { best = L; u = [(b[0] - a[0]) / L, (b[1] - a[1]) / L]; } }
  return u;
}
function halfPlanes(g, p, q) {   // the parts of g left and right of the line through p and q
  const ux = q[0] - p[0], uy = q[1] - p[1], L = Math.hypot(ux, uy) || 1, e = g.getEnvelopeInternal(), R = 4 * Math.hypot(e.getWidth(), e.getHeight()) + 50, u = [ux / L, uy / L], v = [-u[1], u[0]];
  const A = [p[0] - u[0] * R, p[1] - u[1] * R], B = [p[0] + u[0] * R, p[1] + u[1] * R];
  const side = s => jpoly([[A, B, [B[0] + v[0] * R * s, B[1] + v[1] * R * s], [A[0] + v[0] * R * s, A[1] + v[1] * R * s]]]);
  return [ov(g, side(1), 'intersection'), ov(g, side(-1), 'intersection')];
}
function strips(g, u, n) {   // n strips side by side along u (cuts square to u)
  const cs = g.getCoordinates(), v = [-u[1], u[0]]; let t0 = 1e18, t1 = -1e18, s0 = 1e18, s1 = -1e18;
  for (const c of cs) { const t = c.x * u[0] + c.y * u[1], s = c.x * v[0] + c.y * v[1]; t0 = Math.min(t0, t); t1 = Math.max(t1, t); s0 = Math.min(s0, s); s1 = Math.max(s1, s); }
  s0 -= 1; s1 += 1; const out = [], P = (t, s) => [u[0] * t + v[0] * s, u[1] * t + v[1] * s];
  for (let i = 0; i < n; i++) { const a = t0 + (t1 - t0) * i / n - (i ? 0 : 1), b = t0 + (t1 - t0) * (i + 1) / n + (i === n - 1 ? 1 : 0); out.push(ov(g, jpoly([[P(a, s0), P(b, s0), P(b, s1), P(a, s1)]]), 'intersection')); }
  return out;
}
function uvBand(g, u, v, a, b) {   // the strip a..b across v, long enough to cover g along u
  let t0 = 1e18, t1 = -1e18; for (const c of g.getCoordinates()) { const t = c.x * u[0] + c.y * u[1]; t0 = Math.min(t0, t); t1 = Math.max(t1, t); } t0 -= 1; t1 += 1;
  const P = (t, s) => [u[0] * t + v[0] * s, u[1] * t + v[1] * s]; return jpoly([[P(t0, a), P(t1, a), P(t1, b), P(t0, b)]]);
}
const frontLen = (g, u) => { let t0 = 1e18, t1 = -1e18; for (const c of g.getCoordinates()) { const t = c.x * u[0] + c.y * u[1]; t0 = Math.min(t0, t); t1 = Math.max(t1, t); } return t1 - t0; };
function addAll(a, b) { return a && b ? a.concat(b) : a || b; }
function applyOps(map, ops, open) {   // replay splits, merges, divisions and fills in order; each step is cached on its inputs
  const out = { used: new Set(), touched: new Set() };
  ops.forEach((op, i) => {
    const ins = op.t === 'm' || op.t === 'r' ? op.ids.filter(id => map.has(id)) : op.t === 'f' ? (op.to && map.has(op.to) ? [op.to] : []) : map.has(op.id) ? [op.id] : [];
    if (op.t === 'm' && (ins.length < 2 || ins[0] !== op.ids[0])) return;
    if ((op.t === 's' || op.t === 'd' || op.t === 'r') && !ins.length) return;
    let piece = null;
    if (op.t === 'f') { piece = open.find(o => !out.used.has(o) && inPoly(op.q, o.geometry.coordinates)); if (!piece || (op.to && !ins.length)) return; }
    const key = i + JSON.stringify(op) + '|' + ins.map(id => map.get(id).st).join('|') + (piece ? '|' + piece.properties.id + ':' + fmt(piece.area, 1) : '');
    let res = memoOps.get(key);
    if (!res) {
      res = null;
      try {
        if (op.t === 'm') { const ps = ins.map(id => map.get(id)), t = ps[0]; let g = jOf(t); for (const q of ps.slice(1)) g = ov(g, jOf(q), 'union'); g = g.buffer(0.03).buffer(-0.03);
          const lab = [...new Set(ps.flatMap(q => q.properties.lab || []))], u0 = ps.map(q => q.properties.u0).find(x => x) || null;
          res = { del: ins, add: [[t.properties.id, t.properties.block, Object.assign(plotProps(t.properties), { lab, u0 }), g, ps.reduce((a, q) => addAll(a, q.adds), null)]] }; }
        else if (op.t === 's') { const t = map.get(op.id), [L, R] = halfPlanes(jOf(t), op.l[0], op.l[1]);
          if (L.getArea() >= 1 && R.getArea() >= 1) res = { del: [op.id], add: [[op.id + '.1', t.properties.block, plotProps(t.properties), L, t.adds], [op.id + '.2', t.properties.block, plotProps(t.properties), R, t.adds]] }; }
        else if (op.t === 'd') { const t = map.get(op.id), n = Math.max(2, Math.min(60, op.n | 0)), u = [Math.cos(op.a), Math.sin(op.a)], ss = strips(jOf(t), u, n);
          res = { del: [op.id], add: ss.filter(g => g.getArea() >= 1).map((g, k) => [op.id + '.' + (k + 1), t.properties.block, plotProps(t.properties), g, t.adds]) }; }
        else if (op.t === 'r') {   // the block's plots replaced by lots square to its long side, two rows back to back when deeper than 55 m
          const ps = ins.map(id => map.get(id)), g = uunion(ps.map(jOf)).buffer(0.03).buffer(-0.03), u = [Math.cos(op.a), Math.sin(op.a)], v = [-u[1], u[0]], w = Math.max(3, Math.min(60, op.w || 7.6));
          let s0 = 1e18, s1 = -1e18; for (const c of g.getCoordinates()) { const sv = c.x * v[0] + c.y * v[1]; s0 = Math.min(s0, sv); s1 = Math.max(s1, sv); }
          const rows = s1 - s0 > 55 ? 2 : 1, out = [], adds = ps.reduce((a, q) => addAll(a, q.adds), null);
          for (let k = 0; k < rows; k++) { const band = ov(g, uvBand(g, u, v, s0 + (s1 - s0) * k / rows - (k ? 0 : 1), s0 + (s1 - s0) * (k + 1) / rows + (k === rows - 1 ? 1 : 0)), 'intersection'); if (band.isEmpty()) continue;
            const n = Math.max(1, Math.round(frontLen(band, u) / w)); for (const q of (n > 1 ? strips(band, u, n) : [band])) if (q.getArea() >= 1) out.push(q); }
          const lp = ps.filter(x => x.properties.u0).map(x => { const ip = jOf(x).getInteriorPoint(); return [[ip.getX(), ip.getY()], x]; });   // a sheet label goes to the one new lot over its old plot's middle
          res = { del: ins, add: out.map((q, k) => { const ip = q.getInteriorPoint(), pt = [ip.getX(), ip.getY()], src = ps.find(x => inPoly(pt, x.geometry.coordinates)) || ps[0], qr = partsJ(q, 0)[0], hit2 = qr ? lp.find(([c]) => inPoly(c, qr.rings)) : null;
            return [op.id + '.' + (k + 1), src.properties.block, Object.assign(plotProps(src.properties), { kind: 'lot', u0: hit2 ? hit2[1].properties.u0 : null, lab: hit2 ? hit2[1].properties.lab : [] }), q, adds]; }) }; }
        else if (op.t === 'f') { const pj = jOf(piece), fid = 'F' + Math.round(op.q[0]) + '_' + Math.round(op.q[1]);
          if (op.to) { const t = map.get(op.to); let g = ov(jOf(t), pj, 'union'); if (g.getNumGeometries() > 1) g = g.buffer(0.03).buffer(-0.03); res = { del: [op.to], add: [[op.to, t.properties.block, plotProps(t.properties), g, addAll(t.adds, [pj])]] }; }
          else { const nb = nearestPlot(map, op.q), blk = nb ? nb.properties.block : fid, pr = { kind: 'lot', street: piece.properties.street, u0: null, lab: [], we: nb ? nb.properties.we : false };
            const n = Math.max(1, Math.min(60, op.n | 0)); const gs = n > 1 ? strips(pj, [Math.cos(op.a || 0), Math.sin(op.a || 0)], n) : [pj];
            res = { del: [], add: gs.filter(g => g.getArea() >= 1).map((g, k) => [n > 1 ? fid + '.' + (k + 1) : fid, blk, pr, g, [g]]) }; } }
      } catch (e) { console.warn('plot step skipped', op, e); res = null; }
      memoOps.set(key, res);
    }
    if (piece) out.used.add(piece);
    if (!res) return;
    if (!res.objs) { res.objs = [];   // each result in pieces: one plot per piece, the largest keeping the id
      for (const [id, blk, pr, g, adds] of res.add) partsJ(g, 1.0).forEach((p, k) => { const pid = k ? id + '~' + SUF[Math.min(k - 1, 25)] : id, pf = mkPlot(pid, blk, p.rings, pr, p.j); pf.adds = adds; pf.st = key + '>' + pid; res.objs.push(pf); }); }
    for (const id of res.del) map.delete(id);
    for (const pf of res.objs) { map.set(pf.properties.id, pf); out.touched.add(pf.properties.block); }
  });
  return out;
}
function nearestPlot(map, q) { let best = null, bd = 60; for (const pf of map.values()) { if (!bbHit(pf.bb, [q[0], q[1], q[0], q[1]], bd)) continue; const d = lineDist(q, pf.geometry.coordinates[0].concat([pf.geometry.coordinates[0][0]])); if (d < bd) { bd = d; best = pf; } } return best; }
// ---------------------------------------------------------------- rebuild (in slices, so the page keeps moving)
let plTok = 0, plTimer = 0;
function schedulePlots(ms = 150) { clearTimeout(plTimer); if (S.drag) return; plTimer = setTimeout(() => { rebuildPlots().catch(e => { console.error(e); setPlotNote('Plots could not be updated: ' + (e.message || e)); }); }, ms); }
function setPlotNote(t) { S.plNote = t; const el = $('plotNote'); if (el) el.textContent = t; }
const sliceWait = () => new Promise(r => setTimeout(r, 0));
async function rebuildPlots() {
  if (!S.plots0) return;
  const ops = S.edits.plotOps || [];
  const CS = changedStreets(), gk = CS.map(j => j.key).join('|') + '#' + JSON.stringify(ops);
  if (S.pl && S.pl.gk === gk) return;
  if ((CS.length || ops.length) && !jready()) { setPlotNote('Waiting for the geometry library'); schedulePlots(400); return; }
  const tok = ++plTok, t0 = performance.now(); let tl = t0; const st = { s1: 0, n: 0, v: 0, t: [] }, mark = w => st.t.push(w + ' ' + Math.round(performance.now() - t0));
  const yieldNow = async () => { if (performance.now() - tl > 30) { await sliceWait(); tl = performance.now(); } if (tok !== plTok) { mark('aborted'); S.plLog = (S.plLog || []).concat([st]).slice(-12); return true; } return false; };
  if (CS.length) setPlotNote('Updating plots for ' + CS.length + ' moved street' + (CS.length === 1 ? '' : 's'));
  const chg = new Set(CS.map(j => j.id)); for (const f of S.streets0) f._chg = chg.has(f.properties.id);
  // corridors: new (N) and old (O), and what the old one leaves (V), each cut into tiles
  const tiles = new Map(), addT = (tk, h) => { if (!tiles.has(tk)) tiles.set(tk, []); tiles.get(tk).push(h); };
  for (const j of CS) {
    const m = memoC.get(j.key) || {}; if (!m.N) { st.n++; m.N = j.del ? GF.createGeometryCollection([]) : j.runs ? corridorRuns(j.runs, j.basin) : corridor(j.cc, j.w, j.basin); m.O = corridor(j.gc, j.w0, j.basin); m.Nt = j.del ? [] : tilesNear(j.cc, j.w / 2, m.N); memoC.set(j.key, m); }
    j.N = m.N; j.O = m.O; for (const t of m.Nt) addT(t.tk, { kind: 'N', j, g: t.g, bb: t.bb, tk: t.tk, vk: 'N' + j.id + ':' + t.sig });
    if (await yieldNow()) return;
  }
  for (const j of CS) {
    const deps = CS.filter(k => k !== j && ((bbHit(j.bbO, k.bbN) && hit(j.O, k.N)) || (bbHit(j.bbO, k.bbO) && hit(j.O, k.O))));
    const vk = j.key + '/' + deps.map(k => k.key).join('/'), m = memoC.get(vk) || {};
    if (!m.Vt) { st.v++; m.V = vacated(j, CS); m.Vt = tilesNear(j.gc, j.w0 / 2, m.V); memoC.set(vk, m); }
    j.vk = vk; j.V = m.V; for (const t of m.Vt) addT(t.tk, { kind: 'V', j, g: t.g, bb: t.bb, tk: t.tk, vk: 'V' + j.id + ':' + t.sig });
    if (await yieldNow()) return;
  }
  mark('corridors');
  // stage 1: each generated plot against the tiles it touches
  const map = new Map(), claims = new Map(), touched = new Set();
  for (let i = 0; i < S.plots0.length; i++) {
    const pf = S.plots0[i], b = pf.bb, hits = [];
    if (tiles.size) for (let tx = Math.floor((b[0] - 1) / TS); tx <= Math.floor((b[2] + 1) / TS); tx++) for (let ty = Math.floor((b[1] - 1) / TS); ty <= Math.floor((b[3] + 1) / TS); ty++) { const hs = tiles.get(tx + ',' + ty); if (hs) for (const h of hs) if (bbHit(b, h.bb, 1)) hits.push(h); }
    if (!hits.length) { map.set(pf.properties.id, pf); continue; }
    const key = pf.properties.id + '|' + hits.map(h => h.vk + '@' + h.tk).join(',');
    let r = memo1.get(key); if (r === undefined) { st.s1++; r = stage1(pf, hits); memo1.set(key, r); }
    if (!r) { map.set(pf.properties.id, pf); continue; }
    touched.add(pf.properties.block);
    for (const [tk, e] of r.claims) { if (!claims.has(tk)) claims.set(tk, []); claims.get(tk).push(e); }
    r.parts.forEach((p, k) => { const id = k ? pf.properties.id + '~' + SUF[Math.min(k - 1, 25)] : pf.properties.id, q = r.objs && r.objs[k];
      if (q) { map.set(id, q); return; }
      const nq = mkPlot(id, pf.properties.block, p.rings, plotProps(pf.properties), p.j); nq.adds = r.adds; nq.st = key + '#' + k; (r.objs = r.objs || [])[k] = nq; map.set(id, nq); });
    if ((i & 63) === 0 && await yieldNow()) return;
  }
  mark('stage1');
  // open land: what the old corridors leave that no plot took
  let open = [];
  if (CS.length) {
    const m = [];
    for (const j of CS) {
      const Vt = memoC.get(j.vk).Vt || [], ok = 'open|' + j.id + '|' + Vt.map(t => t.sig + ':' + (claims.get(t.tk) || []).length).join(','); let mj = memoC.get(ok);
      if (!mj) { const left = []; mj = [];
        for (const t of Vt) { let g = t.g; for (const e of (claims.get(t.tk) || [])) if (hit(g, e)) g = ov(g, e, 'difference'); if (!g.isEmpty() && g.getArea() > 0.5) left.push(g); }
        if (left.length) for (const p of partsJ(uunion(left), 4)) { if (p.j.buffer(-0.5).isEmpty()) continue; const ip = p.j.getInteriorPoint(), q = [Math.round(ip.getX() * 100) / 100, Math.round(ip.getY() * 100) / 100], sg = segAt(j.gc, q);
          const f = { type: 'Feature', properties: { layer: 'open', id: 'open:' + Math.round(q[0]) + ':' + Math.round(q[1]), q, street: j.id, block: null, axis: Math.atan2(sg[1][1] - sg[0][1], sg[1][0] - sg[0][0]) }, geometry: { type: 'Polygon', coordinates: p.rings }, bb: bbOf(p.rings[0]), area: ringsArea(p.rings) };
          f._j = p.j; mj.push(f); }
        memoC.set(ok, mj); }
      m.push(...mj);
    }
    open = m;
    if (await yieldNow()) return;
  }
  mark('open');
  // splits, merges, divisions and fills, then pieces
  const ao = applyOps(map, ops, open); for (const b of ao.touched) touched.add(b);
  const plots = [...map.values()];
  open = open.filter(o => !ao.used.has(o));
  if (await yieldNow()) return;
  // blocks: the generated block less the new corridors, plus the land its plots took; blocks that now touch join
  const byGen = new Map(); for (const pf of plots) { const b = pf.properties.block; if (!byGen.has(b)) byGen.set(b, []); byGen.get(b).push(pf); }
  const comps = [];
  for (const bid of touched) {
    let bf = S.blkById.get(bid); const mine = byGen.get(bid) || []; let g;
    const bk = 'blk|' + bid + '|' + mine.map(pf => pf.st).join(',') + '|' + CS.filter(j => !bf || bbHit(bf._bb, j.bbN)).map(j => j.key).join('/'), bm = memoC.get(bk);
    if (bm) { comps.push(...bm); continue; }
    if (bf) g = bf._j || (bf._j = jgeom(bf.geometry));
    else { if (!mine.length) continue; g = uunion(mine.map(jOf)).buffer(0.03).buffer(-0.03); bf = { properties: { layer: 'block', id: bid, type: 'building', side: 'new', name: '', area_m2: g.getArea() }, _bb: mine.reduce((b, pf) => [Math.min(b[0], pf.bb[0]), Math.min(b[1], pf.bb[1]), Math.max(b[2], pf.bb[2]), Math.max(b[3], pf.bb[3])], [1e18, 1e18, -1e18, -1e18]) }; }
    for (const j of CS) if (bbHit(bf._bb, j.bbN) && hit(g, j.N)) g = ov(g, j.N, 'difference');
    const extra = []; for (const pf of mine) if (pf.adds) for (const e of pf.adds) if (!extra.includes(e)) extra.push(e);
    if (extra.length) { const n0 = partsJ(g, 4).length; g = uunion([g].concat(extra)); if (partsJ(g, 4).length > n0) g = g.buffer(0.03).buffer(-0.03); }
    const mine2 = partsJ(g, 4).map((p, k) => ({ gen: bid, k, rings: p.rings, j: p.j, bb: bbOf(p.rings[0]), area: ringsArea(p.rings), bf, sg: sig(p.j) })); memoC.set(bk, mine2); comps.push(...mine2);
    if (await yieldNow()) return;
  }
  mark('blocks');
  const par = comps.map((_, i) => i), find = i => par[i] === i ? i : (par[i] = find(par[i]));
  for (let a = 0; a < comps.length; a++) for (let b = a + 1; b < comps.length; b++) { const A = comps[a], B = comps[b]; if (A.gen === B.gen || !bbHit(A.bb, B.bb, 0.1)) continue; const dk = A.sg < B.sg ? A.sg + '|' + B.sg : B.sg + '|' + A.sg; let dd = distMemo.get(dk); if (dd === undefined) { try { dd = A.j.distance(B.j); } catch (e) { dd = 1; } distMemo.set(dk, dd); } if (dd < 0.06) par[find(a)] = find(b); }
  const groups = new Map(); comps.forEach((c, i) => { const r = find(i); if (!groups.has(r)) groups.set(r, []); groups.get(r).push(c); });
  const live = [], blockById = new Map(), seen = new Map();
  for (const grp of groups.values()) {
    grp.sort((a, b) => b.area - a.area); const head = grp[0];
    let rings = grp.map(c => c.rings), j = head.j;
    if (grp.length > 1) { const U = uunion(grp.map(c => c.j)).buffer(0.03).buffer(-0.03), ps = partsJ(U, 4); rings = ps.map(p => p.rings); j = ps.length === 1 ? ps[0].j : GF.createMultiPolygon(ps.map(p => p.j)); }
    const n = seen.get(head.gen) || 0; seen.set(head.gen, n + 1);
    const id = n ? head.gen + '~' + SUF[Math.min(n - 1, 25)] : head.gen;
    const f = { type: 'Feature', properties: Object.assign({}, head.bf.properties, { id, gen: head.gen, joined: grp.length > 1 ? [...new Set(grp.map(c => c.gen))] : null, area_m2: grp.reduce((a, c) => a + c.area, 0), live: true }), geometry: { type: rings.length === 1 ? 'Polygon' : 'MultiPolygon', coordinates: rings.length === 1 ? rings[0] : rings }, _j: j };
    f._bb = rings.reduce((b, r) => { const q = bbOf(r[0]); return [Math.min(b[0], q[0]), Math.min(b[1], q[1]), Math.max(b[2], q[2]), Math.max(b[3], q[3])]; }, [1e18, 1e18, -1e18, -1e18]);
    f._members = grp; live.push(f); blockById.set(id, f);
  }
  // which live block each plot is in
  for (const pf of plots) {
    const b = pf.properties.block; if (!touched.has(b)) { pf.lb = b; continue; }
    const cands = live.filter(f => f._members.some(c => c.gen === b));
    if (cands.length === 1) { pf.lb = cands[0].properties.id; continue; }
    const r = pf.geometry.coordinates[0], ip = pf._ip || (pf._ip = (() => { const p = jOf(pf).getInteriorPoint(); return [p.getX(), p.getY()]; })());
    const hit = cands.find(f => polysOf(f.geometry).some(q => inPoly(ip, q))) || live.find(f => bbHit(f._bb, [ip[0], ip[1], ip[0], ip[1]]) && polysOf(f.geometry).some(q => inPoly(ip, q)));
    pf.lb = hit ? hit.properties.id : b; void r;
  }
  if (tok !== plTok) return;
  const blockList = S.deck.features.filter(f => f.properties.layer === 'block' && !touched.has(f.properties.id)).concat(live);
  for (const f of blockList) if (!f._bb) f._bb = polysOf(f.geometry).reduce((b, p) => { const q = bbOf(p[0]); return [Math.min(b[0], q[0]), Math.min(b[1], q[1]), Math.max(b[2], q[2]), Math.max(b[3], q[3])]; }, [1e18, 1e18, -1e18, -1e18]);
  const byId = new Map(plots.map(pf => [pf.properties.id, pf])), byBlock = new Map();
  for (const pf of plots) { if (!byBlock.has(pf.lb)) byBlock.set(pf.lb, []); byBlock.get(pf.lb).push(pf); }
  const grid = new Map(), G = 100; for (const pf of plots.concat(open)) { const b = pf.bb; for (let x = Math.floor(b[0] / G); x <= Math.floor(b[2] / G); x++) for (let y = Math.floor(b[1] / G); y <= Math.floor(b[3] / G); y++) { const k = x + ',' + y; if (!grid.has(k)) grid.set(k, []); grid.get(k).push(pf); } }
  mark('end'); S.plLog = (S.plLog || []).concat([st]).slice(-12);
  S.pl = { stats: st, gk, plots, byId, byBlock, open, blockList, blockById, grid, touched, cs: CS.length, ms: Math.round(performance.now() - t0) };
  if (memo1.size > 60000) memo1.clear(); if (memoOps.size > 4000) memoOps.clear(); if (memoC.size > 3000) memoC.clear(); if (distMemo.size > 20000) distMemo.clear();
  setPlotNote(plots.length.toLocaleString('en-US') + ' plots' + (CS.length ? ', ' + touched.size + ' block' + (touched.size === 1 ? '' : 's') + ' redrawn round ' + CS.length + ' moved street' + (CS.length === 1 ? '' : 's') : '') + (open.length ? ', ' + open.length + ' piece' + (open.length === 1 ? '' : 's') + ' of open land' : '') + '.');
  S.ver++; reselect(); renderSummary(); redraw();
}
function segAt(c, q) { let bi = 1, bd = 1e18; for (let i = 1; i < c.length; i++) { const d = segDist(q, c[i - 1], c[i]); if (d < bd) { bd = d; bi = i; } } return [c[bi - 1], c[bi]]; }
function reselect() {   // keep the selection across a rebuild
  const s = S.sel; if (!s) return; const L = s.f.properties.layer, id = s.f.properties.id;
  if (L === 'plot') { const f = S.pl.byId.get(id) || chainIds(id).map(k => S.pl.byId.get(k)).find(Boolean); S.sel = f ? { f } : null; }
  else if (L === 'open') { const f = S.pl.open.find(o => o.properties.id === id) || S.pl.open.find(o => inPoly(s.f.properties.q, o.geometry.coordinates)); S.sel = f ? { f } : null; }
  else if (L === 'block') { const f = S.pl.blockById.get(id) || S.pl.blockList.find(b => b.properties.id === id); S.sel = f ? { f } : null; }
  renderSel();
}
// ---------------------------------------------------------------- uses, names, blocks
function blockEditOf(id) { const e = S.edits.blocks[id]; return typeof e === 'string' ? { t: e } : (e || null); }
function blockField(f, key) { const p = f.properties; for (const id of [p.id, p.gen]) { if (!id) continue; const e = blockEditOf(id); if (e && e[key] !== undefined) return e[key]; } return undefined; }
function blockFeat(id) { return (S.pl && (S.pl.blockById.get(id))) || S.blkById.get(id) || null; }
function blockList() { return S.pl ? S.pl.blockList : S.deck.features.filter(f => f.properties.layer === 'block'); }
function plotBlock(pf) { return blockFeat(pf.lb || pf.properties.block); }
function baseUse(pf) {
  const bf = plotBlock(pf), bu = bf ? blockField(bf, 'u') : undefined;
  if (bu !== undefined && bu !== null) return [bu || null, 'block'];
  if (pf.properties.u0) return [pf.properties.u0, 'sheet'];
  const tu = bf ? TYPE_USE[blockType(bf)] : null; return tu ? [tu, 'type'] : [null, null];
}
function plotUse(pf) {
  if (pf._uv === S.ver) return pf._u;
  const ids = chainIds(pf.properties.id); let r = null;
  for (const k of ids) { const e = S.edits.plots[k]; if (e && e.u !== undefined) { r = [e.u || null, k === ids[0] ? 'plot' : 'parent']; break; } }
  if (!r) r = baseUse(pf); pf._u = r; pf._uv = S.ver; return r;
}
const plotName = pf => (S.edits.plots[pf.properties.id] || {}).n || '';
function setPlotField(pf, key, val) {
  const id = pf.properties.id, e = Object.assign({}, S.edits.plots[id] || {});
  if (val === undefined) delete e[key]; else e[key] = val;
  if (Object.keys(e).length) S.edits.plots[id] = e; else delete S.edits.plots[id];
}
function setPlotUse(pf, code) {   // code '' = not set; back to the inherited use when it matches
  const id = pf.properties.id, own = S.edits.plots[id]; const keep = own && own.u !== undefined ? own.u : undefined;
  setPlotField(pf, 'u', undefined); pf._uv = -1; const inh = plotUse(pf)[0] || '';
  setPlotField(pf, 'u', inh === code ? undefined : code); pf._uv = -1; void keep; changed();
}
function setBlockEdit(f, patch) {
  const p = f.properties, id = p.id, e = Object.assign({}, blockEditOf(id) || {});
  for (const [k, v] of Object.entries(patch)) { if (v === undefined || v === null || (k === 'n' && v === '')) delete e[k]; else e[k] = v; }
  if (!p.gen && e.t === p.type) delete e.t;
  if (Object.keys(e).length) S.edits.blocks[id] = e; else delete S.edits.blocks[id];
  changed();
}
function setBlockUse(f, code) {   // every plot of the block: its own settings give way
  for (const pf of (S.pl && S.pl.byBlock.get(f.properties.id)) || []) for (const k of chainIds(pf.properties.id)) { const e = S.edits.plots[k]; if (e && e.u !== undefined) { const x = Object.assign({}, e); delete x.u; if (Object.keys(x).length) S.edits.plots[k] = x; else delete S.edits.plots[k]; } }
  setBlockEdit(f, { u: code });
}
function blockUseMix(f) {   // [{u, n, a}] by area, and the leading use
  if (f._mixV === S.ver && f._mixP === S.pl) return f._mix;
  const ps = (S.pl && S.pl.byBlock.get(f.properties.id)) || [], m = new Map();
  for (const pf of ps) { const u = plotUse(pf)[0] || ''; const x = m.get(u) || { u, n: 0, a: 0 }; x.n++; x.a += pf.area; m.set(u, x); }
  const list = [...m.values()].sort((a, b) => b.a - a.a); f._mix = { list, lead: list.length ? list[0].u : null, n: ps.length }; f._mixV = S.ver; f._mixP = S.pl; return f._mix;
}
const useCol = u => C['u-' + (u || 'n')];
function pushOp(op) { S.edits.plotOps = (S.edits.plotOps || []).concat([op]); changed(); }
function touching(a, b) { if (!bbHit(a.bb, b.bb, 0.5)) return false; if (!jready()) return false; try { return jOf(a).distance(jOf(b)) < 0.3; } catch (e) { return false; } }
function plotAt(p) { if (!S.pl) return null; const k = Math.floor(p[0] / 100) + ',' + Math.floor(p[1] / 100); for (const pf of (S.pl.grid.get(k) || [])) if (pf.properties.layer === 'plot' && (S.layers.we || !pf.properties.we) && inPoly(p, pf.geometry.coordinates)) return pf; return null; }
function openAt(p) { if (!S.pl) return null; const k = Math.floor(p[0] / 100) + ',' + Math.floor(p[1] / 100); for (const pf of (S.pl.grid.get(k) || [])) if (pf.properties.layer === 'open' && inPoly(p, pf.geometry.coordinates)) return pf; return null; }
function neighbours(pf, max = 8) { const out = []; if (!S.pl) return out; const seen = new Set();
  for (let x = Math.floor((pf.bb[0] - 1) / 100); x <= Math.floor((pf.bb[2] + 1) / 100); x++) for (let y = Math.floor((pf.bb[1] - 1) / 100); y <= Math.floor((pf.bb[3] + 1) / 100); y++) for (const q of (S.pl.grid.get(x + ',' + y) || [])) { if (q === pf || q.properties.layer !== 'plot' || seen.has(q)) continue; seen.add(q); if (touching(pf, q)) out.push(q); }
  return out.slice(0, max); }
function longSide(f) {   // direction of the longest side of a block's largest piece
  const ps = polysOf(f.geometry); let r = ps[0][0], A = 0; for (const p of ps) { const a = ringArea(p[0]); if (a > A) { A = a; r = p[0]; } }
  let best = 0, ang = 0; for (let i = 0; i < r.length; i++) { const a = r[i], b = r[(i + 1) % r.length], L = Math.hypot(b[0] - a[0], b[1] - a[1]); if (L > best) { best = L; ang = Math.atan2(b[1] - a[1], b[0] - a[0]); } }
  return Math.round(ang * 1e4) / 1e4;
}
function lotCount(g, u) { return Math.max(2, Math.round(frontLen(g, u) / 7.6)); }
