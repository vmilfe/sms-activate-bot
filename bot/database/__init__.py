from peewee import * 

from typing import List, Dict, Tuple, Union, Optional
from datetime import datetime, timedelta


db = SqliteDatabase('bot/database/database_file/database.sqlite')


class User(Model):
    id = PrimaryKeyField()
    username = TextField(null=True)
    balance = FloatField(default=0)
    ref_balance = IntegerField(default=0) # balance included ref_balance  

    class Meta:
        database = db 

class Referal(Model):
    from_user = IntegerField()
    to_user = IntegerField()

    class Meta:
        database = db 

class Invoices(Model):
    invoice_id = TextField() # use uuid4 for telegram stars and integer for cryptobot
    user_id = IntegerField()
    payment_provider = TextField()
    create_time = DateTimeField()
    status = TextField(default='active')
    payment_message_id = IntegerField()

    class Meta:
        database = db 

class SmsOrder(Model):
    id = PrimaryKeyField()
    order_id = TextField()  # ID активации от SMS-activate
    user_id = IntegerField()
    phone = TextField()  # Номер телефона
    service = TextField()  # Код сервиса
    service_name = TextField()
    coutry_id = IntegerField()
    price = FloatField()  # Цена заказа
    create_time = DateTimeField(default=datetime.now)
    status = TextField(default='active')  # active, completed, cancelled, expired

    class Meta:
        database = db

class Favorites(Model):
    user_id = IntegerField()
    service = TextField()
    service_name = TextField()
    country_id = IntegerField()
    create_time = DateTimeField(default=datetime.now)

    class Meta:
        database = db


class RentNumber(Model):
    order_id = IntegerField()
    user_id = IntegerField()
    phone = TextField()
    start_date = DateTimeField(default=datetime.now)  
    end_date = DateTimeField()
    price = FloatField()  #
    status = TextField(default='active')  # active, cancelled
    
    class Meta:
        database = db


class Promo(Model):
    code = TextField()
    activates = IntegerField()
    amount = IntegerField()

    class Meta:
        database = db 


class PromoUse(Model):
    promo_id = IntegerField()
    user_id = IntegerField()

    class Meta:
        database = db 





class RentDatabase:
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id

    def create_rent_order(self, order_id: int, phone: str, end_date: datetime, price: float) -> int:
        return RentNumber.create(
            order_id=order_id, user_id=self.user_id, phone=phone, end_date=end_date, price=price
        ).id

    def get_rent_orders(self) -> List[RentNumber]:
        return list(RentNumber.select().where(
            RentNumber.user_id == self.user_id
        ).order_by(RentNumber.start_date.desc()))

    @staticmethod
    def get_active_rent_orders() -> List[RentNumber]:
        """Получение всех активных арендованных номеров"""
        return list(RentNumber.select().where(
            (RentNumber.status == 'active') &
            (RentNumber.end_date >= datetime.now())
        ))

    @staticmethod
    def get_rent_order_by_id(order_id: int) -> RentNumber:
        return RentNumber.get(RentNumber.id == order_id)

    @staticmethod
    def cancel_rent_order(order_id: int) -> bool:
        order = RentNumber.get_or_none(RentNumber.id == order_id)
        if not order or order.status != 'active':
            return False

        order.status = 'cancelled'
        order.save()
        return True

    @staticmethod
    def complete_rent_order(order_id: int) -> bool:
        order = RentNumber.get_or_none(RentNumber.id == order_id)
        if not order or order.status != 'active':
            return False

        order.status = 'expired'
        order.save()
        return True



class GlobalDatabase:
    tables = [User, Referal, Invoices, SmsOrder, Favorites, RentNumber, PromoUse, Promo] # change if you add another table in db

    @staticmethod
    def create_tables() -> List[Model]:
        created_tables = db.get_tables()
        now_created = []

        with db:
            for table in GlobalDatabase.tables:
                if table._meta.table_name not in created_tables:
                    db.create_tables([table])
                    now_created.append(table)
                
        return now_created
    
    @staticmethod
    def tables_is_created() -> bool:
        return all(table._meta.table_name in db.get_tables() for table in GlobalDatabase.tables)


