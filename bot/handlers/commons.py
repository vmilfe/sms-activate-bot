from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.utils import generate_country_buttons, generate_favorites_buttons, generate_service_buttons
from bot.models import CustomMessage, CustomCallbackQuery
from bot.database import FavoritesDatabase, UserDatabase, SmsOrdersDatabase

from bot.utils import generate_activation_history_buttons


router = Router()


@router.callback_query(F.data.in_(['back|profile', 'back|profile__newline', 'cancel|profile']), StateFilter('*'))
async def back_to_profile(call: CustomCallbackQuery, state: FSMContext):
    user_db = UserDatabase(call.from_user.id)

    await state.clear()
    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'profile', 'text',
            username=call.from_user.username,
            user_id=call.from_user.id,
            balance=user_db.user.balance
        ), reply_markup=call.bot.textgen.generate_inline_markup(
            'action', 'profile', 'buttons'
        )
    )

@router.callback_query(F.data == 'cancel|buy_number', StateFilter('*'))
async def back_to_buy_number(call: CustomCallbackQuery, state: FSMContext):
    await state.clear()

    services = await call.bot.sms_activate.get_all_services()
    buttons = generate_service_buttons(services['services'])

    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'select_service', 'text'
        ), 
        reply_markup=call.bot.textgen.generate_inline_markup_object(buttons)
    )



@router.callback_query(F.data.in_(['cancel|services']), StateFilter('*'))
async def back_to_countries(call: CustomCallbackQuery):
    services = await call.bot.sms_activate.get_all_services()
    buttons = generate_service_buttons(services['services'])

    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'select_service', 'text'
        ), 
        reply_markup=call.bot.textgen.generate_inline_markup_object(buttons)
    )


@router.callback_query(F.data.startswith('cancel|choose_payment_type'), StateFilter('*'))
async def back_to_choose_payment(call: CustomCallbackQuery, state: FSMContext):
    choose_payment_method = ['action', 'choose_payment_type']
    await state.clear()
    
    if 'answer' in call.data:
        try:
            await call.message.delete()
        except:
            pass
        method = call.message.answer
    else:
        method = call.message.edit_text
    
    await method(
        text=call.bot.textgen.get(
            *choose_payment_method, 'text'
        ), reply_markup=call.bot.textgen.generate_inline_markup(
            *choose_payment_method, 'buttons', 
            skip_list=['new_payment_stars'] if not call.bot.config.tg_stars_enabled else [],
            additional_keys=['common', 'back', 'buttons'],
            additional_custom={"back_type": "profile"}
        )
    )


@router.callback_query(F.data.startswith('back|get_services'))
async def back_to_get_services(call: CustomCallbackQuery):
    services = await call.bot.sms_activate.get_all_services()
    buttons = generate_service_buttons(services['services'])

    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'select_service', 'text'
        ), 
        reply_markup=call.bot.textgen.generate_inline_markup_object(buttons)
    )


@router.callback_query(F.data.startswith('back|activation_history'))
async def back_to_activation_history(call: CustomCallbackQuery):
    activation_history = SmsOrdersDatabase(call.from_user.id).get_all_user_orders()

    buttons = generate_activation_history_buttons(call.bot.textgen, activation_history)
    buttons.extend(
        [call.bot.textgen.get('common', 'back', 'buttons', back_type='profile')]
    )

    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'activation_history', 'text'
        ), reply_markup=call.bot.textgen.generate_inline_markup_object(buttons)
    )


@router.callback_query(F.data.startswith('back|favorites'))
async def back_to_favorites(call: CustomCallbackQuery):
    favorites_list = generate_favorites_buttons(
        call.bot.textgen, 
        FavoritesDatabase(call.from_user.id).get_favorites_list()
    )
    await call.message.edit_text(
        text=call.bot.textgen.get('common', 'favorites_list', 'text'),
        reply_markup=call.bot.textgen.generate_inline_markup_object(favorites_list)
    )



@router.callback_query(F.data == 'answer')
async def answer_empty_data(call: CustomCallbackQuery):
    await call.answer()