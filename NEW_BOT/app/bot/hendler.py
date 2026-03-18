import aiosqlite
from aiogram import Router
from aiogram.types import Message

chat_router = Router()


def clean_tag(tag: str) -> str:
    return "".join(
        c for c in tag
        if c.isalnum() or c == "_"
    )


@chat_router.message()
async def handle_tags(message: Message):

    if not message.text:
        return

    text = message.text

    # быстрый фильтр
    if "#" not in text and "@" not in text:
        return

    if not message.entities:
        return

    chat_id = message.chat.id

    found_tags = set()

    # извлекаем теги
    for entity in message.entities:

        if entity.type not in ("hashtag", "mention"):
            continue

        raw = text[
            entity.offset + 1 :
            entity.offset + entity.length
        ]

        tag = clean_tag(raw).lower()

        if tag:
            found_tags.add(tag)

    if not found_tags:
        return

    async with aiosqlite.connect("tag.db") as db:

        for tag in found_tags:

            # ищем tag_id
            cursor = await db.execute(
                """
                SELECT id
                FROM tags
                WHERE tag = ? AND chat_id = ?
                """,
                (tag, chat_id)
            )

            row = await cursor.fetchone()

            if not row:
                continue

            tag_id = row[0]

            # получаем пользователей
            cursor = await db.execute(
                """
                SELECT user_id, username
                FROM tag_users
                WHERE tag_id = ?
                """,
                (tag_id,)
            )

            users = await cursor.fetchall()

            if not users:
                continue

            mentions = []

            for user_id, username in users:

                if username:
                    mentions.append(f"@{username}")
                else:
                    mentions.append(
                        f"<a href='tg://user?id={user_id}'>user</a>"
                    )

            # Telegram лимит 4096
            chunk = ""
            for m in mentions:

                if len(chunk) + len(m) + 1 > 4000:
                    await message.reply(chunk)
                    chunk = ""

                chunk += m + " "

            if chunk:
                await message.reply(chunk)
