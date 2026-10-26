from pathlib import Path

import yaml

from scanner.models import Item
from scanner.scoring import Scorer
from scanner.store import similarity, tokens

CFG = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text(encoding="utf-8"))
scorer = Scorer(CFG)


def item(title, category="russia", summary=""):
    return Item(uid=title, source="test", category=category, title=title, summary=summary, link="")


def test_important_news_passes():
    assert scorer.score(item("ЦБ неожиданно повысил ключевую ставку до 18%")).value >= CFG["thresholds"]["send"]
    assert scorer.score(item("Трамп ввёл пошлины против Китая", "world")).value >= CFG["thresholds"]["send"]


def test_noise_is_dropped():
    assert scorer.score(item("Песков: Россия должна вернуться в мировую спортивную семью", summary="матч")).value < 6
    assert scorer.score(item("Сборная России по футболу сыграет матч с Сербией")) is None


def test_crypto_only_majors():
    assert scorer.score(item("New memecoin surges 300% after airdrop", "crypto")) is None
    assert scorer.score(item("Solana-based DEX launches v2", "crypto")) is None
    assert scorer.score(item("SEC approves spot Ethereum ETF options", "crypto")).value >= 6


def test_same_story_from_different_outlets():
    a = tokens("CNN: Нетаньяху не убедил Трампа ударить по Ирану до выборов в Израиле")
    b = tokens("CNN: Трамп отказал Нетаньяху в новой атаке на Иран до выборов в Израиле")
    c = tokens("Песков: Россия приветствует победу Лулы на выборах в Бразилии")
    assert similarity(a, b) >= CFG["corroboration"]["similarity"]
    assert similarity(a, c) < CFG["corroboration"]["similarity"]
