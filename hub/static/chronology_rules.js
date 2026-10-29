// The Chronology's shared logic (Ben, 28-29 October), for the Chronology page and node (the timeline, the tests). The
// record: chronology/segments {phase_years, segments: {key: {year, month, phase, src, note, services}}, stations: {key:
// {year, month, src, note}}} (its `core` lists are no longer read); the routes: chronology_lines.json (tools/chronology.py).
//
// No order rules (Ben, 29 October): parts of a line are built before others, the RER runs on old railroad rights of way
// and the central tunnels come last, so any segment may open in any year. What is kept, as information only:
// - a station opens with the earliest segment that touches it, unless its own year is set; a later one is infill;
// - shared TRI track is one segment (one year: the track's), each route's service year can be kept in `services`;
// - unset segments are listed, and record entries whose stations are no longer on a line (orphans).
(function (root) {
  // Metro: per line (no Metro lines share track); TRI: the station pair, so shared track is one segment
  const segKey = (sys, a, b, line) => { const [x, y] = [a, b].sort(); return sys === 'metro' ? `metro|${line}|${x}|${y}` : `${sys}|${x}|${y}`; };
  const keyName = (k) => k.split('|').slice(k.startsWith('metro|') ? 2 : 1).join(' to ');
  const stKey = (sys, n) => `${sys}|${n}`;
  const phaseOfYear = (rec, y) => { if (y == null) return null; for (const [a, b, p] of rec.phase_years || []) if (y >= a && y <= b) return p; return null; };
  const segOf = (rec, k) => (rec.segments || {})[k] || {};
  const segYear = (rec, k) => { const y = segOf(rec, k).year; return y == null || y === '' ? null : +y; };
  const segPhase = (rec, k) => segOf(rec, k).phase || phaseOfYear(rec, segYear(rec, k));
  // a date: {y, m} with the month (1-12) optional (Ben, 29 October); a missing month sorts after the set ones of its year
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const monthOf = (e) => { const m = e && e.month != null && e.month !== '' ? +e.month : null; return m >= 1 && m <= 12 ? m : null; };
  const segWhen = (rec, k) => { const y = segYear(rec, k); return y == null ? null : { y, m: monthOf(segOf(rec, k)) }; };
  const before = (a, b) => !!(a && b) && (a.y < b.y || (a.y === b.y && a.m != null && b.m != null && a.m < b.m));
  const fmtWhen = (w) => (w == null ? 'not set' : (w.m ? MONTHS[w.m - 1] + ' ' : '') + w.y);
  const SYS_NAME = { metro: 'Metro', tri: 'TRI', cvx: 'CVG Express' };
  const PHASE_NAME = { 1: 'Phase 1', 2: 'Phase 2', 3: 'Phase 3', later: 'Later' };

  function analyse(routes, rec) {
    const unset = [];
    for (const r of routes) for (const k of r.segments) if (segYear(rec, k) == null && !segOf(rec, k).phase && !unset.includes(k)) unset.push(k);
    // stations: with their earliest track unless set; later is infill (information)
    const stations = {}, touch = {};
    for (const r of routes) r.segments.forEach((k, i) => { for (const s of [r.stations[i], r.stations[i + 1]]) { const sk = stKey(r.sys, s.name); (touch[sk] = touch[sk] || new Set()).add(k); } });
    const pseudo = new Set(routes.flatMap((r) => r.stations.filter((s) => s.pseudo).map((s) => stKey(r.sys, s.name))));
    for (const [sk, ks] of Object.entries(touch)) {
      if (pseudo.has(sk)) continue;   // junction points are not stations
      let minW = null; for (const k of ks) { const w = segWhen(rec, k); if (w && (!minW || before(w, minW) || (w.y === minW.y && minW.m == null && w.m != null))) minW = w; }
      const se = (rec.stations || {})[sk], ownW = se && se.year != null && se.year !== '' ? { y: +se.year, m: monthOf(se) } : null;
      const own = ownW ? ownW.y : null, min = minW ? minW.y : null, w = ownW || minW;
      stations[sk] = { year: w ? w.y : null, month: w ? w.m : null, own, min, ownW, minW, infill: before(minW, ownW) };
    }
    // orphans: record entries whose stations are not on any route (kept, listed)
    const segSet = new Set(routes.flatMap((r) => r.segments));
    const orphans = { segments: Object.keys(rec.segments || {}).filter((k) => !segSet.has(k)), stations: Object.keys(rec.stations || {}).filter((k) => !touch[k]) };
    return { unset, stations, orphans };
  }

  // an edit: {segments: {key: patch}, stations: {key: patch}}, applied as it is (a field set to null or '' is removed)
  function applyEdit(routes, rec, edit) {
    const clone = JSON.parse(JSON.stringify(rec)); clone.segments = clone.segments || {}; clone.stations = clone.stations || {};
    const put = (coll, k, p) => { const e = Object.assign({}, coll[k] || {}, p); for (const f of Object.keys(e)) if (e[f] === null || e[f] === '' || e[f] === undefined) delete e[f]; if (Object.keys(e).length) coll[k] = e; else delete coll[k]; };
    for (const [k, p] of Object.entries(edit.segments || {})) put(clone.segments, k, p);
    for (const [k, p] of Object.entries(edit.stations || {})) put(clone.stations, k, p);
    return { rec: clone, analysis: analyse(routes, clone) };
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
      const pseudo = new Set(r.stations.filter((s) => s.pseudo).map((s) => s.name));
      e.stations = names.filter((n) => { if (pseudo.has(n)) return false; const sk = stKey(r.sys, n), st = A.stations[sk]; if (!st || st.infill || stAt.has(sk)) return false; if (st.year !== e.w.y) return false; stAt.set(sk, e); return true; });
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
    L.push(`${nSet} of ${nAll} segments have a date; ${A.unset.length} are not set.`, '');
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

  const api = { SYS_NAME, MONTHS, segKey, keyName, stKey, phaseOfYear, segYear, segWhen, fmtWhen, segPhase, PHASE_NAME, analyse, applyEdit, timeline };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.CHRONO = api;
})(typeof self !== 'undefined' ? self : this);
