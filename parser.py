from ledger import *
from type_utils import *

import shlex
import datetime



class ParseError(Exception):
    def __init__(self, linereader, msg=None):
        if msg == None:
            msg = "parsing failed"
        self.msg = msg
        self.filename = linereader.filename
        self.linenum = linereader.linenum

    def __str__(self):
        return "error (%s:%d): %s" % (self.filename, self.linenum, self.msg)



class LineReader(object):
    def __init__(self, filename):
        self.filename = filename
        self.reader = open(filename)
        self.linenum = 0



class Parser(object):
    reader_stack = [] # stack of line readers
    last_command = None
    ledger = Ledger()


    def assert_subcommand(self, t, command, subcommand):
        if not isinstance(self.last_command, t):
            msg = "'%s' subcommand outside of '%s' command context" % (subcommand, command)
            raise ParseError(self.reader_stack[-1], msg)


    def parse_date_or_raise(self, str):
        d = datetime_from_str(str)
        if d: return d
        raise ParseError(self.reader_stack[-1], "invalid date '%s'" % str)

    def parse_amount_or_raise(self, str):
        a = cents_from_str(str)
        if a: return a
        raise ParseError(self.reader_stack[-1], "invalid amount '%s'" % str)


    def parse_add_account(self, tokens):
        if len(tokens) < 2 or len(tokens) > 3:
            raise ParseError(self.reader_stack[-1])
        name = tokens[1]
        account = Account(name, tokens[2] if len(tokens) == 3 else None)
        self.ledger.accounts[name] = account
        self.last_command = account
        return account

    def parse_add_category(self, tokens):
        if len(tokens) < 2 or len(tokens) > 3:
            raise ParseError(self.reader_stack[-1])
        name = tokens[1]
        cat = Category(name, tokens[2] if len(tokens) == 3 else None)
        self.ledger.categories[name] = cat
        self.last_command = cat
        return cat

    def assert_category_subcommand(self, subcommand):
        self.assert_subcommand(Category, "category", subcommand)

    def parse_category_goal(self, tokens):
        self.assert_category_subcommand('goal')
        pass

    def parse_category_budget(self, tokens):
        self.assert_category_subcommand('budget')
        pass

    def parse_transaction(self, date, tokens):
        if len(tokens) != 5:
            raise ParseError(self.reader_stack[-1])
        amount = self.parse_amount_or_raise(tokens[1])
        if not tokens[3] in self.ledger.accounts:
            raise ParseError(self.reader_stack[-1], "account '%s' not defined" % tokens[3])
        account = self.ledger.accounts[tokens[3]]
        if tokens[2].lower() == 'into':
            t = IncomeTransaction(amount, date, account)
        elif tokens[2].lower() == 'from':
            t = ExpenditureTransaction(amount, date, account)
        else:
            raise ParseError(self.reader_stack[-1])
        t.description = tokens[4]
        self.ledger.transactions.append(t)
        self.last_command = t

    def assert_transaction_subcommand(self, subcommand):
        if not isinstance(self.last_command, Transaction):
            msg = "'%s' subcommand outside of transaction context" % subcommand
            raise ParseError(self.reader_stack[-1], msg)

    def parse_transaction_allocate(self, tokens):
        self.assert_transaction_subcommand('allocate')
        if len(tokens) == 4:
            if tokens[1] == 'all' or tokens[1] == 'remainder':
                amount = None
            else:
                amount = self.parse_amount_or_raise(tokens[1])
            cmd = tokens[2]
            cat_name = tokens[3]
        elif len(tokens) == 3:
            amount = None
            cmd = tokens[1]
            cat_name = tokens[2]
        else:
            raise ParseError(self.reader_stack[-1])
        if cmd != 'to' and cmd != 'into' and cmd != 'as':
            raise ParseError(self.reader_stack[-1])
        if not cat_name in self.ledger.categories:
            raise ParseError(self.reader_stack[-1], "category '%s' not defined" % cat_name)
        self.last_command.allocations.append(Allocation(amount, self.ledger.categories[cat_name]))


    def parse_transaction_property(self, tokens):
        self.assert_transaction_subcommand('property')
        if len(tokens) != 2:
            raise ParseError(self.reader_stack[-1])
        key = tokens[0]
        value = tokens[1]
        if key[-1:] == ':': key = key[0:-1]
        self.last_command.properties[key] = value



    def finalize_transaction(self, t):
        alloc_total = 0
        remainder_alloc = None
        for alloc in t.allocations:
            if alloc.amount == None:
                if remainder_alloc:
                    raise ParseError(self.reader_stack[-1], 'multiple remainder categories in transaction')
                remainder_alloc = alloc
                continue
            alloc_total = alloc_total + alloc.amount
        if alloc_total > t.amount:
            raise ParseError(self.reader_stack[-1], 'total of allocations is greater than transaction amount')
        if alloc_total < t.amount:
            r = t.amount - alloc_total
            if remainder_alloc:
                remainder_alloc.amount = r
            else:
                t.allocations.append(Allocation(r, self.ledger.categories['unallocated']))


    commands = {
        'account'  : parse_add_account,
        'category' : parse_add_category,
    }

    continuation_commands = {
        'allocate' : parse_transaction_allocate,
        'goal'     : parse_category_goal,
        'goal:'    : parse_category_goal,
        'budget'   : parse_category_budget,
        'budget:'  : parse_category_budget
    }



    # Parses a file into the ledger
    def parse(self, filename):
        r = LineReader(filename)
        for linenum, line in enumerate(r.reader):
            r.linenum = linenum + 1

            continuation = True if line.startswith((' ', '\t')) else False
            tokens = shlex.split(line)
            if (len(tokens) == 0):
                if isinstance(self.last_command, Transaction):
                    self.finalize_transaction(self.last_command)
                self.last_command = None
                continue

            # if it's not a continuation, it's a command or a transaction
            if not continuation:
                cmd = tokens[0].lower()
                date = datetime_from_str(cmd)
                if date:
                    self.parse_transaction(date, tokens)
                elif cmd in Parser.commands:
                    Parser.commands[cmd](self, tokens)
                else:
                    raise ParseError(r, 'unrecognized command: \'%s\'.' % cmd)

            # for continuations, should have a previous transaction
            elif self.last_command == None:
                raise ParseError(r, 'continuation command before first transaction.')

            # continuations are either a command or a property
            else:
                cmd = tokens[0].lower()
                if cmd in Parser.continuation_commands:
                    Parser.continuation_commands[cmd](self, tokens)
                elif cmd.endswith(':'):
                    self.parse_transaction_property(tokens)
                else:
                    raise ParseError(r, 'unrecognized continuation command: \'%s\'.' % cmd)

        if isinstance(self.last_command, Transaction):
            self.finalize_transaction(self.last_command)

        return self.ledger
