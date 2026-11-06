try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 39 (Ben, 16 October): plots locked by hand (a block whose plots Ben has edited or checked is locked: outlined with a padlock,
# its plots cannot be changed until unlocked, and the plot redraw keeps it as it stands); CVG Express on its own span beside the APEx
# bridge, over the APEx in Ludlow (option A).
# Chain: patch_page.py && patch_v34.py && patch_v36.py && patch_v37.py && patch_v38.py && patch_v39.py
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new, n=1):
    global src
    c = src.count(old)
    if c != n: sys.exit('count %d != %d for: %s' % (c, n, old[:110]))
    src = src.replace(old, new)

# ---------------------------------------------------------------- lock helpers
rep("function setBlockUse(f, code) {   // every plot of the block: its own settings give way",
    "// ---- plots locked by hand (Ben, 16 October): edits.blocks[id].lk = the date locked\n"
    "function blockLocked(bf) { return !!(bf && blockField(bf, 'lk')); }\n"
    "function plotLocked(pf) { return !!pf && pf.properties && pf.properties.layer === 'plot' && blockLocked(plotBlock(pf)); }\n"
    "function lockDate(bf) { const v = bf && blockField(bf, 'lk'); return typeof v === 'string' ? v : ''; }\n"
    "function setLockId(id, on) { const e = Object.assign({}, blockEditOf(id) || {}); if (on) e.lk = new Date().toISOString().slice(0, 10); else delete e.lk; if (Object.keys(e).length) S.edits.blocks[id] = e; else delete S.edits.blocks[id]; }\n"
    "function setBlockLock(bf, on) { const p = bf.properties; if (on) setLockId(p.id, true); else for (const id of [p.id, p.gen]) if (id && (blockEditOf(id) || {}).lk) setLockId(id, false); changed(); }\n"
    "function handEdited() {   // generated block id -> what was done to it by hand\n"
    "  const m = new Map(), add = (id, w) => { if (typeof id !== 'string' || !id) return; let b = null; const pf = S.pl && S.pl.byId.get(id); if (pf) { const bf = plotBlock(pf); b = bf ? (bf.properties.gen || bf.properties.id) : null; }\n"
    "    if (!b && id.includes('-')) b = id.split('-')[0]; if (!b) return; if (!m.has(b)) m.set(b, new Set()); m.get(b).add(w); };\n"
    "  for (const o of (S.edits.plotOps || [])) { add(o.id, 'plot steps'); for (const i of (o.ids || [])) add(i, 'plot steps'); add(o.to, 'plot steps'); }\n"
    "  for (const k of Object.keys(S.edits.plots || {})) add(k, 'plot uses or names');\n"
    "  for (const [k, e] of Object.entries(S.edits.blocks || {})) { const x = typeof e === 'string' ? { t: e } : (e || {}); const ks = Object.keys(x).filter(z => z !== 'lk'); if (ks.length) { if (!m.has(k)) m.set(k, new Set()); m.get(k).add('block type, name or use'); } }\n"
    "  return m; }\n"
    "function lockedCount() { return Object.values(S.edits.blocks || {}).filter(e => e && typeof e === 'object' && e.lk).length; }\n"
    "function lockAllEdited() { if (!S.canWrite) return; const m = handEdited(); let n = 0; for (const id of m.keys()) { if (!(blockEditOf(id) || {}).lk) { setLockId(id, true); n++; } } if (n) changed(); updateLockNote(n); renderSel(); }\n"
    "function updateLockNote(justLocked) { const el = $('lockNote'), b = $('lockAll'); if (!el) return; const n = lockedCount(), m = handEdited(); let open = 0; for (const id of m.keys()) if (!(blockEditOf(id) || {}).lk) open++;\n"
    "  el.textContent = (justLocked ? justLocked + ' block' + (justLocked === 1 ? '' : 's') + ' locked now. ' : '') + n + ' block' + (n === 1 ? '' : 's') + ' locked; ' + open + ' with hand edits not locked yet.';\n"
    "  if (b) { b.disabled = !S.canWrite || !open; b.textContent = open ? 'Lock the ' + open + ' block' + (open === 1 ? '' : 's') + ' with hand edits' : 'Every block with hand edits is locked'; } }\n"
    "function lockMsg() { $('hint').textContent = 'That block is locked: its plots were checked by hand. Unlock it in the block panel to change them.'; }\n"
    "function setBlockUse(f, code) {   // every plot of the block: its own settings give way")
