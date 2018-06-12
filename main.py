#!/usr/bin/env python3
"""
telegram bot
"""
import subprocess
import json
from decimal import Decimal
import telepot
from telepot.delegate import per_chat_id, create_open
from telegram_token import UNSAFEPAY_TELEGRAM

ALLOWED_ID = (16133199, 'martinoz')
ALLOWED_COMMANDS = {'pay', 'info', 'help', 'ping', 'echo', 'add', 'balance'}


def to_btc_str(sats):
    return '{:.8f}'.format(Decimal(sats) / Decimal(1e8))


def amt_to_sat(amt):
    """Get sat or btc amt"""
    if '.' in amt:
        return int(Decimal(amt) * Decimal(1e8))
    return int(amt)


class Lncli:
    """Interface to lncli command"""
    CMD = 'lncli'

    def _command(self, *cmd):
        print([Lncli.CMD] + list(cmd))
        process = subprocess.Popen([Lncli.CMD] + list(cmd), stdout=subprocess.PIPE)
        out, err = process.communicate()
        if process.returncode == 0:
            return json.loads(str(out, 'utf-8'))
        print(out)
        print(err)

    def info(self):
        obj = self._command('getinfo')
        rows = [obj['alias'],
                'Active channels: %s' % obj['num_active_channels'],
                'Num peers: %s' % obj['num_peers'],
                '%s' % obj['uris'][0],
                ]
        if not obj['synced_to_chain']:
            rows.append('Not synced')
        return '\n'.join(rows)

    def pay(self, pay_req, amt=None):
        """lncli payinvoice [command options] pay_req"""
        cmd = ['payinvoice']
        if amt:
            cmd.append('--amt')
            cmd.append('%d' % amt)
        cmd.append(pay_req)
        return self._command(*cmd)

    def add(self, amt=None):
        """lncli addinvoice value"""
        cmd = ['addinvoice']
        if amt:
            cmd.append('%d' % amt)
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
            rows.append('%s: %s' % (key.replace('_', ' '), to_btc_str(wallet[key])))
        rows.append('Channel')
        for key in channel:
            rows.append('%s: %s' % (key.replace('_', ' '), to_btc_str(channel[key])))
        return '\n'.join(rows)

lncli = Lncli()


class TelegramBot(telepot.helper.ChatHandler):
    """ super class for bot """
    def __init__(self, seed_tuple, timeout):
        """ init bot """
        super(TelegramBot, self).__init__(seed_tuple, timeout)
        print('__init__', seed_tuple, timeout)
        # self._id = seed_tuple[1]['from']['id']
        # self._name = seed_tuple[1]['from']['username']

    def on_chat_message(self, msg):
        """ handle chat """
        if msg['chat']['id'] != ALLOWED_ID[0]:
            return
        if msg['chat']['username'] != ALLOWED_ID[1]:
            return

        if 'text' not in msg:
            return
        tokens = msg['text'].split()
        cmd = tokens[0].lower()
        if cmd not in ALLOWED_COMMANDS:
            return

        if cmd == 'help':
            self.sender.sendMessage(' '.join(ALLOWED_COMMANDS))
        elif cmd == 'ping':
            self.sender.sendMessage('pong')
        elif cmd == 'echo':
            self.sender.sendMessage(' '.join(tokens[1:]))
        elif cmd == 'pay':
            if tokens[1:]:
                amt = amt_to_sat(tokens[2]) if tokens[2:] else None
                self.sender.sendMessage(lncli.pay(tokens[1], amt))
        elif cmd == 'info':
            info = lncli.info()
            balance = lncli.balance()
            self.sender.sendMessage('\n'.join([info, balance]))
        elif cmd == 'add':
            amt = amt_to_sat(tokens[1]) if tokens[1:] else None
            self.sender.sendMessage(lncli.add(amt))
        elif cmd == 'balance':
            self.sender.sendMessage(lncli.balance())


bot = telepot.DelegatorBot(UNSAFEPAY_TELEGRAM, [
    (per_chat_id(), create_open(TelegramBot, timeout=60)),
])
bot.message_loop(run_forever=True)
