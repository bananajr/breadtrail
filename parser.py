from ledger import *
from type_utils import *
from parser_tokenize import Token, Line, LineParseError

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


# returns subcommands divided into (both, only_list1, only_list2)
def intersect_subcommands(list1, list2):
    both       = [x for x in list1 if x in list2]
    only_list1 = [x for x in list1 if x not in list2]
    only_list2 = [x for x in list2 if x not in list1]
    return (both, only_list1, only_list2)



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

    def update_account(self, a):
        a.line.tokens[1].value = a.name
        if a.description:
            if len(a.line.tokens) == 3:
                a.line.tokens[2].value = a.description
            else:
                a.line.tokens.append(Token(a.description))
        elif len(a.line.tokens) == 3:
            a.line.tokens.pop(2)
        a.line.rebuild()


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

    def update_category(self, c):
        c.line.tokens[1].value = c.name
        if c.description:
            if len(c.line.tokens) == 3:
                c.line.tokens[2].value = c.description
            else:
                c.line.tokens.append(Token(c.description))
        elif len(c.line.tokens) == 3:
            c.line.tokens.pop(2)
        c.line.rebuild()


    def assert_category_subcommand(self, subcommand):
        self.assert_subcommand(Category, "category", subcommand)

    def parse_category_goal(self, line):
        self.assert_category_subcommand('goal')
        tokens = line.token_values()
        if len(tokens) != 2:
            raise ParseError(self.reader, "wrong number of arguments")
        goal = CategoryGoal(cents_from_str(tokens[1]))
        goal.line = line
        if self.commands[-1].goal:
            raise ParseError(self.reader, "multiple goals for category")
        self.commands[-1].goal = goal
        self.commands[-1].subcommands.append(goal)

    def update_category_goal(self, g):
        g.line.tokens[1].value = '$' + cents_to_str(g.amount)
        g.line.rebuild()

    def parse_category_budget(self, line):
        self.assert_category_subcommand('budget')
        pass

    def update_category_budget(self, b):
        pass

    def parse_transaction(self, date, line):
        tokens = line.token_values()
        if len(tokens) != 5:
            raise ParseError(self.reader, "wrong number of arguments (%d)" % len(tokens))
        amount = self.parse_amount_or_raise(tokens[1])
        if not tokens[3] in self.ledger.accounts:
            raise ParseError(self.reader, "account '%s' not defined" % tokens[3])
        account = self.ledger.accounts[tokens[3]]
        if tokens[2].lower() == 'from':
            amount = -amount
        elif tokens[2].lower() != 'into':
            raise ParseError(self.reader, "transaction should be 'into' or 'from'")
        t = Transaction(amount, date, account)
        t.line = line
        t.description = tokens[4]
        t.subcommands = []
        self.ledger.transactions.append(t)
        self.commands.append(t)

    def update_transaction(self, t):
        if isinstance(t, IncomeTransaction):
            if t.line.tokens[2].value.lower() is not 'into':
                t.line.tokens[2].value = 'into'
        else:
            if t.line.tokens[2].value.lower() is not 'from':
                t.line.tokens[2].value = 'from'
        t.line.tokens[3].value = quote_str_if_needed(t.account.name)
        t.line.tokens[4].value = quote_str(t.description)
        t.line.rebuild()

        # update, add, and remove allocation subcommands
        (both, to_del, to_add) = intersect_subcommands(t.subcommands, t.allocations.values())
        for a in both:
            self.update_transaction_allocate(a)
        for a in to_add:
            self.update_transaction_allocate(a)
            t.subcommands.append(a)
        for a in to_del:
            if not isinstance(a, Allocation): continue
            t.subcommands.remove(a)

        # update, add, and remove property subcommands
        (both, to_del, to_add) = intersect_subcommands(t.subcommands, t.properties.values())
        for prop in both:
            self.update_transaction_property(prop)
        for prop in to_add:
            self.update_transaction_property(prop)
            t.subcommands.append(prop)
        for prop in to_del:
            if not isinstance(prop, Property): continue
            t.subcommands.remove(prop)

        # update, add, and remove tag subcommands
        (both, to_del, to_add) = intersect_subcommands(t.subcommands, t.tags)
        for tag in both:
            self.update_transaction_tag(tag)
        for tag in to_add:
            self.update_transaction_tag(tag)
            t.subcommands.append(tag)
        for tag in to_del:
            if not isinstance(tag, Tag): continue
            t.subcommands.remove(tag)


    def assert_transaction_subcommand(self, subcommand):
        self.assert_subcommand(Transaction, "transaction", subcommand)

    def parse_transaction_allocate(self, line):
        # put [(<amount>|all|remainder)] into [envelope] <category> # for income (+amount)
        # take [(<amount|all|remainder)] from [envelope] <category> # for expense (-amount)
        self.assert_transaction_subcommand(line.tokens[0].value)
        tokens = line.token_values()
        if tokens[0] == "put":
            if self.commands[-1].sign != 1:
                raise ParseError(self.reader, "'put' allocation for income transaction")
        else: # tokens[0] is "take"
            if self.commands[-1].sign != -1:
                raise ParseError(self.reader, "'take' allocation for expenditure transaction")
        tokens = line.token_values()
        if len(tokens) < 3:
            raise ParseError(self.reader, "need at least 2 arguments")
        ti = 1
        if tokens[ti] in ['all', 'remainder', 'rest']:
            amount = None
            ti = ti + 1
        else:
            amount = cents_from_str(tokens[ti])
            if amount is not None:
                if amount < 0:
                    raise ParseError(self.reader, "allocation amounts must be positive")
                ti = ti + 1
        if tokens[0] == "put":
            if tokens[ti] != 'into':
                raise ParseError(self.reader, "parsing error: 'put' needs 'into' after amount")
        else: # tokens[0] is "take"
            if tokens[ti] != 'from':
                raise ParseError(self.reader, "parsing error: 'take' needs 'from' after amount")
        ti = ti + 1
        try:
            if tokens[ti] is 'envelope':
                ti = ti + 1
            cat_name = tokens[ti]
        except IndexError:
            raise ParseError(self.reader, "too few arguments")

        alloc_remainder = self.commands[-1].amount
        for a in self.commands[-1].allocations.values():
            if a.amount is None:
                raise ParseError(self.reader, "overallocated")
            alloc_remainder -= a.amount
        if amount is None:
            if alloc_remainder == 0:
                raise ParseError(self.reader, "overallocated")
            amount = alloc_remainder
        elif amount > alloc_remainder:
            raise ParseError(self.reader, "overallocated")

        if not cat_name in self.ledger.categories:
            raise ParseError(self.reader, "category '%s' not defined" % cat_name)
        if cat_name in self.commands[-1].allocations:
            raise ParseError(self.reader, "multiple allocations to same category")
        alloc = Allocation(amount, self.ledger.categories[cat_name])
        alloc.line = line
        self.commands[-1].allocations[cat_name] = alloc
        self.commands[-1].subcommands.append(alloc)

    def update_transaction_allocate(self, a):
        if not hasattr(a, 'line'):
            a.line = Line('    allocate $%s to %s\n' % (
                    cents_to_str(a.amount),
                    quote_str_if_needed(a.category.name)))
            return
        diff = False
        if a.amount == None:
            if a.line.tokens[1].value.lower() not in ['all', 'remainder']:
                a.line.tokens[1] = 'all'
                diff = True
        elif a.amount != cents_from_str(a.line.tokens[1].value):
            a.line.tokens[1] = '$' + cents_to_str(a.amount)
            diff = True
        if a.line.tokens[3] != a.category.name:
            a.line.tokens[3] = a.category.name
            diff = True
        if diff:
            a.line.rebuild()


    def parse_transaction_tag(self, line):
        self.assert_transaction_subcommand(line.tokens[0].value)
        tokens = line.token_values()
        if len(tokens) != 2:
            raise ParseError(self.reader, "wrong number of arguments")
        tag = Tag(tokens[1])
        tag.line = line
        self.commands[-1].tags.add(tag)
        self.commands[-1].subcommands.append(tag)

    def update_transaction_tag(self, t):
        if not hasattr(t, 'line'):
            t.line = Line('    tag %s\n' % quote_str_if_needed(t.val))
            return
        if t.line.tokens[1].value != t.val:
            t.line.tokens[1].value = t.val
            t.line.rebuild()


    def parse_transaction_property(self, line):
        self.assert_transaction_subcommand(line.tokens[0].value)
        tokens = line.token_values()
        if len(tokens) != 2:
            raise parseerror(self.reader, "wrong number of arguments")
        key = tokens[0][0:-1]
        prop = Property(key, tokens[1])
        prop.line = line
        self.commands[-1].properties[key] = prop
        self.commands[-1].subcommands.append(prop)

    def update_transaction_property(self, p):
        if not hasattr(p, 'line'):
            p.line = Line('    %s: %s\n' % (
                    quote_str_if_needed(p.key),
                    quote_str_if_needed(p.value)))
            return
        if p.line.tokens[0].value[0:-1] != p.key or p.line.tokens[1].value != p.value:
            p.line.tokens[0].value = p.key + ':'
            p.line.tokens[1].value = p.value
            p.line.rebuild()


    def parse_import(self, line):
        tokens = line.token_values()
        if len(tokens) != 2:
            raise parseerror(self.reader, "wrong number of arguments")
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
        'put'      : parse_transaction_allocate,
        'take'     : parse_transaction_allocate,
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
                tok_line = Line(line)
            except LineParseError as error:
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
