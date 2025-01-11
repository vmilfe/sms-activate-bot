import asyncio
from typing import List, Dict, Union

from aiogram import Bot
from httpx import AsyncClient
from structlog.typing import FilteringBoundLogger

from . import CalculatorAsset
from bot.database import InvoicesDatabase, GlobalDatabase, ReferalDatabase
from config.models import Config


class CryptoBotAPI:
    def __init__(
            self, 
            bot: Bot, 
            config: Config, 
            logger: FilteringBoundLogger, 
            backend_puller_autostart: bool = True
        ) -> None:
        self.bot = bot
        self.logger = logger
        self.timeout_cryptobot_updates = 5 # in seconds 
        self.payment_timeout = config.payment_timeout_minutes 
        self.token = config.crypto_bot_api_token
        self.payment_rate = config.cryptobot_usdt_rub_rate

        self.client = AsyncClient(
            base_url='https://pay.crypt.bot/api/',
            headers={
                'Crypto-Pay-API-Token': self.token
        })
        
        self.global_name = 'CryptoBot'
        self._running = False

        if backend_puller_autostart:
            self._running = True
            asyncio.create_task(self._backend_puller())
    

    def _balance_pretty(self, response: List[Dict[str, str]]):
        result_string = ''
        for item in response['result']:
            if float(item['available']) > 0:
                result_string += f'{item["currency_code"]}: {round(float(item["available"]), 2)}  '
        if result_string.endswith('  '):
            result_string = result_string[:-2]

        return result_string if result_string != '' else 0.0
    
    async def get_balance(self, isinit: bool = False) -> Union[str, bool]:
        response = await self.client.get('getBalance')
        response_json = response.json()

        if response_json.get("ok", False) == False:
            if isinit:
                self.logger.error(
                    f"❌ Error auth - {self.global_name}",
                    error_code=response_json["error"]["name"],
                    api_key=self.token[:5] + '...' + self.token[5:]
                )
                return None
        return self._balance_pretty(response.json())

    async def create_invoice(
            self, 
            asset: str, 
            amount: int, 
            description: str = "Пополнение баланса бота"
        ) -> Union[Dict[str, Union[str, int]], None]:
        payment_result = await self.client.get(
            'createInvoice', params={
                "asset": asset,
                "amount": amount,
                "description": description
            }
        )
        payment_result = payment_result.json()

        if payment_result["ok"]:
            return payment_result["result"] 
        
        self.logger.error(str(payment_result))
        
    
    async def wait_for_database(self):
        while not GlobalDatabase.tables_is_created():
            await asyncio.sleep(0.1)

    async def __process_invoice_backend(self, invoice: Dict[str, str]):
        if invoice['status'] == 'paid':
            amount_converted = CalculatorAsset.convert_to_fiat(
                float(invoice['amount']), self.payment_rate
            )
            user_id, message_id = InvoicesDatabase.success_invoice(str(invoice['invoice_id']), amount_converted)
            ref_owner = ReferalDatabase.get_referal_owner(user_id)
            if ref_owner:
                ReferalDatabase.process_referal_payment(ref_owner, amount_converted, self.bot.config.referal_fee)

            await self.bot.send_message(
                user_id, text=self.bot.textgen.get(
                    'common', 'success_pay', 'text', amount=amount_converted
                ), reply_markup=self.bot.textgen.generate_keyboard_markup(
                    'action', 'start', 'buttons'
                ), message_effect_id=self.bot.config.success_payment_reaction_id
            )
            try:
                await self.bot.delete_message(user_id, message_id)
            except:
                pass
    
    async def _backend_puller(self):
        '''
        Функция вызывается автоматически при init и постоянно проверяет статус оплаты
        '''

        await self.wait_for_database()
        while self._running:
            invoices_id_list = InvoicesDatabase.get_actual_invoices_id(
                self.payment_timeout, 'crypto_bot'
            )

            if invoices_id_list:
                invoices_response = await self.client.get('getInvoices', params={
                    "invoice_ids": ",".join(invoices_id_list)
                })
                for invoice in invoices_response.json()['result']['items']:
                    await self.__process_invoice_backend(invoice)

            await asyncio.sleep(self.timeout_cryptobot_updates)

    
    async def close(self):
        self._running = False
        await self.client.aclose()