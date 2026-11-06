try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 52 (Ben, 17 October: "I see no option for that"): the sideways choice sits with the width, so a stretch can be made narrower
# and put on its left edge, centre or right edge of the road beside it in one step; the slider follows once it is narrower.
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new):
    global src
    c = src.count(old)
    if c != 1: sys.exit('count %d for: %s' % (c, old[:100]))
    src = src.replace(old, new)
rep("""function setShiftRange(f, i, j, o) {""",
"""function setWidthAlign(f, i, j, w, al) {   // width for the stretch and its place inside the wider road beside it (left / centre / right edge)
  const n = vertsOf(f).length - 1, e = S.edits.streets[f.properties.id], base = streetWidth(f);
  const wv = e && e.wv && e.wv.length === n ? e.wv.slice() : new Array(n).fill(null), ov = e && e.ov && e.ov.length === n ? e.ov.slice() : new Array(n).fill(null);
  for (let s = i; s < j; s++) wv[s] = Math.abs(w - base) < 0.01 ? null : w;
  let o = 0, msg = '';
  if (al && al !== 'keep') { const W = s => wv[s] || base, O = s => ov[s] || 0; let lo = -1e9, hi = 1e9, any = false, none = false;
    for (const s of [i - 1, j]) { if (s < 0 || s >= n) continue; any = true; const room = (W(s) - w) / 2; if (room < 0.05) { none = true; continue; } lo = Math.max(lo, O(s) - room); hi = Math.min(hi, O(s) + room); }
    if (!any || none || lo > hi) msg = 'Width set; the road on ' + (any ? 'one side is not wider' : 'neither side continues') + ', so the stretch stays on the line.';
    else o = al === 'left' ? hi : al === 'right' ? lo : Math.min(hi, Math.max(lo, 0)); }
  else if (al === 'keep') o = (ov[i] || 0);
  for (let s = i; s < j; s++) ov[s] = Math.abs(o) < 0.01 ? null : Math.round(o * 100) / 100;
  setEdit(f, { wv: wv.some(x => x) ? wv : undefined, ov: ov.some(x => x) ? ov : undefined }); return msg;
}
function setShiftRange(f, i, j, o) {""")
rep("""    const b = document.createElement('button'); b.className = 'btn'; b.textContent = 'Set for this stretch'; b.disabled = !S.canWrite; b.addEventListener('click', () => { const w = parseFloat(inp.value); if (!(w >= 2 && w <= 80)) return; setWidthRange(f, i, j, w); renderSel(); }); row.append(b);""",
"""    const rowA = document.createElement('div'); rowA.className = 'row'; const la = document.createElement('label'); la.htmlFor = 'rgA'; la.textContent = 'Sits on'; const sa = document.createElement('select'); sa.id = 'rgA'; sa.disabled = !S.canWrite;
    for (const [v, t] of [['centre', 'the centre line'], ['left', 'the left edge of the road beside it'], ['right', 'the right edge of the road beside it'], ['keep', 'where it is now']]) { const op = document.createElement('option'); op.value = v; op.textContent = t; sa.append(op); }
    { const ov0 = streetOv(f); if (ov0 && ov0[i]) sa.value = 'keep'; }
    rowA.append(la, sa);
    const b = document.createElement('button'); b.className = 'btn'; b.textContent = 'Set for this stretch'; b.disabled = !S.canWrite; b.addEventListener('click', () => { const w = parseFloat(inp.value); if (!(w >= 2 && w <= 80)) return; const m = setWidthAlign(f, i, j, w, sa.value); if (m) S.rngMsg = m; renderSel(); }); row.append(b);
    box.append(rowA);
    { const an = document.createElement('p'); an.className = 'notes'; an.textContent = 'Left and right are looking from point ' + (i + 1) + ' to point ' + (j + 1) + '. A narrower stretch put on an edge lines up with that edge of the wider road next to it, with no S-bend; the line itself stays where it is.'; box.append(an); }""")
src = src.replace("Sideways position: give this stretch a narrower width than the road next to it, and it can then sit anywhere inside that road\\u2019s width (no S-bend).", "Once this stretch is narrower than the road next to it, a slider here moves it anywhere inside that road\\u2019s width.")
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v52')

# selection highlight follows the runs (width and sideways position)
src = open(SP + 'deckpage/index.html').read()
rep("    ctx.globalAlpha = 0.35; ctx.lineWidth = Math.max(4, wpx); ctx.beginPath(); pathLine(c); ctx.stroke();\n    if (L === 'transit' || many)",
    "    ctx.globalAlpha = 0.35; if (L === 'street' && streetRuns(f)) strokeStreet(f, c, m => Math.max(4, m * v.s + 4)); else { ctx.lineWidth = Math.max(4, wpx); ctx.beginPath(); pathLine(c); ctx.stroke(); }\n    if (L === 'transit' || many)")
open(SP + 'deckpage/index.html', 'w').write(src)
src = open(SP + 'deckpage/index.html').read()
rep('for (let i = 1; i < r.length; i++) { const q = runJoint(r[i - 1], r[i]), [x, y] = W2S(q[0], q[1]);', 'for (let i = 1; i < r.length; i++) { const A = r[i - 1].c, B = r[i].c, a1 = Math.atan2(A[A.length - 1][1] - A[A.length - 2][1], A[A.length - 1][0] - A[A.length - 2][0]), a2 = Math.atan2(B[1][1] - B[0][1], B[1][0] - B[0][0]); if (Math.abs(Math.atan2(Math.sin(a2 - a1), Math.cos(a2 - a1))) < 0.035) continue; const q = runJoint(r[i - 1], r[i]), [x, y] = W2S(q[0], q[1]);')   # no disc where two runs meet in a straight line
open(SP + 'deckpage/index.html', 'w').write(src)
