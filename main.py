#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-

import config
import telepot
import time
import smtplib
from email.mime.text import MIMEText


def send_mail(from, msg):
    msgs = []
    for email in config.EMAILS:
        msg = MIMEText(msg)
        msg["Subject"] = "Telegram Message"
        msg["From"] = "Montagsbot"
        msg["To"] = email
        msgs.add(msg)
    s = smtplib.SMTP("localhost")
    for msg in msgs:
        s.send_message(msg)
    s.quit()


def handle_bot_message(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    if content_type == "text":
        text=msg["text"]
        user=msg["from"]["first_name"]
        if chat_type == "group":
            print("Group message from {}: {}".format(user,text))
            send_msg(user,text)
        elif chat_type == "private":
            print("Private message from {}: {}".format(user,text))


if __name__ == "__main__":
    bot = telepot.Bot(config.BOT_TOKEN)
    bot.notifyOnMessage(handle_bot_message)
    print("Starting montagsbot")
    print(bot.getMe())
    print("Waiting for messages...")
    
    while True:
        time.sleep(10)
