from aiogram.utils.deep_linking import create_startgroup_link
from aiogram import F, Bot, Router
from  aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

bot_router = Router()

def get_main_menu_text_and_markup():
    text = ('Привет! Этот бот поможет тебе быстро упомянуть всех участников группы. Вот что он может:\n\n'
            '📋 Выбрать группу — выбери группу из списка уже добавленных для настройки.\n\n'
            '➕ Добавить бота — добавь меня в новый чат для работы.\n\n'
            'ℹ️ Поддержка — напиши в поддержку, если нужна помощь.\n\n'
            '💰 Донат — поддержи проект и помоги мне стать лучше!\n\n'
            'Нажми на кнопку ниже, чтобы выбрать действие!')
    buttons = [
        [InlineKeyboardButton(text='📋 Выбрать группу', callback_data='group_selection')],
        [InlineKeyboardButton(text='➕ Добавить бота', callback_data='add_bot')],
        [InlineKeyboardButton(text='ℹ️ Поддержка', callback_data='support'),
         InlineKeyboardButton(text='🔒 Донат', callback_data='donat')]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, markup

@bot_router.message(CommandStart())
async def start_function(message:Message):
    if not message.chat.type == 'private':
        return
    text, mark = get_main_menu_text_and_markup()
    await message.answer(text=text, reply_markup=mark)

@bot_router.callback_query(F.data == "add_bot")
async def add_bot(callback_query: CallbackQuery, bot: Bot):
    url = await create_startgroup_link(bot, payload='link')
    url += '&admin=post_messages+edit_messages'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="back_start")]])
    await callback_query.message.edit_text(
        f"Нажмите на [ссылку]({url}) для добавления бота в чат",
        reply_markup=keyboard,
        parse_mode='MarkdownV2')

@bot_router.callback_query(F.data == "back_start")
async def back_start(callback_query: CallbackQuery):
    if callback_query.message.chat.type != 'private':
        return
    text, mark = get_main_menu_text_and_markup()
    await callback_query.message.edit_text(text, reply_markup=mark)