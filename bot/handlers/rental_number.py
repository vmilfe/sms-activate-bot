from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models import CustomMessage, CustomCallbackQuery
from bot.filters import TextGeneratorFilter
from bot.database import UserDatabase, RentDatabase
from bot.utils import generate_rent_countries_button
from bot.api.payments import CalculatorAsset


router = Router()
default_menu_buttons_path = ['action', 'start', 'buttons']


class RentStates(StatesGroup):
    waiting_hours = State()


@router.message(TextGeneratorFilter('rent', *default_menu_buttons_path))
async def rent_number(message: CustomMessage):
    return # наверное уберу эту функцию нахуй
    response = await message.bot.sms_activate.get_rent_price()

    buttons = generate_rent_countries_button(
        message.bot.textgen, response['countries']
    )

    await message.answer(
        text=message.bot.textgen.get('action', 'rent_service', 'text'),
        reply_markup=message.bot.textgen.generate_inline_markup_object(buttons)
    )

@router.callback_query(F.data.startswith('rent-countries-page'))
async def rend_numers_page_callback(call: CustomCallbackQuery):
    response = await call.bot.sms_activate.get_rent_price()

    buttons = generate_rent_countries_button(
        call.bot.textgen, response['countries'], page=int(call.data.split('_')[-1])
    )

    await call.message.edit_text(
        text=call.bot.textgen.get('action', 'rent_service', 'text'),
        reply_markup=call.bot.textgen.generate_inline_markup_object(buttons)
    )


@router.callback_query(F.data.startswith('rent-country'))
async def process_country_selection(call: CustomCallbackQuery, state: FSMContext):
    country_id = int(call.data.split('_')[-1])
    
    await state.set_state(RentStates.waiting_hours)
    await state.update_data(country_id=country_id)
    
    await call.message.edit_text(
        text=call.bot.textgen.get('action', 'rent_hours', 'text'),
        reply_markup=call.bot.textgen.generate_inline_markup(
            'common', 'cancel', 'buttons',
            cancel_type='rent'
        )
    )


@router.message(RentStates.waiting_hours)
async def process_hours_input(message: CustomMessage, state: FSMContext):
    try:
        hours = int(message.text)
        if hours < 4 or hours > 720:
            raise ValueError()
    except ValueError:
        return await message.answer(
            text=message.bot.textgen.get('errors', 'rent_hours_invalid', 'text')
        )

    state_data = await state.get_data()
    country_id = state_data['country_id']


    price = await message.bot.sms_activate.get_rent_price(
        country_id, hours
    )

    # Рассчитываем стоимость аренды
    amount = CalculatorAsset.conver_price_with_fee(
        price,
        message.bot.config.service_fee
    )
    
    # Проверяем баланс
    if not UserDatabase(message.from_user.id).check_balance_available(amount):
        await state.clear()
        return await message.answer(
            text=message.bot.textgen.get('errors', 'rent_insufficient_funds', 'text')
        )

    country_flag = message.bot.textgen.get('flags', str(country_id), 'flag')
    country_name = message.bot.textgen.get('flags', str(country_id), 'name_ru')

    await message.answer(
        text=message.bot.textgen.get(
            'action', 'rent_confirmation', 'text',
            country_flag=country_flag,
            country_name=country_name,
            hours=hours,
            amount=amount
        ),
        reply_markup=message.bot.textgen.generate_inline_markup(
            'action', 'rent_confirmation', 'buttons',
            country_id=country_id,
            hours=hours,
            amount=amount
        )
    )
    await state.clear()


@router.callback_query(F.data.startswith('confirm_rent_'))
async def confirm_rent(call: CustomCallbackQuery):
    _, _, country_id, hours, amount = call.data.split('_')
    hours = int(hours)
    amount = float(amount)
    
    # Получаем номер в аренду
    rent_response = await call.bot.sms_activate.rent_number(
        country_id=country_id,
        hours=hours
    )
    
    if not rent_response or 'phone' not in rent_response:
        return await call.answer(
            text=call.bot.textgen.get('errors', 'number_not_available', 'text'),
            show_alert=True
        )

    phone = rent_response['phone']
    expires_at = datetime.now() + timedelta(hours=hours)
    
    # Списываем баланс
    UserDatabase.transfer_balance(
        call.from_user.id,
        0,  # system
        amount
    )
    
    # Сохраняем в БД
    RentDatabase(call.from_user.id).create_rent_order(
        phone=phone,
        end_date=expires_at,
        price=amount,
        order_id=rent_response.get('id', 0)
    )

    country_flag = call.bot.textgen.get('flags', str(country_id), 'flag')
    country_name = call.bot.textgen.get('flags', str(country_id), 'name_ru')

    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'rent_success', 'text',
            phone=phone,
            country_flag=country_flag,
            country_name=country_name,
            expires_at=expires_at.strftime("%d.%m.%Y %H:%M")
        )
    )