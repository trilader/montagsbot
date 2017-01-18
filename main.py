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
import uuid
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from xmlrpc.server import SimpleXMLRPCServer

__version__ = "0.1.0"

lock = threading.Lock()
msgs = 0

import imghdr
# backport webp support from python 3.5, see https://hg.python.org/cpython/annotate/4fd17e28d4bf/Lib/imghdr.py
def test_webp(h, f):
    if h.startswith(b'RIFF') and h[8:12] == b'WEBP':
        return 'webp'
imghdr.tests.append(test_webp)


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
    if config.OFFLINE_MODE or config.TEST_MODE:
        sprint("Not sending email in offline or test mode")
        return
    if telegram:
        the_sender = get_alias(msg["from"])
    else:
        the_sender = msg["from"]
    mails_to_send = []
    for forward_email in config.EMAILS:
        mail = MIMEMultipart()
        if 'text' in msg:
            mail.attach(MIMEText('{} sagt: {}'.format(the_sender, msg['text'])))
        for i in ['photo', 'sticker']:
            if i in msg:
                with open(msg[i], 'rb') as fp:
                    mail.attach(MIMEImage(fp.read()))
        for i in ['audio', 'voice']:
            if i in msg:
                with open(msg[i], 'rb') as fp:
                    subtype = 'mpeg' if 'audio' else 'opus'
                    mail.attach(MIMEAudio(fp.read(), _subtype=subtype))
        for i in ['document', 'video']:
            if i in msg:
                with open(msg[i], 'rb') as fp:
                    mail.attach(MIMEApplication(fp.read()))
        if 'special' in msg:
            for i in msg['special']:
                major_type = i[1][:i[1].find('/')]
                sub_type = i[1][i[1].find('/')+1:]
                with open(i[0], 'rb') as fp:
                    if major_type == 'image':
                        mail.attach(MIMEImage(fp.read(), _subtype=sub_type))
                    elif major_type == 'audio':
                        mail.attach(MIMEAudio(fp.read(), _subtype=sub_type))
                    elif major_type == 'video':
                        mail.attach(MIMEApplication(fp.read()))
                    elif major_type == 'text':
                        mail.attach(MIMEText(fp.read(), _subtype=sub_type))
                    elif major_type == 'application':
                        mail.attach(MIMEApplication(fp.read(), _subtype=sub_type))
                    else:
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
    user = msg["from"]
    uid = msg["from"]["id"]
    if chat_type == 'private':
        sprint('Private message from {}({})'.format(user, uid))
        return
    if content_type == "text":
        text = msg["text"]
        sprint("Group message from {} ({}): {}".format(user, uid, text))
        send_mail(msg)
    elif content_type in ['audio', 'document', 'photo', 'sticker', 'video', 'voice']:
        with tempfile.TemporaryDirectory() as tmpdir:
            if content_type == 'photo':
                file_id = msg['photo'][-1]['file_id']
                sprint("Got Photo from {} ({}): {}".format(user, uid, file_id))
                bot.download_file(file_id, tmpdir+'/photo')
                msg["photo"] = tmpdir+'/photo'
                send_mail(msg)
            else:
                file_id = msg[content_type]['file_id']
                sprint("Got some content ({}) from {} ({}): {}".format(content_type, user, uid, file_id))
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
 
    new_mail = {'from': the_sender}
    with tempfile.TemporaryDirectory() as tmpdir:
        for part in the_mail.walk():
            part_type = part.get_content_type(decode=True)
            if part_type.startswith('message/') or part_type.startswith('multipart/'):
                sprint('Received mail, skipping current part:', part_type)
                continue
            sprint('Received mail, current part is:', part_type)
            content = part.get_payload(decode=True)
            if part_type == 'text/plain':
                text = content.decode()
                bot_send_message(the_sender, text)
                if 'text' in new_mail:
                    new_mail['text'] += '\n' + text
                else:
                    new_mail['text'] = text
                continue
            major_type = part_type[:part_type.find('/')]
            filename = part.get_filename('file.bin')
            if filename == 'file.bin':
                filename = uuid.uuid4() + '.bin'
            filename = tmpdir+'/'+filename
            if major_type == 'image':
                with open(filename, 'wb') as fp:
                    fp.write(content)
                bot_send_image(the_sender, filename)
            elif major_type == 'audio':
                sub_type = part_type[part_type.find('/')+1:]
                if sub_type in ['mpeg'] and not filename.endswith('.mp3'):
                    filename = filename[:filename.find('.')] + '.mp3'
                with open(filename, 'wb') as fp:
                    fp.write(content)
                bot_send_audio(the_sender, filename)
            elif major_type == 'video':
                sub_type = part_type[part_type.find('/')+1:]
                if sub_type in ['mp4', 'mpeg4-generic'] and not filename.endswith('.mp4'):
                    filename = filename[:filename.find('.')] + '.mp4'
                with open(filename, 'wb') as fp:
                    fp.write(content)
                bot_send_video(the_sender, filename)
            else:
                with open(filename, 'wb') as fp:
                    fp.write(content)
                bot_send_document(the_sender, filename)
            if 'special' in new_mail:
                new_mail['special'].append((filename, part_type))
            else:
                new_mail['special'] = [(filename, part_type)]
        send_mail(new_mail, telegram=False)
    return True

