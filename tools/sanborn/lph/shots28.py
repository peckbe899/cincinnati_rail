import asyncio, sys
from playwright.async_api import async_playwright
OUT = sys.argv[1]
VIEWS = [("dive", "712560,4334650,1.3"), ("lobe", "712270,4335250,1.1"), ("turn", "712200,4335850,0.95"), ("over", "712350,4335450,0.33")]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); logs = []
        for nm, h in VIEWS:
            q = await b.new_page(viewport={"width": 1400, "height": 900})
            q.on("console", lambda m: logs.append(f"{m.type}: {m.text}")); q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
            await q.goto("http://127.0.0.1:8765/index.html#" + h); await q.wait_for_timeout(6000)
            await q.screenshot(path=OUT + f"/v_{nm}.png", clip={"x": 8, "y": 85, "width": 1043, "height": 815}); await q.close()
        print("\n".join(logs[:20])); await b.close()
asyncio.run(main())
