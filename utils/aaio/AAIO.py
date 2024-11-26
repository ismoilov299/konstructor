from dataclasses import dataclass
import hashlib
from urllib.parse import urlencode
import requests
from . import models


@dataclass
class AAIO:
    MAGAZINE_ID: str
    SECRET_KEY_1: str
    SECRET_KEY_2: str
    API_KEY: str
    __url = "https://aaio.so/"
    def __gen_header(self):
        return {
            "Accept": "application/json",
            "X-Api-Key": f"{self.API_KEY}",
        }
    def __request(self, url: str, data: dict = None):
        if not data:
            data = {}
        headers = self.__gen_header()
        return requests.post(f"{self.__url}{url}", headers=headers, data=data)            
        
    def __check_error(self, response: requests.Response):
        if response.status_code == 200:
            data = response.json()
            if data['type'] == 'success':
                return data
        raise Exception(f"{response.status_code} {response.json()['message']}")        
        
    def get_balance(self):
        response = self.__request("api/balance")
        return models.Balance(**self.__check_error(response))
    def get_payment_methods(self):
        params = {
            'merchant_id': self.MAGAZINE_ID
        }
        response = self.__request("api/methods-pay", params)
        return models.PaymentMethodResponse(**self.__check_error(response))
    def get_payout_methods(self):
        response = self.__request("api/methods-payoff")
        return models.PayoutMethodResponse(**self.__check_error(response))
    def get_rates_payoff(self):
        response = self.__request("api/rates-payoff")
        return models.Rate(**self.__check_error(response))
    @staticmethod
    def gen_sign(magazine_id: str, secret_key: str, amount: float, order_id: str, currency: models.Currency = models.Currency.RUB):
        sign = ':'.join([
            magazine_id,
            str(amount),
            currency,
            secret_key,
            order_id            
        ])
        return hashlib.sha256(sign.encode('utf-8')).hexdigest()
    def payment(self, amount: float, order_id: str, desc: str = "", lang: models.Lang = models.Lang.RU, currency: models.Currency = models.Currency.RUB):
        sign = AAIO.gen_sign(self.MAGAZINE_ID, self.SECRET_KEY_1, amount, order_id, currency)
        params = {
            'merchant_id': self.MAGAZINE_ID,
            'amount': amount,
            'currency': currency,
            'order_id': order_id,
            'sign': sign,
            'desc': desc,
            'lang': lang            
        }
        url = f"{self.__url}merchant/pay?{urlencode(params)}"
        return url
    def payout(self, amount: str, order_id: str, wallet: str, method: str, commission_type: int = 0):
        params = {
            'my_id': order_id,
            'method': method,
            'amount': amount,
            'wallet': wallet,
            'commission_type': commission_type,
        }        
        response = self.__request("api/create-payoff", params)
        return self.__check_error(response)
    @staticmethod
    def get_ips():
        response = requests.get(f"https://aaio.so/api/public/ips")
        return response.json()['list']