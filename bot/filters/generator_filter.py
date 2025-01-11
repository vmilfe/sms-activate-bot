from aiogram.filters import BaseFilter
from bot.models import CustomMessage


class TextGeneratorFilter(BaseFilter):  
    def __init__(self, button_id: str, *path): 
        self.button_id = button_id
        self.path = path

    async def __call__(self, message: CustomMessage) -> bool: 
        return message.text == message.bot.textgen.get_text_button_by_id(
            self.button_id, *self.path
        )