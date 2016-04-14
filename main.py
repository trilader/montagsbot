#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import config
import telepot
import time
import smtplib
import threading
import sys
from email.mime.text import MIMEText
from xmlrpc.server import SimpleXMLRPCServer

lock = threading.Lock()


def sprint(*args, **kwargs):
    with lock:
        print(*args, **kwargs)


def send_mail(sender, msg):
    if sender in config.ALIASES:
        the_sender = config.ALIASES[sender]
    else:
        the_sender = sender
    msgs = []
    for email in config.EMAILS:
        mail = MIMEText("{} sagt: {}".format(the_sender,msg))
        mail["Subject"] = "Telegram Message from {}".format(the_sender)
        mail["From"] = "Montagsbot <no-reply@steckdo.se>"
        mail["To"] = email
        mail["X-Telegram-Bot"] = "Montagsbot"
        mail["X-Telegram-Original-User"] = sender
        msgs.append(mail)
    s = smtplib.SMTP("localhost")
    for msg in msgs:
        s.send_message(msg)
    s.quit()


def handle_bot_message(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    if content_type == "text":
        text=msg["text"]
        user=msg["from"]["first_name"]
        uid=msg["from"]["id"]
        if chat_type == "group":
            sprint("Group message from {} ({}): {}".format(user,uid,text))
            send_mail(user,text)
        elif chat_type == "private":
            sprint("Private message from {} ({}): {}".format(user,uid,text))

def handle_reply_mail(mail):
    sprint("You've got Mail!",mail)


def xmlrpc_worker():
    server.serve_forever()


if __name__ == "__main__":

    server = SimpleXMLRPCServer(("localhost", 4711))
    server.register_function(handle_reply_mail)

    bot = telepot.Bot(config.BOT_TOKEN)
    bot.notifyOnMessage(handle_bot_message)
    sprint("Starting montagsbot")
    # print(bot.getMe())

    sprint("Starting email worker thread")
    worker = threading.Thread(target=xmlrpc_worker)
    worker.start()

    sprint("Waiting for messages...")

    
    while True:
        try:
            time.sleep(10)
        except KeyboardInterrupt as ex:
            sprint("Shutting down...")
            server.shutdown()
            worker.join()
            sys.exit(0)
