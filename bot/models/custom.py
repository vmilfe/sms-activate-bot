from aiogram.types import Message, CallbackQuery
from aiogram.client.bot import Bot

from structlog.typing import FilteringBoundLogger

from config.generator import TextGenerator
from config.models import Config

from bot.api import SMSActivateAPI
from bot.api.payments.crypto_bot import CryptoBotAPI


class CustomBot(Bot):
    textgen: TextGenerator
    logger: FilteringBoundLogger
    config: Config
    sms_activate: SMSActivateAPI
    crypto_bot: CryptoBotAPI
    bot_username: str


class CustomBotMixin:
    @property
    def bot(self) -> CustomBot:
        return super().bot


class CustomMessage(CustomBotMixin, Message):
    pass 
        

class CustomCallbackQuery(CustomBotMixin, CallbackQuery):
    pass