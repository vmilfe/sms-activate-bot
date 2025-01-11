from pydantic import BaseModel, field_validator, computed_field
from typing import Union, List, Dict


class Config(BaseModel):
    version: str
    bot_token: str
    admin_id: List[int]
    service_fee: float
    service_name: str 
    referal_fee: float
    messages_path: str
    messages_parse_mode: str
    sms_activate_api_token: str
    crypto_bot_api_token: str
    cryptobot_usdt_rub_rate: float
    tg_stars_max: int
    tg_stars_star_rub_rate: Dict[str, int]
    tg_stars_enabled: bool = True
    success_payment_reaction_id: str | None
    support_username: str 
    support_redirect_channel: str
    payment_timeout_minutes: int
    

    @field_validator('admin_id', mode='before')
    @classmethod
    def validate_admin_id(cls, value: str) -> List[int]:
        admin_ids_list = value.split(',')
        if any(not admin_id.isdigit() for admin_id in admin_ids_list):
            raise ValueError('Admin id должен быть список чисел, разделенных запятой, например: 1234567890,1234567891')
        return [int(admin_id) for admin_id in admin_ids_list]
    
    @field_validator('tg_stars_star_rub_rate', mode='before')
    @classmethod
    def validate_tg_stars_rate(cls, value: str) -> Dict[str, int]:
        if ':' not in value:
            raise ValueError('Курс звезд к рублю должен быть в формате stars:rubles, например 100:215')
        
        value_list = value.split(':')
        if not all(_.isnumeric() for _ in value_list):
            raise ValueError('Между : должны быть только числа')
        
        return {
            "stars": int(value_list[0]), "rub": int(value_list[1])
        }

    @computed_field
    def check_admin_exist(self, admin_id: int) -> bool:
        return admin_id in self.admin_id
