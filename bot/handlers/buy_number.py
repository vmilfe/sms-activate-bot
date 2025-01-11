from datetime import datetime

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.models import CustomMessage, CustomCallbackQuery
from bot.filters import TextGeneratorFilter
from bot.database import UserDatabase, SmsOrdersDatabase, FavoritesDatabase, RentDatabase
from bot.utils import generate_country_buttons, generate_service_buttons
from bot.states import BuyNumber, Rent

router = Router()
default_menu_buttons_path = ['action', 'start', 'buttons']



@router.message(TextGeneratorFilter('buy', *default_menu_buttons_path))
async def get_all_services(message: CustomMessage):
    services = await message.bot.sms_activate.get_all_services()
    buttons = generate_service_buttons(services['services'])

    await message.answer(
        text=message.bot.textgen.get(
            'action', 'select_service', 'text'
        ), 
        reply_markup=message.bot.textgen.generate_inline_markup_object(buttons)
    )

@router.callback_query(F.data.startswith("navigate_page_services_"))
async def change_service_page(callback: CustomCallbackQuery):
    page = int(callback.data.split('_')[-1])
    services = await callback.bot.sms_activate.get_all_services()
    buttons = generate_service_buttons(services['services'], page=page)

    await callback.message.edit_reply_markup(
        reply_markup=callback.bot.textgen.generate_inline_markup_object(buttons)
    )

@router.callback_query(F.data == "service_search")
async def start_service_search(callback: CustomCallbackQuery, state: FSMContext):
    _message = await callback.message.edit_text(
        text=callback.bot.textgen.get('action', 'service_search', 'text'),
        reply_markup=callback.bot.textgen.generate_inline_markup(
            'common', 'cancel', 'buttons',
            cancel_type='services'
        )
    )
    await state.set_state(BuyNumber.search)
    await state.set_data({"back_message": _message.message_id})


@router.message(BuyNumber.search)
async def process_service_search(message: CustomMessage, state: FSMContext):
    state_data = await state.get_data()

    try:
        await message.bot.delete_message( 
            message.chat.id, state_data['back_message']
        )
    except:
        pass 

    search_query = message.text.lower()
    countries = await message.bot.sms_activate.get_all_services()
    
    # Фильтруем страны по поисковому запросу
    filtered_countries = [
        item for item in countries['services'] if search_query in item['name'].lower()
    ]
    
    buttons = generate_service_buttons(filtered_countries)
    
    await message.answer(
        text=message.bot.textgen.get('action', 'select_service', 'text'),
        reply_markup=message.bot.textgen.generate_inline_markup_object(buttons)
    )
    await state.clear()


@router.callback_query(F.data.startswith("select-service_"))
async def get_all_countries_handler(call: CustomCallbackQuery):
    call_data = call.data.split('_')

    service_code = call_data[-1]
    service_name = call_data[-2]

    countries = await call.bot.sms_activate.get_top_countries_by_service(service_code)

    buttons = generate_country_buttons(call.bot.textgen, call.bot.config.service_fee, service_code, service_name, countries)
    buttons.extend(
        [call.bot.textgen.get('common', 'back', 'buttons', back_type='get_services')]
    )

    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'select_country', 'text', service_name=service_name
        ), reply_markup=call.bot.textgen.generate_inline_markup_object(buttons)
    )


@router.callback_query(F.data.startswith('navigate-page'))
async def update_page_countries_handler(call: CustomCallbackQuery):
    call_data = call.data.split('_')
    page, service_code, service_name = int(call_data[-1]), call_data[-3], call_data[-2]

    countries = await call.bot.sms_activate.get_top_countries_by_service(service_code)
    buttons = generate_country_buttons(call.bot.textgen, call.bot.config.service_fee, service_code, service_name, countries, page=page)
    buttons.extend(
        [call.bot.textgen.get('common', 'back', 'buttons', back_type='get_services')]
    )

    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'select_country', 'text', service_name=service_name
        ), reply_markup=call.bot.textgen.generate_inline_markup_object(buttons)
    )


