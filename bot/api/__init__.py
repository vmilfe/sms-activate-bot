from structlog.typing import FilteringBoundLogger

from config.models import Config

from bot.api.sms_client.sms_activate import SMSActivateAPI
from bot.api.payments.crypto_bot import CryptoBotAPI


async def check_all_payments_system(logger: FilteringBoundLogger, config: Config, sms_activate: SMSActivateAPI, crypto_bot: CryptoBotAPI):
    sms_activate_balance = await sms_activate.get_balance(isinit=True)
    if sms_activate_balance is None:
        return False
    
    crypto_bot_balance = await crypto_bot.get_balance(isinit=True)
    if crypto_bot_balance is None:
        return False
    
    logger.info(f'✅ SMS: {sms_activate.global_name} balance: {sms_activate_balance}')

    logger.info(f'✅ PAYMENT: {crypto_bot.global_name} balance: {crypto_bot_balance}')

    if config.tg_stars_enabled:
        logger.info('✅ PAYMENT: Tg stars enable')
    else:
        logger.warn('❌ PAYMENT: Tg stars disable')