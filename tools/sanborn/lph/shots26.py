import asyncio, sys
from playwright.async_api import async_playwright
OUT = sys.argv[1]
VIEWS = [("s", "712050,4331900,0.45"), ("m", "712050,4334000,0.45"), ("n", "712050,4336000,0.45")]

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1400, "height": 900})
        logs = []; pg.on("console", lambda m: logs.append(f"{m.type}: {m.text}")); pg.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        await pg.goto("http://127.0.0.1:8765/index.html"); await pg.wait_for_timeout(4000)
        for nm, h in VIEWS:
            q = await b.new_page(viewport={"width": 1400, "height": 900})
            await q.goto("http://127.0.0.1:8765/index.html#" + h); await q.wait_for_timeout(6000)
            await q.screenshot(path=OUT + f"/v_{nm}.png", clip={"x": 8, "y": 85, "width": 1043, "height": 815}); await q.close()
        print("\n".join(logs[:20])); await b.close()
asyncio.run(main())
