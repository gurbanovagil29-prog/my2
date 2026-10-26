from pathlib import Path

import yaml

from scanner.models import Item
from scanner.routes import Route
from scanner.store import Story
from scanner.scoring import Scorer
from scanner.store import similarity, tokens

CFG = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text(encoding="utf-8"))
scorer = Scorer(CFG)
SEND = 6  # сырые баллы ключевых слов, при которых новость явно по теме


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


SCALE = CFG["importance"]


def test_urgent_burst():
    urgent = Route.from_config("urgent", CFG["channels"]["urgent"])
    story = Story(titles=[], best=item("Трамп купил дизель у России"), score=6, created=0)
    story.source_times = {"ТАСС": 0}
    assert urgent.reason(story, now=120, scale=SCALE) is None
    story.source_times.update({"РБК": 60, "Интерфакс": 300, "Коммерсант": 600})
    assert urgent.reason(story, now=600, scale=SCALE)            # 4 СМИ за 10 минут — срочно
    assert urgent.reason(story, now=3 * 3600, scale=SCALE) is None  # но спустя 3 часа уже не срочно


def test_importance_scale():
    from scanner.importance import importance

    def story(title, outlets):
        s = scorer.score(item(title))
        st = Story(titles=[], best=item(title), score=s.value, created=0, event=s.event)
        st.source_times = {o: 0 for o in outlets}
        return importance(st, SCALE)

    one = ["ТАСС"]
    many = ["ТАСС", "РБК", "РИА", "Интерфакс", "Коммерсант", "Ведомости"]
    # Одно СМИ, сколько бы ключевых слов ни было, — не выше single_source_max.
    assert story("Путин, Трамп, санкции, ЦБ, ставка, нефть, Иран, Китай, войн", one) <= SCALE["single_source_max"]
    # Важная тема без исторического события — не выше 9 даже при полном охвате.
    assert 6 <= story("ЦБ повысил ключевую ставку до 18%", many) <= 9
    # 10 — только историческое событие, о котором пишут все.
    assert story("Россия и Украина подписали мирный договор", many) == 10
    assert story("Россия и Украина подписали мирный договор", one) < 10
    assert story("Песков прокомментировал визит делегации Алжира", one) < CFG["channels"]["feed"]["min_importance"]


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


def test_historic_exclusions():
    assert scorer.score(item("В России введено военное положение")).event
    assert not scorer.score(item("Рада проголосовала за продление военного положения")).event
    assert not scorer.score(item("Эксперт: Россия может ввести военное положение")).event
