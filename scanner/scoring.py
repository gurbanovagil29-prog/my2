"""Оценка важности новости по ключевым словам."""
import re

from .models import Item, Score


def _compile(pattern: str) -> re.Pattern:
    # (?<!\w) — совпадение только с начала слова, чтобы "нато" не находилось в "ренатов".
    return re.compile(r"(?<!\w)(?:" + pattern + ")", re.IGNORECASE)


def _compile_any(patterns: list[str]) -> re.Pattern | None:
    if not patterns:
        return None
    return _compile("|".join(f"(?:{p})" for p in patterns))


class Scorer:
    def __init__(self, cfg: dict):
        self.groups = [
            (g.get("weight", 0), g.get("boost", False), g.get("event", False),
             [(kw, _compile(kw)) for kw in g["keywords"]], _compile_any(g.get("exclude", [])))
            for g in cfg.get("keywords", {}).values()
        ]
        self.blocklist = _compile_any(cfg.get("blocklist", []))
        crypto = cfg.get("crypto", {})
        self.crypto_required = _compile_any(crypto.get("required", []))
        self.crypto_blocklist = _compile_any(crypto.get("blocklist", []))

    def score(self, item: Item) -> Score | None:
        """Возвращает None, если новость надо отбросить безусловно."""
        title, summary = item.title, item.summary
        both = f"{title}\n{summary}"
        if self.blocklist and self.blocklist.search(title):
            return None
        if self.crypto_blocklist and self.crypto_blocklist.search(both):
            return None
        if item.category == "crypto" and self.crypto_required and not self.crypto_required.search(both):
            return None

        # Первое совпадение в группе даёт полный вес, каждое следующее — +1:
        # "Песков" + "Кремль" — это одна тема, а "Трамп" + "Иран" + "ставка" — уже несколько.
        # Группы с boost: true (действия: "повысил", "одобрил") считаются, только если тема уже найдена.
        # Группы с event: true (исторические события) баллов не дают, а только ставят отметку.
        value, boost, hits, event = 0.0, 0.0, [], False
        for weight, is_boost, is_event, patterns, exclude in self.groups:
            if exclude and exclude.search(title):  # например, "продление военного положения" — не событие
                continue
            if is_event:
                for _, rx in patterns:
                    if m := rx.search(title):  # только по заголовку — список строгий
                        event = True
                        hits.append(m.group(0).lower())
                continue
            group_value = 0.0
            for kw, rx in patterns:
                if m := rx.search(title):
                    gain = weight
                elif m := rx.search(summary):
                    gain = weight / 2
                else:
                    continue
                group_value += gain if not group_value else min(gain, 1)
                hits.append(m.group(0).lower())
            if is_boost:
                boost += group_value
            else:
                value += group_value
        if value > 0:
            value += boost + item.source_weight
        return Score(value, hits, event)
