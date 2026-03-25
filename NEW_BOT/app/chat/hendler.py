from NEW_BOT.chat_conf.token import DB

import aiosqlite, asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command, CommandObject

TAG_CACHE = {}

chat_router = Router()

async def load_cache():

    global TAG_CACHE
    TAG_CACHE = {}

    async with aiosqlite.connect("tag.db") as db:

        cursor = await db.execute("""
            SELECT
                t.chat_id,
                t.tag,
                u.user_id,
                u.username,
                u.ping_chat,
                u.ping_bot
            FROM tags t
            JOIN tag_users u ON u.tag_id = t.id
        """)

        rows = await cursor.fetchall()

    for chat_id, tag, uid, username, ping_chat, ping_bot in rows:

        TAG_CACHE.setdefault(chat_id, {})
        TAG_CACHE[chat_id].setdefault(tag, [])

        mention = (
            f"@{username}"
            if username
            else f"<a href='tg://user?id={uid}'>user</a>"
        )

        TAG_CACHE[chat_id][tag].append(
            (uid, mention, ping_chat, ping_bot)
        )

def clean_tag(tag: str) -> str:
    return "".join(c for c in tag if c.isalnum() or c == "_")

@chat_router.message(Command('add'))
async def add_tag(message: Message, command: CommandObject):

    if command.args == None:
        tag = 'all'
    elif not command.args.isspace():
        tag = clean_tag(command.args).lower()
    else:
        await message.reply('Формат: /add сам_тег')
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            INSERT OR IGNORE INTO tags(tag, chat_id)
            VALUES (?, ?)
        """, (tag, chat_id))

        await db.commit()

        cursor = await db.execute("""
            SELECT id FROM tags
            WHERE tag = ? AND chat_id = ?
        """, (tag, chat_id))

        tag_id = (await cursor.fetchone())[0]

        await db.execute("""
            INSERT OR IGNORE INTO tag_users(
                tag_id, user_id, username
            )
            VALUES (?, ?, ?)
        """, (tag_id, user_id, username))

        await db.commit()

    chat_cache = TAG_CACHE.setdefault(chat_id, {})
    tag_list = chat_cache.setdefault(tag, [])

    mention = (
        f"@{username}"
        if username
        else f"<a href='tg://user?id={user_id}'>user</a>"
    )

    await message.reply(f'Теперь вы в теге {tag}')

    if not any(u[0] == user_id for u in tag_list):
        tag_list.append((user_id, mention, 1, 1))

@chat_router.message(Command('del'))
async def del_tag(message: Message, command: CommandObject):

    if command.args == None:
        tag = 'all'
    elif not command.args.isspace():
        tag = clean_tag(command.args).lower()
    else:
        await message.reply('Формат: /del сам_тег')
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT id FROM tags
            WHERE tag = ? AND chat_id = ?
        """, (tag, chat_id))

        row = await cursor.fetchone()

        if not row:
            await message.reply("Тег не найден")
            return

        tag_id = row[0]

        cursor = await db.execute("""
            DELETE FROM tag_users
            WHERE tag_id = ? AND user_id = ?
        """, (tag_id, user_id))

        await db.commit()

        if cursor.rowcount == 0:
            await message.reply("Вы не в теге")
            return

        # удаляем тег если пуст
        await db.execute("""
            DELETE FROM tags
            WHERE id = ?
            AND NOT EXISTS (
                SELECT 1 FROM tag_users
                WHERE tag_id = ?
            )
        """, (tag_id, tag_id))

        await db.commit()
    chat_cache = TAG_CACHE.get(chat_id)

    if chat_cache:

        users = chat_cache.get(tag)

        if users:

            users = [u for u in users if u[0] != user_id]

            if users:
                chat_cache[tag] = users
            else:
                del chat_cache[tag]

def ultra_fast_tags(text: str):

    tags = set()
    n = len(text)
    i = 0

    while i < n:

        c = text[i]

        if c == "#" or c == "@":

            j = i + 1

            while j < n and (
                text[j].isalnum() or text[j] == "_"
            ):
                j += 1

            if j > i + 1:
                tags.add(text[i + 1:j].lower())

            i = j
            continue

        i += 1

    return tags

@chat_router.message()
async def handle_tags(message: Message, bot: Bot):

    if not message.text and not message.caption:
        return

    text = message.text or message.caption

    if not TAG_CACHE:
        load_cache()

    chat_cache = TAG_CACHE.get(message.chat.id)
    if not chat_cache:
        return

    found = ultra_fast_tags(text)
    if not found:
        return

    mentions = []
    dm_users = set()

    for tag in found:

        users = chat_cache.get(tag)
        if not users:
            continue

        for uid, mention, ping_chat, ping_bot in users:

            if ping_chat:
                mentions.append(mention)

            if ping_bot:
                dm_users.add(uid)

    # ping chat
    chunk = ""
    for m in mentions:

        if len(chunk) + len(m) + 1 > 4000:
            await message.reply(chunk)
            chunk = ""

        chunk += m + " "

    if chunk:
        await message.reply(chunk)

    # ping dm
    tasks = [
        bot.send_message(uid, "Вас упомянули по тегу\n"
                              "Чат: [{message.chat.title}]({message.get_url()})"
                         , parse_mode="MarkdownV2")
        for uid in dm_users
    ]

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    # ping bot (параллельно)
    text_dm = (
        f"Вас упомянули по тегу\n"
        f"Чат: [{message.chat.title}]({message.get_url()})"
    )

    tasks = [
        bot.send_message(uid, text_dm, parse_mode="MarkdownV2")
        for uid in dm_users
    ]

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)