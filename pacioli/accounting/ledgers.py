# Copyright (c) 2014, Satoshi Nakamoto Institute
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime
from collections import OrderedDict
from sqlalchemy.sql import func
from pacioli import db, models
import pacioli.accounting.rates as rates
from dateutil import parser

def query_entries(accountName, groupby, currency):
    if groupby == "All":
        ledger_entries = models.LedgerEntries \
            .query \
            .filter_by(ledger=accountName) \
            .filter_by(currency=currency) \
            .order_by(models.LedgerEntries.date.desc()) \
            .order_by(models.LedgerEntries.tside.desc()) \
            .all()
        account = foot_account(accountName, ledger_entries, 'All')
    elif groupby == "Daily":
        debit_ledger_entries = db.session\
            .query( \
                func.date_part('year', models.LedgerEntries.date), \
                func.date_part('month', models.LedgerEntries.date), \
                func.date_part('day', models.LedgerEntries.date), \
                func.sum(models.LedgerEntries.amount)) \
            .filter_by(ledger=accountName)\
            .filter_by(tside='debit')\
            .filter_by(currency=currency)\
            .group_by( \
                func.date_part('year', models.LedgerEntries.date), \
                func.date_part('month', models.LedgerEntries.date), \
                func.date_part('day', models.LedgerEntries.date)) \
            .all()
        credit_ledger_entries = db.session \
            .query( \
                func.date_part('year', models.LedgerEntries.date), \
                func.date_part('month', models.LedgerEntries.date), \
                func.date_part('day', models.LedgerEntries.date), \
                func.sum(models.LedgerEntries.amount))\
            .filter_by(currency=currency) \
            .filter_by(ledger=accountName) \
            .filter_by(tside='credit') \
            .group_by( \
                func.date_part('year', models.LedgerEntries.date), \
                func.date_part('month', models.LedgerEntries.date), \
                func.date_part('day', models.LedgerEntries.date)) \
            .all()
        ledger_entries = {}
        for entry in debit_ledger_entries:
            day = datetime.date(int(entry[0]), int(entry[1]), int(entry[2]))
            if not day in ledger_entries:
                ledger_entries[day] = {}
            ledger_entries[day]['debit'] = int(entry[3])
        for entry in credit_ledger_entries:
            day = datetime.date(int(entry[0]), int(entry[1]), int(entry[2]))
            if not day in ledger_entries:
              ledger_entries[day] = {}
            ledger_entries[day]['credit'] = int(entry[3])
        ledger_entries = OrderedDict(sorted(ledger_entries.items()))
        account = foot_account(accountName, ledger_entries, 'Summary')
    elif groupby == "Monthly":
        debit_ledger_entries = db.session \
            .query( \
                func.date_part('year', models.LedgerEntries.date), \
                func.date_part('month', models.LedgerEntries.date), \
                func.sum(models.LedgerEntries.amount)) \
            .filter_by(ledger=accountName) \
            .filter_by(currency=currency) \
            .filter_by(tside='debit') \
            .group_by( \
                func.date_part('year', models.LedgerEntries.date), \
                func.date_part('month', models.LedgerEntries.date)) \
            .all()
        credit_ledger_entries = db.session\
            .query( \
                func.date_part('year', models.LedgerEntries.date), \
                func.date_part('month', models.LedgerEntries.date), \
                func.sum(models.LedgerEntries.amount)) \
            .filter_by(ledger=accountName) \
            .filter_by(currency=currency) \
            .filter_by(tside='credit') \
            .group_by( \
                func.date_part('year', models.LedgerEntries.date), \
                func.date_part('month', models.LedgerEntries.date)) \
            .all()
        ledger_entries = {}
        for entry in debit_ledger_entries:
            month = datetime.date(int(entry[0]), int(entry[1]), 1)
            if not month in ledger_entries:
                ledger_entries[month] = {}
            ledger_entries[month]['debit'] = int(entry[2])
        for entry in credit_ledger_entries:
            month = datetime.date(int(entry[0]), int(entry[1]), 1)
            if not month in ledger_entries:
                ledger_entries[month] = {}
            ledger_entries[month]['credit'] = int(entry[2])
        ledger_entries = OrderedDict(sorted(ledger_entries.items()))
        account = foot_account(accountName, ledger_entries, 'Summary')
    return [account, ledger_entries]

def foot_account(accountName, entries, interval):
  account = {}
  account['accountName'] = accountName
  account['totalDebit'] = 0
  account['totalCredit'] = 0
  account['debitBalance'] = 0
  account['creditBalance'] = 0
  if interval == 'All':
    for entry in entries:
      if entry.tside == 'debit' and entry.ledger == account['accountName']:
        account['totalDebit'] += entry.amount
      elif entry.tside == 'credit' and entry.ledger == account['accountName']:
        account['totalCredit'] += entry.amount
    if account['totalDebit'] > account['totalCredit']:
      account['debitBalance'] = account['totalDebit'] - account['totalCredit']
    elif account['totalDebit'] < account['totalCredit']:
      account['creditBalance'] = account['totalCredit'] - account['totalDebit']
    return account
  elif interval == 'Summary':
    for entry in entries:
      if 'debit' in entries[entry]:
        account['totalDebit'] += entries[entry]['debit']
      if 'credit' in entries[entry]:
        account['totalCredit'] += entries[entry]['credit']
    if account['totalDebit'] > account['totalCredit']:
      account['debitBalance'] = account['totalDebit'] - account['totalCredit']
    elif account['totalDebit'] < account['totalCredit']:
      account['creditBalance'] = account['totalCredit'] - account['totalDebit']
    return account
    
def get_balance(accountName, querydate):
    if type(querydate) is not datetime.datetime:
        querydate = parser.parse(querydate)
    transactions = query = db.session.query(\
      models.LedgerEntries.amount,\
      models.LedgerEntries.date,\
      models.LedgerEntries.tside).\
      filter(models.LedgerEntries.ledger_name==accountName, models.LedgerEntries.date <= querydate).\
      all()
    balance = 0
    for transaction in transactions:
        if transaction[2] == 'debit':
            balance += transaction[0]
        elif transaction[2] == 'credit':
            balance -= transaction[0]
    if balance > 0:
        debitBalance = balance
        creditBalance = 0
    elif balance < 0:
        debitBalance = 0
        creditBalance = balance
    else:
        debitBalance = 0
        creditBalance = 0
    balance = {'accountName': accountName,\
     'debitBalance' : debitBalance,\
     'creditBalance' : creditBalance}
    return balance