@router.callback_query(F.data.startswith('country-search'))
async def search_country_handler(call: CustomCallbackQuery, state: FSMContext):
    call_data = call.data.split('_')
    service_code = call_data[-1]
    service_name = call_data[-2]

    _message = await call.message.edit_text(
        text=call.bot.textgen.get('action', 'country_search', 'text'),
        reply_markup=call.bot.textgen.generate_inline_markup(
            'common', 'cancel', 'buttons',
            cancel_type='services'
        )
    )
    await state.set_state(BuyNumber.search_country)
    await state.set_data({
        "back_message": _message.message_id, 
        "service_code": service_code,
        "service_name": service_name
    })


@router.message(BuyNumber.search_country)
async def process_country_search(message: CustomMessage, state: FSMContext):
    state_data = await state.get_data()

    try:
        await message.bot.delete_message( 
            message.chat.id, state_data['back_message']
        )
    except:
        pass 

    search_query = message.text.lower()
    countries = await message.bot.sms_activate.get_top_countries_by_service(state_data['service_code'])

    buttons = generate_country_buttons(message.bot.textgen, message.bot.config.service_fee, state_data['service_code'], state_data['service_name'], countries, search=search_query)
    buttons.extend(
        [message.bot.textgen.get('common', 'back', 'buttons', back_type='get_services')]
    )

    await message.answer(
        text=message.bot.textgen.get(
            'action', 'select_country', 'text', service_name=state_data['service_name']
        ), reply_markup=message.bot.textgen.generate_inline_markup_object(buttons)
    )
    await state.clear()


@router.callback_query(F.data.startswith('try-create-sms'))
async def try_to_create_sms(call: CustomCallbackQuery):
    args = call.data.split('_')
    args.pop(0)

    service_name, service_code, country_id, price = args
    price = float(price)
    
    await call.message.edit_text(
        text=call.bot.textgen.get('action', 'buy_selector', 'text'),
        reply_markup=call.bot.textgen.generate_inline_markup(
            'action', 'buy_selector', 'buttons',
            service_name=service_name,
            service_code=service_code,
            country_id=country_id,
            calculated_amount=price
        )
    )

@router.callback_query(F.data.startswith('create-rent'))
async def create_rent_number(call: CustomCallbackQuery, state: FSMContext):
    args = call.data.replace('create-rent_', '').split('_')
    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'rent_hours', 'text'
        ), reply_markup=(
            call.bot.textgen.generate_inline_markup(
                'common', 'cancel', 'buttons',
                cancel_type='buy_number'
            )
        )
    )
    await state.set_state(Rent.hours)
    await state.set_data({
        "service_name": args[0], "service": args[1], "country_id": args[2]
    })

