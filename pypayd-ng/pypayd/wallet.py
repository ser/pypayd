"""wallet.py"""
import os
from pycoin.key import Key
from . import config
#from .errors import PyPayWalletError

NETCODES = {"mainnet": "BTC", "testnet": "XTN"}

def get_netcode():
    """ the bitcoin network we operate on """
    return NETCODES['testnet' if config.TESTNET else 'mainnet']

def get_wallet_from_file(file_dir=None, file_name=None, netcode=None):
    """
    Wallet wrapper around the Pycoin implementation. (Pycoin is a little heavier of
    a dependency than we need, but it already supports python3 and keypath-address handling).

    The PublicKey for the branch specified in the configfile must be loaded at startup,
    branches take default numbers. Hardened branch's are not supported (since hardened
    branches require the root-key to be a private-key which should not be used
    on the payment server).

    get content of wallet file, verify if it is an xpub and return as BIP32 HD key
    """
    if file_dir is None:
        file_dir = config.DATA_DIR
    if file_name is None:
        file_name = config.DEFAULT_WALLET_FILE
    if netcode is None:
        netcode = get_netcode()
    data = open(os.path.join(file_dir, file_name), 'r').read().splitlines()
    key = Key.from_text(data[0]) # we need only the first line which should contain xpub
    key._netcode = netcode
    wallet = key.public_copy()
    return wallet
