import json, uuid

from aiogram import Router, F
from aiogram.types import LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.models import CustomMessage, CustomCallbackQuery
from bot.database import InvoicesDatabase, PromoDatabase, UserDatabase, ReferalDatabase, SmsOrdersDatabase
from bot.states import Deposit, TransferBalance, Promo
from bot.api.payments import CalculatorAsset
from bot.utils import * 


router = Router()

global_asset = "USDT" # change????
back_to_menu = ['common', 'back', 'buttons']
cancel_buttons = ['common', 'cancel', 'buttons']


async def payment_error_type_checker(message: CustomMessage, state: FSMContext, delete_message: bool = True) -> bool | float: 
    # в будущем перенести всю функцию в bot/utils/payment.py 
    state_data = await state.get_data()
    amount = message.text 

    if delete_message:
        try:
            await message.bot.delete_message(
                message.chat.id, 
                state_data['back_message_id']
            )
        except:
            pass 
    
    if not amount.isnumeric():
        await message.answer(
            text=message.bot.textgen.get(
                'errors', 'not_numeric', 'text'
            ), reply_markup=message.bot.textgen.generate_inline_markup(
                *cancel_buttons, cancel_type="choose_payment_type"
            )
        )
        await state.clear()
        return False 
    
    return float(amount)


# F.data.in_(['deposit', 'back|deposit']) - запомнить так делать в будущем 
@router.callback_query(F.data == 'deposit')
async def new_deposit_handler(call: CustomCallbackQuery):
    choose_payment_method = ['action', 'choose_payment_type']

    await call.answer()
    await call.message.edit_text(
        text=call.bot.textgen.get(
            *choose_payment_method, 'text'
        ), reply_markup=call.bot.textgen.generate_inline_markup(
            *choose_payment_method, 'buttons', 
            skip_list=['new_payment_stars'] if not call.bot.config.tg_stars_enabled else [],
            additional_keys=back_to_menu,
            additional_custom={"back_type": "profile"}
        )
    )


@router.callback_query(F.data == 'activate_promo')
async def activate_promo_handler(call: CustomCallbackQuery, state: FSMContext):
    _message = await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'promo', 'text'
        ), reply_markup=call.bot.textgen.generate_inline_markup(
            *cancel_buttons, cancel_type="profile"
        )
    )
    await state.set_state(Promo.wait)
    await state.set_data({"message_id": _message.message_id})


@router.message(StateFilter(Promo.wait))
async def promocode_entered_handler(message: CustomMessage, state: FSMContext):
    state_data = await state.get_data()
    result = PromoDatabase(message.from_user.id).activate_promo(message.text)
    user_db = UserDatabase(message.from_user.id)

    await message.reply('✅' if result[0] else '❌' + f' <b>{result[1]}</b>')
    await message.bot.delete_message(message.chat.id, state_data['message_id'])
    
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



@router.callback_query(F.data == 'new_payment_cryptobot')
async def new_crypto_bot_payment(call: CustomCallbackQuery, state: FSMContext):
    _message = await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'cryptobot_new_payment', 'text',
            payment_type='CryptoBot', rate_usdt_rub=call.bot.config.cryptobot_usdt_rub_rate
        ), reply_markup=call.bot.textgen.generate_inline_markup(
            *cancel_buttons, cancel_type="choose_payment_type"
        )
    )
    await state.set_state(Deposit.new_cryptobot)
    await state.set_data({
        "back_message_id": _message.message_id
    })


@router.message(StateFilter(Deposit.new_cryptobot))
async def crypto_bot_order_created(message: CustomMessage, state: FSMContext):
    amount = await payment_error_type_checker(message, state)

    if not amount:
        return  
    
    result = await message.bot.crypto_bot.create_invoice(
        global_asset, CalculatorAsset.convert_to_crypto(
            amount, message.bot.config.cryptobot_usdt_rub_rate
        )
    )
    if not result:
        return await message.answer(
            text=message.bot.textgen.get(
                'errors', 'payment_provider_error', 'text'
            ), reply_markup=message.bot.textgen.generate_inline_markup(
                *cancel_buttons, cancel_type="choose_payment_type"
            )
        ) 
    
    _message = await message.answer(
        text=message.bot.textgen.get(
            'action', 'new_payment_created', 'text', 
            payment_timeout=message.bot.config.payment_timeout_minutes
        ), reply_markup=message.bot.textgen.generate_inline_markup(
            'action', 'new_payment_created', 'buttons', to_pay_url=result['mini_app_invoice_url']
        )
    )
    InvoicesDatabase(message.from_user.id).create_new_invoice(
        str(result['invoice_id']), "crypto_bot", _message.message_id
    )
    await state.clear()


