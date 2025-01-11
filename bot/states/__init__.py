from aiogram.fsm.state import StatesGroup, State


class Deposit(StatesGroup):
    new_cryptobot = State()
    new_stars = State()

class TransferBalance(StatesGroup):
    username = State()
    amount = State()

class BuyNumber(StatesGroup):
    search = State()
    search_country = State()

class Promo(StatesGroup):
    wait = State()


class Rent(StatesGroup):
    hours = State()