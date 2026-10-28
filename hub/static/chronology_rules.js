// The Chronology rules (Ben, 28 October; handoff "Chronology and tunnel methods", section 1.4), shared by the Chronology
// page and the checks (node). The record: chronology/segments {phase_years, segments: {key: {year, phase, src, note}},
// stations: {key: {year, src, note}}, core: {route: [segment keys]}}; the routes: chronology_lines.json (tools/chronology.py).
//
// 1. Each line's core is its opening segment (core in the record), else its earliest year set. A branch's core is the
//    segment of its parent at the junction.
// 2. Going outward from the core a segment is never older than the one it extends from.
// 3. A station opens no earlier than the earliest segment that touches it (by default that year).
// 4. A station later than that is infill (marked, not an error).
// 5. A shared segment has one year and meets rule 2 on every line.
// 6. Unset segments are skipped; an unset segment between set ones gets the range of years it may take.
(function (root) {
  // Metro: per line (no Metro lines share track); TRI: the station pair, so shared track is one segment
  const segKey = (sys, a, b, line) => { const [x, y] = [a, b].sort(); return sys === 'metro' ? `metro|${line}|${x}|${y}` : `${sys}|${x}|${y}`; };
  const keyName = (k) => k.split('|').slice(k.startsWith('metro|') ? 2 : 1).join(' to ');
  const stKey = (sys, n) => `${sys}|${n}`;
  const phaseOfYear = (rec, y) => { if (y == null) return null; for (const [a, b, p] of rec.phase_years || []) if (y >= a && y <= b) return p; return null; };
  const segOf = (rec, k) => (rec.segments || {})[k] || {};
  const segYear = (rec, k) => { const y = segOf(rec, k).year; return y == null || y === '' ? null : +y; };
  const segPhase = (rec, k) => segOf(rec, k).phase || phaseOfYear(rec, segYear(rec, k));
  const PHASE_NAME = { 1: 'Phase 1', 2: 'Phase 2', 3: 'Phase 3', later: 'Later' };

  function nearestC(route, lon, lat) {   // chainage of the route's path point nearest (lon, lat)
    let best = Infinity, c = 0; const k = Math.cos(lat * Math.PI / 180);
    for (const [cc, x, y] of route.path) { const d = ((x - lon) * k) ** 2 + (y - lat) ** 2; if (d < best) { best = d; c = cc; } }
    return { c, d: Math.sqrt(best) * 111320 };
  }
  function segAtC(route, c) { const st = route.stations; let i = 0; while (i + 2 < st.length && c > st[i + 1].c) i++; return i; }

  // the order of each route outward from its core: [{key, from}] with from = the key it extends (null at the core)
  function orders(routes, rec) {
    const byId = Object.fromEntries(routes.map((r) => [r.id, r])), out = {};
    for (const r of routes) {
      const n = r.segments.length; if (!n) continue;
      let core = null, inner = null;   // core: indices; inner: the parent segment a branch extends
      if (r.parent && byId[r.parent]) {
        const p = byId[r.parent], s0 = r.stations[0], s1 = r.stations[r.stations.length - 1];
        const a = nearestC(p, s0.lon, s0.lat), b = nearestC(p, s1.lon, s1.lat), atStart = a.d <= b.d;
        inner = p.segments[segAtC(p, (atStart ? a : b).c)];
        core = atStart ? [-1] : [n];   // a virtual core just beyond the junction end
      } else {
        const ck = (rec.core || {})[r.id];
        const idx = ck ? r.segments.map((k, i) => (ck.includes(k) ? i : -1)).filter((i) => i >= 0) : [];
        if (idx.length) core = [Math.min(...idx), Math.max(...idx)];
        else {
          let best = null; r.segments.forEach((k, i) => { const y = segYear(rec, k); if (y != null && (best == null || y < segYear(rec, r.segments[best]))) best = i; });
          if (best != null) core = [best, best];
        }
      }
      const seq = [];
      if (core) {
        const lo = core[0], hi = core[core.length - 1];
        for (let i = Math.max(lo, 0); i <= Math.min(hi, n - 1); i++) seq.push({ key: r.segments[i], from: null, core: true });
        for (let i = hi + 1; i < n; i++) seq.push({ key: r.segments[i], from: i - 1 >= 0 && i - 1 >= lo ? r.segments[i - 1] : inner, out: 1, i });
        for (let i = lo - 1; i >= 0; i--) seq.push({ key: r.segments[i], from: i + 1 <= hi && i + 1 < n ? r.segments[i + 1] : inner, out: -1, i });
      }
      out[r.id] = { core, inner, seq };
    }
    return out;
  }

  function analyse(routes, rec) {
    const O = orders(routes, rec), viol = [], ranges = {}, unset = [];
    const label = keyName;
    for (const r of routes) {
      const o = O[r.id]; if (!o) continue;
      // walk outward on each side keeping the newest year inside
      for (const dir of [1, -1]) {
        const side = o.seq.filter((s) => s.out === dir);
        let inside = null, insideKey = null;
        const coreYears = o.seq.filter((s) => s.core).map((s) => segYear(rec, s.key)).filter((y) => y != null);
        if (coreYears.length) { inside = Math.max(...coreYears); insideKey = o.seq.find((s) => s.core && segYear(rec, s.key) === inside).key; }
        if (o.inner && segYear(rec, o.inner) != null) { inside = segYear(rec, o.inner); insideKey = o.inner; }
        for (const s of side) {
          const y = segYear(rec, s.key);
          if (y == null) continue;
          if (inside != null && y < inside) viol.push({ rule: 2, key: s.key, route: r.id, need: inside, inner: insideKey,
            text: `${label(s.key)} (${r.name}) opened ${y}, before ${label(insideKey)} inside it (${inside})` });
          if (inside == null || y > inside) { inside = y; insideKey = s.key; }
        }
      }
      // ranges for unset segments: from the newest year inside to the oldest set year outside
      for (const dir of [1, -1]) {
        const side = o.seq.filter((s) => s.out === dir);
        side.forEach((s, j) => {
          if (segYear(rec, s.key) != null) return;
          const ins = side.slice(0, j).map((t) => segYear(rec, t.key)).concat(o.seq.filter((t) => t.core).map((t) => segYear(rec, t.key)), o.inner ? [segYear(rec, o.inner)] : []).filter((y) => y != null);
          const outs = side.slice(j + 1).map((t) => segYear(rec, t.key)).filter((y) => y != null);
          const lo = ins.length ? Math.max(...ins) : null, hi = outs.length ? Math.min(...outs) : null;
          const prev = ranges[s.key] || [null, null];
          ranges[s.key] = [lo == null ? prev[0] : Math.max(lo, prev[0] ?? lo), hi == null ? prev[1] : Math.min(hi, prev[1] ?? hi)];
        });
      }
      for (const k of r.segments) if (segYear(rec, k) == null && !segOf(rec, k).phase && !unset.includes(k)) unset.push(k);
    }
    // stations: no earlier than their track; later is infill
    const stations = {}, touch = {};
    for (const r of routes) r.segments.forEach((k, i) => { for (const s of [r.stations[i], r.stations[i + 1]]) { const sk = stKey(r.sys, s.name); (touch[sk] = touch[sk] || new Set()).add(k); } });
    for (const [sk, ks] of Object.entries(touch)) {
      const ys = [...ks].map((k) => segYear(rec, k)).filter((y) => y != null), min = ys.length ? Math.min(...ys) : null;
      const own = (rec.stations || {})[sk] && rec.stations[sk].year != null && rec.stations[sk].year !== '' ? +rec.stations[sk].year : null;
      stations[sk] = { year: own ?? min, own, min, infill: own != null && min != null && own > min };
      if (own != null && min != null && own < min) viol.push({ rule: 3, station: sk, need: min, text: `${sk.split('|')[1]} station opened ${own}, before its track (${min})` });
    }
    // orphans: record entries whose stations are not on any route (kept, listed)
    const segSet = new Set(routes.flatMap((r) => r.segments));
    const orphans = { segments: Object.keys(rec.segments || {}).filter((k) => !segSet.has(k)), stations: Object.keys(rec.stations || {}).filter((k) => !touch[k]) };
    return { orders: O, violations: viol, ranges, unset, stations, orphans };
  }

  // an edit: {segments: {key: patch}, stations: {key: patch}}; refused when it would add a rule 2, 3 or 5 violation;
  // outer segments left older than a newly set year can be pushed to it
  function tryEdit(routes, rec, edit, push = false) {
    const clone = JSON.parse(JSON.stringify(rec)); clone.segments = clone.segments || {}; clone.stations = clone.stations || {};
    const put = (coll, k, p) => { const e = Object.assign({}, coll[k] || {}, p); for (const f of Object.keys(e)) if (e[f] === null || e[f] === '' || e[f] === undefined) delete e[f]; if (Object.keys(e).length) coll[k] = e; else delete coll[k]; };
    for (const [k, p] of Object.entries(edit.segments || {})) put(clone.segments, k, p);
    for (const [k, p] of Object.entries(edit.stations || {})) put(clone.stations, k, p);
    const before = analyse(routes, rec), sig = (v) => v.rule + '|' + (v.key || v.station) + '|' + (v.inner || '');
    const had = new Set(before.violations.map(sig));
    let after = analyse(routes, clone), added = after.violations.filter((v) => !had.has(sig(v)));
    const edited = new Set(Object.keys(edit.segments || {}));
    // violations on segments outside the edit, caused by the edit: these can be pushed
    const pushable = added.filter((v) => v.rule === 2 && !edited.has(v.key));
    if (push && pushable.length) {
      for (let guard = 0; guard < 50; guard++) {
        const a = analyse(routes, clone), extra = a.violations.filter((v) => v.rule === 2 && !had.has(sig(v)) && !edited.has(v.key));
        if (!extra.length) break;
        for (const v of extra) put(clone.segments, v.key, { year: v.need, src: 'Ben', note: 'pushed out with the segment inside it' });
      }
      for (const [sk, st] of Object.entries(analyse(routes, clone).stations)) if (st.own != null && st.min != null && st.own < st.min) put(clone.stations, sk, { year: st.min });
      after = analyse(routes, clone); added = after.violations.filter((v) => !had.has(sig(v)));
    }
    const refused = added.filter((v) => !(v.rule === 2 && !edited.has(v.key)));
    return { ok: !added.length, refused, pushable: added.filter((v) => v.rule === 2 && !edited.has(v.key)), rec: clone, analysis: after };
  }

  const api = { segKey, keyName, stKey, phaseOfYear, segYear, segPhase, PHASE_NAME, analyse, tryEdit, orders };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.CHRONO = api;
})(typeof self !== 'undefined' ? self : this);
