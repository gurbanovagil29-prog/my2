"""Память сканера: что уже видели (SQLite) и группировка похожих заголовков в истории."""
import re
import sqlite3
import time
from dataclasses import dataclass, field

from .models import Item, Score

_WORD = re.compile(r"\w+", re.UNICODE)


def tokens(title: str) -> frozenset[str]:
    # Грубый стемминг: первые 5 букв слова, чтобы "Трамп"/"Трампа" и "санкции"/"санкций" совпали.
    return frozenset(w[:5] for w in _WORD.findall(title.lower()) if len(w) >= 4)


def similarity(a: frozenset[str], b: frozenset[str]) -> float:
    """Доля общих слов от более короткого заголовка; меньше 3 общих слов — разные истории."""
    common = len(a & b)
    if common < 3:
        return 0.0
    return common / min(len(a), len(b))


@dataclass
class Story:
    titles: list[frozenset[str]]                                     # слова всех заголовков истории
    best: Item
    score: float
    created: float                                                   # время первой публикации
    source_times: dict[str, float] = field(default_factory=dict)    # источник -> когда он её опубликовал
    sent_to: set[str] = field(default_factory=set)                   # в какие каналы уже отправлена

    @property
    def sources(self) -> set[str]:
        return set(self.source_times)

    def sources_within(self, minutes: float) -> int:
        """Сколько разных источников опубликовали историю за первые N минут."""
        return sum(1 for t in self.source_times.values() if t - self.created <= minutes * 60)


class Store:
    def __init__(self, path: str, window_hours: float, threshold: float):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS seen (uid TEXT PRIMARY KEY, source TEXT, ts REAL)")
        self.db.commit()
        self.window = window_hours * 3600
        self.threshold = threshold
        self.stories: list[Story] = []

    def known_sources(self) -> set[str]:
        return {row[0] for row in self.db.execute("SELECT DISTINCT source FROM seen")}

    def is_seen(self, item: Item) -> bool:
        return self.db.execute("SELECT 1 FROM seen WHERE uid = ?", (item.uid,)).fetchone() is not None

    def mark_seen(self, items: list[Item]) -> None:
        now = time.time()
        self.db.executemany(
            "INSERT OR IGNORE INTO seen (uid, source, ts) VALUES (?, ?, ?)",
            [(i.uid, i.source, now) for i in items],
        )
        self.db.commit()

    def cleanup(self, keep_days: int = 14) -> None:
        self.db.execute("DELETE FROM seen WHERE ts < ?", (time.time() - keep_days * 86400,))
        self.db.commit()
        cutoff = time.time() - self.window
        self.stories = [s for s in self.stories if s.created >= cutoff]

    def add_to_story(self, item: Item, score: Score) -> Story:
        """Находит похожую историю за окно времени или заводит новую."""
        toks = tokens(item.title)
        published = item.published.timestamp()
        cutoff = published - self.window
        best_match, best_sim = None, 0.0
        for story in self.stories:
            if story.created < cutoff:
                continue
            sim = max(similarity(toks, t) for t in story.titles)
            if sim > best_sim:
                best_match, best_sim = story, sim
        if best_match and best_sim >= self.threshold:
            story = best_match
            if score.value > story.score:
                story.score, story.best = score.value, item
            story.created = min(story.created, published)
            if len(story.titles) < 30:
                story.titles.append(toks)
        else:
            story = Story(titles=[toks], best=item, score=score.value, created=published)
            self.stories.append(story)
        story.source_times[item.source] = min(story.source_times.get(item.source, published), published)
        return story
