# -*- coding: utf-8 -*-
import datetime
from pymongo import MongoClient
from config import MONGO_DB_URL
from config import IS_ENABLED_MONGO_LOG

db_conn = MongoClient(MONGO_DB_URL)
ARCH = 'archive_currency'
LOG = 'log'


def get_collection(name=ARCH):
    result = None
    if db_conn:
        if name == ARCH:
            result = db_conn.pb_curr.arch
        elif name == LOG:
            result = db_conn.log.pb_curr
    return result


def insert_arch_data(data):
    col = get_collection(ARCH)
    doc_id = None
    if type(data) is dict:
        doc_id = col.insert(data)
    return doc_id


def write_log(data=None):
    col = get_collection(LOG)
    doc_id = None
    if IS_ENABLED_MONGO_LOG:
        doc_id = col.insert({u'date': datetime.datetime.utcnow(), u'data': data})
    return doc_id


def get_curr_doc_by_date(sel_date):
    result = None
    col = get_collection()
    if type(sel_date) is str:
        result = col.find_one({'date': sel_date})
    return result