@router.callback_query(F.data == 'new_payment_stars')
async def new_telegram_stars_invoice(call: CustomCallbackQuery, state: FSMContext):
    _message = await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'stars_new_payment', 'text', 
            payment_type='Telegram Stars', 
            stars=call.bot.config.tg_stars_star_rub_rate['stars'],
            rub=call.bot.config.tg_stars_star_rub_rate['rub'],
       ), reply_markup=call.bot.textgen.generate_inline_markup(
           *cancel_buttons, cancel_type="choose_payment_type"
       )
    )
    await state.set_state(Deposit.new_stars)
    await state.set_data({
       "back_message_id": _message.message_id
    })


@router.message(StateFilter(Deposit.new_stars))
async def create_payment_stars(message: CustomMessage, state: FSMContext):
    amount = await payment_error_type_checker(message, state, delete_message=False)
    invoice_buttons = ['common', 'invoice']

    if not amount:
        return
    
    ivoice_uuid = str(uuid.uuid4())
    stars_amount = CalculatorAsset.convert_to_stars(
        amount, rate=message.bot.config.tg_stars_star_rub_rate
    )

    if stars_amount > message.bot.config.tg_stars_max:
        return await message.answer(
            message.bot.textgen.get(
                'errors', 'max_amount_error', 'text',
                max_amount=message.bot.config.tg_stars_max
            )
        )
    
    _message = await message.answer_invoice(
        title=message.bot.textgen.get(*invoice_buttons, 'title', service_name=message.bot.config.service_name), 
        description=message.bot.textgen.get(*invoice_buttons, 'description', amount=stars_amount),
        prices=[
            LabeledPrice(label='XTR', amount=stars_amount)
        ], 
        provider_token='',
        payload=json.dumps({
            "invoice_id": ivoice_uuid,
            "amount_rub": amount,
        }),
        currency="XTR",
        reply_markup=message.bot.textgen.generate_inline_markup(
            *invoice_buttons, 'buttons', amount=stars_amount,
            additional_keys=cancel_buttons,
            additional_custom={"cancel_type": "choose_payment_type__answer"}
       )
    )
    InvoicesDatabase(message.from_user.id).create_new_invoice(
        ivoice_uuid, 'stars', _message.message_id
    )
    await state.clear()


@router.pre_checkout_query()
async def on_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(
        ok=InvoicesDatabase(pre_checkout_query.from_user.id).validate_payment(
            json.loads(pre_checkout_query.invoice_payload)
        )
    )


@router.message(F.successful_payment)
async def on_successful_stars_payment(message: CustomMessage):
    invoice_data = json.loads(message.successful_payment.invoice_payload)

    user_db = InvoicesDatabase(message.from_user.id)
    user_db.success_invoice(invoice_data['invoice_id'], invoice_data['amount_rub'])

    ref_owner = ReferalDatabase.get_referal_owner(message.from_user.id)
    if ref_owner:
        ReferalDatabase.process_referal_payment(ref_owner, invoice_data['amount_rub'], message.bot.config.referal_fee)

    try:
        await message.bot.delete_message(
            message.chat.id, user_db.get_invoice_payment_message(invoice_data['invoice_id'])
        )
    except:
        pass 

    await message.answer(
        message.bot.textgen.get(
            'common', 'success_pay', 'text', 
            amount=invoice_data['amount_rub']
        ), reply_markup=message.bot.textgen.generate_keyboard_markup(
            'action', 'start', 'buttons'
        ), message_effect_id=message.bot.config.success_payment_reaction_id
    )


@router.callback_query(F.data == 'transfer_balance')
async def transfer_balance_handler(call: CustomCallbackQuery, state: FSMContext):
    _message = await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'transfer_balance', 'username', 'text'
        ), reply_markup=call.bot.textgen.generate_inline_markup(
           *cancel_buttons, cancel_type="profile"
       )
    )
    await state.set_state(TransferBalance.username)
    await state.set_data({"back_message": _message.message_id})