# ---------------------------------------------------------------- layer panel: count and bulk lock
rep('      <p class="plotnote" id="plotNote">Loading plots</p>',
    '      <p class="plotnote" id="plotNote">Loading plots</p>\n'
    '      <p class="plotnote" id="lockNote"></p>\n'
    '      <div class="row" style="margin-top:4px"><button class="btn" id="lockAll" disabled title="Locks every block with plot steps, plot uses or names, or a block type, name or use set by hand">Lock the blocks with hand edits</button></div>')
rep("$('zReg').onclick = () => fit(701000, 4320300, 737500, 4347500);",
    "$('zReg').onclick = () => fit(701000, 4320300, 737500, 4347500);\n$('lockAll').onclick = () => lockAllEdited();")
# ---------------------------------------------------------------- drawing: outline and padlock
rep("  if (S.layers.blk) drawBlocks(v, wx0, wy0, wx1, wy1);",
    "  if (S.layers.blk) drawBlocks(v, wx0, wy0, wx1, wy1);\n  if (S.layers.blk) drawLocks(v, wx0, wy0, wx1, wy1);\n  updateLockNote();")
rep("function drawBlocks(v, x0, y0, x1, y1) {",
    "function drawLocks(v, x0, y0, x1, y1) {   // blocks whose plots are locked: accent outline, padlock in the middle\n"
    "  const vb = [x0, y0, x1, y1]; ctx.save(); ctx.strokeStyle = C.accent; ctx.lineWidth = 2.2; ctx.setLineDash([]);\n"
    "  for (const f of blockList()) { if (!blockLocked(f)) continue; if (f._bb && !bbHit(f._bb, vb)) continue; if (!(S.layers.we || !isWE(f))) continue;\n"
    "    for (const pg of polysOf(f.geometry)) { ctx.beginPath(); pathLine(pg[0]); ctx.closePath(); ctx.globalAlpha = 0.95; ctx.stroke(); }\n"
    "    if (v.s < 0.35) continue; const ps = polysOf(f.geometry); let r = ps[0][0], A = 0; for (const p of ps) { const a = Math.abs(ringArea(p[0])); if (a > A) { A = a; r = p[0]; } }\n"
    "    const [cx, cy] = ringCentroid(r), [x, y] = W2S(cx, cy), k = 1;\n"
    "    ctx.globalAlpha = 0.92; ctx.fillStyle = C.panel; ctx.beginPath(); ctx.arc(x, y + 1, 11 * k, 0, 7); ctx.fill();\n"
    "    ctx.globalAlpha = 1; ctx.fillStyle = C.accent; ctx.fillRect(x - 5.5, y - 1, 11, 8); ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x, y - 1.5, 3.6, Math.PI, 0); ctx.stroke(); ctx.lineWidth = 2.2; }\n"
    "  ctx.restore(); }\n"
    "function drawBlocks(v, x0, y0, x1, y1) {")
