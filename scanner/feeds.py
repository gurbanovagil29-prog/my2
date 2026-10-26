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
