import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, BOT_VERSION
from handlers import start, upload, playlists, artist, metadata
from utils.notify import broadcast
from db_instance import db

logging.basicConfig(level=logging.INFO)


async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(start.router)
    dp.include_router(upload.router)
    dp.include_router(playlists.router)
    dp.include_router(artist.router)
    dp.include_router(metadata.router)

    # 🚀 Проверяем, отправлялось ли уведомление об обновлении
    if not db.has_version_been_sent(BOT_VERSION):
        users = db.get_all_users()
        if users:
            message = (
                f"🔔 *GarageLib обновлён до {BOT_VERSION}!*\n\n"
                "🆕 Новые возможности:\n"
                "• Исправлены уведомления и рассылки\n"
                "• Повышена стабильность\n\n"
            )
            failed = await broadcast(bot, users, message, parse_mode="Markdown", delay=0.05)
            print(f"✅ Уведомление об обновлении {BOT_VERSION} разослано ({len(users) - len(failed)}/{len(users)} успешно).")

        db.mark_version_as_sent(BOT_VERSION)

    print("🚀 Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
