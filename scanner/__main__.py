"""Сканер новостей.

  python -m scanner              # работать постоянно, слать в Telegram (или в консоль, если нет BOT_TOKEN)
  python -m scanner --dry-run    # то же, но только в консоль
  python -m scanner --once -v    # один проход по свежим новостям с баллами — для настройки config.yaml
  python -m scanner --once --hours 6   # сколько новостей ушло бы в каждый канал за последние 6 часов
  python -m scanner --now        # один проход: прислать в Telegram всё новое с прошлого запуска и выйти
"""
import argparse
import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from .feeds import FeedFetcher, TelegramWebFetcher
from .importance import importance
from .models import Item
from .notify import ConsoleNotifier, TelegramNotifier, format_message
from .routes import Route
from .scoring import Scorer
from .store import Store
from .translate import Translator

log = logging.getLogger("scanner")


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip())


class Scanner:
    def __init__(self, cfg: dict, notifier, once: bool = False, verbose: bool = False, hours: float | None = None,
                 single_pass: bool = False):
        self.cfg = cfg
        self.notifier = notifier
        self.once = once
        self.single_pass = once or single_pass
        self.verbose = verbose
        self.scorer = Scorer(cfg)
        story_cfg = cfg["story"]
        db_path = os.getenv("SCANNER_DB") or cfg.get("db_path", "scanner.db")
        self.store = Store(":memory:" if once else db_path,
                           story_cfg["window_hours"], story_cfg["similarity"])
        self.fetchers = [FeedFetcher(s) for s in cfg["sources"]] + [
            TelegramWebFetcher(c["name"], c.get("category", "russia"), c.get("weight", 0), c.get("outlet", ""))
            for c in cfg.get("telegram_channels", [])
        ]
        self.translate = Translator() if cfg.get("translate", True) else None
        self.sent_before = sum(len(s.sent_to) for s in self.store.stories)
        self.routes = [Route.from_config(key, c) for key, c in cfg["channels"].items()]
        self.max_age = timedelta(hours=hours) if hours else timedelta(minutes=cfg.get("max_age_minutes", 120))

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
        label = self.cfg["categories"].get(story.best.category, story.best.category)
        for route in self.routes:
            if route.key in story.sent_to:
                continue
            # Время "сейчас" берём из новости, чтобы --once на старых новостях вёл себя как вживую.
            reason = route.reason(story, now=item.published.timestamp(), scale=self.cfg["importance"])
            if reason is None:
                continue
            self.store.mark_sent(story, route.key)
            title = await asyncio.to_thread(self.translate, story.best.title) if self.translate else None
            text = format_message(story.best, route.mark, label, reason, importance(story, self.cfg["importance"]), story.hits, title)
            await asyncio.to_thread(self.notifier.send, route, text)

    async def poll_feeds(self) -> None:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=12) as pool:
            while True:
                results = await asyncio.gather(*(loop.run_in_executor(pool, f.fetch) for f in self.fetchers))
                fresh: list[Item] = []
                for items in results:
                    fresh.extend(items)
                # Обрабатываем все источники вместе по хронологии, чтобы видеть, кто опубликовал первым.
                for item in sorted(fresh, key=lambda i: i.published):
                    await self.process(item)
                self.store.commit()
                if self.single_pass:
                    return
                self.store.cleanup()
                await asyncio.sleep(self.cfg.get("poll_interval", 30))

    async def run(self) -> None:
        await self.poll_feeds()


def main() -> None:
    parser = argparse.ArgumentParser(description="Сканер важных новостей")
    parser.add_argument("-c", "--config", default="config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="печатать в консоль вместо Telegram")
    parser.add_argument("--once", action="store_true", help="один проход по свежим новостям, без базы")
    parser.add_argument("-v", "--verbose", action="store_true", help="показывать баллы всех новостей")
    parser.add_argument("--now", action="store_true", help="один проход с отправкой в Telegram и выход")
    parser.add_argument("--hours", type=float, help="с --once: за сколько часов брать новости")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    load_env(Path(".env"))
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    token = os.getenv("BOT_TOKEN")
    if args.dry_run or args.once or not token:
        if not (args.dry_run or args.once):
            log.warning("BOT_TOKEN не задан — вывожу новости в консоль")
        notifier = ConsoleNotifier()
    else:
        notifier = TelegramNotifier(token)

    try:
        scanner = Scanner(cfg, notifier, once=args.once, verbose=args.verbose, hours=args.hours, single_pass=args.now)
        asyncio.run(scanner.run())
    except KeyboardInterrupt:
        pass
    if args.now:
        sent = sum(len(s.sent_to) for s in scanner.store.stories)
        print(f"Готово. Новых сообщений отправлено: {sent - scanner.sent_before}")
    if args.once:
        hours = args.hours or cfg.get("max_age_minutes", 120) / 60
        for name, count in notifier.counts.items():
            print(f"{name}: {count} за {hours:g} ч (~{count / hours:.1f} в час)")


if __name__ == "__main__":
    main()
