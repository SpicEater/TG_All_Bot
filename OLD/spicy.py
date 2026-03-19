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

DB = 'user.db'

async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    title = update.effective_chat.title
    remember('BOT', 0, chat, title)
    await update.message.reply_text('Отлично, теперь дай мне права на чтение сообщений и пропишите команду /remember')

async def start_remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.name
    id_user = update.effective_user.id
    id_chat = update.effective_chat.id
    chat = update.effective_chat.title
    if not remember(user, id_user, id_chat, chat):
        await update.message.reply_text('Вы уже в списке', do_quote=False)

def remember (user, id_user, chat, title):
    con = sql.connect(DB)
    with con:
        cur = con.cursor()
        if not title: title = 'BOT'
        # title = title.replace(" ", "@#!")
        try:
            con.execute("CREATE TABLE IF NOT EXISTS `user` (`name` TEXT, `id_user` INTEGER, `title` TEXT, `id_chat` INTEGER, tags TEXT, 'push' INTEGER, 'message' INTEGER)")
            cur.execute(f"BEGIN TRANSACTION; ")
            cur.execute(f"SELECT COUNT(*) FROM user WHERE name = 'BOT' AND id_chat = '{chat}';")
            prov = cur.fetchall()[0][0]
            if prov == 0:
                cur.execute(f"INSERT INTO user VALUES ('BOT', 0, '{title}', {chat}, '@all', 1, 0);")
            cur.execute(f"SELECT COUNT(*) FROM user WHERE name = '{user}' AND id_chat = '{chat}';")
            if cur.fetchall() != [(0,)]:
                return False
            cur.execute(f"INSERT INTO user VALUES ('{user}', {id_user}, '{title}', {chat}, '@all', 1, 0);")
            con.commit()
            cur.close()
        except ():
            cur.execute(f"INSERT INTO user VALUES ('{user}', {id_user}, '{title}', {chat}, '@all', 1, 0);")
            con.commit()
            cur.close()
            pass
        return True

async def call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat.id
    text = sql.connect(DB).execute(f"SELECT name, id_user FROM user WHERE id_chat = {chat} and name != 'BOT' and push = 1 and id_user != {user.id};").fetchall()
    mas = ''
    for f in text:
        mas += f"[{f[0]}](tg://user?id={f[1]})" + " "
    try: await update.message.reply_text(mas, do_quote=False, parse_mode='MarkdownV2')
    except telegram.error.BadRequest: pass


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
    application = Application.builder().token("6941947875:AAFVzXUviZAgmuZmV1p5dQVhSOtaVcuuEr8").build()

    application.add_handler(CommandHandler("start", link, filters.Regex('link')))
    application.add_handler(CommandHandler("remember", start_remember))
    application.add_handler(MessageHandler(
                            filters.Regex("@all|@все|@чурки|@гойда|@spicyeater_bot") | filters.CaptionRegex(r"@all|@все|@чурки|@гойда"), call))

    loop = asyncio.get_event_loop()
    loop.create_task(periodic_internet_check(interval_hours=6))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()