class UserDatabase:
    def __init__(self, user_id: int, username: str = None) -> None:
        self.user_id = user_id
        self.username = username
        self.user = User.get_or_none(User.id == user_id)
    
    def new_user(self) -> None:
        if self.user:
            if self.user.username != self.username:
                User.update(username=None).where(
                    (User.username == self.username) & 
                    (User.id != self.user_id)
                ).execute()
                User.update(username=self.username).where(User.id == self.user_id).execute()

        else:
            User.create(id=self.user_id, username=self.username)
    
    def check_balance_available(self, amount: float) -> bool:
        return self.user.balance >= amount
    
    @staticmethod
    def get_user_id_by_username(username: str):
        return User.get_or_none(User.username == username)
    
    @staticmethod
    def transfer_balance(from_user_id: int, to_user_id: int, amount: float, is_ref: bool = False) -> bool:
        try:
            with db.atomic():
                # Снимаем баланс у отправителя
                if from_user_id != 0:
                    from_user = User.get(User.id == from_user_id)
                    if from_user.balance < amount:
                        return False
                    
                    User.update(
                        balance=User.balance - amount
                    ).where(
                        User.id == from_user_id
                    ).execute()

                # Начисляем баланс получателю
                if to_user_id != 0:
                    # Обновляем реферальный баланс
                    if is_ref:
                        User.update(
                            ref_balance=User.ref_balance + amount
                        ).where(
                            User.id == to_user_id
                        ).execute()
                    
                    # Обновляем основной баланс
                    User.update(
                        balance=User.balance + amount
                    ).where(
                        User.id == to_user_id
                    ).execute()
                    
            return True
            
        except Exception as e:
            print(f"Error in transfer_balance: {e}")
            return False


class InvoicesDatabase:
    def __init__(self, user_id: Union[int, None] = None) -> None:
        self.user_id = user_id

    def create_new_invoice(
        self,
        invoice_id: str,
        payment_provider: str,
        payment_message_id: int 
    ):
        Invoices.create(
            invoice_id=invoice_id,
            user_id=self.user_id,
            payment_provider=payment_provider,
            create_time=datetime.now(),
            payment_message_id=payment_message_id
        )

    def validate_payment(self, invoice_data: Dict[str, str]) -> bool:
        return Invoices.select().where(
            (Invoices.invoice_id == invoice_data['invoice_id']) &
            (Invoices.user_id == self.user_id) &
            (Invoices.status == 'active')
        ).exists()
    
    @staticmethod
    def get_invoice_payment_message(invoice_id: str):
        return Invoices.get(Invoices.invoice_id == invoice_id).payment_message_id
    
    @staticmethod
    def success_invoice(invoice_id: str, amount: int) -> Tuple[int, int]: # type: ignore
        invoice = Invoices.get(Invoices.invoice_id == invoice_id)
        user = User.get(User.id == invoice.user_id)

        Invoices.update(status = 'paid').where(Invoices.id == invoice.id).execute()
        User.update(balance=user.balance + amount).where(User.id == invoice.user_id).execute()
        
        return user.id, invoice.payment_message_id

    @staticmethod
    def get_actual_invoices_id(timeout: int, payment_provider: str) -> List[int]:
        # timeout in minutes 
        timeout_delta = datetime.now() - timedelta(minutes=timeout)
        return [
            invoice.invoice_id 
            for invoice in Invoices.select().where(
                (Invoices.status == 'active') & 
                (Invoices.create_time >= timeout_delta) &
                (Invoices.payment_provider == payment_provider)
            )
        ]


class ReferalDatabase:
    @staticmethod
    def add_referal(from_user_id: int, to_user_id: int) -> bool:
        if from_user_id == to_user_id:
            return False
            
        if not User.select().where(User.id.in_([from_user_id, to_user_id])).count() == 2:
            return False
            
        if Referal.select().where(
            (Referal.from_user == from_user_id) & 
            (Referal.to_user == to_user_id)
        ).exists():
            return False
            
        Referal.create(
            from_user=from_user_id,
            to_user=to_user_id
        )
        return True
    
    @staticmethod
    def get_referals_count(user_id: int) -> int:
        return Referal.select().where(
            Referal.from_user == user_id
        ).count()
    
    @staticmethod
    def get_referal_owner(user_id: int) -> Union[int, None]:
        referal = Referal.get_or_none(Referal.to_user == user_id)
        return referal.from_user if referal else None
    
    @staticmethod
    def get_all_referal_earned(user_id: int) -> int:
        return User.get(User.id == user_id).ref_balance
    
    @staticmethod
    def process_referal_payment(user_id: int, amount: int, fee: float) -> None:
        print(user_id, amount, fee)
        if fee <= 0:
            return
            
        referal = Referal.get_or_none(Referal.from_user == user_id)
        if not referal:
            return
            
        referal_amount = round(amount * fee)
        if referal_amount <= 0:
            return 

        UserDatabase.transfer_balance(
            0, # system
            referal.from_user,
            referal_amount
        )


