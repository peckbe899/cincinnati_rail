import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); logs = []
        q = await b.new_page(viewport={"width": 1400, "height": 900})
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        for nm, (cx, cy) in [('cw_metro', (712463.2, 4334875.4)), ('ut_rer', (713137.5, 4331851)), ('cw_rer', (712421.4, 4334815.3)), ('kirby', (711896.1, 4338607.0))]:
            s = 1.5
            await q.goto(f"http://127.0.0.1:8765/index.html?n={nm}#{cx},{cy},{s}"); await q.wait_for_timeout(4000)
            r = await q.evaluate("(() => { const r = document.getElementById('cv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
            await q.mouse.click(r[0] + r[2] / 2, r[1] + r[3] / 2); await q.wait_for_timeout(300)
            print(nm.upper() + ':', (await q.inner_text('#selBody'))[:330].replace('\n', ' | '))
            await q.screenshot(path=f'lph/shots29/14_{nm}.png')
        await q.click('#xGeo'); await q.wait_for_timeout(500); await q.click('#xKmz'); await q.wait_for_timeout(500)
        print('STATUS:', await q.inner_text('#statusText'))
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