# ---------------------------------------------------------------- block panel
rep("    if (mix) { kv('Plots', String(mix.n)); kv('Land use', mix.list.map(x => UNAME[x.u] + ' ' + x.n).join(' · ') || 'none'); }\n    body.append(h, sub, dl);",
    "    if (mix) { kv('Plots', String(mix.n)); kv('Land use', mix.list.map(x => UNAME[x.u] + ' ' + x.n).join(' · ') || 'none'); }\n"
    "    const lkd = blockLocked(f), he = handEdited().get(p.gen || p.id); if (he) kv('Edited by hand', [...he].join(', '));\n"
    "    kv('Plots locked', lkd ? 'yes' + (lockDate(f) ? ', since ' + lockDate(f) : '') : 'no');\n"
    "    body.append(h, sub, dl);\n"
    "    { const r0 = document.createElement('div'); r0.className = 'row'; const bL = document.createElement('button'); bL.className = 'btn'; bL.setAttribute('aria-pressed', String(lkd));\n"
    "      bL.textContent = lkd ? 'Unlock the plots' : 'Lock the plots (checked by hand)'; bL.disabled = !S.canWrite; bL.addEventListener('click', () => { setBlockLock(f, !lkd); renderSel(); }); r0.append(bL); body.append(r0);\n"
    "      const nL = document.createElement('p'); nL.className = 'notes'; nL.style.marginTop = '6px'; nL.textContent = lkd ? 'Locked: these plots stand as drawn by hand. Their uses, names, splits, merges and lots cannot be changed until unlocked, and the plot redraw will leave them as they are. A street moved across the block still cuts it.' : 'Locking marks the plots as checked by hand: they cannot be changed by accident, and the plot redraw will leave them as they are.'; body.append(nL); }")
rep("b.disabled = !S.canWrite; const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = useCol(k); b.append(sw, document.createTextNode(lab)); b.addEventListener('click', () => { setBlockUse(f, k); renderSel(); }); seg2.append(b); }",
    "b.disabled = !S.canWrite || lkd; const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = useCol(k); b.append(sw, document.createTextNode(lab)); b.addEventListener('click', () => { setBlockUse(f, k); renderSel(); }); seg2.append(b); }")
rep("bc.disabled = !S.canWrite || bu === undefined;", "bc.disabled = !S.canWrite || bu === undefined || lkd;")
rep("iw.disabled = !S.canWrite || !jready();", "iw.disabled = !S.canWrite || !jready() || lkd;")
rep("br.disabled = !S.canWrite || !jready() || !mix.n;", "br.disabled = !S.canWrite || !jready() || !mix.n || lkd;")
# ---------------------------------------------------------------- plot panel
rep("    if (/~[a-z]$/.test(p.id)) kv('Cut off', 'by a street moved across the plot');\n    body.append(h, sub, dl);",
    "    if (/~[a-z]$/.test(p.id)) kv('Cut off', 'by a street moved across the plot');\n    const plk = plotLocked(f); if (plk) kv('Locked', 'checked by hand' + (lockDate(bf) ? ', since ' + lockDate(bf) : '') + '; unlock in the block panel');\n    body.append(h, sub, dl);")
rep("{ const un = document.createElement('p'); un.className = 'notes'; un.textContent = 'Unfinished: the plot lines were drawn without a check against the sheets and are to be redrawn.'; body.append(un); }",
    "{ const un = document.createElement('p'); un.className = 'notes'; un.textContent = plk ? 'Locked: this block\\u2019s plots were checked by hand and will be kept as they are when the plots are redrawn.' : 'Unfinished: the plot lines were drawn without a check against the sheets and are to be redrawn.'; body.append(un); }")
rep("b.setAttribute('aria-pressed', String((u || '') === k)); b.disabled = !S.canWrite; const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = useCol(k); b.append(sw, document.createTextNode(lab)); b.addEventListener('click', () => { setPlotUse(f, k); renderSel(); }); seg.append(b); }",
    "b.setAttribute('aria-pressed', String((u || '') === k)); b.disabled = !S.canWrite || plk; const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = useCol(k); b.append(sw, document.createTextNode(lab)); b.addEventListener('click', () => { setPlotUse(f, k); renderSel(); }); seg.append(b); }")
