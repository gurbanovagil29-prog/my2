"""Рендер HTML-слайдов в PNG и сборка PDF + PPTX. Картинки: src="fig:имя.png" -> папка figures."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from pptx import Presentation
from pptx.util import Emu
from PIL import Image

DECK, FIG, OUT, NAME = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
PNG = OUT / "_png"; PNG.mkdir(parents=True, exist_ok=True)
for f in PNG.glob("*.png"): f.unlink()
order = (DECK / "order.txt").read_text().split()
fonts = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&display=swap">'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">')
CSS = """body{margin:0} section{width:1920px;height:1080px;box-sizing:border-box;position:relative;overflow:hidden}
h1,h2,h3,p,ul,ol{margin:0} table{border-collapse:collapse}
th,td{padding:0.32em 0.6em;border-bottom:1px solid #D8D3C8;text-align:left;vertical-align:top} th{font-weight:600}"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    for i, sid in enumerate(order, 1):
        html = (DECK / "slides" / f"{sid}.html").read_text().replace('src="fig:', f'src="{FIG.resolve().as_uri()}/')
        page = OUT / "_page.html"
        page.write_text(f"<html><head><meta charset='utf-8'>{fonts}<style>{CSS}</style></head><body>{html}</body></html>")
        pg.goto(page.resolve().as_uri(), wait_until="networkidle"); pg.evaluate("document.fonts.ready")
        pg.screenshot(path=str(PNG / f"{i:02d}_{sid}.png"))
    b.close()
pngs = sorted(PNG.glob("*.png"))
imgs = [Image.open(x).convert("RGB") for x in pngs]
imgs[0].save(OUT / f"{NAME}.pdf", save_all=True, append_images=imgs[1:], resolution=150)
prs = Presentation(); prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
for x in pngs:
    prs.slides.add_slide(prs.slide_layouts[6]).shapes.add_picture(str(x), 0, 0, prs.slide_width, prs.slide_height)
prs.save(OUT / f"{NAME}.pptx")
print(len(pngs), "слайдов")
