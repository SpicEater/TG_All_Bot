import logging
import asyncio

from chat_conf.token import token
from aiogram import Dispatcher, Bot, F
from NEW_BOT.app.bot.hendler import bot_router
from NEW_BOT.app.chat.hendler import chat_router

at_search = (F.chat.type.in_({"group", "supergroup"})) & F.text.contains('@')
is_private = F.chat.type == "private"


bot = Bot(token=token)
dp = Dispatcher()

async def main():
    dp.include_router(bot_router)
    dp.include_router(chat_router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        logging.basicConfig(level=logging.INFO)
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nGoodbye')

