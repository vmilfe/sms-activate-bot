################################################
#                                              #
#      Bot created 15.11.2024-29.11.2024       #
#                 by t.me/awixa                #
#                                              #
################################################

import asyncio, config, locale
import structlog, sys


from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config.generator import TextGenerator

from bot.handlers import get_all_routers
from bot.database import GlobalDatabase
from bot.api import SMSActivateAPI, CryptoBotAPI, check_all_payments_system


async def default_info(bot: Bot):
    me = await bot.get_me()
    database_init = GlobalDatabase.create_tables()
    bot.bot_username = me.username

    bot.logger.info(f'⚙️ [v{bot.config.version}] created by t.me/awixa')
    bot.logger.info(f'Starting bot: @{me.username}')

    if not database_init:
        bot.logger.debug('Use actual database')
    else:
        bot.logger.debug('Created new tables', tables=database_init)
    
    if await check_all_payments_system(
        bot.logger, bot.config, bot.sms_activate, bot.crypto_bot
    ) == False:
        await bot.sms_activate.close()
        await bot.crypto_bot.close()
        await bot.session.close() 
        sys.exit(1)


async def main():
    locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8") # for russia datetime 

    _config = config.load_config()
    logger = structlog.get_logger()
    dp = Dispatcher()
    bot = Bot(token=_config.bot_token, default=DefaultBotProperties(
        parse_mode=_config.messages_parse_mode
    ))

    bot.textgen = TextGenerator(_config.messages_path)
    bot.sms_activate = SMSActivateAPI(_config.sms_activate_api_token, logger, bot)
    bot.crypto_bot = CryptoBotAPI(bot, _config, logger)
    bot.logger = logger
    bot.config = _config
    
    await default_info(bot)

    dp.include_routers(*get_all_routers(logger))
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())