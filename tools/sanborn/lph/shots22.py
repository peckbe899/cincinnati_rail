import asyncio, sys
from playwright.async_api import async_playwright
OUT = sys.argv[1]
VIEWS = [('lph', '711950,4331350,1.0'), ('lphn', '711900,4331600,1.6'), ('hop2', '712300,4334900,1.2'), ('lud2', '712800,4336800,1.2')]

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
