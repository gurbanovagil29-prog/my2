"""Отправка уведомлений: в Telegram-бота или в консоль."""
import html
import logging
import time
from datetime import timedelta, timezone

import requests

from .models import Item

log = logging.getLogger(__name__)
MSK = timezone(timedelta(hours=3))


def format_message(item: Item, mark: str, category_label: str, reason: str,
                   score: float, hits: list[str], title: str | None = None) -> str:
    """title — заголовок для показа (например, переведённый); по умолчанию — оригинальный."""
    when = item.published.astimezone(MSK).strftime("%d.%m %H:%M")
    meta = [category_label, html.escape(item.source), when]
    if reason:
        meta.append(reason)
    words = ", ".join(dict.fromkeys(hits))  # без повторов, в исходном порядке
    text = f"{mark} <b>{html.escape(title or item.title)}</b>\n<i>{' · '.join(meta)}</i>"
    text += f"\n⭐ {score:g}" + (f" · {html.escape(words)}" if words else "")
    if item.link:
        text += f"\n{html.escape(item.link)}"
    return text


class ConsoleNotifier:
    def __init__(self):
        self.counts: dict[str, int] = {}

    def send(self, route, text: str) -> None:
        self.counts[route.name] = self.counts.get(route.name, 0) + 1
        print(f"[{route.name}]")
        print(text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", ""))
        print("-" * 60, flush=True)


class TelegramNotifier:
    # Telegram пускает в группу не больше ~20 сообщений в минуту.
    MIN_INTERVAL = 3.0

    def __init__(self, token: str):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.session = requests.Session()
        self.last_sent: dict[str, float] = {}

    def send(self, route, text: str) -> None:
        wait = self.last_sent.get(route.chat, 0) + self.MIN_INTERVAL - time.time()
        if wait > 0:
            time.sleep(wait)
        self.last_sent[route.chat] = time.time()
        payload = {
            "chat_id": route.chat,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        for _ in range(3):
            try:
                resp = self.session.post(self.url, data=payload, timeout=15)
            except requests.RequestException as e:
                log.warning("Telegram: %s", e)
                time.sleep(2)
                continue
            if resp.status_code == 429:  # слишком часто — Telegram говорит, сколько ждать
                time.sleep(resp.json().get("parameters", {}).get("retry_after", 5))
                continue
            if not resp.ok:
                log.error("Telegram %s: %s", resp.status_code, resp.text)
            return
