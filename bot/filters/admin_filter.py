from aiogram.filters import BaseFilter
from bot.models import CustomMessage, CustomCallbackQuery
from typing import Union


class AdminFilter(BaseFilter):  
    def __init__(self, config): 
        self.admin_ids = config.admin_id

    async def __call__(self, event: Union[CustomMessage, CustomCallbackQuery]) -> bool: 
        return event.from_user.id in self.admin_ids