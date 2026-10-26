"""Отправка уведомлений: в Telegram-бота или в консоль."""
import html
import logging
import time

import requests

from .models import Item

log = logging.getLogger(__name__)


def format_message(item: Item, score: float, sources: set[str], category_label: str, urgent: bool) -> str:
    mark = "🔴" if urgent else "🟡"
    meta = [category_label, html.escape(item.source)]
    if len(sources) > 1:
        meta.append(f"🔁 {len(sources)} источника(ов)")
    text = f"{mark} <b>{html.escape(item.title)}</b>\n<i>{' · '.join(meta)}</i>"
    if item.link:
        text += f"\n{html.escape(item.link)}"
    return text


class ConsoleNotifier:
    def send(self, text: str) -> None:
        print(text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", ""))
        print("-" * 60, flush=True)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
        self.session = requests.Session()

    def send(self, text: str) -> None:
        payload = {
            "chat_id": self.chat_id,
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
