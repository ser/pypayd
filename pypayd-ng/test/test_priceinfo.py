import time
import unittest
import decimal
from pypayd import priceinfo

class PriceInfoTests(unittest.TestCase):

    def testDummyTicker(self):
        self.assertEqual(priceinfo.BTCticker.getprice(ticker="dummy"), 350)
        self.assertEqual(priceinfo.BTCticker.getpriceinbtc(ticker="dummy", amount=175.0), 0.5)

    def testBitstampTicker(self):
        btc_price, last_updated = priceinfo.bitstampticker()
        self.assertTrue((time.time() - float(last_updated) < priceinfo.MAX_TICKER_INTERVAL))
        self.assertTrue(float(btc_price) > 0)

    def testCoindeskTicker(self):
        btc_price, last_updated = priceinfo.coindeskticker()
        self.assertTrue((time.time() - float(last_updated) < priceinfo.MAX_TICKER_INTERVAL))
        self.assertTrue(float(btc_price) > 0)

    def testBitcoinaverageglobalaverageTicker(self):
        btc_price, last_updated = priceinfo.btcavticker()
        self.assertTrue((time.time() - float(last_updated) < priceinfo.MAX_TICKER_INTERVAL))
        self.assertTrue(float(btc_price) > 0)

    def testTicker(self):
        ticker = priceinfo.Ticker(currency='EUR', ticker='btcavgav')
        price = ticker.getpriceinbtc(amount=100)
        # ticker returns a Decimal
        self.assertTrue(isinstance(price, decimal.Decimal))
        # ticker retruns a Decimal quantized to 8 digits
        self.assertTrue(len(str(price).split('.')[1]) == 8)

if __name__ == '__main__':
    unittest.main()
