from collections import defaultdict
from time import time
import requests

MAX_AGE = 5 * 60
KURL = 'https://api.kraken.com/0/public/Ticker?pair=BTCEUR'


class RateError(Exception):
    pass


class Fiat:
    """Conversions satoshis/euros at the Kraken exchange rate"""

    def __init__(self):
        self._cache = defaultdict(lambda: (0, 0))

    def get_rate(self, max_age=MAX_AGE):
        if time() - self._cache['eur'][1] > max_age:
            try:
                data = requests.get(KURL).json()
            except:
                raise RateError
            else:
                if data['error']:
                    raise RateError
                price = float(data['result']['XXBTZEUR']['c'][0])
                self._cache['eur'] = (price, time())
        return self._cache['eur'][0]

    def to_fiat(self, satoshis, max_age=MAX_AGE):
        rate = self.get_rate(max_age)
        return round(satoshis * rate / 1e8, 2)

    def to_satoshis(self, amount, max_age=MAX_AGE):
        rate = self.get_rate(max_age)
        return int(amount / rate * 1e8)

    def to_fiat_str(self, satoshis, max_age=MAX_AGE):
        return '{:.2f} €'.format(self.to_fiat(satoshis, max_age))


def get(url):

    try:
        data = requests.get(KURL).json()
    except ConnectionError:
        raise RateError
    else:
        return data
