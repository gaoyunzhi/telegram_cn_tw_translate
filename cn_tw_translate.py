#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
from telegram.ext import Updater, MessageHandler, Filters
from telegram import InputMediaPhoto
import threading
from telegram_util import log_on_fail
import sys
from datetime import datetime
from opencc import OpenCC
import time
cc = OpenCC('s2tw')

scheulded = False
queue = []

wait = 60 * 5
if 'test' in sys.argv:
	wait = 1

def loadFile(fn):
	with open(fn) as f:
		return yaml.load(f, Loader=yaml.FullLoader)

credential = loadFile('credential')
config = loadFile('config')

tele = Updater(credential['bot_token'], use_context=True)
bot = tele.bot # cn_tw_translate_bot
debug_group = bot.get_chat(-1001198682178)
test_group = bot.get_chat(-353219661)

def popMessages(msg):
	global queue
	if not msg.media_group_id:
		return []
	result = [m for (reciever, m) in queue if m.media_group_id == msg.media_group_id]
	queue = [(reciever, m) for (reciever, m) in queue if m.media_group_id != msg.media_group_id]
	return result

def process():
	global queue
	new_queue = []
	while queue:
		reciever, msg = queue.pop()
		if time.time() - datetime.timestamp(msg.date) < wait:
			new_queue.append((reciever, msg))
			continue
		try:
			r = bot.forward_message(chat_id = test_group.id, 
				from_chat_id = msg.chat_id, message_id = msg.message_id)
			r.delete()
		except:
			continue
		if msg.text:
			bot.send_message(reciever, cc.convert(msg.text))
			continue
		# TODO: support docs, movies also
		media = []
		for m in [msg] + popMessages(msg):
			photo = InputMediaPhoto(m.photo[-1].file_id, 
				caption=cc.convert(m.caption_markdown), 
				parse_mode='Markdown')
			if m.caption_markdown:
				media = [photo] + media
			else:
				media.append(photo)
		bot.send_media_group(reciever, media)
	queue = new_queue
	if queue:
		threading.Timer(wait, process).start()
	else:
		global scheulded
		scheulded = False

@log_on_fail(debug_group)
def manage(update, context):
	msg = update.channel_post
	if not msg:
		return
	reciever = config.get(msg.chat.username)
	if not reciever:
		return
	queue.append((reciever, msg))
	global scheulded
	if not scheulded:
		scheulded = True
		threading.Timer(wait, process).start()

tele.dispatcher.add_handler(MessageHandler(
	Filters.update.channel_posts & (~Filters.command), manage))

tele.start_polling()
tele.idle()