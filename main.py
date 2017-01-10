#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import config
import telepot
import time
import smtplib
import threading
import sys
import email
import tempfile
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from xmlrpc.server import SimpleXMLRPCServer

__version__ = "0.1.0"

lock = threading.Lock()
msgs = 0


def sprint(*args, **kwargs):
    with lock:
        print(*args, **kwargs)


def get_alias(sender):
    the_alias = sender["first_name"]

    if int(sender["id"]) in config.ALIASES:
        the_alias = config.ALIASES[int(sender["id"])]
    elif "nickname" in sender:
        the_alias = sender["nickname"]

    return the_alias


def send_mail(msg, telegram=True):
    if telegram:
        the_sender = get_alias(msg["from"])
    else:
        the_sender = msg["from"]
    mails_to_send = []
    for forward_email in config.EMAILS:
        mail = MIMEMultipart()
        if "text" in msg:
            mail.attach(MIMEText("{} sagt: {}".format(the_sender, msg["text"])))
        if "photo" in msg:
            with open(msg["photo"], 'rb') as fp:
                mail.attach(MIMEImage(fp.read()))
        if "audio" in msg:
            with open(msg["audio"], 'rb') as fp:
                mail.attach(MIMEAudio(fp.read()))
        if "voice" in msg:
            with open(msg["voice"], 'rb') as fp:
                mail.attach(MIMEAudio(fp.read()))
        for i in ['document', 'sticker', 'video', 'contact', 'location', 'venue']:
            if i in msg:
                with open(msg[i], 'rb') as fp:
                    mail.attach(MIMEApplication(fp.read()))
        mail["Subject"] = "Telegram Message from {}".format(the_sender)
        mail["From"] = config.BOT_EMAIL_FROM
        mail["To"] = forward_email
        mail["X-Telegram-Bot"] = config.BOT_NAME
        if telegram:
            mail["X-Telegram-Original-User"] = str(msg["from"]["id"])
        mails_to_send.append(mail)
    s = smtplib.SMTP("localhost")
    for mail in mails_to_send:
        s.send_message(mail)
    s.quit()


def handle_bot_message(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    if content_type == "text":
        text = msg["text"]
        user = msg["from"]
        uid = msg["from"]["id"]
        if chat_type == "group":
            sprint("Group message from {} ({}): {}".format(user, uid, text))
            if config.OFFLINE_MODE or config.TEST_MODE:
                sprint("Not sending email in offline or test mode")
            else:
                send_mail(msg)
        elif chat_type == "private":
            sprint("Private message from {} ({}): {}".format(user, uid, text))
            # This is intended behaviour. This bot doesn't respond to private messages
            # bot.sendMessage(config.GROUP_ID, "{} tuschelt!".format(get_alias(msg["from"])))
            # msg["text"] = "*tuschel*"
            # send_mail(msg)
    elif content_type in ['audio', 'document', 'photo', 'sticker', 'video', 'voice', 'contact', 'location', 'venue']:
        with tempfile.TemporaryDirectory() as tmpdir:
            if content_type == 'photo':
                bot.download_file(msg['photo'][-1]['file_id'], tmpdir+'/photo')
                msg["photo"] = tmpdir+'/photo'
                send_mail(msg)
            else:
                bot.download_file(msg[content_type]['file_id'], tmpdir+'/file')
                msg[content_type] = tmpdir+'/file'
                send_mail(msg)
    elif content_type in ['new_chat_member', 'left_chat_member']:
        new_msg = {"from": msg[content_type]}
        new_msg["text"] = "*tschüss*" if content_type == 'left_chat_member' else "*hallo*"
        send_mail(new_msg)


def handle_reply_mail(mail):
    global msgs
    msgs += 1

    the_mail = email.message_from_string(mail)
    
    the_sender = the_mail["from"]
    sender_parts = the_sender.split(" ")
    if len(sender_parts) != 2:
        sender_parts = sender_parts[0].split("@")
        the_sender = sender_parts[0].strip("<")
    else:
        the_sender = sender_parts[0]
 
    the_text = ""
    if the_mail.is_multipart():
        for part in the_mail.walk():
            if part.get_content_type() == "text/plain":
                the_text += part.get_payload()
            elif not (part.get_content_type().startswith('message/') or part.get_content_type().startswith('multipart/')):
                filename = part.get_filename('file.bin')
                if config.OFFLINE_MODE or config.TEST_MODE:
                    sprint("Received file:", filename)
                else:
                    content = part.get_payload()
                    with tempfile.TemporaryDirectory() as tmpdir:
                        with open(tmpdir+'/file', 'wb') as fp:
                            fp.write(content)
                        with open(tmpdir+'/file', 'rb') as fp:
                            bot.sendDocument(config.GROUP_ID, (filename, fp), caption='Gesendet von: {}'.format(the_sender))
                        send_mail({"from": the_sender, "document": tmpdir+'/file'}, telegram=False)
    else:
        the_text = the_mail.get_payload()

    the_msg = " {} sagt: {}".format(the_sender, the_text)
    if config.OFFLINE_MODE or config.TEST_MODE:
        sprint("The message:", the_msg)
    else:
        bot.sendMessage(config.GROUP_ID, the_msg)
        send_mail({"from": the_sender, "text": the_text}, telegram=False)

    return True


def xmlrpc_worker():
    server.serve_forever()


if __name__ == "__main__":

    server = SimpleXMLRPCServer(("localhost", 4711), logRequests=False)
    server.register_function(handle_reply_mail)
    
    if config.OFFLINE_MODE:
        sprint("Starting in offline mode")
    else:
        bot = telepot.Bot(config.BOT_TOKEN)
        bot.message_loop(handle_bot_message)
    sprint("Starting", config.BOT_NAME)
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
