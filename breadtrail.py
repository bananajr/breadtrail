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
import readline



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


    @cmdln.alias("verify")
    def do_check(self, subcmd, opts):
        """${cmd_name}: simply read and rewrite the ledger, checking for errors

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()
        self._write_ledger()

    def do_commit(self, subcmd, opts):
        """${cmd_name}: copy update files to their actual counterparts

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()
        path_stack = [self.parser.filename]
        for cmd in self.parser.commands:
            if isinstance(cmd, ImportFile):
                path_stack.append(cmd.path)
            elif isinstance(cmd, EndOfFile):
                last_path = path_stack.pop()
                new_path = last_path + '_'
                if os.path.isfile(new_path) and os.path.getsize(new_path) > 0:
                    try:
                        os.rename(new_path, last_path)
                    except OSError as e:
                        sys.stderro.write("Error commiting '%s': %s\n" % (new_path, str(e)))


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

    def expand_account_names_list(self, names):
        names_list = []
        for name in names:
            if name == 'all':
                names_list.extend(self.ledger.accounts.keys())
            else:
                names_list += name

    @cmdln.option("--date", help="compute the balance on the given date")
    @cmdln.alias("bal")
    @cmdln.alias("abal")
    def do_balance(self, subcmd, opts, *names):
        """${cmd_name}: compute the balance of one or more accounts

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()
        L = self.parser.ledger

        date = datetime_from_str(opts.date) if opts.date else None

        keys = L.accounts.keys()
        balances = dict(zip(keys, [Amount(0)]*len(keys)))
        for t in L.transactions:
            if date and t.date > date: continue
            balances[t.account.name] += t.signed_amount()

        if len(names) == 0:
            names_list = keys
        else: 
            names_list = expand_account_names_list(names)
        col = max(len(name) for name in names_list) + 2
        total = Amount(0)
        for name in names_list:
            if not name in balances:
                print "Error: unknown account name '%s'." % name
                return
            total += balances[name]
            print (("%%-%ds" % col) + " %12s") % (name, str(balances[name]))
        if len(names_list) > 0:
            print (("%%-%ds" % col) + " %12s") % ("total:", total)


    @cmdln.option("--date", help="compute the balance on the given date")
    @cmdln.alias("ebal")
    def do_envelope_balance(self, subcmd, opts, *names):
        """${cmd_name}: compute the balance of one or more envelopes

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()
        L = self.parser.ledger

        date = datetime_from_str(opts.date) if opts.date else None

        keys = sorted(L.categories.keys()) + ['<unallocated>']
        balances = dict(zip(keys, [Amount(0)]*len(keys)))
        for t in L.transactions:
            if date and t.date > date: continue
            print t, t.allocations
            for (cat_name, a) in t.allocations.iteritems():
                amount = a.amount
                print '  %s->%s' % (str(a.amount), cat_name)
                balances[a.category.name] += amount*t.sign
            balances['<unallocated>'] += t.unallocated_amount()

        if len(names) == 0:
            names_list = keys
        else:
            names_list = []
            for name in names:
                if name == 'all':
                    names_list.extend(sorted(L.categories.keys()))
                else:
                    names_list += name
        col = max(len(name) for name in names_list) + 2
        total = Amount(0)
        for name in names_list:
            if not name in balances:
                print "Error: unknown category name '%s'." % name
                return
            total += balances[name]
            print (("%%-%ds" % col) + " %12s") % (name, str(balances[name]))
        if len(names_list) > 0:
            print (("%%-%ds" % col) + " %12s") % ("total:", total)


    @cmdln.option("-s", "--select-expn",   help="")
    @cmdln.option("--no-id", "--noid", action="store_true", dest="noid", default=False, help="")
    @cmdln.option("--full", action="store_true", dest="print_full", default=False, help="")
    @cmdln.alias("reg")
    def do_register(self, subcmd, opts, account_name):
        """${cmd_name}: print the history of transactions for an account

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()

        if not account_name in self.parser.ledger.accounts:
            print "Error: unknown account name '%s'." % account_name
            return
        account = self.parser.ledger.accounts[account_name]

        if not opts.select_expn:
            select = None
        else:
            m = re.match("([A-Za-z_]+):(.*$)", opts.select_expn)
            if m:
                t_var_name = m.groups(1)
                opts.select_expn = m.groups(2)
            else:
                t_var_name = 't'
            select = compile('lambda %s: %s' % (t_var_name, opts.select_expn), '<string>', 'eval')

        balance = Amount(0)
        for t in self.parser.ledger.transactions:
            if t.account is not account: continue
            amount = t.signed_amount()
            balance = balance + amount
            if select and not eval(select)(t):
                continue
            date = t.date
            desc = t.description or ''
            if opts.noid:
                print "%s %10s %10s  %s" % (str(t.date.date()), str(amount), str(balance), desc)
            else:
                print "%s  %s %10s %10s  %s" % (t.id(), str(t.date.date()), str(amount), str(balance), desc)

            if opts.print_full:
                for sc in t.subcommands:
                    sys.stdout.write(sc.line.raw_line)
                print


    @cmdln.option("-s", "--select-expn",   help="")
    @cmdln.alias("ereg", "eregister")
    def do_envelope_register(self, subcmd, opts, cat_name):
        """${cmd_name}: print the history of allocations for a category

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()
        if not cat_name in self.parser.ledger.categories:
            print "Error: unknown category name '%s'." % cat_name
            return
        cat = self.parser.ledger.categories[cat_name]

        if not opts.select_expn:
            select = None
        else:
            m = re.match("([A-Za-z_]+),([A-Za-z_]+):(.*$)", opts.select_expn)
            if m:
                t_var_name = m.groups(1)
                a_var_name = m.groups(2)
                opts.select_expn = m.groups(3)
            else:
                t_var_name = 't'
                a_var_name = 'a'
            opts.select_expn = 'lambda %s,%s: %s' % (t_var_name, a_var_name, opts.select_expn)
            select = compile(opts.select_expn, '<string>', 'eval')

        balance = Amount(0)
        for t in self.parser.ledger.transactions:
            if not cat.name in t.allocations:
                continue
            a = t.allocations[cat.name]
            amount = a.amount
            balance = balance + amount
            if select and not eval(select)(t,a):
                continue
            desc = t.description or ''
            print "%s %10s %10s %s" % (str(t.date.date()), str(amount), str(balance), desc)

    @cmdln.option("-i", "--init-stmt",     help="")
    @cmdln.option("-s", "--select-expn",   help="")
    @cmdln.option("-r", "--report-stmt",   help="")
    @cmdln.option("-f", "--finalize-stmt", help="")
    def do_report(self, subcmd, opts, t_var_name):
        """${cmd_name}: process transactions

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

        if not opts.report_stmt:
            opts.report_stmt = 'print %s.date, %s.amount, %s.description' % \
                (t_var_name, t_var_name, t_var_name)
        report = compile(opts.report_stmt, '<string>', 'exec')

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
            exec(report, context)
        if finalize:
            exec(finalize, context)


    @cmdln.alias("ls")
    def do_list(self, subcmd, opts, what):
        """${cmd_name}: lists the ledger file and all imported files

        ${cmd_usage}
        ${cmd_option_list}
        """
        self._parse_ledger()
        if what == 'accounts':
            for a in self.parser.ledger.accounts.keys():
                print a
        elif what == 'categories' or what == 'envelopes':
            for c in sorted(self.parser.ledger.categories.keys()):
                print c
        elif what == 'files':
            print self.parser.filename
            for cmd in self.parser.commands:
                if isinstance(cmd, ImportFile):
                    print cmd.path
        else:
            sys.stderr.write("Error: don't know how to list '%s'" % what)


    @cmdln.option("-s", "--select-expn",   help="")
    def do_process(self, subcmd, opts):
        """${cmd_name}: interactively process transactions

        ${cmd_usage}
        ${cmd_option_list}
        """

        class ListCompleter(object):
            def __init__(self, list):
                self.items = sorted(list)
            def complete(self, text, state):
                if state == 0:
                    if text:
                        self.matches = [i for i in self.items if i and i.startswith(text)]
                        if len(text) >= 2:
                            self.matches.extend([i for i in self.items if text in i])
                    else:    self.matches = self.items[:]
                return self.matches[state] if state < len(self.matches) else None

        self._parse_ledger()

        if not opts.select_expn:
            select = None
        else:
            m = re.match("([A-Za-z_]+):(.*$)", opts.select_expn)
            if m:
                t_var_name = m.groups(1)
                opts.select_expn = m.groups(2)
            else:
                t_var_name = 't'
            select = compile('lambda %s: %s' % (t_var_name, opts.select_expn), '<string>', 'eval')

        categories    = self.parser.ledger.categories.keys()
        cat_completer = ListCompleter(categories)
        readline.parse_and_bind('tab: complete')

        allocation_patterns = {}  # map of descriptions to (new_description, Allocation)
        cmd = 'q'
        for t in self.parser.ledger.transactions:
            if select and not eval(select)(t):
                continue

            orig_desc = t.description

            def print_txn(t):
                print "%s %s %s %s %s" % (t.id(), str(t.date.date()), t.account.name,
                        str(t.signed_amount()), t.description)

            prev_match = None
            for (pattern, value) in allocation_patterns.iteritems():
                if re.match(pattern, t.description):
                    prev_match = value
                    break

            cmd = ''
            remainder_allocation = None
            while cmd != 'q' and cmd != 'x':
                print
                print_txn(t)
                for (cat_name, a) in t.allocations.iteritems():
                    print "   ", a
                if t.remainder_allocation:
                    print "   ", t.remainder_allocation
                if prev_match:
                    print "Match: '%s', %s" % (prev_match[0], prev_match[1])

                if t.description in allocation_patterns:
                    prev_match = allocation_patterns[t.description]
                    pass

                remainder = t.unallocated_amount()
                if remainder > 0: print "%s remains unallocated" % remainder

                line = raw_input('Command [n,a,p,d,D,y,P,x,q,?]? ')
                if len(line) == 0: continue
                cmd = line[0]

                if cmd == '?':
                    print """\
