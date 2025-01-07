import asyncio
import json
from os import getenv
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder
from aiogram.types.callback_query import CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy import and_
from aiogram.fsm.state import State, StatesGroup

from db.connect import async_session_maker
from db.models import User, BodyPart, Exercise

from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)

logging.getLogger('sqlalchemy.engine.Engine').setLevel(logging.ERROR)

load_dotenv()

TOKEN = getenv("bot_token")
alembic_cfg = Config(getenv("alembic_cfg"))

dp = Dispatcher()

ITEMS_PER_PAGE = 6

users_db_state = {}


class Form(StatesGroup):
    user_id_db = State()
    body_part = State()
    bp_id = State()
    exercise = State()
    note = State()


def get_paginated_keyboard(data: list, current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Добавляем элементы текущей страницы
    start = current_page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    for item in data[start:end]:
        builder.button(text=item["name"], callback_data=f"{prefix}item_{item['name']}_{item['id']}")

    builder.adjust(2)
    # Добавляем кнопки пагинации
    navigation_buttons = []
    if current_page > 0:  # Кнопка "влево" (если не первая страница)
        navigation_buttons.append(InlineKeyboardButton(text="«", callback_data=f"{prefix}page_{current_page - 1}"))
    if current_page < total_pages - 1:  # Кнопка "вправо" (если не последняя страница)
        navigation_buttons.append(InlineKeyboardButton(text="»", callback_data=f"{prefix}page_{current_page + 1}"))

    if navigation_buttons:
        builder.row(*navigation_buttons)  # Добавляем кнопки на одну строку

    return builder.as_markup()


@dp.message(CommandStart())
async def command_start_handler(message: Message, from_func: bool = False) -> None:
    """
    This handler receives messages with `/start` command
    """

    user_id = message.from_user.id
    user_name = message.from_user.username
    async with async_session_maker() as session:
        async with session.begin():
            try:

                result = await session.execute(select(User).where(User.user_id == user_id))
                user_db = result.scalars().first()
                if not user_db:
                    user_db = User(user_id=user_id, user_name=user_name)
                    session.add(user_db)
                    await session.commit()

                if not from_func:
                    users_db_state[user_id] = user_db.id
                bps = await session.execute(select(BodyPart))

                bps_dict = [{"id": b.id, "name": b.name} for b in bps.scalars().all()]

                total_pages = (len(bps_dict) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

                await message.answer(
                    "Что сегодня будем качать?",
                    reply_markup=get_paginated_keyboard(bps_dict, 0, total_pages, prefix="bp")
                )

            except IntegrityError as e:
                logger.error(f"IntegrityError: {e}")
                await session.rollback()
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await session.rollback()


@dp.callback_query(lambda callback: callback.data.startswith("bppage_"))
async def handle_page_click(callback: CallbackQuery):
    # todo: сделать кеш на запрос в бд
    async with async_session_maker() as session:
        async with session.begin():
            bps = await session.execute(select(BodyPart))
            bps_dict = [{"id": b.id, "name": b.name} for b in bps.scalars().all()]

    current_page = int(callback.data.split("_", 1)[1])
    total_pages = (len(bps_dict) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    keyboard = get_paginated_keyboard(bps_dict, current_page, total_pages, prefix="bp")

    # Обновляем сообщение с новой клавиатурой
    await callback.message.edit_text(f"Что сегодня будем качать?", reply_markup=keyboard)
    # await callback.answer()


# Обработка нажатий на элементы
@dp.callback_query(lambda callback: callback.data.startswith("bpitem_"))
async def handle_item_click(callback: CallbackQuery, state: FSMContext):

    item_name = callback.data.split("_")[1]
    item_id = callback.data.split("_")[2]
    await state.update_data(body_part=item_name, bp_id=item_id)

    await callback.message.edit_text(
        f"Вы выбрали: {item_name}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Выбрать упражнение", callback_data="ex_choose"),
                    InlineKeyboardButton(text="Создать упражнение", callback_data="ex_create"),
                ],
                [
                    InlineKeyboardButton(text="Назад", callback_data="ex_back")
                ]
            ]
        )
    )


@dp.callback_query(lambda callback: callback.data.startswith("ex_choose"))
async def handle_ex_choose(callback: CallbackQuery, state: FSMContext):

    bp_id = await state.get_value("bp_id")

    async with async_session_maker() as session:
        async with session.begin():
            exs = await session.execute(
                select(Exercise).where(and_(Exercise.user_id == users_db_state.get(callback.from_user.id),
                                            Exercise.bp_id == bp_id))
            )
            exs_dict = [{"id": e.id, "name": e.name} for e in exs.scalars().all()]

    total_pages = (len(exs_dict) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    keyboard = get_paginated_keyboard(exs_dict, 0, total_pages, "ex")
    await callback.message.edit_text("Выберите упражнение", reply_markup=keyboard)


@dp.callback_query(lambda callback: callback.data.startswith("ex_back"))
async def handle_ex_back(callback: CallbackQuery):
    await callback.message.delete()
    await command_start_handler(callback.message, from_func=True)


@dp.callback_query(lambda callback: callback.data.startswith("ex_create"))
async def handle_ex_create(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.exercise)
    await callback.message.edit_text(f"{callback.message.text}\nВведите название упражнения")


@dp.message(Form.exercise)
async def process_exercise(message: Message, state: FSMContext) -> None:
    data = await state.update_data(exercise=message.text)
    user_id = users_db_state.get(message.from_user.id)
    async with async_session_maker() as session:
        async with session.begin():
            exercise = Exercise(user_id=user_id, bp_id=data.get("bp_id"), name=data.get("exercise"))
            session.add(exercise)
            await session.commit()

    await state.set_state(Form.note)
    await message.answer(f"Упражнение сохранено.\nДалее ввод записи формата: 100(8)-90(7)")


@dp.message(Form.note)
async def process_exercise(message: Message, state: FSMContext) -> None:
    data = await state.update_data(note=message.text)
    print(data)


@dp.message(Command("body"))
async def echo_handler(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        print(message)
        await message.answer("eblan?")
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    command.upgrade(alembic_cfg, "head")
    logger.info("bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
