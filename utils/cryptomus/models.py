from dataclasses import dataclass, field
from enum import Enum

class PaymentStatus(Enum):
    INIT = "init"
    CANCEL = "cancel"
    PAID = "paid"
    WRONG_AMOUNT = "wrong_amount" 
    PAID_OVER = "paid_over"

@dataclass
class CurrencyStructure:
    currency: str
    network: str
    def __str__(self) -> str:
        return f"{self.currency}: {self.network}"

@dataclass
class Payment:
    uuid: str
    order_id: str
    amount: str
    payment_amount: float = 0
    payer_amount: float = 0
    payer_currency: float = 0
    commission: int = 0
    payment_amount_usd: float = None
    payer_amount_exchange_rate: float = None
    currency: str = ""
    comments: str = ""
    network: str = ""
    address: str = ""
    merchant_amount: str = ""
    created_at: str = ""
    updated_at: str = ""
    from_wallet: str = ""
    status: PaymentStatus = PaymentStatus.INIT
    txid: str = ""
    url: str = ""
    expired_at: str = ""
    payment_status: PaymentStatus = PaymentStatus.INIT
    is_final: bool = False
    additional_data: list = None
    currencies: list = None
    discount: str = None
    discount_percent: int = None

@dataclass
class CreateStaticWalletResponse:
    wallet_uuid:str
    uuid: str
    address: str
    network: str
    currency: str
    
@dataclass
class PaymentResponseWebHookRetry:
    type: str
    uuid: str
    order_id: str
    amount: str
    merchant_amount: str
    commission: str
    is_final: str = ""
    status: str = ""
    txid: str = ""
    sign: str = ""
    payer_currency: str = ""
    payer_amount: str = ""

@dataclass
class ServiceLimit:
    min_amount: str = ""
    max_amount: str = ""

@dataclass
class ServiceCommission:
    fee_amount: str = ""
    percent: str = ""

@dataclass
class Service:
    network: str = ""
    currency: str = ""
    is_available: bool = False
    limit: ServiceLimit = field(default_factory=ServiceLimit)
    commission: ServiceCommission = field(default_factory=ServiceCommission)
    
    def __post_init__(self):
        if isinstance(self.limit, dict):
            self.limit = ServiceLimit(**self.limit)
        if isinstance(self.commission, dict):
            self.commission = ServiceCommission(**self.commission)

@dataclass
class ServiceResponse:
    state: int
    result: list = field(default_factory=list)
    error: str = ""
    message: str = ""
    def __post_init__(self):
        for result_dict in self.result:
            result_dict["limit"] = ServiceLimit(**result_dict["limit"])
            result_dict["commission"] = ServiceCommission(**result_dict["commission"])
        self.result = [Service(**result_dict) for result_dict in self.result]



@dataclass
class MethodCode:
    currens_code: str
    network_code: str
    description: str

METHOD_CODES = [
    MethodCode("BCH", "BCH", "Bitcoin Cash")
]

class PaymentType(Enum):
    PAYMENT = "payment"
    
@dataclass
class CurrencyInformation:
    to_currency: str = ""
    commission: str = ""
    rate: str = ""
    amount: str = ""

@dataclass
class PaymentWebhook:
    type: PaymentType = PaymentType.PAYMENT
    uuid: str = ""
    order_id: str = ""
    PaymentType: str = ""
    PaymentType: str = ""
    payer_amount: str = ""
    amount: str = ""
    payment_amount: str = ""
    payment_amount_usd: str = None
    merchant_amount: str = ""
    commission: str = ""
    is_final: bool = False
    status: PaymentStatus = PaymentStatus.INIT
    from_wallet: str = ""
    wallet_address_uuid: str = ""
    network: str = ""
    txid: str = ""
    currency: str = ""
    additional_data: str = ""
    payer_currency: str = ""
    payer_currency: str = ""
    convert: CurrencyInformation = field(default_factory=dict)
    sign: str = ""
    def __post_init__(self):
        self.convert = CurrencyInformation(**self.convert)

@dataclass
class Currency:
    from_service: str = ""
    to: str = ""
    course: str = ""
    
@dataclass
class CurrencyResponse:
    state: int
    result: list = field(default_factory=list)
    error: str = ""
    message: str = ""
    def __post_init__(self):
        self.result = [Currency(**change_dict_key(result_dict, "from", "from_service")) for result_dict in self.result]
    
def change_dict_key(data: dict, key: str, new_key: str) -> dict:
    if key in data:
        data[new_key] = data.pop(key)
    return data

@dataclass 
class SendTestWebhooSuccess:
    state: int
    result: dict
    
@dataclass 
class SendTestWebhooError:
    state: int
    message: str