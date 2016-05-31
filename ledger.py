class Account(object):
    def __init__(self, name, description=None):
        self.name = name
        self.description = description


class Category(object):
    def __init__(self, name, description=None):
        self.name = name
        self.description = description
        self.goal = None

class CategoryGoal(object):
    def __init__(self, amount):
        self.amount = amount


class Transaction(object):
    def __init__(self, amount, date):
        self.amount = amount
        self.date = date
        self.description = None;
        self.allocations = {}
        self.projected = False
        self.properties = {}
        self.tags = set()

class IncomeTransaction(Transaction):
    def __init__(self, amount, date, account):
        super(IncomeTransaction, self).__init__(amount, date)
        self.account = account
    def signed_amount(self):
        return self.amount

class ExpenditureTransaction(Transaction):
    def __init__(self, amount, date, account):
        super(ExpenditureTransaction, self).__init__(amount, date)
        self.account = account
    def signed_amount(self):
        return -self.amount


class Allocation(object):
    def __init__(self, amount, category):
        self.amount = amount
        self.category = category
        self.tags = []

class Tag(object):
    def __init__(self, val):
        self.val = val
    def __hash__(self):
        return hash(self.val)
    def __cmp__(self, other):
        return cmp(self.val, other.val)

class Property(object):
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

