try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data_live.json').read(); JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
JS = r"""
() => {
  const { select, streetCoords } = window.__fn, S = window.__S, r = {};
  const all = S.deck.features.filter(f => f.properties.layer === 'street');
  const bk = all.filter(f => /^Beekman/.test(f.properties.name)); r.bk = bk.map(f => [f.properties.id, f.properties.name, f.geometry.coordinates.length]);
  const F = all.find(f => f.properties.id === 'SB0720');
  const B = bk.sort((a, b) => b.geometry.coordinates.length - a.geometry.coordinates.length)[0]; if (!B) return r;
  const b = (a, c) => ((Math.atan2(c[0] - a[0], c[1] - a[1]) * 180 / Math.PI) + 360) % 180;
  select(F); [...document.querySelectorAll('#selBody button')].find(x => x.textContent === 'Copy heading').click();
  const v0 = streetCoords(B).map(q => q.slice()), vv0 = B.geometry.coordinates.map(q => q.slice()); const n = vv0.length;
  window.__fn.select(B); S.rng = { id: B.properties.id, n, a: 0, b: 1 }; S.tool = 'edit'; window.__fn.select(B); S.rng = { id: B.properties.id, n, a: 0, b: 1 };
  document.getElementById('tEdit').click(); S.rng = { id: B.properties.id, n, a: 0, b: 1 };
  [...document.querySelectorAll('#selBody button')].find(x => x.textContent === 'Drop the picks') || null;
  // re-render the panel with the range
  select(B); S.rng = { id: B.properties.id, n, a: 0, b: 1 }; document.getElementById('tEdit').dispatchEvent(new Event('noop'));
  return { r, n, beforeSeg: b(vv0[0], vv0[1]), F: [F.properties.name, b(F.geometry.coordinates[0], F.geometry.coordinates[F.geometry.coordinates.length-1])] };
}
"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); q = await b.new_page(viewport={"width": 1400, "height": 1000}); logs = []
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto("http://127.0.0.1:8765/index.html?debug#712500,4337500,1.4"); await q.wait_for_timeout(20000)
        print(await q.evaluate(JS))
        await q.evaluate("() => { window.__fn.select(window.__S.streetById.get(window.__S.rng.id)); }")
        await q.wait_for_timeout(500)
        print(await q.evaluate(r'''() => { const S = window.__S, f = S.streetById.get(S.rng.id), before = window.__fn.streetCoords(f).map(q => q.slice()); const bt = [...document.querySelectorAll('#selBody button')].filter(x => x.textContent.startsWith('Match ')); const txt = bt.map(x => x.textContent); bt[bt.length - 1].click(); const after = window.__fn.streetCoords(S.streetById.get(f.properties.id)); const v = window.__fn.lenOf; const b = (a, c) => ((Math.atan2(c[0] - a[0], c[1] - a[1]) * 180 / Math.PI) + 360) % 180; const vb = S.edits.streets[f.properties.id].c; return { txt, seg: b(vb[0], vb[1]), next: vb.length > 2 ? b(vb[1], vb[2]) : null, kept0: vb[0], rest: vb.slice(2) , orig: f.geometry.coordinates.slice(2)}; }'''))
        await q.wait_for_timeout(1000)
        await q.screenshot(path=SP + 'plots/hdg.png', clip={'x':1050,'y':100,'width':350,'height':900})
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
