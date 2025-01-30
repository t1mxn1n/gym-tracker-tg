import asyncio
import logging
import os
from collections import defaultdict
from datetime import datetime, time
from os import getenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile
from aiogram.types.callback_query import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from db.connect import async_session_maker
from db.models import User, BodyPart, Exercise, History

logging.getLogger('sqlalchemy.engine.Engine').setLevel(logging.ERROR)

load_dotenv()

TOKEN = getenv("bot_token")
dump_key = getenv("dump_key")
alembic_cfg = Config(getenv("alembic_cfg"))

dp = Dispatcher()

ITEMS_PER_PAGE = 6

users_db_state = {}


class Form(StatesGroup):
    user_id_db = State()
    body_part = State()
    bp_id = State()
    exercise = State()
    ex_id = State()
    note = State()


def get_paginated_keyboard(data: list, current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    start = current_page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    for item in data[start:end]:
        builder.button(text=item["name"][:29], callback_data=f"{prefix}item_{item['id']}")

    builder.adjust(2)
    # Добавляем кнопки пагинации
    navigation_buttons = []
    if current_page > 0:
        navigation_buttons.append(InlineKeyboardButton(text="«", callback_data=f"{prefix}page_{current_page - 1}"))
    if current_page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton(text="»", callback_data=f"{prefix}page_{current_page + 1}"))

    if navigation_buttons:
        builder.row(*navigation_buttons)

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

    await callback.message.edit_text(f"Что сегодня будем качать?", reply_markup=keyboard)


# Обработка нажатий на элементы (часть тела)
@dp.callback_query(lambda callback: callback.data.startswith("bpitem_"))
async def handle_item_click(callback: CallbackQuery, state: FSMContext):

    item_id = callback.data.split("_")[1]

    async with async_session_maker() as session:
        async with session.begin():
            bp_name = await session.execute(select(BodyPart.name).where(BodyPart.id == item_id))

    bp_name = bp_name.scalars().first()

    await state.update_data(body_part=bp_name, bp_id=item_id)

    await callback.message.edit_text(
        f"Вы выбрали: {bp_name}",
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
    if not keyboard.inline_keyboard:
        await callback.message.edit_text("Нет ни одного созданного упражнения",
                                         reply_markup=InlineKeyboardMarkup(
                                             inline_keyboard=[
                                                 [InlineKeyboardButton(text="Создать", callback_data="ex_create")]
                                             ]))
    else:
        await callback.message.edit_text("Выберите упражнение", reply_markup=keyboard)


# Обработка нажатий на элементы (упражнение)
@dp.callback_query(lambda callback: callback.data.startswith("exitem_"))
async def handle_item_click_ex(callback: CallbackQuery, state: FSMContext):

    item_id = callback.data.split("_")[1]

    async with async_session_maker() as session:
        async with session.begin():
            ex_name = await session.execute(select(Exercise.name).where(Exercise.id == item_id))
    ex_name = ex_name.scalars().first()

    await state.update_data(exercise=ex_name, ex_id=item_id)
    await state.set_state(Form.note)

    async with async_session_maker() as session:
        async with session.begin():
            hist = await session.execute(
                select(History).where(
                    and_(History.user_id == users_db_state.get(callback.from_user.id),
                         History.exercise_id == item_id)).
                order_by(History.created_at.asc())
            )
            hist_dict = [{"time": e.created_at, "note": e.note} for e in hist.scalars().all()]

    hist_dict = hist_dict[-10:]
    if hist_dict:
        hist_msg = "".join(f"{h['time'].strftime('%d.%m.%Y')} | {h['note']}\n" for h in hist_dict)
    else:
        hist_msg = "Нет записей о прошлых занятиях.\n"
    await callback.message.edit_text(f"Вы выбрали: \"{ex_name}\".\n{hist_msg}Далее ввод записи формата: 100(8)-90(7)",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
                                         text="Стоп", callback_data="stop")]]))


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
    if message.text == "/exit":
        await exit_command(message, state)
        return
    data = await state.update_data(exercise=message.text)
    user_id = users_db_state.get(message.from_user.id)
    async with async_session_maker() as session:
        async with session.begin():
            exercise = Exercise(user_id=user_id, bp_id=data.get("bp_id"), name=data.get("exercise"))
            session.add(exercise)
            await session.commit()
            await state.update_data(ex_id=exercise.id)
    await state.set_state(Form.note)
    await message.answer(f"Упражнение \"{message.text}\" сохранено.\nДалее ввод записи формата: 100(8)-90(7)",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
                             text="Стоп", callback_data="stop")]]))


