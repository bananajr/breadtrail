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
        # Income
        ("SYNAPSE PROD(UCT)?\s+PAYROLL.*", "Synapse Product Development Payroll", "income:jake:salary"),
        ("SYNAPSE PRODUCT\s+DIRECT.*", "Synapse Product Development Payroll", "income:jake:salary"),


        # Restaurants & bars
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
        ("8OZ BURGER BAR.*", "8oz Burger Bar", "food:restaurants"),
        ("ANCHOVIES AND BAR COTT.*", "Anchovies and Olives / Bar Cotta", "food:restaurants"),
        ("ATHENIAN SEAFOOD.*SEATTLE", "The Athenian", "food:restaurants"),
        ("CAFE PRESSE.*SEAT.*", "Cafe Presse", "food:restaurants"),
        ("CANTINETTA.*SEAT.*", "Cantinetta", "food:restaurants"),
        ("LOCAL 360.*SEAT.*", "Local 360", "food:restaurants"),
        ("LOUISA\s*S CAFE.*SEAT.*", "Louisa's Cafe", "food:restaurants"),
        ("MARJORIE RESTAURANT.*SEAT.*", "Marjorie Restaurant", "food:restaurants"),
        ("NAAM THAI CUISINE.*SEAT.*", "Naam Thai Cuisine", "food:restaurants"),
        ("NEW SAIGON.*SEAT.*", "New Saigon Restaurant", "food:restaurants"),
        ("ODDFELLOWS CAFE.*SEAT.*", "Oddfellows Cafe", "food:restaurants"),
        ("PAMELAS FINE FOODS.*", "Pamela's Fine Foods", "food:restaurants"),
        ("POQUITOS .*SEAT.*", "Poquitos Restaurant", "food:restaurants"),
        ("QDOBA .*GRILL.*", "Qdoba Mexican Grill", "food:restaurants"),
        ("PORTAGE BAY CAFE .*SEAT.*", "Portage Bay Cafe", "food:restaurants"),
        ("BAGUETTE BOX.*", "Baguette Box", "food:work_lunches"),
        ("SINGLE SHOT .*SEAT.*", "Single Shot", "food:restaurants"),
        ("SMITH .*SEAT.*", "Smith Restaurant", "food:restaurants"),
        ("STEELHEAD DINER .*SEAT.*", "Steelhead Diner", "food:restaurants"),
        ("VOLUNTEER PARK CAFE.*", "Volunteer Park Cafe", "food:restaurants"),
        ("MADRONA ARMS.*SEAT.*", "Madrona Arms", "food:bars"),
        ("SCHOONER EXACT BREWING", "Schooner Exact Brewing Company", None),
        ("OLIVER'S TWIST.*SEAT.*", "Oliver's Twist", "food:bars"),
        ("14 CARROT CAFE SEATTLE.*", "14 Carrot Cafe, Eastlake, Seattle", "food:restaurants"),
        ("CACTUS MADISON PARK.*", "Cactus, Madison Park", "food:restaurants"),
        ("PAGLIACCI MADISON.*", "Pagliacci Pizza, Madison Park", "food:restaurants"),
        ("BAR SUE.*SEATTLE", "Bar Sue, Capitol Hill, Seattle", "food:bars"),
        ("BARRIO.*SEATTLE", "Barrio, Seattle", "food:restaurants"),
        ("LIQUOR AND WINE.*SEAT.*", "Liquor and Wine", "food:booze"),
        ("NW LIQUOR CAPITOL HILL.*", "NW Liquor, Capitol Hill", "food:booze"),

        # Grocery stores
        ("CENTRAL COOP.*", "Central Co-op", "food:groceries"),
        ("DELAURENTI.*", "DeLaurenti Specialty Foods", None),
        ("GROCERY OUTLET", "Grocery Outlet", "food:groceries"),
        ("KRESS SUPERMARKET.*", "Kress Supermarket", "food:groceries"),
        ("LESCHI FOOD MART.*SEAT.*", "Leschi Food Mart", "food:groceries"),
        ("METROPOLITAN MKT.*SEAT.*", "Metropolitan Market", "food:groceries"),
        ("QFC #5847", "QFC--Broadway and Pine, Seattle, WA", "food:groceries"),
        ("QFC #5807 .*SEAT.*", "QFC--University Village, Seattle WA", "food:groceries"),
        ("QFC #5825 .*SEAT.*", "QFC No. 5825", "food:groceries"),
        ("QFC #5849 .*SEAT.*", "QFC No. 5849", "food:groceries"),
        ("QFC #5869 .*SEAT.*", "QFC No. 5869", "food:groceries"),
        ("WHOLEFDS.*", "Whole Foods", "food:groceries"),
        ("MADRONA HOMEMADE DELI.*SEAT.*", "Madrona Homemade Deli", "food:groceries"),

        # Coffee shops, cupcakes, ice cream, etc.
        ("CUPCAKE ROYALE.*", "Cupcake Royale", "food:coffee"),
        ("BEECHERS SEATAC.*", "Beecher's at SeaTac", "food:coffee"),
        ("FUEL COFFEE.*", "Fuel Coffee", "food:coffee"),
        ("SQ *MOLLY MOON'S MADRO.*", "Molly Moon's Ice Cream", "food:coffee"),
        ("SQ \*HELLO ROBIN.*", "Hello Robin", "food:coffee"),
        ("STUMPTOWN COFFEE.*", "Stumptown Coffee", "food:coffee"),

        # Transportation
        ("ALASKA AIR IN FLIGHT.*", "Alaska Airlines In-flight Meals", None),
        ("ALASKA AIR.*", "Alaska Airlines", "travel"),
        ("UNITED.*2732", "United Airlines", None),
        ("GOGOAIR.COM.*", "Gogo In-flight Internet", None),
        ("SEATTLE\s+684-PARK.*", "Seattle DOT Street Parking", "parking"),
        ("IMPARK\d+.*", "Impark Parking", "parking"),
        ("SEA PPG POF & IN LANE.*", "Pacific Place Parking Garage", "parking"),
        ("AMPCO PARKING MERIDIAN.*", "AMPCO Parking Garage (Meridian)", "parking"),
        ("REPUBLIC PARKING 29.*", "Republic Parking (1208 Pine St., Capitol Hill)", "parking"),
        ("REPUBLIC PARKING 30.*", "Republic Parking (Century Square)", "parking"),
        ("REPUBLIC PARKING 30.*", "Republic Parking (2nd and Union)", "parking"),
        ("REPUBLIC PARKING 31.*", "Republic Parking (Skyline Tower in Bellevue)", "parking"),
        ("ACE PRKING PS #3265.*", "Ace Parking (1515 7th Ave)", "parking"),
        ("CAR2GO.*", "Car2Go", "transportation"),
        ("DARTMOUTH COACH.*", "Dartmouth Coach", None),
        ("DIAMOND PARKING.*", "Diamond Parking", None),
        ("DIAMOND PARKING.*", "Diamond Parking", None),
        ("UBER TECHNOLOGIES.*", "Uber", "transportation"),
        ("UBER.*576.*", "Uber", "transportation"),
        ("WSFERRIES.*", "Washington State Ferries", "transportation"),
        ("AIRBNB.*", "Airbnb.com", None),

        # Car stuff
        ("MONTLAKE 76.*SEAT.*", "Montlake 76", "gas"),
        ("UNION 76.*", "Union 76", "gas"),
        ("SHELL OIL.*", "Shell Oil", "gas"),


        # Hardware, home stores, household, gear
        ("HARDWICK.*", "Hardwick and Sons", "household"),
        ("PACIFIC SUPPLY COMPANY.*", "Pacific Supply Hardware Store", "household"),
        ("THE HOME DEPOT 4702.*", "Home Depot (SODO)", "household"),
        ("LOWES #00004.*", "Lowes (Rainer Valley)", "household"),
        ("20 20 CYCLE.*", "20/20 Cycle Shop", "gear"),
        ("REI 11 SEAT.*", "REI Flagship Store", "gear"),
        ("GLASSYBABY.*", "GlassyBaby", "gifts_for_us"),
        ("ANTIQUES AT PIKE PLACE.*", "Antiques at Pike Place", None),
        ("THE HOME DEPOT.*4706.*", "Home Depot (SODO, Seattle)", "household"),
        (".*DOLLAR SHAVE CLUB.*", "Dollar Shave Club", "household"),
        ("THE HOME DEPOT.*8944.*", "Home Depot (West Seattle)", "household"),
        ("HARBOR FREIGHT TOOLS.*", "Harbor Freight Tools", "household:tools"),

        # Monthly bills
        ("COBALT MORTGAGE.*", "Cobalt Mortgage", "monthly:mortgage"),
        ("SENECA MORTGAGE.*", "Seneca Mortgage", "monthly:mortgage"),
        ("PEMCO INS PYMT.*", "Pemco Insurance Payment", "car:insurance"),
        ("PUGET SOUND ENER ONLINE PMT.*", "Puget Sound Energy", "monthly:utilities"),
        ("SEATTLEUTILTIES", "Seattle City Utilities", "monthly:utilities"),
        ("SEATTLE UTILITY\s+WEB DEBIT.*", "Seattle City Utilities", "monthly:utilities"),
        ("SEATTLE LIGHT\s+WEB DEBIT.*", "Seattle City Light", "monthly:utilities"),
        ("COMCAST CABLE.*", "Comcast", "monthly:comms"),
        ("AT&T\s+PAYMENT.*", "AT&T Payment", "monthly:comms"),
        ("DREAMHOST DH-FEE.*", "DreamHost", "monthly:comms"),
        ("DreamHost dh-fee.*", "DreamHost", "monthly:comms"),
        ("Dropbox\*", "DropBox", "monthly:comms"),
        ("GOOGLE \*Google Storage", "Google Cloud Storage", "monthly:comms"),
        ("NETFLIX.COM.*", "Netflix", "entertainment"),
        ("ADY\*Spotify.*", "Spotify", "entertainment"),
        ("HLU\*Hulu.*", "Hulu", "entertainment"),
        ("Amazon Video On Demand AMZN.COM.*", "Amazon Video On Demand", "entertainment"),
        ("APL.*ITUNES.COM.*", "Apple iTunes Bill", None),
        ("APL*APPLE ONLINE STORE.*", "Apple Online Store", None),
        ("A.*AMZN.COM/BILL.*", "Amazon.com", None),
        ("PAIR NETWORKS.*", "Pair Networks", "monthly:comms"),

        # Other merchants
        ("AMAZON MKTPLACE PMTS.*", "Amazon.com", None),
        ("AMAZON.COM AMZN.COM.*"  "Amazon.com", None),
        ("ELLIOTT BAY BOOK.*", "Elliot Bay Book Company", "books"),
        ("MADRONA WINE MERCHANTS.*", "Madrona Wine Merchants", "food:booze"),
        ("WASHINGTON ATHLETIC CLUB.*", "Washington Athletic Club", "gym"),
        ("CAPELLI'S BARBERSHOP.*", "Capelli's Barbershop", "haircuts"),
        ("APL\*APPLE ITUNES STORE.*", "Apple iTunes Store", None),
        ("01 BARTELL DRUGS.*", "Bartell's Drugs (5th and Olive)", "medical"),
        ("23 BARTELL DRUGS.*", "Bartell's Drugs (Broadway at Pike)", "medical"),
        ("AUTOZONE.*", "AutoZone", "car:maintenance"),
        ("GREEN LAKE JEWELRY.*", "Greenlake Jewelry", "gifts_for_us"),
        ("AMAZON VIDEO ON DEMAND.*", "Amazon Video", "entertainment"),
        ("RDIOINC.*", "Rdio Subscription", "entertainment"),
        ("STG PRESENTS SEATTLE WA", "Seattle Theatre Group (STG)", "entertainment"),
        ("WASHINGTON ATHLE BILL PYMT.*", "Washington Athletic Club", "gym"),

        # Transfers, fees, and other financial things
        ("ATM WITHDRAWAL.*", "ATM Withdrawal", "transfer:cash"),
        ("NON-CHASE ATM WITHDRAW.*", "ATM Withdrawal (Out of Network)", "transfer:cash"),
        ("NON-CHASE ATM FEE.*", "Out-of-network ATM Fee", "fees"),
        ("BA ELECTRONIC PAYMENT.*", "Credit Card Payment (Jake's Alaska Airlines Visa)", "transfer"),
        ("BK OF AMER VI/MC ONLINE PMT.*", "Credit Card Payment (Jake's Alaska Airlines Visa)", "transfer"),
        ("CITI AUTOPAY.*", "Credit Card Payment (Jake's Citibank Visa)", "transfer"),
        ("PAYPAL .*ECHECK.*", "Paypal Purchase", None),
        ("ATM CHECK DEPOSIT.*1401 5TH", "Deposit at Chase ATM, 1401 5th Ave.", None),
        ("ATM CHECK DEPOSIT.*1429 BRO", "Deposit at Chase ATM, 1429 Broadway", None),
        ("ATM CHECK DEPOSIT.*600 PINE", "Deposit at Chase ATM, 600 Pine St.", None),
        ]
@add_filter
def filter_subs(ledger, t):
    filtered = False
    for s in _subs:
        match = re.match(s[0], t.description)
        if match:
            t.properties['bank_description'] = Property('bank_description', t.description)
            t.description = match.expand(s[1])
            if len(s) > 2 and s[2] is not None:
                t.allocations = { s[2]: Allocation(t, t.amount, ledger.categories[s[2]]) }
            filtered = True
    return filtered


@add_filter
def filter_titlecase(ledger, t):
    if 'bank_description' in t.properties: return False
    if 'bank_memo'        in t.properties: return False
    t.properties['bank_description'] = Property('bank_description', t.description)
    t.description = titlecase(t.description)
    return True



def filter_transaction(ledger, t):
    filtered = False
    for fn in _filters:
        if fn(ledger, t): filtered = True
    return filtered
