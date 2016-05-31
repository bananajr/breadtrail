import re

from type_utils import *



_filters = []
def add_filter(fn):
    _filters.extend([fn])



def atoi(str):
    try:
        return int(str)
    except ValueError:
        return None


_subs = [
        # Restaurants
        ("LITTLE WATER CANTINA.*", "Little Water Cantina", "food:restaurants"),
        ("MEXICO CANTINA.*", "Mexico Cantina", "food:restaurants"),
        ("BLUE WATER TACO GRILL - 5.*", "Blue Water Taco Grill (515 Union St.)", "food:restaurants"),
        ("ST CLOUDS.*", "St. Clouds Restaurant", "food:restaurants"),
        ("RAVISH\s+SEATTLE.*", "Ravish Restaurant in Eastlake", "food:restaurants"),
        ("VIA TRIBUNALI.*", "Via Tribunali Restaurant", "food:restaurants"),
        ("GP\*BOTTLEHOUSE.*", "Bottlehouse (Madrona)", "food:restaurants"),
        ("ARAMARK WILD RYE CAFE.*", "Wild Rye (Convention Center)", "food:restaurants"),
        ("LOUISA'S CAFE AND BAKERY.*", "Lousa's Cafe", "food:restaurants"),
        ("SQ *NYC DELI 7TH AVE", "NYC Deli (7th Ave, downtown Seattle)", "food:restaurants"),

        # Grocery stores
        ("CENTRAL COOP - NCGA.*", "Central Co-op", "food:groceries"),
        ("QFC #5847", "QFC--Broadway and Pine, Seattle, WA", "food:groceries"),

        # Coffee shops
        ("CUPCAKE ROYALE & VERITE", "Cupcake Royale", "food:coffee"),

        # Parking
        ("SEATTLE\s+684-PARK.*", "Seattle DOT Street Parking", "parking"),
        ("IMPARK\d+.*", "Impark Parking", "parking"),
        ("SEA PPG POF & IN LANE.*", "Pacific Place Parking Garage", "parking"),
        ("AMPCO PARKING MERIDIAN.*", "AMPCO Parking Garage (Meridian)", "parking"),
        ("REPUBLIC PARKING 29 543.*", "Republic Parking (1208 Pine St., Capitol Hill)", "parking"),
        ("REPUBLIC PARKING 30 534.*", "Republic Parking (Century Square)", "parking"),
        ("REPUBLIC PARKING 30 592.*", "Republic Parking (2nd and Union)", "parking"),
        ("REPUBLIC PARKING 31 567.*", "Republic Parking (Skyline Tower in Bellevue)", "parking"),
        ("NETFLIX.COM.*", "Netflix Monthly Subscription", "entertainment"),

        # Hardware and home stores
        ("PACIFIC SUPPLY COMPANY.*", "Pacific Supply Hardware Store", "household"),
        ("THE HOME DEPOT 4702.*", "Home Depot (SODO)", "household"),
        ("LOWES #00004.*", "Lowes (Rainer Valley)", "household"),

        ("COMCAST CABLE.*", "Comcast", "monthly:comms"),

        # Other merchants
        ("ELLIOTT BAY BOOK.*", "Elliot Bay Book Company", "books"),
        ("MADRONA WINE MERCHANTS.*", "Madrona Wine Merchants", "food:booze"),
        ("WASHINGTON ATHLETIC CLUB.*", "Washington Athletic Club", "gym"),
        ("CAPELLI'S BARBERSHOP.*", "Capelli's Barbershop", "haircuts"),
        ("APL\*APPLE ITUNES STORE.*", "Apple iTunes Store", None),
        ("Amazon.com AMZN.COM/BILLWA.*", "Amazon.com", None),
        ("01 BARTELL DRUGS.*", "Bartell's Drugs (5th and Olive)", "medical"),

        # Transfers, fees, and other financial things
        ("BA ELECTRONIC PAYMENT", "Credit Card Payment", "transfer"),
        ]
@add_filter
def filter_subs(t):
    for s in _subs:
        match = re.match(s[0], t.description, re.IGNORECASE)
        if match:
            t.properties['bank_memo'] = t.description
            t.description = match.expand(s[1])
            if len(s) > 2 and s[2]: # category
                t.allocations.append((None, s[2]))
    return t



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



def filter_transaction(t):
    for fn in _filters:
        t = fn(t)
    return t


def filter_imported_transaction(t):
    for fn in _filters:
        new_t = fn(t)
        if new_t:
            return new_t
    return t

