from spicy import remember
import logging
import asyncio
import aiohttp
import telegram
import re
import sqlite3 as sql
from telegram import Update, helpers, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, ChatInviteLink
from telegram.ext import Application, ContextTypes, MessageHandler, filters, CommandHandler, CallbackQueryHandler
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

DB = 'user.db' ##путь к БД

async def periodic_internet_check(interval_hours): ##запуск команды проверки соеденения
    while True:
        internet_connected = await check_internet_connection()
        if internet_connected:
            logger.info("Интернет-соединение установлено.")
        else:
            logger.warning("Отсутствует интернет-соединение.")

        await asyncio.sleep(interval_hours * 3600)


async def check_internet_connection(): ##проверка соедениния с интернетом
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://www.google.com') as response: ##обращение к google
                return response.status == 200
    except aiohttp.ClientError:
        return False

async def add_bot(update: Update, context: ContextTypes.DEFAULT_TYPE): ##оброботчик команды /add_bot
    url = helpers.create_deep_linked_url('spicyeater_bot', "link", group=True)
    url += '&admin=post_messages'
    query = update.callback_query
    try:
        await query.edit_message_text(
            'Нажми на кнопку, чтобы добавить бота',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='Ссылка', url=url)], [InlineKeyboardButton(text='Меню', callback_data='start')]]))
    except:
        await update.message.reply_text(
            'Нажми на кнопку, чтобы добавить бота',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='Ссылка', url=url)], [InlineKeyboardButton(text='Меню', callback_data='start')]]))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): ##оброботчик команды /start
    args = context.args
    user = update.effective_user.name
    user_id = update.effective_user.id

    if args:
        args = args[0].split('25zwV56')
        sear = re.search(r"(.*?)-", args[0])
        decode_spes = ''.join(chr(int(code)) for code in sear.group(1).split('I'))
        text = args[0].replace(sear.group(1), decode_spes)
        encoded_bytes = text.encode('ascii')
        args[0] = encoded_bytes.decode('punycode')
        chat = int(''.join(args[-1:]))
        title = " ".join(args[:-1])
        if not remember(user, user_id, chat, title):
            await context.bot.send_message(update.effective_chat.id,
                                           "Вы уже состоите в этом чате", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text= 'Назад', callback_data=f'start')]]))
    else:
        masage = 'Привет! Этот бот поможет тебе быстро упомянуть всех участников гуппы. Вот что он может:\n\n' \
                 '📋 Выбрать гуппу — выбери гуппу из списка уже добавленных для настройки.\n\n' \
                 '➕ Добавить бота — добавь меня в новый чат для работы.\n\n' \
                 'ℹ️ Поддержка — напиши в поддержку, если нужна помощь.\n\n' \
                 '💰 Донат — поддержи проект и помоги мне стать лучше! \n\n' \
                 'Нажми на кнопку ниже, чтобы выбрать действие!'
        mark = InlineKeyboardMarkup([[InlineKeyboardButton(text='📋Выбрать гуппу', callback_data='group_selection')],[InlineKeyboardButton(text='➕Добавить бота', callback_data='add_bot')],
                                       [InlineKeyboardButton(text='ℹ️Поддержка', callback_data='suport'), InlineKeyboardButton(text='🔒Донат', callback_data='donat')]])
        try:
            await update.callback_query.edit_message_text(masage,reply_markup= mark)
        except:
            await update.message.reply_text(masage, reply_markup=mark)

async def group_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id= str(update.effective_user.id)
    chat_id = update.effective_chat.id
    user_name = update.effective_user.name
    con = sql.connect(DB)

    with con:
        cur = con.cursor()
        try:
            cur.execute(f"SELECT DISTINCT title FROM user WHERE id_user = '{user_id}' or name = '{user_name}';")##
            # print(cur.fetchall())
        except:
            await context.bot.send_message(chat_id, "Не нашел вас ни в одном чате")
            return False
        w = []
        for i in cur.fetchall():
            w.append(i[0])
        masage = '📋Выбрите гуппу'
        button = [[InlineKeyboardButton(i, callback_data=f'group {i}')] for i in w]

        mark = InlineKeyboardMarkup(button)
        try:
            await update.callback_query.edit_message_text(masage, reply_markup=mark)
        except:
            await update.message.reply_text(masage, reply_markup=mark)

async def group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.callback_query.data[6::]
    information = f'{args}\n' \
                  f''
    markup =  InlineKeyboardMarkup([[InlineKeyboardButton(text= 'Добавить людей', callback_data=f'add_people {args}'),InlineKeyboardButton(text= 'Уведомления', callback_data=f'notify   {args}')],
                                    [InlineKeyboardButton(text= 'Выйти из группы', callback_data=f'delete {args}'),InlineKeyboardButton(text= 'Назад', callback_data=f'start')]])
    try:
        await update.callback_query.edit_message_text(information, reply_markup=markup)
    except:
        await update.message.reply_text(information, reply_markup=markup)

