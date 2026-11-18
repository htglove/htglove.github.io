# -*- coding: utf-8 -*-
"""글 폴더 안의 cardN.html 을 1080px 너비 imgN.png 로 렌더링 (Playwright Chromium)
  python3 _cafe/tools/render.py _cafe/posts/<폴더>"""
import asyncio, glob, os, re, sys
from playwright.async_api import async_playwright


async def main(folder):
    files = sorted(glob.glob(os.path.join(folder, "card*.html")))
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 800}, device_scale_factor=1)
        for f in files:
            n = re.search(r"card(\d+)\.html$", f).group(1)
            html = open(f, encoding="utf-8").read()
            if not html.lower().lstrip().startswith("<!doctype"):
                html = "<!doctype html>" + html
            await pg.set_content(html)
            await pg.wait_for_timeout(300)
            out = os.path.join(folder, f"img{n}.png")
            await pg.screenshot(path=out, full_page=True)
            print(out)
        await b.close()

asyncio.run(main(sys.argv[1]))
