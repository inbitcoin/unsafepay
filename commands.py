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
from decimal import Decimal
import time
import git
import hashlib
import threading
import binascii
from fiat_rate import Fiat, RateError
from cities import read_cities
import lighterer  # module import is required by Lighterer mock
from lighterer import RpcError

_24H = 60 * 60 * 24
TX_LINK = 'https://www.smartbit.com.au/tx/%s'
CH_LINK = 'https://1ml.com/channel/%s'
CH_LINK_ALT = 'https://lightblock.me/lightning-channel/%s'
ND_LINK = 'https://1ml.com/node/%s'
ND_LINK_ALT = 'https://lightblock.me/lightning-node/%s'


def to_btc_str(sats):
    return '{:.8f}'.format(Decimal(sats) / Decimal(1e8))


def to_sat_str(msats):
    return '{:.3f}'.format(Decimal(msats) / Decimal(1e3))


def amt_to_sat(amt, fiat):
    """Get sat"""
    symbol = fiat.SYMBOLS & set(amt)
    if symbol:
        eur = float(amt.replace(symbol.pop(), ''))
        return fiat.to_satoshis(eur)
    if '.' in amt:
        return int(Decimal(amt) * Decimal(1e8))
    return int(amt)


def amt_to_bits(amt, fiat):
    """Get bits amount from btc, satoshis or fiat"""
    symbol = set('€Ee') & set(amt)
    if symbol:
        eur = float(amt.replace(symbol.pop(), ''))
        return fiat.to_bits(eur)
    if '.' in amt:
        return float(Decimal(amt) * Decimal(1e6))
    return int(amt) / 100


def bits_to_sats(bits):
    """Get amount in sats"""
    return int(bits * 100)


