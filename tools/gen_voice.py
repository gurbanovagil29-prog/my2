"""Озвучка сцен бесплатным локальным Piper TTS (ONNX-голоса, без API).

Ударения в сценарии отмечаются «+» перед гласной (Арк+ад) и превращаются
в знак ударения U+0301, который понимает русский фонемизатор.
"""
import json, re, sys, wave, pathlib
from piper import PiperVoice, SynthesisConfig

book = pathlib.Path(sys.argv[1])
voice_name = sys.argv[2] if len(sys.argv) > 2 else "ru_RU-dmitri-medium"
only = sys.argv[3] if len(sys.argv) > 3 else None  # номер сцены для пробы

d = json.loads((book / "scenes.json").read_text())
voice = PiperVoice.load(str(pathlib.Path.home() / ".cache/piper" / f"{voice_name}.onnx"))
cfg = SynthesisConfig(length_scale=1.08, noise_scale=0.6, noise_w_scale=0.7)

def prep(t):
    return re.sub(r"\+([аеёиоуыэюяАЕЁИОУЫЭЮЯ])", "\\1\u0301", t)

texts = [("title", d["title"] + ". " + d["subtitle"].split("·")[0].strip() + ".")] + [(s["id"], s["text"]) for s in d["scenes"]]
out = book / ("audio" if only is None else "samples")
out.mkdir(exist_ok=True)
for i, text in texts:
    if only is not None and i != only:
        continue
    dst = out / (f"{i}.wav" if only is None else f"{voice_name}_{i}.wav")
    with wave.open(str(dst), "wb") as w:
        voice.synthesize_wav(prep(text), w, syn_config=cfg)
    print("voice", i, flush=True)
