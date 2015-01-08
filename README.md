pypayd
===============

Pypayd is a small daemon (<1000 lines) for accepting bitcoin payments with light-weight dependencies. This is meant to be a good alternative if you do not want setup an account with a third-party payment processor.*
Pypayd provides an API for creating orders and automatically records order fulfillment (payment received) as well as invalid payments.

Pypayd automatically creates receiving addresses from it's own wallet, a wrapper around the pycoin implementation of BIP32**. The wallet (can generate addresses from a public or private master-key (note that there is no need to store the private key on the server). It also supports loading keys from mnemonic, byte-string, or encrypted file. 

example usage
-----------------
Obtain an encrypted-file with a publickey on an offline server from a mnemonic:

```python pypayd.py wallet --from-mnemonic " " --mnemonic-type="electrum" --to-file="payment_wallet.txt" --encrypt-pw="foobar" ```

This will generate a BIP32 wallet from the mnemonic and save only the master public key to an encrypted file. CP the file to your online server. Then run pypayd:

```python pypayd.py --server wallet --from-file="payment_wallet.txt" --encrypt-pw="foobar" ```

Then from your webserver (i.e. to create an order for a payment of 20 usd): 
```
    import requests
    import json
    url = "http://127.0.0.1:8080"
    headers = {'content-type': 'application/json'}
    payload = {
        "method": "create_order",
        "params": {"amount": 20.0, "qr_code": True} 
        "jsonrpc": "2.0",
        "id": 0,
    }
    response = requests.post( url, data=json.dumps(payload), headers=headers).json()
```

This will return an automatically created order_id, a price converted to Bitcoin from the ``DEFAULT_CURRENCY`` by the ``DEFAULT_TICKER``, a receiving address, as well as a time left on the transaction (note that the timeleft on the transaction is the time-lapse after which a payment received for the order will not be considered valid; it may be preferable to set a longer ``TX_LIFE`` then the one displayed to the customer). The full argument list for ``create_order`` as follows: 

    * amount     
    * currency      takes a string such as 'USD', config.DEFAULT_CURRENCY if none
    * item_number       specify an item-number to associate  with the order in the database
    * order_id        specify an order-id, if one is not given an order-id will be created by hashing other order attributes
    * gen_new         generate a new address for the order if True, otherwise uses config settings
    * qr_code         generate a qr_code for the corresponding receiving address if True
