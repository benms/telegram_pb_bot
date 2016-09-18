# -*- coding: utf-8 -*-
import re
import requests
import json
import datetime as dt
import calendar as cal
from functools import reduce
import mongodb

URL = 'https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5'
URL_DAY = 'https://api.privatbank.ua/p24api/exchange_rates?json&date='
FROM_CACHE = 'from cache'
NOT_FROM_CACHE = 'not from cache'


def load_exchange():
    return json.loads(requests.get(URL).text)


def load_day_exchange(dte=''):
    """ Load day exchange
    :param dte is string of date in UA standard example 10.12.2016
    :return real
    """
    dte = dte if ((type(dte) is str) and (len(dte) > 0) and (len(dte.split('.')) > 0)) else get_current_date()
    url = URL_DAY + dte
    data_from_cache = mongodb.get_curr_doc_by_date(dte)
    if not data_from_cache:
        data = json.loads(requests.get(url).text)
        mongodb.insert_arch_data(data)
        mongodb.write_log(NOT_FROM_CACHE)
    else:
        data = data_from_cache
        mongodb.write_log(FROM_CACHE)
    data = data[u'exchangeRate']
    usd_list = filter(lambda el: el[u'currency'] == "USD", data)
    usd = list(usd_list).pop()
    return usd[u'saleRate']


def get_current_date():
    """ Get current string of date
     :return string
    """
    now = dt.datetime.now()
    return ".".join(map(lambda el: str(el), [now.day, now.month, now.year]))


def get_last_month_days_range(monnth_num=0):
    """ Get last month days range
    :param monnth_num the number of month in year
    :return list of days
    """
    now = dt.datetime.now()
    if monnth_num:
        prev_month = monnth_num
        prev_year = now.year
    else:
        prev_month = 12 if (now.month == 1) else now.month - 1
        prev_year = now.year - 1 if (now.month == 1) else now.year
    m_range = cal.monthrange(prev_year, prev_month)
    date_a = dt.date(prev_year, prev_month, m_range[0] + 1)
    date_b = dt.date(prev_year, prev_month, m_range[1])
    date_delta = date_b - date_a
    days_list = [(date_a + dt.timedelta(days=delta)) for delta in range(date_delta.days + 1)]
    days_list_str = map(lambda el: str(el.day) + '.' + str(el.month) + '.' + str(el.year), days_list)
    return days_list_str


def get_month_stat(monnth_num=0):
    """ Get month stat
    :param monnth_num the number of month in year
    :return list of exchange for month
    """
    days = get_last_month_days_range(monnth_num)
    return [load_day_exchange(day) for day in days]


def get_month_average_usd_stat(monnth_num=0):
    """ Get month average USD stat
    :param monnth_num the number of month in year
    :return average month sell number
    """
    month_list_stat = get_month_stat(monnth_num)
    sum_stat = reduce(lambda acc, el: acc+el, month_list_stat)
    return round(sum_stat / len(month_list_stat), 3)


def get_exchange(ccy_key):
    for exc in load_exchange():
        if ccy_key == exc['ccy']:
            return exc
    return False


def get_exchanges(ccy_pattern):
    result = []
    ccy_pattern = re.escape(ccy_pattern) + '.*'
    for exc in load_exchange():
        if re.match(ccy_pattern, exc['ccy'], re.IGNORECASE) is not None:
            result.append(exc)
    return result
