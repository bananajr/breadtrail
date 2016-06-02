#!/usr/bin/env python
from ofxparse import OfxParser
from parser import Parser as LedgerParser, ParseError as LedgerParseError
from ledger import *
from type_utils import *
from config import config

import sys
import argparse

from filter import filter_transaction



progname = None
args     = None


txn_count_imported = 0
txn_count_new      = 0


# returns a dictionary mapping ofxid to transactions in the list
# for only transactions that have an ofxid
def ledger_transactions_by_ofxid(txns):
    def generator():
        for txn in txns:
            if 'ofxid' in txn.properties:
                yield txn.properties['ofxid'], txn
            if 'ofx_id' in txn.properties:
                yield txn.properties['ofx_id'], txn
            if 'bankid' in txn.properties:
                yield txn.properties['bankid'], txn
            if 'bank_id' in txn.properties:
                yield txn.properties['bank_id'], txn
    return dict(generator())


# filters out (and sorts) transactions from the ofx tree that have
# a transaction with the same ofxid in the list of ledger transactions
def filter(ofx, lgr_txns):
    global txn_count_imported, txn_count_new
    lgr_txns_by_ofxid = ledger_transactions_by_ofxid(lgr_txns)
    ofx_txns = ofx.account.statement.transactions
    txn_count_imported = len(ofx_txns)

    filtered_ofx_txns = [t for t in ofx_txns if not t.id in lgr_txns_by_ofxid]
    txn_count_new = len(filtered_ofx_txns)
    if txn_count_new == 0:
        sorted_ofx_txns = filtered_ofx_txns
#    elif all(isinstance(txn, InvestmentTransaction) for txn in filtered_ofx_txns):
#        if all(txn.settleDate is not None for txn in filtered_ofx_txns):
#            sorted_ofx_txns = sorted(filtered_ofx_txns, key=lambda t: t.settleDate)
#        else:
#            sorted_ofx_txns = sorted(filtered_ofx_txns, key=lambda t: t.tradeDate)
    else:
        sorted_ofx_txns = sorted(filtered_ofx_txns, key=lambda t: t.date)
    return sorted_ofx_txns


def ofx_txn_to_ledger_txn(t):
    #t.type    # unicode string: 'payment', 'credit'
    #t.date    # datetime.datetime
    #t.amount  # decimal.Decimal: negative for payments
    #t.payee   # unicode string
    #t.id      # unicode string
    #t.memo
    #t.sic
    #t.mcc
    #t.checknum
    cents = cents_from_decimal(t.amount)
    it = ImportedTransaction(t.date, cents_from_decimal(t.amount), account.name)
    it.description = str(t.payee)

    if t.memo and len(t.memo) > 0 and t.memo != t.payee:
        it.properties['bank_memo'] = str(t.memo)
    if t.id and len(t.id) > 0:
        it.properties['bank_id'] = str(t.id)
    it.tags.append("import_unverified")
    return it



def finalize_ledger_txn(it):
    if args.memo and 'bank_memo' not in it.properties:
        it.properties['bank_memo'] = it.description
        if args.memo == 'title':
            it.description = titlecase_str(it.description)
    return it



def print_txn(t, f):
    datestr = datetime_to_date_str(t.date)
    dirstr = "from" if t.amount < 0 else "into"
    amtstr = cents_to_str(t.amount if t.amount >= 0 else -t.amount)
    line = (datestr, " $", amtstr, " ", dirstr, " ", t.account_name, " ", quote_str(t.description))
    for tok in line: f.write(tok)
    f.write("\n")
    for (cat_name, a) in t.allocations.iteritems():
        if not a.amount:
            line = ("    allocate all to ", cat_name)
        else:
            line = ("    allocate $", cents_to_str(a.amount), " to ", cat_name)
        for tok in line: f.write(tok)
        f.write("\n")
    for tag in t.tags:
        f.write("    tag ")
        f.write(quote_str_if_needed(tag))
        f.write("\n")
    for key, value in t.properties.iteritems():
        line = ("    ", key, ": ", quote_str_if_needed(value))
        for tok in line: f.write(tok)
        f.write("\n")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Import & convert OFX file')
    parser.add_argument('-l', '--ledger', type=str,
                        help='Ledger file to compare against')
    parser.add_argument('--memo', choices=['none', 'title'], default=None,
                        help='make a bank_memo: property and update the memo')
    parser.add_argument('--combine-memo', dest="combine_memo", action="store_true", 
                        help='Combine the bank memo field with the payee')
    parser.set_defaults(combine_memo=False);
    parser.add_argument('--stats', dest="output_stats", action="store_true", default=False,
                        help='Output stats even when printing to stdout')
    parser.set_defaults(output_stats=False);
    parser.add_argument('--ofx-account', type=str, default=None,
                        help='OFX account name to use (default: first')
    parser.add_argument('ofx_filename', metavar="FILENAME", help='OFX file to import')
    parser.add_argument('account_name', metavar="ACCOUNT", help='Ledger account name to compare against')
    progname = sys.argv[0]
    args = parser.parse_args(sys.argv[1:])

    try:
        p = LedgerParser(args.ledger or config.get_ledger_path())
        p.parse()
        ledger = p.ledger
    except LedgerParseError as e:
        sys.stderr.write("Error (%s:%d): %s" % (e.filename, e.linenum, e.msg))
        if not e.msg.endswith('\n'):
            sys.stderr.write('\n')
        sys.exit(1)

    if not args.account_name in ledger.accounts:
        sys.stderr.write("Error: no account named '%s' in ledger" % args.account_name)
        sys.exit(1)
    laccount = ledger.accounts[args.account_name]
    ltxns = [t for t in ledger.transactions if t.account is laccount]

    ofx = OfxParser.parse(file(args.ofx_filename))
    new_txns = filter(ofx, ltxns)

    for ot in new_txns:
        lt = ofx_txn_to_ledger_txn(ot)
        filter_transaction(ledger, lt)
        lt = finalize_ledger_txn(lt)
        print_txn(lt, laccount, sys.stdout)
        print

    if (args.output_stats):
        print "%d imported transactions, %d new" % (txn_count_imported, txn_count_new)


