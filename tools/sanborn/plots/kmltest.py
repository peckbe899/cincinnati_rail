try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio, re
SP=_ws.DATA
JSTS=open(_ws.CODE+'jslib/package/dist/jsts.min.js').read()
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1200, 'height': 900})
        await pg.route('**/cdn.jsdelivr.net/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=JSTS)); await pg.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body='')); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8765/index.html?debug#712060,4336200,1.0', wait_until='load'); await pg.wait_for_timeout(20000)
        r = await pg.evaluate("""() => { try { const k = window.__kml ? window.__kml() : null; if (!k) return 'no kml fn'; 
            const m = k.match(/<Placemark>.*?<\\/Placemark>/g) || []; const st = m.filter(x => x.includes('#thru') || x.includes('#tee')); const poly = st.filter(x => x.includes('<Polygon>'));
            return JSON.stringify({len: k.length, streets: st.length, withArea: poly.length, jsts: !!window.jsts, err: (window.__kerr||[]).slice(0,2), n0: [...window.__S.streetById.keys()].slice(0,3), p0: (st[0]||"").slice(0,300), sample: (poly.find(x => x.includes('Millvale Boulevard')) || '').slice(0, 400)}); } catch (e) { return 'ERR ' + e.message; } }""")
        print(r); k = await pg.evaluate('window.__kml()'); open(SP+'plots/kml_test.kml','w').write(k); print('errors', errs[:3]); await b.close()
asyncio.run(main())
