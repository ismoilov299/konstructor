from dataclasses import dataclass
import hashlib
import base64
import json
import requests
from . import models


@dataclass
class Cryptomus:
    URL = "https://api.cryptomus.com"
    merchant: str
    API_KEY: str

    def gen_sign(self, data: dict):
        a = json.dumps(data, ensure_ascii=False).encode('utf-8')
        base = base64.b64encode(a)
        sign = hashlib.md5(base + self.API_KEY.encode("utf-8")).hexdigest()
        return sign

    def gen_sign_to_check(self, data: dict):
        a = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        base = base64.b64encode(a)
        sign = hashlib.md5(base + self.API_KEY.encode("utf-8")).hexdigest()
        return sign

    def get_header(self, data: dict) -> dict:
        sign = self.gen_sign(data)
        return {
            "merchant": self.merchant,
            "sign": sign,
            "Content-Type": "application/json",
        }

    def add_payment(self,
                    amount: float,
                    currency: str,
                    order_id: str,
                    network: str = None,
                    url_return: str = None,
                    url_callback: str = None,
                    is_payment_multiple: bool = None,
                    lifetime: str = None,
                    to_currency: str = None,
                    subtract: int = None,
                    accuracy_payment_percent: int = None,
                    additional_data: list = None,
                    currencies: list = None,
                    except_currencies: list = None,
                    discount_percent: int = None,
                    ):
        url = f"{self.URL}/v1/payment"
        query = {
            "amount": amount,
            "currency": currency,
            "order_id": order_id,
        }
        if network:
            query["network"] = network
        if url_return:
            query["url_return"] = url_return
        if url_callback:
            query["url_callback"] = url_callback
        if is_payment_multiple:
            query["is_payment_multiple"] = is_payment_multiple
        if lifetime:
            query["lifetime"] = lifetime
        if to_currency:
            query["to_currency"] = to_currency
        if subtract:
            query["subtract"] = subtract
        if accuracy_payment_percent:
            query["accuracy_payment_percent"] = accuracy_payment_percent
        if additional_data:
            query["additional_data"] = additional_data
        if currencies:
            query["currencies"] = currencies
        if except_currencies:
            query["except_currencies"] = except_currencies
        if discount_percent:
            query["discount_percent"] = discount_percent
        header = self.get_header(query)
        response = requests.post(url, json=query, headers=header).json()
        if "result" in response:
            res = response["result"]
            res = models.change_dict_key(res, "from", "from_wallet")
            return models.Payment(**res)
        elif 'errors' in response:
            return response['errors']
        res: str = response["message"]
        return res

    def create_static_wallet(
            self,
            network: str,
            currency: str,
            order_id: str,
            url_callback: str = None,
    ):
        url = f"{self.URL}/v1/wallet"
        query = {
            "network": network,
            "currency": currency,
            "order_id": order_id,
        }
        if url_callback:
            query["url_callback"] = url_callback
        header = self.get_header(query)
        response = requests.post(url, json=query, headers=header).json()
        if "result" in response:
            res = response["result"]
            return models.CreateStaticWalletResponse(**res)
        return None

    def services(self):
        url = f"{self.URL}/v1/payment/services"
        header = self.get_header({})
        response = requests.post(url, json={}, headers=header).json()
        return models.ServiceResponse(**response)

    def currency(self, currency: str):
        url = f"{self.URL}/v1/exchange-rate/{currency}/list"
        header = self.get_header({})
        response = requests.get(url, json={}, headers=header).json()
        return models.CurrencyResponse(**response)

    def send_test_webhook_payment(self, url_callback: str, currency: str, network: str, uid: str = None,
                                  order_id: str = None, status: str = "paid"):
        if not uid and not order_id:
            raise ValueError("uid or order_id is required")
        ulr = f"{self.URL}/v1/test-webhook/payment"
        query = {
            "url_callback": url_callback,
            "status": status,
            "currency": currency,
            "network": network,
        }
        if uid:
            query["uuid"] = uid
        if order_id:
            query["order_id"] = order_id
        header = self.get_header(query)
        res = requests.post(ulr, json=query, headers=header).json()
        return json.dumps(res)
