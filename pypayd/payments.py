"""pypayd payments module"""

import json
import datetime
import decimal
import time
import threading
import logging
from hashlib import sha1
from pycoin.encoding import b2a_base58
from . import config
from .db import Orders, Payments
from .priceinfo import BTCticker
from .interfaces.wallets import path

D = decimal.Decimal
def normalize_amount(amount):
    """ store money without commas """
    return D(str(amount)).quantize(D('.0000000'))

def ensure_list(list_ensured):
    """ ensure_list """
    return list_ensured if isinstance(list_ensured, list) else [list_ensured]

def extract_special_digits(amount):
    """ extract_special_digits """
#   if type(amount) is not decimal.Decimal:
    if not isinstance(amount, decimal.Decimal):
        amount = D(str(amount)).quantize(D('.0000000'))
    return int(str(amount)[-4:])

class ProcessingError(Exception):
    """ empty """
    pass

class PaymentHandler(object):
    """
    The Payment Handler class - this basically handles all the payment logic connecting all
    the other interfaces (wallet, db, api, message_feed, blockchain_interface)
    """
    # One particular aspect of current transaction handling is that order's are not given a
    # block_number; on creation, for an order to be filled #a payment must be received within
    # a certain time - in otherwords Pypay does not check if the payment was made prior to
    # order creation - #this may be convenient in certain cases (i.e. resubmitting an order
    # to validate an invalid payment), the major drawback is that addresses #that are used
    # for other functions should NOT be used as payment addresses
    #Todo - Add a configureable flag to disable this behaviour
    def __init__(self,
                 pypayd_database,
                 pypayd_wallet,
                 pypayd_wallet_type,
                 bitcoin_interface_name=None):
        self.locks = {'order': threading.Lock(), 'polling':threading.Lock()}
        self.polling = {'addresses': [], 'last_updated': 0}
        self.database = pypayd_database
        self.wallet = pypayd_wallet
        self.wallet_type = pypayd_wallet_type
        if not bitcoin_interface_name:
            bitcoin_interface_name = config.BLOCKCHAIN_SERVICE
        self.bitcoin_interface_name = bitcoin_interface_name
        exec("from .interfaces import %s" %bitcoin_interface_name) #instead of 6 lines of importlib
        global bitcoin_interface
        bitcoin_interface = eval(bitcoin_interface_name)
        bitcoin_interface.setHost()

