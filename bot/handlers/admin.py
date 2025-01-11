from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models import CustomMessage, CustomCallbackQuery
from bot.database import PromoDatabase
from bot.filters import AdminFilter


router = Router()

class PromoStates(StatesGroup):
    waiting_code = State()
    waiting_activates = State()
    waiting_amount = State()


@router.message(Command('admin'))
async def admin_menu(message: CustomMessage):
    if not await AdminFilter(message.bot.config)(message):
        return
    

    await message.answer(
        text=message.bot.textgen.get('admin', 'menu', 'text'),
        reply_markup=message.bot.textgen.generate_inline_markup(
            'admin', 'menu', 'buttons'
        )
    )

@router.callback_query(F.data.in_(['admin', 'cancel|admin']))
async def admin_back_to_menu(call: CustomCallbackQuery, state: FSMContext):
    if not await AdminFilter(call.bot.config)(call):
        return
    
    await state.clear()
    await call.message.edit_text(
        text=call.bot.textgen.get('admin', 'menu', 'text'),
        reply_markup=call.bot.textgen.generate_inline_markup(
            'admin', 'menu', 'buttons'
        )
    )


@router.callback_query(F.data == "create_promo")
async def create_promo_start(call: CustomCallbackQuery, state: FSMContext):
    if not await AdminFilter(call.bot.config)(call):
        return
        
    await call.message.edit_text(
        text=call.bot.textgen.get('admin', 'promo_create', 'code'),
        reply_markup=call.bot.textgen.generate_inline_markup(
            'common', 'cancel', 'buttons',
            cancel_type='admin'
        )
    )
    await state.set_state(PromoStates.waiting_code)


@router.message(PromoStates.waiting_code)
async def promo_enter_code(message: CustomMessage, state: FSMContext):
    if not await AdminFilter(message.bot.config)(message):
        return
        
    await state.update_data(code=message.text)
    await message.answer(
        text=message.bot.textgen.get('admin', 'promo_create', 'activates'),
        reply_markup=message.bot.textgen.generate_inline_markup(
            'common', 'cancel', 'buttons',
            cancel_type='admin'
        )
    )
    await state.set_state(PromoStates.waiting_activates)


@router.message(PromoStates.waiting_activates)
async def promo_enter_activates(message: CustomMessage, state: FSMContext):
    if not await AdminFilter(message.bot.config)(message):
        return
        
    if not message.text.isdigit():
        return await message.answer(
            text=message.bot.textgen.get('errors', 'not_numeric', 'text')
        )
        
    await state.update_data(activates=int(message.text))
    await message.answer(
        text=message.bot.textgen.get('admin', 'promo_create', 'amount'),
        reply_markup=message.bot.textgen.generate_inline_markup(
            'common', 'cancel', 'buttons',
            cancel_type='admin'
        )
    )
    await state.set_state(PromoStates.waiting_amount)


@router.message(PromoStates.waiting_amount)
async def promo_enter_amount(message: CustomMessage, state: FSMContext):
    if not await AdminFilter(message.bot.config)(message):
        return
        
    if not message.text.isdigit():
        return await message.answer(
            text=message.bot.textgen.get('errors', 'not_numeric', 'text')
        )
        
    data = await state.get_data()
    await state.clear()
    
    promo = PromoDatabase.create_promo(
        code=data['code'],
        activates=data['activates'],
        amount=int(message.text)
    )
    
    await message.answer(
        text=message.bot.textgen.get(
            'admin', 'promo_created', 'text',
            code=promo.code,
            activates=promo.activates,
            amount=promo.amount
        ),
        reply_markup=message.bot.textgen.generate_inline_markup(
            'admin', 'menu', 'buttons'
        )
    )


@router.callback_query(F.data == "list_promos")
async def list_promos(call: CustomCallbackQuery):
    if not await AdminFilter(call.bot.config)(call):
        return
        
    promos = PromoDatabase.get_all_promos()
    
    await call.message.edit_text(
        text=call.bot.textgen.get(
            'admin', 'promo_list', 'text',
            promos="\n".join([
                f"- Код: {p.code} | Активаций: {p.activates} | Сумма: {p.amount}₽ | Удалить: /delete_{p.id} "
                for p in promos
            ]) if promos else "Нет активных промокодов"
        ),
        reply_markup=call.bot.textgen.generate_inline_markup(
            'admin', 'promo_list', 'buttons'
        )
    )


@router.message(F.text.startswith("/delete_"))
async def delete_promo(message: CustomMessage):
    if not await AdminFilter(message.bot.config)(message):
        return
        
    promo_code = int(message.text.split('_')[1])

    if PromoDatabase.delete_promo(promo_code):
        await message.reply("Промокод успешно удален")
    else:
        await message.reply("Промокод не найден")


@router.callback_query(F.data == 'close')
async def _close_handler(call: CustomCallbackQuery):
    await call.message.delete()