from typing import Dict, List

from bot.api.payments import CalculatorAsset
from bot.database import SmsOrder, Favorites
from config.generator import TextGenerator


ITEMS_PER_PAGE = 18
ITEMS_COLUMN = 2
FLAG_PATH = ['flags']


def generate_referal_url(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref-{user_id}"

def generate_referal_button_url(referal_url: str) -> str:
    return f"tg://msg_url?url={referal_url}"

def get_user_from_start(text: str) -> int | None:
    splited = text.split()

    if len(splited) == 2:
        arg_splited = splited[1].split('-')
        if arg_splited[0] == 'ref' and arg_splited[1].isdigit():
            return int(arg_splited[1])
        

def get_pages(countries: Dict, page: int = 1) -> tuple:
    _type_countries = False

    if hasattr(countries, "items"):
        items = list(countries.items())
        _type_countries = True
    else:
        items = [country for country in countries if country['code'] != 'full']
        
    total_pages = (len(items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    # Проверка валидности номера страницы
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    
    return (
        dict(items[start_idx:end_idx]) 
        if _type_countries == True 
        else items[start_idx:end_idx], 
        
        total_pages, page
    )


def generate_country_buttons(
        textgen: TextGenerator, 
        fee: float, 
        service_code: str, 
        service_name: str, 
        countries: Dict, 
        page: int = 1, 
        search: str | None = None
    ) -> List[Dict[str, str]]:
    """Генерирует кнопки со странами и навигацией."""
    buttons = []
    page_countries, total, current = get_pages(countries, page)

    service_name = service_name.replace('_', '')

    for _, country_data in page_countries.items():
        flag = textgen.get(*FLAG_PATH, str(country_data['country']), "flag")
        name = textgen.get(*FLAG_PATH, str(country_data['country']), "name_ru")
        name_en = textgen.get(*FLAG_PATH, str(country_data['country']), "name_en")
        calculated_amount = CalculatorAsset.conver_price_with_fee(country_data["price"], fee)

        if search and (search not in name.lower() and search not in name_en.lower()):
            continue

        buttons.append({
            'text': f"{flag} {name} ({calculated_amount}₽)",
            'callback_data': f'try-create-sms_{service_name[:30]}_{service_code}_{str(country_data["country"])}_{calculated_amount}'
        })
    
    # Разбиение кнопок на колонки
    columnized_buttons = [buttons[i:i + ITEMS_COLUMN] for i in range(0, len(buttons), ITEMS_COLUMN)]
    
    # Добавление статистики и поиска
    columnized_buttons.append([{
        'text': '🔍 Поиск',
        'callback_data': f'country-search_{service_name}_{service_code}'
    }])
    

    # Добавление кнопок навигации
    navigation_buttons = []
    if current > 1:
        navigation_buttons.append({
            'text': '⏪',
            'callback_data': f'navigate-page_{service_code}_{service_name}_{current - 1}'
        })
    navigation_buttons.append({
        'text': f'{page}/{total}',
        'callback_data': 'answer'
    })
    if current < total:
        navigation_buttons.append({
            'text': '⏩',
            'callback_data': f'navigate-page_{service_code}_{service_name}_{current + 1}'
        })
    if navigation_buttons:
        columnized_buttons.append(navigation_buttons)
    
    return columnized_buttons


def generate_service_buttons(services: List[Dict], page: int = 1) -> List[List[Dict[str, str]]]:
    """Генерирует кнопки с сервисами и навигацией."""
    buttons = []
    page_services, total, current = get_pages(services, page)

    for service in page_services:
        buttons.append({
            'text': service['name'],
            'callback_data': f'select-service_{service["name"]}_{service["code"]}'
        })
    
    # Разбиение кнопок на колонки
    columnized_buttons = [buttons[i:i + ITEMS_COLUMN] for i in range(0, len(buttons), ITEMS_COLUMN)]
    
    # Добавление поиска
    columnized_buttons.append([{
        'text': '🔍 Поиск',
        'callback_data': 'service_search'
    }])

    # Добавление кнопок навигации
    navigation_buttons = []
    if current > 1:
        navigation_buttons.append({
            'text': '⏪',
            'callback_data': f'navigate_page_services_{current - 1}'
        })
    navigation_buttons.append({
        'text': f'{current}/{total}',
        'callback_data': 'answer'
    })
    if current < total:
        navigation_buttons.append({
            'text': '⏩',
            'callback_data': f'navigate_page_services_{current + 1}'
        })
    if navigation_buttons:
        columnized_buttons.append(navigation_buttons)
    
    return columnized_buttons


def generate_activation_history_buttons(textgen: TextGenerator, history: List[SmsOrder]) -> List[Dict[str, str]]:
    buttons = []

    for order in history[:5]:
        country_name = textgen.get(*FLAG_PATH, str(order.coutry_id), "name_ru")

        if order.status == 'completed':
            status = '✅'
        elif order.status == 'active':
            status = '🔄'
        else:
            status = '❌'

        buttons.append([{
            "text": f"{order.service_name} [{country_name}] - {status}",
            "callback_data": f"get-order-info_{order.order_id}"
        }])
    
    return buttons



def generate_favorites_buttons(textgen: TextGenerator, favorites_list: List[Favorites]):
    buttons = []

    for order in favorites_list[:10]:
        country_name = textgen.get(*FLAG_PATH, str(order.country_id), "name_ru")

        buttons.append([{
            "text": f"{order.service_name} [{country_name}]",
            "callback_data": f"get-favorite_{order.id}"
        }])
    
    if not buttons:
        return [[{
            "text": "Список пуст",
            "callback_data": "answer"
        }]]
    
    return buttons


def generate_rent_countries_button(textgen: TextGenerator, countries: Dict, page: int = 1) -> List[List[Dict[str, str]]]:
    """Генерирует кнопки со странами для аренды с пагинацией."""
    buttons = []
    page_countries, total, current = get_pages(countries, page)
    
    for country_id, _ in page_countries.items():
        try:
            buttons.append({
                "text": textgen.get(*FLAG_PATH, str(country_id), "name_ru"),
                "callback_data": f"rent-country_{country_id}"
            })
        except:
            pass

    # Разбиение кнопок на колонки
    columnized_buttons = [buttons[i:i + ITEMS_COLUMN] for i in range(0, len(buttons), ITEMS_COLUMN)]
    
    # Добавление кнопок навигации
    navigation_buttons = []
    if current > 1:
        navigation_buttons.append({
            "text": "⏪",
            "callback_data": f"rent-countries-page_{current - 1}"
        })
    
    navigation_buttons.append({
        "text": f"📄 {current}/{total}",
        "callback_data": "answer"
    })
    
    if current < total:
        navigation_buttons.append({
            "text": "⏩",
            "callback_data": f"rent-countries-page_{current + 1}"
        })
    
    if navigation_buttons:
        columnized_buttons.append(navigation_buttons)
    
    return columnized_buttons