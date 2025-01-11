from aiogram import Router, F

from bot.models import CustomCallbackQuery
from bot.database import FavoritesDatabase
from bot.api.payments import CalculatorAsset
from bot.utils import * 


router = Router()


@router.callback_query(F.data.startswith('get-favorite'))
async def get_favorite_action(call: CustomCallbackQuery):
    favorite_id = int(call.data.split('_')[-1])
    favorite_data = FavoritesDatabase.get_favorite_by_id(favorite_id)

    api_amount = await call.bot.sms_activate.get_price(favorite_data.service, favorite_data.country_id)
    amount = CalculatorAsset.conver_price_with_fee(api_amount, call.bot.config.service_fee)

    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'favorite_selector', 'text',
            country=call.bot.textgen.get(*FLAG_PATH, str(favorite_data.country_id), "name_ru"),
            service_name=favorite_data.service_name,
            amount=amount
        ), reply_markup=call.bot.textgen.generate_inline_markup(
            'action', 'favorite_selector', 'buttons',
            additional_keys=['common', 'back', 'buttons'],
            additional_custom={"back_type": "favorites"},
            favorite_id=favorite_data.id,
            service_name=favorite_data.service_name[:30],
            service_code=favorite_data.service,
            country_id=favorite_data.country_id,
            calculated_amount=amount
        )
    )

@router.callback_query(F.data.startswith('delete-sms-by-favorites'))
async def delete_favorites(call: CustomCallbackQuery):
    favorite_id = int(call.data.split('_')[-1])
    FavoritesDatabase.delete_favorite(favorite_id)

    favorites_list = generate_favorites_buttons(
        call.bot.textgen, 
        FavoritesDatabase(call.from_user.id).get_favorites_list()
    )
    await call.message.edit_text(
        text=call.bot.textgen.get('common', 'favorites_list', 'text'),
        reply_markup=call.bot.textgen.generate_inline_markup_object(favorites_list)
    )