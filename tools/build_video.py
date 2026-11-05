"""Сборка видео: картинки + озвучка + плавный наезд камеры + переходы + субтитры.

Использование: python3 tools/build_video.py books/babylon [--no-subs]
"""
import json, re, sys, subprocess, pathlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

book = pathlib.Path(sys.argv[1])
subs_on = "--no-subs" not in sys.argv
d = json.loads((book / "scenes.json").read_text())
build = book / "build"
build.mkdir(exist_ok=True)
FPS, W, H = 25, 1920, 1080
GAP = 0.7          # пауза после каждой сцены, с
FADE = 0.35        # затемнение на стыках, с
FONT_DIR = "/usr/share/fonts/opentype/inter/"

def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout)

def clean(t):
    return t.replace("+", "")

# ---------- заставка ----------
def title_card():
    im = Image.open(book / "images" / f"{d['scenes'][0]['id']}.jpg").convert("RGB")
    im = ImageEnhance.Brightness(im.filter(ImageFilter.GaussianBlur(6))).enhance(0.45)
    dr = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(FONT_DIR + "InterDisplay-ExtraBold.otf", 104)
    f2 = ImageFont.truetype(FONT_DIR + "InterDisplay-Medium.otf", 46)
    # короткие предлоги не оставляем в конце строки
    words, lines, cur = re.sub(r"(?<=\s)(\S{1,2})\s", "\\1\u00a0", " " + d["title"].upper()).split(" ")[1:], [], ""
    for w in words:  # перенос по ширине
        test = (cur + " " + w).strip()
        if dr.textlength(test, font=f1) > W * 0.82 and cur:
            lines.append(cur); cur = w
        else:
            cur = test
    lines.append(cur)
    y = H / 2 - len(lines) * 62 - 30
    for ln in lines:
        dr.text((W / 2, y), ln, font=f1, fill="white", anchor="mt")
        y += 124
    dr.text((W / 2, y + 30), d["subtitle"], font=f2, fill=(240, 200, 120), anchor="mt")
    p = build / "title.jpg"
    im.save(p, quality=94)
    return p

# ---------- сегменты ----------
segments = [("title", title_card(), book / "audio" / "title.wav", 1.2)]
for s in d["scenes"]:
    segments.append((s["id"], book / "images" / f"{s['id']}.jpg", book / "audio" / f"{s['id']}.wav", GAP))

clips, audio_parts, events, t = [], [], [], 0.0
for n, (sid, img, wav, gap) in enumerate(segments):
    dur = duration(wav) + gap + (0.5 if n == 0 else 0)
    frames = round(dur * FPS)
    dur = frames / FPS
    # чётные сцены — наезд, нечётные — отъезд, со лёгким сдвигом
    if n % 2 == 0:
        z = f"1+0.12*on/{frames}"
    else:
        z = f"1.12-0.12*on/{frames}"
    vf = (f"scale={W*2}:{H*2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={frames}:s={W}x{H}:fps={FPS},"
          f"fade=t=in:st=0:d={FADE},fade=t=out:st={dur-FADE:.3f}:d={FADE},format=yuv420p")
    clip = build / f"clip_{n:02d}.mp4"
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-vf", vf, "-frames:v", str(frames),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-r", str(FPS), str(clip)])
    clips.append(clip)
    # аудио, дополненное тишиной до длины клипа
    part = build / f"aud_{n:02d}.wav"
    lead = 0.5 if n == 0 else 0
    run(["ffmpeg", "-y", "-i", str(wav), "-af",
         f"adelay={int(lead*1000)}:all=1,apad,atrim=0:{dur:.3f},aresample=48000",
         "-ac", "1", str(part)])
    audio_parts.append(part)
    # субтитры: делим текст на фразы, время пропорционально длине
    if sid != "title":
        text = clean(next(s["text"] for s in d["scenes"] if s["id"] == sid))
        chunks = [c.strip() for c in re.split(r"(?<=[.!?…»])\s+(?=[«А-ЯЁ—])", text) if c.strip()]
        split = []
        for c in chunks:  # длинные фразы режем по запятым
            while len(c) > 90:
                cut = c.rfind(", ", 0, 90)
                cut = cut if cut > 30 else c.find(" ", 70)
                if cut <= 0: break
                split.append(c[:cut + 1].strip()); c = c[cut + 1:].strip()
            split.append(c)
        speech = duration(wav)
        total = sum(len(c) for c in split)
        ct = t
        for c in split:
            dt = speech * len(c) / total
            events.append((ct, ct + dt, c)); ct += dt
    t += dur
    print(f"clip {n} {sid} {dur:.1f}s", flush=True)

# ---------- склейка ----------
(build / "clips.txt").write_text("".join(f"file '{c.name}'\n" for c in clips))
run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(build / "clips.txt"), "-c", "copy", str(build / "video.mp4")])
(build / "audio.txt").write_text("".join(f"file '{a.name}'\n" for a in audio_parts))
run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(build / "audio.txt"),
     "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", str(build / "audio.wav")])

def ts(x):
    h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
    return f"{h}:{m:02d}:{s:05.2f}"

ass = build / "subs.ass"
ass.write_text(
    "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n"
    "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
    "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
    "Alignment, MarginL, MarginR, MarginV, Encoding\n"
    "Style: Default,Inter SemiBold,54,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,3.2,1.5,2,160,160,70,1\n\n"
    "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    + "".join(f"Dialogue: 0,{ts(a)},{ts(b)},Default,,0,0,0,,{c}\n" for a, b, c in events))

out = book / "output"
out.mkdir(exist_ok=True)
final = out / ("video_subs.mp4" if subs_on else "video.mp4")
vf = ["-vf", f"subtitles={ass}:fontsdir={FONT_DIR}"] if subs_on else []
run(["ffmpeg", "-y", "-i", str(build / "video.mp4"), "-i", str(build / "audio.wav"), *vf,
     "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
     "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)])
print("done", final, f"{duration(final):.1f}s")
