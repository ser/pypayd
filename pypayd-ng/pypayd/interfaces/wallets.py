"""
This file contens key paths to derive addresses from supported HD wallets.
"""
def path(wallet_type, order_id):
    """ returns proper path """
    if wallet_type == "copay":
        return "0/%d" % order_id
    elif wallet_type == "electrum":
        return "%d" % order_id
    elif wallet_type == "mycelium":
        return "%d" % order_id
