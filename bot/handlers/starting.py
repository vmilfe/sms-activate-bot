from aiogram import Router 
from aiogram.filters import CommandStart

from bot.models import CustomMessage
from bot.middlewares import UserDatabaseMiddleware
from bot.database import ReferalDatabase
from bot.utils import get_user_from_start


router = Router()
router.message.outer_middleware.register(UserDatabaseMiddleware())


@router.message(CommandStart())
async def new_user_handler(message: CustomMessage):
    ref_user = get_user_from_start(message.text)
    if ref_user:
        try:
            ReferalDatabase.add_referal(ref_user, message.from_user.id)
        except Exception as unique_err:
            message.bot.logger.err(f"New referal err: {unique_err}")

    await message.answer(
        text=message.bot.textgen.get(
            'action', 'start', 'text', 
            full_name=message.from_user.full_name, 
            service_name=message.bot.config.service_name
        ), reply_markup=message.bot.textgen.generate_keyboard_markup(
            'action', 'start', 'buttons'
        )
    )