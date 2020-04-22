#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
from telegram.ext import Updater, MessageHandler, Filters
from telegram import InputMediaPhoto
import threading
from telegram_util import log_on_fail
import sys

def loadFile(fn):
	with open(fn) as f:
    	return yaml.load(f, Loader=yaml.FullLoader)

credential = loadFile('credential')
config = loadFile('config')

tele = Updater(CREDENTIALS['bot_token'], use_context=True)
bot = tele.bot # cn_tw_translate_bot
debug_group = bot.get_chat(-1001198682178)

@log_on_fail(debug_group)
def command(update, context):
    handleCommand(update, context, dbs)

def hold(msg):
    orig_msg = (msg.forward_from_chat.id, msg.forward_from_message_id) if msg.forward_from_chat else (msg.chat_id, msg.message_id)
    dbh.hold(orig_msg, hold_hour = 5)
    if msg.media_group_id:
        dbh.hold(msg.media_group_id, hold_hour = 5)
    cache.add((msg.chat_id, orig_msg[0], orig_msg[1]))

    dbh.hold(msg.chat_id, msg, hold_hour=queue.getHoldHour(msg.chat_id))

@log_on_fail(debug_group)
def addHold(update, context):
    msg = update.effective_message
    if msg:
        hold(msg)
        dbs.record(msg.chat)

@log_on_fail(debug_group)
def manage(update, context):
    msg = update.channel_post
    if not msg:
        return
    for reciever in dbs.getSubsribers(msg.chat_id):
        queue.append((reciever, msg.chat_id, msg.message_id, msg.media_group_id))
    hold(msg)

tele.dispatcher.add_handler(MessageHandler(
    (~Filters.private) & Filters.command, command))
tele.dispatcher.add_handler(MessageHandler(
    Filters.update.channel_posts & (~Filters.command), manage))
tele.dispatcher.add_handler(MessageHandler(
    Filters.update.channel_posts | Filters.group, addHold), group=2)

def forwardMsg(item):
    reciever, chat_id, message_id, media_group_id = item
    if not media_group_id:
        try:
            return [bot.forward_message(chat_id = reciever,
                from_chat_id = chat_id, message_id = message_id)]
        except Exception as e:
            print(item)
            raise e
    media = []
    for mid in queue.pop_all(reciever, chat_id, media_group_id) + [message_id]:
        try:
            r = bot.forward_message(chat_id = debug_group.id, 
                from_chat_id = chat_id, message_id = mid)
            r.delete()
        except Exception as e:
            pass
        if r.photo[-1].file_id not in [x.media for x in media]:
            m = InputMediaPhoto(r.photo[-1].file_id, 
                caption=r.caption_markdown, parse_mode='Markdown')
            if r.caption_markdown:
                media = [m] + media
            else:
                media.append(m)
    if media:
        return bot.send_media_group(reciever, media)
    return []

@log_on_fail(debug_group)
def loopImp():
    dbh.clearHold(debug_group)
    queue_to_push_back = []
    while not queue.empty():
        item = queue.pop()
        queue_to_push_back.append(item)
        reciever, chat_id, message_id, media_group_id = item
        if 'test' in str(sys.argv):
            if reciever != -1001197970228:
                continue
        
        if dbh.onHold(reciever):
            continue
        if media_group_id and dbh.onHold(media_group_id):
            continue
        
        try:
            r = bot.forward_message(chat_id = debug_group.id, 
                from_chat_id = chat_id, message_id = message_id)
            r.delete()
        except:
            if 'test' in str(sys.argv):
                print('message no longer exist.', chat_id, message_id)
            queue_to_push_back.pop()
            continue

        orig_msg = (r.forward_from_chat.id, r.forward_from_message_id) \
            if r.forward_from_chat else (chat_id, message_id)

        if dbh.onHold(orig_msg):
            continue

        if not cache.add((reciever, orig_msg[0], orig_msg[1])):
            if 'test' in str(sys.argv):
                print('message already sent', chat_id, message_id)
            queue_to_push_back.pop()
            continue

        for m in forwardMsg(item):
            hold(m)
        if media_group_id:
            dbh.hold(media_group_id, hold_hour = 5)
        queue_to_push_back.pop()
        hold(r)
    queue.replace(queue_to_push_back[::-1]) # preserve order

loop_count = 0
def loop():
    global loop_count
    if 'test' in str(sys.argv):
        print('loop', loop_count)
    loop_count += 1
    loopImp()
    threading.Timer(HOUR, loop).start() 

if 'skip' not in str(sys.argv):
    threading.Timer(1, loop).start()

tele.start_polling()
tele.idle()