#    def checkPriceInfo(self):
#        return BTCticker.getprice()

    #fix blockchain service imports
    def checkBlockchainService(self):
        return bitcoin_interface.check()

    #Runs address polling for new payments
    def run(self):
        """ run """
        self.poller_thread = threading.Thread(target=self._run, daemon=True)
        self.poller_thread.start()
        return self.poller_thread.is_alive(), self.poller_thread.ident

    def _run(self, polling_delay=config.POLLING_DELAY):
        while True:
            t = time.time()
            self.pollActiveAddresses()
            try:
                time.sleep((config.POLLING_DELAY - (time.time() - t)))
            except Exception:
                logging.debug("I got provided some strange time for sleep:", exc_info=True)
                time.sleep(10) # if we get a negative value, let us sleep 10 seconds

    def get_payments(self, bindings):
        payments = self.database.getPayments(bindings)
        return payments

    def update_active_addresses(self):
        '''If the database has been updated, refresh the list of active addresses'''
        if self.database.last_updated['addresses'] >= self.polling['last_updated'] \
                or time.time() - 600 > self.polling['last_updated']:
            #Get all addresses that have not been stale for longer than leaf poll life
            addresses = self.database.getOrders(Orders.created_at >
                                                time.time() -
                                                config.POLL_LIFE)
            logging.info('addresses %s', addresses)
            self.polling['addresses'] = [i.receiving_address for i in addresses]
            self.polling['last_updated'] = time.time()

    def poll_address(self, addr):
        """ TODO """
        logging.info('calling %s api for address info %s', self.bitcoin_interface_name, addr)
        unspent_tx = bitcoin_interface.getUtxo(addr)
        if unspent_tx:
            logging.debug("Found %i utxo for address %s processing...", len(unspent_tx), addr)
        for txn in unspent_tx:
            #logging.debug(("tx: ", txn))
            self.processTxIn(addr, txn)

    #Add socketio listener option for locally hosted insight-api
    def pollActiveAddresses(self):
        '''Polling for inbound transactions to active addresses'''
        with self.locks['polling']:
            self.current_block = bitcoin_interface.getInfo()['info']['blocks']
            self.update_active_addresses()
            logging.info("Current block is %s polling %i active addresses",
                         self.current_block, len(self.polling['addresses']))
            #No locks here, since _run() is locked atm.. We could thread this but it doesn't seem important.
            for addr in self.polling['addresses']:
                self.poll_address(addr)

    def pollPayments(self, bindings):
        if not bindings.get('receiving_address'):
            orders = self.database.getOrders(bindings)
        bindings['receiving_address'] = orders[0]['receiving_address']
        self.poll_address(orders[0]['receiving_address'])
        time.sleep(.5)
        return self.get_payments(bindings)

    def processTxIn(self, receiving_address, tx):
        '''This method handles transactions inbound to active addresses '''
        notes = []
        logging.debug("receiving address: %s, tx: %s", receiving_address, tx)
        timestamp = datetime.datetime.utcnow()
        tx_full = bitcoin_interface.getTxInfo(tx['txid'])
        tx_record = self.database.getPayments(Payments.txid == tx['txid'])
        amount = normalize_amount(tx['amount'])
        logging.debug("tx_full: %s", str(tx_full))

        orders = self.database.getOrders(Orders.receiving_address == receiving_address)
        order = orders[0]
        order_id = order.order_id

        amount_real = str(BTCticker.getpriceincurrency(amount, currency=order.native_currency))

        if len(tx_record) > 0:  # we already registered this payment and we just
                                # want to update details in connection to number of confirmations

            tx_record = tx_record[0]
            # If a payment exists but has been recorded with less confirmations
            # than we have in the local database, update the confirmation number
            if tx_record.confirmations != tx['confirmations']:
                self.database.updatePayment(
                    {"txid": tx["txid"], "confirmations": tx['confirmations']})
                logging.debug("We have updated payment to %s confirmations",
                              tx['confirmations'])
            else:
                logging.debug("The number of confirmations has not changed.")
            # Mark order as filled if we reached required number of
            # confirmations in required timeframe
            logging.debug("Checking if the order is filled...")
            logging.debug("order.filled: %s, tx_record.valid: %s, confirmations: %s, "
                          "order.created_at: %s, timestamp: %s, TD: %s, TD-: %s",
                          str(order.filled),
                          str(tx_record.valid),
                          str(tx['confirmations']),
                          str(order.created_at),
                          str(timestamp),
                          str(datetime.timedelta(seconds=config.ORDER_LIFE)),
                          str(timestamp - datetime.timedelta(seconds=config.ORDER_LIFE)))
            if order.filled == 0 and \
                    tx_record.valid is True and \
                    tx['confirmations'] >= config.PAID_ON_CONFIRM and \
                    order.created_at >= timestamp - datetime.timedelta(seconds=config.ORDER_LIFE):
                logging.debug("Yes, the order is filled, processing database...")
                self.database.updateOrder({'order_id': order_id, 'filled': tx['txid']})
                logging.info("ORDER %s IS PAID!!! We required %s confirmations.",
                             order_id, config.PAID_ON_CONFIRM)
            elif order.filled != 0:
                logging.debug("This order was already paid and marked as filled.")
            return True # we do not process this payment further in this iteration

        else:
            valid = True # we assume that order is valid
            # A matching order has been found - let's register it in payments
            # database and verify other validity parameters
            if amount < D(order.btc_price):
                valid = False
                notes.append("amount received is less than btc_price required for order_id %s"
                             %order_id)
            elif amount > D(order.btc_price) + D('.00001'):
                notes.append("transaction with order_id %s overpaid amount by %s"
                             %(order_id, str(amount - D(order.btc_price))))
            # processing as config.ORDER_LIFE allows some control (i.e. if there was a server
            # shutdown and we want to process old orders) blockchain timestamps are
            # unfortunatly not very accurate
            logging.debug("order.created_at: %s, timestamp: %s, "
                          "timedelta: %s, timestamp-timedelta: %s",
                          str(order.created_at), str(timestamp),
                          str(datetime.timedelta(seconds=config.ORDER_LIFE)),
                          str(timestamp - datetime.timedelta(seconds=config.ORDER_LIFE))
                         )
            if order.created_at <= timestamp - datetime.timedelta(seconds=config.ORDER_LIFE):
                valid = False
                notes.append("transaction received after expiration time for order_id %s" %order_id)
            if order.filled != 0 and order.filled != tx['txid']:
                valid = False
                notes.append("payment for order_id %s has already been received with txid %s"
                             %(order_id, order.filled))
            logging.debug(("txid: ", tx['txid'], "Valid:", str(valid), "Notes:", str(notes)))
            sources = str(bitcoin_interface.sourceAddressesFromTX(tx_full))
            #payment record
            bindings = {
                'receiving_address': receiving_address,
                'txid': tx['txid'],
                'source_address': sources,
                'confirmations': tx.get('confirmations', 0),
                'block_number': (self.current_block - tx.get('confirmations', 0)),
                'notes': str(notes),
                'order_id': order_id,
                'valid': valid,
                'amount': str(amount),
                'amount_real': str(amount_real),
            }
            self.database.addPayment(bindings)
        # Send event to socketio / ZMQ feed
        # There should either be a dummy feed class or a self
        # method which will do nothing if config.ZMQ_FEED = False
        # feed.publishMessage("payments", "new", str(bindings))
        return True

    def create_order(self, amount, currency=config.DEFAULT_CURRENCY,
                     item_number=None, order_id=None):
        '''The main order creation method to which the api call is routed'''
        # Try ret
        btc_price = str(BTCticker.getpriceinbtc(amount, currency=currency))
        logging.info('Creating new order amount %s in currency %s, which gives %s in bitcoin',
                     str(amount), currency, str(btc_price))
        # if error: return error
        with self.locks['order']:
            receiving_address = self.get_payment_address()
        if not receiving_address:
            return "Failed to obtain payment address stuff!!!!!!!!!!!"
        logging.info('Preparing address %s for that payment', receiving_address)
        # Hash an order_id as base58 - because if someone needs to reference it
        # the bitcoin standard is the most readable.
        # Note that the pycoin to_long method reads bytes as big endian.
        if not order_id:
            order_id = b2a_base58(
                sha1(json.dumps(
                    {'price': str(btc_price),
                     'address': str(receiving_address)
                    }).encode("utf-8")).digest())
        logging.info('Order id is %s', str(order_id))
        timeleft = config.ORDER_LIFE
        logging.info('Time left for payment is %s seconds.', str(timeleft))
        err = self.database.addOrder({'order_id': order_id,
                                      'native_price': amount,
                                      'native_currency': currency,
                                      'btc_price': btc_price,
                                      'item_number': item_number,
                                      'receiving_address': receiving_address,
                                      'max_life': timeleft})
        if err:
            return {'error': str(err)}
        return {'amount': btc_price, 'receiving_address': receiving_address,
                'order_id': order_id, 'timeleft': timeleft}

    def get_payment_address(self, order_id=None):
        '''
        Obtain a payment address
        '''
        session = self.database.Session()
        if order_id is None:
            # create a new address from the HD wallet
            orders_counter = session.query(Orders).count()
            tmpwallet = self.wallet.subkey_for_path(path(self.wallet_type, orders_counter+1))
            address = tmpwallet.address(use_uncompressed=False)
            logging.debug("generated new address %s at path %s", str(address),
                          path(self.wallet_type, orders_counter+1))
            self.database.last_updated['addresses'] = time.time()
            #self.database.Session.remove()
        else:
            # get the previously generated address from orders table
            address = session.query(
                Orders.receiving_address).filter(Orders.order_id == order_id)
            #self.database.Session.remove()
        return address
