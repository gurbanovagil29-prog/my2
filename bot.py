"""Telegram-бот для пересылки сообщений из чатов-источников в чаты-получатели."""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("forwarder")


def parse_ids(value: str | None) -> set[int]:
    if not value:
        return set()
    return {int(part) for part in value.replace(" ", "").split(",") if part}


BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHAT_IDS = parse_ids(os.getenv("SOURCE_CHAT_IDS"))
TARGET_CHAT_IDS = parse_ids(os.getenv("TARGET_CHAT_IDS"))
# forward — пересылка с подписью «Переслано от…», copy — копия без автора
MODE = os.getenv("MODE", "forward").lower()

router = Router()


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    """Подсказывает ID текущего чата — нужен для настройки .env."""
    await message.answer(f"ID этого чата: <code>{message.chat.id}</code>")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Я пересылаю сообщения из чатов-источников в чаты-получатели.\n"
        "Команда /id покажет ID текущего чата."
    )


async def relay(message: Message, bot: Bot) -> None:
    if SOURCE_CHAT_IDS and message.chat.id not in SOURCE_CHAT_IDS:
        return

    for target in TARGET_CHAT_IDS:
        if target == message.chat.id:
            continue  # не пересылаем сообщение в тот же чат
        try:
            if MODE == "copy":
                await bot.copy_message(target, message.chat.id, message.message_id)
            else:
                await bot.forward_message(target, message.chat.id, message.message_id)
        except Exception:
            log.exception("Не удалось переслать сообщение %s в %s", message.message_id, target)


# Обычные сообщения (личка, группы) и посты в каналах
router.message.register(relay, ~F.text.startswith("/"))
router.channel_post.register(relay)


async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("Не задан BOT_TOKEN (см. .env.example)")
    if not TARGET_CHAT_IDS:
        raise SystemExit("Не задан TARGET_CHAT_IDS (см. .env.example)")
    if MODE not in ("forward", "copy"):
        raise SystemExit("MODE должен быть forward или copy")

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(router)

    log.info(
        "Старт: источники=%s, получатели=%s, режим=%s",
        SOURCE_CHAT_IDS or "все чаты",
        TARGET_CHAT_IDS,
        MODE,
    )
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
