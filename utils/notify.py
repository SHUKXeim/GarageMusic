# utils/notify.py
import asyncio
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError, TelegramRetryAfter

async def broadcast(bot, user_ids: list[int], message: str, parse_mode: str = None, delay: float = 0.05):
    """
    Рассылает сообщение всем пользователям.
    Возвращает список ID пользователей, которым не удалось отправить сообщение.
    """
    failed = []

    for uid in user_ids:
        try:
            await bot.send_message(uid, message, parse_mode=parse_mode)
            await asyncio.sleep(delay)
        except (TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError, TelegramRetryAfter):
            failed.append(uid)
        except Exception:
            failed.append(uid)

    return failed