async def add_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.callback_query.data[11::]
    con = sql.connect(DB)

    if args:
        with con:
            cur = con.cursor()
            try:
                cur.execute(f"SELECT DISTINCT id_chat FROM user WHERE title = '{args}';")
                chat = cur.fetchall()
            except:
                await context.bot.send_message(update.effective_chat.id,
                                               "Для того чтобы пригласить когото нужно чтобы хотябы у одного человека были включены уведомления. Попробуйте перелогиниться, прописав команду /remember в чате")
    name_chat = args
    text = str(args.encode('punycode'))
    text = text[2:len(text) - 1]
    sear = re.search(r"(.*?)-", text)
    encode_spes = 'I'.join(str(ord(char)) for char in sear.group(1))
    text = text.replace(sear.group(1), encode_spes)
    text = ''.join(k if k != " " else "32I" for k in list(text))
    link = context.bot.link + f'?start={text}25zwV56{chat[0][0]}'
    await update.callback_query.edit_message_text(
        f"Поделитесь этой ссылкой для присоединения других пользователей:\n{link}", reply_markup=
        InlineKeyboardMarkup([[InlineKeyboardButton(text='Назад', callback_data=f'group {name_chat}')]]))

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def confrim():
        con.execute(f"DELETE FROM user WHERE user_id = '{user_id}' and title = '{chat}';")
        con.commit()
    user_id = update.effective_user.id
    con = sql.connect(DB)
    chat = update.callback_query.data[7::]
    if update.callback_query.data.startswith('delete1'):
        confrim()
        await update.callback_query.edit_message_text("Вы удалены из группы", reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text='Меню', callback_data='start')]]))

    murkup = InlineKeyboardMarkup([[InlineKeyboardButton(text=f'Да', callback_data=f'delete1{chat}'),
                                    InlineKeyboardButton(text=f'Нет', callback_data=f'group {chat}')]])
    await update.callback_query.edit_message_text("Вы уверены что хотите выйти из группы?", reply_markup= murkup)

async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def chang(con):
        push_value = update.callback_query.data[8:9:]
        con.execute(f"UPDATE user SET push = {push_value} WHERE name = '{user}' and title = '{chat}';")
        con.commit()
    user = update.effective_user.name
    con = sql.connect(DB)
    chat = update.callback_query.data[9::]
    if update.callback_query.data.startswith('notify 1'):
        chang(con)
    elif update.callback_query.data.startswith('notify 2'):
        pass
    push_value = 0
    push_emojis = '✅'
    if con.execute(f"SELECT COUNT(*) FROM user WHERE name = '{user}' and title = '{chat}' and push = 0;").fetchone()[0] == 1:
        push_value = 1
        push_emojis = '❌'
    con.close()
    murkup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=f'{push_emojis}Упоменуть в чате', callback_data=f'notify 1{push_value}{chat}'),
          InlineKeyboardButton(text=f'🔒Сообщение в боте', callback_data=f'notify 2{push_value}{chat}')],
         [InlineKeyboardButton(text='Назад', callback_data=f'group {chat}')]])
    await update.callback_query.edit_message_text("🔔Уведомления \n\n"
                                                  "Здесь вы можете включить или выключит уведомления для группы\n"
                                                  "Упоменуть в чате - ваш ник будет упомянут в чате\n"
                                                  "Сообщение в боте - вам придет сообщение от бота что вас упомянули", reply_markup=murkup)

async def suport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    murkup = InlineKeyboardMarkup([[InlineKeyboardButton(text='Поддержка', url='https://t.me/SuportAllBot?start=start')], [InlineKeyboardButton(text='Отмена', callback_data='start')]])
    await update.callback_query.edit_message_text(
        "Напишите проблему с которой вы сталкнулись во время работы с ботом. Ваши отзывы, предложения и комментарии помогают нам улучшать функционал, исправлять ошибки и делать бота более удобным для всех пользователей.",
        reply_markup=murkup)



def main() -> None:
    application = Application.builder().token("6572779723:AAGvYhji-PdqXZWj72E1lrAUjqOMYT5Tz0E").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start, pattern='start'))

    application.add_handler(MessageHandler(filters.Regex('^/add_bot|Добавить бота$'), add_bot))
    application.add_handler(CallbackQueryHandler(add_bot, '^add_bot$'))

    application.add_handler(MessageHandler(filters.Regex('^/suport|Поддержка$'), suport))
    application.add_handler(CallbackQueryHandler(suport, '^suport$'))

    application.add_handler(CommandHandler("group_selection", group_selection))
    application.add_handler(CallbackQueryHandler(group_selection, pattern='^group_selection'))

    application.add_handler(CallbackQueryHandler(group, pattern = 'group'))

    application.add_handler(CallbackQueryHandler(add_people, pattern='add_people'))


    application.add_handler(CallbackQueryHandler(notify, pattern='notify'))

    application.add_handler(CallbackQueryHandler(delete, pattern='delete'))

    loop = asyncio.get_event_loop()
    # loop.create_task(delete_mess(interval_hours=12)
    loop.create_task(periodic_internet_check(interval_hours=6)) ##выполнение команды проверки интернета каждые 6 часов

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()