rep("ni.id = 'pName'; ni.className = 'namein'; ni.maxLength = 80; ni.value = nm; ni.disabled = !S.canWrite;", "ni.id = 'pName'; ni.className = 'namein'; ni.maxLength = 80; ni.value = nm; ni.disabled = !S.canWrite || plk;")
rep("bS.disabled = !S.canWrite || !jready();", "bS.disabled = !S.canWrite || !jready() || plk;")
rep("bM.disabled = !S.canWrite || !jready(); bM.setAttribute('aria-pressed', String(tool === 'merge'));", "bM.disabled = !S.canWrite || !jready() || plk; bM.setAttribute('aria-pressed', String(tool === 'merge'));")
rep("inp.id = 'pDiv'; inp.min = '2'; inp.max = '60'; inp.step = '1'; inp.style.width = '70px'; inp.disabled = !S.canWrite || !jready();",
    "inp.id = 'pDiv'; inp.min = '2'; inp.max = '60'; inp.step = '1'; inp.style.width = '70px'; inp.disabled = !S.canWrite || !jready() || plk;")
rep("bD.textContent = 'Divide along the street'; bD.disabled = !S.canWrite || !jready();", "bD.textContent = 'Divide along the street'; bD.disabled = !S.canWrite || !jready() || plk;")
rep("bR.textContent = 'Reset use and name'; bR.disabled = !S.canWrite || !S.edits.plots[p.id];", "bR.textContent = 'Reset use and name'; bR.disabled = !S.canWrite || !S.edits.plots[p.id] || plk;")
# open land into a locked plot
rep("for (const q of nbs) { const b = document.createElement('button'); b.className = 'btn'; b.disabled = !S.canWrite;",
    "for (const q of nbs) { const b = document.createElement('button'); b.className = 'btn'; b.disabled = !S.canWrite || plotLocked(q); if (plotLocked(q)) b.title = 'Locked block';")
# merge tool, split
rep("  if (!q || q === t) return;\n  if (!touching(t, q))", "  if (!q || q === t) return;\n  if (plotLocked(t) || plotLocked(q)) { lockMsg(); return; }\n  if (!touching(t, q))")
rep("  const pf = S.sel && S.sel.f, t = S.ptool; if (!pf || !t || pf.properties.id !== t.id) { redraw(); return; }",
    "  const pf = S.sel && S.sel.f, t = S.ptool; if (!pf || !t || pf.properties.id !== t.id) { redraw(); return; }\n  if (plotLocked(pf)) { S.ptool = null; lockMsg(); redraw(); return; }")
# several selected
rep("  const ml = multiList(), plots = ml.filter(f => f.properties.layer === 'plot'), streets",
    "  const ml0 = multiList(), lockedSel = ml0.filter(f => plotLocked(f)), ml = ml0, plots = ml.filter(f => f.properties.layer === 'plot' && !plotLocked(f)), streets")
rep("  if (streets.length >= 2) {\n    const plan = planMerge(streets)",
    "  { const blks = new Map(); for (const f of ml) { const bf = f.properties.layer === 'plot' ? plotBlock(f) : f.properties.layer === 'block' ? f : null; if (bf) blks.set(bf.properties.id, bf); }\n"
    "    if (blks.size) { const box = document.createElement('div'); box.className = 'stop'; box.append(P('stop-h', 'Lock'));\n"
    "      const all = [...blks.values()], nl = all.filter(b => blockLocked(b)).length; if (lockedSel.length) box.append(P('notes', lockedSel.length + ' selected plot' + (lockedSel.length === 1 ? ' is' : 's are') + ' in a locked block and left out of merging and uses.'));\n"
    "      const row = document.createElement('div'); row.className = 'row'; const bL = document.createElement('button'); bL.className = 'btn'; bL.disabled = !S.canWrite || nl === all.length; bL.textContent = 'Lock their ' + all.length + ' block' + (all.length === 1 ? '' : 's');\n"
    "      bL.addEventListener('click', () => { for (const b of all) if (!blockLocked(b)) setLockId(b.properties.id, true); changed(); renderSel(); });\n"
    "      const bU = document.createElement('button'); bU.className = 'btn'; bU.disabled = !S.canWrite || !nl; bU.textContent = 'Unlock them';\n"
    "      bU.addEventListener('click', () => { for (const b of all) for (const id of [b.properties.id, b.properties.gen]) if (id && (blockEditOf(id) || {}).lk) setLockId(id, false); changed(); renderSel(); });\n"
    "      row.append(bL, bU); box.append(row); body.append(box); } }\n"
    "  if (streets.length >= 2) {\n    const plan = planMerge(streets)")
