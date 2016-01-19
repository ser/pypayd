""" get current bitcoin exchange rate """
import time
import calendar
import decimal
#import unittest
import logging
import requests
from . import config
D = decimal.Decimal

# Raise error if price return is greater than
MAX_TICKER_INTERVAL = 300

class PriceInfoError(Exception):
    """ BTC price error object """
    pass

def bitstampticker(currency='USD'):
    """ get current bitcoin exchange rate from Bitstamp """
    if currency != 'USD':
        raise PriceInfoError("Bitstamp Ticker does not currently support currencies other than USD")
    data = requests.get('https://www.bitstamp.net/api/ticker/').json()
    dataprice = data['last']
    datatime = data['timestamp']
    return dataprice, float(datatime)

def coindeskticker(currency='USD'):
    """ get current bitcoin exchange rate from Coindesk """
    data = requests.get('https://api.coindesk.com/v1/bpi/currentprice.json').json()
    dataprice = data['bpi'][currency]['rate']
    datatime = calendar.timegm(time.strptime(data['time']['updated'], "%b %d, %Y %H:%M:%S %Z"))
    return dataprice, datatime

def btcavticker(currency='USD'):
    """ get current bitcoin exchange rate from Bitcoinaverage """
    data = requests.get('https://api.bitcoinaverage.com/ticker/global/all').json()
    dataprice = data[currency]['last']
    datatime = calendar.timegm(time.strptime(
        data[currency]['timestamp'], "%a, %d %b %Y %H:%M:%S %z"))
    return dataprice, datatime

class Ticker(object):
    """ Exchange rate object """
    alltickers = {
        'bitstamp': bitstampticker,
        'coindesk': coindeskticker,
        'btcavgav': btcavticker,
        'dummy': (lambda x: (350, time.time()))
        }

    def __init__(self, ticker=None, currency=None):
        self.ticker = ticker or config.DEFAULT_TICKER
        self.currency = currency or config.DEFAULT_CURRENCY
        self.last_price = {}

    def getprice(self, ticker=None, currency=None):
        """ get rate """
        if not currency:
            currency = self.currency
        if not ticker:
            ticker = self.ticker
        #Use stored value if fetched within last 60 seconds
        if self.last_price.get(ticker, {}).get(currency):
            if self.last_price[ticker][currency][1] > time.time() - 60:
                return self.last_price[ticker][currency][0]
        btc_price, last_updated = self.alltickers[ticker](currency.upper())
        if not btc_price or (time.time() - last_updated) > MAX_TICKER_INTERVAL:
            raise PriceInfoError("Ticker failed to return BTC price or returned outdated info")
        if not self.last_price.get(ticker):
            self.last_price[ticker] = {}
        self.last_price[ticker][currency] = btc_price, last_updated
        logging.debug('1 BTC is equal to %s %s according to %s',
                      str(btc_price), str(currency), str(ticker))
        return btc_price

    # For now rounding is three-points, last four are used
    # as significant for payment records and last 1 is ignored
    def getpriceinbtc(self, amount, currency=None, ticker=None):
        """ btc price """
        if not currency:
            currency = self.currency
        if not ticker:
            ticker = self.ticker
        btc_price = D(str(self.getprice(currency=currency, ticker=ticker)))
        amount = D(str(amount))
        logging.debug('Asking amount is: %s', str(amount))
        amount_in_btc = (amount/btc_price).quantize(D('.00000000'))
        logging.debug('In BTC it is: %s',
                      str(amount_in_btc))
        return amount_in_btc

    def getpriceincurrency(self, amount, currency=None, ticker=None):
        """ btc price """
        if not currency:
            currency = self.currency
        if not ticker:
            ticker = self.ticker
        btc_price = D(str(self.getprice(currency=currency, ticker=ticker)))
        amount = D(str(amount))
        logging.debug('Asking amount is: %s BTC', str(amount))
        amount_in_currency = (amount*btc_price).quantize(D('.00'))
        logging.debug('In %s it is: %s',
                      str(currency),
                      str(amount_in_currency))
        return amount_in_currency

BTCticker = Ticker()
