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
        q.on("console", lambda m: logs.append(f"{m.type}: {m.text}"[:300]) if m.type == 'error' else None)
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto("http://127.0.0.1:8765/index.html?debug&r=9#714190,4332600,2.2")
        for i in range(80):
            await q.wait_for_timeout(400)
            if 'redrawn' in await q.inner_text('#plotNote') or 'plots,' in await q.inner_text('#plotNote'): break
        await q.wait_for_timeout(800)
        print('canWrite', await q.evaluate("__S.canWrite"))
        print('lockNote:', await q.inner_text('#lockNote'), '| button:', await q.inner_text('#lockAll'), await q.evaluate("document.getElementById('lockAll').disabled"))
        async def click_world(X, Y):
            pt = await q.evaluate(f"(() => {{ const r = document.getElementById('cv').getBoundingClientRect(), v = __S.view; return [r.left + r.width / 2 + ({X} - v.cx) * v.s, r.top + r.height / 2 - ({Y} - v.cy) * v.s]; }})()")
            await q.mouse.click(pt[0], pt[1]); await q.wait_for_timeout(500)
            return (await q.inner_text('#selBody'))[:300].replace('\n', ' | ')
        # a plot in SBB0147
        print('plot ->', await click_world(714190, 4332590))
        sel_block = await q.evaluate("__S.sel.f.properties.block")
        print('block of selection', sel_block)
        await q.get_by_role('button', name='Select the block').click(); await q.wait_for_timeout(400)
        print('block panel ->', (await q.inner_text('#selBody'))[:400].replace('\n', ' | '))
        btn = q.get_by_role('button', name='Lock the plots (checked by hand)')
        await btn.click(); await q.wait_for_timeout(500)
        print('after lock ->', (await q.inner_text('#selBody'))[:300].replace('\n', ' | '))
        print('edits.blocks', await q.evaluate(f"JSON.stringify(__S.edits.blocks['{sel_block}'])"))
        print('plot ->', await click_world(714190, 4332590))
        print('split disabled', await q.evaluate("[...document.querySelectorAll('#selBody button')].filter(b => /Split|Merge with|Divide/.test(b.textContent)).map(b => b.textContent + ':' + b.disabled).join(', ')"))
        await q.screenshot(path=SP + 'plots/v_lock1.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        await q.click('#lockAll'); await q.wait_for_timeout(500)
        print('after lockAll:', await q.inner_text('#lockNote'), '| locked', await q.evaluate("JSON.stringify(Object.entries(__S.edits.blocks).filter(([k, e]) => e && e.lk).map(([k]) => k))"))
        await q.evaluate("location.hash = '#713200,4333200,0.6'"); await q.wait_for_timeout(1500)
        await q.screenshot(path=SP + 'plots/v_lock2.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
