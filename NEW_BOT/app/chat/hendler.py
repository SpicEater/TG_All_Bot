import aiosqlite, re
from aiogram import Router, F
from aiogram.types import Message

TAG_CACHE = {}

chat_router = Router()

async def load_cache():
    global TAG_CACHE

    TAG_CACHE = {}

    async with aiosqlite.connect("chat_conf/tag.db") as db:

        cursor = await db.execute("""
            SELECT t.chat_id, t.tag, u.user_id, u.username
            FROM tags t
            JOIN tag_users u ON u.tag_id = t.id
        """)

        rows = await cursor.fetchall()

    for chat_id, tag, user_id, username in rows:

        TAG_CACHE.setdefault(chat_id, {})
        TAG_CACHE[chat_id].setdefault(tag, [])

        if username:
            mention = f"@{username}"
        else:
            mention = f"<a href='tg://user?id={user_id}'>user</a>"

        TAG_CACHE[chat_id][tag].append(mention)

def clean_tag(tag: str) -> str:
    return "".join(c for c in tag if c.isalnum() or c == "_")

@chat_router.message(F.text.startswith("\\add"))
async def add_tag(message: Message):

    match = re.search(r'"(.+?)"', message.text)

    if not match:
        await message.reply('Формат: \\add "tag"')
        return

    tag = clean_tag(match.group(1)).lower()

    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username

    async with aiosqlite.connect("chat_conf/tag.db") as db:

        await db.execute("""
            INSERT OR IGNORE INTO tags(tag, chat_id)
            VALUES (?, ?)
        """, (tag, chat_id))

        cursor = await db.execute("""
            SELECT id FROM tags
            WHERE tag = ? AND chat_id = ?
        """, (tag, chat_id))

        tag_id = (await cursor.fetchone())[0]

        await db.execute("""
            INSERT OR IGNORE INTO tag_users(tag_id, user_id, username)
            VALUES (?, ?, ?)
        """, (tag_id, user_id, username))

        await db.commit()

    # обновляем cache точечно
    TAG_CACHE.setdefault(chat_id, {})
    TAG_CACHE[chat_id].setdefault(tag, [])

    mention = f"@{username}" if username else f"<a href='tg://user?id={user_id}'>user</a>"

    if mention not in TAG_CACHE[chat_id][tag]:
        TAG_CACHE[chat_id][tag].append(mention)

    await message.reply(f"Добавлен в тег {tag}")

@chat_router.message()
async def handle_tags(message: Message):

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

    for tag in found:

        users = chat_cache.get(tag)

        if users:
            result_mentions.extend(users)

    if not result_mentions:
        return

    # chunking
    chunk = ""

    for m in result_mentions:

        if len(chunk) + len(m) + 1 > 4000:
            await message.reply(chunk)
            chunk = ""

        chunk += m + " "

    if chunk:
        await message.reply(chunk)

