from type_utils import cents_from_str
from sys import maxint


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

    @staticmethod
    def from_cents(c):
        return Amount(c//100, c % 100)

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
        if isinstance(other, Amount):
            return self.cents == other.cents
        elif isinstance(other, int):
            return self.cents == other*100
        elif isinstance(other, float):
            return self.cents == int(other*100.0)
        else:
            return False
    def __gt__(self, other):
        return self.cents >  other.cents if isinstance(other, Amount) else self.cents >  other*100
    def __ge__(self, other):
        return self.cents >= other.cents if isinstance(other, Amount) else self.cents >= other*100
    def __lt__(self, other):
        return self.cents <  other.cents if isinstance(other, Amount) else self.cents <  other*100
    def __le__(self, other):
        return self.cents <= other.cents if isinstance(other, Amount) else self.cents <= other*100

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
        return isinstance(other, LedgerObject) and self.__dict__ == other.__dict__
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
        self.remainder_allocation = None
        self.projected = False
        self.properties = {}   # map of key names to Properties
        self.tags = set()

    def __repr__(self):
        fmt = "%s %s " + ("from" if self.sign == -1 else "into") + " %s: %s"
        return fmt % (self.date, self.amount, self.account.name, self.description)

    def __hash__(self):
        if 'bank_description' in self.properties:
            desc = self.properties['bank_description'].value
        else:
            desc = self.description
        return hash((self.amount, self.sign, self.date, desc))

    def id(self):
        h = hash(self)
        if h < 0: h = maxint + h + 1
        hexstr = hex(h)
        if hexstr.startswith('0x') or hexstr.startswith('0X'):
            hexstr = hexstr[2:]
        if len(hexstr) < 6:
            return '0'*(6-len(hexstr)) + hexstr
        else:
            return hexstr[0:6]

    def signed_amount(self):
        return self.amount*self.sign

    def description_matches(self, pattern):
        return re.match(self.description, pattern)

    def unallocated_amount(self):
        if self.remainder_allocation != None:
            return Amount(0)
        remainder_amount = self.amount
        for a in self.allocations.values():
            remainder_amount -= a.amount
        return remainder_amount

    def allocate_to(self, category_name, amount=None):
        amount = mk_amount(amount)
        if amount is not None:
            if not isinstance(amount, Amount):
                amount = Amount(amount)
        if category_name in self.allocations:
            self.allocations[category_name].amount = amount;
        else:
            self.allocations[category_name] = Allocation(self, amount, category_name)


class Allocation(LedgerObject):
    def __init__(self, txn, amount, category):
        self.parent_txn = txn
        self.amount = mk_amount(amount)
        self.category = category
        self.tags = []
    def __repr__(self):
        return "%s->%s" % (str(self.amount), self.category.name)

class RemainderAllocation(LedgerObject):
    def __init__(self, txn, category):
        self.parent_txn = txn
        self.category = category
        self.tags = []
    def __repr__(self):
        return "all->%s" % self.category.name


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

