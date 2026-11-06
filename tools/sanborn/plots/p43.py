try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio, json
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data.json').read(); JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); logs = []
        q = await b.new_page(viewport={"width": 1400, "height": 1000})
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        q.on("console", lambda m: logs.append(f"CONSOLE {m.type}: {m.text}") if m.type == 'error' else None)
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        async def goto(X, Y, s, tag):
            await q.goto(f"http://127.0.0.1:8765/index.html?debug&r={tag}#{X},{Y},{s}"); await q.wait_for_timeout(6000)
        async def scr(X, Y):
            return await q.evaluate(f"(() => {{ const r = document.getElementById('cv').getBoundingClientRect(), v = __S.view; return [r.left + r.width / 2 + ({X} - v.cx) * v.s, r.top + r.height / 2 - ({Y} - v.cy) * v.s]; }})()")
        async def click_world(X, Y, wait=600):
            pt = await scr(X, Y); await q.mouse.click(pt[0], pt[1]); await q.wait_for_timeout(wait)
        body = lambda n=500: q.inner_text('#selBody')
        shot = lambda nm: q.screenshot(path=SP + f'plots/v_c43_{nm}.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        # ---- street: Harrison Avenue (west): add a point, pick a stretch, give it a width
        await goto(712300, 4333560, 1.6, 'a')
        c = await q.evaluate("__S.streetById.get('S006').geometry.coordinates"); print('S006', c)
        mid = [(c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2]
        await click_world(*mid); print('sel:', (await body())[:80].replace('\n', ' | '))
        await q.locator('#selBody button', has_text='Edit points').click(); await q.wait_for_timeout(400)
        v = c
        await click_world(*v[0], 400); await click_world(*v[1], 600)
        print('range panel:', (await body())[-700:].replace('\n', ' | '))
        await q.fill('#rgW', '32'); await q.locator('#selBody button', has_text='Set for this stretch').click(); await q.wait_for_timeout(1500)
        print('edit S006', json.dumps(await q.evaluate("__S.edits.streets['S006']")))
        print('width kv:', [l for l in (await body()).split('\n') if 'Width' in l or 'between points' in l][:3])
        await shot('street')
        q14 = [c[1][0] * 0.75 + c[2][0] * 0.25, c[1][1] * 0.75 + c[2][1] * 0.25]; pt = await scr(*q14); await q.mouse.dblclick(pt[0], pt[1]); await q.wait_for_timeout(800)
        print('after adding a point on the other segment', json.dumps(await q.evaluate("__S.edits.streets['S006']")))
        # ---- transit: RER line, one curve between two points
        f = await q.evaluate("(() => { const f = __S.tf.find(t => t.properties.sys === 'rer' && t.geometry.coordinates.length > 12 && t.properties.k && Object.keys(t.properties.k).length > 3); return { id: f.properties.id, v: f.geometry.coordinates, k: f.properties.k }; })()")
        print('rer', f['id'], len(f['v']), sorted(map(int, f['k'].keys()))[:20])
        import math
        V = f['v']; K = {int(a): b for a, b in f['k'].items()}
        def tdir(a, b): return math.atan2(b[1] - a[1], b[0] - a[0])
        best = None
        for i in range(1, len(V) - 6):
            for j in range(i + 2, min(len(V) - 1, i + 6)):
                tA = tdir(K.get(i - 1, V[i - 1]), V[i]); tB = tdir(V[j], K.get(j, V[j + 1])); th = (tB - tA + math.pi) % (2 * math.pi) - math.pi
                turns = [(tdir(V[s], K.get(s, V[s + 1])) - tdir(K.get(s - 1, V[s - 1]), V[s]) + math.pi) % (2 * math.pi) - math.pi for s in range(i, j + 1)]
                if abs(th) > 0.5 and all(t * th >= -0.01 for t in turns): best = (i, j); break
            if best: break
        i0, j0 = best; print('picked', i0, j0)
        A, Bp = f['v'][i0], f['v'][j0]
        await goto((A[0] + Bp[0]) / 2, (A[1] + Bp[1]) / 2, 0.5, 'b')
        seg = f['v'][i0 + 1]; await click_world(*seg); print('sel:', (await body())[:90].replace('\n', ' | '))
        await q.locator('#selBody button', has_text='Edit points').click(); await q.wait_for_timeout(400)
        await click_world(*A, 400); await click_world(*Bp, 600)
        print('range:', [l for l in (await body()).split('\n') if 'Points' in l][:2])
        await q.locator('#selBody button', has_text='One curve between them').click(); await q.wait_for_timeout(800)
        print('result:', [l for l in (await body()).split('\n') if 'One curve of' in l or 'both ways' in l or 'straight here' in l or 'top of each' in l][:2])
        e = await q.evaluate(f"__S.edits.transit['{f['id']}']"); print('verts now', len(e['c']), 'curved', len(e.get('k') or {}))
        await shot('rer')
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
