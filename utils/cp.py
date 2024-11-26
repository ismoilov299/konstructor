from dataclasses import dataclass
import math
from typing import List

from utils.exchange_rate import ExchangeRateRussia

@dataclass
class AIPrices:
    stars: int
    price: float
    
    def __str__(self) -> str:
        return f"{self.stars}:= {self.price}"
    
@dataclass
class AIPrice:
    AI_PRICE: float
    ADMIN_PRICE: float
    TOTAL_PRICE: float
    COUNT_STARS: int

class CalculatePrice:
    STARS = [
        250, 500, 750, 1500, 2000, 3000, 4000, 5000,
    ]
    AI_COST_DOLLAR = 0.04
    BASE_STAR_COST = 1.5
    star_cost: float
    pay_admin: float
    admin_percent: float
    CURRENCY = 91.64
    PAY_AI: float
    total_cost_per_one_star: float
    ONE_STARS_COUNT_TOKENS = 500
    AI_TOKENS = 1_000
    
    def __init__(self, admin_percent: float) -> None:
        self.admin_percent = admin_percent
        self.PAY_AI = self.AI_COST_DOLLAR * self.CURRENCY
        self.star_cost = self.BASE_STAR_COST + self.PAY_AI
        self.pay_admin = self.BASE_STAR_COST / 100 * self.admin_percent
        self.total_cost_per_one_star = self.star_cost + self.pay_admin
        exchange = ExchangeRateRussia()
        self.CURRENCY = exchange.get_currency("R01235")        
        
    def calc_prices(self):
        result: List[AIPrices] = []
        for i in range(len(self.STARS)):
            result.append(AIPrices(self.STARS[i], round(self.total_cost_per_one_star * self.STARS[i], 0)))
        return result
    
    def calc_price(self, stars: int) -> float:
        return round(self.total_cost_per_one_star * stars, 0)
    
    def calc_price_ai(self, input_tokens: int, output_tokens: int):
        total_tokens = input_tokens + output_tokens
        total_stars = math.ceil(total_tokens / self.ONE_STARS_COUNT_TOKENS)
        price = total_stars * self.total_cost_per_one_star
        pay_openai = self.PAY_AI / self.AI_TOKENS * total_tokens
        pay_admin = self.pay_admin * total_stars
        return AIPrice(
            AI_PRICE=pay_openai,
            ADMIN_PRICE=pay_admin,
            TOTAL_PRICE=price,
            COUNT_STARS = total_stars
        )
    
    def __str__(self):
        return f"""
    {self.AI_COST_DOLLAR=}
    {self.CURRENCY=}
    {self.PAY_AI=}
    {self.admin_percent=}
    {self.BASE_STAR_COST=}
    {self.star_cost=}
    {self.pay_admin=}
    {self.total_cost_per_one_star=}
    {self.ONE_STARS_COUNT_TOKENS=} 
    {self.AI_TOKENS=} 
    """