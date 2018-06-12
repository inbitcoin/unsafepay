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
import time
import tempfile
import os
import os.path
import re
from random import randint
import telepot
from telepot.loop import MessageLoop
from lnd import NodeException
from commands import Commands, RpcError
from fiat_rate import RateError
from qr import decode, encode
import config_manager

OVERT_COMMANDS = (
    'pay', 'balance', '1ml', 'lightblock', 'payment',
    'info', 'channels', 'chs', 'add', 'uri',
    'address', 'decode',
)
COVERT_COMMANDS = (
    'ping', 'echo', 'unicode', 'help',
)
ALLOWED_COMMANDS = set(OVERT_COMMANDS + COVERT_COMMANDS)
_24H = 60 * 60 * 24

bot = None
commands = None

authorized = None
challenge = None, None  # chat_id, challenge


def format_doc(doc):
    """Foramt the __doc__ str of Lncli class methods"""
    return '\n'.join([x.strip() for x in doc.splitlines()])


def lower_first(string):
    """Lower only the first char of a string"""
    return string[0].lower() + string[1:]


def escape_cmd(cmd):
    """Python attrs cannot start with digits, if needed we escape them with n_"""
    if '0' <= cmd[0] <= '9':
        return 'n_' + cmd
    return cmd


def text(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    tokens = msg['text'].lstrip('/').split()
    cmd = tokens[0].lower()
    if cmd not in ALLOWED_COMMANDS:
        return

    if hasattr(commands, escape_cmd(cmd)):
        try:
            out = getattr(commands, escape_cmd(cmd))(*tokens[1:])
            if cmd == 'add' and is_pay_req(out[0], True):
                send_qr(chat_id, out[0])
                bot.sendMessage(chat_id, 'payment %s' % out[1])
            elif cmd in ('uri', 'address'):
                send_qr(chat_id, out)
            else:
                if not isinstance(out, list):
                    out = [out]
                for ou in out:
                    if ou:
                        bot.sendMessage(chat_id, ou)
        except RpcError as exception:
            bot.sendMessage(chat_id, '\u274c ' + str(exception))
        except RateError:
            bot.sendMessage(chat_id, '\u274c Exchange rate is not available')
    elif cmd == 'help':
        if tokens[1:] and hasattr(commands, escape_cmd(tokens[1])):
            # Return doc of the command
            cmd_doc = format_doc(getattr(commands, escape_cmd(tokens[1])).__doc__ or 'No doc, yet')
            bot.sendMessage(chat_id, cmd_doc)
        else:
            if tokens[1:] and escape_cmd(tokens[1]) == 'help':
                cmd_doc = '''General help or specific help for commands
                tg> help [cmd]
                Specify a command to get a specific help'''
                bot.sendMessage(chat_id, format_doc(cmd_doc))
            else:
                help_msg = [
                    'Commands:',
                ]
                for cmd in OVERT_COMMANDS:
                    if hasattr(commands, escape_cmd(cmd)):
                        doc = getattr(commands, escape_cmd(cmd)).__doc__
                        if doc:
                            short_help = lower_first(doc.split('\n', 1)[0])
                            help_msg.append('{}: {}'.format(cmd, short_help))
                        else:
                            help_msg.append(cmd)
                    else:
                        print('The cmd {} is not implemented by Commands'.format(cmd))
                help_msg.append('{}: {}'.format('help', 'this help and help for commands'))

                SYMBOLS = [
                    ('\u26a1\ufe0f', 'active'),
                    ('\U0001f64a', 'not active'),
                    ('\U0001f512', 'private'),
                    ('\u23f3', 'pending'),
                ]

                help_msg.append('')
                help_msg.append('Symbols:')

                for sym, desc in SYMBOLS:
                    help_msg.append('{}: {}'.format(sym, desc))

                bot.sendMessage(chat_id, '\n'.join(help_msg))
    elif cmd == 'ping':
        bot.sendMessage(chat_id, 'pong')
    elif cmd == 'echo':
        bot.sendMessage(chat_id, ' '.join(tokens[1:]))
    elif cmd == 'unicode':
        encoded = ' '.join(tokens[1:]).encode(
            'unicode-escape').decode('ascii')
        bot.sendMessage(chat_id, encoded)
    else:
        bot.sendMessage(chat_id, 'Not implemented, sorry')
    # ln.update_aliases()


def photo(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    _, file = tempfile.mkstemp(prefix='unsafepay')
    bot.download_file(msg['photo'][-1]['file_id'], file)
    data = decode(file)
    if data:
        if is_pay_req(data):
            try:
                bot.sendMessage(chat_id, commands.pay(data))
            except NodeException as exception:
                bot.sendMessage(chat_id, '\u274c ' + str(exception))
        else:
            bot.sendMessage(chat_id, 'The payment request is not valid')
    else:
        bot.sendMessage(chat_id, 'The qr code is not readable')
    os.remove(file)


def send_qr(chat_id, data):
    _, file = tempfile.mkstemp(prefix='unsafepay')
    with open(file, 'wb') as fd:
        encode(data, fd)
    with open(file, 'rb') as fd:
        bot.sendPhoto(chat_id, fd, data)
    os.remove(file)


def is_authorized(msg):
    chat_id = msg['chat']['id']
    return authorized == chat_id


def is_paired():
    return authorized is not None


def send_challenge(msg):
    global challenge
    chat_id = msg['chat']['id']
    challenge = chat_id, randint(1, 99999)
    bot.sendMessage(chat_id, str(challenge[1]))


def on_chat_message(msg):
    """ handle chat """
    bot.sendMessage(msg['chat']['id'], '\U0001f916')
    if not is_authorized(msg):
        if not is_paired():
            send_challenge(msg)
        return

    if 'text' in msg:
        text(msg)
    elif 'photo' in msg:
        photo(msg)


def is_pay_req(pay_req, weak=False):

    if re.match('(lightning:)?ln(bc|tb)\d+[munp]', pay_req):
        return weak or commands.is_pay_req(pay_req)
    return False


def start():
    global bot
    global commands
    global authorized

    config = config_manager.load()

    token = config.get('telegram', 'token', fallback=None)
    authorized = config.getint('telegram', 'user', fallback=None)

    host = config.get('lighter', 'host', fallback=None)
    port = config.get('lighter', 'port', fallback=None)
    cert_path = config.get('lighter', 'cert', fallback=None)
    macaroon_path = config.get('lighter', 'macaroon', fallback=None)

    commands = Commands(host, port, cert_path, macaroon_path)

    while not token:
        print('Talk with the BotFather on Telegram '
              '(https://telegram.me/BotFather), '
              'create a bot and insert the token')
        token = input('> ')
        config['telegram']['token'] = token
        config_manager.save(config)

    bot = telepot.Bot(token)
    # answerer = telepot.helper.Answerer(bot)

    MessageLoop(bot, {'chat': on_chat_message}).run_as_thread()
    print('Listening ...')

    while not authorized:
        print('Please add your bot on Telegram, '
              'than copy here the numeric code')
        try:
            code = int(input('> '))
        except ValueError:
            continue
        if int(code) == challenge[1]:
            # User paired
            msg = [
                '\U0001f308 Congratulations \U0001f308',
                'Your bot is now ready for use \u26a1\ufe0f'
            ]
            print('Congratulations')
            authorized = challenge[0]  # chat_id
            config['telegram']['user'] = str(authorized)
            config_manager.save(config)
            bot.sendMessage(authorized, '\n'.join(msg))

    # Keep the program running.
    while 1:
        time.sleep(10)


start()
