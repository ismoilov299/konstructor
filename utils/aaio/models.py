from dataclasses import dataclass, field
from typing import List
from strenum import StrEnum


@dataclass
class Balance:
    type: str
    balance: float
    referral: float
    hold: float
    
@dataclass
class MoneyData:
    RUB: float = None
    UAH: float = None
    USD: float = None
    EUR: float = None
    
@dataclass
class PaymentMethod:
    name: str
    min: MoneyData
    max: MoneyData
    commission_percent: float
    commission_user_percent: float = 0
    commission_merchant_percent: float = 0
    commission_type: float = 0
    def __post_init__(self):
        self.min = MoneyData(**self.min)
        self.max = MoneyData(**self.max)
        
@dataclass
class PayoutMethod:
    code: str
    name: str
    min: float
    max: float
    commission_percent: float
    commission_sum: float = 0
    
    

        
@dataclass
class PaymentMethodResponse:
    type: str
    list: List[PaymentMethod] = field(default_factory=List[PaymentMethod])
    def __post_init__(self):
        self.list = [PaymentMethod(**self.list[x]) for x in self.list.keys()]
    def get_method(self, method_name: str) -> 'PaymentMethod':
        for method in self.list:
            if method.name == method_name:
                return method
        return None
    
@dataclass
class PayoutMethodResponse:
    type: str
    list: List[PayoutMethod] = field(default_factory=List[PayoutMethod])
    def __post_init__(self):
        self.list = [PayoutMethod(**(self.list[x] | {"code": x})) for x in self.list.keys()]
    def get_method(self, method_name: str) -> 'PayoutMethod':
        for method in self.list:
            if method.name == method_name:
                return method
        return None
    
@dataclass
class Rate:
    type: str
    USD: float
    UAH: float
    USDT: float
    BTC: float
    
class Lang(StrEnum):
    RU = "ru"
    EN = "en"

class Currency(StrEnum):
    RUB = "RUB"    
    
@dataclass
class PaymentWebhook:
    status: str
    merchant_id: str
    invoice_id: str
    order_id: str
    amount: float
    currency: Currency
    profit: float
    commission: float
    commission_client: float
    commission_type: str
    sign: str
    method: str
    desc: str
    email: str
    us_key: str = None
    
@dataclass
class PayoutWebhook:
    id: str
    my_id: str
    method: str
    wallet: str
    amount: float
    amount_in_currency: float
    amount_currency: float
    amount_rate: float = 0
    amount_down: float = 0
    commission: float = 0
    commission_type: int = 0
    status: str = ""
    cancel_message: str = ""
    date: str = ""
    complete_date: str = ""
    sign: str = ""
    us_key: str = ""