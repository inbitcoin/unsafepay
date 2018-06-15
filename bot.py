#!/usr/bin/env python3
import time
import telepot
from telepot.loop import MessageLoop
from telegram_token import UNSAFEPAY_TELEGRAM
from lnd import Lncli, NodeException

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


def on_chat_message__example(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    print('Chat:', content_type, chat_type, chat_id)
    bot.sendMessage(chat_id, msg['text'])


def text(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    tokens = msg['text'].lstrip('/').split()
    cmd = tokens[0].lower()
    if cmd not in ALLOWED_COMMANDS:
        return

    if hasattr(ln, cmd):
        try:
            bot.sendMessage(chat_id, getattr(ln, cmd)(*tokens[1:]))
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
    file = bot.download_file(msg['photo'][0]['file_id'], '/tmp/bot')
    print(file)


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
