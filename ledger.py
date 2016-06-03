from type_utils import cents_from_str


class Amount(object):
    def __init__(self, amount, cents=None):
        if isinstance(amount, int):
            self.cents = amount*100
        elif isinstance(amount, float):
            self.cents = int(amount*100.0)
        elif isinstance(amount, str):
            self.cents = cents_from_str(amount)
        elif isinstance(amount, Amount):
            self.cents = amount.cents
        else:
            raise ValueError("invalid literal for Amount(): '%s'" % repr(amount))
        if cents != None:
            self.cents += int(cents)

    def __float__(self):
        return float(self.cents)/100.0

    def __add__(self, other):
        return Amount(0, self.cents + other.cents)

    def __sub__(self, other):
        return Amount(0, self.cents - other.cents)

    def __mul__(self, other):
        if isinstance(other, int):
            return Amount(0, self.cents*other)
        elif isinstance(other, float):
            return Amount(0, int(self.cents*other))
        else:
            return Amount(0, self.cents*other.cents)

    def __div__(self, other):
        if isinstance(other, int):
            return Amount(0, self.cents/other)
        elif isinstance(other, float):
            return Amount(0, int(self.cents/other))
        else:
            return Amount(0, self.cents/other.cents)

    def __neg__(self):
        return Amount(0, -self.cents)

    def __eq__(self, other):
        return self.cents == other.cents if isinstance(other, Amount) else self.cents == other
    def __gt__(self, other):
        return self.cents >  other.cents if isinstance(other, Amount) else self.cents >  other
    def __ge__(self, other):
        return self.cents >= other.cents if isinstance(other, Amount) else self.cents >= other
    def __lt__(self, other):
        return self.cents <  other.cents if isinstance(other, Amount) else self.cents <  other
    def __le__(self, other):
        return self.cents <= other.cents if isinstance(other, Amount) else self.cents <= other

    def __str__(self):
        if self.cents >= 0:
            return "%d.%02d" % (self.cents//100, self.cents % 100)
        else:
            nc = -self.cents
            return "-%d.%02d" % (nc//100, nc % 100)

    def format(self, nodollar=False, bookkeeping=False):
        dollar = 1 - nodollar
        if self.cents >= 0:
            return ["%d.%02d", "$%d.%02d"][1*dollar] % (self.cents//100, self.cents % 100)
        else:
            fmt = ["-%d.%02d", "-$%d.%02d", "(%d.%02d)", "($%d.%02d)"][1*dollar + 2*bookkeeping]
            nc = -self.cents
            return  fmt % (nc//100, nc % 100)

    def __repr__(self):
        return 'Amount ' + self.format()

def mk_amount(a):
    return a if isinstance(a, Amount) else Amount(a)

def amount_from_str_or_none(s):
    try:               return Amount(a)
    except ValueError: return None


class LedgerObject(object):
    def __eq__(self, other):
        return self.__dict__ == other.__dict__
    def __ne__(self, other):
        return not self == other


class Account(LedgerObject):
    def __init__(self, name, description=None):
        self.name = name
        self.description = description


class Category(LedgerObject):
    def __init__(self, name, description=None):
        self.name = name
        self.description = description
        self.goal = None

class CategoryGoal(LedgerObject):
    def __init__(self, amount):
        self.amount = mk_amount(amount)


class Transaction(LedgerObject):
    def __init__(self, amount, date, account):
        amount = mk_amount(amount)
        if amount < 0:
            self.sign = -1
            self.amount = -amount
        else:
            self.sign = 1
            self.amount = amount
        self.date = date
        self.account = account
        self.description = None;
        self.allocations = {}  # map of category names to Allocations
        self.projected = False
        self.properties = {}   # map of key names to Properties
        self.tags = set()

    def signed_amount(self):
        return self.amount*self.sign

    def description_matches(self, pattern):
        return re.match(self.description, pattern)

    def allocate_to(self, category_name, amount=None):
        amount = mk_amount(amount)
        if amount is not None:
            if not isinstance(amount, Amount):
                amount = Amount(amount)
        if category_name in self.allocations:
            self.allocations[category_name].amount = amount;
        else:
            self.allocations[category_name] = Allocation(amount, category_name)


class Allocation(LedgerObject):
    def __init__(self, amount, category):
        self.amount = mk_amount(amount)
        self.category = category
        self.tags = []

class Tag(LedgerObject):
    def __init__(self, val):
        self.value = val
    def __hash__(self):
        return hash(self.value)

class Property(LedgerObject):
    def __init__(self, key, value):
        self.key = key
        self.value = value



class Whitespace(object):
    pass

class Comment(object):
    pass

class ImportFile(object):
    def __init__(self, path):
        self.path = path

class EndOfFile(object):
    pass



class Ledger(object):
    def __init__(self):
        self.accounts     = {}   # keyed by account.name
        self.categories   = { 'unallocated': Category('unallocated')  }
        self.transactions = []

    def append(self, other):
        print "append t0: %d" % len(self.transactions)
        self.accounts.update(other.accounts)
        self.categories.update(other.categories)
        self.transactions.extend(other.transactions)
        print "append t1: %d" % len(self.transactions)

