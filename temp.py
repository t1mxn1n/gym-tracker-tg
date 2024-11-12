import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from sqlalchemy import create_engine, Column, Integer, String, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Замените на свой токен
API_TOKEN = 'YOUR_BOT_API_TOKEN'

# Настроим логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Подключение к базе данных SQLite через SQLAlchemy
DATABASE_URL = "sqlite:///user_data.db"
Base = declarative_base()


# Модель данных для пользователя
class UserChoice(Base):
    __tablename__ = 'user_choices'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    selected_state = Column(String, nullable=False)
    selected_option = Column(String, nullable=True)


# Создаем таблицы в базе данных (если они не существуют)
engine = create_engine(DATABASE_URL, echo=True)
Base.metadata.create_all(bind=engine)

# Сессия для работы с БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Создание машины состояний
class Form(StatesGroup):
    waiting_for_state = State()
    waiting_for_choice = State()


# Функция для сохранения данных в БД
def save_user_choice(user_id: int, selected_state: str, selected_option: str = None):
    session = SessionLocal()
    try:
        user = session.query(UserChoice).filter(UserChoice.user_id == user_id).first()
        if user:
            # Обновление данных пользователя
            user.selected_state = selected_state
            user.selected_option = selected_option
        else:
            # Добавление нового пользователя
            user = UserChoice(user_id=user_id, selected_state=selected_state, selected_option=selected_option)
            session.add(user)

        session.commit()
    except IntegrityError:
        session.rollback()
    finally:
        session.close()


# Начало работы с ботом
@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    # Отправляем сообщение с кнопками для выбора состояния
    keyboard = InlineKeyboardMarkup(row_width=1)
    state_button = InlineKeyboardButton(text="Выбрать состояние", callback_data="choose_state")
    keyboard.add(state_button)
    await message.answer("Привет! Выберите действие.", reply_markup=keyboard)


# Обработка нажатия на кнопку выбора состояния
@dp.callback_query_handler(lambda c: c.data == 'choose_state', state='*')
async def choose_state(call: types.CallbackQuery):
    # Переходим в состояние выбора состояния
    await Form.waiting_for_state.set()

    # Кнопки выбора состояния
    keyboard = InlineKeyboardMarkup(row_width=1)
    state1_button = InlineKeyboardButton(text="Состояние 1", callback_data="state_1")
    state2_button = InlineKeyboardButton(text="Состояние 2", callback_data="state_2")
    keyboard.add(state1_button, state2_button)

    await call.message.answer("Выберите состояние:", reply_markup=keyboard)


# Обработка выбора состояния
@dp.callback_query_handler(lambda c: c.data in ['state_1', 'state_2'], state=Form.waiting_for_state)
async def process_state_choice(call: types.CallbackQuery, state: FSMContext):
    # Сохраняем выбранное состояние
    selected_state = call.data
    await state.update_data(state=selected_state)

    # Переходим к следующему состоянию, связанному с выбором
    await Form.waiting_for_choice.set()

    # Генерация выпадающего списка в зависимости от выбранного состояния
    if selected_state == 'state_1':
        choices = ['Опция 1', 'Опция 2', 'Опция 3']
    else:
        choices = ['Опция A', 'Опция B', 'Опция C']

    # Создание кнопок для выбора
    keyboard = InlineKeyboardMarkup(row_width=1)
    for choice in choices:
        keyboard.add(InlineKeyboardButton(text=choice, callback_data=choice))

    await call.message.answer(f"Вы выбрали {selected_state}. Теперь выберите опцию:", reply_markup=keyboard)


# Обработка выбора из выпадающего списка
@dp.callback_query_handler(state=Form.waiting_for_choice)
async def process_choice(call: types.CallbackQuery, state: FSMContext):
    # Получаем выбранную опцию
    chosen_option = call.data
    user_id = call.from_user.id

    # Сохраняем выбор в базу данных
    user_data = await state.get_data()
    selected_state = user_data.get('state')

    # Сохраняем состояние и опцию в базе данных
    save_user_choice(user_id, selected_state, chosen_option)

    await call.message.answer(f"Вы выбрали: {chosen_option}. Ваш выбор сохранен.")

    # Завершаем сессию
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