@router.message(Rent.hours, )
async def process_rent_hours(message: CustomMessage, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer(
            text=message.bot.textgen.get('errors', 'not_numeric', 'text'),
            reply_markup=message.bot.textgen.generate_inline_markup(
                'common', 'cancel', 'buttons',
                cancel_type='buy_number'
            )
        )
    
    hours = int(message.text)
    if hours < 4 or hours > 720:
        return await message.answer(
            text=message.bot.textgen.get('errors', 'rent_hours_invalid', 'text'),
            reply_markup=message.bot.textgen.generate_inline_markup(
                'common', 'cancel', 'buttons', 
                cancel_type='buy_number'
            )
        )

    state_data = await state.get_data()
    country_id = state_data.get('country_id')

    response = await message.bot.sms_activate.get_rent_price(state_data['service'], country_id, hours)
    price = response['services'][state_data['service']]['cost'] * hours

    flag = message.bot.textgen.get('flags', country_id, "flag")
    country_name = message.bot.textgen.get('flags', country_id, "name_ru")
    
    await message.answer(
        text=message.bot.textgen.get(
            'action', 'rent_confirmation', 'text',
            country_name=country_name,
            country_flag=flag,
            hours=hours,
            amount=price 
        ),
        reply_markup=message.bot.textgen.generate_inline_markup(
            'action', 'rent_confirmation', 'buttons',
            service=state_data['service'],
            country_id=country_id,
            hours=hours
        )
    )

@router.callback_query(F.data.startswith('confirm-rent'), StateFilter(Rent.hours))
async def rent_created(call: CustomCallbackQuery, state: FSMContext):
    _, service, country_id, hours = call.data.split('_')
    hours = int(hours)

    user_db = UserDatabase(call.from_user.id)
    response = await call.bot.sms_activate.get_rent_price(service, int(country_id), hours)
    price = response['services'][service]['cost'] * hours

    if not user_db.check_balance_available(price):
        return await call.answer(
            text=call.bot.textgen.get('errors', 'insufficient_funds_sms', 'text'),
            show_alert=True
        )

    number_data = await call.bot.sms_activate.rent_number(
        service, hours, int(country_id)
    )

    if not number_data:
        return await call.answer(
            text=call.bot.textgen.get('errors', 'number_not_available', 'text'),
            show_alert=True
        )

    # Списываем баланс
    UserDatabase.transfer_balance(
        call.from_user.id,
        0,  # system
        price
    )

    flag = call.bot.textgen.get('flags', country_id, "flag")
    country_name = call.bot.textgen.get('flags', country_id, "name_ru")

    expires_at = datetime.strptime(number_data['endDate'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')

    RentDatabase(call.from_user.id).create_rent_order(
        number_data['id'],
        number_data['number'], 
        datetime.strptime(number_data['endDate'], '%Y-%m-%d %H:%M:%S'),  # Исправленный формат
        price
    )

    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'rent_success', 'text',
            phone=number_data['number'],
            country_flag=flag,
            country_name=country_name,
            expires_at=expires_at
        )
    )
    await state.clear()


@router.callback_query(F.data.startswith('add-service'))
async def fuck_answer(call: CustomCallbackQuery):
    await call.answer(
        'В разработке, почти готово, скоро будет подключено', show_alert=True
    )


@router.callback_query(F.data.startswith('create-sms'))
async def create_new_sms_invoice(call: CustomCallbackQuery):
    args = call.data.split('_')
    args.pop(0)

    service_name, service_code, country_id, price = args
    price = float(price)

    if not UserDatabase(call.from_user.id).check_balance_available(price):
        return await call.answer(
            text=call.bot.textgen.get('errors', 'insufficient_funds_sms', 'text'),
            show_alert=True
        )
    
    number_data = await call.bot.sms_activate.get_number(
        service_code, int(country_id)
    )
    
    if not number_data:
        return await call.answer(
            text=call.bot.textgen.get('errors', 'number_not_available', 'text'),
            show_alert=True
        )

    # Списываем баланс
    UserDatabase.transfer_balance(
        call.from_user.id,
        0,  # system
        price
    )

    # Создаем заказ в БД
    SmsOrdersDatabase(call.from_user.id).create_order(
        order_id=number_data['id'],
        phone=number_data['phone'],
        service=service_code,
        service_name=service_name,
        coutry_id=int(country_id),
        price=price
    )

    await call.message.edit_text(
        text=call.bot.textgen.get(
            'common', 'success_invoice_sms', 'text',
            phone_number=number_data['phone']
        ),
        reply_markup=call.bot.textgen.generate_inline_markup(
            'common', 'success_invoice_sms', 'buttons',
            additional_keys=['common', 'success_invoice_sms', 'additional', 'add'],
            additional_custom={"order_id": number_data['id']},
            order_id=number_data['id']
        )
    )

@router.callback_query(F.data.startswith('cancel_sms_'))
async def cancel_sms_order(call: CustomCallbackQuery):
    order_id = int(call.data.replace('__newline','').split('_')[-1])
    order = SmsOrdersDatabase.get_order(order_id)
    timeout = (datetime.now() - order.create_time).total_seconds() 

    # не забыть убрать
    if timeout < 120: 
        return  await call.message.answer(
            text=call.bot.textgen.get('errors', 'order_timeout_wait', 'text', timout=str(round(120 - timeout, 2))),
            show_alert=True
        )
    
    if not order or order.user_id != call.from_user.id:
        return await call.answer(
            text=call.bot.textgen.get('errors', 'order_not_found', 'text'),
            show_alert=True
        )
    
    if order.status != 'active':
        return await call.answer(
            text=call.bot.textgen.get('errors', 'order_already_cancelled', 'text'),
            show_alert=True
        )
    
    # Отменяем активацию в API
    await call.bot.sms_activate.set_status(str(order_id), 8)
    
    # Возвращаем деньги
    UserDatabase.transfer_balance(
        0, # system
        call.from_user.id,
        order.price
    )
    
    # Отмечаем заказ как отмененный
    SmsOrdersDatabase.cancel_order(order_id)
    
    await call.message.edit_text(
        text=call.bot.textgen.get('common', 'order_cancelled', 'text')
    )

@router.callback_query(F.data.startswith('resend_sms_'))
async def resend_sms_code(call: CustomCallbackQuery):
    order_id = int(call.data.replace('__newline','').split('_')[-1])
    order = SmsOrdersDatabase.get_order(order_id)
    
    if not order or order.user_id != call.from_user.id:
        return await call.answer(
            text=call.bot.textgen.get('errors', 'order_not_found', 'text'),
            show_alert=True
        )
    
    if order.status != 'active':
        return await call.answer(
            text=call.bot.textgen.get('errors', 'order_expired', 'text'),
            show_alert=True
        )
    
    # Запрашиваем повторную отправку SMS
    await call.bot.sms_activate.set_status(str(order_id), 6)
    
    await call.answer(
        text=call.bot.textgen.get('common', 'sms_resent', 'text'),
        show_alert=True
    )


@router.callback_query(F.data.startswith('favorites_'))
async def add_order_to_favorites(call: CustomCallbackQuery):
    order_id = int(call.data.replace('__newline','').split('_')[-1])
    order = SmsOrdersDatabase.get_order(order_id)

    favorite_id = FavoritesDatabase(call.from_user.id).create_new_favorite(
        order.service, order.service_name, int(order.coutry_id)
    )
    
    await call.message.edit_text(
        text=call.bot.textgen.get(
            'common', 'success_invoice_sms', 'text',
            phone_number=order.phone
        ),
        reply_markup=call.bot.textgen.generate_inline_markup(
            'common', 'success_invoice_sms', 'buttons',
            additional_keys=['common', 'success_invoice_sms', 'additional', 'remove'],
            additional_custom={"favorite_id": favorite_id, "order_id": order.order_id},
            order_id=order.order_id
        )
    )

@router.callback_query(F.data.startswith('remove_favorites_'))
async def add_order_to_favorites(call: CustomCallbackQuery):
    call_args = call.data.replace('__newline','').split('_')
    favorite_id, order_id  = map(int, [call_args[-1], call_args[-2]])


    order = SmsOrdersDatabase.get_order(order_id)
    FavoritesDatabase.delete_favorite(favorite_id)


    await call.message.edit_text(
        text=call.bot.textgen.get(
            'common', 'success_invoice_sms', 'text',
            phone_number=order.phone
        ),
        reply_markup=call.bot.textgen.generate_inline_markup(
            'common', 'success_invoice_sms', 'buttons',
            additional_keys=['common', 'success_invoice_sms', 'additional', 'add'],
            additional_custom={"order_id": order_id},
            order_id=order_id
        )
    )