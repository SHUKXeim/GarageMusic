# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎧 Мой каталог", callback_data="my_catalog")],
        [InlineKeyboardButton(text="🌍 Общий плейлист", callback_data="common_playlist")],
        [InlineKeyboardButton(text="🎤 Мои карточки артиста", callback_data="my_artist")],
        [InlineKeyboardButton(text="➕ Добавить трек", callback_data="add_track")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about_bot")]
    ])

def track_save_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Личный каталог", callback_data="save_personal")],
        [InlineKeyboardButton(text="🌍 Общий плейлист", callback_data="save_common")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_upload")]
    ])
