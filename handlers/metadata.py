# handlers/metadata.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from keyboards import main_menu
from db_instance import db

router = Router()

class MetadataForm(StatesGroup):
    waiting_for_title = State()
    waiting_for_performer_choice = State()

# === Начало редактирования метаданных ===
@router.callback_query(F.data == "edit_metadata")
async def start_metadata_edit(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🎵 Введи новое название трека:")
    await state.set_state(MetadataForm.waiting_for_title)


# === Пользователь вводит новое название ===
@router.message(MetadataForm.waiting_for_title)
async def set_new_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title:
        await message.answer("⚠️ Название не может быть пустым. Введи ещё раз:")
        return
    await state.update_data(title=title)

    user_id = message.from_user.id
    artists = db.get_user_artists(user_id)

    if not artists:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать карточку", callback_data="create_artist_card")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_metadata")]
        ])
        await message.answer("У тебя нет карточек артиста. Создай новую, чтобы указать исполнителя.", reply_markup=kb)
        await state.set_state(MetadataForm.waiting_for_performer_choice)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a[1], callback_data=f"meta_artist_{a[0]}")] for a in artists
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ Создать новую", callback_data="create_artist_card")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_metadata")])

    await message.answer("🎤 Выбери исполнителя (твою карточку артиста):", reply_markup=kb)
    await state.set_state(MetadataForm.waiting_for_performer_choice)


# === Обработка выбора карточки артиста ===
@router.callback_query(F.data.startswith("meta_artist_"))
async def set_metadata_artist(callback: CallbackQuery, state: FSMContext):
    try:
        artist_id = int(callback.data.split("_", 2)[2])
    except Exception:
        await callback.answer("Неверный выбор.", show_alert=True)
        return

    artist = db.get_artist(artist_id)
    if not artist:
        await callback.answer("Карточка не найдена.", show_alert=True)
        return

    await state.update_data(performer=artist[2])
    data = await state.get_data()
    title = data.get("title", "Без названия")
    performer = artist[2]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить", callback_data="confirm_metadata")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_metadata")]
    ])

    await callback.message.edit_text(
        f"📀 *Проверим:*\n🎵 Название: {title}\n👤 Исполнитель: {performer}",
        reply_markup=kb,
        parse_mode="Markdown"
    )


# === Подтверждение изменения метаданных ===
# === Подтверждение изменения метаданных ===
@router.callback_query(F.data == "confirm_metadata")
async def confirm_metadata(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    title = data.get("title", "Без названия")
    performer = data.get("performer", "Неизвестен")

    # Обновляем состояние, чтобы upload.py видел обновлённые данные
    await state.update_data(title=title, performer=performer)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Личный каталог", callback_data="save_personal")],
        [InlineKeyboardButton(text="🌍 Общий плейлист", callback_data="save_common")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_upload")]
    ])

    await callback.message.edit_text(
        f"✅ Метаданные обновлены!\n\n🎵 Название: {title}\n👤 Исполнитель: {performer}\n\nТеперь выбери, куда сохранить трек:",
        reply_markup=kb
    )

    # Не очищаем state, чтобы upload.py мог использовать данные


# === Отмена редактирования ===
@router.callback_query(F.data == "cancel_metadata")
async def cancel_metadata(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Редактирование отменено.", reply_markup=main_menu())
    await state.clear()
