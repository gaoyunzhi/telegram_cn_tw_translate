import cached_url
import time
import random
import yaml

with open('credential') as f:
	credential = yaml.load(f, Loader=yaml.FullLoader)

class Timer(object):
	def __init__(self):
		self.reset()

	def reset(self):
		self.last_request = 0

	def wait(self, wait):
		if time.time() - self.last_request < wait:
			print('wait', wait + self.last_request - time.time())
			time.sleep(wait + self.last_request - time.time())
		self.last_request = time.time()

class SoupGet(object):
	def __init__(self):
		self.timer = Timer()
		self.reset()

	def reset(self):
		self.num_requests = 0
		self.timer.reset()

	def getContent(self, url):
		self.num_requests += 1
		wait = min(random.random() * 10, self.num_requests / 3 * random.random())
		self.timer.wait(wait)
		print('getContent', url)
		return cached_url.get(url, 
			headers = {'cookie': credential['cookie']})