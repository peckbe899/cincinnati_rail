// Extracted unchanged from the Mill Creek Deck page (https://claude.ai/artifact/L81dVQSV8THSWai2LhZhcv, version 1793213425-9636), index.html lines 412-579.
// The original arcs/fitarcs.py and arcs/fitarcs.js from the Topography workspace are lost; this is the page's port of the same rules (Relief_Maps_Log 10ze.6).
// fitSource() below uses the page's vertsOf/ctrlOf helpers and is included for reference only. FA.fit(points) is self-contained.

// ---------------------------------------------------------------- constant-radius curves from a line's own points (arcs/fitarcs.py, same rules)
// Corner points that turn the same way make one curve: three or more give its circle (least squares); one or two give the curve
// between the straights either side (radius fitted to the two points, or the largest that fits). The straights adapt as the common
// tangents of their curves; a curve that cannot join, sweeps the wrong way or strays from the drawn line falls back and shrinks.
const FA = (() => {
  const D_MIN = 0.3, CHORD = 150, rad = Math.PI / 180;
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1]], add = (a, b) => [a[0] + b[0], a[1] + b[1]], mul = (a, s) => [a[0] * s, a[1] * s];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1], cr = (a, b) => a[0] * b[1] - a[1] * b[0], len = a => Math.hypot(a[0], a[1]);
  const unit = a => { const n = len(a); return n > 1e-12 ? [a[0] / n, a[1] / n] : [0, 0]; };
  function clean(V) {
    V = V.map(p => [p[0], p[1]]); let ch = true;
    while (ch && V.length > 3) {
      ch = false; const L = []; for (let i = 0; i < V.length - 1; i++) L.push(len(sub(V[i + 1], V[i])));
      for (let i = 0; i < L.length; i++) { const nb = [L[i - 1], L[i + 1]].filter(x => x !== undefined);
        if (L[i] < 12 && nb.length && L[i] < 0.3 * Math.min(...nb)) { if (i === 0) V.splice(1, 1); else if (i === L.length - 1) V.splice(V.length - 2, 1); else { V[i] = mul(add(V[i], V[i + 1]), 0.5); V.splice(i + 1, 1); } ch = true; break; } }
    }
    return V;
  }
  function defl(V) { const d = [0]; for (let i = 1; i < V.length - 1; i++) { const a = unit(sub(V[i], V[i - 1])), b = unit(sub(V[i + 1], V[i])); d.push(Math.atan2(cr(a, b), dot(a, b)) / rad); } d.push(0); return d; }
  function runsOf(V, d) {
    const out = []; let cur = [];
    for (let i = 1; i < V.length - 1; i++) {
      if (Math.abs(d[i]) < D_MIN) { if (cur.length) { out.push(cur); cur = []; } continue; }
      if (cur.length && (Math.sign(d[i]) !== Math.sign(d[cur[cur.length - 1]]) || len(sub(V[i], V[cur[cur.length - 1]])) > CHORD)) { out.push(cur); cur = []; }
      cur.push(i);
    }
    if (cur.length) out.push(cur); return out;
  }
  function solve(M, v) {   // small dense solve (Gauss-Jordan with pivoting)
    const n = v.length, A = M.map((r, i) => [...r, v[i]]);
    for (let c = 0; c < n; c++) { let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(A[r][c]) > Math.abs(A[p][c])) p = r; [A[c], A[p]] = [A[p], A[c]];
      if (Math.abs(A[c][c]) < 1e-12) return null; for (let r = 0; r < n; r++) if (r !== c) { const f = A[r][c] / A[c][c]; for (let k = c; k <= n; k++) A[r][k] -= f * A[c][k]; } }
    return A.map((r, i) => r[n] / r[i]);
  }
  function circleFit(P) {
    const n = P.length, mx = P.reduce((s, p) => s + p[0], 0) / n, my = P.reduce((s, p) => s + p[1], 0) / n;
    let sxx = 0, sxy = 0, syy = 0, sxz = 0, syz = 0, sz = 0;
    for (const p of P) { const x = p[0] - mx, y = p[1] - my, z = x * x + y * y; sxx += x * x; sxy += x * y; syy += y * y; sxz += x * z; syz += y * z; sz += z; }
    const s = solve([[sxx, sxy, 0], [sxy, syy, 0], [0, 0, n]], [sxz, syz, sz]); if (!s) return null;
    let O = [s[0] / 2 + mx, s[1] / 2 + my];
    for (let it = 0; it < 30; it++) {
      const r = P.map(p => len(sub(p, O))), rm = r.reduce((a, b) => a + b, 0) / n, J = P.map((p, i) => [-(p[0] - O[0]) / r[i], -(p[1] - O[1]) / r[i]]);
      const jm = [J.reduce((a, j) => a + j[0], 0) / n, J.reduce((a, j) => a + j[1], 0) / n], Jc = J.map(j => [j[0] - jm[0], j[1] - jm[1]]);
      let a = 0, b = 0, c = 0, g0 = 0, g1 = 0; Jc.forEach((j, i) => { const res = r[i] - rm; a += j[0] * j[0]; b += j[0] * j[1]; c += j[1] * j[1]; g0 -= j[0] * res; g1 -= j[1] * res; });
      const det = a * c - b * b; if (Math.abs(det) < 1e-12) break; const st = [(c * g0 - b * g1) / det, (a * g1 - b * g0) / det]; O = add(O, st); if (len(st) < 1e-4) break;
    }
    const r = P.map(p => len(sub(p, O))), rm = r.reduce((a, b) => a + b, 0) / n; return { O, R: rm, dev: Math.max(...r.map(x => Math.abs(x - rm))) };
  }
  function inter(p, d, q, e) { const det = d[0] * -e[1] - (-e[0]) * d[1]; if (Math.abs(det) < 1e-9) return null; const w = sub(q, p), t = (w[0] * -e[1] - (-e[0]) * w[1]) / det; return add(p, mul(d, t)); }
  function fillet(V, d, r) {
    const a = r[0], b = r[r.length - 1], s = {}; s.din = unit(sub(V[a], V[a - 1])); s.dout = unit(sub(V[b + 1], V[b])); s.delta = Math.atan2(cr(s.din, s.dout), dot(s.din, s.dout));
    s.PI = a === b ? V[a] : inter(V[a - 1], s.din, V[b], s.dout); s.ok = !!s.PI && Math.abs(s.delta) > 0.05 * rad; if (!s.ok) return s;
    s.tn = Math.tan(Math.abs(s.delta) / 2); s.h = Math.cos(Math.abs(s.delta) / 2); s.bis = unit(add(mul(s.din, -1), s.dout)); s.sg = s.delta > 0 ? 1 : -1;
    s.centre = R => add(s.PI, mul(s.bis, R / s.h));
    const rl = dot(sub(s.PI, V[a - 1]), s.din) - (Math.abs(d[a - 1]) >= D_MIN ? 0.5 * len(sub(V[a], V[a - 1])) : 1);
    const rr = dot(sub(V[b + 1], s.PI), s.dout) - (Math.abs(d[b + 1]) >= D_MIN ? 0.5 * len(sub(V[b + 1], V[b])) : 1);
    s.Rmax = Math.max(Math.min(rl, rr), 0.5) / s.tn; s.R = s.Rmax; const pts = r.map(i => V[i]);
    if (pts.length >= 2) { let best = 1e18, bR = s.Rmax; const l0 = Math.log(3), l1 = Math.log(Math.max(s.Rmax, 4));
      for (let q = 0; q < 300; q++) { const R = Math.exp(l0 + (l1 - l0) * q / 299), O = s.centre(R); let c = 0; for (const p of pts) { const e = len(sub(p, O)) - R; c += e * e; } if (c < best) { best = c; bR = R; } }
      s.R = Math.min(bR, s.Rmax); }
    s.far = pts.length >= 2 && len(sub(s.PI, mul(add(V[a], V[b]), 0.5))) > Math.max(3 * len(sub(V[b], V[a])), 120);
    return s;
  }
  function segdist(p, c) { let best = 1e18; for (let i = 0; i < c.length - 1; i++) { const a = c[i], ab = sub(c[i + 1], a), L2 = dot(ab, ab); const u = L2 < 1e-12 ? 0 : Math.max(0, Math.min(1, dot(sub(p, a), ab) / L2)); best = Math.min(best, len(sub(add(a, mul(ab, u)), p))); } return best; }
  function tangent(A, B) {
    const D = sub(B.O, A.O), L = len(D), k = B.s * B.R - A.s * A.R;
    if (L > 1e-9 && Math.abs(k) >= L - 1e-6 && A.s === B.s && A.R > 0 && B.R > 0 && Math.abs(k) - L <= Math.max(3, 0.03 * Math.max(A.R, B.R))) {
      const big = A.R > B.R ? A : B, small = big === A ? B : A, u = unit(sub(small.O, big.O)), P = mul(add(add(big.O, mul(u, big.R)), add(small.O, mul(u, small.R))), 0.5);
      const w = sub(P, A.O); return [P, P, mul(unit([-w[1], w[0]]), A.s)];
    }
    for (const [P, Cc, first] of [[A, B, true], [B, A, false]]) {   // a line end on (or just inside) the curve starts on it
      if (P.R === 0 && Cc.R > 0 && Math.abs(len(sub(P.O, Cc.O)) - Cc.R) <= Math.max(2, 0.01 * Cc.R)) {
        const w = sub(P.O, Cc.O), tt = mul(unit([-w[1], w[0]]), Cc.s), q = add(Cc.O, mul(unit(w), Cc.R)); return first ? [P.O, q, tt] : [q, P.O, tt]; }
    }
    if (L < 1e-9 || Math.abs(k) >= L) return null;
    const ang = Math.atan2(D[1], D[0]), phi = Math.asin(k / L);
    for (const th of [ang + (Math.PI / 2 - phi), ang - (Math.PI / 2 - phi)]) { const n = [Math.cos(th), Math.sin(th)], t = [n[1], -n[0]]; if (dot(D, t) > 0) return [sub(A.O, mul(n, A.s * A.R)), sub(B.O, mul(n, B.s * B.R)), t]; }
    return null;
  }
  function circles(V, d, r, depth) {   // one circle if the points sit on it within 0.6% (1 m at least), else the split that does, else one within 2.5%
    const f = circleFit(r.map(i => V[i])), net = r.reduce((s, i) => s + d[i], 0), one = f ? [{ run: r, net, fil: null, kind: 'circle', O: f.O, R: f.R, s: net > 0 ? 1 : -1, dev: f.dev }] : null;
    if (f && f.R < 5e4 && f.dev < Math.max(1, 0.006 * f.R)) return one;
    let best = null;
    if (depth < 2 && r.length >= 6) for (let c = 3; c < r.length - 2; c++) { const a = circles(V, d, r.slice(0, c), depth + 1), b = a && circles(V, d, r.slice(c), depth + 1);
      if (a && b) { const cand = a.concat(b), key = [cand.length, Math.max(...cand.map(x => x.dev))]; if (!best || key[0] < best.key[0] || (key[0] === best.key[0] && key[1] < best.key[1])) best = { key, cand }; } }
    if (best) return best.cand;
    if (f && f.R < 5e4 && f.dev < Math.max(2, 0.025 * f.R)) return one;
    return null;
  }
  function fit(V0) {
    const V = clean(V0), d = V.length >= 3 ? defl(V) : [];
    if (V.length < 3 || Math.max(...d.map(Math.abs)) > 120) return { verts: V, k: {}, curves: [], skipped: true };
    let els = [];
    for (const r of runsOf(V, d)) {
      const f = fillet(V, d, r), e = { run: r, net: r.reduce((s, i) => s + d[i], 0), fil: f.ok ? f : null, kind: null };
      if (r.length >= 3) { const parts = circles(V, d, r, 0); if (parts && parts.length === 1) Object.assign(e, parts[0]); else if (parts) { els.push(...parts); continue; } }
      if (!e.kind) {
        if (f.ok && f.far && r.length >= 2) { for (const i of r) { const g = fillet(V, d, [i]); if (g.ok) els.push({ run: [i], net: d[i], fil: g, kind: 'fillet', O: g.centre(g.R), R: g.R, s: g.sg }); } continue; }
        if (!f.ok) continue; Object.assign(e, { kind: 'fillet', O: f.centre(f.R), R: f.R, s: f.sg });
      }
      els.push(e);
    }
    const ends = [{ O: V[0], R: 0, s: 1, run: [0], kind: 'end' }, { O: V[V.length - 1], R: 0, s: 1, run: [V.length - 1], kind: 'end' }];
    const ang = (p, O) => Math.atan2(p[1] - O[1], p[0] - O[0]), mod = x => ((x % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
    function check(i, T) {
      const e = els[i]; if (e.kind === 'point') return true; const ta = T[i], tb = T[i + 1], pin = ta[1], pout = tb[0];
      const a0 = ang(pin, e.O), sw = mod((ang(pout, e.O) - a0) * e.s); e.a0 = a0; e.sw = sw;
      if (sw / rad > Math.abs(e.net) * 1.6 + 20 || sw / rad > 179) return false;
      const r0 = e.run[0], r1 = e.run[e.run.length - 1];
      for (const [t, ref] of [[ta[2], sub(V[r0], V[r0 - 1])], [tb[2], sub(V[r1 + 1], V[r1])]]) if (dot(t, unit(ref)) < Math.cos(25 * rad)) return false;
      const span = Math.max(len(sub(V[r1], V[r0])), 30); if (len(sub(pin, V[r0])) > 2.5 * span + 60 || len(sub(pout, V[r1])) > 2.5 * span + 60) return false;
      const loc = [ta[0], ta[1]]; for (let q = 1; q < 12; q++) { const t = a0 + e.s * sw * q / 12; loc.push(add(e.O, [e.R * Math.cos(t), e.R * Math.sin(t)])); } loc.push(tb[0], tb[1]);
      const allow = e.run.length === 1 ? 20 : 8; for (let j = r0; j <= r1; j++) if (segdist(V[j], loc) > allow) return false;
      for (let j = r0; j < r1; j++) if (segdist(mul(add(V[j], V[j + 1]), 0.5), loc) > 12) return false;
      for (const [jo, vi, tp] of [[r0 - 1, V[r0], pin], [r1 + 1, V[r1], pout]]) {
        if (Math.abs(d[jo]) >= D_MIN && jo > 0 && jo < V.length - 1) continue; const vo = V[jo];
        if (segdist(vo, loc) > 8) return false; const sg = sub(vi, vo), L2 = dot(sg, sg);
        if (L2 > 1 && dot(sub(tp, vo), sg) / L2 > 0.5 && segdist(mul(add(vo, vi), 0.5), loc) > 8) return false;
      }
      return true;
    }
    const singles = run => run.map(i => { const g = fillet(V, d, [i]); return g.ok ? { run: [i], net: d[i], fil: g, kind: 'fillet', O: g.centre(g.R), R: g.R, s: g.sg } : { run: [i], net: 0, fil: null, kind: 'point', O: V[i], R: 0, s: 1 }; });
    function demote(e) {
      const f = e.fil;
      if (e.kind === 'circle') { if (f && f.ok && !f.far) return [Object.assign(e, { kind: 'fillet', O: f.centre(f.R), R: f.R, s: f.sg })]; return singles(e.run); }
      if (e.kind === 'fillet' && e.R > 2) { e.R *= 0.8; e.O = f.centre(e.R); return [e]; }
      if (e.run.length > 1) return singles(e.run);
      return [{ run: e.run, net: e.net, fil: null, kind: 'point', O: V[e.run[0]], R: 0, s: 1 }];
    }
    function straightBad(seq, T) {
      for (let j = 0; j < T.length; j++) { const tj = T[j], ia = seq[j].run[seq[j].run.length - 1], ib = seq[j + 1].run[0], pts = [];
        for (let i = ia + 1; i < ib; i++) pts.push(V[i]); for (let i = ia; i < ib; i++) pts.push(mul(add(V[i], V[i + 1]), 0.5));
        const seg = [sub(tj[0], mul(tj[2], 5)), add(tj[1], mul(tj[2], 5))];
        if (pts.some(p => segdist(p, seg) > 8)) { const cand = [j - 1, j].filter(x => x >= 0 && x < els.length && els[x].kind !== 'point'); if (cand.length) return cand.reduce((a, b) => els[a].R >= els[b].R ? a : b); } }
      return null;
    }
    function snap() { for (let i = 0; i < els.length - 1; i++) { const A = els[i], B = els[i + 1]; if (A.kind !== 'circle' || B.kind !== 'circle' || A.s !== B.s) continue;
      const big = A.R >= B.R ? A : B, small = big === A ? B : A, D = sub(small.O, big.O), L = len(D), k = big.R - small.R; if (k - Math.max(3, 0.03 * big.R) <= L && L < k && L > 1e-6) small.O = add(big.O, mul(D, k / L)); } }
    let T;
    for (let it = 0; it < 6000; it++) {
      snap(); const seq = [ends[0], ...els, ends[1]]; T = []; for (let j = 0; j < seq.length - 1; j++) T.push(tangent(seq[j], seq[j + 1]));
      let bad = null; for (let j = 0; j < T.length; j++) if (!T[j]) { const cand = [j - 1, j].filter(x => x >= 0 && x < els.length && els[x].kind !== 'point'); bad = cand.length ? cand.reduce((a, b) => els[a].R >= els[b].R ? a : b) : null; break; }
      if (bad === null) { for (let i = 0; i < els.length; i++) if (!check(i, T)) { bad = i; break; } }
      if (bad === null) bad = straightBad(seq, T);
      if (bad === null) break;
      els.splice(bad, 1, ...demote(els[bad]));
    }
    { const seq = [ends[0], ...els, ends[1]]; T = []; for (let j = 0; j < seq.length - 1; j++) T.push(tangent(seq[j], seq[j + 1])); }
    const verts = [V[0]], k = {}, curves = [], push = p => { if (len(sub(p, verts[verts.length - 1])) > 0.5) verts.push(p); };
    els.forEach((e, i) => {
      if (e.kind === 'point') { push(e.O); return; }
      check(i, T); push(T[i][1]); const m = Math.max(1, Math.ceil(e.sw / rad / 15));
      for (let j = 0; j < m; j++) { const t1 = e.a0 + e.s * e.sw * (j + 1) / m, tm = e.a0 + e.s * e.sw * (j + 0.5) / m, th = e.sw / m;
        k[verts.length - 1] = add(e.O, [e.R / Math.cos(th / 2) * Math.cos(tm), e.R / Math.cos(th / 2) * Math.sin(tm)]); verts.push(add(e.O, [e.R * Math.cos(t1), e.R * Math.sin(t1)])); }
      const tmid = e.a0 + e.s * e.sw / 2; curves.push({ R: e.R, sweep: e.sw / rad, mid: add(e.O, [e.R * Math.cos(tmid), e.R * Math.sin(tmid)]) });
    });
    push(V[V.length - 1]);
    const r1 = x => Math.round(x * 10) / 10, rp = p => [r1(p[0]), r1(p[1])];
    const kk = {}; for (const [i, q] of Object.entries(k)) kk[i] = rp(q);
    return { verts: verts.map(rp), k: kk, curves };
  }
  return { fit };
})();
function fitSource(f) {   // the line's own points, plus a few along any piece bent more than 5 m off straight (about every 60 m, two to four pieces)
  const v = vertsOf(f), K = ctrlOf(f) || {}, out = [v[0]];
  for (let i = 0; i < v.length - 1; i++) { const k = K[i]; if (k && Math.hypot(k[0] - (v[i][0] + v[i + 1][0]) / 2, k[1] - (v[i][1] + v[i + 1][1]) / 2) / 2 > 5) { const n = Math.min(4, Math.max(2, Math.round(Math.hypot(v[i + 1][0] - v[i][0], v[i + 1][1] - v[i][1]) / 60))); for (let j = 1; j < n; j++) out.push(qpt(v[i], k, v[i + 1], j / n)); } out.push(v[i + 1]); }
  return out;
}

if (typeof module !== 'undefined') module.exports = { FA };
