#!/usr/bin/env python

from ledger import *
from type_utils import *
import parser
from config import config
from filter import filter_transaction

import cmdln
import sys, os
import re
import filecmp



class BreadTrail(cmdln.Cmdln):
    name = "breadtrail"

    def __init__(self):
        cmdln.Cmdln.__init__(self)

    def _parse_ledger(self):
        try:
            self.parser = parser.Parser(self.options.filename or config.get_ledger_path())
            self.parser.parse()
        except parser.ParseError as e:
            sys.stderr.write("Error (%s:%d): %s" % (e.filename, e.linenum, e.msg))
            if not e.msg.endswith('\n'):
                sys.stderr.write('\n')
            sys.exit(1)

    def _write_ledger(self):
        class writer(object):
            def __init__(self, filename):
                self.filename = filename
                self.fp = open(self.filename + '_', 'w')
            def write(self, s):
                self.fp.write(s)
            def finish_and_test_same(self):
                self.fp.close()
                if not filecmp.cmp(self.filename, self.filename + '_'):
                    return False
                os.remove(self.filename + '_')
                return True

        out_stack = [writer(self.parser.filename)]
        #print ">>> output is now going to " + out_stack[-1].filename
        for cmd in self.parser.commands:
            if cmd.line:
                out_stack[-1].write(cmd.line.raw_line)
            if hasattr(cmd, 'subcommands'):
                for scmd in cmd.subcommands:
                    if scmd.line:
                        out_stack[-1].write(scmd.line.raw_line)
            if isinstance(cmd, ImportFile):
                out_stack.append(writer(cmd.path))
                #print ">>> output is now going to " + out_stack[-1].filename
            elif isinstance(cmd, EndOfFile):
                last_writer = out_stack.pop()
                if last_writer.finish_and_test_same():
                    pass
                #    print ">>> no difference when writing %s; deleting tmp file" % last_writer.filename
                if len(out_stack) > 0: # still going
                    pass
                #    print ">>> output is back to " + out_stack[-1].filename


    def get_optparser(self):
        op = cmdln.Cmdln.get_optparser(self)
        op.add_option("-f", "--filename", dest="filename",
                      help="ledger filename")
        return op

    #@cmdln.option("-u", "--show-updates", action="store_true", help="display update information")
    #@cmdln.option("-v", "--verbose", action="store_true", help="print extra information")

    @cmdln.alias("verify")
    def do_check(self, subcmd, opts):
        """${cmd_name}: simply read and rewrite the ledger, checking for errors

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()
        self._write_ledger()

    def do_filter(self, subcmd, opts):
        """${cmd_name}: filter the register

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()
        for t in self.parser.ledger.transactions:
            if filter_transaction(self.parser.ledger, t):
                self.parser.update_transaction(t)
        self._write_ledger()

    @cmdln.option("--date", help="compute the balance on the given date")
    @cmdln.alias("bal")
    def do_balance(self, subcmd, opts, *names):
        """${cmd_name}: compute the balance of an account

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()
        L = self.parser.ledger

        date = datetime_from_str(opts.date) if opts.date else None

        keys = sorted(L.accounts.keys()) + sorted(L.categories.keys())
        balances = dict(zip(keys, [Amount(0)]*len(keys)))
        for t in L.transactions:
            if date and t.date > date: continue
            balances[t.account.name] += t.signed_amount()
            for (cat_name, a) in t.allocations.iteritems():
                amount = a.amount
                balances[a.category.name] += amount

        if len(names) == 0:
            names_list = keys
        else:
            names_list = []
            for name in names:
                if name == 'accounts':
                    names_list.extend(sorted(L.accounts.keys()))
                elif name == 'categories' or name == 'envelopes':
                    names_list.extend(sorted(L.categories.keys()))
                elif name == 'all':
                    names_list.extend(sorted(L.accounts.keys()))
                    names_list.extend(sorted(L.categories.keys()))

        col = max(len(name) for name in names_list) + 2
        for name in names_list:
            if not name in balances:
                print "Error: unknown account or category name '%s'." % name
                return
            print (("%%-%ds" % col) + " %8s") % (name, str(balances[name]))

    @cmdln.alias("reg")
    def do_register(self, subcmd, opts, account):
        """${cmd_name}: print the history of transactions for an account

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()
        if not account in self.parser.ledger.accounts:
            print "Error: unknown account name '%s'." % account
            return
        account = self.parser.ledger.accounts[account]
        balance = 0
        for t in self.parser.ledger.transactions:
            if t.account is not account: continue
            amount = t.amount
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
        self._parse_ledger()
        if not category in self.parser.ledger.categories:
            print "Error: unknown category name '%s'." % cat_name
            return
        cat = self.parser.ledger.categories[category]
        balance = 0
        for t in self.parser.ledger.transactions:
            factor = 1 
            desc = t.description or ''
            if not cat.name in t.allocations:
                continue
            a = t.allocations[cat.name]
            amount = a.amount
            balance = balance + amount
            print "%s %10s %10s %s" % (str(t.date.date()), cents_to_str(amount),
                    cents_to_str(balance), t.description)

    @cmdln.option("-s", "--select-expn",   help="")
    @cmdln.option("-i", "--init-stmt",     help="")
    @cmdln.option("-p", "--process-stmt",  help="")
    @cmdln.option("-f", "--finalize-stmt", help="")
    def do_report(self, subcmd, opts, t_var_name):
        """${cmd_name}: generate reports

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()

        if not opts.select_expn:
            select = None
        else:
            select = compile('lambda %s: %s' % (t_var_name, opts.select_expn), '<string>', 'eval')

        if not opts.init_stmt:
            init = None
        else:
            init = compile(opts.init_stmt, '<string>', 'exec')

        if not opts.process_stmt:
            opts.process_stmt = 'print %s.date, %s.amount, %s.description' % \
                (t_var_name, t_var_name, t_var_name)
        process = compile(opts.process_stmt, '<string>', 'exec')

        if not opts.finalize_stmt:
            finalize = None
        else:
            finalize = compile(opts.finalize_stmt, '<string>', 'exec')

        context = { }
        if init:
            exec(init, context)
        for t in self.parser.ledger.transactions:
            if select != None and not eval(select, context)(t):
                continue
            context[t_var_name] = t
            exec(process, context)
        if finalize:
            exec(finalize, context)


    def do_listfiles(self, usbcmd, opts):
        """${cmd_name}: lists the ledger file and all imported files

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()
        print self.parser.filename
        for cmd in self.parser.commands:
            if isinstance(cmd, ImportFile):
                print cmd.path






if __name__ == "__main__":
    app = BreadTrail()
    sys.exit(app.main())
