"""Чтение Telegram-каналов в реальном времени через Telethon (ваш пользовательский аккаунт)."""
import logging
from collections.abc import Awaitable, Callable

from .models import Item

log = logging.getLogger(__name__)


async def listen(api_id: int, api_hash: str, cfg: dict, on_item: Callable[[Item], Awaitable[None]]) -> None:
    from telethon import TelegramClient, events

    channels = cfg.get("channels", [])
    if not channels:
        return
    client = TelegramClient("scanner", api_id, api_hash)
    await client.start()  # при первом запуске спросит телефон и код из Telegram

    @client.on(events.NewMessage(chats=channels))
    async def handler(event):
        text = (event.message.message or "").strip()
        if not text:
            return
        chat = await event.get_chat()
        username = getattr(chat, "username", None) or str(event.chat_id)
        title, _, rest = text.partition("\n")
        await on_item(Item(
            uid=f"tg:{username}:{event.message.id}",
            source=f"@{username}",
            category=cfg.get("category", "russia"),
            title=title[:300],
            summary=rest[:1000],
            link=f"https://t.me/{username}/{event.message.id}",
            source_weight=cfg.get("weight", 0),
        ))

    log.info("Слушаю Telegram-каналы: %s", ", ".join(channels))
    await client.run_until_disconnected()
