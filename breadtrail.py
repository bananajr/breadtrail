#!/usr/bin/env python

from ledger import *
from type_utils import *
import parser
from config import config

import cmdln
from datetime import datetime
import sys
import re
import logging



class BreadTrail(cmdln.Cmdln):
    name = "breadtrail"

    def __init__(self):
        cmdln.Cmdln.__init__(self)
        self.ledger = Ledger()

    def init_ledger(self):
        try:
            p = parser.Parser(self.ledger)
            p.parse(self.options.filename or config.get_ledger_path())
        except parser.ParseError as e:
            sys.stderr.write("Error (%s:%d): %s" % (e.filename, e.linenum, e.msg))
            if not e.msg.endswith('\n'):
                sys.stderr.write('\n')
            sys.exit(1)


    def get_optparser(self):
        op = cmdln.Cmdln.get_optparser(self)
        op.add_option("-f", "--filename", dest="filename",
                      help="ledger filename")
        return op

    #@cmdln.option("-u", "--show-updates", action="store_true", help="display update information")
    #@cmdln.option("-v", "--verbose", action="store_true", help="print extra information")


    @cmdln.alias("bal")
    def do_balance(self, subcmd, opts, *account_names):
        """${cmd_name}: compute the balance of an account

        ${cmd_usage}
        ${cmd_option_list}
        """
        self.init_ledger()

        keys = self.ledger.accounts.keys()
        balances = dict(zip(keys, [0]*len(keys)))
        for t in self.ledger.transactions:
            balances[t.account.name] += t.signed_amount()

        if len(account_names) == 0:
            for name, amount in balances.iteritems():
                print "%s: %s" % (name, cents_to_str(amount))
        else:
            for name in account_names:
                if not name in balances:
                    print "Error: unknown account name '%s'." % name
                    return
                print "%s: %s" % (name, cents_to_str(balances[name]))

    @cmdln.alias("reg")
    def do_register(self, subcmd, opts, account):
        """${cmd_name}: print the history of transactions for an account

        ${cmd_usage}
        ${cmd_option_list}
        """
        self.init_ledger()
        if not account in self.ledger.accounts:
            print "Error: unknown account name '%s'." % account
            return
        account = self.ledger.accounts[account]
        balance = 0
        for t in self.ledger.transactions:
            if t.account is not account: continue
            amount = t.amount
            if isinstance(t, ExpenditureTransaction): amount = -amount
            balance = balance + amount
            date = t.date
            desc = t.description or ''
            print "%s %10s %10s %s" % (str(t.date.date()), cents_to_str(amount), cents_to_str(balance), desc)

    @cmdln.alias("ereg", "eregister")
    def do_envelope_register(self, subcmd, opts, category):
        """${cmd_name}: print the history of allocations for a category

        ${cmd_usage}
        ${cmd_option_list}
        """
        self.init_ledger()
        if not category in self.ledger.categories:
            print "Error: unknown category name '%s'." % cat_name
            return
        cat = self.ledger.categories[category]
        balance = 0
        for t in self.ledger.transactions:
            factor = 1 if isinstance(t, IncomeTransaction) else -1
            desc = t.description or ''
            for a in t.allocations:
                if a.category is not cat: continue
                amount = a.amount*factor
                balance = balance + amount
                print "%s %10s %10s %s" % (str(t.date.date()), cents_to_str(amount), cents_to_str(balance), desc)





if __name__ == "__main__":
    app = BreadTrail()
    sys.exit(app.main())
