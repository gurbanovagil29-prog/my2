"""Плавное движение камеры по картинке (без рывков zoompan).

Каждый кадр считается с субпиксельной точностью (аффинное преобразование
с бикубической интерполяцией) и плавным ускорением/замедлением (easing).
"""
import subprocess
from PIL import Image

W, H, FPS = 1920, 1080, 30

MOVES = [  # (зум_начало, зум_конец, сдвиг_x_начало, сдвиг_x_конец, сдвиг_y_начало, сдвиг_y_конец)
    (1.00, 1.14, 0.0, 0.0, 0.0, -0.02),    # медленный наезд
    (1.16, 1.04, 0.03, -0.03, 0.0, 0.0),   # отъезд с проходом влево
    (1.12, 1.12, -0.05, 0.05, 0.0, 0.0),   # панорама вправо
    (1.04, 1.16, 0.03, 0.0, 0.02, -0.01),  # наезд со смещением
    (1.12, 1.12, 0.05, -0.05, 0.01, -0.01),  # панорама влево
    (1.14, 1.00, 0.0, 0.0, -0.02, 0.0),    # отъезд
]

def ease(t):
    # мягкий старт и мягкая остановка, но без полной остановки в середине
    s = t * t * (3 - 2 * t)
    return 0.35 * t + 0.65 * s

def render_clip(img_path, out_path, seconds, move_index, src_scale=1.0):
    src = Image.open(img_path).convert("RGB")
    # исходник с запасом под зум, чтобы не было мыла
    big = src.resize((int(W * 1.25 * src_scale), int(H * 1.25 * src_scale)), Image.LANCZOS)
    bw, bh = big.size
    z0, z1, x0, x1, y0, y1 = MOVES[move_index % len(MOVES)]
    frames = round(seconds * FPS)
    p = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
         "-pix_fmt", "yuv420p", str(out_path)], stdin=subprocess.PIPE)
    for f in range(frames):
        t = ease(f / max(1, frames - 1))
        z = z0 + (z1 - z0) * t
        # видимая область в координатах большой картинки
        vw, vh = bw / z, bh / z
        cx = bw / 2 + (x0 + (x1 - x0) * t) * bw
        cy = bh / 2 + (y0 + (y1 - y0) * t) * bh
        left = min(max(cx - vw / 2, 0), bw - vw)
        top = min(max(cy - vh / 2, 0), bh - vh)
        sx, sy = vw / W, vh / H
        frame = big.transform((W, H), Image.AFFINE, (sx, 0, left, 0, sy, top), resample=Image.BICUBIC)
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    p.wait()
    return frames / FPS
