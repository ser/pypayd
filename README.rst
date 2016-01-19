.. image:: https://img.shields.io/travis/ser/pypayd-ng.svg
    :target: https://travis-ci.org/ser/pypayd-ng
.. image:: https://img.shields.io/pypi/pyversions/pypayd-ng.svg
    :target: https://pypi.python.org/pypi/pypayd-ng
.. image:: https://img.shields.io/pypi/v/pypayd-ng.svg
    :target: https://pypi.python.org/pypi/pypayd-ng
.. image:: https://img.shields.io/pypi/l/pypayd-ng.svg
    :target: https://pypi.python.org/pypi/pypayd-ng
.. image:: https://img.shields.io/pypi/status/pypayd-ng.svg
    :target: https://pypi.python.org/pypi/pypayd-ng
.. image:: https://img.shields.io/pypi/format/pypayd-ng.svg
    :target: https://pypi.python.org/pypi/pypayd-ng
.. image:: https://coveralls.io/repos/github/ser/pypayd-ng/badge.svg?branch=master
    :target: https://coveralls.io/github/ser/pypayd-ng?branch=master 

pypayd-ng
=========

Pypayd is a minimalistic daemon for accepting bitcoin payments,
originally written by Alexander Maznev. This is meant to be a good
alternative if you do not want setup an account with a third-party
payment processor. Pypayd provides an API for creating orders and
automatically records order fulfillment (payment received) as well as
invalid payments.

Pypayd-NG is a rewritten version of pypayd, which automatically creates
receiving addresses for provided HD wallet, a wrapper around the pycoin
implementation of BIP32. It generates addresses compatible with modern
HD wallets from a public master-key only (note that there is no need to
store the private key on the server, it's much safer to use the public
key only!).

Installation
------------

The recommended installation is to use ``pip3 install pypayd-ng``.

If you prefer to use a developement version:
``git clone https://github.com/ser/pypayd-ng``

following that ``cd`` into the pypayd-ng directory and execute:
``pip3 install -r requirements.txt``.

Configuration
-------------

You are able to configure pypayd via creating ``pypayd.conf`` file.
Consult ``pypayd_ng/pypayd/config.py`` for configuration values.

currency exchange rates
^^^^^^^^^^^^^^^^^^^^^^^

Currently there are three sources of live currency exchange rates
available:

-  ``btcavga``: https://api.bitcoinaverage.com/ticker/global/all
-  ``bitstamp``: https://www.bitstamp.net/api/ticker
-  ``coindesk``: https://api.coindesk.com/v1/bpi/currentprice.json

Example usage
-------------

Get a wallet. Pypayd supports the following wallets out of the box:

-  Copay: ``copay`` (supports Live and Test BTC networks)
-  Electrum: ``electrum`` (supports Live BTC network only, Electrum
   versions >=2.0)
-  Mycelium: ``mycelium`` (supports Live and Test BTC networks)

| Obtain a publickey from your wallet. It should look like:
| ``tpubD8z6BcZQGXU6AVeqgkqmhDKAtfMPoX2sNyYaSzoiZYHRdJjG75f5CTbzmQ9sWCWsijwnwW9MEvVbQuckbKQoZktBjJyxL1ui4rSoAyQDnwF``
  (please do not use that public key, as it is an example only)

Insert the publickey into a file ``payment_wallet.txt`` on your online
server. Then run pypayd, specifying type of the wallet you are using
(for example Copay):

``pypayd_ng.py --server wallet --wallet-type="copay" --from-file="payment_wallet.txt"``

Then from your webserver (i.e. to create an order for a payment of 20
USD):

::

    import requests
    import json
    url = "http://127.0.0.1:3080"
    headers = {'content-type': 'application/json'}
    payload = {
        "method": "create_order",
        "params": {"amount": 20.0, "qr_code": True},
        "jsonrpc": "2.0",
        "id": 0,
    }
    response = requests.post( url, data=json.dumps(payload), headers=headers).json()

This will return an automatically created order\_id, a price converted
to Bitcoin from the ``DEFAULT_CURRENCY`` by the ``DEFAULT_TICKER``, a
receiving address, as well as a time left on the transaction (note that
the timeleft on the transaction is the time-lapse after which a payment
received for the order will not be considered valid; it may be
preferable to set a longer ``TX_LIFE`` then the one displayed to the
customer). The full argument list for ``create_order`` as follows:

::

    * amount          order amount in native currency
    * currency        takes a string such as 'USD', config.DEFAULT_CURRENCY if none
    * item_number     specify an item-number to associate  with the order in the database
    * order_id        specify an order-id, if one is not given an order-id will be created by hashing other order attributes
    * gen_new         generate a new address for the order if True, otherwise uses config settings
    * qr_code         generate a qr_code for the corresponding receiving address if True

dependencies
------------

-  Python3
-  See ``requirements.txt``
-  ``zbarimg`` binary is required for tests only, you can find it in ``zbar-tools`` package in debian/ubuntu

to do
-----

See the ``TODO.md`` list.

interfaces
----------

Pypayd-NG supports insight-api (run locally or hosted:
https://insight.bitpay.com/) and blockr (https://blockr.io/). I'll
probably add support for jmcorgan's fork of bitcoin-core with address
indexing in the near future. To configure set ``BLOCKCHAIN_SERVICE`` to
the interface Pypayd should load ("insight" or "blockr") and
``BLOCKCHAIN_CONNECT`` to the complete url in the ``pypayd.conf`` file.
