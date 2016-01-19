"""
http://insight.bitpay.com/
"""
import logging
from time import sleep
import requests
from .. import config

def getUrl(request_string):
    """ geturl """
    while True:
        try:
            insighturl = requests.get(request_string).json()
        except Exception:
            logging.debug(requests.get(request_string))
            logging.debug(
                "Cannot get an understandable answer "
                "from Insight API, trying again in 10 seconds...",
                exc_info=True)
            sleep(10) # Wait en seconds before next attempt to contact
            insighturl = None
        if insighturl is not None:
            break
    return insighturl

def setHost():
    """ sethost """
    if config.LOCAL_BLOCKCHAIN:
        config.BLOCKCHAIN_CONNECT = ('http://localhost:3001'
                                     if config.TESTNET else 'http://localhost:3000')
    else:
        config.BLOCKCHAIN_CONNECT = ("https://test-insight.bitpay.com"
                                     if config.TESTNET else "https://insight.bitpay.com")

def check():
    """ check """
    url = config.BLOCKCHAIN_CONNECT + '/api/sync/'
    logging.info("Testing Blockchain connection at: %s", url)
    result = getUrl(url)
    if result.get('error'):
        raise Exception('Insight reports error: %s' % result['error'])
    if result.get('status') == 'error':
        raise Exception('Insight reports error: %s' % result['error'])
    if result.get('status') == 'syncing':
        logging.warning("WARNING: Insight is not fully synced to the blockchain: %s%% complete",
                        result['syncPercentage'])
    return result

def getInfo():
    return getUrl(config.BLOCKCHAIN_CONNECT + '/api/status?q=getInfo')

def getUtxo(address):
    return getUrl(config.BLOCKCHAIN_CONNECT + '/api/addr/' + address + '/utxo/')

def getAddressInfo(address):
    return getUrl(config.BLOCKCHAIN_CONNECT + '/api/addr/' + address + '/')

def getTxInfo(tx_hash):
    return getUrl(config.BLOCKCHAIN_CONNECT + '/api/tx/' + tx_hash + '/')

def getBlockInfo(block_hash):
    return getUrl(config.BLOCKCHAIN_CONNECT + '/api/block/' + block_hash + '/')

def sourceAddressesFromTX(tx_full):
    '''Return source (outbound) addresses for a bitcoin tx'''
    return [i['addr'] for i in tx_full['vin']]