def bot_send_document(sender, filename):
    if config.OFFLINE_MODE or config.TEST_MODE:
        sprint('Not sending document via bot due to offline or test mode')
        return
    with open(filename, 'rb') as fp:
        bot.sendDocument(config.GROUP_ID, (filename, fp),
                         caption="Gesendet von: {}".format(sender))

def bot_send_video(sender, filename):
    if config.OFFLINE_MODE or config.TEST_MODE:
        sprint('Not sending video via bot due to offline or test mode')
        return
    with open(filename, 'rb') as fp:
        if filename.endswith('.mp4'):
            bot.sendVideo(config.GROUP_ID, (filename, fp),
                             caption="Gesendet von: {}".format(sender))
        else:
            bot.sendDocument(config.GROUP_ID, (filename, fp),
                             caption="Gesendet von: {}".format(sender))

def bot_send_audio(sender, filename):
    if config.OFFLINE_MODE or config.TEST_MODE:
        sprint('Not sending audio via bot due to offline or test mode')
        return
    what = None
    with open(filename, 'rb') as fp:
        if fp.read(8) == 'OpusHead'.encode():
            what = 'opus'
    with open(filename, 'rb') as fp:
        if what == 'opus':
            if not filename.endswith('.ogg'):
                filename = filename[:filename.find('.')] + '.ogg'
            bot.sendVoice(config.GROUP_ID, (filename, fp),
                          caption="Gesendet von: {}".format(sender))
        elif filename.endswith('.mp3'):
            bot.sendAudio(config.GROUP_ID, (filename, fp),
                          caption="Gesendet von: {}".format(sender))
        else:
            bot.sendDocument(config.GROUP_ID, (filename, fp),
                          caption="Gesendet von: {}".format(sender))

def bot_send_image(sender, filename):
    if config.OFFLINE_MODE or config.TEST_MODE:
        sprint('Not sending image via bot due to offline or test mode')
        return
    what = imghdr.what(filename)
    if what is None:
        sprint('Not sending image because of unknown file type')
        return
    with open(filename, 'rb') as fp:
        if what in ['gif', 'jpeg', 'png']:
            if not (filename[-3:] == what or (what == 'jpeg' and filename[-4:] in ['.jpg', 'jpeg'])):
                if what == 'jpeg':
                    what = 'jpg'
                filename = filename[:filename.find('.')] + '.' + what
            bot.sendPhoto(config.GROUP_ID, (filename, fp),
                          caption="Gesendet von: {}".format(sender))
        elif what == 'webp':
            if not filename.endswith('.webp'):
                filename = filename[:filename.find('.')] + '.webp'
            bot.sendSticker(config.GROUP_ID, (filename, fp))
        else:
            bot.sendDocument(config.GROUP_ID, (filename, fp),
                          caption="Gesendet von: {}".format(sender))

def bot_send_message(sender, msg):
    if config.OFFLINE_MODE or config.TEST_MODE:
        sprint('Not sending message via bot due to offline or test mode')
        return
    bot.sendMessage(config.GROUP_ID, '{} sagt: {}'.format(sender, msg))

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
