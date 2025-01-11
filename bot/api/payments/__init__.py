from typing import Dict
from math import ceil

class CalculatorAsset:
    @staticmethod
    def convert_to_crypto(fiat_amount: float | int, rate: float) -> float:
        return round(float(fiat_amount) / rate, 2)

    @staticmethod
    def convert_to_fiat(crypto_amount: float | int, rate: float) -> int:
        return round(float(crypto_amount) * rate)
    
    @staticmethod
    def convert_to_stars(fiat_amount: float | int, rate: Dict[str, int]) -> int:
        stars_per_rub = rate['stars'] / rate['rub']
        return ceil(float(fiat_amount) * stars_per_rub)

    @staticmethod
    def conver_price_with_fee(amount: int, fee: float) -> float:
        return ceil((amount + (amount * fee)) * 10) / 10