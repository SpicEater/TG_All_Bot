import aiosqlite, re
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
# from NEW_BOT.chat_bot import bot

TAG_CACHE = {}

chat_router = Router()

async def load_cache():
    global TAG_CACHE
    TAG_CACHE = {}

    async with aiosqlite.connect("chat_conf/tag.db") as db:

        cursor = await db.execute("""
            SELECT c.chat_id, c.ping_chat, c.ping_bot,
                   t.tag,
                   u.user_id, u.username
            FROM chats c
            LEFT JOIN tags t ON t.chat_id = c.chat_id
            LEFT JOIN tag_users u ON u.tag_id = t.id
        """)

        rows = await cursor.fetchall()

    for chat_id, ping_chat, ping_bot, tag, user_id, username in rows:

        TAG_CACHE.setdefault(chat_id, {
            "ping_chat": ping_chat,
            "ping_bot": ping_bot,
            "tags": {}
        })

        if not tag or not user_id:
            continue

        TAG_CACHE[chat_id]["tags"].setdefault(tag, [])

        mention = f"@{username}" if username else f"<a href='tg://user?id={user_id}'>user</a>"

        TAG_CACHE[chat_id]["tags"][tag].append((user_id, mention))

def clean_tag(tag: str) -> str:
    return "".join(c for c in tag if c.isalnum() or c == "_")

@chat_router.message(Command('add'))
async def add_tag(message: Message, command: CommandObject):

    if command.args == None:
        tag = 'all'
    elif not command.args.isspace():
        tag = clean_tag(command.args).lower()
    else:
        await message.reply('Формат: \\add сам_тег')
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username

    async with aiosqlite.connect("chat_conf/tag.db") as db:

        await db.execute("""
            INSERT OR IGNORE INTO tags (tag, chat_id)
            VALUES (?, ?)
        """, (tag, chat_id))

        cursor = await db.execute("""
            SELECT id FROM tags
            WHERE tag = ? AND chat_id = ?
        """, (tag, chat_id))

        tag_id = (await cursor.fetchone())[0]

        await db.execute("""
            INSERT OR IGNORE INTO tag_users (tag_id, user_id, username)
            VALUES (?, ?, ?)
        """, (tag_id, user_id, username))

        await db.execute("""
            INSERT OR IGNORE INTO chats (chat_id)
            VALUES (?)
        """, (chat_id,))

        await db.commit()

    # 🔥 точечное обновление cache
    TAG_CACHE.setdefault(chat_id, {
        "ping_chat": 1,
        "ping_bot": 0,
        "tags": {}
    })

    TAG_CACHE[chat_id]["tags"].setdefault(tag, [])

    mention = f"@{username}" if username else f"<a href='tg://user?id={user_id}'>user</a>"

    TAG_CACHE[chat_id]["tags"][tag].append((user_id, mention))

    await message.reply(f"Добавлен в тег {tag}")

@chat_router.message()
async def handle_tags(message: Message, bot: Bot):

    if not message.text:
        return

    text = message.text

    if "#" not in text and "@" not in text:
        return

    # if not message.entities:
    #     return

    chat_id = message.chat.id

    if TAG_CACHE == {}:
        await load_cache()
    chat_cache = TAG_CACHE.get(chat_id)

    if not chat_cache:
        return

    ping_chat = chat_cache["ping_chat"]
    ping_bot = chat_cache["ping_bot"]
    tags_map = chat_cache["tags"]

    found = set()

    n = len(text)
    i = 0
    while i < n:
        chunk = text[i]
        if chunk == "@" or chunk == "#":
            i += 1
            start = i
            while i < n:
                c = text[i]

                if c.isalnum() or c == "_":
                    i += 1
                else:
                    break
            if start != i:
                found.add(text[start:i].lower())
        else:
            i += 1

    if not found:
        return

    result_mentions = []
    result_user_ids = set()

    for tag in found:

        users = tags_map.get(tag)
        if not users:
            continue

        for user_id, mention in users:
            result_mentions.append(mention)
            result_user_ids.add(user_id)

    # 🔥 ping в чате
    if ping_chat and result_mentions:

        chunk = ""
        for m in result_mentions:

            if len(chunk) + len(m) + 1 > 4000:
                await message.reply(chunk)
                chunk = ""

            chunk += m + " "

        if chunk:
            await message.reply(chunk)

    # 🔥 уведомление в ЛС
    if ping_bot and result_user_ids:

        text_dm = (
            f"Вас упомянули по тегу.\n"
            f"Чат: {message.chat.title}\n"
            f"Сообщение:\n"
            f"{message.text[:500]}"
        )

        for uid in result_user_ids:
            try:
                await bot.send_message(uid, text_dm)
            except:
                pass
