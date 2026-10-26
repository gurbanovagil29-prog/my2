"""Отправка уведомлений: в Telegram-бота или в консоль."""
import html
import logging
import time

import requests

from .models import Item

log = logging.getLogger(__name__)


def format_message(item: Item, mark: str, category_label: str, reason: str) -> str:
    meta = [category_label, html.escape(item.source)]
    if reason:
        meta.append(reason)
    text = f"{mark} <b>{html.escape(item.title)}</b>\n<i>{' · '.join(meta)}</i>"
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
    def __init__(self, token: str):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.session = requests.Session()

    def send(self, route, text: str) -> None:
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
