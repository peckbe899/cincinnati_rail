import asyncio, math
from playwright.async_api import async_playwright
a, b = (712161.0, 4331820.7), (712226.3, 4332847.9)
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(); logs = []
        q = await br.new_page(viewport={"width": 1400, "height": 900}); q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        cx, cy, s = b[0], b[1] - 60, 1.5
        await q.goto(f"http://127.0.0.1:8765/index.html?l=1#{cx},{cy},{s}"); await q.wait_for_timeout(4000)
        r = await q.evaluate("(() => { const r = document.getElementById('cv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
        W = lambda wx, wy: (r[0] + (wx - cx) * s + r[2] / 2, r[1] + (cy - wy) * s + r[3] / 2)
        S2W = lambda px, py: ((px - r[0] - r[2] / 2) / s + cx, cy - (py - r[1] - r[3] / 2) / s)
        mx, my = W((a[0] + b[0]) / 2 * 0.1 + b[0] * 0.9, (a[1] + b[1]) / 2 * 0.1 + b[1] * 0.9)
        await q.mouse.click(mx, my); await q.wait_for_timeout(300); print('SEL', (await q.inner_text('#selBody')).split('\n')[0])
        await q.click('#tEdit'); x, y = W(*b)
        await q.keyboard.down('Control'); await q.mouse.move(x, y); await q.mouse.down()
        await q.mouse.move(x + 20, y - 40, steps=5); await q.mouse.move(x + 60, y - 120, steps=8)
        await q.screenshot(path='lph/shots29/20_lock_drag.png'); await q.mouse.up(); await q.keyboard.up('Control'); await q.wait_for_timeout(300)
        info = (await q.inner_text('#selBody')).replace('\n', ' | ')[:220]; print('AFTER', info)
        # read back the end point by exporting? compute from the drop point projection
        ex, ey = S2W(x + 60, y - 120); ux, uy = b[0] - a[0], b[1] - a[1]; L = math.hypot(ux, uy); ux, uy = ux / L, uy / L
        sproj = (ex - b[0]) * ux + (ey - b[1]) * uy
        print('expected extension along line (m):', round(sproj, 1), ' new length ~', round(L + sproj))
        # free drag without ctrl for contrast, then undo
        x2, y2 = W(b[0] + ux * sproj, b[1] + uy * sproj)
        await q.mouse.move(x2, y2); await q.mouse.down(); await q.mouse.move(x2 + 40, y2, steps=5); await q.mouse.up(); await q.wait_for_timeout(200)
        print('FREE', (await q.inner_text('#selBody')).replace('\n', ' | ')[:160])
        await q.click('#uUndo'); await q.wait_for_timeout(200); print('UNDO', (await q.inner_text('#selBody')).replace('\n', ' | ')[:160])
        print('\n'.join(logs) or 'no page errors'); await br.close()
asyncio.run(main())
