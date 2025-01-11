import bot.handlers
import pkgutil, importlib
from structlog.typing import FilteringBoundLogger

from typing import List
from aiogram import Router


def get_all_routers(logger: FilteringBoundLogger) -> List[Router]:
    routers = []
    
    for module_info in pkgutil.iter_modules(bot.handlers.__path__):
        module = importlib.import_module(f"bot.handlers.{module_info.name}")
        if hasattr(module, 'router'):
            routers.append(module.router)
            logger.debug(f'Success load handler', handler=module_info.name)
            
    return routers
