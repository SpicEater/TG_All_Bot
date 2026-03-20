import aiosqlite, asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command, CommandObject

TAG_CACHE = {}

chat_router = Router()

async def load_cache():

    global TAG_CACHE
    TAG_CACHE = {}

    async with aiosqlite.connect("chat_conf/tag.db") as db:

        cursor = await db.execute("""
            SELECT
                t.chat_id,
                t.tag,
                u.user_id,
                u.username,
                s.ping_chat,
                s.ping_bot
            FROM tags t
            JOIN tag_users u ON u.tag_id = t.id
            LEFT JOIN chats s
                ON s.chat_id = t.chat_id
                AND s.user_id = u.user_id
        """)

        rows = await cursor.fetchall()

    for chat_id, tag, uid, username, ping_chat, ping_bot in rows:

        TAG_CACHE.setdefault(chat_id, {})
        TAG_CACHE[chat_id].setdefault(tag, [])

        mention = f"@{username}" if username else f"<a href='tg://user?id={uid}'>user</a>"

        TAG_CACHE[chat_id][tag].append({
            "uid": uid,
            "mention": mention,
            "ping_chat": ping_chat if ping_chat is not None else 1,
            "ping_bot": ping_bot if ping_bot is not None else 1
        })

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
            INSERT OR IGNORE INTO chats (chat_id, user_id)
            VALUES (?, ?)
        """, (chat_id, user_id))

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

    if not message.text and not message.caption:
        return

    text = message.text or message.caption

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

    mentions = []
    dm_users = set()

    for tag in found:

        users = chat_cache.get(tag)
        if not users:
            continue

        for u in users:

            if u["ping_chat"]:
                mentions.append(u["mention"])

            if u["ping_bot"]:
                dm_users.add(u["uid"])

    # ping chat
    chunk = ""
    for m in mentions:

        if len(chunk) + len(m) + 1 > 4000:
            await message.reply(chunk)
            chunk = ""

        chunk += m + " "

    if chunk:
        await message.reply(chunk)

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