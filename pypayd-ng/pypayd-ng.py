#!/usr/bin/env python3
""" pypayd-ng: https://github.com/ser/pypayd-ng"""

import os
import sys
import argparse
import logging
import logging.handlers
from ast import literal_eval
import appdirs
from configobj import ConfigObj
from pypayd import wallet, db, payments, api, config

def try_type_eval(val):
    """try_type_eval(val)"""
    try:
        return literal_eval(val)
    except: # pylint: disable=W0702
        return val

if __name__ == '__main__':
    # pylint: disable=C0103
    parser = argparse.ArgumentParser(prog='pypayd',
                                     description='A small daemon for processing bitcoin payments')
    subparsers = parser.add_subparsers(dest='action', help='available actions')


    parser.add_argument("-S", "--server", help="run pypayd", action='store_true')
    parser.add_argument('-V', '--version', action='version', version="pypayd v%s" % config.VERSION)
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False,
                        help='sets log level to DEBUG instead of WARNING')
    parser.add_argument('--testnet', action='store_true', default=False,
                        help='run on Bitcoin testnet')
    parser.add_argument('--data-dir', help='override default directory for config and db files')
    parser.add_argument('--config-file', help='the location of the configuration file')
    parser.add_argument('--log-file', help='the location of the log file')
    parser.add_argument('--pid-file', help='the location of the pid file')

    parser.add_argument('--rpc-host',
                        help='the IP of the interface to bind to for providing \
                        API access (0.0.0.0 for all interfaces)')
    parser.add_argument('--rpc-port', type=int, help='port on which to provide API access')
    parser_wallet = subparsers.add_parser('wallet', help='access pypayd wallet from command-line')
    parser_wallet.add_argument("--from-file",
                               help="load wallet info from specified file",
                               nargs='?', const=config.DEFAULT_WALLET_FILE)
    parser_wallet.add_argument('--wallet-type', help='type of the wallet you are using', \
                               choices=['copay', 'electrum', 'mycelium'], required=True)

    args = parser.parse_args()

    def exitPyPay(message, exit_status=0):
        """exitPyPay(message, exit_status=0)"""
        logging.info(message)
        sys.exit(exit_status)

    if len(sys.argv) < 2:
        exitPyPay("No arguments received, exiting...")

    if not config.__dict__.get('DATA_DIR'):
        config.DATA_DIR = args.data_dir or appdirs.user_data_dir(appauthor='pik',
                                                                 appname='pypayd', roaming=True)
    if not os.path.exists(config.DATA_DIR):
        os.makedirs(config.DATA_DIR)
    # read the .conf file and stuff it into config.py
    print("Loading config settings...")
    conf_file = os.path.join((args.config_file or config.DATA_DIR), "pypayd.conf")
    # create an empty local config file if it does not exist
    if not os.path.exists(conf_file):
        with open(conf_file, 'w') as wfile:
            wfile.write("[Default]")
    conf = ConfigObj(conf_file)
    # This will raise on a conf file without a [Default] field
    #  and will not set values that are not in config.py
    # Might change this behaviour later
    for field, value in conf['Default'].items():
        try:
            if field.upper() in config.__dict__.keys():
                config.__dict__[field.upper()] = (try_type_eval(value))
        except: # pylint: disable=W0702
            print("Error handling config file field %s, %s" %(field, value))

    #set standard values to default or args values if they have not been set
    if not config.__dict__.get('PID'):
        config.PID = (args.pid_file or os.path.join(config.DATA_DIR, "pypayd.pid"))
    if not config.__dict__.get("LOG"):
        config.LOG = (args.log_file or os.path.join(config.DATA_DIR, "pypayd.log"))
    config.RPC_PORT = (args.rpc_port or config.RPC_PORT)
    config.RPC_HOST = (args.rpc_host or config.RPC_HOST)
    config.TESTNET = (True if args.testnet else config.TESTNET)
    if not config.__dict__.get('DB'):
        config.DB = config.DEFAULT_TESTNET_DB if config.TESTNET else config.DEFAULT_DB

    #write pid to file
    pid = str(os.getpid())
    pid_file = open(config.PID, 'w')
    pid_file.write(pid)
    pid_file.close()

    #logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    fileh = logging.handlers.RotatingFileHandler(config.LOG,
                                                 maxBytes=config.MAX_LOG_SIZE, backupCount=5)
    fileh.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    formatter = logging.Formatter('[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} '
                                  '%(levelname)s - %(message)s', '%m-%d %H:%M:%S')
    fileh.setFormatter(formatter)
    logger.addHandler(fileh)
    #So we aren't spammed with requests creating new connections every poll
    logging.getLogger("requests").setLevel(logging.WARN)

    # for debug purposes dump the current configuration
    #logging.debug("Configuration: %s", str(config))

    #print(args, "\n")
    if args.action == 'wallet':
        if not args.from_file:
            exitPyPay("No arguments provided for wallet, Exiting...")
        elif args.from_file:
            pypay_wallet = wallet.get_wallet_from_file(file_name=args.from_file)
            print(pypay_wallet)
        if not pypay_wallet:
            exitPyPay("Unable to load wallet, Exiting...")
        logging.info("Wallet loaded: %s", pypay_wallet.public_copy())

    if args.server:
        try:
            assert pypay_wallet
        except NameError:
            exitPyPay("A wallet is required for running the server, Exiting...")
        print(config.DATA_DIR, config.DB, "\n")
        database = db.PyPayDB(os.path.join(config.DATA_DIR, config.DB))
        logging.info("DB loaded: %s", config.DB)
        if not database:
            exitPyPay("Unable to load SQL database, Exiting...")
        payment_handler = payments.PaymentHandler(
            pypayd_database=database,
            pypayd_wallet=pypay_wallet,
            pypayd_wallet_type=args.wallet_type,
            bitcoin_interface_name=config.BLOCKCHAIN_SERVICE
            )
        if not payment_handler:
            exitPyPay("Unable to start Payment Handler, Exiting...")
        #logging.info("Testing priceinfo ticker: %s BTC/USD" %(payment_handler.checkPriceInfo()))
        payment_handler.checkBlockchainService()
        api_serv = api.API()
        try:
            logging.info("Payment Handler loaded, starting auto-poller..")
            payment_handler.run()
            api_serv.serve_forever(payment_handler, threaded=False)
        except KeyboardInterrupt:
            api_serv.server.stop()
        exitPyPay("Interrupted, Exiting...")
