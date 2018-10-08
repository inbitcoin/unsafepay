#!/usr/bin/env python3
"""
telegram bot
"""
import subprocess
import json
from decimal import Decimal
import time
import git

_24H = 60 * 60 * 24
TX_LINK = 'https://www.smartbit.com.au/tx/%s'
CH_LINK = 'https://1ml.com/channel/%s'
ND_LINK = 'https://1ml.com/node/%s'


def to_btc_str(sats):
    return '{:.8f}'.format(Decimal(sats) / Decimal(1e8))


def to_sat_str(msats):
    return '{:.3f}'.format(Decimal(msats) / Decimal(1e3))


def amt_to_sat(amt):
    """Get sat or btc amt"""
    if '.' in amt:
        return int(Decimal(amt) * Decimal(1e8))
    return int(amt)


class NodeException(Exception):
    pass


class Lncli:
    """Interface to lncli command"""
    CMD = 'lncli'

    def __init__(self):
        self.aliases = {}
        self._updated = 0
        self.update_aliases()

    @staticmethod
    def _command(*cmd):
        print([Lncli.CMD] + list(cmd))
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
        graph = self._command('describegraph')
        aliases = {}
        for node in graph['nodes']:
            aliases[node['pub_key']] = node['alias']
        self.aliases = aliases
        self._updated = time.time()

    def info(self):
        obj = self._command('getinfo')
        n_chs = len(self._command('listchannels')['channels'])
        rows = [obj['alias'],
                ND_LINK % obj['identity_pubkey'],
                'Active channels: %s' % obj['num_active_channels'],
                'Channels: %d' % n_chs,
                ]
        if obj['num_pending_channels']:
            rows.append('Pending channels: %s' % obj['num_pending_channels'])
        rows.append('Num peers: %s' % obj['num_peers'])
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
        return self._command('getinfo')['uris'][0]

    def pay(self, pay_req, amt=None):
        """lncli payinvoice [command options] pay_req"""
        cmd = ['payinvoice']
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
        """lncli addinvoice value"""
        cmd = ['addinvoice']
        if amt:
            cmd.append('%d' % amt_to_sat(amt))
        out = self._command(*cmd)
        if 'pay_req' in out:
            return out['pay_req']
        else:
            return out

    def balance(self):
        """lncli walletbalance and channelbalance"""
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

    def channels(self, pending=True):
        """lncli listchannels"""
        chs = self._command('listchannels')['channels']
        messages = []
        for ch in chs:
            rows = []
            pubkey = ch['remote_pubkey']
            active = '\u26a1\ufe0f' if ch['active'] else '\U0001f64a'
            rows.append('%s %s' % (self.aliases.get(pubkey, pubkey), active))
            if ch['chan_id'] != '0':
                rows.append(CH_LINK % ch['chan_id'])
            rows.append(to_btc_str(ch['capacity']))
            local = to_btc_str(ch['local_balance'])
            remote = to_btc_str(ch['remote_balance'])
            rows.append('L: %s R: %s' % (local, remote))
            rows.append(TX_LINK % (ch['channel_point'].split(':')[0]))
            messages.append('\n'.join(rows))
        if pending:
            messages += self.pending()
        return messages

    def chs(self):
        chs = self._command('listchannels')['channels']
        rows = []
        for ch in chs:
            pubkey = ch['remote_pubkey']
            active = '\u26a1\ufe0f' if ch['active'] else '\U0001f64a'
            capacity = to_btc_str(ch['capacity']).rstrip('0').rstrip('.')
            rows.append('%s %s %s' % (self.aliases.get(pubkey, pubkey[:8]), capacity, active))
        return '\n'.join(rows)

    def pending(self):
        chs = self._command('pendingchannels')['pending_open_channels']
        messages = []
        for ch in chs:
            rows = []
            pubkey = ch['channel']['remote_node_pub']
            rows.append('%s \u23f3' % (self.aliases.get(pubkey, pubkey), ))
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
