#!/usr/bin/env python3
import time
import tempfile
import os
import re
import telepot
from telepot.loop import MessageLoop
from config import *
from lnd import Lncli, NodeException
from qr import decode, encode

AUTH_COMMANDS = {
    'pay', 'balance', 'ping', 'echo', 'unicode',
}
NO_AUTH_COMMANDS = {
    'info', 'help', 'channels', 'chs', 'pending', 'add', 'uri',
}
ALLOWED_COMMANDS = AUTH_COMMANDS | NO_AUTH_COMMANDS
_24H = 60 * 60 * 24
TX_LINK = 'https://www.smartbit.com.au/tx/%s'
CH_LINK = 'https://1ml.com/channel/%s'

bot = None
ln = Lncli()


def text(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    tokens = msg['text'].lstrip('/').split()
    cmd = tokens[0].lower()
    if cmd not in ALLOWED_COMMANDS:
        return

    if hasattr(ln, cmd):
        try:
            out = getattr(ln, cmd)(*tokens[1:])
            if cmd == 'add' and is_pay_req(out, True) or cmd == 'uri':
                send_qr(chat_id, out)
            else:
                if not isinstance(out, list):
                    out = [out]
                for ou in out:
                    bot.sendMessage(chat_id, ou)
        except NodeException as exception:
            bot.sendMessage(chat_id, '\u274c ' + str(exception))
    elif cmd == 'help':
        bot.sendMessage(chat_id, ' '.join(ALLOWED_COMMANDS))
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
    ln.update_aliases()


def photo(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    _, file = tempfile.mkstemp(prefix='unsafepay')
    bot.download_file(msg['photo'][-1]['file_id'], file)
    data = decode(file)
    if data:
        if is_pay_req(data):
            try:
                bot.sendMessage(chat_id, ln.pay(data))
            except NodeException as exception:
                bot.sendMessage(chat_id, '\u274c ' + str(exception))
        else:
            bot.sendMessage(chat_id, 'Richiesta di pagamento non valida')
    else:
        bot.sendMessage(chat_id, 'Non sembra un qrcode')
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
    username = msg['chat']['username']
    for allowed in ALLOWED_IDS:
        if chat_id == allowed[0] and username == allowed[1]:
            return True
    return False


def send_alloewd_ids_config(msg):
    chat_id = msg['chat']['id']
    username = msg['chat']['username']
    bot.sendMessage(chat_id, "ALLOWED_IDS = [(%d, '%s')]" % (chat_id, username))


def on_chat_message(msg):
    """ handle chat """
    if not is_authorized(msg):
        send_alloewd_ids_config(msg)
        return

    if 'text' in msg:
        text(msg)
    elif 'photo' in msg:
        photo(msg)


def is_pay_req(pay_req, weak=False):

    if re.match('(lightning:)?ln(bc|tb)\d+[munp]', pay_req):
        return weak or ln.is_pay_req(pay_req)
    return False


def start():
    global bot

    bot = telepot.Bot(UNSAFEPAY_TELEGRAM)
    # answerer = telepot.helper.Answerer(bot)

    MessageLoop(bot, {'chat': on_chat_message}).run_as_thread()
    print('Listening ...')

    # Keep the program running.
    while 1:
        time.sleep(10)

start()
