import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); logs = []
        q = await b.new_page(viewport={"width": 1400, "height": 900}); q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        cx, cy, s = 712102.5, 4333378.7, 1.6
        await q.goto(f"http://127.0.0.1:8765/index.html?u=1#{cx},{cy},{s}"); await q.wait_for_timeout(4000)
        r = await q.evaluate("(() => { const r = document.getElementById('cv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
        x, y = r[0] + r[2] / 2, r[1] + r[3] / 2
        st = lambda: q.evaluate("[document.getElementById('uUndo').disabled, document.getElementById('uRedo').disabled, document.getElementById('editNote').textContent.slice(0, 60)]")
        print('start', await st())
        await q.mouse.click(x, y); await q.click('#tEdit')
        await q.mouse.move(x, y); await q.mouse.down(); await q.mouse.move(x + 40, y + 40, steps=6); await q.mouse.move(x + 70, y + 70, steps=6); await q.mouse.up(); await q.wait_for_timeout(200)
        print('drag', await st(), (await q.inner_text('#selBody')).split('\n')[10:13])
        await q.get_by_role('button', name='Side', exact=True).first.click(); await q.wait_for_timeout(200)
        print('side', await st())
        await q.click('#uUndo'); await q.wait_for_timeout(200); print('undo1', await st(), [l for l in (await q.inner_text('#selBody')).split('\n') if 'RER A:' in l or 'Centre' in l])
        await q.keyboard.press('Control+z'); await q.wait_for_timeout(200); print('undo2', await st(), [l for l in (await q.inner_text('#selBody')).split('\n') if 'RER A:' in l or 'Centre' in l])
        await q.keyboard.press('Control+Shift+z'); await q.wait_for_timeout(200); print('redo1', await st(), [l for l in (await q.inner_text('#selBody')).split('\n') if 'RER A:' in l or 'Centre' in l])
        await q.screenshot(path='lph/shots29/18_undo.png', clip={"x": 0, "y": 0, "width": 1400, "height": 120})
        m = await b.new_page(viewport={"width": 390, "height": 800}); await m.goto("http://127.0.0.1:8765/index.html?u=2"); await m.wait_for_timeout(3000)
        await m.screenshot(path='lph/shots29/19_mobile.png'); sw = await m.evaluate("document.documentElement.scrollWidth"); print('mobile scrollWidth', sw)
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