@router.message(StateFilter(TransferBalance.username))
async def get_username_for_transfer(message: CustomMessage, state: FSMContext):
    username = message.text.replace('@', '')
    state_data = await state.get_data()

    try:
        await message.bot.edit_message_reply_markup(
            chat_id=message.chat.id, message_id=state_data['back_message'],
            reply_markup=message.bot.textgen.empty_markup('inline')
        )
    except:
        pass 

    if username == message.from_user.username:
        return await message.answer(
            message.bot.textgen.get('errors', 'self_transfer', 'text'), 
            reply_markup=message.bot.textgen.generate_inline_markup(
                *cancel_buttons, cancel_type="profile"
            )
        ) 
    
    to_user = UserDatabase.get_user_id_by_username(username)

    if not to_user:
        return await message.answer(
            message.bot.textgen.get('errors', 'not_found_username', 'text'),
            reply_markup=message.bot.textgen.generate_inline_markup(
                *cancel_buttons, cancel_type="profile"
            )
        ) 
    
    await message.answer(
        text=message.bot.textgen.get(
            'action', 'transfer_balance', 'amount', 'text',
            amount=UserDatabase(message.from_user.id).user.balance
        ), reply_markup=message.bot.textgen.generate_inline_markup(
           *cancel_buttons, cancel_type="profile"
       )
    )

    await state.set_state(TransferBalance.amount)
    await state.set_data({"to": to_user.id, "to_username": username})


@router.message(StateFilter(TransferBalance.amount))
async def complete_transfer(message: CustomMessage, state: FSMContext):
    amount = message.text
    state_data = await state.get_data()
    
    if not amount.isdigit():
        return await message.answer(
            message.bot.textgen.get('errors', 'not_numeric', 'text'),
            reply_markup=message.bot.textgen.generate_inline_markup(
                *cancel_buttons, cancel_type="profile"
            )
        )
    
    amount = int(amount)

    if not UserDatabase(message.from_user.id).check_balance_available(amount):
        return await message.answer(
            message.bot.textgen.get('errors', 'insufficient_funds', 'text'),
            reply_markup=message.bot.textgen.generate_inline_markup(
                *cancel_buttons, cancel_type="profile"
            )
        )
    
    UserDatabase.transfer_balance(
        message.from_user.id, state_data['to'], amount
    )
    try:
        await message.bot.send_message(
            state_data['to'], text=message.bot.textgen.get(
                'action', 'transfer_balance', 'success_to', 'text',
                username=message.from_user.username, amount=amount
            )
        )
    except:
        pass 

    await message.answer(
        text=message.bot.textgen.get(
            'action', 'transfer_balance', 'success_from', 'text',
            username=state_data['to_username'], amount=amount, 
            balance=UserDatabase(message.from_user.id).user.balance,
        ), reply_markup=message.bot.textgen.generate_keyboard_markup(
            'action', 'start', 'buttons'
        )
    )

    await state.clear()


@router.callback_query(F.data == 'ref_menu')
async def referals_handler(call: CustomCallbackQuery):
    referal_url = generate_referal_url(call.bot.bot_username, call.from_user.id)
    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'referal', 'text',
            count_invited=ReferalDatabase.get_referals_count(call.from_user.id),
            percent=int(call.bot.config.referal_fee * 100), ref_url=referal_url,
            earned_amount=ReferalDatabase.get_all_referal_earned(call.from_user.id)
        ), reply_markup=call.bot.textgen.generate_inline_markup(
            'action', 'referal', 'buttons', 
            ref_tg_url=generate_referal_button_url(referal_url),
            additional_keys=back_to_menu,
            additional_custom={"back_type": "profile"}
        )
    )


@router.callback_query(F.data.startswith('activation_history'))
async def get_activation_history_handler(call: CustomCallbackQuery):
    activation_history = SmsOrdersDatabase(call.from_user.id).get_all_user_orders()

    buttons = generate_activation_history_buttons(call.bot.textgen, activation_history)
    buttons.extend(
        [call.bot.textgen.get(*back_to_menu, back_type='profile')]
    )

    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'activation_history', 'text'
        ), reply_markup=call.bot.textgen.generate_inline_markup_object(buttons)
    )


@router.callback_query(F.data.startswith('get-order-info'))
async def get_order_info(call: CustomCallbackQuery):
    order_id = int(call.data.split('_')[-1])
    order = SmsOrdersDatabase.get_order(order_id)
    castom_country_data = lambda arg: call.bot.textgen.get(*FLAG_PATH, str(order.coutry_id), arg)

    await call.message.edit_text(
        text=call.bot.textgen.get(
            'action', 'activation_info', 'text',
            datetime_data=order.create_time.strftime("%d %B %Y, %H:%M:%S"),
            order_id=order.order_id,
            order_status=order.status.upper(),
            phone_number=order.phone,
            service_name=order.service_name,
            country_name=castom_country_data('flag') + ' ' + castom_country_data('name_ru'),
            price=order.price,
            order_timeout=call.bot.config.payment_timeout_minutes
        ), reply_markup=call.bot.textgen.generate_inline_markup(
            *back_to_menu, back_type="activation_history"
        )
    )