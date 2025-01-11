import yaml
from typing import List, Dict, Union, Callable

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, \
                            InlineKeyboardMarkup, InlineKeyboardButton, \
                            WebAppInfo

class TextGenerator:
    def __init__(self, messages_yaml_path: str) -> None:
        self.auto_resize = True # for resize buttons in default ReplyKeyboardMarkup
        self.newline_code = '__newline'
        self.items_use_newline = ['id', 'url', 'callback']

        with open(messages_yaml_path, encoding='utf-8') as yaml_stream:
            self.result = yaml.safe_load(yaml_stream)
    
    def get(self, *keys: str, **custom_section: str) -> str | List[str] | List[Dict[str, str]]:
        '''
        Получает текст из yaml файла сообщений по ключам.

        Args:
            - *keys: Ключи для поиска в yaml
            - **custom_section: Параметры для форматирования текста

        Returns:
            - str: Отформатированный текст
        '''

        _current = self.result

        for key in keys:
            _current = _current[key]
        
        if isinstance(_current, list):
            _current = [
                self.__button_set_custom_keys(item, **custom_section)
                for item in _current
            ]
            return _current
        
        return _current.format(**custom_section) if custom_section else _current
    
    def get_text_button_by_id(self, _id: str, *keys: str) -> str | None:
        return next(
            (button['text'] for button in self.get(*keys) if button['id'].split('__')[0] == _id),
            None
        )
    
    def __button_use_newline(self, button: Dict[str, str]):
        return any([
            self.newline_code in button.get(item, '') 
            for item in self.items_use_newline
        ])

    def __button_remove_newline(self, button: Dict[str, str]) -> Dict[str, str]:
        button = button.copy() # fix remove neline in self.result!!
        for key in self.items_use_newline:
            if key in button:
                button[key] = button[key].replace(self.newline_code, '')
        return button
    
    def __button_set_custom_keys(self, button: Dict[str, str], **custom_keys: str) -> Dict[str, str]:
        button = button.copy()
        for key, value in button.items():
            if isinstance(value, str) and '{' in value and '}' in value:
                button[key] = value.format(**custom_keys)
        return button
    
    def _process_buttons(
            self, 
            buttons_data: List[Dict[str, str]], 
            button_factory: Callable[[Dict[str, str]], InlineKeyboardButton],
            skip_callbacks_list: List[str],
            **custom_keys: str
        ) -> List[Union[
            InlineKeyboardButton, KeyboardButton
    ]]: 
        '''
            method for create buttons 
            buttons_data: list[dict] from yaml 
            button_factory: function for return Button 
        '''

        keyboard = []
        current_row = []

        
        for button in buttons_data:
            if button.get('callback', '') in skip_callbacks_list:
                continue

            button = self.__button_set_custom_keys(button, **custom_keys)
            if self.__button_use_newline(button):
                if current_row:
                    keyboard.append(current_row)
                    current_row = []
                keyboard.append([button_factory(self.__button_remove_newline(button))])
            else:
                current_row.append(button_factory(button))
                if len(current_row) == 2:
                    keyboard.append(current_row)
                    current_row = []
        
        if current_row:
            keyboard.append(current_row)
            
        return keyboard

    def generate_keyboard_markup(self, *keys) -> ReplyKeyboardMarkup:
        '''
        Создание клавиатуры по пути из keys
        '''
        buttons_data = self.get(*keys)
        keyboard = self._process_buttons(
            buttons_data,
            lambda _: KeyboardButton(text=_['text']),
            skip_callbacks_list=[]
        )
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=self.auto_resize)
    

    def generate_inline_markup(
            self, 
            *keys: str, 
            skip_list: Union[List[str], None] = None,
            additional_keys: Union[List[str], None] = None,
            additional_custom: Union[Dict[str, str], None] = None,
            **custom_keys: str
        ) -> InlineKeyboardMarkup:
        '''
        using keys and custom_keys: 

        Args:
            *keys: последовательность строковых ключей для поиска в yaml файле
            skip_list: последовательность callback'ов которые надо пропустить 
            additional_keys: последовательных строковых ключей которые ведут к кнопкам дополнительным котоыре в конце добавятся
            **custom_keys: словарь с параметрами для форматирования текста кнопок 

        Returns:
            InlineKeyboardMarkup: Inline клавиатура

        Example:
            generate_inline_markup('buttons', 'main_menu', url='https://example.com', name='John')
        '''

        if skip_list is None:
            skip_list = []

        buttons_data = self.get(*keys, **custom_keys).copy() # fix problem change self.result!!!

        if additional_keys:
            if additional_custom is None:
                additional_custom = {}
            buttons_data.extend(self.get(*additional_keys, **additional_custom))
        else:
            additional_keys = []

        keyboard = self._process_buttons(
            buttons_data,
            lambda _: InlineKeyboardButton(
                text=_['text'], 
                callback_data=_['callback'] if 'callback' in _ else None, 
                web_app=WebAppInfo(url=_['webapp_url']) if 'webapp_url' in _ else None, 
                url=_['url'] if 'url' in _ else None,
                pay=_['pay'] if 'pay' in _ else None
             ), 
            skip_callbacks_list=skip_list,
            **custom_keys
        )
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def empty_markup(
        self, _type: str = 'inline'
    ) -> Union[InlineKeyboardMarkup, ReplyKeyboardMarkup]:
        '''
        create keyboard with type

        Args:
            type: тип клавиатуры ('inline' или 'reply')

        Returns:
            InlineKeyboardMarkup или ReplyKeyboardMarkup: пустая клавиатура
        '''
        if _type == 'inline':
            return InlineKeyboardMarkup(inline_keyboard=[])
        return ReplyKeyboardMarkup(keyboard=[], resize_keyboard=self.auto_resize)
    

    def generate_inline_markup_object(self, data: List[List[Dict[str, str]]]) -> InlineKeyboardMarkup:
        '''
        generate a keyboard markup from structured data.

        Args:
            data: a list of rows, each containing a list of button dictionaries.

        Example data:
            - [
                [
                    {'text': '🇷🇺 Россия', 'callback_data': 'select_country_0'}, 
                    {'text': '🇺🇦 Украина', 'callback_data': 'select_country_1'}
                ]
            ]
        
        Returns:
            InlineKeyboardMarkup: A fully constructed inline keyboard markup.
        '''
        keyboard = []
        
        for row in data:
            button_row = []
            for button_data in row:
                button_row.append(
                    InlineKeyboardButton(
                        text=button_data.get('text'),
                        callback_data=button_data.get('callback_data', None) or button_data.get('callback', None),
                        url=button_data.get('url', None),
                        web_app=WebAppInfo(url=button_data.get('webapp_url')) if 'webapp_url' in button_data else None,
                        pay=button_data.get('pay', None)
                    )
                )
            keyboard.append(button_row)
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
