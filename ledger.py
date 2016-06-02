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
        self.amount = amount


class Transaction(LedgerObject):
    def __init__(self, amount, date, account):
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

class Allocation(LedgerObject):
    def __init__(self, amount, category):
        self.amount = amount
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
#        self.tags         = { 'import_unverified' : Tag('unverified') }
        self.transactions = []

    def append(self, other):
        print "append t0: %d" % len(self.transactions)
        self.accounts.update(other.accounts)
        self.categories.update(other.categories)
        self.transactions.extend(other.transactions)
        print "append t1: %d" % len(self.transactions)

