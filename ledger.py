class Account(object):
    def __init__(self, name, description=None):
        self.name = name
        self.description = description



class Category(object):
    def __init__(self, name, description=None):
        self.name = name
        self.description = description
        self.goal = None

class Allocation(object):
    def __init__(self, amount, category):
        self.amount = amount
        self.category = category



class Transaction(object):
    def __init__(self, amount, date):
        self.amount = amount
        self.date = date
        self.description = None;
        self.projected = False
        self.properties = {}

class IncomeTransaction(Transaction):
    def __init__(self, amount, date, account):
        super(IncomeTransaction, self).__init__(amount, date)
        self.account = account
        self.allocations = []
    def signed_amount(self):
        return self.amount

class ExpenditureTransaction(Transaction):
    def __init__(self, amount, date, account):
        super(ExpenditureTransaction, self).__init__(amount, date)
        self.account = account
        self.allocations = []
    def signed_amount(self):
        return -self.amount

class TransferTransaction(Transaction):
    def __init__(self, amount, date, from_account, to_account):
        super(IncomeTransaction, self).__init__(amount, date)
        self.from_account = from_account
        self.to_account   = to_account



class Ledger(object):
    def __init__(self):
        self.accounts     = {}   # keyed by account.name
        self.categories   = { 'unallocated': Category('unallocated') }
        self.transactions = []

    def append(self, other):
        self.accounts.update(other.accounts)
        self.categories.update(other.categories)
        self.transactions.extend(other.transactions)

