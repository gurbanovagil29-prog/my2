"""Сканер новостей.

  python -m scanner              # работать постоянно, слать в Telegram (или в консоль, если нет BOT_TOKEN)
  python -m scanner --dry-run    # то же, но только в консоль
  python -m scanner --once -v    # один проход по свежим новостям с баллами — для настройки config.yaml
"""
import argparse
import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from .feeds import FeedFetcher
from .models import Item
from .notify import ConsoleNotifier, TelegramNotifier, format_message
from .scoring import Scorer
from .store import Store

log = logging.getLogger("scanner")


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip())


class Scanner:
    def __init__(self, cfg: dict, notifier, once: bool = False, verbose: bool = False):
        self.cfg = cfg
        self.notifier = notifier
        self.once = once
        self.verbose = verbose
        self.scorer = Scorer(cfg)
        corr = cfg["corroboration"]
        self.store = Store(":memory:" if once else cfg.get("db_path", "scanner.db"),
                           corr["window_hours"], corr["similarity"])
        self.fetchers = [FeedFetcher(s) for s in cfg["sources"]]
        self.max_age = timedelta(minutes=cfg.get("max_age_minutes", 120))
        self.send_at = cfg["thresholds"]["send"]
        self.urgent_at = cfg["thresholds"]["urgent"]
        self.corr_sources = corr["min_sources"]
        self.corr_score = corr["min_score"]

    async def process(self, item: Item) -> None:
        if self.store.is_seen(item):
            return
        self.store.mark_seen([item])
        if datetime.now(timezone.utc) - item.published > self.max_age:
            return
        score = self.scorer.score(item)
        if score is None:
            return
        story = self.store.add_to_story(item, score)
        if self.verbose and score.value > 0:
            log.info("[%4.1f] %s: %s  %s", score.value, item.source, item.title, score.hits)
        if story.sent:
            return
        corroborated = len(story.sources) >= self.corr_sources and story.score >= self.corr_score
        if story.score >= self.send_at or corroborated:
            story.sent = True
            label = self.cfg["categories"].get(story.best.category, story.best.category)
            text = format_message(story.best, story.score, story.sources, label, story.score >= self.urgent_at)
            await asyncio.to_thread(self.notifier.send, text)

    async def poll_feeds(self) -> None:
        loop = asyncio.get_running_loop()
        known = self.store.known_sources()
        with ThreadPoolExecutor(max_workers=12) as pool:
            while True:
                results = await asyncio.gather(*(loop.run_in_executor(pool, f.fetch) for f in self.fetchers))
                for fetcher, items in zip(self.fetchers, results):
                    name = fetcher.source["name"]
                    # Новый источник: всё, что в ленте уже есть, запоминаем без отправки,
                    # иначе при первом запуске прилетит сотня старых новостей.
                    if not self.once and name not in known:
                        if items:  # источник мог не ответить — тогда запомним на следующем круге
                            self.store.mark_seen(items)
                            known.add(name)
                            log.info("%s: запомнил %d текущих новостей", name, len(items))
                        continue
                    # Ленты отдают новые сверху; обрабатываем по хронологии.
                    for item in reversed(items):
                        await self.process(item)
                if self.once:
                    return
                self.store.cleanup()
                await asyncio.sleep(self.cfg.get("poll_interval", 30))

    async def run(self) -> None:
        tasks = [self.poll_feeds()]
        api_id, api_hash = os.getenv("TG_API_ID"), os.getenv("TG_API_HASH")
        if api_id and api_hash and not self.once and self.cfg.get("telegram_channels"):
            from .telegram_channels import listen
            tasks.append(listen(int(api_id), api_hash, self.cfg["telegram_channels"], self.process))
        await asyncio.gather(*tasks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Сканер важных новостей")
    parser.add_argument("-c", "--config", default="config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="печатать в консоль вместо Telegram")
    parser.add_argument("--once", action="store_true", help="один проход по свежим новостям, без базы")
    parser.add_argument("-v", "--verbose", action="store_true", help="показывать баллы всех новостей")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    load_env(Path(".env"))
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    token, chat_id = os.getenv("BOT_TOKEN"), os.getenv("CHAT_ID")
    if args.dry_run or args.once or not (token and chat_id):
        if not (args.dry_run or args.once):
            log.warning("BOT_TOKEN/CHAT_ID не заданы — вывожу новости в консоль")
        notifier = ConsoleNotifier()
    else:
        notifier = TelegramNotifier(token, chat_id)

    try:
        asyncio.run(Scanner(cfg, notifier, once=args.once, verbose=args.verbose).run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
