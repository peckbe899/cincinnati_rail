try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio, sys, json
from playwright.async_api import async_playwright
SP = _ws.DATA[:-1]
OUT = SP + '/lph/shots29'
deck = json.load(open(SP + '/deckpage/deck.json'))
st = [f for f in deck['features'] if f['properties'].get('layer') == 'street' and len(f['geometry']['coordinates']) >= 2]
# a deck street with a long first segment
import math
best = max(st, key=lambda f: math.dist(f['geometry']['coordinates'][0], f['geometry']['coordinates'][1]) if f['properties'].get('kind') in ('T', 'NS') else 0)
blk = [f for f in deck['features'] if f['properties'].get('layer') == 'block' and f['properties'].get('type') == 'building' and f['properties'].get('side') != 'WV']
blk = max(blk, key=lambda f: f['properties']['area_m2'])
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); logs = []
        q = await b.new_page(viewport={"width": 1400, "height": 900})
        q.on("console", lambda m: logs.append(f"{m.type}: {m.text}")); q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        async def go(cx, cy, s):
            go.n = getattr(go, "n", 0) + 1; await q.goto(f"http://127.0.0.1:8765/index.html?r={go.n}#{cx},{cy},{s}"); await q.wait_for_timeout(4500)
            r = await q.evaluate("(() => { const r = document.getElementById('cv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
            return lambda wx, wy: (r[0] + (wx - cx) * s + r[2] / 2, r[1] + (cy - wy) * s + r[3] / 2)
        async def sel(): return (await q.inner_text('#selBody'))[:400].replace('\n', ' | ')
        async def shot(n): await q.screenshot(path=OUT + '/' + n + '.png')
        # 1 Westwood RER station
        W = await go(712102.5, 4333378.7, 1.6)
        x, y = W(712102.5, 4333378.7); await q.mouse.click(x, y); await q.wait_for_timeout(300)
        print('STATION:', await sel()); await shot('01_westwood_sel')
        await q.click('#tEdit'); await q.wait_for_timeout(200)
        await q.mouse.move(x, y); await q.mouse.down(); await q.mouse.move(x + 30, y + 30, steps=5); await q.mouse.move(x + 70, y + 70, steps=5); await q.mouse.up(); await q.wait_for_timeout(300)
        print('AFTER DRAG:', await sel()); await shot('02_westwood_dragged')
        await q.get_by_role('button', name='Side', exact=True).first.click(); await q.wait_for_timeout(300)
        print('SIDE:', await sel()); await shot('03_westwood_side')
        await q.get_by_role('button', name='Delete station').click(); await q.wait_for_timeout(300)
        print('DELETED:', await sel()); await shot('04_westwood_deleted')
        print('EDITS:', await q.inner_text('#editNote'))
        # 2 street curve
        c = best['geometry']['coordinates']; m = [(c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2]
        W = await go(m[0], m[1], 1.2); await q.click('#tSel')
        x, y = W(*m); await q.mouse.click(x, y); await q.wait_for_timeout(600)
        print('STREET:', best['properties']['name'], '|', await sel())
        await q.click('#tEdit'); await q.wait_for_timeout(200)
        dx, dy = c[1][0] - c[0][0], c[1][1] - c[0][1]; L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
        await q.mouse.move(x, y); await q.mouse.down(); await q.mouse.move(x + nx * 40, y - ny * 40, steps=8); await q.mouse.up(); await q.wait_for_timeout(300)
        print('CURVED:', await sel()); await shot('05_street_curve')
        await q.mouse.dblclick(x + nx * 20, y - ny * 20); await q.wait_for_timeout(300)
        print('INSERTED:', await sel()); await shot('06_street_insert')
        # 3 metro line 5 at Sassafras
        W = await go(712468.0, 4335724.8, 1.4); await q.click('#tSel')
        x, y = W(712468.0, 4335724.8 + 140); await q.mouse.click(x, y); await q.wait_for_timeout(400)
        print('CLICK NEAR L5:', await sel())
        await q.mouse.click(x, y); await q.wait_for_timeout(800)
        print('CLICK AGAIN:', await sel()); await shot('07_l5_cycle')
        ctxj = json.load(open(SP + '/deckpage/context.json'))
        l5 = [m for m in ctxj['metro'] if m['name'] == 'Line 5']
        st5 = (712468.0, 4335724.8)
        bestv = min(((math.dist(v, st5), v) for m in l5 for v in m['c']))[1]
        print('L5 vertex', bestv, round(math.dist(bestv, st5)))
        await q.click('#tEdit'); await q.wait_for_timeout(200)
        vx, vy = W(*bestv); await q.mouse.move(vx, vy); await q.mouse.down(); await q.mouse.move(vx + 10, vy, steps=4); await q.mouse.move(vx + 25, vy, steps=4); await q.mouse.up(); await q.wait_for_timeout(400)
        print('L5 DRAGGED:', await sel()); await shot('08_l5_vertex')
        await q.get_by_role('button', name='Smooth curve').click(); await q.wait_for_timeout(400)
        print('L5 SMOOTH:', await sel()); await shot('09_l5_smooth')
        print('EDITS:', await q.inner_text('#editNote'))
        # 4 block type + name
        bc = blk['geometry']['coordinates'][0] if blk['geometry']['type'] == 'Polygon' else blk['geometry']['coordinates'][0][0]
        cx = sum(p[0] for p in bc) / len(bc); cy = sum(p[1] for p in bc) / len(bc)
        W = await go(cx, cy, 1.0); await q.click('#tSel'); x, y = W(cx, cy); await q.mouse.click(x, y); await q.wait_for_timeout(400)
        print('BLOCK CLICK:', await sel())
        bb = q.locator('.also .btn', has_text='Block')
        if await bb.count(): await bb.first.click(); await q.wait_for_timeout(300)
        print('BLOCK:', await sel())
        await q.get_by_role('button', name='Tower').click(); await q.fill('#bName', 'Test Tower'); await q.press('#bName', 'Enter'); await q.wait_for_timeout(400)
        print('BLOCK AFTER:', await sel()); await shot('10_block_tower')
        await q.get_by_role('button', name='Landmark').click(); await q.wait_for_timeout(300)
        print('BLOCK LANDMARK:', await sel())
        print('EDITS:', await q.inner_text('#editNote'))
        print("\n".join(logs[:30])); await b.close()
asyncio.run(main())
