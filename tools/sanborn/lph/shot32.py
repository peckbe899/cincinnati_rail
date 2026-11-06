import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); q = await b.new_page(viewport={"width": 1400, "height": 1000})
        await q.goto("http://127.0.0.1:8765/index.html?v=33#712280,4335500,0.62"); await q.wait_for_timeout(5000)
        await q.screenshot(path='lph/shots29/23_trunk_new.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915}); await b.close()
asyncio.run(main())
