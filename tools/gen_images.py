"""Генерация иллюстраций для сцен через бесплатный Pollinations (1 картинка / 45 с)."""
import json, sys, time, urllib.parse, urllib.request, pathlib
from PIL import Image

book = pathlib.Path(sys.argv[1])
d = json.loads((book / "scenes.json").read_text())
out = book / "images"
out.mkdir(exist_ok=True)

def prompt_for(scene):
    p = scene["image"]
    for key, desc in sorted(d["characters"].items(), key=lambda kv: -len(kv[0])):
        p = p.replace(key, desc)
    return f"{p}. {d['style']}"

for i, s in enumerate(d["scenes"]):
    dst = out / f"{s['id']}.jpg"
    if dst.exists():
        continue
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt_for(s))
           + f"?width=1280&height=720&seed={100 + int(s['id'])}&nologo=true")
    for attempt in range(8):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                raw = r.read()
            tmp = out / "tmp.jpg"
            tmp.write_bytes(raw)
            im = Image.open(tmp).convert("RGB")
            w, h = im.size
            # обрезаем водяной знак в правом нижнем углу и белые края, оставляя 16:9
            cw = int(w * 0.92); ch = int(cw * 9 / 16)
            x0 = int(w * 0.015); y0 = max(0, int((h * 0.94 - ch) / 2))
            im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((1920, 1080), Image.LANCZOS)
            im.save(dst, quality=92)
            tmp.unlink()
            print(f"ok {i}", flush=True)
            break
        except Exception as e:
            print(f"retry {i}: {e}", flush=True)
            time.sleep(20)
    time.sleep(47)
print("done")