class SmsOrdersDatabase:
    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id

    def create_order(
        self,
        order_id: str,
        phone: str,
        service: str,
        service_name: str,
        coutry_id: int,
        price: float
    ) -> SmsOrder:
        return SmsOrder.create(
            order_id=order_id,
            user_id=self.user_id,
            phone=phone,
            service=service,
            service_name=service_name,
            coutry_id=coutry_id,
            price=price
        )
    
    def get_all_user_orders(self) -> List[SmsOrder]:
        return list(SmsOrder.select().where(
            SmsOrder.user_id == self.user_id
        ).order_by(SmsOrder.create_time.desc()))
    
    @staticmethod
    def get_order(order_id: str) -> Optional[SmsOrder]:
        return SmsOrder.get_or_none(SmsOrder.order_id == order_id)
    
    @staticmethod
    def get_all_active_orders() -> List[SmsOrder]:
        timeout_delta = datetime.now() - timedelta(minutes=20)
        return list(SmsOrder.select().where(
            (SmsOrder.status == 'active') &
            (SmsOrder.create_time >= timeout_delta)
        ))
    
    @staticmethod
    def complete_order(order_id: str) -> bool:
        order = SmsOrder.get_or_none(SmsOrder.order_id == order_id)
        if not order or order.status != 'active':
            return False
            
        order.status = 'completed'
        order.save()
        return True
    
    @staticmethod
    def cancel_order(order_id: str) -> bool:
        """Отменяет заказ"""
        order = SmsOrder.get_or_none(SmsOrder.order_id == order_id)
        if not order or order.status != 'active':
            return False
            
        order.status = 'cancelled'
        order.save()
        return True


class FavoritesDatabase:
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
    
    def create_new_favorite(self, service: str, service_name: str, country_id: int) -> int:
        return Favorites.create(
            user_id=self.user_id, service=service, service_name=service_name, country_id=country_id
        ).id
    
    def get_favorites_list(self) -> List[Favorites]:
        return list(Favorites.select().where(
            Favorites.user_id == self.user_id
        ).order_by(Favorites.create_time.desc()))
    
    @staticmethod
    def get_favorite_by_id(favorite_id: int) -> Favorites:
        return Favorites.get(Favorites.id == favorite_id)
    
    @staticmethod
    def delete_favorite(favorite_id: int):
        Favorites.delete().where(Favorites.id == favorite_id).execute()


class PromoDatabase:
    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id
    
    @staticmethod
    def create_promo(code: str, activates: int, amount: int) -> Promo:
        """
        Создает новый промокод
        :param code: Код промокода
        :param activates: Количество возможных активаций
        :param amount: Сумма начисления
        :return: Объект промокода
        """
        return Promo.create(
            code=code,
            activates=activates,
            amount=amount
        )
    
    def activate_promo(self, promo_code: str) -> (bool, str): # type: ignore
        """
        Активирует промокод для пользователя
        :param promo_code: Код промокода
        :return: (Успех активации, Сообщение)
        """
        promo = Promo.get_or_none(Promo.code == promo_code)
        
        if not promo:
            return False, "Промокод не найден"
            
        # Проверяем, использовал ли пользователь этот промокод
        if PromoUse.select().where(
            (PromoUse.promo_id == promo.id) & 
            (PromoUse.user_id == self.user_id)
        ).exists():
            return False, "Вы уже использовали этот промокод"
            
        # Проверяем количество активаций
        used_count = PromoUse.select().where(PromoUse.promo_id == promo.id).count()
        if used_count >= promo.activates:
            return False, "Промокод больше не действителен"
            
        # Активируем промокод
        with db.atomic():
            PromoUse.create(
                promo_id=promo.id,
                user_id=self.user_id
            )
            UserDatabase.transfer_balance(
                0,  # system
                self.user_id,
                promo.amount
            )
            
        return True, f"Промокод активирован! Начислено: {promo.amount}"
    
    @staticmethod
    def get_promo_info(promo_code: str) -> Optional[Dict[str, Union[str, int]]]:
        """
        Получает информацию о промокоде
        :return: Словарь с информацией или None
        """
        promo = Promo.get_or_none(Promo.code == promo_code)
        if not promo:
            return None
            
        used_count = PromoUse.select().where(PromoUse.promo_id == promo.id).count()
        return {
            "code": promo.code,
            "amount": promo.amount,
            "activates": promo.activates,
            "used": used_count,
            "remaining": promo.activates - used_count
        }
    
    @staticmethod
    def delete_promo(promo_id: int) -> bool:
        """
        Удаляет промокод
        :return: Успех удаления
        """
        promo = Promo.get_or_none(Promo.id == promo_id)
        if not promo:
            return False
            
        with db.atomic():
            PromoUse.delete().where(PromoUse.promo_id == promo.id).execute()
            promo.delete_instance()
        return True

    @staticmethod
    def get_all_promos() -> List[Promo]:
        """
        Получает список всех промокодов
        :return: Список объектов промокодов
        """
        return list(Promo.select().order_by(Promo.code))