try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio, json, math
from playwright.async_api import async_playwright
SP = _ws.DATA[:-1]; OUT = SP + '/lph/shots29'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); logs = []
        q = await b.new_page(viewport={"width": 1400, "height": 900})
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        cx, cy, s = 712468.0, 4335724.8, 3.0
        await q.goto(f"http://127.0.0.1:8765/index.html?z=1#{cx},{cy},{s}"); await q.wait_for_timeout(4500)
        r = await q.evaluate("(() => { const r = document.getElementById('cv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
        W = lambda wx, wy: (r[0] + (wx - cx) * s + r[2] / 2, r[1] + (cy - wy) * s + r[3] / 2)
        await q.screenshot(path=OUT + '/11_sassafras_before.png')
        x, y = W(cx, cy); await q.click('#tEdit'); await q.mouse.click(x, y); await q.wait_for_timeout(300)
        print('SEL:', (await q.inner_text('#selBody'))[:120].replace('\n', ' | '))
        # drag platform 30 m north (screen up)
        await q.mouse.move(x, y - 15); await q.mouse.down(); await q.mouse.move(x, y - 60, steps=6); await q.mouse.move(x, y - 105, steps=6); await q.mouse.up(); await q.wait_for_timeout(300)
        print('SEL2:', (await q.inner_text('#selBody'))[:200].replace('\n', ' | '))
        await q.keyboard.press('Escape'); await q.wait_for_timeout(300)
        await q.screenshot(path=OUT + '/12_sassafras_after.png')
        await q.mouse.click(x, y); await q.wait_for_timeout(200)
        await q.get_by_role('button', name='Side', exact=True).first.click(); await q.keyboard.press('Escape'); await q.wait_for_timeout(300)
        await q.screenshot(path=OUT + '/13_sassafras_side.png')
        print('\n'.join(logs)); await b.close()
asyncio.run(main())
