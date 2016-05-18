import re
import datetime
from pipes import quote
from decimal import Decimal
from titlecase import titlecase



def cents_from_str(s):
    s = s.strip().translate(None, ',')
    m = re.match(r"\s*\$?([,\d]+).(\d\d)", s)
    if m:
        return int(m.group(1))*100 + int(m.group(2))
    m = re.match(r"\s*\$?(\d+)", s)
    if m:
        return int(m.group(1))*100
    return None

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



_find_unsafe = re.compile(r'[a-zA-Z0-9_^@%+=:,./-] \t\r\n').search

def quote_str(s):
    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return "\"" + s.replace("\"", "\\\"") + "\""

def quote_str_if_needed(s):
    return s if not _find_unsafe(s) is None else quote_str(s)

_acronyms = [
        'TCP', 'UDP',
        'LLC',
        'WA', 'CA', 'OR', 'NY',
        ]
def _titlecase_callback(s, **kwargs):
    s = s.upper()
    if s in _acronyms: return s

def titlecase_str(s):
    return titlecase(s, callback=_titlecase_callback)
