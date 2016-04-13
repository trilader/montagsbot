#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import config
import telepot
import time
import smtplib
from email.mime.text import MIMEText


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
            print("Group message from {} ({}): {}".format(user,uid,text))
            send_mail(user,text)
        elif chat_type == "private":
            print("Private message from {} ({}): {}".format(user,uid,text))


if __name__ == "__main__":
    bot = telepot.Bot(config.BOT_TOKEN)
    bot.notifyOnMessage(handle_bot_message)
    print("Starting montagsbot")
    print(bot.getMe())
    print("Waiting for messages...")
    
    while True:
        time.sleep(10)
