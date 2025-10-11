# handlers/start.py
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from keyboards import main_menu
from db_instance import db
from config import STORAGE_CHAT_ID
import asyncio


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
        "🤖 GarageLib Bot v1.2\n\n"
        "Бот для артистов: загружай демо, управляй личным каталогом и делись треками в общем плейлисте.\n\n"
        "Функции:\n• Личный каталог\n• Общий плейлист с карточками артистов\n• Уведомления при добавлении трека в общий плейлист\n• Улучшенная версия изменения метаданных\n"
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
        [InlineKeyboardButton(text="🌍 Сделать общедоступным", callback_data=f"make_public_{tid}")],
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

@router.callback_query(F.data.startswith("make_public_"))
async def make_public(callback: CallbackQuery, bot: Bot):
    try:
        tid = int(callback.data.split("_", 2)[2])
    except Exception:
        await callback.answer("Неверный трек.", show_alert=True)
        return

    track = db.get_track(tid)
    if not track:
        await callback.answer("⚠️ Трек не найден.", show_alert=True)
        return

    user_id = callback.from_user.id
    file_id = track[5]
    title = track[3] or "Без названия"
    performer = track[4] or "Неизвестен"

    user_artists = db.get_user_artists(user_id)
    if not user_artists:
        artist_id, artist_name = db.get_or_create_first_artist(user_id, performer)
        chosen_artist_id = artist_id
        chosen_artist_name = artist_name
    elif len(user_artists) == 1:
        chosen_artist_id = user_artists[0][0]
        chosen_artist_name = user_artists[0][1]
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=a[1], callback_data=f"make_public_choose_{tid}_{a[0]}")] for a in user_artists
        ])
        kb.inline_keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")])
        await callback.message.answer("Выбери карточку артиста:", reply_markup=kb)
        return

    await publish_track(bot, callback, tid, file_id, title, chosen_artist_name, chosen_artist_id, user_id)

@router.callback_query(F.data.startswith("make_public_choose_"))
async def make_public_choose(callback: CallbackQuery, bot: Bot):
    try:
        _, _, tid, artist_id = callback.data.split("_")
        tid = int(tid)
        artist_id = int(artist_id)
    except Exception:
        await callback.answer("Ошибка выбора.", show_alert=True)
        return

    track = db.get_track(tid)
    if not track:
        await callback.answer("⚠️ Трек не найден.", show_alert=True)
        return

    artist = db.get_artist(artist_id)
    if not artist:
        await callback.answer("Карточка не найдена.", show_alert=True)
        return

    await publish_track(bot, callback, tid, track[5], track[3], artist[2], artist_id, callback.from_user.id)

async def publish_track(bot, callback, tid, file_id, title, artist_name, artist_id, user_id):
    from config import STORAGE_CHAT_ID

    # Отправляем в хранилище
    storage_msg_id = None
    try:
        sent = await bot.send_audio(chat_id=STORAGE_CHAT_ID, audio=file_id, caption=f"{artist_name} — {title}")
        if hasattr(sent, "audio") and getattr(sent.audio, "file_id", None):
            file_id = sent.audio.file_id
        storage_msg_id = sent.message_id
    except Exception as e:
        print(f"[make_public storage error] {e}")

    # Сохраняем в БД как общий трек
    db.add_common_track(user_id=user_id, file_id=file_id, title=title,
                        performer=artist_name, artist_id=artist_id, storage_message_id=storage_msg_id)

    # Рассылка уведомлений
    users = db.get_all_users()
    note = f"🎵 {artist_name} выложил новый трек: «{title}»"
    for uid in users:
        if uid == user_id:
            continue
        try:
            await bot.send_message(uid, note)
            await asyncio.sleep(0.03)
        except Exception:
            pass

    await callback.message.answer(f"✅ Трек «{title}» опубликован от имени {artist_name}!", reply_markup=main_menu())
