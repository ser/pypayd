""" pypayd default configuration """
# Defaults - overridable via. pypayd.conf or command-line arguments
DEFAULT_TICKER = 'btcavgav'
DEFAULT_CURRENCY = 'USD'
DEFAULT_WALLET_FILE = 'wallet.txt'
DB = None
DEFAULT_DB = "pypayd.db"
DEFAULT_TESTNET_DB = "pypayd_testnet.db"
# Pypay server settings
RPC_HOST = '127.0.0.1'
RPC_PORT = 3080
VERSION = 0.2
AUTH_REQUIRED = True
# Blockchain
TESTNET = False
LOCAL_BLOCKCHAIN = False
BLOCKCHAIN_CONNECT = 'http://localhost:3001' #'https://test-insight.bitpay.com' #None
BLOCKCHAIN_SERVICE = 'insight'
# delay between requests to the blockchain service for new transactions
POLLING_DELAY = 60 # seconds
# maximum amount of time an order received for generated amount will be considered valid
ORDER_LIFE = 86400 # 86400 seconds = 24 hours
# time from last order creation, after which an adress is considered stale and no longer polled
POLL_LIFE = ORDER_LIFE*7 # one week

# log file settings
LOG = None
MAX_LOG_SIZE = 16*1024*1024

# On which confirmation you assume that order is paid.
# You can lower this value if you want speedier transactions,
# but there always is some risk if the value is lower than 6.
PAID_ON_CONFIRM = 6

DATA_DIR = ""
RPC_USER = 'user'
RPC_PASSWORD = 'password'

# INTERNAL
STATE = {"last_order_updates": {"order_id":None, "timestamp": None}}

# UNUSED
ZMQ_BIND = None
ZMQ_FEED = False
SOCKETIO_BIND = None
SOCKETIO_FEED = False
