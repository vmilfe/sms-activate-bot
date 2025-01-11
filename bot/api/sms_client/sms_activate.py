from structlog.typing import FilteringBoundLogger
from typing import Union, Dict, Optional

from httpx import AsyncClient 
from typing import Union

import asyncio

from bot.database import SmsOrdersDatabase, GlobalDatabase, UserDatabase, RentDatabase
from aiogram import Bot


class SMSActivateAPI:
    def __init__(self, sms_activate_token: str, logger: FilteringBoundLogger, bot: Bot) -> None:
        self.global_name = 'SmsActivate'
        self.api_key = sms_activate_token
        self.bot = bot
        self.client = AsyncClient(
            base_url='https://api.sms-activate.guru/',
            params={
                'api_key': self.api_key
        })
        
        self.logger = logger
        self._running = True
        
        # Запускаем backend puller
        asyncio.create_task(self._backend_puller())
    
    async def get_balance(self, isinit: bool = False) -> Union[str, bool]:
        response = await self.client.get(
            'stubs/handler_api.php', params={
                'action': 'getBalance'
            }
        )
        response_text = response.text
        if 'ACCESS_BALANCE' not in response_text:
            if isinit:
                self.logger.error(
                    f"❌ Error auth - {self.global_name}",
                    error_code=response_text,
                    api_key=self.api_key[:5] + '...' + self.api_key[-5:]
                )
        else:
            return float(response_text.split(':')[1])
    
    async def get_top_countries_by_service(self, service: str | None = None) -> Dict:
        """Получение списка всех стран с ценами"""
        response = await self.client.get(
            'stubs/handler_api.php', 
            params={
                'action': 'getTopCountriesByService',
                'service': service if service else ''
            }
        )
        
        if response.status_code == 200:
            self.countries_data = response.json()
            return self.countries_data
        
        self.logger.error(
            f"❌ Ошибка получения списка стран - {self.global_name}",
            status_code=response.status_code
        )
        return {}

    async def rent_number(self, service: str, rent_time: int, country: int = 0) -> Union[dict, bool]:
        """Получение номера в аренду для указанного сервиса"""
        response = await self.client.get(
            'stubs/handler_api.php',
            params={
                'action': 'getRentNumber',
                'service': service,
                'rent_time': rent_time,
                'country': country
            }
        )

        if response.status_code != 200:
            self.logger.error(
                f"❌ Ошибка аренды номера - {self.global_name}",
                status_code=response.status_code,
                service=service
            )
            return False

        response_data = response.json()
        if response_data.get('status', '') == 'success':
            return response_data['phone']
        return False
    
    async def get_rent_status(self, order_id: str) -> Union[Dict, bool]:
        """Получение статуса аренды и SMS"""
        response = await self.client.get(
            'stubs/handler_api.php',
            params={
                'action': 'getRentStatus',
                'id': order_id
            }
        )
        
        if response.status_code != 200:
            self.logger.error(
                f"❌ Ошибка получения статуса аренды - {self.global_name}",
                status_code=response.status_code,
                order_id=order_id
            )
            return False
        
        return response.json()

    async def get_all_services(self) -> Dict:
        """Получение доступных сервисов для конкретной страны"""
        response = await self.client.get(
            'stubs/handler_api.php',
            params={
                'action': 'getServicesList',
                'lang': 'ru'
            }
        )
        
        if response.status_code == 200:
            return response.json()
        
        self.logger.error(
            f"❌ Ошибка получения сервисов страны - {self.global_name}",
            status_code=response.status_code
        )
        return {}

    async def get_number(self, service: str, country: int = 0) -> Union[dict, bool]:
        """Получение номера для указанного сервиса"""
        response = await self.client.get(
            'stubs/handler_api.php', 
            params={
                'action': 'getNumber',
                'service': service,
                'country': country
            }
        )
        
        if response.status_code != 200:
            self.logger.error(
                f"❌ Ошибка получения номера - {self.global_name}",
                status_code=response.status_code,
                service=service
            )
            return False
            
        response_text = response.text
        if 'ACCESS_NUMBER' in response_text:
            # Формат ответа: ACCESS_NUMBER:id:phone_number
            _, activation_id, phone = response_text.split(':')
            return {
                'id': activation_id,
                'phone': phone
            }
        return False

    async def get_status(self, activation_id: str) -> Union[str, bool]:
        """Получение статуса активации"""
        response = await self.client.get(
            'stubs/handler_api.php',
            params={
                'action': 'getStatus',
                'id': activation_id
            }
        )
        
        if response.status_code == 200:
            return response.text
        return False
    
    async def get_price(self, service: str, country_id: int):
        response = await self.client.get(
            'stubs/handler_api.php',
            params={
                'action':'getPrices',
                'service': service,
                'country': country_id
            }
        )
        return response.json()[str(country_id)][str(service)]["cost"]

    async def set_status(self, activation_id: str, status: int) -> bool:
        """Установка статуса активации
        status: 8 - подтвердить получение смс
              6 - запросить еще одну смс
              3 - отменить активацию
        """
        response = await self.client.get(
            'stubs/handler_api.php',
            params={
                'action': 'setStatus',
                'id': activation_id,
                'status': status
            }
        )
        
        return response.status_code == 200
    
    async def get_rent_price(self, service: str, country_id: int, hours: int = 1) -> float:
        response = await self.client.post(
            'stubs/handler_api.php',
            params={
                'action': 'getRentServicesAndCountries',
                'rent_time': hours,
                'country': country_id
            }
        )
        print(response.json())

        return response.json()

    async def close(self):
        self._running = False
        await self.client.aclose()

    async def _backend_puller(self):
        await self.wait_for_database()
        
        while self._running:
            try:
                # Проверка обычных SMS заказов
                active_orders = SmsOrdersDatabase.get_all_active_orders()
                for order in active_orders:
                    status = await self.get_status(str(order.order_id))
                    
                    if not status:
                        continue
                        
                    if status.startswith('STATUS_OK'):
                        code = status.split('STATUS_OK:')[1]
                        await self._process_sms_received(order, code)
                    elif status == 'STATUS_CANCEL':
                        await self._process_sms_cancelled(order)
                    elif status in ['STATUS_WAIT_CODE', 'STATUS_WAIT_RETRY']:
                        continue
                    else:
                        self.logger.warning(
                            "Неизвестный статус SMS",
                            status=status,
                            order_id=order.order_id
                        )

                # Проверка арендованных номеров
                rent_orders = RentDatabase.get_active_rent_orders()
                for rent in rent_orders:
                    status = await self.get_rent_status(str(rent.order_id))
                    
                    if not status or status.get('status') != 'success':
                        continue

                    # Обработка новых SMS
                    if int(status.get('quantity', 0)) > 0:
                        for sms in status['values'].values():
                            await self._process_rent_sms_received(rent, sms)
                    
                    # Проверка статуса аренды
                    if status.get('message') in ['STATUS_FINISH', 'STATUS_CANCEL', 'STATUS_REVOKE']:
                        await self._process_rent_finished(rent, status.get('message'))
                        
            except Exception as e:
                self.logger.error(
                    "Ошибка в SMS backend puller",
                    error=str(e)
                )
                
            await asyncio.sleep(10)

    async def _process_sms_received(self, order, code):
        """Обработка полученного SMS"""
        await self.bot.send_message(
            order.user_id,
            text=self.bot.textgen.get(
                'common', 'sms_received', 'text',
                code=code
            )
        )
        SmsOrdersDatabase.complete_order(order.order_id)

    async def _process_sms_cancelled(self, order):
        """Обработка отмененной активации"""
        # Возвращаем деньги пользователю
        UserDatabase.transfer_balance(
            0,  # system
            order.user_id,
            order.price
        )
        SmsOrdersDatabase.cancel_order(order.order_id)
        await self.bot.send_message(
            order.user_id,
            text=self.bot.textgen.get(
                'common', 'sms_cancelled', 'text'
            )
        )

    async def _process_rent_sms_received(self, rent, sms_data):
        """Обработка полученного SMS для арендованного номера"""
        await self.bot.send_message(
            rent.user_id,
            text=self.bot.textgen.get(
                'common', 'rent_sms_received', 'text',
                phone_from=sms_data['phoneFrom'],
                text=sms_data['text'],
                service=sms_data['service'],
                date=sms_data['date']
            )
        )

    async def _process_rent_finished(self, rent, status):
        """Обработка завершения аренды"""
        if status in ['STATUS_CANCEL', 'STATUS_REVOKE']:
            # Возврат денег при отмене
            UserDatabase.transfer_balance(
                0,  # system
                rent.user_id,
                rent.price
            )
            RentDatabase.cancel_rent_order(rent.id)
            message = 'rent_cancelled'
        else:
            RentDatabase.complete_rent_order(rent.id)
            message = 'rent_finished'
            
        await self.bot.send_message(
            rent.user_id,
            text=self.bot.textgen.get(
                'common', message, 'text'
            )
        )

    async def wait_for_database(self):
        while not GlobalDatabase.tables_is_created():
            await asyncio.sleep(0.1)