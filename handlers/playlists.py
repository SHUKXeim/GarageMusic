# handlers/playlists.py
from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db_instance import db
from keyboards import main_menu

router = Router()

@router.callback_query(lambda c: c.data == "my_catalog")
async def my_catalog(callback: CallbackQuery):
    user_id = callback.from_user.id
    tracks = db.get_user_tracks(user_id)
    if not tracks:
        return await callback.message.edit_text("📭 В твоём каталоге пока нет треков.", reply_markup=main_menu())

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{t[4] or 'NoName'} — {t[3] or 'NoArtist'}", callback_data=f"play_{t[0]}")] for t in tracks
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    await callback.message.edit_text("🎧 Твои треки:", reply_markup=kb)

