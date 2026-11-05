"""Сборка горизонтального видео для YouTube (16:9, без субтитров).

Плавная камера (tools/motion.py), перетекание сцен друг в друга, озвучка ElevenLabs.
Использование: python3 tools/build_youtube.py books/babylon [папка_аудио]
"""
import json, re, subprocess, sys, pathlib
from multiprocessing import Pool
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from motion import render_clip, W, H

book = pathlib.Path(sys.argv[1])
audio_dir = book / (sys.argv[2] if len(sys.argv) > 2 else "audio_eleven")
d = json.loads((book / "scenes.json").read_text())
build = book / "build_yt"
build.mkdir(exist_ok=True)
SR = 44100
X = 1.0      # длительность перетекания между сценами, с
LEAD = 0.35  # пауза перед голосом в начале сцены, с
GAP = 0.55   # пауза после фразы, с
FONT_DIR = "/usr/share/fonts/opentype/inter/"

def load_audio(path):
    wav = build / (path.stem + ".wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), str(wav)], check=True)
    a, _ = sf.read(wav, dtype="float32")
    return a

def title_card():
    im = Image.open(book / "images" / f"{d['scenes'][0]['id']}.jpg").convert("RGB")
    im = ImageEnhance.Brightness(im.filter(ImageFilter.GaussianBlur(6))).enhance(0.45)
    dr = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(FONT_DIR + "InterDisplay-ExtraBold.otf", 104)
    f2 = ImageFont.truetype(FONT_DIR + "InterDisplay-Medium.otf", 46)
    words = re.sub(r"(?<=\s)(\S{1,2})\s", "\\1\u00a0", " " + d["title"].upper()).split(" ")[1:]
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if dr.textlength(test, font=f1) > W * 0.82 and cur:
            lines.append(cur); cur = w
        else:
            cur = test
    lines.append(cur)
    y = H / 2 - len(lines) * 62 - 30
    for ln in lines:
        dr.text((W / 2, y), ln, font=f1, fill="white", anchor="mt"); y += 124
    dr.text((W / 2, y + 30), d["subtitle"], font=f2, fill=(240, 200, 120), anchor="mt")
    p = build / "title.jpg"
    im.save(p, quality=94)
    return p

def job(args):
    n, img, out, dur = args
    render_clip(img, out, dur, n)
    print(f"clip {n} готов", flush=True)

if __name__ == "__main__":
    segs = [("title", title_card())] + [(s["id"], book / "images" / f"{s['id']}.jpg") for s in d["scenes"]]
    audios = [load_audio(audio_dir / f"{sid}.mp3") for sid, _ in segs]
    durs = []
    for n, a in enumerate(audios):
        dur = LEAD + len(a) / SR + GAP + X + (0.6 if n == 0 else 0)
        durs.append(round(dur * 30) / 30)

    # 1) клипы с плавной камерой — параллельно
    clips = [build / f"clip_{n:02d}.mp4" for n in range(len(segs))]
    with Pool(4) as pool:
        pool.map(job, [(n, str(img), str(clips[n]), durs[n]) for n, (_, img) in enumerate(segs)])

    # 2) звук: каждая фраза на своём месте временной шкалы
    starts, t = [], 0.0
    for dur in durs:
        starts.append(t); t += dur - X
    total = starts[-1] + durs[-1]
    mix = np.zeros(int(total * SR) + SR, dtype="float32")
    for n, a in enumerate(audios):
        s = int((starts[n] + LEAD + (0.6 if n == 0 else 0)) * SR)
        mix[s:s + len(a)] += a
    sf.write(build / "voice.wav", mix[:int(total * SR)], SR)

    # 3) видео: цепочка перетеканий xfade + звук
    inputs, chain, prev, off = [], [], "0:v", 0.0
    for c in clips:
        inputs += ["-i", str(c)]
    for n in range(1, len(clips)):
        off += durs[n - 1] - X
        lbl = f"v{n}"
        chain.append(f"[{prev}][{n}:v]xfade=transition=fade:duration={X}:offset={off:.3f}[{lbl}]")
        prev = lbl
    chain.append(f"[{prev}]fade=t=in:st=0:d=0.8,fade=t=out:st={total-1.2:.3f}:d=1.2,format=yuv420p[vout]")
    out = book / "output"
    out.mkdir(exist_ok=True)
    final = out / "youtube.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-i", str(build / "voice.wav"),
                    "-filter_complex", ";".join(chain),
                    "-map", "[vout]", "-map", f"{len(clips)}:a",
                    "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st={total-1.2:.3f}:d=1.2",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
                    "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000", "-movflags", "+faststart",
                    str(final)], check=True)
    print("done", final, f"{total:.1f}s")
