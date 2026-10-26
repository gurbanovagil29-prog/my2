"""Итоговая важность истории по шкале 0–10.

Складывается из трёх частей:
  тема   — ключевые слова, максимум topic_max; растёт всё медленнее, словами 10 не набрать;
  охват  — сколько разных СМИ написали об истории и как быстро;
  событие — бонус за историческое событие из короткого списка (группы с event: true).
Высокие баллы требуют охвата: одно СМИ даёт не больше single_source_max,
а 10 возможно только для исторического события, о котором пишут top_min_sources СМИ.
"""
import math

from .store import Story


def importance(story: Story, cfg: dict) -> float:
    topic = cfg["topic_max"] * (1 - math.exp(-story.score / cfg["topic_scale"]))
    if story.event:  # историческое событие важно по определению, какими бы словами его ни описали
        topic = max(topic, cfg["event_topic_min"])
    n = len(story.sources)
    coverage_steps = cfg["coverage"]
    coverage = coverage_steps[min(n, len(coverage_steps)) - 1] if n else 0
    burst = cfg["burst"]
    if story.sources_within(burst["minutes"]) >= burst["sources"]:
        coverage += burst["bonus"]
    total = topic + coverage + (cfg["event_bonus"] if story.event else 0)

    if n <= 1:
        total = min(total, cfg["single_source_max"])
    if not (story.event and n >= cfg["top_min_sources"]):
        total = min(total, 9)
    return round(min(total, 10), 1)
