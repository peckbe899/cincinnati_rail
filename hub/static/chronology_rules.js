// The Chronology rules (Ben, 28 October; handoff "Chronology and tunnel methods", section 1.4), shared by the Chronology
// page and the checks (node). The record: chronology/segments {phase_years, segments: {key: {year, phase, src, note}},
// stations: {key: {year, src, note}}, core: {route: [segment keys]}}; the routes: chronology_lines.json (tools/chronology.py).
//
// 1. Each line's core is its opening segment (core in the record), else its earliest year set. A branch's core is the
//    segment of its parent at the junction.
// 2. Going outward from the core a segment is never older than the one it extends from.
// 3. A station opens no earlier than the earliest segment that touches it (by default that year).
// 4. A station later than that is infill (marked, not an error).
// 5. A shared segment has one year (the track's) and meets rule 2 on every line, except that a line running onto older
//    track is exempt there (its service year can be kept in the segment's `services`); its own new segments are checked.
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
  // a date: {y, m} with the month (1-12) optional (Ben, 29 October). With a month missing on either side, two dates in the
  // same year count as the same date: the order rules never break on a month that is not set.
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const monthOf = (e) => { const m = e && e.month != null && e.month !== '' ? +e.month : null; return m >= 1 && m <= 12 ? m : null; };
  const segWhen = (rec, k) => { const y = segYear(rec, k); return y == null ? null : { y, m: monthOf(segOf(rec, k)) }; };
  const before = (a, b) => !!(a && b) && (a.y < b.y || (a.y === b.y && a.m != null && b.m != null && a.m < b.m));
  const fmtWhen = (w) => (w == null ? 'not set' : (w.m ? MONTHS[w.m - 1] + ' ' : '') + w.y);
  const SYS_NAME = { metro: 'Metro', tri: 'TRI', cvx: 'CVG Express' };
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
    const O = orders(routes, rec), viol = [], ranges = {}, unset = [], exempt = [], shared = {};
    for (const r of routes) for (const k of r.segments) shared[k] = (shared[k] || 0) + 1;
    const label = keyName;
    for (const r of routes) {
      const o = O[r.id]; if (!o) continue;
      // walk outward on each side keeping the newest year inside
      for (const dir of [1, -1]) {
        const side = o.seq.filter((s) => s.out === dir);
        let inside = null, insideKey = null;
        for (const s of o.seq.filter((t) => t.core)) { const w = segWhen(rec, s.key); if (w && (!inside || before(inside, w) || (inside.y === w.y && inside.m == null && w.m != null))) { inside = w; insideKey = s.key; } }
        if (o.inner && segWhen(rec, o.inner)) { inside = segWhen(rec, o.inner); insideKey = o.inner; }
        for (const s of side) {
          const y = segWhen(rec, s.key);
          if (y == null) continue;
          // a line running onto older track (shared with another route, opened before) is exempt there; its own new
          // segments are still checked (Ben, 28 October: RER E on RER B's CVG track)
          if (before(y, inside) && (shared[s.key] || 0) > 1) { exempt.push({ key: s.key, route: r.id, year: y.y }); continue; }
          if (before(y, inside)) viol.push({ rule: 2, key: s.key, route: r.id, need: inside.y, needM: inside.m, inner: insideKey,
            text: `${label(s.key)} (${r.name}) opened ${fmtWhen(y)}, before ${label(insideKey)} inside it (${fmtWhen(inside)})` });
          if (inside == null || before(inside, y) || (inside.y === y.y && inside.m == null && y.m != null)) { inside = y; insideKey = s.key; }
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
      let minW = null; for (const k of ks) { const w = segWhen(rec, k); if (w && (!minW || before(w, minW) || (w.y === minW.y && minW.m == null && w.m != null))) minW = w; }
      const se = (rec.stations || {})[sk], ownW = se && se.year != null && se.year !== '' ? { y: +se.year, m: monthOf(se) } : null;
      const own = ownW ? ownW.y : null, min = minW ? minW.y : null, w = ownW || minW;
      stations[sk] = { year: w ? w.y : null, month: w ? w.m : null, own, min, ownW, minW, infill: before(minW, ownW) };
      if (before(ownW, minW)) viol.push({ rule: 3, station: sk, need: min, needM: minW.m, text: `${sk.split('|')[1]} station opened ${fmtWhen(ownW)}, before its track (${fmtWhen(minW)})` });
    }
    // orphans: record entries whose stations are not on any route (kept, listed)
    const segSet = new Set(routes.flatMap((r) => r.segments));
    const orphans = { segments: Object.keys(rec.segments || {}).filter((k) => !segSet.has(k)), stations: Object.keys(rec.stations || {}).filter((k) => !touch[k]) };
    return { orders: O, violations: viol, ranges, unset, stations, orphans, exempt };
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
        for (const v of extra) put(clone.segments, v.key, { year: v.need, month: v.needM ?? null, src: 'Ben', note: 'pushed out with the segment inside it' });
      }
      for (const [sk, st] of Object.entries(analyse(routes, clone).stations)) if (before(st.ownW, st.minW)) put(clone.stations, sk, { year: st.minW.y, month: st.minW.m ?? null });
      after = analyse(routes, clone); added = after.violations.filter((v) => !had.has(sig(v)));
    }
    const refused = added.filter((v) => !(v.rule === 2 && !edited.has(v.key)));
    return { ok: !added.length, refused, pushable: added.filter((v) => v.rule === 2 && !edited.has(v.key)), rec: clone, analysis: after };
  }

  // ---- the timeline (Markdown): every set opening in date order, runs of a line's segments opened together, stations
  // opened with them, infill stations and services onto older track; what is not set at the end ----
  function timeline(routes, rec, opts = {}) {
    const A = analyse(routes, rec), byId = Object.fromEntries(routes.map((r) => [r.id, r])), claimed = new Set(), ev = [];
    const sysOrder = { metro: 0, cvx: 1, tri: 2 }, rs = routes.slice().sort((a, b) => (sysOrder[a.sys] ?? 3) - (sysOrder[b.sys] ?? 3));
    for (const r of rs) {
      let run = null;
      const flush = () => { if (run) ev.push(run); run = null; };
      r.segments.forEach((k, i) => {
        const w = segWhen(rec, k);
        if (!w || claimed.has(k)) { flush(); return; }
        claimed.add(k);
        const ph = segPhase(rec, k), sameDate = run && run.w.y === w.y && run.w.m === w.m && run.phase === ph && run.end === i;
        if (!sameDate) { flush(); run = { kind: 'run', w, route: r, phase: ph, from: r.stations[i].name, segs: [], end: i }; }
        run.segs.push(k); run.to = r.stations[i + 1].name; run.end = i + 1;
        const e0 = segOf(rec, k), n = e0.src === 'default' || e0.src === 'route data' ? null : e0.note; if (n && !run.notes) run.notes = new Set(); if (n) run.notes.add(n);
      });
      flush();
    }
    // stations: with the run that reaches them first, else infill
    const stAt = new Map();
    for (const [sk, st] of Object.entries(A.stations)) if (st.ownW && st.infill) ev.push({ kind: 'infill', w: st.ownW, name: sk.split('|')[1], sys: sk.split('|')[0], track: st.minW, note: ((rec.stations || {})[sk] || {}).note });
    for (const e of ev) if (e.kind === 'run') {
      const r = e.route; const names = r.stations.slice(r.segments.indexOf(e.segs[0]), e.end + 1).map((s) => s.name);
      e.stations = names.filter((n) => { const sk = stKey(r.sys, n), st = A.stations[sk]; if (!st || st.infill || stAt.has(sk)) return false; if (st.year !== e.w.y) return false; stAt.set(sk, e); return true; });
    }
    const sv = new Map();   // services onto track that opened earlier, per route and year
    for (const [k, e] of Object.entries(rec.segments || {})) for (const [rid, y] of Object.entries(e.services || {})) {
      if (+y === segYear(rec, k)) continue; const id = rid + '|' + y; if (!sv.has(id)) sv.set(id, { kind: 'service', w: { y: +y, m: null }, route: byId[rid], keys: [] }); sv.get(id).keys.push(k); }
    ev.push(...sv.values());
    ev.sort((a, b) => a.w.y - b.w.y || (a.w.m ?? 13) - (b.w.m ?? 13) || ({ run: 0, service: 1, infill: 2 }[a.kind] - { run: 0, service: 1, infill: 2 }[b.kind]));
    const L = [];
    L.push('# Cincinnati Rail: opening timeline', '');
    L.push(`From the Chronology record (hub \`chronology/segments\`)${opts.when ? ', ' + opts.when : ''}. Dates are opening dates; the month where it is set. ` +
      'A run is a line\'s segments that opened on the same date one after another; stations are listed with the run that reached them, later stations as infill. Shared track is listed once, under the first line that has it.', '');
    const nSet = claimed.size, nAll = new Set(routes.flatMap((r) => r.segments)).size;
    L.push(`${nSet} of ${nAll} segments have a date; ${A.unset.length} are not set${A.violations.length ? `; **${A.violations.length} rule breaks** (see the Chronology)` : ''}.`, '');
    let dec = null, yr = null, mo;
    for (const e of ev) {
      const d = Math.floor(e.w.y / 10) * 10;
      if (d !== dec) { dec = d; L.push(`## ${d}s`, ''); }
      if (e.w.y !== yr) { yr = e.w.y; mo = undefined; L.push(`### ${yr}`, ''); }
      if (e.w.m !== mo) { mo = e.w.m; if (mo) L.push(`**${MONTHS[mo - 1]}**`, ''); else if (ev.some((x) => x.w.y === yr && x.w.m)) L.push('**Month not set**', ''); }
      if (e.kind === 'run') {
        const sys = e.route.sys === 'tri' ? 'TRI ' : '', ph = e.route.sys === 'tri' ? '' : e.phase ? ` (${PHASE_NAME[e.phase]})` : '';
        const shared = e.segs.flatMap((k) => routes.filter((r) => r !== e.route && r.segments.includes(k)).map((r) => r.name)), sh = [...new Set(shared)];
        L.push(`- **${sys}${e.route.name}**${ph}: ${e.from} to ${e.to} (${e.segs.length} segment${e.segs.length > 1 ? 's' : ''})` +
          (e.stations.length ? `. Stations: ${e.stations.join(', ')}` : '') + (sh.length ? `. Also used by ${sh.join(', ')}` : '') +
          (e.notes && e.notes.size ? `. _${[...e.notes].join('; ')}_` : ''));
      } else if (e.kind === 'infill') L.push(`- Infill station: **${e.name}** (${SYS_NAME[e.sys] || e.sys}; its track ${fmtWhen(e.track)})${e.note ? `. _${e.note}_` : ''}`);
      else { const ys = [...new Set(e.keys.map((k) => segYear(rec, k)))].join(', '), r = e.route, sh = e.keys.length;
        L.push(`- **${r ? (r.sys === 'tri' ? 'TRI ' : '') + r.name : 'A route'}** services begin on older track: ${sh > 2 ? sh + ' segments' : e.keys.map(keyName).join(', ')} (opened ${ys})`); }
      const nx = ev[ev.indexOf(e) + 1]; if (!nx || nx.w.y !== yr || nx.w.m !== mo) L.push('');
    }
    L.push('## Not set', '');
    const byR = {}; for (const k of A.unset) for (const r of routes) if (r.segments.includes(k)) { (byR[r.name] = byR[r.name] || []).push(k); break; }
    for (const [n, ks] of Object.entries(byR).sort((x, y) => x[0].localeCompare(y[0], 'en', { numeric: true }))) L.push(`- ${n}: ${ks.length} segment${ks.length > 1 ? 's' : ''}`);
    if (!A.unset.length) L.push('Nothing.');
    return L.join('\n') + '\n';
  }

  const api = { SYS_NAME, MONTHS, segKey, keyName, stKey, phaseOfYear, segYear, segWhen, fmtWhen, segPhase, PHASE_NAME, analyse, tryEdit, orders, timeline };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.CHRONO = api;
})(typeof self !== 'undefined' ? self : this);