@dp.message(Form.note)
async def process_exercise(message: Message, state: FSMContext) -> None:
    await state.update_data(note=message.text)
    if message.text == "/exit":
        await exit_command(message, state)
        return
    await message.answer(f"Подтверждаете запись \"{message.text}\"?.",
                         reply_markup=
                         InlineKeyboardMarkup(inline_keyboard=[
                             [
                                 InlineKeyboardButton(text="Да", callback_data="save_1"),
                                 InlineKeyboardButton(text="Нет", callback_data="save_0"),
                             ]
                         ]))


@dp.callback_query(lambda callback: callback.data.startswith("save"))
async def handle_save_hist(callback: CallbackQuery, state: FSMContext):
    flag = callback.data.split("_")[1]
    if flag == "1":
        data = await state.get_data()
        user_id = users_db_state.get(callback.from_user.id)
        async with async_session_maker() as session:
            async with session.begin():
                hist = History(
                    user_id=int(user_id),
                    bp_id=int(data.get("bp_id", 0)),
                    exercise_id=int(data.get("ex_id", 0)),
                    note=data.get("note", "")
                )
                session.add(hist)
                await session.commit()
        await callback.message.edit_text(f"Запись сохранена!")
        await state.clear()
        del users_db_state[callback.from_user.id]
    else:
        await callback.message.edit_text(f"Введите запись о упражнении:")
        await state.set_state(Form.note)


@dp.callback_query(lambda callback: callback.data.startswith("stop"))
async def handle_stop(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if users_db_state.get(callback.from_user.id):
        del users_db_state[callback.from_user.id]
    msg = callback.message.text.split("\n")[:-1]
    msg = "\n".join(msg)
    await callback.message.edit_text(f"{msg}\n/start \n/today_stat")


@dp.message(Command("exit"))
async def exit_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    if users_db_state.get(message.from_user.id):
        del users_db_state[message.from_user.id]
    await message.answer(f"Завершено.\n /start \n/today_stat")


@dp.message(Command("today_stat"))
async def exit_command(message: Message) -> None:
    async with async_session_maker() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.user_id == message.from_user.id))
            user_db = result.scalars().first()
            if not user_db:
                await message.answer(f"У вас нет записей.")
                return

            hist = await session.execute(
                select(History).where(History.user_id == user_db.id).
                options(joinedload(History.body_part), joinedload(History.exercise)).
                filter(History.created_at >= datetime.combine(datetime.today(), time.min))
            )

            hist_dict = [
                {"bp": e.body_part.name, "exercise": e.exercise.name, "note": e.note}
                for e in hist.scalars().all()
            ]

            if not hist_dict:
                await message.answer(f"У вас нет записей за сегодня.")
                return

            grouped = defaultdict(list)
            for item in hist_dict:
                grouped[item["bp"]].append(item)
            grouped = dict(grouped)
            msg = ""
            c = 1
            for bp in grouped:
                msg += f"<b>{bp}</b> \n"
                for ex in grouped[bp]:
                    msg += f"{c}. {ex['exercise']} | {ex['note']} \n"
                    c += 1
                msg += "\n"

    await message.answer(f"{msg}")


@dp.message(Command("dump"))
async def echo_handler(message: Message) -> None:
    if len(message.text.split(" ")) == 1:
        await message.answer(f"боже куда мы лезем...")
        return
    pass_phrase = message.text.split(" ")[1]
    if pass_phrase == dump_key:
        if os.path.exists("data.db"):
            await message.answer_document(FSInputFile(path="data.db"), caption="derji")
        else:
            await message.answer(f"я в ахуе если често...")
    else:
        await message.answer(f"боже куда мы лезем...")


@dp.message(Command("body"))
async def echo_handler(message: Message) -> None:
    try:
        await message.answer("eblan?")
    except TypeError:
        await message.answer("Nice try!")


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    command.upgrade(alembic_cfg, "head")
    logger.info("bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