# export
rep("p.edited = !!(S.edits.blocks[p.id] || (p.gen && S.edits.blocks[p.gen]));", "p.edited = !!(S.edits.blocks[p.id] || (p.gen && S.edits.blocks[p.gen])); p.plots_locked = blockLocked(f) ? (lockDate(f) || true) : false;")
# notes: plots
rep("<p>Plots (15 October; unfinished, tabled):",
    "<p>Locks (16 October): a block whose plots have been edited or checked by hand can be locked from its panel, several at once from a multiple selection, or every block with hand edits at once from the Layers panel. A locked block is outlined with a padlock in the middle; its plots cannot be changed until it is unlocked, and the plot redraw will keep them as they stand.</p>\n      <p>Plots (15 October; unfinished, tabled):")
# ---------------------------------------------------------------- CVG Express (option A, separate span)
old = src[src.index("  if (T.cvg) kv('CVG Express (M, 15-16)'"):]; old = old[:old.index('\n') + 1]
rep(old, "  if (T.cvg) kv('CVG Express (M, 15-16)', 'east of the APEx approach; at grade only across the Cardinal pair (N ' + fmt(T.cvg.cardinal_N[0]) + '-' + fmt(T.cvg.cardinal_N[1]) + '); own span beside the APEx bridge (' + fmt(T.cvg.span_gap, 1) + ' m between structures); in Ludlow ' + fmt(T.cvg.over_apex.clear, 1) + ' m over the APEx, onto the CS line ' + fmt(T.cvg.s_junction) + ' m from the bank; tightest curve ' + fmt(T.cvg.r_min) + ' m');\n")
rep("The CVG Express leaves M on the east side and crosses the six APEx approach tracks at grade just south of the throat, inside the throat interlocking (Ben: no flyover for a single line), then runs onto the TRIMET CS viaduct and joins the intercity pair (A-D) at the CS bridge abutment; at 6 trains an hour each way its 12 moves an hour fit between the APEx knots (:25-:50), when the Kentucky approach is quiet.",
    "The CVG Express (16 October, Ben: its own span) leaves M and stays on the east side of the APEx approach, crossing only the Cardinal pair at grade south of W 8th (the Cardinal runs about 1.4 trains an hour each way); it crosses the Ohio on its own double-track span beside the APEx bridge, about 6 m clear of it, and in Ludlow swings west over the APEx where the APEx is already below ground (about 10 m clear), joining the CS line about 650 m from the bank by a flat junction (southbound CVG trains cross the northbound CS track). The intercity pair (A-D) has the CS bridge to itself.")
rep("In Ludlow (Ben: 4 APEx tracks, at least 2 intercity, 6 to 8 in all) the two CS tracks carry the intercity trains and the CVG Express across the 1922 bridge and on at grade along the TRIMET CS line;",
    "Eight tracks cross the river: the CS bridge (intercity 2), the APEx bridge (4) and the CVG span (2). In Ludlow (Ben: 4 APEx tracks, at least 2 intercity, 6 to 8 in all) the two CS tracks carry the intercity trains across the 1922 bridge and on at grade along the TRIMET CS line, with the CVG Express from the Ludlow junction;")
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v39', len(src))
