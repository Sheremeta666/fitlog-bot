import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Router
from dotenv import load_dotenv

# Токен
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Бот
from aiogram.client.default import DefaultBotProperties
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# Программа тренировок
workouts = {
    "Понедельник — Грудь + Скакалка": ["Отжимания (4x20)", "Жим гантелей лёжа (4x12)", "Скакалка (5-10 мин)"],
    "Вторник — Спина + Пресс": ["Подтягивания (4x6-8)", "Тяга гантелей в наклоне (3x12)", "Планка (3x40 сек)"],
    "Среда — Восстановление": ["Скакалка (10 мин)", "Растяжка (10-15 мин)"],
    "Четверг — Ноги + Прыжки": ["Приседания с гантелями (4x15)", "Прыжки на возвышенность (3x10)"],
    "Пятница — Плечи + Пресс": ["Жим гантелей вверх (4x12)", "Скручивания + подъёмы ног (4x15)"],
    "Суббота — Кардио": ["Бег в горку (3 подхода по 20 сек)", "Скакалка (10 мин)"],
    "Воскресенье — Отдых и Растяжка": ["Растяжка (10-15 мин)", "Прогулка (20 мин)"]
}

user_progress = {}
last_bot_messages = {}
main_menu_messages = {}
reply_menu_messages = {}
text_reply_messages = {}

def days_keyboard():
    kb = InlineKeyboardBuilder()
    for day in workouts:
        kb.button(text=day, callback_data=f"day:{day}")
    kb.adjust(1)
    return kb.as_markup()

def workout_keyboard(user_id: int, day: str):
    kb = InlineKeyboardBuilder()
    user_progress.setdefault(user_id, {}).setdefault(day, [])
    for i, exercise in enumerate(workouts[day]):
        if i not in user_progress[user_id][day]:
            kb.button(text=f"✅ {exercise}", callback_data=f"do:{day}:{i}")
    kb.button(text="🔙 Назад", callback_data="back")
    kb.adjust(1)
    return kb.as_markup()

def main_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📅 Вернуться к расписанию")]],
        resize_keyboard=True,
        is_persistent=True
    )

async def clear_old(user_id, chat_id):
    if user_id in last_bot_messages:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=last_bot_messages[user_id])
        except:
            pass
    if user_id in reply_menu_messages:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=reply_menu_messages[user_id])
        except:
            pass
    if user_id in text_reply_messages:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=text_reply_messages[user_id])
        except:
            pass

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    await clear_old(user_id, chat_id)
    msg = await message.answer("Выбери день недели для тренировки:", reply_markup=days_keyboard())
    await message.answer(reply_markup=main_reply_keyboard())
    main_menu_messages[user_id] = msg.message_id
    last_bot_messages[user_id] = msg.message_id

@router.callback_query(lambda c: c.data.startswith("day:"))
async def handle_day(callback: types.CallbackQuery):
    day = callback.data.split(":")[1]
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    user_progress.setdefault(user_id, {})
    user_progress[user_id][day] = []
    await callback.message.delete()
    await clear_old(user_id, chat_id)
    msg = await callback.message.answer(
        f"<b>Тренировка на {day}:</b>\n\nНажимай на упражнения, которые выполнил 👇",
        reply_markup=workout_keyboard(user_id, day)
    )
    await callback.message.answer(reply_markup=main_reply_keyboard())
    last_bot_messages[user_id] = msg.message_id
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("do:"))
async def handle_done(callback: types.CallbackQuery):
    _, day, index = callback.data.split(":")
    index = int(index)
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    user_progress.setdefault(user_id, {}).setdefault(day, [])
    if index not in user_progress[user_id][day]:
        user_progress[user_id][day].append(index)
    await callback.message.delete()
    await clear_old(user_id, chat_id)
    msg = await callback.message.answer(
        f"<b>Тренировка на {day}:</b>\n\nНажимай на упражнения, которые выполнил 👇",
        reply_markup=workout_keyboard(user_id, day)
    )
    await callback.message.answer(reply_markup=main_reply_keyboard())
    last_bot_messages[user_id] = msg.message_id
    await callback.answer("Отмечено как выполнено ✅")

@router.callback_query(lambda c: c.data == "back")
async def go_back(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    await callback.message.delete()
    await clear_old(user_id, chat_id)
    msg = await callback.message.answer("Выбери день недели для тренировки:", reply_markup=days_keyboard())
    await callback.message.answer(reply_markup=main_reply_keyboard())
    last_bot_messages[user_id] = msg.message_id
    main_menu_messages[user_id] = msg.message_id
    await callback.answer()

@router.message(lambda m: m.text == "📅 Вернуться к расписанию")
async def return_to_schedule(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    await clear_old(user_id, chat_id)
    try:
        await message.delete()
    except:
        pass
    msg = await message.answer("Выбери день недели для тренировки:", reply_markup=days_keyboard())
    await message.answer(reply_markup=main_reply_keyboard())
    last_bot_messages[user_id] = msg.message_id
    main_menu_messages[user_id] = msg.message_id

@router.message()
async def rude_reply(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        await message.delete()
    except:
        pass
    await clear_old(user_id, chat_id)
    msg = await message.answer("ты додик? нахуй ты мне это пишешь, теряйся")
    await message.answer(reply_markup=main_reply_keyboard())
    last_bot_messages[user_id] = msg.message_id

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
