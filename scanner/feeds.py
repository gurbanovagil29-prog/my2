"""Загрузка RSS/Atom-лент с условными запросами (ETag/Last-Modified), чтобы не качать одно и то же."""
import calendar
import hashlib
import html
import logging
import re
from datetime import datetime, timezone

import feedparser
import requests

from .models import Item

log = logging.getLogger(__name__)

_TAG = re.compile(r"<[^>]+>")
_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
USER_AGENT = "Mozilla/5.0 (compatible; news-scanner/1.0)"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", text or ""))).strip()


class FeedFetcher:
    def __init__(self, source: dict):
        self.source = source
        self.etag: str | None = None
        self.modified: str | None = None
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    def fetch(self) -> list[Item]:
        headers = {}
        if self.etag:
            headers["If-None-Match"] = self.etag
        if self.modified:
            headers["If-Modified-Since"] = self.modified
        try:
            resp = self.session.get(self.source["url"], headers=headers, timeout=15)
        except requests.RequestException as e:
            log.warning("%s: %s", self.source["name"], e)
            return []
        if resp.status_code == 304:
            return []
        if resp.status_code != 200:
            log.warning("%s: HTTP %s", self.source["name"], resp.status_code)
            return []
        self.etag = resp.headers.get("ETag")
        self.modified = resp.headers.get("Last-Modified")

        feed = feedparser.parse(resp.content)
        return [self._to_item(e) for e in feed.entries if e.get("title")]

    def _to_item(self, entry) -> Item:
        src = self.source
        link = entry.get("link", "")
        raw_id = entry.get("id") or link or entry.get("title", "")
        uid = src["name"] + ":" + hashlib.sha1(raw_id.encode()).hexdigest()
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        published = (
            datetime.fromtimestamp(calendar.timegm(parsed), timezone.utc) if parsed else datetime.now(timezone.utc)
        )
        return Item(
            uid=uid,
            source=src["name"],
            category=src.get("category", "world"),
            title=clean(entry.get("title", "")),
            summary=clean(entry.get("summary", ""))[:1000],
            link=link,
            published=published,
            source_weight=src.get("weight", 0),
        )


class TelegramWebFetcher:
    """Публичный Telegram-канал через его веб-версию t.me/s/<канал>: последние ~20 постов, без входа в аккаунт."""

    _POST = re.compile(r'data-post="([^"/]+)/(\d+)"')
    _TEXT = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.DOTALL)
    _TIME = re.compile(r'<time datetime="([^"]+)"')

    def __init__(self, channel: str, category: str, weight: float, outlet: str = ""):
        self.channel = channel.lstrip("@")
        self.source = {"name": f"@{self.channel}", "category": category, "weight": weight, "outlet": outlet}
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    def fetch(self) -> list[Item]:
        try:
            resp = self.session.get(f"https://t.me/s/{self.channel}", timeout=15)
        except requests.RequestException as e:
            log.warning("@%s: %s", self.channel, e)
            return []
        if resp.status_code != 200:
            log.warning("@%s: HTTP %s", self.channel, resp.status_code)
            return []
        return self.parse(resp.text)

    @staticmethod
    def _headline(line: str) -> str:
        """Строка без хэштегов, @упоминаний и эмодзи в начале; пусто, если в ней нет текста."""
        line = re.split(r"\W*\b(?:Подписаться|Подпишись|Мы в)\b", line)[0]  # хвосты вида «🔹 Подписаться / Мы в Максе»
        line = re.sub(r"[#@]\w+", "", line)
        line = re.sub(r"^\W+", "", line).strip()
        if len(re.findall(r"[^\W\d_]{2,}", line)) < 2:  # меньше двух слов — это не заголовок
            return ""
        # Длинный первый абзац (как у ТАСС) обрезаем по первому предложению.
        if len(line) > 200 and (cut := line.find(". ", 60, 250)) != -1:
            line = line[: cut + 1]
        return line

    def parse(self, page: str) -> list[Item]:
        items = []
        posts = list(self._POST.finditer(page))
        for n, m in enumerate(posts):
            block = page[m.end(): posts[n + 1].start() if n + 1 < len(posts) else len(page)]
            text_m, time_m = self._TEXT.search(block), self._TIME.search(block)
            if not text_m or not time_m:
                continue  # пост без текста (только фото/видео)
            lines = [clean(line) for line in _BR.split(text_m.group(1))]
            lines = [line for line in lines if line]
            title = next((t for t in map(self._headline, lines) if t), "")
            if not title or " pinned «" in lines[0]:  # служебное «закрепил сообщение» — не новость
                continue
            rest = " ".join(lines)  # весь текст, вместе с хэштегами — по ним тоже считаются баллы
            username, post_id = m.group(1), m.group(2)
            items.append(Item(
                uid=f"tg:{username}:{post_id}",
                source=self.source["name"],
                category=self.source["category"],
                title=title[:300],
                summary=rest[:1000],
                link=f"https://t.me/{username}/{post_id}",
                published=datetime.fromisoformat(time_m.group(1)),
                source_weight=self.source["weight"],
                outlet=self.source["outlet"],
            ))
        return items
