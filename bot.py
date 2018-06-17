#!/usr/bin/env python3
import time
import tempfile
import os
import re
import telepot
from telepot.loop import MessageLoop
from config import UNSAFEPAY_TELEGRAM
from lnd import Lncli, NodeException
from qr import decode, encode

ALLOWED_ID = (16133199, 'martinoz')
ALLOWED_COMMANDS = {
    'pay', 'info', 'help',
    'add', 'balance', 'ping',
    'echo', 'channels', 'unicode',
}
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
            if cmd == 'add' and is_pay_req(out, True):
                send_qr(chat_id, out)
            else:
                bot.sendMessage(chat_id, out)
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


def on_chat_message(msg):
    """ handle chat """
    if msg['chat']['id'] != ALLOWED_ID[0]:
        return
    if msg['chat']['username'] != ALLOWED_ID[1]:
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
