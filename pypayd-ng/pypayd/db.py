""" pypayd database handling """
import time
import logging
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy import Sequence
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

#def qNum(num_items):
#    """qNum"""
#    return ','.join('?' for i in range(num_items))

#def rowtracer(cursor, sql):
#    """rowtracer"""
#    dictionary = {}
#    for index, (name, type_) in enumerate(cursor.getdescription()):
#        dictionary[name] = sql[index]
#    return dictionary

Base = declarative_base()

class Orders(Base):
    """ Orders table definition """
    __tablename__ = 'orders'

    rowid = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    order_id = Column(String(35), unique=True)
    native_price = Column(String(10))
    native_currency = Column(String(3))
    btc_price = Column(String(15))
    item_number = Column(Integer)
    receiving_address = Column(String(35))
    created_at = Column(DateTime, default=datetime.utcnow)
    max_life = Column(Integer)
    filled = Column(Integer, default=0)

    def __repr__(self):
        str_created_at = self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        return "<Orders(native_price='%s', native_currency='%s', \
                btc_price='%s', item_number='%s', receiving_address='%s', \
                created_at='%s', max_life='%s', filled='%s')>" % (
                    self.native_price, self.native_currency, self.btc_price,
                    self.item_number, self.receiving_address, self.created_at,
                    self.max_life, self.filled)

class Payments(Base):
    """ Payments table definition """
    __tablename__ = 'payments'

    rowid = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    receiving_address = Column(String(35))
    source_address = Column(String(35))
    amount = Column(String(15))
    amount_real = Column(String(10))
    txid = Column(String(64))
    order_id = Column(String(35), unique=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    block_number = Column(Integer)
    confirmations = Column(Integer)
    valid = Column(Boolean, default=True)
    notes = Column(Text)

    def __repr__(self):
        return "<Payments(receiving_address='%s', source_address='%s', \
                amount='%s', amount_real='%s', txid='%s', \
                order_id='%s', timestamp='%s', \
                block_number='%s', confirmations='%s', \
                valid='%s', notes='%s')>" % (
                    self.receiving_address, self.source_address, self.amount,
                    self.amount_real, self.txid, self.order_id, self.timestamp,
                    self.block_number, self.confirmations, self.valid, self.notes)


class PyPayDB(object):
    """Database object using apsw (I got some mixed info regarding pysqlite threading support: there
    seems to be a flag to enable it (sqlite3 does support threading) but I saw more than a few error
    reports as well) - therefore switching to APSW seemed like the safer bet.
    """
    def __init__(self, db_name, bindings=None):
        if db_name is None:
            engine = create_engine('sqlite://',
                                   connect_args={'check_same_thread':False},
                                   poolclass=StaticPool) # use temporary in-memory database
        else:
            engine = create_engine('sqlite:////'+db_name)
        # the same but with database debugging on, switch it off for production
        #engine = create_engine('sqlite:////'+db_name, echo=True)
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        self.Session = scoped_session(session_factory)
        #self.session = Session()   # because of threading we must do it
                                    # separately for each transaction
        self.bindings = bindings

        #keep time-record of last update to tables
        self.last_updated = {"addresses": 0, "orders": 0, "payments": 0}

    # payments and invalid are insert or replace, since confirmations are updated.
    # TODO remove confirmations as table updating, and simply introduce a check to
    # make sure the transaction has not been reversed (confirmations can simply be
    # calculated after a querys as current_block - tx_block).
    def addPayment(self, bindings):
        """ addPayment """
        session = self.Session()
        newpayment = Payments(
            receiving_address=bindings['receiving_address'],
            source_address=bindings['source_address'],
            amount=bindings['amount'],
            amount_real=bindings['amount_real'],
            txid=bindings['txid'],
            order_id=bindings['order_id'],
            block_number=bindings['block_number'],
            confirmations=bindings['confirmations'],
            notes=bindings['notes'],
            valid=bindings['valid'])
        session.add(newpayment)
        self.last_updated['payments'] = time.time()
        session.commit()
        #self.Session.remove()
        return None

    def addOrder(self, bindings):
        """ addOrder """
        session = self.Session()
        neworder = Orders(
            order_id=bindings['order_id'],
            native_price=bindings['native_price'],
            native_currency=bindings['native_currency'],
            btc_price=bindings['btc_price'],
            item_number=bindings['item_number'],
            receiving_address=bindings['receiving_address'],
            max_life=bindings['max_life'])
        try:
            session.add(neworder)
            session.commit()
            self.last_updated['orders'] = time.time()
        except sqlalchemy.exc.SQLAlchemyError as e:
            logging.warning(e)
            return e
        #self.Session.remove()
        return None

    def updateOrder(self, bindings):
        session = self.Session()
        updatedbq = session.query(Orders).filter_by(order_id=bindings['order_id'])
        #updatedbq = session.query(Payments).filter_by(txid=bindings['txid'])
        order = updatedbq.one()
        order.filled = bindings['filled']
        session.commit()
        self.last_updated['orders'] = time.time()
        #self.Session.remove()
        return None

    def updatePayment(self, bindings):
        session = self.Session()
        updatedbq = session.query(Payments).filter_by(txid=bindings['txid'])
        logging.debug("updatedbq is: %s", str(updatedbq))
        payment = updatedbq.one()
        payment.confirmations = bindings['confirmations']
        session.commit()
        self.last_updated['payments'] = time.time()
        #self.Session.remove()
        return None

    def getPayments(self, bindings):
        session = self.Session()
        return session.query(Payments).filter(bindings).all()

    def getOrders(self, bindings):
        session = self.Session()
        return session.query(Orders).filter(bindings).all()

#    def updateInTable(self, table, bindings):
#        ''' update fields in a single row for a table '''
#        k = [i for i in list(bindings.keys())
#             if i not in (['txid', 'rowid']
#                          if table == 'payments' else ['order_id', 'rowid'])]
#        assert k and ('txid' in bindings.keys()
#                      or 'rowid' in bindings.keys() or 'order_id' in bindings.keys())
#        statement = "update %s" %table
#        for i in range(len(k)):
#            statement += ' AND' if i > 0 else ' SET' +' %s = :%s' %(k[i], k[i])
#        statement += " where {0} = :{0}".format([i for i in bindings
#                                                 if i in ['rowid', 'txid', 'order_id']][0])
#        self.wquery(statement, bindings)
#        self.last_updated[table] = time.time()

#    def getFromTable(self, table, bindings):
#        """Turn a list of bindings into a get query for the appropriate table, uses 'and' & '=',
#        I don't think we need comprehensive dynamic querying for 3 tables, just write an sqlite
#        statement for anything more specific."""
#        k = list(bindings.keys())
#        statement = "select * from %s" %table
#        for i, _ in enumerate(len(k)):
#            statement += (' AND' if i > 0 else ' WHERE') + ' (%s = :%s)' %(k[i], k[i])
#        return self.rquery(statement, bindings)

