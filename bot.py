import asyncio
from os import getenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from db.connect import async_session_maker
from db.models import User

load_dotenv()

TOKEN = getenv("bot_token")
alembic_cfg = Config(getenv("alembic_cfg"))

dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    user_id = message.from_user.id
    user_name = message.from_user.username

    async with async_session_maker() as session:
        async with session.begin():
            try:

                result = await session.execute(select(User).where(User.user_id == user_id))

                if not result.scalars().first():
                    user = User(user_id=user_id, user_name=user_name)
                    session.add(user)
                    await session.commit()
                else:
                    await message.answer("An error occurred while saving your data. Please try again later.")

            except IntegrityError as e:
                logger.error(f"IntegrityError: {e}")
                await session.rollback()
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await session.rollback()


@dp.message()
async def echo_handler(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        await message.send_copy(chat_id=message.chat.id)
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
