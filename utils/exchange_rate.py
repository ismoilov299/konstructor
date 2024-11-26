from requests import get
import re

class ExchangeRateRussia:
    __xml_data: str = None
    def __init__(self):
        self.__xml_data = get('https://www.cbr-xml-daily.ru/daily_utf8.xml').text
    
    def get_currency(self, id: str):
        return float(re.findall(f'<Valute\s+ID=\"{id}\">.*?<Value>(.*?)</Value>', self.__xml_data)[0].replace(',', '.'))