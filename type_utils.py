import re
import datetime
from pipes import quote
from decimal import Decimal



def cents_from_str(s):
    s = s.strip().translate(None, ',')
    m = re.match(r"\s*\$?([,\d]+).(\d\d)", s)
    if m:
        return int(m.group(1))*100 + int(m.group(2))
    m = re.match(r"\s*\$?(\d+)", s)
    if m:
        return int(m.group(1))*100
    raise ValueError('invalid literal for Amount(): %s' % s)

def cents_to_str(c):
    if c >= 0:
        return "%d.%d" % (c//100, c % 100)
    else:
        nc = -c
        return "(%d.%d)" % (nc//100, nc % 100)

def cents_from_decimal(d):
    return int(d*100)

def cents_to_decimal(c):
    return Decimal(cents_to_str(c))



def datetime_to_date_str(d):
    return datetime.datetime.strftime(d, '%Y-%m-%d')

def datetime_from_str(str):
    try:               return datetime.datetime.strptime(str, '%Y-%m-%d')
    except ValueError: pass
    try:               return datetime.datetime.strptime(str, '%Y%m%d')
    except ValueError: pass


def quote_str(s):
    return quote(s)

def quote_str_if_needed(s):
    sq = quote_str(s)
    return s if len(sq) == len(s) + 2 else sq

