from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from keyboards import track_save_menu, main_menu
from config import STORAGE_CHAT_ID
from db_instance import db
import asyncio

router = Router()


class UploadForm(StatesGroup):
    waiting_for_audio = State()
    waiting_for_meta_edit = State()


async def safe_edit_or_answer(message_obj, text, reply_markup=None, parse_mode=None):
    """Безопасное редактирование или ответ (чтобы не падал при одинаковом тексте)."""
    try:
        await message_obj.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        try:
            await message_obj.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            pass


# === Шаг 1. Пользователь нажал “Добавить трек” ===
@router.callback_query(F.data == "add_track")
async def add_track_menu(callback: CallbackQuery, state: FSMContext):
    db.add_user(callback.from_user.id, callback.from_user.full_name or callback.from_user.first_name)
    await callback.message.answer("🎵 Отправь мне аудиофайл (mp3/ogg), чтобы добавить его.")
    await state.clear()
    await state.set_state(UploadForm.waiting_for_audio)


# === Шаг 2. Пользователь отправил аудиофайл ===
@router.message(F.audio)
async def on_audio(message: Message, state: FSMContext):
    audio = message.audio
    user_id = message.from_user.id

    db.add_user(user_id, message.from_user.full_name or message.from_user.first_name)

    title = audio.title or "Без названия"
    performer = audio.performer or (message.from_user.full_name or message.from_user.first_name)

    await state.update_data(file_id=audio.file_id, title=title, performer=performer)
    await message.answer(
        f"📀 Трек: *{title}*\nИсполнитель: *{performer}*\n\nКуда сохранить?",
        reply_markup=track_save_menu(),
        parse_mode="Markdown"
    )
    await state.set_state(UploadForm.waiting_for_meta_edit)


# === Отмена ===
@router.callback_query(F.data == "cancel_upload")
async def cancel_upload(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_or_answer(callback.message, "❌ Отменено. Возвращаю в главное меню.", reply_markup=main_menu())


# === Шаг 3. Сохранение трека ===
@router.callback_query(F.data.in_(["save_personal", "save_common"]))
async def save_track(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    file_id = data.get("file_id")
    title = data.get("title") or "Без названия"
    performer = data.get("performer") or (callback.from_user.full_name or callback.from_user.first_name)
    user_id = callback.from_user.id

    if not file_id:
        await safe_edit_or_answer(callback.message, "⚠️ Ошибка: файл не найден в сессии.", reply_markup=main_menu())
        await state.clear()
        return

    # === Сохранение в личный каталог ===
    if callback.data == "save_personal":
        storage_msg_id = None
        saved_file_id = file_id
        try:
            sent = await bot.send_audio(chat_id=STORAGE_CHAT_ID, audio=file_id, caption=f"{performer} — {title}")
            if hasattr(sent, "audio") and getattr(sent.audio, "file_id", None):
                saved_file_id = sent.audio.file_id
            storage_msg_id = sent.message_id
        except Exception as e:
            print(f"[storage send error personal] {e}")

        db.add_user_track(user_id=user_id, file_id=saved_file_id, title=title, performer=performer,
                          artist_id=None, storage_message_id=storage_msg_id)

        await safe_edit_or_answer(callback.message, f"✅ Трек «{title}» сохранён в личном каталоге.", reply_markup=main_menu())
        await state.clear()
        return

    # === Сохранение в общий плейлист ===
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
            [InlineKeyboardButton(text=a[1], callback_data=f"choose_artist_{a[0]}")] for a in user_artists
        ])
        kb.inline_keyboard.append([InlineKeyboardButton(text="➕ Создать новую", callback_data="create_artist_card")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_upload")])
        await callback.message.answer("У тебя несколько карточек. Выбери, под какой опубликовать трек:", reply_markup=kb)
        await state.update_data(pending_save="save_common")
        return

    storage_msg_id = None
    saved_file_id = file_id
    try:
        sent = await bot.send_audio(chat_id=STORAGE_CHAT_ID, audio=file_id, caption=f"{chosen_artist_name} — {title}")
        if hasattr(sent, "audio") and getattr(sent.audio, "file_id", None):
            saved_file_id = sent.audio.file_id
        storage_msg_id = sent.message_id
    except Exception as e:
        print(f"[storage send error common] {e}")

    db.add_common_track(user_id=user_id, file_id=saved_file_id, title=title, performer=chosen_artist_name,
                        artist_id=chosen_artist_id, storage_message_id=storage_msg_id)

    # Рассылка уведомлений
    users = db.get_all_users()
    note = f"🎵 {chosen_artist_name} выложил новый трек: «{title}»"
    for uid in users:
        if uid == user_id:
            continue
        try:
            await bot.send_message(uid, note)
            await asyncio.sleep(0.03)
        except Exception:
            pass

    await safe_edit_or_answer(callback.message, f"🌍 Трек «{title}» добавлен в общий плейлист от «{chosen_artist_name}».",
                              reply_markup=main_menu())
    await state.clear()


# === Выбор артиста (если у пользователя несколько карточек) ===
@router.callback_query(F.data.startswith("choose_artist_"))
async def choose_artist(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        artist_id = int(callback.data.split("_", 2)[2])
    except Exception:
        await callback.answer("Неверный выбор.", show_alert=True)
        return

    data = await state.get_data()
    pending = data.get("pending_save")
    if pending != "save_common":
        await callback.answer("Нет ожидаемой операции.", show_alert=True)
        return

    file_id = data.get("file_id")
    title = data.get("title") or "Без названия"
    user_id = callback.from_user.id

    artist = db.get_artist(artist_id)
    if not artist:
        await callback.answer("Карточка не найдена.", show_alert=True)
        await state.clear()
        return

    artist_name = artist[2]
    storage_msg_id = None
    saved_file_id = file_id
    try:
        sent = await bot.send_audio(chat_id=STORAGE_CHAT_ID, audio=file_id, caption=f"{artist_name} — {title}")
        if hasattr(sent, "audio") and getattr(sent.audio, "file_id", None):
            saved_file_id = sent.audio.file_id
        storage_msg_id = sent.message_id
    except Exception as e:
        print(f"[storage send error choose_artist] {e}")

    db.add_common_track(user_id=user_id, file_id=saved_file_id, title=title, performer=artist_name,
                        artist_id=artist_id, storage_message_id=storage_msg_id)

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

    await callback.message.answer(f"🌍 Трек «{title}» добавлен в общий плейлист от «{artist_name}».", reply_markup=main_menu())
    await state.clear()
