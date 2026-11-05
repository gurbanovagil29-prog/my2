"""Озвучка сцен через ElevenLabs (голос George по умолчанию).

Сохраняет mp3 и тайминги символов (для субтитров Reels) в books/<книга>/audio_eleven/.
Ключ читается из ~/.config/elevenlabs_key или переменной ELEVENLABS_API_KEY.
Использование: python3 tools/gen_voice_eleven.py books/babylon [voice_id]
"""
import base64, json, os, pathlib, sys, time, urllib.request, urllib.error

book = pathlib.Path(sys.argv[1])
voice_id = sys.argv[2] if len(sys.argv) > 2 else "JBFqnCBsd6RMkjVDRZzb"  # George
key = os.environ.get("ELEVENLABS_API_KEY") or (pathlib.Path.home() / ".config/elevenlabs_key").read_text().strip()

d = json.loads((book / "scenes.json").read_text())
items = [("title", d["title"] + ". " + d["subtitle"].split("·")[0].strip() + ".")] + \
        [(s["id"], s["text"]) for s in d["scenes"]]
items = [(i, t.replace("+", "")) for i, t in items]
out = book / "audio_eleven"
out.mkdir(exist_ok=True)

for n, (sid, text) in enumerate(items):
    mp3 = out / f"{sid}.mp3"
    if mp3.exists():
        continue
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "language_code": "ru",
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True},
        # соседний текст помогает держать единую интонацию между сценами
        "previous_text": items[n - 1][1] if n > 0 else None,
        "next_text": items[n + 1][1] if n + 1 < len(items) else None,
    }
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128",
        data=json.dumps(body).encode(), headers={"xi-api-key": key, "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                res = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(5 * (attempt + 1)); continue
            sys.exit(f"Ошибка ElevenLabs на сцене {sid}: {e.code} {msg}")
    mp3.write_bytes(base64.b64decode(res["audio_base64"]))
    (out / f"{sid}.json").write_text(json.dumps(res.get("alignment"), ensure_ascii=False))
    print("voice", sid, flush=True)
print("done")
