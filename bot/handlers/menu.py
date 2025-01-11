from aiogram import Router

from bot.models import CustomMessage, CustomCallbackQuery
from bot.filters import TextGeneratorFilter
from bot.database import UserDatabase, FavoritesDatabase
from bot.utils import generate_favorites_buttons


router = Router()
default_menu_buttons_path = ['action', 'start', 'buttons'] # action/start/buttons


@router.message(TextGeneratorFilter(
    'profile', *default_menu_buttons_path
))
async def profile_handler(message: CustomMessage):
    user_db = UserDatabase(message.from_user.id)
    
    await message.answer(
        message.bot.textgen.get(
            'action', 'profile', 'text',
            username=message.from_user.username,
            user_id=message.from_user.id,
            balance=round(user_db.user.balance, 2)
        ), reply_markup=message.bot.textgen.generate_inline_markup(
            'action', 'profile', 'buttons'
        )
    )

@router.message(TextGeneratorFilter(
    'info', *default_menu_buttons_path
))
async def info_handler(message: CustomMessage):
    await message.answer(
        message.bot.textgen.get('action', 'info', 'text'),
        reply_markup=message.bot.textgen.generate_inline_markup(
            'action', 'info', 'buttons', 
            support_username=message.bot.config.support_username,
            redirect_channel=message.bot.config.support_redirect_channel
        )
    )

@router.message(TextGeneratorFilter(
    'favorites', *default_menu_buttons_path
))
async def favorites_handler(message: CustomMessage):
    favorites_list = generate_favorites_buttons(
        message.bot.textgen, 
        FavoritesDatabase(message.from_user.id).get_favorites_list()
    )
    await message.answer(
        text=message.bot.textgen.get('common', 'favorites_list', 'text'),
        reply_markup=message.bot.textgen.generate_inline_markup_object(favorites_list)
    )