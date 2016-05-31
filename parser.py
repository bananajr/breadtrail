from ledger import *
from type_utils import *
import parser_tokenize

import StringIO
import datetime
import os



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

    def __init__(self, filename, ledger=Ledger()):
        self.filename = filename
        self.commands = []        # list of commands parsed
        self.ledger = ledger      # ledger to parser into


    # make sure the last top-level command is of type t
    def assert_subcommand(self, t, command, subcommand):
        if len(self.commands) == 0 or not isinstance(self.commands[-1], t):
            msg = "'%s' subcommand outside of '%s' command context" % (subcommand, command)
            raise ParseError(self.reader, msg)

    # returns true if the last top-level command has a 'subcommands' attribute
    def can_subcommand(self):
        return len(self.commands) > 0 and hasattr(self.commands[-1], 'subcommands')

    def parse_date_or_raise(self, str):
        d = datetime_from_str(str)
        if d: return d
        raise ParseError(self.reader, "invalid date '%s'" % str)

    def parse_amount_or_raise(self, str):
        a = cents_from_str(str)
        if a is not None: return a
        raise ParseError(self.reader, "invalid amount '%s'" % str)


    def parse_add_account(self, line):
        tokens = line.token_values()
        if len(tokens) < 2 or len(tokens) > 3:
            raise ParseError(self.reader, "wrong number of arguments")
        name = tokens[1]
        account = Account(name, tokens[2] if len(tokens) == 3 else None)
        self.ledger.accounts[name] = account
        account.line = line
        self.commands.append(account)
        return account

    def parse_add_category(self, line):
        tokens = line.token_values()
        if len(tokens) < 2 or len(tokens) > 3:
            raise ParseError(self.reader, "wrong number of arguments")
        name = tokens[1]
        cat = Category(name, tokens[2] if len(tokens) == 3 else None)
        cat.line = line
        cat.subcommands = []
        self.ledger.categories[name] = cat
        self.commands.append(cat)
        return cat

    def assert_category_subcommand(self, subcommand):
        self.assert_subcommand(Category, "category", subcommand)

    def parse_category_goal(self, line):
        self.assert_category_subcommand('goal')
        tokens = line.token_values()
        if len(tokens) != 2:
            raise ParseError(self.reader, "wrong number of arguments")
        goal = CategoryGoal(tokens[1])
        goal.line = line
        if self.commands[-1].goal:
            raise ParseError(self.reader, "multiple goals for category")
        self.commands[-1].goal = goal
        self.commands[-1].subcommands.append(goal)

    def parse_category_budget(self, line):
        self.assert_category_subcommand('budget')
        pass

    def parse_transaction(self, date, line):
        tokens = line.token_values()
        if len(tokens) != 5:
            raise ParseError(self.reader, "wrong number of arguments (%d)" % len(tokens))
        amount = self.parse_amount_or_raise(tokens[1])
        if not tokens[3] in self.ledger.accounts:
            raise ParseError(self.reader, "account '%s' not defined" % tokens[3])
        account = self.ledger.accounts[tokens[3]]
        if tokens[2].lower() == 'into':
            t = IncomeTransaction(amount, date, account)
        elif tokens[2].lower() == 'from':
            t = ExpenditureTransaction(amount, date, account)
        else:
            raise ParseError(self.reader, "transaction should be 'into' or 'from'")
        t.line = line
        t.description = tokens[4]
        t.subcommands = []
        self.ledger.transactions.append(t)
        self.commands.append(t)

    def assert_transaction_subcommand(self, subcommand):
        self.assert_subcommand(Transaction, "transaction", subcommand)

    def parse_transaction_allocate(self, line):
        self.assert_transaction_subcommand(line.tokens[0].value)

        # allocate (<amount>|all|remainder) (to|into|as) <category> 
        tokens = line.token_values()
        if len(tokens) != 4:
            raise ParseError(self.reader, "wrong number of arguments")
        if tokens[1] == 'all' or tokens[1] == 'remainder':
            amount = None
        else:
            amount = self.parse_amount_or_raise(tokens[1])
        cmd = tokens[2]
        if cmd != 'to' and cmd != 'into' and cmd != 'as':
            raise ParseError(self.reader, "allocation should be 'to', 'into', or 'as'")
        cat_name = tokens[3]
        if not cat_name in self.ledger.categories:
            raise ParseError(self.reader, "category '%s' not defined" % cat_name)
        if cat_name in self.commands[-1].allocations:
            raise ParseError(self.reader, "multiple allocations to same category")
        alloc = Allocation(amount, self.ledger.categories[cat_name])
        alloc.line = line
        self.commands[-1].allocations[cat_name] = alloc
        self.commands[-1].subcommands.append(alloc)

    def parse_transaction_tag(self, line):
        self.assert_transaction_subcommand(line.tokens[0].value)
        tokens = line.token_values()
        if len(tokens) != 2:
            raise ParseError(self.reader, "wrong number of arguments")
        tag = Tag(tokens[1])
        tag.line = line
        self.commands[-1].tags.add(tag)
        self.commands[-1].subcommands.append(tag)

    def parse_transaction_property(self, line):
        self.assert_transaction_subcommand(line.tokens[0].value)
        tokens = line.token_values()
        if len(tokens) != 2:
            raise ParseError(self.reader, "wrong number of arguments")
        key = tokens[0][0:-1]
        value = tokens[1]
        prop = Property(key, value)
        prop.line = line
        self.commands[-1].properties[key] = value
        self.commands[-1].subcommands.append(prop)


    def parse_import(self, line):
        tokens = line.token_values()
        if len(tokens) != 2:
            raise ParseError(self.reader, "wrong number of arguments")
        path = os.path.expanduser(tokens[1])
        if not os.path.isabs(path):
            cur_dir = os.path.dirname(self.reader.filename)
            path = os.path.join(cur_dir, path)
        ic = ImportFile(path)
        ic.line = line
        ic.tokens = tokens
        self.commands.append(ic)
        p = Parser(path, self.ledger)
        p.parse()
        self.commands.extend(p.commands)





    def finalize_transaction(self, t):
        alloc_total = 0
        remainder_alloc = None
        for alloc in t.allocations.values():
            if alloc.amount == None:
                if remainder_alloc:
                    raise ParseError(self.reader, 'multiple remainder categories in transaction')
                remainder_alloc = alloc
                continue
            alloc_total = alloc_total + alloc.amount
        if alloc_total > t.amount:
            raise ParseError(self.reader, 'total of allocations is greater than transaction amount')
        if alloc_total < t.amount:
            r = t.amount - alloc_total
            if remainder_alloc:
                remainder_alloc.amount = r
            else:
                t.allocations['unallocated'] = Allocation(r, self.ledger.categories['unallocated'])

    def finalize_last_command(self):
        if len(self.commands) > 0 and isinstance(self.commands[-1], Transaction):
            self.finalize_transaction(self.commands[-1])


    commands = {
        'account'  : parse_add_account,
        'category' : parse_add_category,
        'import'   : parse_import,
    }

    continuation_commands = {
        'allocate' : parse_transaction_allocate,
        'tag'      : parse_transaction_tag,
        'goal'     : parse_category_goal,
        'budget'   : parse_category_budget,
    }


    # Parses a file into the ledger
    def parse(self):
        self.reader = LineReader(self.filename)
        for linenum, line in enumerate(self.reader.reader):
            self.reader.linenum = linenum + 1
            try:
                tok_line = parser_tokenize.Line(line)
            except parser_tokenize.LineParseError as error:
                raise ParseError(self.reader, str(error) + ' (column %d)' % error.index)

            # if no tokens, it's a blank line or comment
            if len(tok_line.tokens) == 0:
                if len(tok_line.suffix) == 0 or str.isspace(tok_line.suffix):
                    # blank lines terminate the previous command
                    self.finalize_last_command()
                    ws = Whitespace()
                    ws.line = tok_line
                    self.commands.append(ws)
                    continue
                else:
                    # comment- add to either commands or subcommands
                    comment = Comment()
                    comment.line = tok_line
                    if self.can_subcommand():
                        self.commands[-1].subcommands.append(comment)
                    else:
                        self.commands.append(comment)
                    continue

            cmd = tok_line.tokens[0].value.lower()

            # if first token has a prefix, it's a subcommand; otherwise,
            # it's a command or a transaction
            if len(tok_line.tokens[0].prefix) == 0:
                self.finalize_last_command()
                date = datetime_from_str(cmd)
                if date:
                    self.parse_transaction(date, tok_line)
                elif cmd in Parser.commands:
                    Parser.commands[cmd](self, tok_line)
                else:
                    raise ParseError(self.reader, 'unrecognized command: \'%s\'.' % cmd)

            # for continuations, should have a previous transaction
            elif not self.can_subcommand():
                raise ParseError(self.reader, 'subcommand out of context.')

            # continuations are either a command or a property
            else:
                if cmd in Parser.continuation_commands:
                    Parser.continuation_commands[cmd](self, tok_line)
                elif cmd.endswith(':'):
                    self.parse_transaction_property(tok_line)
                else:
                    raise ParseError(self.reader, 'unrecognized subcommand: \'%s\'.' % cmd)

        # done parsing this file
        self.finalize_last_command()
        eof = EndOfFile()
        eof.line = None
        self.commands.append(eof)

        return self.ledger
