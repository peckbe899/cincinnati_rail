try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import re, sys
SP = _ws.DATA
src = open(SP + 'deckpage/index_v32.html').read()
engine = open(_ws.CODE + 'plots/engine.js').read()
def rep(old, new, n=1):
    global src
    c = src.count(old)
    if c != n: sys.exit('count %d != %d for: %s' % (c, n, old[:90]))
    src = src.replace(old, new)

# ---- head: geometry library
rep('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">',
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">\n<script src="https://cdn.jsdelivr.net/npm/jsts@2.12.1/dist/jsts.min.js" async></script>')
# ---- colours for land use
rep("  --tower: #8a6447; --landmark: #c9a227; --worship: #a0607e; --school: #5f8fb4; --hospital: #c45a5a; --industrial: #8b9297;\n  --font-ui",
    "  --tower: #8a6447; --landmark: #c9a227; --worship: #a0607e; --school: #5f8fb4; --hospital: #c45a5a; --industrial: #8b9297;\n  --u-r: #f0cf6a; --u-m: #ef9d4a; --u-c: #df5b57; --u-i: #9a7cc7; --u-w: #b5708f; --u-v: #5f95c9; --u-p: #a5aab0; --u-o: #8cc27a; --u-n: #dfe4e2;\n  --font-ui")
DARK_U = "    --u-r: #b9993e; --u-m: #c07534; --u-c: #b0423f; --u-i: #7a60a3; --u-w: #8f5a75; --u-v: #4a77a3; --u-p: #6c7176; --u-o: #5f8a4e; --u-n: #2c3a3c;\n"
rep("    --tower: #6e4f37; --landmark: #b8952a; --worship: #8f5a75; --school: #4f7899; --hospital: #a84c4c; --industrial: #5f666b;\n    color-scheme: dark;\n  }\n}",
    "    --tower: #6e4f37; --landmark: #b8952a; --worship: #8f5a75; --school: #4f7899; --hospital: #a84c4c; --industrial: #5f666b;\n" + DARK_U + "    color-scheme: dark;\n  }\n}")
rep("  --tower: #6e4f37; --landmark: #b8952a; --worship: #8f5a75; --school: #4f7899; --hospital: #a84c4c; --industrial: #5f666b;\n  color-scheme: dark;\n}",
    "  --tower: #6e4f37; --landmark: #b8952a; --worship: #8f5a75; --school: #4f7899; --hospital: #a84c4c; --industrial: #5f666b;\n" + DARK_U.replace('    ', '  ', 1) + "  color-scheme: dark;\n}")
rep(".empty { color: var(--muted); font-size: 14px; }",
    ".empty { color: var(--muted); font-size: 14px; }\n.colby { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--muted); margin-top: 8px; }\n.colby select { min-height: 28px; padding: 2px 6px; }\n.seg .btn.use { min-height: 28px; padding: 2px 8px; font-size: 13px; }\n.plotnote { font-size: 12px; color: var(--muted); margin: 6px 0 0; }")
# ---- layers panel: plots, colour by, status line
rep('        <label><input type="checkbox" id="lIdx"> Sheet index</label>\n      </div>',
    '        <label><input type="checkbox" id="lIdx"> Sheet index</label>\n        <label><input type="checkbox" id="lPlt" checked> Plots</label>\n      </div>\n      <div class="colby"><label for="colBy">Colour blocks and plots by</label><select id="colBy"><option value="use" selected>Land use</option><option value="type">Block type</option></select></div>')
rep('      <div class="op"><label for="opBlk">Blocks</label><input type="range" id="opBlk" min="0" max="100" value="70"></div>\n    </section>',
    '      <div class="op"><label for="opBlk">Blocks</label><input type="range" id="opBlk" min="0" max="100" value="70"></div>\n      <p class="plotnote" id="plotNote">Loading plots</p>\n    </section>')
# ---- legend: land use
rep('        <div><span class="sw" style="background:var(--lower);opacity:.45"></span>Lower platform</div>\n      </div>',
    '        <div><span class="sw" style="background:var(--lower);opacity:.45"></span>Lower platform</div>\n      </div>\n      <h2 style="margin-top:12px">Land use (blocks and plots)</h2>\n      <div class="legend">\n'
    + ''.join('        <div><span class="sw" style="background:var(--u-%s)"></span>%s</div>\n' % (k, n) for k, n in [('r', 'Residential'), ('m', 'Mixed use'), ('c', 'Commercial'), ('i', 'Industrial'), ('w', 'Religious'), ('v', 'Civic'), ('p', 'Parking'), ('o', 'Open or vacant'), ('n', 'Not set')])
    + '        <div><span class="sw" style="background:repeating-linear-gradient(135deg,var(--warn) 0 1px,transparent 1px 4px);outline:1px dashed var(--warn)"></span>Open land left by a moved street</div>\n      </div>')
# ---- sources note
rep('      <p>CUT tracks: APEx lines from the APEx Routes KMZ;',
    '      <p>Plots (15 October): every block is divided into plots, measured and snapped. On each block face that fronts a street the lot width is measured from the 1904 sheet (the repeat of its printed lot lines), the lots are cut square to the street at that width, and each cut moves onto the nearest printed lot line within 2.5 m; faces with no clear repeat use even widths. Corner lots front the longer face, and land deeper than the lots on very deep blocks is left as interior plots. Deck blocks are divided the same way at the density of the basin around them. The use is filled in only where the sheet says it plainly: 5,679 printed labels (church, school, hall, engine house, store, saloon, office, bank, garage, livery, factory, works, a named company, mill, foundry, brewery, warehouse and the like) were read off the sheets and placed on 4,227 plots; a plot with labels of more than one kind takes the commonest. Unlabelled plots, the dwellings among them, are not set, and blocks typed as worship, civic, school, hospital, industrial, square, park or planting lend their plots that use until a plot is set. The plots follow the streets as they are edited: a street moved, widened or lengthened cuts the plots under its new corridor, and the land its old corridor leaves goes to the plots that front it, out to the old centre line, so blocks stretch and join; land no plot fronts is left as open land. Plots can be split along a line, merged with a neighbour, divided into lots, and given a use and a name, one by one or a whole block at a time.</p>\n      <p>CUT tracks: APEx lines from the APEx Routes KMZ;')
# ---- state
rep("  layers: { san: true, rel: false, blk: true, str: true, met: true, rer: true, trk: true, lab: true, idx: false, we: true, s12: false },",
    "  layers: { san: true, rel: false, blk: true, str: true, met: true, rer: true, trk: true, lab: true, idx: false, we: true, s12: false, plt: true }, colorBy: 'use', plots0: null, pl: null, ptool: null, pendingSel: null, plNote: '',")
rep("  edits: { streets: {}, blocks: {}, transit: {}, stations: {} }, tf: []", "  edits: { streets: {}, blocks: {}, transit: {}, stations: {}, plots: {}, plotOps: [] }, tf: []")
rep("'school','hospital','industrial']) C[k] = css('--' + k); }", "'school','hospital','industrial','u-r','u-m','u-c','u-i','u-w','u-v','u-p','u-o','u-n']) C[k] = css('--' + k); }")
# ---- blocks read through the new edit model
rep("function blockEdit(f) { return S.edits.blocks[f.properties.id]; }\nfunction blockType(f) { const e = blockEdit(f); return (typeof e === 'string' ? e : e && e.t) || f.properties.type; }\nfunction blockName(f) { const e = blockEdit(f); return e && typeof e === 'object' ? (e.n || '') : ''; }",
    "function blockType(f) { return blockField(f, 't') || f.properties.type; }\nfunction blockName(f) { return blockField(f, 'n') || ''; }")
# ---- engine after the feature helpers
rep("const feats = layer => S.deck.features.filter(f => f.properties.layer === layer && (S.layers.we || !isWE(f)));\n",
    "const feats = layer => S.deck.features.filter(f => f.properties.layer === layer && (S.layers.we || !isWE(f)));\n" + engine)
rep("function featLabel(f) { const p = f.properties; return p.layer === 'street'", "function featLabel(f) { const p = f.properties; if (p.layer === 'plot') return plotName(f) || 'Plot ' + p.id; if (p.layer === 'open') return 'Open land'; return p.layer === 'street'")
# ---- drawing: blocks, plots, open land
rep("  if (S.layers.blk) for (const f of feats('block')) { const t = blockType(f), big = t === 'tower' || t === 'landmark'; fillPoly(f.geometry, C[BT[t]] || C.bldg, C.ink, big ? 1.6 : 0.6, big ? Math.min(1, S.op.blk + 0.15) : S.op.blk); }",
    "  if (S.layers.blk) drawBlocks(v, wx0, wy0, wx1, wy1);")
rep("function drawRerStruct(v) {", r'''function drawBlocks(v, x0, y0, x1, y1) {
  // blocks by type or by their leading use; zoomed in, the plots, each filled by its use, then block outlines and open land
  const useMode = S.colorBy === 'use', showP = S.layers.plt && !!S.pl && v.s >= PZ, vb = [x0, y0, x1, y1];
  const list = blockList().filter(f => (S.layers.we || !isWE(f)) && (!f._bb || bbHit(f._bb, vb)));
  for (const f of list) { if (showP && useMode) break; const t = blockType(f), big = t === 'tower' || t === 'landmark';
    const lead = useMode ? blockUseMix(f).lead : null; fillPoly(f.geometry, useMode ? useCol(lead) : (C[BT[t]] || C.bldg), showP ? null : C.ink, big ? 1.6 : 0.6, (useMode && !lead ? 0.35 : 1) * (big ? Math.min(1, S.op.blk + 0.15) : S.op.blk)); }
  if (!S.pl) return;
  const vis = [], open = [];
  if (showP || v.s >= 0.4) { const seen = new Set();
    for (let gx = Math.floor(x0 / 100); gx <= Math.floor(x1 / 100); gx++) for (let gy = Math.floor(y0 / 100); gy <= Math.floor(y1 / 100); gy++) for (const pf of (S.pl.grid.get(gx + ',' + gy) || [])) {
      if (seen.has(pf) || !bbHit(pf.bb, vb)) continue; seen.add(pf);
      if (pf.properties.layer === 'open') open.push(pf); else if (showP && (S.layers.we || !pf.properties.we)) vis.push(pf); } }
  if (showP) {
    if (useMode) { const by = new Map(); for (const pf of vis) { const u = plotUse(pf)[0] || ''; if (!by.has(u)) by.set(u, []); by.get(u).push(pf); }
      ctx.save(); for (const [u, ps] of by) { ctx.globalAlpha = u ? S.op.blk : S.op.blk * 0.35; ctx.fillStyle = useCol(u); ctx.beginPath(); for (const pf of ps) pathPoly(pf.geometry); ctx.fill('evenodd'); } ctx.restore(); }
    ctx.save(); ctx.strokeStyle = C.ink; ctx.globalAlpha = 0.42; ctx.lineWidth = v.s >= 2.5 ? 0.9 : 0.6; ctx.lineJoin = 'round'; ctx.beginPath(); for (const pf of vis) pathPoly(pf.geometry); ctx.stroke(); ctx.restore();
    ctx.save(); ctx.strokeStyle = C.ink; ctx.lineJoin = 'round';
    for (const f of list) { const t = blockType(f), big = t === 'tower' || t === 'landmark'; ctx.globalAlpha = 0.85; ctx.lineWidth = big ? 2.2 : 1.2; ctx.beginPath(); pathPoly(f.geometry); ctx.stroke(); }
    ctx.restore();
    if (S.layers.lab && v.s >= 1.6) { ctx.save(); ctx.font = '600 11px ' + css('--font-ui'); ctx.textBaseline = 'middle';
      for (const pf of vis) { const nm = plotName(pf); if (!nm) continue; const r = pf.geometry.coordinates[0], c = pf._c || (pf._c = [r.reduce((a, q) => a + q[0], 0) / r.length, r.reduce((a, q) => a + q[1], 0) / r.length]), [x, y] = W2S(c[0], c[1]), tw = ctx.measureText(nm).width;
        ctx.fillStyle = C.panel; ctx.globalAlpha = 0.85; ctx.fillRect(x - tw / 2 - 2, y - 7, tw + 4, 14); ctx.globalAlpha = 1; ctx.fillStyle = C.ink; ctx.fillText(nm, x - tw / 2, y); }
      ctx.restore(); }
  }
  if (open.length) { ctx.save();
    if (!S.hatch || S.hatchC !== C.warn) { const c = document.createElement('canvas'); c.width = c.height = 7; const g = c.getContext('2d'); g.strokeStyle = C.warn; g.lineWidth = 1; g.beginPath(); g.moveTo(-1, 8); g.lineTo(8, -1); g.stroke(); S.hatch = ctx.createPattern(c, 'repeat'); S.hatchC = C.warn; }
    ctx.globalAlpha = 0.9; ctx.fillStyle = S.hatch; ctx.beginPath(); for (const o of open) pathPoly(o.geometry); ctx.fill('evenodd');
    ctx.setLineDash([4, 3]); ctx.strokeStyle = C.warn; ctx.lineWidth = 1; ctx.stroke(); ctx.restore(); }
}
function drawRerStruct(v) {''')
# selection: the split line being drawn
rep("  } else { ctx.beginPath(); pathPoly(f.geometry); ctx.stroke(); }\n  ctx.restore();\n}",
    "  } else { ctx.beginPath(); pathPoly(f.geometry); ctx.stroke(); }\n  const d = S.drag; if (d && d.mode === 'cut') { const a = W2S(d.p0[0], d.p0[1]), b = W2S(d.p1[0], d.p1[1]); ctx.setLineDash([6, 4]); ctx.lineWidth = 2; ctx.globalAlpha = 1; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); ctx.setLineDash([]); }\n  ctx.restore();\n}")
rep("function draw() {\n  if (!S.deck) return;", "function draw() {\n  if (!S.deck) return; const tD = performance.now();")
rep("  drawSelection();\n  drawScale(r);\n}", "  drawSelection();\n  drawScale(r); S.drawMs = performance.now() - tD;\n}")
rep("Drag to pan, scroll or pinch to zoom. Click a street or block to see it.</div>", "Drag to pan, scroll or pinch to zoom. Click a street, block or plot to see it.</div>")
rep("Nothing selected. Click a street, a block or a civic space on the plan.", "Nothing selected. Click a street, a block, a plot or a civic space on the plan. Plots show from about 1 pixel per metre.")
rep("'Drag to pan, scroll or pinch to zoom. Click a street, line, station or block to see it; click again to step through what is under it.'", "'Drag to pan, scroll or pinch to zoom. Click a street, line, station, block or plot to see it; click again to step through what is under it.'")
# ---- picking: open land, plots, live blocks
rep("  if (S.layers.blk) for (const f of feats('block')) if (polysOf(f.geometry).some(q => inPoly(p, q))) { out.push(f); break; }\n  return out;",
    "  if (S.layers.blk && S.pl && S.view.s >= 0.4) { const o = openAt(p); if (o) out.push(o); }\n  if (S.layers.blk && S.layers.plt && S.pl && S.view.s >= PZ) { const q = plotAt(p); if (q) out.push(q); }\n  const pb = [p[0], p[1], p[0], p[1]];\n  if (S.layers.blk) for (const f of blockList()) if ((S.layers.we || !isWE(f)) && (!f._bb || bbHit(f._bb, pb)) && polysOf(f.geometry).some(q => inPoly(p, q))) { out.push(f); break; }\n  return out;")
# ---- selection: cancel a plot tool when something else is chosen
rep("function select(f) { S.sel = f ? { f } : null; renderSel(); redraw(); }",
    "function select(f) { S.sel = f ? { f } : null; if (S.ptool && (!f || f.properties.id !== S.ptool.id)) { S.ptool = null; setTool(S.tool); } renderSel(); redraw(); }")
# ---- block panel
OLD_BLOCK = src[src.index("  } else if (L === 'block') {"):src.index("  } else if (L === 'transit') {")]
NEW_BLOCK = r'''  } else if (L === 'block') {
    const t = blockType(f), nm = blockName(f); h.textContent = nm || p.name || 'Block ' + p.id; sub.textContent = (isWE(f) ? 'Basin · 1904 Sanborn · ' : p.side === 'WV' ? 'West side of the valley, off the deck · ' : p.side === 'new' ? 'New block on open land · ' : 'On the deck · ') + (t === 'square' ? 'square with vents' : t);
    kv('Area', fmt(p.area_m2) + ' m²'); if (p.side !== 'new') kv('Generated as', p.type); kv('Now', t);
    if (p.gen && p.gen !== p.id) kv('Part of', 'Block ' + p.gen + ', cut by a street');
    if (p.joined) kv('Joined with', p.joined.filter(x => x !== p.gen).map(x => 'Block ' + x).join(', ') + ' (a street between them moved)');
    const mix = S.pl ? blockUseMix(f) : null;
    if (mix) { kv('Plots', String(mix.n)); kv('Land use', mix.list.map(x => UNAME[x.u] + ' ' + x.n).join(' · ') || 'none'); }
    body.append(h, sub, dl);
    const seg = document.createElement('div'); seg.className = 'seg';
    for (const [k, lab] of BLOCK_TYPES) { const b = document.createElement('button'); b.className = 'btn'; b.setAttribute('aria-pressed', String(t === k)); b.disabled = !S.canWrite; const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = C[BT[k]]; b.append(sw, document.createTextNode(lab)); b.addEventListener('click', () => { setBlockEdit(f, { t: k }); renderSel(); }); seg.append(b); }
    body.append(seg);
    const nl = document.createElement('label'); nl.className = 'notes'; nl.htmlFor = 'bName'; nl.textContent = 'Name on the plan (e.g. Carew Tower, Music Hall)'; nl.style.display = 'block'; nl.style.marginTop = '10px';
    const ni = document.createElement('input'); ni.type = 'text'; ni.id = 'bName'; ni.className = 'namein'; ni.maxLength = 80; ni.value = nm; ni.disabled = !S.canWrite; ni.placeholder = 'No name';
    ni.addEventListener('change', () => { setBlockEdit(f, { n: ni.value.trim() }); renderSel(); });
    body.append(nl, ni);
    if (mix) {
      const box = document.createElement('div'); box.className = 'stop'; const hh = document.createElement('p'); hh.className = 'stop-h'; hh.textContent = 'Land use for every plot in the block'; box.append(hh);
      const bu = blockField(f, 'u'), seg2 = document.createElement('div'); seg2.className = 'seg';
      for (const [k, lab] of USES.concat([['', 'Not set']])) { const b = document.createElement('button'); b.className = 'btn use'; b.setAttribute('aria-pressed', String(bu === k)); b.disabled = !S.canWrite; const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = useCol(k); b.append(sw, document.createTextNode(lab)); b.addEventListener('click', () => { setBlockUse(f, k); renderSel(); }); seg2.append(b); }
      const row = document.createElement('div'); row.className = 'row'; const bc = document.createElement('button'); bc.className = 'btn'; bc.textContent = 'Clear the block setting'; bc.disabled = !S.canWrite || bu === undefined; bc.addEventListener('click', () => { setBlockEdit(f, { u: undefined }); renderSel(); }); row.append(bc);
      const n = document.createElement('p'); n.className = 'notes'; n.style.marginTop = '8px'; n.textContent = 'Setting the block gives every plot in it that use, replacing their own settings; a plot changed afterwards keeps its change. Cleared, plots go back to the sheet labels and the block type. Zoom in to see and select single plots.';
      box.append(seg2, row, n); body.append(box);
      const box2 = document.createElement('div'); box2.className = 'stop'; const h2 = document.createElement('p'); h2.className = 'stop-h'; h2.textContent = 'Re-divide the block into lots'; box2.append(h2);
      const row2 = document.createElement('div'); row2.className = 'row'; row2.style.marginTop = '0'; const lw = document.createElement('label'); lw.htmlFor = 'bLot'; lw.textContent = 'Lot width (m)';
      const iw = document.createElement('input'); iw.type = 'number'; iw.id = 'bLot'; iw.min = '3'; iw.max = '60'; iw.step = '0.1'; iw.value = '7.6'; iw.style.width = '80px'; iw.disabled = !S.canWrite || !jready();
      const br = document.createElement('button'); br.className = 'btn'; br.textContent = 'Re-divide'; br.disabled = !S.canWrite || !jready() || !mix.n;
      br.addEventListener('click', () => { const ps = S.pl.byBlock.get(p.id) || []; if (!ps.length) return; pushOp({ t: 'r', id: 'R' + Date.now().toString(36), ids: ps.map(q => q.properties.id), w: Math.max(3, Math.min(60, parseFloat(iw.value) || 7.6)), a: longSide(f) }); });
      row2.append(lw, iw, br); box2.append(row2);
      const n3 = document.createElement('p'); n3.className = 'notes'; n3.style.marginTop = '8px'; n3.textContent = 'Replaces the plots with lots square to the block\u2019s longest side, two rows back to back where the block is deeper than 55 m. Useful where a new street has cut a block into odd pieces. The 1904 sheet labels carry over; uses set on the old plots do not (undo brings them back).';
      box2.append(n3); body.append(box2);
    }
    alsoHere(f, body);
  } else if (L === 'plot') {
    const [u, src] = plotUse(f), bf = plotBlock(f), nm = plotName(f), tool = S.ptool && S.ptool.id === p.id ? S.ptool.mode : null;
    h.textContent = nm || 'Plot ' + p.id; sub.textContent = UNAME[u || ''] + (src ? ' · ' + USRC[src] : '');
    kv('Area', fmt(f.area) + ' m²'); const sf = p.street && S.streetById.get(p.street); if (sf) kv('Fronts', sf.properties.name);
    kv('Block', bf ? featLabel(bf) : 'Block ' + p.block);
    if (p.lab && p.lab.length) kv('On the 1904 sheet', p.lab.join(' · '));
    if (/~[a-z]$/.test(p.id)) kv('Cut off', 'by a street moved across the plot');
    body.append(h, sub, dl);
    const seg = document.createElement('div'); seg.className = 'seg';
    for (const [k, lab] of USES.concat([['', 'Not set']])) { const b = document.createElement('button'); b.className = 'btn use'; b.setAttribute('aria-pressed', String((u || '') === k)); b.disabled = !S.canWrite; const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = useCol(k); b.append(sw, document.createTextNode(lab)); b.addEventListener('click', () => { setPlotUse(f, k); renderSel(); }); seg.append(b); }
    body.append(seg);
    const nl = document.createElement('label'); nl.className = 'notes'; nl.htmlFor = 'pName'; nl.textContent = 'Name (optional)'; nl.style.display = 'block'; nl.style.marginTop = '10px';
    const ni = document.createElement('input'); ni.type = 'text'; ni.id = 'pName'; ni.className = 'namein'; ni.maxLength = 80; ni.value = nm; ni.disabled = !S.canWrite; ni.placeholder = 'No name';
    ni.addEventListener('change', () => { setPlotField(f, 'n', ni.value.trim() || undefined); changed(); renderSel(); });
    body.append(nl, ni);
    const box = document.createElement('div'); box.className = 'stop'; const hh = document.createElement('p'); hh.className = 'stop-h'; hh.textContent = 'Divide or join'; box.append(hh);
    const row = document.createElement('div'); row.className = 'row'; row.style.marginTop = '0';
    const bS = document.createElement('button'); bS.className = 'btn'; bS.textContent = tool === 'split' ? 'Cancel split' : 'Split with a line'; bS.disabled = !S.canWrite || !jready(); bS.setAttribute('aria-pressed', String(tool === 'split'));
    bS.addEventListener('click', () => { S.ptool = tool === 'split' ? null : { mode: 'split', id: p.id }; ptoolHint(); renderSel(); redraw(); });
    const bM = document.createElement('button'); bM.className = 'btn'; bM.textContent = tool === 'merge' ? 'Done merging' : 'Merge with neighbours'; bM.disabled = !S.canWrite || !jready(); bM.setAttribute('aria-pressed', String(tool === 'merge'));
    bM.addEventListener('click', () => { S.ptool = tool === 'merge' ? null : { mode: 'merge', id: p.id }; ptoolHint(); renderSel(); redraw(); });
    row.append(bS, bM); box.append(row);
    const ud = frontDir(f), row2 = document.createElement('div'); row2.className = 'row';
    const lab2 = document.createElement('label'); lab2.htmlFor = 'pDiv'; lab2.textContent = 'Lots'; const inp = document.createElement('input'); inp.type = 'number'; inp.id = 'pDiv'; inp.min = '2'; inp.max = '60'; inp.step = '1'; inp.style.width = '70px'; inp.disabled = !S.canWrite || !jready();
    inp.value = String(jready() ? lotCount(jOf(f), ud) : 2);
    const bD = document.createElement('button'); bD.className = 'btn'; bD.textContent = 'Divide along the street'; bD.disabled = !S.canWrite || !jready();
    bD.addEventListener('click', () => { const n = Math.max(2, Math.min(60, parseInt(inp.value, 10) || 2)); S.pendingSel = { layer: 'plot', id: p.id + '.1' }; pushOp({ t: 'd', id: p.id, n, a: Math.round(Math.atan2(ud[1], ud[0]) * 1e4) / 1e4 }); });
    row2.append(lab2, inp, bD); box.append(row2);
    const n2 = document.createElement('p'); n2.className = 'notes'; n2.style.marginTop = '8px';
    n2.textContent = tool === 'split' ? 'Drag a line across the plot on the map. Hold Ctrl (Cmd on a Mac) to keep it square to the street or along it. Esc cancels.' : tool === 'merge' ? 'Click plots that touch this one to join them to it; it keeps its id, use and name. Esc or Done to finish.' : 'Divide cuts the plot into equal lots square to its street (about 7.6 m, 25 ft, each by default).' + (jready() ? '' : ' The geometry library is still loading.');
    box.append(n2); body.append(box);
    const row3 = document.createElement('div'); row3.className = 'row';
    const bR = document.createElement('button'); bR.className = 'btn'; bR.textContent = 'Reset use and name'; bR.disabled = !S.canWrite || !S.edits.plots[p.id]; bR.addEventListener('click', () => { delete S.edits.plots[p.id]; changed(); renderSel(); });
    const bB = document.createElement('button'); bB.className = 'btn'; bB.textContent = 'Select the block'; bB.disabled = !bf; bB.addEventListener('click', () => select(bf));
    row3.append(bR, bB); body.append(row3); alsoHere(f, body);
  } else if (L === 'open') {
    h.textContent = 'Open land'; sub.textContent = 'Left where a street moved, narrowed or got shorter, with no plot fronting it';
    kv('Area', fmt(f.area) + ' m²'); const sf = p.street && S.streetById.get(p.street); if (sf) kv('Was part of', sf.properties.name);
    body.append(h, sub, dl);
    const nbs = neighbours(f);
    if (nbs.length) { const hh = document.createElement('p'); hh.className = 'stop-h'; hh.style.marginTop = '10px'; hh.textContent = 'Add it to a plot it touches'; body.append(hh);
      const d = document.createElement('div'); d.className = 'also'; d.style.marginTop = '0';
      for (const q of nbs) { const b = document.createElement('button'); b.className = 'btn'; b.disabled = !S.canWrite; b.textContent = featLabel(q) + ' · ' + UNAME[plotUse(q)[0] || ''];
        b.addEventListener('click', () => { S.pendingSel = { layer: 'plot', id: q.properties.id }; pushOp({ t: 'f', q: p.q, to: q.properties.id }); }); d.append(b); }
      body.append(d); }
    const ua = [Math.cos(p.axis || 0), Math.sin(p.axis || 0)], fid = 'F' + Math.round(p.q[0]) + '_' + Math.round(p.q[1]);
    const row = document.createElement('div'); row.className = 'row';
    const b1 = document.createElement('button'); b1.className = 'btn'; b1.textContent = 'Make it one plot'; b1.disabled = !S.canWrite; b1.addEventListener('click', () => { S.pendingSel = { layer: 'plot', id: fid }; pushOp({ t: 'f', q: p.q, n: 1 }); });
    row.append(b1); body.append(row);
    const row2 = document.createElement('div'); row2.className = 'row';
    const lab2 = document.createElement('label'); lab2.htmlFor = 'oDiv'; lab2.textContent = 'Lots'; const inp = document.createElement('input'); inp.type = 'number'; inp.id = 'oDiv'; inp.min = '2'; inp.max = '60'; inp.step = '1'; inp.style.width = '70px'; inp.disabled = !S.canWrite; inp.value = String(jready() ? lotCount(jOf(f), ua) : 2);
    const b2 = document.createElement('button'); b2.className = 'btn'; b2.textContent = 'Divide into lots'; b2.disabled = !S.canWrite;
    b2.addEventListener('click', () => { const n = Math.max(2, Math.min(60, parseInt(inp.value, 10) || 2)); S.pendingSel = { layer: 'plot', id: fid + '.1' }; pushOp({ t: 'f', q: p.q, n, a: Math.round((p.axis || 0) * 1e4) / 1e4 }); });
    row2.append(lab2, inp, b2); body.append(row2);
    const n = document.createElement('p'); n.className = 'notes'; n.style.marginTop = '8px'; n.textContent = 'New plots join the nearest block. Lots are cut square to the street the land came from.'; body.append(n);
    alsoHere(f, body);
'''
src = src.replace(OLD_BLOCK, NEW_BLOCK)
# ---- block edits
rep("function setBlock(f, t, n) {\n  const id = f.properties.id;\n  if (t === f.properties.type && !n) delete S.edits.blocks[id]; else S.edits.blocks[id] = n ? { t, n } : t;\n  changed();\n}\n", "")
rep("  if (!from.length || !S.canWrite || S.drag) return; to.push(snapEdits()); const s = from.pop(); S.edits = JSON.parse(s); hist.last = s;",
    "  if (!from.length || !S.canWrite || S.drag) return; to.push(snapEdits()); const s = from.pop(); S.edits = JSON.parse(s); S.edits.plots = S.edits.plots || {}; S.edits.plotOps = S.edits.plotOps || []; hist.last = s;")
rep("function changed(rec = true) { if (rec) record(); S.ver++; renderEdits(); renderSummary(); redraw();",
    "function changed(rec = true) { if (rec) record(); S.ver++; schedulePlots(); renderEdits(); renderSummary(); redraw();")
rep("  const body = { streets: S.edits.streets, blocks: S.edits.blocks, transit: S.edits.transit, stations: S.edits.stations, updated:",
    "  const body = { streets: S.edits.streets, blocks: S.edits.blocks, transit: S.edits.transit, stations: S.edits.stations, plots: S.edits.plots, plotOps: S.edits.plotOps || [], updated:")
rep("function putEdit(f, patch) { const kind = editKind(f), id = f.properties.id; S.edits[kind][id] = Object.assign({}, S.edits[kind][id] || seedEdit(f), patch); S.ver++; }",
    "function putEdit(f, patch) { const kind = editKind(f), id = f.properties.id; S.edits[kind][id] = Object.assign({}, S.edits[kind][id] || seedEdit(f), patch); S.ver++; if (kind === 'streets') schedulePlots(220); }")
rep("$('resetYes').onclick = () => { S.edits = { streets: {}, blocks: {}, transit: {}, stations: {} };",
    "$('resetYes').onclick = () => { S.edits = { streets: {}, blocks: {}, transit: {}, stations: {}, plots: {}, plotOps: [] };")
rep("    S.edits = d ? { streets: cp(d.streets), blocks: cp(d.blocks), transit: cp(d.transit), stations: cp(d.stations) } : { streets: {}, blocks: {}, transit: {}, stations: {} };\n    S.ver++; hist.last = snapEdits(); renderEdits(); renderSummary(); renderSel(); redraw();",
    "    S.edits = d ? { streets: cp(d.streets), blocks: cp(d.blocks), transit: cp(d.transit), stations: cp(d.stations), plots: cp(d.plots), plotOps: Array.isArray(d.plotOps) ? JSON.parse(JSON.stringify(d.plotOps)) : [] } : { streets: {}, blocks: {}, transit: {}, stations: {}, plots: {}, plotOps: [] };\n    S.ver++; hist.last = snapEdits(); schedulePlots(0); renderEdits(); renderSummary(); renderSel(); redraw();")
rep("  const ns = Object.keys(S.edits.streets).length, nb = Object.keys(S.edits.blocks).length, nt = Object.keys(S.edits.transit).length, np = Object.keys(S.edits.stations).length;\n  const parts = [[ns, 'street'], [nb, 'block'], [nt, 'Metro/RER line'], [np, 'station']]",
    "  const ns = Object.keys(S.edits.streets).length, nb = Object.keys(S.edits.blocks).length, nt = Object.keys(S.edits.transit).length, np = Object.keys(S.edits.stations).length, nq = Object.keys(S.edits.plots || {}).length, no = (S.edits.plotOps || []).length;\n  const parts = [[ns, 'street'], [nb, 'block'], [nq, 'plot setting'], [no, 'plot split, merge or fill'], [nt, 'Metro/RER line'], [np, 'station']]")
rep("w + (n === 1 ? '' : 's'));", "w.replace('split, merge or fill', n === 1 ? 'split, merge or fill' : 'splits, merges or fills') + (n === 1 || w.endsWith('fill') ? '' : 's'));")
rep("<div class=\"confirm\" id=\"resetConfirm\" hidden>Put every street, block, Metro and RER line and station back to the generated layout?",
    "<div class=\"confirm\" id=\"resetConfirm\" hidden>Put every street, block, plot, Metro and RER line and station back to the generated layout?")
# ---- summary: plots and land use
rep("  if (S.we) { const ws = S.deck.features.filter(f => isWE(f) && f.properties.layer === 'street')",
    "  if (S.pl) { const n = S.pl.plots.length; let set = 0; const by = {}; for (const pf of S.pl.plots) { const u = plotUse(pf)[0]; if (u) { set++; by[u] = (by[u] || 0) + pf.area; } }\n    kv('Plots', fmt(n) + (S.pl.open.length ? ' · ' + S.pl.open.length + ' open land' : '')); kv('Plots with a use', fmt(set) + ' (' + fmt(100 * set / Math.max(1, n)) + '%)');\n    for (const [k, lab] of USES) if (by[k]) kv(lab, fmt(by[k] / 10000, 1) + ' ha'); }\n  if (S.we) { const ws = S.deck.features.filter(f => isWE(f) && f.properties.layer === 'street')")
# ---- tools: split and merge
rep("function setTool(t) { S.tool = t;", "function ptoolHint() { const t = S.ptool; if (!t) { setTool(S.tool); return; } $('hint').textContent = t.mode === 'split' ? 'Split: drag a line across the plot. Hold Ctrl (Cmd on a Mac) to square it to the street. Esc cancels.' : 'Merge: click plots that touch the selected one to join them to it. Esc to finish.'; }\nfunction setTool(t) { S.tool = t;")
rep("  const [px, py] = local(e);\n  if (S.canWrite) {\n    const vi = vertexAt(px, py);",
    "  const [px, py] = local(e);\n  if (S.canWrite && S.ptool && S.ptool.mode === 'split') { const p0 = S2W(px, py); S.drag = { mode: 'cut', p0, p1: p0 }; down = null; return; }\n  if (S.canWrite) {\n    const vi = vertexAt(px, py);")
rep("    else if (d.mode === 'slide') {",
    "    else if (d.mode === 'cut') { let q = [wx, wy]; if ((e.ctrlKey || e.metaKey) && S.sel.f.properties.layer === 'plot') { const u = frontDir(S.sel.f), dx = wx - d.p0[0], dy = wy - d.p0[1]; let best = null, bd = -1; for (const w of [u, [-u[1], u[0]]]) { const t = dx * w[0] + dy * w[1]; if (Math.abs(t) > bd) { bd = Math.abs(t); best = [w, t]; } } q = [d.p0[0] + best[0][0] * best[1], d.p0[1] + best[0][1] * best[1]]; } d.p1 = q; }\n    else if (d.mode === 'slide') {")
rep("  if (S.drag) { S.drag = null; cv.classList.remove('dragging'); changed(); renderSel(); return; }",
    "  if (S.drag && S.drag.mode === 'cut') { const d = S.drag; S.drag = null; finishCut(d); return; }\n  if (S.drag) { S.drag = null; cv.classList.remove('dragging'); changed(); renderSel(); return; }\n  if (down && !down.moved && S.ptool && S.ptool.mode === 'merge') { mergeClick(S2W(down.px, down.py)); down = null; return; }")
rep("cv.addEventListener('pointerup', endPtr);", r'''function finishCut(d) {
  const pf = S.sel && S.sel.f, t = S.ptool; if (!pf || !t || pf.properties.id !== t.id) { redraw(); return; }
  if (Math.hypot(d.p1[0] - d.p0[0], d.p1[1] - d.p0[1]) * S.view.s < 6) { redraw(); return; }
  const r2 = q => [Math.round(q[0] * 100) / 100, Math.round(q[1] * 100) / 100], [A, B] = halfPlanes(jOf(pf), d.p0, d.p1);
  if (A.getArea() < 1 || B.getArea() < 1) { $('hint').textContent = 'That line does not cross the plot. Drag again, from one side of it to the other.'; redraw(); return; }
  S.ptool = null; S.pendingSel = { layer: 'plot', id: pf.properties.id + '.1' }; setTool(S.tool); pushOp({ t: 's', id: pf.properties.id, l: [r2(d.p0), r2(d.p1)] });
}
function mergeClick(p) {
  const t = S.pl && S.pl.byId.get(S.ptool.id), q = plotAt(p); if (!t) { S.ptool = null; ptoolHint(); return; }
  if (!q || q === t) return;
  if (!touching(t, q)) { $('hint').textContent = featLabel(q) + ' does not touch ' + featLabel(t) + '. Click a plot next to it, or Esc to finish.'; return; }
  S.pendingSel = { layer: 'plot', id: t.properties.id }; pushOp({ t: 'm', ids: [t.properties.id, q.properties.id] }); ptoolHint();
}
cv.addEventListener('pointerup', endPtr);''')
rep("  if (e.key === 'Escape' && S.sel) select(null);", "  if (e.key === 'Escape') { if (S.ptool) { S.ptool = null; S.drag = null; setTool(S.tool); return; } if (S.sel) select(null); }")
rep("for (const [id, key] of [['lSan', 'san'], ['lRel', 'rel'], ['lBlk', 'blk'], ['lStr', 'str'], ['lMet', 'met'], ['lRer', 'rer'], ['lTrk', 'trk'], ['lLab', 'lab'], ['lIdx', 'idx'], ['lWe', 'we'], ['l12', 's12']])",
    "$('colBy').addEventListener('change', e => { S.colorBy = e.target.value; redraw(); });\nfor (const [id, key] of [['lSan', 'san'], ['lRel', 'rel'], ['lBlk', 'blk'], ['lStr', 'str'], ['lMet', 'met'], ['lRer', 'rer'], ['lTrk', 'trk'], ['lLab', 'lab'], ['lIdx', 'idx'], ['lWe', 'we'], ['l12', 's12'], ['lPlt', 'plt']])")
# ---- reselect: pending selection after a split, merge, division or fill
rep("function reselect() {   // keep the selection across a rebuild\n  const s = S.sel; if (!s) return;",
    "function reselect() {   // keep the selection across a rebuild\n  if (S.pendingSel) { const ps = S.pendingSel, f = ps.layer === 'plot' ? S.pl.byId.get(ps.id) : null; if (f) { S.pendingSel = null; S.sel = { f }; renderSel(); return; } }\n  const s = S.sel; if (!s) return;")
# ---- export: live blocks, plots, open land
rep("  return S.deck.features.map(f => { const p = Object.assign({}, f.properties); let g = f.geometry;\n    if (p.layer === 'street') { g = { type: 'LineString', coordinates: streetCoords(f) }; p.width_m = streetWidth(f); p.edited = !!S.edits.streets[p.id]; }\n    if (p.layer === 'block') { p.type = blockType(f); if (blockName(f)) p.block_name = blockName(f); p.edited = !!S.edits.blocks[p.id]; }\n    return { type: 'Feature', properties: p, geometry: mapG(g) }; }).concat(transitFeatures(mapG), extra);",
    "  const blocks = blockList().map(f => { const p = Object.assign({}, f.properties); delete p.live; p.type = blockType(f); if (blockName(f)) p.block_name = blockName(f); const bu = blockField(f, 'u'); if (bu !== undefined && bu !== null) p.use_for_all_plots = UNAME[bu];\n    if (S.pl) { const mix = blockUseMix(f); p.plots = mix.n; p.land_use = mix.list.map(x => UNAME[x.u] + ' ' + x.n).join(', '); } p.edited = !!(S.edits.blocks[p.id] || (p.gen && S.edits.blocks[p.gen])); if (p.joined) p.joined = p.joined.join(', '); else delete p.joined; return { type: 'Feature', properties: p, geometry: mapG(f.geometry) }; });\n  const plots = S.pl ? S.pl.plots.map(pf => { const [u, src] = plotUse(pf), p = pf.properties, sf = p.street && S.streetById.get(p.street), o = { layer: 'plot', id: p.id, block: pf.lb || p.block, use: UNAME[u || ''], use_code: u || '', use_from: src ? USRC[src] : '', area_m2: Math.round(pf.area) };\n    if (plotName(pf)) o.name = plotName(pf); if (sf) o.fronts = sf.properties.name; if (p.lab && p.lab.length) o.sheet_labels = p.lab.join('; '); return { type: 'Feature', properties: o, geometry: mapG(pf.geometry) }; }) : [];\n  const open = S.pl ? S.pl.open.map(f => ({ type: 'Feature', properties: { layer: 'open_land', id: f.properties.id, area_m2: Math.round(f.area) }, geometry: mapG(f.geometry) })) : [];\n  return S.deck.features.filter(f => f.properties.layer !== 'block').map(f => { const p = Object.assign({}, f.properties); let g = f.geometry;\n    if (p.layer === 'street') { g = { type: 'LineString', coordinates: streetCoords(f) }; p.width_m = streetWidth(f); p.edited = !!S.edits.streets[p.id]; }\n    return { type: 'Feature', properties: p, geometry: mapG(g) }; }).concat(blocks, plots, open, transitFeatures(mapG), extra);")
rep("  const st = Object.entries(col).map(([k, c]) => `<Style id=\"b_${k}\">",
    "  const ucol = { r: '6acff0', m: '4a9def', c: '575bdf', i: 'c77c9a', w: '8f70b5', v: 'c9955f', p: 'b0aaa5', o: '7ac28c', '': 'dcded9' };\n  const st = Object.entries(ucol).map(([k, c]) => `<Style id=\"u_${k || 'n'}\"><LineStyle><color>ff555555</color><width>0.6</width></LineStyle><PolyStyle><color>b3${c}</color></PolyStyle></Style>`).join('') + '<Style id=\"open_land\"><LineStyle><color>ff2e2ecf</color><width>1</width></LineStyle><PolyStyle><color>402e2ecf</color></PolyStyle></Style>' + Object.entries(col).map(([k, c]) => `<Style id=\"b_${k}\">")
rep("    if (L === 'street') style = (p.kind === 'through' || p.kind === 'radial') ? 'thru' : 'tee'; else if (L === 'block') style = 'b_' + p.type;",
    "    if (L === 'street') style = (p.kind === 'through' || p.kind === 'radial') ? 'thru' : 'tee'; else if (L === 'block') style = 'b_' + p.type; else if (L === 'plot') { style = 'u_' + (p.use_code || 'n'); name = p.name || p.id; } else if (L === 'open_land') style = 'open_land';")
# ---- boot: indexes and plots
rep("  try { const we = await fetch('basin.json').then(r => r.json()); S.we = we; for (const f of we.features) S.deck.features.push(f); } catch (e) { S.we = null; }",
    "  try { const we = await fetch('basin.json').then(r => r.json()); S.we = we; for (const f of we.features) S.deck.features.push(f); } catch (e) { S.we = null; }\n  indexLayers(); if (/[?&]debug\\b/.test(location.search)) window.__S = S;\n  fetch('plots.json').then(r => r.json()).then(D => { S.plots0 = decodePlots(D); setPlotNote(fmt(S.plots0.length) + ' plots loaded'); schedulePlots(0); }).catch(e => { console.error(e); setPlotNote('Plots could not be loaded'); });")
rep("async function boot() {", r'''function indexLayers() {
  S.streetById = new Map(); S.streets0 = []; S.openFeats = []; S.blkById = new Map();
  const bbG = g => polysOf(g).reduce((b, p) => { const q = bbOf(p[0]); return [Math.min(b[0], q[0]), Math.min(b[1], q[1]), Math.max(b[2], q[2]), Math.max(b[3], q[3])]; }, [1e18, 1e18, -1e18, -1e18]);
  for (const f of S.deck.features) { const p = f.properties;
    if (p.layer === 'street') { S.streetById.set(p.id, f); f._bb = grow(bbOf(genCoords(f)), (p.width_m || 10) / 2 + 1); S.streets0.push(f); }
    else if (p.layer === 'block') { S.blkById.set(p.id, f); f._bb = bbG(f.geometry); }
    else if (OPEN_LAYERS.has(p.layer) && f.geometry && /Polygon/.test(f.geometry.type)) { f._bb = bbG(f.geometry); S.openFeats.push(f); } }
}
async function boot() {''')
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok', len(src))
