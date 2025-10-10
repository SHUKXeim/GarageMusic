# handlers/artist.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from db_instance import db
from keyboards import main_menu

router = Router()

class ArtistForm(StatesGroup):
    waiting_for_name = State()

@router.callback_query(lambda c: c.data == "common_playlist")
async def common_playlist(callback: CallbackQuery):
    artists = db.get_all_artists()
    if not artists:
        return await callback.message.edit_text("🌍 В общем плейлисте пока нет артистов.", reply_markup=main_menu())

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a[2], callback_data=f"artist_{a[0]}")] for a in artists
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    await callback.message.edit_text("🎤 Артисты:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data.startswith("artist_"))
async def view_artist(callback: CallbackQuery):
    try:
        artist_id = int(callback.data.split("_", 1)[1])
    except Exception:
        await callback.answer("Неверный артист.", show_alert=True)
        return
    artist = db.get_artist(artist_id)
    if not artist:
        return await callback.message.answer("⚠️ Артист не найден.")

    tracks = db.cur.execute("SELECT id, title, performer FROM tracks WHERE artist_id = ? AND is_common = 1 ORDER BY created_at DESC", (artist[0],)).fetchall()
    text = f"🎤 *{artist[2]}*\n\n🎵 Треки:"
    if not tracks:
        text += "\n(У артиста пока нет треков в общем плейлисте)"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{t[2]} — {t[1]}", callback_data=f"play_{t[0]}")] for t in tracks
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="common_playlist")])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "my_artist")
async def my_artist(callback: CallbackQuery):
    user_id = callback.from_user.id
    artists = db.get_user_artists(user_id)
    if not artists:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆕 Создать карточку", callback_data="create_artist_card")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
        ])
        return await callback.message.edit_text("🎤 У тебя ещё нет карточек артиста.", reply_markup=kb)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a[1], callback_data=f"artist_{a[0]}")] for a in artists
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ Создать новую", callback_data="create_artist_card")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    await callback.message.edit_text("🎤 Твои карточки артистов:", reply_markup=kb)

@router.callback_query(lambda c: c.data == "create_artist_card")
async def start_artist_creation(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите имя нового артиста:")
    await state.set_state(ArtistForm.waiting_for_name)

@router.message(ArtistForm.waiting_for_name)
async def process_artist_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Имя не может быть пустым. Введи ещё раз:")
        return
    db.add_artist(message.from_user.id, name)
    await message.answer(f"✅ Карточка артиста '{name}' создана!", reply_markup=main_menu())
    await state.clear()
