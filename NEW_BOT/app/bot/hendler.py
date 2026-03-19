import asyncio
import re
import aiosqlite
from aiogram import Router, Bot

from  aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

bot_router = Router()

@bot_router.message(CommandStart())
async def start_function(message:Message):
    measage = 'Привет! Этот бот поможет тебе быстро упомянуть всех участников гуппы. Вот что он может:\n\n' \
             '📋 Выбрать гуппу — выбери гуппу из списка уже добавленных для настройки.\n\n' \
             '➕ Добавить бота — добавь меня в новый чат для работы.\n\n' \
             'ℹ️ Поддержка — напиши в поддержку, если нужна помощь.\n\n' \
             '💰 Донат — поддержи проект и помоги мне стать лучше! \n\n' \
             'Нажми на кнопку ниже, чтобы выбрать действие!'
    buttons = [
        [InlineKeyboardButton(text='📋Выбрать гуппу', callback_data='group_selection')],
                                 [InlineKeyboardButton(text='➕Добавить бота', callback_data='add_bot')],
                                 [InlineKeyboardButton(text='ℹ️Поддержка', callback_data='suport'),
                                  InlineKeyboardButton(text='🔒Донат', callback_data='donat')]
    ]
    mark = InlineKeyboardMarkup(inline_keyboard = buttons)
    await message.answer(measage, reply_markup=mark)

@bot_router.message(Command('admins'))
async def info_chat(message:Message, bot:Bot):
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_list = "Список администраторов:\n\n"
    for admin in admins:
        user = admin.user
        status = "Создатель" if admin.status == 'creator' else "Администратор"
        admin_list += f"• {user.full_name} (@{user.username}) - {status}\n"
        if admin.custom_title:  # Если есть специальный титул
            admin_list += f"  Титул: {admin.custom_title}\n"

    await message.answer(admin_list)

