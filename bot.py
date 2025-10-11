# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers import start, upload, playlists, artist, metadata
from db_instance import db
from config import BOT_VERSION

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(metadata.router)
    dp.include_router(start.router)
    dp.include_router(upload.router)
    dp.include_router(playlists.router)
    dp.include_router(artist.router)

    # --- Проверяем обновление версии ---
    prev_version = db.get_bot_version()
    if prev_version != BOT_VERSION:
        db.set_bot_version(BOT_VERSION)
        users = db.get_all_users()
        message = (
            f"⚙️ GarageLib обновился до версии *{BOT_VERSION}*!\n\n"
            "🆕 Новое в этом обновлении:\n"
            "• Улучшенный редактор метаданных\n"
            "• Возможность публикации треков из личного каталога в общий\n"
            "• Мелкие исправления и улучшения стабильности"
        )
        for uid in users:
            try:
                await bot.send_message(uid, message, parse_mode="Markdown")
                await asyncio.sleep(0.05)
            except Exception:
                pass
        print(f"📢 Рассылка обновления {BOT_VERSION} завершена.")

    print("🚀 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
