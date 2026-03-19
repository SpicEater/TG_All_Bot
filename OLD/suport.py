import sqlite3 as sql
import logging
import asyncio
import aiohttp
import telegram.error
from telegram import Update, Bot
from telegram.ext import Application, ContextTypes, MessageHandler, filters, CommandHandler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Здравствуйте! Это поддержка SendAll. Напишите своё сообщение и мы постораемся решить вашу проблуму.')

# Обработка сообщений от пользователей
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_message = update.message.text

    # Отправляем сообщение администратору с информацией о пользователе
    await context.bot.send_message(
        chat_id=911810571,
        text=f"Сообщение от {user.first_name} {user.last_name} (username: @{user.username}, id: {user.id}):\n\n{user_message}"
    )

    # Подтверждаем пользователю, что сообщение отправлено
    await update.message.reply_text('Ваше сообщение отправлено. Ваш отзыв помогает нам стать лучше.')

# Функция для обработки ответов администратора
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Сообщение должно быть в формате: "/reply <user_id> <ответ>"
    if not update.message.chat_id == 911810571:
        return
    command, user_id, *reply_message = update.message.text.split()
    reply_text = ' '.join(reply_message)
    await context.bot.send_message(chat_id=int(user_id), text=f"Здарвсвуйте, дорогой пользователь. {reply_text}")

async def periodic_internet_check(interval_hours):
    while True:
        internet_connected = await check_internet_connection()
        if internet_connected:
            logger.info("Интернет-соединение установлено.")
        else:
            logger.warning("Отсутствует интернет-соединение.")

        await asyncio.sleep(interval_hours * 3600)
async def check_internet_connection():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://www.google.com') as response:
                return response.status == 200
    except aiohttp.ClientError:
        return False

def main() -> None:
    application = Application.builder().token("7751044247:AAHa5acZt8gs_xdBY_GhY3f5yLT2QwTJ378").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("reply", handle_admin_reply))

    loop = asyncio.get_event_loop()
    loop.create_task(periodic_internet_check(interval_hours=6))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()