?   show help
n   go to the next transaction
a   add an allocation
p   print the current transaction
d   edit the description; copy the old description to 'bank_description' property
D   edit the description; don't copy the old description
y   accept the matched previous update
P   edit the description pattern to match
x   exit (write ledger)
q   quit (don't write ledger)"""

                elif cmd == 'n' or cmd == 'x' or cmd == 'q':
                    if remainder_allocation:
                        allocation_patterns[orig_desc] = (t.description, remainder_allocation)
                    break

                elif cmd == 'p':
                    print_txn(t)

                elif cmd == 'a':
                    amount_str = raw_input('Amount: $').strip()
                    try:
                        if len(amount_str) == 0:
                            amount = None
                        else:
                            amount = Amount(str(amount_str))
                    except ValueError:
                        print "Error: invalid amount"
                        continue
                    if amount and amount <= 0:
                        print "Error: allocations must be positive"
                        continue
                    if amount and amount > remainder:
                        print "Error: can't allocate more than remains (%s)" % remainder
                        continue
                    if amount == remainder:
                        amount = None
                    readline.set_completer(cat_completer.complete)
                    cat_name = raw_input('Category: ').strip()
                    readline.set_completer(None)
                    if not cat_name in categories:
                        print "Error: unknown category '%s'" % cat_name
                        continue
                    cat = self.parser.ledger.categories[cat_name]

                    if not amount: # remainder allocation
                        a = RemainderAllocation(t, cat)
                        t.remainder_allocation = a
                    else:
                        a = Allocation(t, amount, )
                        t.allocations[cat_name] = a
                    self.parser.update_transaction(t)
                    print "allocate %s" % str(a)

                    if amount == None:
                        remainder_amount = a

                elif cmd == 'd' or cmd == 'D':
                    new_desc = raw_input('New description: ').strip()
                    if cmd == 'D':
                        write_bank_desc = False
                    elif 'bank_description' in t.properties:
                        yn = raw_input('Bank description exists; overwrite? ').strip().lower()
                        write_bank_desc = (yn == 'y' or yn == 'yes')
                    else:
                        write_bank_desc = True
                    if write_bank_desc:
                        t.properties['bank_description'] = Property('bank_description', t.description)
                    t.description = new_desc

                else:
                    print "Error: unknown command '%s'" % cmd

            if cmd == 'q' or cmd == 'x':
                break
        if cmd == 'x':
            print "Writing ledger"






if __name__ == "__main__":
    app = BreadTrail()
    sys.exit(app.main())
