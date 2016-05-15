import re



_filters = []
def add_filter(fn):
    _filters.extend([fn])



def atoi(str):
    try:
        return int(str)
    except ValueError:
        return None


qfc_re = re.compile("QFC\s*#?(\d+)\s+(.*)", flags=re.IGNORECASE)
qfcs = { '5847' : 'Broadway at Pine, Seattle, WA' }
@add_filter
def filter_qfc(t):
    m = qfc_re.match(t.description)
    if not m: return t
    qfcid = str(m.group(1))
    t.properties['bank_memo'] = t.description
    t.description = "QFC"
    if qfcid in qfcs:
        t.description += " " + qfcs[qfcid]
    t.allocations.append((None, "food:groceries"))
    return t



def filter_imported_transaction(t):
    for fn in _filters:
        t = fn(t)
    return t

