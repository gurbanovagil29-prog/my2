from pathlib import Path

import yaml

from scanner.models import Item
from scanner.routes import Route
from scanner.store import Story
from scanner.scoring import Scorer
from scanner.store import similarity, tokens

CFG = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text(encoding="utf-8"))
scorer = Scorer(CFG)
SEND = CFG["channels"]["feed"]["min_score"]


def item(title, category="russia", summary=""):
    return Item(uid=title, source="test", category=category, title=title, summary=summary, link="")


def test_important_news_passes():
    assert scorer.score(item("ЦБ неожиданно повысил ключевую ставку до 18%")).value >= SEND
    assert scorer.score(item("Трамп ввёл пошлины против Китая", "world")).value >= SEND


def test_noise_is_dropped():
    assert scorer.score(item("Песков: Россия должна вернуться в мировую спортивную семью", summary="матч")).value < SEND
    assert scorer.score(item("Сборная России по футболу сыграет матч с Сербией")) is None


def test_crypto_only_majors():
    assert scorer.score(item("New memecoin surges 300% after airdrop", "crypto")) is None
    assert scorer.score(item("Solana-based DEX launches v2", "crypto")) is None
    assert scorer.score(item("SEC approves spot Ethereum ETF options", "crypto")).value >= SEND


def test_same_story_from_different_outlets():
    a = tokens("CNN: Нетаньяху не убедил Трампа ударить по Ирану до выборов в Израиле")
    b = tokens("CNN: Трамп отказал Нетаньяху в новой атаке на Иран до выборов в Израиле")
    c = tokens("Песков: Россия приветствует победу Лулы на выборах в Бразилии")
    assert similarity(a, b) >= CFG["story"]["similarity"]
    assert similarity(a, c) < CFG["story"]["similarity"]


def test_urgent_burst():
    urgent = Route.from_config("urgent", CFG["channels"]["urgent"])
    story = Story(titles=[], best=item("Трамп купил дизель у России"), score=4, created=0)
    story.source_times = {"ТАСС": 0, "РБК": 60}
    assert urgent.reason(story, now=120) is None
    story.source_times.update({"Интерфакс": 300, "Коммерсант": 600})
    assert urgent.reason(story, now=600)            # 4 СМИ за 10 минут — срочно
    assert urgent.reason(story, now=3 * 3600) is None  # но спустя 3 часа уже не срочно


def test_translation_fallbacks(monkeypatch):
    from scanner import translate

    assert not translate.needs_translation("ЦБ повысил ставку")
    assert translate.needs_translation("Fed cuts rates")
    t = translate.Translator()
    monkeypatch.setattr(translate, "_google", lambda text, s: None)
    monkeypatch.setattr(translate, "_mymemory", lambda text, s: "ФРС снизила ставки")
    assert t("Fed cuts rates") == "ФРС снизила ставки"
    monkeypatch.setattr(translate, "_mymemory", lambda text, s: "MYMEMORY WARNING")  # не перевод
    assert t("Oil jumps") == "Oil jumps"
