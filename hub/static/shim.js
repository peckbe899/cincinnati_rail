// The hub's stand-in for the artifact runtime (window.claude): the page's database is the hub's one database, live
// over server-sent events, so a record saved in one view reaches every open view. Also a small bar to move between
// the views and see the pipeline.
(() => {
  const api = (u, o) => fetch(u, o).then((r) => { if (!r.ok) throw Object.assign(new Error(r.status + ' ' + u), { code: r.status }); return r.status === 204 ? null : r.json(); });
  const enc = encodeURIComponent;
  const docL = new Map(), collL = new Map();   // path -> Set(cb), collection -> Set(cb)
  const snapDoc = (p, r) => ({ id: p.split('/').pop(), ref: { path: p }, exists: !!r, data: () => (r ? JSON.parse(JSON.stringify(r.data)) : undefined), metadata: { hasPendingWrites: false, fromCache: false } });
  const fireDoc = async (p) => { const cbs = docL.get(p); if (!cbs || !cbs.size) return; const r = await api('/api/doc?p=' + enc(p)); cbs.forEach((cb) => { try { cb(snapDoc(p, r)); } catch (e) { console.error(e); } }); };
  const fireColl = async (c) => {
    const cbs = collL.get(c); if (!cbs || !cbs.size) return;
    const rows = await api('/api/coll?c=' + enc(c));
    const q = { docs: rows.map((r) => snapDoc(r.path, r)), size: rows.length, empty: !rows.length, metadata: { hasPendingWrites: false, fromCache: false } };
    q.forEach = (f) => q.docs.forEach(f);
    cbs.forEach((cb) => { try { cb(q); } catch (e) { console.error(e); } });
  };
  const listen = (map, key, cb, fire) => { if (!map.has(key)) map.set(key, new Set()); map.get(key).add(cb); fire(key).catch(console.error); return () => map.get(key).delete(cb); };
  const doc = (p) => ({
    id: p.split('/').pop(), path: p,
    get: async () => snapDoc(p, await api('/api/doc?p=' + enc(p))),
    set: (data) => api('/api/doc?p=' + enc(p), { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(data) }),
    update: (data) => api('/api/doc?p=' + enc(p), { method: 'PATCH', headers: { 'content-type': 'application/json' }, body: JSON.stringify(data) }),
    delete: () => api('/api/doc?p=' + enc(p), { method: 'DELETE' }),
    onSnapshot: (cb) => listen(docL, p, cb, fireDoc),
  });
  const collection = (c) => ({
    path: c, doc: (id) => doc(c + '/' + id),
    get: async () => { const rows = await api('/api/coll?c=' + enc(c)); const q = { docs: rows.map((r) => snapDoc(r.path, r)), size: rows.length, empty: !rows.length }; q.forEach = (f) => q.docs.forEach(f); return q; },
    onSnapshot: (cb) => listen(collL, c, cb, fireColl),
  });
  const ME = 'local';
  const user = { id: async () => ME, me: async () => ({ id: ME, name: 'Ben' }), can: async () => true, canEdit: async () => true };
  const downloads = {
    save: async ({ filename, data, type }) => {
      const blob = data instanceof Blob ? data : new Blob([data], { type: type || 'application/octet-stream' });
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = filename || 'download';
      document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    },
  };
  window.claude = { use: async (k) => ({ db: { doc, collection }, user, downloads }[k] || null) };

  // ---- live events ----
  const bar = { el: null, runs: {} };
  const es = new EventSource('/api/events');
  es.onmessage = (m) => {
    const ev = JSON.parse(m.data);
    if (ev.t === 'doc') {
      fireDoc(ev.p).catch(console.error);
      const c = ev.p.includes('/') ? ev.p.slice(0, ev.p.lastIndexOf('/')) : '';
      fireColl(c).catch(console.error);
    } else if (ev.t === 'run') { bar.runs[ev.job] = ev.state; drawBar(); }
    else if (ev.t === 'files' && ev.site === SITE) { filesChanged = true; drawBar(); }
  };
  es.onerror = () => { offline = true; drawBar(); };
  es.onopen = () => { offline = false; drawBar(); };

  // ---- the hub bar ----
  const SITE = location.pathname.split('/')[1] || '';
  let filesChanged = false, offline = false;
  const VIEWS = [['deck', 'Deck'], ['profiles', 'Profiles'], ['3d', '3D']];
  const HOME = '<a href="/" title="Home: the hub page" style="display:inline-flex;align-items:center;gap:5px;background:#fff;color:#14181c;'
    + 'text-decoration:none;font-weight:700;padding:3px 10px 3px 8px;border-radius:999px;margin-right:4px">'
    + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    + '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/></svg>Home</a>';
  function drawBar() {
    if (!document.body) return;
    if (!bar.el) {
      bar.el = document.createElement('div');
      bar.el.style.cssText = 'position:fixed;left:50%;bottom:10px;transform:translateX(-50%);z-index:99999;display:flex;gap:6px;align-items:center;'
        + 'font:12px/1.2 system-ui,sans-serif;background:rgba(20,24,28,.88);color:#eef;padding:5px 8px;border-radius:999px;box-shadow:0 2px 8px rgba(0,0,0,.3)';
      document.body.appendChild(bar.el);
    }
    const running = Object.entries(bar.runs).filter(([, s]) => s === 'running').map(([j]) => j);
    const failed = Object.entries(bar.runs).filter(([, s]) => s === 'failed').map(([j]) => j);
    bar.el.innerHTML = (SITE ? HOME : "") + VIEWS.map(([k, n]) => `<a href="/${k}${k ? '/' : ''}" style="color:${k === SITE ? '#fff' : '#9cf'};text-decoration:none;font-weight:${k === SITE ? 700 : 400}">${n}</a>`).join('<span style="opacity:.4">·</span>')
      + (offline ? ' <span style="color:#f99">hub offline</span>' : '')
      + (running.length ? ` <span style="color:#fd6">updating: ${running.join(', ')}</span>` : '')
      + (failed.length ? ` <a href="/#runs" style="color:#f99">failed: ${failed.join(', ')}</a>` : '')
      + (filesChanged ? ' <button style="font:inherit;border:0;border-radius:999px;padding:2px 8px;background:#fd6;cursor:pointer" onclick="location.reload()">New data: reload</button>' : '');
  }
  document.addEventListener('DOMContentLoaded', drawBar);
})();
