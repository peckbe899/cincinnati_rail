import asyncio, math
from playwright.async_api import async_playwright
a, b = (712028.9, 4331051.8), (712253.2, 4331037.7)
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(); logs = []
        q = await br.new_page(viewport={"width": 1400, "height": 900}); q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        cx, cy, s = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 2.5
        await q.goto(f"http://127.0.0.1:8765/index.html?d=1#{cx},{cy},{s}"); await q.wait_for_timeout(4000)
        r = await q.evaluate("(() => { const r = document.getElementById('cv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
        W = lambda wx, wy: (r[0] + (wx - cx) * s + r[2] / 2, r[1] + (cy - wy) * s + r[3] / 2)
        info = lambda t: t[:200].replace('\n', ' | ')
        x, y = W(cx, cy); await q.mouse.click(x, y); await q.wait_for_timeout(300); print('SEL', info(await q.inner_text('#selBody')))
        await q.click('#tEdit'); await q.mouse.move(x, y); await q.mouse.down(); await q.mouse.move(x, y - 40, steps=5); await q.mouse.move(x, y - 80, steps=5); await q.mouse.up(); await q.wait_for_timeout(300)
        print('BENT', info(await q.inner_text('#selBody'))); await q.screenshot(path='lph/shots29/15_perin_bent.png')
        # double-click on the curve a quarter of the way: quadratic point at t=0.25
        k = (2 * cx - (a[0] + b[0]) / 2, 2 * (cy + 80 / s) - (a[1] + b[1]) / 2)
        t = 0.25; qp = ((1-t)**2*a[0] + 2*(1-t)*t*k[0] + t*t*b[0], (1-t)**2*a[1] + 2*(1-t)*t*k[1] + t*t*b[1])
        await q.mouse.dblclick(*W(*qp)); await q.wait_for_timeout(300); print('SPLIT', info(await q.inner_text('#selBody'))); await q.screenshot(path='lph/shots29/16_perin_split.png')
        await q.mouse.dblclick(*W(*qp)); await q.wait_for_timeout(300); print('MERGED', info(await q.inner_text('#selBody'))); await q.screenshot(path='lph/shots29/17_perin_merged.png')
        await q.get_by_role('button', name='Straighten').click(); await q.wait_for_timeout(200); print('STRAIGHT', info(await q.inner_text('#selBody')))
        print('\n'.join(logs) or 'no page errors'); await br.close()
asyncio.run(main())
