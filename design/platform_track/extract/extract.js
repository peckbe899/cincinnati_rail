() => {
  // Read the page's platform and track design through its own functions (window.__D, exposed by deck_headless.py).
  const D = window.__D, S = window.__S;
  const r1 = x => Math.round(x * 10) / 10, r2 = x => Math.round(x * 100) / 100;
  const deg = (dx, dy) => (Math.atan2(dx, dy) * 180 / Math.PI + 360) % 360;
  const area = r => { let a = 0; for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += (r[j][0] + r[i][0]) * (r[j][1] - r[i][1]); return Math.abs(a) / 2; };
  const idxAt = (cs, s) => { let lo = 0, hi = cs.length - 1; while (lo < hi) { const m = (lo + hi) >> 1; if (cs[m] < s) lo = m + 1; else hi = m; } return lo; };
  const live = D.liveLines();
  const KEY = { fountain_square: [715100, 4331050, 700], cut: [712950, 4331900, 900], norwood_central: [720300, 4337950, 900] };
  const near = (q, k) => Math.hypot(q[0] - KEY[k][0], q[1] - KEY[k][1]) <= KEY[k][2];
  const keyOf = q => Object.keys(KEY).filter(k => near(q, k));
  const pts = c => c.map(q => [r1(q[0]), r1(q[1])]);

  // generated track lines by line id (drawn while a line is untouched)
  const genT = new Map();
  for (const t of S.ctx.tracks) { const k = t.pid || ('nopid:' + t.sys + ':' + t.line); if (!genT.has(k)) genT.set(k, []); genT.get(k).push(t); }
  const signedOff = (c, f, q) => { let best = 1e18, bp = null; for (let i = 1; i < c.length; i++) { const a = c[i - 1], b = c[i], dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy || 1e-9; let t = ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / L2; t = Math.max(0, Math.min(1, t)); const px = a[0] + t * dx, py = a[1] + t * dy, d = (px - q[0]) ** 2 + (py - q[1]) ** 2; if (d < best) { best = d; bp = [px, py]; } } return { d: Math.sqrt(best), off: (bp[0] - q[0]) * (-f[3]) + (bp[1] - q[1]) * f[2] }; };

  const out = { meta: S.ctx.meta, constants: { PW: D.PW, H0_rer: D.H0('rer'), H0_cvx: D.H0('cvx'), H0_metro_twin: D.H0('metro', 'twin'), H0_metro_bore: D.H0('metro', 'bore'), EDGE: { metro: D.EDGE('metro'), rer: D.EDGE('rer'), cvx: D.EDGE('cvx') }, TAPER: D.TAPER, H_TUBE: D.H_TUBE, H_BOX: D.H_BOX, SLIDE_M: D.SLIDE_M }, stations: [], lines: [], key_tracks: {} };

  for (const st of S.sf) {
    const p = st.properties, q = st.geometry.coordinates;
    const rec = { key: p.id, sys: p.sys, name: p.name, lines: p.line, E: r1(q[0]), N: r1(q[1]), deleted: D.stDeleted(st), edited: !!S.edits.stations[p.id], areas: keyOf(q), stops: [] };
    for (const sp of p.stops) {
      const lf = sp.pid ? S.tfById.get(sp.pid) : null;
      const o = { pid: sp.pid, line: lf ? D.featLabel(lf) : null, era: sp.era || null, L: r2(sp.L), n_generated: sp.n, type_generated: sp.type0, type: D.stopType(sp), edit: D.stopEdit(sp), live: D.stopLive(sp), o_generated: r1(sp.o0), o: r1(D.stopOff(sp)), lat0: r2(sp.lat0), w_island_generated: r2(sp.w0) };
      o.bands = D.stopBands(sp).map(b => [r2(b[0]), r2(b[1])]);
      const rings = D.stopRings(sp);
      o.ring_area_m2 = rings.map(rg => r1(area(rg)));
      o.rings = rings.map(rg => pts(rg.filter((_, i) => i % 2 === 0 || i === rg.length - 1)));
      if (lf) {
        const [, sc, g] = D.stopFrame(sp), f = D.frameAt(g.c, g.cs, sc), P = lf.properties;
        o.centre = [r1(f[0]), r1(f[1])]; o.heading = r1(deg(f[2], f[3]));
        o.h_default = D.H0(sp.sys, sp.era);
        o.h_at_centre = P.hs ? D.hAt(P, f[0], f[1], o.h_default) : o.h_default;
        o.bored_at_centre = P.hs ? o.h_at_centre === D.H_TUBE : null;
        if (o.live) {
          const pair = D.trackPair(lf), i = idxAt(g.cs, sc), c = g.c[i], n = [-f[3], f[2]], off = pt => (pt[0] - c[0]) * n[0] + (pt[1] - c[1]) * n[1];
          o.track_offsets = [r2(off(pair[0][i])), r2(off(pair[1][i]))]; o.tracks_from = 'settings';
        } else {
          const ts = genT.get(sp.pid) || [];
          const offs = ts.map(t => signedOff(t.c, f, f)).filter(x => x.d < 30).map(x => r2(x.off)).sort((a, b) => b - a);
          o.track_offsets = offs; o.tracks_from = 'generated';
        }
      }
      rec.stops.push(o);
    }
    out.stations.push(rec);
  }

  // every line: construction along it (bored = twin tubes at 8 m for Metro), whether drawn from settings
  for (const f of S.tf) {
    const P = f.properties, g = D.geomOf(f), L = g.cs[g.cs.length - 1];
    const o = { id: P.id, label: D.featLabel(f), sys: P.sys, era: P.era || null, name: P.name, sub: P.sub || null, live: live.has(P.id), edited: !!S.edits.transit[P.id], length_m: r1(L), has_hs: !!P.hs };
    if (P.sys === 'metro' && P.hs) {
      const runs = []; let cur = null;
      for (let s = 0; s <= L; s += 20) { const q = D.frameAt(g.c, g.cs, s), b = D.hAt(P, q[0], q[1], D.H0(P.sys, P.era)) === D.H_TUBE ? 1 : 0; if (cur && cur.b === b) cur.s1 = s; else { cur = { b, s0: s, s1: s }; runs.push(cur); } }
      o.bored_runs = runs.map(r => [r.s0, r.s1, r.b ? 'bored' : 'box']); o.bored_m = runs.filter(r => r.b).reduce((a, r) => a + r.s1 - r.s0, 0);
    }
    out.lines.push(o);
  }

  // drawn tracks inside the three key areas
  for (const k of Object.keys(KEY)) {
    const [cx, cy, R] = KEY[k], inR = q => Math.hypot(q[0] - cx, q[1] - cy) <= R, list = [];
    const clip = c => { const runs = []; let cur = null; for (const q of c) { if (inR(q)) { if (!cur) { cur = []; runs.push(cur); } cur.push(q); } else cur = null; } return runs.filter(r => r.length > 1); };
    for (const f of S.tf) { const P = f.properties; if (!live.has(P.id)) continue; const pair = D.trackPair(f); pair.forEach((c, j) => clip(c).forEach(r => list.push({ pid: P.id, line: D.featLabel(f), sys: P.sys, side: j ? 'right' : 'left', from: 'settings', c: pts(r.filter((_, i) => i % 3 === 0 || i === r.length - 1)) }))); }
    for (const t of S.ctx.tracks) { if (t.pid && live.has(t.pid)) continue; clip(t.c).forEach(r => list.push({ pid: t.pid || null, line: t.line, sys: t.sys, from: 'generated', c: pts(r) })); }
    out.key_tracks[k] = list;
  }
  // every drawn track pair in the plan: lines drawn from settings through trackPair (every 10 m), the rest as generated
  out.all_tracks = [];
  for (const f of S.tf) { const P = f.properties; if (!live.has(P.id)) continue; const pair = D.trackPair(f);
    pair.forEach((c, j) => out.all_tracks.push({ pid: P.id, line: D.featLabel(f), sys: P.sys, side: j ? 'right' : 'left', from: 'settings', c: pts(c.filter((_, i) => i % 5 === 0 || i === c.length - 1)) })); }
  for (const t of S.ctx.tracks) { if (t.pid && live.has(t.pid)) continue; out.all_tracks.push({ pid: t.pid || null, line: t.line, sys: t.sys, from: 'generated', c: pts(t.c) }); }
  out.edits_count = { stations: Object.keys(S.edits.stations).length, transit: Object.keys(S.edits.transit).length };
  return out;
}
