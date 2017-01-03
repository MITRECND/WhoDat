import json
from multiprocessing import Queue, JoinableQueue
import Queue as queue   #required for queue.empty exception
import random
import redis
import sys

REDIS_LIST_ID_MAX = 100000000000

class PydatQueue:
	
	def factory(type, args = None):
		if type == "python-queue":
			return Queue()
		if type == "python-joinable-queue":
			return JoinableQueue(maxsize= args['maxsize'])
		if type == "redis":
			return redisQueue(args)
		assert 0, "Bad queue creation: " + type

	factory = staticmethod(factory)

	

'''
interface for redis API

-as redis does not implement a complete queue API, this class serves as 
a wrapper to the redis api in order to provide all queue functionality 
required by the scipt (basically mimic all functionality provided by
python multiprocessing queues)

Arguments are passed via a dictionary. They are:

	'serialize' : True | False (if the item type to be put into the queue is a dict, list, or other object that needs to be serialized; i.e. not a string or number)
	'host' :  IP address of redis instance (direct argument to actual redis api)
	'port' :  port of redis instance (direct argument to actual redis api)
	'db' :    db of the redis instance , if specified (direct argument to actual redis api)
	'unix_socket_path':  unix domain socket path to use for redis instance (direct argument to actual redis api)

'''
class RedisQueue:
	def __init__(args):
		self.redis_list_id = random.randint(0, REDIS_LIST_ID_MAX)
		self.serialize = args['serialize']
		if 'host' in args and "port" in args and "db" in args:
			self.queue = redis.StrictRedis(host= args['host'], port= args['port'], db=args['db'])
		elif 'unix_socket_path' in args:
			self.queue = redis.StrictRedis(unix_socket_path= args['unix_socket_path'])
		else:
			err = "Could not create Redis queue, not enough arguments"
			sys.stdout.write(err)

	'''signal the closing and no longer need for the queue for the
	   calling process

	   redis has no equivalent so no effect
	'''
	def close(self):
		pass


	'''check if queue is empty'''
	def empty(self):
		return True if self.queue.llen(self.redis_list_id)==0 else False


	'''blocking queue get call'''
	def get(self, block = True, timeout = 0):
		item = self.redis_instance.brpop(self.redis_list_id, timeout = timeout)
		if item == "nil":
			#if queue is empty, raise exception that the script is expecting if condition occurs
			raise queue.Empty   
		else:
			#deserialize item if need be, as script is expecting string, dict or list
			if self.serialize:
				item = json.loads(item)
			return item


	'''non-blocking queue get call'''
	def get_nowait(self):	
		item = self.redis_instance.rpop(self.redis_list_id)
		if item == "nil":
			#if queue is empty, raise exception that the script is expecting if condition occurs
			raise queue.Empty   
		else:
			#deserialize item if need be, as script is expecting string, dict or list
			if self.serialize:
				item = json.loads(item)
			return item

	'''blocking join call'''
	def join(self):
		'''TODO: this is a crude polling hack to mimic join() for redis, try to make better'''
		while self.redis_instance.llen(self.redis_list_id) != 0:
			pass
		return


	'''blocking queue put call'''
	def put(self, item):
		#make all items(inserted into queue) a serialized string
		if self.serialize:
			item = json.dumps(str)
		return self.redis_instance.lpush(self.redis_list_id, item)


	'''non-blocking task_done signal call to queue
		
		redis does not have an equivalent so no effect
	'''
	def task_done(self):
		pass





