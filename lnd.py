#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# unsafepay - because Telegram could empty your channels
# Copyright (C) 2018-2019  Martino Salvetti
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
telegram bot
"""
import re
import subprocess
import json
from decimal import Decimal
import time
import base64
import git
import hashlib
import binascii
from fiat_rate import Fiat

_24H = 60 * 60 * 24
TX_LINK = 'https://www.smartbit.com.au/tx/%s'
CH_LINK = 'https://1ml.com/channel/%s'
CH_LINK_ALT = 'https://lightblock.me/lightning-channel/%s'
ND_LINK = 'https://1ml.com/node/%s'
ND_LINK_ALT = 'https://lightblock.me/lightning-node/%s'

fiat = Fiat()


def to_btc_str(sats):
    return '{:.8f}'.format(Decimal(sats) / Decimal(1e8))


def to_sat_str(msats):
    return '{:.3f}'.format(Decimal(msats) / Decimal(1e3))


def amt_to_sat(amt):
    """Get sat or btc amt"""
    symbol = set('€Ee') & set(amt)
    if symbol:
        eur = float(amt.replace(symbol.pop(), ''))
        return fiat.to_satoshis(eur)
    if '.' in amt:
        return int(Decimal(amt) * Decimal(1e8))
    return int(amt)


class NodeException(Exception):
    pass


class Lncli:
    """Interface to lncli command"""
    CMD = 'lncli'

    def __init__(self):
        self._1ml = True
        self._lightblock = True
        self.aliases = {}
        self._cities = None
        self._updated = 0
        self.update_aliases()

    @staticmethod
    def _command(*cmd):
        print('$', Lncli.CMD, *cmd, sep='  ')
        process = subprocess.Popen(
            [Lncli.CMD] + list(cmd),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        if process.returncode == 0:
            return json.loads(str(out, 'utf-8'))
        raise NodeException(str(err, 'utf-8'))

    def update_aliases(self):

        if time.time() - self._updated < _24H:
            return
        try:
            graph = self._command('describegraph')
        except NodeException as e:
            print(e)
            return
        aliases = {}
        for node in graph['nodes']:
            aliases[node['pub_key']] = node['alias']
        self.aliases = aliases
        self._updated = time.time()

    def info(self):
        """Get information about the node"""
        obj = self._command('getinfo')
        n_chs = len(self._command('listchannels')['channels'])
        rows = [obj['alias']]
        self._1ml and rows.append(ND_LINK % obj['identity_pubkey'])
        self._lightblock and rows.append(ND_LINK_ALT % obj['identity_pubkey'])
        rows.append('Active channels: %s' % obj['num_active_channels'])
        rows.append('Channels: %d' % n_chs)
        if obj['num_pending_channels']:
            rows.append('Pending channels: %s' % obj['num_pending_channels'])
        rows.append('Num peers: %s' % obj['num_peers'])
        if obj['uris']:
            rows.append('%s' % obj['uris'][0])
        if not obj['synced_to_chain']:
            rows.append('Not synced')
        rows.append(self.balance())
        rows.append(self.feereport())
        commit = git.get_git_revision_short_hash()
        if commit:
            rows.append('Version: %s' % commit)
        return '\n'.join(rows)

    def uri(self):
        """Get the node uri
        tg> uri"""
        return self._command('getinfo')['uris'][0]

    def pay(self, pay_req, amt=None):
        """Pay an invoice
        tg> pay <payment request> [amt]
        If amt is a float it is considered a bitcoin amount, if amt is an integer it is considered a satoshi amount"""
        # lncli payinvoice [command options] pay_req
        cmd = ['payinvoice', '-f']
        if pay_req.lower().startswith('lightning:'):
            pay_req = pay_req[10:]
        if amt:
            cmd.append('--amt')
            cmd.append('%d' % amt_to_sat(amt))
        cmd.append(pay_req)
        out = self._command(*cmd)
        rows = []
        if out['payment_error']:
            rows.append('Error: %s' % out['payment_error'])
        else:
            route = out['payment_route']
            rows.append('Amount: %s btc' % to_btc_str(route['total_amt']))
            rows.append('Fee: %s sat' % to_sat_str(
                route['total_fees_msat'] if 'total_fees_msat' in route else 0))
            rows.append('# hops: %d' % len(route['hops']))
        return '\n'.join(rows)

    def add(self, amt=None):
        """Add invoice
        tg> add [amt]
        If amt is a float it is considered a bitcoin amount, if amt is an integer it is considered a satoshi amount"""
        # lncli addinvoice value
        cmd = ['addinvoice', '--expiry', '43200']
        if amt:
            cmd.append('%d' % amt_to_sat(amt))
        out = self._command(*cmd)
        if 'pay_req' in out:
            return out['pay_req'], out['r_hash']
        else:
            return out

    @staticmethod
    def __is_expired(expiration: int):
        return time.time() > expiration

    def payment(self, r_hash=None):
        """Check a payment status
        tg> payment [r_hash]
        If r_hash is not provided the last payment will be checked
        """
        PAID = '\U0001f44d'
        NOT_PAID = '\U0001f44e'
        NOT_FOUND = 'Invoice not found'
        if r_hash and len(r_hash) == 64 and re.match('^[\da-f]{64}$', r_hash):
            invoice = self._command('lookupinvoice', r_hash)
        else:
            invoices = self._command('listinvoices', '--max_invoices', '1')['invoices']
            if not invoices:
                return NOT_FOUND
            invoice = invoices[0]

        rows = []
        paid = PAID if invoice['settled'] else NOT_PAID
        rows.append('{} {}'.format(to_btc_str(invoice['value']), paid))
        if not r_hash:
            r_hex = base64.decodebytes(bytes(invoice['r_hash'], 'ascii')).hex()
            rows.append(r_hex)

        creation = time.ctime(int(invoice['creation_date']))
        rows.append('Created on {}'.format(creation))

        if invoice['settled']:
            settled = time.ctime(int(invoice['settle_date']))
            rows.append('Settled on {}'.format(settled))
        else:
            expiration = time.ctime(int(invoice['creation_date']) + int(invoice['expiry']))
            expired = self.__is_expired(int(invoice['creation_date']) + int(invoice['expiry']))
            exp_format = 'Expired on {}' if expired else 'Expires {}'
            rows.append(exp_format.format(expiration))

        return '\n'.join(rows)

    def balance(self):
        """Walletbalance and channelbalance
        tg> balance"""
        wallet = self._command('walletbalance')
        channel = self._command('channelbalance')
        rows = []
        rows.append('Wallet')
        for key in wallet:
            rows.append(
                '%s: %s' % (key.replace('_', ' '), to_btc_str(wallet[key])))
        rows.append('Channel')
        for key in channel:
            rows.append(
                '%s: %s' % (key.replace('_', ' '), to_btc_str(channel[key])))
        return '\n'.join(rows)

    def address(self):
        """Generate a new bech32 bitcoin address
        tg> address"""
        out = self._command('newaddress', 'p2wkh')
        return out['address']

    def _alias(self, pubkey, default=None):
        """Return a not null alias or the pubkey"""
        return self.aliases.get(pubkey) or default or self._city_alias(pubkey)

    def _city_alias(self, pubkey):
        CITYSCAPE = '\U0001f3d9'
        CITY_DUSK = '\U0001f306'
        if self._cities is None:
            with open('cities.txt', 'rt') as fd:
                self._cities = [x.strip() for x in fd.readlines()]
        city = self._cities[self._int_hash_pubkey(pubkey) % len(self._cities)]
        emoji = CITY_DUSK if self.aliases else CITYSCAPE
        return emoji + ' ' + city

    @staticmethod
    def _int_hash_pubkey(pubkey):
        hash = hashlib.sha256(binascii.unhexlify(pubkey)).digest()
        return int.from_bytes(hash, byteorder='big', signed=False)

    def channels(self, filter_by_alias=None, pending=True):
        """List channels
        tg> channles [filter]
        Specify a filter to select channels by aliases and pubkeys"""
        # lncli listchannels
        chs = self._command('listchannels')['channels']
        messages = []
        for ch in chs:
            rows = []
            pubkey = ch['remote_pubkey']
            alias = self._alias(pubkey)
            if not filter_by_alias or filter_by_alias in alias or filter_by_alias in pubkey:
                active = '\u26a1\ufe0f' if ch['active'] else '\U0001f64a'
                private = '\U0001f512' if ch['private'] else ''
                rows.append('%s %s%s' % (alias, active, private))
                if not private and ch['chan_id'] != '0':
                    self._1ml and rows.append(CH_LINK % ch['chan_id'])
                    self._lightblock and rows.append(CH_LINK_ALT % ch['chan_id'])
                rows.append(to_btc_str(ch['capacity']))
                local = to_btc_str(ch['local_balance'])
                remote = to_btc_str(ch['remote_balance'])
                rows.append('L: %s R: %s' % (local, remote))
                rows.append(TX_LINK % (ch['channel_point'].split(':')[0]))
                messages.append('\n'.join(rows))
        if pending:
            messages += self.pending(filter_by_alias)
        return messages

    def chs(self):
        """Short version of channels
        tg> chs"""
        chs = self._command('listchannels')['channels']
        rows = []
        for ch in chs:
            pubkey = ch['remote_pubkey']
            active = '\u26a1\ufe0f' if ch['active'] else '\U0001f64a'
            capacity = to_btc_str(ch['capacity']).rstrip('0').rstrip('.')
            private = '\U0001f512' if ch['private'] else ''
            rows.append('%s %s %s%s' % (self._alias(pubkey), capacity, active, private))
        return '\n'.join(rows)

    def pending(self, filter_by_alias=None):
        """List pending channels
        tg> pending [filter]
        Specify a filter to select pending channels by aliases and pubkeys"""
        chs = self._command('pendingchannels')['pending_open_channels']
        messages = []
        for ch in chs:
            rows = []
            pubkey = ch['channel']['remote_node_pub']
            alias = self._alias(pubkey)
            if not filter_by_alias or filter_by_alias in alias or filter_by_alias in pubkey:
                rows.append('%s \u23f3' % (alias, ))
                rows.append(to_btc_str(ch['channel']['capacity']))
                local = to_btc_str(ch['channel']['local_balance'])
                remote = to_btc_str(ch['channel']['remote_balance'])
                rows.append('L: %s R: %s' % (local, remote))
                rows.append(TX_LINK % (ch['channel']['channel_point'].split(':')[0]))
                messages.append('\n'.join(rows))
        return messages

    def feereport(self):
        out = self._command('feereport')
        return 'Fees\nday: %s, week: %s, month: %s' % (
            out['day_fee_sum'], out['week_fee_sum'], out['month_fee_sum'])

    def is_pay_req(self, pay_req):
        if pay_req.lower().startswith('lightning:'):
            pay_req = pay_req[10:]
        try:
            self._command('decodepayreq', pay_req)
        except NodeException:
            return False
        else:
            return True

    def n_1ml(self):
        """Toggle https://1ml.com block explorer links
        tg> 1ml"""
        self._1ml = not self._1ml
        return '1ml toggled'

    def lightblock(self):
        """Toggle https://lightblock.me block explorer links
        tg> lightblock"""
        self._lightblock = not self._lightblock
        return 'lightblock toggled'

    def decode(self, pay_req):
        """Decode a payment request
        tg> decode <payment request>"""
        if not self.is_pay_req(pay_req):
            return 'This is not a payment request'
        decoded = self._command('decodepayreq', pay_req)
        pubkey = decoded['destination']
        rows = []
        alias = self._alias(pubkey, '-')
        if alias != '-':
            rows.append('To {}'.format(alias))
        rows.append('Pubkey {}'.format(pubkey))
        amount = int(decoded['num_satoshis'])
        if amount:
            if amount > .0001 * 1e8:
                amount_str = 'Amount {} btc'.format(to_btc_str(amount))
            else:
                amount_str = 'Amount {} sat'.format(amount)
            rows.append(amount_str)
        if decoded['description']:
            rows.append('Description {}'.format(decoded['description']))

        creation = time.ctime(int(decoded['timestamp']))
        rows.append('Created on {}'.format(creation))
        expiration = time.ctime(int(decoded['timestamp']) + int(decoded['expiry']))
        expired = self.__is_expired(int(decoded['timestamp']) + int(decoded['expiry']))
        exp_format = 'Expired on {}' if expired else 'Expires {}'
        rows.append(exp_format.format(expiration))

        return '\n'.join(rows)
