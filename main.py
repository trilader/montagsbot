#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import config
import telepot
import time
import smtplib
import threading
import sys
import email
from email.mime.text import MIMEText
from xmlrpc.server import SimpleXMLRPCServer

lock = threading.Lock()
msgs=0

def sprint(*args, **kwargs):
    with lock:
        print(*args, **kwargs)

def get_alias(sender):
    the_alias=sender["first_name"]

    if int(sender["id"]) in config.ALIASES:
        the_alias = config.ALIASES[int(sender["id"])]
    elif "nickname" in sender:
        the_alias = sender["nickname"]

    return the_alias


def send_mail(msg):
    the_sender = get_alias(msg["from"])
    msgs = []
    for email in config.EMAILS:
        mail = MIMEText("{} sagt: {}".format(the_sender,msg["text"]))
        mail["Subject"] = "Telegram Message from {}".format(the_sender)
        mail["From"] = "Montagsbot <no-reply@steckdo.se>"
        mail["To"] = email
        mail["X-Telegram-Bot"] = "Montagsbot"
        mail["X-Telegram-Original-User"] = msg["from"]["id"]
        msgs.append(mail)
    s = smtplib.SMTP("localhost")
    for msg in msgs:
        s.send_message(msg)
    s.quit()


def handle_bot_message(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    if content_type == "text":
        text=msg["text"]
        user=msg["from"]
        sprint(msg)
        uid=msg["from"]["id"]
        if chat_type == "group":
            sprint("Group message from {} ({}): {}".format(user,uid,text))
            #send_mail(msg)
        elif chat_type == "private":
            sprint("Private message from {} ({}): {}".format(user,uid,text))

def handle_reply_mail(mail):
    global msgs
    xmsgs+=1
    sprint("You've got Mail!",msgs,"so far")
    the_mail=email.message_from_string(mail)
    the_payload=the_mail.get_payload()
    if type(the_payload) is str:
        the_sender=the_mail["from"]
        sender_parts=the_sender.split(" ")
        if len(sender_parts)!=2:
            sender_parts=sender_parts[0].split("@")
            the_sender=sender_parts[0].strip("<")
        else:
            the_sender=sender_parts[0]
        #sprint("Mail from:", the_sender)
        #sprint("Mail text:", the_payload)
        the_msg="{} sagt: {}".format(the_sender,the_payload)
        bot.sendMessage(config.GROUP_ID,the_msg)
    else:
        sprint("Unsupported payload type", type(the_payload))
        if hasattr(the_payload,'__str__'):
            sprint("the_payload.__str__():",the_payload)
    return True


def xmlrpc_worker():
    server.serve_forever()


if __name__ == "__main__":

    server = SimpleXMLRPCServer(("localhost", 4711),logRequests=False)
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
