# handlers/start.py
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from keyboards import main_menu
from db_instance import db
from config import STORAGE_CHAT_ID


router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    db.add_user(message.from_user.id, message.from_user.full_name or message.from_user.first_name)
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\nДобро пожаловать в GarageLib.\n\n📦 Версия бота: *{db.get_user(message.from_user.id) and 'v1.1' or 'v1.1'}*",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "about_bot")
async def about_bot(callback: CallbackQuery):
    text = (
        "🤖 GarageLib Bot v1.1\n\n"
        "Бот для артистов: загружай демо, управляй личным каталогом и делись треками в общем плейлисте.\n\n"
        "Функции:\n• Личный каталог\n• Общий плейлист с карточками артистов\n• Уведомления при добавлении трека в общий плейлист\n"
    )
    try:
        await callback.message.edit_text(text, reply_markup=main_menu())
    except Exception:
        await callback.message.answer(text, reply_markup=main_menu())

@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    try:
        await callback.message.edit_text("🏠 Главное меню:", reply_markup=main_menu())
    except Exception:
        await callback.message.answer("🏠 Главное меню:", reply_markup=main_menu())

@router.callback_query(F.data.startswith("play_"))
async def play_track(callback: CallbackQuery):
    try:
        tid = int(callback.data.split("_", 1)[1])
    except Exception:
        await callback.answer("Неверный трек.", show_alert=True)
        return

    track = db.get_track(tid)
    if not track:
        await callback.answer("⚠️ Трек не найден.", show_alert=True)
        return

    title = track[3] or "Без названия"
    performer = track[4] or "Неизвестен"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎧 Послушать", callback_data=f"listen_{tid}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{tid}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])

    text = f"🎵 {performer} — {title}"
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("listen_"))
async def listen_track(callback: CallbackQuery):
    try:
        tid = int(callback.data.split("_", 1)[1])
    except Exception:
        await callback.answer("Неверный трек.", show_alert=True)
        return

    track = db.get_track(tid)
    if not track:
        await callback.answer("⚠️ Трек не найден.", show_alert=True)
        return

    file_id = track[5]  # file_id в БД
    title = track[3] or "Без названия"
    performer = track[4] or "Неизвестен"
    try:
        await callback.message.answer_audio(audio=file_id, caption=f"{performer} — {title}")
    except Exception:
        await callback.answer("Не удалось отправить трек.", show_alert=True)


@router.callback_query(F.data.startswith("delete_"))
async def delete_track(callback: CallbackQuery, bot: Bot):
    try:
        tid = int(callback.data.split("_", 1)[1])
    except Exception:
        await callback.answer("Неверный трек.", show_alert=True)
        return

    track = db.get_track(tid)
    if not track:
        await callback.answer("⚠️ Трек не найден.", show_alert=True)
        return

    owner_id = track[1]  # user_id владельца
    if callback.from_user.id != owner_id:
        await callback.answer("🚫 Ты не можешь удалить чужой трек.", show_alert=True)
        return

    # Попытаться удалить из канала-хранилища (если есть message_id)
    storage_msg_id = track[6]  # storage_message_id
    if storage_msg_id:
        try:
            await bot.delete_message(chat_id=STORAGE_CHAT_ID, message_id=storage_msg_id)
        except Exception:
            pass

    # Удаляем запись из БД
    db.delete_track(tid)

    try:
        await callback.message.edit_text("🗑 Трек удалён.", reply_markup=main_menu())
    except Exception:
        await callback.message.answer("🗑 Трек удалён.", reply_markup=main_menu())