class Commands:
    """Execute commands"""

    LOCAL = '\u2b55\ufe0f'
    REMOTE = '\u274c'
    PRIVATE = '\U0001f512'
    ACTIVE = '\u26a1\ufe0f'
    NACTIVE = '\U0001f64a'

    def __init__(self, host, port, cert_path, macaroon_path):
        self._fiat = Fiat()
        try:
            cert = lighterer.Lighterer.read_cert(cert_path)
            macaroon = lighterer.Lighterer.read_macaroon(macaroon_path)
        except FileNotFoundError:
            print('No cert and macaroon: use insecure connection')
            cert = macaroon = None
        self._lit = lighterer.Lighterer(host, port, cert, macaroon)
        self._1ml = True
        self._lightblock = True
        self.aliases = {}
        self._cities = None
        self._update_lock = threading.Lock()
        self._updated = 0
        self.update_aliases()  # Lighter misses this

    def _command(self, *cmd):
        raise NotImplementedError
        # print('$', *self._cmd, *cmd, sep='  ')
        # process = subprocess.Popen(
        #     self._cmd + list(cmd),
        #     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # out, err = process.communicate()
        # if process.returncode == 0:
        #     return json.loads(str(out, 'utf-8'))
        # raise NodeException(str(err, 'utf-8'))

    def update_aliases(self):
        return

        # with self._update_lock:
        #     if time.time() - self._updated < _24H:
        #         return
        #     try:
        #         graph = self._command('describegraph')
        #     except NodeException as e:
        #         print(e)
        #         return
        #     aliases = {}
        #     for node in graph['nodes']:
        #         aliases[node['pub_key']] = node['alias']
        #     self.aliases = aliases
        #     self._updated = time.time()

    def bg_update_aliases(self):
        th = threading.Thread(target=lambda: self.update_aliases())
        th.start()

    def info(self):
        """Get information about the node"""
        info = self._lit.getinfo()
        n_chs = len(self._lit.listchannels())
        n_active_chs = len(self._lit.listchannels(True))
        rows = [info.alias]
        self._1ml and rows.append(ND_LINK % info.identity_pubkey)
        self._lightblock and rows.append(ND_LINK_ALT % info.identity_pubkey)
        if n_active_chs != n_chs:
            rows.append('Active channels: %s' % n_active_chs)
        rows.append('Channels: %d' % n_chs)
        # Not implemented
        # if obj['num_pending_channels']:
        #     rows.append('Pending channels: %s' % obj['num_pending_channels'])
        # FIXME: lighter error: unable to find node
        # FIXME: rows.append('Num peers: %s' % len(self._lit.listpeers()))
        rows.append(self.uri())
        rows.append('Block height: {}'.format(info.blockheight))
        rows.append(self.balance())
        commit = git.get_git_revision_short_hash()
        if commit:
            rows.append('Version: %s' % commit)
        return '\n'.join(rows)

    def uri(self):
        """Get the node uri
        FiXME: no network address
        tg> uri"""
        info = self._lit.getinfo()
        return info.node_uri

    def pay(self, pay_req, amt=None):
        """Pay an invoice
        tg> pay <payment request> [amt]
        If amt is a float it is considered a bitcoin amount, if amt is
        an integer it is considered a satoshi amount"""
        if pay_req.lower().startswith('lightning:'):
            pay_req = pay_req[10:]
        amt_bits = None
        if amt:
            amt_bits = amt_to_bits(amt, self._fiat)
        preimage = self._lit.payinvoice(pay_req, amt and amt_bits)
        rows = ['Done: {}'.format(preimage)]
        # # TODO: error checking
        # if out['payment_error']:
        #     rows.append('Error: %s' % out['payment_error'])
        # else:
        #     route = out['payment_route']
        #     rows.append('Amount: %s btc' % to_btc_str(route['total_amt']))
        #     rows.append('Fee: %s sat' % to_sat_str(
        #         route['total_fees_msat']
        #         if 'total_fees_msat' in route else 0))
        #
        #     nodes = []
        #     for hop in route['hops']:
        #         if 'pub_key' in hop:
        #             nodes.append(self._alias(hop['pub_key']))
        #     if nodes:
        #         rows.append('Path:')
        #         rows.extend(nodes)
        #     else:
        #         rows.append('# hops: %d' % len(route['hops']))

        return '\n'.join(rows)

    def add(self, amt=None):
        """Add invoice
        tg> add [amt]
        If amt is a float it is considered a bitcoin amount, if amt is
        an integer it is considered a satoshi amount"""
        amt_bits = None
        if amt:
            amt_bits = amt_to_bits(amt, self._fiat)
        invoice = self._lit.createinvoice(amt and amt_bits, expiry_time=43200)
        return invoice.payment_request, invoice.payment_hash

    @staticmethod
    def __is_expired(expiration: int):
        return time.time() > expiration

    def payment(self, payment_hash=None):
        """Check a payment status
        tg> payment [payment_hash]
        If payment_hash is not provided the last payment will be checked
        """
        PAID = '\U0001f44d'
        NOT_PAID = '\U0001f44e'
        NOT_FOUND = 'Invoice not found'
        if payment_hash and len(payment_hash) == 64 and \
                re.match(r'^[\da-f]{64}$', payment_hash):
            try:
                settled = self._lit.checkinvoice(payment_hash)
            except RpcError:
                # FIXME: check the type of the error and manage only
                # "Invoice not found"
                return NOT_FOUND
        else:
            # self, max_items=200, search_timestamp=None,
            # search_order='ASCENDING', list_order='ASCENDING', paid=False,
            # pending=False, expired=False):
            invoices = self._lit.listinvoices(1)
            if not invoices:
                return NOT_FOUND
            invoice = invoices[0]
            settled = invoice.state == 0  # InvoiceState.PAID
            payment_hash = invoice.payment_hash

        rows = [PAID if settled else NOT_PAID, payment_hash]
        return '\n'.join(rows)

        # Extended command: give other information on the invoice
        # rows = []
        # paid = PAID if invoice.settled else NOT_PAID
        # rows.append('{} {}'.format(to_btc_str(invoice['value']), paid))
        # if not payment_hash:
        #     r_hex = base64.decodebytes(
        #         bytes(invoice['r_hash'], 'ascii')).hex()
        #     rows.append(r_hex)
        #
        # creation = time.ctime(int(invoice['creation_date']))
        # rows.append('Created on {}'.format(creation))
        #
        # if invoice['settled']:
        #     settled = time.ctime(int(invoice['settle_date']))
        #     rows.append('Settled on {}'.format(settled))
        # else:
        #     expiration = time.ctime(
        #         int(invoice['creation_date']) + int(invoice['expiry']))
        #     expired = self.__is_expired(
        #         int(invoice['creation_date']) + int(invoice['expiry']))
        #     exp_format = 'Expired on {}' if expired else 'Expires {}'
        #     rows.append(exp_format.format(expiration))
        #
        # return '\n'.join(rows)

    def balance(self):
        """Walletbalance and channelbalance
        tg> balance"""
        wallet = bits_to_sats(self._lit.walletbalance())
        rows = []
        show_fiat = True
        if float(wallet):
            rows.append('On-chain total balance: %s' % to_btc_str(wallet))
            eur_str, show_fiat = self._to_eur_str(wallet, show_fiat, ' [%s]')
            rows[-1] += eur_str

        channel = bits_to_sats(self._lit.channelbalance())
        if float(channel):
            rows.append('Channel balance: %s' % to_btc_str(channel))
            eur_str, show_fiat = self._to_eur_str(channel, show_fiat, ' [%s]')
            rows[-1] += eur_str
        return '\n'.join(rows)

    def address(self):
        """Generate a new bech32 bitcoin address
        tg> address"""
        return self._lit.newaddress('P2WKH')

    def _alias(self, pubkey, default=None):
        """Return a not null alias or the pubkey"""
        self.bg_update_aliases()
        return self.aliases.get(pubkey) or default or self._city_alias(pubkey)

    def _city_alias(self, pubkey):
        CITYSCAPE = '\U0001f3d9'
        CITY_DUSK = '\U0001f306'
        if self._cities is None:
            self._cities = read_cities()
        city = self._cities[self._int_hash_pubkey(pubkey) % len(self._cities)]
        emoji = CITY_DUSK if self.aliases else CITYSCAPE
        return emoji + ' ' + city

    @staticmethod
    def _int_hash_pubkey(pubkey):
        hash = hashlib.sha256(binascii.unhexlify(pubkey)).digest()
        return int.from_bytes(hash, byteorder='big', signed=False)

    def _to_eur_str(self, sats, show_fiat=True, template='%s'):
        """return eur_str, show_fiat"""
        eur = ''
        if show_fiat:
            if sats:
                try:
                    if self._fiat.to_fiat(sats):
                        eur = template % self._fiat.to_fiat_str(sats)
                except RateError:
                    show_fiat = False
        return eur, show_fiat

    def channels(self, filter_by_alias=None, pending=False):
        """List channels
        tg> channles [filter]
        Specify a filter to select channels by aliases and pubkeys"""
        assert not pending, 'Not implemented'
        chs = sorted(self._lit.listchannels(), key=lambda x: x.private)
        active_channels = {ch.channel_id for ch in self._lit.listchannels(True)}
        messages = []
        show_fiat = True
        for ch in chs:
            rows = []
            pubkey = ch.remote_pubkey
            alias = self._alias(pubkey)
            if not filter_by_alias or filter_by_alias in alias + pubkey:
                active = ch.channel_id in active_channels
                rows.append('%s %s%s' % (
                    alias,
                    self.ACTIVE if active else self.NACTIVE,
                    self.PRIVATE if ch.private else ''
                ))
                # FIXME: I don't know the undefined value of ch.chan_id
                if not ch.private and ch.channel_id:
                    self._1ml and rows.append(CH_LINK % ch.channel_id)
                    self._lightblock and rows.append(
                        CH_LINK_ALT % ch.channel_id)
                rows.append(to_btc_str(bits_to_sats(ch.capacity)))
                local = bits_to_sats(ch.local_balance)
                remote = bits_to_sats(ch.remote_balance)
                local_str = to_btc_str(local)
                remote_str = to_btc_str(remote)
                local_eur, show_fiat = self._to_eur_str(
                    local, show_fiat, self.LOCAL + ' %s')
                remote_eur, show_fiat = self._to_eur_str(
                    remote, show_fiat, self.REMOTE + ' %s')
                rows.append('%s %s %s %s' % (
                    self.LOCAL, local_str, self.REMOTE, remote_str))
                rows.append(local_eur + remote_eur)
                rows.append(TX_LINK % ch.funding_txid[:64])
                # [:64] -> Workaround: lighter bug
                messages.append('\n'.join(rows))
        return messages

    def chs(self):
        """Short version of channels
        tg> chs"""
        chs = sorted(self._lit.listchannels(), key=lambda x: x.private)
        active_channels = {ch.channel_id for ch in self._lit.listchannels(True)}
        rows = []
        show_fiat = True
        for ch in chs:
            pubkey = ch.remote_pubkey
            local = bits_to_sats(ch.local_balance)
            remote = bits_to_sats(ch.remote_balance)
            active = ch.channel_id in active_channels
            local_str = '%s %s' % (self.LOCAL, to_btc_str(
                local).rstrip('0').rstrip('.') if local else '')
            remote_str = '%s %s' % (self.REMOTE, to_btc_str(
                remote).rstrip('0').rstrip('.') if remote else '')
            local_eur, show_fiat = self._to_eur_str(local, show_fiat, ' [%s]')
            remote_eur, show_fiat = self._to_eur_str(remote, show_fiat, ' [%s]')
            rows.append('%s%s %s' % (
                self.ACTIVE if active else self.NACTIVE,
                self.PRIVATE if ch.private else '',
                self._alias(pubkey)
            ))
            local and rows.append('%s%s' % (local_str, local_eur))
            remote and rows.append('%s%s' % (remote_str, remote_eur))

        return '\n'.join(rows)

    def pending(self):
        """List pending channels
        tg> pending [filter]
        Specify a filter to select pending channels by aliases and pubkeys"""
        return []

    def is_pay_req(self, pay_req):
        if pay_req.lower().startswith('lightning:'):
            pay_req = pay_req[10:]
        try:
            self._lit.decodeinvoice(pay_req)
        except RpcError:
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
        decoded = self._lit.decodeinvoice(pay_req)
        pubkey = decoded.destination_pubkey
        rows = []
        alias = self._alias(pubkey, '-')
        if alias != '-':
            rows.append('To {}'.format(alias))
        rows.append('Pubkey {}'.format(pubkey))
        amount = bits_to_sats(decoded.amount_bits)
        if amount:
            if amount > .0001 * 1e8:
                amount_str = 'Amount {} btc'.format(to_btc_str(amount))
            else:
                amount_str = 'Amount {} sat'.format(amount)
            rows.append(amount_str)
        if decoded.description:
            rows.append('Description {}'.format(decoded.description))

        creation = time.ctime(decoded.timestamp)
        rows.append('Created on {}'.format(creation))
        expiration = time.ctime(decoded.timestamp + decoded.expiry_time)
        expired = self.__is_expired(decoded.timestamp + decoded.expiry_time)
        exp_format = 'Expired on {}' if expired else 'Expires {}'
        rows.append(exp_format.format(expiration))

        return '\n'.join(rows)


__all_ = [
    'Commands',
    'RpcError',
]
