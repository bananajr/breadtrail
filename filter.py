from ledger import *
from type_utils import *

import re




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
        ("BLUE WATER TACO GRILL.*", "Blue Water Taco Grill", "food:restaurants"),
        ("ST CLOUDS.*", "St. Clouds Restaurant", "food:restaurants"),
        ("RAVISH\s+SEATTLE.*", "Ravish Restaurant in Eastlake", "food:restaurants"),
        ("VIA TRIBUNALI.*", "Via Tribunali Restaurant", "food:restaurants"),
        ("GP\*BOTTLEHOUSE.*", "Bottlehouse (Madrona)", "food:restaurants"),
        ("ARAMARK WILD RYE CAFE.*", "Wild Rye (Convention Center)", "food:restaurants"),
        ("LOUISA'S CAFE AND BAKERY.*", "Lousa's Cafe", "food:restaurants"),
        ("SQ *NYC DELI 7TH AVE", "NYC Deli (7th Ave, downtown Seattle)", "food:restaurants"),
        ("AGUA VERDE.*SEATTLE.*", "Agua Verde Restaurant", "food:restaurants"),
        ("BAR CANTINETTA.*", "Bar Cantinetta", "food:restaurants"),
        ("CAFE LAGO.*", "Cafe Lago", "food:restaurants"),
        ("HI-SPOT CAFE.*", "Hi-Spot Cafe", "food:restaurants"),

        # Grocery stores
        ("CENTRAL COOP.*", "Central Co-op", "food:groceries"),
        ("QFC #5847", "QFC--Broadway and Pine, Seattle, WA", "food:groceries"),
        ("DELAURENTI.*", "DeLaurenti Specialty Foods", None),

        # Coffee shops
        ("CUPCAKE ROYALE.*", "Cupcake Royale", "food:coffee"),

        # Transportation
        ("ALASKA AIR IN FLIGHT.*", "Alaska Airlines In-flight Meals", None),
        ("ALASKA AIR.*", "Alaska Airlines", "travel"),
        ("GOGOAIR.COM.*", "Gogo In-flight Internet", None),
        ("SEATTLE\s+684-PARK.*", "Seattle DOT Street Parking", "parking"),
        ("IMPARK\d+.*", "Impark Parking", "parking"),
        ("SEA PPG POF & IN LANE.*", "Pacific Place Parking Garage", "parking"),
        ("AMPCO PARKING MERIDIAN.*", "AMPCO Parking Garage (Meridian)", "parking"),
        ("REPUBLIC PARKING 29 543.*", "Republic Parking (1208 Pine St., Capitol Hill)", "parking"),
        ("REPUBLIC PARKING 30 534.*", "Republic Parking (Century Square)", "parking"),
        ("REPUBLIC PARKING 30 592.*", "Republic Parking (2nd and Union)", "parking"),
        ("REPUBLIC PARKING 31 567.*", "Republic Parking (Skyline Tower in Bellevue)", "parking"),
        ("ACE PRKING PS #3265.*", "Ace Parking (1515 7th Ave)", "parking"),
        ("CAR2GO.*", "Car2Go", "transportation"),


        # Hardware and home stores
        ("HARDWICK.*", "Hardwick and Sons", "household"),
        ("PACIFIC SUPPLY COMPANY.*", "Pacific Supply Hardware Store", "household"),
        ("THE HOME DEPOT 4702.*", "Home Depot (SODO)", "household"),
        ("LOWES #00004.*", "Lowes (Rainer Valley)", "household"),

        ("COMCAST CABLE.*", "Comcast", "monthly:comms"),
        ("DREAMHOST DH-FEE.*", "DreamHost", "monthly:comms"),
        ("DreamHost dh-fee.*", "DreamHost", "monthly:comms"),
        ("Dropbox\*", "DropBox", "monthly:comms"),
        ("GOOGLE \*Google Storage", "Google Cloud Storage", "montly:comms"),
        ("NETFLIX.COM.*", "Netflix", "entertainment"),
        ("ADY\*Spotify.*", "Spotify", "entertainment"),
        ("HLU\*Hulu.*", "Hulu", "entertainment"),
        ("Amazon Video On Demand AMZN.COM.*", "Amazon Video On Demand", "entertainment"),
        ("APL.*ITUNES.COM.*", "Apple iTunes Bill", None),
        ("APL*APPLE ONLINE STORE.*", "Apple Online Store", None),
        ("A.*AMZN.COM/BILL.*", "Amazon.com", None),
        ("AMAZON MKTPLACE PMTS.*", "Amazon.com", None),

        # Other merchants
        ("ELLIOTT BAY BOOK.*", "Elliot Bay Book Company", "books"),
        ("MADRONA WINE MERCHANTS.*", "Madrona Wine Merchants", "food:booze"),
        ("WASHINGTON ATHLETIC CLUB.*", "Washington Athletic Club", "gym"),
        ("CAPELLI'S BARBERSHOP.*", "Capelli's Barbershop", "haircuts"),
        ("APL\*APPLE ITUNES STORE.*", "Apple iTunes Store", None),
        ("01 BARTELL DRUGS.*", "Bartell's Drugs (5th and Olive)", "medical"),
        ("23 BARTELL DRUGS.*", "Bartell's Drugs (Broadway at Pike)", "medical"),
        ("AUTOZONE.*", "AutoZone", "car:maintenance"),
        ("GREEN LAKE JEWELRY.*", "Greenlake Jewelry", "gifts_for_us"),

        # Transfers, fees, and other financial things
        ("BA ELECTRONIC PAYMENT", "Credit Card Payment", "transfer"),
        ]
@add_filter
def filter_subs(ledger, t):
    filtered = False
    for s in _subs:
        match = re.match(s[0], t.description)
        if match:
            t.properties['bank_memo'] = Property('bank_memo', t.description)
            t.description = match.expand(s[1])
            if len(s) > 2 and s[2] is not None:
                t.allocations = { s[2]: Allocation(t.amount, ledger.categories[s[2]]) }
            filtered = True
    return filtered


def filter_transaction(ledger, t):
    filtered = False
    for fn in _filters:
        if fn(ledger, t): filtered = True
    return filtered
